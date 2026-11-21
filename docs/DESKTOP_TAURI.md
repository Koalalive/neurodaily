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
- Minimizing the window keeps the sidecar and its daily schedule running.
- Closing the window or quitting requests confirmation. The shell closes the
  sidecar's parent pipe on confirmed exit to stop scheduled and in-progress delivery.
- Every desktop launch opens `/settings`. Choose the neuroscience or oncology preset,
  or keep the saved settings. Save to continue to `/run`, then start a search to open its report.

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
- `desktop/tauri/src-tauri/target/release/bundle/dmg/NeuroDaily_1.0.1_aarch64.dmg`

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
| macos-15 | aarch64-apple-darwin | app, dmg |
| macos-15-intel | x86_64-apple-darwin | app, dmg |
| windows-latest | x86_64-pc-windows-msvc | nsis, msi |
| ubuntu-24.04 | x86_64-unknown-linux-gnu | appimage, deb |

Each job builds and smoke-tests the sidecar, builds Tauri, and uploads its
installers. On macOS, the workflow creates and verifies the DMG from the Tauri
app bundle. The publish job attaches the installers after all builds pass.

### Private desktop updates

Install v1.0.2 or later from the private GitHub Releases page once. In the app,
choose **更新 → 更新授权…** and save your own GitHub fine-grained personal access
token. Select `Koalalive` as the resource owner, limit repository access to
`neurodaily`, and grant **Contents: Read-only**. If GitHub does not offer the
repository for your account's token, download new installers from Releases
using your signed-in browser.

NeuroDaily stores the credential in the system credential store and checks for
updates on startup and every 12 hours. On Linux this uses a Secret Service
provider such as GNOME Keyring or KWallet. **检查更新…** runs a check immediately.
When a newer version is available, the app asks to download it, verifies its
version-bound signature, and asks again before installing and restarting.
Configuration and report data live outside the installation directory.

Release tags must match the desktop app version. The release workflow builds
signed update packages for macOS, Windows NSIS/MSI and Linux AppImage/deb,
checks that the complete set is available, and publishes the draft release.
Configure `TAURI_SIGNING_PRIVATE_KEY` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`
as Actions secrets. Keep a backup of the original signing key so later
versions can update existing installations.

## 5. Signing & notarization

- macOS builds use ad hoc bundle signing by default. Packaging checks the app
  code signature before and after copying it into the DMG and runs the signed
  sidecar. The ad hoc build uses `hardenedRuntime: false` so the sidecar can load
  the bundled Python libraries. An ad hoc build downloaded from a trusted source
  may still require approval in Privacy & Security.
- For Apple notarization, sign the frozen Python libraries and the app with the
  same Developer ID Application identity, enable `hardenedRuntime` in the release
  configuration, and configure Tauri's Apple notarization credentials.
- Windows: Authenticode certificate (Tauri supports `WINDOWS_CERTIFICATE`).
- Linux: no OS-level signing required; publish checksums.

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Window stays on splash | Sidecar failed; run `neurodaily-server` manually and check stderr |
| `failed to start .../neurodaily-server` | Sidecar missing or wrong target triple; rebuild with `desktop/build_sidecar.sh` |
| macOS “app is damaged” | Verify the download hash and run `codesign --verify --deep --strict /Applications/NeuroDaily.app`. If the signature fails, replace it with a verified build. |
| Windows SmartScreen | Unsigned installer; use More info → Run anyway |
| Linux webview error | Install `libwebkit2gtk-4.1-0` / `libgtk-3-0` |
| Port conflict | Sidecar chooses a free localhost port automatically |

## 7. Requirements

See [`INSTALL_REQUIREMENTS.md`](INSTALL_REQUIREMENTS.md) for end-user OS,
CPU/RAM/disk and optional API/SMTP requirements.
