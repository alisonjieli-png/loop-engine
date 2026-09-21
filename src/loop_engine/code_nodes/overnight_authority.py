"""What a night may do, written down before anyone goes to bed.

An unattended run has nobody at the keyboard, so every decision a person
would have made has to exist as a typed field before the run starts. This
module holds four of them and refuses a night that leaves any one implicit.

  * The declared authority: how long, how many model calls, which folders
    may be read, which may be written, and where the working folder is.
    Everything absent from it is refused at the moment of use, not argued
    about afterwards.
  * The residency policy: how long the server keeps the weights loaded
    between steps. The evidence record of September 21, 2026 measured one
    machine where the first call paid 87.28 seconds to load the weights and
    the next two took 0.71 and 0.78 seconds. A night that lets the server
    unload between steps pays that load again at every step, so residency
    is a declared setting with a stated reason rather than an accident.
  * The accepted endings. A run may finish for a verified result, spent
    authority, a question only a person can answer, a cancellation, or a
    recorded provider outage. It may never finish because it tried three
    times.
  * The typed next action a failure becomes. A failure is an input to the
    next step, and the closed vocabulary below is the only set of things
    the night is allowed to do about one.

Nothing here runs a step, opens a socket or writes a file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .solve_terminal import SolveTerminalCode

#: The five accepted endings, each with the terminal codes that report it.
#: Every code the solve runtime can return belongs to exactly one ending, so
#: a night can never finish for a reason outside this table.
ACCEPTED_ENDINGS = {
    "accepted_result": (
        SolveTerminalCode.COMPLETED_VERIFIED.value,
    ),
    "declared_authority_spent": (
        SolveTerminalCode.BUDGET_EXHAUSTED.value,
        SolveTerminalCode.DEADLINE_EXHAUSTED.value,
        SolveTerminalCode.NO_PROGRESS.value,
        SolveTerminalCode.COMPLETED_PARTIAL.value,
        SolveTerminalCode.VERIFICATION_FAILED.value,
        SolveTerminalCode.REPAIR_UNAVAILABLE.value,
        SolveTerminalCode.ABSTAINED.value,
    ),
    "question_only_a_person_can_answer": (
        SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value,
        SolveTerminalCode.AUTHORITY_REQUIRED.value,
        SolveTerminalCode.CAPABILITY_GAP.value,
    ),
    "operator_cancellation": (
        SolveTerminalCode.CANCELLED.value,
    ),
    "provider_outage_recorded_for_resumption": (
        SolveTerminalCode.PROVIDER_UNAVAILABLE.value,
    ),
}

#: Endings a night may not declare, each with the reason it is refused.
#: These are the ways an unattended run quietly stops doing the work while
#: reporting that it finished.
REFUSED_ENDINGS = {
    "attempt_count": (
        "a fixed number of attempts is counting, not finishing; declare a "
        "model call, wall time or spending limit instead"),
    "retry_limit": (
        "a retry limit ends the run on arithmetic rather than on authority "
        "or a result"),
    "first_failure": (
        "one failed step becomes a typed next action, not the end of the "
        "night"),
    "good_enough_score": (
        "a score is a model observation; acceptance is an independent "
        "verification"),
    "model_says_done": (
        "a producer never accepts its own work"),
}

#: What a failure is allowed to become. The night picks one of these and
#: records it; there is no branch that simply tries the same thing again.
NEXT_ACTIONS = {
    "narrow_the_request": (
        "quote the failure and ask again for only the failing part"),
    "change_the_step": (
        "the same request failed the same way; move to a different step of "
        "the profile rather than repeating it"),
    "wait_for_the_provider": (
        "the server stopped answering; wait inside the declared wait and "
        "resume rather than restarting"),
    "record_and_continue": (
        "the observation is usable as it is; write it to the state and "
        "carry on"),
    "carry_forward_as_provisional": (
        "keep the best result so far, labelled provisional, with its "
        "findings"),
    "stop_and_ask": (
        "only a person can answer this; stop and name the question"),
}


class AuthorityError(ValueError):
    """A night that cannot be run as written."""


def ending_for(terminal_code: str) -> str:
    """Which of the five accepted endings a terminal code reports."""
    for ending, codes in ACCEPTED_ENDINGS.items():
        if terminal_code in codes:
            return ending
    raise AuthorityError(
        f"terminal code {terminal_code!r} belongs to no accepted ending; the "
        "five endings are " + ", ".join(ACCEPTED_ENDINGS))


@dataclass(frozen=True)
class ResidencyPolicy:
    """How long the server keeps the weights loaded between steps.

    ``reason`` is required because this is the one setting whose cost is
    invisible in the morning: a night that reloaded the weights at every
    step looks the same in the report as one that did not, except that it
    got less done.
    """

    keep_resident_seconds: int
    reason: str

    def __post_init__(self) -> None:
        if isinstance(self.keep_resident_seconds, bool) \
                or not isinstance(self.keep_resident_seconds, int) \
                or self.keep_resident_seconds < 0:
            raise AuthorityError(
                "keep_resident_seconds must be a whole number of seconds, "
                "zero or more; zero means the server may unload between "
                "steps and pay the load again at the next one")
        if not str(self.reason).strip():
            raise AuthorityError(
                "state why this residency was chosen; an unattended night "
                "that reloads the weights at every step looks identical in "
                "the morning report to one that does not")

    def covers(self, night_seconds: float) -> bool:
        """Whether the weights stay loaded across the whole night."""
        return self.keep_resident_seconds >= night_seconds

    def to_dict(self) -> dict:
        return {"record_type": "overnight_residency/v1",
                "keep_resident_seconds": self.keep_resident_seconds,
                "reason": self.reason}


@dataclass(frozen=True)
class OvernightAuthority:
    """Everything the night may do. What is absent here is refused."""

    night_hours: float
    max_model_calls: int
    workspace_root: str
    residency: ResidencyPolicy
    read_roots: tuple = ()
    write_roots: tuple = ()
    gate_command: str = ""
    outage_wait_seconds: float = 60.0
    spending_authority: str = "none"
    endings: tuple = tuple(ACCEPTED_ENDINGS)
    notes: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.night_hours, bool) \
                or not isinstance(self.night_hours, (int, float)) \
                or self.night_hours <= 0:
            raise AuthorityError("night_hours must be a positive number")
        if isinstance(self.max_model_calls, bool) \
                or not isinstance(self.max_model_calls, int) \
                or self.max_model_calls < 1:
            raise AuthorityError(
                "an unattended run declares its model call ceiling; nobody "
                "is awake to stop it")
        if not isinstance(self.residency, ResidencyPolicy):
            raise AuthorityError("residency must be a declared ResidencyPolicy")
        if isinstance(self.outage_wait_seconds, bool) \
                or not isinstance(self.outage_wait_seconds, (int, float)) \
                or self.outage_wait_seconds <= 0:
            raise AuthorityError(
                "outage_wait_seconds must be a positive number; an unbounded "
                "wait is not a declared wait")
        if self.spending_authority != "none":
            raise AuthorityError(
                "this night declares no spending authority; a paid route "
                "needs its own decision, not a local model's plan")
        workspace = str(self.workspace_root).strip()
        if not workspace or not os.path.isabs(workspace):
            raise AuthorityError(
                "the working folder must be one absolute path that persists "
                "across attempts")
        object.__setattr__(self, "workspace_root",
                           str(Path(workspace).resolve(strict=False)))
        for name in ("read_roots", "write_roots"):
            roots = tuple(str(item) for item in getattr(self, name))
            for root in roots:
                if not os.path.isabs(root):
                    raise AuthorityError(
                        f"every entry of {name} must be an absolute path; "
                        f"got {root!r}")
            object.__setattr__(self, name, tuple(
                str(Path(root).resolve(strict=False)) for root in roots))
        endings = tuple(self.endings)
        if not endings:
            raise AuthorityError("a night names at least one accepted ending")
        for ending in endings:
            if ending in REFUSED_ENDINGS:
                raise AuthorityError(
                    f"{ending} is not an ending a night may declare: "
                    + REFUSED_ENDINGS[ending])
            if ending not in ACCEPTED_ENDINGS:
                raise AuthorityError(
                    f"unknown ending {ending!r}; the five accepted endings "
                    "are " + ", ".join(ACCEPTED_ENDINGS))
        if "accepted_result" not in endings:
            raise AuthorityError(
                "a night that cannot end on an accepted result has no reason "
                "to run")
        object.__setattr__(self, "endings", endings)
        if self.gate_command:
            gate = str(self.gate_command)
            if not os.path.isabs(gate):
                raise AuthorityError(
                    "the gate is one absolute path to a script the night "
                    "runs; it is not a shell line")
            object.__setattr__(self, "gate_command",
                               str(Path(gate).resolve(strict=False)))

    def _within(self, path, roots) -> bool:
        if not roots:
            return False
        try:
            resolved = Path(path).resolve(strict=False)
        except OSError:
            return False
        for root in roots:
            try:
                resolved.relative_to(Path(root))
            except ValueError:
                continue
            return True
        return False

    def may_read(self, path) -> bool:
        """Whether a path is inside a declared read root or the working folder.

        The path is resolved first, so a symbolic link pointing out of the
        working folder and a path spelled with ``..`` both land outside and
        are refused, which is the only reading of confinement that survives
        an unattended night.
        """
        return self._within(path, (self.workspace_root,) + tuple(self.read_roots)
                            + tuple(self.write_roots))

    def may_write(self, path) -> bool:
        """Whether a path is inside a declared write root or the working folder."""
        return self._within(path, (self.workspace_root,)
                            + tuple(self.write_roots))

    def refuse_write(self, path) -> str:
        """The sentence recorded when a write lands outside the authority."""
        return (f"refused: writing {str(path)!r} is outside the folders this "
                "night declared. Declared: "
                + ", ".join((self.workspace_root,) + tuple(self.write_roots)))

    def to_dict(self) -> dict:
        return {
            "record_type": "overnight_authority/v1",
            "night_hours": float(self.night_hours),
            "max_model_calls": int(self.max_model_calls),
            "workspace_root": self.workspace_root,
            "read_roots": list(self.read_roots),
            "write_roots": list(self.write_roots),
            "gate_command": self.gate_command,
            "outage_wait_seconds": float(self.outage_wait_seconds),
            "spending_authority": self.spending_authority,
            "residency": self.residency.to_dict(),
            "endings": list(self.endings),
            "ending_terminal_codes": {
                ending: list(ACCEPTED_ENDINGS[ending])
                for ending in self.endings},
            "notes": list(self.notes),
        }


def self_test() -> dict:
    """Every guard beside the known wrong night it exists to refuse."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:220]})

    def refuses(name, call, fragment):
        try:
            call()
        except AuthorityError as error:
            check(name, fragment in str(error), str(error))
        else:
            check(name, False, "accepted a known wrong night")

    import tempfile

    residency = ResidencyPolicy(
        keep_resident_seconds=3600,
        reason="one load, then every later step answers without reloading")
    with tempfile.TemporaryDirectory() as folder:
        workspace = str(Path(folder) / "night")
        os.makedirs(workspace, exist_ok=True)
        authority = OvernightAuthority(
            night_hours=8.0, max_model_calls=200, workspace_root=workspace,
            residency=residency)
        check("a_complete_night_is_accepted",
              authority.to_dict()["record_type"] == "overnight_authority/v1")
        check("every_terminal_code_belongs_to_one_of_the_five_endings",
              all(ending_for(code.value) for code in SolveTerminalCode))
        check("the_working_folder_may_be_written",
              authority.may_write(os.path.join(workspace, "notes.md")))
        check("a_path_outside_every_declared_root_may_not_be_written",
              authority.may_write("/etc/passwd") is False)
        check("a_path_spelled_with_dot_dot_lands_outside_and_is_refused",
              authority.may_write(
                  os.path.join(workspace, "..", "escape.txt")) is False)
        link = Path(workspace) / "pointer"
        try:
            link.symlink_to("/etc")
            check("a_symbolic_link_out_of_the_working_folder_is_refused",
                  authority.may_write(str(link / "passwd")) is False)
        except OSError:
            check("a_symbolic_link_out_of_the_working_folder_is_refused",
                  True, "the platform refused to create a link; not exercised")
        check("the_refusal_sentence_names_the_folders_that_were_declared",
              workspace in authority.refuse_write("/etc/passwd"))

        refuses("a_night_that_may_call_a_model_without_a_ceiling_is_refused",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=0,
                    workspace_root=workspace, residency=residency),
                "nobody is awake to stop it")
        refuses("a_relative_working_folder_is_refused",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root="night", residency=residency),
                "one absolute path")
        refuses("an_undeclared_residency_is_refused",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=3600),
                "declared ResidencyPolicy")
        refuses("an_attempt_count_is_refused_as_an_ending",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=residency,
                    endings=("accepted_result", "attempt_count")),
                "counting, not finishing")
        refuses("a_retry_limit_is_refused_as_an_ending",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=residency,
                    endings=("accepted_result", "retry_limit")),
                "arithmetic rather than on authority")
        refuses("a_model_that_grades_itself_is_refused_as_an_ending",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=residency,
                    endings=("accepted_result", "model_says_done")),
                "never accepts its own work")
        refuses("a_night_that_cannot_succeed_is_refused",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=residency,
                    endings=("operator_cancellation",)),
                "no reason to run")
        refuses("an_unbounded_wait_is_refused",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=residency,
                    outage_wait_seconds=0),
                "not a declared wait")
        refuses("spending_this_night_never_declared_is_refused",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=residency,
                    spending_authority="up to ten dollars"),
                "its own decision")
        refuses("a_gate_that_is_a_shell_line_rather_than_a_script_is_refused",
                lambda: OvernightAuthority(
                    night_hours=8.0, max_model_calls=10,
                    workspace_root=workspace, residency=residency,
                    gate_command="pytest -q"),
                "not a shell line")

    refuses("a_residency_without_a_stated_reason_is_refused",
            lambda: ResidencyPolicy(keep_resident_seconds=3600, reason=" "),
            "state why this residency was chosen")
    refuses("a_negative_residency_is_refused",
            lambda: ResidencyPolicy(keep_resident_seconds=-1, reason="x"),
            "zero or more")
    check("a_residency_shorter_than_the_night_does_not_cover_it",
          ResidencyPolicy(keep_resident_seconds=300,
                          reason="declared short on purpose").covers(3600.0)
          is False)
    check("every_next_action_says_what_it_does_instead_of_repeating",
          all(NEXT_ACTIONS.values()) and "retry" not in NEXT_ACTIONS)
    passed = sum(item["passed"] for item in tests)
    return {"name": "overnight_authority", "tests": tests,
            "passed": passed, "total": len(tests)}
