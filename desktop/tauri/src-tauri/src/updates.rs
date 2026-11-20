use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use keyring::Entry;
use reqwest::header::{HeaderValue, ACCEPT, AUTHORIZATION};
use reqwest::{Client, StatusCode};
use semver::Version;
use serde::Deserialize;
use tauri::menu::{Menu, MenuItem, Submenu};
use tauri::utils::{config::BundleType, platform::bundle_type};
use tauri::{
    webview::NewWindowResponse, AppHandle, Manager, Url, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder,
};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
use tauri_plugin_updater::{Update, UpdaterExt};

use super::{link_destination, open_in_browser, stop_sidecar, LinkDestination, QuitState};

const API: &str = "https://api.github.com/repos/Koalalive/neurodaily/releases";
const RELEASES: &str = "https://github.com/Koalalive/neurodaily/releases/latest";
const TOKEN_SETTINGS: &str = "https://github.com/settings/personal-access-tokens/new?name=NeuroDaily%20Updates&target_name=Koalalive&contents=read";
const AUTH_WINDOW: &str = "update-auth";
const CHECK_INTERVAL: Duration = Duration::from_secs(12 * 60 * 60);
const KEYRING_ERROR: &str = "无法访问系统凭据库，请先解锁后重试。";
const ACCESS_ERROR: &str =
    "GitHub 令牌无法读取该私有仓库。请检查有效期、仓库范围和 Contents 读取权限。";

#[derive(Default)]
pub struct UpdateCheck(AtomicBool);

struct ActiveCheck<'a>(&'a AtomicBool);

impl Drop for ActiveCheck<'_> {
    fn drop(&mut self) {
        self.0.store(false, Ordering::Release);
    }
}

#[derive(Deserialize)]
struct Release {
    tag_name: String,
    assets: Vec<Asset>,
}

#[derive(Deserialize)]
struct Asset {
    id: u64,
    name: String,
}

enum Available {
    Current,
    Manual(Version),
    Signed(Update),
}

fn credential() -> keyring::Result<Entry> {
    Entry::new("com.neurodaily.app", "github-update-token")
}

fn token_format_valid(token: &str) -> bool {
    token.strip_prefix("github_pat_").is_some_and(|value| {
        (20..=500).contains(&value.len())
            && value
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'_')
    })
}

fn request_client() -> Result<Client, String> {
    Client::builder()
        .https_only(true)
        .user_agent("NeuroDaily-Updater")
        .timeout(Duration::from_secs(20))
        .build()
        .map_err(|_| "无法初始化更新网络连接。".into())
}

fn github_status(status: StatusCode) -> Result<(), String> {
    match status {
        StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN | StatusCode::NOT_FOUND => {
            Err(ACCESS_ERROR.into())
        }
        status if status.is_success() => Ok(()),
        status => Err(format!("GitHub 更新服务返回 HTTP {status}。")),
    }
}

async fn latest_release(client: &Client, token: &str) -> Result<Release, String> {
    let response = client
        .get(format!("{API}/latest"))
        .bearer_auth(token)
        .header(ACCEPT, "application/vnd.github+json")
        .send()
        .await
        .map_err(|_| "暂时无法连接 GitHub 更新服务。".to_string())?;
    github_status(response.status())?;
    response
        .json()
        .await
        .map_err(|_| "GitHub 发布信息格式无效。".into())
}

fn package_name(bundle: BundleType, arch: &str, version: &Version) -> Option<String> {
    let suffix = match (bundle, arch) {
        (BundleType::App, "aarch64") => "aarch64.app.tar.gz",
        (BundleType::App, "x86_64") => "x64.app.tar.gz",
        (BundleType::Nsis, "x86_64") => "x64-setup.exe",
        (BundleType::Msi, "x86_64") => "x64_en-US.msi",
        (BundleType::AppImage, "x86_64") => "amd64.AppImage",
        (BundleType::Deb, "x86_64") => "amd64.deb",
        _ => return None,
    };
    Some(format!("NeuroDaily_{version}_{suffix}"))
}

fn signed_assets(release: &Release, name: &str) -> Option<(u64, u64)> {
    let signature_name = format!("{name}.sig");
    let package = release.assets.iter().find(|asset| asset.name == name)?;
    let signature = release
        .assets
        .iter()
        .find(|asset| asset.name == signature_name)?;
    Some((package.id, signature.id))
}

