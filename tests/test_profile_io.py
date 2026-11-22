import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from neurodaily.config import Config, DEFAULT_CONFIG
from neurodaily.profile_exchange import FORMAT, VERSION, export_profile, import_profile

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return {
        "version": 2,
        "profile": "unit",
        "disciplines": [{
            "name": "Neuroscience",
            "arxiv_cats": ["q-bio.NC"],
            "mesh_terms": ["Neurosciences"],
            "bio_cats": ["neuroscience"],
            "keywords": ["brain"],
            "enabled": True,
        }],
        "global_keywords": ["brain"],
        "search": {"query": "brain", "sets": {}, "journal_mode": "any",
                   "journals": [], "sort": "default"},
        "sources": {
            "pubmed": {"enabled": True, "max_results": 10, "lookback_days": 2},
            "my_feed": {"type": "rss", "url": "https://example.org/feed.xml",
                        "kind": "funding", "enabled": True},
        },
        "journals": [{"name": "Nature", "url": "https://www.nature.com/",
                      "category": "general", "impact_factor": 50.5,
                      "jcr": "Q1", "cas": "1区"}],
        "windows": {"daily_paper_hours": 36},
        "output": {"dir": "/private/output"},
        "scheduled": {"enabled": True},
    }


class ProfileExchangeTests(unittest.TestCase):
    def test_export_is_single_portable_json(self):
        cfg = Config.from_dict(fixture())
        doc = export_profile(cfg)
        self.assertEqual(doc["format"], FORMAT)
        self.assertEqual(doc["version"], VERSION)
        self.assertEqual(doc["config"]["search"]["query"], "brain")
        self.assertNotIn("output", doc["config"])
        self.assertNotIn("scheduled", doc["config"])
        self.assertEqual(doc["config"]["journals"][0]["impact_factor"], 50.5)

    def test_import_preserves_search_and_source_type(self):
        cfg, _ = import_profile(export_profile(Config.from_dict(fixture())), DEFAULT_CONFIG())
        self.assertEqual(cfg.search["query"], "brain")
        self.assertEqual(cfg.sources["my_feed"]["type"], "rss")
        self.assertEqual(cfg.journals[0].cas, "1区")

    def test_url_secrets_are_removed(self):
        data = fixture()
        data["sources"]["my_feed"]["url"] = (
            "https://user:pass@example.org/feed.xml?token=abc&x=1&apikey=zzz"
        )
        cfg = Config.from_dict(data)
        out = export_profile(cfg)["config"]["sources"]["my_feed"]["url"]
        self.assertNotIn("user", out)
        self.assertNotIn("token", out)
        self.assertNotIn("apikey", out)
        self.assertIn("example.org", out)


class ProfileCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.env = {**os.environ, "NEURODAILY_HOME": str(self.home)}
        self.src = Path(self.tmp.name) / "config.json"
        self.src.write_text(json.dumps(fixture()), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "neurodaily", *args],
            cwd=ROOT, env=self.env, text=True, capture_output=True,
        )

    def test_export_import_validate_doctor_roundtrip(self):
        out = Path(self.tmp.name) / "unit.profile.json"
        r = self.run_cli("profile", "export", str(self.src), "-o", str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        wrapped = json.loads(out.read_text())
        self.assertEqual(wrapped["format"], FORMAT)

        r = self.run_cli("profile", "validate", str(out), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)["ok"])

        r = self.run_cli("profile", "import", str(out), "--name", "unit", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        target = self.home / "config" / "profiles" / "unit.json"
        self.assertTrue(target.exists())
        saved = json.loads(target.read_text())
        self.assertEqual(saved["search"]["query"], "brain")
        self.assertEqual(saved["sources"]["my_feed"]["type"], "rss")

        r = self.run_cli("profile", "doctor", "unit")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_doctor_flags_broken_custom_source(self):
        broken = fixture()
        broken["sources"]["broken"] = {"enabled": True}
        path = Path(self.tmp.name) / "broken.json"
        path.write_text(json.dumps(broken), encoding="utf-8")
        r = self.run_cli("profile", "doctor", str(path))
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken", r.stdout)

    def test_invalid_profile_rejected(self):
        path = Path(self.tmp.name) / "bad.json"
        path.write_text(json.dumps({"profile": "x", "disciplines": []}), encoding="utf-8")
        r = self.run_cli("profile", "validate", str(path))
        self.assertEqual(r.returncode, 1)
