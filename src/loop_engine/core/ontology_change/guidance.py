"""Envelope layers of ontology change planning: refusal guidance, handshake verdicts and the apply replay.

```text
ontology_change_planning, the reference adoption of the envelope layers
├── frustration_avoidance  REFUSAL_GUIDANCE: every closed failure code of the contract as envelope_refusal/v1,
│                          with what happened, the next action, who acts and the retry rule; no code is left
│                          without wording (guidance_gaps); RECOVERY_POLICY declares no automatic retry
├── handshake              handshake_for: one envelope_handshake_verdict/v1 for each screened installation,
│                          from its declaration (request version, profiles, blank nodes, effects) and the
│                          host's granted effects
├── tracking               apply_identity and replayed_apply: a retried apply of the same plan and approval is
│                          answered with its first result when the store still holds that result, decided by
│                          the shared journal decision
└── preflight              PREFLIGHT_CHECKS: the selected engine is checked again for availability just before
                           each dispatch; no self-repair is declared, because none of its diagnoses has a repair
                           without effects
```

Every refusal here happens before the store writes anything, so each one carries the effect commitment
none. Nothing here runs an engine, writes the store or grants authority; the envelope (``component.py``)
and the store (``store.py``) call these pieces. The contract (``contract.py``) keeps its records and
codes unchanged, so the engines' implementation digests do not move.
"""
from __future__ import annotations

from types import MappingProxyType

from ..configuration_capabilities import digest
from ..engines.envelope import (
    CALLER, DO_NOT_RETRY, OPERATOR, RETRY_AFTER_FIX, EnvelopeHandshakeDeclaration, EnvelopeHandshakeRequest,
    EnvelopeRecoveryPolicy, EnvelopeRefusal, envelope_refusal, negotiate_handshake)
from ..engines.envelope_preflight import EnvelopePreflightCheck
from ..engines.envelope_tracking import (
    ANSWER_FROM_FIRST_RESULT, EFFECT_STATE_CONFIRMED, EFFECT_STATE_NONE, journal_decision, journal_intent,
    journal_reconciliation, request_identity_digest)
from .contract import APPLY_RESULT_RECORD_TYPE, FAILURE_CODES, REQUEST_RECORD_TYPE, SLOT_ID

#: The journal operation of an apply, as ``store.py`` writes it.
APPLY_OPERATION = "apply"

#: What each closed failure code tells its reader: what happened, the next action, the retry rule and who
#: acts. A stale base and a locked term refuse before any write, as does every other code, so a corrected
#: request is always safe to send.
REFUSAL_GUIDANCE = MappingProxyType({
    "request_invalid": ("The request does not have the fields and values that its record version names.",
                        "Correct the field the detail names, following ontology_change_request/v1, then send it.",
                        RETRY_AFTER_FIX, CALLER),
    "unsupported_syntax": ("The ontology text could not be read as Turtle or as N-Triples.",
                           "Fix the syntax error the detail names, or send the ontology as N-Triples, then plan.",
                           RETRY_AFTER_FIX, CALLER),
    "base_digest_mismatch": ("The digest in the request does not belong to the ontology it carries, so no "
                             "engine ran.",
                             "Take the graph digest of the ontology you send, put it in base_digest, then plan "
                             "again.", RETRY_AFTER_FIX, CALLER),
    "change_invalid": ("The change removes a triple the ontology does not hold, or adds one it already holds.",
                       "Take the triple the detail names out of the change, then plan the change again.",
                       RETRY_AFTER_FIX, CALLER),
    "profile_unsupported": ("No rule table of this release has the profile that the request names.",
                            "Ask for the rdfs profile or the owl-rl profile, then plan the change again.",
                            RETRY_AFTER_FIX, CALLER),
    "limit_exceeded": ("The ontology or its closure is larger than the bound that this request allows.",
                       "Raise maximum_closure within its ceiling, or plan a smaller ontology, then send it again.",
                       RETRY_AFTER_FIX, CALLER),
    "no_eligible_engine": ("No installed engine may plan this change here, for the reasons the detail lists.",
                           "Install, enable or grant an engine the detail names, or record its conformance "
                           "report, then plan.", RETRY_AFTER_FIX, OPERATOR),
    "engine_unavailable": ("The selected engine could not run here, and no other declared engine was left.",
                           "Install the engine's pinned binary and its sandbox as the detail names, then plan "
                           "again.", RETRY_AFTER_FIX, OPERATOR),
    "engine_failed": ("The engine reported a failure, and no other declared engine was left to try.",
                      "Read the engine's failure in the detail, remove its cause on this machine, then plan again.",
                      RETRY_AFTER_FIX, OPERATOR),
    "result_invalid": ("The engine's answer failed the envelope's own checks, so no plan was written.",
                       "Report the detail to whoever maintains the engine, and plan again after their fix.",
                       RETRY_AFTER_FIX, OPERATOR),
    "plan_invalid": ("The plan sent for apply is not one this component wrote for the store's state.",
                     "Plan the change again from the store's current state, then apply the new plan.",
                     RETRY_AFTER_FIX, CALLER),
    "approval_required": ("Apply and rollback need an approval that names the plan's digest, and none was sent.",
                          "Ask whoever approves changes for an approval naming this plan's digest, then apply.",
                          RETRY_AFTER_FIX, OPERATOR),
    "approval_mismatch": ("The approval sent with the plan names the digest of another plan.",
                          "Send the approval that names this plan's digest, or ask for one, then apply again.",
                          RETRY_AFTER_FIX, CALLER),
    "stale_base": ("The store holds another state than the one this plan was made for, so nothing changed.",
                   "Plan the change again from the store's current state, then apply that plan.",
                   RETRY_AFTER_FIX, CALLER),
    "locked_term": ("The change or one of its consequences touches a term the store locks, so nothing changed.",
                    "Plan a change that leaves the locked term alone, or ask the lock's owner to lift it.",
                    RETRY_AFTER_FIX, CALLER),
    "store_corrupt": ("The store's state or one of its graph files could not be read as it was written.",
                      "Restore the store folder from its last good copy, then check it before any change.",
                      RETRY_AFTER_FIX, OPERATOR),
    "rollback_invalid": ("The rollback request does not carry a rollback record that an apply of this store "
                         "returned.", "Send the rollback record from the apply result unchanged, with its approval.",
                         RETRY_AFTER_FIX, CALLER),
    "stale_rollback": ("The store no longer holds the state this rollback would replace, so nothing changed.",
                       "Read the store's current state, then plan a change from it instead of rolling back.",
                       DO_NOT_RETRY, CALLER),
    "rollback_mismatch": ("The rollback would not restore the digest it records, so nothing was changed.",
                          "Keep the rollback record and report the detail to whoever maintains this store.",
                          DO_NOT_RETRY, OPERATOR),
})


