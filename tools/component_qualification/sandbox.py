"""Run a component's entry-point imports and its own tests in a bounded sandbox with no network.

One sandbox run per component. The package's exact files are written into a fresh work folder, and a
small driver (this module's code, not the component's) runs inside the sandbox: it imports each declared
Python module in its own child process, then runs the package's unittest modules in another child
process, and reports both as JSON after a marker it received on standard input. The tested code runs
only in child processes, so it cannot change the driver's report, and it never sees the marker.

```text
Sandbox run (engine bwrap_rlimits, or systemd_scope_bwrap which adds cgroup task and memory ceilings)
├── bubblewrap: read-only system, private /tmp of bounded size, /home /root /run /mnt /media /srv hidden,
│   new network, process, IPC and UTS namespaces (no network at all: loopback only), new session,
│   cleared environment, the work folder (mounted at /home/work) the only writable path
├── resource limits on every process: CPU seconds, address space, file size, open files, no core files
├── wall-clock timeout for the whole run; the process group is killed on expiry
└── the system interpreter in isolated-environment mode (-E -s -B): no user site, no PYTHON* variables
```

The engines are the existing library ingestion sandbox (`sandbox_argv`, bubblewrap with no network)
extended with the hidden paths and limits this stage needs. Nothing here approves a component: a passing
run is one observation, recorded with the interpreter, limits and engine that produced it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import secrets
import shutil
import signal
import subprocess
import time

SANDBOX_RECORD = "component_sandbox_run/v1"
ENGINES = ("bwrap_rlimits", "systemd_scope_bwrap")
SYSTEM_PATH = "/usr/bin:/bin"
#: Host paths the sandbox never shows: home folders (credentials, keyrings, other checkouts), runtime
#: sockets (session bus, keyring, container daemon) and removable or mounted volumes.
HIDDEN_PATHS = ("/home", "/root", "/run", "/mnt", "/media", "/srv")
TAIL_CHARACTERS = 1200
#: Where the package folder appears inside the sandbox: inside the empty /home, so its host path and every
#: host home folder stay hidden.
SANDBOX_WORK = "/home/work"
#: What the cgroup engine's launcher needs to reach the user service manager; the sandbox clears it again.
LAUNCHER_ENVIRONMENT = ("DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR")

DRIVER = r'''
import json, subprocess, sys, time
spec = json.loads(sys.stdin.readline())
python = sys.executable
isolated = [python, "-E", "-s", "-B"]
def run(argv, timeout):
    started = time.monotonic()
    try:
        done = subprocess.run(argv, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
        return {"exit": done.returncode, "timed_out": False, "seconds": round(time.monotonic() - started, 3),
                "stdout": done.stdout[-6000:].decode("utf-8", "replace"),
                "stderr": done.stderr[-12000:].decode("utf-8", "replace")}
    except subprocess.TimeoutExpired:
        return {"exit": None, "timed_out": True, "seconds": round(time.monotonic() - started, 3),
                "stdout": "", "stderr": ""}
report = {"interpreter": sys.version.split()[0], "imports": [], "tests": None}
importer = "import importlib, sys; sys.path.insert(0, '.'); importlib.import_module(sys.argv[1])"
for module in spec["modules"]:
    report["imports"].append({"module": module, **run(isolated + ["-c", importer, module], spec["import_seconds"])})
if spec["tests"]:
    report["tests"] = run(isolated + ["-m", "unittest", "-v"] + spec["tests"], spec["test_seconds"])
sys.stdout.write("\n" + spec["marker"] + json.dumps(report) + "\n")
sys.stdout.flush()
'''

_RAN = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
_RESULT = re.compile(r"^(OK|FAILED)(?: \((.*)\))?\s*$")
_MODULE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class SandboxError(RuntimeError):
    """The sandbox could not be set up; the component is not qualified by a run that did not happen."""


@dataclass(frozen=True)
class SandboxLimits:
    wall_seconds: float = 90.0
    import_seconds: float = 20.0
    test_seconds: float = 60.0
    cpu_seconds: int = 60
    memory_bytes: int = 1024 * 1024 * 1024
    file_bytes: int = 64 * 1024 * 1024
    open_files: int = 256
    tmp_bytes: int = 64 * 1024 * 1024
    #: Enforced by the cgroup engine only.
    tasks: int = 64

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SandboxSettings:
    engine: str = "bwrap_rlimits"
    python: str = "/usr/bin/python3"
    bwrap: str = "bwrap"
    limits: SandboxLimits = SandboxLimits()

    def __post_init__(self):
        if self.engine not in ENGINES:
            raise SandboxError(f"the sandbox engine is one of {ENGINES}")
        if not os.path.isabs(self.python) or any(self.python.startswith(path + "/") for path in HIDDEN_PATHS):
            raise SandboxError("the sandbox interpreter is an absolute path outside the hidden folders")

    def available(self) -> tuple:
        missing = [name for name in (self.bwrap, self.python) if not shutil.which(name)]
        if self.engine == "systemd_scope_bwrap" and not shutil.which("systemd-run"):
            missing.append("systemd-run")
        return (not missing, f"missing {missing}" if missing else "")

    def works(self) -> bool:
        """Whether this machine can start the sandbox at all (user namespaces may be refused), by running a
        trivial command in it once."""
        if not self.available()[0]:
            return False
        argv = [self.bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--unshare-net",
                "--unshare-pid", "--die-with-parent", self.python, "-c", "print('sandbox works')"]
        try:
            done = subprocess.run(argv, capture_output=True, timeout=30, check=False, env={"PATH": SYSTEM_PATH})
        except (OSError, subprocess.TimeoutExpired):
            return False
        return done.returncode == 0 and b"sandbox works" in done.stdout


def python_modules(component) -> tuple:
    """(importable modules, test modules): root-level Python files, tests named test_*.py."""
    modules, tests = [], []
    for entry in component.package.files:
        path = PurePosixPath(entry.path)
        if path.suffix != ".py" or len(path.parts) != 1 or not _MODULE_NAME.fullmatch(path.stem):
            continue
        (tests if path.stem.startswith("test_") else modules).append(path.stem)
    return tuple(sorted(modules)), tuple(sorted(tests))


def _limits(limits: SandboxLimits):
    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds + 5))
        resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (limits.file_bytes, limits.file_bytes))
        resource.setrlimit(resource.RLIMIT_NOFILE, (limits.open_files, limits.open_files))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    return apply


def sandbox_argv(settings: SandboxSettings, work: Path) -> list:
    argv = [settings.bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    for path in HIDDEN_PATHS:
        if os.path.isdir(path) and not os.path.islink(path):
            argv += ["--tmpfs", path]
    argv += ["--size", str(settings.limits.tmp_bytes), "--tmpfs", "/tmp",
             "--unshare-net", "--unshare-ipc", "--unshare-pid", "--unshare-uts", "--die-with-parent",
             "--new-session", "--bind", str(work), SANDBOX_WORK, "--chdir", SANDBOX_WORK, "--clearenv",
             "--setenv", "HOME", SANDBOX_WORK, "--setenv", "PATH", SYSTEM_PATH, "--setenv", "LANG", "C.UTF-8",
             "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "TMPDIR", "/tmp",
             "--", settings.python, "-E", "-s", "-B", "-c", DRIVER]
    if settings.engine == "systemd_scope_bwrap":
        argv = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"TasksMax={settings.limits.tasks}",
                "-p", f"MemoryMax={settings.limits.memory_bytes}", "--"] + argv
    return argv


def write_package(component, work: Path) -> None:
    """Write the exact files under a fresh folder; every path stays inside it."""
    work.mkdir(parents=True, exist_ok=False)
    root = work.resolve()
    for path, payload in component.payloads.items():
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts:
            raise SandboxError("a package path escapes its folder")
        target = root.joinpath(*pure.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve().parent != target.parent.resolve() or not str(target.resolve()).startswith(str(root)):
            raise SandboxError("a package path escapes its folder")
        with open(target, "xb") as stream:
            stream.write(payload)


def parse_unittest(stderr: str) -> dict:
    """What unittest printed: tests ran, skipped, failures and errors, and whether it ended with OK."""
    ran = _RAN.findall(stderr)
    lines = [line for line in stderr.strip().splitlines() if line.strip()]
    result = _RESULT.match(lines[-1]) if lines else None
    counts = {"failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}
    if result and result.group(2):
        for part in result.group(2).split(","):
            name, _, value = part.strip().partition("=")
            key = name.strip().replace(" ", "_")
            if key in counts and value.strip().isdigit():
                counts[key] = int(value)
    return {"ran": int(ran[-1]) if ran else 0, "ok": bool(result) and result.group(1) == "OK", **counts}


def run_component(component, settings: SandboxSettings, work_root: Path) -> dict:
    """One sandbox run: import every declared module, run every test module, record what happened."""
    modules, tests = python_modules(component)
    record = {"record_type": SANDBOX_RECORD, "engine": settings.engine, "limits": settings.limits.to_dict(),
              "modules": list(modules), "test_modules": list(tests), "ran": False}
    if not modules and not tests:
        return record | {"reason": "no_python_entry_points_or_tests"}
    work = Path(work_root) / f"{component.package.package_digest[:24]}-{secrets.token_hex(4)}"
    marker = "SANDBOX-REPORT-" + secrets.token_hex(16) + ":"
    spec = json.dumps({"modules": list(modules), "tests": list(tests), "marker": marker,
                       "import_seconds": settings.limits.import_seconds,
                       "test_seconds": settings.limits.test_seconds}) + "\n"
    started = time.monotonic()
    try:
        write_package(component, work)
        launcher = {"PATH": SYSTEM_PATH}
        if settings.engine == "systemd_scope_bwrap":
            launcher.update({name: os.environ[name] for name in LAUNCHER_ENVIRONMENT if name in os.environ})
        process = subprocess.Popen(sandbox_argv(settings, work), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=launcher, start_new_session=True,
                                   preexec_fn=_limits(settings.limits))
        try:
            stdout, stderr = process.communicate(spec.encode(), timeout=settings.limits.wall_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            timed_out = True
    finally:
        shutil.rmtree(work, ignore_errors=True)
    elapsed = round(time.monotonic() - started, 3)
    text = stdout.decode("utf-8", "replace")
    report = None
    for line in reversed(text.splitlines()):
        if line.startswith(marker):
            try:
                report = json.loads(line[len(marker):])
            except ValueError:
                report = None
            break
    record.update({"ran": report is not None, "wall_seconds": elapsed, "timed_out": timed_out,
                   "exit": process.returncode})
    if report is None:
        return record | {"reason": "timed_out" if timed_out else "no_driver_report",
                         "stderr_tail": stderr.decode("utf-8", "replace")[-TAIL_CHARACTERS:]}
    record["interpreter"] = report["interpreter"]
    record["imports"] = [{"module": row["module"], "ok": row["exit"] == 0 and not row["timed_out"],
                          "timed_out": row["timed_out"], "seconds": row["seconds"],
                          "tail": "" if row["exit"] == 0 else row["stderr"][-TAIL_CHARACTERS:]}
                         for row in report["imports"]]
    tests_row = report["tests"]
    if tests_row is None:
        record["tests"] = None
    else:
        parsed = parse_unittest(tests_row["stderr"])
        passed = tests_row["exit"] == 0 and not tests_row["timed_out"] and parsed["ok"]
        record["tests"] = {**parsed, "passed": passed, "timed_out": tests_row["timed_out"],
                           "exit": tests_row["exit"], "seconds": tests_row["seconds"],
                           "tail": "" if passed else tests_row["stderr"][-TAIL_CHARACTERS:]}
    return record
