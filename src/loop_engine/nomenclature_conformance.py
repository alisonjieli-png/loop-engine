"""Conformance checks for retired source terminology and term placement.

Two policies live outside this module so the scanner hides no vocabulary in
code. ``forbidden_paths.json`` carries the retired source terms and the narrow
upstream protocol exceptions. ``terminology.yaml`` carries every term with its
kind, definition, the surfaces where it may appear, the surfaces where it must
not appear and its status; ``vocabulary_violations`` reads that contract and
refuses a term without a definition, a retired name used in a document, and a
technical word placed on a surface that forbids it.
"""
from __future__ import annotations

import os
import re
from pathlib import PurePosixPath


_TEXT_SUFFIXES = (".py", ".html", ".json", ".jsonl", ".md")
_DOCUMENT_SUFFIX = ".md"
_SKIPPED_DIRECTORIES = ("__pycache__", "node_modules", ".git")
_FENCE = re.compile(r"^\s*```")
_VIEW = re.compile(r'^\s{4}<section data-view="([A-Za-z0-9_-]+)"')
_TEMPLATE = re.compile(r'^\s{2}<template id="([A-Za-z0-9_-]+)"')
_FOOTER = re.compile(r"^\s{2}<footer")
_HEADER = re.compile(r"^\s{2}<header")
_MAIN_END = re.compile(r"^\s{2}</main>")
_PLACEMENT_FIELDS = ("may_appear", "must_not_appear", "status")


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


def served_page_regions(text: str) -> dict:
    """Split the one served page into the regions a placement rule names."""
    regions: dict = {}
    current = None
    for number, line in enumerate(text.splitlines(), 1):
        view, template = _VIEW.match(line), _TEMPLATE.match(line)
        if view:
            current = "view:" + view.group(1)
        elif template:
            current = "template:" + template.group(1)
        elif _FOOTER.match(line):
            current = "footer"
        elif _HEADER.match(line):
            current = "header"
        elif _MAIN_END.match(line):
            current = None
        if current:
            regions.setdefault(current, []).append((number, line))
    return regions


def _prose_lines(path: str):
    """Document lines outside fenced code blocks, which carry commands."""
    inside = False
    with open(path, encoding="utf-8", errors="replace") as stream:
        for number, line in enumerate(stream, 1):
            if _FENCE.match(line):
                inside = not inside
                continue
            if not inside:
                yield number, line


def _surface_documents(root: str, surface: dict):
    """Every document the named surface declares, in a stable order."""
    exclusions = tuple(surface.get("document_exclusions") or ())
    for declared in surface.get("document_paths") or ():
        absolute = os.path.join(root, declared)
        if os.path.isfile(absolute):
            yield declared
            continue
        for directory, names, files in os.walk(absolute):
            names[:] = [name for name in sorted(names)
                        if name not in _SKIPPED_DIRECTORIES]
            for name in sorted(files):
                if not name.endswith(_DOCUMENT_SUFFIX):
                    continue
                relative = os.path.relpath(
                    os.path.join(directory, name), root).replace(os.sep, "/")
                if any(relative == excluded
                       or relative.startswith(excluded + "/")
                       for excluded in exclusions):
                    continue
                yield relative


def resolved_terms(contract: dict) -> dict:
    """Every term with its kind, definition, placement and status.

    ``vocabulary`` holds the words a writer chooses and owns the placement of
    a name that is also a code identifier. ``terms`` holds the code
    identifiers and takes its placement from ``placement_defaults`` for its
    kind, so every term carries all five facts without repeating them.
    """
    defaults = contract.get("placement_defaults") or {}
    resolved: dict = {}
    for section in ("terms", "vocabulary"):
        for name, entry in (contract.get(section) or {}).items():
            entry = entry if isinstance(entry, dict) else {}
            fallback = defaults.get(entry.get("kind"), {})
            item = {"name": name, "section": section,
                    "kind": entry.get("kind"),
                    "definition": entry.get("definition"),
                    "pattern": entry.get("pattern"),
                    "case_sensitive": entry.get("case_sensitive", True),
                    "quotation_exceptions": tuple(
                        entry.get("quotation_exceptions") or ())}
            for field in _PLACEMENT_FIELDS:
                item[field] = (entry[field] if field in entry
                               else fallback.get(field))
            resolved[name] = item
    return resolved


def _matcher(term: dict):
    """The exact expression that finds one term, or None when it has no body."""
    pattern = term.get("pattern") or (r"\b" + re.escape(term["name"]) + r"\b")
    flags = 0 if term.get("case_sensitive", True) else re.IGNORECASE
    try:
        return re.compile(pattern, flags)
    except re.error:
        return None


