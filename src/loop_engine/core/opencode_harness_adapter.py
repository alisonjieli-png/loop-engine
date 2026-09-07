"""OpenCode event normalization with raw host execution quarantined.

The canonical ``Loop`` and external-harness contract retain ownership of the
goal, authority, intelligence, budgets, and result. The old process path used
``--auto``, inherited ambient credentials and configuration, placed the prompt
in process arguments, treated a working directory as isolation, and recorded
raw NDJSON. Those mechanics cannot satisfy the typed execution requirements.

This module still renders a bounded work packet and normalizes saved offline
OpenCode events. ``OpenCodeProcessAdapter`` is a refusal-only compatibility
adapter until a separately reviewed execution profile can prove configuration,
credential, prompt, tool, context, effect, cancellation, and limit controls.

Owns:
    - OpenCodeProcessAdapter: quarantined ExternalHarnessAdapter compatibility.
    - parse_opencode_events(): the deterministic event normalization.
    - render_opencode_message(): the packet-to-message rendering.

Does not own: the harness result contract (core.external_harness), the Loop
that wraps the run (core.external_harness.run_external_harness), or the
instruction text (strings.prompt_fragments).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .external_harness import (
    HarnessAdapterInfo,
    HarnessError,
    HarnessModelCall,
    HarnessRunRequest,
    HarnessRunResult,
    HarnessServices,
    HarnessToolEvent,
)
from .harness_execution_contracts import (
    HarnessExecutionCapabilities,
    plain_harness_json,
    unmet_harness_requirements,
)

OPENCODE_HARNESS_ID = "opencode"
ADAPTER_VERSION = "1.1.0"
_UNQUALIFIED_REASON = "OpenCode host process execution profile is not qualified"
_CAPABILITY_EVIDENCE = (
    "https://dev.opencode.ai/docs/cli/",
    "https://opencode.ai/docs/permissions",
    "https://opencode.ai/v2/docs/config",
)
#: OpenCode tool names mapped to the LoopContract effect vocabulary.
_TOOL_EFFECTS = {
    "write": "writes_fs", "edit": "writes_fs", "patch": "writes_fs",
    "bash": "spawns_process", "task": "spawns_process",
    "read": "reads_fs", "glob": "reads_fs", "grep": "reads_fs",
    "list": "reads_fs", "webfetch": "network", "websearch": "network",
    "todowrite": "pure", "todoread": "pure",
}


class OpenCodeAdapterError(HarnessError):
    """The adapter could not honor the request as declared."""


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_opencode_message(request: HarnessRunRequest) -> str:
    """Compose the message: default instructions, goal, contract, inputs."""
    from ..strings.prompt_fragments import external_harness_instruction_bundle
    instructions = external_harness_instruction_bundle(
        OPENCODE_HARNESS_ID).render({}, provenance={})
    instruction_text = getattr(instructions, "text", None) or str(instructions)
    contract = request.contract
    lines = [
        instruction_text.strip(),
        "",
        f"Task: {request.goal.strip()}",
        f"Input roles: {', '.join(contract.input_roles) or 'none'}.",
        f"Output roles: {', '.join(contract.output_roles) or 'result'}.",
    ]
    if request.input_data:
        lines.append("Inputs (JSON): " + json.dumps(
            plain_harness_json(request.input_data), sort_keys=True,
            ensure_ascii=False, allow_nan=False))
    return "\n".join(lines)


@dataclass(frozen=True)
class ParsedOpenCodeEvents:
    """Normalized view of one headless run's JSON event stream."""

    texts: tuple
    model_calls: tuple
    tool_events: tuple
    session_id: str
    event_count: int
    unmapped_types: tuple
    final_json: dict | None
    final_json_admission: dict | None = None


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_opencode_events(lines, *, provider_id: str, model_id: str,
                          admission_parent=None, admission_ledger=None
                          ) -> ParsedOpenCodeEvents:
    """Normalize raw ``opencode run --format json`` lines.

    A ``step_finish`` part is one physical model turn; its ``tokens`` object
    carries input, output, reasoning, and cache counts, and ``cost`` the
    provider-reported cost when known. ``text`` parts accumulate the model's
    visible output. The final nonempty text part may contain a complete bare
    or JSON-fenced object. Earlier objects cannot replace an invalid final
    answer. Tool parts become tool events with the effect class of
    the tool name and no bodies. Unknown event types are counted, never
    dropped silently.
    """
    texts, calls, tools, unmapped = [], [], [], {}
    session_id = ""
    count = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except ValueError:
            unmapped["unparsable_line"] = unmapped.get("unparsable_line", 0) + 1
            continue
        count += 1
        if not isinstance(event, dict):
            unmapped["non_object"] = unmapped.get("non_object", 0) + 1
            continue
        session_id = session_id or str(event.get("sessionID") or "")
        kind = str(event.get("type") or "")
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        if kind == "text":
            texts.append(str(part.get("text") or ""))
        elif kind == "step_finish":
            tokens = part.get("tokens") if isinstance(part.get("tokens"), dict) else {}
            cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
            input_tokens = _int(tokens.get("input"))
            if input_tokens is not None:
                input_tokens += (_int(cache.get("read")) or 0)
            output_tokens = _int(tokens.get("output"))
            if output_tokens is not None:
                output_tokens += (_int(tokens.get("reasoning")) or 0)
            cost = part.get("cost")
            calls.append(HarnessModelCall(
                provider_id, model_id, str(part.get("reason") or "") != "error",
                input_tokens=input_tokens, output_tokens=output_tokens,
                cost=float(cost) if isinstance(cost, (int, float)) else None,
                error_code="" if str(part.get("reason") or "") != "error"
                else "step_error"))
        elif kind in ("tool", "tool_use", "tool_result") or str(
                part.get("type") or "").startswith("tool"):
            name = str(part.get("tool") or part.get("name") or "tool")
            state = part.get("state") if isinstance(part.get("state"), dict) else {}
            payload = json.dumps(state.get("input", {}), sort_keys=True,
                                 default=str).encode("utf-8")
            tools.append(HarnessToolEvent(
                name, str(state.get("status") or kind),
                effect=_TOOL_EFFECTS.get(name, "unknown"),
                input_digest=_digest_bytes(payload)))
        elif kind in ("step_start", "session", "message", "reasoning"):
            continue
        else:
            unmapped[kind or "untyped"] = unmapped.get(kind or "untyped", 0) + 1
    from .model_response_admission import (
        ModelResponseAdmissionPolicy, ModelResponseAdmissionRequest,
        admit_model_response_as_loop)

    final_json, admission = None, None
    final_text = next((text for text in reversed(texts) if text.strip()), "")
    if final_text:
        request = ModelResponseAdmissionRequest(
            final_text, "opencode_final_object/v1",
            _digest_bytes(b'{"type":"object"}'), schema={"type": "object"},
            policy=ModelResponseAdmissionPolicy(allowed_strategies=(
                "strict_json", "json_markdown_fence_removed")))
        admitted = admit_model_response_as_loop(
            request, parent=admission_parent, ledger=admission_ledger)
        admission = admitted.to_dict()
        if admitted.admitted:
            final_json = admitted.value
    return ParsedOpenCodeEvents(
        tuple(texts), tuple(calls), tuple(tools), session_id, count,
        tuple(sorted(unmapped.items())), final_json, admission)


