"""Require a complete set of installers and version-bound updater signatures."""

import base64
import json
from pathlib import Path
import re
import sys


def verify(directory: Path, tag: str) -> None:
    config = Path(__file__).parent / "tauri" / "src-tauri" / "tauri.conf.json"
    version = json.loads(config.read_text(encoding="utf-8"))["version"]
    if tag != f"v{version}":
        raise SystemExit(f"Release tag {tag} does not match app version {version}")

    def asset(suffix: str) -> Path:
        name = f"NeuroDaily_{version}_{suffix}"
        matches = list(directory.rglob(name))
        if len(matches) != 1 or not matches[0].stat().st_size:
            raise SystemExit(f"Expected one nonempty release asset named {name}")
        return matches[0]

    for suffix in ("aarch64.dmg", "x64.dmg"):
        asset(suffix)
    for suffix in (
        "aarch64.app.tar.gz",
        "x64.app.tar.gz",
        "x64-setup.exe",
        "x64_en-US.msi",
        "amd64.AppImage",
        "amd64.deb",
    ):
        asset(suffix)
        signature = asset(f"{suffix}.sig")
        lines = base64.b64decode(signature.read_text().strip(), validate=True).decode().splitlines()
        comment = next((line for line in lines if line.startswith("trusted comment:")), "")
        if not re.search(rf"(?:\s|;)version:{re.escape(version)}(?:\s|;|$)", comment):
            raise SystemExit(f"Updater signature {signature.name} must bind version {version}")


if __name__ == "__main__":
    verify(Path(sys.argv[1]), sys.argv[2])
