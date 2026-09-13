"""Passive, versioned recovery policy for one brokered semantic step.

The existing harness boundary executes each attempt as a canonical Loop.
This module only classifies observations and selects an explicitly registered
alternative. It grants neither model authority nor permission to replay effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from .harness_execution_contracts import valid_harness_id


class HarnessFailureKind(str, Enum):
    UNAVAILABLE = "adapter_unavailable"
    INCOMPATIBLE = "harness_capability_requirement_unsatisfied"
    EXECUTION_FAILED = "adapter_reported_failure"
    RESPONSE_REJECTED = "output_validation_failed"
    SEMANTIC_REJECTED = "semantic_response_rejected"


@dataclass(frozen=True)
class HarnessFallbackPolicy:
    """Ordered, finite alternatives; the primary is the first identifier.

    Switching is opt-in by both exact adapter identity and failure category.
    Provider failover is a separate policy and is never implied by this one.
    """

    harness_ids: tuple[str, ...]
    switch_on: tuple[HarnessFailureKind, ...]
    version: str = "1.0.0"

    def __post_init__(self):
        if self.version != "1.0.0":
            raise ValueError("unsupported harness fallback policy version")
        if type(self.harness_ids) not in (tuple, list) or not self.harness_ids:
            raise ValueError("fallback needs an explicit nonempty adapter order")
        ids = tuple(self.harness_ids)
        if any(not valid_harness_id(item) for item in ids) or len(set(ids)) != len(ids):
            raise ValueError("fallback adapters must be unique bounded identifiers")
        if type(self.switch_on) not in (tuple, list):
            raise TypeError("fallback causes must be an explicit sequence")
        causes = tuple(self.switch_on)
        if any(type(item) is not HarnessFailureKind for item in causes):
            raise TypeError("fallback causes must be typed HarnessFailureKind values")
        if len(set(causes)) != len(causes):
            raise ValueError("fallback causes must not repeat")
        object.__setattr__(self, "harness_ids", ids)
        object.__setattr__(self, "switch_on", causes)

    def to_dict(self):
        encoding = ('harness_fallback_policy/v2' if HarnessFailureKind.SEMANTIC_REJECTED in self.switch_on
                    else 'harness_fallback_policy/v1')
        return {"record_type": encoding, "version": self.version,
                "harness_ids": list(self.harness_ids),
                "switch_on": [item.value for item in self.switch_on]}

    @property
    def content_digest(self):
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True,
                                        separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class HarnessFallbackDecision:
    """A recovery decision, not evidence of solution correctness."""

    reason: str
    next_harness_id: str = ""
    accounting_uncertain: bool = False


@dataclass(frozen=True)
class HarnessRecoveryObservation:
    """Small prior-attempt reference, not copied transcript or new authority."""

    harness_id: str
    harness_loop_id: str
    semantic_call_id: str
    failure: HarnessFailureKind
    evaluation_contract_ref: str = ''
    finding_codes: tuple[str, ...] = ()

    def __post_init__(self):
        if not valid_harness_id(self.harness_id) or type(self.failure) is not HarnessFailureKind:
            raise ValueError('recovery needs an exact adapter and typed failure')
        for value in (self.harness_loop_id, self.semantic_call_id):
            if type(value) is not str or len(value) > 192 or any(c.isspace() for c in value):
                raise ValueError('recovery references must be bounded identifiers')
        if not self.semantic_call_id:
            raise ValueError('recovery must name its semantic step')
        if self.evaluation_contract_ref:
            from .harness_response_evaluation import ResponseEvaluationVerdict
            from .harness_selection_records import exact_text
            exact_text(self.evaluation_contract_ref,'evaluation contract reference')
            object.__setattr__(self,'finding_codes',ResponseEvaluationVerdict('rejected',self.finding_codes).finding_codes)
        elif self.finding_codes or self.failure is HarnessFailureKind.SEMANTIC_REJECTED:
            raise ValueError('semantic recovery feedback needs its evaluated contract')

    def to_dict(self):
        return {'record_type': ('harness_recovery_observation/v2' if self.evaluation_contract_ref
                                else 'harness_recovery_observation/v1'),
                'harness_id': self.harness_id, 'harness_loop_id': self.harness_loop_id,
                'semantic_call_id': self.semantic_call_id, 'failure': self.failure.value,
                **({'evaluation_contract_ref':self.evaluation_contract_ref,
                    'finding_codes':list(self.finding_codes)} if self.evaluation_contract_ref else {})}


def assess_harness_attempt(policy, index, result, gateway_results, *,
                           accounting_uncertain=False, response_evaluation=None):
    """Fail closed on unknown effects, accounting, provider or shared failures.

    Only the semantic binding calls this after the canonical boundary checks
    identities and effects. An empty model-call list is not a successful step.
    """
    from .external_harness import HarnessRunResult
    from .model_gateway import ModelGatewayResult
    if not isinstance(policy, HarnessFallbackPolicy) or not isinstance(result, HarnessRunResult):
        raise TypeError("typed fallback policy and harness result are required")
    if type(index) is not int or not 0 <= index < len(policy.harness_ids):
        raise ValueError("attempt index is outside the configured order")
    if result.harness_id != policy.harness_ids[index]:
        raise ValueError("attempt does not match its registered position")
    if any(not isinstance(item, ModelGatewayResult) for item in gateway_results):
        raise TypeError("gateway observations must be typed")
    physical_calls = sum(item.physical_model_calls for item in gateway_results)
    if (accounting_uncertain or not result.call_count_complete
            or result.physical_model_calls != physical_calls
            or any(not call.gateway_loop_id for call in result.model_calls)):
        return HarnessFallbackDecision("unresolved_model_accounting", accounting_uncertain=True)
    if result.tool_events or result.spawned_task_ids:
        return HarnessFallbackDecision("unexpected_effects_require_reconciliation")
    if response_evaluation is not None:
        from .harness_response_evaluation import HarnessResponseEvaluation
        if not isinstance(response_evaluation,HarnessResponseEvaluation):
            raise TypeError('response evaluation must be an issued typed record')
        if response_evaluation.status == 'inconclusive':
            return HarnessFallbackDecision('response_evaluation_inconclusive')
    if result.completed and physical_calls:
        return HarnessFallbackDecision("response_admitted")
    from .model_gateway import EVALUATOR_VERDICT_ERRORS
    failures = [item.error_code for item in gateway_results if not item.ok]
    # An evaluator's verdict is a judgement about the answer, recorded by the
    # gateway with its own code. It is not a provider or shared failure.
    if any(code != HarnessFailureKind.RESPONSE_REJECTED.value
           and code not in EVALUATOR_VERDICT_ERRORS for code in failures):
        return HarnessFallbackDecision("provider_or_shared_gateway_failure")
    if result.status == "budget_exhausted":
        return HarnessFallbackDecision("shared_budget_exhausted")
    if "response_evaluation_inconclusive" in failures:
        return HarnessFallbackDecision("response_evaluation_inconclusive")
    code = (HarnessFailureKind.RESPONSE_REJECTED.value if failures else result.error_code)
    if "semantic_response_rejected" in failures or (
            response_evaluation is not None and response_evaluation.status == 'rejected'):
        code = HarnessFailureKind.SEMANTIC_REJECTED.value
    try:
        cause = HarnessFailureKind(code)
    except ValueError:
        return HarnessFallbackDecision("unclassified_failure_requires_review")
    if cause not in policy.switch_on:
        return HarnessFallbackDecision("failure_not_permitted_by_policy")
    if index + 1 == len(policy.harness_ids):
        return HarnessFallbackDecision("alternatives_exhausted")
    return HarnessFallbackDecision(cause.value, policy.harness_ids[index + 1])


def self_test():
    from .harness_fallback_checks import run_self_test_checks
    return run_self_test_checks()
