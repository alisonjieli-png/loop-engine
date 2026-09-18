"""Local resource detection and a supervisor for the harness instances a machine carries.

Every node of the solutioning space can be its own harness instance, and on
one machine those are processes competing for the same memory and
processors. This module owns the measured snapshot of what the machine has
(memory, pressure stall information, control group limits, load, processors,
each marked unknown when it cannot be read), the ledger of live instances
with their heartbeats and sampled memory, the append-only event log that
records every transition with its reason, admission of a new instance
against a ceiling derived from the machine rather than typed into a file,
stall detection by heartbeat age, pausing the largest instance under memory
pressure and resuming it when memory recovers, and stopping a stalled
instance. Every operating-system effect goes through an injected controller
that acts only on an owned handle; an instance without a handle is recorded
and never signaled. The supervisor grants no authority and starts nothing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

STATES = ("running", "paused", "hibernated", "stopped", "stalled")
LIVE_STATES = STATES[:2]
INSTANCE_KINDS = ("harness_process", "in_process", "container")
EVENT_KINDS = ("registered", "heartbeat", "admitted", "refused", "paused", "resumed", "hibernated",
               "stalled", "stopped", "skipped_no_handle")
PRESSURE_FILES = (("memory", "memory"), ("cpu", "cpu"), ("io", "io"))
SNAPSHOT_RECORD_TYPE = "resource_snapshot/v1"
LEDGER_RECORD_TYPE = "instance_ledger/v1"
REPORT_RECORD_TYPE = "supervision_report/v1"


class LocalResourceError(ValueError):
    """A policy, instance, or controller request is invalid."""


@dataclass(frozen=True)
class ResourceSnapshot:
    """What the machine reports at one moment; a field that could not be read is None."""

    taken_at: float
    cpu_count: "int | None"
    load_average_1m: "float | None"
    memory_total_bytes: "int | None"
    memory_available_bytes: "int | None"
    memory_basis: str
    pressure_memory_some_avg10: "float | None"
    pressure_cpu_some_avg10: "float | None"
    cgroup_memory_max_bytes: "int | None"
    cgroup_memory_current_bytes: "int | None"

    @property
    def memory_available_fraction(self) -> "float | None":
        if not self.memory_total_bytes or self.memory_available_bytes is None:
            return None
        return round(self.memory_available_bytes / self.memory_total_bytes, 4)

    def to_dict(self) -> dict:
        return {"record_type": SNAPSHOT_RECORD_TYPE, "taken_at": self.taken_at, "cpu_count": self.cpu_count,
                "load_average_1m": self.load_average_1m, "memory_total_bytes": self.memory_total_bytes,
                "memory_available_bytes": self.memory_available_bytes, "memory_basis": self.memory_basis,
                "memory_available_fraction": self.memory_available_fraction,
                "pressure_memory_some_avg10": self.pressure_memory_some_avg10,
                "pressure_cpu_some_avg10": self.pressure_cpu_some_avg10,
                "cgroup_memory_max_bytes": self.cgroup_memory_max_bytes,
                "cgroup_memory_current_bytes": self.cgroup_memory_current_bytes}


def _read_text(path: str) -> "str | None":
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, ValueError):
        return None


def _meminfo(proc: str) -> tuple["int | None", "int | None", str]:
    text = _read_text(os.path.join(proc, "meminfo"))
    if text is None:
        return None, None, "unmeasured"
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                values[parts[0][:-1]] = int(parts[1]) * 1024
            except ValueError:
                continue
    total, available = values.get("MemTotal"), values.get("MemAvailable")
    return total, available, "/proc/meminfo MemTotal and MemAvailable" if available is not None else "unmeasured"


def _pressure_some_avg10(proc: str, resource: str) -> "float | None":
    text = _read_text(os.path.join(proc, "pressure", resource))
    if text is None:
        return None
    for line in text.splitlines():
        if line.startswith("some "):
            for item in line.split()[1:]:
                key, _, value = item.partition("=")
                if key == "avg10":
                    try:
                        return float(value)
                    except ValueError:
                        return None
    return None


def _cgroup_int(cgroup: str, name: str) -> "int | None":
    text = _read_text(os.path.join(cgroup, name))
    if text is None:
        return None
    value = text.strip()
    if value == "max":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def detect_resources(*, proc: str = "/proc", cgroup: str = "/sys/fs/cgroup",
                     now: "float | None" = None) -> ResourceSnapshot:
    """Read what the machine reports; nothing is guessed and nothing is zero for unknown."""
    import time
    total, available, basis = _meminfo(proc)
    try:
        load = os.getloadavg()[0]
    except (OSError, AttributeError):
        load = None
    return ResourceSnapshot(
        taken_at=time.time() if now is None else now, cpu_count=os.cpu_count(),
        load_average_1m=load, memory_total_bytes=total, memory_available_bytes=available,
        memory_basis=basis, pressure_memory_some_avg10=_pressure_some_avg10(proc, PRESSURE_FILES[0][1]),
        pressure_cpu_some_avg10=_pressure_some_avg10(proc, PRESSURE_FILES[1][1]),
        cgroup_memory_max_bytes=_cgroup_int(cgroup, "memory.max"),
        cgroup_memory_current_bytes=_cgroup_int(cgroup, "memory.current"))


@dataclass(frozen=True)
class ResourcePolicy:
    """The declared policy a supervisor applies; the ceiling is derived from the machine unless set."""

    max_instances: "int | None" = None
    memory_reserve_fraction: float = 0.2
    resume_reserve_fraction: float = 0.3
    stall_after_seconds: float = 300.0
    pressure_pause_avg10: float = 20.0
    version: str = "1.0.0"

    def __post_init__(self):
        if self.max_instances is not None and (type(self.max_instances) is not int or self.max_instances < 1):
            raise LocalResourceError("max_instances must be empty or a positive integer")
        for name in ("memory_reserve_fraction", "resume_reserve_fraction"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not 0 <= value < 1:
                raise LocalResourceError(f"{name} must be a fraction below 1")
        if self.resume_reserve_fraction < self.memory_reserve_fraction:
            raise LocalResourceError("resume_reserve_fraction must not be below memory_reserve_fraction")
        if type(self.stall_after_seconds) not in (int, float) or self.stall_after_seconds <= 0:
            raise LocalResourceError("stall_after_seconds must be positive")
        if type(self.pressure_pause_avg10) not in (int, float) or not 0 <= self.pressure_pause_avg10 <= 100:
            raise LocalResourceError("pressure_pause_avg10 is a percentage from 0 to 100")

    def ceiling(self, snapshot: ResourceSnapshot) -> "int | None":
        """The instance ceiling: declared, or derived from the processors the machine reports."""
        if self.max_instances is not None:
            return self.max_instances
        return snapshot.cpu_count if snapshot.cpu_count else None


@dataclass
class InstanceRecord:
    instance_id: str
    kind: str
    owner_loop_id: str
    started_at: float
    last_heartbeat_at: float
    memory_bytes: "int | None" = None
    state: str = STATES[0]
    handle: object = None

    def to_dict(self) -> dict:
        return {"instance_id": self.instance_id, "kind": self.kind, "owner_loop_id": self.owner_loop_id,
                "started_at": self.started_at, "last_heartbeat_at": self.last_heartbeat_at,
                "memory_bytes": self.memory_bytes, "state": self.state, "has_handle": self.handle is not None}


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    reason: str
    live_count: int
    ceiling: "int | None"
    memory_available_fraction: "float | None"

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason, "live_count": self.live_count,
                "ceiling": self.ceiling, "memory_available_fraction": self.memory_available_fraction}


class InstanceLedger:
    """The live instances, their heartbeats, and an append-only log of every transition."""

    def __init__(self):
        self._instances: dict = {}
        self.events: list = []

    def _log(self, kind: str, instance_id: str, at: float, reason: str = "", **extra) -> None:
        if kind not in EVENT_KINDS:
            raise LocalResourceError(f"event kind must be one of {EVENT_KINDS}")
        self.events.append({"kind": kind, "instance_id": instance_id, "at": at, "reason": reason, **extra})

    def register(self, instance_id: str, kind: str, owner_loop_id: str, *, now: float,
                 handle: object = None, memory_bytes: "int | None" = None) -> InstanceRecord:
        if kind not in INSTANCE_KINDS:
            raise LocalResourceError(f"instance kind must be one of {INSTANCE_KINDS}")
        if not instance_id or instance_id in self._instances:
            raise LocalResourceError(f"instance identity {instance_id!r} is empty or already registered")
        record = InstanceRecord(instance_id, kind, owner_loop_id, now, now, memory_bytes, STATES[0], handle)
        self._instances[instance_id] = record
        self._log(EVENT_KINDS[0], instance_id, now, instance_kind=kind, has_handle=handle is not None)
        return record

    def heartbeat(self, instance_id: str, *, now: float, memory_bytes: "int | None" = None) -> None:
        record = self.get(instance_id)
        record.last_heartbeat_at = now
        if memory_bytes is not None:
            record.memory_bytes = memory_bytes
        self._log(EVENT_KINDS[1], instance_id, now, memory_bytes=memory_bytes)

    def get(self, instance_id: str) -> InstanceRecord:
        try:
            return self._instances[instance_id]
        except KeyError:
            raise LocalResourceError(f"no instance {instance_id!r}") from None

    def live(self) -> tuple[InstanceRecord, ...]:
        return tuple(item for item in self._instances.values() if item.state in LIVE_STATES)

    def of_state(self, state: str) -> tuple[InstanceRecord, ...]:
        if state not in STATES:
            raise LocalResourceError(f"state must be one of {STATES}")
        return tuple(item for item in self._instances.values() if item.state == state)

    def transition(self, instance_id: str, state: str, *, now: float, reason: str) -> InstanceRecord:
        record = self.get(instance_id)
        if state not in STATES:
            raise LocalResourceError(f"state must be one of {STATES}")
        record.state = state
        self._log({STATES[1]: EVENT_KINDS[4], STATES[0]: EVENT_KINDS[5], STATES[2]: EVENT_KINDS[6],
                   STATES[4]: EVENT_KINDS[7], STATES[3]: EVENT_KINDS[8]}[state], instance_id, now, reason)
        return record

    def to_dict(self) -> dict:
        return {"record_type": LEDGER_RECORD_TYPE,
                "instances": [item.to_dict() for item in self._instances.values()],
                "events": list(self.events)}


def admit(ledger: InstanceLedger, policy: ResourcePolicy, snapshot: ResourceSnapshot, *,
          instance_id: str, now: float) -> AdmissionDecision:
    """Whether one more instance may start now, with the number that decided it."""
    live = len(ledger.live())
    ceiling = policy.ceiling(snapshot)
    fraction = snapshot.memory_available_fraction
    if ceiling is not None and live >= ceiling:
        decision = AdmissionDecision(False, f"{live} live instances reach the ceiling {ceiling}", live, ceiling, fraction)
    elif fraction is not None and fraction < policy.memory_reserve_fraction:
        decision = AdmissionDecision(False, f"available memory {fraction} is below the reserve "
                                            f"{policy.memory_reserve_fraction}", live, ceiling, fraction)
    elif ceiling is None and fraction is None:
        decision = AdmissionDecision(False, "neither a ceiling nor the available memory could be measured",
                                     live, ceiling, fraction)
    else:
        decision = AdmissionDecision(True, "within the ceiling and above the memory reserve", live, ceiling, fraction)
    ledger._log(EVENT_KINDS[2] if decision.allowed else EVENT_KINDS[3], instance_id, now, decision.reason)
    return decision


def stalled(ledger: InstanceLedger, policy: ResourcePolicy, *, now: float) -> tuple[InstanceRecord, ...]:
    """Running instances whose last heartbeat is older than the policy allows."""
    return tuple(item for item in ledger.of_state(STATES[0])
                 if now - item.last_heartbeat_at > policy.stall_after_seconds)


def _memory_pressure(policy: ResourcePolicy, snapshot: ResourceSnapshot) -> "str | None":
    fraction = snapshot.memory_available_fraction
    if fraction is not None and fraction < policy.memory_reserve_fraction:
        return f"available memory {fraction} is below the reserve {policy.memory_reserve_fraction}"
    pressure = snapshot.pressure_memory_some_avg10
    if pressure is not None and pressure > policy.pressure_pause_avg10:
        return f"memory pressure {pressure} is above {policy.pressure_pause_avg10}"
    return None


def _act(controller, action: str, record: InstanceRecord, ledger: InstanceLedger, now: float,
         reason: str, state: str, report: dict) -> None:
    if record.handle is None:
        ledger._log(EVENT_KINDS[9], record.instance_id, now, reason, action=action)
        report["skipped_no_handle"].append(record.instance_id)
        return
    getattr(controller, action)(record.handle)
    ledger.transition(record.instance_id, state, now=now, reason=reason)
    report[action].append(record.instance_id)


def supervise(ledger: InstanceLedger, policy: ResourcePolicy, snapshot: ResourceSnapshot, controller, *,
              now: float) -> dict:
    """One supervision pass: stop stalled instances, pause under pressure, resume on recovery."""
    for name in ("pause", "resume", "stop"):
        if not callable(getattr(controller, name, None)):
            raise LocalResourceError(f"the controller must offer {name}(handle)")
    report = {"record_type": REPORT_RECORD_TYPE, "at": now, "stop": [], "pause": [], "resume": [],
              "skipped_no_handle": [], "pressure": None, "snapshot": snapshot.to_dict()}
    for record in stalled(ledger, policy, now=now):
        age = round(now - record.last_heartbeat_at, 3)
        _act(controller, "stop", record, ledger, now,
             f"no heartbeat for {age} seconds, above {policy.stall_after_seconds}", STATES[4], report)
    pressure = _memory_pressure(policy, snapshot)
    report["pressure"] = pressure
    if pressure is not None:
        running = [item for item in ledger.of_state(STATES[0]) if item.handle is not None]
        running.sort(key=lambda item: (-(item.memory_bytes or 0), item.started_at))
        if running:
            _act(controller, "pause", running[0], ledger, now, pressure, STATES[1], report)
    else:
        fraction = snapshot.memory_available_fraction
        if fraction is not None and fraction >= policy.resume_reserve_fraction:
            for record in sorted(ledger.of_state(STATES[1]), key=lambda item: item.started_at):
                _act(controller, "resume", record, ledger, now,
                     f"available memory {fraction} recovered above {policy.resume_reserve_fraction}",
                     STATES[0], report)
    report["live_count"] = len(ledger.live())
    return report


class SignalController:
    """Pause, resume, and stop an owned process by identity with the standard signals."""

    def __init__(self, owned_pids):
        self._owned = set(int(pid) for pid in owned_pids)

    def _check(self, pid) -> int:
        if int(pid) not in self._owned:
            raise LocalResourceError(f"process {pid} is not an owned handle")
        return int(pid)

    def pause(self, pid) -> None:
        import signal
        os.kill(self._check(pid), signal.SIGSTOP)

    def resume(self, pid) -> None:
        import signal
        os.kill(self._check(pid), signal.SIGCONT)

    def stop(self, pid) -> None:
        import signal
        os.kill(self._check(pid), signal.SIGTERM)


def self_test() -> dict:
    """Detection from fixture files, admission, stalls, pressure, recovery, and owned handles."""
    import tempfile
    from pathlib import Path
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except LocalResourceError:
            return True
        except Exception:  # noqa: BLE001  (a crash is not a typed refusal)
            return False
        return False

    with tempfile.TemporaryDirectory(prefix="loop-resources-") as folder:
        proc = Path(folder) / "proc"
        (proc / "pressure").mkdir(parents=True)
        (proc / "meminfo").write_text("MemTotal:       16000000 kB\nMemFree:  1000000 kB\n"
                                      "MemAvailable:    4000000 kB\n", "utf-8")
        (proc / "pressure" / "memory").write_text("some avg10=3.50 avg60=1.00 avg300=0.50 total=100\n"
                                                  "full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n", "utf-8")
        cgroup = Path(folder) / "cgroup"
        cgroup.mkdir()
        (cgroup / "memory.max").write_text("max\n", "utf-8")
        (cgroup / "memory.current").write_text("123456\n", "utf-8")
        snapshot = detect_resources(proc=str(proc), cgroup=str(cgroup), now=1000.0)
        empty = detect_resources(proc=str(Path(folder) / "absent"), cgroup=str(Path(folder) / "absent"), now=1.0)
    check("detection_reads_memory_pressure_and_control_groups_and_marks_the_unreadable_unknown",
          snapshot.memory_total_bytes == 16000000 * 1024 and snapshot.memory_available_bytes == 4000000 * 1024
          and snapshot.memory_available_fraction == 0.25 and snapshot.pressure_memory_some_avg10 == 3.5
          and snapshot.pressure_cpu_some_avg10 is None and snapshot.cgroup_memory_max_bytes is None
          and snapshot.cgroup_memory_current_bytes == 123456 and snapshot.cpu_count == os.cpu_count()
          and empty.memory_total_bytes is None and empty.memory_available_fraction is None
          and empty.memory_basis == "unmeasured" and snapshot.to_dict()["record_type"] == SNAPSHOT_RECORD_TYPE)
    policy = ResourcePolicy(max_instances=2, stall_after_seconds=60)
    ledger = InstanceLedger()
    first = admit(ledger, policy, snapshot, instance_id="i1", now=1000.0)
    ledger.register("i1", INSTANCE_KINDS[0], "loop-a", now=1000.0, handle=101, memory_bytes=500)
    ledger.register("i2", INSTANCE_KINDS[0], "loop-b", now=1001.0, handle=102, memory_bytes=900)
    third = admit(ledger, policy, snapshot, instance_id="i3", now=1002.0)
    derived = ResourcePolicy()
    check("admission_refuses_above_the_ceiling_and_the_ceiling_derives_from_the_machine_unless_declared",
          first.allowed and third.allowed is False and "ceiling 2" in third.reason and third.live_count == 2
          and derived.ceiling(snapshot) == os.cpu_count()
          and derived.ceiling(ResourceSnapshot(1.0, None, None, None, None, "unmeasured", None, None, None, None)) is None
          and ledger.events[-1]["kind"] == EVENT_KINDS[3])
    low = ResourceSnapshot(1003.0, 4, 1.0, 100, 10, "fixture", None, None, None, None)
    refused_low = admit(ledger, ResourcePolicy(max_instances=9), low, instance_id="i4", now=1003.0)
    blind = ResourceSnapshot(1003.0, None, None, None, None, "unmeasured", None, None, None, None)
    unknown = admit(ledger, ResourcePolicy(), blind, instance_id="i5", now=1003.0)
    check("admission_refuses_under_the_memory_reserve_and_when_nothing_could_be_measured",
          refused_low.allowed is False and "below the reserve" in refused_low.reason
          and unknown.allowed is False and "could be measured" in unknown.reason)

    class Controller:
        def __init__(self):
            self.calls = []

        def pause(self, handle):
            self.calls.append(("pause", handle))

        def resume(self, handle):
            self.calls.append(("resume", handle))

        def stop(self, handle):
            self.calls.append(("stop", handle))

    controller = Controller()
    ledger.heartbeat("i1", now=1050.0, memory_bytes=700)
    stale_report = supervise(ledger, policy, snapshot, controller, now=1100.0)
    check("a_running_instance_without_a_recent_heartbeat_is_stopped_through_its_handle_and_logged",
          stale_report["stop"] == ["i2"] and ("stop", 102) in controller.calls
          and ledger.get("i2").state == STATES[4] and ledger.get("i1").state == STATES[0]
          and any(event["kind"] == EVENT_KINDS[7] and "no heartbeat" in event["reason"]
                  for event in ledger.events))
    ledger.register("i3", INSTANCE_KINDS[1], "loop-c", now=1100.0, handle=103, memory_bytes=2000)
    ledger.register("i4", INSTANCE_KINDS[0], "loop-d", now=1100.0, handle=None, memory_bytes=9000)
    pressed = supervise(ledger, policy, low, controller, now=1101.0)
    check("under_memory_pressure_the_largest_handled_instance_is_paused_and_a_handleless_one_is_never_signaled",
          pressed["pause"] == ["i3"] and ("pause", 103) in controller.calls
          and ledger.get("i3").state == STATES[1] and ledger.get("i4").state == STATES[0]
          and not any(call[1] is None for call in controller.calls)
          and pressed["pressure"] is not None)
    stale_no_handle = supervise(ledger, ResourcePolicy(max_instances=9, stall_after_seconds=0.5), low,
                                controller, now=2000.0)
    check("a_stalled_instance_without_a_handle_is_recorded_as_skipped_never_signaled",
          "i4" in stale_no_handle["skipped_no_handle"] and ledger.get("i4").state == STATES[0]
          and any(event["kind"] == EVENT_KINDS[9] and event["instance_id"] == "i4" for event in ledger.events))
    recovered = ResourceSnapshot(2001.0, 4, 1.0, 100, 50, "fixture", 1.0, None, None, None)
    resumed = supervise(ledger, policy, recovered, controller, now=2001.0)
    check("a_paused_instance_resumes_when_memory_recovers_above_the_resume_reserve",
          resumed["resume"] == ["i3"] and ("resume", 103) in controller.calls
          and ledger.get("i3").state == STATES[0] and resumed["pressure"] is None
          and resumed["live_count"] == len(ledger.live()))
    ledger.heartbeat("i3", now=2001.5, memory_bytes=2100)
    pressure_only = ResourceSnapshot(2002.0, 4, 1.0, 100, 50, "fixture", 45.0, None, None, None)
    high = supervise(ledger, policy, pressure_only, controller, now=2002.0)
    check("pressure_stall_information_alone_pauses_the_largest_running_instance",
          high["pause"] == ["i3"] and "memory pressure 45.0" in high["pressure"])
    kinds = [event["kind"] for event in ledger.events]
    check("the_event_log_is_append_only_typed_and_carries_reasons",
          all(kind in EVENT_KINDS for kind in kinds) and len(ledger.events) >= 12
          and all("reason" in event and "at" in event for event in ledger.events)
          and ledger.to_dict()["record_type"] == LEDGER_RECORD_TYPE
          and refuses(lambda: ledger._log("exploded", "i1", 1.0)))
    check("policies_instances_and_controllers_are_validated",
          all(refuses(action) for action in (
              lambda: ResourcePolicy(max_instances=0),
              lambda: ResourcePolicy(memory_reserve_fraction=1.0),
              lambda: ResourcePolicy(memory_reserve_fraction=0.5, resume_reserve_fraction=0.4),
              lambda: ResourcePolicy(stall_after_seconds=0),
              lambda: ResourcePolicy(pressure_pause_avg10=101),
              lambda: ledger.register("i1", INSTANCE_KINDS[0], "x", now=1.0),
              lambda: ledger.register("i9", "thread", "x", now=1.0),
              lambda: ledger.transition("i1", "flying", now=1.0, reason="x"),
              lambda: ledger.of_state("flying"),
              lambda: supervise(ledger, policy, snapshot, object(), now=1.0),
              lambda: SignalController((1,)).pause(2))))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "local_resources_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
