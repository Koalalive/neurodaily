from contextlib import contextmanager
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.optimization import Optimizer, pareto
from neurodaily.optimization_api import router
from neurodaily.optimization_store import Store


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
                   return_value={"sources": [{"source": "pubmed", "status": "healthy"}],
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
