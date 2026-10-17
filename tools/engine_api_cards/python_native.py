"""The native side of a Python library's cards: the pinned interpreter imports the pinned wheels inside bubblewrap,
reads the library's public surface once, and later checks every card in one more run (python_introspect.py).

```text
bwrap: the system read only, /home /root /run /mnt /media /srv hidden, a private /tmp, no network (a new network
│      namespace holds only loopback), a new process, IPC and UTS namespace, a cleared environment with a fixed hash
│      seed and one thread per numeric library, CPU, file size, open file and wall-clock limits
├── /home/work/env/<n>  each unpacked wheel, read only: the library's own first, then its pinned dependencies
├── /home/work/bin/python_introspect.py, read only
└── /home/work/out      the only writable folder: the spec in, the result out
    │
    └── python3.14 -I -S -B python_introspect.py read|verify spec.json result.json
          (isolated: no user site, no PYTHON* variables, no site packages, no script folder on the path)
```

One evidence record per card (engine_api_card_native_evidence/v1, as godot_native writes it): the interpreter's
version and binary digest, the wheel and the digest of the whole environment, the card digest it checked, each
check with its state, and no time stamp.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import godot_native
from .godot_native import EVIDENCE_RECORD, FAILED, PASSED, NativeError

SCRIPT = Path(__file__).resolve().parent / "python_introspect.py"
SPEC_RECORD, RESULTS_RECORD, CHECK_RECORD = ("python_api_introspection_spec/v1", "python_api_introspection/v1",
                                             "python_api_check_results/v1")
READ, VERIFY = MODES = ("read", "verify")
ENGINE_NAME = "cpython"
#: Where things appear inside the sandbox. /home is an empty file system there, so no host home folder shows.
SANDBOX_ROOT = "/home/work"
SANDBOX_ENV, SANDBOX_BIN, SANDBOX_OUT, SANDBOX_HOME = (f"{SANDBOX_ROOT}/env", f"{SANDBOX_ROOT}/bin",
                                                       f"{SANDBOX_ROOT}/out", f"{SANDBOX_ROOT}/home")
#: Host paths the sandbox never shows (the qualification sandbox's list), and the interpreter's flags.
HIDDEN_PATHS = ("/home", "/root", "/run", "/mnt", "/media", "/srv")
FLAGS = ("-I", "-S", "-B")
SYSTEM_PATH, LOCALE = "/usr/bin:/bin", "C.UTF-8"
#: The variables every run is given and nothing else: a fixed hash seed, so a set's repr (part of a surface) is the
#: same in the read and in the check, and one thread per numeric library (OpenBLAS starts one per core otherwise).
FIXED_VARIABLES = (("PYTHONHASHSEED", "0"), ("OPENBLAS_NUM_THREADS", "1"), ("OMP_NUM_THREADS", "1"),
                   ("MKL_NUM_THREADS", "1"), ("NUMEXPR_MAX_THREADS", "1"), ("TMPDIR", "/tmp"))
TMP_BYTES = 256 * 1024 * 1024
CPU_SECONDS, FILE_BYTES, OPEN_FILES = 3600, 1024 * 1024 * 1024, 4096
#: The checks of each kind of card, in the order an evidence record lists them.
CHECKS = {"class": ("object_known", "kind_matches", "ancestors_in_order", "constructor_matches", "members_match"),
          "function": ("object_known", "kind_matches", "signature_matches"),
          "method": ("object_known", "kind_matches", "member_matches"),
          "property": ("object_known", "kind_matches", "member_matches")}
CONSTRUCTOR = "<constructor>"


@dataclass(frozen=True)
class PythonEngine:
    """The interpreter that imports the wheels, and the environment it imports them from."""

    path: str
    version: str
    sha256: str
    distribution: str = ""
    wheel: str = ""
    wheel_sha256: str = ""
    environment: tuple = ()  # ((wheel file name, SHA-256), ...), the library's own first

    def environment_sha256(self) -> str:
        return hashlib.sha256(json.dumps([list(row) for row in self.environment]).encode("utf-8")).hexdigest()

    def identity(self) -> dict:
        return {"name": ENGINE_NAME, "version": self.version, "binary_sha256": self.sha256,
                "distribution": self.distribution, "wheel": self.wheel, "wheel_sha256": self.wheel_sha256,
                "environment_sha256": self.environment_sha256()}


def locate(path: str, expected_version: str) -> PythonEngine:
    """The pinned interpreter, which must be the version the sources name."""
    binary = Path(path)
    if not binary.is_file():
        raise NativeError("engine_missing", f"{path} is not installed")
    completed = subprocess.run([str(binary), *FLAGS, "-c", "import sys; print(sys.version.split()[0])"],
                               capture_output=True, text=True, timeout=60, env={"PATH": SYSTEM_PATH})
    version = completed.stdout.strip()
    if version != expected_version:
        raise NativeError("engine_version_differs", f"{path} is {version or 'unreadable'}, not {expected_version}")
    resolved = binary.resolve()
    return PythonEngine(str(resolved), version, godot_native.file_sha256(resolved))


def sandbox_argv(interpreter: str, roots, out: Path, mode: str, *, bwrap: str = "bwrap") -> list:
    argv = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    for path in HIDDEN_PATHS:
        if os.path.isdir(path) and not os.path.islink(path):
            argv += ["--tmpfs", path]
    argv += ["--size", str(TMP_BYTES), "--tmpfs", "/tmp", "--unshare-net", "--unshare-ipc", "--unshare-pid",
             "--unshare-uts", "--die-with-parent", "--new-session", "--dir", SANDBOX_HOME]
    for index, root in enumerate(roots):
        argv += ["--ro-bind", str(Path(root).resolve()), f"{SANDBOX_ENV}/{index}"]
    argv += ["--ro-bind", str(SCRIPT), f"{SANDBOX_BIN}/{SCRIPT.name}", "--bind", str(Path(out).resolve()),
             SANDBOX_OUT, "--chdir", SANDBOX_OUT, "--clearenv", "--setenv", "HOME", SANDBOX_HOME, "--setenv", "PATH",
             SYSTEM_PATH, "--setenv", "LANG", LOCALE]
    for name, value in FIXED_VARIABLES:
        argv += ["--setenv", name, value]
    return argv + ["--", interpreter, *FLAGS, f"{SANDBOX_BIN}/{SCRIPT.name}", mode, f"{SANDBOX_OUT}/spec.json",
                   f"{SANDBOX_OUT}/result.json"]


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS + 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_BYTES, FILE_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (OPEN_FILES, OPEN_FILES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(engine: PythonEngine, roots, spec: dict, workspace: Path, mode: str, *, timeout: float = 3600.0) -> dict:
    """One sandboxed run of python_introspect.py over the wheels' folders: the result it wrote, or NativeError."""
    if mode not in MODES:
        raise NativeError("mode_unknown", mode)
    if not shutil.which("bwrap"):
        raise NativeError("sandbox_unavailable", "bubblewrap is not installed")
    workspace = Path(workspace)
    if workspace.exists():
        shutil.rmtree(workspace)
    out = workspace / "out"
    out.mkdir(parents=True)
    body = dict(spec, record_type=SPEC_RECORD, roots=[f"{SANDBOX_ENV}/{index}" for index in range(len(roots))])
    (out / "spec.json").write_text(json.dumps(body, sort_keys=True), encoding="utf-8")
    process = subprocess.Popen(sandbox_argv(engine.path, roots, out, mode), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={"PATH": SYSTEM_PATH},
                               start_new_session=True, preexec_fn=_limits)
    try:
        _stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise NativeError("sandbox_timed_out", f"{mode} ran longer than {timeout:.0f} s") from None
    result = out / "result.json"
    if not result.is_file():
        raise NativeError("introspection_wrote_nothing",
                          f"exit {process.returncode}: {stderr.decode('utf-8', 'replace')[-400:]}")
    answer = json.loads(result.read_text(encoding="utf-8"))
    expected = RESULTS_RECORD if mode == READ else CHECK_RECORD
    if answer.get("record_type") != expected:
        raise NativeError("introspection_answer_invalid", str(answer.get("record_type")))
    if answer.get("interpreter") != engine.version:
        raise NativeError("engine_version_differs", f"the sandbox ran {answer.get('interpreter')}")
    return answer


