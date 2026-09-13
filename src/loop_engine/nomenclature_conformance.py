"""Conformance checks for retired source terminology.

The configured terms and narrow upstream protocol exceptions live in
``forbidden_paths.json`` so the scanner does not hide policy in code.
"""
from __future__ import annotations

import os
import re
from pathlib import PurePosixPath


_TEXT_SUFFIXES = (".py", ".html", ".json", ".jsonl", ".md")


def retired_nomenclature_violations(root: str, policy: dict) -> list[dict]:
    """Return every configured retired term outside an exact exception."""
    terms = tuple(str(term) for term in policy.get("terms", ()))
    excluded = set(policy.get("excluded_files", ()))
    excluded_directories = {
        ".git", ".venv", "__pycache__", "archive", "assets", "build",
        "dist", "evidence", "node_modules", "venv",
        *policy.get("excluded_directories", ()),
    }
    prefixes = tuple(policy.get("excluded_path_prefixes", ()))
    included = policy.get('included_paths')
    if included is not None and (type(included) not in (tuple,list) or not included):
        raise ValueError('included source paths require an explicit nonempty sequence')
    included = tuple(included) if included is not None else None
    if included is not None and any(not isinstance(path,str) or not path or path in ('.','/')
            or PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or path.endswith('/')
            for path in included):
        raise ValueError('included source paths must be exact repository-relative paths')
    def selected(path):
        return included is None or any(path==item or path.startswith(item+'/') for item in included)
    def may_contain_selected(path):
        return selected(path) or any(item.startswith(path+'/') for item in included or ())
    if any(not isinstance(prefix, str) or not prefix or prefix in (".", "/")
           or PurePosixPath(prefix).is_absolute() or ".." in PurePosixPath(prefix).parts
           or prefix.endswith("/") for prefix in prefixes):
        raise ValueError("nomenclature exclusions require exact repository-relative directory prefixes")
    allowed = {str(path): tuple(fragments) for path, fragments
               in policy.get("allowed_fragments", {}).items()}
    violations = []
    for directory, dirnames, filenames in os.walk(root):
        relative_directory = os.path.relpath(directory, root).replace(os.sep, "/")
        if any(relative_directory == prefix or relative_directory.startswith(prefix + "/")
               for prefix in prefixes):
            dirnames[:] = []
            continue
        dirnames[:] = [name for name in dirnames
                       if name not in excluded_directories
                       and may_contain_selected(str(PurePosixPath(relative_directory)/name))]
        for filename in filenames:
            if not filename.endswith(_TEXT_SUFFIXES):
                continue
            path = os.path.join(directory, filename)
            relative = os.path.relpath(path, root)
            if not selected(relative.replace(os.sep,'/')):
                continue
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


def self_test():
    """A declared external-source exclusion never hides neighboring source."""
    from pathlib import Path
    import tempfile
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    with tempfile.TemporaryDirectory(prefix="nomenclature-prefix-check-") as directory:
        root = Path(directory)
        for relative in ("embodiments/example/runtime/upstream.py",
                         "embodiments/example/runtime_extra/active.py",
                         "embodiments/example/README.md", "src/package/active.py"):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("prohibited_fixture_term\n", encoding="utf-8")
        policy = {"terms": ["prohibited_fixture_term"],
                  "excluded_path_prefixes": ["embodiments/example/runtime"]}
        found = {item["file"] for item in retired_nomenclature_violations(directory, policy)}
        check("only_exact_declared_external_subtree_is_excluded", found == {
            "embodiments/example/runtime_extra/active.py", "embodiments/example/README.md",
            "src/package/active.py"})
        scoped=retired_nomenclature_violations(directory,{**policy,'included_paths':['src','embodiments/example/README.md']})
        check('declared_authored_scope_includes_untracked_source_and_selected_documents',
              {item['file'] for item in scoped}=={'src/package/active.py','embodiments/example/README.md'})
        for selection in ([],'.',['.'],['../outside'],['/absolute'],[2]):
            try:retired_nomenclature_violations(directory,{**policy,'included_paths':selection})
            except ValueError:refused=True
            else:refused=False
            check('invalid_included_scope_refused_'+repr(selection),refused)
        for value in ("", ".", "/", "../outside", "/absolute", "trailing/", 2):
            refused = False
            try:
                retired_nomenclature_violations(directory, {**policy, "excluded_path_prefixes": [value]})
            except ValueError:
                refused = True
            check("unsafe_exclusion_refused_" + repr(value), refused)
    return {"tests": tests, "passed": sum(t["passed"] for t in tests), "total": len(tests)}
