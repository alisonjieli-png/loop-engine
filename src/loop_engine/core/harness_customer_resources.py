"""Attempt-owned aggregate resource bounds for a native customer process.

Reuses the systemd plus Bubblewrap approach of component qualification. A
fresh transient service owns only this process tree. No slice, timer, provider
resource or other worker is edited. Missing cgroup enforcement is a refusal.
"""
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shutil
import subprocess
from threading import Lock
import time
import uuid

from .harness_process import HarnessProcessError


@dataclass(frozen=True)
class CustomerResourceLimits:
    memory_bytes: int = 2 * 1024 * 1024 * 1024
    tasks: int = 64
    cpu_percent: int = 200
    workspace_bytes: int = 256 * 1024 * 1024
    temporary_bytes: int = 64 * 1024 * 1024

    def __post_init__(self):
        if (type(self.memory_bytes) is not int or self.memory_bytes < 64 * 1024 * 1024
                or type(self.tasks) is not int or self.tasks < 4
                or type(self.cpu_percent) is not int or self.cpu_percent < 1
                or any(type(value) is not int or value < 1024 * 1024 for value in (self.workspace_bytes, self.temporary_bytes))):
            raise HarnessProcessError("customer_resource_limits_invalid")


def _duration_seconds(value):
    units = {"us": .000001, "ms": .001, "s": 1, "min": 60, "h": 3600, "d": 86400}
    parts = re.findall(r"([0-9]+(?:\.[0-9]+)?)(us|ms|min|s|h|d)", value)
    if not parts or "".join(number + unit for number, unit in parts) != value.replace(" ", ""):
        raise HarnessProcessError("customer_runtime_limit_unreadable")
    return sum(float(number) * units[unit] for number, unit in parts)


@dataclass
class CustomerResourceScope:
    limits: CustomerResourceLimits = CustomerResourceLimits()
    unit: str = field(default_factory=lambda: "baltor-native-customer-" + uuid.uuid4().hex + ".service", init=False)
    timeout_seconds: float = field(default=0, init=False)
    verified: dict = field(default_factory=dict, init=False)
    cleanup_confirmed: bool = field(default=False, init=False)
    dispatched: bool = field(default=False, init=False)
    control_group: str = field(default="", init=False)
    lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def environment(self):
        runtime = Path("/run/user") / str(os.getuid())
        if not (runtime / "bus").is_socket() or any(shutil.which(name) != "/usr/bin/" + name for name in ("systemd-run", "systemctl")):
            raise HarnessProcessError("customer_cgroup_unavailable")
        return {"PATH": "/usr/bin:/bin", "XDG_RUNTIME_DIR": str(runtime),
                "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + str(runtime / "bus")}

    def command(self, command, timeout_seconds):
        self.environment()
        self.timeout_seconds = timeout_seconds
        return ["/usr/bin/systemd-run", "--user", "--wait", "--pipe", "--quiet", "--collect", "--service-type=exec",
                "--unit=" + self.unit, "--property=MemoryMax=" + str(self.limits.memory_bytes),
                "--property=MemorySwapMax=0",
                "--property=TasksMax=" + str(self.limits.tasks), "--property=CPUQuota=" + str(self.limits.cpu_percent) + "%",
                "--property=RuntimeMaxSec=" + str(timeout_seconds), "--property=KillMode=control-group", "--",
                # The user manager supplies its own ambient environment. Scrub
                # at execve *before* Bubblewrap becomes namespace PID 1: its
                # --clearenv switch alone clears only the final process, leaving
                # the supervisor's initial environ visible through /proc.
                "/usr/bin/env", "-i", "PATH=/usr/bin:/bin", *command]

    def inspect(self):
        result = subprocess.run(["/usr/bin/systemctl", "--user", "show", self.unit,
            "--property=ControlGroup,MemoryMax,TasksMax,CPUQuotaPerSecUSec,RuntimeMaxUSec,KillMode,ActiveState"],
            env=self.environment(), capture_output=True, text=True, timeout=3)
        if result.returncode:
            raise HarnessProcessError("customer_cgroup_unavailable")
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        location = values.get("ControlGroup", "")
        if (not location.startswith("/user.slice/") or not location.endswith("/" + self.unit) or ".." in location.split("/")
                or values.get("KillMode") != "control-group" or values.get("ActiveState") != "active"):
            raise HarnessProcessError("customer_cgroup_not_active")
        root = Path("/sys/fs/cgroup" + location)
        self.control_group = location
        memory = int((root / "memory.max").read_text().strip())
        swap = int((root / "memory.swap.max").read_text().strip())
        tasks = int((root / "pids.max").read_text().strip())
        quota, period = map(int, (root / "cpu.max").read_text().split())
        runtime = _duration_seconds(values["RuntimeMaxUSec"])
        if (memory != self.limits.memory_bytes or swap != 0 or tasks != self.limits.tasks
                or period <= 0 or quota <= 0 or quota / period > self.limits.cpu_percent / 100
                or runtime <= 0 or runtime > self.timeout_seconds + .00001):
            raise HarnessProcessError("customer_cgroup_limit_mismatch")
        self.verified = {"record_type": "customer_resource_scope/v1", "unit": self.unit, "memory_bytes": memory,
                         "maximum_swap_bytes": swap,
                         "maximum_tasks": tasks, "cpu_quota": quota, "cpu_period": period,
                         "maximum_seconds": runtime, "kill_mode": values["KillMode"]}
        return self.verified

    def wait_verified(self, process):
        deadline = time.monotonic() + 4
        while process.poll() is None and time.monotonic() < deadline:
            try:
                return self.inspect()
            except (OSError, ValueError, HarnessProcessError):
                time.sleep(.05)
        raise HarnessProcessError("customer_cgroup_verification_failed")

    def stop(self):
        with self.lock:
            if self.cleanup_confirmed:
                return
            if not self.dispatched:
                self.cleanup_confirmed = True
                return
            environment = self.environment()
            subprocess.run(["/usr/bin/systemctl", "--user", "kill", "--kill-whom=all", "--signal=KILL", self.unit],
                           env=environment, capture_output=True, timeout=3)
            subprocess.run(["/usr/bin/systemctl", "--user", "stop", self.unit], env=environment, capture_output=True, timeout=3)
            result = subprocess.run(["/usr/bin/systemctl", "--user", "show", self.unit, "--property=ActiveState", "--value"],
                                    env=environment, capture_output=True, text=True, timeout=3)
            kernel_empty = False
            if self.control_group:
                tasks = Path("/sys/fs/cgroup" + self.control_group) / "cgroup.procs"
                kernel_empty = not tasks.exists() or not tasks.read_text().strip()
            self.cleanup_confirmed = (result.returncode == 0 and result.stdout.strip() in ("inactive", "failed")) or kernel_empty
            if not self.cleanup_confirmed:
                raise HarnessProcessError("customer_cgroup_cleanup_unknown")
