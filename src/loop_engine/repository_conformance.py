"""Repository conformance harness: file-by-file, symbol-by-symbol, relationship-by-relationship.

This module indexes every production Python file, class, function, and
import; validates the one-Loop-runtime invariant, import boundaries, and
reference integrity; and canary-proves every detector against
intentionally bad fixtures before judging the live tree.

The conformance graph is a disposable development artifact. The
authoritative checks are the detectors and their canary proofs. A
detector that cannot be made to fire on a planted violation is not
trusted against the live tree.
"""
from __future__ import annotations

import ast
import hashlib
import os

import yaml

_PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PACKAGE_ROOT))

#: Node is an abstract category. Active first-party Node classes are forbidden.
ALLOWED_NODE_CLASSES = frozenset()

#: Roots production code must never import.
FORBIDDEN_IMPORT_ROOTS = ("devtools", "tests", "examples", "benchmarks")

#: Manifest schema the intelligence bundles must declare.
MANIFEST_SCHEMA = "catalog_manifest/v1"


class RepositoryConformanceError(ValueError):
    """The repository violates a conformance rule."""


def _py_files(root: str) -> list[str]:
    """Every Python file under root, excluding caches."""
    found = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if filename.endswith(".py"):
                found.append(os.path.join(directory, filename))
    return sorted(found)


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_files(root: str) -> list[dict]:
    """One record per production file: hash, symbols, imports, docstring."""
    records = []
    for path in _py_files(root):
        relative = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            tree = ast.parse(open(path, encoding="utf-8").read(), path)
        except (OSError, SyntaxError) as exc:
            records.append({"path": relative, "parse_error": str(exc)})
            continue
        classes = [node.name for node in ast.walk(tree)
                   if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree)
                     if isinstance(node, (ast.FunctionDef,
                                          ast.AsyncFunctionDef))]
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        docstring = ast.get_docstring(tree)
        records.append({
            "path": relative,
            "content_hash": _sha256_file(path),
            "classes": sorted(set(classes)),
            "functions": sorted(set(functions)),
            "imports": sorted(set(imports)),
            "has_module_docstring": bool(docstring),
        })
    return records


def node_class_violations(root: str) -> list[dict]:
    """Classes named Node or ending in Node outside the allowlist."""
    violations = []
    for path in _py_files(root):
        relative = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            tree = ast.parse(open(path, encoding="utf-8").read(), path)
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name == "Node" or (
                    node.name.endswith("Node")
                    and node.name not in ALLOWED_NODE_CLASSES):
                violations.append({
                    "rule": "node_class",
                    "file": relative, "line": node.lineno,
                    "class": node.name,
                    "detail": "Node is conceptual; executable work uses Loop"})
    return violations


def import_boundary_violations(root: str) -> list[dict]:
    """Production files importing development-only roots."""
    violations = []
    for path in _py_files(root):
        relative = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            tree = ast.parse(open(path, encoding="utf-8").read(), path)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                        violations.append({
                            "rule": "import_boundary", "file": relative,
                            "line": node.lineno, "import": alias.name,
                            "detail": "production code must not import "
                                      "development-only roots"})
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                    violations.append({
                        "rule": "import_boundary", "file": relative,
                        "line": node.lineno, "import": node.module,
                        "detail": "production code must not import "
                                  "development-only roots"})
    return violations


def _manifest_paths(root: str) -> list[str]:
    found = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        relative_dir = os.path.relpath(directory, root).replace(os.sep, "/")
        if not relative_dir.startswith("intelligence"):
            continue
        for filename in filenames:
            if filename in ("manifest.yaml", "manifest.json"):
                found.append(os.path.join(directory, filename))
    return sorted(found)


