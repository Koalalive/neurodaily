#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::ffi::OsStr;
use std::io::{BufRead, BufReader, Write};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use tauri::{
    webview::{DownloadEvent, NewWindowResponse},
    AppHandle, Manager, RunEvent, Url, WebviewWindow, WebviewWindowBuilder, WindowEvent,
};
use tauri_plugin_dialog::{DialogExt, FilePath, MessageDialogButtons, MessageDialogKind};
use tauri_plugin_opener::OpenerExt;

#[cfg(target_os = "macos")]
mod macos_quit;
mod updates;

struct Sidecar(Mutex<Option<Child>>);

fn background_command(program: impl AsRef<OsStr>) -> Command {
    let command = Command::new(program);
    #[cfg(windows)]
    let command = {
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let mut command = command;
        command.creation_flags(CREATE_NO_WINDOW);
        command
    };
    command
}

#[derive(Debug, PartialEq, Eq)]
enum LinkDestination {
    App,
    Browser,
    Block,
}

fn link_destination(url: &Url, sidecar_port: u16) -> LinkDestination {
    match (url.scheme(), url.host_str()) {
        ("tauri", Some("localhost")) if url.port().is_none() => LinkDestination::App,
        ("http" | "https", Some("tauri.localhost")) if url.port().is_none() => LinkDestination::App,
        ("http", Some("127.0.0.1"))
            if sidecar_port != 0 && url.port_or_known_default() == Some(sidecar_port) =>
        {
            LinkDestination::App
        }
        ("http" | "https", Some(_)) => LinkDestination::Browser,
        _ => LinkDestination::Block,
    }
}

fn is_config_download(url: &Url, sidecar_port: u16) -> bool {
    url.scheme() == "http"
        && url.host_str() == Some("127.0.0.1")
        && sidecar_port != 0
        && url.port_or_known_default() == Some(sidecar_port)
        && url.path() == "/api/config/export"
}

fn save_config_download(window: &WebviewWindow, url: Url, suggested: &Path) {
    let name = suggested
        .file_name()
        .and_then(OsStr::to_str)
        .unwrap_or("neurodaily-config.json");
    let app = window.app_handle().clone();
    let title = match url.query_pairs().find(|(key, _)| key == "language") {
        Some((_, language)) if language == "en" => "Export saved settings",
        Some((_, language)) if language == "ru" => "Экспорт сохранённых настроек",
        _ => "导出已保存的配置",
    };
    app.dialog()
        .file()
        .set_parent(window)
        .set_title(title)
        .set_file_name(name)
        .add_filter("JSON", &["json"])
        .save_file(move |target| {
            let Some(target) = target else { return };
            tauri::async_runtime::spawn(async move {
                if let Err(error) = download_config(url, target).await {
                    eprintln!("Could not export config: {error}");
                    app.dialog()
                        .message("无法保存配置文件。请检查所选目录的写入权限，或稍后再试。")
                        .title("导出失败")
                        .kind(MessageDialogKind::Error)
                        .show(|_| {});
                }
            });
        });
}

async fn download_config(
    url: Url,
    target: FilePath,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let path = target.into_path()?;
    let response = reqwest::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(10))
        .build()?
        .get(url)
        .send()
        .await?;
    if !response.status().is_success() {
        return Err(format!("Config export returned HTTP {}", response.status()).into());
    }
    let bytes = response.bytes().await?;
    tauri::async_runtime::spawn_blocking(move || write_config_export(&path, &bytes)).await??;
    Ok(())
}

fn write_config_export(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let folder = path.parent().ok_or(std::io::ErrorKind::InvalidInput)?;
    let mut temporary = tempfile::NamedTempFile::new_in(folder)?;
    temporary.write_all(bytes)?;
    temporary.persist(path)?;
    Ok(())
}

fn open_in_browser(app: &AppHandle, url: &Url) {
    if let Err(error) = app.opener().open_url(url.as_str(), None::<&str>) {
        eprintln!("Could not open external link: {error}");
        app.dialog()
            .message("系统未能启动默认浏览器。请检查系统的默认浏览器设置后重试。")
            .title("无法打开外部链接")
            .kind(MessageDialogKind::Error)
            .show(|_| {});
    }
}

