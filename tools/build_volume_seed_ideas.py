#!/usr/bin/env python3
"""Turn the owner-authored projects of a volume inventory into seed ideas for the generation lanes.

The owner, September 26, 2026: the attached drive of the owner's own projects
is "seed material for harness component file generation", to be "summarized
into MD files, generated into code, plugins, contracts, etc". This command
reads one inventory written by ``tools/scan_local_volume.py``, keeps the
projects whose provenance class is the owner's own, and writes one
``harness_idea_batch/v1`` whose ideas the OpenCode generation lanes accept
(``tools/opencode_generation_lanes.py``). Each idea carries a bounded
excerpt of the project's own README, module outlines and dependency names
as seed material the lane may copy and adapt, because the owner wrote it.

```text
Seed ideas from one inventory (outside the repository: they quote private paths)
├── seed-ideas.json      harness_idea_batch/v1: one idea per kept project, with applicability.seed
├── seed-report.json     counts by provenance class, owner index status and file kind; what was left out
└── excluded.jsonl       one row per project left out, with its reason
```

What keeps a project out, each recorded: a provenance class that is not the
owner's (a git remote under another account, a licence file or a copyright
line naming someone else), the owner's own project index marking it an
imported workspace or an incomplete archive, no source file, or an excerpt
that could not be read. Nothing here calls a model, copies a project, or
approves anything: the ideas are candidate material for the lanes, whose
output still passes the prechecks and the screening call before publication.

    PYTHONPATH=src python tools/build_volume_seed_ideas.py \\
        --inventory ~/baltor-library/volumes/expansion/inventory-1 --volume /run/media/username/Expansion \\
        --registry MAIN_PROJECTS/PROJECT_REGISTRY.json --output ~/baltor-library/volumes/expansion/seeds-1
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from harness_idea_matrix import DATATYPES, FACET_DIMENSIONS, FILE_KINDS, OPERATIONS, USE_CASES  # noqa: E402
from scan_local_volume import OWNER_DECLARED, OWNER_REMOTE, PROJECT_RECORD_TYPE  # noqa: E402

BATCH_RECORD_TYPE = "harness_idea_batch/v1"
IDEA_RECORD_TYPE = "harness_idea_record/v1"
REPORT_RECORD_TYPE = "volume_seed_report/v1"
SEED_RECORD_TYPE = "volume_seed/v1"
OWNER_CLASSES = (OWNER_DECLARED, OWNER_REMOTE)
#: Statuses of the owner's own project index that mark material the owner did not write.
INDEX_STATUSES_LEFT_OUT = ("imported_workspace", "incomplete_archive")
IDENTITY = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
EXCERPT_BOUND = 6000
README_BOUND = 1500
#: A project without a module outline seeds an idea only when it holds this many source files (a notebook or
#: script collection whose README says what it does), never when it is a README alone.
MINIMUM_SOURCE_FILES_WITHOUT_OUTLINE = 5
MODULE_BOUND = 5
OUTLINE_BOUND = 1200
ENTRY_NAMES = ("main.py", "app.py", "cli.py", "__main__.py", "run.py", "server.py", "bot.py", "pipeline.py")
REQUIREMENT_FILES = ("requirements.txt", "pyproject.toml", "package.json", "environment.yml")
_DATATYPE_WORDS = (
    ("image", ("pil", "pillow", "cv2", "opencv", "image", "photo", "png", "jpeg", "stable diffusion", "diffusers")),
    ("audio", ("audio", "wav", "mp3", "whisper", "speech", "voice", "tts")),
    ("html_page", ("selenium", "playwright", "bs4", "beautifulsoup", "scrape", "scraper", "browser", "html")),
    ("csv_table", ("pandas", "csv", "dataframe", "spreadsheet", "xlsx")),
    ("json_object", ("json", "api", "rest", "webhook", "graphql")),
    ("pdf_document", ("pdf", "pypdf", "reportlab")),
    ("sql_table", ("sqlite", "postgres", "sqlalchemy", "sql", "database")),
    ("log_lines", ("log", "logging", "monitor")),
    ("markdown_document", ("markdown", "notes", "documentation")),
)
_OPERATION_WORDS = (
    ("extraction", ("scrape", "scraper", "extract", "crawl", "parse")),
    ("classification", ("classify", "classifier", "detect", "label", "score", "rank")),
    ("monitoring", ("monitor", "watch", "alert", "poll", "track")),
    ("transformation", ("convert", "render", "generate", "edit", "resize", "encode", "pipeline", "transform")),
    ("validation", ("validate", "verify", "check", "test", "lint")),
    ("matching", ("match", "dedup", "reconcile", "compare")),
    ("planning", ("plan", "schedule", "roadmap", "coach", "goal")),
    ("estimation", ("predict", "forecast", "trading", "backtest", "estimate", "model")),
    ("formatting", ("format", "template", "caption", "post", "publish")),
)
_USE_CASE_WORDS = (
    ("machine_learning", ("torch", "tensorflow", "sklearn", "model", "training", "diffusion", "llm", "embedding")),
    ("data_engineering", ("pipeline", "etl", "pandas", "dataframe", "dataset")),
    ("agentic_task", ("agent", "harness", "automation", "automate", "browser", "selenium", "playwright", "bot")),
    ("financial_reconciliation", ("trading", "finance", "market", "portfolio", "ledger", "invoice")),
    ("entity_resolution", ("entity", "register", "registry", "company", "person", "verification")),
    ("customer_support", ("email", "newsletter", "support", "chat")),
    ("report_generation", ("report", "summary", "dashboard", "analytics")),
    ("devops", ("docker", "deploy", "kubernetes", "terraform", "ci", "infra")),
    ("text_processing", ("text", "caption", "prompt", "content", "social", "post")),
    ("research_analysis", ("research", "analysis", "study", "benchmark")),
)
_DOMAIN_USE_CASES = {"SOCIAL_MEDIA_CONTENT": "text_processing", "LOOP_ENGINE": "agentic_task",
                     "ENTITY_INTELLIGENCE": "entity_resolution", "LEGAL_AND_PROPERTY": "compliance_audit",
                     "FINANCE_AND_MARKETS": "financial_reconciliation", "GOAL_COACHING": "project_management",
                     "CODING_PROJECTS": "software_development", "NEWSLETTER_BUSINESS": "customer_support"}
KNOWN_WRONG = ("The file names a command, a library, a file or a step that the seed project does not contain, or it "
               "presents a third-party library's text as the owner's own procedure instead of the project's approach.")


class SeedError(ValueError):
    """A stable refusal code for seed material that cannot be built as declared."""


def refuse(code: str, message: str = "") -> None:
    raise SeedError(f"{code}: {message}" if message else code)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "project"


def _read(path: Path, bound: int) -> str:
    try:
        with open(path, "rb") as stream:
            return stream.read(bound * 4).decode("utf-8", "replace")[:bound]
    except OSError:
        return ""


def module_outline(path: Path) -> str:
    """The docstring, imports and the signatures of one Python module, never its bodies."""
    text = _read(path, 200_000)
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return ""
    lines = [f"module {path.name}"]
    docstring = ast.get_docstring(tree)
    if docstring:
        lines.append("  doc: " + " ".join(docstring.split())[:300])
    imports = sorted({(alias.name.split(".")[0]) for node in ast.walk(tree)
                      if isinstance(node, ast.Import) for alias in node.names}
                     | {node.module.split(".")[0] for node in ast.walk(tree)
                        if isinstance(node, ast.ImportFrom) and node.module})
    if imports:
        lines.append("  imports: " + ", ".join(imports[:20]))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = ", ".join(argument.arg for argument in node.args.args)
            summary = (ast.get_docstring(node) or "").split("\n")[0][:120]
            lines.append(f"  def {node.name}({arguments}): {summary}".rstrip(": "))
        elif isinstance(node, ast.ClassDef):
            methods = [item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
            lines.append(f"  class {node.name}: methods {', '.join(methods[:12])}")
    return "\n".join(lines)[:OUTLINE_BOUND]


def _entries(root: Path) -> list:
    """Python modules at the project root and one level down, entry files first, bounded."""
    found = []
    try:
        top = sorted(os.scandir(root), key=lambda entry: entry.name)
    except OSError:
        return []
    for entry in top:
        if entry.is_file(follow_symlinks=False) and entry.name.endswith(".py"):
            found.append(Path(entry.path))
        elif entry.is_dir(follow_symlinks=False) and not entry.name.startswith(".") and entry.name not in (
                "node_modules", "venv", ".venv", "__pycache__", "tests", "test", "build", "dist"):
            try:
                for inner in sorted(os.scandir(entry.path), key=lambda item: item.name)[:60]:
                    if inner.is_file(follow_symlinks=False) and inner.name.endswith(".py"):
                        found.append(Path(inner.path))
            except OSError:
                continue
    found.sort(key=lambda path: (path.name not in ENTRY_NAMES, path.name == "__init__.py", len(path.parts), path.name))
    return found[:MODULE_BOUND]


def _requirements(root: Path) -> list:
    names = []
    for name in REQUIREMENT_FILES:
        text = _read(root / name, 4000)
        if not text:
            continue
        if name == "requirements.txt":
            names.extend(re.split(r"[<>=!~\[; ]", line.strip())[0] for line in text.splitlines()
                         if line.strip() and not line.startswith(("#", "-")))
        elif name == "package.json":
            try:
                names.extend(json.loads(text).get("dependencies", {}).keys())
            except ValueError:
                pass
        else:
            names.extend(re.findall(r'^\s*"?([A-Za-z0-9_.-]+)"?\s*[>=<~]', text, re.MULTILINE))
    return sorted({name.lower() for name in names if name})[:30]


def excerpt_for(root: Path, project: dict) -> tuple:
    """(excerpt, modules read): the README head, the module outlines and the dependency names, bounded."""
    parts = []
    readme = (project.get("readme") or "").strip()
    if readme:
        parts.append("README:\n" + readme[:README_BOUND])
    modules = _entries(root)
    outlines = [module_outline(path) for path in modules]
    outlines = [outline for outline in outlines if outline]
    if outlines:
        parts.append("Modules:\n" + "\n".join(outlines))
    requirements = _requirements(root)
    if requirements:
        parts.append("Dependencies: " + ", ".join(requirements))
    return "\n\n".join(parts)[:EXCERPT_BOUND], [path.relative_to(root).as_posix() for path in modules]


def _pick(words: str, table, default: str) -> str:
    scores = Counter()
    for value, needles in table:
        scores[value] = sum(words.count(needle) for needle in needles)
    best = max(scores, key=lambda value: (scores[value], -[value for value, _ in table].index(value)))
    return best if scores[best] > 0 else default


def facets_for(project: dict, excerpt: str, domain: str) -> tuple:
    words = (project["name"] + " " + excerpt).lower()
    datatype = _pick(words, _DATATYPE_WORDS, "text")
    operation = _pick(words, _OPERATION_WORDS, "transformation")
    use_case = _pick(words, _USE_CASE_WORDS, _DOMAIN_USE_CASES.get(domain, "software_development"))
    languages = project.get("languages") or {}
    if "hooks.json" in excerpt or operation == "monitoring" and use_case in ("devops", "agentic_task"):
        kind = "hook"
    elif use_case == "agentic_task" and sum(languages.values()) > 40:
        kind = "workflow"
    elif use_case == "project_management":
        kind = "harness_routing"
    else:
        kind = "skill"
    assert datatype in DATATYPES and operation in OPERATIONS and use_case in USE_CASES and kind in FILE_KINDS
    return datatype, operation, use_case, kind


def index_statuses(registry_path: "Path | None", volume: Path) -> dict:
    """The owner's own project index: relative path -> status, for the projects it names."""
    if registry_path is None or not registry_path.is_file():
        return {}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    statuses = {}
    for item in registry.get("items", []):
        path = item.get("path") or ""
        try:
            relative = Path(path).resolve().relative_to(volume.resolve()).as_posix()
        except ValueError:
            continue
        statuses[relative] = (item.get("status") or "", item.get("domain") or "")
    return statuses


