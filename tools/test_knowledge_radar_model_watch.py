"""Known-wrong checks for the hourly model watch: a failed read is never "no change", and only changes invalidate.

No network is used: the watched listings answer through a fake run network with recorded shapes.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT, ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from dataclasses import replace  # noqa: E402

from knowledge_radar import model_watch, planner  # noqa: E402
from knowledge_radar.records import SourceBinding, read_contracts, read_registry  # noqa: E402

REGISTRY = read_registry(json.loads((ROOT / "tools/knowledge_radar/questions-v1.json").read_text(encoding="utf-8")))
CONTRACTS = read_contracts(json.loads((ROOT / "tools/knowledge_radar/source-contracts-v1.json").read_text(encoding="utf-8")))


def openrouter(*models):
    return json.dumps({"data": [{"id": model_id, "name": name, "created": 1790000000 + index,
                                 "context_length": 131072,
                                 "pricing": {"prompt": "0.000001", "completion": price},
                                 "expiration_date": None, "description": "Long prose that is never copied anywhere."}
                                for index, (model_id, name, price) in enumerate(models)]}).encode()


HUGGING_FACE = json.dumps([{"id": "google/model-a", "createdAt": "2026-09-20T00:00:00.000Z",
                            "lastModified": "2026-09-21T00:00:00.000Z", "downloads": 10, "likes": 2,
                            "tags": ["license:apache-2.0"], "pipeline_tag": "text-generation"}]).encode()
ALPHA = ("lab/alpha", "Lab: Alpha", "0.000002")
BETA = ("lab/beta", "Lab: Beta", "0.000004")


class Response:
    def __init__(self, status, body):
        self.status, self.body = status, body


class Network:
    """Answers by host and path; a status per host can be set to simulate an outage."""

    def __init__(self, openrouter_body, hugging_face_body=HUGGING_FACE):
        self.bodies = {"openrouter.ai": (200, openrouter_body), "huggingface.co": (200, hugging_face_body)}
        self.requests = []

    def get(self, engine_id, host, path, query=None, accept="application/json"):
        self.requests.append((engine_id, host, path, query))
        status, body = self.bodies[host]
        if host == "huggingface.co" and query and query.get("author") == "failing-author":
            return Response(503, b"")
        return Response(status, body)


class ModelWatchChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.library = Path(self.temporary.name)
        self.clock = 0

    def tick(self, network):
        self.clock += 1
        return model_watch.tick(REGISTRY, CONTRACTS, ROOT, self.library, network,
                                now=f"2026-09-27T{self.clock:02d}:07:00Z")

    def source(self, record, engine):
        return next(row for row in record["sources"] if row["engine_id"] == engine)

    def snapshot(self):
        return json.loads((self.library / "state/model-watch/openrouter_models-00.json").read_text())

    def test_a_first_read_is_a_baseline_and_invalidates_nothing(self):
        record = self.tick(Network(openrouter(ALPHA)))
        row = self.source(record, "openrouter_models")
        self.assertEqual(row["outcome"], "checked_material_change")
        self.assertTrue(row["baseline"])
        self.assertEqual(record["invalidated"], [])

    def test_the_same_listing_is_no_change_and_a_new_model_invalidates_its_dependents(self):
        self.tick(Network(openrouter(ALPHA)))
        same = self.tick(Network(openrouter(ALPHA)))
        self.assertEqual(self.source(same, "openrouter_models")["outcome"], "checked_no_relevant_change")
        self.assertEqual(same["invalidated"], [])
        added = self.tick(Network(openrouter(ALPHA, BETA)))
        row = self.source(added, "openrouter_models")
        self.assertEqual((row["outcome"], row["added"]), ("checked_material_change", ["Lab: Beta"]))
        expected = sorted(question.id for question in REGISTRY.active()
                          if any(binding.engine == "openrouter_models" for binding in question.sources))
        self.assertEqual(added["invalidated"], expected)
        self.assertIn("models_new_releases", expected)
        self.assertTrue(list((self.library / "model-watch/2026-09-27").glob("change-*.json")))

    def test_known_wrong_a_failed_read_is_never_no_change(self):
        self.tick(Network(openrouter(ALPHA)))
        before = self.snapshot()
        broken = Network(openrouter(ALPHA))
        broken.bodies["openrouter.ai"] = (503, b"")
        record = self.tick(broken)
        row = self.source(record, "openrouter_models")
        self.assertEqual(row["outcome"], "could_not_check")
        self.assertNotEqual(row["outcome"], "checked_no_relevant_change")
        after = self.snapshot()
        self.assertEqual(after["fingerprints"], before["fingerprints"])
        self.assertEqual(after["freshness"]["last_successful_retrieval"], before["freshness"]["last_successful_retrieval"])
        self.assertNotEqual(after["freshness"]["last_attempted_retrieval"], before["freshness"]["last_attempted_retrieval"])
        self.assertEqual(record["invalidated"], [])

    def test_removed_guard_control_the_failure_branch_is_what_refuses(self):
        def naive(status, previous, current):
            return "checked_no_relevant_change", {"baseline": False, "added": [], "removed": [], "changed": []}
        self.tick(Network(openrouter(ALPHA)))
        broken = Network(openrouter(ALPHA))
        broken.bodies["openrouter.ai"] = (503, b"")
        with mock.patch.object(model_watch, "outcome_of", naive):
            record = self.tick(broken)
        self.assertEqual(self.source(record, "openrouter_models")["outcome"], "checked_no_relevant_change")

    def test_a_vanished_source_is_named_and_a_price_change_is_material(self):
        self.tick(Network(openrouter(ALPHA)))
        gone = Network(openrouter(ALPHA))
        gone.bodies["openrouter.ai"] = (404, b"")
        self.assertEqual(self.source(self.tick(gone), "openrouter_models")["outcome"],
                         "source_disappeared_or_access_changed")
        priced = self.tick(Network(openrouter(("lab/alpha", "Lab: Alpha", "0.000009"))))
        self.assertEqual(self.source(priced, "openrouter_models")["changed"], ["Lab: Alpha"])

    def test_a_partial_read_never_counts_a_removal(self):
        question = REGISTRY.question(model_watch.WATCHED_QUESTION)
        self.assertEqual(question.refresh, "hourly")
        binding = question.sources[1]

        def registry_with(authors):
            changed = replace(question, sources=(question.sources[0], SourceBinding(
                binding.engine, binding.section, {**binding.parameters, "authors": authors})))

            class Registry:
                def question(self, identity):
                    return changed if identity == changed.id else REGISTRY.question(identity)

                def active(self):
                    return tuple(changed if item.id == changed.id else item for item in REGISTRY.active())
            return Registry()

        network = Network(openrouter(ALPHA))
        first = model_watch.tick(registry_with(["google"]), CONTRACTS, ROOT, self.library, network,
                                 now="2026-09-27T01:07:00Z")
        self.assertEqual(self.source(first, "huggingface_new_models")["outcome"], "checked_material_change")
        network.bodies["huggingface.co"] = (200, HUGGING_FACE.replace(b"google/model-a", b"google/model-b"))
        second = model_watch.tick(registry_with(["google", "failing-author"]), CONTRACTS, ROOT, self.library, network,
                                  now="2026-09-27T02:07:00Z")
        row = self.source(second, "huggingface_new_models")
        self.assertEqual(row["outcome"], "partially_checked")
        self.assertEqual((row["added"], row["removed"]), (["google/model-b"], []))
        kept = json.loads((self.library / "state/model-watch/huggingface_new_models-01.json").read_text())
        self.assertEqual(sorted(kept["fingerprints"]), ["hf:google/model-a", "hf:google/model-b"])
        self.assertEqual(model_watch.outcome_of("partial", None, {"hf:x": "1"})[0], "partially_checked")

    def test_the_planner_answers_an_invalidated_question_before_it_is_due(self):
        state = {question.id: {"last_built_as_of": "2026-09-27", "last_built_at": "2026-09-27T08:30:00Z"}
                 for question in REGISTRY.active()}
        record = planner.plan(REGISTRY, state, "2026-09-27", maximum=5,
                              invalidations={"calendar_model_deprecations": "2026-09-27T12:07:00Z"})
        reasons = {row["question_id"]: (row["reason"], row["detail"]) for row in record["selected"]}
        self.assertEqual(reasons["calendar_model_deprecations"][0], "changed_source")
        self.assertIn("model watch", reasons["calendar_model_deprecations"][1])
        stale = planner.plan(REGISTRY, state, "2026-09-27", maximum=5,
                             invalidations={"calendar_model_deprecations": "2026-09-27T07:00:00Z"})
        self.assertNotIn("calendar_model_deprecations",
                         {row["question_id"] for row in stale["selected"] if row["reason"] == "changed_source"})


if __name__ == "__main__":
    unittest.main()