def vocabulary_violations(root: str, contract: dict,
                          scan_files: bool = True) -> list[dict]:
    """Refuse an undefined term, a retired name and a misplaced word.

    ``scan_files`` is false for an installed package, which carries the
    contract but not the repository documents or the served page source.
    """
    surfaces = contract.get("surfaces") or {}
    terms = resolved_terms(contract)
    if not surfaces or not terms:
        raise ValueError(
            "the vocabulary contract needs declared surfaces and terms")
    violations: list[dict] = []
    for name, term in sorted(terms.items()):
        if not str(term.get("definition") or "").strip():
            violations.append({"rule": "term_without_definition",
                               "file": "terminology.yaml", "line": 0,
                               "detail": f"term {name!r} has no definition"})
        for field in _PLACEMENT_FIELDS:
            if term.get(field) is None:
                violations.append({
                    "rule": "term_without_placement",
                    "file": "terminology.yaml", "line": 0,
                    "detail": f"term {name!r} declares no {field} and its "
                              f"kind {term.get('kind')!r} has no default"})
        for field in ("may_appear", "must_not_appear"):
            for named in term.get(field) or ():
                if named not in surfaces:
                    violations.append({
                        "rule": "term_names_an_undeclared_surface",
                        "file": "terminology.yaml", "line": 0,
                        "detail": f"term {name!r} {field} names {named!r}"})
        if _matcher(term) is None:
            violations.append({"rule": "term_pattern_is_not_an_expression",
                               "file": "terminology.yaml", "line": 0,
                               "detail": f"term {name!r} has an invalid pattern"})
    if scan_files:
        violations.extend(_page_placement_violations(root, surfaces, terms))
        violations.extend(
            _document_vocabulary_violations(root, surfaces, terms))
    return violations


def _page_placement_violations(root, surfaces, terms) -> list[dict]:
    """A declared page region must exist and must not carry a refused word."""
    violations: list[dict] = []
    for surface_name, surface in sorted(surfaces.items()):
        page = surface.get("html_page")
        if not page:
            continue
        absolute = os.path.join(root, page)
        if not os.path.isfile(absolute):
            violations.append({"rule": "declared_surface_page_missing",
                               "file": page, "line": 0,
                               "detail": f"surface {surface_name!r} names a "
                                         "page that is not in the tree"})
            continue
        regions = served_page_regions(
            open(absolute, encoding="utf-8", errors="replace").read())
        lines: list = []
        for region in surface.get("html_regions") or ():
            if region not in regions:
                violations.append({
                    "rule": "declared_surface_region_missing",
                    "file": page, "line": 0,
                    "detail": f"surface {surface_name!r} declares region "
                              f"{region!r}, which the page no longer has"})
                continue
            lines.extend(regions[region])
        if surface.get("enforcement") != "checked":
            continue
        for name, term in sorted(terms.items()):
            if surface_name not in (term.get("must_not_appear") or ()):
                continue
            expression = _matcher(term)
            if expression is None:
                continue
            for number, line in lines:
                if expression.search(line):
                    violations.append({
                        "rule": "forbidden_term_on_surface",
                        "file": page, "line": number,
                        "detail": f"{name!r} must not appear on "
                                  f"{surface_name!r}"})
                    break
    return violations


def _document_vocabulary_violations(root, surfaces, terms) -> list[dict]:
    """A retired name must not appear in the prose of a current document."""
    violations: list[dict] = []
    for surface_name, surface in sorted(surfaces.items()):
        if surface.get("enforcement") != "checked":
            continue
        if not surface.get("document_paths"):
            continue
        refused = [(name, term, _matcher(term))
                   for name, term in sorted(terms.items())
                   if surface_name in (term.get("must_not_appear") or ())
                   and str(term.get("status") or "") == "retired"]
        refused = [item for item in refused if item[2] is not None]
        if not refused:
            continue
        for relative in _surface_documents(root, surface):
            for number, line in _prose_lines(os.path.join(root, relative)):
                for name, term, expression in refused:
                    if relative in term.get("quotation_exceptions", ()):
                        continue
                    if expression.search(line):
                        violations.append({
                            "rule": "retired_name_in_document",
                            "file": relative, "line": number,
                            "detail": f"retired name {name!r} on "
                                      f"{surface_name!r}"})
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
    tests.extend(_vocabulary_self_test())
    return {"tests": tests, "passed": sum(t["passed"] for t in tests), "total": len(tests)}


_FIXTURE_PAGE = """<!doctype html>
<html lang="en">
<body>
  <header class="header">Baltor</header>
  <main id="main">
    <section data-view="home">
      <p>Break the work into focused steps.</p>
    </section>
    <section data-view="docs">
      <p>Every executable graph vertex is a Loop.</p>
    </section>
  </main>
  <footer><span>Baltor</span></footer>
</body>
</html>
"""
_FIXTURE_GUIDE = """# A guide

The service returns a record for every download.

```text
chronicle
```
"""
_FIXTURE_QUOTED = """# A retirement note

An earlier release wrote `chronicle` in that field. It was renamed.
"""


