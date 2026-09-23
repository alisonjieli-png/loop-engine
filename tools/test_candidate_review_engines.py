"""Checks for the reviewer engines behind the review panel's fixed reviewer edge.

Every engine answers the same way: one ``ReviewerAttempt`` with a closed
outcome, the answer text, the usage exactly as reported (unknown stays
unknown), the physical model calls, the pause the provider asked for, and the
model identity. The engines differ only inside:

```text
Reviewer engines
├── model_gateway: an Ollama Cloud model through the repository's model gateway
│   ├── usage as the provider reported it, or unknown
│   ├── a rate limit, a spent allowance, an outage and a refused key kept apart
│   ├── the model policy's refusal honoured before any provider call
│   └── the output allocation the panel policy declares
└── command_line: the Codex and Claude Code command lines
    ├── the prompt on standard input, never on the command line
    ├── an empty temporary working folder, removed afterwards
    ├── the output protocol of each command read exactly
    └── a timeout, a failed command and a refused login kept apart
```

No network, model or provider call happens here: the gateway engine talks to a
fake provider adapter, and the command engine runs small fake programs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from loop_engine.core.model_capabilities import ModelOutputCapability  # noqa: E402
from loop_engine.core.ollama_client import ChatResult  # noqa: E402

from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines  # noqa: E402
from candidate_review import reviewers  # noqa: E402
from candidate_review.records import CandidateReviewError  # noqa: E402
from candidate_review.reviewers import gateway as gateway_module  # noqa: E402

RESOURCES = HERE / "candidate_review" / "resources"
PANEL_RECORD = json.loads((RESOURCES / "panel.json").read_text(encoding="utf-8"))
PANEL = config.PanelConfiguration.from_dict(PANEL_RECORD)
PROMPT = reviewers.ReviewPrompt(system="You review one item.", user="The item text is here.",
                                sha256="0" * 64, estimated_input_tokens=12)
ALLOWANCE = reviewers.CallAllowance(max_output_tokens=PANEL.policy.output_allocation_tokens,
                                    timeout_seconds=30.0, temperature=PANEL.policy.temperature)
LISTING = {"glm-5.3": {"digest": "632dfda18c6d", "modified_at": "2026-08-28T08:00:00-07:00"},
           "deepseek-v4-pro:0813": {"digest": "db976f1eacdd", "modified_at": "2026-08-13T08:00:00-07:00"}}


@dataclass
class FakeAdapter:
    """A provider adapter that answers from a script and remembers what it was asked."""

    result: ChatResult
    DEFAULT_MODEL: str = "glm-5.3"
    calls: list = field(default_factory=list)

    def output_capability_for(self, model):
        return ModelOutputCapability(1048576, "fixture declaration", observed_at="2026-09-22")

    def verify(self, model=""):
        return True

    def live_models(self):
        return list(LISTING)

    def chat_maxout(self, prompt, *, model="", system="", temperature=0.7, timeout=900.0, max_attempts=1,
                    max_output_tokens=None, output_capability=None):
        self.calls.append({"prompt": prompt, "model": model, "system": system, "temperature": temperature,
                           "max_output_tokens": max_output_tokens})
        return self.result


def _installation(installation_id: str) -> config.ReviewerInstallation:
    return next(item for item in PANEL.installations if item.installation_id == installation_id)


def _enabled(installation_id: str) -> config.ReviewerInstallation:
    value = next(dict(item) for item in PANEL_RECORD["installations"] if item["installation_id"] == installation_id)
    value["enabled"], value["disabled_reason"] = True, ""
    return config.ReviewerInstallation.from_dict(value, PANEL.families)


def _gateway(result: ChatResult, installation_id: str = "ollama.glm-5.3", listing=None):
    adapter = FakeAdapter(result)
    context = reviewers.ReviewerContext(provider_adapters={"ollama_cloud": adapter},
                                        model_listing=LISTING if listing is None else listing)
    installation = (_installation(installation_id) if _installation(installation_id).enabled
                    else _enabled(installation_id))
    engine = engines.build_reviewer(installation, PANEL.policy, context)
    return engine, adapter


def _answer(text: str = '{"decision": "approve"}', model: str = "glm-5.3", **fields) -> ChatResult:
    values = {"prompt_tokens": 1200, "eval_tokens": 90, "response_received": True, "done": True,
              "done_reason": "stop", "usage_reported": True}
    values.update(fields)
    return ChatResult(text, model, **values)


#: The provider's credential variable, set to a placeholder that is not shaped like a key. The engine
#: checks only that the variable is present; the fake adapter never reads it.
PRESENT = {"OLLAMA_API_KEY": "placeholder-for-a-check"}


class GatewayEngineTest(unittest.TestCase):
    """An Ollama Cloud model reached through the repository's model gateway."""

    def setUp(self):
        patcher = mock.patch.dict(os.environ, PRESENT)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_credential_missing_from_the_environment_makes_the_engine_unavailable(self):
        """The key is read only from the environment, so no configuration file is ever consulted instead."""
        engine, adapter = _gateway(_answer())
        with mock.patch.dict(os.environ, {}, clear=True):
            availability = engine.availability()
            attempt = engine.review(PROMPT, ALLOWANCE)
        self.assertFalse(availability.available)
        self.assertEqual(availability.reason_code, reviewers.AUTHENTICATION_UNAVAILABLE)
        self.assertNotIn("placeholder", availability.reason)
        self.assertEqual(attempt.outcome, reviewers.AUTHENTICATION_UNAVAILABLE)
        self.assertEqual(attempt.physical_model_calls, 0)
        self.assertEqual(adapter.calls, [])

    def test_the_listing_reads_the_key_only_from_the_environment(self):
        """Even when the repository's loader would find a key elsewhere, the listing refuses without the variable."""
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(gateway_module.ollama_client, "load_api_key", lambda *arguments: "found-elsewhere"), \
                mock.patch.object(gateway_module.urllib.request, "urlopen",
                                  side_effect=AssertionError("no request without the variable")):
            record = gateway_module.listed_model_versions()
        self.assertFalse(record["ok"])
        self.assertIn("environment", record["error"])
        self.assertNotIn("found-elsewhere", json.dumps(record))

    def test_an_answer_keeps_the_usage_the_provider_reported(self):
        engine, adapter = _gateway(_answer())
        availability = engine.availability()
        self.assertTrue(availability.available, availability.reason)
        self.assertEqual(availability.model_version["digest"], "632dfda18c6d")
        attempt = engine.review(PROMPT, ALLOWANCE)
        self.assertEqual(attempt.outcome, reviewers.ANSWERED)
        self.assertEqual(attempt.text, '{"decision": "approve"}')
        self.assertEqual((attempt.usage.input_tokens, attempt.usage.output_tokens), (1200, 90))
        self.assertEqual(attempt.usage.source, reviewers.PROVIDER_REPORTED)
        self.assertEqual(attempt.physical_model_calls, 1)
        self.assertEqual(attempt.reported_model, "glm-5.3")
        self.assertEqual(len(adapter.calls), 1)

    def test_the_system_and_the_request_travel_apart_with_the_declared_allocation(self):
        engine, adapter = _gateway(_answer())
        engine.review(PROMPT, ALLOWANCE)
        sent = adapter.calls[0]
        self.assertEqual((sent["system"], sent["prompt"]), (PROMPT.system, PROMPT.user))
        self.assertEqual(sent["max_output_tokens"], PANEL.policy.output_allocation_tokens)
        self.assertEqual(sent["temperature"], PANEL.policy.temperature)

    def test_missing_usage_stays_unknown_never_zero(self):
        engine, _adapter = _gateway(_answer(prompt_tokens=None, eval_tokens=None, usage_reported=False))
        attempt = engine.review(PROMPT, ALLOWANCE)
        self.assertEqual(attempt.outcome, reviewers.ANSWERED)
        self.assertIsNone(attempt.usage.input_tokens)
        self.assertIsNone(attempt.usage.output_tokens)
        self.assertEqual(attempt.usage.source, reviewers.USAGE_UNKNOWN)
        self.assertFalse(attempt.usage.complete)

    def test_provider_failures_keep_their_classes(self):
        cases = {
            "HTTP 429 (retry after 7s): too many requests": (reviewers.RATE_LIMITED, 7.0),
            "HTTP 429: you have reached your weekly usage limit, add usage credits": (reviewers.USAGE_LIMIT_REACHED,
                                                                                      None),
            "HTTP 503: service unavailable": (reviewers.PROVIDER_UNAVAILABLE, None),
            "HTTP 401: unauthorized": (reviewers.AUTHENTICATION_UNAVAILABLE, None),
            "OLLAMA_API_KEY not found": (reviewers.AUTHENTICATION_UNAVAILABLE, None),
        }
        for error, (outcome, retry_after) in cases.items():
            with self.subTest(error=error):
                result = ChatResult("", "glm-5.3", ok=False, error=error, retry_after_seconds=retry_after,
                                    physical_requests=0 if "not found" in error else 1)
                engine, _adapter = _gateway(result)
                attempt = engine.review(PROMPT, ALLOWANCE)
                self.assertEqual(attempt.outcome, outcome)
                self.assertEqual(attempt.retry_after_seconds, retry_after)
                self.assertEqual(attempt.text, "")

    def test_a_different_model_answering_is_not_an_answer(self):
        engine, _adapter = _gateway(_answer(model="glm-5.2"))
        attempt = engine.review(PROMPT, ALLOWANCE)
        self.assertEqual(attempt.outcome, reviewers.MODEL_IDENTITY_MISMATCH)

    def test_the_model_policy_refusal_is_honoured_before_any_provider_call(self):
        engine, adapter = _gateway(_answer(), installation_id="ollama.kimi-k3")
        availability = engine.availability()
        self.assertFalse(availability.available)
        self.assertEqual(availability.reason_code, reviewers.REFUSED_BY_ROUTE_POLICY)
        attempt = engine.review(PROMPT, ALLOWANCE)
        self.assertEqual(attempt.outcome, reviewers.REFUSED_BY_ROUTE_POLICY)
        self.assertEqual(attempt.physical_model_calls, 0)
        self.assertEqual(adapter.calls, [])

    def test_a_declared_allocation_above_the_model_capacity_is_unavailable(self):
        value = next(dict(item) for item in PANEL_RECORD["installations"] if item["installation_id"] == "ollama.glm-5.3")
        value["settings"] = dict(value["settings"], output_allocation_tokens=2_000_000)
        installation = config.ReviewerInstallation.from_dict(value, PANEL.families)
        engine = engines.build_reviewer(installation, PANEL.policy, reviewers.ReviewerContext(
            provider_adapters={"ollama_cloud": FakeAdapter(_answer())}, model_listing=LISTING))
        self.assertFalse(engine.availability().available)

    def test_the_declared_allocation_and_answer_format_reach_the_call(self):
        value = next(dict(item) for item in PANEL_RECORD["installations"] if item["installation_id"] == "ollama.glm-5.3")
        value["settings"] = dict(value["settings"], output_allocation_tokens=32768,
                                 answer_format="json_after_reasoning")
        installation = config.ReviewerInstallation.from_dict(value, PANEL.families)
        adapter = FakeAdapter(_answer())
        engine = engines.build_reviewer(installation, PANEL.policy, reviewers.ReviewerContext(
            provider_adapters={"ollama_cloud": adapter}, model_listing=LISTING))
        self.assertEqual((engine.output_allocation_tokens, engine.answer_format), (32768, "json_after_reasoning"))
        engine.review(PROMPT, reviewers.CallAllowance(32768, 30.0, 0.0))
        self.assertEqual(adapter.calls[0]["max_output_tokens"], 32768)

    def test_an_unknown_answer_format_is_refused_at_construction(self):
        value = next(dict(item) for item in PANEL_RECORD["installations"] if item["installation_id"] == "ollama.glm-5.3")
        value["settings"] = dict(value["settings"], answer_format="anything_goes")
        installation = config.ReviewerInstallation.from_dict(value, PANEL.families)
        with self.assertRaises(CandidateReviewError) as caught:
            engines.build_reviewer(installation, PANEL.policy, reviewers.ReviewerContext())
        self.assertEqual(caught.exception.code, "installation_setting_invalid")

    def test_a_model_the_provider_does_not_list_is_unavailable(self):
        engine, adapter = _gateway(_answer(), listing={})
        availability = engine.availability()
        self.assertFalse(availability.available)
        self.assertEqual(availability.reason_code, reviewers.ENGINE_UNAVAILABLE)
        self.assertEqual(adapter.calls, [])


