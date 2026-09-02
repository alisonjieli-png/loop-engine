"""What the model chose from the options it was offered, and what came of it.

Every packet offers the model a portfolio it may draw on: the perspectives it
may reason as, the question sets it may work through, the guidance it may
apply. Selection authority is the model's by design, and the current step is
a hint rather than a gate, so the portfolio can hold far more than any one
call will use.

That design only compounds if selection is observed. An option nobody ever
picks and an option that carries every solved run look identical in the
source; they separate only in the record of what was picked, on which step,
and how those runs ended. This module owns that record: the contract asking
the model to name what it used, the admission of that answer against the
options actually offered, and the per-run tally that saved Run History
carries into ``core.task_region_statistics``.

The record is evidence, never a gate. Nothing here narrows what a later call
may be offered; a rarely chosen option stays on the menu until a person reads
the evidence and decides otherwise. A reading that names an option the packet
never offered is dropped rather than counted, because an invented reference
would corrupt the very tally it lands in.

Owns:
    - SELECTION_REPORT_CONTRACT: the uniform ask added to every packet.
    - admitted_selection(): the reported selection, kept to what was offered.
    - SelectionTally: the per-run accumulation saved with the result.

Does not own: the portfolio itself (core.practitioner_context), packet
assembly (core.adaptive_practitioner_prompting), or the cross-run projection
that reads the saved tally (core.task_region_statistics).
"""
from __future__ import annotations

from dataclasses import dataclass, field

SELECTION_RECORD_TYPE = "option_selection_tally/v1"

#: The uniform ask carried in every packet's output contract. These keys sit
#: beside the step's own schema and are removed before the step's typed
#: validator ever sees the response, so a step schema never has to know that
#: selection is being observed at all.
SELECTION_REPORT_CONTRACT = {
    "purpose": ("Name what you actually drew on, so the portfolio can be "
                "judged on use rather than on intent. This is a record, not "
                "a test: an honest empty list is worth more than a plausible "
                "one, and nothing you report here narrows what you are "
                "offered next time."),
    "keys": {
        "used_perspectives": ("persona_id values from [PERSPECTIVES] whose "
                              "reasoning you actually applied"),
        "used_question_refs": ("step_id values from [QUESTIONS] whose "
                               "questions you actually worked through, "
                               "including any step other than the active "
                               "one"),
        "used_guidance_refs": ("record_id values from [SELECTED "
                               "INTELLIGENCE] that changed what you "
                               "returned"),
        "wanted_but_absent": ("in your own words, anything you needed and "
                              "the portfolio did not offer"),
        "operator_gap": ("when you needed an operation this runtime has no "
                         "way to perform, an object with `needed` (the "
                         "operation), `tried` (the capability refs you "
                         "attempted) and `runtime_said` (what it refused "
                         "with). A run once restated the same correct repair "
                         "for twenty passes because it had no way to say "
                         "this"),
    },
    "optional": True,
    "affects_validation": False,
}

#: The name the contract is presented under. A model shown a contract as
#: ``selection_report: {keys: {...}}`` may answer with the keys flat or with
#: one object under this name. Both are the same answer honestly given, and
#: an optional record that changes no verdict must never be the reason a
#: step's typed validator rejects the work it came attached to.
SELECTION_REPORT_KEY = "selection_report"

#: The keys stripped from a model response before typed validation, derived
#: from the contract rather than restated beside it. A key added to the
#: contract is stripped by construction; a second hand-kept copy of this list
#: is exactly how the container name came to be asked for and never removed.
SELECTION_KEYS = (SELECTION_REPORT_KEY,) + tuple(SELECTION_REPORT_CONTRACT["keys"])


class OptionSelectionError(ValueError):
    """A selection record violated its typed contract."""


