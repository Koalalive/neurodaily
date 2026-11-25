from contextlib import contextmanager
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.optimization import Optimizer, pareto
from neurodaily.optimization_api import router
from neurodaily.optimization_evidence import CAPTURE_VERSION
from neurodaily.optimization_store import LabelsChanged, Store
from neurodaily.sources import http as source_http


def result(recall, information, errors=1, cost=1):
    return {
        "eligible": True,
        "metrics": {"recall": recall, "information_gain": information, "false_positives": errors, "cost": cost},
        "baseline_metrics": {"recall": 0.5, "information_gain": 1, "false_positives": 1, "cost": 1},
    }


class SearchOptimizationTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory / "config.json"
        self.base = DEFAULT_CONFIG()
        self.base.save(str(self.path))
        self.store = Store(self.directory / "optimizer.db")
        self.optimizer = Optimizer(str(self.path), self.store)
        self.scope, _ = self.optimizer.current()

    @contextmanager
    def fake_trials(self):
        first = {"title": "broaden", "patch": {"search": {"query": "neuroscience"}}}
        second = {"title": "qualify", "patch": {"search": {"query": "neuroscience AND cortex"}}}

        def score(_snapshot, _base, candidate, **_kw):
            return result(1, 2) if "AND" in candidate.search["query"] else result(0.6, 2, errors=30)

        with patch("neurodaily.optimization.capture_evidence",
                   return_value={"version": CAPTURE_VERSION, "sources": [{"source": "pubmed", "status": "healthy"}],
                                 "window": {}, "captures": {}}), \
                patch("neurodaily.optimization.public_evidence", side_effect=lambda evidence: evidence), \
                patch("neurodaily.optimization._propose", side_effect=[[first], [second]]) as model, \
                patch("neurodaily.optimization.evaluate_candidate", side_effect=score), \
                patch("neurodaily.optimization.verify_candidate", return_value=result(1, 2)) as holdout, \
                patch("neurodaily.optimization.recent_history", return_value=[]):
            yield model, holdout

    @staticmethod
    def drain(optimizer, run_id):
        stop = Event()
        for _ in range(30):
            row = optimizer.store.get(optimizer.scope_for(optimizer.current()[1].profile), run_id)
            if row["status"] != "running":
                return
            optimizer._step(optimizer.current()[0], run_id, stop)
        raise AssertionError("Expected the optimisation loop to finish")

    def test_update_after_trials_and_review_before_apply(self):
        queued = self.optimizer.launch("Find cortex articles", rounds=2)
        run_id = queued["id"]
        self.store.update(self.scope, run_id, {"status": "running"})
        with self.fake_trials() as (model, holdout):
            self.drain(self.optimizer, run_id)
        review = self.store.get(self.scope, run_id)
        self.assertEqual(review["status"], "review")
        self.assertEqual(model.call_count, 2)
        holdout.assert_called_once()
        self.assertEqual([row["title"] for row in review["candidates"]], ["qualify"])
        self.assertEqual(self.path.read_bytes().decode("utf-8").count("neuroscience AND cortex"), 0)
        with self.assertRaises(LookupError):
            self.optimizer.command(run_id, "accept", "unverified")
        candidate = review["candidates"][0]["id"]
        self.optimizer.command(run_id, "accept", candidate)
        with patch("neurodaily.optimization_graph.invoke"):
            self.optimizer.tick(Event())
        self.assertEqual(self.optimizer.current()[1].search["query"], "neuroscience AND cortex")
        self.optimizer.command(run_id, "rollback")
        self.optimizer.tick(Event())
        self.assertEqual(self.optimizer.current()[1].version(), self.base.version())
        self.assertEqual(self.store.get(self.scope, run_id)["status"], "rolled_back")

    def test_config_compare_and_swap(self):
        self.base.global_keywords = ["changed externally"]
        self.base.save(str(self.path))
        self.assertRaises(ValueError, DEFAULT_CONFIG().save, str(self.path), expected_version="old")
        self.assertEqual(self.optimizer.current()[1].global_keywords, ["changed externally"])

    def test_proposal_context_excludes_other_conversations(self):
        first = self.optimizer.launch("Only for the first conversation")
        self.store.update(self.scope, first["id"], {"status": "completed"})
        conversation = self.store.conversation(self.scope, self.base.profile, new=True)
        second = self.optimizer.launch("Only for the second conversation", conversation_id=conversation)
        self.store.update(self.scope, second["id"], {"status": "running", "stage": "propose",
                                                   "snapshot": {"version": CAPTURE_VERSION, "sources": []}})
        with patch("neurodaily.optimization._propose", return_value=[]) as propose:
            self.optimizer._step(self.scope, second["id"], Event())
        self.assertEqual([row["text"] for row in propose.call_args.args[2]], ["Only for the second conversation"])

    def test_application_conflicts_with_revised_labels_at_accept_and_commit(self):
        self.store.label(self.scope, ["pmid:17"], True)
        for during_review in (True, False):
            with self.subTest(during_review=during_review):
                run = self.optimizer.launch("Find cortex articles", rounds=2)["id"]
                self.store.update(self.scope, run, {"status": "running"})
                with self.fake_trials():
                    self.drain(self.optimizer, run)
                identifier = self.store.get(self.scope, run)["candidates"][0]["id"]
                if during_review:
                    self.store.label(self.scope, ["pmid:17"], False)
                    with self.assertRaises(LabelsChanged):
                        self.optimizer.command(run, "accept", identifier)
                else:
                    self.optimizer.command(run, "accept", identifier)
                    self.store.label(self.scope, ["pmid:17"], False)
                    self.optimizer.tick(Event())
                self.assertEqual(self.optimizer.current()[1].version(), self.base.version())
                self.assertTrue(self.optimizer.state()["run"]["labels_changed"])
                self.assertEqual(self.store.get(self.scope, run)["status"], "review")
                self.optimizer.command(run, "reject")
                self.store.label(self.scope, ["pmid:17"], True)

    def test_trial_records_are_paginated_and_distinct_by_phase_and_draft(self):
        from fastapi import FastAPI

        run = self.optimizer.launch("Try cortex separately")
        self.store.update(self.scope, run["id"], {"trials": [{"id": "candidate-a", "title": "A",
                         "added": [{"ids": [f"pmid:{n}"]} for n in range(51)]}],
                         "verified": [{"id": "candidate-a", "title": "A", "lost": [{"ids": ["pmid:2"]}]}]})
        app = FastAPI()
        app.include_router(router(self.optimizer))
        client = TestClient(app)
        diagnostics = client.get("/api/optimization").json()["trial_diagnostics"]
        self.assertEqual([(row["phase"], row["added_count"], row["lost_count"]) for row in diagnostics],
                         [("development", 51, 0), ("holdout", 0, 1)])
        path = f'/api/optimization/runs/{run["id"]}/trials/candidate-a/records'
        page = client.get(path, params={"phase": "development", "direction": "added", "offset": 50, "limit": 1})
        self.assertEqual(page.json(), {"total": 51, "records": [{"ids": ["pmid:50"]}]})
        holdout = client.get(path, params={"phase": "holdout", "direction": "lost"})
        self.assertEqual(holdout.json(), {"total": 1, "records": [{"ids": ["pmid:2"]}]})

    def test_status_uses_projection_and_revision_tracks_visible_changes(self):
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router(self.optimizer))
        client = TestClient(app)
        run = self.optimizer.launch("A large evidence request")
        path = f'/api/optimization/status?conversation_id={run["conversation_id"]}'
        self.store.update(self.scope, run["id"], {"evidence": "x" * 100_000})
        with patch.object(self.store, "get", side_effect=AssertionError("Do not load evidence during polling")):
            first = client.get(path).json()
            self.assertEqual(first["run"]["stage"], "capture")
            self.assertNotIn("evidence", first["run"])
            self.assertEqual(client.get(path).json()["revision"], first["revision"])
        self.store.update(self.scope, run["id"], {"status": "running", "stage": "evaluate", "round": 2})
        second = client.get(path).json()
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertEqual(second["run"]["round"], 2)
        self.store.begin_budget(run["id"], "round:2", 3, 20)
        self.store.reserve_request(self.scope, run["id"], "round:2")
        third = client.get(path).json()
        self.assertEqual(third["revision"], second["revision"])
        self.assertEqual(third["budget_usage"][0]["requests"], 1)
        restored = self.optimizer.state(run["conversation_id"])
        self.assertEqual(restored["revision"], second["revision"])
        self.assertIn("evidence", restored)

    def test_request_limit_covers_redirects_retries_and_resumed_phase(self):
        run = self.optimizer.launch("Probe one source", online_requests=2)
        self.store.update(self.scope, run["id"], {"status": "running"})
        dispatched = []

        def response(request):
            dispatched.append(request.url.path)
            if request.url.path == "/start":
                return httpx.Response(302, headers={"location": "/article"})
            return httpx.Response(500)

        with httpx.Client(transport=httpx.MockTransport(response), follow_redirects=True,
                          event_hooks=source_http._source_get_events) as client:
            with patch.object(source_http, "_client", client), source_http.capture_requests() as diagnostics:
                _, use = self.optimizer._online(self.scope, run, "round:1", Event(), lambda: source_http.get(
                    "https://example.test/start", retries=2, backoff=0))
            restored = Optimizer(str(self.path), Store(self.store.path))
            with patch.object(source_http, "_client", client):
                restored._online(self.scope, run, "round:1", Event(), lambda: source_http.get(
                    "https://example.test/start", retries=0))
        self.assertEqual(dispatched, ["/start", "/article"])
        self.assertEqual(diagnostics.request_count, 2)
        self.assertEqual((use["requests"], use["reason"]), (2, "online_request_budget_exhausted"))

    def test_capture_worker_limits_parallel_http_and_keeps_incomplete_diagnostics(self):
        run = self.optimizer.launch("PubMed", rounds=1, max_sources=2, online_requests=3)
        self.store.update(self.scope, run["id"], {"status": "running"})
        sent = []

        def response(request):
            sent.append(str(request.url))
            return httpx.Response(200)

        def fetch(_config, name, start, end, *, broad=False):
            with source_http.capture_requests() as diagnostic:
                source_http.get("https://example.test/" + name, retries=0)
                return [], {**diagnostic.as_dict(0), "captured": 0}

        with httpx.Client(transport=httpx.MockTransport(response), event_hooks=source_http._source_get_events) as client:
            with patch.object(source_http, "_client", client), patch("neurodaily.optimization.recent_history", return_value=[]), \
                 patch("neurodaily.optimization_evidence._fetch", side_effect=fetch), \
                 patch("neurodaily.optimization._propose", side_effect=AssertionError("Partial capture cannot call model")):
                self.drain(self.optimizer, run["id"])
        completed = self.optimizer.state(run["conversation_id"])
        self.assertEqual(len(sent), 3)
        self.assertEqual(completed["run"]["status"], "completed")
        self.assertEqual(completed["run"]["blockers"], ["online_request_budget_exhausted"])
        self.assertTrue(completed["evidence"])

    def test_incomplete_holdout_cannot_promote_candidate_to_review(self):
        run = self.optimizer.launch("Probe two holdout records", rounds=2, online_requests=1)
        self.store.update(self.scope, run["id"], {"status": "running"})

        def verify(*args, **kwargs):
            for path in ("/one", "/two"):
                source_http.get("https://example.test" + path, retries=0)
            return result(1, 2)

        with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)),
                          event_hooks=source_http._source_get_events) as client:
            with self.fake_trials(), patch.object(source_http, "_client", client), \
                 patch("neurodaily.optimization.verify_candidate", side_effect=verify):
                self.drain(self.optimizer, run["id"])
        completed = self.optimizer.state(run["conversation_id"])
        self.assertEqual(completed["run"]["status"], "completed")
        self.assertEqual(completed["run"]["blockers"], ["online_request_budget_exhausted"])
        self.assertEqual(completed["budget_usage"][-1]["phase"], "holdout")
        self.assertEqual(completed["budget_usage"][-1]["requests"], 1)

    def test_time_limit_and_cancellation_stop_further_http(self):
        run = self.optimizer.launch("Probe time and then stop", online_seconds=1)
        self.store.update(self.scope, run["id"], {"status": "running"})
        for stop_early in (False, True):
            with self.subTest(stop_early=stop_early):
                sent, clock, stop = [], [100.0], Event()

                def response(request):
                    sent.append(request.extensions["timeout"])
                    if stop_early:
                        stop.set()
                    else:
                        clock[0] += 2
                    return httpx.Response(200)

                def fetch_pair():
                    for path in ("/first", "/second"):
                        source_http.get("https://example.test" + path, timeout=20, retries=0)

                with httpx.Client(transport=httpx.MockTransport(response), event_hooks=source_http._source_get_events) as client:
                    with patch.object(source_http, "_client", client), \
                         patch("neurodaily.optimization_store.time", side_effect=lambda: clock[0]):
                        _, use = self.optimizer._online(self.scope, run, f"phase-{stop_early}", stop, fetch_pair)
                self.assertEqual(len(sent), 1)
                self.assertLessEqual(sent[0]["read"], 1)
                self.assertEqual(use["reason"], None if stop_early else "online_time_budget_exhausted")

    def test_report_feedback_changes_label_and_prioritizes_sources_in_next_trial(self):
        self.store.record_feedback(self.scope, ["pmid:15"], False, "2026-11-11",
                                   report_id=20, record_key="article-token", title="Result", source="biorxiv",
                                   journal="", rules=["tag:test"])
        requested = self.optimizer.launch("Check the topic")
        self.assertIn("biorxiv", requested["focus_sources"])
        self.assertEqual(requested["report_feedback"][0]["rules"], ["tag:test"])
        self.assertEqual(requested["labels"], [{"ids": ["pmid:15"], "relevant": False, "date": "2026-11-11"}])
        self.assertEqual(self.store.report_feedback(self.scope, 20), {"article-token": False})
        self.assertEqual(self.store.report_feedback("other", 20), {})

    def test_conversation_scoping_controls_and_label_aliases(self):
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router(self.optimizer))
        client = TestClient(app)
        first = client.get("/api/optimization").json()["conversation_id"]
        state = client.post("/api/optimization/messages", json={"text": "Remember my profile"}).json()
        self.assertEqual(state["messages"][0]["text"], "Remember my profile")
        run = state["run"]["id"]
        self.assertEqual(client.post(f"/api/optimization/runs/{run}/cancel").json()["run"]["status"], "cancelled")
        self.assertEqual(client.post(f"/api/optimization/runs/{run}/resume").json()["run"]["status"], "queued")
        second = client.post("/api/optimization/conversations").json()["conversation_id"]
        self.assertNotEqual(first, second)
        self.assertEqual(client.get(f"/api/optimization?conversation_id={first}").json()["run"]["id"], run)
        client.post("/api/optimization/labels", json={"ids": ["doi:a", "pmid:1"], "relevant": True})
        client.post("/api/optimization/labels", json={"ids": ["pmid:1", "title:a"], "relevant": False})
        labels = self.store.labels(self.scope)
        self.assertEqual(labels, [{"ids": ["doi:a", "pmid:1", "title:a"], "relevant": False}])
        self.base.profile = "other"
        self.base.save(str(self.path))
        self.assertEqual(client.get(f"/api/optimization?conversation_id={first}").status_code, 404)
        self.assertEqual(client.post(f"/api/optimization/runs/{run}/resume").status_code, 404)
        self.assertFalse(self.store.labels(self.optimizer.current()[0]))
        client.post("/api/optimization/preferences", json={"enabled": False})
        self.assertEqual(client.post("/api/optimization/messages", json={"text": "Use AI"}).status_code, 409)

    def test_tradeoff_requires_permission_and_incomplete_trial_is_ineligible(self):
        strict = {"id": "strict", **result(0.75, 2)}
        trade = {"id": "trade", **result(1, 3, errors=2)}
        incomplete = {"id": "incomplete", **result(1, 8, errors=0), "eligible": False}
        self.assertEqual([row["id"] for row in pareto([strict, trade, incomplete], allow_tradeoffs=False)], ["strict"])
        self.assertEqual([row["id"] for row in pareto([strict, trade, incomplete], allow_tradeoffs=True)],
                         ["strict", "trade"])

    @unittest.skipUnless(importlib.util.find_spec("langgraph"), "LangGraph dependencies unavailable")
    def test_native_langgraph_checkpoint_interrupt_and_resume(self):
        from langgraph.checkpoint.sqlite import SqliteSaver

        run_id = self.optimizer.launch("Find cortex articles", rounds=2)["id"]
        original = self.optimizer._step

        def stop_after_capture(scope, identifier, stop):
            original(scope, identifier, stop)
            stop.set()

        with self.fake_trials() as (model, _):
            with patch.object(self.optimizer, "_step", side_effect=stop_after_capture):
                self.optimizer.tick(Event())
            self.assertEqual(self.store.get(self.scope, run_id)["stage"], "propose")
            Optimizer(str(self.path), Store(self.store.path)).tick(Event())
            state = self.store.get(self.scope, run_id)
            self.assertEqual(state["status"], "review")
            self.assertEqual(model.call_count, 2)

        graph_path = self.store.path.with_suffix(".checkpoints.db")
        configuration = {"configurable": {"thread_id": run_id}}
        with SqliteSaver.from_conn_string(str(graph_path)) as saver:
            self.assertIsNotNone(saver.get_tuple(configuration))
        self.optimizer.command(run_id, "accept", state["candidates"][0]["id"])
        self.optimizer.tick(Event())
        self.assertEqual(self.store.get(self.scope, run_id)["status"], "applied")
