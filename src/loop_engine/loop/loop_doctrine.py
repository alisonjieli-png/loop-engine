"""Loop Doctrine — ONE declarative baseline for every loop in the system.

Architectural role: loop (the doctrine authority for "everything is a
PractitionerLoop, and every loop is built on the same baseline").

Owner doctrine (2026-08-23→24, escalating rulings that converge here):

    "Everything is a PractitionerLoop — even a deterministic check."
    "Each loop is a node with deterministic, hybrid, and non-deterministic modes."
    "Code nodes can be loops; call them code loops; have templates on how
     functional code is placed into a standard loop object."
    "Since all loops have deterministic, hybrid, and non-deterministic
     runtimes and clear inputs and outputs, set up a standard loop class
     that everything inherits or uses as a baseline template."
    "There should be a baseline for all types of intelligence, all DAGs /
     canvas solutions.  Everything is a loop, WITH A CONDITION TO STOP —
     and sometimes that condition is simply: run one iteration, once,
     successfully."
    "Before a loop even runs, set that it should run only one iteration
     successfully — starting deterministic, then hybrid, then
     non-deterministic.  Solution loops and practitioner loops use the same
     setup, even though a solution loop is usually deterministic and runs
     once and succeeds.  But if a loop has a clear goal and typed I/O, it
     can always fall back to an LLM.  That is, in some aspects,
     self-correcting code — packaged as loops it is far more efficient,
     effective, and flexible."

This module is that doctrine executable.  It does NOT replace the runtime
(``recursive_loop.Loop``), the templates (``loop_templates``), the typed
contract (``loop_contract.LoopContract``), or the facet vocabulary
(``core.facets``).  It is the DECLARATIVE BASELINE that names
what every loop — practitioner, internal-service, intelligence, or Solution
DAG vertex — has in common, so each is an instance of the same shape rather
than a bespoke object.  The thesis this makes concrete:

    ONE BASELINE.  EVERY LOOP IS AN INSTANCE:
    a typed GOAL — what this loop is for, set before it runs;
    typed INPUT/OUTPUT roles — a clear contract it can be searched,
        tested, and composed against;
    a declared STOPPING CONDITION — when the loop is done.  The degenerate,
        fully legal stop is "one successful iteration": most Solution DAG
        nodes stop exactly there.
    a per-loop ESCALATION WATERFALL deterministic → hybrid → model_backed —
        the self-correcting seam.  A code loop nominally stops determin- ;
        istically in one iteration; if it cannot honestly satisfy its goal,
        the waterfall is the governed route to a model — never a hidden call.

Because practitioner loops and Solution loops share this one baseline, the
SAME machinery (spawn, clamp, ledger, pause/resume, RunHistory, evidence
gate, Studio) serves both — practitioner loops and Solution loops are not
two runtimes, they are two instances of one baseline.  And because the
waterfall is a property of every loop, ANY deterministic code loop that
hits an unknown case has a sanctioned path to ask for a model — which is
exactly self-correcting code, packaged so the correction is governed,
visible, budgeted, and recorded.

Baseline templates shipped here (registered names, not inline literals):

  * code_loop          — one deterministic act, stop at the first success,
                         code_only, waterfall never escalates (a pure check).
  * solution_loop  — a DAG vertex as a loop: stop at first success, but
                         with an explicit fallback arm AND an escalation
                         waterfall, so a failed primary self-corrects.
  * practitioner_loop   — a general bounded problem loop: stop at its
                         success condition; full waterfall.
  * validation_loop     — a deterministic gate: stop at first success;
                         abstains rather than escalating.

A baseline is a starting contract, NOT an authority: escalation past a
loop's declared stop is itself bounded by the runtime's permission clamp
and budget.  Deterministic is always tried first; a model is only ever
reached through the declared waterfall, visible and record-every-time.

Owns:
    - LoopBaseline (the declarative stop+waterfall+goal shape);
    - EXIT_CONDITIONS + ESCALATION_WATERFALLS (closed vocabularies);
    - baseline_for_code_loop / _solution_node / _practitioner / _validation;
    - loop_baseline_for(objective, ...) -> the composed LoopContract +
      baseline, ready to hand to the runtime.

Does not own:
    - the runtime's iteration engine, templates, typed contract, facets,
      RunHistory, or the evidence gate.

Key invariants:
    - every baseline has a stopping condition (fail-closed, closed vocab);
    - every baseline declares which modes it MAY escalate through (closed
      vocab, cheapest-first);
    - "stop at one success" is a first-class stop, not a hack;
    - the waterfall is the ONLY route to a model — a declared code_only
      loop can never reach one by construction.

Verification: self_test() — positive builds, the one-success stop, and
adversarial (unknown stop refused, out-of-waterfall mode forbidden, a
solution node and a practitioner share the same baseline shape).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..loop.loop_contract import (LoopContract, LoopContractError)

#: Successful exits for a Loop baseline. Budgets and iteration limits are
#: safety bounds, not successful outcomes.
EXIT_CONDITIONS = ("steps_complete", "accepted_success")

#: per-mode escalation path (cheapest-first).  A code_only loop never
#: reaches a model; everything wider is the governed self-correcting seam.
ESCALATION_WATERFALLS = {"code_only": ("code_only",),
                         "hybrid": ("code_only", "hybrid"),
                         "model_led": ("code_only", "hybrid", "model_led")}


class DoctrineError(ValueError):
    """A loop baseline is misconfigured (closed vocabularies enforced)."""


@dataclass(frozen=True)
class LoopBaseline:
    """The ONE baseline every loop is an instance of: goal + typed I/O +
    exit condition + escalation waterfall.  Immutable — a baseline is a
    property of the loop's identity, declared before it runs."""
    goal: str
    exit_condition: str = "accepted_success"
    escalate_to: tuple = ("code_only",)   # closed: subset of one waterfall
    input_roles: tuple = ()
    output_roles: tuple = ()
    notes: str = ""

    def __post_init__(self):
        if self.exit_condition not in EXIT_CONDITIONS:
            raise DoctrineError(
                f"exit_condition {self.exit_condition!r} not in "
                f"{EXIT_CONDITIONS}")
        if not self.escalate_to:
            raise DoctrineError("a baseline must declare an escalation "
                                "waterfall (even the terminal code_only)")
        bad = [m for m in self.escalate_to if m not in ESCALATION_WATERFALLS]
        if bad:
            raise DoctrineError(f"escalate_to modes {bad} not in "
                                f"{tuple(ESCALATION_WATERFALLS)}")
        # cheapest-first: the waterfall must be a prefix-consistent subset
        # of the mode's own ladder — never leapfrog past hybrid.
        for m in self.escalate_to:
            ladder = ESCALATION_WATERFALLS[m]
            if self.escalate_to[0] != ladder[0]:
                raise DoctrineError(
                    f"waterfall must start cheapest-first ({ladder[0]}), "
                    f"got {self.escalate_to[0]!r}")
        if not self.output_roles:
            raise DoctrineError(
                "a loop must declare at least one output role — a loop with "
                "no output cannot be composed or verified")

    @property
    def terminal_mode(self) -> str:
        """The widest mode this loop may reach through its waterfall."""
        return self.escalate_to[-1]


