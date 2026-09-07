"""Structured execution state carried between composed steps.

WHAT THIS REPLACES
The first version passed the previous step's whole JSON reply forward, then
truncated it: ``carried = json.dumps(value)[:1200]``. Two problems, and the
truncation is the worse one. Growth is quadratic -- every step re-reads
everything before it -- and a cut at 1200 bytes removes whichever fact
happened to be printed last, silently, with no way for the next step to
know something was dropped.

THE MECHANISM
Each step receives exactly three things:

    P   the immutable procedural specification -- the step's own prompt
    S   the current structured state, a flat typed record
    O   the latest observation, the real output of the last command run

and returns a PATCH to S. The reasoning that produced the patch is not
carried forward; once the patch is validated and applied, it is gone. This
keeps prompt size bounded by the size of the state rather than by how long
the run has been going, which is the difference between a loop that can run
for twelve hours and one that cannot.

This follows SKILL.state (arXiv 2608.26263), which reports 16.2x fewer
cumulative tokens at a 100-step horizon against a stateful baseline. The
claim reproduced here is only the mechanism, not that number.

WHY A PATCH RATHER THAN A REPLACEMENT
A step that returns the whole next state can silently drop a field it did
not think about, and the run has no way to distinguish "deleted on purpose"
from "forgot to mention". A patch says what changed. Deletion has to be
spelled: ``None`` removes a key, which is the merge-with-null-deletion the
paper describes, and it is the only way to remove one.

WHY THE SCHEMA IS CLOSED
An unknown field in a patch is refused rather than stored. A state that
accepts anything becomes a second transcript within a few steps, and the
bound this exists to enforce is gone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any

#: The fields a run's state may hold. Closed on purpose: see the module
#: docstring. Adding a field is a reviewed change, not something a step can
#: do by mentioning a new key.
STATE_FIELDS = {
    "task": str,                    # the immutable ask, never patched
    "gate_command": str,            # how success is decided
    "reproduction": str,            # the one-line command that fails
    "observed_failure": str,        # what the gate actually printed
    "hypothesis": str,              # the current best explanation
    "ruled_out": list,              # explanations tested and rejected
    "files_examined": list,
    "files_changed": list,
    "commands_run": list,
    "unknowns": list,
    "blocked_on": str,              # non-empty means the run cannot proceed
    "verified": bool,
}

#: Fields a step may never patch. The task and the gate are the run's
#: identity: a step that could rewrite either could redefine success into
#: something it had already achieved.
IMMUTABLE_FIELDS = ("task", "gate_command")

#: How much of the state is allowed into a prompt. The whole point is a
#: bound; without one, list fields grow without limit and the state becomes
#: the transcript it replaced.
MAX_LIST_ITEMS = 12
MAX_TEXT_CHARS = 900


class StepStateError(ValueError):
    """A patch violated the state contract and was not applied."""


@dataclass(frozen=True)
class StepState:
    """One run's structured state. Immutable; patches produce new states."""

    values: dict = field(default_factory=dict)
    revision: int = 0

    @classmethod
    def start(cls, task: str, gate_command: str = "") -> "StepState":
        if not str(task).strip():
            raise StepStateError("a run's state must carry its task")
        return cls(values={"task": str(task), "gate_command": str(gate_command)},
                   revision=0)

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)

    def apply(self, patch: dict) -> "StepState":
        """Validate a patch and return the next state.

        ``None`` as a value deletes the key. Everything else replaces it.
        A list field is appended to rather than replaced, because a step
        that observed one more file should not erase the others by
        reporting only what it saw.
        """
        if not isinstance(patch, dict):
            raise StepStateError(
                f"a patch must be an object, not {type(patch).__name__}")
        unknown = sorted(set(patch) - set(STATE_FIELDS))
        if unknown:
            raise StepStateError(
                f"patch names fields that do not exist: {unknown}. The state "
                f"schema is closed; it holds {', '.join(sorted(STATE_FIELDS))}")
        frozen = sorted(set(patch) & set(IMMUTABLE_FIELDS))
        if frozen:
            raise StepStateError(
                f"patch tries to change {frozen}, which is the run's "
                "identity; a step that can rewrite the task or the gate can "
                "redefine success into something already achieved")
        values = dict(self.values)
        for name, value in patch.items():
            expected = STATE_FIELDS[name]
            if value is None:
                values.pop(name, None)
                continue
            if expected is list:
                if not isinstance(value, list):
                    value = [value]
                merged = list(values.get(name, []))
                for item in value:
                    text = str(item).strip()
                    if text and text not in merged:
                        merged.append(text)
                values[name] = merged[-MAX_LIST_ITEMS:]
                continue
            if expected is bool:
                if not isinstance(value, bool):
                    raise StepStateError(
                        f"{name} must be true or false, got {value!r}")
                values[name] = value
                continue
            values[name] = str(value)[:MAX_TEXT_CHARS]
        return StepState(values=values, revision=self.revision + 1)

    def for_prompt(self) -> str:
        """The bounded rendering a step actually receives.

        Empty fields are omitted rather than shown as empty. A step reading
        ``"hypothesis": ""`` treats it as a hypothesis of nothing; a step
        that does not see the field knows it has not been established.
        """
        shown = {name: value for name, value in sorted(self.values.items())
                 if value not in ("", [], None)}
        return json.dumps(shown, indent=1, sort_keys=True)

    def size(self) -> int:
        return len(self.for_prompt())

    def blocked(self) -> bool:
        return bool(str(self.get("blocked_on", "")).strip())