# -- the check of every card ----------------------------------------------------------------------------------------
def _signature(item: dict) -> dict:
    return {"params": item.get("params"), "returns": (item.get("returns") or {}).get("type")}


def member_expectation(section: str, item: dict) -> dict:
    """What a card's api.json says of one member, in the record shape python_introspect.member_record writes."""
    if section == "methods":
        return {"kind": "method", "qualifiers": list(item.get("qualifiers", ())), "signature": _signature(item)}
    if section == "constants":
        return {"kind": "constant", "value": item["value"]}
    row = {"kind": item.get("kind", "property"), "qualifiers": list(item.get("qualifiers", ())),
           "type": item.get("type")}
    if "default" in item:
        row["default"] = item["default"]
    return row


def expectation(api: dict, location: dict) -> dict:
    """What the interpreter is asked about one card: its object's location (module, qualified name, member) and every
    item of its api.json."""
    card = {"card": api["class"], "kind": api["kind"], "module": location["module"],
            "qualname": location["qualname"]}
    sections = api["sections"]
    if api["kind"] == "function":
        card["functions"] = [{"signature": _signature(item), "qualifiers": list(item.get("qualifiers", ()))}
                             for item in sections.get("functions", ())]
    elif api["kind"] in ("method", "property"):
        section = "methods" if api["kind"] == "method" else "members"
        card.update(member=location["member"], expected=member_expectation(section, sections[section][0]))
    else:
        constructors = sections.get("constructors", ())
        card["constructor"] = constructors[0].get("params") if constructors else None
        card["members"] = {item["name"]: member_expectation(section, item)
                           for section in ("methods", "members", "constants") for item in sections.get(section, ())}
        card["ancestors"] = list(location.get("ancestors", ()))
    return card


