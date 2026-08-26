"""Asset lifecycle — ONE canonical promotion vocabulary for every resource.

Owner-confirmed simplification (2026-08-23): the same "how-trusted / how-promoted"
idea was spelled six different ways — intelligence_strings maturity, learning_bundle
storage-stage + disposition, intelligence_registry lifecycle + tier,
runtime_contracts promotion-status, housekeeping maturity, and (a different axis)
knowledge_state claim-status.  This module is the single vocabulary they all map
onto, so the practitioner reasons about trust ONCE.

  * ONE LIFECYCLE (promotion maturity):
        draft → candidate → validated → registered → preferred → deprecated → retired
  * ONE TIER derived from it: draft/candidate/validated = RUNTIME (provisional);
    registered/preferred/deprecated = DATABASE (promoted); retired = gone.
    Only registered/preferred SERVE as truth.
  * The runtime→database crossing (validated → registered) is the evidence-gated
    candidate→truth boundary — never crossed by assertion.
  * ONE ``Resource`` envelope (id · class · role · content · scope · lifecycle ·
    version · digest · provenance · relationships) so String ROLES
    (question / record / work_item / evidence_window / improvement_finding /
    capability_snapshot …) stop spawning near-identical dataclasses.

Orthogonality note: the lifecycle is promotion maturity.  It is NOT the epistemic
axis — ``knowledge_state`` claim statuses (observed / inferred / asserted) describe
where a claim came from, a separate fact carried alongside, never folded in.

This LAYERS over the existing modules via ``normalize`` adapters; nothing is
refactored, so the suite stays green while the vocabularies converge.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Sequence

# The one canonical promotion lifecycle, ordered.
LIFECYCLE_STATES = ("draft", "candidate", "validated", "registered", "preferred",
                    "deprecated", "retired")
_ORDER = {s: i for i, s in enumerate(LIFECYCLE_STATES)}
_TERMINAL = ("deprecated", "retired")
TIERS = ("runtime", "database")
SCOPES = ("run", "project", "org", "core")
ASSET_CLASSES = ("string", "code")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class LifecycleError(RuntimeError):
    """An illegal lifecycle transition (backwards, or unknown state)."""


class PromotionRefused(RuntimeError):
    """Runtime → database promotion attempted without evidence."""


def tier_of(state: str) -> str:
    """The tier a lifecycle state lives in.  Registered onward is database."""
    if state not in _ORDER:
        raise LifecycleError(f"unknown lifecycle state {state!r}")
    if state == "retired":
        return "database"                       # historical, not served
    return "database" if _ORDER[state] >= _ORDER["registered"] else "runtime"


def is_served(state: str) -> bool:
    """Only registered/preferred serve as database truth."""
    return state in ("registered", "preferred")


def advance(state: str, to: str, *, evidence: Sequence = ()) -> str:
    """Move a resource forward.  Lifecycle only advances (deprecate/retire allowed
    from anywhere); the runtime→database crossing is EVIDENCE-GATED."""
    if to not in _ORDER:
        raise LifecycleError(f"unknown target state {to!r}")
    if to in _TERMINAL:
        return to
    if _ORDER[to] < _ORDER[state]:
        raise LifecycleError(f"lifecycle only moves forward: {state} → {to}")
    if tier_of(state) == "runtime" and tier_of(to) == "database" and not evidence:
        raise PromotionRefused(
            f"{state} → {to} crosses runtime→database (candidate→truth) — it needs "
            "evidence, never assertion")
    return to


# ---------------------------------------------------------------------------
# Convergence adapters — map the six legacy vocabularies onto the one lifecycle.
# ---------------------------------------------------------------------------

VOCAB_MAPS = {
    "string_maturity": {                        # intelligence_strings.MATURITY
        "ephemeral": "draft", "candidate": "candidate",
        "validated": "validated", "preferred": "preferred"},
    "registry_lifecycle": {                     # intelligence_registry.LIFECYCLE
        "generated": "draft", "staged": "candidate", "validated": "validated",
        "served": "registered", "superseded": "deprecated", "retired": "retired"},
    "storage_stage": {                          # learning_bundle.STORAGE_STAGES
        "raw_capture": "draft", "run_local_staging": "candidate",
        "shared_promotion": "registered"},
    "learning_disposition": {                   # learning_bundle dispositions
        "no_new_learning": "draft", "ephemeral_task_only": "draft",
        "reusable_candidates_extracted": "candidate",
        "requires_additional_structuring": "draft",
        "requires_additional_research": "draft",
        "requires_validation": "candidate", "rejected_or_unreliable": "retired"},
    "housekeeping_maturity": {                  # housekeeping ImprovementCandidate
        "runtime_raw": "draft", "normalized_candidate": "candidate",
        "registered": "registered", "preferred": "preferred",
        "deprecated_or_retired": "retired"},
    "contract_status": {                        # runtime_contracts ContractCandidate
        "proposed": "candidate", "registered": "registered"},
}


def normalize(vocab: str, value: str) -> str:
    """Map a value from any legacy vocabulary onto the canonical lifecycle."""
    if vocab not in VOCAB_MAPS:
        raise KeyError(f"no vocabulary {vocab!r}; have {sorted(VOCAB_MAPS)}")
    m = VOCAB_MAPS[vocab]
    if value not in m:
        raise KeyError(f"{value!r} is not in vocabulary {vocab!r}")
    return m[value]


# ---------------------------------------------------------------------------
# The one Resource envelope.
# ---------------------------------------------------------------------------


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()[:16]


@dataclass
class Resource:
    """The single envelope for every asset — String or Code node, any role."""
    asset_id: str
    asset_class: str                    # string | code
    role: str                           # question / logic_rule / record / …
    content: str = ""
    scope: str = "run"
    lifecycle: str = "draft"
    version: str = "0.1.0"
    provenance: str = ""
    relationships: tuple = ()
    tags: tuple = ()
    digest: str = ""

    def __post_init__(self):
        if self.asset_class not in ASSET_CLASSES:
            raise ValueError(f"asset_class must be one of {ASSET_CLASSES}")
        if self.lifecycle not in LIFECYCLE_STATES:
            raise ValueError(f"lifecycle must be one of {LIFECYCLE_STATES}")
        if self.scope not in SCOPES:
            raise ValueError(f"scope must be one of {SCOPES}")
        if not _SEMVER.match(self.version):
            raise ValueError("version must be semver x.y.z")
        self.digest = _digest(self.asset_class, self.role, self.content,
                              self.version)

    @property
    def tier(self) -> str:
        return tier_of(self.lifecycle)

    @property
    def served(self) -> bool:
        return is_served(self.lifecycle)

    def promote(self, to: str, *, evidence: Sequence = (),
                scope: "str | None" = None) -> "Resource":
        """Advance the lifecycle (evidence-gated at the runtime→database crossing)
        and widen scope on promotion."""
        self.lifecycle = advance(self.lifecycle, to, evidence=evidence)
        if scope:
            self.scope = scope
        return self

    def to_store_record(self, *, record_id: "str | None" = None,
                        kind: "str | None" = None,
                        extra_body: "dict | None" = None,
                        extra_tags: Sequence = (), tier: "str | None" = None):
        """The ONE search projection.  A producer sources class/role/lifecycle
        from this Resource and may pass overrides (record_id / kind / extra_body /
        extra_tags / tier) to reproduce its exact search record — so the Resource
        is the single source of truth while search shapes stay stable."""
        from ..core.store_serve import StoreRecord
        k = kind or ("question" if self.role == "question"
                     else "node" if self.asset_class == "code" else "context")
        body = {"asset_class": self.asset_class, "role": self.role,
                "scope": self.scope, "lifecycle": self.lifecycle,
                "tier": self.tier, "served": self.served,
                "version": self.version, "digest": self.digest,
                "provenance": self.provenance}
        if extra_body:
            body.update(extra_body)
        return StoreRecord(
            record_id=record_id or f"res.{self.asset_id}", kind=k,
            title=self.content[:80] or self.role, body=body,
            tags=("resource", self.asset_class, self.role, self.lifecycle)
            + tuple(self.tags) + tuple(extra_tags),
            tier=tier or ("core" if self.tier == "database" else "experimental"))


def from_string(s, *, role: str = "consideration") -> "Resource":
    """Bridge an IntelligenceString onto the one envelope (maturity → lifecycle)."""
    return Resource(asset_id=s.string_id, asset_class="string",
                    role=role or s.kind, content=s.text,
                    lifecycle=normalize("string_maturity", s.maturity),
                    provenance=s.provenance)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def promotion_review_as_loop(state: str, to: str, evidence=(), *,
                             advance_fn=None, ledger=None) -> dict:
    """Loop-standardization item #3: promotion review runs AS a
    PractitionerLoop on the registered adversarial_review template —
    collect_claims (the requested transition), attack (the evidence
    checks that try to refuse it), verify_survivors (the gate itself:
    the SAME advance() authority, wrapped, never weakened), report.
    A refused promotion completes the loop with the refusal as
    evidence — review never dies on a rejection, it RECORDS it."""
    from ..loop.recursive_loop import Loop, StepOutcome
    from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
    tmpl = next(b for b in TEMPLATE_LIBRARY
                if b["template_id"] == "adversarial_review")
    gate = advance_fn or advance
    state_d: dict = {"promoted": False, "reason": ""}

    def handler(lp, step, ctx):
        if step == "collect_claims":
            return StepOutcome(output=f"claim:{state} -> {to} with "
                                      f"{len(tuple(evidence))} evidence refs",
                               mode="deterministic", confidence=0.95)
        if step == "attack":
            gaps = [] if evidence else ["no evidence attached"]
            return StepOutcome(output="attack:" + (";".join(gaps) or
                                                   "no gaps found"),
                               mode="deterministic",
                               confidence=0.9 if not gaps else 0.5)
        if step == "verify_survivors":
            try:
                new_state = gate(state, to, evidence=tuple(evidence))
                state_d.update(promoted=True, new_state=new_state)
                out = f"verify:promoted to {new_state}"
            except (PromotionRefused, LifecycleError) as e:
                state_d["reason"] = str(e)[:160]
                out = f"verify:REFUSED — {state_d['reason'][:80]}"
            return StepOutcome(output=out, mode="deterministic",
                               confidence=0.95)
        return StepOutcome(
            output=f"report:{'promoted' if state_d['promoted'] else 'refused'}",
            mode="deterministic", confidence=0.95)

    loop = Loop(f"promotion review: {state} -> {to}",
                config_from_template(tmpl, power="standard"), ledger=ledger)
    res = loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    return {"loop_id": res.loop_id, "promoted": state_d["promoted"],
            "new_state": state_d.get("new_state"),
            "reason": state_d["reason"], "model_calls": res.model_calls,
            "stopped": res.stopped}


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. ONE ordered lifecycle; tier is derived; only registered/preferred serve.
    check("one_ordered_lifecycle_with_derived_tier",
          LIFECYCLE_STATES[0] == "draft" and LIFECYCLE_STATES[4] == "preferred"
          and tier_of("candidate") == "runtime"
          and tier_of("registered") == "database"
          and is_served("preferred") and not is_served("candidate"),
          "draft/candidate/validated = runtime; registered/preferred = database")

    # 2. lifecycle advances forward; the runtime→database crossing is
    # EVIDENCE-GATED (candidate→truth, never by assertion).
    ok_fwd = advance("candidate", "validated") == "validated"
    refused = False
    try:
        advance("validated", "registered")          # no evidence
    except PromotionRefused:
        refused = True
    promoted = advance("validated", "registered",
                       evidence=["paired trial accepted"]) == "registered"
    backward = False
    try:
        advance("registered", "candidate")
    except LifecycleError:
        backward = True
    check("advance_is_forward_only_and_promotion_is_evidence_gated",
          ok_fwd and refused and promoted and backward,
          "validated→registered needs evidence; no going backwards")

    # 3. THE CONVERGENCE: all six legacy vocabularies normalize into the one
    # lifecycle — pulled from the REAL module constants where exported.
    from ..strings.intelligence_strings import MATURITY
    from ..code_nodes.learning_bundle import STORAGE_STAGES, LEARNING_DISPOSITIONS
    from ..core.intelligence_registry import LIFECYCLE as REG_LIFE
    unmapped = []
    for v in MATURITY:
        if normalize("string_maturity", v) not in LIFECYCLE_STATES:
            unmapped.append(("string_maturity", v))
    for v in STORAGE_STAGES:
        if normalize("storage_stage", v) not in LIFECYCLE_STATES:
            unmapped.append(("storage_stage", v))
    for v in LEARNING_DISPOSITIONS:
        if normalize("learning_disposition", v) not in LIFECYCLE_STATES:
            unmapped.append(("learning_disposition", v))
    for v in REG_LIFE:
        if normalize("registry_lifecycle", v) not in LIFECYCLE_STATES:
            unmapped.append(("registry_lifecycle", v))
    for v in ("runtime_raw", "normalized_candidate", "registered", "preferred",
              "deprecated_or_retired"):
        if normalize("housekeeping_maturity", v) not in LIFECYCLE_STATES:
            unmapped.append(("housekeeping_maturity", v))
    for v in ("proposed", "registered"):
        if normalize("contract_status", v) not in LIFECYCLE_STATES:
            unmapped.append(("contract_status", v))
    check("all_six_vocabularies_converge_onto_one_lifecycle",
          not unmapped,
          f"every legacy state maps to a canonical one; unmapped: {unmapped}")

    # 4. the mapping is faithful: a legacy 'served'/'shared_promotion' lands on
    # the DATABASE tier; a legacy 'ephemeral'/'raw_capture' stays RUNTIME.
    check("the_mapping_preserves_the_trust_boundary",
          tier_of(normalize("registry_lifecycle", "served")) == "database"
          and tier_of(normalize("storage_stage", "shared_promotion")) == "database"
          and tier_of(normalize("string_maturity", "ephemeral")) == "runtime"
          and tier_of(normalize("storage_stage", "raw_capture")) == "runtime",
          "promoted legacy states → database; provisional ones → runtime")

    # 5. ONE Resource envelope carries every role (question / record / work_item
    # / logic_rule …) — the same object, a different role.
    r_q = Resource("q1", "string", "question", "Are the residuals patterned?")
    r_rcpt = Resource("rc1", "string", "record", "pass 3 result", scope="run")
    r_logic = Resource("lg1", "code", "logic_rule", "IF r>0.9 THEN flag",
                       lifecycle="validated")
    check("one_envelope_carries_every_role",
          r_q.asset_class == "string" and r_logic.asset_class == "code"
          and {r_q.role, r_rcpt.role, r_logic.role}
          == {"question", "record", "logic_rule"}
          and r_q.tier == "runtime" and r_q.digest,
          "String roles and Code nodes share one envelope — no per-role classes")

    # 6. a Resource promotes through the same gate.
    refused2 = False
    try:
        r_logic.promote("registered")               # no evidence
    except PromotionRefused:
        refused2 = True
    r_logic.promote("registered", evidence=["diff-tested"], scope="org")
    check("resource_promotes_through_the_evidence_gate",
          refused2 and r_logic.tier == "database" and r_logic.served
          and r_logic.scope == "org",
          "the envelope crosses to the database only on evidence")

    # 7. epistemic status is NOT folded into the lifecycle (orthogonal axis).
    from ..strings.knowledge_state import CLAIM_STATUSES
    check("epistemic_status_is_kept_orthogonal",
          "observed" in CLAIM_STATUSES
          and "observed" not in LIFECYCLE_STATES
          and "observed" not in VOCAB_MAPS,
          "observed/inferred/asserted is provenance, not promotion — kept separate")

    # 8. resources are searchable through the one store DAG.
    from ..core.store_serve import SolverStore
    from ..strings.intelligence_strings import IntelligenceString
    res = from_string(IntelligenceString("consideration",
                                         "watch for temporal leakage",
                                         maturity="preferred"))
    store = SolverStore(core_records=[res.to_store_record()])
    hit = store.search("temporal leakage consideration")
    check("resources_flow_through_the_one_search_dag",
          res.tier == "database" and hit["hits"]
          and any("res." in h["record_id"] for h in hit["hits"]),
          "a preferred string bridges to a database Resource, searchable")

    # 9. MIGRATION: the core reusable types across the modules all EMIT the one
    # Resource envelope (asset_class · role · lifecycle) — one shape, not many.
    from ..strings.intelligence_strings import IntelligenceString
    from ..code_nodes.learning_bundle import LearningCandidate
    from ..code_nodes.runtime_contracts import ContractDefinition
    from ..code_nodes.logic_ast import LogicRule
    from ..code_nodes.housekeeping import ImprovementCandidate
    emitters = [
        IntelligenceString("consideration", "watch leakage",
                           maturity="preferred").resource(),
        LearningCandidate("logic_candidate", "IF a THEN b",
                          validation_status="validated").resource(),
        ContractDefinition("out", "enum", allowed_values=("a", "b")).resource(),
        LogicRule("lg", "review redundancy", "check",
                  condition={"op": "exists", "field": "x"}).resource(),
        ImprovementCandidate("code_node", "build a vif node").resource(),
    ]
    check("core_types_emit_one_resource_envelope",
          all(isinstance(r, Resource) for r in emitters)
          and all(r.lifecycle in LIFECYCLE_STATES for r in emitters)
          and {r.asset_class for r in emitters} == {"string", "code"}
          and emitters[2].asset_class == "code" and emitters[2].role == "contract"
          and emitters[0].tier == "database",
          "IntelligenceString / LearningCandidate / Contract / LogicRule / "
          "ImprovementCandidate all emit the same Resource shape")

    # LOOP-STANDARDIZATION #3: promotion review as an adversarial loop —
    # the SAME gate authority wrapped: evidence-less runtime→database
    # promotion is REFUSED with the refusal AS loop evidence; with
    # evidence it promotes; zero model calls either way.
    from ..loop.recursive_loop import LoopLedger as _LL
    _lgP = _LL()
    bad = promotion_review_as_loop("candidate", "registered",
                                   evidence=(), ledger=_lgP)
    good = promotion_review_as_loop("candidate", "registered",
                                    evidence=("record:r1",))
    refusal_on_ledger = any("verify:REFUSED" in str(e.get("output", ""))
                            for e in _lgP.events)
    check("promotion_review_is_an_adversarial_loop_gate_intact",
          not bad["promoted"] and "evidence" in bad["reason"]
          and refusal_on_ledger and good["promoted"]
          and good["new_state"] == "registered"
          and bad["model_calls"] == 0 and bad["stopped"] == "done",
          "refusal recorded as loop evidence; the gate itself unweakened")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "asset_lifecycle_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