fn create_main_window(app: &tauri::App, sidecar_port: Arc<AtomicU16>) -> tauri::Result<()> {
    let config = app
        .config()
        .app
        .windows
        .iter()
        .find(|window| window.label == "main")
        .expect("main window configuration");
    let navigation_port = Arc::clone(&sidecar_port);
    let download_port = Arc::clone(&sidecar_port);
    let navigation_app = app.handle().clone();
    let popup_app = app.handle().clone();
    let mut builder = WebviewWindowBuilder::from_config(app, config)?;
    if let Some(icon) = app.default_window_icon() {
        builder = builder.icon(icon.clone())?;
    }
    builder
        .initialization_script(
            r#"
            document.addEventListener('click', (event) => {
                if (event.defaultPrevented || event.button !== 0 || !(event.target instanceof Element)) return;
                const link = event.target.closest('a[href][target="_blank" i]');
                if (!link || !['http:', 'https:'].includes(link.protocol)) return;
                // Route clicks through native navigation before popup policy is applied.
                event.preventDefault();
                window.location.assign(link.href);
            });
            "#,
        )
        .on_navigation(move |url| {
            match link_destination(url, navigation_port.load(Ordering::Relaxed)) {
                LinkDestination::App => true,
                LinkDestination::Browser => {
                    open_in_browser(&navigation_app, url);
                    false
                }
                LinkDestination::Block => false,
            }
        })
        .on_new_window(move |url, _| {
            match link_destination(&url, sidecar_port.load(Ordering::Relaxed)) {
                LinkDestination::App => {
                    let handle = popup_app.clone();
                    let _ = popup_app.run_on_main_thread(move || {
                        if let Some(window) = handle.get_webview_window("main") {
                            let _ = window.navigate(url);
                        }
                    });
                }
                LinkDestination::Browser => open_in_browser(&popup_app, &url),
                LinkDestination::Block => {}
            }
            NewWindowResponse::Deny
        })
        .on_download(move |webview, event| match event {
            DownloadEvent::Requested { url, destination } => {
                if is_config_download(&url, download_port.load(Ordering::Relaxed)) {
                    if let Some(window) = webview.app_handle().get_webview_window("main") {
                        save_config_download(&window, url, destination);
                    }
                }
                false
            }
            _ => true,
        })
        .build()?;
    Ok(())
}

#[derive(Default)]
struct QuitState {
    prompt_open: AtomicBool,
    confirmed: AtomicBool,
}

fn confirm_quit(app: &AppHandle) {
    if app
        .state::<QuitState>()
        .prompt_open
        .swap(true, Ordering::Relaxed)
    {
        return;
    }
    let handle = app.clone();
    app.dialog()
        .message("退出将停止定时推送，并中断正在进行的检索或推送。若要继续运行，可以最小化窗口。")
        .title("退出 NeuroDaily？")
        .kind(MessageDialogKind::Warning)
        .buttons(MessageDialogButtons::OkCancelCustom(
            "退出".into(),
            "继续运行".into(),
        ))
        .show(move |exit| {
            let state = handle.state::<QuitState>();
            if exit {
                state.confirmed.store(true, Ordering::Relaxed);
                handle.exit(0);
            } else {
                state.prompt_open.store(false, Ordering::Relaxed);
            }
        });
}

fn stop_sidecar(app: &AppHandle) {
    let state = app.state::<Sidecar>();
    let child = state.0.lock().ok().and_then(|mut guard| guard.take());
    let Some(mut child) = child else { return };
    drop(child.stdin.take());
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        match child.try_wait() {
            Ok(Some(_)) => return,
            Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(25)),
            _ => break,
        }
    }
    #[cfg(windows)]
    if background_command("taskkill")
        .args(["/PID", &child.id().to_string(), "/T", "/F"])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .is_ok_and(|status| status.success())
    {
        let _ = child.wait();
        return;
    }
    if child.kill().is_ok() {
        let _ = child.wait();
    }
}

fn sidecar_path() -> std::path::PathBuf {
    if let Ok(p) = std::env::var("NEURODAILY_SIDECAR") {
        return p.into();
    }
    let exe = std::env::current_exe().unwrap_or_default();
    let dir = exe.parent().unwrap_or_else(|| std::path::Path::new("."));
    let name = if cfg!(windows) {
        "neurodaily-server.exe"
    } else {
        "neurodaily-server"
    };
    dir.join(name)
}

fn initialize_tls() {
    // Updater uses reqwest's rustls-no-provider feature. Register its ring
    // provider before either the export or authenticated update client starts.
    let _ = rustls::crypto::ring::default_provider().install_default();
}

