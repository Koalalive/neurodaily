"""NeuroDaily desktop sidecar.

Tauri starts this executable; it prepares a writable app home, starts the
FastAPI server on localhost, and prints machine-readable startup markers.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from threading import Thread


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
        sched["enabled"] = False
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


def main() -> None:
    managed = os.environ.get("NEURODAILY_MANAGED") == "1"
    if os.name == "nt" and any(stream is None for stream in (sys.stdin, sys.stdout, sys.stderr)):
        # The windowed bootloader has standard streams only when the desktop
        # shell supplies them. A direct double-click must not start a server.
        raise SystemExit(1 if managed else 0)

    home = app_home()
    os.environ["NEURODAILY_HOME"] = str(home)
    os.environ["NEURODAILY_NO_OPEN"] = "1"
    first_run = prepare_home(home)

    port = int(os.environ.get("NEURODAILY_PORT") or 0)
    print(f"NEURODAILY_HOME={home}", flush=True)
    print(f"NEURODAILY_FIRST_RUN={1 if first_run else 0}", flush=True)
    if os.name == "nt" and managed:
        from ctypes import windll
        print(f"NEURODAILY_CONSOLE={int(bool(windll.kernel32.GetConsoleWindow()))}", flush=True)

    from neurodaily.webapp import create_app
    import uvicorn

    class DesktopServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            if self.started:
                bound_port = self.servers[0].sockets[0].getsockname()[1]
                self.config.app.state.base_url = f"http://127.0.0.1:{bound_port}"
                print(f"NEURODAILY_PORT={bound_port}", flush=True)

    if managed:
        # The desktop shell owns the write end of this pipe for its entire life.
        # Closing it stops delivery even if the PyInstaller bootloader has a child.
        def stop_on_eof():
            sys.stdin.buffer.read()
            os._exit(0)

        Thread(target=stop_on_eof, name="neurodaily-parent", daemon=True).start()

    app = create_app(str(home / "config" / "config.json"), desktop=True, open_report_browser=not managed)
    server = DesktopServer(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info"))
    server.run()


if __name__ == "__main__":
    main()
