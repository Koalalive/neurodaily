# Windows and Linux desktop app (Tauri 2 + Python sidecar)

The desktop app wraps the FastAPI workspace in a Tauri 2 window and bundles the Python server as a sidecar executable. On macOS, install NeuroDaily from the private Homebrew tap and open the workspace in a browser. [macOS setup](MACOS_HOMEBREW.md)

## 1. Architecture

```text
Windows NSIS / MSI or Linux AppImage / DEB
  └─ Tauri shell (Rust + system webview)
       ├─ starts sidecar: neurodaily-server
       │    ├─ sets NEURODAILY_HOME=<user data dir>
       │    ├─ creates config/ + output/ on first run
       │    ├─ prints NEURODAILY_FIRST_RUN / NEURODAILY_PORT
       │    └─ runs FastAPI on 127.0.0.1:<free port>
       └─ navigates the webview to the local workspace
```

- PyInstaller freezes the sidecar using `desktop/sidecar/neurodaily-server.spec`. Tauri reads the executable from `desktop/tauri/src-tauri/binaries/neurodaily-server-<target-triple>`.
- The first workspace tab shows settings. Choose a neuroscience, oncology, or critical care medicine preset, or keep the saved settings. Completed searches open their own report tab.
- Minimizing the window keeps the sidecar and its daily schedule running. On confirmed exit, the shell closes the sidecar's parent pipe and stops scheduled and in-progress delivery.

## 2. User data locations

| OS | Path |
|---|---|
| Windows | `%APPDATA%/NeuroDaily/` |
| Linux | `~/.local/share/neurodaily/` or `$XDG_DATA_HOME/neurodaily` |

The directory holds `config/` and `output/`, including saved reports and the local history database. Keep this directory when moving to a new installation.

## 3. Local build

Install Python 3.12 or later, Node 20 or later, and stable Rust. On Windows, run the following commands from the repository root in PowerShell with MSVC build tools available.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e . pyinstaller
./desktop/build_sidecar.ps1
cd desktop/tauri
npm ci
npm run icon
npx tauri build --bundles nsis,msi
```

On Ubuntu 24.04, install the WebView system dependencies and build from the repository root.

```bash
sudo apt install libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
python3 -m venv .venv
.venv/bin/pip install -e . pyinstaller
bash desktop/build_sidecar.sh
cd desktop/tauri
npm ci
npm run icon
npx tauri build --bundles appimage,deb
```

## 4. CI release matrix

`.github/workflows/release-tauri.yml` packages these desktop targets on version tags.

| Runner | Target | Bundles |
|---|---|---|
| `windows-latest` | `x86_64-pc-windows-msvc` | NSIS and MSI |
| `ubuntu-24.04` | `x86_64-unknown-linux-gnu` | AppImage and DEB |

Each job builds the sidecar, tests it, builds Tauri and uploads the installers. The publish job attaches the verified installers and updater signatures after the release checks pass. [GitHub Actions guide](GITHUB_ACTIONS.md)

### Private desktop updates

Install the Windows or Linux app from the private GitHub Releases page. In the app, choose **更新 → 更新授权…** and save your own GitHub fine-grained personal access token. Select `Koalalive` as the resource owner, limit repository access to `neurodaily` and grant **Contents: Read-only**. If GitHub does not list the repository for your account's token, use your signed-in browser to download the installers.

NeuroDaily stores the credential in the system credential store and checks for updates on startup and every 12 hours. On Linux this uses a Secret Service provider such as GNOME Keyring or KWallet. **检查更新…** runs a check immediately. When a newer version is available, the app asks to download it, verifies its version-bound signature, and asks again before installing and restarting. Configuration and report data live outside the installation directory.

## 5. Signing

Release tags match the desktop app version. The workflow checks the signature for each Windows and Linux installer against the public key embedded in the app. Keep the existing signing key available as the `TAURI_SIGNING_PRIVATE_KEY` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` Actions secrets so users of earlier installations can update. Windows Authenticode uses a separate certificate.

## 6. Troubleshooting

| Symptom | Check |
|---|---|
| Window stays on splash | Run `neurodaily-server` manually and check stderr |
| `failed to start .../neurodaily-server` | Check that the sidecar was built for the right target triple |
| Windows SmartScreen | Check that the downloaded file came from the expected private Release |
| Linux WebView error | Install `libwebkit2gtk-4.1-0` and `libgtk-3-0` |
| Port conflict | Inspect the sidecar startup output for the localhost URL and port |

See [installation requirements](INSTALL_REQUIREMENTS.md) for end-user OS, hardware and optional AI or SMTP requirements.
