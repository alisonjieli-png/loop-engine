"""Prepare bounded, offline harness candidates from pinned local sources.

The input is ``harness_candidate_batch_proposals/v1`` for individual bodies, or
version two for complete native packages. Its source revision must
be this checkout's HEAD; every named source and the MIT licence file must have
the declared SHA-256 digest and the same bytes at that revision. This tool
creates only a new candidate catalogue folder. It neither judges the authored
text nor approves, stages, installs, serves, or publishes it.

    PYTHONPATH=src python3 tools/prepare_harness_candidates.py \\
      --repository . --proposals proposals.json --output candidate-batch-001 \\
      --authorize-preparation

The resulting items and population files use the starter catalogue's current
record versions and can be checked with its ``refresh.py`` and the existing
candidate compiler. A later independent review is still mandatory.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # File-path invocation is a launcher; contracts belong to the canonical module.
    from tools.prepare_harness_candidates import main as canonical_main
    raise SystemExit(canonical_main())

from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
from loop_engine.core.intelligence_tagging import TagSet
from loop_engine.core.service_runtime.catalogue_bundle import strict_json
from loop_engine.core.service_runtime.records import ServiceRuntimeError

INPUT_TYPE = "harness_candidate_batch_proposals/v1"
NATIVE_INPUT_TYPE = "harness_candidate_batch_proposals/v2"
ITEMS_TYPE = "starter_catalogue_candidate_items/v2"
SPECIFICATIONS_TYPE = "candidate_intelligence_specifications/v1"
REPORT_TYPE = "harness_candidate_preparation_report/v1"
POPULATION_SIZE = 50
MAXIMUM_CANDIDATES = 5000
MAXIMUM_INPUT_BYTES = 64 * 1024 * 1024
MAXIMUM_BODY_CHARACTERS = 12000
REVISION = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")
SPEC_FAMILY = re.compile(r"[a-z][a-z0-9_]*\Z")
LAYERS = frozenset(("context", "code", "runtime_history_solution", "user_feedback"))
INPUT_FIELDS = frozenset(("record_type", "source_revision", "license", "sources", "proposals"))
PROPOSAL_FIELDS = frozenset(("id", "title", "purpose", "body", "sources", "layer", "family",
                            "search_tags", "tags", "symbols", "declared_effects"))
REQUIRED_PROPOSAL_FIELDS = PROPOSAL_FIELDS - {"symbols", "declared_effects"}


class PreparationError(ValueError):
    """A typed, body-free reason the preparation cannot proceed."""


@dataclass(frozen=True)
class PreparationRequest:
    repository: Path
    proposals: Path
    output: Path
    writes_authorized: bool = False


def _refuse(code: str, detail: str = "") -> None:
    raise PreparationError(f"{code}: {detail}" if detail else code)


def _object(value, expected: set[str], code: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        _refuse(code)
    return value


def _digest_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _text(value, code: str, *, maximum: int, one_line: bool = False) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _refuse(code)
    if "\x00" in value or (one_line and ("\n" in value or "\r" in value)):
        _refuse(code)
    if one_line and any(ord(character) < 32 for character in value):
        _refuse(code)
    return value


def _relative_path(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or ":" in value:
        _refuse("unsafe_source_path")
    path = PurePosixPath(value)
    parts = value.split("/")
    if path.is_absolute() or any(part in ("", ".", "..") or part.startswith(".") for part in parts):
        _refuse("unsafe_source_path")
    return tuple(parts)


def _regular_source(repository: Path, relative: str) -> Path:
    parts = _relative_path(relative)
    path = repository
    for part in parts:
        path = path / part
        if path.is_symlink():
            _refuse("source_symlink_refused", relative)
    if not path.is_file() or repository not in path.resolve().parents:
        _refuse("source_missing_or_escaped", relative)
    return path


def _git(repository: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(["git", "-C", str(repository), *arguments],
                                capture_output=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        _refuse("revision_unreadable")
    if result.returncode != 0:
        _refuse("revision_unreadable")
    return result.stdout


def _committed_bytes(repository: Path, revision: str, relative: str) -> bytes:
    tree_row = _git(repository, "ls-tree", "-z", revision, "--", relative).split(b"\0")[0]
    try:
        head, recorded = tree_row.split(b"\t", 1)
        mode, object_type, _object_id = head.split(b" ", 2)
        if recorded.decode("utf-8") != relative or mode not in (b"100644", b"100755") \
                or object_type != b"blob":
            _refuse("source_not_regular_at_revision", relative)
    except (UnicodeDecodeError, ValueError):
        _refuse("source_not_regular_at_revision", relative)
    return _git(repository, "show", f"{revision}:{relative}")


def _checked_source(repository: Path, revision: str, relative: str, declared_digest: str) -> str:
    if not isinstance(declared_digest, str) or DIGEST.fullmatch(declared_digest) is None:
        _refuse("source_digest_mismatch", relative)
    current = _regular_source(repository, relative).read_bytes()
    committed = _committed_bytes(repository, revision, relative)
    if current != committed:
        _refuse("source_bytes_changed", relative)
    measured = _digest_of(current)
    if measured != declared_digest:
        _refuse("source_digest_mismatch", relative)
    return measured


def _output_path(path: Path) -> Path:
    absolute = path.absolute()
    if ".." in path.parts or absolute.exists() or absolute.is_symlink():
        _refuse("output_already_exists" if absolute.exists() or absolute.is_symlink()
                else "unsafe_output_path")
    if not absolute.parent.is_dir() or absolute.resolve() != absolute:
        _refuse("unsafe_output_path")
    return absolute


def _input_record(request: PreparationRequest) -> tuple[dict, bytes]:
    if (request.proposals.is_symlink() or not request.proposals.is_file()
            or request.proposals.absolute().resolve() != request.proposals.absolute()):
        _refuse("proposals_not_regular")
    if request.proposals.stat().st_size > MAXIMUM_INPUT_BYTES:
        _refuse("proposals_too_large")
    raw = request.proposals.read_bytes()
    try:
        value = strict_json(raw, "proposals_unreadable")
    except ServiceRuntimeError:
        _refuse("proposals_unreadable")
    _object(value, INPUT_FIELDS, "unsupported_proposal_contract")
    if value["record_type"] not in (INPUT_TYPE, NATIVE_INPUT_TYPE):
        _refuse("unsupported_proposal_contract")
    return value, raw


def _validated_sources(repository: Path, record: dict) -> tuple[str, dict[str, str], str]:
    revision = record["source_revision"]
    if not isinstance(revision, str) or REVISION.fullmatch(revision) is None \
            or _git(repository, "rev-parse", "HEAD").decode("ascii").strip() != revision:
        _refuse("revision_mismatch")
    license_record = _object(record["license"], {"expression", "path", "sha256"},
                             "unknown_license")
    if license_record["expression"] != "MIT" or license_record["path"] != "LICENSE":
        _refuse("unknown_license")
    license_digest = _checked_source(repository, revision, "LICENSE", license_record["sha256"])
    try:
        license_text = (repository / "LICENSE").read_text(encoding="utf-8")
    except UnicodeDecodeError:
        _refuse("unknown_license")
    if (not license_text.startswith("MIT License\n")
            or "Permission is hereby granted" not in license_text
            or "copies or substantial portions of the Software" not in license_text
            or 'THE SOFTWARE IS PROVIDED "AS IS"' not in license_text):
        _refuse("unknown_license")
    sources = record["sources"]
    if not isinstance(sources, dict) or not sources:
        _refuse("sources_required")
    measured = {"LICENSE": license_digest}
    for relative, declared in sources.items():
        if relative == "LICENSE":
            _refuse("license_is_not_an_item_source")
        measured[relative] = _checked_source(repository, revision, relative, declared)
    return revision, measured, "MIT"


def _string_list(value, code: str, *, maximum: int, may_be_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not may_be_empty) or len(value) > maximum:
        _refuse(code)
    if any(not isinstance(item, str) or not item.strip() or len(item) > 160 for item in value):
        _refuse(code)
    if len(value) != len(set(value)):
        _refuse(code)
    return value


def _compile(record: dict, revision: str, source_digests: dict[str, str], license_name: str):
    proposals = record["proposals"]
    if not isinstance(proposals, list) or not 1 <= len(proposals) <= MAXIMUM_CANDIDATES:
        _refuse("candidate_population_out_of_bounds")
    bodies, specification_rows, item_rows, identities, used_sources = {}, [], [], set(), set()
    for proposal in proposals:
        if not isinstance(proposal, dict) or not REQUIRED_PROPOSAL_FIELDS <= set(proposal) \
                or set(proposal) - PROPOSAL_FIELDS:
            _refuse("invalid_candidate_fields")
        identity = proposal["id"]
        if not isinstance(identity, str) or len(identity) > 64 or IDENTITY.fullmatch(identity) is None:
            _refuse("unsafe_identity")
        if identity in identities:
            _refuse("duplicate_identity", identity)
        identities.add(identity)
        title = _text(proposal["title"], "invalid_title", maximum=160, one_line=True)
        purpose = _text(proposal["purpose"], "invalid_purpose", maximum=1024, one_line=True)
        body = _text(proposal["body"], "invalid_body", maximum=MAXIMUM_BODY_CHARACTERS)
        if body.startswith("---\n") or not body.startswith(f"# {title}\n"):
            _refuse("body_format_invalid", identity)
        cited = _string_list(proposal["sources"], "invalid_candidate_sources", maximum=20)
        if any(source not in source_digests or source == "LICENSE" for source in cited):
            _refuse("source_not_declared", identity)
        used_sources.update(cited)
        if not isinstance(proposal["layer"], str) or proposal["layer"] not in LAYERS \
                or not isinstance(proposal["family"], str) \
                or SPEC_FAMILY.fullmatch(proposal["family"]) is None:
            _refuse("invalid_classification", identity)
        search_tags = _string_list(proposal["search_tags"], "invalid_search_tags", maximum=20)
        symbols = _string_list(proposal.get("symbols", []), "invalid_symbols", maximum=30, may_be_empty=True)
        effects = _string_list(proposal.get("declared_effects", []), "invalid_effects",
                               maximum=20, may_be_empty=True)
        raw_tags = proposal["tags"]
        if not isinstance(raw_tags, dict) or "lifecycle" in raw_tags:
            _refuse("lifecycle_not_candidate", identity)
        if any(not isinstance(values, list) or any(not isinstance(value, str) or
               not value.strip() or len(value) > 160 for value in values)
               for values in raw_tags.values()):
            _refuse("invalid_tags", identity)
        try:
            tags = TagSet({**raw_tags, "lifecycle": ["candidate"]})
            draft = HarnessIntelligenceDraft(identity, "skill", purpose, "harness_local",
                f"{cited[0]}@{revision}", license_name, tuple(effects), (), "metadata_only",
                "remote", tags=tags)
            item = item_from_body(draft, body)
        except (TypeError, ValueError) as error:
            _refuse("invalid_harness_item", f"{identity}: {type(error).__name__}")
        try:
            bodies[identity] = body.encode("utf-8")
        except UnicodeEncodeError:
            _refuse("invalid_body", identity)
        specification_rows.append({"id": identity, "layer": proposal["layer"],
            "family": proposal["family"], "title": title, "tags": search_tags,
            "text": body, "sources": [*cited, "LICENSE"], "symbols": symbols})
        item_rows.append({"reference": item.reference(), "body_path": f"bodies/{identity}.md"})
    if used_sources != set(record["sources"]):
        _refuse("unused_source_declaration")
    return bodies, specification_rows, item_rows


def prepare(request: PreparationRequest) -> dict:
    """Create one exclusive, candidate-only folder after all pure preflight checks."""
    if not isinstance(request, PreparationRequest) or request.writes_authorized is not True:
        _refuse("preparation_not_authorized")
    repository = request.repository.absolute()
    if not repository.is_dir() or repository.resolve() != repository:
        _refuse("repository_not_regular")
    output = _output_path(request.output)
    record, raw = _input_record(request)
    revision, source_digests, license_name = _validated_sources(repository, record)
    if record["record_type"] == NATIVE_INPUT_TYPE:
        from tools.native_harness_candidates import prepare_native
        native_request = PreparationRequest(repository, request.proposals, output, True)
        return prepare_native(native_request, record, raw, revision, source_digests, license_name)
    bodies, rows, items = _compile(record, revision, source_digests, license_name)
    # A concurrent edit after the first read cannot silently change the
    # evidence the output claims. The commit remains the ultimate source.
    if _git(repository, "rev-parse", "HEAD").decode("ascii").strip() != revision:
        _refuse("revision_mismatch")
    for relative, digest in source_digests.items():
        if _digest_of(_regular_source(repository, relative).read_bytes()) != digest:
            _refuse("source_bytes_changed", relative)
    count = (len(rows) + POPULATION_SIZE - 1) // POPULATION_SIZE
    population_names = [f"specifications-{number:03d}.json" for number in range(1, count + 1)]
    catalogue = {"record_type": ITEMS_TYPE, "source_revision": revision,
                 "previous_source_revisions": [], "source_digests": source_digests,
                 "publication": "not_published", "items": items}
    report = {"record_type": REPORT_TYPE, "complete": True, "candidates": len(rows),
              "population_files": population_names, "source_revision": revision,
              "input_sha256": _digest_of(raw), "source_files": len(source_digests),
              "approved": False, "hosted_publication": False,
              "semantic_grounding_verified": False,
              "limits": "Offline byte-pinned preparation only; source meaning, rights for each cited file, safety, usefulness and native loading remain unreviewed."}
    try:
        documents = {"items.json": _json_bytes(catalogue),
                     "preparation-report.json": _json_bytes(report)}
        for number, name in enumerate(population_names, start=1):
            start = (number - 1) * POPULATION_SIZE
            population = {"record_type": SPECIFICATIONS_TYPE, "population": number,
                          "populations": count, "specifications": rows[start:start + POPULATION_SIZE]}
            documents[name] = _json_bytes(population)
    except (TypeError, UnicodeEncodeError):
        _refuse("candidate_record_unserializable")
    try:
        output.mkdir(mode=0o700)
    except FileExistsError:
        _refuse("output_already_exists")
    (output / "bodies").mkdir(mode=0o700)
    for identity, payload in bodies.items():
        with (output / "bodies" / f"{identity}.md").open("xb") as stream:
            stream.write(payload)
    for name in [*population_names, "items.json", "preparation-report.json"]:
        with (output / name).open("xb") as stream:
            stream.write(documents[name])
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare an offline, candidate-only harness batch of bodies or complete native packages.",
        epilog="Input format and limits: tools/PREPARE-HARNESS-CANDIDATES.md")
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorize-preparation", action="store_true")
    options = parser.parse_args(argv)
    try:
        report = prepare(PreparationRequest(options.repository, options.proposals,
                                            options.output, options.authorize_preparation))
    except PreparationError as error:
        print(json.dumps({"record_type": REPORT_TYPE, "complete": False, "refusal": str(error)}))
        return 1
    print(json.dumps(report))
    return 0