def step_inputs(state: StepState, procedure: str, observation: str = "") -> dict:
    """The three things a step gets: P, S, and O. Nothing else.

    Notably absent: the previous step's reasoning, and every step before
    that. That absence is the mechanism, not an oversight.
    """
    if not str(procedure).strip():
        raise StepStateError("a step needs its procedure")
    return {
        "procedure": str(procedure),
        "state": state.for_prompt(),
        "observation": str(observation)[:MAX_TEXT_CHARS] if observation else "",
    }


def render_step_prompt(state: StepState, procedure: str, observation: str,
                       patch_schema: str) -> str:
    """Assemble the prompt a composed step receives."""
    parts = [procedure, "", "Current state:", state.for_prompt()]
    if observation:
        parts += ["", "Latest observation (the real output, not a summary):",
                  str(observation)[:MAX_TEXT_CHARS]]
    parts += [
        "",
        "Return one JSON object that PATCHES the state. Include only fields "
        "you are changing; omit the rest. Use null to remove a field. List "
        "fields are appended to, so report only what you newly observed.",
        f"Patchable fields: {patch_schema}",
    ]
    return "\n".join(parts)


def self_test() -> dict:
    """Prove bounding, merge semantics, and every refusal."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    state = StepState.start("fix the failing gate", "pytest -q")
    check("a_run_starts_with_its_task_and_gate",
          state.get("task") == "fix the failing gate" and state.revision == 0)

    state = state.apply({"hypothesis": "null revenue is summed",
                         "files_examined": ["pipeline.py"]})
    state = state.apply({"files_examined": ["test_pipeline.py"],
                         "commands_run": ["pytest -q"]})
    check("list_fields_append_rather_than_replace",
          state.get("files_examined") == ["pipeline.py", "test_pipeline.py"],
          str(state.get("files_examined")))
    check("a_patch_advances_the_revision", state.revision == 2)

    state = state.apply({"hypothesis": None})
    check("null_deletes_a_field", "hypothesis" not in state.values)

    # The bound: many steps must not grow the prompt without limit.
    grown = StepState.start("t", "g")
    for index in range(60):
        grown = grown.apply({"files_examined": [f"file_{index}.py"],
                             "hypothesis": "h" * 4000})
    check("state_stays_bounded_across_many_steps",
          grown.size() < 3000 and len(grown.get("files_examined")) == MAX_LIST_ITEMS,
          f"{grown.size()} chars, {len(grown.get('files_examined'))} files "
          f"after 60 patches")

    check("empty_fields_are_omitted_not_shown_empty",
          '""' not in StepState.start("t", "g").for_prompt(),
          "a step reading an empty hypothesis treats it as a hypothesis")

    inputs = step_inputs(state, "You are the verify step.", "2 passed")
    check("a_step_gets_exactly_procedure_state_observation",
          set(inputs) == {"procedure", "state", "observation"}, str(set(inputs)))

    rendered = render_step_prompt(state, "P", "REAL OUTPUT", "hypothesis")
    check("the_prompt_carries_no_prior_reasoning",
          "REAL OUTPUT" in rendered and "Current state:" in rendered
          and "reasoning" not in rendered.lower())

    for patch, why, fragment in (
            ({"invented_field": "x"}, "an unknown field", "schema is closed"),
            ({"task": "something easier"}, "rewriting the task", "identity"),
            ({"gate_command": "true"}, "rewriting the gate", "identity"),
            ({"verified": "yes"}, "a non-boolean verified", "true or false")):
        try:
            state.apply(patch)
            check(f"refuses_{why.replace(' ', '_')}", False, "accepted")
        except StepStateError as exc:
            check(f"refuses_{why.replace(' ', '_')}",
                  fragment in str(exc), str(exc)[:100])

    try:
        state.apply(["not", "an", "object"])
        check("refuses_a_non_object_patch", False)
    except StepStateError as exc:
        check("refuses_a_non_object_patch", "must be an object" in str(exc))

    blocked = state.apply({"blocked_on": "needs a database credential"})
    check("a_blocked_run_says_so", blocked.blocked() and not state.blocked())

    return {"module": "core.step_state", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
