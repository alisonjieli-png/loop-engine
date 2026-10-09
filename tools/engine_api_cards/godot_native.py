"""The Godot engine adapter's native side: dump the class reference from the pinned binary, and ask the same
binary about every card.

```text
the pinned Godot binary (located and run by tools/creative_originals/engines.py: an isolated HOME and XDG
│   folders inside the workspace, a wall-clock limit, a memory-capped scope)
├── dump:   --headless --doctool OUT        every class's structure, no description text (about 1 s)
└── verify: --headless --script godot_verify.gd -- expectations.json results.json
            one run for every card: ClassDB, Variant types and the global scopes (godot_verify.gd)
                  │
                  └── one evidence record per class (engine_api_card_native_evidence/v1): the engine build, the
                      card digest it checked, each check with its state, and no time stamp
```
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from creative_originals import engines

from .godot_reference import ClassKind

EVIDENCE_RECORD = "engine_api_card_native_evidence/v1"
EXPECTATIONS_RECORD = "godot_class_check_expectations/v1"
RESULTS_RECORD = "godot_class_check_results/v1"
EVIDENCE_PATH = "verification/native.json"
VERIFIER = Path(__file__).resolve().parent / "godot_verify.gd"
VERIFIER_NAME, PROBE_TARGET_NAME = "godot_verify.gd", "probe_target.gd"
PROBE_TARGET_TEXT = "extends RefCounted\n"
EXPECTATIONS_NAME, RESULTS_NAME = "expectations.json", "results.json"
DUMP_FOLDER = "doctool"
ENGINE_NAME = "godot"
PASSED, FAILED = EVIDENCE_STATES = ("passed", "failed")
#: The checks of each kind of class, in the order an evidence record lists them: the check, the key of the engine's
#: answer it reads and the key of the expectation that lists what was asked.
CHECKS = {ClassKind.OBJECT_CLASS: (("class_known", None, None), ("parent_matches", None, None),
                                   ("methods_known", "methods", "methods"),
                                   ("properties_known", "members", "members"),
                                   ("overridden_properties_known", "overridden_members", "overridden_members"),
                                   ("signals_known", "signals", "signals"),
                                   ("constants_known", "constants", "constants"),
                                   ("enumerations_known", "enums", "enums")),
          ClassKind.BUILTIN_TYPE: (("type_known", None, None), ("methods_callable", "methods", "methods"),
                                   ("members_readable", "members", "members")),
          ClassKind.GLOBAL_SCOPE: (("scope_known", None, None), ("functions_compile", "methods", "functions"),
                                   ("singletons_known", "members", "members"))}
#: A property that overrides an ancestor's default names that ancestor under this key.
OVERRIDES_KEY = "overrides"
KNOWN_CHECKS = ("class_known", "type_known", "scope_known")
PARENT_CHECK = "parent_matches"
#: The most missing names an evidence record lists for one check.
MAXIMUM_LISTED = 25


class NativeError(RuntimeError):
    """The engine could not be run or did not answer; nothing it would have checked passes."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_version(binary: Path) -> str:
    """The version line a Godot build prints for --version, run with an isolated HOME; "" when it prints none."""
    with tempfile.TemporaryDirectory(prefix="baltor-godot-version-") as home:
        completed = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=120,
                                   env=engines._isolated_environment(Path(home)))
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()[:1].isdigit()]
    return lines[0] if lines else ""


def locate(path: "str | None" = None) -> engines.Engine:
    """The Godot build to use: the given path, else the pinned build tools/creative_originals/engines.py finds."""
    if path:
        binary = Path(path).resolve()
        if not binary.is_file():
            raise NativeError("engine_missing", str(binary))
        return engines.Engine(ENGINE_NAME, str(binary), build_version(binary), file_sha256(binary))
    try:
        return engines.locate(ENGINE_NAME)
    except engines.EngineUnavailable as error:
        raise NativeError("engine_missing", str(error)[:300]) from None


def dump(engine: engines.Engine, workspace: Path, *, timeout: int = 300) -> dict:
    """Run the binary's doctool into workspace/doctool and return {relative path: bytes} of every class file."""
    workspace = Path(workspace)
    target = workspace / DUMP_FOLDER
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    outcome = engines.run(engine, ["--headless", "--doctool", str(target)], workspace=workspace, timeout=timeout)
    files = {str(path.relative_to(target)): path.read_bytes() for path in sorted(target.rglob("*.xml"))}
    if outcome.get("returncode") != 0 or not files:
        raise NativeError("dump_failed", f"exit {outcome.get('returncode')}: {outcome.get('stderr', '')[-300:]}")
    return files


