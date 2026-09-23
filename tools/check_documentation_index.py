"""Check documentation sources, closed index routes, rendered bytes and terminology.

This development check does not serve files or grant runtime authority. The
customer table in docs/guides/README.md owns which guides must be reachable.
The versioned index owns their presentation; WEB_ASSETS owns served routes.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

import check_service_documentation as facts
import yaml
from build_documentation_index import (
    INDEX_FILE,
    PAGE_TABLE_MODULE,
    PAGES_FILE,
    WEB_ASSETS,
    DocumentationBuildError,
    build,
    differences,
    index_pages,
    load_index,
    serialize,
)

from loop_engine.nomenclature_conformance import resolved_terms

VERSION = "documentation_index_check/v1"
GUIDES = "docs/guides/README.md"


def route_files(root):
    """Read the literal address table without importing or running application code."""
    tree = ast.parse((root / PAGE_TABLE_MODULE).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "WEB_ASSETS" for target in node.targets):
            return {ast.literal_eval(key): ast.literal_eval(value.elts[0])
                    for key, value in zip(node.value.keys, node.value.values)}
    raise DocumentationBuildError("WEB_ASSETS address table is absent")


def check(root: Path) -> dict:
    findings, checked = [], 0

    def refuse(subject, kind, note):
        findings.append({"subject": subject, "kind": kind, "note": note})

    try:
        index = load_index(root)
    except DocumentationBuildError as error:
        return {"record_type": VERSION, "pages": 0, "facts_checked": 0,
                "findings": [{"subject": INDEX_FILE, "kind": "index", "note": str(error)}], "passed": False}
    pages = index_pages(index)
    paths = tuple(page["repository_path"] for page in pages if page.get("repository_path"))
    section = (root / GUIDES).read_text().split("## For a paying customer of the hosted service", 1)[1].split("\n## ", 1)[0]
    required = {"docs/guides/" + name for line in section.splitlines() if line.startswith("| [")
                for name in re.findall(r"\]\(([a-z0-9-]+\.md)\)", line)}
    if set(paths) != required:
        refuse(GUIDES, "customer_coverage", str(sorted(set(paths) ^ required)))
    if set(paths) != set(facts.DOCUMENTED_PAGES):
        refuse(INDEX_FILE, "fact_coverage", "source-fact check and index name different guides")
    routes = route_files(root)
    expected = {"/docs": "index.html", "/assets/documentation-index.json": "documentation-index.json",
                "/assets/documentation.js": "documentation.js", "/assets/documentation.css": "documentation.css"}
    client = (root / WEB_ASSETS / "service.js").read_text()
    match = re.search(r"const routeNames = (\{[^;]+\});", client)
    views = json.loads(match.group(1)) if match else {}
    for page in pages:
        expected[page["address"]] = "index.html"
        for alias in page.get("aliases", []):
            expected[alias] = "index.html"
            if not page.get("body") and views.get(alias) != views.get(page["address"]):
                refuse(alias, "alias_view", "alias does not select the same application view")
        if page.get("body"):
            expected[page["body"]] = "docs/" + page["id"] + ".html"
    for address, filename in expected.items():
        if routes.get(address) != filename or not (root / WEB_ASSETS / filename).is_file():
            refuse(address, "route", "route does not serve the declared packaged file")
    for address in routes:
        if address.startswith(("/docs/", "/assets/docs/")) and address not in expected:
            refuse(address, "unlisted_route", "documentation route is not named by the index")
    try:
        record, bodies = build(root)
    except DocumentationBuildError as error:
        refuse(PAGES_FILE, "build", str(error))
        bodies = {}
    else:
        for path in differences(root, serialize(record), bodies):
            refuse(path, "stale_pages", "run tools/build_documentation_index.py")
    contract = yaml.safe_load((root / "terminology.yaml").read_text())
    texts = {INDEX_FILE: json.dumps(index), **bodies}
    for name, term in resolved_terms(contract).items():
        if "website_documentation_view" not in (term.get("must_not_appear") or ()):
            continue
        expression = re.compile(term.get("pattern") or re.escape(name),
                                0 if term.get("case_sensitive", True) else re.IGNORECASE)
        for path, text in texts.items():
            if expression.search(text):
                refuse(path, "terminology", "forbidden documentation term: " + name)
    source = facts.check(root, pages=paths)
    checked += source["facts_checked"]
    for finding in source["findings"]:
        refuse(finding["page"], finding["kind"], finding["value"] + ": " + finding["note"])
    return {"record_type": VERSION, "pages": len(pages), "sections": len(index["sections"]),
            "facts_checked": checked, "findings": findings, "passed": not findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = check(Path(args.repository).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
