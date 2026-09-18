"""The registry of response contracts a model step can name.

A response contract is the JSON shape one model step asks for. Until now each
step carried its shape as an inline literal, so two steps could drift apart,
no record could say which contract an answer belonged to, and a later
training pass could not group answers by contract. This registry gives each
contract an identifier and a version, renders the same JSON text the literal
produced, and can pair a contract with a suggested output. A contract's
enumerations come from the vocabularies that validate the answers, so the
prompt and the check cannot disagree.

Registering a contract grants nothing. The admission policy and the
evaluation contract still decide what is accepted.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .action_vector_assessment import (CONTINUATION_STATUSES, OUTPUT_CHECK_STATUSES,
                                       PROCESS_CHECK_STATUSES, PROGRESS_STATUSES)
from .adaptive_practitioner_validation import MODEL_ROUTE_VALUES
from .independent_evidence import ADMITTED_VERDICTS
from .suggested_output import SuggestedOutput

PRACTITIONER_ROUTE = "practitioner.route"
PRACTITIONER_VERIFY = "practitioner.verify"
INDEPENDENT_CRITERION_JUDGMENT = "independent.criterion_judgment"
INDEPENDENT_FAILURE_CONFIRMATION = "independent.failure_confirmation"
TEXT_CONFORMANCE_ESCALATION = "text_conformance.escalation_response"
STEP_EFFICIENCY_REVIEW = "practitioner.step_efficiency_review"
TYPED_DECISION = "typed_decision.choice"
#: The most candidates one typed decision may weigh; a wider choice is split.
TYPED_DECISION_MAX_CANDIDATES = 10
#: One operation from a declared vocabulary and one target row of an element
#: table in one answer; the table may be far wider than a plain choice.
TYPED_ACTION_DECISION = "typed_decision.action"

#: The evidence a failure review must quote; shared by its classification
#: and confirmation calls so both are grounded the same way.
FAILURE_REVIEW_EVIDENCE_CONTRACT = [
    "exact passage copied from the failed cases, probe source, or subject excerpts"]
CRITERION_JUDGMENT_EVIDENCE_CONTRACT = ["exact passage copied from observed_deliverable"]


class ResponseContractError(KeyError):
    """A contract identifier is not registered or a contract is invalid."""


@dataclass(frozen=True)
class ResponseContract:
    """One named, versioned JSON shape for a model step's answer."""

    contract_id: str
    version: str
    description: str
    schema: dict
    suggested_output: "SuggestedOutput | None" = None

    def __post_init__(self):
        for name in ("contract_id", "version", "description"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ResponseContractError(f"a response contract needs a nonempty {name}")
        if not isinstance(self.schema, dict) or not self.schema:
            raise ResponseContractError("a response contract schema is a nonempty mapping")
        if self.suggested_output is not None and not isinstance(self.suggested_output, SuggestedOutput):
            raise ResponseContractError("suggested_output must be a typed SuggestedOutput")

    def contract_json(self) -> str:
        """The schema as the compact JSON text a model step shows the model."""
        return json.dumps(self.schema, separators=(",", ":"))

    def schema_copy(self) -> dict:
        """A fresh copy for callers that embed the schema in their own packet."""
        return json.loads(self.contract_json())

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(self.contract_json().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {"record_type": "response_contract/v1", "contract_id": self.contract_id,
                "version": self.version, "description": self.description,
                "schema": self.schema_copy(), "content_digest": self.content_digest,
                "suggested_output": (self.suggested_output.to_dict()
                                     if self.suggested_output is not None else None)}


def _verify_schema() -> dict:
    return {
        "verdict": "|".join(ADMITTED_VERDICTS),
        "best_index": 0, "scores": [0.0], "notes": "string",
        "remaining_gaps": [{"criterion_ref": "criterion:0", "gap": "string"}],
        "advisory_findings": ["string"],
        "new_requirement_proposals": ["string"],
        "action_vector": {
            "process_checks": [{"check_id": "one registered process check",
                                "status": "|".join(PROCESS_CHECK_STATUSES),
                                "finding": "observable finding"}],
            "expected_output_status": "|".join(OUTPUT_CHECK_STATUSES),
            "expected_output_findings": ["string"],
            "requested_output_checks": [{"criterion_ref": "criterion:0",
                                         "status": "|".join(OUTPUT_CHECK_STATUSES),
                                         "finding": "string"}],
            "progress_status": "|".join(PROGRESS_STATUSES),
            "progress_evidence": ["string"],
            "continuation_status": "|".join(CONTINUATION_STATUSES),
            "remaining_work": ["string"],
        },
    }


_REGISTRY = {contract.contract_id: contract for contract in (
    ResponseContract(PRACTITIONER_ROUTE, "1.0.0",
                     "the route chosen after verification and the reason for it",
                     {"route": "|".join(MODEL_ROUTE_VALUES), "reason": "string"}),
    ResponseContract(PRACTITIONER_VERIFY, "1.0.0",
                     "the verdict on the results, remaining gaps, and the action vector",
                     _verify_schema()),
    ResponseContract(INDEPENDENT_CRITERION_JUDGMENT, "1.0.0",
                     "one judged criterion with quoted evidence",
                     {"satisfied": "boolean", "evidence": CRITERION_JUDGMENT_EVIDENCE_CONTRACT,
                      "reason": "string"}),
    ResponseContract(INDEPENDENT_FAILURE_CONFIRMATION, "1.0.0",
                     "confirmation of a claimed check defect with quoted evidence",
                     {"confirmed": "boolean", "evidence": FAILURE_REVIEW_EVIDENCE_CONTRACT,
                      "reason": "string"}),
    ResponseContract(TEXT_CONFORMANCE_ESCALATION, "1.0.0",
                     "ranked normal forms for one low-confidence cell, or an abstention",
                     {"rows": [{"candidate": "string", "confidence": 0, "reason": "string"}],
                      "abstain": "boolean"},
                     SuggestedOutput("ranked_list", columns=("candidate", "confidence"),
                                     cardinality=3, confidence_scale="unit_interval",
                                     abstention_allowed=True, path="rows",
                                     notes="Best first; abstain when no candidate is defensible.")),
    ResponseContract(STEP_EFFICIENCY_REVIEW, "1.0.0",
                     "ranked alternative ways to perform one step, each with a confidence",
                     {"rows": [{"alternative": "string", "confidence": 0, "reason": "string"}],
                      "inputs_too_big": "boolean", "outputs_too_big": "boolean",
                      "chosen_index": 0},
                     SuggestedOutput("ranked_list", columns=("alternative", "confidence"),
                                     cardinality=5, confidence_scale="unit_interval",
                                     abstention_allowed=False, path="rows",
                                     notes="Name the chosen row with chosen_index.")),
    ResponseContract(TYPED_DECISION, "1.0.0",
                     "one chosen candidate from a declared set, a probability per candidate, "
                     "a confidence, and an abstention flag",
                     {"chosen": "string",
                      "rows": [{"candidate": "string", "confidence": 0.0}],
                      "confidence": 0.0, "abstain": "boolean", "reason": "string"},
                     SuggestedOutput("ranked_list", columns=("candidate", "confidence"),
                                     cardinality=TYPED_DECISION_MAX_CANDIDATES,
                                     confidence_scale="unit_interval",
                                     abstention_allowed=True, path="rows",
                                     notes="One row per declared candidate whose confidence is "
                                           "the probability mass given to it; rows sum to one; "
                                           "abstain when no candidate is defensible.")),
    ResponseContract(TYPED_ACTION_DECISION, "1.0.0",
                     "one operation from the declared vocabulary and one target row of the element "
                     "table, each with a confidence, plus text when the operation types it",
                     {"operation": "string", "target_index": 0, "operation_confidence": 0.0,
                      "target_confidence": 0.0, "text": "string", "abstain": "boolean",
                      "reason": "string"},
                     SuggestedOutput("object", abstention_allowed=True,
                                     notes="Name one declared operation and, when it needs one, "
                                           "the index of one table row; abstain when no action "
                                           "is defensible.")),
)}


def registered_contract(contract_id: str) -> ResponseContract:
    """The registered contract, or a typed error naming the unknown identifier."""
    try:
        return _REGISTRY[contract_id]
    except KeyError:
        raise ResponseContractError(f"no response contract is registered as {contract_id!r}") from None


def contract_ids() -> tuple[str, ...]:
    return tuple(_REGISTRY)


def registry_records() -> list[dict]:
    """Every contract as a record, for reports and the contracts index."""
    return [contract.to_dict() for contract in _REGISTRY.values()]


def self_test() -> dict:
    """Registered identities, byte-stable JSON, vocabulary-bound enumerations."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ResponseContractError:
            return True
        return False

    route = registered_contract(PRACTITIONER_ROUTE)
    check("the_route_contract_renders_the_same_text_as_the_former_literal",
          route.contract_json() == json.dumps(
              {"route": "|".join(MODEL_ROUTE_VALUES), "reason": "string"}, separators=(",", ":")))
    verify = registered_contract(PRACTITIONER_VERIFY)
    rendered = json.loads(verify.contract_json())
    check("the_verify_contract_keeps_its_key_order_and_vocabularies",
          list(rendered) == ["verdict", "best_index", "scores", "notes", "remaining_gaps",
                             "advisory_findings", "new_requirement_proposals", "action_vector"]
          and rendered["verdict"].split("|") == list(ADMITTED_VERDICTS)
          and rendered["action_vector"]["continuation_status"].split("|") == list(CONTINUATION_STATUSES)
          and rendered["action_vector"]["process_checks"][0]["status"].split("|")
          == list(PROCESS_CHECK_STATUSES))
    check("every_contract_has_a_unique_id_a_version_and_a_stable_digest",
          len(set(contract_ids())) == len(contract_ids()) == 8
          and all(record["version"].count(".") == 2 for record in registry_records())
          and verify.content_digest == registered_contract(PRACTITIONER_VERIFY).content_digest)
    judgment = registered_contract(INDEPENDENT_CRITERION_JUDGMENT)
    copy = judgment.schema_copy()
    copy["evidence"].append("tampered")
    check("a_schema_copy_never_changes_the_registered_contract",
          judgment.schema["evidence"] == CRITERION_JUDGMENT_EVIDENCE_CONTRACT
          and registered_contract(INDEPENDENT_FAILURE_CONFIRMATION).schema["evidence"]
          == FAILURE_REVIEW_EVIDENCE_CONTRACT)
    check("an_unknown_contract_is_refused_by_name",
          refuses(lambda: registered_contract("practitioner.guess"))
          and refuses(lambda: ResponseContract("x", "1.0.0", "d", {}))
          and refuses(lambda: ResponseContract("x", "", "d", {"a": 1}))
          and refuses(lambda: ResponseContract("x", "1.0.0", "d", {"a": 1},
                                               suggested_output={"shape": "list"})))
    suggested = ResponseContract("fixture.ranked", "1.0.0", "fixture",
                                 {"rows": [{"candidate": "string", "confidence": 0}]},
                                 SuggestedOutput("ranked_list", columns=("candidate", "confidence"),
                                                 cardinality=10, confidence_scale="percent"))
    check("a_contract_may_carry_its_suggested_output_in_its_record",
          suggested.to_dict()["suggested_output"]["cardinality"] == 10
          and route.to_dict()["suggested_output"] is None)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "response_contracts_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