def _named(value) -> list:
    """Return the distinct non-empty strings in a reported list."""
    if not isinstance(value, (list, tuple)):
        return []
    seen = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def admitted_selection(value, offered: dict) -> dict:
    """Keep the reported selection to the options the packet actually offered.

    ``offered`` names what this packet held, keyed as the report is. A
    reference outside it is recorded separately rather than silently kept or
    silently dropped: an invented persona is itself a finding about the
    prompt, and it must not be counted as use of an option that exists.
    """
    if not isinstance(value, dict):
        return {}
    # Accept the nested shape as well as the flat one. Read the container
    # first so that a caller answering in both shapes has its flat keys win.
    inner = value.get(SELECTION_REPORT_KEY)
    if isinstance(inner, dict):
        value = {**inner, **{key: item for key, item in value.items()
                             if key != SELECTION_REPORT_KEY}}
    admitted: dict = {}
    unoffered: dict = {}
    for key in ("used_perspectives", "used_question_refs",
                "used_guidance_refs"):
        reported = _named(value.get(key))
        available = set(offered.get(key) or ())
        admitted[key] = [item for item in reported if item in available]
        outside = [item for item in reported if item not in available]
        if outside:
            unoffered[key] = outside
    wanted = _named(value.get("wanted_but_absent"))
    if wanted:
        admitted["wanted_but_absent"] = wanted
    # A missing operator is a different finding from a missing perspective:
    # one says the portfolio is thin, the other says the runtime cannot do
    # the thing at all. They are counted apart for that reason.
    from .cognitive_grammar import admitted_gap_report
    gap = admitted_gap_report(value.get("operator_gap"))
    if gap:
        admitted["operator_gap"] = gap
    if unoffered:
        admitted["named_but_not_offered"] = unoffered
    return {key: item for key, item in admitted.items() if item}


@dataclass
class SelectionTally:
    """What one run drew on, counted per option and per step.

    The tally is written as the run goes and saved with the result, so the
    cross-run projection reads a finished count rather than replaying every
    packet. Steps are counted alongside options because a step nobody's
    reasoning ever reaches is the same kind of evidence as an unused persona.
    """

    perspectives: dict = field(default_factory=dict)
    question_refs: dict = field(default_factory=dict)
    guidance_refs: dict = field(default_factory=dict)
    steps_reported: dict = field(default_factory=dict)
    steps_offered: dict = field(default_factory=dict)
    wanted_but_absent: list = field(default_factory=list)
    #: Operations a caller needed and this runtime could not perform. The
    #: highest-value entry in the whole tally: it names what to build next.
    operator_gaps: list = field(default_factory=list)
    named_but_not_offered: list = field(default_factory=list)
    reports: int = 0
    calls: int = 0

    def note_offered(self, step_id: str) -> None:
        """Record that a step made a call, whether or not it reported use."""
        step = str(step_id or "unknown")
        self.steps_offered[step] = self.steps_offered.get(step, 0) + 1
        self.calls += 1

    def note(self, step_id: str, selection: dict) -> None:
        """Add one admitted selection report to the tally."""
        if not isinstance(selection, dict) or not selection:
            return
        step = str(step_id or "unknown")
        counted = False
        for key, target in (("used_perspectives", self.perspectives),
                            ("used_question_refs", self.question_refs),
                            ("used_guidance_refs", self.guidance_refs)):
            for item in selection.get(key) or ():
                target[item] = target.get(item, 0) + 1
                counted = True
        for item in selection.get("wanted_but_absent") or ():
            self.wanted_but_absent.append({"step": step, "text": item[:280]})
            counted = True
        gap = selection.get("operator_gap")
        if isinstance(gap, dict):
            self.operator_gaps.append({**gap, "step": step})
            counted = True
        outside = selection.get("named_but_not_offered") or {}
        if isinstance(outside, dict):
            for key, items in outside.items():
                for item in items:
                    self.named_but_not_offered.append(
                        {"step": step, "key": key, "ref": item[:120]})
                    counted = True
        if counted:
            self.steps_reported[step] = self.steps_reported.get(step, 0) + 1
            self.reports += 1

    def to_dict(self) -> dict:
        return {
            "record_type": SELECTION_RECORD_TYPE,
            "perspectives": dict(sorted(self.perspectives.items())),
            "question_refs": dict(sorted(self.question_refs.items())),
            "guidance_refs": dict(sorted(self.guidance_refs.items())),
            "steps_reported": dict(sorted(self.steps_reported.items())),
            "steps_offered": dict(sorted(self.steps_offered.items())),
            "wanted_but_absent": list(self.wanted_but_absent),
            "operator_gaps": list(self.operator_gaps),
            "named_but_not_offered": list(self.named_but_not_offered),
            "reports": self.reports,
            "calls": self.calls,
        }


