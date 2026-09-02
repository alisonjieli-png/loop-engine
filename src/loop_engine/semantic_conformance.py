"""Machine enforcement for the repository semantic data dictionary.

The dictionary is the vocabulary authority. This checker proves that every
registered term has one category and authority, source symbols exist, aliases
cannot become competing canonical terms, runtime identity is singular, and
parameterization or inheritance decisions are explicit.
"""
from __future__ import annotations

import ast
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

_PACKAGE_ROOT = Path(__file__).resolve().parent
_REPOSITORY_ROOT = _PACKAGE_ROOT.parent.parent
_TERMINOLOGY_PATH = _REPOSITORY_ROOT / "terminology.yaml"
_PROJECTION_PATH = _PACKAGE_ROOT / "data" / "semantic_data_dictionary.yaml"
_RENDERED_PATH = (_REPOSITORY_ROOT / "docs" / "architecture"
                  / "SEMANTIC-IDENTITY-DICTIONARY.md")
_REQUIRED_ENTRY_FIELDS = frozenset({
    "term_id", "canonical_name", "primary_category", "definition",
    "source_of_truth", "source_symbol", "public_or_internal",
    "runtime_or_passive", "authoritative_or_projection", "versioning",
    "related_terms", "difference_from_neighbors",
    "parameterization_decision", "composition_decision",
    "inheritance_decision", "storage_authority", "lifecycle",
    "legacy_aliases", "migration", "examples", "negative_examples",
    "conformance_rules",
})


class SemanticConformanceError(ValueError):
    """The semantic dictionary or a registered identity is invalid."""


def load_semantic_dictionary(path: Path | None = None) -> dict[str, Any]:
    """Load terminology authority in a checkout or its installed projection."""
    selected = path or (_TERMINOLOGY_PATH if _TERMINOLOGY_PATH.is_file()
                        else _PROJECTION_PATH)
    try:
        document = yaml.safe_load(selected.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SemanticConformanceError(
            f"cannot read semantic dictionary: {exc}") from exc
    if not isinstance(document, dict):
        raise SemanticConformanceError("semantic authority must be a mapping")
    if document.get("semantic_schema_version") == "semantic_constitution/v1":
        return {
            "schema_version": "semantic_constitution/v1",
            "dictionary_version": "1.0.0",
            "categories": document.get("semantic_categories"),
            "decision_rules": document.get("semantic_decision_rules"),
            "entries": document.get("semantic_terms"),
        }
    if document.get("schema_version") != \
            "semantic_data_dictionary_projection/v1":
        raise SemanticConformanceError(
            "semantic authority or installed projection has an invalid schema")
    return document


def _source_path(module: str) -> Path | None:
    prefix = "loop_engine."
    if not module.startswith(prefix):
        return None
    relative = module[len(prefix):].replace(".", "/")
    module_file = _PACKAGE_ROOT / f"{relative}.py"
    if module_file.is_file():
        return module_file
    package_file = _PACKAGE_ROOT / relative / "__init__.py"
    return package_file if package_file.is_file() else None


def _top_level_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            result.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) \
                else (node.target,)
            result.update(target.id for target in targets
                          if isinstance(target, ast.Name))
    return result


def _source_problem(entry: dict[str, Any]) -> str:
    source = entry.get("source_symbol")
    if source is None:
        return ""
    if not isinstance(source, str) or source.count(":") != 1:
        return "source must use module:Symbol or null"
    module, symbol = source.split(":", 1)
    path = _source_path(module)
    if path is None:
        return f"source module does not exist: {module}"
    try:
        symbols = _top_level_symbols(path)
    except (OSError, SyntaxError) as exc:
        return f"source module cannot be parsed: {exc}"
    if symbol not in symbols:
        return f"source symbol does not exist: {source}"
    return ""


