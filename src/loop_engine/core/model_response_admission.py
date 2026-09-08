"""Typed admission and deterministic repair of untrusted model responses.

This component sits after ModelGateway transport and before any semantic
consumer. It may remove only approved non-semantic envelopes, parse JSON,
validate an optional JSON Schema, and return a typed candidate disposition.
It never invents keys, changes values, grants authority, or commits effects.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from typing import Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome


_NORMALIZATION_STRATEGIES = (
    "strict_json", "json_markdown_fence_removed",
    "approved_json_preamble_removed", "double_encoded_json_unwrapped")
_APPROVED_PREAMBLE = re.compile(
    r"\s*(?:here\s+it\s+is|here\s+is\s+the\s+(?:requested\s+)?json|"
    r"here's\s+the\s+(?:requested\s+)?json|json\s+response|response)\s*:\s*"
    r"(?P<body>\{.*\})\s*", flags=re.IGNORECASE | re.DOTALL)
_JSON_FENCE = re.compile(
    r"\s*```(?:json)?\s*\n?(?P<body>.*?)\n?```\s*",
    flags=re.IGNORECASE | re.DOTALL)
#: Reported when the JSON decoder exhausts the interpreter stack on a deeply
#: nested candidate. It is a refusal of that text, never a run abort.
_NESTING_DEPTH_MESSAGE = "Nesting depth exceeded"
#: Deep nesting was refused only because the decoder ran out of stack, which
#: makes the refusal a property of the interpreter rather than of this
#: boundary: CPython 3.10 raises at about 1,000 levels and 3.12 and 3.14 parse
#: far deeper, so the same response was refused on one CI leg and admitted on
#: another. The boundary declares its own limit instead. Nothing a model is
#: asked to return here is nested anywhere near this deep.
MAXIMUM_NESTING_DEPTH = 200
_JSON_DECODER_MESSAGES = frozenset((
    _NESTING_DEPTH_MESSAGE,
    "Expecting value", "Extra data",
    "Expecting property name enclosed in double quotes",
    "Expecting ':' delimiter", "Expecting ',' delimiter",
    "Illegal trailing comma before end of object",
    "Illegal trailing comma before end of array",
    "Unterminated string starting at", "Invalid \\escape",
    "Invalid control character at", "Invalid \\uXXXX escape",
    "Unexpected UTF-8 BOM (decode using utf-8-sig)",
    "JSON syntax error",
))


@dataclass(frozen=True)
class ResponseJSONSyntaxDiagnostic:
    """Content-free parse facts about one approved normalization candidate.

    Offsets count characters in that candidate, not bytes in the raw response.
    Root hints describe its first non-whitespace character, not valid syntax.
    """

    strategy: str
    syntax_valid: bool
    decoder_message: str
    position: int | None
    line: int | None
    column: int | None
    candidate_char_count: int
    candidate_byte_count: int | None
    root_hint: str

    def __post_init__(self) -> None:
        if (self.strategy not in _NORMALIZATION_STRATEGIES
                or type(self.syntax_valid) is not bool
                or self.root_hint not in (
                    "object", "array", "string", "number", "boolean",
                    "null", "empty", "unknown")
                or self.decoder_message not in _JSON_DECODER_MESSAGES | {""}):
            raise ValueError("JSON syntax diagnostic classification is invalid")
        counts = (self.candidate_char_count, self.candidate_byte_count)
        if (type(counts[0]) is not int or any(
                value is not None and (type(value) is not int or value < 0)
                for value in counts)):
            raise ValueError("JSON syntax diagnostic counts are invalid")
        locations = (self.position, self.line, self.column)
        if self.syntax_valid:
            valid = not self.decoder_message and all(v is None for v in locations)
        else:
            valid = (bool(self.decoder_message)
                     and all(type(v) is int for v in locations)
                     and 0 <= self.position <= self.candidate_char_count
                     and self.line >= 1 and self.column >= 1)
        if not valid:
            raise ValueError("JSON syntax diagnostic location is invalid")

    def to_dict(self) -> dict:
        return {
            "record_type": "response_json_syntax_diagnostic/v1",
            "strategy": self.strategy, "syntax_valid": self.syntax_valid,
            "decoder_message": self.decoder_message,
            "position": self.position, "line": self.line, "column": self.column,
            "candidate_char_count": self.candidate_char_count,
            "candidate_byte_count": self.candidate_byte_count,
            "root_hint": self.root_hint,
        }


def _syntax_diagnostic(strategy: str, candidate: str,
                       error: json.JSONDecodeError | RecursionError | None
                       ) -> ResponseJSONSyntaxDiagnostic:
    first = candidate.lstrip()[:1]
    root_hint = ({"{": "object", "[": "array", '"': "string",
                  "t": "boolean", "f": "boolean", "n": "null"}.get(first)
                 or ("empty" if not first else "number"
                     if first in "-0123456789" else "unknown"))
    try:
        byte_count = len(candidate.encode("utf-8"))
    except UnicodeEncodeError:
        # A decoded outer JSON string can contain an unpaired surrogate.
        # Reporting diagnostics must not introduce a new parse failure.
        byte_count = None
    if isinstance(error, RecursionError):
        # The decoder ran out of stack before it could judge the syntax. The
        # text is refused as unparseable from its root value, offset zero.
        return ResponseJSONSyntaxDiagnostic(
            strategy=strategy, syntax_valid=False,
            decoder_message=_NESTING_DEPTH_MESSAGE, position=0, line=1,
            column=1, candidate_char_count=len(candidate),
            candidate_byte_count=byte_count, root_hint=root_hint)
    message = (error.msg if error is not None
               and error.msg in _JSON_DECODER_MESSAGES else "JSON syntax error")
    return ResponseJSONSyntaxDiagnostic(
        strategy=strategy, syntax_valid=error is None,
        decoder_message=message if error is not None else "",
        position=error.pos if error is not None else None,
        line=error.lineno if error is not None else None,
        column=error.colno if error is not None else None,
        candidate_char_count=len(candidate), candidate_byte_count=byte_count,
        root_hint=root_hint)


class ModelResponseRepairStalled(RuntimeError):
    """A response repair cycle repeated without semantic progress."""


@dataclass(frozen=True)
class ModelResponseAdmissionPolicy:
    """Allowed meaning-preserving normalization strategies."""

    allowed_strategies: tuple[str, ...] = _NORMALIZATION_STRATEGIES
    expected_root_type: str = "object"

    def __post_init__(self) -> None:
        strategies = tuple(self.allowed_strategies)
        if (not strategies or len(strategies) != len(set(strategies))
                or any(item not in _NORMALIZATION_STRATEGIES
                       for item in strategies)):
            raise ValueError("response admission strategies are invalid")
        if self.expected_root_type != "object":
            raise ValueError("version 1 response admission expects an object")
        object.__setattr__(self, "allowed_strategies", strategies)


@dataclass(frozen=True)
class ModelResponseAdmissionRequest:
    """Raw provider text plus its exact expected response contract."""

    raw_text: str = field(repr=False, compare=False)
    contract_ref: str
    contract_digest: str
    schema: Mapping[str, object] | None = field(
        default=None, repr=False, compare=False)
    policy: ModelResponseAdmissionPolicy = field(
        default_factory=ModelResponseAdmissionPolicy)

    def __post_init__(self) -> None:
        if not isinstance(self.raw_text, str):
            raise ValueError("raw model response must be text")
        if not self.contract_ref.strip() or len(self.contract_digest) != 64:
            raise ValueError("response admission contract identity is invalid")
        if self.schema is not None:
            try:
                Draft202012Validator.check_schema(dict(self.schema))
            except SchemaError:
                raise SchemaError("response admission schema is invalid") from None

    @property
    def raw_digest(self) -> str:
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModelResponseAdmissionResult:
    """Admitted object or a typed rejection with no raw text."""

    admitted: bool
    value: dict | None = field(default=None, repr=False, compare=False)
    strategy: str = "unparsed"
    failure_code: str = ""
    raw_digest: str = ""
    normalized_digest: str = ""
    schema_errors: tuple[str, ...] = ()
    transformation_trace: tuple[str, ...] = ()
    loop_id: str = ""
    model_calls: int = 0
    syntax_diagnostics: tuple[ResponseJSONSyntaxDiagnostic, ...] = ()

    def to_dict(self) -> dict:
        return {
            "record_type": "model_response_admission_result/v1",
            "admitted": self.admitted, "strategy": self.strategy,
            "failure_code": self.failure_code, "raw_digest": self.raw_digest,
            "normalized_digest": self.normalized_digest,
            "schema_errors": list(self.schema_errors),
            "transformation_trace": list(self.transformation_trace),
            "loop_id": self.loop_id, "model_calls": self.model_calls,
            "syntax_diagnostics": [item.to_dict()
                                   for item in self.syntax_diagnostics]}


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()


def _schema_error_category(error) -> str:
    """Keep the failed constraint, never candidate values or property names."""
    keyword = error.validator
    if keyword not in Draft202012Validator.VALIDATORS:
        keyword = "unknown"
    return "schema_constraint_failed:" + keyword


def _candidate_texts(request: ModelResponseAdmissionRequest):
    raw = request.raw_text
    allowed = set(request.policy.allowed_strategies)
    if "strict_json" in allowed:
        yield "strict_json", raw, ()
    if "json_markdown_fence_removed" in allowed:
        match = _JSON_FENCE.fullmatch(raw)
        if match is not None:
            yield ("json_markdown_fence_removed",
                   match.group("body").strip(),
                   ("removed_exact_markdown_json_fence",))
    if "approved_json_preamble_removed" in allowed:
        match = _APPROVED_PREAMBLE.fullmatch(raw)
        if match is not None:
            yield ("approved_json_preamble_removed",
                   match.group("body").strip(),
                   ("removed_approved_nonsemantic_json_preamble",))
    if "double_encoded_json_unwrapped" in allowed:
        try:
            outer = json.loads(raw)
        except (TypeError, json.JSONDecodeError, RecursionError):
            outer = None
        if isinstance(outer, str):
            yield ("double_encoded_json_unwrapped", outer,
                   ("unwrapped_one_json_string_layer",))


def _nesting_depth(text: str) -> int:
    """Maximum bracket nesting in a candidate, counted without decoding.

    Brackets inside string literals are not structure, so the scan tracks
    string state and backslash escapes. Cheap, total, and identical on
    every interpreter -- which is the whole point.
    """
    depth = 0
    deepest = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "{[":
            depth += 1
            if depth > deepest:
                deepest = depth
        elif character in "}]":
            depth -= 1
    return deepest


def _admit(request: ModelResponseAdmissionRequest) \
        -> ModelResponseAdmissionResult:
    saw_non_object = False
    diagnostics = []
    for strategy, candidate, trace in _candidate_texts(request):
        if _nesting_depth(candidate) > MAXIMUM_NESTING_DEPTH:
            # Refused by the declared limit, before the decoder is asked --
            # so the verdict is the same whether or not this interpreter
            # would have run out of stack.
            diagnostics.append(_syntax_diagnostic(
                strategy, candidate, RecursionError(_NESTING_DEPTH_MESSAGE)))
            continue
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, RecursionError) as exc:
            diagnostics.append(_syntax_diagnostic(strategy, candidate, exc))
            continue
        diagnostics.append(_syntax_diagnostic(strategy, candidate, None))
        if not isinstance(value, dict):
            saw_non_object = True
            continue
        # JSON syntax can be valid while duplicate keys make the value
        # ambiguous. Reuse the existing finite, unique-key record decoder;
        # this is a value check, not an invented syntax-error location.
        from .record_operations_records import RecordOperationError, parse_json
        try:
            value = parse_json(candidate)
        except (RecordOperationError, RecursionError):
            return ModelResponseAdmissionResult(
                False, None, strategy, "invalid_json_value", request.raw_digest,
                syntax_diagnostics=tuple(diagnostics))
        errors = ()
        if request.schema is not None:
            validator = Draft202012Validator(dict(request.schema))
            errors = tuple(sorted(
                _schema_error_category(error)
                for error in validator.iter_errors(value)))
        if errors:
            return ModelResponseAdmissionResult(
                False, None, strategy, "schema_validation_failed",
                request.raw_digest, _canonical_digest(value), errors, trace,
                syntax_diagnostics=tuple(diagnostics))
        return ModelResponseAdmissionResult(
            True, value, strategy, "", request.raw_digest,
            _canonical_digest(value), (), trace,
            syntax_diagnostics=tuple(diagnostics))
    return ModelResponseAdmissionResult(
        False, None, "unparsed",
        "root_not_object" if saw_non_object else "invalid_json",
        request.raw_digest, syntax_diagnostics=tuple(diagnostics))


def admit_model_response_as_loop(
        request: ModelResponseAdmissionRequest, *, parent=None, ledger=None
        ) -> ModelResponseAdmissionResult:
    """Admit one untrusted response through a deterministic component Loop."""
    if not isinstance(request, ModelResponseAdmissionRequest):
        raise TypeError("model response admission requires its typed request")
    config = LoopConfig(
        framework="custom", custom_steps=("admit",), power="light",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        exit_condition="accepted_success")
    identity = LoopRoleIdentity(LoopRole.SOLUTION, "solution.validator")
    relationship = (LoopRelationship.spawned_by(parent.loop_id)
                    if parent is not None else LoopRelationship.starting())
    loop = (parent.spawn(
        "admit one untrusted model response", config, identity=identity,
        relationship=relationship) if parent is not None else Loop(
            "admit one untrusted model response", config, ledger=ledger,
            identity=identity, relationship=relationship))
    holder = {}

    def handler(active, _step, _context):
        holder["value"] = _admit(request)
        admission_record = holder["value"].to_dict()
        admission_record.pop("loop_id", None)
        active.ledger.record(
            loop_id=active.loop_id, event="custom",
            custom_kind="model_response_admission",
            admission=admission_record)
        return StepOutcome(
            "response:admitted" if holder["value"].admitted
            else "response:rejected", "deterministic",
            1.0 if holder["value"].admitted else 0.0,
            failed=not holder["value"].admitted)

    run = loop.run(handler=handler, max_steps=2)
    value = holder.get("value")
    if not isinstance(value, ModelResponseAdmissionResult):
        raise TypeError("model response admission returned the wrong type")
    if run.model_calls != 0:
        raise RuntimeError("deterministic response admission called a model")
    return replace(value, loop_id=run.loop_id, model_calls=0)


def self_test() -> dict:
    """Exercise deterministic wrappers, schema rejection, and redaction."""
    digest = hashlib.sha256(b"contract").hexdigest()

    def admit(text, schema=None):
        return admit_model_response_as_loop(ModelResponseAdmissionRequest(
            text, "fixture.response/v1", digest, schema=schema))

    strict = admit('{"ok":true}')
    fenced = admit('```json\n{"ok":true}\n```')
    preamble = admit('Here is the JSON: {"ok":true}')
    doubled = admit(json.dumps('{"ok":true}'))
    prose = admit('Explanation before {"ok":true} after')
    schema = admit('{"ok":"yes"}', {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"], "additionalProperties": False})
    raw_safe = "Here is the JSON" not in json.dumps(preamble.to_dict())
    tests = [{
        "test": "approved_response_envelopes_are_repaired_deterministically",
        "passed": all(item.admitted for item in (
            strict, fenced, preamble, doubled))
        and [strict.strategy, fenced.strategy, preamble.strategy,
             doubled.strategy] == list(_NORMALIZATION_STRATEGIES),
        "detail": ", ".join(item.strategy for item in (
            strict, fenced, preamble, doubled)),
    }, {
        "test": "arbitrary_prose_and_schema_mismatch_are_rejected",
        "passed": (not prose.admitted and prose.failure_code == "invalid_json"
                   and not schema.admitted
                   and schema.failure_code == "schema_validation_failed"),
        "detail": f"{prose.failure_code}; {schema.failure_code}",
    }, {
        "test": "admission_records_digests_not_raw_model_text",
        "passed": raw_safe and len(preamble.raw_digest) == 64,
        "detail": preamble.raw_digest,
    }]
    tests.extend(_syntax_diagnostic_checks())
    tests.extend(_schema_diagnostic_checks())
    tests.extend(_nesting_depth_checks())
    for index, body in enumerate((
            '{"value":1,"value":2}', '{"nested":{"value":1,"value":2}}',
            '{"value":NaN}', '{"value":Infinity}', '{"value":1e999}',
            '```json\n{"value":1,"value":2}\n```',
            json.dumps('{"value":1,"value":2}'))):
        rejected = admit(body)
        tests.append({"test": f"ambiguous_or_nonfinite_object_{index}_refused",
            "passed": not rejected.admitted and rejected.failure_code == "invalid_json_value"
            and rejected.value is None and not rejected.normalized_digest,
            "detail": "Syntax validity does not admit ambiguous keys or nonfinite values."})
    tests.append(_format_repair_feedback_check())
    return {"record_type": "model_response_admission_test/v1",
            "tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def _nesting_depth_checks() -> list[dict]:
    """Nesting past the declared limit is a typed refusal on EVERY
    interpreter, and text within the limit still parses.

    The earlier form of this check drove 1,500 levels and relied on the
    decoder raising RecursionError. CPython 3.10 does; 3.12 and 3.14 do
    not, so the check failed on two of the three CI legs while the
    boundary itself was behaving reasonably. Asserting the declared limit
    tests the contract instead of the interpreter.
    """
    digest = hashlib.sha256(b"depth-contract").hexdigest()
    over = MAXIMUM_NESTING_DEPTH + 1
    deep_object = '{"a":' * over + "1" + "}" * over
    deep_array = "[" * over + "]" * over
    outcomes = {}
    for label, text in (("object", deep_object), ("array", deep_array),
                        ("double_encoded", json.dumps(deep_object))):
        try:
            result = admit_model_response_as_loop(ModelResponseAdmissionRequest(
                text, "fixture.response/v1", digest))
            outcomes[label] = (
                result.admitted is False
                and result.failure_code in (
                    "invalid_json", "invalid_json_value", "root_not_object")
                and any(item.decoder_message == _NESTING_DEPTH_MESSAGE
                        and item.syntax_valid is False
                        for item in result.syntax_diagnostics))
        except RecursionError:
            outcomes[label] = False
    # The limit must refuse deep text WITHOUT refusing ordinary replies: a
    # cap that rejected everything would pass the assertions above.
    under = MAXIMUM_NESTING_DEPTH - 1
    nested_but_legal = '{"a":' * under + "1" + "}" * under
    admitted = admit_model_response_as_loop(ModelResponseAdmissionRequest(
        nested_but_legal, "fixture.response/v1", digest))
    # A bracket inside a string is text, not structure, and must not count.
    bracketed = json.dumps({"note": "[" * 5000})
    string_ok = admit_model_response_as_loop(ModelResponseAdmissionRequest(
        bracketed, "fixture.response/v1", digest))
    return [{
        "test": "nesting_depth_beyond_the_declared_limit_is_a_typed_refusal",
        "passed": all(outcomes.values()),
        "detail": ", ".join(f"{label}={ok}" for label, ok in outcomes.items()),
    }, {
        "test": "nesting_within_the_declared_limit_is_still_admitted",
        "passed": admitted.admitted is True and string_ok.admitted is True,
        "detail": f"under-limit admitted={admitted.admitted}, "
                  f"brackets-in-a-string admitted={string_ok.admitted}",
    }]


def _syntax_diagnostic_checks() -> list[dict]:
    """Exercise syntax evidence without copying candidate text into records."""
    from ..loop.recursive_loop import LoopLedger

    secret = "PRIVATE_SYNTAX_MARKER"
    malformed = '{"value":"' + secret + '\u00e9",}'
    digest = hashlib.sha256(b"syntax-contract").hexdigest()

    def admit(raw, *, ledger=None):
        return admit_model_response_as_loop(ModelResponseAdmissionRequest(
            raw, "fixture.syntax/v1", digest), ledger=ledger)

    ledger = LoopLedger()
    rejected = admit(malformed, ledger=ledger)
    diagnostic = rejected.syntax_diagnostics[0]
    try:
        json.loads(malformed)
    except json.JSONDecodeError as exc:
        expected = (exc.msg, exc.pos, exc.lineno, exc.colno)
    fenced = admit("```json\n" + malformed + "\n```")
    doubled = admit(json.dumps(malformed))
    empty = admit("")
    valid = admit(json.dumps({"value": secret}))
    combined = admit('Here is the JSON: ```json\n{"ok":true}\n```')
    custom = _syntax_diagnostic(
        "strict_json", malformed, json.JSONDecodeError(secret, malformed, 0))
    rendered = json.dumps({
        "results": [item.to_dict() for item in (
            rejected, fenced, doubled, empty, valid, combined)],
        "ledger": ledger.events, "unknown_error": custom.to_dict(),
    })
    return [{
        "test": "json_syntax_diagnostics_preserve_exact_location_and_utf8_counts",
        "passed": (
            not rejected.admitted and rejected.failure_code == "invalid_json"
            and (diagnostic.decoder_message, diagnostic.position,
                 diagnostic.line, diagnostic.column) == expected
            and diagnostic.candidate_char_count == len(malformed)
            and diagnostic.candidate_byte_count == len(malformed.encode("utf-8"))
            and diagnostic.root_hint == "object"),
    }, {
        "test": "each_attempted_normalization_has_candidate_relative_diagnostics",
        "passed": (
            [item.strategy for item in fenced.syntax_diagnostics]
            == ["strict_json", "json_markdown_fence_removed"]
            and fenced.syntax_diagnostics[1].position == diagnostic.position
            and [item.syntax_valid for item in doubled.syntax_diagnostics]
            == [True, False]
            and doubled.failure_code == "root_not_object"),
    }, {
        "test": "syntax_reporting_keeps_admission_and_envelope_semantics",
        "passed": (
            valid.admitted and valid.value == {"value": secret}
            and valid.syntax_diagnostics[0].syntax_valid
            and valid.syntax_diagnostics[0].decoder_message == ""
            and empty.failure_code == "invalid_json"
            and empty.syntax_diagnostics[0].root_hint == "empty"
            and empty.syntax_diagnostics[0].candidate_char_count == 0
            and not combined.admitted
            and combined.failure_code == "invalid_json"),
    }, {
        "test": "syntax_evidence_and_ledger_do_not_leak_candidate_or_error_text",
        "passed": (
            secret not in rendered and malformed not in rendered
            and custom.decoder_message == "JSON syntax error"
            and any(item.get("admission", {}).get("syntax_diagnostics")
                    for item in ledger.events)),
    }]


def _format_repair_feedback_check() -> dict:
    """Prove actual adaptive packet assembly carries only safe parse facts."""
    from tempfile import TemporaryDirectory
    from unittest.mock import patch

    from . import adaptive_practitioner_records as records
    from .adaptive_practitioner_acceptance_checks import _run, _success_answers

    secret = "PRIVATE_FORMAT_REPAIR_MARKER"
    malformed = '{"value":"' + secret + '",}'
    assembled = []
    original_assemble = records.assemble_work_packet

    def capture(request, owner):
        result = original_assemble(request, owner)
        assembled.append((request.packet, result))
        return result

    with TemporaryDirectory(prefix="loop-syntax-feedback-") as directory, patch(
            "loop_engine.core.adaptive_practitioner_records.assemble_work_packet",
            side_effect=capture):
        result = _run("Create a verified result.",
                      (malformed, *_success_answers()), directory)
    first, repaired = assembled[:2]
    feedback = repaired[0].attempt_history.get("response_syntax_failure", {})
    snapshots = result.get("context_snapshots", ())
    return {
        "test": "adaptive_format_repair_receives_bound_private_safe_parse_feedback",
        "passed": (
            result.get("solved") is True and result.get("model_calls") == 8
            and feedback.get("response_digest")
            == hashlib.sha256(malformed.encode()).hexdigest()
            and feedback.get("failure_code") == "invalid_json"
            and feedback.get("syntax_diagnostics", [{}])[0].get("decoder_message")
            in ("Expecting property name enclosed in double quotes",
                "Illegal trailing comma before end of object")
            and '"response_syntax_failure"' in repaired[1].prompt
            and all(secret not in item.prompt for _, item in assembled)
            and first[0].content_digest != repaired[0].content_digest
            and repaired[1].snapshot.packet_digest == repaired[0].content_digest
            and len(snapshots) >= 2
            and snapshots[0]["packet_artifact_ref"]
            != snapshots[1]["packet_artifact_ref"]),
    }


def _schema_diagnostic_checks() -> list[dict]:
    """Keep schema failures actionable without leaking instance or schema data."""
    from ..loop.recursive_loop import LoopLedger

    secret = "PRIVATE_SCHEMA_MARKER"
    digest = hashlib.sha256(b"schema-contract").hexdigest()
    ledger = LoopLedger()
    cases = (
        ({"value": secret}, {"type": "object", "properties": {
            "value": {"type": "integer"}}}, "type"),
        ({}, {"type": "object", "required": [secret]}, "required"),
        ({secret: 1}, {"type": "object", "additionalProperties": False},
         "additionalProperties"),
    )
    results = [admit_model_response_as_loop(ModelResponseAdmissionRequest(
        json.dumps(value), "fixture.schema/v1", digest, schema=schema), ledger=ledger)
        for value, schema, _ in cases]
    schema_error = ""
    try:
        ModelResponseAdmissionRequest(
            "{}", "fixture.schema/v1", digest, schema={"type": secret})
    except SchemaError as exc:
        schema_error = str(exc)
    return [{
        "test": "schema_rejections_keep_fixed_constraint_categories",
        "passed": all(
            not result.admitted and result.failure_code == "schema_validation_failed"
            and result.schema_errors == ("schema_constraint_failed:" + category,)
            and result.syntax_diagnostics[0].syntax_valid
            for result, (_, _, category) in zip(results, cases)),
    }, {
        "test": "schema_diagnostics_and_ledger_redact_values_names_and_invalid_schema",
        "passed": (
            secret not in json.dumps([item.to_dict() for item in results])
            and secret not in json.dumps(ledger.events)
            and schema_error == "response admission schema is invalid"),
    }]


__all__ = (
    "ModelResponseAdmissionPolicy", "ModelResponseAdmissionRequest",
    "ModelResponseAdmissionResult", "ModelResponseRepairStalled",
    "ResponseJSONSyntaxDiagnostic",
    "admit_model_response_as_loop")
