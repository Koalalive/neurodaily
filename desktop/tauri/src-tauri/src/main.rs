#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::{Manager, RunEvent};

struct Sidecar(Mutex<Option<Child>>);

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

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let path = sidecar_path();
            let mut cmd = Command::new(&path);
            cmd.env("NEURODAILY_NO_OPEN", "1")
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());

            let mut child = cmd
                .spawn()
                .map_err(|e| format!("failed to start {}: {e}", path.display()))?;

            let stdout = child.stdout.take();
            let stderr = child.stderr.take();
            app.manage(Sidecar(Mutex::new(Some(child))));

            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let mut first_run = false;
                if let Some(stdout) = stdout {
                    for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                        if let Some(v) = line.strip_prefix("NEURODAILY_FIRST_RUN=") {
                            first_run = v.trim() == "1";
                        }
                        if let Some(port) = line.strip_prefix("NEURODAILY_PORT=") {
                            let path = if first_run { "/settings" } else { "/" };
                            let url = format!("http://127.0.0.1:{}{}", port.trim(), path);
                            let h = handle.clone();
                            let _ = handle.run_on_main_thread(move || {
                                if let Some(w) = h.get_webview_window("main") {
                                    let _ = w.eval(&format!("window.location.href = {url:?};"));
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
        .run(|app, event| {
            if matches!(event, RunEvent::Exit) {
                if let Some(state) = app.try_state::<Sidecar>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        });
}