def self_test() -> dict:
    """Prove admission, tallying, and that the record never gates a run."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    offered = {
        "used_perspectives": ["core.persona.adversary", "core.persona.researcher"],
        "used_question_refs": ["orient", "decide_next"],
        "used_guidance_refs": ["core.guidance.one_next_action"],
    }
    admitted = admitted_selection({
        "used_perspectives": ["core.persona.adversary", "core.persona.invented"],
        "used_question_refs": ["decide_next"],
        "used_guidance_refs": [],
        "wanted_but_absent": ["a perspective for cost over time"],
    }, offered)
    check("a_reported_option_the_packet_offered_is_counted",
          admitted["used_perspectives"] == ["core.persona.adversary"],
          str(admitted.get("used_perspectives")))
    check("an_option_the_packet_never_offered_is_recorded_not_counted",
          admitted["named_but_not_offered"]["used_perspectives"]
          == ["core.persona.invented"]
          and "core.persona.invented" not in admitted["used_perspectives"],
          str(admitted.get("named_but_not_offered")))
    check("a_gap_the_model_names_is_kept_verbatim",
          admitted["wanted_but_absent"] == ["a perspective for cost over time"])

    tally = SelectionTally()
    tally.note_offered("orient")
    tally.note("orient", admitted)
    tally.note_offered("verify")
    value = tally.to_dict()
    check("use_is_counted_per_option",
          value["perspectives"] == {"core.persona.adversary": 1})
    check("a_step_that_called_without_reporting_is_still_visible",
          value["steps_offered"] == {"orient": 1, "verify": 1}
          and value["steps_reported"] == {"orient": 1},
          str(value["steps_offered"]))
    check("the_tally_states_both_calls_and_reports",
          value["calls"] == 2 and value["reports"] == 1)

    # A model that reports nothing, or reports rubbish, must cost a run
    # nothing. The record is evidence; it can never become a gate.
    check("an_absent_or_malformed_report_is_survivable",
          admitted_selection(None, offered) == {}
          and admitted_selection({"used_perspectives": "not a list"},
                                 offered) == {}
          and admitted_selection({}, {}) == {})
    quiet = SelectionTally()
    quiet.note("orient", {})
    quiet.note("orient", None)
    check("tallying_nothing_records_nothing",
          quiet.to_dict()["reports"] == 0)
    # A missing operator and a missing perspective are different findings and
    # must not collapse into one list: one says build something, the other
    # says offer something.
    gapped = admitted_selection({"operator_gap": {
        "needed": "read back a file this run generated",
        "tried": ["core.source.inspect"],
        "runtime_said": "source inspection requested unknown paths"}},
        offered)
    gap_tally = SelectionTally()
    gap_tally.note_offered("how")
    gap_tally.note("how", gapped)
    value = gap_tally.to_dict()
    check("a_missing_operator_is_recorded_apart_from_a_missing_option",
          len(value["operator_gaps"]) == 1
          and value["operator_gaps"][0]["step"] == "how"
          and value["operator_gaps"][0]["tried"] == ["core.source.inspect"]
          and not value["wanted_but_absent"],
          str(value["operator_gaps"])[:160])

    check("every_reported_key_has_a_contract_entry",
          set(SELECTION_KEYS) ==
          set(SELECTION_REPORT_CONTRACT["keys"]) | {SELECTION_REPORT_KEY})
    nested = admitted_selection(
        {SELECTION_REPORT_KEY: {"used_perspectives": ["p.one"]}},
        {"used_perspectives": ["p.one"]})
    check("a selection reported under its container name is read",
          nested.get("used_perspectives") == ["p.one"])
    check("the container name is stripped before typed validation",
          SELECTION_REPORT_KEY in SELECTION_KEYS)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "option_selection_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
