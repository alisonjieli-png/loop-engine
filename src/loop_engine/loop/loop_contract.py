"""The standard Loop contract — ONE baseline spec every loop carries.

Architectural role: loop (the runtime's typed-interface affordance).

Owner doctrine (2026-08-23→24, escalating): "everything is a PractitionerLoop"
… "code nodes can be loops — call them code loops" … "some loops that are
pretty much deterministic DAGs should be set up as each node in the DAG
actually being a loop and inheriting loop capabilities" … "since all loops
have deterministic, hybrid, and non-deterministic runtimes and have clear
inputs and outputs, set up a standard loop class that everything inherits
or uses as a baseline template."  This module is that baseline made ONE
named object.

The insight to preserve, not blur: the RUNTIME mode vocabulary
(``recursive_loop.MODES``: deterministic / hybrid / non_deterministic) and
the EXECUTION vocabulary (``static_architecture.facets.EXECUTION_MODES``:
code_only / hybrid / model_led) are two projections of the SAME three modes
— ``recursive_loop.INTERNAL_MODE_NAMES`` already states this.  The contract
declares the loop's mode in the INTERNAL execution names (that is what a
capability search filters on) and DERIVES the runtime mode from it, so the
two never drift and neither is silently re-typed.

What a loop declares here, fail-closed, in one place:

  * ``input_roles`` / ``output_roles`` — the typed I/O contract.  A loop
    with a clear input and output is searchable, testable, and composable;
    these roles are the same names Code Intelligence facets use, so a
    capability query can match a loop's contract the way it matches a
    node's facets.
  * ``execution_mode`` — the mode classification (code_only / hybrid /
    model_led), from which the runtime ``deterministic / hybrid /
    non_deterministic`` waterfall is derived.
  * ``effects``, ``locality``, ``cost_class`` — the same closed facet
    vocabularies, validated by the one authority (``facets.code_facets``),
    never re-typed here.

A contract answers "is this loop composable into this slot?": its
output_roles must cover the slot's required input_roles, its execution mode
must be within the caller's allowed modes, and its effects must not violate
the caller's effect ceiling.  This is composition CHECK, not promotion —
compatibility is nominated by the contract and PROVEN by tests and the
evidence gate.

Owns:
    - LoopContract (dataclass): the one baseline typed + mode spec;
    - contract_for_code_loop(fn_name, ...): the standard template for
      turning one callable into a code loop's declared contract;
    - contract_compatible(contract, required_inputs, allowed_modes,
      effect_ceiling): fail-closed composability check.

Does not own:
    - the Loop runtime (recursive_loop), templates (loop_templates), the
      facet vocab authority (static_architecture.facets), or any semantic
      path — a code_only contract makes a semantic call impossible by
      construction downstream.

Key invariants:
    - execution_mode is validated fail-closed against the closed vocabulary;
    - the runtime mode waterfall is DERIVED from execution_mode, never
      hand-specified twice;
    - a contract missing required input_roles, an out-of-window mode, or an
      over-ceiling effect is INELIGIBLE — fail-closed, never warned-and-passed.

Verification: self_test() — positive contract build + compatibility, and
adversarial (bad mode refused, mode mismatch ineligible, effect over
ceiling ineligible, missing contract means not composable).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..static_architecture.facets import (EXECUTION_MODES, LOCALITY,
                                          COST_CLASSES, EFFECTS)

#: runtime mode name  <-  internal execution-mode name (the ONE map).
_EXECUTION_TO_RUNTIME_MODE = {"code_only": "deterministic",
                              "hybrid": "hybrid",
                              "model_led": "non_deterministic"}

#: the default per-mode waterfall, cheapest-first (the regime doctrine).
_MODE_WATERFALL = {"code_only": ("code_only",),
                   "hybrid": ("code_only", "hybrid"),
                   "model_led": ("code_only", "hybrid", "model_led")}


class LoopContractError(ValueError):
    """A loop contract is misconfigured or a composability check failed closed."""


@dataclass(frozen=True)
class LoopContract:
    """The ONE baseline typed + mode spec every loop carries.

    Immutable: a contract is a property of the loop's identity, not state
    that drifts mid-run.  ``input_roles`` / ``output_roles`` are the typed
    I/O; ``execution_mode`` is the mode classification; the rest are the
    closed facet vocabs.
    """
    name: str
    execution_mode: str                       # code_only | hybrid | model_led
    input_roles: tuple = ()
    output_roles: tuple = ()
    effects: tuple = ("pure",)
    locality: str = "local_machine"
    cost_class: str = "free"
    role: str = ""

    def __post_init__(self):
        if self.execution_mode not in EXECUTION_MODES:
            raise LoopContractError(
                f"execution_mode {self.execution_mode!r} not in "
                f"{EXECUTION_MODES}")
        if self.locality not in LOCALITY:
            raise LoopContractError(
                f"locality {self.locality!r} not in {LOCALITY}")
        if self.cost_class not in COST_CLASSES:
            raise LoopContractError(
                f"cost_class {self.cost_class!r} not in {COST_CLASSES}")
        bad = [e for e in self.effects if e not in EFFECTS]
        if bad:
            raise LoopContractError(f"effects {bad} not in {EFFECTS}")
        if "pure" in self.effects and len(self.effects) > 1:
            raise LoopContractError("'pure' excludes every other effect")
        if not self.output_roles:
            raise LoopContractError(
                "a loop must declare at least one output role — a loop with "
                "no output is not composable")

    @property
    def runtime_mode(self) -> str:
        """The recursive_loop.MODES name, derived — never declared twice."""
        return _EXECUTION_TO_RUNTIME_MODE[self.execution_mode]

    @property
    def mode_waterfall(self) -> tuple:
        """Cheapest-first execution path for this loop's mode."""
        return _MODE_WATERFALL[self.execution_mode]


