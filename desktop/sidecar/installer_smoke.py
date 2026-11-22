"""Exercise the release installer and verify an installed app can run a daily search."""

import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

from smoke import (
    check_preserved_sources, check_scheduled_search, check_settings, check_version, fetch_json,
    running_service,
)


def windows_install_registration():
    from winreg import HKEY_CURRENT_USER, OpenKey, QueryValueEx

    path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\NeuroDaily"
    try:
        with OpenKey(HKEY_CURRENT_USER, path) as key:
            directory = Path(QueryValueEx(key, "InstallLocation")[0].strip('"'))
            version = QueryValueEx(key, "DisplayVersion")[0]
            return directory, version
    except FileNotFoundError:
        return None


def install_windows(installer: Path, destination: Path, home: Path, version: str) -> Path:
    registered = windows_install_registration()
    if registered and registered[0] != destination:
        raise RuntimeError("The test requires a Windows user without an existing NeuroDaily installation")
    # NSIS requires an unquoted absolute /D at the end, including paths with spaces.
    prefix = subprocess.list2cmdline([str(installer.resolve()), "/S"])
    env = {**os.environ, "APPDATA": str(home.parent)}
    subprocess.run(f"{prefix} /D={destination}", env=env, check=True, timeout=240)
    registered = windows_install_registration()
    assert registered == (destination, version), f"Unexpected installer registration: {registered}"
    executable = destination / "neurodaily-desktop.exe"
    assert executable.is_file(), f"Missing application in {destination}"
    assert executable.with_name("neurodaily-server.exe").is_file(), "Missing installed sidecar"
    return executable


def install_macos(image: Path, destination: Path) -> Path:
    mount = destination.parent / "mounted"
    mount.mkdir(parents=True)
    response = subprocess.check_output([
        "hdiutil", "attach", "-plist", "-nobrowse", "-readonly", "-mountpoint", str(mount),
        str(image.resolve()),
    ], timeout=90)
    devices = plistlib.loads(response)["system-entities"]
    device = next(entry["dev-entry"] for entry in devices if "dev-entry" in entry)
    try:
        subprocess.run(["ditto", str(mount / "NeuroDaily.app"), str(destination)],
                       check=True, timeout=90)
    finally:
        detach = ["hdiutil", "detach", device]
        if subprocess.run(detach, timeout=30).returncode != 0:
            subprocess.run([*detach, "-force"], check=True, timeout=30)
        mount.rmdir()
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(destination)],
                   check=True, timeout=60)
    return destination / "Contents" / "MacOS" / "neurodaily-desktop"


def start_app(executable, home):
    return running_service(executable, home, desktop=True, use_windows_appdata=os.name == "nt")


def check_report(opener, base_url, run_id):
    with opener.open(f"{base_url}/history/{run_id}", timeout=5) as response:
        assert b"Scheduled smoke result" in response.read(), "Missing original report"


def check_upgrade(baseline, baseline_version, candidate, candidate_version, destination, home):
    app = install_windows(baseline, destination, home, baseline_version)
    with start_app(app, home) as (opener, base_url):
        check_version(opener, base_url, baseline_version)
        check_settings(opener, base_url, home)
        check_scheduled_search(opener, base_url, home)
        saved_config = fetch_json(opener, base_url, "/api/config")
        saved_history = fetch_json(opener, base_url, "/api/history")
        saved_schedule = fetch_json(opener, base_url, "/api/launchd/status")
        assert saved_config["scheduled"]["enabled"], saved_config["scheduled"]
        assert saved_history["count"] == 1, saved_history
        run_id = saved_history["runs"][0]["id"]
        assert saved_schedule["last_run"]["status"] == "completed", saved_schedule
        check_report(opener, base_url, run_id)

    config_file = home / "config" / "config.json"
    original_config = config_file.read_bytes()
    app = install_windows(candidate, destination, home, candidate_version)
    assert config_file.read_bytes() == original_config, "The installer modified the user config"
    with start_app(app, home) as (opener, base_url):
        check_version(opener, base_url, candidate_version)
        check_settings(opener, base_url, home)
        config = fetch_json(opener, base_url, "/api/config")
        for field in ("profile", "search", "scheduled"):
            assert config[field] == saved_config[field], f"Upgrade changed {field}"
        check_preserved_sources(saved_config["sources"], config["sources"])
        history = fetch_json(opener, base_url, f"/api/history/{run_id}")
        original_run = saved_history["runs"][0]
        for field in ("id", "profile", "status", "item_count", "report_path"):
            assert history[field] == original_run[field], f"Upgrade changed history field {field}"
        check_report(opener, base_url, run_id)
        schedule = fetch_json(opener, base_url, "/api/launchd/status")
        for field in ("schedule", "loaded", "last_run"):
            assert schedule[field] == saved_schedule[field], f"Upgrade changed schedule field {field}"
        # A separate profile lets today's automatic search run again without
        # bypassing the preserved once-per-day record for the original profile.
        check_scheduled_search(opener, base_url, home, new_profile="installer-smoke")
    print(f"Installed upgrade {baseline_version} -> {candidate_version} preserved data and ran a scheduled search")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("candidate_version")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--baseline-version")
    args = parser.parse_args()
    if bool(args.baseline) != bool(args.baseline_version):
        parser.error("--baseline and --baseline-version are required together")
    if args.baseline_version == args.candidate_version:
        parser.error("Upgrade verification requires two different versions")
    if os.name == "nt" and any(path.suffix.lower() != ".exe"
                               for path in (args.candidate, args.baseline) if path):
        parser.error("Windows installer verification requires the NSIS setup EXE")
    if sys.platform == "darwin" and (args.candidate.suffix != ".dmg" or args.baseline):
        parser.error("macOS installer verification requires the candidate DMG")
    if os.name != "nt" and sys.platform != "darwin":
        parser.error("Installer verification is available on Windows and macOS")

    with tempfile.TemporaryDirectory(prefix="neurodaily-installer-") as scratch:
        workdir = Path(scratch).resolve()
        home = workdir / "AppData" / "NeuroDaily"
        destination = workdir / "Installed Apps"
        if not args.candidate.is_file() or (args.baseline and not args.baseline.is_file()):
            parser.error("Every requested release installer must exist")
        if args.baseline:
            check_upgrade(args.baseline, args.baseline_version, args.candidate,
                          args.candidate_version, destination, home)
            return
        if os.name == "nt":
            executable = install_windows(args.candidate, destination, home, args.candidate_version)
        else:
            executable = install_macos(args.candidate, destination / "NeuroDaily.app")
        with start_app(executable, home) as (opener, base_url):
            check_version(opener, base_url, args.candidate_version)
            check_settings(opener, base_url, home)
            check_scheduled_search(opener, base_url, home)
        print(f"Installed {args.candidate_version} started, ran a scheduled search and stopped cleanly")


if __name__ == "__main__":
    main()
