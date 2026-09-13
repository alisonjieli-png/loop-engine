#!/usr/bin/env python3
"""Decomposition strategies: several shapes, chosen per task, including none.

One decomposition shape does not fit every task.  A data pipeline wants
sequential stages; a library wants independent components integrated last; a
document wants draft-critique-revise; an optimisation wants several candidates
scored against each other.  Forcing all of them through one shape produces
units that are awkward at best and unsolvable at worst.

Two findings from the literature shape this module and are worth stating,
because both cut against the obvious design:

* **Decompose as needed, not to a fixed depth.**  ADaPT (arXiv:2311.05772)
  decomposes based on task complexity and *executor capability* rather than a
  preset structure.  What is one unit for a strong model is three for a weak
  one, so granularity is a function of who is solving.
* **Imposed structure is not free.**  The instance-level Self-Discover study
  (arXiv:2507.03347) found unstructured reasoning beating structured plans by
  up to 18.9%, and a single-agent baseline matched multi-agent workflows at
  lower cost (arXiv:2602.04853 reports decomposition's accuracy benefit
  shrinking as models grow).  So NONE is a real strategy, not a fallback, and
  a task that fits in one unit should stay in one unit.

Every strategy below emits the same record shape, so the validator, the
dependency ordering and the overnight queue are shared.  Adding a strategy is
adding a prompt and a name, not a new runtime.
"""
from __future__ import annotations

STRATEGIES = {
    "pipeline": {
        "when": "output of each stage feeds the next: parsing, transforming, "
                "aggregating, rendering",
        "shape": "a linear or near-linear chain; each unit consumes the "
                 "previous unit's output contract",
        "guidance": "Write the EXACT data contract between consecutive "
                    "units as a literal example, not a description. Measured "
                    "2026-09-05: a scheduler unit returned {'a': 2, 'b': 7} "
                    "(finish times) while the next unit and the constraint "
                    "checker both expected {'a': {'start': 0, 'end': 2}}. "
                    "Both shapes are defensible; neither could consume the "
                    "other, and the mismatch was invisible until the "
                    "downstream unit ran. Every unit's task text must show a "
                    "literal example of what it RECEIVES and what it "
                    "RETURNS. Prefer more, smaller stages.",
    },
    "components": {
        "when": "several capabilities that do not depend on each other, "
                "assembled at the end: a library, a toolkit, a set of "
                "endpoints",
        "shape": "a wide fan of independent units plus one final integration "
                 "unit depending on all of them",
        "guidance": "Units must not reference each other's internals -- only "
                    "their public contracts. The integration unit is the only "
                    "one allowed to know they all exist.",
    },
    "spec_first": {
        "when": "requirements are precise and disputable: a parser, a "
                "protocol, a calculation with edge cases",
        "shape": "unit 1 writes the executable specification (tests, "
                "examples, invariants); later units implement against it",
        "guidance": "The specification unit must NOT hand-compute expected "
                    "values for anything with multi-step arithmetic -- state "
                    "invariants and relations instead (f(a+b) == f(a)+f(b)). "
                    "Measured 2026-09-05: a model wrote a correct parser and "
                    "incorrect constants, then condemned the correct parser.",
    },
    "refine": {
        "when": "the deliverable is prose or a plan whose quality improves by "
                "revision: a report, a design, a proposal",
        "shape": "draft, then critique against stated criteria, then revise; "
                "each a separate unit",
        "guidance": "The critique unit must judge against criteria written "
                    "BEFORE the draft, or it will simply approve what it "
                    "sees. State the criteria in unit 1.",
    },
    "explore": {
        "when": "several plausible approaches exist and the best is not "
                "known: an algorithm choice, a layout, a schema",
        "shape": "N independent candidate units, then one comparison unit "
                 "that scores them on stated measures",
        "guidance": "Candidates must be generated without seeing each other, "
                    "or they collapse into variations of the first. The "
                    "comparison unit needs a measure that a machine can "
                    "compute.",
    },
    "checklist": {
        "when": "a known list of items must each be handled: an audit, a "
                "migration across files, a compliance pass",
        "shape": "one unit per item, all independent, plus a final "
                 "reconciliation unit",
        "guidance": "Enumerate the items exactly. If the list cannot be "
                    "enumerated up front, this is the wrong strategy -- use "
                    "pipeline with a discovery stage first.",
    },
    "none": {
        "when": "the task already fits in a single unit that one model call "
                "chain can solve and verify",
        "shape": "exactly one unit -- the task as given",
        "guidance": "This is a real answer, not a failure to decompose. "
                    "Splitting a small task adds context-passing overhead and "
                    "more places to fail, and decomposition's measured "
                    "benefit shrinks as models get stronger. Choose this "
                    "whenever the task is one coherent deliverable with one "
                    "verification.",
    },
}

SELECT_PROMPT = """Choose ONE decomposition strategy for this goal.

GOAL:
{goal}

EXECUTOR: a medium-capability model working unattended, which solves small
self-contained units reliably and large multi-part tasks poorly. Granularity
should suit THAT executor, not an ideal one.

STRATEGIES:
{catalogue}

Choosing "none" is correct whenever the goal is one coherent deliverable with
one verification -- splitting such a task makes it harder, not easier.

Return ONLY: {{"strategy": "<name>", "reason": "<one sentence>"}}
"""


def catalogue_text() -> str:
    lines = []
    for name, spec in STRATEGIES.items():
        lines.append(f"- {name}: use when {spec['when']}. Shape: {spec['shape']}.")
    return "\n".join(lines)


def strategy_prompt(name: str) -> str:
    """The extra guidance a chosen strategy contributes to the divide prompt."""
    spec = STRATEGIES.get(name)
    if not spec:
        return ""
    return (f"DECOMPOSITION STRATEGY: {name}\n"
            f"Shape: {spec['shape']}\n"
            f"{spec['guidance']}\n")


def self_test() -> dict:
    results = []

    def check(name, ok, detail=""):
        results.append({"name": name, "passed": bool(ok), "detail": detail})

    check("every_strategy_declares_all_three_fields",
          all({"when", "shape", "guidance"} <= set(v)
              for v in STRATEGIES.values()))
    check("none_is_a_first_class_strategy", "none" in STRATEGIES)
    check("none_is_framed_as_a_real_answer",
          "not a failure" in STRATEGIES["none"]["guidance"])
    check("spec_first_warns_against_hand_computed_constants",
          "invariants" in STRATEGIES["spec_first"]["guidance"])
    check("explore_requires_a_machine_computable_measure",
          "machine can compute" in STRATEGIES["explore"]["guidance"])
    check("catalogue_lists_every_strategy",
          all(n in catalogue_text() for n in STRATEGIES))
    check("prompt_for_unknown_strategy_is_empty",
          strategy_prompt("no_such_strategy") == "")
    check("prompt_for_known_strategy_carries_guidance",
          "Shape:" in strategy_prompt("pipeline"))
    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


if __name__ == "__main__":
    import json
    r = self_test()
    print(f"strategies self_test: {r['passed']}/{r['total']}")
    for t in r["tests"]:
        if not t["passed"]:
            print("  FAIL:", t["name"])
    print(f"\n{len(STRATEGIES)} strategies:")
    print(catalogue_text())
