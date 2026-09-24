"""Offline checks for the generator's committed provider binding.

Every provider answer comes from a fixture transport patched in place of the
custom endpoint adapter's opener, so the real settings loader, CustomEndpoint
adapter and ModelGateway run while no socket is opened. The credential is a
secret-shaped fixture returned by an injected resolver; each run asserts it
reaches only the request header and never a file.
"""
import json
import tempfile
import unittest
import urllib.error
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from loop_engine.core import custom_endpoint
from tools import generate_original_native_candidates as generation
from tools.candidate_review import panel
from tools.test_prepare_harness_candidates import _git

KEY = "sk-" + "fixture0credential0" * 3
MODEL = "fixture-coder"
ENDPOINT = "https://fixture.invalid:6969/v1"
BINDING = "bindings/fixture.json"


class Transport:
    """Answers each request with an OpenAI-shaped event stream."""

    def __init__(self, model=MODEL, usage=True, error=None):
        self.model, self.usage, self.error = model, usage, error
        self.requests = []

    def open(self, request, timeout=None):
        body = json.loads(request.data)
        self.requests.append({"url": request.full_url, "headers": dict(request.header_items()), "json": body})
        if self.error is not None:
            raise self.error
        method = json.loads(body["messages"][-1]["content"])["method"]
        draft = {"record_type": generation.DRAFT_TYPE, "method_id": method["id"], "files": [
            {"path": f["path"], "content": "# Original fixture instructions\nRead reference.md.\n"
             if f["path"] == "AGENTS.md" else "# Reference\nA bounded fixture with no execution.\n"}
            for f in method["files"]]}
        text = json.dumps(draft)
        final = {"model": self.model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        if self.usage:
            final["usage"] = {"prompt_tokens": 120, "completion_tokens": 60}
        lines = [b"data: " + json.dumps({"model": self.model, "choices": [
                     {"index": 0, "delta": {"content": text[i:i + 50]}, "finish_reason": None}]}).encode()
                 for i in range(0, len(text), 50)]
        lines += [b"data: " + json.dumps(final).encode(), b"data: [DONE]"]
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


class ProviderBindingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.name", "Fixture")
        _git(self.repo, "config", "user.email", "fixture@example.invalid")
        (self.repo / "LICENSE").write_bytes((Path(__file__).resolve().parents[1] / "LICENSE").read_bytes())
        (self.repo / "source.py").write_text("def fixture(value):\n    return value\n")
        self.panel = {"record_type": "candidate_review_panel/v1",
                      "families": ["anthropic", "openai", "zhipu", "alibaba", "google"], "installations": []}
        self.provider = {"id": "fixture_box", "kind": "custom", "endpoint": ENDPOINT, "model": MODEL,
                         "wire": "openai", "locality": "organization", "purposes": ["generation"],
                         "stream": "stream", "tls_verification": "ca_file", "tls_ca_file": "resources/anchor.pem",
                         "tls_server_name": "origin.fixture.invalid", "tls_pinned_sha256": "ab" * 32}
        self.family = {"record_type": generation.FAMILY_EVIDENCE_TYPE, "provider_id": "fixture_box",
                       "endpoint": ENDPOINT, "model": MODEL, "family": "google",
                       "basis": "Fixture evidence for the binding contract only."}
        self.capacity = {"record_type": generation.CAPACITY_TYPE, "provider_id": "fixture_box",
                         "endpoint": ENDPOINT, "model": MODEL, "maximum_output_tokens": 8192,
                         "observed_at": "2026-09-23"}
        self.anchor = b"-----BEGIN CERTIFICATE-----\nZml4dHVyZSBhbmNob3I=\n-----END CERTIFICATE-----\n"
        self.method = {"id": "inspect_fixture", "title": "Inspect fixture", "purpose": "Inspect one bounded input.",
                       "sources": ["source.py"], "layer": "context", "family": "native_instruction",
                       "search_tags": ["inspect fixture"], "tags": {"domain": ["software"], "language": ["en"]},
                       "symbols": [], "declared_effects": [], "kind": "instruction_file", "styles": ["codex"],
                       "dependencies": [], "brief": "Inspect the supplied value without mutation.",
                       "acceptance": ["Report unknown when the required value is absent."],
                       "opportunity": "Original fixture method for contract testing, not customer intelligence.",
                       "files": [{"path": "AGENTS.md", "role": "instruction_file", "media_type": "text/markdown",
                                  "purpose": "Native briefing"},
                                 {"path": "reference.md", "role": "skill_reference", "media_type": "text/markdown",
                                  "purpose": "Supporting checks"}]}
        self.methods = [self.method]
        self.resolved = []
        self.commit()

    def write(self, relative, raw):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw if isinstance(raw, bytes) else json.dumps(raw, indent=1).encode())
        return generation.digest(path.read_bytes())

    def commit(self, **binding_changes):
        self.write("tools/candidate_review/resources/panel.json", self.panel)
        anchor = self.write("resources/anchor.pem", self.anchor)
        family = self.write("evidence/family.json", self.family)
        capacity = self.write("evidence/capacity.json", self.capacity)
        binding = {"record_type": generation.BINDING_TYPE, "binding_id": "fixture_binding",
                   "provider": self.provider, "trust_anchor_sha256": anchor, "producer_family": "google",
                   "family_evidence": {"path": "evidence/family.json", "sha256": family},
                   "capacity": {"path": "evidence/capacity.json", "sha256": capacity},
                   "credential_reference": "fixture-credential", **binding_changes}
        self.binding_digest = self.write(BINDING, binding)
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-q", "--allow-empty", "-m", "fixture binding")
        plan = {"record_type": generation.PLAN_TYPE, "source_revision": _git(self.repo, "rev-parse", "HEAD"),
                "license": {"expression": "MIT", "path": "LICENSE",
                            "sha256": generation.digest((self.repo / "LICENSE").read_bytes())},
                "sources": {"source.py": generation.digest((self.repo / "source.py").read_bytes())},
                "methods": self.methods}
        self.plan_path = self.root / "plan.json"
        self.plan_path.write_text(json.dumps(plan))

    def resolver(self, name):
        self.resolved.append(name)
        if name != "fixture-credential":
            raise LookupError("unknown reference")
        return KEY

    def request(self, **changes):
        request = generation.GenerationRequest(
            self.repo, self.plan_path, generation.digest(self.plan_path.read_bytes()), self.root / "run", MODEL,
            "google", 3, output_tokens=4096, allow_unbounded_total=True, calls_authorized=True,
            writes_authorized=True, provider_binding=BINDING, provider_binding_sha256=self.binding_digest)
        return replace(request, **changes)

    def run_bound(self, transport=None, resolver=None, **changes):
        self.transport = transport or Transport()
        with patch.object(custom_endpoint, "_endpoint_opener", lambda ep: self.transport), \
                patch.object(custom_endpoint, "_claim_call_slot", lambda name: 0.0):
            return generation.generate(self.request(**changes), credential_resolver=resolver or self.resolver)

    def assert_refused_before_credential(self, code, **changes):
        with self.assertRaisesRegex(generation.GenerationError, code):
            self.run_bound(**changes)
        self.assertEqual(self.resolved, [])
        self.assertEqual(self.transport.requests, [])
        self.assertFalse((self.root / "run").exists())

    def output_files_text(self):
        return "".join(path.read_bytes().decode("utf-8", "replace")
                       for path in (self.root / "run").rglob("*") if path.is_file())

    def test_bound_provider_prepares_a_candidate_through_the_real_adapter_and_gateway(self):
        result = self.run_bound()
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["approval_count"], 0)
        self.assertFalse(result["fixture_run"])
        self.assertEqual(self.resolved, ["fixture-credential"])
        [sent] = self.transport.requests
        self.assertEqual(sent["url"], ENDPOINT + "/chat/completions")
        self.assertEqual(sent["headers"]["Authorization"], "Bearer " + KEY)
        self.assertEqual((sent["json"]["model"], sent["json"]["max_tokens"], sent["json"]["stream"]),
                         (MODEL, 4096, True))
        self.assertNotIn(KEY, self.output_files_text())
        run = json.loads((self.root / "run/run.json").read_text())
        self.assertEqual(run["record_type"], "original_native_generation_run/v7")
        self.assertEqual(run["provider"], "fixture_box")
        self.assertEqual(run["producer_family"], "google")
        self.assertEqual(run["family_source_sha256"], generation.digest((self.repo / "evidence/family.json").read_bytes()))
        binding = run["provider_binding"]
        self.assertEqual(binding["sha256"], self.binding_digest)
        self.assertEqual(binding["credential_reference"], "operator:fixture-credential")
        self.assertEqual(binding["tls_pinned_sha256"], "ab" * 32)
        self.assertEqual(run["capacity"]["maximum_output_tokens"], 8192)
        self.assertIn("evidence/capacity.json", run["capacity"]["source"])
        for module in ("custom_endpoint.py", "runtime_settings.py", "settings_loader.py", "model_gateway.py"):
            self.assertIn(module, run["implementations"])
        completion = json.loads((self.root / "run/journal.jsonl").read_text().splitlines()[-1])["data"]
        self.assertEqual((completion["reported_model"], completion["attempt_provider"]), (MODEL, "fixture_box"))
        self.assertEqual((completion["input_tokens"], completion["output_tokens"]), (120, 60))
        items = json.loads((self.root / "run/inspect_fixture.attempt-1/candidates/items.json").read_text())
        self.assertEqual(items["items"][0]["producer"]["family"], "google")
        self.assertEqual(items["items"][0]["producer"]["producer_identity"], "fixture_box:" + MODEL)

    def test_producer_family_from_the_binding_cannot_approve_its_own_candidate(self):
        self.run_bound()
        items = json.loads((self.root / "run/inspect_fixture.attempt-1/candidates/items.json").read_text())
        producer = items["items"][0]["producer"]["family"]
        policy = type("Policy", (), {"minimum_approvals": 3, "minimum_distinct_families": 3})()
        rows = [{"reviewer_id": name, "decision": panel.APPROVE, "reasons": []} for name in ("a", "b", "c", "d")]
        same = {"a": "google", "b": "google", "c": "google", "d": "google"}
        mixed = {"a": "google", "b": "openai", "c": "zhipu", "d": "alibaba"}
        self.assertEqual(panel.decide_outcome(rows, policy, same, producer)[0], panel.PANEL_INCOMPLETE)
        self.assertEqual(panel.decide_outcome(rows[:3], policy, mixed, producer)[0], panel.PANEL_INCOMPLETE)
        self.assertEqual(panel.decide_outcome(rows, policy, mixed, producer)[0], panel.APPROVED)
        reviewer = type("Installation", (), {"family": "google"})()
        self.assertTrue(panel.producer_family_excluded(reviewer, type("Producer", (), {"family": producer})()))

    def test_only_an_ollama_credential_refuses_before_dispatch(self):
        def missing(name):
            self.resolved.append(name)
            raise LookupError("no Tactical credential in this keyring")

        with patch.dict("os.environ", {"OLLAMA_API_KEY": "present-but-not-this-provider"}), \
                patch("loop_engine.core.ollama_client.chat_maxout",
                      side_effect=AssertionError("Ollama must never be called")), \
                self.assertRaisesRegex(generation.GenerationError, "provider_credential_unavailable"):
            self.run_bound(resolver=missing)
        self.assertEqual(self.resolved, ["fixture-credential"])
        self.assertEqual(self.transport.requests, [])
        self.assertFalse((self.root / "run").exists())

    def test_changed_binding_anchor_evidence_capacity_or_panel_bytes_refuse_before_credential(self):
        for relative in (BINDING, "resources/anchor.pem", "evidence/family.json", "evidence/capacity.json",
                         "tools/candidate_review/resources/panel.json"):
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                try:
                    self.assert_refused_before_credential("not_committed|invalid|trust_anchor")
                finally:
                    path.write_bytes(original)

    def test_uncommitted_binding_refuses_even_when_its_digest_matches(self):
        raw = (self.repo / BINDING).read_bytes().replace(b'"fixture_binding"', b'"uncommitted_binding"')
        self.binding_digest = self.write("bindings/uncommitted.json", raw)
        self.assert_refused_before_credential("provider_binding_not_committed",
                                              provider_binding="bindings/uncommitted.json")

    def test_unverified_or_plain_endpoint_refuses_even_without_trust_options(self):
        cases = ({"tls_verification": "skip"}, {"tls_verification": "default"},
                 {"tls_verification": "default", "endpoint": "http://fixture.invalid:6969/v1"})
        for change in cases:
            with self.subTest(change=sorted(change)):
                saved = dict(self.provider)
                self.provider.update({"tls_ca_file": "", "tls_server_name": "", "tls_pinned_sha256": "", **change})
                for key in [key for key, value in self.provider.items() if value == ""]:
                    del self.provider[key]
                self.commit(trust_anchor_sha256=None)
                code = ("provider_binding_requires_verified_https" if change.get("tls_verification") == "skip"
                        or "endpoint" in change else None)
                if code is None:
                    # System trust over HTTPS is a verified connection; it is accepted.
                    self.assertEqual(self.run_bound()["candidate_count"], 1)
                    self.resolved.clear()
                    (self.root / "run").rename(self.root / "run-system-trust")
                else:
                    self.assert_refused_before_credential(code)
                self.provider = saved

    def test_model_or_family_that_differs_from_the_binding_refuses_without_alias_normalization(self):
        self.assert_refused_before_credential("provider_binding_model_mismatch", model=MODEL + ":latest")
        self.assert_refused_before_credential("provider_binding_family_mismatch", producer_family="alibaba")
        self.assert_refused_before_credential("provider_binding_not_committed", provider_binding_sha256="0" * 64)

    def test_unknown_or_foreign_capacity_refuses_before_credential(self):
        cases = ((("maximum_output_tokens", "unknown"),), (("model", "other-model"),),
                 (("endpoint", "https://other.invalid/v1"),), (("record_type", "endpoint_output_capacity/v0"),))
        for changes in cases:
            with self.subTest(changes=changes):
                saved = dict(self.capacity)
                self.capacity.update(dict(changes))
                self.commit()
                code = ("output_capacity_unknown" if changes[0][0] == "maximum_output_tokens"
                        else "capacity_record_invalid" if changes[0][0] == "record_type"
                        else "capacity_record_not_for_this_binding")
                self.assert_refused_before_credential(code)
                self.capacity = saved

    def test_family_evidence_for_another_model_or_family_refuses(self):
        for key, value in (("model", "other-model"), ("family", "alibaba")):
            with self.subTest(key=key):
                saved = dict(self.family)
                self.family[key] = value
                self.commit()
                self.assert_refused_before_credential("family_evidence_not_for_this_binding")
                self.family = saved

    def test_producer_family_outside_the_review_vocabulary_refuses(self):
        self.panel["families"] = ["anthropic", "openai", "zhipu", "alibaba"]
        self.commit()
        self.assert_refused_before_credential("producer_family_outside_review_vocabulary")

    def test_unverified_plain_or_credential_bearing_settings_refuse(self):
        cases = (({"tls_verification": "skip", "tls_ca_file": "", "tls_server_name": "", "tls_pinned_sha256": ""},
                  "provider_binding_requires_verified_https|provider_binding_trust_anchor_invalid"),
                 ({"endpoint": "http://fixture.invalid:6969/v1"}, "provider_binding_settings_invalid"),
                 ({"api_key": KEY}, "provider_binding_contains_secret"),
                 ({"api_key": "not-secret-shaped"}, "provider_binding_settings_invalid"),
                 ({"credential_env": "FIXTURE_KEY"}, "provider_binding_settings_invalid"),
                 ({"maximum_output_tokens": 999999, "maximum_output_source": "guess"},
                  "provider_binding_settings_invalid"),
                 ({"purposes": ["decide_label"]}, "provider_binding_purpose_undeclared"))
        for change, code in cases:
            with self.subTest(change=sorted(change)):
                saved = dict(self.provider)
                self.provider.update(change)
                self.commit()
                self.assert_refused_before_credential(code)
                self.provider = saved

    def test_a_binding_serves_only_the_purposes_it_declares(self):
        def load(purpose):
            return generation.load_provider_binding(self.repo, _git(self.repo, "rev-parse", "HEAD"), BINDING,
                                                    self.binding_digest, MODEL, "google", purpose=purpose)

        self.assertEqual(load("generation").binding_id, "fixture_binding")
        with self.assertRaisesRegex(generation.GenerationError, "provider_binding_purpose_undeclared"):
            load("decide_label")
        self.provider["purposes"] = ["generation", "decide_label"]
        self.commit()
        self.assertEqual(load("decide_label").binding_id, "fixture_binding")
        self.assertEqual(self.resolved, [], "a purpose check never reads the credential")

    def test_binding_and_injected_provider_are_mutually_exclusive(self):
        with self.assertRaisesRegex(generation.GenerationError, "provider_binding_excludes_injected_provider"):
            generation.generate(self.request(), provider_spec=object())

    def test_another_reported_model_produces_no_candidate_and_stops(self):
        self.methods.append({**self.method, "id": "second_fixture"})
        self.commit()
        result = self.run_bound(Transport(model="other-model"))
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["stop_reason"], "model_identity_mismatch")
        self.assertEqual(len(self.transport.requests), 1)
        completion = json.loads((self.root / "run/journal.jsonl").read_text().splitlines()[-1])["data"]
        self.assertEqual(completion["error_code"], "model_identity_mismatch")
        # The observed identity is kept; it is never replaced by the requested one.
        self.assertEqual(completion["reported_model"], "other-model")

    def test_omitted_usage_stays_unknown_not_zero(self):
        self.run_bound(Transport(usage=False))
        completion = json.loads((self.root / "run/journal.jsonl").read_text().splitlines()[-1])["data"]
        self.assertIsNone(completion["input_tokens"])
        self.assertIsNone(completion["output_tokens"])
        self.assertEqual(completion["charge_basis"], "unknown")

    def test_tls_trust_refusal_sends_nothing_and_stops_the_run(self):
        self.methods.append({**self.method, "id": "second_fixture"})
        self.commit()
        refused = urllib.error.URLError(custom_endpoint.TLSTrustRefused("fixture pin mismatch"))
        result = self.run_bound(Transport(error=refused))
        self.assertEqual(result["stop_reason"], "tls_trust_refused")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(len(self.transport.requests), 1)
        completion = json.loads((self.root / "run/journal.jsonl").read_text().splitlines()[-1])["data"]
        self.assertEqual((completion["error_code"], completion["physical_model_calls"]), ("tls_trust_refused", 0))

    def test_changed_binding_summary_refuses_resume_before_another_call(self):
        self.run_bound()
        summary = generation.ProviderBinding.summary
        with patch.object(generation.ProviderBinding, "summary",
                          lambda binding: {**summary(binding), "settings_sha256": "0" * 64}), \
                self.assertRaisesRegex(generation.GenerationError, "resume_binding_changed"):
            self.run_bound()
        self.assertEqual(len(self.transport.requests), 0)

    def test_without_a_binding_the_reviewed_ollama_panel_still_decides(self):
        with self.assertRaisesRegex(generation.GenerationError, "producer_family_not_bound_to_registered_model"):
            self.run_bound(provider_binding=None, provider_binding_sha256=None)
        self.assertEqual(self.resolved, [])
        self.assertEqual(self.transport.requests, [])


if __name__ == "__main__":
    unittest.main()
