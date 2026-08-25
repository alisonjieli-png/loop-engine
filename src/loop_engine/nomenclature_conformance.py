"""Conformance checks for retired source terminology.

The configured terms and narrow upstream protocol exceptions live in
``forbidden_paths.json`` so the scanner does not hide policy in code.
"""
from __future__ import annotations

import os
import re


_TEXT_SUFFIXES = (".py", ".html", ".json", ".jsonl", ".md")


def retired_nomenclature_violations(root: str, policy: dict) -> list[dict]:
    """Return every configured retired term outside an exact exception."""
    terms = tuple(str(term) for term in policy.get("terms", ()))
    excluded = set(policy.get("excluded_files", ()))
    allowed = {str(path): tuple(fragments) for path, fragments
               in policy.get("allowed_fragments", {}).items()}
    violations = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames
                       if name not in ("__pycache__", "build", "dist",
                                       "evidence")]
        for filename in filenames:
            if not filename.endswith(_TEXT_SUFFIXES):
                continue
            path = os.path.join(directory, filename)
            relative = os.path.relpath(path, root)
            if relative in excluded:
                continue
            for line_number, line in enumerate(
                    open(path, encoding="utf-8", errors="replace"), 1):
                folded = line.casefold()
                permitted = tuple(fragment.casefold()
                                  for fragment in allowed.get(relative, ()))
                for term in terms:
                    if re.search(re.escape(term), folded, re.IGNORECASE) \
                            and not any(fragment in folded
                                        for fragment in permitted):
                        violations.append({
                            "rule": "retired_source_nomenclature",
                            "file": relative, "line": line_number,
                            "detail": f"retired term {term!r}"})
    return violations
