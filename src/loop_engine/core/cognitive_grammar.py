"""The cognitive vocabulary this runtime actually has, and what it lacks.

The Practitioner runs one fixed sequence of kernel nodes. That sequence is
useful and it is not the same thing as a cognitive architecture: it is one
profile, and nothing in the repository said so, named the alternatives, or
gave a run any way to report that the operation it needed did not exist.

A live run on 2026-09-02 made the cost of the last of those concrete. The
model wrote a file with a syntax error, was told the line, concluded it should
read the file, and found no operator that could. It restated that correct
conclusion for twenty passes. The cycle was not too short and the recovery
ladder was not missing; it ran soft reset and cold restart on schedule. What
was missing was one operator, and the run had no way to say so. Nothing in
the record distinguished "this model reasons badly" from "this catalog has a
hole", which is the distinction a system that intends to improve most needs.

This module is the vocabulary made explicit and inspectable:

  - The operator catalog is *derived* from the kernel nodes, action kinds and
    capabilities the runtime really has. It is not a second list to maintain,
    because a second list drifts and the drift is silent.
  - Cycle profiles are named, versioned skip sets over the canonical nodes.
    They compose with the kernel's existing per-pass skipping rather than
    introducing a second sequencer, and a profile may never skip a required
    node.
  - The transition table states the whole algebra a network of Loops would
    need and marks each entry realized or not, with the mechanism or the
    reason. An honest map of what is missing is worth more than a longer list
    of what exists.
  - The gap report is the channel the failing run lacked: a caller may name
    the operation it needed and could not reach, and that lands in the run
    record beside what it did use.

Nothing here decides anything. It names, it never gates: no profile is
imposed, no operator is withheld, and a reported gap is evidence for a person,
not an instruction to the runtime.

Owns:
    - cognitive_operators(): the derived catalog.
    - CYCLE_PROFILES and profile_skip_set(): named node profiles.
    - TRANSITIONS: the algebra with its realization state.
    - admitted_gap_report(): the missing-operator channel.

Does not own: the kernel sequence (loop.kernel), the action vocabulary or
capabilities (core.adaptive_practitioner_records), the routes
(core.adaptive_practitioner_validation), or the tally that carries reported
gaps into saved history (core.option_selection).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..loop.kernel import (KERNEL_NODES, KERNEL_NODE_QUESTIONS,
                           KERNEL_OPTIONAL_NODES, KERNEL_REQUIRED_NODES)
from .adaptive_practitioner_validation import MODEL_ROUTE_VALUES

COGNITIVE_GRAMMAR_VERSION = "cognitive_grammar/v1"
OPERATOR_GAP_RECORD_TYPE = "operator_gap_report/v1"


class CognitiveGrammarError(ValueError):
    """A grammar record violated its typed contract."""


def cognitive_operators() -> dict:
    """Every operation this runtime can actually perform, by where it lives.

    Derived on call from the live sources. A hand-written copy of this would
    describe the runtime as it was when someone last edited the copy, which
    is exactly the failure mode this catalog exists to expose.
    """
    from .adaptive_practitioner_records import (ADAPTIVE_CAPABILITIES,
                                                NEXT_ACTION_KINDS)
    operators = {}
    for node in KERNEL_NODES:
        operators[f"node:{node}"] = {
            "operator": node,
            "realized_by": "kernel node",
            "required": node in KERNEL_REQUIRED_NODES,
            "skippable": node in KERNEL_OPTIONAL_NODES,
            "question": KERNEL_NODE_QUESTIONS.get(node, ""),
        }
    for kind in NEXT_ACTION_KINDS:
        operators[f"action:{kind}"] = {
            "operator": kind,
            "realized_by": "next action kind",
            "required": False,
            "skippable": True,
            "question": "",
        }
    for item in ADAPTIVE_CAPABILITIES:
        ref = str(item.get("capability_ref") or "")
        operators[f"capability:{ref}"] = {
            "operator": ref,
            "realized_by": "capability",
            "required": False,
            "skippable": True,
            "question": str(item.get("purpose") or "")[:200],
        }
    return operators


#: Named node profiles. A profile is a claim about which optional reasoning a
#: pass can do without, never about what the model may choose; every operator
#: and every portfolio option stays on offer under all of them. Profiles are
#: candidates to compare, not defaults to impose: only `full` is in use, and
#: the rest exist so that "does a shorter cycle do as well here" is a question
#: the repository can answer with a measurement rather than an opinion.
CYCLE_PROFILES = {
    "full": {
        "version": "1.0.0",
        "skip": (),
        "suits": "the default; every optional node runs",
    },
    "compact_action": {
        "version": "1.0.0",
        "skip": ("frame_alternatives", "reconcile_horizon",
                 "forecast_outcome", "calibrate"),
        "suits": ("a bounded action on a task already understood, where the "
                  "cost of framing and forecasting exceeds what they would "
                  "change"),
    },
    "experiment": {
        "version": "1.0.0",
        "skip": ("standardize_task", "reconcile_horizon"),
        "suits": ("a hypothesis under test, where forecasting and "
                  "calibration are the point and re-standardising is not"),
    },
    "repair": {
        "version": "1.0.0",
        "skip": ("frame_alternatives", "standardize_task",
                 "reconcile_horizon"),
        "suits": ("a known failure with a known cause, where the task is "
                  "settled and only the fix is open"),
    },
    "orientation": {
        "version": "1.0.0",
        "skip": ("forecast_outcome", "calibrate", "integrate_commit"),
        "suits": ("a first pass on an unfamiliar task, where framing and "
                  "horizon matter and there is not yet a result to commit"),
    },
}


def profile_skip_set(profile_id: str) -> tuple:
    """Return the optional nodes a profile skips, refusing an invalid one.

    A profile that named a required node would silently produce a pass that
    never oriented, decided, or verified. The kernel would refuse it at run
    time; refusing it here says which profile was wrong.
    """
    profile = CYCLE_PROFILES.get(str(profile_id))
    if profile is None:
        raise CognitiveGrammarError(
            f"unknown cycle profile {profile_id!r}; the profiles are "
            f"{sorted(CYCLE_PROFILES)}")
    skip = tuple(profile["skip"])
    forbidden = [node for node in skip if node in KERNEL_REQUIRED_NODES]
    if forbidden:
        raise CognitiveGrammarError(
            f"cycle profile {profile_id!r} would skip required nodes "
            f"{forbidden}; only {list(KERNEL_OPTIONAL_NODES)} may be skipped")
    unknown = [node for node in skip if node not in KERNEL_NODES]
    if unknown:
        raise CognitiveGrammarError(
            f"cycle profile {profile_id!r} names nodes that do not exist: "
            f"{unknown}")
    return skip


#: The transition algebra a Loop network needs, and what this runtime has of
#: it. An entry is realized when a live mechanism performs it; the rest are
#: named so the distance between the design and the runtime is a fact in the
#: repository rather than an impression. Adding a name here realizes nothing.
TRANSITIONS = {
    "NEXT": ("realized", "route 'continue'"),
    "REPEAT": ("realized", "route 'retry'"),
    "REPAIR": ("realized", "route 'repair' and action kind REPAIR"),
    "FORK": ("realized", "route 'explore_branch'"),
    "REFRAME": ("realized", "route 'reframe'"),
    "SOFT_RESET": ("realized", "escalation ladder"),
    "COLD_RESTART": ("realized", "escalation ladder"),
    "TERMINATE_TASK": ("realized", "routes 'stop_success', 'stop_unprofitable'"),
    "SPAWN": ("realized", "Loop.spawn and action kind SPAWN_LOOP"),
    "QUERY": ("realized", "action kind RETRIEVE_INTELLIGENCE"),
    "RETRIEVE": ("realized", "action kind RECALL_MEMORY"),
    "DELEGATE": ("realized", "action kind SPAWN_LOOP with a contract"),
    "RACE": ("realized", "action kind RUN_PARALLEL"),
    "JOIN": ("realized", "action kind JOIN_RESULTS"),
    "CHALLENGE": ("realized", "action kind VERIFY"),
    "ESCALATE": ("realized", "action kind REQUEST_AUTHORITY and supervision"),
    "PAUSE": ("realized", "action kind ASK_USER"),
    "ABSTAIN": ("realized", "action kind ABSTAIN"),
    "GOTO": ("not_realized", "a pass is acyclic; there is no jump target"),
    "REVISIT": ("not_realized",
                "reframe restarts a pass rather than returning to one node"),
    "BACKTRACK": ("not_realized",
                  "reframe and cold restart step back, but not to a named "
                  "checkpoint chosen by the model"),
    "ROLLBACK": ("not_realized",
                 "state is derived forward; there is no compensating "
                 "transition to a prior trusted state"),
    "RESUME": ("not_realized",
               "Run History replays a finished run; it does not resume a "
               "stopped one mid-pass"),
    "RECONTEXTUALIZE": ("not_realized",
                        "context is compiled per call; a model cannot ask "
                        "for recompilation and retry the same operator"),
    "DEESCALATE": ("not_realized", "no route returns to a cheaper model"),
    "TOURNAMENT": ("not_realized", "no multi-round candidate elimination"),
    "VOTE": ("not_realized", "no discrete candidate selection transition"),
    "ENSEMBLE": ("not_realized",
                 "COMPOSE_SOLUTION composes capabilities, not verified "
                 "candidate outputs"),
    "RETURN_INCUMBENT": ("not_realized",
                         "a run returns once; there is no return-and-continue"),
    "TERMINATE_BRANCH": ("not_realized",
                         "explore_branch opens a branch; nothing closes one "
                         "independently of the run"),
    "REPLAN": ("not_realized",
               "reframe replaces the approach; there is no plan object to "
               "replace on its own"),
}


@dataclass
class OperatorGapReport:
    """One operation a caller needed and could not reach.

    The failing run's whole problem, reduced to a record. It carries what was
    wanted, what was tried, and what the runtime said, so a reader can tell a
    missing operator from a model that did not look.
    """

    needed: str
    tried: tuple = ()
    runtime_said: str = ""
    step: str = ""

    def __post_init__(self) -> None:
        if not str(self.needed or "").strip():
            raise CognitiveGrammarError(
                "an operator gap must say what was needed")

    def to_dict(self) -> dict:
        return {
            "record_type": OPERATOR_GAP_RECORD_TYPE,
            "needed": str(self.needed)[:400],
            "tried": [str(item)[:200] for item in self.tried],
            "runtime_said": str(self.runtime_said)[:600],
            "step": str(self.step),
        }


def admitted_gap_report(value, step: str = "") -> "dict | None":
    """Admit a reported gap, keeping only what a reader could act on.

    A gap naming an operator that does exist is kept and marked, because a
    caller that could not find a present operator is itself a finding about
    the prompt rather than about the catalog.
    """
    if not isinstance(value, dict):
        return None
    needed = str(value.get("needed") or "").strip()
    if not needed:
        return None
    tried = value.get("tried")
    report = OperatorGapReport(
        needed=needed,
        tried=tuple(tried) if isinstance(tried, (list, tuple)) else (),
        runtime_said=str(value.get("runtime_said") or ""),
        step=step).to_dict()
    catalog = cognitive_operators()
    names = {item["operator"] for item in catalog.values()}
    report["names_an_existing_operator"] = needed in names
    return report


def grammar_snapshot() -> dict:
    """What the runtime's cognitive vocabulary is, counted and stated."""
    operators = cognitive_operators()
    realized = [name for name, (state, _why) in TRANSITIONS.items()
                if state == "realized"]
    missing = [name for name, (state, _why) in TRANSITIONS.items()
               if state != "realized"]
    return {
        "record_type": COGNITIVE_GRAMMAR_VERSION,
        "operators": len(operators),
        "operators_by_realization": {
            kind: sum(1 for item in operators.values()
                      if item["realized_by"] == kind)
            for kind in sorted({item["realized_by"]
                                for item in operators.values()})},
        "kernel_nodes": len(KERNEL_NODES),
        "required_nodes": len(KERNEL_REQUIRED_NODES),
        "optional_nodes": len(KERNEL_OPTIONAL_NODES),
        "cycle_profiles": sorted(CYCLE_PROFILES),
        "routes": list(MODEL_ROUTE_VALUES),
        "transitions_realized": sorted(realized),
        "transitions_not_realized": sorted(missing),
        "note": ("profiles and transitions are named here; only the routes "
                 "and the realized transitions execute"),
    }