fn main() {
    initialize_tls();
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![updates::set_update_token])
        .manage(QuitState::default())
        .manage(updates::UpdateCheck::default())
        .setup(|app| {
            #[cfg(target_os = "macos")]
            macos_quit::install(app.handle())?;

            let sidecar_port = Arc::new(AtomicU16::new(0));
            create_main_window(app, Arc::clone(&sidecar_port))?;
            let path = sidecar_path();
            let mut cmd = background_command(&path);
            cmd.env("NEURODAILY_NO_OPEN", "1")
                .env("NEURODAILY_MANAGED", "1")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());

            let mut child = cmd
                .spawn()
                .map_err(|e| format!("failed to start {}: {e}", path.display()))?;

            let stdout = child.stdout.take();
            let stderr = child.stderr.take();
            app.manage(Sidecar(Mutex::new(Some(child))));
            updates::start(app.handle())?;

            let handle = app.handle().clone();
            std::thread::spawn(move || {
                if let Some(stdout) = stdout {
                    for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                        if let Some(port) = line
                            .strip_prefix("NEURODAILY_PORT=")
                            .and_then(|port| port.trim().parse::<u16>().ok())
                            .filter(|port| *port != 0)
                        {
                            sidecar_port.store(port, Ordering::Relaxed);
                            let url = format!("http://127.0.0.1:{port}/desktop")
                                .parse()
                                .expect("valid sidecar URL");
                            let h = handle.clone();
                            let _ = handle.run_on_main_thread(move || {
                                if let Some(w) = h.get_webview_window("main") {
                                    let _ = w.navigate(url);
                                }
                            });
                        }
                    }
                }
            });

            if let Some(stderr) = stderr {
                std::thread::spawn(move || {
                    for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                        eprintln!("[sidecar] {line}");
                    }
                });
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building NeuroDaily")
        .run(|app, event| match event {
            RunEvent::WindowEvent {
                label,
                event: WindowEvent::CloseRequested { api, .. },
                ..
            } if label == "main" && !app.state::<QuitState>().confirmed.load(Ordering::Relaxed) => {
                api.prevent_close();
                confirm_quit(app);
            }
            RunEvent::ExitRequested { api, .. }
                if !app.state::<QuitState>().confirmed.load(Ordering::Relaxed) =>
            {
                api.prevent_exit();
                confirm_quit(app);
            }
            RunEvent::Exit => stop_sidecar(app),
            _ => {}
        });
}

#[cfg(test)]
mod tests {
    use super::{link_destination, LinkDestination, Url};

    #[test]
    fn only_application_origins_are_kept_inside_the_window() {
        let cases = [
            ("tauri://localhost/index.html", LinkDestination::App),
            ("http://tauri.localhost/index.html", LinkDestination::App),
            ("http://127.0.0.1:8031/settings", LinkDestination::App),
            ("http://127.0.0.1:8032/", LinkDestination::Browser),
            (
                "https://tauri.localhost.example.org/",
                LinkDestination::Browser,
            ),
            ("https://doi.org/10.1000/example", LinkDestination::Browser),
            ("file:///test.html", LinkDestination::Block),
        ];
        for (url, expected) in cases {
            assert_eq!(
                link_destination(&Url::parse(url).unwrap(), 8031),
                expected,
                "{url}"
            );
        }
    }

    #[test]
    fn only_the_active_sidecar_can_download_a_config() {
        let path = "/api/config/export";
        let local = Url::parse(&format!("http://127.0.0.1:1234{path}")).unwrap();
        let external = Url::parse(&format!("https://example.org{path}")).unwrap();
        assert!(super::is_config_download(&local, 1234));
        assert!(!super::is_config_download(&local, 0));
        assert!(!super::is_config_download(&local, 1235));
        assert!(!super::is_config_download(&external, 1234));
        assert!(!super::is_config_download(
            &local.join("/api/config").unwrap(),
            1234
        ));
    }

    #[test]
    fn config_export_writes_to_the_selected_directory_and_filename() {
        let folder = tempfile::tempdir().unwrap();
        let path = folder.path().join("研究配置.json");
        let shared_config = br#"{"format":"neurodaily.profile","version":1,"config":{}}"#;
        std::fs::write(&path, b"previous export").unwrap();
        super::write_config_export(&path, shared_config).unwrap();
        assert_eq!(std::fs::read(&path).unwrap(), shared_config);
        assert_eq!(std::fs::read_dir(folder.path()).unwrap().count(), 1);
    }

    #[test]
    fn native_config_download_uses_the_initialized_http_client() {
        use std::io::{Read, Write};

        super::initialize_tls();
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let url = Url::parse(&format!(
            "http://{}/api/config/export",
            listener.local_addr().unwrap()
        ))
        .unwrap();
        let server = std::thread::spawn(move || {
            let (mut socket, _) = listener.accept().unwrap();
            let mut request = [0; 4096];
            assert!(socket.read(&mut request).unwrap() > 0);
            socket
                .write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}")
                .unwrap();
        });
        let folder = tempfile::tempdir().unwrap();
        let path = folder.path().join("shared configuration.json");
        tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap()
            .block_on(super::download_config(
                url,
                tauri_plugin_dialog::FilePath::Path(path.clone()),
            ))
            .unwrap();
        server.join().unwrap();
        assert_eq!(std::fs::read(&path).unwrap(), b"{}");
    }

    #[cfg(windows)]
    #[test]
    fn windows_background_command_keeps_pipes_without_a_console() {
        let output = super::background_command("powershell.exe")
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                r#"
                Add-Type -Namespace NeuroDaily -Name ConsoleProbe -MemberDefinition '
                    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
                '
                if ([NeuroDaily.ConsoleProbe]::GetConsoleWindow() -ne [IntPtr]::Zero) { exit 1 }
                Write-Output 'hidden console with stdout'
                "#,
            ])
            .output()
            .expect("launch hidden Windows helper");
        assert!(output.status.success(), "{:?}", output);
        assert_eq!(
            String::from_utf8_lossy(&output.stdout).trim(),
            "hidden console with stdout"
        );
    }
}
