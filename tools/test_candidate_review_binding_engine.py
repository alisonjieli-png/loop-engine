"""Offline checks for the ``provider_binding`` reviewer engine.

The engine reaches an organisation endpoint only through a provider binding
committed in the checkout, validated by the generator's own loader for the
review purpose, with the credential resolved inside the process by an injected
resolver. Every provider answer comes from a fixture transport patched in place
of the custom endpoint adapter's opener, so the real settings loader, adapter
and ModelGateway run while no socket is opened.

```text
provider_binding engine
├── available only for a committed binding that declares the review purpose
├── refused before the credential: other bytes, other model, other family, capacity too small
├── the credential reaches the request header only
└── the answering model is the one the endpoint reports
```
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent))

from loop_engine.core import custom_endpoint  # noqa: E402

from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, reviewers  # noqa: E402
from tools import generate_original_native_candidates as generation  # noqa: E402
from tools.test_prepare_harness_candidates import _git  # noqa: E402

RESOURCES = HERE / "candidate_review" / "resources"
PANEL_RECORD = json.loads((RESOURCES / "panel.json").read_text(encoding="utf-8"))
PANEL = config.PanelConfiguration.from_dict(PANEL_RECORD)
KEY = "sk-" + "fixture0credential0" * 3
MODEL = "fixture-coder"
ENDPOINT = "https://fixture.invalid:6969/v1"
BINDING = "bindings/fixture.json"
PROMPT = reviewers.ReviewPrompt(system="You review one item.", user="The item text is here.", sha256="0" * 64,
                                estimated_input_tokens=12)
ALLOWANCE = reviewers.CallAllowance(max_output_tokens=4096, timeout_seconds=30.0, temperature=0.0)
ANSWER = '{"body_sha256": "' + "a" * 64 + '", "decision": "approve", "findings": [], "reasons": "Fine."}'


class Transport:
    """Answers each request with an OpenAI-shaped event stream holding one fixed answer."""

    def __init__(self, model=MODEL, text=ANSWER):
        self.model, self.text, self.requests = model, text, []

    def open(self, request, timeout=None):
        self.requests.append({"url": request.full_url, "headers": dict(request.header_items()),
                              "json": json.loads(request.data)})
        final = {"model": self.model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                 "usage": {"prompt_tokens": 900, "completion_tokens": 70}}
        lines = [b"data: " + json.dumps({"model": self.model, "choices": [
            {"index": 0, "delta": {"content": self.text}, "finish_reason": None}]}).encode(),
            b"data: " + json.dumps(final).encode(), b"data: [DONE]"]
        return _Stream(lines)


class _Stream:
    def __init__(self, lines):
        self.lines = lines

    def __iter__(self):
        return iter(self.lines)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class BindingEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.name", "Fixture")
        _git(self.repo, "config", "user.email", "fixture@example.invalid")
        self.provider = {"id": "fixture_box", "kind": "custom", "endpoint": ENDPOINT, "model": MODEL,
                         "wire": "openai", "locality": "organization", "purposes": ["generation", "decide_label"],
                         "stream": "stream", "tls_verification": "ca_file", "tls_ca_file": "resources/anchor.pem",
                         "tls_server_name": "origin.fixture.invalid", "tls_pinned_sha256": "ab" * 32}
        self.capacity = 65536
        self.resolved = []
        self.commit()

    def write(self, relative, value):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else json.dumps(value, indent=1).encode())
        return generation.digest(path.read_bytes())

    def commit(self):
        self.write("tools/candidate_review/resources/panel.json",
                   {"record_type": "candidate_review_panel/v1", "families": list(PANEL.families), "installations": []})
        anchor = self.write("resources/anchor.pem",
                            b"-----BEGIN CERTIFICATE-----\nZml4dHVyZSBhbmNob3I=\n-----END CERTIFICATE-----\n")
        identity = {"provider_id": "fixture_box", "endpoint": ENDPOINT, "model": MODEL}
        family = self.write("evidence/family.json", {"record_type": generation.FAMILY_EVIDENCE_TYPE, **identity,
                                                     "family": "google", "basis": "Fixture evidence only."})
        capacity = self.write("evidence/capacity.json", {"record_type": generation.CAPACITY_TYPE, **identity,
                                                         "maximum_output_tokens": self.capacity,
                                                         "observed_at": "2026-09-24"})
        self.binding_digest = self.write(BINDING, {
            "record_type": generation.BINDING_TYPE, "binding_id": "fixture_binding", "provider": self.provider,
            "trust_anchor_sha256": anchor, "producer_family": "google",
            "family_evidence": {"path": "evidence/family.json", "sha256": family},
            "capacity": {"path": "evidence/capacity.json", "sha256": capacity},
            "credential_reference": "fixture-credential"})
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-q", "--allow-empty", "-m", "fixture binding")

    def resolver(self, name):
        self.resolved.append(name)
        if name != "fixture-credential":
            raise LookupError("unknown reference")
        return KEY

    def engine(self, *, family="google", model=MODEL, resolver="default", **settings):
        value = next(dict(item) for item in PANEL_RECORD["installations"]
                     if item["installation_id"] == "tactical.gemma-4-coding-abliterated")
        value.update(family=family, model=model)
        value["settings"] = {**value["settings"], "binding_path": BINDING, "binding_sha256": self.binding_digest,
                             **settings}
        installation = config.ReviewerInstallation.from_dict(value, PANEL.families)
        context = reviewers.ReviewerContext(repository=self.repo,
                                            credential_resolver=self.resolver if resolver == "default" else resolver)
        return engines.build_reviewer(installation, PANEL.policy, context)

    def review(self, engine, transport=None):
        self.transport = transport or Transport()
        with patch.object(custom_endpoint, "_endpoint_opener", lambda endpoint: self.transport), \
                patch.object(custom_endpoint, "_claim_call_slot", lambda name: 0.0):
            return engine.availability(), engine.review(PROMPT, ALLOWANCE)

    def test_a_committed_review_binding_answers_through_the_gateway(self):
        availability, attempt = self.review(self.engine())
        self.assertTrue(availability.available, availability.reason)
        self.assertEqual(availability.engine_version, "provider_binding/fixture_binding")
        self.assertEqual(availability.model_version["binding_sha256"], self.binding_digest)
        self.assertEqual(attempt.outcome, reviewers.ANSWERED)
        self.assertEqual((attempt.text, attempt.reported_model), (ANSWER, MODEL))
        self.assertEqual((attempt.usage.input_tokens, attempt.usage.output_tokens), (900, 70))
        self.assertEqual(attempt.physical_model_calls, 1)
        [sent] = self.transport.requests
        self.assertEqual(sent["url"], ENDPOINT + "/chat/completions")
        self.assertEqual(sent["headers"]["Authorization"], "Bearer " + KEY)
        self.assertEqual((sent["json"]["model"], sent["json"]["max_tokens"]), (MODEL, 4096))
        self.assertEqual(self.resolved, ["fixture-credential"])
        self.assertNotIn(KEY, json.dumps(availability.model_version) + attempt.route_or_command + attempt.error_detail)

    def test_refusals_before_the_credential_is_read(self):
        cases = {
            "the binding does not declare the review purpose": (
                lambda: self.provider.update(purposes=["generation"]) or self.commit(), {},
                "provider_binding_purpose_undeclared"),
            "the installation names other bytes": (lambda: None, {"binding_sha256": "b" * 64},
                                                    "provider_binding_not_committed"),
            "the installation names another family": (lambda: None, {"family": "openai"},
                                                      "provider_binding_family_mismatch"),
            "the installation names another model": (lambda: None, {"model": "other-model"},
                                                     "provider_binding_model_mismatch"),
            "the allocation exceeds the measured capacity": (lambda: None, {"output_allocation_tokens": 70000},
                                                             "exceeds the binding's measured capacity"),
        }
        for name, (change, overrides, reason) in cases.items():
            with self.subTest(case=name):
                self.setUp()
                change()
                family, model = overrides.pop("family", "google"), overrides.pop("model", MODEL)
                engine = self.engine(family=family, model=model, **overrides)
                availability, attempt = self.review(engine)
                self.assertFalse(availability.available)
                self.assertEqual(availability.reason_code, reviewers.ENGINE_UNAVAILABLE)
                self.assertIn(reason, availability.reason)
                self.assertEqual(attempt.outcome, reviewers.ENGINE_UNAVAILABLE)
                self.assertEqual(self.resolved, [], "no refusal reads the credential")
                self.assertEqual(self.transport.requests, [])

    def test_an_unavailable_credential_is_a_refused_login(self):
        def missing(name):
            self.resolved.append(name)
            raise LookupError("no credential in this keyring")

        for resolver in (None, missing):
            with self.subTest(resolver=resolver):
                availability, attempt = self.review(self.engine(resolver=resolver))
                self.assertFalse(availability.available)
                self.assertEqual(availability.reason_code, reviewers.AUTHENTICATION_UNAVAILABLE)
                self.assertEqual(attempt.outcome, reviewers.AUTHENTICATION_UNAVAILABLE)
                self.assertEqual(self.transport.requests, [])

    def test_another_reported_model_is_not_an_answer(self):
        _availability, attempt = self.review(self.engine(), Transport(model="other-model"))
        self.assertEqual(attempt.outcome, reviewers.MODEL_IDENTITY_MISMATCH)
        self.assertEqual(attempt.text, "")
        self.assertEqual(attempt.reported_model, "other-model", "the observed identity is kept")


if __name__ == "__main__":
    unittest.main()
