"""Derive a native-profile plan from the frozen hundred-file plan, and preflight its layout.

The hundred-file plan of September 23 predates the native review profile's
placement rules, so every package generated from it was refused by the
prechecks. This keeps its eight tool methods and changes only the declared
layout: acceptance data moves to verification/, compatibility metadata becomes
strict JSON data, a CLAUDE.md that imports AGENTS.md serves the declared claude
style, and file purposes state the schema and import rules. Methods, briefs and
acceptance criteria are otherwise unchanged. The plan is pinned to HEAD with
the sources committed there.

``preflight`` builds one synthetic package per method with minimal content that
follows the declared layout, prepares it with the existing factory and writes
the factory input, so the native prechecks can judge the layout before any
model is asked. The synthetic packages are fixtures, never candidates.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]

from tools import generate_original_native_candidates as generation  # noqa: E402

SCHEMA_RULE = (' It must declare "$schema": "https://json-schema.org/draft/2020-12/schema" and use only local "#" '
               "references.")
TEST_RULE = (" Use only unittest and the standard library. Run the helper as a subprocess by its bundled path, or "
             "import it by its bare module name after adding its folder to sys.path; never import a package named "
             "tools or tests.")
DROPPED = ("select_traceable_context_evidence", "review_json_with_native_claude_plugin")


def successor(method):
    files = []
    for row in method["files"]:
        row = dict(row)
        if row["path"] == "fixtures/acceptance.json":
            row["path"] = "verification/acceptance.json"
        if row["path"] == "references/compatibility.json":
            row["role"] = "other"
        if row["path"].startswith("contracts/") and row["path"].endswith(".schema.json"):
            row["purpose"] += SCHEMA_RULE
        if row["path"].startswith("tests/") and row["path"].endswith(".py"):
            row["purpose"] += TEST_RULE
        files.append(row)
    files.insert(1, {"path": "CLAUDE.md", "role": "instruction_file", "media_type": "text/markdown",
                     "purpose": "Claude Code entrypoint: one line, @AGENTS.md, importing the shared instructions, "
                                "and nothing else."})
    return {**method, "files": files}


def build(source_plan: Path, output: Path) -> dict:
    plan = json.loads(source_plan.read_text(encoding="utf-8"))
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sources = {}
    for name in plan["sources"]:
        raw = (ROOT / name).read_bytes()
        if raw != subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=ROOT):
            raise SystemExit("source is not the committed version: " + name)
        sources[name] = hashlib.sha256(raw).hexdigest()
    methods = [successor(method) for method in plan["methods"] if method["id"] not in DROPPED]
    derived = {**plan, "source_revision": revision, "sources": sources, "methods": methods}
    output.write_text(json.dumps(derived, indent=1) + "\n", encoding="utf-8")
    return {"path": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "source_revision": revision, "methods": len(methods),
            "payload_files_planned": sum(len(method["files"]) for method in methods)}


def synthetic(row, method):
    stem = Path(row["path"]).stem
    if row["path"] == "AGENTS.md":
        return f"# {method['title']}\n\nRun `python3 tools/{method['id']}.py`. See [method](references/method.md).\n"
    if row["path"] == "CLAUDE.md":
        return "@AGENTS.md\n"
    if row["path"].endswith(".schema.json"):
        return json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}) + "\n"
    if row["path"].endswith(".json"):
        return "{}\n"
    if row["path"].startswith("tests/"):
        return f"import subprocess\nimport sys\nimport unittest\n\n\nclass {stem.title().replace('_', '')}(unittest.TestCase):\n    pass\n"
    if row["path"].endswith(".py"):
        return "import json\nimport sys\n\n\ndef main():\n    return 0\n"
    return f"# {stem}\n\nSynthetic layout fixture.\n"


def preflight(plan_path: Path, output: Path) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    producer = {"producer_identity": "layout-preflight:synthetic", "family": "google",
                "method_identity": "original_native_generation_fixture/v1"}
    proposals = []
    for method in plan["methods"]:
        value = {"record_type": generation.DRAFT_TYPE, "method_id": method["id"],
                 "files": [{"path": row["path"], "content": synthetic(row, method)} for row in method["files"]]}
        proposal = generation.parse_draft(generation.canonical(value), method, plan, producer)
        proposals.extend(proposal["proposals"])
    merged = {**{key: proposal[key] for key in ("record_type", "source_revision", "license")},
              "sources": {name: plan["sources"][name] for name in plan["sources"]}, "proposals": proposals}
    output.write_text(json.dumps(merged, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"path": str(output), "proposals": len(proposals)}


if __name__ == "__main__":
    if sys.argv[1] == "build":
        print(json.dumps(build(Path(sys.argv[2]), Path(sys.argv[3]))))
    else:
        print(json.dumps(preflight(Path(sys.argv[2]), Path(sys.argv[3]))))
