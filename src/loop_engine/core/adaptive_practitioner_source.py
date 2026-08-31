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


def source_inspection_model_view(
        inspections: list[dict], *, include_selected_content: bool = True
        ) -> list[dict]:
    """Project source evidence without replaying a repository manifest."""
    output = []
    for inspection in inspections:
        manifest = inspection.get("source_manifest") or ()
        manifest_digest = hashlib.sha256(json.dumps(
            manifest, sort_keys=True, separators=(",", ":"),
            default=str).encode()).hexdigest()
        surface_counts = Counter(
            str(item.get("surface") or "other") for item in manifest)
        selected = []
        for item in inspection.get("selected") or ():
            row = dict(item)
            if not include_selected_content:
                row.pop("content", None)
            selected.append(row)
        output.append({
            "record_type": str(inspection.get("record_type") or
                               "source_inspection_result/v1"),
            "query": str(inspection.get("query") or ""),
            "source_count": int(inspection.get("source_count") or 0),
            "source_surface_counts": dict(sorted(surface_counts.items())),
            "source_manifest_digest": manifest_digest,
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
    unknown_paths = sorted(set(requested) - set(by_path))
    if unknown_paths:
        raise AdaptivePractitionerError(
            f"source inspection requested unknown paths {unknown_paths}")
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
    selected_paths = list(requested)
    if not selected_paths and include_contents:
        selected_paths = [item["path"] for item in candidates]
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
    tests = [{
        "test": "source_inspection_returns_exact_selected_content",
        "passed": exact,
        "detail": "selected UTF-8 body and digest",
    }, {
        "test": "source_query_model_view_omits_complete_manifest",
        "passed": bounded,
        "detail": "generated evidence is excluded from query candidates",
    }]
    return {"record_type": "adaptive_source_inspection_test/v1",
            "tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


__all__ = (
    "inspectable_source_files", "source_inspection_model_view",
    "source_inspection_operation",
)
