"""Check a Debian upgrade or AppImage launch on a disposable Linux test runner."""

import argparse
from pathlib import Path
import shlex
import subprocess
import sys
from tempfile import TemporaryDirectory

from smoke import (
    check_preserved_sources, check_scheduled_search, check_settings, check_version, fetch_json,
    running_service, smoke,
)


def deb_field(path, field):
    return subprocess.check_output(["dpkg-deb", "-f", path, field], text=True, timeout=30).strip()


def deb_version(package):
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${db:Status-Abbrev}${Version}", package],
        text=True, capture_output=True, timeout=30,
    )
    if result.returncode == 0 and result.stdout.startswith("ii "):
        return result.stdout[3:]
    return None


def install_deb(path, package, version):
    subprocess.run(["sudo", "apt-get", "install", "-y", str(path)], check=True, timeout=240)
    assert deb_version(package) == version, f"Installed Debian package is not {package} {version}"
    app = Path("/usr/bin/neurodaily-desktop")
    assert app.is_file(), "Debian installer did not install the desktop launcher"
    assert app.with_name("neurodaily-server").is_file(), "Debian installer did not install the sidecar"
    return app


def report_bytes(opener, base_url, path):
    with opener.open(base_url + path, timeout=5) as response:
        return response.read()


def check_deb_upgrade(baseline, baseline_version, candidate, candidate_version, home):
    package = deb_field(baseline, "Package")
    assert package and deb_field(candidate, "Package") == package, "The installers use different Debian package names"
    assert deb_field(baseline, "Version") == baseline_version, "Baseline Debian artifact version mismatch"
    assert deb_field(candidate, "Version") == candidate_version, "Candidate Debian artifact version mismatch"
    assert deb_version(package) is None, "The upgrade check requires a clean, disposable Linux runner"

    app = install_deb(baseline, package, baseline_version)
    with running_service(app, home, desktop=True) as (opener, base_url):
        check_version(opener, base_url, baseline_version)
        check_settings(opener, base_url, home)
        check_scheduled_search(opener, base_url, home)
        config = fetch_json(opener, base_url, "/api/config")
        history = fetch_json(opener, base_url, "/api/history")
        schedule = fetch_json(opener, base_url, "/api/launchd/status")
        assert config["scheduled"]["enabled"], config["scheduled"]
        assert schedule["last_run"]["status"] == "completed", schedule
        assert history["count"] == 1, history
        run = history["runs"][0]
        report_url = f"/history/{run['id']}/report"
        report = report_bytes(opener, base_url, report_url)
        assert b"Scheduled smoke result" in report, "The baseline report is missing the offline fixture"

    config_file = home / "config" / "config.json"
    original_config = config_file.read_bytes()
    app = install_deb(candidate, package, candidate_version)
    assert config_file.read_bytes() == original_config, "The upgrade modified the configuration file"
    with running_service(app, home, desktop=True) as (opener, base_url):
        check_version(opener, base_url, candidate_version)
        check_settings(opener, base_url, home)
        loaded_config = fetch_json(opener, base_url, "/api/config")
        for field in ("profile", "search", "scheduled"):
            assert loaded_config[field] == config[field], f"The upgrade changed config field {field}"
        check_preserved_sources(config["sources"], loaded_config["sources"])
        loaded_history = fetch_json(opener, base_url, f"/api/history/{run['id']}")
        for field in ("id", "profile", "status", "item_count", "report_path"):
            assert loaded_history[field] == run[field], f"The upgrade changed history field {field}"
        assert report_bytes(opener, base_url, report_url) == report, "The upgrade changed the saved report"
        assert report_bytes(opener, base_url, "/") == report, "The desktop did not restore the saved report"
        loaded_schedule = fetch_json(opener, base_url, "/api/launchd/status")
        for field in ("schedule", "loaded", "last_run"):
            assert loaded_schedule[field] == schedule[field], f"The upgrade changed scheduler field {field}"
        check_scheduled_search(opener, base_url, home, new_profile="deb-upgrade-smoke")
    print(f"Debian {baseline_version} -> {candidate_version} preserved config, history, report and schedule")


def check_appimage(candidate, version, workdir):
    candidate.chmod(candidate.stat().st_mode | 0o100)
    # The AppImage runtime extracts its own payload without requiring a FUSE
    # mount on the runner. Launch the original entry point from the extracted image.
    with (workdir / "appimage-extract.log").open("wb") as log:
        result = subprocess.run([candidate, "--appimage-extract"], cwd=workdir, timeout=90,
                                stdout=log, stderr=log)
    if result.returncode != 0:
        errors = (workdir / "appimage-extract.log").read_text(encoding="utf-8", errors="replace")
        raise RuntimeError(f"AppImage runtime could not extract the candidate:\n{errors}")
    appdir = workdir / "squashfs-root"
    entrypoint = appdir / "AppRun"
    assert entrypoint.is_file(), "The AppImage extraction did not include AppRun"
    # Keep AppRun's original path, even if it is a symlink. AppRun uses the
    # AppImage runtime environment to locate its bundled binaries and libraries.
    launch = workdir / "launch-appimage"
    launch.write_text(f'#!/bin/sh\n'
                      f'export APPIMAGE={shlex.quote(str(candidate))}\n'
                      f'export APPDIR={shlex.quote(str(appdir))}\n'
                      f'exec {shlex.quote(str(entrypoint))} "$@"\n', encoding="utf-8")
    launch.chmod(0o700)
    smoke(launch, desktop=True, expected_version=version)
    print(f"AppImage {version} launched in extract-and-run mode and completed a scheduled search")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("version")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--baseline-version")
    args = parser.parse_args()
    if not sys.platform.startswith("linux"):
        parser.error("This smoke check requires a Linux runner")
    candidate = args.candidate.resolve()
    if not candidate.is_file() or candidate.suffix not in (".deb", ".AppImage"):
        parser.error("The candidate must be an existing DEB or AppImage")
    with TemporaryDirectory(prefix="neurodaily-linux-installer-") as folder:
        workdir = Path(folder)
        if candidate.suffix == ".AppImage":
            if args.baseline or args.baseline_version:
                parser.error("The AppImage smoke check takes only a candidate")
            check_appimage(candidate, args.version, workdir)
        else:
            if not args.baseline or not args.baseline_version or args.baseline_version == args.version:
                parser.error("A DEB upgrade requires both --baseline and a different --baseline-version")
            baseline = args.baseline.resolve()
            if not baseline.is_file() or baseline.suffix != ".deb":
                parser.error("The baseline must be an existing DEB")
            check_deb_upgrade(baseline, args.baseline_version, candidate, args.version, workdir / "home")


if __name__ == "__main__":
    main()
