"""Daily report comparisons use formal runs, provenance and explicit notices."""

from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase, mock

from fastapi.testclient import TestClient

from neurodaily import history
from neurodaily.config import DEFAULT_CONFIG, DEFAULT_DIRS
from neurodaily.digest import DigestResult, save_report, snapshot
from neurodaily.models import Item
from neurodaily.webapp import create_app


def paper(title, doi, source="pubmed", **extra):
    return Item(title, doi=doi, source=source, url=f"https://doi.org/{doi}", extra=extra)


def source(name, status="ok", coverage="full"):
    return {"source": name, "status": status, "coverage": coverage,
            "count": 1, "ok": status == "ok", "ms": 10}


class ReportDeltaTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        patched = mock.patch.dict(DEFAULT_DIRS, {"output": directory.name, "config": directory.name})
        patched.start()
        self.addCleanup(patched.stop)
        self.config = DEFAULT_CONFIG()
        self.config.output["dir"] = directory.name
        self.config_path = self.config.save(str(self.folder / "config.json"))

    def _report(self, name, day, items, sources, *, mode="daily", config=None, status="completed"):
        cfg = config or self.config
        when = f"2026-11-{day}T08:00:00"
        sections = {"papers": [row for row in items if row.kind == "paper"],
                    "trials_conferences": [row for row in items if row.kind == "trial"]}
        result = DigestResult(items=items, sections=sections, health=sources, generated_at=when,
                              config=cfg, config_profile=cfg.profile, search_window={
                                  "mode": mode, "start": f"2026-11-{int(day)-1:02d} 00:00",
                                  "end": f"2026-11-{day} 08:00",
                              })
        result.history_id = history.record_run(history.compute_fingerprint(cfg, mode), cfg.profile,
                                               status, when, when, snapshot=snapshot(result, mode))
        path = self.folder / name
        save_report(result, str(path))
        return result, path

    def test_exact_profile_fingerprint_and_provider_coverage_guard_comparison(self):
        trial_before = Item("Registry study", kind="trial", source="trials",
                            url="https://clinicaltrials.gov/study/NCT00000001",
                            extra={"nct": "NCT00000001", "status": "RECRUITING",
                                   "trial_dates": {"last_update_posted": "2026-11-21"}})
        baseline, _ = self._report("first.html", "22", [
            paper("A paper with a new notice", "10.1000/a"),
            paper("A paper from an unavailable source", "10.1000/missing", source="openalex"),
            paper("Paper no longer found", "10.1000/not-found"), trial_before,
        ], [source("pubmed"), source("openalex"), source("trials")])
        other = DEFAULT_CONFIG()
        other.profile = "oncology"
        self._report("other-profile.html", "23", [paper("Another profile", "10.1000/other")],
                     [source("pubmed")], config=other)
        self._report("manual.html", "23", [paper("Manual result", "10.1000/manual")],
                     [source("pubmed")], mode="manual")
        trial_after = Item("Registry study", kind="trial", source="trials",
                           url=trial_before.url, extra={"nct": "NCT00000001", "status": "COMPLETED",
                                                        "trial_dates": {"last_update_posted": "2026-11-24"}})
        notices = [{"doi": "10.1000/notice", "kind": "retraction", "direction": "notice", "date": "2026-11-24"},
                   {"doi": "10.1000/correction", "kind": "correction", "direction": "notice", "date": "2026-11-24"}]
        latest, path = self._report("latest.html", "24", [
            paper("Added article", "10.1000/new"),
            paper("A paper with a new notice", "10.1000/a", publication_updates=notices),
            paper("Unverified aggregator match", "10.1000/indexed", source="openalex", is_retracted=True),
            trial_after,
        ], [source("pubmed"), source("openalex", "timeout", "partial"), source("trials")])
        self.assertEqual(latest.delta["baseline"]["id"], baseline.history_id)
        self.assertEqual([row["title"] for row in latest.delta["added_papers"]],
                         ["Added article", "Unverified aggregator match"])
        self.assertEqual([row["title"] for row in latest.delta["uncertain"]], ["A paper from an unavailable source"])
        self.assertEqual([row["title"] for row in latest.delta["not_seen"]], ["Paper no longer found"])
        change, = latest.delta["trial_changes"]
        self.assertEqual((change["before"], change["after"]), ("RECRUITING", "COMPLETED"))
        self.assertEqual([row["kind"] for row in latest.delta["retractions"]], ["retraction"])
        self.assertEqual([row["kind"] for row in latest.delta["publication_updates"]], ["correction"])
        self.assertIn("10.1000/notice", path.read_text(encoding="utf8"))

    def test_crossref_retraction_notice_points_to_the_notice_and_its_target_once(self):
        original = paper("Originally published", "10.1000/target", publication_updates=[
            {"doi": "10.1000/notice", "kind": "retraction", "direction": "notice"},
        ])
        notice = paper("Official retraction notice", "10.1000/notice", publication_updates=[
            {"doi": "10.1000/target", "kind": "retraction", "direction": "notice_for"},
        ])
        result, _ = self._report("notice.html", "24", [notice, original], [source("pubmed")])
        alert, = result.delta["retractions"]
        self.assertEqual(alert["notice_url"], "https://doi.org/10.1000/notice")
        self.assertEqual(alert["target_url"], "https://doi.org/10.1000/target")

    def test_feedback_uses_server_validated_identifiers_and_checks_report_profile(self):
        result, path = self._report("feedback.html", "24", [paper("Watched paper", "10.1000/watched")],
                                    [source("pubmed")])
        saved_html = path.read_text(encoding="utf8")
        self.assertIn("data-report-record=", saved_html)
        self.assertNotIn("/static/report/feedback.js", saved_html)
        self.assertIsNotNone(result.delta)
        from neurodaily.report_feedback import record_key

        key = record_key(history.get_run(result.history_id)["snapshot"]["records"][0])
        client = TestClient(create_app(self.config_path))
        route = f"/api/history/{result.history_id}/feedback"
        report = client.get(f"/history/{result.history_id}/report")
        self.assertEqual(report.status_code, 200)
        self.assertTrue('/static/report/feedback.js' in report.text)
        self.assertEqual(client.post(route, json={"record_key": key, "relevant": False},
                                     headers={"Origin": "https://elsewhere.test"}).status_code, 403)
        self.assertEqual(client.post(route, json={"record_key": key, "relevant": False},
                                     headers={"Origin": "http://testserver:8080"}).status_code, 403)
        self.assertEqual(client.post(route, json={"record_key": "0" * 64, "relevant": False}).status_code, 404)
        original_config = Path(self.config_path).read_bytes()
        self.assertEqual(client.post(route, json={"record_key": key, "relevant": False}).status_code, 200)
        self.assertEqual(client.get(route).json()["feedback"], {key: False})
        feedback = client.get("/api/optimization").json()["report_feedback"]
        self.assertEqual([(row["title"], row["relevant"]) for row in feedback], [("Watched paper", False)])
        self.assertEqual(Path(self.config_path).read_bytes(), original_config)
        self.config.profile = "oncology"
        self.config.save(self.config_path)
        self.assertEqual(client.get(route).status_code, 404)