@dataclass
class OpenCodeProcessAdapter:
    """Refuse raw host execution until a governed profile is qualified."""

    # Constructor fields remain for import compatibility. They are never used
    # to discover a binary, select a model, or grant execution authority.
    binary: str = "opencode"
    auto_approve: bool = False
    listed_models: tuple | None = None
    version_timeout_seconds: float = 20.0
    _version: str = field(default="", init=False, repr=False)

    def info(self) -> HarnessAdapterInfo:
        """Return passive facts without starting or interrogating a process."""
        return HarnessAdapterInfo(
            harness_id=OPENCODE_HARNESS_ID, adapter_version=ADAPTER_VERSION,
            package_name="opencode", package_version="",
            features=("offline_event_normalization", "offline_message_rendering"),
            limitations=(
                "raw host process execution is quarantined",
                "a working directory is not a sandbox",
                "ambient configuration and credentials are not isolated",
                (
                    "tool, skill, context, effect, and preemptive budget "
                    "controls are not qualified"
                ),
            ),
            available=False,
            availability_reason=_UNQUALIFIED_REASON,
            execution_capabilities=HarnessExecutionCapabilities(
                supported_features=(), enforced_limits=(),
                isolation="cwd_only", evidence_refs=_CAPABILITY_EVIDENCE),
        )

    def run(self, request: HarnessRunRequest,
            services: HarnessServices) -> HarnessRunResult:
        """Return a fixed pre-execution refusal and disclose no request body."""
        del services
        info = self.info()
        base = {
            "request_id": request.request_id,
            "harness_id": OPENCODE_HARNESS_ID,
            "adapter_version": ADAPTER_VERSION,
            "provider_id": request.provider_id,
            "model_id": request.model_id,
        }
        missing = unmet_harness_requirements(
            request, info.execution_capabilities)
        if missing:
            return HarnessRunResult(
                status="refused",
                error_code="harness_capability_requirement_unsatisfied",
                error="requested harness mechanics are not supported",
                capability_evaluation={
                    "satisfied": False,
                    "missing": list(missing),
                    "execution_started": False,
                },
                **base,
            )
        return HarnessRunResult(
            status="refused",
            error_code="opencode_execution_profile_unqualified",
            error=_UNQUALIFIED_REASON,
            capability_evaluation={
                "satisfied": True,
                "missing": [],
                "execution_started": False,
            },
            **base,
        )


