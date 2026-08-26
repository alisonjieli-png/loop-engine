"""Structural validation for the folder and catalog ontology.

The checks enforce agreement between four views of the same facts: the
folder tree on disk, README front matter, catalog manifests, and the
generated index. Each rule is canary-proven: the self-test plants an
invalid fixture, asserts the detector fires, and only then asserts the
live tree scans clean.
"""
from __future__ import annotations

import os
import re

import yaml

from .artifacts import ONTOLOGY_VERSION
from .catalog import MANIFEST_SCHEMA, UnifiedCatalog
from .folders import (
    FOLDER_ONTOLOGY,
    SEMANTIC_FOLDER_IDS,
    expected_front_matter,
    folder_path,
)

_README_BANNED = re.compile(
    r"\b(chronicles?|receipts?|stop[ _-]conditions?|root loops?"
    r"|children?|child loop)\b", re.IGNORECASE)


class OntologyCheckError(ValueError):
    """The package tree disagrees with the folder ontology."""


def _read_front_matter(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---"):
        raise OntologyCheckError(f"{path} has no front matter block")
    marker = text.find("\n---", 3)
    if marker < 0:
        raise OntologyCheckError(f"{path} has an unterminated front matter")
    document = yaml.safe_load(text[3:marker])
    if not isinstance(document, dict):
        raise OntologyCheckError(f"{path} front matter must be a mapping")
    return document


def _check_readme(folder_abs: str, rel: str, folder_id: str,
                  problems: list[str]) -> None:
    readme = os.path.join(folder_abs, "README.md")
    if not os.path.isfile(readme):
        problems.append(f"{rel}/README.md is missing")
        return
    try:
        matter = _read_front_matter(readme)
    except OntologyCheckError as exc:
        problems.append(str(exc))
        return
    expected = expected_front_matter(folder_id)
    for key, want in expected.items():
        got = matter.get(key)
        if got != want:
            problems.append(
                f"{rel}/README.md front matter {key}={got!r};"
                f" expected {want!r}")
    with open(readme, encoding="utf-8") as handle:
        body = handle.read()
    match = _README_BANNED.search(body)
    if match:
        problems.append(
            f"{rel}/README.md uses retired term {match.group(0)!r}")


def _check_python_free(folder_abs: str, rel: str,
                       problems: list[str]) -> None:
    for dirpath, _dirnames, filenames in os.walk(folder_abs):
        for name in filenames:
            if name.endswith(".py"):
                found = os.path.relpath(os.path.join(dirpath, name),
                                        folder_abs)
                problems.append(
                    f"{rel} must not contain Python modules; found {found}")


def run_checks(package_root: str | None = None) -> dict:
    """Validate the live package tree against the folder ontology."""
    if package_root is None:
        import loop_engine as package
        package_root = os.path.dirname(os.path.abspath(package.__file__))
    problems: list[str] = []
    for folder_id in SEMANTIC_FOLDER_IDS:
        spec = FOLDER_ONTOLOGY[folder_id]
        rel = folder_path(folder_id)
        folder_abs = os.path.join(package_root, rel)
        if not os.path.isdir(folder_abs):
            problems.append(f"semantic folder {rel}/ is missing")
            continue
        _check_readme(folder_abs, rel, folder_id, problems)
        if spec.requires_manifest:
            manifest = os.path.join(folder_abs, "manifest.yaml")
            if not os.path.isfile(manifest):
                problems.append(f"{rel}/manifest.yaml is missing")
            else:
                with open(manifest, encoding="utf-8") as handle:
                    document = yaml.safe_load(handle)
                if (not isinstance(document, dict)
                        or document.get("schema") != MANIFEST_SCHEMA):
                    problems.append(
                        f"{rel}/manifest.yaml must declare schema "
                        f"{MANIFEST_SCHEMA}")
        if spec.python_free:
            _check_python_free(folder_abs, rel, problems)
    index_path = os.path.join(package_root, "ontology", "index.json")
    snapshot = UnifiedCatalog(package_root=package_root).discover()
    problems.extend(snapshot.problems)
    generated = snapshot.index_json() + "\n"
    if not os.path.isfile(index_path):
        problems.append("ontology/index.json has not been generated")
    else:
        with open(index_path, encoding="utf-8") as handle:
            saved = handle.read()
        if saved != generated:
            problems.append(
                "ontology/index.json is stale; regenerate it with"
                " --write-ontology-index")
    return {
        "record_type": "ontology_checks/v1",
        "package_root": package_root,
        "problems": problems,
        "passed": not problems,
    }


def self_test() -> dict:
    """Canary-prove every detector, then assert the live tree is clean."""
    import shutil
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "pkg")
        shutil.copytree(os.path.dirname(os.path.abspath(__file__)),
                        os.path.join(root, "ontology"))
        for fid in SEMANTIC_FOLDER_IDS:
            os.makedirs(os.path.join(root, folder_path(fid)),
                        exist_ok=True)

        broken = run_checks(root)
        check("missing_readmes_are_detected",
              any("README.md is missing" in p for p in broken["problems"]),
              f"{len(broken['problems'])} problems")

        readme_dir = os.path.join(root, folder_path("governance"))
        with open(os.path.join(readme_dir, "README.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("# governance\n\nNo front matter here.\n")
        no_matter = run_checks(root)
        check("front_matter_is_required",
              any("no front matter" in p for p in no_matter["problems"]))

        with open(os.path.join(readme_dir, "README.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("---\nfolder_id: governance\nparent:"
                         " wrong_parent\nontology_version:"
                         f" {ONTOLOGY_VERSION}\n---\n\n# governance\n")
        wrong = run_checks(root)
        check("wrong_parent_is_detected",
              any("front matter parent='wrong_parent'" in p
                  for p in wrong["problems"]),
              str(wrong["problems"])[:200])

        with open(os.path.join(readme_dir, "README.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("---\nfolder_id: governance\nparent:"
                         " governance\nontology_version:"
                         f" {ONTOLOGY_VERSION}\n---\n\n"
                         "Uses the retired word chronicle.\n")
        banned = run_checks(root)
        check("retired_terms_in_readme_are_detected",
              any("retired term" in p for p in banned["problems"]))

        os.remove(os.path.join(readme_dir, "README.md"))
        py_dir = os.path.join(root, folder_path("kernel.executor"))
        os.makedirs(py_dir, exist_ok=True)
        with open(os.path.join(py_dir, "rogue.py"), "w",
                  encoding="utf-8") as handle:
            handle.write("\n")
        rogue = run_checks(root)
        check("python_modules_in_python_free_folders_are_detected",
              any("must not contain Python" in p
                  for p in rogue["problems"]))

    live = run_checks()
    check("live_tree_passes_all_checks", live["passed"],
          "; ".join(live["problems"])[:400])
    return {"tests": results}
