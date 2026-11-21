"""Check frozen sidecar startup, scheduled retrieval and shutdown."""

from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import time
from urllib.request import ProxyHandler, Request, build_opener


class Feed(BaseHTTPRequestHandler):
    def do_GET(self):
        feed = b'''<rss version="2.0"><channel><title>Scheduler test feed</title>
        <link>https://example.test/</link><description>Offline fixture</description>
        <item><title>Scheduled smoke result</title><link>https://example.test/paper</link>
        <description>Scheduled smoke abstract</description></item></channel></rss>'''
        self.send_response(200)
        self.send_header("Content-Type", "application/rss+xml")
        self.send_header("Content-Length", str(len(feed)))
        self.end_headers()
        self.wfile.write(feed)


def check_scheduled_search(opener, base_url, home):
    def fetch_json(path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(base_url + path, data=data, headers={"Content-Type": "application/json"})
        with opener.open(request, timeout=5) as response:
            return json.load(response)

    status = fetch_json("/api/launchd/status")
    assert status["backend"] == "desktop" and status["state"] == "off", status
    cfg = fetch_json("/api/config")
    with ThreadingHTTPServer(("127.0.0.1", 0), Feed) as feed:
        Thread(target=feed.serve_forever, daemon=True).start()
        try:
            cfg["sources"] = {name: {**opts, "enabled": False} for name, opts in cfg["sources"].items()}
            cfg["sources"]["smoke"] = {"type": "rss", "kind": "paper", "enabled": True,
                                       "url": f"http://127.0.0.1:{feed.server_port}/feed"}
            cfg.update(journals=[], policy_feeds=[], search={"query": 'TI="Scheduled smoke result"'})
            now = datetime.now()
            cfg["scheduled"].update(enabled=True, hour=now.hour, minute=now.minute,
                                    on_this_day={"enabled": False})
            assert fetch_json("/api/config", cfg)["ok"]
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                status = fetch_json("/api/launchd/status")
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
        finally:
            feed.shutdown()


def smoke(executable: Path) -> None:
    with tempfile.TemporaryDirectory() as workdir:
        home = Path(workdir) / "home"
        config_dir = home / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "ai_summary.json").write_text('{"enabled":false}', encoding="utf-8")
        (config_dir / "email.json").write_text('{"enabled":false}', encoding="utf-8")
        (config_dir / "webhooks.json").write_text('{"feishu":"","wecom":""}', encoding="utf-8")
        log = Path(workdir) / "sidecar.log"
        env = {**os.environ, "NEURODAILY_HOME": str(home), "NEURODAILY_PORT": "0",
               "NEURODAILY_MANAGED": "1", "NO_PROXY": "127.0.0.1,localhost"}
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with log.open("wb") as output:
            process = subprocess.Popen([str(executable.resolve())], cwd=workdir,
                                       env=env, stdin=subprocess.PIPE, stdout=output,
                                       stderr=subprocess.STDOUT, creationflags=flags)
        try:
            deadline = time.monotonic() + 90
            while process.poll() is None and time.monotonic() < deadline:
                lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
                port = next((line.partition("=")[2] for line in lines
                             if line.startswith("NEURODAILY_PORT=")), None)
                if port:
                    assert "NEURODAILY_FIRST_RUN=1" in lines
                    if os.name == "nt":
                        assert "NEURODAILY_CONSOLE=0" in lines, lines
                    assert (home / "config" / "config.json").is_file()
                    opener = build_opener(ProxyHandler({}))
                    for route in ("/settings", "/api/status", "/run"):
                        with opener.open(f"http://127.0.0.1:{port}{route}", timeout=5) as response:
                            assert response.status == 200, route
                    with opener.open(f"http://127.0.0.1:{port}/api/config/presets", timeout=5) as response:
                        profiles = {preset["config"]["profile"] for preset in json.load(response)}
                        assert {"neuro", "oncology"} <= profiles, profiles
                    check_scheduled_search(opener, f"http://127.0.0.1:{port}", home)
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError(log.read_text(encoding="utf-8", errors="replace"))
        finally:
            process.stdin.close()
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
            assert process.returncode == 0, log.read_text(encoding="utf-8", errors="replace")
        print("Frozen sidecar started, ran a scheduled search, wrote a report and stopped on parent pipe closure")


if __name__ == "__main__":
    smoke(Path(sys.argv[1]))