_FIXTURE_EVENTS = (
    (
        '{"type":"step_start","timestamp":1,"sessionID":"ses_fixture","part":'
        '{"id":"prt_1","messageID":"msg_1","sessionID":"ses_fixture",'
        '"type":"step-start"}}'
    ),
    (
        '{"type":"tool","timestamp":2,"sessionID":"ses_fixture","part":'
        '{"id":"prt_2","type":"tool","tool":"write","state":'
        '{"status":"completed","input":{"filePath":"tiny_math.py"}}}}'
    ),
    (
        '{"type":"text","timestamp":3,"sessionID":"ses_fixture","part":'
        '{"id":"prt_3","type":"text","text":"Done.\\n{\\"status\\": '
        '\\"ok\\", \\"summary\\": \\"implemented clamp\\", \\"files\\": '
        '[\\"tiny_math.py\\"]}"}}'
    ),
    (
        '{"type":"step_finish","timestamp":4,"sessionID":"ses_fixture",'
        '"part":{"id":"prt_4","reason":"stop","type":"step-finish",'
        '"tokens":{"input":120,"output":30,"reasoning":5,"cache":'
        '{"read":40,"write":0}},"cost":0.0012}}'
    ),
    '{"type":"mystery","timestamp":5,"sessionID":"ses_fixture","part":{}}',
)


