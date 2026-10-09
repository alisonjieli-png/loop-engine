"""The native side of a JavaScript library's cards: import the library's published module in Node and ask it about
every card in one run (javascript_verify.mjs).

```text
node javascript_verify.mjs MODULE expectations.json results.json   (an isolated HOME, a wall-clock limit)
├── the module exports the class as a constructor
├── its parent is the expected one
├── every listed method is callable (static on the class, else on its prototype or a new instance)
└── every listed property is held: on the class (static), its prototypes or a new instance, or named in the source
    of the class or a class it extends; a property the card marks "declare" must not be held
      │
      └── one evidence record per class (engine_api_card_native_evidence/v1, as godot_native writes it): Node's
          identity, the module's file and SHA-256, the card digest it checked, each check, and no time stamp
```

A member marked abstract has no body for any module to hold (a subclass implements it); it is listed on the card
and not asked. "declare" is not read from a declaration: observe() asks the same module which properties it does
not hold before the cards are written, and the check then holds each card to that observation both ways.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import godot_native
from .godot_native import EVIDENCE_RECORD, FAILED, PASSED, NativeError

VERIFIER = Path(__file__).resolve().parent / "javascript_verify.mjs"
VERIFIER_NAME, EXPECTATIONS_NAME, RESULTS_NAME = "javascript_verify.mjs", "expectations.json", "results.json"
RESULTS_RECORD = "javascript_class_check_results/v1"
NODE_NAME = "node"
#: The checks of a class, in the order an evidence record lists them, and the key of the answer each reads.
CHECKS = (("class_exported", None), ("parent_matches", None), ("methods_callable", "methods"),
          ("properties_present", "members"))
KNOWN_CHECK, PARENT_CHECK = "class_exported", "parent_matches"
MEMBERS_KEY = "members"
STATIC = "static"
#: The environment Node runs with: no user configuration, no network proxy, a fixed locale.
SEARCH_PATH, LOCALE = "/usr/bin:/bin", "C.UTF-8"


@dataclass(frozen=True)
class NodeEngine:
    """The Node build that imports the module, and the module it imports."""

    path: str
    version: str
    sha256: str
    module: str  # the module's path inside the package, as the card names it
    module_sha256: str

    def identity(self) -> dict:
        return {"name": NODE_NAME, "version": self.version, "binary_sha256": self.sha256, "module": self.module,
                "module_sha256": self.module_sha256}


def locate(module: str, module_sha256: str, path: "str | None" = None) -> NodeEngine:
    """Node on the system path (or the one named), with its version and binary digest."""
    found = path or shutil.which(NODE_NAME)
    if not found or not Path(found).is_file():
        raise NativeError("engine_missing", "node is not installed")
    version = subprocess.run([found, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    return NodeEngine(str(Path(found).resolve()), version, godot_native.file_sha256(Path(found).resolve()), module,
                      module_sha256)


#: A member no module holds by itself (a subclass implements it): listed on a card and not asked.
ABSTRACT = "abstract"
#: A property the module was observed not to hold: it exists once a caller assigns it, and the check confirms the
#: module still does not hold it.
DECLARE = "declare"


def _asked(item: dict) -> bool:
    return ABSTRACT not in item.get("qualifiers", ())


def _declared(item: dict) -> bool:
    return DECLARE in item.get("qualifiers", ())


def expectation(api: dict) -> dict:
    """What the module is asked about one card, read from the card's own api.json."""
    def rows(section):
        return [{"name": item["name"], "static": STATIC in item.get("qualifiers", ())}
                for item in api["sections"].get(section, ()) if _asked(item)]
    return {"name": api["class"], "methods": rows("methods"), "members": rows("members")}


def unasked(api: dict, section: str) -> int:
    """How many listed members of a section are abstract, which no module holds by itself."""
    return sum(1 for item in api["sections"].get(section, ()) if not _asked(item))


