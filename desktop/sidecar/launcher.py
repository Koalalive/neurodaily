"""NeuroDaily desktop sidecar.

Tauri starts this executable; it prepares a writable app home, starts the
FastAPI server on localhost, and prints machine-readable startup markers.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
from pathlib import Path


def app_home() -> Path:
    override = os.environ.get("NEURODAILY_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "NeuroDaily"
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "NeuroDaily"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "neurodaily"


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _copy_if_missing(src: Path, dst: Path) -> bool:
    if dst.exists() or not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def prepare_home(home: Path) -> bool:
    """Create config/output and return True on first run."""
    root = resource_root()
    cfg_dir = home / "config"
    out_dir = home / "output"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    first_run = not (cfg_dir / "config.json").exists()
    if first_run:
        example = root / "config.example.json"
        if not example.exists():
            raise SystemExit(f"missing config.example.json at {example}")
        data = json.loads(example.read_text(encoding="utf-8"))
        data.setdefault("output", {})["dir"] = str(out_dir)
        sched = data.setdefault("scheduled", {})
        launchd = sched.setdefault("launchd", {})
        launchd["stdout"] = str(out_dir / "launchd_stdout.log")
        launchd["stderr"] = str(out_dir / "launchd_stderr.log")
        (cfg_dir / "config.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    for name in ("email", "ai_summary", "webhooks"):
        _copy_if_missing(root / "config" / f"{name}.example.json",
                         cfg_dir / f"{name}.json")
    return first_run


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> None:
    home = app_home()
    os.environ["NEURODAILY_HOME"] = str(home)
    os.environ["NEURODAILY_NO_OPEN"] = "1"
    first_run = prepare_home(home)

    port = int(os.environ.get("NEURODAILY_PORT") or free_port())
    print(f"NEURODAILY_HOME={home}", flush=True)
    print(f"NEURODAILY_FIRST_RUN={1 if first_run else 0}", flush=True)
    print(f"NEURODAILY_PORT={port}", flush=True)

    from neurodaily.webapp import create_app
    import uvicorn

    app = create_app(str(home / "config" / "config.json"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
