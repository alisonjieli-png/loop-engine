"""Run the night, unattended, and end for a reason that can be named.

This is the part that has to work while nobody is watching. It holds the
loop itself and three properties the loop exists to keep:

  * Nothing happens outside the declared authority. A read outside the
    declared folders, a write outside them, and a model call past the
    declared ceiling are refused at the moment of use and recorded as
    refusals, not argued about in the morning.
  * A failure is an input, not a stop. Every failure becomes one of the
    typed next actions, the run says which, and it carries on. The run
    never ends because it tried a certain number of times. It ends for a
    verified result, spent authority, a question only a person can answer,
    a cancellation, or a recorded provider outage, and it records which.
  * Every effect is written down before it happens. A process killed
    between the intent and the outcome leaves a record saying so, and a
    later resume repeats only what was declared repeatable.

THE STEP CONTRACT
Each step receives its procedure, the current structured state and the
latest real observation, and returns one object:

    {"patch": {...}, "read": ["path", ...], "write": {"path", "content"}}

Every key is optional and an unknown key is refused rather than ignored.
``patch`` goes through the closed state schema. ``read`` supplies the next
observation from files inside the declared read folders. ``write`` is the
only way a step changes anything on disk, and it is journalled by its
content digest so a resume can see that the file already holds it.

WHAT A ROUND IS
A round runs every procedure of the declared profile once, in order, and
then runs the declared gate. A round that changed nothing does not end the
night; it changes the approach, quoting the failure and narrowing the next
request. Only the declared authority ends a night that is not finished.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..core import overnight_outcome
from ..core.night_budget import NightBudget, NightBudgetError
from ..core.step_state import (MAX_TEXT_CHARS, STATE_FIELDS, StepState,
                               StepStateError, render_step_prompt)
from .overnight_authority import NEXT_ACTIONS, OvernightAuthority, ending_for
from .overnight_journal import OvernightJournal, content_digest
from .solve_terminal import SolveTerminalCode

#: Keys a step may return. Unknown keys are refused so that a step cannot
#: invent an effect by naming it.
STEP_REPLY_KEYS = ("patch", "read", "write")

#: How much of a file the night puts in front of a step. A bound, because
#: an unbounded observation turns the state back into a transcript.
MAX_OBSERVATION_CHARS = MAX_TEXT_CHARS


class NightError(RuntimeError):
    """The night cannot be run as declared."""


@dataclass(frozen=True)
class StepProcedure:
    """One step of the declared profile.

    ``satisfied_when`` names state fields whose presence means this step's
    output already exists. It is consulted only on the first round of a
    resumed night, so a resume does not repeat orientation it already did.
    """

    name: str
    instruction: str
    satisfied_when: tuple = ()

    def __post_init__(self) -> None:
        if not str(self.name).strip() or not str(self.instruction).strip():
            raise NightError("every step of the profile is named and written")
        for field_name in self.satisfied_when:
            if field_name not in STATE_FIELDS:
                raise NightError(
                    f"satisfied_when names {field_name!r}, which is not a "
                    "state field; the state schema is closed")


#: A general profile: orient, reproduce, explain, change, and let the
#: declared gate decide. It is a default, not the only shape. A caller may
#: declare more steps, fewer, or different ones.
DEFAULT_STEP_PROFILE = (
    StepProcedure(
        "orient",
        "Read the task. Say what you would need to see to make progress. "
        "Ask for files by path through the read key rather than guessing "
        "their contents.",
        ("files_examined",)),
    StepProcedure(
        "reproduce",
        "State the single command that shows the problem, and what it "
        "prints now. Put it in reproduction and observed_failure.",
        ("reproduction",)),
    StepProcedure(
        "explain",
        "Give one hypothesis for the cause, in one sentence. Move any "
        "explanation you have tested and rejected into ruled_out."),
    StepProcedure(
        "change",
        "Make the smallest change you believe fixes it. Return it through "
        "the write key with the full new content of one file. If you cannot "
        "name a file and its whole content, do not write anything; say what "
        "is missing in unknowns instead."),
)


def _reply_schema() -> str:
    return ("{\"patch\": {field: value}, \"read\": [\"absolute path\"], "
            "\"write\": {\"path\": \"absolute path\", \"content\": \"the "
            "whole new file\"}}")


def parse_step_reply(text: str) -> dict:
    """The one object a step returns, or a refusal that says what was wrong.

    A model that answers with prose around its object is common and is not
    a failure of the run, so the outermost braces are located rather than
    demanded. A model that answers with something else entirely is a
    refusal, and the refusal quotes what arrived.
    """
    raw = str(text or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise StepStateError(
            "the step returned no object; it returned: " + raw[:200])
    try:
        value = json.loads(raw[start:end + 1])
    except ValueError as error:
        raise StepStateError(
            f"the step's object did not parse ({error}); it returned: "
            + raw[start:start + 200]) from error
    if not isinstance(value, dict):
        raise StepStateError("the step returned a value that is not an object")
    unknown = sorted(set(value) - set(STEP_REPLY_KEYS))
    if unknown:
        raise StepStateError(
            f"the step named keys that do not exist: {unknown}. A step may "
            "return " + ", ".join(STEP_REPLY_KEYS))
    if "patch" in value and not isinstance(value["patch"], dict):
        raise StepStateError("patch must be an object")
    if "read" in value and not isinstance(value["read"], list):
        raise StepStateError("read must be a list of paths")
    write = value.get("write")
    if write is not None:
        if not isinstance(write, dict) or not str(write.get("path", "")).strip() \
                or not isinstance(write.get("content"), str):
            raise StepStateError(
                "write must name a path and the whole new content")
    return value


def _read_files(authority: OvernightAuthority, paths) -> tuple:
    """Files a step asked for, inside the authority, with refusals named."""
    parts, refusals = [], []
    for item in list(paths)[:4]:
        path = str(item)
        if not authority.may_read(path):
            refusals.append(
                f"refused: reading {path!r} is outside the folders this night "
                "declared")
            continue
        try:
            body = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            refusals.append(f"could not read {path!r}: {type(error).__name__}")
            continue
        parts.append(f"--- {path} ---\n" + body[:MAX_OBSERVATION_CHARS])
    return ("\n".join(parts)[:MAX_OBSERVATION_CHARS], refusals)


def _apply_write(authority: OvernightAuthority, journal: OvernightJournal,
                 write: dict, *, round_number: int) -> dict:
    """Write one file inside the authority, once, keyed by its content.

    The digest is the key, so a resume that finds the file already holding
    that content records the effect as already done instead of writing it
    again. The journal entry is written before the file, so a process
    killed in between leaves a record that says the outcome is unknown.
    """
    path = str(write.get("path", ""))
    content = str(write.get("content", ""))
    digest = content_digest(content)
    record = {"record_type": "overnight_write/v1", "path": path,
              "digest": digest, "round": round_number}
    if not authority.may_write(path):
        record.update(written=False, refused=authority.refuse_write(path))
        journal.append("refusal", **record)
        return record
    existing = ""
    try:
        existing = Path(path).read_text(encoding="utf-8")
    except (OSError, ValueError):
        existing = ""
    if existing and content_digest(existing) == digest:
        record.update(written=False,
                      already_present="the file already holds exactly this "
                                      "content, so nothing was written again")
        journal.append("effect", effect_key=f"write/{digest[:16]}",
                       effect_kind="workspace_write", commitment="committed",
                       outcome=dict(record), detail={"path": path,
                                                     "digest": digest})
        return record
    token = journal.intend_effect(
        "workspace_write", f"write/{digest[:16]}", repeatable=False,
        detail={"path": path, "digest": digest})
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        record.update(written=True, bytes=len(content.encode("utf-8")))
    except OSError as error:
        record.update(written=False, failed=type(error).__name__)
    journal.commit_effect(token, dict(record))
    return record


#: What the server saying nothing looks like on the socket. A timeout is
#: deliberately absent. Observed on 2026-09-21: a step that ran past the
#: time this run granted it reported ``TimeoutError: timed out``, the run
#: read that as the server going away, waited, and ended the night as a
#: provider outage while the server was answering the whole time. Our own
#: deadline expiring is a budget event and belongs to the run, not to the
#: provider.
#: Each marker names the socket failing, not merely the word refused: the
#: gateway refusing a request is a refusal by the engine's own contract and
#: has nothing to do with the server being reachable.
_OUTAGE_MARKERS = ("urlerror", "connectionrefused", "connection refused",
                   "connectionreset", "connection reset", "connectionerror",
                   "unreachable", "no route to host", "remotedisconnected",
                   "broken pipe", "transport_unavailable")
_DEADLINE_MARKERS = ("timeout", "timed out")


def classify_call_failure(error: str) -> str:
    """Whose failure this was: ``deadline``, ``outage`` or ``refusal``.

    The deadline is checked first because the timeout this run set is the
    one that fires, and a message can carry both words.
    """
    text = str(error or "").casefold()
    if any(marker in text for marker in _DEADLINE_MARKERS):
        return "deadline"
    if any(marker in text for marker in _OUTAGE_MARKERS):
        return "outage"
    return "refusal"


@dataclass
class _Ledger:
    """What the night has spent and produced so far."""

    model_calls: int = 0
    prompt_tokens: int = 0
    eval_tokens: int = 0
    usage_unknown: int = 0
    rounds: int = 0
    next_actions: list = field(default_factory=list)
    writes: list = field(default_factory=list)
    refusals: list = field(default_factory=list)
    gate_runs: list = field(default_factory=list)
    tried: list = field(default_factory=list)
    rejected: list = field(default_factory=list)

    def act(self, action: str, detail: str) -> None:
        if action not in NEXT_ACTIONS:
            raise NightError(
                f"{action!r} is not a declared next action; the night may "
                "only " + ", ".join(NEXT_ACTIONS))
        self.next_actions.append({"action": action,
                                  "means": NEXT_ACTIONS[action],
                                  "detail": str(detail)[:300]})


def _record_usage(ledger: _Ledger, result) -> None:
    prompt = getattr(result, "prompt_tokens", None)
    evaluated = getattr(result, "eval_tokens", None)
    if prompt is None or evaluated is None:
        ledger.usage_unknown += 1
        return
    ledger.prompt_tokens += int(prompt)
    ledger.eval_tokens += int(evaluated)


def _select_steps(profile, state: StepState, *, first_round: bool) -> list:
    """The procedures this round runs, in order.

    Only the first round of a resumed night skips a step whose output the
    state already holds. Every later round runs the whole profile, because
    a failing gate means the earlier answers were not enough.
    """
    if not first_round:
        return list(profile)
    chosen = []
    for step in profile:
        satisfied = step.satisfied_when and all(
            state.get(name) not in (None, "", [], False)
            for name in step.satisfied_when)
        if not satisfied:
            chosen.append(step)
    return chosen or list(profile)


@dataclass(frozen=True)
class NightRunners:
    """The things the night actually calls, kept apart from what it may do.

    Grouping them is what lets the whole loop run against declared replies
    in a check, with no socket and no subprocess, while the run itself
    hands over the real adapter and the real gate.
    """

    call_model: object
    run_gate: object = None
    sleep: object = time.sleep
    cancelled: object = None

    def __post_init__(self) -> None:
        if not callable(self.call_model):
            raise NightError("a night needs a way to call the model")
        for name in ("run_gate", "cancelled"):
            value = getattr(self, name)
            if value is not None and not callable(value):
                raise NightError(f"{name} must be callable or absent")
        if not callable(self.sleep):
            raise NightError("sleep must be callable")

    def was_cancelled(self) -> bool:
        return bool(self.cancelled and self.cancelled())


def run_night(*, task: str, authority: OvernightAuthority,
              runners: NightRunners, profile=DEFAULT_STEP_PROFILE,
              journal: "OvernightJournal | None" = None,
              budget: "NightBudget | None" = None,
              state: "StepState | None" = None,
              output_allowance: int = 0) -> dict:
    """Run until one of the five endings, and say which one it was.

    ``runners.call_model`` takes the assembled prompt, a timeout and an
    output allowance, and returns a result carrying ``ok``, ``text``,
    ``prompt_tokens``, ``eval_tokens`` and ``error``. ``output_allowance``
    is zero when the run asks for the full capacity the route declared, and
    a positive number when a typed allocation selected a smaller one.
    """
    if not isinstance(authority, OvernightAuthority):
        raise NightError("run_night takes a declared OvernightAuthority")
    if not isinstance(runners, NightRunners):
        raise NightError("run_night takes a NightRunners")
    profile = tuple(profile)
    if not profile:
        raise NightError("a night runs at least one declared step")
    if isinstance(output_allowance, bool) \
            or not isinstance(output_allowance, int) or output_allowance < 0:
        raise NightError(
            "output_allowance is zero for the route's full declared capacity "
            "or a positive number a typed allocation selected")
    call_model = runners.call_model
    sleep = runners.sleep
    cancelled = runners.was_cancelled
    journal = journal or OvernightJournal(authority.workspace_root)
    budget = budget or NightBudget(hours=authority.night_hours,
                                   expected_steps=len(profile) + 1)
    state = state or StepState.start(task, authority.gate_command)
    ledger = _Ledger()
    terminal = ""
    observation = ""
    started = time.time()
    journal.append("night_started", task=str(task)[:MAX_TEXT_CHARS],
                   authority=authority.to_dict(),
                   output_allowance=output_allowance,
                   profile=[step.name for step in profile])

    first_round = True
    while not terminal:
        if cancelled():
            terminal = SolveTerminalCode.CANCELLED.value
            break
        if budget.exhausted():
            terminal = SolveTerminalCode.DEADLINE_EXHAUSTED.value
            break
        steps = _select_steps(profile, state, first_round=first_round)
        first_round = False
        # Compared by value, not by revision. Applying the same patch twice
        # raises the revision and changes nothing, which is exactly the case
        # this comparison exists to catch.
        values_at_round_start = dict(state.values)
        # One refusal repeated at every step of a whole round is not a
        # prompting problem, so asking differently cannot fix it. Observed
        # on 2026-09-21: the gateway refused a reduced output ceiling, and
        # the night asked fourteen more times in fourteen different words.
        round_refusals: list = []
        for step in steps:
            if cancelled():
                terminal = SolveTerminalCode.CANCELLED.value
                break
            if ledger.model_calls >= authority.max_model_calls:
                terminal = SolveTerminalCode.BUDGET_EXHAUSTED.value
                break
            try:
                grant = budget.grant(step.name, steps_left=len(steps) + 1)
            except NightBudgetError:
                terminal = SolveTerminalCode.DEADLINE_EXHAUSTED.value
                break
            prompt = render_step_prompt(state, step.instruction, observation,
                                        _reply_schema())
            key = f"round-{ledger.rounds}/{step.name}/call-{ledger.model_calls + 1}"
            token = journal.intend_effect(
                "model_call", key, repeatable=True,
                detail={"step": step.name, "round": ledger.rounds,
                        "prompt_digest": content_digest(prompt),
                        "grant_seconds": round(grant, 1)})
            call_started = time.monotonic()
            result = call_model(prompt, timeout=grant,
                                max_output_tokens=output_allowance)
            elapsed = time.monotonic() - call_started
            ledger.model_calls += 1
            budget.record(step.name, elapsed)
            _record_usage(ledger, result)
            journal.commit_effect(token, {
                "ok": bool(getattr(result, "ok", False)),
                "error": str(getattr(result, "error", ""))[:300],
                "prompt_tokens": getattr(result, "prompt_tokens", None),
                "eval_tokens": getattr(result, "eval_tokens", None),
                "elapsed_seconds": round(elapsed, 2)})
            ledger.tried.append({"round": ledger.rounds, "step": step.name,
                                 "elapsed_seconds": round(elapsed, 2),
                                 "ok": bool(getattr(result, "ok", False))})

            if not getattr(result, "ok", False):
                error = str(getattr(result, "error", "")) or "no reason given"
                whose = classify_call_failure(error)
                ledger.rejected.append(
                    {"round": ledger.rounds, "step": step.name,
                     "why": f"{whose}: {error}"[:200]})
                if whose == "outage":
                    ledger.act("wait_for_the_provider", error)
                    journal.append("provider_silence", detail=error[:300],
                                   waiting_seconds=authority.outage_wait_seconds)
                    sleep(min(float(authority.outage_wait_seconds),
                              max(0.0, budget.remaining())))
                    probe = call_model("", timeout=min(30.0, grant),
                                       max_output_tokens=output_allowance)
                    ledger.model_calls += 1
                    if not getattr(probe, "ok", False) \
                            and classify_call_failure(
                                str(getattr(probe, "error", ""))) == "outage":
                        terminal = SolveTerminalCode.PROVIDER_UNAVAILABLE.value
                        break
                    observation = ("the server went quiet and answered again: "
                                   + error)[:MAX_OBSERVATION_CHARS]
                    continue
                if whose == "deadline":
                    # Our own deadline, not the server's silence. The answer
                    # is to ask for less, in fewer words, not to wait.
                    ledger.act("narrow_the_request",
                               "the step ran past the time this night granted "
                               f"it ({grant / 60:.0f} min); the next request "
                               "asks for the object alone")
                    observation = (
                        "the last answer ran past the time it was given and "
                        "was stopped. Reply with the object only. No "
                        "explanation, no code fences, nothing before or after "
                        "it.")[:MAX_OBSERVATION_CHARS]
                    continue
                round_refusals.append(error)
                ledger.act("narrow_the_request", error)
                observation = ("the last request failed with: " + error)[
                    :MAX_OBSERVATION_CHARS]
                continue

            try:
                reply = parse_step_reply(getattr(result, "text", ""))
            except StepStateError as error:
                ledger.act("narrow_the_request", str(error))
                ledger.rejected.append(
                    {"round": ledger.rounds, "step": step.name,
                     "why": str(error)[:200]})
                observation = str(error)[:MAX_OBSERVATION_CHARS]
                continue

            observation = ""
            if not any(reply.get(name) for name in STEP_REPLY_KEYS):
                # Observed on 2026-09-21: a step answered with a well formed
                # but empty object, the run recorded nothing, and the round
                # looked like a step that had worked.
                ledger.act("narrow_the_request",
                           f"{step.name} returned an object with nothing in "
                           "it, so the round gained nothing")
                ledger.rejected.append(
                    {"round": ledger.rounds, "step": step.name,
                     "why": "the object was empty: no patch, no read, no write"})
                observation = (
                    "the last answer was an empty object. Name at least one "
                    "state field you are changing, or ask for a file by "
                    "path.")[:MAX_OBSERVATION_CHARS]
                continue
            if reply.get("patch"):
                try:
                    state = state.apply(reply["patch"])
                    ledger.act("record_and_continue",
                               f"{step.name} changed "
                               + ", ".join(sorted(reply["patch"])))
                except StepStateError as error:
                    ledger.act("narrow_the_request", str(error))
                    ledger.rejected.append(
                        {"round": ledger.rounds, "step": step.name,
                         "why": str(error)[:200]})
                    observation = str(error)[:MAX_OBSERVATION_CHARS]
            if reply.get("read"):
                body, refusals = _read_files(authority, reply["read"])
                ledger.refusals.extend(refusals)
                for refusal in refusals:
                    journal.append("refusal", detail=refusal)
                observation = (body or "; ".join(refusals))[
                    :MAX_OBSERVATION_CHARS]
            if reply.get("write"):
                record = _apply_write(authority, journal, reply["write"],
                                      round_number=ledger.rounds)
                ledger.writes.append(record)
                if record.get("refused"):
                    ledger.refusals.append(record["refused"])
                    observation = record["refused"][:MAX_OBSERVATION_CHARS]
                elif record.get("written"):
                    state = state.apply({"files_changed": [record["path"]]})
            if state.blocked():
                terminal = SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value
                break

        if terminal:
            break
        if len(round_refusals) == len(steps) and len(set(round_refusals)) == 1:
            state = state.apply({"blocked_on": (
                "every step of a whole round was refused for the same "
                "reason, so rewording the request cannot clear it: "
                + round_refusals[0])[:MAX_TEXT_CHARS]})
            terminal = SolveTerminalCode.CAPABILITY_GAP.value
            journal.append("repeated_refusal", detail=round_refusals[0][:300],
                           steps=len(steps))
            break
        ledger.rounds += 1
        gate = _run_gate_once(authority, journal, runners.run_gate, ledger)
        if gate is not None:
            if gate.get("passed"):
                state = state.apply({"verified": True})
                terminal = SolveTerminalCode.COMPLETED_VERIFIED.value
                break
            tail = "\n".join(gate.get("output_tail") or [])[
                :MAX_OBSERVATION_CHARS]
            observation = tail
            try:
                state = state.apply({"observed_failure": tail})
            except StepStateError:
                pass
        if state.values == values_at_round_start:
            # The same failure came back unchanged. The answer is to change
            # the approach, never to end on how many times it happened.
            ledger.act("change_the_step",
                       "the round changed nothing, so the next round quotes "
                       "the failure and asks for one narrower thing")
            observation = ("nothing changed last round. Quote the exact "
                           "failure and change one thing only.\n" + observation)[
                              :MAX_OBSERVATION_CHARS]

    if not terminal:
        terminal = SolveTerminalCode.NO_PROGRESS.value
    if terminal == SolveTerminalCode.DEADLINE_EXHAUSTED.value \
            and state.revision == 0:
        terminal = SolveTerminalCode.NO_PROGRESS.value
    if terminal != SolveTerminalCode.COMPLETED_VERIFIED.value \
            and state.revision > 0:
        ledger.act("carry_forward_as_provisional",
                   "the work so far is kept and labelled provisional")
    if terminal in (SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value,
                    SolveTerminalCode.CAPABILITY_GAP.value):
        ledger.act("stop_and_ask", str(state.get("blocked_on", "")))
    ended = {
        "record_type": "overnight_night_result/v1",
        "task": str(task)[:MAX_TEXT_CHARS],
        "terminal_code": terminal,
        "ending": ending_for(terminal),
        "verified": bool(state.get("verified")),
        "state": dict(state.values),
        "state_revision": state.revision,
        "rounds": ledger.rounds,
        "model_calls": ledger.model_calls,
        "prompt_tokens_reported": ledger.prompt_tokens,
        "eval_tokens_reported": ledger.eval_tokens,
        "calls_with_no_usage_reported": ledger.usage_unknown,
        "next_actions": ledger.next_actions,
        "tried": ledger.tried,
        "rejected": ledger.rejected,
        "writes": ledger.writes,
        "refusals": ledger.refusals,
        "gate_runs": ledger.gate_runs,
        "time_spent": budget.spent(),
        "elapsed_seconds": round(time.time() - started, 1),
        "workspace_root": authority.workspace_root,
        "gate_command": authority.gate_command,
        "journal": str(journal.path),
        "residency": authority.residency.to_dict(),
    }
    ended["outcome"] = overnight_outcome.classify(
        gate_passed=bool(state.get("verified")),
        state=state,
        gate_before_failed=True,
        skipped_reason="").to_dict()
    journal.append("night_ended", **{
        key: ended[key] for key in
        ("terminal_code", "ending", "verified", "rounds", "model_calls",
         "prompt_tokens_reported", "eval_tokens_reported")})
    return ended


def _run_gate_once(authority: OvernightAuthority, journal: OvernightJournal,
                   run_gate, ledger: _Ledger):
    """Run the declared gate, or say plainly that none was declared."""
    if not authority.gate_command or run_gate is None:
        if not ledger.gate_runs:
            journal.append("no_gate",
                           detail="no gate was declared, so nothing here "
                                  "independently verified the work")
        return None
    key = f"gate/round-{ledger.rounds}"
    token = journal.intend_effect("gate_run", key, repeatable=True,
                                  detail={"gate": authority.gate_command})
    try:
        record = run_gate(authority.gate_command)
    except Exception as error:                              # noqa: BLE001
        record = {"passed": False, "output_tail": [
            f"the gate could not run: {type(error).__name__}"]}
    journal.commit_effect(token, {"passed": bool(record.get("passed")),
                                  "exit_code": record.get("exit_code")})
    ledger.gate_runs.append({"round": ledger.rounds,
                             "passed": bool(record.get("passed")),
                             "exit_code": record.get("exit_code")})
    return record
