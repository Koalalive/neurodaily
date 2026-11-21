import asyncio
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch, sentinel

from fastapi.testclient import TestClient

from neurodaily import __version__
from neurodaily.cli import build_parser, main
from neurodaily.config import Config, DEFAULT_CONFIG, DEFAULT_DIRS


class WebCLITests(unittest.TestCase):
    def test_installed_version_flag(self):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as exited:
            main(["--version"])
        self.assertEqual(exited.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), f"neurodaily {__version__}")

    def test_port_defaults_validation_and_local_only(self):
        parser = build_parser()
        self.assertEqual(parser.parse_args(["web"]).port, 8031)
        self.assertEqual(parser.parse_args(["web", "--port", "65535"]).port, 65535)
        self.assertEqual(parser.parse_args(["serve", "--host", "0.0.0.0"]).host, "0.0.0.0")
        for arguments in (["--port", "0"], ["--port", "65536"], ["--port", "abc"], ["--host", "0.0.0.0"]):
            with self.subTest(arguments=arguments), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(["web", *arguments])

    def _launch_with_fake_server(self, config_path, *flags, listening=True):
        events = []
        captured = {}

        def bind(config):
            self.assertEqual(config.host, "127.0.0.1")
            self.assertEqual(config.port, 8031)
            self.assertFalse(config.proxy_headers)
            events.append("bound")
            return nullcontext(sentinel.listener)

        async def startup(server, sockets=None):
            self.assertEqual(sockets, [sentinel.listener])
            self.assertTrue(config_path.is_file())
            captured["app"] = server.config.app
            events.append("startup")
            server.started = listening

        def run(server, sockets=None):
            asyncio.run(server.startup(sockets=sockets))

        def open_browser(url):
            events.append(url)
            return True

        def immediate(*, target, name, daemon):
            return Mock(start=target)

        with (
            patch.object(Config, "default_path", return_value=str(config_path)),
            patch("uvicorn.Config.bind_socket", new=bind),
            patch("uvicorn.Server.startup", new=startup),
            patch("uvicorn.Server.run", new=run),
            patch("threading.Thread", side_effect=immediate),
            patch("webbrowser.open", side_effect=open_browser),
            redirect_stdout(StringIO()),
        ):
            status = main(["web", *flags])
        return status, captured["app"], events

    def test_first_run_disables_schedule_and_browser_opens_only_after_startup(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config" / "config.json"
            with patch.dict(DEFAULT_DIRS, {"output": str(Path(tmp) / "output")}):
                status, app, events = self._launch_with_fake_server(config_path)
                self.assertEqual(status, 0)
                self.assertEqual(app.state.base_url, "http://127.0.0.1:8031")
                self.assertFalse(Config.load(str(config_path)).scheduled["enabled"])
                self.assertEqual(events, ["bound", "startup", "http://127.0.0.1:8031/desktop"])
                status, _, events = self._launch_with_fake_server(config_path, listening=False)
                self.assertEqual(status, 1)
                self.assertEqual(events, ["bound", "startup"])

    def test_existing_config_stays_intact_and_browser_writes_are_local(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            existing = DEFAULT_CONFIG()
            existing.profile = "critical-care"
            existing.save(str(config_path))
            original = config_path.read_bytes()
            status, app, events = self._launch_with_fake_server(config_path, "--no-open")
            self.assertEqual((status, events), (0, ["bound", "startup"]))
            self.assertEqual(config_path.read_bytes(), original)
            client = TestClient(app, base_url="http://127.0.0.1:8031")
            url = "/api/ui/preferences"
            self.assertEqual(client.get(url, headers={"host": "outside.example"}).status_code, 400)
            self.assertEqual(client.post(url, json={"language": "en"},
                                         headers={"origin": "https://outside.example"}).status_code, 403)
            self.assertEqual(client.post(url, json={"language": "en"},
                                         headers={"origin": "http://127.0.0.1:8031"}).status_code, 200)
            self.assertEqual(client.post(url, json={"language": "ru"}).status_code, 200)
            self.assertEqual(config_path.read_bytes(), original)