def self_test() -> dict:
    """Prove offline normalization and pre-execution quarantine."""
    from dataclasses import replace
    from unittest.mock import patch

    from ..loop.loop_contract import LoopContract
    from .external_harness import HarnessBudget, run_external_harness
    from .harness_execution_contracts import HarnessExecutionRequirements

    parsed = parse_opencode_events(
        _FIXTURE_EVENTS, provider_id="ollama-cloud", model_id="deepseek-v4-flash")
    call = parsed.model_calls[0]
    contract = LoopContract(
        name="implement clamp", execution_mode="model_led",
        input_roles=("repository",), output_roles=("changed_files",),
        effects=("writes_fs", "spawns_process"), role="solution")
    request = HarnessRunRequest(
        "req-1", OPENCODE_HARNESS_ID, "Implement clamp so the tests pass.",
        contract, HarnessBudget(max_model_calls=4, max_seconds=60),
        provider_id="ollama-cloud", model_id="deepseek-v4-flash",
        input_data={"tests": "test_tiny_math.py"}, workspace_ref="/nonexistent",
        authorize_model_calls=True)
    message = render_opencode_message(request)
    nested_message = render_opencode_message(replace(
        request, input_data={"nested": {"a": 1},
                             "sequence": [{"b": 2}]}))
    nested_payload = json.loads(nested_message.split("Inputs (JSON): ", 1)[1])
    private_marker = "PRIVATE_OPENCODE_PROCESS_MARKER"
    adapter = OpenCodeProcessAdapter(
        binary=private_marker, auto_approve=True,
        listed_models=(private_marker,))
    with patch("subprocess.run") as process_run, patch(
            "subprocess.Popen") as process_open:
        info = adapter.info()
        effect_refusal = adapter.run(request, HarnessServices())
        product_refusal = run_external_harness(adapter, request)
        explicit = replace(
            request,
            goal=private_marker,
            contract=LoopContract(
                name="pure fixture", execution_mode="model_led",
                output_roles=("answer",), role="solution"),
            context_refs=("context.fixture",),
            tool_refs=("tool.fixture",),
            skill_refs=("skill.fixture",),
            context_visibility="shared_runtime_memory",
            approval_policy_ref="approval.fixture",
            execution_requirements=HarnessExecutionRequirements(
                required_features=(
                    "configuration_isolation", "credential_isolation",
                    "private_prompt_channel", "private_raw_events",
                    "process_tree_cancellation"),
                required_limits=("model_calls", "total_tokens", "cost",
                                 "wall_time", "maximum_output"),
                allowed_isolations=("os_sandbox", "container"),
            ),
        )
        explicit_refusal = adapter.run(explicit, HarnessServices())
        pure_refusal = adapter.run(replace(
            explicit, context_refs=(), tool_refs=(), skill_refs=(),
            context_visibility="selected_refs", approval_policy_ref="",
            workspace_ref="",
            execution_requirements=HarnessExecutionRequirements()),
            HarnessServices())
    tests = [{
        "test": "step_finish_becomes_one_model_call_with_tokens_cost_and_cache_reads",
        "passed": (len(parsed.model_calls) == 1 and call.ok
                   and call.input_tokens == 160 and call.output_tokens == 35
                   and call.cost == 0.0012 and parsed.session_id == "ses_fixture"),
        "detail": f"in={call.input_tokens} out={call.output_tokens}",
    }, {
        "test": "tool_parts_become_effect_typed_events_and_unknown_types_are_counted",
        "passed": (len(parsed.tool_events) == 1
                   and parsed.tool_events[0].tool_name == "write"
                   and parsed.tool_events[0].effect == "writes_fs"
                   and parsed.tool_events[0].status == "completed"
                   and parsed.unmapped_types == (("mystery", 1),)
                   and parsed.event_count == 5),
        "detail": str(parsed.unmapped_types),
    }, {
        "test": "prose_wrapped_object_is_not_guessed_from_its_last_line",
        "passed": parsed.final_json is None,
        "detail": "Only a complete bare or JSON-fenced final object is admitted.",
    }, {
        "test": "message_carries_default_instructions_goal_contract_and_inputs",
        "passed": ("bounded coding task" in message and "Task: Implement clamp"
                   in message and "Output roles: changed_files" in message
                   and '"tests": "test_tiny_math.py"' in message
                   and "Do not claim verification" in message),
        "detail": message[:120],
    }, {
        "test": "nested_frozen_inputs_render_as_json_objects_not_strings",
        "passed": (nested_payload["nested"] == {"a": 1}
                   and nested_payload["sequence"] == [{"b": 2}]),
        "detail": str(nested_payload),
    }, {
        "test": "adapter_information_is_passive_and_execution_is_quarantined",
        "passed": (not info.available
                   and info.availability_reason == _UNQUALIFIED_REASON
                   and info.execution_capabilities is not None
                   and info.execution_capabilities.supported_features == ()
                   and info.execution_capabilities.enforced_limits == ()
                   and info.execution_capabilities.isolation == "cwd_only"
                   and not process_run.called and not process_open.called),
        "detail": info.availability_reason,
    }, {
        "test": "effectful_contract_is_refused_before_execution",
        "passed": (effect_refusal.status == "refused"
                   and effect_refusal.error_code
                   == "harness_capability_requirement_unsatisfied"
                   and effect_refusal.capability_evaluation.get(
                       "execution_started") is False
                   and effect_refusal.capability_evaluation.get("missing")
                   == ["feature:filesystem_effects", "feature:process_effects",
                       "feature:workspace_binding"]),
        "detail": str(effect_refusal.capability_evaluation),
    }, {
        "test": "product_path_checks_capabilities_before_availability",
        "passed": (product_refusal.status == "refused"
                   and product_refusal.error_code
                   == "harness_capability_requirement_unsatisfied"
                   and product_refusal.capability_evaluation
                   == effect_refusal.capability_evaluation
                   and not process_run.called and not process_open.called),
        "detail": str(product_refusal.capability_evaluation),
    }, {
        "test": "all_explicit_mechanics_and_preemptive_limits_fail_closed",
        "passed": (explicit_refusal.status == "refused"
                   and explicit_refusal.error_code
                   == "harness_capability_requirement_unsatisfied"
                   and "feature:context_refs" in explicit_refusal.capability_evaluation["missing"]
                   and "feature:tool_refs" in explicit_refusal.capability_evaluation["missing"]
                   and "feature:skill_refs" in explicit_refusal.capability_evaluation["missing"]
                   and "feature:configuration_isolation"
                   in explicit_refusal.capability_evaluation["missing"]
                   and "preemptive_limit:model_calls"
                   in explicit_refusal.capability_evaluation["missing"]
                   and "isolation" in explicit_refusal.capability_evaluation["missing"]),
        "detail": str(explicit_refusal.capability_evaluation),
    }, {
        "test": "even_a_pure_empty_request_needs_a_qualified_process_profile",
        "passed": (pure_refusal.status == "refused"
                   and pure_refusal.error_code
                   == "opencode_execution_profile_unqualified"
                   and pure_refusal.capability_evaluation
                   == {"satisfied": True, "missing": [],
                       "execution_started": False}),
        "detail": pure_refusal.error_code,
    }, {
        "test": "refusals_disclose_no_private_constructor_or_request_values",
        "passed": (private_marker not in json.dumps(info.__dict__, default=str)
                   and private_marker not in json.dumps(
                       effect_refusal.safe_summary(), default=str)
                   and private_marker not in json.dumps(
                       explicit_refusal.safe_summary(), default=str)
                   and private_marker not in json.dumps(
                       product_refusal.safe_summary(), default=str)
                   and not effect_refusal.raw_events_ref
                   and not explicit_refusal.raw_events_ref),
        "detail": "fixed diagnostics only",
    }]
    good_outputs = (
        ('{"value":3}', "strict_json"),
        ('{\n  "value": 3\n}', "strict_json"),
        ('```json\n{"value":3}\n```', "json_markdown_fence_removed"),
        ('```JSON\r\n{\r\n"value":3\r\n}\r\n```', "json_markdown_fence_removed"),
        ('```\n{"value":3}\n```', "json_markdown_fence_removed"),
    )
    for index, (body, strategy) in enumerate(good_outputs):
        observed = parse_opencode_events((json.dumps({"type": "text", "part": {"text": body}}),),
            provider_id="fixture", model_id="fixture")
        tests.append({"test": f"complete_final_object_envelope_{index}",
            "passed": observed.final_json == {"value": 3}
            and observed.texts == (body,)
            and observed.final_json_admission["strategy"] == strategy
            and observed.final_json_admission["model_calls"] == 0,
            "detail": "Exact envelope recovery only; raw text and admission identity retained."})
    invalid_outputs = (
        '{"value":3}\nUnverified commentary.',
        '{"value":3}\n{"value":4}',
        '```json\n{"value":3}\n```\n```json\n{"value":4}\n```',
        '```json\n{"value":3', '[]', 'null', '{"value":NaN}',
        '{"value":3,"value":4}', '```json\n{"value":3,"value":4}\n```',
    )
    for index, body in enumerate(invalid_outputs):
        observed = parse_opencode_events((json.dumps({"type": "text", "part": {"text": text}})
            for text in ('{"old_result":true}', body)), provider_id="fixture", model_id="fixture")
        tests.append({"test": f"invalid_final_object_cannot_reuse_prior_answer_{index}",
            "passed": observed.final_json is None,
            "detail": "Malformed, ambiguous, nonfinite, or duplicate-key final output is not admitted."})
    return {"module": "core.opencode_harness_adapter",
            "passed": all(item["passed"] for item in tests), "tests": tests}