def semantic_dictionary_violations(
        document: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Return deterministic dictionary, authority, and source violations."""
    data = document or load_semantic_dictionary()
    categories = data.get("categories")
    rules = data.get("decision_rules")
    entries = data.get("entries")
    violations: list[dict[str, str]] = []
    if not isinstance(categories, dict) or not categories:
        return [{"rule": "categories", "detail": "categories are required"}]
    if not isinstance(rules, dict) or set(rules) != {
            "parameterize", "compose", "separate_class",
            "separate_function", "separate_loop", "inherit",
            "retain_typed_data_class"}:
        violations.append({
            "rule": "decision_rules",
            "detail": "all six parameterization decisions are required",
        })
    if not isinstance(entries, list) or not entries:
        return [*violations, {
            "rule": "entries", "detail": "dictionary entries are required"}]
    terms: list[str] = []
    authorities: list[str] = []
    aliases: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            violations.append({"rule": "entry_shape",
                               "detail": f"entry {index} is not a mapping"})
            continue
        missing = _REQUIRED_ENTRY_FIELDS - set(entry)
        extra = set(entry) - _REQUIRED_ENTRY_FIELDS
        if missing or extra:
            violations.append({
                "rule": "entry_shape", "term": str(entry.get("term", index)),
                "detail": f"missing={sorted(missing)} extra={sorted(extra)}",
            })
            continue
        term = entry["canonical_name"]
        if not isinstance(term, str) or not term.strip():
            violations.append({"rule": "term", "detail": f"entry {index}"})
            continue
        terms.append(term)
        if entry["primary_category"] not in categories:
            violations.append({"rule": "category", "term": term,
                               "detail": str(entry["primary_category"])})
        authority = entry["source_of_truth"]
        if not isinstance(authority, str) or not authority.strip():
            violations.append({"rule": "authority", "term": term,
                               "detail": "one authority is required"})
        else:
            authorities.append(authority)
        if not isinstance(entry["definition"], str) \
                or not entry["definition"].strip():
            violations.append({"rule": "meaning", "term": term,
                               "detail": "plain-language meaning is required"})
        if not isinstance(entry["parameterization_decision"], str) \
                or not entry["parameterization_decision"].strip():
            violations.append({"rule": "parameterization", "term": term,
                               "detail": "decision is required"})
        if not isinstance(entry["inheritance_decision"], str) \
                or not entry["inheritance_decision"].strip():
            violations.append({"rule": "inheritance", "term": term,
                               "detail": "decision is required"})
        if not isinstance(entry["legacy_aliases"], list) or any(
                not isinstance(alias, str) or not alias.strip()
                for alias in entry["legacy_aliases"]):
            violations.append({"rule": "aliases", "term": term,
                               "detail": "aliases must be exact strings"})
        else:
            aliases.extend(entry["legacy_aliases"])
        source_problem = _source_problem(entry)
        if source_problem:
            violations.append({"rule": "source", "term": term,
                               "detail": source_problem})
    for term, count in Counter(terms).items():
        if count != 1:
            violations.append({"rule": "duplicate_term", "term": term,
                               "detail": f"count={count}"})
    for alias, count in Counter(aliases).items():
        if count != 1:
            violations.append({"rule": "duplicate_alias", "term": alias,
                               "detail": f"count={count}"})
        if alias in terms:
            violations.append({"rule": "alias_is_canonical", "term": alias,
                               "detail": "alias competes with a canonical term"})
    runtime_entries = [entry for entry in entries
                       if isinstance(entry, dict)
                       and entry.get("primary_category") == "runtime"]
    if [entry.get("canonical_name") for entry in runtime_entries] != ["Loop"]:
        violations.append({"rule": "runtime_authority",
                           "detail": "Loop must be the sole runtime"})
    return violations


def runtime_identity_violations() -> list[dict[str, str]]:
    """Prove Loop is the one sealed runtime and LoopNode is absent."""
    from .loop.recursive_loop import Loop
    import loop_engine
    violations: list[dict[str, str]] = []
    if Loop.__name__ != "Loop":
        violations.append({"rule": "runtime_name",
                           "detail": Loop.__name__})
    if Loop.__subclasses__():
        violations.append({"rule": "runtime_subclass",
                           "detail": str(Loop.__subclasses__())})
    if "LoopNode" in getattr(loop_engine, "__all__", ()) \
            or hasattr(loop_engine, "LoopNode"):
        violations.append({"rule": "public_legacy_runtime_alias",
                           "detail": "LoopNode is visible at package root"})
    loop_locations: list[str] = []
    loop_node_locations: list[str] = []
    for path in _PACKAGE_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "Loop":
                loop_locations.append(str(path.relative_to(_PACKAGE_ROOT)))
            if isinstance(node, ast.ClassDef) and node.name == "LoopNode":
                loop_node_locations.append(
                    str(path.relative_to(_PACKAGE_ROOT)))
    if loop_locations != ["loop/recursive_loop.py"]:
        violations.append({"rule": "runtime_class_count",
                           "detail": str(loop_locations)})
    if loop_node_locations:
        violations.append({"rule": "active_loop_node_class",
                           "detail": str(loop_node_locations)})
    return violations


def semantic_source_violations(
        root: Path | None = None) -> list[dict[str, str]]:
    """Detect active retired runtime names and legacy record emission."""
    selected = root or _PACKAGE_ROOT
    violations: list[dict[str, str]] = []
    compatibility_files = {
        "ontology/loop_node.py", "ontology/loop_definition_record.py"}
    for path in selected.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(selected).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name == "LoopNode":
                    violations.append({"rule": "active_loop_node_class",
                                       "detail": f"{relative}:{node.lineno}"})
                elif node.name == "Loop" \
                        and relative != "loop/recursive_loop.py":
                    violations.append({"rule": "second_loop_runtime",
                                       "detail": f"{relative}:{node.lineno}"})
                elif node.name.endswith("Node"):
                    violations.append({"rule": "active_node_class",
                                       "detail": f"{relative}:{node.lineno}"})
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) \
                    else (node.target,)
                if any(isinstance(target, ast.Name)
                       and target.id == "LoopNode" for target in targets):
                    violations.append({"rule": "active_loop_node_alias",
                                       "detail": f"{relative}:{node.lineno}"})
        if relative in compatibility_files:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                pairs = zip(node.keys, node.values, strict=True)
                if any(isinstance(key, ast.Constant) and key.value == "kind"
                       and isinstance(value, ast.Constant)
                       and value.value == "loop_node" for key, value in pairs):
                    violations.append({"rule": "legacy_loop_node_emission",
                                       "detail": f"{relative}:{node.lineno}"})
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "kind" \
                            and isinstance(keyword.value, ast.Constant) \
                            and keyword.value.value == "loop_node":
                        violations.append({"rule": "legacy_loop_node_emission",
                                           "detail": f"{relative}:{node.lineno}"})
    return violations


def semantic_projection_violations() -> list[dict[str, str]]:
    """Prove the installed projection exactly matches terminology authority."""
    if not _TERMINOLOGY_PATH.is_file() or not _PROJECTION_PATH.is_file():
        return []
    source = load_semantic_dictionary(_TERMINOLOGY_PATH)
    try:
        projection_raw = yaml.safe_load(
            _PROJECTION_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [{"rule": "semantic_projection", "detail": str(exc)}]
    comparable = {
        "schema_version": "semantic_data_dictionary_projection/v1",
        "generated_from": "terminology.yaml",
        "dictionary_version": source["dictionary_version"],
        "categories": source["categories"],
        "decision_rules": source["decision_rules"],
        "entries": source["entries"],
    }
    digest = hashlib.sha256(json.dumps(
        comparable, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    expected = {**comparable, "source_digest": digest}
    if projection_raw != expected:
        return [{"rule": "semantic_projection",
                 "detail": "installed projection differs from terminology.yaml"}]
    return []


def render_data_dictionary(document: dict[str, Any] | None = None) -> str:
    """Render the normative YAML dictionary as a stable reader-facing table."""
    data = document or load_semantic_dictionary()
    from ._conformance_scan import _rules
    retired_public_terms = {
        str(term).casefold() for term in _rules().get(
            "retired_source_nomenclature", {}).get("terms", ())}
    lines = [
        "# Loop Engine data dictionary", "",
        "This file is generated from the semantic constitution in "
        "`terminology.yaml`. The packaged YAML is a verified install-time "
        "projection. The dictionary records "
        "one meaning, category, authority, and customization decision for "
        "each material public concept.", "", "## Decision rule", "",
        "| Situation | Required representation |",
        "|---|---|",
    ]
    rule_labels = {
        "parameterize": "Values or behavior settings vary",
        "compose": "Algorithm or provider varies behind one contract",
        "separate_class": "State, lifecycle, protocol, or authority differs",
        "separate_function": "Stateless deterministic operation",
        "separate_loop": "Work needs independent governance",
        "inherit": "A truly substitutable subtype is unavoidable",
        "retain_typed_data_class": "A passive typed contract is cohesive",
    }
    for key, rule in data["decision_rules"].items():
        lines.append(f"| {rule_labels[key]} | {rule['action']} |")
    lines.extend(["", "## Semantic categories", "",
                  "| Category | Meaning | Preferred suffixes |",
                  "|---|---|---|"])
    for name, category in data["categories"].items():
        suffixes = ", ".join(category.get("preferred_suffixes", ())) or "none"
        lines.append(f"| `{name}` | {category['definition']} | {suffixes} |")
    lines.extend(["", "## Public concepts", "",
                  "| Term | Category | Meaning | Authority | Customization | Inheritance | Aliases |",
                  "|---|---|---|---|---|---|---|"])
    for entry in data["entries"]:
        aliases = ", ".join(
            f"`{alias}`" for alias in entry["legacy_aliases"]
            if alias.casefold() not in retired_public_terms) or "none"
        lines.append(
            f"| `{entry['canonical_name']}` | "
            f"`{entry['primary_category']}` | "
            f"{entry['definition']} | `{entry['source_of_truth']}` | "
            f"{entry['parameterization_decision']} | "
            f"{entry['inheritance_decision']} | "
            f"{aliases} |")
    lines.extend(["", "## Compatibility rule", "",
                  "An alias must resolve to the same object or be accepted only "
                  "by an exact immutable-record reader. It cannot own execution, "
                  "persistence, promotion, settings, or graph authority.", ""])
    return "\n".join(lines)


def rendered_dictionary_is_fresh() -> bool:
    """Return true outside a checkout or when the committed rendering matches."""
    if not _RENDERED_PATH.exists():
        return not _TERMINOLOGY_PATH.exists()
    return _RENDERED_PATH.read_text(encoding="utf-8") == render_data_dictionary()


def semantic_conformance_report() -> dict[str, Any]:
    """Return the complete semantic gate report."""
    violations = [*semantic_dictionary_violations(),
                  *semantic_projection_violations(),
                  *runtime_identity_violations(),
                  *semantic_source_violations()]
    if not rendered_dictionary_is_fresh():
        violations.append({"rule": "data_dictionary_freshness",
                           "detail": str(_RENDERED_PATH)})
    return {
        "record_type": "semantic_conformance/v1",
        "violations": violations,
        "passed": not violations,
    }


def self_test() -> dict[str, Any]:
    """Canary-prove dictionary validation and judge the live repository."""
    tests: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    document = load_semantic_dictionary()
    check("dictionary_schema_loads", bool(document.get("entries")))
    duplicate = {**document, "entries": [*document["entries"],
                                          document["entries"][0]]}
    planted = semantic_dictionary_violations(duplicate)
    check("duplicate_term_and_alias_canary_fires",
          any(item["rule"] == "duplicate_term" for item in planted))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "bad.py").write_text(
            "class LoopNode: pass\nLoopNode = object\n"
            "legacy = {'kind': 'loop_node'}\nclass Loop: pass\n",
            encoding="utf-8")
        mutations = {item["rule"] for item in
                     semantic_source_violations(root)}
    check("runtime_and_legacy_emission_mutations_are_detected",
          {"active_loop_node_class", "active_loop_node_alias",
           "legacy_loop_node_emission", "second_loop_runtime"}
          <= mutations, str(sorted(mutations)))
    live = semantic_conformance_report()
    check("live_semantic_contract_passes", live["passed"],
          str(live["violations"])[:800])
    return {"tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests), "all_passed": all(
                item["passed"] for item in tests)}


__all__ = (
    "SemanticConformanceError", "load_semantic_dictionary",
    "render_data_dictionary", "runtime_identity_violations",
    "semantic_conformance_report", "semantic_dictionary_violations",
    "semantic_source_violations",
)
