"""Bounded source inventory and selection for the adaptive Practitioner.

Complete manifests remain passive evidence. Model-facing projections contain
only a manifest digest, surface counts, retrieval candidates, and explicitly
selected bodies. Retrieval ranking is advisory and never grants authority.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from collections import Counter
from pathlib import Path

from .adaptive_practitioner_records import (
    AdaptivePractitionerError, AdaptiveRunServices)


_GENERATED_SOURCE_PARTS = frozenset({
    ".cache", ".pytest_cache", "artifacts", "build", "coverage",
    "dist", "graphify-out", "htmlcov", "node_modules", "__pycache__",
})
_CODE_SOURCE_PARTS = frozenset({"app", "lib", "src", "test", "tests"})


def _source_surface(relative: str) -> str:
    """Classify a repository path for retrieval, never for authority."""
    path = Path(relative)
    parts = {part.casefold() for part in path.parts}
    if parts & _GENERATED_SOURCE_PARTS:
        return "generated_or_evidence"
    if parts & {"test", "tests"} or path.name.startswith("test_"):
        return "test"
    if "docs" in parts or path.suffix.casefold() in {".md", ".rst"}:
        return "documentation"
    if parts & _CODE_SOURCE_PARTS or path.suffix.casefold() in {
            ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx"}:
        return "source"
    if path.name in {"pyproject.toml", "setup.cfg", "requirements.txt"} \
            or path.suffix.casefold() in {".toml", ".yaml", ".yml"}:
        return "configuration"
    return "other"


_SELECTED_CONTENT_BYTE_LIMIT = 12_000
_SELECTED_CONTENT_PER_FILE_BYTE_LIMIT = 6_000


def source_inspection_model_view(
        inspections: list[dict], *, include_selected_content: bool = True,
        selected_content_byte_limit: "int | None" = _SELECTED_CONTENT_BYTE_LIMIT,
        ) -> list[dict]:
    """Project source evidence without replaying a repository manifest.

    Selected bodies are bounded: each selected body contributes at most
    ``selected_content_byte_limit // len(selected)`` bytes to the model view
    so one selection cannot grow prompts without bound. Truncated rows are
    marked; the full body stays available in the source inspection record
    for deterministic project inputs.
    """
    output = []
    for inspection in inspections:
        manifest = inspection.get("source_manifest") or ()
        manifest_digest = hashlib.sha256(json.dumps(
            manifest, sort_keys=True, separators=(",", ":"),
            default=str).encode()).hexdigest()
        surface_counts = Counter(
            str(item.get("surface") or "other") for item in manifest)
        selected = []
        rows = [dict(item) for item in inspection.get("selected") or ()]
        per_file_limit = selected_content_byte_limit
        if selected_content_byte_limit is not None and rows:
            per_file_limit = max(
                512, selected_content_byte_limit // len(rows))
        for row in rows:
            if not include_selected_content:
                row.pop("content", None)
            elif selected_content_byte_limit is not None:
                body = row.get("content")
                if isinstance(body, str) and len(body.encode(
                        "utf-8")) > per_file_limit:
                    encoded = body.encode("utf-8")[:per_file_limit]
                    row["content"] = encoded.decode(
                        "utf-8", errors="replace")
                    row["content_truncated"] = True
                    row["content_truncated_from_bytes"] = len(body.encode(
                        "utf-8"))
            selected.append(row)
        output.append({
            "record_type": str(inspection.get("record_type") or
                               "source_inspection_result/v1"),
            "query": str(inspection.get("query") or ""),
            "source_count": int(inspection.get("source_count") or 0),
            "source_surface_counts": dict(sorted(surface_counts.items())),
            "source_manifest_digest": manifest_digest,
            "manifest_paths": [
                str(item.get("path") or "") for item in manifest
                if str(item.get("path") or "")],
            "candidates": list(inspection.get("candidates") or ()),
            "selected": selected,
            "contents_included": bool(inspection.get("contents_included")),
        })
    return output


def inspectable_source_files(
        services: AdaptiveRunServices) -> tuple[tuple[str, Path], ...]:
    """Resolve confined text sources without selecting their task meaning."""
    if not services.request.allow_source_materialization_to_model:
        raise PermissionError(
            "source inspection requires explicit source-to-model authority")
    allowed_names = {"pyproject.toml", "requirements.txt", "setup.cfg"}
    allowed_suffixes = {
        ".bib", ".cfg", ".csv", ".eml", ".fasta", ".fa", ".geojson",
        ".graphql", ".ics", ".ini", ".json", ".jsonl", ".md", ".po",
        ".py", ".rst", ".sql", ".srt", ".toml", ".tsv", ".txt",
        ".vcf", ".xml", ".yaml", ".yml"}
    excluded_parts = {
        ".git", ".venv", "__pycache__", "node_modules", "build", "dist"}
    resolved = []
    used = set()
    for source_ref in services.request.source_refs:
        source = Path(source_ref).expanduser().resolve()
        if not source.exists() or source.is_symlink():
            continue
        candidates = (source,) if source.is_file() else tuple(sorted(
            item for item in source.rglob("*")
            if item.is_file() and not item.is_symlink()
            and not excluded_parts.intersection(
                item.relative_to(source).parts)))
        for path in candidates:
            if (path.name.startswith(".") or path.name not in allowed_names
                    and path.suffix.lower() not in allowed_suffixes):
                continue
            relative = (path.name if source.is_file()
                        else f"{source.name}/{path.relative_to(source).as_posix()}")
            if relative in used:
                continue
            used.add(relative)
            resolved.append((relative, path))
    return tuple(resolved)


def _resolve_requested_paths(
        requested: list[str], by_path: dict[str, Path]) -> dict[str, str]:
    """Resolve one admitted path for each requested path.

    A requested path may be the exact admitted relative path, one of its
    suffixes such as the basename, or an absolute path inside one admitted
    source root. Every form resolves to the same admitted file so a caller
    never needs to guess one exact spelling. Ambiguous basenames resolve to
    no file and are reported as unknown.
    """
    resolved: dict[str, str] = {}
    exact = set(by_path)
    basenames: dict[str, list[str]] = {}
    for relative in by_path:
        basenames.setdefault(Path(relative).name, []).append(relative)
    for raw in requested:
        requested_path = Path(raw)
        if raw in exact and raw not in resolved:
            resolved[raw] = raw
            continue
        absolute = str(requested_path.expanduser().resolve())
        matches = [relative for relative, path in by_path.items()
                   if str(path) == absolute]
        if len(matches) == 1 and matches[0] not in resolved:
            resolved[raw] = matches[0]
            continue
        name = requested_path.name
        same_name = [relative for relative in basenames.get(name, ())
                     if relative not in resolved]
        if len(same_name) == 1:
            resolved[raw] = same_name[0]
            continue
        suffix_matches = [relative for relative in by_path
                          if relative.endswith(f"/{raw}") and raw not in exact
                          and relative not in resolved]
        if len(suffix_matches) == 1:
            resolved[raw] = suffix_matches[0]
    return resolved


def source_inspection_operation(
        arguments: dict, services: AdaptiveRunServices) -> dict:
    """Return an exact manifest and deterministic relevance band."""
    files = inspectable_source_files(services)
    requested = arguments.get("paths") or []
    if not isinstance(requested, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in requested):
        raise AdaptivePractitionerError(
            "source inspection paths must be a list of non-empty text")
    query = str(arguments.get("query") or "").strip()
    include_contents = arguments.get("include_contents", False)
    if not isinstance(include_contents, bool):
        raise AdaptivePractitionerError(
            "source inspection include_contents must be boolean")
    by_path = {relative: path for relative, path in files}
    resolved_requested = _resolve_requested_paths(requested, by_path)
    unknown_paths = sorted(set(requested) - set(resolved_requested))
    if unknown_paths:
        raise AdaptivePractitionerError(
            f"source inspection requested unknown paths {unknown_paths}"
            "; inspect manifest_paths for the exact admitted paths")
    query_terms = tuple(dict.fromkeys(
        re.findall(r"[a-z0-9_]{2,}", query.lower())))
    text_by_path = {}
    scored = []
    for relative, path in files:
        body = path.read_bytes()
        text = body.decode("utf-8", errors="replace")
        text_by_path[relative] = text
        relative_lower = relative.lower()
        text_lower = text.lower()
        path_hits = sum(term in relative_lower for term in query_terms)
        body_hits = sum(term in text_lower for term in query_terms)
        surface = _source_surface(relative)
        row = {
            "path": relative, "byte_count": len(body),
            "digest": hashlib.sha256(body).hexdigest(),
            "media_type": mimetypes.guess_type(path.name)[0] or "text/plain",
            "surface": surface,
        }
        if query_terms and (path_hits or body_hits) \
                and surface != "generated_or_evidence":
            scored.append((path_hits, body_hits, row))
    candidates = []
    if scored:
        maximum_path_hits = max(item[0] for item in scored)
        if maximum_path_hits:
            relevance_band = [item for item in scored
                              if item[0] == maximum_path_hits]
        else:
            maximum_body_hits = max(item[1] for item in scored)
            relevance_band = [item for item in scored
                              if item[1] == maximum_body_hits]
        candidates = [{
            **item[2], "path_term_matches": item[0],
            "body_term_matches": item[1],
        } for item in sorted(
            relevance_band,
            key=lambda item: (-item[0], -item[1], item[2]["path"]))]
    selected_paths = [resolved_requested[item] for item in requested]
    if not selected_paths and include_contents:
        selected_paths = [item["path"] for item in candidates]
    seen_selected: set[str] = set()
    deduplicated = []
    for relative in selected_paths:
        if relative not in seen_selected:
            seen_selected.add(relative)
            deduplicated.append(relative)
    selected_paths = deduplicated
    selected = []
    for relative in selected_paths:
        path = by_path[relative]
        body = path.read_bytes()
        row = {
            "path": relative, "byte_count": len(body),
            "digest": hashlib.sha256(body).hexdigest(),
            "media_type": mimetypes.guess_type(path.name)[0] or "text/plain",
            "surface": _source_surface(relative),
        }
        if include_contents:
            row["content"] = text_by_path[relative]
        selected.append(row)
    manifest = [{
        "path": relative, "byte_count": path.stat().st_size,
        "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
        "media_type": mimetypes.guess_type(path.name)[0] or "text/plain",
        "surface": _source_surface(relative),
    } for relative, path in files]
    return {
        "record_type": "source_inspection_result/v1",
        "source_manifest": manifest, "candidates": candidates,
        "selected": selected, "query": query,
        "contents_included": include_contents,
        "source_count": len(manifest),
    }


def source_profile_operation(
        arguments: dict, services: AdaptiveRunServices) -> dict:
    """Profile source structure deterministically without model exposure.

    Discovery stays effect-free toward the model: only counts, field names,
    and bounded samples leave the operation, and nothing is sent to a
    provider. A profile never selects a source or grants authority.
    """
    files = dict(inspectable_source_files(services))
    requested = arguments.get("paths") or []
    if not isinstance(requested, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in requested):
        raise AdaptivePractitionerError(
            "source profile paths must be a list of non-empty text")
    maximum_sample_bytes = arguments.get("maximum_sample_bytes") or 512
    if (not isinstance(maximum_sample_bytes, int)
            or isinstance(maximum_sample_bytes, bool)
            or maximum_sample_bytes < 1):
        raise AdaptivePractitionerError(
            "source profile maximum_sample_bytes must be a positive integer")
    resolved = _resolve_requested_paths(requested, files) \
        if requested else {name: name for name in files}
    unknown = sorted(set(requested) - set(resolved))
    if unknown:
        raise AdaptivePractitionerError(
            f"source profile requested unknown paths {unknown}"
            "; inspect manifest_paths from core.source.inspect first")
    profiles = []
    for raw, relative in sorted(resolved.items()):
        path = files[relative]
        body = path.read_bytes()
        text = body.decode("utf-8", errors="replace")
        lines = text.splitlines()
        profile: dict = {
            "path": relative,
            "byte_count": len(body),
            "line_count": len(lines),
            "media_type": mimetypes.guess_type(path.name)[0] or "text/plain",
            "structure_kind": "text",
            "fields": [],
            "sample": text[:maximum_sample_bytes],
        }
        if path.suffix.lower() == ".csv" or path.suffix.lower() == ".tsv":
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            header = lines[0] if lines else ""
            fields = [field.strip() for field in header.split(delimiter)]
            profile["structure_kind"] = "delimited_table"
            profile["fields"] = fields
            profile["data_row_count"] = max(0, len(lines) - 1)
        elif path.suffix.lower() == ".json":
            try:
                parsed = json.loads(text) if text.strip() else None
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                profile["structure_kind"] = "json_object"
                profile["fields"] = sorted(str(key) for key in parsed)
            elif isinstance(parsed, list):
                profile["structure_kind"] = "json_array"
                if parsed and isinstance(parsed[0], dict):
                    profile["fields"] = sorted(
                        str(key) for key in parsed[0])
                profile["data_row_count"] = len(parsed)
        elif path.suffix.lower() in {".jsonl", ".ndjson"}:
            profile["structure_kind"] = "json_lines"
            if lines:
                try:
                    first = json.loads(lines[0])
                    if isinstance(first, dict):
                        profile["fields"] = sorted(str(key) for key in first)
                except ValueError:
                    pass
                profile["data_row_count"] = len(lines)
        profiles.append(profile)
    return {
        "record_type": "source_profile_result/v1",
        "profiles": profiles,
        "profiled_count": len(profiles),
    }


def self_test() -> dict:
    """Prove exact selection and bounded model projection."""
    import tempfile
    from types import SimpleNamespace

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
        "test": "selected_content_is_bounded_in_the_model_view",
        "passed": bounded_selection and small_selection_untouched,
        "detail": "large selections truncate to a fixed byte budget with "
                  "explicit truncation flags; small bodies pass through "
                  "unchanged",
    }]
    return {"record_type": "adaptive_source_inspection_test/v1",
            "tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


__all__ = (
    "inspectable_source_files", "source_inspection_model_view",
    "source_inspection_operation",
)
