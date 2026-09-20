"""Repository-wide structural review and graph export for development.

Extends the existing component inventory, not runtime authority. All source
relationships are labeled by their evidence: syntax, declarations, or an
explicitly unresolved call. Static analysis never claims an observed run.
"""
from __future__ import annotations

import argparse
import ast
import base64
from datetime import datetime, timezone
import gzip
import hashlib
from importlib import metadata
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from loop_engine.core.component_inventory import ComponentInventoryRequest, run_component_inventory
from loop_engine.reachability_report import LIVE_ENTRY_POINTS, reachable_from, reachability_report
from architecture_audit_evidence import check_evidence, component_rows, source_identity
from architecture_report_data import report_sections

REPOSITORY = Path(__file__).resolve().parents[1]
OUTPUT = REPOSITORY / "artifacts/architecture-audit-2026-09-19"
SENSITIVE_NAMES = {".env", ".env.local", ".env.production", "credentials.json",
                   "kaggle.json", "auth.json", "secrets.json"}
BINARY_SUFFIXES = {".zip", ".pdf", ".png", ".jpg", ".jpeg", ".mp4", ".gif",
                   ".woff", ".woff2", ".ico", ".sqlite", ".db", ".parquet"}


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=REPOSITORY, text=True)


def expression(value) -> str:
    return ast.unparse(value)[:500] if value is not None else ""


def callee(value) -> str:
    """Name a call shape without copying literal prompts or large expressions."""
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        return callee(value.value) + "." + value.attr
    if isinstance(value, ast.Call):
        return callee(value.func) + "()"
    if isinstance(value, ast.Subscript):
        return callee(value.value) + "[]"
    return "<" + type(value).__name__ + ">"


def module_name(path: str) -> str:
    for prefix in ("src/", "devtools/src/"):
        if path.startswith(prefix):
            value = path[len(prefix):-3].replace("/", ".")
            return value.removesuffix(".__init__")
    return ""


def comparison_tables(path: Path) -> dict:
    """Carry the dated research tables without upgrading documentary evidence."""
    if not path.is_file():
        return {"state": "not_recorded", "tables": []}
    source = path.read_text("utf-8")
    tables, rows, heading = [], [], ""
    for line in source.splitlines() + [""]:
        if line.startswith("| Product |") or rows and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r"[: -]+", cell) for cell in cells):
                rows.append(cells)
        elif rows:
            tables.append({"title": heading, "columns": rows[0], "rows": rows[1:]})
            rows = []
        if line.startswith("## "):
            heading = line[3:]
    return {"state": "dated_primary_source_documentation_review", "source": path.name,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "tables": tables,
            "limits": "Not documented is not proof of absence. Vendor accounts and production behavior were not independently exercised."}