async fn available_update(app: &AppHandle, token: &str) -> Result<Available, String> {
    let client = request_client()?;
    let release = latest_release(&client, token).await?;
    let version = Version::parse(release.tag_name.trim_start_matches('v'))
        .map_err(|_| "GitHub 发布版本号无效。".to_string())?;
    if version <= app.package_info().version {
        return Ok(Available::Current);
    }
    let Some(name) =
        bundle_type().and_then(|bundle| package_name(bundle, std::env::consts::ARCH, &version))
    else {
        return Ok(Available::Manual(version));
    };
    let (package_id, signature_id) = signed_assets(&release, &name)
        .ok_or_else(|| "该版本缺少当前安装方式的更新包或签名。".to_string())?;
    let response = client
        .get(format!("{API}/assets/{signature_id}"))
        .bearer_auth(token)
        .header(ACCEPT, "application/octet-stream")
        .send()
        .await
        .map_err(|_| "无法下载更新签名。".to_string())?;
    github_status(response.status())?;
    let signature = response
        .text()
        .await
        .map_err(|_| "无法读取更新签名。".to_string())?;

    let mut authorization = HeaderValue::from_str(&format!("Bearer {token}"))
        .map_err(|_| "更新授权格式无效。".to_string())?;
    authorization.set_sensitive(true);
    let handle = app.clone();
    let updater = app
        .updater_builder()
        .endpoints(vec![Url::parse(API).expect("valid GitHub API URL")])
        .map_err(|_| "更新服务地址无效。".to_string())?
        .configure_client(|client| client.https_only(true))
        .header(AUTHORIZATION, authorization)
        .and_then(|builder| builder.header(ACCEPT, "application/octet-stream"))
        .map_err(|_| "无法设置更新下载权限。".to_string())?
        .on_before_exit(move || stop_sidecar(&handle))
        .build()
        .map_err(|_| "无法启动更新器。".to_string())?;
    // Explicit GitHub asset IDs keep the credential on the fixed private repository API.
    let update = updater
        .restore_update(serde_json::json!({
            "version": version.to_string(),
            "url": format!("{API}/assets/{package_id}"),
            "signature": signature.trim(),
        }))
        .map_err(|_| "更新包信息无效。".to_string())?;
    Ok(update.map(Available::Signed).unwrap_or(Available::Current))
}

async fn ask(app: &AppHandle, message: String, yes: &str) -> bool {
    let (sender, receiver) = tokio::sync::oneshot::channel();
    app.dialog()
        .message(message)
        .title("NeuroDaily 软件更新")
        .buttons(MessageDialogButtons::OkCancelCustom(
            yes.into(),
            "稍后".into(),
        ))
        .show(move |confirmed| {
            let _ = sender.send(confirmed);
        });
    receiver.await.unwrap_or(false)
}

fn notify(app: &AppHandle, message: impl Into<String>, kind: MessageDialogKind) {
    app.dialog()
        .message(message)
        .title("NeuroDaily 软件更新")
        .kind(kind)
        .show(|_| {});
}

async fn download_and_apply(app: &AppHandle, update: Update) -> Result<(), String> {
    if !ask(
        app,
        format!("发现 NeuroDaily {}。现在下载更新吗？", update.version),
        "下载更新",
    )
    .await
    {
        return Ok(());
    }
    let bytes = update
        .download(|_, _| {}, || {})
        .await
        .map_err(|_| "更新下载或签名验证失败，当前版本仍可继续使用。".to_string())?;
    if !ask(
        app,
        "下载和签名验证已完成。安装会重启 NeuroDaily，请先结束正在进行的检索和推送。".into(),
        "安装并重启",
    )
    .await
    {
        return Ok(());
    }
    tauri::async_runtime::spawn_blocking(move || update.install(bytes))
        .await
        .map_err(|_| "更新安装任务结束异常。".to_string())?
        .map_err(|_| {
            "更新安装失败。请重新打开 NeuroDaily 恢复推送，或从 GitHub Releases 下载新版。"
                .to_string()
        })?;
    app.state::<QuitState>()
        .confirmed
        .store(true, Ordering::Relaxed);
    stop_sidecar(app);
    app.restart();
}

async fn check_once(app: AppHandle, manual: bool) {
    let state = app.state::<UpdateCheck>();
    if state.0.swap(true, Ordering::Acquire) {
        if manual {
            notify(&app, "更新检查或下载正在进行。", MessageDialogKind::Info);
        }
        return;
    }
    let _active = ActiveCheck(&state.0);
    let token = match tauri::async_runtime::spawn_blocking(|| credential()?.get_password()).await {
        Ok(Ok(token)) => token,
        Ok(Err(keyring::Error::NoEntry)) => {
            if manual {
                show_authorization(&app);
            }
            return;
        }
        _ => {
            if manual {
                notify(&app, KEYRING_ERROR, MessageDialogKind::Error);
            }
            return;
        }
    };
    let result = available_update(&app, &token).await;
    match result {
        Ok(Available::Signed(update)) => {
            if let Err(error) = download_and_apply(&app, update).await {
                notify(&app, error, MessageDialogKind::Error);
            }
        }
        Ok(Available::Manual(version)) => {
            if ask(
                &app,
                format!("发现 NeuroDaily {version}。当前安装方式需要从 GitHub 下载新版安装包。"),
                "打开下载页",
            )
            .await
            {
                open_in_browser(
                    &app,
                    &Url::parse(RELEASES).expect("valid GitHub release URL"),
                );
            }
        }
        Ok(Available::Current) if manual => {
            notify(&app, "当前已是最新版本。", MessageDialogKind::Info);
        }
        Err(error) if manual => notify(&app, error, MessageDialogKind::Error),
        _ => {}
    }
}

