# Desktop app (Tauri 2 + Python sidecar)

The desktop build wraps the existing FastAPI UI in a Tauri 2 window and bundles
the Python server as a sidecar executable. End users install one app; Python,
Node and Rust are **not** required on their machine.

## 1. Architecture

```text
NeuroDaily.app / NeuroDaily.exe / NeuroDaily.AppImage
  └─ Tauri shell (Rust + system webview)
       ├─ starts sidecar: neurodaily-server
       │    ├─ sets NEURODAILY_HOME=<user data dir>
       │    ├─ creates config/ + output/ on first run
       │    ├─ prints NEURODAILY_FIRST_RUN / NEURODAILY_PORT
       │    └─ runs FastAPI on 127.0.0.1:<free port>
       └─ navigates the webview to the local URL
```

- Sidecar is built with PyInstaller (`desktop/sidecar/neurodaily-server.spec`).
- Tauri external binary: `desktop/tauri/src-tauri/binaries/neurodaily-server-<target-triple>`.
- On quit, the shell kills the sidecar.
- First run goes to `/settings`; later launches go to `/`.

## 2. User data locations

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/NeuroDaily/` |
| Windows | `%APPDATA%\NeuroDaily\` |
| Linux | `~/.local/share/neurodaily/` (or `$XDG_DATA_HOME/neurodaily`) |

Inside: `config/`, `output/`, `last_email.json`. Uninstalling the app does not
delete this directory.

## 3. Local build (macOS example)

Prerequisites: Python 3.12+, Node 20+, Rust stable, Xcode Command Line Tools.

```bash
cd /path/to/neurodaily
python3 -m venv .venv
.venv/bin/pip install -e . pyinstaller

# 1) Python sidecar -> dist/neurodaily-server
#    and copy to binaries/neurodaily-server-<rust host triple>
bash desktop/build_sidecar.sh

# 2) Tauri shell
cd desktop/tauri
npm install
npm run icon
npx tauri build
```

Artifacts:

- `desktop/tauri/src-tauri/target/release/bundle/macos/NeuroDaily.app`
- `desktop/tauri/src-tauri/target/release/bundle/dmg/NeuroDaily_1.0.0_aarch64.dmg`

Windows (PowerShell):

```powershell
.\.venv\Scripts\python -m pip install -e . pyinstaller
.\desktop\build_sidecar.ps1
cd desktop\tauri
npm install
npm run icon
npx tauri build --bundles nsis,msi
```

Linux (Ubuntu 24.04):

```bash
sudo apt install libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
bash desktop/build_sidecar.sh
cd desktop/tauri && npm install && npm run icon
npx tauri build --bundles appimage,deb
```

## 4. CI release matrix

`.github/workflows/release-tauri.yml` builds on tag `v*`:

| Runner | Target | Bundles |
|---|---|---|
| macos-14 | aarch64-apple-darwin | app, dmg |
| macos-13 | x86_64-apple-darwin | app, dmg |
| windows-latest | x86_64-pc-windows-msvc | nsis, msi |
| ubuntu-24.04 | x86_64-unknown-linux-gnu | appimage, deb |

Each job builds the sidecar first, then Tauri, uploads artifacts, and attaches
installers to the GitHub Release.

## 5. Signing & notarization

Unsigned builds work locally but trigger OS warnings:

- macOS: right-click → Open, or `xattr -dr com.apple.quarantine /Applications/NeuroDaily.app`
- Windows: SmartScreen → More info → Run anyway

For clean distribution:

- macOS: Apple Developer ID Application certificate + `notarytool` (Tauri supports
  `APPLE_CERTIFICATE`, `APPLE_ID`, `APPLE_TEAM_ID`).
- Windows: Authenticode certificate (Tauri supports `WINDOWS_CERTIFICATE`).
- Linux: no OS-level signing required; publish checksums.

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Window stays on splash | Sidecar failed; run `neurodaily-server` manually and check stderr |
| `failed to start .../neurodaily-server` | Sidecar missing or wrong target triple; rebuild with `desktop/build_sidecar.sh` |
| macOS “app is damaged” | Unsigned/quarantine; remove quarantine or sign/notarize |
| Windows SmartScreen | Unsigned installer; use More info → Run anyway |
| Linux webview error | Install `libwebkit2gtk-4.1-0` / `libgtk-3-0` |
| Port conflict | Sidecar chooses a free localhost port automatically |

## 7. Requirements

See [`INSTALL_REQUIREMENTS.md`](INSTALL_REQUIREMENTS.md) for end-user OS,
CPU/RAM/disk and optional API/SMTP requirements.
