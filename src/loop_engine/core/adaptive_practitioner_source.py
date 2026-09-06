"""Bounded source inventory and selection for the adaptive Practitioner.

Complete manifests remain passive evidence. Model-facing projections contain
manifest identity, surface counts, exclusion reasons, retrieval candidates, and
explicitly selected bodies. Ranking is advisory and never grants authority.
"""
from __future__ import annotations

import csv
import codecs
import hashlib
import json
import mimetypes
import os
import re
import stat
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .adaptive_practitioner_records import (
    AdaptivePractitionerError, AdaptiveRunServices)
from .capability_rejection import (CapabilityRejected, CapabilityRejection,
                                   bounded_admitted_values)
from .runtime_capacity import converged, model_evidence_bytes
from .context_budget import ContextBudgetPolicy


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


#: Where core.generated_project materializes an admitted source inside the
#: sandbox. Stated once, here, so the path the runtime tells the model and the
#: path the runtime actually writes cannot drift apart. A live run drifted
#: exactly this way: runtime facts stated the bare admitted path, the sandbox
#: held it under this prefix, and the generated solution opened the path it had
#: been told about and found nothing.
PROJECT_INPUT_PREFIX = "inputs/"


def project_input_path(relative: str) -> str:
    """The exact sandbox path one admitted source is materialized at."""
    return PROJECT_INPUT_PREFIX + relative


#: Only the fallback for a caller with no measured budget to offer. Every
#: production caller passes the allowance the run itself declares, so raising
#: a run's context raises what its source bodies may carry, with nothing to
#: edit here.
_SELECTED_CONTENT_BYTE_LIMIT = 12_000



#: Bytes of one selected body kept in the SAVED record. The run holds the
#: full body in memory for deterministic project inputs and that is
#: unchanged; this bounds only what is written to disk afterwards. The row
#: already carries the file's path, byte count and digest, and the file it
#: came from is read-only and still there, so copying its bytes into the
#: record identifies nothing further. One competition run wrote an 80 MB
#: train.csv into a 113 MB result and, with two other runs doing the same
#: into a RAM-backed temporary filesystem, exhausted the machine.
_SAVED_CONTENT_BYTE_LIMIT = 64_000


def saved_source_inspections(inspections: list) -> list:
    """Bound the source bodies a finished record carries to disk.

    A record that elides a body says so, and says where the body is, so a
    later reader can tell an elision from a file that was empty at the time.
    """
    saved = []
    for inspection in inspections:
        row_out = []
        for row in inspection.get("selected") or ():
            row = dict(row)
            body = row.get("content")
            if isinstance(body, str) and len(body.encode("utf-8", "replace")) \
                    > _SAVED_CONTENT_BYTE_LIMIT:
                kept = body.encode("utf-8", "replace")[
                    :_SAVED_CONTENT_BYTE_LIMIT].decode("utf-8", "ignore")
                row["content"] = kept
                row["content_elided"] = True
                row["content_kept_bytes"] = len(kept.encode("utf-8", "replace"))
                row["content_available_at"] = row.get("path", "")
            row_out.append(row)
        saved.append({**inspection, "selected": row_out})
    return saved


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
            "source_exclusions": list(inspection.get("source_exclusions") or ()),
        })
    return output


@dataclass(frozen=True)
class SourceAdmissionRecord:
    """Body-free observation of one declared source entry."""

    path: str
    disposition: str
    reason: str
    byte_count: int | None = None
    sampled_bytes: int = 0
    sample_complete: bool = False

    def to_dict(self) -> dict:
        return {"record_type": "source_admission/v1", **asdict(self)}


@dataclass(frozen=True)
class SourceInventory:
    """Compatible admitted path pairs plus explicit admission evidence."""

    files: tuple[tuple[str, Path], ...]
    records: tuple[SourceAdmissionRecord, ...]


_IGNORED_SOURCE_DIRECTORIES = frozenset({
    ".git", ".venv", "__pycache__", "node_modules", "build", "dist"})
_PROTECTED_SOURCE_NAMES = frozenset({
    "secrets", "credentials", "secrets.json", "credentials.json",
    "id_rsa", "id_ecdsa", "id_ed25519"})


