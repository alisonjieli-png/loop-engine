"""Deterministic structure profiles of admitted supplied sources.

The profile operation reports what a supplied table or record file contains:
field names, row counts, and bounded value profiles read under the run's
measured byte allowance. It never selects a source, never sends a body to a
model, and grants no authority. It moved here from adaptive_practitioner_source
so that module has room for source admission and selection; that module
re-exports ``source_profile_operation`` for existing callers.
"""
from __future__ import annotations

import csv
import json
import mimetypes

from .adaptive_practitioner_records import (
    AdaptiveRunServices)
from .adaptive_practitioner_validation import AdaptivePractitionerError
from .capability_rejection import (CapabilityRejected, CapabilityRejection,
                                   bounded_admitted_values)
from .runtime_capacity import converged, model_evidence_bytes


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
    # Imported at call time: adaptive_practitioner_source re-exports this
    # operation, and a call-time import also sees any replacement of these
    # helpers on that module.
    from .adaptive_practitioner_source import (
        _exclusion_matches, _read_source_bytes, _resolve_requested_paths,
        _source_text, inventory_source_files)
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
            "; inspect manifest_paths from core.source.inspect first. Exclusions: "
            + str(_exclusion_matches(unknown, inventory.records)),
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


__all__ = ("PROFILE_EXAMPLE_VALUE_LIMIT", "PROFILE_VALUE_TEXT_LIMIT",
           "source_profile_operation")
