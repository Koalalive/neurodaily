"""Check that a frozen sidecar starts with an empty user data directory."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import ProxyHandler, build_opener


def smoke(executable: Path) -> None:
    with tempfile.TemporaryDirectory() as workdir:
        home = Path(workdir) / "home"
        log = Path(workdir) / "sidecar.log"
        env = {**os.environ, "NEURODAILY_HOME": str(home), "NEURODAILY_PORT": "0",
               "NEURODAILY_MANAGED": "1"}
        with log.open("wb") as output:
            process = subprocess.Popen([str(executable.resolve())], cwd=workdir,
                                       env=env, stdin=subprocess.PIPE, stdout=output,
                                       stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 90
            while process.poll() is None and time.monotonic() < deadline:
                lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
                port = next((line.partition("=")[2] for line in lines
                             if line.startswith("NEURODAILY_PORT=")), None)
                if port:
                    assert "NEURODAILY_FIRST_RUN=1" in lines
                    assert (home / "config" / "config.json").is_file()
                    opener = build_opener(ProxyHandler({}))
                    for route in ("/settings", "/api/status", "/run"):
                        with opener.open(f"http://127.0.0.1:{port}{route}", timeout=5) as response:
                            assert response.status == 200, route
                    with opener.open(f"http://127.0.0.1:{port}/api/config/presets", timeout=5) as response:
                        profiles = {preset["config"]["profile"] for preset in json.load(response)}
                        assert {"neuro", "oncology"} <= profiles, profiles
                    with opener.open(f"http://127.0.0.1:{port}/api/launchd/status", timeout=5) as response:
                        assert json.load(response)["backend"] == "desktop"
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError(log.read_text(encoding="utf-8", errors="replace"))
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/pid", str(process.pid), "/t", "/f"],
                                   stdout=subprocess.DEVNULL, check=False)
                else:
                    process.kill()
                process.wait(timeout=5)
                raise
            assert process.returncode == 0, log.read_text(encoding="utf-8", errors="replace")
        print("Frozen sidecar started with the desktop scheduler and stopped when its parent pipe closed")


if __name__ == "__main__":
    smoke(Path(sys.argv[1]))
