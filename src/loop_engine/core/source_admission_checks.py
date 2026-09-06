"""Focused checks for source admission, selection, and exclusion evidence.

Fixtures cover confined multilingual text sources, non-text inputs, protected
paths, source identity, and bounded model projections. No model is called.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .adaptive_practitioner_source import (
    CapabilityRejected, _SAVED_CONTENT_BYTE_LIMIT, _resolve_requested_paths,
    _saved_record_is_bounded, inspectable_source_files,
    saved_source_inspections, source_inspection_model_view,
    source_inspection_operation, source_profile_operation)


def run_checks() -> dict:
    """Prove exact selection and bounded model projection."""
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as directory:
        source_root = Path(directory) / "source"
        source_root.mkdir()
        source_file = source_root / "unexpected_format.py"
        source_file.write_text(
            "def convert(value):\n    return value.casefold()\n",
            encoding="utf-8")
        services = SimpleNamespace(request=SimpleNamespace(
            source_refs=(str(source_root),),
            allow_source_materialization_to_model=True))
        inspected = source_inspection_operation({
            "paths": ["source/unexpected_format.py"],
            "include_contents": True}, services)
        exact = (inspected["source_count"] == 1
                 and inspected["selected"][0]["content"].startswith(
                     "def convert")
                 and len(inspected["selected"][0]["digest"]) == 64)
        with patch("loop_engine.core.adaptive_practitioner_source._read_source_bytes",
                   side_effect=(b"sample", b"A", b"B")) as reader:
            changing = source_inspection_operation({
                "paths": ["source/unexpected_format.py"],
                "query": "unexpected_format", "include_contents": True}, services)
        one_read_consistent = (
            reader.call_count == 2 and changing["selected"][0]["content"] == "A"
            and all(row["digest"] == hashlib.sha256(b"A").hexdigest()
                    and row["byte_count"] == 1 for row in (
                        *changing["selected"], *changing["candidates"],
                        *changing["source_manifest"]))
            and all("content" not in row for row in changing["source_manifest"]))
        with patch.object(Path, "is_symlink", return_value=True), patch.object(
                Path, "resolve", side_effect=AssertionError("must refuse before resolve")):
            try:
                inspectable_source_files(services)
                root_symlink_refused = False
            except PermissionError:
                root_symlink_refused = True
        generated = source_root / "artifacts"
        generated.mkdir()
        (generated / "orientation.json").write_text(
            '{"solve":"progress practitioner cancellation stderr stdout"}',
            encoding="utf-8")
        (source_root / "solve_cli.py").write_text(
            "def solve():\n    # progress on stderr\n    return 'practitioner'\n",
            encoding="utf-8")
        queried = source_inspection_operation({
            "query": "solve progress practitioner cancellation stderr stdout",
            "include_contents": False}, services)
        model_view = source_inspection_model_view([queried])
        bounded = bool(
            queried["candidates"]
            and queried["candidates"][0]["path"] == "source/solve_cli.py"
            and not queried["selected"]
            and "source_manifest" not in model_view[0]
            and len(model_view[0]["source_manifest_digest"]) == 64)
        manifest_paths_visible = (
            "source/solve_cli.py" in model_view[0]["manifest_paths"]
            and "source/unexpected_format.py"
            in model_view[0]["manifest_paths"]
            and all("content" not in item for item in queried["selected"]))
        alias_selected = source_inspection_operation({
            "paths": ["unexpected_format.py"], "include_contents": False},
            services)
        exact_alias = (
            len(alias_selected["selected"]) == 1
            and alias_selected["selected"][0]["path"]
            == "source/unexpected_format.py")
        resolved = _resolve_requested_paths(
            ["unexpected_format.py",
             "source/unexpected_format.py",
             str(source_root / "unexpected_format.py")],
            {"source/unexpected_format.py": source_file})
        alias_forms_agree = (
            len(set(resolved.values())) == 1
            and set(resolved.values()) == {"source/unexpected_format.py"})
        ambiguous_root = Path(directory) / "second"
        ambiguous_root.mkdir()
        (ambiguous_root / "unexpected_format.py").write_text("x = 1\n",
                                                             encoding="utf-8")
        ambiguous_services = SimpleNamespace(request=SimpleNamespace(
            source_refs=(str(source_root), str(ambiguous_root)),
            allow_source_materialization_to_model=True))
        ambiguous_files = dict(inspectable_source_files(ambiguous_services))
        ambiguous_resolved = _resolve_requested_paths(
            ["unexpected_format.py"], ambiguous_files)
        ambiguous_basename_refused = (
            list(ambiguous_resolved.values()) == [])
        # A path the run never admitted is refused with the admitted set
        # attached, so the next decision is a lookup rather than a guess.
        try:
            source_inspection_operation(
                {"paths": ["/elsewhere/on/disk"],
                 "include_contents": False}, services)
            rejection = None
        except CapabilityRejected as refused:
            rejection = refused.rejection
        unadmitted_carries_admitted = bool(
            rejection is not None
            and rejection.reason_code == "argument_not_admitted"
            and rejection.admitted_values
            and "source/unexpected_format.py" in rejection.admitted_values
            and rejection.admitted_values_total
            == len(dict(inspectable_source_files(services)))
            and rejection.repair_hint)
        big_body = "z" * 100_000
        big_view = source_inspection_model_view([{
            "record_type": "source_inspection_result/v1",
            "source_count": 1, "source_manifest": [], "candidates": [],
            "selected": [{"path": "source/big.csv", "digest": "c" * 64,
                          "content": big_body}],
            "contents_included": True}])
        big_row = big_view[0]["selected"][0]
        bounded_selection = (
            len(big_row["content"].encode("utf-8")) <= 12_000
            and big_row.get("content_truncated") is True
            and big_row.get("content_truncated_from_bytes") == 100_000)
        unbounded_view = source_inspection_model_view([{
            "record_type": "source_inspection_result/v1",
            "source_count": 1, "source_manifest": [], "candidates": [],
            "selected": [{"path": "source/tiny.csv", "digest": "d" * 64,
                          "content": "a,b\n1,2\n"}],
            "contents_included": True}])
        tiny_row = unbounded_view[0]["selected"][0]
        small_selection_untouched = (
            tiny_row["content"] == "a,b\n1,2\n"
            and "content_truncated" not in tiny_row)
    tests = [{
        "test": "materialization_revalidates_sample_then_binds_one_exact_read",
        "passed": one_read_consistent,
        "detail": "admission sample is separate; selected content and metadata share A",
    }, {
        "test": "root_symlink_is_refused_before_resolution",
        "passed": root_symlink_refused,
        "detail": "a root classified as a symbolic link never reaches resolve",
    }, {
        "test": "source_inspection_returns_exact_selected_content",
        "passed": exact,
        "detail": "selected UTF-8 body and digest",
    }, {
        "test": "source_query_model_view_omits_complete_manifest",
        "passed": bounded,
        "detail": "generated evidence is excluded from query candidates",
    }, {
        "test": "model_view_exposes_manifest_paths_without_bodies",
        "passed": manifest_paths_visible,
        "detail": "exact admitted paths are visible; file bodies stay hidden "
                  "until selection",
    }, {
        "test": "basename_and_absolute_paths_resolve_to_admitted_files",
        "passed": exact_alias and alias_forms_agree,
        "detail": "basename, exact, and absolute forms select the same "
                  "admitted source",
    }, {
        "test": "ambiguous_basename_is_refused_not_guessed",
        "passed": ambiguous_basename_refused,
        "detail": "a basename matching several admitted files resolves to "
                  "nothing and is reported as unknown",
    }, {
        "test": "an_unadmitted_path_is_refused_with_the_admitted_set_attached",
        "passed": unadmitted_carries_admitted,
        "detail": "the typed rejection names the admitted relative paths and "
                  "the repair, so a repeat is never the only next move",
    }, {
        "test": "selected_content_is_bounded_in_the_model_view",
        "passed": bounded_selection and small_selection_untouched,
        "detail": "large selections truncate to a fixed byte budget with "
                  "explicit truncation flags; small bodies pass through "
                  "unchanged",
    }, {
        "test": "a_saved_record_does_not_carry_a_whole_dataset",
        "passed": _saved_record_is_bounded(),
        "detail": "the record keeps a bounded head of a large body and says "
                  "it elided the rest and where the file is; the row already "
                  "carries the path, byte count and digest that identify it",
    }]
    tests.extend(_content_admission_checks())
    return {"record_type": "adaptive_source_inspection_test/v1",
            "tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def _content_admission_checks() -> list[dict]:
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    from . import adaptive_practitioner_source as source
    from .context_budget import ContextBudgetPolicy

    tests = []

    def check(name, value):
        tests.append({"test": name, "passed": bool(value), "detail": "offline source fixtures"})

    with tempfile.TemporaryDirectory(prefix="source-admission-") as directory:
        root = Path(directory) / "repo"
        root.mkdir()
        text_names = ("main.ts", "main.js", "main.go", "main.rs", "Main.java",
                      "README", "data.unfamiliar")
        for name in text_names:
            (root / name).write_text("Readable source π with arbitrary syntax.\n", encoding="utf-8")
        (root / "binary.bin").write_bytes(b"\x00\xff\x01")
        (root / "unreadable.txt").write_text("unavailable")
        (root / ".env").write_text("PRIVATE_VALUE=never-export-this")
        for name in (".git", "node_modules", "secrets", ".private"):
            folder = root / name
            folder.mkdir()
            (folder / "private.txt").write_text("never-export-this")
        (root / "secret-document.txt").write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nnever-export-this")
        (root / "linked.txt").symlink_to(root / "README")
        services = SimpleNamespace(request=SimpleNamespace(
            source_refs=(str(root),), allow_source_materialization_to_model=True,
            context_budget=ContextBudgetPolicy(list_total_bytes=64)))
        real_read = source._read_source_bytes
        touched = []

        def read(path, limit=None):
            touched.append((path, limit))
            if path.name == "unreadable.txt":
                raise PermissionError("offline unreadable fixture")
            return real_read(path, limit)

        with patch.object(source, "_read_source_bytes", side_effect=read):
            inventory = source.inventory_source_files(services)
            inspection = source_inspection_operation({}, services)
        admitted = dict(inventory.files)
        excluded = {item["path"]: item["reason"] for item in inspection["source_exclusions"]}
        check("source_admission_depends_on_text_content_not_language_suffix",
              set(admitted) == {"repo/" + name for name in text_names})
        check("binary_unreadable_hidden_ignored_and_protected_entries_are_visible_exclusions",
              excluded["repo/binary.bin"] == "binary_or_unsupported_encoding"
              and excluded["repo/unreadable.txt"] == "unreadable_source"
              and excluded["repo/secret-document.txt"] == "protected_content"
              and excluded["repo/.env"] == "hidden_path"
              and excluded["repo/.git"] == "ignored_directory"
              and excluded["repo/node_modules"] == "ignored_directory"
              and excluded["repo/secrets"] == "protected_source_path"
              and excluded["repo/linked.txt"] == "symlink")
        check("source_inventory_samples_are_budget_bound_and_excluded_bodies_never_export",
              all(limit == 64 for path, limit in touched[:len(text_names) + 3])
              and not any("never-export-this" in str(value) for value in (
                  inspection, source_inspection_model_view([inspection])))
              and all(not any(part in (".git", ".private", "node_modules", "secrets", ".env")
                              for part in path.parts) for path, _ in touched))
        services.request.source_refs = (str(root / "main.ts"),)
        check("explicit_non_python_text_file_is_admitted",
              dict(inspectable_source_files(services)) == {"main.ts": root / "main.ts"})
        services.request.source_refs = (str(root / "README"), str(root / "README"))
        duplicated = source.inventory_source_files(services)
        check("duplicate_source_references_preserve_one_identity_with_an_explicit_record",
              len(duplicated.files) == 1 and duplicated.records[-1].reason == "duplicate_reference")
        other = Path(directory) / "elsewhere" / "repo"
        other.mkdir(parents=True)
        (other / "main.ts").write_text("different source")
        services.request.source_refs = (str(root), str(other))
        ambiguous = source.inventory_source_files(services)
        check("colliding_relative_source_identities_are_excluded_not_first_wins",
              "repo/main.ts" not in dict(ambiguous.files)
              and any(item.reason == "ambiguous_identity" for item in ambiguous.records))
        (root / "late.bin").write_bytes(b"A" * 80 + b"\x00")
        services.request.source_refs = (str(root / "late.bin"),)
        late = source_inspection_operation({}, services)
        check("binary_tail_after_admission_sample_cannot_enter_full_materialization",
              late["source_count"] == 0
              and late["source_exclusions"][0]["reason"] == "source_changed_or_non_text")
        services.request.allow_source_materialization_to_model = False
        with patch.object(source, "_read_source_bytes") as reader:
            try:
                source.inventory_source_files(services)
                refused = False
            except PermissionError:
                refused = True
        check("source_admission_has_no_read_without_the_existing_grant", refused and not reader.called)
        services.request.allow_source_materialization_to_model = True
        link = Path(directory) / "linked-root"
        link.symlink_to(root, target_is_directory=True)
        services.request.source_refs = (str(link),)
        try:
            inspectable_source_files(services)
            refused_root = False
        except PermissionError:
            refused_root = True
        check("source_root_symlink_remains_refused", refused_root)
        ancestor = Path(directory) / "ancestor-alias"
        actual = Path(directory) / "actual"
        actual.mkdir()
        project = actual / "project"
        project.mkdir()
        (project / "main.ts").write_text("export const value = 1;\n")
        ancestor.symlink_to(actual, target_is_directory=True)
        services.request.source_refs = (str(ancestor / "project"),)
        aliased = source.inventory_source_files(services)
        check("authorized_ancestor_alias_is_canonicalized_without_rejecting_the_root",
              dict(aliased.files) == {"project/main.ts": project / "main.ts"})
        escape = project / "escape"
        escape.symlink_to(root, target_is_directory=True)
        escaped = source.inventory_source_files(services)
        check("nested_directory_symlink_cannot_expand_the_source_scope",
              dict(escaped.files) == {"project/main.ts": project / "main.ts"}
              and any(item.path == "project/escape" and item.reason == "symlink"
                      for item in escaped.records))
        (project / "unicode.cut").write_text("A" * 63 + "π")
        check("bounded_utf8_sample_can_end_inside_a_multibyte_character",
              "project/unicode.cut" in dict(source.inventory_source_files(services).files))
        services.request.context_budget = ContextBudgetPolicy(list_total_bytes=0)
        empty_budget = source.inventory_source_files(services)
        check("explicit_zero_inspection_budget_does_not_receive_an_invented_sample_allowance",
              not empty_budget.files and any(item.reason == "inspection_budget_unavailable"
                                             for item in empty_budget.records))
    return tests
