"""One model call boundary for every model kind, in front of the text seam.

The engine's text seam takes a prompt and returns text. A model call is
wider than that: a step may hand a table to a tabular foundation model, an
image to a vision model, a series to a forecaster, or a passage to a small
classifier, and it wants a typed answer in a suggested shape. This module
owns the request that names the purpose, the model kind, the typed input
parts, the response contract, and the suggested output, and the record that
keeps what each call cost and returned. A text-servable request becomes the
existing text invocation through ``text_invocation``; any other kind is
refused with a typed reason until a route of that kind is declared, so no
image or table is ever pasted into a prompt by accident.

The request grants nothing. Authority, budgets, admission, and evaluation
stay with the session and the owning Loop. Records carry digests and counts,
never the prompt text, which the prompt assembly artifact already holds.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .facets import DETERMINISM
from .model_ontology import MODALITIES, MODEL_KINDS, TEXT_SERVABLE_KINDS
from .model_routes import PURPOSES
from .suggested_output import SuggestedOutput

RECORD_TYPE = "model_call_record/v1"


class ModelCallContractError(ValueError):
    """A model call request or record is invalid."""


class UnsupportedModelKind(ModelCallContractError):
    """The request needs a route kind the text seam cannot serve."""

    def __init__(self, kind: str, modalities: tuple[str, ...]):
        self.kind = kind
        self.modalities = modalities
        super().__init__(
            f"a {kind} call over {', '.join(modalities)} parts needs a declared {kind} "
            f"route; the text seam serves {', '.join(TEXT_SERVABLE_KINDS)} over text parts only")


def _digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModelInput:
    """One typed input part of a model call."""

    part_kind: str
    text: str = ""
    reference: str = ""
    digest: str = ""
    media_type: str = ""
    label: str = ""

    def __post_init__(self):
        if self.part_kind not in MODALITIES:
            raise ModelCallContractError(f"part kind must be one of {MODALITIES}")
        for name in ("text", "reference", "digest", "media_type", "label"):
            if not isinstance(getattr(self, name), str):
                raise ModelCallContractError(f"{name} must be text")
        if self.part_kind == MODALITIES[0]:
            if not self.text:
                raise ModelCallContractError("a text part carries its text")
        elif not (self.reference or self.digest):
            raise ModelCallContractError(f"a {self.part_kind} part carries a reference or a digest")

    @property
    def content_digest(self) -> str:
        return self.digest or (_digest_text(self.text) if self.text else "")

    def to_dict(self) -> dict:
        """The part without its raw text; the digest identifies the content."""
        return {"part_kind": self.part_kind, "digest": self.content_digest,
                "reference": self.reference, "media_type": self.media_type,
                "label": self.label, "characters": len(self.text)}


@dataclass(frozen=True)
class ModelCallRequest:
    """What one step asks of a model, independent of the model's kind."""

    purpose: str
    model_kind: str
    inputs: tuple[ModelInput, ...]
    system: str = ""
    response_contract_id: str = ""
    suggested_output: "SuggestedOutput | None" = None
    determinism_expectation: str = DETERMINISM[2]
    route_name: str = ""
    semantic_call_id: str = ""
    temperature: "float | None" = None

    def __post_init__(self):
        if self.purpose not in PURPOSES:
            raise ModelCallContractError(f"purpose must be one of {PURPOSES}")
        if self.model_kind not in MODEL_KINDS:
            raise ModelCallContractError(f"model kind must be one of {MODEL_KINDS}")
        inputs = tuple(self.inputs)
        if not inputs or any(not isinstance(item, ModelInput) for item in inputs):
            raise ModelCallContractError("a model call carries at least one typed ModelInput")
        if self.determinism_expectation not in DETERMINISM:
            raise ModelCallContractError(f"determinism expectation must be one of {DETERMINISM}")
        if self.suggested_output is not None and not isinstance(self.suggested_output, SuggestedOutput):
            raise ModelCallContractError("suggested_output must be a typed SuggestedOutput")
        for name in ("system", "response_contract_id", "route_name", "semantic_call_id"):
            if not isinstance(getattr(self, name), str):
                raise ModelCallContractError(f"{name} must be text")
        if self.temperature is not None and (
                type(self.temperature) not in (int, float) or not 0 <= self.temperature <= 2):
            raise ModelCallContractError("temperature must be empty or a number from 0 to 2")
        object.__setattr__(self, "inputs", inputs)

    @property
    def modalities(self) -> tuple[str, ...]:
        seen = []
        for item in self.inputs:
            if item.part_kind not in seen:
                seen.append(item.part_kind)
        return tuple(seen)

    @property
    def text_servable(self) -> bool:
        return self.model_kind in TEXT_SERVABLE_KINDS and self.modalities == (MODALITIES[0],)

    def to_dict(self) -> dict:
        return {"record_type": "model_call_request/v1", "purpose": self.purpose,
                "model_kind": self.model_kind, "inputs": [item.to_dict() for item in self.inputs],
                "system_digest": _digest_text(self.system) if self.system else "",
                "response_contract_id": self.response_contract_id,
                "suggested_output": (self.suggested_output.to_dict()
                                     if self.suggested_output is not None else None),
                "determinism_expectation": self.determinism_expectation,
                "route_name": self.route_name, "semantic_call_id": self.semantic_call_id,
                "temperature": self.temperature}

    @property
    def request_digest(self) -> str:
        return _digest_text(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")))

    def prompt_text(self) -> str:
        """The text parts joined in order, each under its label when it has one."""
        return "\n\n".join(f"[{item.label}]\n{item.text}" if item.label else item.text
                           for item in self.inputs if item.part_kind == MODALITIES[0])

    def system_text(self) -> str:
        """The system text with the suggested output instruction appended."""
        if self.suggested_output is None:
            return self.system
        instruction = self.suggested_output.to_instruction()
        return f"{self.system}\n\n{instruction}" if self.system else instruction

    def text_invocation(self, invocation_type, **extra):
        """Build the existing text invocation for a text-servable call.

        ``invocation_type`` is the session's request class; passing it keeps
        this boundary free of the seam's module. Any other kind or modality
        raises ``UnsupportedModelKind`` instead of flattening the parts.
        """
        if not self.text_servable:
            raise UnsupportedModelKind(self.model_kind, self.modalities)
        fields = {"prompt": self.prompt_text(), "system": self.system_text(),
                  "semantic_call_id": self.semantic_call_id}
        if self.temperature is not None:
            fields["temperature"] = self.temperature
        fields.update(extra)
        return invocation_type(**fields)


def _count_or_unknown(name: str, value):
    if value is not None and (type(value) is not int or value < 0):
        raise ModelCallContractError(f"{name} must be unknown or a non-negative integer")
    return value


@dataclass(frozen=True)
class ModelCallRecord:
    """What one model call was, cost, and returned; unknown counts stay unknown."""

    call_id: str
    request_digest: str
    purpose: str
    model_kind: str
    response_contract_id: str = ""
    suggested_output_digest: str = ""
    route: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    latency_ms: "int | None" = None
    output_digest: str = ""
    admitted: "bool | None" = None
    suggested_output_check: "dict | None" = field(default=None)
    outcome_label: str = ""

    def __post_init__(self):
        for name in ("call_id", "request_digest", "purpose", "model_kind"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ModelCallContractError(f"a model call record needs its {name}")
        if self.purpose not in PURPOSES or self.model_kind not in MODEL_KINDS:
            raise ModelCallContractError("a record names a registered purpose and model kind")
        for name in ("input_tokens", "output_tokens", "latency_ms"):
            _count_or_unknown(name, getattr(self, name))
        if self.admitted is not None and type(self.admitted) is not bool:
            raise ModelCallContractError("admitted must be unknown or a Boolean")
        if self.suggested_output_check is not None and not isinstance(self.suggested_output_check, dict):
            raise ModelCallContractError("a suggested output check is a mapping")

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "call_id": self.call_id,
                "request_digest": self.request_digest, "purpose": self.purpose,
                "model_kind": self.model_kind, "response_contract_id": self.response_contract_id,
                "suggested_output_digest": self.suggested_output_digest, "route": self.route,
                "provider": self.provider, "model": self.model,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "latency_ms": self.latency_ms, "output_digest": self.output_digest,
                "admitted": self.admitted, "suggested_output_check": self.suggested_output_check,
                "outcome_label": self.outcome_label}


@dataclass(frozen=True)
class ModelCallObservation:
    """What the session observed about one finished call; every field optional."""

    route: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    latency_ms: "int | None" = None
    output_text: str = ""
    admitted: "bool | None" = None
    admitted_value: object = None
    outcome_label: str = ""


def record_model_call(request: ModelCallRequest, call_id: str,
                      observation: "ModelCallObservation | None" = None) -> ModelCallRecord:
    """Build the record for one finished call from what the session observed.

    The suggested output is checked against the admitted value only when both
    exist; a deviation is recorded, never raised.
    """
    seen = observation if observation is not None else ModelCallObservation()
    if not isinstance(seen, ModelCallObservation):
        raise ModelCallContractError("a typed ModelCallObservation is required")
    check = None
    if request.suggested_output is not None and seen.admitted_value is not None:
        check = request.suggested_output.check(seen.admitted_value)
    return ModelCallRecord(
        call_id=call_id, request_digest=request.request_digest, purpose=request.purpose,
        model_kind=request.model_kind, response_contract_id=request.response_contract_id,
        suggested_output_digest=(request.suggested_output.content_digest
                                 if request.suggested_output is not None else ""),
        route=seen.route, provider=seen.provider, model=seen.model,
        input_tokens=seen.input_tokens, output_tokens=seen.output_tokens,
        latency_ms=seen.latency_ms,
        output_digest=_digest_text(seen.output_text) if seen.output_text else "",
        admitted=seen.admitted, suggested_output_check=check, outcome_label=seen.outcome_label)


def self_test() -> dict:
    """Typed parts, the text adapter, the typed refusal, and the call record."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action, error=ModelCallContractError):
        try:
            action()
        except Exception as exc:  # a refusal must be typed, not an accidental crash
            return isinstance(exc, error)
        return False

    @dataclass
    class FixtureInvocation:
        prompt: str
        system: str = ""
        temperature: float = 0.7
        semantic_call_id: str = ""

    suggestion = SuggestedOutput("ranked_list", columns=("candidate", "confidence"),
                                 cardinality=10, confidence_scale="percent")
    text_call = ModelCallRequest(
        PURPOSES[1], MODEL_KINDS[1],
        (ModelInput(MODALITIES[0], "Which file holds the invoice total?", label="question"),
         ModelInput(MODALITIES[0], "total.csv, notes.txt", label="files")),
        system="Answer from the listed files.", suggested_output=suggestion,
        semantic_call_id="call:1", response_contract_id="practitioner.route")
    invocation = text_call.text_invocation(FixtureInvocation)
    check("a_text_call_becomes_the_existing_invocation_with_labeled_parts",
          isinstance(invocation, FixtureInvocation)
          and invocation.prompt.startswith("[question]\nWhich file")
          and "[files]\ntotal.csv" in invocation.prompt and invocation.temperature == 0.7
          and invocation.semantic_call_id == "call:1")
    check("the_suggested_output_instruction_rides_in_the_system_text",
          invocation.system.startswith("Answer from the listed files.")
          and "Suggested output: a ranked list of at most 10 rows" in invocation.system)
    check("a_set_temperature_and_extra_fields_reach_the_invocation",
          ModelCallRequest(PURPOSES[1], MODEL_KINDS[0], text_call.inputs, temperature=0.2)
          .text_invocation(FixtureInvocation, semantic_call_id="call:2").temperature == 0.2
          and refuses(lambda: ModelCallRequest(PURPOSES[1], MODEL_KINDS[0], text_call.inputs,
                                               temperature=3)))
    vision_call = ModelCallRequest(
        PURPOSES[5], MODEL_KINDS[6],
        (ModelInput(MODALITIES[1], reference="materials/chart.png", media_type="image/png"),
         ModelInput(MODALITIES[0], "What does the chart show?")))
    refused = None
    try:
        vision_call.text_invocation(FixtureInvocation)
    except UnsupportedModelKind as exc:
        refused = exc
    check("a_non_text_kind_is_refused_with_its_kind_and_modalities",
          refused is not None and refused.kind == MODEL_KINDS[6]
          and refused.modalities == (MODALITIES[1], MODALITIES[0])
          and "declared vision route" in str(refused) and not vision_call.text_servable)
    check("an_embedding_call_over_text_still_needs_its_own_route",
          refuses(lambda: ModelCallRequest(PURPOSES[7], MODEL_KINDS[4], text_call.inputs[:1])
                  .text_invocation(FixtureInvocation), UnsupportedModelKind))
    check("parts_purposes_kinds_and_expectations_are_validated",
          all(refuses(action) for action in (
              lambda: ModelInput("thought", "x"),
              lambda: ModelInput(MODALITIES[0]),
              lambda: ModelInput(MODALITIES[2]),
              lambda: ModelCallRequest("guess", MODEL_KINDS[0], text_call.inputs),
              lambda: ModelCallRequest(PURPOSES[1], "oracle", text_call.inputs),
              lambda: ModelCallRequest(PURPOSES[1], MODEL_KINDS[0], ()),
              lambda: ModelCallRequest(PURPOSES[1], MODEL_KINDS[0], text_call.inputs,
                                       determinism_expectation="mostly"),
              lambda: ModelCallRequest(PURPOSES[1], MODEL_KINDS[0], text_call.inputs,
                                       suggested_output={"shape": "list"}))))
    record = record_model_call(text_call, "call:1", ModelCallObservation(
        route="cloud", provider="fixture", model="fixture-model", output_tokens=12,
        output_text="[]", admitted=True,
        admitted_value=[{"candidate": "total.csv", "confidence": 95}]))
    check("a_call_record_keeps_digests_counts_and_the_suggestion_check_without_text",
          record.input_tokens is None and record.output_tokens == 12
          and record.output_digest == _digest_text("[]")
          and record.suggested_output_check["conforms"] is True
          and record.suggested_output_digest == suggestion.content_digest
          and "prompt" not in json.dumps(record.to_dict())
          and "Which file" not in json.dumps(text_call.to_dict()))
    check("unknown_usage_stays_unknown_and_negative_counts_are_refused",
          record_model_call(text_call, "call:3").input_tokens is None
          and record_model_call(text_call, "call:3").suggested_output_check is None
          and refuses(lambda: record_model_call(text_call, "call:4",
                                                ModelCallObservation(input_tokens=-1)))
          and refuses(lambda: record_model_call(text_call, "call:4",
                                                ModelCallObservation(input_tokens=0.5)))
          and refuses(lambda: record_model_call(text_call, "call:4", {"route": "x"}))
          and refuses(lambda: record_model_call(text_call, "")))
    check("the_request_digest_is_stable_and_content_sensitive",
          text_call.request_digest == ModelCallRequest(
              PURPOSES[1], MODEL_KINDS[1], text_call.inputs, system="Answer from the listed files.",
              suggested_output=suggestion, semantic_call_id="call:1",
              response_contract_id="practitioner.route").request_digest
          and text_call.request_digest != vision_call.request_digest)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "model_call_contract_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