def verify(engine: NodeEngine, module_file: Path, apis: list, workspace: Path, *, timeout: int = 300) -> dict:
    """{class: the module's answer} for every api.json given, from one Node run."""
    workspace = Path(workspace)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    shutil.copyfile(VERIFIER, workspace / VERIFIER_NAME)
    (workspace / EXPECTATIONS_NAME).write_text(json.dumps({"classes": [expectation(api) for api in apis]}),
                                               encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="baltor-node-home-", dir=workspace) as home:
        environment = {"HOME": home, "PATH": SEARCH_PATH, "LANG": LOCALE, "TMPDIR": home}
        completed = subprocess.run([engine.path, VERIFIER_NAME, str(Path(module_file).resolve()), EXPECTATIONS_NAME,
                                    RESULTS_NAME], cwd=workspace, env=environment, capture_output=True, text=True,
                                   timeout=timeout)
    results = workspace / RESULTS_NAME
    if not results.is_file():
        raise NativeError("verifier_wrote_nothing", f"exit {completed.returncode}: {completed.stderr[-300:]}")
    answer = json.loads(results.read_text(encoding="utf-8"))
    if answer.get("record_type") != RESULTS_RECORD or not isinstance(answer.get("classes"), dict):
        raise NativeError("verifier_answer_invalid", str(answer.get("record_type")))
    return answer["classes"]


def observe(engine: NodeEngine, module_file: Path, apis: list, workspace: Path) -> dict:
    """{class: [the listed properties the module does not hold]}, from one Node run over the surfaces given (each
    {"class", "sections"}), before any card is written. A class the module does not export is left out: its card
    fails class_exported."""
    answers = verify(engine, module_file, apis, workspace)
    observed = {}
    for api in apis:
        answer = answers.get(api["class"])
        missing = (answer or {}).get("missing") if isinstance(answer, dict) and answer.get("known") is True else None
        if isinstance(missing, dict) and isinstance(missing.get("members"), list):
            observed[api["class"]] = list(missing["members"])
    return observed


def evidence(engine: NodeEngine, api: dict, answer: "dict | None", card_digest: str) -> dict:
    """The evidence record of one card: each check passed or failed, bound to the card's digest."""
    answer = answer if isinstance(answer, dict) else {}
    missing = answer.get("missing") if isinstance(answer.get("missing"), dict) else {}
    asked = expectation(api)
    checks = []
    for name, key in CHECKS:
        if name == KNOWN_CHECK:
            state = PASSED if answer.get("known") is True else FAILED
            checks.append({"name": name, "state": state, "detail": {"class": api["class"]}})
        elif name == PARENT_CHECK:
            expected = api["inherits"][0] if api.get("inherits") else ""
            found = answer.get("parent")
            checks.append({"name": name, "state": PASSED if found == expected else FAILED,
                           "detail": {"expected": expected, "found": found}})
        else:
            absent = missing.get(key) if isinstance(missing.get(key), list) else None
            declared = [item["name"] for item in api["sections"].get(key, ()) if _asked(item) and _declared(item)]
            # Held: a property the card does not mark declare that the module lacks fails, and so does one the
            # card marks declare that the module holds after all.
            lacking = [entry for entry in absent if entry not in declared] if absent is not None else None
            held = [entry for entry in declared if entry not in absent] if absent is not None else None
            state = PASSED if absent is not None and not lacking and not held else FAILED
            detail = {"checked": len(asked[key]), "abstract": unasked(api, key),
                      "missing": lacking[:godot_native.MAXIMUM_LISTED] if lacking is not None else "no answer"}
            if key == MEMBERS_KEY:
                detail.update(declared=len(declared), held_although_declared=(
                    held[:godot_native.MAXIMUM_LISTED] if held is not None else "no answer"))
            checks.append({"name": name, "state": state, "detail": detail})
    state = PASSED if all(check["state"] == PASSED for check in checks) else FAILED
    return {"record_type": EVIDENCE_RECORD, "engine": engine.identity(), "class": api["class"], "kind": api["kind"],
            "card_digest": card_digest, "checks": checks, "state": state}


__all__ = ["NodeEngine", "locate", "expectation", "verify", "observe", "evidence", "CHECKS"]
