import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DockerPersistenceTests(unittest.TestCase):
    def test_data_home_matches_configuration_and_output_mounts(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        match = re.search(r"\bNEURODAILY_HOME=(/[^\s]+)", dockerfile)
        self.assertIsNotNone(match)
        data_home = match.group(1)
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn(f"./config:{data_home}/config", compose)
        self.assertIn(f"./output:{data_home}/output", compose)

        with TemporaryDirectory() as directory:
            env = os.environ.copy()
            env["NEURODAILY_HOME"] = directory
            subprocess.run([sys.executable, "-c", """
from pathlib import Path
import sys
from neurodaily import ai_summary, config, journal_metrics, mailer, mail_tui, webhooks

root = Path(sys.argv[1])
assert Path(config.DEFAULT_DIRS['output']) == root / 'output'
assert Path(mailer.LAST_PATH).parent == root / 'output'
for file in (config.Config.default_path(), ai_summary.CFG_PATH, mailer.CFG_PATH,
             mail_tui.CFG_PATH, webhooks.CFG_PATH, journal_metrics.OFFICIAL_PATH):
    assert Path(file).parent == root / 'config', file
""", directory], cwd=ROOT, env=env, check=True, timeout=10)

    def test_replace_preserves_old_settings_and_existing_host_file(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "scripts").mkdir()
            (folder / "config").mkdir()
            (folder / "config/email.json").write_text('{"use_host_setting": true}')
            (folder / "bin").mkdir()
            shutil.copyfile(ROOT / "scripts/docker_deploy.sh", folder / "scripts/docker_deploy.sh")
            docker = folder / "bin/docker"
            docker.write_text("""#!/bin/bash
printf '%s\n' "$*" >> "$ND_DOCKER_CALLS"
case "$1" in
  cp)
    case "$2" in
      */ai_summary.json|*/email.json) printf '%s\n' '{"legacy": true}' > "$3" ;;
      *) echo 'Could not find the file' >&2; exit 1 ;;
    esac ;;
esac
""")
            curl = folder / "bin/curl"
            curl.write_text("#!/bin/bash\nprintf '200'\n")
            for helper in (docker, curl):
                helper.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(folder / "bin") + os.pathsep + env["PATH"]
            env["ND_DOCKER_CALLS"] = str(folder / "calls")
            env["VOLUMES"] = "1"
            result = subprocess.run(["bash", str(folder / "scripts/docker_deploy.sh"), "run"],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"legacy"', (folder / "config/ai_summary.json").read_text())
            self.assertIn('"use_host_setting"', (folder / "config/email.json").read_text())
            backup, = (folder / "output").glob(".container-settings.*")
            self.assertIn('"legacy"', (backup / "email.json").read_text())
            self.assertEqual(backup.stat().st_mode & 0o077, 0)
            calls = (folder / "calls").read_text()
            self.assertLess(calls.index("cp "), calls.index("rm -f"))
