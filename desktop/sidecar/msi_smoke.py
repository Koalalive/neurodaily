"""Install and run the Windows MSI on a fresh Windows test machine."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from smoke import check_scheduled_search, check_settings, check_version, running_service


def registered_versions() -> set[str]:
    import winreg

    versions = set()
    uninstall_key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            access = winreg.KEY_READ | view
            try:
                key = winreg.OpenKey(hive, uninstall_key, 0, access)
            except FileNotFoundError:
                continue
            with key:
                for index in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        name = winreg.EnumKey(key, index)
                        with winreg.OpenKey(key, name, 0, access) as entry:
                            if winreg.QueryValueEx(entry, "DisplayName")[0] == "NeuroDaily":
                                try:
                                    version = winreg.QueryValueEx(entry, "DisplayVersion")[0]
                                except FileNotFoundError:
                                    version = "unknown"
                                versions.add(version)
                    except FileNotFoundError:
                        continue
    return versions


def run_installer(action: str, package: Path, log: Path) -> None:
    msiexec = Path(os.environ["SystemRoot"]) / "System32" / "msiexec.exe"
    result = subprocess.run([str(msiexec), action, str(package), "/quiet", "/norestart",
                             "/log", str(log)], timeout=240)
    # 3010 signals a successful operation that requests a reboot. The runner
    # remains active so we can verify that the installed application works now.
    if result.returncode not in (0, 3010):
        diagnostics = []
        if log.is_file():
            data = log.read_bytes()
            encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8"
            diagnostics = [line for line in data.decode(encoding, errors="replace").splitlines()
                           if "Return value 3" in line or "Error " in line]
        raise RuntimeError(f"msiexec {action} returned {result.returncode}\n"
                           + "\n".join(diagnostics[-15:]))


def msi_smoke(package: Path, version: str) -> None:
    program_files = os.environ.get("ProgramW6432") or os.environ["ProgramFiles"]
    install_dir = Path(program_files) / "NeuroDaily"
    if install_dir.exists() or registered_versions():
        raise RuntimeError("Use a fresh Windows test machine without NeuroDaily installed")

    with tempfile.TemporaryDirectory(prefix="neurodaily-msi-") as directory:
        scratch = Path(directory).resolve()
        home = scratch / "AppData" / "NeuroDaily"
        try:
            run_installer("/i", package, scratch / "install.log")
            installed = registered_versions()
            assert installed == {version}, f"Unexpected MSI registration: {installed}"
            executable = install_dir / "neurodaily-desktop.exe"
            assert executable.is_file(), f"Missing MSI application at {executable}"
            assert executable.with_name("neurodaily-server.exe").is_file(), "Missing MSI sidecar"
            with running_service(executable, home, desktop=True, use_windows_appdata=True) as (opener, base_url):
                check_version(opener, base_url, version)
                check_settings(opener, base_url, home)
                check_scheduled_search(opener, base_url, home)
        finally:
            if registered_versions():
                run_installer("/x", package, scratch / "uninstall.log")

    assert not registered_versions(), "MSI uninstall left the product registered"
    print(f"MSI {version} installed, completed a scheduled search, stopped and uninstalled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("version")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("MSI verification requires Windows")
    if args.package.suffix.lower() != ".msi" or not args.package.is_file():
        parser.error("An existing MSI package is required")
    msi_smoke(args.package.resolve(), args.version)
