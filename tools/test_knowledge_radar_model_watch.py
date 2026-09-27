"""Known-wrong checks for the hourly model watch: a failed read is never "no change", a 304 to sent validators
is, and only a real change marks the questions that read the changed source.

No network is used: the watched sources (models.dev, the newest Hugging Face repositories of named labs and the
LiteLLM price map) answer through a fake run network that honours validators the way a server does.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT, ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from knowledge_radar import model_watch, planner  # noqa: E402
from knowledge_radar.engines_network import request_key  # noqa: E402
from knowledge_radar.records import SourceBinding, read_contracts, read_registry  # noqa: E402

REGISTRY = read_registry(json.loads((ROOT / "tools/knowledge_radar/questions-v1.json").read_text(encoding="utf-8")))
CONTRACTS = read_contracts(json.loads((ROOT / "tools/knowledge_radar/source-contracts-v1.json").read_text(encoding="utf-8")))


def models_dev(*models):
    """A models.dev answer: one provider, each model with its output price; an OpenRouter provider is always present."""
    body = {"hostx": {"id": "hostx", "name": "Host X", "doc": "https://hostx.example.org/docs", "models": {
        model_id: {"id": model_id, "name": name, "structured_output": True, "tool_call": True,
                   "release_date": f"2026-09-{20 + index:02d}", "last_updated": "2026-09-26",
                   "limit": {"context": 131072, "output": 8192}, "cost": {"input": 0.1, "output": price},
                   "description": "Prose that is never copied into a brief."}
        for index, (model_id, name, price) in enumerate(models)}},
            "openrouter": {"id": "openrouter", "name": "OpenRouter", "models": {
                "lab/hidden": {"id": "lab/hidden", "name": "Only on OpenRouter", "cost": {"input": 0, "output": 0},
                               "structured_output": True}}}}
    return json.dumps(body).encode()


HUGGING_FACE = json.dumps([{"id": "google/model-a", "createdAt": "2026-09-20T00:00:00.000Z",
                            "lastModified": "2026-09-21T00:00:00.000Z", "downloads": 10, "likes": 2,
                            "tags": ["license:apache-2.0"], "pipeline_tag": "text-generation"}]).encode()
LITELLM = json.dumps({"sample_spec": {}, "hostx/alpha": {
    "litellm_provider": "hostx", "mode": "chat", "input_cost_per_token": 1e-07, "output_cost_per_token": 4e-07,
    "max_input_tokens": 131072, "supports_response_schema": True, "deprecation_date": "2026-12-01"}}).encode()
ALPHA = ("alpha", "Alpha", 0.4)
BETA = ("beta", "Beta", 0.2)


class Response:
    def __init__(self, status, body, etag=None):
        self.status, self.body, self.etag, self.last_modified = status, body, etag, None


class Network:
    """A run network that serves recorded bodies, answers 304 to a matching validator, and records validators."""

    def __init__(self, models_body, hugging_face_body=HUGGING_FACE, litellm_body=LITELLM):
        self.bodies = {"models.dev": (200, models_body), "huggingface.co": (200, hugging_face_body),
                       "raw.githubusercontent.com": (200, litellm_body)}
        self.requests, self.conditional, self.observed_validators, self.sent = [], {}, {}, []

    def get(self, engine_id, host, path, query=None, accept="application/json"):
        key = request_key(host, path, query)
        self.requests.append((engine_id, host, path, query))
        if host == "huggingface.co" and query and query.get("author") == "failing-author":
            return Response(503, b"")
        status, body = self.bodies[host]
        etag = '"%d"' % hash(body) if status == 200 else None
        sent = self.conditional.get(key)
        self.sent.append((key, sent))
        if status == 200 and sent and sent.get("etag") == etag:
            self.observed_validators[key] = dict(sent)
            return Response(304, b"", etag)
        if status == 200 and etag:
            self.observed_validators[key] = {"etag": etag, "last_modified": None}
        return Response(status, body, etag)


class ModelWatchChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.library = Path(self.temporary.name)
        self.clock = 0

    def tick(self, network, registry=REGISTRY):
        self.clock += 1
        return model_watch.tick(registry, CONTRACTS, ROOT, self.library, network,
                                now=f"2026-09-27T{self.clock:02d}:07:00Z")

    def source(self, record, engine):
        return next(row for row in record["sources"] if row["engine_id"] == engine)

    def snapshot(self, engine="models_dev_catalogue", index=0):
        return json.loads((self.library / f"state/model-watch/{engine}-{index:02d}.json").read_text())

    def test_the_hourly_question_reads_openly_licensed_sources_only(self):
        question = REGISTRY.question(model_watch.WATCHED_QUESTION)
        self.assertEqual(question.refresh, "hourly")
        engines = [binding.engine for binding in question.sources]
        self.assertEqual(engines, ["models_dev_catalogue", "huggingface_new_models", "litellm_prices"])
        self.assertTrue(all(CONTRACTS[engine].republication == "stored_facts" for engine in engines))

    def test_a_first_read_is_a_baseline_and_invalidates_nothing(self):
        record = self.tick(Network(models_dev(ALPHA)))
        row = self.source(record, "models_dev_catalogue")
        self.assertEqual((row["outcome"], row["baseline"]), ("checked_material_change", True))
        self.assertEqual(record["invalidated"], [])
        titles = json.dumps(self.snapshot())
        self.assertNotIn("Only on OpenRouter", titles)

    def test_the_same_listing_answers_304_and_that_is_a_validated_no_change(self):
        network = Network(models_dev(ALPHA))
        self.tick(network)
        before = self.snapshot()
        again = self.tick(network)
        row = self.source(again, "models_dev_catalogue")
        self.assertEqual((row["outcome"], row["validated_by_source"]), ("checked_no_relevant_change", True))
        self.assertTrue(any(sent and sent.get("etag") for key, sent in network.sent if key.startswith("models.dev")))
        after = self.snapshot()
        self.assertEqual(after["fingerprints"], before["fingerprints"])
        self.assertGreater(after["freshness"]["last_successful_retrieval"], before["freshness"]["last_successful_retrieval"])
        self.assertEqual(again["invalidated"], [])

    def test_a_new_model_invalidates_every_question_that_reads_the_source(self):
        self.tick(Network(models_dev(ALPHA)))
        added = self.tick(Network(models_dev(ALPHA, BETA)))
        row = self.source(added, "models_dev_catalogue")
        self.assertEqual((row["outcome"], row["added"]), ("checked_material_change", ["Beta (Host X)"]))
        expected = sorted(question.id for question in REGISTRY.active()
                          if any(binding.engine == "models_dev_catalogue" for binding in question.sources))
        self.assertEqual(added["invalidated"], expected)
        self.assertIn("models_structured_extraction", expected)
        self.assertTrue(list((self.library / "model-watch/2026-09-27").glob("change-*.json")))

    def test_known_wrong_a_failed_read_is_never_no_change(self):
        self.tick(Network(models_dev(ALPHA)))
        before = self.snapshot()
        broken = Network(models_dev(ALPHA))
        broken.bodies["models.dev"] = (503, b"")
        record = self.tick(broken)
        row = self.source(record, "models_dev_catalogue")
        self.assertEqual(row["outcome"], "could_not_check")
        self.assertNotEqual(row["outcome"], "checked_no_relevant_change")
        after = self.snapshot()
        self.assertEqual(after["fingerprints"], before["fingerprints"])
        self.assertEqual(after["validators"], before["validators"])
        self.assertEqual(after["freshness"]["last_successful_retrieval"], before["freshness"]["last_successful_retrieval"])
        self.assertNotEqual(after["freshness"]["last_attempted_retrieval"], before["freshness"]["last_attempted_retrieval"])
        self.assertEqual(record["invalidated"], [])

    def test_removed_guard_control_the_failure_branch_is_what_refuses(self):
        def naive(status, previous, current, complete=True):
            return "checked_no_relevant_change", {"baseline": False, "added": [], "removed": [], "changed": []}
        self.tick(Network(models_dev(ALPHA)))
        broken = Network(models_dev(ALPHA))
        broken.bodies["models.dev"] = (503, b"")
        with mock.patch.object(model_watch, "outcome_of", naive):
            record = self.tick(broken)
        self.assertEqual(self.source(record, "models_dev_catalogue")["outcome"], "checked_no_relevant_change")

    def test_a_304_without_an_earlier_snapshot_proves_nothing(self):
        self.assertEqual(model_watch.outcome_of("not_modified", None, {})[0], "could_not_check")
        self.assertEqual(model_watch.outcome_of("not_modified", {"a": "1"}, {})[0], "checked_no_relevant_change")

    def test_a_vanished_source_is_named_and_a_price_change_is_material(self):
        self.tick(Network(models_dev(ALPHA)))
        gone = Network(models_dev(ALPHA))
        gone.bodies["models.dev"] = (404, b"")
        self.assertEqual(self.source(self.tick(gone), "models_dev_catalogue")["outcome"],
                         "source_disappeared_or_access_changed")
        priced = self.tick(Network(models_dev(("alpha", "Alpha", 0.9))))
        self.assertEqual(self.source(priced, "models_dev_catalogue")["changed"], ["Alpha (Host X)"])

    def test_a_partial_read_never_counts_a_removal(self):
        question = REGISTRY.question(model_watch.WATCHED_QUESTION)
        binding = question.sources[1]

        def registry_with(authors):
            changed = replace(question, sources=(question.sources[0], SourceBinding(
                binding.engine, binding.section, {**binding.parameters, "authors": authors}), question.sources[2]))

            class Registry:
                def question(self, identity):
                    return changed if identity == changed.id else REGISTRY.question(identity)

                def active(self):
                    return tuple(changed if item.id == changed.id else item for item in REGISTRY.active())
            return Registry()

        network = Network(models_dev(ALPHA))
        first = self.tick(network, registry_with(["google"]))
        self.assertEqual(self.source(first, "huggingface_new_models")["outcome"], "checked_material_change")
        network.bodies["huggingface.co"] = (200, HUGGING_FACE.replace(b"google/model-a", b"google/model-b"))
        second = self.tick(network, registry_with(["google", "failing-author"]))
        row = self.source(second, "huggingface_new_models")
        self.assertEqual(row["outcome"], "partially_checked")
        self.assertEqual((row["added"], row["removed"]), (["google/model-b"], []))
        kept = self.snapshot("huggingface_new_models", 1)
        self.assertEqual(sorted(kept["fingerprints"]), ["hf:google/model-a", "hf:google/model-b"])
        self.assertEqual(kept["validators"], {})
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