def self_test() -> dict:
    """Prove the catalog is derived, the profiles are safe, and gaps land."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    from .adaptive_practitioner_records import (ADAPTIVE_CAPABILITIES,
                                                NEXT_ACTION_KINDS)
    operators = cognitive_operators()
    check("the_catalog_is_derived_from_every_live_source",
          len(operators) == (len(KERNEL_NODES) + len(NEXT_ACTION_KINDS)
                             + len(ADAPTIVE_CAPABILITIES))
          and all(f"node:{node}" in operators for node in KERNEL_NODES)
          and all(f"action:{kind}" in operators
                  for kind in NEXT_ACTION_KINDS),
          f"{len(operators)} operators")

    # A profile is a claim about optional work. One that skipped a required
    # node would produce a pass that never oriented or verified, and the
    # profile is where that must be caught, not the run.
    check("no_profile_skips_a_required_node",
          all(not set(profile_skip_set(name)) & set(KERNEL_REQUIRED_NODES)
              for name in CYCLE_PROFILES),
          str({name: profile_skip_set(name) for name in CYCLE_PROFILES}))
    check("every_profile_names_nodes_that_exist",
          all(set(profile_skip_set(name)) <= set(KERNEL_NODES)
              for name in CYCLE_PROFILES))
    check("the_default_profile_skips_nothing",
          profile_skip_set("full") == ())

    refused = 0
    for bad in ("nonexistent_profile",):
        try:
            profile_skip_set(bad)
        except CognitiveGrammarError:
            refused += 1
    check("an_unknown_profile_is_refused_by_name", refused == 1)

    # Every realized transition must name a mechanism, and every unrealized
    # one must say why. A blank either way would let the map drift into
    # decoration.
    check("every_transition_states_a_mechanism_or_a_reason",
          all(state in ("realized", "not_realized") and str(why).strip()
              for state, why in TRANSITIONS.values()),
          f"{len(TRANSITIONS)} transitions")
    check("the_routes_the_runtime_admits_are_all_realized_transitions",
          len([1 for state, _why in TRANSITIONS.values()
               if state == "realized"]) >= len(MODEL_ROUTE_VALUES),
          f"{len(MODEL_ROUTE_VALUES)} routes")

    # The channel the failing run did not have.
    gap = admitted_gap_report({
        "needed": "read back a file this run generated",
        "tried": ["core.source.inspect", "core.generated_project"],
        "runtime_said": "source inspection requested unknown paths"},
        step="how")
    check("a_missing_operator_can_be_reported_with_what_was_tried",
          gap["needed"].startswith("read back")
          and gap["tried"] == ["core.source.inspect",
                               "core.generated_project"]
          and gap["step"] == "how",
          str(gap)[:160])
    check("a_gap_naming_an_operator_that_exists_is_marked_as_such",
          admitted_gap_report({"needed": "core.workspace.read"})[
              "names_an_existing_operator"] is True
          and gap["names_an_existing_operator"] is False,
          "a caller that missed a present operator is a prompt finding")
    check("an_empty_or_malformed_gap_report_costs_nothing",
          admitted_gap_report(None) is None
          and admitted_gap_report({}) is None
          and admitted_gap_report({"needed": "   "}) is None)

    snapshot = grammar_snapshot()
    check("the_snapshot_states_what_does_not_execute",
          snapshot["transitions_not_realized"]
          and "only the routes" in snapshot["note"],
          f"{len(snapshot['transitions_not_realized'])} unrealized")

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "cognitive_grammar_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
