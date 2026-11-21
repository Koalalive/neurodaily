"""Require a complete set of installers and version-bound updater signatures."""

import base64
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def verify(directory: Path, tag: str) -> None:
    config = Path(__file__).parent / "tauri" / "src-tauri" / "tauri.conf.json"
    settings = json.loads(config.read_text(encoding="utf-8"))
    version = settings["version"]
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
    pubkey = base64.b64decode(settings["plugins"]["updater"]["pubkey"], validate=True)
    with TemporaryDirectory(prefix="neurodaily-signatures-") as workdir:
        public_key = Path(workdir, "updater.pub")
        public_key.write_bytes(pubkey)
        for suffix in ("aarch64.app.tar.gz", "x64.app.tar.gz", "x64-setup.exe",
                       "x64_en-US.msi", "amd64.AppImage", "amd64.deb"):
            package = asset(suffix)
            signature = asset(f"{suffix}.sig")
            decoded = base64.b64decode(signature.read_text().strip(), validate=True)
            signature_file = Path(workdir, signature.name)
            signature_file.write_bytes(decoded)
            subprocess.run(["minisign", "-Vm", str(package), "-p", str(public_key),
                            "-x", str(signature_file), "-q"], check=True)
            comment = decoded.decode().splitlines()[2].removeprefix("trusted comment: ")
            signed_version = next((field.removeprefix("version:") for field in comment.split("\t")
                                   if field.startswith("version:")), None)
            if signed_version != version:
                raise SystemExit(f"Updater signature {signature.name} must bind version {version}")
            print(f"Verified {package.name}")


if __name__ == "__main__":
    verify(Path(sys.argv[1]), sys.argv[2])
