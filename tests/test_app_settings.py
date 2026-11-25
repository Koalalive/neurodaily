import unittest
from unittest.mock import patch

from neurodaily import ai_summary, app_settings, mailer


class AppSettingsTests(unittest.TestCase):
    def test_export_excludes_secrets_and_contains_per_recipient_email(self):
        data = app_settings.export_settings()
        self.assertEqual(data["format"], "neurodaily.app-settings")
        email = data["settings"]["email"]
        self.assertNotIn("password", email)
        self.assertNotIn("api_key", data["settings"]["ai"])
        self.assertIn("recipients", email)
        self.assertNotIn("disciplines", data["settings"])
        self.assertNotIn("search", data["settings"])

    def test_import_requires_correct_wrapper(self):
        with self.assertRaises(ValueError):
            app_settings.import_settings({"format": "wrong", "version": 1, "settings": {}})

    def test_import_rejects_server_changes_before_writing_any_settings(self):
        for settings, message in (
            ({"ai": {"base_url": "https://other.example.test/v1"}}, "API"),
            ({"email": {"smtp_host": "smtp.other.example.test"}}, "SMTP"),
            ({"webhooks": {"feishu": "https://127.0.0.1/value"}}, "Webhook"),
        ):
            with self.subTest(settings=settings), \
                 patch.object(ai_summary, "load_cfg", return_value={**ai_summary.DEFAULT_CFG,
                                                                    "api_key": "saved-key"}), \
                 patch.object(mailer, "load_cfg", return_value={**mailer.DEFAULT_CFG,
                                                                 "password": "saved-password"}), \
                 patch.object(app_settings, "Config") as config, patch.object(app_settings, "_write") as write:
                document = {"format": app_settings.FORMAT, "version": 1,
                            "settings": {"output": {"dir": "elsewhere"}, **settings}}
                with self.assertRaisesRegex(ValueError, message):
                    app_settings.import_settings(document)
                config.load.assert_not_called()
                write.assert_not_called()

    def test_import_merges_only_whitelisted_sections(self):
        current = {"settings": {"format": "x"}}
        with patch.object(app_settings, "Config") as config, \
             patch.object(app_settings, "mailer") as mailer, \
             patch.object(app_settings, "webhooks") as hooks, \
             patch.object(app_settings, "ai_summary") as ai:
            config.load.return_value.profile = "fixture"
            config.load.return_value.output = {"dir": "/old"}
            config.load.return_value.scheduled = {}
            mailer.load_cfg.return_value = {"enabled": True, "to": []}
            hooks.load_cfg.return_value = {}
            ai.load_cfg.return_value = {"enabled": True}
            with patch.object(app_settings, "_write"):
                app_settings.import_settings({
                    "format": "neurodaily.app-settings", "version": 1,
                    "settings": {"output": {"dir": "/new"}, "unknown": {"x": 1},
                                 "email": {"enabled": False}},
                }, "/tmp/config.json")
            self.assertEqual(config.load.return_value.output["dir"], "/new")
            self.assertNotIn("x", config.load.return_value.output)


if __name__ == "__main__":
    unittest.main()