fn show_authorization(app: &AppHandle) {
    let result = if let Some(window) = app.get_webview_window(AUTH_WINDOW) {
        window.set_focus()
    } else {
        let handle = app.clone();
        WebviewWindowBuilder::new(app, AUTH_WINDOW, WebviewUrl::App("update-auth.html".into()))
            .title("NeuroDaily 更新授权")
            .inner_size(540.0, 380.0)
            .min_inner_size(460.0, 340.0)
            .on_navigation(move |url| {
                if url.as_str() == TOKEN_SETTINGS {
                    open_in_browser(&handle, url);
                }
                link_destination(url, 0) == LinkDestination::App
                    && url.path() == "/update-auth.html"
            })
            .on_new_window(|_, _| NewWindowResponse::Deny)
            .build()
            .map(|_| ())
    };
    if result.is_err() {
        notify(app, "无法打开更新授权窗口。", MessageDialogKind::Error);
    }
}

#[tauri::command]
pub async fn set_update_token(window: WebviewWindow, token: Option<String>) -> Result<(), String> {
    if window.label() != AUTH_WINDOW {
        return Err("更新授权只能在授权窗口中设置。".into());
    }
    if let Some(token) = token.as_ref() {
        if !token_format_valid(token) {
            return Err("请输入 GitHub 细粒度只读令牌。".into());
        }
        latest_release(&request_client()?, token).await?;
    }
    let saved = token.is_some();
    tauri::async_runtime::spawn_blocking(move || {
        let entry = credential()?;
        match token {
            Some(token) => entry.set_password(&token),
            None => match entry.delete_credential() {
                Err(keyring::Error::NoEntry) => Ok(()),
                result => result,
            },
        }
    })
    .await
    .map_err(|_| KEYRING_ERROR.to_string())?
    .map_err(|_| KEYRING_ERROR.to_string())?;
    if saved {
        tauri::async_runtime::spawn(check_once(window.app_handle().clone(), false));
    }
    Ok(())
}

pub fn start(app: &AppHandle) -> tauri::Result<()> {
    let check = MenuItem::with_id(app, "check-update", "检查更新…", true, None::<&str>)?;
    let authorize = MenuItem::with_id(app, "update-auth", "更新授权…", true, None::<&str>)?;
    let updates = Submenu::with_items(app, "更新", true, &[&check, &authorize])?;
    let menu = Menu::default(app)?;
    menu.append(&updates)?;
    app.set_menu(menu)?;
    app.on_menu_event(|app, event| match event.id().as_ref() {
        "check-update" => {
            tauri::async_runtime::spawn(check_once(app.clone(), true));
        }
        "update-auth" => {
            let handle = app.clone();
            tauri::async_runtime::spawn(async move { show_authorization(&handle) });
        }
        _ => {}
    });
    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        loop {
            check_once(handle.clone(), false).await;
            tokio::time::sleep(CHECK_INTERVAL).await;
        }
    });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn uses_the_installed_package_format_and_architecture() {
        let version = Version::new(1, 0, 2);
        for (bundle, arch, name) in [
            (
                BundleType::App,
                "aarch64",
                "NeuroDaily_1.0.2_aarch64.app.tar.gz",
            ),
            (BundleType::App, "x86_64", "NeuroDaily_1.0.2_x64.app.tar.gz"),
            (BundleType::Nsis, "x86_64", "NeuroDaily_1.0.2_x64-setup.exe"),
            (BundleType::Msi, "x86_64", "NeuroDaily_1.0.2_x64_en-US.msi"),
            (
                BundleType::AppImage,
                "x86_64",
                "NeuroDaily_1.0.2_amd64.AppImage",
            ),
            (BundleType::Deb, "x86_64", "NeuroDaily_1.0.2_amd64.deb"),
        ] {
            assert_eq!(package_name(bundle, arch, &version).as_deref(), Some(name));
        }
        assert_eq!(package_name(BundleType::App, "arm", &version), None);
    }

    #[test]
    fn requires_the_signature_for_the_exact_package() {
        let mut release = Release {
            tag_name: "v1.0.2".into(),
            assets: vec![
                Asset {
                    id: 1,
                    name: "test.exe".into(),
                },
                Asset {
                    id: 2,
                    name: "test.msi.sig".into(),
                },
            ],
        };
        assert_eq!(signed_assets(&release, "test.exe"), None);
        release.assets.push(Asset {
            id: 3,
            name: "test.exe.sig".into(),
        });
        assert_eq!(signed_assets(&release, "test.exe"), Some((1, 3)));
    }
}