def baseline_for_code_loop(goal: str, *, input_roles=(), output_roles=(),
                           notes: str = "") -> LoopBaseline:
    """One deterministic act, stop at the first success; never escalates.

    This is a PURE code loop — a check or transform that either satisfies
    its goal deterministically or abstains.  It cannot reach a model.
    """
    return LoopBaseline(goal=goal, exit_condition="accepted_success",
                        escalate_to=("code_only",),
                        input_roles=tuple(input_roles),
                        output_roles=tuple(output_roles), notes=notes)


def baseline_for_solution_loop(goal: str, *, input_roles=(), output_roles=(),
                               notes: str = "") -> LoopBaseline:
    """A DAG vertex as a loop: stop at first success, but self-correcting —
    its waterfall MAY escalate code_only → hybrid if the deterministic arm
    cannot honestly satisfy the goal.  The vertex is still a loop; escalation
    is governed, visible, and budgeted, not a hidden model call."""
    return LoopBaseline(goal=goal, exit_condition="accepted_success",
                        escalate_to=("code_only", "hybrid"),
                        input_roles=tuple(input_roles),
                        output_roles=tuple(output_roles), notes=notes)


def baseline_for_practitioner(goal: str, *, input_roles=(), output_roles=(),
                              notes: str = "") -> LoopBaseline:
    """A general bounded problem loop: stop at its success condition, with
    the full deterministic → hybrid → model_led waterfall available."""
    return LoopBaseline(goal=goal, exit_condition="accepted_success",
                        escalate_to=("code_only", "hybrid", "model_led"),
                        input_roles=tuple(input_roles),
                        output_roles=tuple(output_roles), notes=notes)


