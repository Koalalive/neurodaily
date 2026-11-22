# Build: .venv/bin/pyinstaller --clean --noconfirm desktop/sidecar/neurodaily-server.spec
# Run from the repository root.
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.getcwd()
datas = [
    (os.path.join(ROOT, "config.example.json"), "."),
    (os.path.join(ROOT, "config", "email.example.json"), "config"),
    (os.path.join(ROOT, "config", "ai_summary.example.json"), "config"),
    (os.path.join(ROOT, "config", "webhooks.example.json"), "config"),
]
examples = os.path.join(ROOT, "config", "examples")
if os.path.isdir(examples):
    datas.append((examples, "config/examples"))
datas += collect_data_files("neurodaily")

hiddenimports = []
for pkg in ("uvicorn", "fastapi", "starlette", "pydantic", "jinja2",
            "feedparser", "httpx", "httpcore", "anyio", "h11", "click",
            "certifi", "email_validator", "sklearn", "scipy", "numpy",
            "joblib", "threadpoolctl"):
    hiddenimports += collect_submodules(pkg)

a = Analysis(
    [os.path.join(ROOT, "desktop", "sidecar", "launcher.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas", "PyQt5", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="neurodaily-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=sys.platform != "win32",
    disable_windowed_traceback=True,
    icon=os.path.join(ROOT, "desktop", "tauri", "src-tauri", "icons", "icon.ico")
    if sys.platform == "win32" else None,
)