def _index_lookup(statuses: dict, relative: str) -> tuple:
    """The nearest index entry above or at the project path, or ('', '')."""
    parts = relative.split("/")
    for length in range(len(parts), 0, -1):
        found = statuses.get("/".join(parts[:length]))
        if found:
            return found
    return "", ""


def build(inventory: Path, volume: Path, registry: "Path | None", output: Path, *, maximum: int,
          volume_name: str) -> dict:
    projects_path = inventory / "projects.jsonl"
    if not projects_path.is_file():
        refuse("inventory_missing", f"{projects_path} is not an inventory")
    inventory_sha256 = hashlib.sha256(projects_path.read_bytes()).hexdigest()
    statuses = index_statuses(registry, volume)
    output.mkdir(parents=True, exist_ok=False)
    excluded_stream = (output / "excluded.jsonl").open("w", encoding="utf-8")
    ideas, seen_ids = [], set()
    counts = {"projects": 0, "kept": 0, "by_provenance_class": Counter(), "by_index_status": Counter(),
              "by_file_kind": Counter(), "by_use_case": Counter(), "excluded": Counter()}
    for line in projects_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        project = json.loads(line)
        if project.get("record_type") != PROJECT_RECORD_TYPE:
            refuse("inventory_record_unsupported", f"a project row is {project.get('record_type')!r}")
        counts["projects"] += 1
        counts["by_provenance_class"][project["provenance_class"]] += 1
        status, domain = _index_lookup(statuses, project["path"])
        counts["by_index_status"][status or "(not in the owner's index)"] += 1
        reason = ""
        if project["provenance_class"] not in OWNER_CLASSES:
            reason = "provenance_class:" + project["provenance_class"]
        elif status in INDEX_STATUSES_LEFT_OUT:
            reason = "owner_index_status:" + status
        elif project["name"].startswith("_") or "/_ORGANIZATION/" in "/" + project["path"] + "/":
            reason = "organization_folder"
        elif not project.get("source_files"):
            reason = "no_source_file"
        if not reason:
            root = volume / project["path"]
            excerpt, modules = excerpt_for(root, project)
            if not excerpt.strip():
                reason = "no_readable_excerpt"
            elif not modules and project.get("source_files", 0) < MINIMUM_SOURCE_FILES_WITHOUT_OUTLINE:
                # A folder that is only a README about other folders seeds nothing a harness can use.
                reason = "no_module_outline"
        if reason:
            counts["excluded"][reason.split(":")[0]] += 1
            excluded_stream.write(json.dumps({"path": project["path"], "reason": reason}) + "\n")
            continue
        if len(ideas) >= maximum:
            counts["excluded"]["maximum_reached"] += 1
            excluded_stream.write(json.dumps({"path": project["path"], "reason": "maximum_reached"}) + "\n")
            continue
        datatype, operation, use_case, kind = facets_for(project, excerpt, domain or project.get("top_folder", ""))
        # The identity names the project by its folder and its parent, so "src" under two projects stays two
        # identities; a further clash takes a short digest of the path.
        parts = project["path"].split("/")
        parent = _slug(parts[-2]) if len(parts) > 1 else ""
        identity = "-".join(part for part in ("vol", _slug(volume_name), parent[:20], _slug(project["name"])[:24]) if part)
        if identity in seen_ids:
            identity = f"{identity[:56]}-{hashlib.sha256(project['path'].encode()).hexdigest()[:6]}"
        if not IDENTITY.match(identity):
            refuse("identity_invalid", identity)
        seen_ids.add(identity)
        excerpt_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        task = (f"The owner's own project {project['name']} ({', '.join(sorted(project.get('languages') or {}))}) "
                f"at {project['path']} on the {volume_name} volume. " + " ".join((project.get("readme") or "")
                                                                                 .split())[:400])
        ideas.append({
            "record_type": IDEA_RECORD_TYPE, "id": identity, "file_kind": kind, "datatype": datatype,
            "operation": operation, "use_case": use_case, "lifecycle": "candidate",
            "applicability": {
                "occupation_code": "", "occupation_title": "", "task_reference": task,
                "facet_dimensions": list(FACET_DIMENSIONS), "facet": {},
                "seed": {"record_type": SEED_RECORD_TYPE, "volume": volume_name, "project_path": project["path"],
                         "project_name": project["name"], "provenance_class": project["provenance_class"],
                         "owner_index_status": status, "inventory_sha256": inventory_sha256,
                         "modules_read": modules, "excerpt_sha256": excerpt_sha256,
                         "authorship_basis": ("The owner declared on September 26, 2026 that everything on the "
                                              "volume was written by the owner; no git remote, licence file or "
                                              "copyright line of this project names anyone else.")},
                "seed_excerpt": excerpt},
            "method_signature": hashlib.sha256(f"{project['path']}|{excerpt_sha256}".encode()).hexdigest(),
            "brief": (f"Write an original {kind.replace('_', ' ')} that lets a coding harness do what the owner's "
                      f"project {project['name']} does, in the owner's own approach: its purpose, the steps its "
                      f"modules take, the inputs and outputs, the effects it needs, and the check that shows it "
                      f"worked. Use the seed excerpt freely; it is the owner's own work."),
            "known_wrong": KNOWN_WRONG,
        })
        counts["kept"] += 1
        counts["by_file_kind"][kind] += 1
        counts["by_use_case"][use_case] += 1
    excluded_stream.close()
    if not ideas:
        refuse("no_seed_project", "no project kept its owner provenance and readable excerpt")
    batch_digest = hashlib.sha256(json.dumps(ideas, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    batch = {"record_type": BATCH_RECORD_TYPE,
             "matrix": {"record_type": "harness_idea_matrix/v1", "datatypes": len(DATATYPES),
                        "operations": len(OPERATIONS), "use_cases": len(USE_CASES),
                        "facet_dimensions": list(FACET_DIMENSIONS)},
             "sources": [{"kind": "owner_volume_inventory", "path": str(projects_path), "sha256": inventory_sha256}],
             "ideas": ideas, "idea_count": len(ideas),
             "unique_method_signatures": len({idea["method_signature"] for idea in ideas}),
             "unique_ids": len({idea["id"] for idea in ideas}), "file_kinds": len(FILE_KINDS),
             "batch_sha256": batch_digest}
    (output / "seed-ideas.json").write_text(json.dumps(batch, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {"record_type": REPORT_RECORD_TYPE, "written_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "inventory": str(inventory), "inventory_sha256": inventory_sha256, "volume": str(volume),
              "registry": str(registry) if registry else "", "maximum": maximum,
              **{key: (dict(value.most_common()) if isinstance(value, Counter) else value)
                 for key, value in counts.items()},
              "batch_sha256": batch_digest, "what_this_is_not": "No model was called, no project copied, nothing approved."}
    (output / "seed-report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--volume", required=True)
    parser.add_argument("--registry", help="the owner's PROJECT_REGISTRY.json, relative to the volume or absolute")
    parser.add_argument("--output", required=True, help="a new folder outside the repository")
    parser.add_argument("--maximum", type=int, default=500)
    parser.add_argument("--volume-name", default="")
    args = parser.parse_args(argv)
    volume, output = Path(args.volume).resolve(), Path(args.output).resolve()
    repository = HERE.parent
    if output == repository or repository in output.parents:
        print("seed ideas quote private paths; write them outside the repository", file=sys.stderr)
        return 2
    registry = Path(args.registry) if args.registry else None
    if registry is not None and not registry.is_absolute():
        registry = volume / registry
    try:
        report = build(Path(args.inventory).resolve(), volume, registry, output, maximum=args.maximum,
                       volume_name=args.volume_name or volume.name)
    except SeedError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({key: report[key] for key in ("projects", "kept", "by_provenance_class", "by_file_kind",
                                                     "excluded")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