def verify(engine: PythonEngine, roots, apis: list, locations: dict, workspace: Path, *,
           timeout: float = 3600.0) -> dict:
    """{card: the interpreter's answer} for every api.json given, from one sandboxed run."""
    cards = [expectation(api, locations[api["class"]]) for api in apis]
    answer = run(engine, roots, {"cards": cards, "target": 0}, workspace, VERIFY, timeout=timeout)
    if any(row.get("kind") == "network" for row in answer.get("events", ())):
        raise NativeError("import_touches_network", json.dumps(answer["events"][:3])[:300])
    return answer["cards"]


def evidence(engine: PythonEngine, api: dict, answer: "dict | None", card_digest: str) -> dict:
    """The evidence record of one card: each check of its kind passed or failed, bound to the card's digest."""
    answer = answer if isinstance(answer, dict) else {}
    differs, missing = list(answer.get("differs") or []), list(answer.get("missing") or [])
    checks = []
    for name in CHECKS[api["kind"]]:
        if name == "object_known":
            state, detail = answer.get("known") is True, {"card": api["class"], "error": answer.get("error", "")}
        elif name == "kind_matches":
            state, detail = answer.get("kind_matches") is True, {"kind": api["kind"]}
        elif name == "ancestors_in_order":
            state, detail = answer.get("ancestors_in_order") is True, {"ancestors": api.get("inherits", [])[:25]}
        elif name == "constructor_matches":
            state, detail = answer.get("known") is True and CONSTRUCTOR not in differs, {}
        else:
            named = [entry for entry in differs + missing if entry != CONSTRUCTOR]
            checked = sum(len(api["sections"].get(section, ())) for section in api["sections"])
            state = answer.get("kind_matches") is True and not named
            detail = {"checked": checked, "differs": [entry for entry in differs if entry != CONSTRUCTOR]
                      [:godot_native.MAXIMUM_LISTED], "missing": missing[:godot_native.MAXIMUM_LISTED]}
        checks.append({"name": name, "state": PASSED if state else FAILED, "detail": detail})
    state = PASSED if checks and all(check["state"] == PASSED for check in checks) else FAILED
    return {"record_type": EVIDENCE_RECORD, "engine": engine.identity(), "class": api["class"], "kind": api["kind"],
            "card_digest": card_digest, "checks": checks, "state": state}


__all__ = ["PythonEngine", "locate", "sandbox_argv", "run", "expectation", "verify", "evidence", "CHECKS",
           "READ", "VERIFY"]