def _open_source(path: Path, *, directory: bool = False) -> int:
    """Open every path component without following links, including ancestors."""
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            next_descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY
                                      | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                       | (os.O_DIRECTORY if directory else 0), dir_fd=descriptor)
    finally:
        os.close(descriptor)


def _read_source_bytes(path: Path, limit: int | None = None) -> bytes:
    """Read stable regular-file bytes without a symlink or device escape."""
    with os.fdopen(_open_source(path), "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise OSError("source is not a regular file")
        body = stream.read() if limit is None else stream.read(limit)
        after = os.fstat(stream.fileno())
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if identity(before) != identity(after):
        raise OSError("source changed during reading")
    return body


class _ProtectedSourceContent(ValueError):
    """A recognizable private-key body is excluded from source exposure."""


def _source_text(body: bytes, *, complete: bool = True) -> str:
    text = codecs.getincrementaldecoder("utf-8-sig")("strict").decode(
        body, final=complete)
    if any((ord(char) < 32 and char not in "\t\n\r\f") or ord(char) == 127
           for char in text):
        raise ValueError("binary control bytes")
    if re.search(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----", text):
        raise _ProtectedSourceContent("private key material")
    return text


def inventory_source_files(services: AdaptiveRunServices) -> SourceInventory:
    """Inspect bounded text samples; preserve why other entries were excluded."""
    if not services.request.allow_source_materialization_to_model:
        raise PermissionError(
            "source inspection requires explicit source-to-model authority")
    limit = (model_evidence_bytes(services)
             if getattr(services.request, "context_budget", None) is not None
             else ContextBudgetPolicy().list_total_bytes)
    admitted, records, identities = {}, [], {}

    def observe(path, relative, is_directory):
        reason = ("ignored_directory" if is_directory and path.name in _IGNORED_SOURCE_DIRECTORIES
                  else "hidden_path" if path.name.startswith(".")
                  else "protected_source_path" if path.name.casefold() in _PROTECTED_SOURCE_NAMES
                  or path.suffix.casefold() in (".key", ".pem") else "")
        if reason:
            records.append(SourceAdmissionRecord(relative, "excluded", reason))
            return
        if is_directory:
            try:
                descriptor = _open_source(path, directory=True)
                try:
                    with os.scandir(descriptor) as entries:
                        for entry in sorted(entries, key=lambda item: item.name):
                            entry_path = path / entry.name
                            name = f"{relative}/{entry.name}"
                            if entry.is_symlink():
                                records.append(SourceAdmissionRecord(name, "excluded", "symlink"))
                            else:
                                observe(entry_path, name, entry.is_dir(follow_symlinks=False))
                finally:
                    os.close(descriptor)
            except OSError:
                records.append(SourceAdmissionRecord(relative, "excluded", "unreadable_directory"))
            return
        if relative in identities:
            same = identities[relative] == path
            if not same:
                admitted.pop(relative, None)
                records[:] = [replace(item, disposition="excluded", reason="ambiguous_identity")
                              if item.path == relative else item for item in records]
            records.append(SourceAdmissionRecord(relative, "excluded",
                                                  "duplicate_reference" if same else "ambiguous_identity"))
            return
        identities[relative] = path
        size, body = None, b""
        try:
            status = path.stat(follow_symlinks=False)
            size = status.st_size
            if not stat.S_ISREG(status.st_mode):
                reason = "not_regular_file"
            elif limit == 0 and size:
                reason = "inspection_budget_unavailable"
            else:
                body = _read_source_bytes(path, limit)
                _source_text(body, complete=len(body) == size)
                admitted[relative] = path
        except PermissionError:
            reason = "unreadable_source"
        except OSError:
            reason = "unreadable_source"
        except _ProtectedSourceContent:
            reason = "protected_content"
        except (UnicodeError, ValueError):
            reason = "binary_or_unsupported_encoding"
        records.append(SourceAdmissionRecord(
            relative, "excluded" if reason else "admitted", reason or "utf8_text_sample",
            size, len(body), len(body) == size))

    for source_ref in services.request.source_refs:
        source = Path(source_ref).expanduser()
        if source.is_symlink():
            raise PermissionError("source inspection refuses symbolic-link roots")
        source = source.resolve()
        if not source.exists():
            records.append(SourceAdmissionRecord(source.name, "excluded", "source_missing"))
            continue
        observe(source, source.name, source.is_dir())
    return SourceInventory(tuple(admitted.items()), tuple(records))


def inspectable_source_files(
        services: AdaptiveRunServices) -> tuple[tuple[str, Path], ...]:
    """Compatibility projection of the explicit source admission inventory."""
    return inventory_source_files(services).files


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
    """Bind materialized text and metadata to the same revalidated byte read.

    This does not freeze sources across calls or make a directory read atomic.
    """
    inventory = inventory_source_files(services)
    files = inventory.files
    admission = list(inventory.records)
    requested = arguments.get("paths") or []
    if not isinstance(requested, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in requested):
        raise CapabilityRejected(CapabilityRejection(
            "core.source.inspect", "argument_type_invalid",
            "source inspection paths must be a list of non-empty text",
            rejected_arguments=(("paths", str(requested)[:200]),),
            repair_hint=("pass paths as a list of admitted relative paths, "
                         "or omit paths to receive the manifest")))
    query = str(arguments.get("query") or "").strip()
    include_contents = arguments.get("include_contents", False)
    if not isinstance(include_contents, bool):
        raise AdaptivePractitionerError(
            "source inspection include_contents must be boolean")
    by_path = {relative: path for relative, path in files}
    resolved_requested = _resolve_requested_paths(requested, by_path)
    unknown_paths = sorted(set(requested) - set(resolved_requested))
    if unknown_paths:
        admitted, total = bounded_admitted_values(by_path)
        raise CapabilityRejected(CapabilityRejection(
            "core.source.inspect", "argument_not_admitted",
            f"source inspection requested unknown paths {unknown_paths}"
            "; inspect manifest_paths for the exact admitted paths. Exclusions: "
            + str({item.path: item.reason for item in admission
                   if item.path in unknown_paths and item.disposition == "excluded"}),
            rejected_arguments=(("paths", tuple(unknown_paths)),),
            admitted_values=admitted, admitted_values_total=total,
            repair_hint=("omit paths to receive the manifest, then request "
                         "only paths listed in admitted_values")))
    query_terms = tuple(dict.fromkeys(
        re.findall(r"[a-z0-9_]{2,}", query.lower())))
    text_by_path = {}
    rows_by_path = {}
    scored = []
    for relative, path in files:
        try:
            body = _read_source_bytes(path)
            text = _source_text(body)
        except (OSError, UnicodeError, ValueError):
            admission = [replace(item, disposition="excluded", reason="source_changed_or_non_text")
                         if item.path == relative else item for item in admission]
            if relative in resolved_requested.values():
                raise CapabilityRejected(CapabilityRejection(
                    "core.source.inspect", "source_no_longer_admitted",
                    "selected source became unreadable, protected, or non-text",
                    rejected_arguments=(("path", relative),),
                    repair_hint="inspect the source inventory again before selecting content")) from None
            continue
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
        rows_by_path[relative] = row
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
        row = dict(rows_by_path[relative])
        if include_contents:
            row["content"] = text_by_path[relative]
        selected.append(row)
    manifest = list(rows_by_path.values())
    return {
        "record_type": "source_inspection_result/v1",
        "source_manifest": manifest, "candidates": candidates,
        "selected": selected, "query": query,
        "contents_included": include_contents,
        "source_count": len(manifest),
        "source_admission": [item.to_dict() for item in admission],
        "source_exclusions": [item.to_dict() for item in admission
                              if item.disposition == "excluded"],
    }


#: How much a profile keeps of what it saw. These shape the report, not how
#: much is read: a field with three labels and a field with three million
#: identifiers both describe themselves in a few values, and the sample stops
#: when the description stops changing rather than at a row number chosen
#: here. Profiling a 44 MB table therefore costs what that table needs.
PROFILE_EXAMPLE_VALUE_LIMIT = 8
PROFILE_VALUE_TEXT_LIMIT = 40


def _sampled_rows(rows, fields, byte_allowance: int):
    """Read rows until they stop teaching, or until the allowance is spent.

    Two guesses are avoided here. A fixed row count guesses how varied the
    data is: too few rows for one dataset, wasted work on the next. And
    stopping only when every field settles never terminates, because a unique
    identifier gains a value on every row and always will — that it does so is
    the finding, not a reason to keep reading. So the bound is the same
    measured byte allowance the rest of the run uses, applied to the rows
    themselves, and convergence only lets a narrow file stop sooner.
    """
    seen: list[set] = [set() for _ in fields]
    taken = 0
    batch = 32
    unchanged = 0
    spent = 0
    while taken < len(rows):
        before = [len(values) for values in seen]
        for row in rows[taken:taken + batch]:
            spent += sum(len(str(cell)) for cell in row) + len(row)
            for index in range(len(fields)):
                value = _scalar_text(row[index]) if index < len(row) else ""
                if value:
                    seen[index].add(value)
        taken = min(len(rows), taken + batch)
        after = [len(values) for values in seen]
        if converged(before, after, unchanged):
            break
        if byte_allowance > 0 and spent >= byte_allowance:
            break
        unchanged = unchanged + 1 if before == after else 0
        batch *= 2
    return rows[:taken]


def _is_number(value: str) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _scalar_text(value: object) -> str:
    """One field value as text; a missing or null value reads as empty."""
    return "" if value is None else str(value).strip()


def _field_value_profiles(sampled: "list[tuple[str, list[str]]]") -> list[dict]:
    """State what each field's sampled values look like, never what they mean.

    A field name is not its type. A live run read a column holding Yes and No
    as a continuous target, chose a regressor, and reported a root mean
    squared error it could not have computed. The header alone allowed that;
    the values would not have. Whatever the runtime can settle exactly over
    the rows it sampled, it settles here: how many distinct values appeared,
    what some of them are, whether every one parses as a number, how many were
    empty. What the field is *for* stays a reading, and stays the model's.
    """
    profiles = []
    for field, values in sampled:
        present = [value for value in values if value != ""]
        distinct = sorted(set(present))
        profiles.append({
            "field": field,
            "sampled_values": len(values),
            "empty_sampled_values": len(values) - len(present),
            "distinct_sampled_values": len(distinct),
            "example_values": [item[:PROFILE_VALUE_TEXT_LIMIT]
                               for item in distinct[
                                   :PROFILE_EXAMPLE_VALUE_LIMIT]],
            "every_sampled_value_is_a_number": bool(present) and all(
                _is_number(item) for item in present),
        })
    return profiles


def source_profile_operation(
        arguments: dict, services: AdaptiveRunServices) -> dict:
    """Profile source structure deterministically without model exposure.

    Discovery stays effect-free toward the model: only counts, field names,
    and bounded samples leave the operation, and nothing is sent to a
    provider. A profile never selects a source or grants authority.
    """
    inventory = inventory_source_files(services)
    files = dict(inventory.files)
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
        admitted, total = bounded_admitted_values(files)
        raise CapabilityRejected(CapabilityRejection(
            "core.source.profile", "argument_not_admitted",
            f"source profile requested unknown paths {unknown}"
            "; inspect manifest_paths from core.source.inspect first",
            rejected_arguments=(("paths", tuple(unknown)),),
            admitted_values=admitted, admitted_values_total=total,
            repair_hint=("omit paths to profile every admitted source, or "
                         "request only paths listed in admitted_values")))
    # The rows a profile reads are bounded by the same measured allowance the
    # rest of the run spends, not by a row count written here.
    row_allowance = model_evidence_bytes(services)
    profiles = []
    for raw, relative in sorted(resolved.items()):
        path = files[relative]
        try:
            body = _read_source_bytes(path)
            text = _source_text(body)
        except (OSError, UnicodeError, ValueError):
            raise CapabilityRejected(CapabilityRejection(
                "core.source.profile", "source_no_longer_admitted",
                "source became unreadable, protected, or non-text before profiling",
                rejected_arguments=(("path", relative),),
                repair_hint="inspect current source exclusions before profiling")) from None
        lines = text.splitlines()
        profile: dict = {
            "path": relative,
            "byte_count": len(body),
            "line_count": len(lines),
            "media_type": mimetypes.guess_type(path.name)[0] or "text/plain",
            "structure_kind": "text",
            "fields": [],
            "field_profiles": [],
            "sample": text[:maximum_sample_bytes],
        }
        if path.suffix.lower() in {".csv", ".tsv"}:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            # csv.reader, not split: a quoted value containing the delimiter
            # would otherwise shift every field after it and make the whole
            # profile a confident description of the wrong columns.
            rows = list(csv.reader(lines, delimiter=delimiter))
            fields = [str(name).strip() for name in (rows[0] if rows else ())]
            sampled = _sampled_rows(rows[1:], fields, row_allowance)
            profile["structure_kind"] = "delimited_table"
            profile["fields"] = fields
            profile["data_row_count"] = max(0, len(lines) - 1)
            profile["sampled_row_count"] = len(sampled)
            profile["field_profiles"] = _field_value_profiles([
                (name, [_scalar_text(row[index]) if index < len(row) else ""
                        for row in sampled])
                for index, name in enumerate(fields)])
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
                    fields = sorted(str(key) for key in parsed[0])
                    sampled_rows = _sampled_rows(
                        [[_scalar_text(row.get(name)) for name in fields]
                         for row in parsed if isinstance(row, dict)],
                        fields, row_allowance)
                    profile["fields"] = fields
                    profile["sampled_row_count"] = len(sampled_rows)
                    profile["field_profiles"] = _field_value_profiles([
                        (name, [row[index] for row in sampled_rows])
                        for index, name in enumerate(fields)])
                profile["data_row_count"] = len(parsed)
        elif path.suffix.lower() in {".jsonl", ".ndjson"}:
            profile["structure_kind"] = "json_lines"
            if lines:
                sampled_rows = []
                for line in lines:
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(entry, dict):
                        sampled_rows.append(entry)
                if sampled_rows:
                    fields = sorted(str(key) for key in sampled_rows[0])
                    kept = _sampled_rows(
                        [[_scalar_text(row.get(name)) for name in fields]
                         for row in sampled_rows], fields, row_allowance)
                    profile["fields"] = fields
                    profile["sampled_row_count"] = len(kept)
                    profile["field_profiles"] = _field_value_profiles([
                        (name, [row[index] for row in kept])
                        for index, name in enumerate(fields)])
                profile["data_row_count"] = len(lines)
        profiles.append(profile)
    return {
        "record_type": "source_profile_result/v1",
        "profiles": profiles,
        "profiled_count": len(profiles),
        "source_exclusions": [item.to_dict() for item in inventory.records
                              if item.disposition == "excluded"],
        "usage": (
            "field_profiles states what each field's sampled values are, not "
            "what the field is for. A field name is not its type: read "
            "every_sampled_value_is_a_number and example_values before "
            "deciding whether a field holds quantities or labels, and prefer "
            "what the values show over what the header suggests"),
    }


def _saved_record_is_bounded() -> bool:
    """A saved body is bounded, marked as elided, and small bodies are not."""
    large = saved_source_inspections([{"selected": [
        {"path": "data/train.csv", "digest": "d",
         "content": "x" * (_SAVED_CONTENT_BYTE_LIMIT * 3)}]}])
    row = large[0]["selected"][0]
    small = saved_source_inspections([{"selected": [
        {"path": "tiny.csv", "content": "a,b\n1,2\n"}]}])[0]["selected"][0]
    return (len(row["content"]) <= _SAVED_CONTENT_BYTE_LIMIT
            and row.get("content_elided") is True
            and row.get("content_available_at") == "data/train.csv"
            and "content_elided" not in small
            and small["content"] == "a,b\n1,2\n")


def self_test() -> dict:
    """Run focused source admission and model-projection checks."""
    from .source_admission_checks import run_checks
    return run_checks()


__all__ = (
    "SourceAdmissionRecord", "SourceInventory", "inventory_source_files",
    "inspectable_source_files", "project_input_path",
    "source_inspection_model_view", "source_inspection_operation",
)