def contract_for_code_loop(name: str, *, input_roles=(), output_roles=(),
                           effects=("pure",), locality="local_machine",
                           cost_class="free", role="") -> LoopContract:
    """The standard template for placing functional code into a standard
    loop object: one callable becomes a "code loop" whose contract is
    code_only (deterministic preferred), with its typed I/O declared.
    Escalating to hybrid/model_led is a NEW contract, not an edit."""
    return LoopContract(name=name, execution_mode="code_only",
                        input_roles=tuple(input_roles),
                        output_roles=tuple(output_roles),
                        effects=tuple(effects), locality=locality,
                        cost_class=cost_class, role=role)


def contract_compatible(contract: "LoopContract | None", *,
                        required_inputs=(), allowed_modes=EXECUTION_MODES,
                        effect_ceiling=EFFECTS) -> tuple:
    """(compatible, reasons).  Fail-closed in every direction:

    - a MISSING contract is not composable (no interface, no slot);
    - output_roles must cover the slot's required_inputs;
    - execution_mode must be inside allowed_modes;
    - every effect must be inside effect_ceiling.
    Compatibility is NOMINATION; the evidence gate still admits.
    """
    if contract is None:
        return False, ["no contract declared — fail-closed: not composable"]
    reasons = []
    for r in tuple(required_inputs):
        if r not in contract.output_roles:
            reasons.append(f"missing required output role {r!r}")
    if contract.execution_mode not in tuple(allowed_modes):
        reasons.append(f"mode {contract.execution_mode!r} outside allowed "
                       f"{tuple(allowed_modes)!r}")
    over = [e for e in contract.effects if e not in tuple(effect_ceiling)]
    if over:
        reasons.append(f"effects {over} over ceiling {tuple(effect_ceiling)!r}")
    return (not reasons), reasons


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # 1. POSITIVE — a code loop gets a standard contract; runtime mode is
    #    DERIVED and the waterfall is cheapest-first.
    c = contract_for_code_loop("impute-column", input_roles=("clean_table_req",),
                               output_roles=("clean_table",), role="transform")
    ok, why = contract_compatible(c, required_inputs=("clean_table",),
                                  allowed_modes=("code_only",),
                                  effect_ceiling=("pure",))
    check("code_loop_contract_derives_mode_and_is_composable",
          c.execution_mode == "code_only"
          and c.runtime_mode == "deterministic"
          and c.mode_waterfall == ("code_only",)
          and ok and not why,
          f"{c.name}: code_only -> deterministic, composable")

    # 2. the two mode vocabularies NEVER conflate — hybrid and model_led
    #    derive their runtime names correctly, and the waterfall stays cheap.
    hb = LoopContract(name="repair", execution_mode="hybrid",
                      output_roles=("fix",))
    ml = LoopContract(name="plan", execution_mode="model_led",
                      output_roles=("plan",))
    check("internal_and_runtime_modes_map_not_conflate",
          hb.runtime_mode == "hybrid" and hb.mode_waterfall == ("code_only",
                                                                "hybrid")
          and ml.runtime_mode == "non_deterministic"
          and ml.mode_waterfall[0] == "code_only",
          "hybrid -> hybrid; model_led -> non_deterministic; cheapest-first")

    # 3. ADVERSARIAL — a bad execution_mode is refused at construction.
    refused = False
    try:
        LoopContract(name="x", execution_mode="magic", output_roles=("y",))
    except LoopContractError:
        refused = True
    check("unknown_execution_mode_refused_fail_closed", refused)

    # 4. ADVERSARIAL — a loop with NO declared output is refused.
    refused = False
    try:
        LoopContract(name="x", execution_mode="code_only")
    except LoopContractError:
        refused = True
    check("loop_with_no_output_role_refused", refused)

    # 5. ADVERSARIAL — compatibility fails closed in each direction.
    no_contract, _ = contract_compatible(None, required_inputs=("y",))
    wrong_slot, _ = contract_compatible(c, required_inputs=("model_artifact",))
    wrong_mode, _ = contract_compatible(ml, allowed_modes=("code_only",))
    net = LoopContract(name="scrape", execution_mode="code_only",
                       output_roles=("rows",), effects=("network",))
    over_fx, _ = contract_compatible(net, effect_ceiling=("pure",))
    check("compatibility_fails_closed_on_missing_contract_slot_mode_effect",
          not no_contract and not wrong_slot and not wrong_mode and not over_fx,
          "no contract / missing role / wrong mode / over-ceiling effect")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
