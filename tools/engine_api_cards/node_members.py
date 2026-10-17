"""The native side of a JavaScript library's member cards: Node requires the published module once and is asked about
every card (javascript_members_verify.mjs), the way node_native asks a library about its classes.

```text
node javascript_members_verify.mjs MODULE expectations.json results.json   (an isolated HOME, a wall-clock limit)
├── a function card: the value at its path from the module's export is a function
├── an object card: the value is an object or a function, every listed method is a function on it and every listed
│   property is held by it (its own or a prototype's)
└── a member card: its owner holds it, as a function for a method
      │
      └── one evidence record per card (engine_api_card_native_evidence/v1): Node's identity, the module's file and
          SHA-256, the card digest it checked, each check, and no time stamp
```
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import godot_native
from .godot_native import EVIDENCE_RECORD, FAILED, PASSED, NativeError
from .node_native import LOCALE, SEARCH_PATH, NodeEngine

VERIFIER = Path(__file__).resolve().parent / "javascript_members_verify.mjs"
EXPECTATIONS_NAME, RESULTS_NAME = "expectations.json", "results.json"
RESULTS_RECORD = "javascript_member_check_results/v1"
#: The checks of each kind of card, in the order an evidence record lists them.
CHECKS = {"function": ("function_exported",), "object": ("object_exported", "members_present"),
          "method": ("member_present",), "property": ("member_present",)}
LISTED_SECTIONS = (("methods", "method"), ("members", "property"))


def expectation(api: dict, path: list) -> dict:
    """What Node is asked about one card, from its own api.json and its object's property path."""
    card = {"card": api["class"], "kind": api["kind"], "path": list(path)}
    if api["kind"] == "object":
        card["members"] = [{"name": item["name"], "kind": kind} for section, kind in LISTED_SECTIONS
                           for item in api["sections"].get(section, ())]
    return card


def verify(engine: NodeEngine, module_file: Path, apis: list, paths: dict, workspace: Path, *,
           timeout: int = 300) -> dict:
    """{card: Node's answer} for every api.json given, from one Node run."""
    workspace = Path(workspace)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    shutil.copyfile(VERIFIER, workspace / VERIFIER.name)
    (workspace / EXPECTATIONS_NAME).write_text(json.dumps(
        {"cards": [expectation(api, paths[api["class"]]) for api in apis]}), encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="baltor-node-home-", dir=workspace) as home:
        environment = {"HOME": home, "PATH": SEARCH_PATH, "LANG": LOCALE, "TMPDIR": home}
        completed = subprocess.run([engine.path, VERIFIER.name, str(Path(module_file).resolve()), EXPECTATIONS_NAME,
                                    RESULTS_NAME], cwd=workspace, env=environment, capture_output=True, text=True,
                                   timeout=timeout)
    results = workspace / RESULTS_NAME
    if not results.is_file():
        raise NativeError("verifier_wrote_nothing", f"exit {completed.returncode}: {completed.stderr[-300:]}")
    answer = json.loads(results.read_text(encoding="utf-8"))
    if answer.get("record_type") != RESULTS_RECORD or not isinstance(answer.get("cards"), dict):
        raise NativeError("verifier_answer_invalid", str(answer.get("record_type")))
    return answer["cards"]


def evidence(engine: NodeEngine, api: dict, answer: "dict | None", card_digest: str) -> dict:
    """The evidence record of one card: each check passed or failed, bound to the card's digest."""
    answer = answer if isinstance(answer, dict) else {}
    checks = []
    for name in CHECKS[api["kind"]]:
        if name == "members_present":
            missing = answer.get("missing") if isinstance(answer.get("missing"), list) else None
            state = answer.get("kind_matches") is True and missing == []
            detail = {"checked": sum(len(api["sections"].get(section, ())) for section, _kind in LISTED_SECTIONS),
                      "missing": (missing or [])[:godot_native.MAXIMUM_LISTED] if missing is not None
                      else "no answer"}
        else:
            state = answer.get("known") is True and answer.get("kind_matches") is True
            detail = {"card": api["class"], "kind": api["kind"]}
        checks.append({"name": name, "state": PASSED if state else FAILED, "detail": detail})
    state = PASSED if checks and all(check["state"] == PASSED for check in checks) else FAILED
    return {"record_type": EVIDENCE_RECORD, "engine": engine.identity(), "class": api["class"], "kind": api["kind"],
            "card_digest": card_digest, "checks": checks, "state": state}


__all__ = ["expectation", "verify", "evidence", "CHECKS"]
