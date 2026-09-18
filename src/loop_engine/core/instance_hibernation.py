"""Reservation, freeze, checkpoint and release, and progress-aware stalls for harness instances.

Pausing a process stops its execution and keeps its memory. Hibernating it
means something else: reach a supported boundary, write and verify a
checkpoint of the declared state, fence the old attempt so it can no longer
publish as the current owner, confirm the worker and the processes it owns
have actually stopped, and only then release the capacity it reserved. This
module owns those four distinct actions (yield, freeze, checkpoint and
release, cancel), the reservation ledger that admits work against measured
memory before it starts and refuses to free capacity that was never
confirmed gone, the checkpoint record with its declared restoration
fidelity, and the progress assessment that separates a declared wait from a
stall. It grants no authority, starts nothing, and signals nothing itself:
every operating-system effect goes through an injected controller that acts
only on an owned handle.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .local_resources import EVENT_KINDS, STATES, InstanceLedger, LocalResourceError

#: What a caller can ask of a running instance, and whether it frees memory.
ACTIONS = ("yield", "freeze", "checkpoint_and_release", "cancel")
ACTION_FREES_MEMORY = ((ACTIONS[0], False), (ACTIONS[1], False), (ACTIONS[2], True), (ACTIONS[3], True))
_FREES_MEMORY = dict(ACTION_FREES_MEMORY)
#: The ordered steps of the hibernation protocol; a report names the last one reached.
HIBERNATION_STEPS = ("requested", "quiesced", "checkpoint_written", "checkpoint_verified",
                     "publication_fenced", "worker_confirmed_stopped", "reservation_released",
                     "hibernated")
#: How much of a stopped instance an adapter can actually restore. A caller
#: declares one; claiming more than the adapter declares is refused.
FIDELITIES = ("restart_only", "native_session_resume", "application_checkpoint",
              "filesystem_snapshot", "process_memory_restore")
#: What a step reports about its own progress. A declared wait is not a stall.
PROGRESS_KINDS = ("advancing", "waiting_declared", "no_progress", "unknown")
WAITING_REASONS = ("model_call", "dependency", "approval", "external_effect", "queue")
CHECKPOINT_RECORD_TYPE = "instance_checkpoint/v1"
RESERVATION_RECORD_TYPE = "resource_reservation/v1"
HIBERNATION_RECORD_TYPE = "hibernation_report/v1"
PROGRESS_RECORD_TYPE = "progress_assessment/v1"
#: Memory kept back from admission for the operating system, the controller,
#: and the work of writing a checkpoint when capacity runs short.
DEFAULT_HEADROOM_FRACTION = 0.15


class HibernationError(LocalResourceError):
    """A reservation, checkpoint, action, or protocol step is invalid."""


@dataclass(frozen=True)
class Checkpoint:
    """The declared state one instance can be restored from, and how far that goes."""

    instance_id: str
    fidelity: str
    session_ref: str = ""
    workspace_ref: str = ""
    intelligence_ref: str = ""
    graph_position: str = ""
    published_outputs: tuple[str, ...] = ()
    pending_effects: tuple[str, ...] = ()
    resume_requirements: tuple[str, ...] = ()
    written_at: float = 0.0

    def __post_init__(self):
        if self.fidelity not in FIDELITIES:
            raise HibernationError(f"fidelity must be one of {FIDELITIES}")
        if not isinstance(self.instance_id, str) or not self.instance_id.strip():
            raise HibernationError("a checkpoint names its instance")
        for name in ("session_ref", "workspace_ref", "intelligence_ref", "graph_position"):
            if not isinstance(getattr(self, name), str):
                raise HibernationError(f"{name} must be text")
        for name in ("published_outputs", "pending_effects", "resume_requirements"):
            values = tuple(getattr(self, name))
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise HibernationError(f"{name} must be nonempty references")
            object.__setattr__(self, name, values)
        if self.fidelity != FIDELITIES[0] and not (self.session_ref or self.workspace_ref):
            raise HibernationError(
                f"fidelity {self.fidelity!r} restores state, so the checkpoint names a session "
                "or a workspace to restore it from")

    @property
    def restores_state(self) -> bool:
        return self.fidelity != FIDELITIES[0]

    def to_dict(self) -> dict:
        return {"record_type": CHECKPOINT_RECORD_TYPE, "instance_id": self.instance_id,
                "fidelity": self.fidelity, "session_ref": self.session_ref,
                "workspace_ref": self.workspace_ref, "intelligence_ref": self.intelligence_ref,
                "graph_position": self.graph_position,
                "published_outputs": list(self.published_outputs),
                "pending_effects": list(self.pending_effects),
                "resume_requirements": list(self.resume_requirements),
                "written_at": self.written_at, "restores_state": self.restores_state}

    @property
    def digest(self) -> str:
        body = {key: value for key, value in self.to_dict().items() if key != "written_at"}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class Reservation:
    """Capacity held for one instance from before it starts until its worker is gone."""

    reservation_id: str
    instance_id: str
    memory_bytes: int
    reserved_at: float
    released_at: "float | None" = None
    release_reason: str = ""

    @property
    def active(self) -> bool:
        return self.released_at is None

    def to_dict(self) -> dict:
        return {"record_type": RESERVATION_RECORD_TYPE, "reservation_id": self.reservation_id,
                "instance_id": self.instance_id, "memory_bytes": self.memory_bytes,
                "reserved_at": self.reserved_at, "released_at": self.released_at,
                "release_reason": self.release_reason, "active": self.active}


class ReservationLedger:
    """Memory reserved before work starts, released only when a worker is confirmed gone."""

    def __init__(self, *, headroom_fraction: float = DEFAULT_HEADROOM_FRACTION):
        if type(headroom_fraction) not in (int, float) or not 0 <= headroom_fraction < 1:
            raise HibernationError("headroom_fraction must be a fraction below 1")
        self.headroom_fraction = headroom_fraction
        self._reservations: dict = {}

    @property
    def reserved_bytes(self) -> int:
        return sum(item.memory_bytes for item in self._reservations.values() if item.active)

    def active(self) -> tuple[Reservation, ...]:
        return tuple(item for item in self._reservations.values() if item.active)

    def get(self, reservation_id: str) -> Reservation:
        try:
            return self._reservations[reservation_id]
        except KeyError:
            raise HibernationError(f"no reservation {reservation_id!r}") from None

    def headroom_bytes(self, snapshot) -> "int | None":
        total = getattr(snapshot, "memory_total_bytes", None)
        return None if not total else int(total * self.headroom_fraction)

    def reserve(self, instance_id: str, memory_bytes: int, snapshot, *, now: float,
                ledger: "InstanceLedger | None" = None) -> Reservation:
        """Hold capacity for one instance, or refuse with the number that decided it.

        The measurement is of the machine as it stands, so capacity already
        reserved for instances that have not yet grown into it is counted
        again here; otherwise two admissions in the same second would both
        see the same free memory and both start.
        """
        if type(memory_bytes) is not int or memory_bytes <= 0:
            raise HibernationError("a reservation names a positive number of bytes")
        if not instance_id or not isinstance(instance_id, str):
            raise HibernationError("a reservation names its instance")
        available = getattr(snapshot, "memory_available_bytes", None)
        headroom = self.headroom_bytes(snapshot)
        if available is None or headroom is None:
            raise HibernationError(
                "memory could not be measured, so no capacity is reserved; an unmeasured "
                "machine is not an unlimited one")
        free_after = available - self.reserved_bytes - memory_bytes
        if free_after < headroom:
            raise HibernationError(
                f"reserving {memory_bytes} bytes would leave {free_after} bytes, below the "
                f"headroom {headroom} kept for the operating system and for writing a checkpoint")
        reservation = Reservation(f"reservation:{instance_id}:{len(self._reservations)}",
                                  instance_id, memory_bytes, now)
        self._reservations[reservation.reservation_id] = reservation
        if ledger is not None:
            ledger.record_event(EVENT_KINDS[10], instance_id, now,
                                f"reserved {memory_bytes} bytes", reservation_id=reservation.reservation_id)
        return reservation

    def release(self, reservation_id: str, *, now: float, confirmed_stopped: bool, reason: str,
                ledger: "InstanceLedger | None" = None) -> Reservation:
        """Free held capacity, and only when the worker is confirmed gone.

        A written checkpoint and a sent signal are both requests. A worker
        that did not stop still holds its memory, so the reservation stands
        and the refusal is recorded.
        """
        reservation = self.get(reservation_id)
        if not reservation.active:
            raise HibernationError(f"reservation {reservation_id!r} is already released")
        if not confirmed_stopped:
            if ledger is not None:
                ledger.record_event(EVENT_KINDS[15], reservation.instance_id, now,
                                    "the worker was not confirmed stopped, so its capacity stays reserved",
                                    reservation_id=reservation_id)
            raise HibernationError(
                "capacity is released only after the worker is confirmed stopped; a written "
                "checkpoint or a sent signal is a request, not a confirmation")
        reservation.released_at = now
        reservation.release_reason = reason
        if ledger is not None:
            ledger.record_event(EVENT_KINDS[11], reservation.instance_id, now, reason,
                                reservation_id=reservation_id, memory_bytes=reservation.memory_bytes)
        return reservation

    def to_dict(self) -> dict:
        return {"reserved_bytes": self.reserved_bytes, "headroom_fraction": self.headroom_fraction,
                "reservations": [item.to_dict() for item in self._reservations.values()]}


@dataclass(frozen=True)
class ProgressSignal:
    """What one instance reports about its own progress at one moment."""

    kind: str
    at: float
    detail: str = ""
    waiting_reason: str = ""
    waiting_deadline_at: "float | None" = None

    def __post_init__(self):
        if self.kind not in PROGRESS_KINDS:
            raise HibernationError(f"progress kind must be one of {PROGRESS_KINDS}")
        if self.kind == PROGRESS_KINDS[1]:
            if self.waiting_reason not in WAITING_REASONS:
                raise HibernationError(f"a declared wait names one of {WAITING_REASONS}")
            if self.waiting_deadline_at is None:
                raise HibernationError("a declared wait names the time its own deadline expires")
        elif self.waiting_reason:
            raise HibernationError("only a declared wait carries a waiting reason")

    def to_dict(self) -> dict:
        return {"kind": self.kind, "at": self.at, "detail": self.detail,
                "waiting_reason": self.waiting_reason, "waiting_deadline_at": self.waiting_deadline_at}


@dataclass(frozen=True)
class ProgressAssessment:
    """Whether an instance is stalled, and the reason either way."""

    instance_id: str
    stalled: bool
    reason: str
    heartbeat_age_seconds: float
    signal: "ProgressSignal | None" = None

    def to_dict(self) -> dict:
        return {"record_type": PROGRESS_RECORD_TYPE, "instance_id": self.instance_id,
                "stalled": self.stalled, "reason": self.reason,
                "heartbeat_age_seconds": round(self.heartbeat_age_seconds, 3),
                "signal": self.signal.to_dict() if self.signal is not None else None}


def assess_progress(ledger: InstanceLedger, instance_id: str, policy, *, now: float,
                    signal: "ProgressSignal | None" = None) -> ProgressAssessment:
    """A stall is silence without a declared wait, or a declared wait past its own deadline.

    An instance waiting for an authorized model call is not stalled while its
    own deadline holds, however quiet it is. An instance that keeps sending
    heartbeats while reporting no progress is stalled once the policy's age
    passes, because a heartbeat is liveness, not work.
    """
    record = ledger.get(instance_id)
    age = now - record.last_heartbeat_at
    if signal is not None and signal.kind == PROGRESS_KINDS[1]:
        if now <= signal.waiting_deadline_at:
            return ProgressAssessment(instance_id, False,
                                      f"waiting on {signal.waiting_reason} until "
                                      f"{signal.waiting_deadline_at}", age, signal)
        return ProgressAssessment(instance_id, True,
                                  f"the declared wait on {signal.waiting_reason} passed its "
                                  f"deadline {signal.waiting_deadline_at}", age, signal)
    if signal is not None and signal.kind == PROGRESS_KINDS[0]:
        if age <= policy.stall_after_seconds:
            return ProgressAssessment(instance_id, False, "advancing", age, signal)
        return ProgressAssessment(instance_id, True,
                                  f"reported advancing but its last heartbeat is {round(age, 3)} "
                                  f"seconds old, above {policy.stall_after_seconds}", age, signal)
    if age > policy.stall_after_seconds:
        named = signal.kind if signal is not None else PROGRESS_KINDS[3]
        return ProgressAssessment(instance_id, True,
                                  f"progress {named} and no heartbeat for {round(age, 3)} seconds, "
                                  f"above {policy.stall_after_seconds}", age, signal)
    return ProgressAssessment(instance_id, False,
                              f"no heartbeat for {round(age, 3)} seconds, within "
                              f"{policy.stall_after_seconds}", age, signal)


@dataclass(frozen=True)
class HibernationReport:
    """What the protocol reached, and what it refused to claim."""

    instance_id: str
    action: str
    steps_reached: tuple[str, ...]
    hibernated: bool
    memory_released: bool
    checkpoint_digest: str = ""
    fidelity: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {"record_type": HIBERNATION_RECORD_TYPE, "instance_id": self.instance_id,
                "action": self.action, "steps_reached": list(self.steps_reached),
                "hibernated": self.hibernated, "memory_released": self.memory_released,
                "checkpoint_digest": self.checkpoint_digest, "fidelity": self.fidelity,
                "reason": self.reason}


def _require(controller, *names) -> None:
    missing = [name for name in names if not callable(getattr(controller, name, None))]
    if missing:
        raise HibernationError(f"the controller must offer {', '.join(missing)}")


def freeze(ledger: InstanceLedger, instance_id: str, controller, *, now: float,
           reason: str = "") -> HibernationReport:
    """Stop execution and keep the memory; this is a freeze, never a hibernation."""
    _require(controller, "pause")
    record = ledger.get(instance_id)
    if record.handle is None:
        ledger.record_event(EVENT_KINDS[9], instance_id, now, reason, action=ACTIONS[1])
        return HibernationReport(instance_id, ACTIONS[1], (), False, False,
                                 reason="no owned handle, so nothing was signaled")
    controller.pause(record.handle)
    ledger.transition(instance_id, STATES[1], now=now, reason=reason or "frozen on request")
    return HibernationReport(instance_id, ACTIONS[1], (), False, _FREES_MEMORY[ACTIONS[1]],
                             reason="execution stopped; the memory stays held until a checkpoint "
                                    "and a confirmed stop release it")


def hibernate(ledger: InstanceLedger, instance_id: str, controller, write_checkpoint, *, now: float,
              reservations: "ReservationLedger | None" = None,
              reservation_id: str = "", fidelity: str = FIDELITIES[2]) -> HibernationReport:
    """Checkpoint, fence, stop, confirm, and only then release the reserved capacity.

    ``write_checkpoint`` is an injected callable that returns a typed
    ``Checkpoint``; this module writes no files. The controller must offer
    ``quiesce``, ``stop``, and ``confirm_stopped``; a controller that cannot
    confirm cannot end a hibernation, because unconfirmed memory is not free.
    Every step is recorded, and the report names the last step reached.
    """
    _require(controller, "quiesce", "stop", "confirm_stopped")
    if not callable(write_checkpoint):
        raise HibernationError("hibernation needs a callable that writes the checkpoint")
    if fidelity not in FIDELITIES:
        raise HibernationError(f"fidelity must be one of {FIDELITIES}")
    record = ledger.get(instance_id)
    if record.state in (STATES[2], STATES[3]):
        raise HibernationError(f"instance {instance_id!r} is already {record.state}")
    if record.handle is None:
        ledger.record_event(EVENT_KINDS[9], instance_id, now, "hibernation", action=ACTIONS[2])
        return HibernationReport(instance_id, ACTIONS[2], (), False, False,
                                 reason="no owned handle, so nothing was signaled")
    steps = [HIBERNATION_STEPS[0]]
    controller.quiesce(record.handle)
    steps.append(HIBERNATION_STEPS[1])
    checkpoint = write_checkpoint(record)
    if not isinstance(checkpoint, Checkpoint):
        raise HibernationError("the checkpoint writer must return a typed Checkpoint")
    if checkpoint.instance_id != instance_id:
        raise HibernationError("the checkpoint names another instance")
    if FIDELITIES.index(checkpoint.fidelity) > FIDELITIES.index(fidelity):
        raise HibernationError(
            f"the checkpoint claims {checkpoint.fidelity!r}, above the {fidelity!r} this adapter "
            "declares; an adapter cannot promise a restoration it does not perform")
    steps.append(HIBERNATION_STEPS[2])
    ledger.record_event(EVENT_KINDS[12], instance_id, now, "checkpoint written",
                        digest=checkpoint.digest, fidelity=checkpoint.fidelity)
    verifier = getattr(controller, "verify_checkpoint", None)
    if callable(verifier) and not verifier(checkpoint):
        return HibernationReport(instance_id, ACTIONS[2], tuple(steps), False, False,
                                 checkpoint.digest, checkpoint.fidelity,
                                 "the checkpoint did not verify, so the instance keeps running")
    steps.append(HIBERNATION_STEPS[3])
    ledger.record_event(EVENT_KINDS[13], instance_id, now, "checkpoint verified",
                        digest=checkpoint.digest)
    fence = getattr(controller, "fence_publication", None)
    if callable(fence):
        fence(record.handle)
    steps.append(HIBERNATION_STEPS[4])
    ledger.record_event(EVENT_KINDS[14], instance_id, now,
                        "the stopped attempt can no longer publish as the current owner")
    controller.stop(record.handle)
    if not controller.confirm_stopped(record.handle):
        ledger.record_event(EVENT_KINDS[15], instance_id, now,
                            "the worker did not confirm it stopped; its capacity stays reserved")
        return HibernationReport(instance_id, ACTIONS[2], tuple(steps), False, False,
                                 checkpoint.digest, checkpoint.fidelity,
                                 "the worker was not confirmed stopped, so no capacity was released")
    steps.append(HIBERNATION_STEPS[5])
    released = False
    if reservations is not None and reservation_id:
        reservations.release(reservation_id, now=now, confirmed_stopped=True,
                             reason=f"hibernated with a {checkpoint.fidelity} checkpoint",
                             ledger=ledger)
        released = True
        steps.append(HIBERNATION_STEPS[6])
    ledger.transition(instance_id, STATES[2], now=now,
                      reason=f"hibernated with a {checkpoint.fidelity} checkpoint")
    steps.append(HIBERNATION_STEPS[7])
    return HibernationReport(instance_id, ACTIONS[2], tuple(steps), True, released,
                             checkpoint.digest, checkpoint.fidelity,
                             "checkpoint verified, publication fenced, worker confirmed stopped")


@dataclass(frozen=True)
class ResumeOutcome:
    """Whether a hibernated instance may start again now, and from what."""

    instance_id: str
    resumed: bool
    reason: str
    reservation_id: str = ""
    restores_state: bool = False
    checkpoint_digest: str = ""
    unresolved_effects: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"instance_id": self.instance_id, "resumed": self.resumed, "reason": self.reason,
                "reservation_id": self.reservation_id, "restores_state": self.restores_state,
                "checkpoint_digest": self.checkpoint_digest,
                "unresolved_effects": list(self.unresolved_effects)}


def resume(ledger: InstanceLedger, instance_id: str, checkpoint: Checkpoint, reservations: ReservationLedger,
           snapshot, *, now: float, memory_bytes: int) -> ResumeOutcome:
    """Take capacity again before restarting; a refusal names the number that caused it."""
    if not isinstance(checkpoint, Checkpoint):
        raise HibernationError("resume needs the typed checkpoint the hibernation wrote")
    record = ledger.get(instance_id)
    if record.state != STATES[2]:
        raise HibernationError(f"instance {instance_id!r} is {record.state}, not hibernated")
    if checkpoint.instance_id != instance_id:
        raise HibernationError("the checkpoint names another instance")
    try:
        reservation = reservations.reserve(instance_id, memory_bytes, snapshot, now=now, ledger=ledger)
    except HibernationError as exc:
        return ResumeOutcome(instance_id, False, str(exc), restores_state=checkpoint.restores_state,
                             checkpoint_digest=checkpoint.digest,
                             unresolved_effects=checkpoint.pending_effects)
    ledger.transition(instance_id, STATES[0], now=now,
                      reason=f"resumed from a {checkpoint.fidelity} checkpoint")
    ledger.record_event(EVENT_KINDS[16], instance_id, now,
                        f"resumed from a {checkpoint.fidelity} checkpoint",
                        digest=checkpoint.digest,
                        unresolved_effects=list(checkpoint.pending_effects))
    reason = ("restarted without restored state" if not checkpoint.restores_state
              else f"restored from a {checkpoint.fidelity} checkpoint")
    if checkpoint.pending_effects:
        reason += ("; its pending external effects are unresolved and need reconciliation "
                   "before they are repeated")
    return ResumeOutcome(instance_id, True, reason, reservation.reservation_id,
                         checkpoint.restores_state, checkpoint.digest, checkpoint.pending_effects)


class ProcessTreeController:
    """Signal an owned process group, and confirm it is gone before capacity is freed.

    The signaller and the liveness probe are injected so the contract can be
    exercised without sending a real signal. Only a declared owned group is
    ever signaled; an unowned identity is refused by name.
    """

    def __init__(self, owned_groups, *, signaller=None, alive=None):
        self._owned = set(int(item) for item in owned_groups)
        self._signaller = signaller
        self._alive = alive

    def _check(self, group) -> int:
        if int(group) not in self._owned:
            raise HibernationError(f"process group {group} is not an owned handle")
        return int(group)

    def _send(self, group, name: str) -> None:
        import signal as signal_module
        number = getattr(signal_module, name)
        if self._signaller is not None:
            self._signaller(self._check(group), number)
            return
        import os
        os.killpg(self._check(group), number)

    def pause(self, group) -> None:
        self._send(group, "SIGSTOP")

    def resume(self, group) -> None:
        self._send(group, "SIGCONT")

    def quiesce(self, group) -> None:
        """Ask the tree to stop starting new work; the harness decides how."""
        self._send(group, "SIGUSR1")

    def stop(self, group) -> None:
        self._send(group, "SIGTERM")

    def confirm_stopped(self, group) -> bool:
        """Whether the owned group is gone; unknown counts as not stopped."""
        checked = self._check(group)
        if self._alive is not None:
            return not self._alive(checked)
        import os
        try:
            os.killpg(checked, 0)
        except ProcessLookupError:
            return True
        except OSError:
            return False
        return False


def self_test() -> dict:
    """Reservations, the four actions, the ordered protocol, fidelity, and progress."""
    from .local_resources import INSTANCE_KINDS, ResourcePolicy, ResourceSnapshot
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except HibernationError:
            return True
        except Exception:  # noqa: BLE001  (a crash is not a typed refusal)
            return False
        return False

    def machine(available: int, total: int = 1000) -> ResourceSnapshot:
        return ResourceSnapshot(1000.0, 4, 1.0, total, available, "fixture", 1.0, None, None, None)

    check("the_four_actions_declare_whether_they_free_memory",
          _FREES_MEMORY[ACTIONS[0]] is False and _FREES_MEMORY[ACTIONS[1]] is False
          and _FREES_MEMORY[ACTIONS[2]] is True and _FREES_MEMORY[ACTIONS[3]] is True
          and len(ACTION_FREES_MEMORY) == len(ACTIONS) == 4)
    ledger = InstanceLedger()
    ledger.register("i1", INSTANCE_KINDS[0], "loop-a", now=1000.0, handle=101, memory_bytes=300)
    reservations = ReservationLedger(headroom_fraction=0.1)
    held = reservations.reserve("i1", 300, machine(800), now=1000.0, ledger=ledger)
    check("capacity_is_held_before_the_work_starts_and_counted_against_the_next_admission",
          held.active and reservations.reserved_bytes == 300
          and refuses(lambda: reservations.reserve("i2", 450, machine(800), now=1000.0))
          and reservations.reserve("i3", 300, machine(800), now=1000.0).active
          and reservations.reserved_bytes == 600,
          f"reserved={reservations.reserved_bytes}")
    check("an_unmeasured_machine_reserves_nothing_and_a_bad_request_is_refused",
          refuses(lambda: reservations.reserve("i4", 10, machine(None), now=1.0))
          and refuses(lambda: reservations.reserve("i4", 0, machine(800), now=1.0))
          and refuses(lambda: reservations.reserve("", 10, machine(800), now=1.0))
          and refuses(lambda: ReservationLedger(headroom_fraction=1.0))
          and refuses(lambda: reservations.get("reservation:absent:0")))
    probe = reservations.reserve("i1", 50, machine(800), now=1000.5, ledger=ledger)
    check("capacity_is_never_released_on_an_unconfirmed_stop",
          refuses(lambda: reservations.release(probe.reservation_id, now=1001.0,
                                               confirmed_stopped=False, reason="asked",
                                               ledger=ledger))
          and probe.active and reservations.reserved_bytes == 650
          and any(event["kind"] == EVENT_KINDS[15] for event in ledger.events))
    reservations.release(probe.reservation_id, now=1001.5, confirmed_stopped=True,
                         reason="the probe worker is gone", ledger=ledger)

    class Controller:
        def __init__(self, *, confirms=True, verifies=True):
            self.calls = []
            self._confirms = confirms
            self._verifies = verifies

        def pause(self, handle):
            self.calls.append(("pause", handle))

        def quiesce(self, handle):
            self.calls.append(("quiesce", handle))

        def stop(self, handle):
            self.calls.append(("stop", handle))

        def fence_publication(self, handle):
            self.calls.append(("fence", handle))

        def verify_checkpoint(self, checkpoint):
            self.calls.append(("verify", checkpoint.digest))
            return self._verifies

        def confirm_stopped(self, handle):
            self.calls.append(("confirm", handle))
            return self._confirms

    controller = Controller()
    frozen = freeze(ledger, "i1", controller, now=1002.0, reason="memory pressure")
    check("a_freeze_stops_execution_and_keeps_the_memory",
          frozen.action == ACTIONS[1] and frozen.memory_released is False
          and frozen.hibernated is False and ledger.get("i1").state == STATES[1]
          and ("pause", 101) in controller.calls and held.active
          and "stays held" in frozen.reason)

    def writer(record):
        return Checkpoint(record.instance_id, FIDELITIES[2], session_ref="session:abc",
                          workspace_ref="workspace:i1", published_outputs=("solution:v1",),
                          pending_effects=("provider-call:77",), written_at=1003.0)

    report = hibernate(ledger, "i1", controller, writer, now=1003.0, reservations=reservations,
                       reservation_id=held.reservation_id)
    check("hibernation_walks_every_step_in_order_and_only_then_releases_the_capacity",
          report.hibernated and report.memory_released
          and report.steps_reached == HIBERNATION_STEPS
          and [name for name, _ in controller.calls[1:]] == ["quiesce", "verify", "fence", "stop", "confirm"]
          and ledger.get("i1").state == STATES[2] and not held.active
          and reservations.reserved_bytes == 300
          and [event["kind"] for event in ledger.events[-5:]].count(EVENT_KINDS[11]) == 1,
          json.dumps(report.to_dict())[:200])
    unconfirmed_ledger = InstanceLedger()
    unconfirmed_ledger.register("u1", INSTANCE_KINDS[0], "loop-b", now=1.0, handle=7)
    unconfirmed_reservations = ReservationLedger(headroom_fraction=0.1)
    unconfirmed_held = unconfirmed_reservations.reserve("u1", 100, machine(800), now=1.0)
    unconfirmed = hibernate(unconfirmed_ledger, "u1", Controller(confirms=False), writer_for("u1"),
                            now=2.0, reservations=unconfirmed_reservations,
                            reservation_id=unconfirmed_held.reservation_id)
    check("a_worker_that_does_not_confirm_it_stopped_keeps_its_capacity_and_its_state",
          unconfirmed.hibernated is False and unconfirmed.memory_released is False
          and unconfirmed.steps_reached[-1] == HIBERNATION_STEPS[4]
          and unconfirmed_held.active and unconfirmed_ledger.get("u1").state == STATES[0]
          and any(event["kind"] == EVENT_KINDS[15] for event in unconfirmed_ledger.events),
          json.dumps(unconfirmed.to_dict())[:200])
    failed_ledger = InstanceLedger()
    failed_ledger.register("v1", INSTANCE_KINDS[0], "loop-c", now=1.0, handle=8)
    unverified = hibernate(failed_ledger, "v1", Controller(verifies=False), writer_for("v1"), now=2.0)
    check("a_checkpoint_that_does_not_verify_leaves_the_instance_running",
          unverified.hibernated is False and unverified.steps_reached[-1] == HIBERNATION_STEPS[2]
          and failed_ledger.get("v1").state == STATES[0]
          and "did not verify" in unverified.reason)
    check("a_checkpoint_cannot_claim_a_restoration_the_adapter_does_not_perform",
          refuses(lambda: hibernate(failed_ledger, "v1", Controller(),
                                    lambda record: Checkpoint("v1", FIDELITIES[4],
                                                              workspace_ref="w"),
                                    now=3.0, fidelity=FIDELITIES[2]))
          and refuses(lambda: Checkpoint("v1", FIDELITIES[2]))
          and refuses(lambda: Checkpoint("v1", "perfect", workspace_ref="w"))
          and Checkpoint("v1", FIDELITIES[0]).restores_state is False
          and refuses(lambda: hibernate(failed_ledger, "v1", Controller(), lambda record: {"a": 1}, now=3.0))
          and refuses(lambda: hibernate(failed_ledger, "v1", object(), writer_for("v1"), now=3.0)))
    checkpoint = writer(ledger.get("i1"))
    crowded = resume(ledger, "i1", checkpoint, reservations, machine(320), now=1010.0, memory_bytes=300)
    check("a_resume_takes_capacity_again_and_a_refusal_names_the_number",
          crowded.resumed is False and "headroom" in crowded.reason
          and ledger.get("i1").state == STATES[2]
          and crowded.unresolved_effects == ("provider-call:77",))
    resumed = resume(ledger, "i1", checkpoint, reservations, machine(900), now=1011.0, memory_bytes=300)
    check("a_resume_that_fits_restores_the_state_and_names_the_unresolved_effects",
          resumed.resumed and ledger.get("i1").state == STATES[0]
          and resumed.restores_state and "unresolved" in resumed.reason
          and resumed.reservation_id and resumed.checkpoint_digest == checkpoint.digest
          and any(event["kind"] == EVENT_KINDS[16] for event in ledger.events)
          and refuses(lambda: resume(ledger, "i1", checkpoint, reservations, machine(900),
                                     now=1012.0, memory_bytes=300)))
    policy = ResourcePolicy(max_instances=4, stall_after_seconds=60)
    quiet = InstanceLedger()
    quiet.register("w1", INSTANCE_KINDS[0], "loop-d", now=0.0, handle=9)
    waiting = ProgressSignal(PROGRESS_KINDS[1], 100.0, waiting_reason=WAITING_REASONS[0],
                             waiting_deadline_at=500.0)
    check("an_instance_waiting_on_a_declared_model_call_is_not_stalled_however_quiet_it_is",
          assess_progress(quiet, "w1", policy, now=400.0, signal=waiting).stalled is False
          and assess_progress(quiet, "w1", policy, now=400.0, signal=waiting).heartbeat_age_seconds == 400.0
          and assess_progress(quiet, "w1", policy, now=600.0, signal=waiting).stalled is True
          and "passed its deadline" in assess_progress(quiet, "w1", policy, now=600.0,
                                                       signal=waiting).reason)
    quiet.heartbeat("w1", now=600.0)
    beating = ProgressSignal(PROGRESS_KINDS[2], 600.0, detail="same candidate for ten rounds")
    check("a_heartbeat_without_progress_still_stalls_and_a_recent_advance_does_not",
          assess_progress(quiet, "w1", policy, now=700.0, signal=beating).stalled is True
          and assess_progress(quiet, "w1", policy, now=630.0, signal=beating).stalled is False
          and assess_progress(quiet, "w1", policy, now=700.0,
                              signal=ProgressSignal(PROGRESS_KINDS[0], 700.0)).stalled is True
          and assess_progress(quiet, "w1", policy, now=620.0,
                              signal=ProgressSignal(PROGRESS_KINDS[0], 620.0)).stalled is False
          and assess_progress(quiet, "w1", policy, now=700.0).stalled is True
          and refuses(lambda: ProgressSignal(PROGRESS_KINDS[1], 1.0))
          and refuses(lambda: ProgressSignal(PROGRESS_KINDS[0], 1.0, waiting_reason="model_call"))
          and refuses(lambda: ProgressSignal("fine", 1.0)))
    signals = []
    tree = ProcessTreeController((4242,), signaller=lambda group, number: signals.append((group, number)),
                                 alive=lambda group: False)
    check("a_process_tree_controller_signals_only_an_owned_group_and_confirms_it_is_gone",
          tree.confirm_stopped(4242) is True and refuses(lambda: tree.stop(99))
          and refuses(lambda: tree.confirm_stopped(99))
          and [tree.quiesce(4242), tree.stop(4242)] is not None and len(signals) == 2
          and ProcessTreeController((1,), signaller=lambda g, n: None,
                                    alive=lambda g: True).confirm_stopped(1) is False)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "instance_hibernation_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}


def writer_for(instance_id: str):
    """A checkpoint writer for one instance; used by the checks and by callers with no state."""
    def write(record):
        return Checkpoint(instance_id, FIDELITIES[2], session_ref=f"session:{instance_id}",
                          workspace_ref=f"workspace:{instance_id}")
    return write