#: This envelope never sends a step again itself: an engine failure moves to the next declared engine as
#: a fallback decision, and every refusal goes back to its caller with its next action.
RECOVERY_POLICY = EnvelopeRecoveryPolicy(SLOT_ID, 0, ())


def refusal_for(code: str) -> EnvelopeRefusal:
    """The envelope refusal of one closed failure code; nothing has been written when any of them is raised."""
    message, next_action, retry, by = REFUSAL_GUIDANCE[code]
    return envelope_refusal(code, message, next_action, retry=retry, next_action_by=by)


def guidance_gaps(table=REFUSAL_GUIDANCE) -> list:
    """Every failure code without wording, and every worded code the contract does not have."""
    return sorted(set(FAILURE_CODES) ^ set(table))


# The handshake layer: one verdict for each screened installation.

def capability_names(declaration) -> tuple:
    """What one engine declaration offers, named as handshake capabilities."""
    return tuple(f"profile:{profile}" for profile in declaration.profiles) + (
        ("blank_nodes",) if declaration.blank_nodes else ())


def required_capabilities(planning_input) -> tuple:
    """What one planning input needs of an engine."""
    return (f"profile:{planning_input.profile}",) + (("blank_nodes",) if planning_input.has_blank_nodes else ())


def handshake_for(installation, declaration, descriptor, planning_input, granted_effects):
    """The handshake verdict of one installation: request version, capabilities and effects, never inferred."""
    request = EnvelopeHandshakeRequest(SLOT_ID, (REQUEST_RECORD_TYPE,), required_capabilities(planning_input), (),
                                       tuple(granted_effects))
    offered = EnvelopeHandshakeDeclaration(installation.installation_id,
                                           tuple(descriptor.supported_edge_contracts), capability_names(declaration),
                                           tuple(declaration.effects))
    return negotiate_handshake(request, offered)


# The preflight layer: the selected engine is still available just before it is dispatched.

def _engine_still_available(context):
    available, _reason = context["engine"].availability()
    return None if available else refusal_for("engine_unavailable")


PREFLIGHT_CHECKS = (EnvelopePreflightCheck("the_selected_engine_is_still_available", ("engine_unavailable",),
                                           _engine_still_available),)


# The tracking layer: a retried apply is answered with its first result while the store still holds it.

def apply_identity(plan_digest_value: str, approval_ref: str) -> str:
    """The request identity of one apply: the plan and the approval that authorized it."""
    return request_identity_digest({"plan_digest": plan_digest_value, "approval_ref": approval_ref})


def _first_result(entry: dict) -> dict:
    return {"record_type": APPLY_RESULT_RECORD_TYPE, "applied": True, "plan_digest": entry["plan_digest"],
            "previous_digest": entry["before"], "new_digest": entry["after"], "approval_ref": entry["approval_ref"],
            "rollback": entry["rollback"]}


def replayed_apply(journal: list, state: dict, plan: dict, approval_ref: str) -> "dict | None":
    """The first result of this exact apply when the store's current state is still the one it wrote.

    The store's journal line is the intent and the outcome in one; whether its effect holds is observed
    from the store state itself, whose digest and sequence must be the ones that apply wrote. Any other
    case returns None, and the compare-and-swap refuses the request as stale."""
    lines = [entry for entry in journal if entry.get("operation") == APPLY_OPERATION
             and entry.get("plan_digest") == plan["plan_digest"] and entry.get("approval_ref") == approval_ref]
    if not lines:
        return None
    line, identity = lines[-1], apply_identity(plan["plan_digest"], approval_ref)
    holds = state.get("digest") == line.get("after") and state.get("sequence") == line.get("sequence")
    result = _first_result(line)
    intent = journal_intent((), component=SLOT_ID, request_identity=identity, repeatable=False, at=line["at"])
    observed = journal_reconciliation(
        (intent,), component=SLOT_ID, request_identity=identity,
        observed_effect_state=EFFECT_STATE_CONFIRMED if holds else EFFECT_STATE_NONE,
        result_digest=digest(result) if holds else "", at=line["at"])
    decision = journal_decision((intent, observed), identity)
    return result if decision.decision == ANSWER_FROM_FIRST_RESULT and decision.result_digest == digest(result) \
        else None