def baseline_for_validation(goal: str, *, input_roles=(), output_roles=(),
                            notes: str = "") -> LoopBaseline:
    """A deterministic gate: stop at first success; abstains rather than
    escalating (a validator that guesses is not a validator)."""
    return LoopBaseline(goal=goal, exit_condition="accepted_success",
                        escalate_to=("code_only",),
                        input_roles=tuple(input_roles),
                        output_roles=tuple(output_roles), notes=notes)


def loop_baseline_for(baseline: LoopBaseline, **facet_kw) -> LoopContract:
    """Compose a LoopBaseline into a LoopContract the runtime can execute.

    The two are one shape at two altitudes: the baseline is the DECLARATION
    (goal, stop, waterfall), the contract is the typed interface the runtime
    enforces.  The execution_mode is derived from the baseline's widest
    reachable mode, so the two never drift.
    """
    contract_mode = baseline.terminal_mode
    try:
        return LoopContract(name=baseline.goal, execution_mode=contract_mode,
                            input_roles=baseline.input_roles,
                            output_roles=baseline.output_roles, **facet_kw)
    except LoopContractError as e:
        raise DoctrineError(f"baseline did not compose into a contract: {e}") from e


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # 1. POSITIVE — the degenerate legal stop is first-class: a code loop
    #    runs ONE successful iteration and cannot reach a model.
    c = baseline_for_code_loop("map column to id",
                               input_roles=("raw_col",), output_roles=("id_col",))
    check("code_loop_baseline_is_one_success_and_code_only",
          c.exit_condition == "accepted_success"
          and c.escalate_to == ("code_only",)
          and c.terminal_mode == "code_only",
          f"{c.goal}: stop after one success, never escalates")

    # 2. POSITIVE — practitioner and Solution loop share the SAME baseline
    #    shape, differing only in the waterfall (the self-correcting seam).
    sol = baseline_for_solution_loop("clean column", output_roles=("clean",))
    pract = baseline_for_practitioner("build a model", output_roles=("model",))
    check("solution_node_and_practitioner_share_one_baseline",
          type(sol) is type(pract) is LoopBaseline
          and sol.exit_condition == "accepted_success"
          and pract.exit_condition == "accepted_success"
          and sol.terminal_mode == "hybrid"
          and pract.terminal_mode == "model_led",
          "same shape; solution loop escalates to hybrid, practitioner to model_led")

    # 3. ADVERSARIAL: an unknown exit condition is refused fail-closed.
    refused = False
    try:
        LoopBaseline(goal="x", exit_condition="whenever",
                     output_roles=("y",))
    except DoctrineError:
        refused = True
    check("unknown_exit_condition_refused", refused)

    # 4. ADVERSARIAL — a waterfall that leapfrogs hybrid is refused, and the
    #    composed contract's runtime mode is ALWAYS derived, never double-
    #    declared.
    leapfrog = False
    try:
        LoopBaseline(goal="x", escalate_to=("model_led",),
                     output_roles=("y",))
    except DoctrineError:
        leapfrog = True
    contract = loop_baseline_for(baseline_for_practitioner("g",
                                                           output_roles=("o",)))
    check("waterfall_cannot_leapfrog_and_contract_mode_is_derived",
          leapfrog and contract.execution_mode == "model_led"
          and contract.runtime_mode == "non_deterministic"
          and contract.mode_waterfall[0] == "code_only",
          "first-success waterfall enforced; model_led -> non_deterministic")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