def _program(folder: Path, name: str, body: str) -> Path:
    path = folder / name
    path.write_text("#!" + sys.executable + "\n" + textwrap.dedent(body), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _command(installation_id: str, program: Path, **overrides) -> reviewers.ReviewerEngine:
    value = next(dict(item) for item in PANEL_RECORD["installations"] if item["installation_id"] == installation_id)
    value["settings"] = dict(value["settings"], program=str(program), **overrides)
    installation = config.ReviewerInstallation.from_dict(value, PANEL.families)
    return engines.build_reviewer(installation, PANEL.policy, reviewers.ReviewerContext())


CODEX_SUCCESS = """
import json, os, pathlib, sys
if sys.argv[1:] == ["--version"]:
    print("codex-cli 0.0.1-fake"); sys.exit(0)
prompt = sys.stdin.read()
spy = pathlib.Path(os.environ.get("SPY_FILE", "/dev/null"))
workdir = sys.argv[sys.argv.index("-C") + 1]
if str(spy) != "/dev/null":
    spy.write_text(json.dumps({"argv": sys.argv[1:], "stdin": prompt, "cwd": os.getcwd(), "workdir": workdir,
                               "listing": sorted(os.listdir(workdir))}))
for event in ({"type": "thread.started", "thread_id": "t"}, {"type": "turn.started"},
              {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "the answer"}},
              {"type": "turn.completed", "usage": {"input_tokens": 20000, "cached_input_tokens": 15000,
               "cache_write_input_tokens": 0, "output_tokens": 300, "reasoning_output_tokens": 100}}):
    print(json.dumps(event))
"""


class CommandLineEngineTest(unittest.TestCase):
    """The Codex and Claude Code command lines, each read by its own output protocol."""

    def test_codex_usage_is_read_without_inventing_the_answering_model(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = _command("codex.gpt-6-sol", _program(Path(directory), "codex", CODEX_SUCCESS))
            availability = engine.availability()
            self.assertFalse(availability.available)
            self.assertEqual(availability.reason_code, reviewers.MODEL_IDENTITY_MISMATCH)
            self.assertEqual(availability.engine_version, "codex-cli 0.0.1-fake")
            attempt = engine.review(PROMPT, ALLOWANCE)
        self.assertEqual(attempt.outcome, reviewers.MODEL_IDENTITY_MISMATCH)
        self.assertEqual(attempt.text, "")
        self.assertEqual(attempt.reported_model, "")
        self.assertEqual(availability.model_version, {})
        self.assertEqual((attempt.usage.input_tokens, attempt.usage.output_tokens,
                          attempt.usage.reasoning_output_tokens, attempt.usage.cached_input_tokens),
                         (20000, 300, 100, 15000))
        self.assertEqual(attempt.usage.source, reviewers.COMMAND_LINE_REPORTED)
        self.assertEqual(attempt.physical_model_calls, 1)

    def test_the_prompt_travels_on_standard_input_into_an_empty_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            spy = Path(directory) / "spy.json"
            engine = _command("codex.gpt-6-sol", _program(Path(directory), "codex", CODEX_SUCCESS))
            import os
            previous = os.environ.get("SPY_FILE")
            os.environ["SPY_FILE"] = str(spy)
            try:
                engine.review(PROMPT, ALLOWANCE)
            finally:
                if previous is None:
                    os.environ.pop("SPY_FILE", None)
                else:
                    os.environ["SPY_FILE"] = previous
            seen = json.loads(spy.read_text())
        self.assertIn(PROMPT.user, seen["stdin"])
        self.assertIn(PROMPT.system, seen["stdin"])
        self.assertFalse(any(PROMPT.user in argument for argument in seen["argv"]))
        self.assertEqual(seen["listing"], [])
        self.assertEqual(seen["cwd"], seen["workdir"])
        self.assertIn("gpt-6-sol", seen["argv"])
        self.assertFalse(Path(seen["workdir"]).exists(), "the working folder is removed after the call")

    def test_codex_failures_keep_their_classes(self):
        cases = {
            "429 Too Many Requests: rate limit reached": reviewers.RATE_LIMITED,
            "You've hit your usage limit. Try again later.": reviewers.USAGE_LIMIT_REACHED,
            "401 Unauthorized: please log in": reviewers.AUTHENTICATION_UNAVAILABLE,
            "stream disconnected before completion": reviewers.PROVIDER_FAILED,
        }
        for message, outcome in cases.items():
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                program = _program(Path(directory), "codex", f"""
                    import json, sys
                    if sys.argv[1:] == ["--version"]:
                        print("codex-cli 0.0.1-fake"); sys.exit(0)
                    sys.stdin.read()
                    print(json.dumps({{"type": "thread.started", "thread_id": "t"}}))
                    print(json.dumps({{"type": "error", "message": {message!r}}}))
                    print(json.dumps({{"type": "turn.failed", "error": {{"message": {message!r}}}}}))
                    sys.exit(1)
                """)
                attempt = _command("codex.gpt-6-sol", program).review(PROMPT, ALLOWANCE)
                self.assertEqual(attempt.outcome, outcome)
                self.assertEqual(attempt.text, "")
                self.assertIsNone(attempt.usage.input_tokens)

    def test_a_command_that_runs_too_long_is_a_timeout_with_unknown_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            program = _program(Path(directory), "codex", """
                import sys, time
                if sys.argv[1:] == ["--version"]:
                    print("codex-cli 0.0.1-fake"); sys.exit(0)
                sys.stdin.read(); time.sleep(30)
            """)
            attempt = _command("codex.gpt-6-sol", program, timeout_seconds=1.0).review(
                PROMPT, reviewers.CallAllowance(ALLOWANCE.max_output_tokens, 1.0, ALLOWANCE.temperature))
        self.assertEqual(attempt.outcome, reviewers.TIMEOUT)
        self.assertIsNone(attempt.usage.input_tokens)
        self.assertIsNone(attempt.physical_model_calls, "a killed command may have called the model")

    def test_a_refused_login_is_no_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            program = _program(Path(directory), "claude", """
                import json, sys
                if sys.argv[1:] == ["--version"]:
                    print("2.0.0 (Claude Code)"); sys.exit(0)
                sys.stdin.read()
                print(json.dumps({"type": "result", "subtype": "success", "is_error": True,
                                  "result": "Not logged in \\u00b7 Please run /login", "duration_api_ms": 0,
                                  "usage": {"input_tokens": 0, "output_tokens": 0}, "modelUsage": {},
                                  "terminal_reason": "api_error"}))
                sys.exit(1)
            """)
            attempt = _command("claude_code.bare", program).review(PROMPT, ALLOWANCE)
        self.assertEqual(attempt.outcome, reviewers.AUTHENTICATION_UNAVAILABLE)
        self.assertEqual(attempt.physical_model_calls, 0)

    def test_claude_output_is_read_with_its_model_identity(self):
        answers = {"claude-opus-5-5": reviewers.ANSWERED, "claude-other-model": reviewers.MODEL_IDENTITY_MISMATCH}
        for reported, outcome in answers.items():
            with self.subTest(reported=reported), tempfile.TemporaryDirectory() as directory:
                program = _program(Path(directory), "claude", f"""
                    import json, sys
                    if sys.argv[1:] == ["--version"]:
                        print("2.0.0 (Claude Code)"); sys.exit(0)
                    sys.stdin.read()
                    print(json.dumps({{"type": "result", "subtype": "success", "is_error": False,
                                      "result": "the answer", "duration_api_ms": 900, "num_turns": 1,
                                      "usage": {{"input_tokens": 1000, "output_tokens": 200,
                                                "cache_read_input_tokens": 500, "cache_creation_input_tokens": 0}},
                                      "modelUsage": {{{reported!r}: {{"inputTokens": 1000}}}}}}))
                """)
                attempt = _command("claude_code.bare", program).review(PROMPT, ALLOWANCE)
                self.assertEqual(attempt.outcome, outcome)
                if outcome == reviewers.ANSWERED:
                    self.assertEqual(attempt.text, "the answer")
                    self.assertEqual((attempt.usage.input_tokens, attempt.usage.output_tokens), (1500, 200))
                    self.assertEqual(attempt.reported_model, "claude-opus-5-5")

    def test_a_missing_program_is_unavailable(self):
        engine = _command("codex.gpt-6-sol", Path("/nonexistent/codex"))
        availability = engine.availability()
        self.assertFalse(availability.available)
        self.assertEqual(availability.reason_code, reviewers.ENGINE_UNAVAILABLE)

    def test_an_unknown_placeholder_is_refused(self):
        value = next(dict(item) for item in PANEL_RECORD["installations"]
                     if item["installation_id"] == "codex.gpt-6-sol")
        value["settings"] = dict(value["settings"], arguments=["exec", "{prompt}"])
        installation = config.ReviewerInstallation.from_dict(value, PANEL.families)
        with self.assertRaises(CandidateReviewError) as caught:
            engines.build_reviewer(installation, PANEL.policy, reviewers.ReviewerContext())
        self.assertEqual(caught.exception.code, "installation_argument_unknown")

    def test_an_unknown_output_protocol_is_refused(self):
        value = next(dict(item) for item in PANEL_RECORD["installations"]
                     if item["installation_id"] == "codex.gpt-6-sol")
        value["settings"] = dict(value["settings"], output_protocol="plain_text")
        installation = config.ReviewerInstallation.from_dict(value, PANEL.families)
        with self.assertRaises(CandidateReviewError) as caught:
            engines.build_reviewer(installation, PANEL.policy, reviewers.ReviewerContext())
        self.assertEqual(caught.exception.code, "installation_output_protocol_unknown")


class FactoryTableTest(unittest.TestCase):
    """Only the factory table names concrete engine classes, and it covers every engine kind."""

    def test_every_engine_kind_has_one_factory(self):
        self.assertEqual(set(engines.REVIEWER_ENGINE_FACTORIES), set(config.ENGINE_KINDS))

    def test_every_committed_installation_builds(self):
        context = reviewers.ReviewerContext(provider_adapters={"ollama_cloud": FakeAdapter(_answer())},
                                            model_listing=LISTING)
        for installation in PANEL.installations:
            with self.subTest(installation=installation.installation_id):
                engine = engines.build_reviewer(installation, PANEL.policy, context)
                self.assertEqual(engine.installation, installation)


if __name__ == "__main__":
    unittest.main()
