import unittest
from unittest.mock import patch

from neurodaily import app_settings


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
