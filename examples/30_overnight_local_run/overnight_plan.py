"""The written declaration a night runs under, checked before it starts.

An overnight run is a run nobody watches. Everything that would otherwise
be decided by a person at the keyboard has to be written down first: what
the run may do, what it may spend, how long it waits for a provider that
went quiet, and which endings are allowed to finish it.

The last of those is the one that goes wrong most often. A run that ends
after three tries has not finished the work, it has finished counting. The
accepted endings come from the persistent general solving decision record:

  accepted result   verification passed
  authority spent   model calls, passes, wall time or money ran out
  owner question    only the owner can answer it
  cancelled         an operator stopped it
  provider outage   recorded so the run resumes rather than restarts

This module holds those five, maps them to the terminal codes the solve
runtime actually returns, and refuses a plan that names anything else as a
reason to finish. It decides nothing at run time and calls no provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from loop_engine.code_nodes.solve_terminal import SolveTerminalCode
from loop_engine.core.model_routes import (RoutePolicy, RouteViolation,
                                           screen_route)

#: The five accepted endings, and the terminal codes that report each one.
#: Every code the solve runtime can return belongs to exactly one ending,
#: so a night can never finish for a reason outside this table.
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
    "question_only_the_owner_can_answer": (
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

#: Endings a plan may not declare, with the reason each one is refused.
#: These are the ways an unattended run quietly stops doing the work while
#: reporting that it finished.
REFUSED_ENDINGS = {
    "attempt_count": (
        "a fixed number of attempts is counting, not finishing; declare a "
        "model call, pass, wall time or spending limit instead"),
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


class PlanError(ValueError):
    """A night plan that cannot be run as written."""


def ending_for(terminal_code: str) -> str:
    """Which of the five accepted endings a terminal code reports."""
    for ending, codes in ACCEPTED_ENDINGS.items():
        if terminal_code in codes:
            return ending
    raise PlanError(
        f"terminal code {terminal_code!r} belongs to no accepted ending; the "
        "five endings are " + ", ".join(ACCEPTED_ENDINGS))


@dataclass(frozen=True)
class DeclaredAuthority:
    """What the night may do. Everything absent here is refused."""

    authorize_model_calls: bool = False
    max_model_calls: "int | None" = None
    allow_workspace_writes: bool = False
    allow_sandbox_commands: bool = False
    allow_local_execution: bool = False
    allow_network_reads: bool = False
    allow_model_failover: bool = False
    #: Counted generation on a local route is refused by the repository
    #: default, because a benchmark's token counts must be reproducible on
    #: another machine. An overnight run on your own hardware is not a
    #: benchmark, so it declares the permission deliberately and the plan
    #: records that it did.
    allow_local_counted_generation: bool = False
    spending_authority: str = "none"

    def __post_init__(self) -> None:
        for name in ("authorize_model_calls", "allow_workspace_writes",
                     "allow_sandbox_commands", "allow_local_execution",
                     "allow_network_reads", "allow_model_failover",
                     "allow_local_counted_generation"):
            if type(getattr(self, name)) is not bool:
                raise PlanError(f"{name} must be true or false, stated in the plan")
        if self.max_model_calls is not None and (
                isinstance(self.max_model_calls, bool)
                or not isinstance(self.max_model_calls, int)
                or self.max_model_calls < 1):
            raise PlanError("max_model_calls must be a positive whole number when set")
        if self.authorize_model_calls and self.max_model_calls is None:
            raise PlanError(
                "an unattended run that may call a model declares its call "
                "ceiling; nobody is awake to stop it")
        if self.allow_local_execution and self.allow_sandbox_commands is False:
            raise PlanError(
                "local execution without a sandbox is the weaker isolation "
                "and still needs allow_sandbox_commands declared")

    def route_policy(self) -> RoutePolicy:
        return RoutePolicy(
            allow_local_counted_generation=self.allow_local_counted_generation)

    def to_dict(self) -> dict:
        return {
            "record_type": "overnight_declared_authority/v1",
            "authorize_model_calls": self.authorize_model_calls,
            "max_model_calls": self.max_model_calls,
            "allow_workspace_writes": self.allow_workspace_writes,
            "allow_sandbox_commands": self.allow_sandbox_commands,
            "allow_local_execution": self.allow_local_execution,
            "allow_network_reads": self.allow_network_reads,
            "allow_model_failover": self.allow_model_failover,
            "allow_local_counted_generation": self.allow_local_counted_generation,
            "spending_authority": self.spending_authority,
        }


@dataclass(frozen=True)
class DeclaredWait:
    """How long the night waits for a provider that stopped answering.

    Two ceilings, because the two refusals are different events. An outage
    is a path that may come back in seconds. A spent allowance resets on
    the provider's own calendar and no amount of waiting in the next minute
    changes it. Both are bounded, so no wait is unbounded and no ending is
    reached by counting attempts.
    """

    outage_wait_seconds: float
    allowance_wait_seconds: float
    wait_attempt_ceiling: int

    def __post_init__(self) -> None:
        for name in ("outage_wait_seconds", "allowance_wait_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise PlanError(f"{name} must be a positive number of seconds")
        if (isinstance(self.wait_attempt_ceiling, bool)
                or not isinstance(self.wait_attempt_ceiling, int)
                or self.wait_attempt_ceiling < 1):
            raise PlanError("wait_attempt_ceiling must be a positive whole number")

    def to_dict(self) -> dict:
        return {
            "record_type": "overnight_declared_wait/v1",
            "outage_wait_seconds": float(self.outage_wait_seconds),
            "allowance_wait_seconds": float(self.allowance_wait_seconds),
            "wait_attempt_ceiling": self.wait_attempt_ceiling,
        }


@dataclass(frozen=True)
class OvernightPlan:
    """One night, declared before it starts and saved beside its result."""

    task_name: str
    route_name: str
    night_hours: float
    expected_steps: int
    authority: DeclaredAuthority
    wait: DeclaredWait
    endings: tuple[str, ...] = tuple(ACCEPTED_ENDINGS)
    runs_dir: str = ""
    workspace_root: str = ""
    verifier_command: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.task_name.strip():
            raise PlanError("a plan names the task it is for")
        if not self.route_name.strip():
            raise PlanError("a plan names the exact route it runs on")
        if (isinstance(self.night_hours, bool)
                or not isinstance(self.night_hours, (int, float))
                or self.night_hours <= 0):
            raise PlanError("night_hours must be a positive number")
        if (isinstance(self.expected_steps, bool)
                or not isinstance(self.expected_steps, int)
                or self.expected_steps < 1):
            raise PlanError("expected_steps must be a positive whole number")
        if not isinstance(self.authority, DeclaredAuthority):
            raise PlanError("authority must be a DeclaredAuthority")
        if not isinstance(self.wait, DeclaredWait):
            raise PlanError("wait must be a DeclaredWait")
        endings = tuple(self.endings)
        if not endings:
            raise PlanError("a plan names at least one accepted ending")
        for ending in endings:
            if ending in REFUSED_ENDINGS:
                raise PlanError(
                    f"{ending} is not an ending a night may declare: "
                    + REFUSED_ENDINGS[ending])
            if ending not in ACCEPTED_ENDINGS:
                raise PlanError(
                    f"unknown ending {ending!r}; the five accepted endings are "
                    + ", ".join(ACCEPTED_ENDINGS))
        if "accepted_result" not in endings:
            raise PlanError(
                "a night that cannot end on an accepted result has no reason "
                "to run")
        object.__setattr__(self, "endings", endings)
        if self.authority.allow_workspace_writes and not self.workspace_root.strip():
            raise PlanError(
                "workspace writes need a path confined workspace_root")

    def screen(self, route) -> None:
        """Refuse before the night starts what the gateway would refuse at 3am.

        A local route used for counted generation is the case that matters
        here: the repository default refuses it, the refusal names the
        policy switch, and a plan that forgot the switch should fail at the
        keyboard rather than after the operator has gone to bed.
        """
        try:
            screen_route(route, purpose="counted_generation",
                         policy=self.authority.route_policy())
        except RouteViolation as exc:
            raise PlanError(
                f"the plan's route {self.route_name!r} cannot serve this "
                f"night: {exc}") from exc

    def to_dict(self) -> dict:
        return {
            "record_type": "overnight_plan/v1",
            "task_name": self.task_name,
            "route_name": self.route_name,
            "night_hours": float(self.night_hours),
            "expected_steps": self.expected_steps,
            "authority": self.authority.to_dict(),
            "wait": self.wait.to_dict(),
            "endings": list(self.endings),
            "ending_terminal_codes": {
                ending: list(ACCEPTED_ENDINGS[ending]) for ending in self.endings},
            "runs_dir": self.runs_dir,
            "workspace_root": self.workspace_root,
            "verifier_command": self.verifier_command,
            "notes": list(self.notes),
        }


def self_check() -> list[dict]:
    """Every guard with the known wrong plan it exists to refuse."""
    from loop_engine.core.model_routes import ModelRoute

    results = []

    def check(name, passed, detail=""):
        results.append({"check": name, "passed": bool(passed),
                        "detail": str(detail)[:200]})

    def refuses(name, call, expect_fragment):
        try:
            call()
        except PlanError as exc:
            check(name, expect_fragment in str(exc), str(exc))
        else:
            check(name, False, "accepted a known wrong plan")

    authority = DeclaredAuthority(
        authorize_model_calls=True, max_model_calls=400,
        allow_local_counted_generation=True)
    wait = DeclaredWait(outage_wait_seconds=60.0,
                        allowance_wait_seconds=900.0, wait_attempt_ceiling=8)
    good = OvernightPlan(task_name="repair the failing import check",
                         route_name="custom.local_ollama", night_hours=12.0,
                         expected_steps=8, authority=authority, wait=wait)
    check("a_complete_plan_is_accepted",
          good.to_dict()["record_type"] == "overnight_plan/v1")
    check("every_terminal_code_belongs_to_one_of_the_five_endings",
          all(ending_for(code.value) for code in SolveTerminalCode))

    refuses("an_attempt_count_is_refused_as_an_ending",
            lambda: OvernightPlan(
                task_name="t", route_name="custom.local_ollama",
                night_hours=12.0, expected_steps=8, authority=authority,
                wait=wait, endings=("accepted_result", "attempt_count")),
            "counting, not finishing")
    refuses("a_retry_limit_is_refused_as_an_ending",
            lambda: OvernightPlan(
                task_name="t", route_name="custom.local_ollama",
                night_hours=12.0, expected_steps=8, authority=authority,
                wait=wait, endings=("accepted_result", "retry_limit")),
            "ends the run on arithmetic")
    refuses("a_model_that_grades_itself_is_refused_as_an_ending",
            lambda: OvernightPlan(
                task_name="t", route_name="custom.local_ollama",
                night_hours=12.0, expected_steps=8, authority=authority,
                wait=wait, endings=("accepted_result", "model_says_done")),
            "never accepts its own work")
    refuses("a_night_that_cannot_succeed_is_refused",
            lambda: OvernightPlan(
                task_name="t", route_name="custom.local_ollama",
                night_hours=12.0, expected_steps=8, authority=authority,
                wait=wait, endings=("operator_cancellation",)),
            "no reason to run")
    refuses("model_calls_without_a_ceiling_are_refused_for_an_unattended_run",
            lambda: DeclaredAuthority(authorize_model_calls=True),
            "nobody is awake to stop it")
    refuses("a_wait_without_a_ceiling_is_refused",
            lambda: DeclaredWait(outage_wait_seconds=60.0,
                                 allowance_wait_seconds=900.0,
                                 wait_attempt_ceiling=0),
            "wait_attempt_ceiling")
    refuses("workspace_writes_without_a_confined_root_are_refused",
            lambda: OvernightPlan(
                task_name="t", route_name="custom.local_ollama",
                night_hours=12.0, expected_steps=8,
                authority=DeclaredAuthority(
                    authorize_model_calls=True, max_model_calls=10,
                    allow_workspace_writes=True),
                wait=wait),
            "path confined workspace_root")

    local_route = ModelRoute("custom.local_ollama", "local_ollama",
                             "qwen3:8b", "local",
                             purposes=("counted_generation", "decide_label"))
    unpermitted = OvernightPlan(
        task_name="t", route_name="custom.local_ollama", night_hours=12.0,
        expected_steps=8, wait=wait,
        authority=DeclaredAuthority(authorize_model_calls=True,
                                    max_model_calls=10))
    refuses("a_local_route_without_the_declared_policy_is_refused_before_the_night",
            lambda: unpermitted.screen(local_route),
            "allow_local_counted_generation")
    good.screen(local_route)
    check("the_same_route_passes_once_the_policy_is_declared", True,
          "allow_local_counted_generation=True permits counted generation locally")
    return results
