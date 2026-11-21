"""Exercise Linux Tauri link dispatch and the actual GTK export dialog under Xvfb."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from smoke import check_scheduled_search, check_version


EXPORT_LINK = 'a[href="/api/config/export"][download]'
EXPORT_DIALOG = "^导出已保存的配置$"
PAPER_URL = "https://example.test/paper"
WEB_ELEMENT = "element-6066-11e4-a52e-4f735466cecf"


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def until(probe, message, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if result := probe():
                return result
        except (FileNotFoundError, URLError):
            pass
        time.sleep(0.1)
    raise AssertionError(message)


class WebKitSession:
    def __init__(self, opener, base):
        self.opener = opener
        self.base = base
        self.session_id = None

    def request(self, path, method="GET", payload=None, timeout=45):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(self.base + path, data=data, method=method,
                          headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=timeout) as response:
                return json.load(response)["value"]
        except HTTPError as error:
            raise RuntimeError(f"WebDriver {method} {path}: {error.read().decode('utf-8', 'replace')}") from error

    def command(self, path, payload=None):
        return self.request(f"/session/{self.session_id}{path}",
                            "POST" if payload is not None else "GET", payload)

    def ready(self, url, selector):
        return self.command("/execute/sync", {
            "script": "return location.href === arguments[0] && !!document.querySelector(arguments[1]);",
            "args": [url, selector],
        })

    def click(self, selector):
        element = self.command("/element", {"using": "css selector", "value": selector})
        return self.command(f"/element/{element[WEB_ELEMENT]}/click", {})

    def top(self):
        self.command("/frame", {"id": None})

    def panel(self, url, selector):
        self.top()
        tabs = self.command("/elements", {"using": "css selector", "value": "#panes iframe:not([hidden])"})
        if tabs:
            self.command("/frame", {"id": tabs[0]})
        return self.ready(url + ("?ui=1" if tabs else ""), selector)

    def tab_count(self):
        self.top()
        return len(self.command("/elements", {"using": "css selector", "value": "#tabs [role=tab]"}))

    def open_dashboard(self, settings):
        self.top()
        if self.tab_count():
            self.click('#tabs > .tab:first-child [role=tab]')
        else:
            assert self.ready(settings, EXPORT_LINK)
            self.click("header a[href='/']")


@contextmanager
def desktop_session(executable, root, home, url_log, service_port):
    shim = root / "bin" / "xdg-open"
    shim.parent.mkdir()
    shim.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$NEURODAILY_UI_URLS"\n', encoding="utf-8")
    shim.chmod(0o755)
    xdg_config = root / "xdg-config"
    xdg_config.mkdir()
    downloads = root / "downloads"
    downloads.mkdir()
    (xdg_config / "user-dirs.dirs").write_text(f'XDG_DOWNLOAD_DIR="{downloads}"\n', encoding="utf-8")
    env = {**os.environ, "PATH": f"{shim.parent}{os.pathsep}{os.environ['PATH']}",
           "NEURODAILY_HOME": str(home), "NEURODAILY_PORT": str(service_port),
           "NEURODAILY_UI_URLS": str(url_log), "NO_PROXY": "127.0.0.1,localhost",
           "XDG_CONFIG_HOME": str(xdg_config), "XDG_DATA_HOME": str(root / "xdg-data"),
           "XDG_CACHE_HOME": str(root / "xdg-cache"), "TAURI_WEBVIEW_AUTOMATION": "true",
           "GDK_BACKEND": "x11", "WEBKIT_DISABLE_DMABUF_RENDERER": "1"}
    env.pop("NEURODAILY_SIDECAR", None)
    env.pop("NEURODAILY_DEMO", None)
    config = home / "config"
    config.mkdir(parents=True)
    for name in ("email", "ai_summary", "webhooks"):
        (config / f"{name}.json").write_text('{"enabled":false}', encoding="utf-8")

    driver_port = free_port()
    while driver_port == service_port:
        driver_port = free_port()
    log = root / "webdriver.log"
    with log.open("wb") as output:
        process = subprocess.Popen(["WebKitWebDriver", f"--port={driver_port}", "--host=127.0.0.1"],
                                   env=env, cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    opener = build_opener(ProxyHandler({}))
    driver = WebKitSession(opener, f"http://127.0.0.1:{driver_port}")
    try:
        until(lambda: driver.request("/status", timeout=2), "Native WebKitWebDriver did not start")
        session = driver.request("/session", "POST", {"capabilities": {"alwaysMatch": {
            "webkitgtk:browserOptions": {"binary": str(executable)},
        }}})
        driver.session_id = session["sessionId"]
        yield opener, driver
    except BaseException:
        print(log.read_text(encoding="utf-8", errors="replace"), file=sys.stderr, end="")
        raise
    finally:
        if driver.session_id:
            with suppress(OSError, RuntimeError):
                driver.request(f"/session/{driver.session_id}", "DELETE", timeout=3)
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def xdo(*args):
    subprocess.run(["xdotool", *args], check=True, timeout=8)


def picker_window():
    result = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", EXPORT_DIALOG],
                            capture_output=True, text=True, timeout=5)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    windows = result.stdout.splitlines()
    return windows[0] if windows else None


def choose_export(driver, target, *, cancel=False):
    # A native modal can hold the WebDriver click open until the dialog returns.
    with ThreadPoolExecutor(max_workers=1) as actions:
        click = actions.submit(driver.click, EXPORT_LINK)
        try:
            window = until(picker_window, "The native GTK export dialog did not open")
            xdo("windowfocus", "--sync", window)
            xdo("key", "--clearmodifiers", "ctrl+l", "ctrl+a")
            xdo("type", "--clearmodifiers", "--", str(target))
            xdo("key", "--clearmodifiers", "Escape" if cancel else "Return")
            until(lambda: not picker_window(), "The native GTK export dialog did not close")
        finally:
            click.result()


def smoke(executable, version):
    with tempfile.TemporaryDirectory(prefix="neurodaily-native-ui-") as directory:
        root = Path(directory)
        home = root / "neurodaily"
        url_log = root / "opened-urls.txt"
        export_folder = root / "selected export directory"
        export_folder.mkdir()
        service_port = free_port()
        base = f"http://127.0.0.1:{service_port}"
        settings = base + "/settings"
        with desktop_session(executable, root, home, url_log, service_port) as (opener, driver):
            until(lambda: driver.panel(settings, EXPORT_LINK), "The packaged settings page did not load", 45)
            check_version(opener, base, version)
            with opener.open(base + "/api/config/export", timeout=5) as response:
                expected = response.read()
            assert json.loads(expected)["format"] == "neurodaily.profile"
            cancelled = export_folder / "cancelled.json"
            choose_export(driver, cancelled, cancel=True)
            assert not cancelled.exists(), "Cancelling created the selected file"
            assert not list((root / "downloads").iterdir()), "Cancelling created an automatic download"
            saved = export_folder / "shared profile.json"
            choose_export(driver, saved)
            until(saved.is_file, "The profile was not written to the selected path")
            assert saved.read_bytes() == expected, "The selected file differs from the portable profile"
            assert not cancelled.exists(), "The cancelled profile was written later"

            check_scheduled_search(opener, base, home)
            paper_link = f'main details summary a[href="{PAPER_URL}"]'
            if driver.tab_count():
                # A scheduled run opens its own report without closing settings.
                until(lambda: driver.tab_count() == 5, "The scheduled report did not open as a tab")
                assert not driver.command("/elements", {"using": "css selector", "value": ".toolbar"})
                driver.click('#tabs > .tab:nth-child(4) [role=tab]')
                until(lambda: driver.panel(settings, EXPORT_LINK), "The original settings tab was lost")
                driver.click("header a[href='/']")
                assert driver.tab_count() == 5, "Dashboard navigation duplicated or replaced a tab"
                until(lambda: driver.command("/execute/sync", {
                    "script": "return /^\\d{4}-\\d{2}-\\d{2}/.test(document.querySelector('#tabs [role=tab]').textContent)",
                    "args": [],
                }), "The latest report tab did not show its date")
            else:
                driver.open_dashboard(settings)
            dashboard = base + "/"
            until(lambda: driver.panel(dashboard, paper_link), "The saved report did not load in the desktop app")
            driver.click(paper_link)
            until(url_log.is_file, "The report link did not invoke the system's xdg-open dispatcher")
            assert url_log.read_text(encoding="utf-8").splitlines() == [PAPER_URL]
            assert driver.panel(dashboard, paper_link), "The external link navigated away from the app"
        print("Native Linux UI: picker cancelled and saved to the selected path; report link dispatched through xdg-open")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("version")
    args = parser.parse_args()
    if sys.platform != "linux" or not os.environ.get("DISPLAY"):
        parser.error("Run on Linux in an X11 session or under xvfb-run")
    if not args.executable.is_file():
        parser.error("Pass the installed Tauri executable")
    smoke(args.executable.resolve(), args.version)
