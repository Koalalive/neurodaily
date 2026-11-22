"""Check packaged desktop startup, scheduled retrieval and shutdown."""

import argparse
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from threading import Event, Thread
import time
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import HTTPError


class Feed(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.search_started.set()
        if not self.server.finish_search.wait(15):
            self.send_error(503)
            return
        feed = b'''<rss version="2.0"><channel><title>Scheduler test feed</title>
        <link>https://example.test/</link><description>Offline fixture</description>
        <item><title>Scheduled smoke result</title><link>https://example.test/paper</link>
        <description>Scheduled smoke abstract</description></item></channel></rss>'''
        self.send_response(200)
        self.send_header("Content-Type", "application/rss+xml")
        self.send_header("Content-Length", str(len(feed)))
        self.end_headers()
        self.wfile.write(feed)


def fetch_json(opener, base_url, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(base_url + path, data=data, headers={"Content-Type": "application/json"})
    with opener.open(request, timeout=5) as response:
        return json.load(response)


def check_version(opener, base_url, expected):
    version = fetch_json(opener, base_url, "/openapi.json")["info"]["version"]
    assert version == expected, f"Expected packaged version {expected}, got {version}"


def check_preserved_sources(previous, current):
    for name, options in previous.items():
        assert current.get(name) == options, f"The upgrade changed source {name}"
    for name in current.keys() - previous.keys():
        assert current[name].get("enabled") is False, f"The upgrade enabled new source {name}"


def check_scheduled_search(opener, base_url, home, *, new_profile=None):
    status = fetch_json(opener, base_url, "/api/launchd/status")
    assert status["backend"] == "desktop", status
    cfg = fetch_json(opener, base_url, "/api/config")
    if new_profile is None:
        assert status["state"] == "off", status
    else:
        assert cfg["profile"] != new_profile, cfg["profile"]
        cfg["profile"] = new_profile
    with ThreadingHTTPServer(("127.0.0.1", 0), Feed) as feed:
        feed.search_started = Event()
        feed.finish_search = Event()
        Thread(target=feed.serve_forever, daemon=True).start()
        try:
            cfg["sources"] = {name: {**opts, "enabled": False} for name, opts in cfg["sources"].items()}
            cfg["sources"]["smoke"] = {"type": "rss", "kind": "paper", "enabled": True,
                                       "url": f"http://127.0.0.1:{feed.server_port}/feed"}
            cfg.update(journals=[], policy_feeds=[], search={"query": 'TI="Scheduled smoke result"'})
            cfg.setdefault("output", {})["topic_map"] = False
            now = datetime.now()
            cfg["scheduled"].update(enabled=True, hour=now.hour, minute=now.minute,
                                    on_this_day={"enabled": False})
            assert fetch_json(opener, base_url, "/api/config", cfg)["ok"]
            assert feed.search_started.wait(15), "The configured schedule did not contact the feed"
            run = fetch_json(opener, base_url, "/api/search/status")["search"]
            assert run["status"] == "running" and run["scheduled_for"], run
            try:
                fetch_json(opener, base_url, "/api/run?force=1", {})
            except HTTPError as exc:
                assert exc.code == 409, exc.code
            else:
                raise AssertionError("A manual search started during the scheduled run")
            feed.finish_search.set()
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                status = fetch_json(opener, base_url, "/api/launchd/status")
                attempt = status["last_run"]
                if attempt:
                    assert attempt["status"] == "completed", attempt
                    break
                time.sleep(0.25)
            else:
                raise AssertionError(f"Scheduled search never completed: {status}")
            with opener.open(base_url + "/report/latest", timeout=5) as response:
                assert b"Scheduled smoke result" in response.read()
            assert list((home / "output").glob("*.html"))
            assert fetch_json(opener, base_url, "/api/search/status")["search"]["status"] == "completed"
        finally:
            feed.finish_search.set()
            feed.shutdown()


def check_settings(opener, base_url, home):
    assert (home / "config" / "config.json").is_file()
    for route in ("/settings", "/api/status", "/run", "/api/ai/settings"):
        with opener.open(base_url + route, timeout=5) as response:
            assert response.status == 200, route
    with opener.open(base_url + "/api/config/presets", timeout=5) as response:
        profiles = {preset["config"]["profile"] for preset in json.load(response)}
        assert {"neuro", "oncology"} <= profiles, profiles
    with opener.open(base_url + "/api/config/export", timeout=5) as response:
        assert response.headers["Content-Disposition"].startswith("attachment;")
        assert json.load(response)["format"] == "neurodaily.profile"


@contextmanager
def running_service(executable: Path, home: Path, *, desktop=False, use_windows_appdata=False):
    first_run = not (home / "config" / "config.json").exists()
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    if first_run:
        (config_dir / "ai_summary.json").write_text('{"enabled":false}', encoding="utf-8")
        (config_dir / "email.json").write_text('{"enabled":false}', encoding="utf-8")
        (config_dir / "webhooks.json").write_text('{"feishu":"","wecom":""}', encoding="utf-8")
    log = home / "sidecar.log"
    env = {**os.environ, "NEURODAILY_HOME": str(home), "NEURODAILY_PORT": "0",
           "NEURODAILY_MANAGED": "1", "NEURODAILY_ALLOW_PRIVATE_SOURCES": "1",
           "NO_PROXY": "127.0.0.1,localhost"}
    env.pop("NEURODAILY_SIDECAR", None)
    env.pop("NEURODAILY_DEMO", None)
    if use_windows_appdata:
        assert home.name == "NeuroDaily", home
        env.pop("NEURODAILY_HOME")
        env["APPDATA"] = str(home.parent)
    if desktop:
        # Capture a port independently of the GUI process's stdout on Windows.
        with socket.socket() as port_probe:
            port_probe.bind(("127.0.0.1", 0))
            env["NEURODAILY_PORT"] = str(port_probe.getsockname()[1])
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log.open("wb") as output:
        process = subprocess.Popen([str(executable.resolve())], cwd=home.parent,
                                   env=env, stdin=subprocess.PIPE, stdout=output,
                                   stderr=subprocess.STDOUT, creationflags=flags)
    try:
        opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 90
        while process.poll() is None and time.monotonic() < deadline:
            if desktop:
                port = env["NEURODAILY_PORT"]
                try:
                    with opener.open(f"http://127.0.0.1:{port}/api/search/status", timeout=1):
                        break
                except OSError:
                    time.sleep(0.25)
                    continue
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
            port = next((line.partition("=")[2] for line in lines
                         if line.startswith("NEURODAILY_PORT=")), None)
            if port:
                assert f"NEURODAILY_FIRST_RUN={int(first_run)}" in lines, lines
                if os.name == "nt":
                    assert "NEURODAILY_CONSOLE=0" in lines, lines
                break
            time.sleep(0.25)
        else:
            raise RuntimeError(f"{executable} did not open the local service:\n"
                               + log.read_text(encoding="utf-8", errors="replace"))
        yield opener, f"http://127.0.0.1:{port}"
    finally:
        process.stdin.close()
        if desktop and process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/pid", str(process.pid), "/t", "/f"],
                               stdout=subprocess.DEVNULL, check=False)
            else:
                process.kill()
            process.wait(timeout=5)
            raise
        if not desktop:
            assert process.returncode == 0, log.read_text(encoding="utf-8", errors="replace")
    if desktop:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
                    pass
            except OSError:
                break
            time.sleep(0.25)
        else:
            raise AssertionError("The desktop sidecar continued listening after its parent stopped")
        if os.name == "nt":
            # Port closure can precede the release of Windows process handles.
            deadline = time.monotonic() + 10
            stopped_log = log.with_suffix(".stopped.log")
            while True:
                try:
                    log.replace(stopped_log)
                except PermissionError as exc:
                    if exc.winerror not in (32, 33) or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.25)
                else:
                    stopped_log.replace(log)
                    break


def smoke(executable: Path, *, desktop=False, expected_version=None) -> None:
    with tempfile.TemporaryDirectory() as workdir:
        home = Path(workdir) / "home"
        with running_service(executable, home, desktop=desktop) as (opener, base_url):
            if expected_version:
                check_version(opener, base_url, expected_version)
            check_settings(opener, base_url, home)
            check_scheduled_search(opener, base_url, home)
        print("Packaged service ran a scheduled search, blocked a manual duplicate, wrote a report and stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--expect-version")
    args = parser.parse_args()
    smoke(args.executable, desktop=args.desktop, expected_version=args.expect_version)