def _fixture_contract() -> dict:
    """A small contract with the same shape as terminology.yaml."""
    return {
        "surfaces": {
            "public_website_pages": {
                "definition": "The homepage and the shared footer.",
                "enforcement": "checked", "html_page": "page.html",
                "html_regions": ["view:home", "footer"]},
            "website_documentation_view": {
                "definition": "The Documentation view.",
                "enforcement": "declared_only", "html_page": "page.html",
                "html_regions": ["view:docs"]},
            "technical_documents": {
                "definition": "Markdown under docs.",
                "enforcement": "checked", "document_paths": ["docs"],
                "document_exclusions": ["docs/evidence"]},
        },
        "placement_defaults": {"canonical": {
            "may_appear": ["technical_documents"],
            "must_not_appear": ["public_website_pages"],
            "status": "current"}},
        "terms": {"LoopValueRef": {
            "kind": "canonical",
            "definition": "A body-free identity for one produced value."}},
        "vocabulary": {
            "Loop": {"kind": "technical_word",
                     "definition": "The sole operational runtime type.",
                     "pattern": r"\bLoops?\b", "case_sensitive": True,
                     "may_appear": ["technical_documents",
                                    "website_documentation_view"],
                     "must_not_appear": ["public_website_pages"],
                     "status": "current"},
            "chronicle": {"kind": "retired_word",
                          "definition": "A retired word for saved events.",
                          "replacement": "Run History",
                          "pattern": r"\bchronicles?\b",
                          "case_sensitive": False, "may_appear": [],
                          "must_not_appear": ["technical_documents",
                                              "public_website_pages"],
                          "quotation_exceptions": ["docs/quoted.md"],
                          "status": "retired"},
        },
    }


def _vocabulary_self_test() -> list:
    """Every vocabulary rule fires on its own known-wrong case."""
    import copy
    import tempfile
    tests = []

    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})

    def rules(root, contract):
        return {item["rule"] for item in vocabulary_violations(root, contract)}

    with tempfile.TemporaryDirectory(prefix="vocabulary-check-") as directory:
        os.makedirs(os.path.join(directory, "docs", "evidence"))
        for relative, body in (("page.html", _FIXTURE_PAGE),
                               ("docs/guide.md", _FIXTURE_GUIDE),
                               ("docs/quoted.md", _FIXTURE_QUOTED),
                               ("docs/evidence/old.md", "A chronicle.\n")):
            with open(os.path.join(directory, relative), "w",
                      encoding="utf-8") as stream:
                stream.write(body)
        clean = _fixture_contract()
        check("a_complete_contract_and_a_correct_tree_report_nothing",
              rules(directory, clean) == set())

        undefined = copy.deepcopy(clean)
        undefined["vocabulary"]["Loop"]["definition"] = ""
        check("a_term_without_a_definition_is_refused",
              "term_without_definition" in rules(directory, undefined))

        unplaced = copy.deepcopy(clean)
        unplaced["terms"]["Orphan"] = {"kind": "unlisted_kind",
                                       "definition": "A term with no kind."}
        check("a_term_whose_kind_has_no_placement_default_is_refused",
              "term_without_placement" in rules(directory, unplaced))

        mistyped = copy.deepcopy(clean)
        mistyped["vocabulary"]["Loop"]["must_not_appear"] = ["public_pages"]
        check("a_term_naming_an_undeclared_surface_is_refused",
              "term_names_an_undeclared_surface" in rules(directory, mistyped))

        with open(os.path.join(directory, "docs", "leak.md"), "w",
                  encoding="utf-8") as stream:
            stream.write("# A note\n\nThe run writes a chronicle.\n")
        check("a_retired_name_in_document_prose_is_refused",
              "retired_name_in_document" in rules(directory, clean))
        os.remove(os.path.join(directory, "docs", "leak.md"))

        check("a_retired_name_inside_a_fenced_block_is_not_prose",
              rules(directory, clean) == set())
        without_exception = copy.deepcopy(clean)
        without_exception["vocabulary"]["chronicle"][
            "quotation_exceptions"] = []
        check("a_retired_name_in_an_inline_code_span_needs_a_declared_reason",
              "retired_name_in_document" in rules(directory,
                                                  without_exception))

        page = os.path.join(directory, "page.html")
        original = open(page, encoding="utf-8").read()
        with open(page, "w", encoding="utf-8") as stream:
            stream.write(original.replace(
                "<p>Break the work into focused steps.</p>",
                "<p>Every step is a Loop.</p>"))
        check("a_technical_word_on_a_public_page_region_is_refused",
              "forbidden_term_on_surface" in rules(directory, clean))

        with open(page, "w", encoding="utf-8") as stream:
            stream.write(original.replace('data-view="home"',
                                          'data-view="landing"'))
        check("a_declared_page_region_that_disappeared_is_refused",
              "declared_surface_region_missing" in rules(directory, clean))
        with open(page, "w", encoding="utf-8") as stream:
            stream.write(original)

        os.remove(page)
        check("a_declared_page_that_is_missing_is_refused",
              "declared_surface_page_missing" in rules(directory, clean))

        empty = {"surfaces": {}, "terms": {}, "vocabulary": {}}
        try:
            vocabulary_violations(directory, empty)
            refused = False
        except ValueError:
            refused = True
        check("an_empty_vocabulary_contract_is_refused", refused)
    return tests
