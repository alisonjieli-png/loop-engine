"""Whole nights driven against declared replies, with no socket at all.

Every check here runs one complete night through :func:`run_night` with a
scripted model and a scripted gate, so the loop that has to work while
nobody is watching is exercised without a server, a subprocess or a model.
Each case is paired with the known wrong night it exists to refuse, and the
cases marked with a date were written after a real run on this machine
behaved that way.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .overnight_authority import OvernightAuthority, ResidencyPolicy, ending_for
from .overnight_journal import OvernightJournal, content_digest
from .overnight_night import (DEFAULT_STEP_PROFILE, NightError, NightRunners,
                              StepProcedure, _Ledger, classify_call_failure,
                              parse_step_reply, run_night)
from .solve_terminal import SolveTerminalCode


def self_test() -> dict:
    """Drive whole nights against declared replies, with no socket at all."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:220]})

    class _Reply:
        def __init__(self, text="", ok=True, error="", prompt=7, evaluated=5):
            self.text, self.ok, self.error = text, ok, error
            self.prompt_tokens, self.eval_tokens = prompt, evaluated

    def scripted(replies):
        queue = list(replies)

        def call(prompt, *, timeout, max_output_tokens=0):  # noqa: ARG001
            return queue.pop(0) if queue else _Reply(
                '{"patch": {"unknowns": ["nothing left to say"]}}')
        return call

    residency = ResidencyPolicy(
        keep_resident_seconds=1800,
        reason="one load for the whole night rather than one for each step")

    def authority_in(folder, **extra):
        return OvernightAuthority(
            night_hours=1.0, max_model_calls=extra.pop("calls", 6),
            workspace_root=folder, residency=residency, **extra)

    # 1. A night that reaches a verified result ends on that and nothing else.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, gate_command=str(
            Path(folder) / "gate.sh"), calls=8)
        Path(authority.gate_command).write_text("exit 0\n", encoding="utf-8")
        result = run_night(
            task="make the declared gate pass", authority=authority,
            runners=NightRunners(
                call_model=scripted([
                    _Reply('{"patch": {"reproduction": "bash gate.sh"}}'),
                    _Reply('{"patch": {"hypothesis": "it already passes"}}'),
                ]),
                run_gate=lambda path: {"passed": True, "exit_code": 0,
                                       "output_tail": []}),
            profile=DEFAULT_STEP_PROFILE[:2])
        check("a_verified_result_ends_the_night_on_the_verified_code",
              result["terminal_code"] == "COMPLETED_VERIFIED"
              and result["ending"] == "accepted_result"
              and result["verified"] is True, result["terminal_code"])
        check("the_report_carries_only_the_tokens_the_server_reported",
              result["prompt_tokens_reported"] == 14
              and result["eval_tokens_reported"] == 10
              and result["calls_with_no_usage_reported"] == 0)

    # 2. A night whose gate never passes ends on spent authority, not on a
    #    number of attempts, and keeps changing the approach in between.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=4, gate_command=str(
            Path(folder) / "gate.sh"))
        Path(authority.gate_command).write_text("exit 1\n", encoding="utf-8")
        result = run_night(
            task="a problem nothing solves", authority=authority,
            runners=NightRunners(
                call_model=scripted([]),
                run_gate=lambda path: {"passed": False, "exit_code": 1,
                                       "output_tail": ["still red"]}),
            profile=DEFAULT_STEP_PROFILE[:2])
        check("a_night_that_cannot_finish_ends_on_spent_authority",
              result["terminal_code"] == "BUDGET_EXHAUSTED"
              and result["ending"] == "declared_authority_spent",
              result["terminal_code"])
        check("the_declared_model_call_ceiling_is_never_exceeded",
              result["model_calls"] == 4, result["model_calls"])
        check("a_round_that_changed_nothing_changes_the_approach",
              any(item["action"] == "change_the_step"
                  for item in result["next_actions"]))
        check("unfinished_work_is_carried_forward_as_provisional",
              any(item["action"] == "carry_forward_as_provisional"
                  for item in result["next_actions"]))

    # 3. A failure becomes a typed next action rather than a stop.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=3)
        result = run_night(
            task="a step that answers with prose", authority=authority,
            runners=NightRunners(call_model=scripted([
                _Reply("I think the problem is interesting."),
                _Reply('{"patch": {"hypothesis": "recovered"}}'),
            ])),
            profile=DEFAULT_STEP_PROFILE[:2])
        check("a_reply_that_is_not_an_object_narrows_the_request_and_continues",
              any(item["action"] == "narrow_the_request"
                  for item in result["next_actions"])
              and result["state"].get("hypothesis") == "recovered",
              result["next_actions"][:1])
        check("the_rejected_list_says_what_was_rejected_and_why",
              bool(result["rejected"])
              and "returned no object" in result["rejected"][0]["why"])

    # 4. A step may not invent an effect by naming a key.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=1)
        result = run_night(
            task="a step that invents an effect", authority=authority,
            runners=NightRunners(call_model=scripted([
                _Reply('{"patch": {}, "send_email": {"to": "someone"}}')])),
            profile=DEFAULT_STEP_PROFILE[:1])
        check("a_key_the_contract_does_not_declare_is_refused_not_ignored",
              any("send_email" in item["why"] for item in result["rejected"]),
              result["rejected"][:1])

    # 5. A write outside the declared folders is refused and recorded.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=1)
        result = run_night(
            task="a step that writes outside the night", authority=authority,
            runners=NightRunners(call_model=scripted([
                _Reply(json.dumps({"write": {
                    "path": "/etc/loop-engine-was-here",
                    "content": "no"}}))])),
            profile=DEFAULT_STEP_PROFILE[:1])
        check("a_write_outside_the_declared_folders_is_refused",
              bool(result["refusals"])
              and "outside the folders" in result["refusals"][0]
              and not Path("/etc/loop-engine-was-here").exists(),
              result["refusals"][:1])

    # 6. A write inside the folders happens once and is not repeated.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=2)
        target = str(Path(folder) / "answer.txt")
        result = run_night(
            task="write one file, twice", authority=authority,
            runners=NightRunners(call_model=scripted([
                _Reply(json.dumps({"write": {"path": target,
                                             "content": "the answer"}})),
                _Reply(json.dumps({"write": {"path": target,
                                             "content": "the answer"}})),
            ])),
            profile=DEFAULT_STEP_PROFILE[:1])
        second = [item for item in result["writes"]
                  if item.get("already_present")]
        check("the_same_content_is_not_written_a_second_time",
              Path(target).read_text(encoding="utf-8") == "the answer"
              and len(second) == 1, result["writes"])
        check("the_journal_can_say_which_writes_finished",
              OvernightJournal(folder).committed_write_digests().get(target)
              == content_digest("the answer"))

    # 7. A server that goes away is recorded for resumption, not retried away.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=6)
        result = run_night(
            task="a server that stops answering", authority=authority,
            runners=NightRunners(
                call_model=scripted([
                    _Reply(ok=False, error="URLError: connection refused"),
                    _Reply(ok=False, error="URLError: connection refused"),
                ]),
                sleep=lambda seconds: None),
            profile=DEFAULT_STEP_PROFILE[:1])
        check("a_provider_outage_is_its_own_ending_kept_for_resumption",
              result["terminal_code"] == "PROVIDER_UNAVAILABLE"
              and result["ending"] ==
              "provider_outage_recorded_for_resumption",
              result["terminal_code"])
        check("the_wait_is_declared_before_the_night_rather_than_invented",
              any(item["action"] == "wait_for_the_provider"
                  for item in result["next_actions"]))

    # 7b. Our own deadline is not the server going away. Observed on
    #     2026-09-21: a step that ran past its time grant reported
    #     "TimeoutError: timed out", the night read that as an outage, and
    #     ended as a provider outage while the server kept answering.
    check("a_timeout_is_our_deadline_and_a_refused_socket_is_the_provider",
          classify_call_failure("TimeoutError: timed out") == "deadline"
          and classify_call_failure("URLError: connection refused") == "outage"
          and classify_call_failure("output_validation_failed") == "refusal")
    check("the_word_refused_alone_is_not_the_server_going_away",
          classify_call_failure(
              "the gateway refused the requested output ceiling") == "refusal"
          and classify_call_failure(
              "ConnectionRefusedError: [Errno 111]") == "outage")
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=2)
        result = run_night(
            task="a step that runs past its time grant", authority=authority,
            runners=NightRunners(
                call_model=scripted([
                    _Reply(ok=False, error="TimeoutError: timed out"),
                    _Reply('{"patch": {"hypothesis": "shorter answer"}}'),
                ]),
                sleep=lambda seconds: None),
            profile=DEFAULT_STEP_PROFILE[:1])
        check("a_step_over_its_time_grant_narrows_rather_than_blaming_the_server",
              result["terminal_code"] != "PROVIDER_UNAVAILABLE"
              and any(item["action"] == "narrow_the_request"
                      for item in result["next_actions"])
              and not any(item["action"] == "wait_for_the_provider"
                          for item in result["next_actions"]),
              result["terminal_code"])

    # 7c. An empty object is a step that did nothing. Observed on
    #     2026-09-21: a well formed but empty reply left the round looking
    #     like a step that had worked.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=1)
        result = run_night(
            task="a step that answers with an empty object",
            authority=authority,
            runners=NightRunners(call_model=scripted([_Reply('{"patch": {}}')])),
            profile=DEFAULT_STEP_PROFILE[:1])
        check("an_empty_object_is_recorded_as_a_step_that_gained_nothing",
              any("empty" in item["why"] for item in result["rejected"])
              and any(item["action"] == "narrow_the_request"
                      for item in result["next_actions"]),
              result["rejected"][:1])

    # 7e. One refusal at every step of a whole round is a question for a
    #     person, not something to ask again in different words.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=12)
        same = "the gateway refused the requested output ceiling"

        def always_refuses(prompt, *, timeout, max_output_tokens=0):  # noqa: ARG001
            return _Reply(ok=False, error=same)
        result = run_night(
            task="a night the machine cannot answer", authority=authority,
            runners=NightRunners(call_model=always_refuses),
            profile=DEFAULT_STEP_PROFILE[:2])
        check("one_refusal_at_every_step_of_a_round_becomes_a_question",
              result["terminal_code"] == "CAPABILITY_GAP"
              and result["ending"] == "question_only_a_person_can_answer"
              and result["model_calls"] == 2
              and any(item["action"] == "stop_and_ask"
                      for item in result["next_actions"]),
              result["terminal_code"])
        check("the_repeated_refusal_is_quoted_rather_than_summarised",
              same in str(result["state"].get("blocked_on", "")))

    # 7f. Different refusals are still worked through, not stopped.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=4)
        result = run_night(
            task="two different refusals", authority=authority,
            runners=NightRunners(call_model=scripted([
                _Reply(ok=False, error="output_validation_failed: one"),
                _Reply(ok=False, error="output_validation_failed: two"),
                _Reply('{"patch": {"hypothesis": "recovered"}}'),
            ])),
            profile=DEFAULT_STEP_PROFILE[:2])
        check("two_different_refusals_do_not_end_the_night",
              result["terminal_code"] != "CAPABILITY_GAP"
              and result["state"].get("hypothesis") == "recovered",
              result["terminal_code"])

    # 7d. The output allowance is declared, never invented.
    refused_allowance = False
    try:
        with tempfile.TemporaryDirectory() as folder:
            run_night(task="t", authority=authority_in(folder, calls=1),
                      runners=NightRunners(call_model=scripted([])),
                      output_allowance=-5)
    except NightError:
        refused_allowance = True
    check("an_output_allowance_below_zero_is_refused", refused_allowance)
    seen = {}
    with tempfile.TemporaryDirectory() as folder:
        def watching(prompt, *, timeout, max_output_tokens):  # noqa: ARG001
            seen["allowance"] = max_output_tokens
            return _Reply('{"patch": {"hypothesis": "x"}}')
        run_night(task="t", authority=authority_in(folder, calls=1),
                  runners=NightRunners(call_model=watching),
                  profile=DEFAULT_STEP_PROFILE[:1], output_allowance=512)
    check("the_declared_output_allowance_reaches_every_call",
          seen.get("allowance") == 512, seen)

    # 8. A question only a person can answer ends the night as one.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=2)
        result = run_night(
            task="something nobody here can decide", authority=authority,
            runners=NightRunners(call_model=scripted([
                _Reply(json.dumps({"patch": {
                    "blocked_on": "the licence for this data is not "
                                  "stated"}}))])),
            profile=DEFAULT_STEP_PROFILE[:1])
        check("a_blocked_night_ends_as_a_question_for_a_person",
              result["terminal_code"] == "BLOCKED_MATERIAL_INPUT"
              and result["ending"] == "question_only_a_person_can_answer"
              and any(item["action"] == "stop_and_ask"
                      for item in result["next_actions"]),
              result["terminal_code"])

    # 9. Cancellation is its own ending.
    with tempfile.TemporaryDirectory() as folder:
        authority = authority_in(folder, calls=2)
        result = run_night(
            task="a night an operator stops", authority=authority,
            runners=NightRunners(call_model=scripted([]),
                                 cancelled=lambda: True),
            profile=DEFAULT_STEP_PROFILE[:1])
        check("a_cancellation_is_recorded_as_a_cancellation",
              result["terminal_code"] == "CANCELLED"
              and result["ending"] == "operator_cancellation")

    # 10. Every reply key and every next action is declared, not invented.
    check("the_step_contract_is_closed",
          parse_step_reply('{"patch": {"hypothesis": "x"}}')["patch"][
              "hypothesis"] == "x")
    refused_profile = False
    try:
        StepProcedure("s", "do it", ("not_a_state_field",))
    except NightError:
        refused_profile = True
    check("a_step_profile_that_names_a_field_outside_the_schema_is_refused",
          refused_profile)
    refused_action = False
    try:
        _Ledger().act("try_again", "")
    except NightError:
        refused_action = True
    check("a_next_action_nobody_declared_is_refused",
          refused_action)
    check("every_ending_the_loop_can_reach_maps_to_one_of_the_five",
          all(ending_for(code.value) for code in SolveTerminalCode))
    passed = sum(item["passed"] for item in tests)
    return {"name": "overnight_night_checks", "tests": tests,
            "passed": passed, "total": len(tests)}