def reference_violations(root: str) -> list[dict]:
    """Manifest payloads and code references that do not resolve."""
    violations = []
    for path in _manifest_paths(root):
        relative = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            document = yaml.safe_load(open(path, encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            violations.append({"rule": "manifest", "file": relative,
                               "detail": f"unreadable manifest: {exc}"})
            continue
        if not isinstance(document, dict):
            violations.append({"rule": "manifest", "file": relative,
                               "detail": "manifest must be a mapping"})
            continue
        if document.get("schema") != MANIFEST_SCHEMA:
            violations.append({"rule": "manifest", "file": relative,
                               "detail": f"manifest must declare schema "
                                         f"{MANIFEST_SCHEMA}"})
            continue
        manifest_dir = os.path.dirname(path)
        for obj in document.get("objects", []):
            payload = obj.get("payload", "")
            if isinstance(payload, str) and payload.startswith("file:"):
                target = os.path.normpath(os.path.join(
                    manifest_dir, payload[len("file:"):]))
                if not target.startswith(os.path.abspath(manifest_dir)
                                          + os.sep):
                    violations.append({
                        "rule": "reference", "file": relative,
                        "detail": f"payload escapes its root: {payload!r}"})
                    continue
                if not os.path.isfile(target):
                    violations.append({
                        "rule": "reference", "file": relative,
                        "detail": f"payload is missing: {payload!r}"})
                    continue
                if obj.get("content_digest") and \
                        _sha256_file(target) != obj["content_digest"]:
                    violations.append({
                        "rule": "reference", "file": relative,
                        "detail": f"payload digest mismatch: {payload!r}"})
            elif isinstance(payload, str) and payload.startswith("code_ref:"):
                import importlib
                module_name = payload[len("code_ref:"):].rsplit(".", 1)[0]
                try:
                    importlib.import_module(module_name)
                except ImportError as exc:
                    violations.append({
                        "rule": "reference", "file": relative,
                        "detail": f"code_ref does not resolve: "
                                  f"{payload!r} ({exc})"})
    return violations


def run_repository_conformance(root: str | None = None) -> dict:
    """Index the tree and run every detector against it."""
    base = root or _PACKAGE_ROOT
    problems: list[dict] = []
    problems.extend(node_class_violations(base))
    problems.extend(import_boundary_violations(base))
    problems.extend(reference_violations(base))
    files = index_files(base)
    unparsed = [f for f in files if "parse_error" in f]
    for record in unparsed:
        problems.append({"rule": "parse", "file": record["path"],
                         "detail": record["parse_error"]})
    return {
        "record_type": "repository_conformance/v1",
        "files_indexed": len(files),
        "problems": problems,
        "passed": not problems,
    }


def self_test() -> dict:
    """Canary-prove every detector, then assert the live tree is clean."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        # Canary 1: a forbidden node-named class must be detected.
        bad_node = os.path.join(tmp, "bad_node.py")
        with open(bad_node, "w", encoding="utf-8") as handle:
            handle.write("class ConfigurationNode:\n    pass\n")
        check("node_class_detector_fires_on_planted_violation",
              any(v["class"] == "ConfigurationNode"
                  for v in node_class_violations(tmp)),
              "a planted ConfigurationNode must be detected")

        # Canary 2: a production import of a dev root must be detected.
        bad_import = os.path.join(tmp, "bad_import.py")
        with open(bad_import, "w", encoding="utf-8") as handle:
            handle.write("import devtools.architecture\n")
        check("import_boundary_detector_fires_on_planted_violation",
              any(v["import"] == "devtools.architecture"
                  for v in import_boundary_violations(tmp)),
              "a planted devtools import must be detected")

        # Canary 3: a manifest with a missing payload must be detected.
        bad_manifest_dir = os.path.join(tmp, "intelligence", "context",
                                        "core")
        os.makedirs(bad_manifest_dir)
        with open(os.path.join(bad_manifest_dir, "manifest.yaml"), "w",
                  encoding="utf-8") as handle:
            yaml.safe_dump({
                "schema": MANIFEST_SCHEMA,
                "objects": [{"id": "x", "version": "1.0.0",
                             "artifact_kind": "intelligence_record",
                             "lifecycle": "registered",
                             "payload": "file:missing.jsonl"}],
            }, handle)
        check("reference_detector_fires_on_missing_payload",
              any("payload is missing" in v["detail"]
                  for v in reference_violations(tmp)),
              "a manifest pointing at a missing payload must be detected")

        # Canary 4: a manifest with a traversal payload must be detected.
        with open(os.path.join(bad_manifest_dir, "manifest.yaml"), "w",
                  encoding="utf-8") as handle:
            yaml.safe_dump({
                "schema": MANIFEST_SCHEMA,
                "objects": [{"id": "x", "version": "1.0.0",
                             "artifact_kind": "intelligence_record",
                             "lifecycle": "registered",
                             "payload": "file:../../etc/passwd"}],
            }, handle)
        check("reference_detector_fires_on_traversal_payload",
              any("escapes its root" in v["detail"]
                  for v in reference_violations(tmp)),
              "a manifest payload escaping its root must be detected")

        # Canary 5: a file without a module docstring must be indexed as such.
        with open(bad_node, "w", encoding="utf-8") as handle:
            handle.write("x = 1\n")
        records = index_files(tmp)
        check("file_indexer_records_docstring_absence",
              any(r["path"] == "bad_node.py"
                  and not r["has_module_docstring"] for r in records),
              "a file without a docstring must be indexed as missing one")

    live = run_repository_conformance()
    check("live_tree_passes_repository_conformance", live["passed"],
          str(live["problems"])[:400])
    check("live_tree_indexes_every_file",
          live["files_indexed"] > 100,
          f"indexed {live['files_indexed']} files")
    return {"tests": results}