def python_structure(path: str, text: str) -> dict:
    tree = ast.parse(text, filename=path)
    module = module_name(path)
    base = module.split(".") if path.endswith("/__init__.py") else module.split(".")[:-1]
    symbols, imports, calls, tests, literals = [], [], [], [], []

    def walk(scope, owner="", inside_test=False):
        for item in ast.iter_child_nodes(scope):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{owner}.{item.name}" if owner else item.name
                testing = inside_test or item.name == "self_test" or item.name.startswith("test_")
                record = {"name": name, "line": item.lineno,
                          "end_line": getattr(item, "end_lineno", item.lineno),
                          "kind": "class" if isinstance(item, ast.ClassDef) else "function",
                          "test_context": testing,
                          "decorators": [expression(x) for x in item.decorator_list]}
                if isinstance(item, ast.ClassDef):
                    record["bases"] = [expression(x) for x in item.bases]
                    record["fields"] = [{"name": expression(x.target), "type": expression(x.annotation)}
                                        for x in item.body if isinstance(x, ast.AnnAssign)]
                else:
                    arguments = item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                    record["arguments"] = [{"name": x.arg, "type": expression(x.annotation)} for x in arguments]
                    record["returns"] = expression(item.returns)
                    if item.name == "self_test" or item.name.startswith("test_"):
                        tests.append({"name": name, "line": item.lineno, "kind": "test_function"})
                symbols.append(record)
                walk(item, name, testing)
                continue
            if isinstance(item, ast.Import):
                imports.extend({"module": x.name, "line": item.lineno, "scope": owner,
                                "test_context": inside_test, "names": [x.asname or x.name]}
                               for x in item.names)
            elif isinstance(item, ast.ImportFrom):
                target = ".".join(base[:len(base) - item.level + 1] +
                                  ([item.module] if item.module else [])) if item.level else (item.module or "")
                imports.append({"module": target, "line": item.lineno, "scope": owner,
                                "test_context": inside_test,
                                "names": [x.name for x in item.names]})
            elif isinstance(item, ast.Call):
                called = callee(item.func)
                calls.append({"expression": called, "line": item.lineno, "scope": owner,
                              "column": item.col_offset,
                              "test_context": inside_test,
                              "argument_count": len(item.args),
                              "keyword_names": [x.arg for x in item.keywords]})
                if called == "check" and item.args and isinstance(item.args[0], ast.Constant) and isinstance(item.args[0].value, str):
                    tests.append({"name": item.args[0].value, "line": item.lineno,
                                  "kind": "named_check", "scope": owner})
            elif isinstance(item, ast.Constant) and isinstance(item.value, str):
                value = item.value
                if re.fullmatch(r"[a-z][a-z0-9_.-]*/v[0-9]+", value):
                    literals.append({"kind": "record_type_literal", "value": value, "line": item.lineno})
                elif re.fullmatch(r"loop_engine(?:\.[a-z_][a-z0-9_]*)+", value):
                    literals.append({"kind": "module_reference_literal", "value": value, "line": item.lineno})
            walk(item, owner, inside_test)

    walk(tree)
    return {"module": module, "symbols": symbols, "imports": imports, "calls": calls,
            "tests": tests, "references": literals,
            "module_description": (ast.get_docstring(tree) or "").split("\n")[0]}