def dump_digest(files: dict) -> str:
    """One digest of a whole dump: every relative path and the SHA-256 of its bytes."""
    rows = sorted((path, hashlib.sha256(data).hexdigest()) for path, data in files.items())
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def expectation(api: dict) -> dict:
    """What the engine is asked about one card, read from the card's own api.json."""
    sections = api["sections"]
    names = {key: [item["name"] for item in sections.get(key, ())] for key in sections}
    row = {"name": api["class"], "kind": api["kind"]}
    if api["kind"] == ClassKind.OBJECT_CLASS.value:
        members = sections.get("members", ())
        row.update({"methods": names.get("methods", []),
                    "members": [item["name"] for item in members if OVERRIDES_KEY not in item],
                    "overridden_members": [item["name"] for item in members if OVERRIDES_KEY in item],
                    "signals": names.get("signals", []),
                    "constants": names.get("constants", []) + [value["name"] for item in sections.get("enums", ())
                                                               for value in item["values"]],
                    "enums": names.get("enums", [])})
    elif api["kind"] == ClassKind.BUILTIN_TYPE.value:
        row.update({"methods": names.get("methods", []), "members": names.get("members", [])})
    else:
        row.update({"functions": [{"name": item["name"], "params": item.get("params", [])}
                                  for item in sections.get("methods", ())],
                    "members": names.get("members", [])})
    return row


def verify(engine: engines.Engine, apis: list, workspace: Path, *, timeout: int = 600) -> dict:
    """{class: the engine's answer} for every api.json given, from one run of the binary."""
    workspace = Path(workspace)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    shutil.copyfile(VERIFIER, workspace / VERIFIER_NAME)
    (workspace / PROBE_TARGET_NAME).write_text(PROBE_TARGET_TEXT, encoding="utf-8")
    (workspace / EXPECTATIONS_NAME).write_text(json.dumps({"record_type": EXPECTATIONS_RECORD,
                                                           "classes": [expectation(api) for api in apis]}),
                                               encoding="utf-8")
    outcome = engines.run(engine, ["--headless", "--script", VERIFIER_NAME, "--", EXPECTATIONS_NAME, RESULTS_NAME],
                          workspace=workspace, timeout=timeout)
    results = workspace / RESULTS_NAME
    if not results.is_file():
        raise NativeError("verifier_wrote_nothing",
                          f"exit {outcome.get('returncode')}: {outcome.get('stderr', '')[-300:]}")
    answer = json.loads(results.read_text(encoding="utf-8"))
    if answer.get("record_type") != RESULTS_RECORD or not isinstance(answer.get("classes"), dict):
        raise NativeError("verifier_answer_invalid", str(answer.get("record_type")))
    return answer["classes"]


def evidence(engine: engines.Engine, api: dict, answer: "dict | None", card_digest: str) -> dict:
    """The evidence record of one card: each check of its kind passed or failed, bound to the card's digest."""
    kind = ClassKind(api["kind"])
    checks = []
    answer = answer if isinstance(answer, dict) else {}
    missing = answer.get("missing") if isinstance(answer.get("missing"), dict) else {}
    asked = expectation(api)
    for name, key, listed_key in CHECKS[kind]:
        if name in KNOWN_CHECKS:
            known = answer.get("known") is True
            checks.append({"name": name, "state": PASSED if known else FAILED, "detail": {"class": api["class"]}})
        elif name == PARENT_CHECK:
            expected = api["inherits"][0] if api.get("inherits") else ""
            found = answer.get("parent")
            checks.append({"name": name, "state": PASSED if found == expected else FAILED,
                           "detail": {"expected": expected, "found": found}})
        else:
            listed = asked.get(listed_key, [])
            absent = missing.get(key) if isinstance(missing.get(key), list) else None
            state = PASSED if absent == [] else FAILED
            checks.append({"name": name, "state": state,
                           "detail": {"checked": len(listed),
                                      "missing": (absent or [])[:MAXIMUM_LISTED] if absent is not None
                                      else "no answer"}})
    state = PASSED if checks and all(check["state"] == PASSED for check in checks) else FAILED
    return {"record_type": EVIDENCE_RECORD, "engine": engine.identity(), "class": api["class"], "kind": kind.value,
            "card_digest": card_digest, "checks": checks, "state": state}


def read_evidence(data: bytes, api: dict, card_digest: str) -> dict:
    """An evidence record checked against the card it claims to describe; raises NativeError with the reason."""
    try:
        record = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise NativeError("evidence_unreadable") from None
    fields = {"record_type", "engine", "class", "kind", "card_digest", "checks", "state"}
    if not isinstance(record, dict) or set(record) != fields or record["record_type"] != EVIDENCE_RECORD:
        raise NativeError("evidence_invalid", "record shape")
    if record["class"] != api["class"] or record["card_digest"] != card_digest:
        raise NativeError("evidence_stale", f"{api['class']}: the evidence describes other card bytes")
    if record["state"] not in EVIDENCE_STATES or not record["checks"]:
        raise NativeError("evidence_invalid", "state and checks")
    if record["state"] == PASSED and any(check.get("state") != PASSED for check in record["checks"]):
        raise NativeError("evidence_invalid", "a passed record holds only passed checks")
    if record["state"] != PASSED:
        failed = [check["name"] for check in record["checks"] if check.get("state") != PASSED]
        raise NativeError("native_check_failed", f"{api['class']}: {', '.join(failed)}")
    return record


def evidence_bytes(record: dict) -> bytes:
    return (json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


__all__ = ["EVIDENCE_RECORD", "EVIDENCE_PATH", "NativeError", "locate", "dump", "dump_digest", "expectation",
           "verify", "evidence", "read_evidence", "evidence_bytes", "file_sha256"]
