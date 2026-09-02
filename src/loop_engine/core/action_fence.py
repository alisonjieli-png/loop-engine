"""Repeated-action fence: the runtime refuses to re-run an identical failed call.

Architectural role: a deterministic supervision law in front of capability
execution. The model may propose any registered call; the runtime keeps a
per-run ledger of (capability, canonical arguments) digests that failed, and
once one digest has failed ``identical_failures_before_fence`` times it is
refused without execution, with the last typed rejection attached, for the
rest of the run. The fence never chooses the alternative. It makes exact
repetition impossible and keeps the runtime's facts about every refused call
in one bounded, model-visible view.

History that motivated it: a live run proposed the same rejected source
inspection for twenty passes because a model-written diagnosis kept
repeating a wrong cause; soft reset and cold restart reframed the prose but
not the action. The fence closes that class of stall for every capability,
present and future, without naming any task.

Owns:
    - ActionFencePolicy (passive, carried by the supervision policy).
    - action_digest(): the one canonical identity of a proposed call.
    - ActionFenceLedger: failures, successes, refusals, and the model view.

Does not own: the rejection vocabulary (core.capability_rejection), the
execution path that consults the ledger (core.adaptive_practitioner_capabilities),
or the packet projection (core.practitioner_runtime_facts).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .capability_rejection import CapabilityRejection


@dataclass(frozen=True)
class ActionFencePolicy:
    """How many identical failures one run tolerates before refusing."""

    policy_id: str = "practitioner.action_fence"
    version: str = "1.0.0"
    identical_failures_before_fence: int = 2
    remembered_rejections: int = 8

    def __post_init__(self) -> None:
        for name in ("identical_failures_before_fence",
                     "remembered_rejections"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) \
                    or value < 1:
                raise ValueError(f"ActionFencePolicy.{name} must be >= 1")

    def to_dict(self) -> dict:
        return {"policy_id": self.policy_id, "version": self.version,
                "identical_failures_before_fence":
                    self.identical_failures_before_fence,
                "remembered_rejections": self.remembered_rejections}


def action_digest(capability_ref: str, arguments: Mapping) -> str:
    """Canonical identity of one proposed call: capability plus arguments."""
    return hashlib.sha256(json.dumps(
        {"capability_ref": capability_ref, "arguments": dict(arguments)},
        sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@dataclass
class ActionFenceEntry:
    """Exact failure memory for one call identity."""

    digest: str
    capability_ref: str
    arguments: dict
    failures: int = 0
    first_pass: int = 0
    last_pass: int = 0
    last_error: str = ""
    last_rejection: dict | None = None

    def to_dict(self) -> dict:
        return {"digest": self.digest, "capability_ref": self.capability_ref,
                "arguments": self.arguments, "failures": self.failures,
                "first_pass": self.first_pass, "last_pass": self.last_pass,
                "last_error": self.last_error,
                "last_rejection": self.last_rejection}


class ActionFenceLedger:
    """Per-run memory of failed call identities and the refusals issued."""

    def __init__(self) -> None:
        self._entries: dict[str, ActionFenceEntry] = {}
        self.refusals: list[dict] = []

    def note_failure(self, capability_ref: str, arguments: Mapping, *,
                     error: str, rejection: dict | None = None,
                     pass_number: int = 0) -> ActionFenceEntry:
        digest = action_digest(capability_ref, arguments)
        entry = self._entries.get(digest)
        if entry is None:
            entry = ActionFenceEntry(digest, capability_ref, dict(arguments),
                                     first_pass=pass_number)
            self._entries[digest] = entry
        entry.failures += 1
        entry.last_pass = pass_number
        entry.last_error = str(error)[:500]
        if rejection is not None:
            entry.last_rejection = dict(rejection)
        return entry

    def note_success(self, capability_ref: str, arguments: Mapping) -> None:
        self._entries.pop(action_digest(capability_ref, arguments), None)

    def failures(self, capability_ref: str, arguments: Mapping) -> int:
        entry = self._entries.get(action_digest(capability_ref, arguments))
        return entry.failures if entry else 0

    def is_fenced(self, capability_ref: str, arguments: Mapping,
                  policy: ActionFencePolicy) -> bool:
        return (self.failures(capability_ref, arguments)
                >= policy.identical_failures_before_fence)

    def refusal(self, capability_ref: str, arguments: Mapping,
                policy: ActionFencePolicy, *,
                pass_number: int = 0) -> CapabilityRejection:
        """The typed refusal for a fenced call; recorded, never executed."""
        entry = self._entries[action_digest(capability_ref, arguments)]
        last = entry.last_rejection or {}
        admitted = tuple(last.get("admitted_values") or ())
        refusal = CapabilityRejection(
            capability_ref, "repeated_identical_failure",
            (f"{capability_ref} with these exact arguments failed "
             f"{entry.failures} time(s) (last: {entry.last_error[:200]}); "
             "the runtime will not execute the identical call again in "
             "this run"),
            rejected_arguments=tuple(sorted(entry.arguments.items())),
            admitted_values=admitted,
            admitted_values_total=int(
                last.get("admitted_values_total") or len(admitted)),
            repair_hint=(
                "choose different arguments or a different capability; "
                + (f"admitted values from the last rejection: "
                   f"{list(admitted)[:8]}" if admitted else
                   str(last.get("repair_hint") or
                       "the last error text is exact"))),
            identical_failures=entry.failures, pass_number=pass_number)
        self.refusals.append(refusal.to_dict())
        return refusal

    def fenced_entries(self, policy: ActionFencePolicy) -> tuple:
        return tuple(entry for entry in self._entries.values()
                     if entry.failures >= policy.identical_failures_before_fence)

    def model_view(self, policy: ActionFencePolicy) -> dict:
        """Bounded, deduplicated facts for the packet."""
        recent = sorted(self._entries.values(),
                        key=lambda entry: (entry.last_pass, entry.digest))
        recent = recent[-policy.remembered_rejections:]
        return {
            "record_type": "action_fence_view/v1",
            "policy": policy.to_dict(),
            "fenced": [
                {"capability_ref": entry.capability_ref,
                 "arguments": entry.arguments, "failures": entry.failures,
                 "digest": entry.digest[:16]}
                for entry in self.fenced_entries(policy)],
            "recent_failures": [
                {"capability_ref": entry.capability_ref,
                 "arguments": entry.arguments, "failures": entry.failures,
                 "last_pass": entry.last_pass,
                 "rejection": entry.last_rejection}
                for entry in recent],
            "refusals_issued": len(self.refusals),
        }

    def to_dict(self) -> dict:
        return {"record_type": "action_fence_ledger/v1",
                "entries": [entry.to_dict() for entry in
                            self._entries.values()],
                "refusals": list(self.refusals)}


def self_test() -> dict:
    """Prove the fence refuses only exact repetition, after the policy count."""
    policy = ActionFencePolicy()
    ledger = ActionFenceLedger()
    call = {"paths": ["/abs/dir"], "include_contents": False}
    rejection = CapabilityRejection(
        "core.source.inspect", "argument_not_admitted", "unknown paths",
        rejected_arguments=(("paths", ("/abs/dir",)),),
        admitted_values=("train.csv", "test.csv"), admitted_values_total=2,
        repair_hint="omit paths").to_dict()
    ledger.note_failure("core.source.inspect", call, error="unknown paths",
                        rejection=rejection, pass_number=1)
    fenced_after_one = ledger.is_fenced("core.source.inspect", call, policy)
    reordered = {"include_contents": False, "paths": ["/abs/dir"]}
    ledger.note_failure("core.source.inspect", reordered,
                        error="unknown paths", rejection=rejection,
                        pass_number=2)
    fenced_after_two = ledger.is_fenced("core.source.inspect", call, policy)
    different = ledger.is_fenced(
        "core.source.inspect", {"paths": ["train.csv"]}, policy)
    refusal = ledger.refusal("core.source.inspect", call, policy,
                             pass_number=3)
    view = ledger.model_view(policy)
    ledger.note_success("core.source.inspect", call)
    tests = [{
        "test": "one_failure_does_not_fence_the_call",
        "passed": fenced_after_one is False,
        "detail": f"threshold {policy.identical_failures_before_fence}",
    }, {
        "test": "argument_order_does_not_change_the_identity",
        "passed": (fenced_after_two is True and different is False
                   and action_digest("c", call)
                   == action_digest("c", reordered)),
        "detail": action_digest("core.source.inspect", call)[:12],
    }, {
        "test": "the_refusal_carries_the_last_admitted_values",
        "passed": (refusal.reason_code == "repeated_identical_failure"
                   and refusal.admitted_values == ("train.csv", "test.csv")
                   and refusal.identical_failures == 2
                   and view["fenced"][0]["failures"] == 2
                   and view["refusals_issued"] == 1),
        "detail": refusal.repair_hint[:80],
    }, {
        "test": "a_success_clears_the_identity",
        "passed": (ledger.is_fenced("core.source.inspect", call, policy)
                    is False and ledger.failures(
                        "core.source.inspect", call) == 0),
        "detail": "cleared",
    }]
    return {"module": "core.action_fence",
            "passed": all(item["passed"] for item in tests), "tests": tests}