def collect(output: Path = OUTPUT) -> dict:
    source_before = source_identity(REPOSITORY)
    tracked = set(filter(None, git("ls-files", "-z").split("\0")))
    pending = set(filter(None, git("ls-files", "--others", "--exclude-standard", "-z").split("\0")))
    paths = sorted(tracked | {p for p in pending if not p.startswith("artifacts/")})
    records, parsed = [], {}
    for relative in paths:
        path = REPOSITORY / relative
        row = {"path": relative, "tracked": relative in tracked,
               "extension": path.suffix, "folder": path.parent.relative_to(REPOSITORY).as_posix(),
               "semantic_review": "not_yet_recorded", "inspection": "metadata_only"}
        if path.is_symlink():
            row["exclusion"] = "symbolic link not followed"
        elif not path.is_file():
            row["exclusion"] = "missing file or separate repository entry"
        elif path.name.startswith(".env") or path.name in SENSITIVE_NAMES or path.suffix in {".pem", ".key", ".p12"}:
            row["exclusion"] = "credential-bearing path excluded from content review"
        else:
            row["bytes"] = path.stat().st_size
            if path.suffix.lower() in BINARY_SUFFIXES or row["bytes"] > 4 * 1024 * 1024:
                row["exclusion"] = "binary or large artifact; inspect with the owning format when required"
            else:
                raw = path.read_bytes()
                row["sha256"] = hashlib.sha256(raw).hexdigest()
                try:
                    text = raw.decode("utf-8")
                    if "\x00" in text:
                        raise UnicodeError("binary content")
                    row["lines"] = len(text.splitlines())
                    row["inspection"] = "text_read_structurally"
                    if path.suffix == ".py":
                        try:
                            parsed[relative] = python_structure(relative, text)
                            row["inspection"] = "python_syntax_analyzed"
                        except SyntaxError as exc:
                            row["parse_error"] = f"{exc.msg} at line {exc.lineno}"
                    elif path.suffix == ".md":
                        row["headings"] = re.findall(r"^#{1,3} (.+)$", text, re.M)
                        row["local_reference_count"] = len(re.findall(r"\]\((?!https?://)[^)]+\)", text))
                    elif path.suffix in {".json", ".jsonl", ".yaml", ".yml", ".toml"}:
                        row["inspection"] = "structured_text_read"
                except UnicodeError:
                    row["exclusion"] = "non-UTF-8 or binary content"
        records.append(row)
    reviews = defaultdict(list)
    for review_path in sorted(output.glob("*-coverage.json")):
        review = json.loads(review_path.read_text("utf-8"))
        hashes = review.get("baseline_source_sha256", {})
        for path in review.get("files", []):
            reviews[path].append({"report": review["report"], "scope": review.get("scope", ""),
                                  "reviewed_sha256": hashes.get(path)})
    for row in records:
        if row["path"] in reviews:
            row["semantic_review"] = "focused_review_recorded"
            row["reviews"] = reviews[row["path"]]
            for review in row["reviews"]:
                expected = review["reviewed_sha256"]
                review["source_state"] = ("unchanged_since_review" if expected == row.get("sha256")
                                          else "changed_since_review" if expected else "check_report_scope")
    canonical = run_component_inventory(ComponentInventoryRequest(str(REPOSITORY / "src/loop_engine")))
    modules = {value["module"]: key for key, value in parsed.items() if value["module"]}
    entities = [{"id": "file:" + row["path"], "kind": "file", "path": row["path"]} for row in records]
    edges = []
    for path, value in parsed.items():
        source = "file:" + path
        for symbol in value["symbols"]:
            target = source + "#" + symbol["name"]
            entities.append({"id": target, "kind": symbol["kind"], "path": path, **symbol})
            edges.append({"source": source, "target": target, "relation": "declares", "evidence": "python_syntax"})
        for item in value["imports"]:
            names = [item["module"]] + [item["module"] + "." + name for name in item["names"]]
            resolved = sorted({modules[name] for name in names if name in modules})
            for imported in resolved:
                edges.append({"source": source, "target": "file:" + imported,
                              "relation": "test_import" if item["test_context"] else "source_import",
                              "line": item["line"], "scope": item["scope"], "evidence": "python_syntax"})
            if not resolved:
                target = "import:" + item["module"]
                entities.append({"id": target, "kind": "unresolved_import_name", "name": item["module"]})
                edges.append({"source": source, "target": target, "relation": "unresolved_import",
                              "line": item["line"], "test_context": item["test_context"],
                              "evidence": "import_name_not_a_distribution_identity"})
        for item in value["calls"]:
            target = source + ":call:" + str(item["line"]) + ":" + str(item["column"])
            entities.append({"id": target, "kind": "call_expression", "path": path, **item})
            caller = source + "#" + item["scope"] if item["scope"] else source
            edges.append({"source": caller, "target": target, "relation": "contains_call_expression",
                          "evidence": "syntax_only_dynamic_target_unresolved"})
        for item in value["references"]:
            if item["kind"] == "record_type_literal":
                target = "record_encoding:" + item["value"]
                entities.append({"id": target, "kind": "record_encoding_literal", "value": item["value"]})
                edges.append({"source": source, "target": target, "relation": "mentions_record_encoding",
                              "line": item["line"], "evidence": "literal_not_proof_of_current_read_or_write_support"})
            if item["kind"] == "module_reference_literal" and item["value"] in modules:
                edges.append({"source": source, "target": "file:" + modules[item["value"]],
                              "relation": "string_reference", "line": item["line"],
                              "evidence": "literal_reference_not_proof_of_dispatch"})
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    project = tomllib.loads((REPOSITORY / "pyproject.toml").read_text("utf-8"))
    requirements = {"base": project["project"]["dependencies"], **project["project"].get("optional-dependencies", {})}
    for group, specs in requirements.items():
        for spec in specs:
            target = f"distribution:{spec}"
            entities.append({"id": target, "kind": "distribution_requirement", "requirement": spec})
            edges.append({"source": "file:pyproject.toml", "target": target,
                          "relation": "declares_distribution_dependency", "extra": group,
                          "evidence": "project_metadata"})
    installed = metadata.packages_distributions()
    for row in tuple(entities):
        if row["kind"] != "unresolved_import_name":
            continue
        for distribution in installed.get(row["name"].split(".")[0], []):
            try:
                version = metadata.version(distribution)
            except metadata.PackageNotFoundError:
                version = None
            target = f"installed_distribution:{distribution}"
            entities.append({"id": target, "kind": "installed_distribution", "name": distribution,
                             "version": version})
            edges.append({"source": row["id"], "target": target,
                          "relation": "installed_distribution_candidate",
                          "evidence": "local_package_metadata_not_observed_import_or_registry_verification"})
    entities = list({row["id"]: row for row in entities}.values())
    population = hashlib.sha256(json.dumps([(r["path"], r.get("sha256"), r.get("bytes"))
                                          for r in records], separators=(",", ":")).encode()).hexdigest()
    entry_points = {name: {**reachability_report(name), "modules": sorted(
        module.removesuffix(".__init__") for module in reachable_from(entry))}
        for name, entry in LIVE_ENTRY_POINTS.items()}
    sections = report_sections(REPOSITORY)
    evidence_reference = sections["roadmap"].get("verification_report")
    evidence_path = REPOSITORY / evidence_reference if evidence_reference else output / "verification.json"
    if not evidence_path.resolve().is_relative_to(REPOSITORY.resolve()):
        raise ValueError("verification report must remain inside the repository")
    if source_before != source_identity(REPOSITORY):
        raise ValueError("package source changed during inventory; regenerate after writers settle")
    return {"record_type": "repository_architecture_audit/v1", "source_revision": git("rev-parse", "HEAD").strip(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **sections,
            "population_digest": population, "scope": "all tracked files plus pending non-artifact files",
            "exclusions": "ignored dependencies, generated runs, private configuration, and separate repositories are not silently treated as reviewed source",
            "files": records, "python": parsed, "canonical_inventory": canonical,
            "entry_points": entry_points,
            "check_evidence": check_evidence(REPOSITORY, evidence_path),
            "comparison": comparison_tables(REPOSITORY / "artifacts/continuation-research-2026-09-19/competitors.md"),
            "distribution": project["project"], "entities": entities, "relationships": edges,
            "limits": ["Source imports are not observed execution.",
                       "Call expressions are not resolved dynamic dispatch or dataflow.",
                       "Structural reading is not a semantic review of each file.",
                       "Declared component interactions remain declarations until tested."]}


def write_outputs(inventory: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    inventory["components"] = component_rows(inventory)
    inventory_bytes = json.dumps(inventory, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    (output / "inventory.json").write_bytes(inventory_bytes)
    inventory_archive = gzip.compress(inventory_bytes, mtime=0)
    (output / "inventory.json.gz").write_bytes(inventory_archive)
    graph = {key: inventory[key] for key in ("source_revision", "population_digest", "entities", "relationships", "limits")}
    graph_bytes = json.dumps(graph, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    (output / "graph.json").write_bytes(graph_bytes)
    graph_archive = gzip.compress(graph_bytes, mtime=0)
    (output / "graph.json.gz").write_bytes(graph_archive)
    module_edges = [row for row in inventory["relationships"]
                    if row["relation"] not in {"declares", "contains_call_expression"}]
    dot = ["digraph source_relationships {", '  graph [label="Source relationships, not a Loop execution graph", labelloc=t];']
    for edge in module_edges:
        dot.append(f"  {json.dumps(edge['source'])} -> {json.dumps(edge['target'])} [label={json.dumps(edge['relation'])}];")
    dot.append("}")
    (output / "architecture.dot").write_text("\n".join(dot) + "\n", "utf-8")
    lines = ["# File coverage", "", "Kind: generated structural coverage record.", "",
             f"Source: `{inventory['source_revision']}`. Population: `{inventory['population_digest']}`.", "",
             "Each row reports what was actually inspected. Structural parsing does not establish semantic correctness.", "",
             "| File | Structural inspection | Semantic review | Exclusion or parse finding |", "|---|---|---|---|"]
    for row in inventory["files"]:
        lines.append(f"| `{row['path']}` | {row['inspection']} | {row['semantic_review']} | {row.get('exclusion', row.get('parse_error', ''))} |")
    (output / "FILE-COVERAGE.md").write_text("\n".join(lines) + "\n", "utf-8")
    (output / "components.json").write_text(json.dumps({
        "record_type": "architecture_component_rows/v1", "population_digest": inventory["population_digest"],
        "evidence": inventory["check_evidence"], "rows": inventory["components"]},
        separators=(",", ":"), ensure_ascii=False), "utf-8")
    lines = ["# Component rows", "", "Kind: generated file-level build guide.", "",
             "One row per shipped Python file. Import closure, local checks, observed invocation, and review are separate facts.", "",
             "A record-type literal can occur in a reader, writer, or refusal test. It is not automatically a supported encoding.", "",
             "| File | Lines | Static import paths | Current recorded checks | Focused review |", "|---|---:|---|---|---|"]
    for row in inventory["components"]:
        checks = row["offline_checks"]
        measured = (f"{checks['passed']} passed, {checks['failed']} failed, {checks['not_tested']} not tested"
                    if checks else "not recorded for this source")
        lines.append(f"| `{row['path']}` | {row['lines']} | {', '.join(row['static_import_paths']) or 'not in measured closures'} | {measured} | {row['review']} |")
    (output / "COMPONENTS.md").write_text("\n".join(lines) + "\n", "utf-8")
    questions = []
    for path in sorted(output.glob("*-questions.json")):
        rows = json.loads(path.read_text("utf-8"))
        questions.extend({**row, "source_register": path.name}
                         for row in rows.get("questions", []))
    identities = [row["id"] for row in questions]
    if len(identities) != len(set(identities)):
        raise ValueError("question identifiers must remain distinct across reviews")
    (output / "questions.json").write_text(json.dumps({
        "record_type": "combined_architecture_questions/v1", "count": len(questions),
        "status_counts": dict(Counter(row["status"] for row in questions)),
        "meaning": "Questions refer to their dated review sources; later repairs do not rewrite the baseline.",
        "questions": questions}, indent=1, ensure_ascii=False), "utf-8")
    inventory["questions"] = questions
    counts = {"files": len(inventory["files"]), "python_files": len(inventory["python"]),
              "component_rows": len(inventory["components"]),
              "entities": len(inventory["entities"]), "relationships": len(inventory["relationships"]),
              "call_sites": sum(len(row["calls"]) for row in inventory["python"].values()),
              "test_declarations": sum(len(row["tests"]) for row in inventory["python"].values()),
              "focused_review_files": sum(row["semantic_review"] == "focused_review_recorded" for row in inventory["files"]),
              "review_questions": len(questions),
              "inspection": dict(Counter(row["inspection"] for row in inventory["files"]))}
    (output / "counts.json").write_text(json.dumps(counts, indent=2), "utf-8")
    from architecture_audit_view import render
    inventory["archives"] = {"inventory": base64.b64encode(inventory_archive).decode(),
                             "graph": base64.b64encode(graph_archive).decode()}
    (output / "loop-engine-system-map.html").write_text(render(inventory, counts), "utf-8")
    pointer = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0;url=loop-engine-system-map.html">'
        '<title>Loop Engine system map</title></head><body>'
        '<p>The complete system map is in one self-contained file: '
        '<a href="loop-engine-system-map.html">Open Loop Engine system map</a>.</p>'
        '</body></html>\n')
    for name in ("architecture.html", "mvp-client-server.html"):
        (output / name).write_text(pointer, "utf-8")
    print(json.dumps(counts, sort_keys=True))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    write_outputs(collect(args.output), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
