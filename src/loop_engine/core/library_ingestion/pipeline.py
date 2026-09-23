"""The ingestion pipeline: from source candidates to staging rows, outlines and refusals.

It runs after the source engines and before the staging tool, and it is
pure: every engine it uses is handed in, already selected and recorded.
For each candidate, the licence evidence decides the path. A refused source
leaves only its refusal. An outline-only source leaves an outline of its
abstract purpose. A verbatim source is rendered into its native file and
must pass the format engines, the size and body bounds and the bundled-file
rule. A registry entry is rendered into connection files from its facts and
must pass the format engines and the package check. Every rendered package
then goes to every safety engine; a blocking finding refuses it by name.
A verbatim item whose text repeats the text of a refused or outline-only
source in the same run is refused as a copy of a restricted source: a
permissive collection that holds a copy of a restricted original does not
license the copy. Survivors are grouped into exact and near duplicates, and
each kept item becomes one staging row whose provenance lists every merged
source. Every candidate is counted exactly once, and nothing is approved or
served here.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .candidates import REASONS, SKILL, TOOL, read_candidate_batch, refusal, source_ref
from .connection_rendering import NPM, PYPI, endpoint_identity, render_connection
from .duplicates import DuplicateSubject, group_duplicates, normalized, shingles
from .effects import declared_effects
from .licences import is_licence_file, is_notice_file
from .outline_model import CallCeilingReached, OutlineCallFailed
from .provenance import LINK_ONLY, OUTLINE_ONLY, REFUSED, VERBATIM, read_outside_provenance
from .record_rules import bytes_digest
from .rendering_types import RenderRefused
from .skill_rendering import parse_skill, render_instruction, render_skill
from .staging_rows import GENERATED_FROM_FACTS, IMPORTED_VERBATIM, specification_row
from .topics import topic_words

RESULT_RECORD_TYPE = "library_ingestion_result/v1"
PRODUCER = "library_ingestion_pipeline/v1"
#: Codex's presentation metadata beside a skill; the skill works without it.
_OPTIONAL_FILES = re.compile(r"(?:^|/)agents/openai\.ya?ml\Z")


@dataclass(frozen=True)
class PipelineSettings:
    maximum_text_characters: int = 65_536
    minimum_body_characters: int = 200
    near_duplicate_threshold: float = 0.85
    source_order: tuple = ()


@dataclass
class PipelineEngines:
    validators: tuple
    scanners: tuple
    near_duplicate: object
    outline: object
    fallback_outline: object
    package_resolver: object = None
    decisions: tuple = ()


@dataclass
class _Item:
    candidate: dict
    source_id: str
    package: object
    effects: object
    tags: list
    comparison: str
    exact_only: bool
    authoring: str
    license_expression: str
    roles: dict
    triage: list = field(default_factory=list)
    scan_files: tuple = ()


def _stage_for(code: str) -> str:
    for stage in ("registry", "format", "size", "render", "outline"):
        if code in REASONS[stage]:
            return stage
    return "render"


def _refuse(refusals, candidate, code, detail, stage=None):
    stage = stage or _stage_for(code)
    code = code if code in REASONS[stage] else "render_failed"
    refusals.append(refusal(stage, code, detail, source=source_ref(candidate["provenance"]),
                            key=candidate["candidate_key"]))


def _attachments(quarantine, evidence) -> tuple:
    """The governing licence file and every notice file, read back from quarantine."""
    governing = evidence.get("governing_file")
    licence = (governing["path"], quarantine.get(governing["sha256"])) if governing else None
    notices = tuple((row["path"], quarantine.get(row["sha256"])) for row in evidence["file_level_notices"]
                    if row["kind"] == "notice_file")
    return licence, notices


def _distinctive(word: str) -> bool:
    """A name long and unusual enough that seeing it alone in prose means this file or folder."""
    return len(word) >= 6 and any(mark in word for mark in "-_.")


def reference_spellings(path: str) -> tuple:
    """Every spelling by which a skill's text can point at one of its bundled files.

    The path itself, its file name when that is distinctive, each folder above
    it written as a folder (with a trailing slash, a leading ./ or in code
    quotes), a distinctive folder name on its own, and for a Python file its
    dotted module name and a distinctive stem, because a skill often imports
    its helper code (from core.gif_builder import ...) without naming a file.
    """
    location = PurePosixPath(path)
    spellings = {path, "./" + path}
    if _distinctive(location.name):
        spellings.add(location.name)
    folders = location.parent.parts
    for depth in range(1, len(folders) + 1):
        folder = "/".join(folders[:depth])
        spellings.update({folder + "/", "./" + folder, "`" + folder + "`"})
        if _distinctive(folders[depth - 1]):
            spellings.add(folders[depth - 1])
    if location.suffix == ".py":
        spellings.add(".".join((*folders, location.stem)))
        if _distinctive(location.stem):
            spellings.add(location.stem)
    return tuple(sorted(spellings))


def _mentions(text: str, spelling: str) -> bool:
    """True when the spelling stands in the text on its own, not inside a longer name.

    Nothing that belongs to a name may come before it, so ../core is not
    ./core; and when the spelling ends in a letter, digit or underscore,
    nothing that belongs to a name may follow it, so core_extra is not core.
    A folder spelling that ends in a slash may be followed by anything.
    """
    after = r"(?![A-Za-z0-9_-])" if spelling[-1].isalnum() or spelling[-1] == "_" else ""
    return re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(spelling) + after, text) is not None


def _bundled(candidate, text) -> tuple:
    """The bundled files a skill's text points at, and every bundled file beside it."""
    extra = [path for path in candidate["package_paths"]
             if not is_licence_file(path) and not is_notice_file(path) and not _OPTIONAL_FILES.search(path)]
    referenced = [path for path in extra
                  if any(_mentions(text, spelling) for spelling in reference_spellings(path))]
    return referenced, extra


def _roles(package, licence, notices) -> dict:
    roles = {}
    for path, _ in package.files:
        name = PurePosixPath(path).name
        if licence and name == PurePosixPath(licence[0]).name and path != package.main_path:
            roles[path] = "licence"
        elif any(name == PurePosixPath(notice[0]).name for notice in notices) and path != package.main_path:
            roles[path] = "notice"
    return roles


def _prepare_file(candidate, source_id, provenance, quarantine, engines, settings, refusals):
    text = quarantine.get(provenance.source_digest).decode("utf-8")
    licence, notices = _attachments(quarantine, provenance.licence_evidence)
    try:
        if candidate["kind"] == SKILL:
            parsed = parse_skill(text)
            referenced, extra = _bundled(candidate, parsed.body)
            if referenced:
                raise RenderRefused("bundled_files_not_supported_yet",
                                    f"the skill refers to {len(referenced)} bundled file(s), for example "
                                    f"{referenced[0][:120]}")
            package = render_skill(parsed, provenance, licence_file=licence, notice_files=notices)
            body, frontmatter = parsed.body, parsed.frontmatter
            for validator in engines.validators:
                if SKILL in validator.applies_to:
                    problems = validator.validate_skill(package.folder, package.main_text)
                    if problems:
                        code = ("reference_validator_refused" if validator.engine_id
                                == "agent_skills_reference_validator" else "frontmatter_invalid")
                        raise RenderRefused(code, f"{validator.engine_id}: {problems[0][:200]}")
            name_words = (candidate["name"], str(frontmatter.get("description") or ""), package.title)
            tags = ["agent skill", *topic_words(*name_words)]
            triage = [f"pipeline:omitted_unreferenced_files_{len(extra)}"] if extra else []
        else:
            package = render_instruction(text, provenance, candidate["native_format"], candidate["name"],
                                         licence, notices)
            body, frontmatter, triage = text, {}, []
            label = "copilot instructions" if candidate["native_format"] == "copilot_instructions" else "cursor rules"
            tags = ["instruction file", label, *topic_words(candidate["name"], package.title, text[:2000])]
    except RenderRefused as error:
        _refuse(refusals, candidate, error.code, error.detail)
        return None
    if len(package.main_text) > settings.maximum_text_characters:
        _refuse(refusals, candidate, "body_exceeds_staging_limit",
                f"{len(package.main_text)} characters, above {settings.maximum_text_characters}", "size")
        return None
    if len(body.strip()) < settings.minimum_body_characters:
        _refuse(refusals, candidate, "body_too_short", f"{len(body.strip())} characters of body", "format")
        return None
    effects = declared_effects(candidate["kind"], body, frontmatter)
    return _Item(candidate, source_id, package, effects, tags, body, False, IMPORTED_VERBATIM,
                 provenance.spdx, _roles(package, licence, notices), triage, package.files)


def _prepare_connection(candidate, source_id, provenance, quarantine, engines, refusals):
    raw = quarantine.get(provenance.source_digest)
    try:
        entry = json.loads(raw)
    except ValueError:
        _refuse(refusals, candidate, "entry_unreadable", "the quarantined entry is not JSON", "registry")
        return None
    # A rendering refusal is itself a ValueError, so it is caught on its own and keeps its
    # reason; anything else a malformed entry raises is an unreadable entry.
    try:
        package = render_connection(entry, provenance)
    except RenderRefused as error:
        _refuse(refusals, candidate, error.code, error.detail)
        return None
    except (ValueError, TypeError, AttributeError, KeyError) as error:
        _refuse(refusals, candidate, "entry_unreadable", f"the entry does not have the documented shape "
                                                         f"({type(error).__name__})", "registry")
        return None
    document, triage = package.document, []
    server = document["server"]
    if server["package"] is not None and server["package"]["registry"] in (NPM, PYPI):
        verdict = engines.package_resolver.resolves(server["package"]) if engines.package_resolver else None
        if verdict is False:
            _refuse(refusals, candidate, "package_does_not_resolve",
                    f"{server['package']['registry']} has no {server['package']['identifier']} "
                    f"{server['package']['version']}", "registry")
            return None
        if verdict is None:
            triage.append("pipeline:package_resolution_not_checked")
    for validator in engines.validators:
        if TOOL in validator.applies_to:
            problems = validator.validate_package(document)
            if problems:
                _refuse(refusals, candidate, "connection_schema_refused",
                        f"{validator.engine_id}: {problems[0][:200]}", "format")
                return None
    if provenance.spdx in ("NONE", "NOASSERTION"):
        triage.append(f"pipeline:upstream_licence_{provenance.licence_evidence['reason']}")
    identity = endpoint_identity(document)
    effects = declared_effects(TOOL, "", {}, connection=document)
    tags = ["protocol server", "mcp", server["transport"], *document["topic_words"]]
    scan = package.files + (("registry-entry.json", raw),)
    return _Item(candidate, source_id, package, effects, tags, identity, True, GENERATED_FROM_FACTS, "MIT",
                 {"baltor-connection.json": "package_document"}, triage, scan)


def _restricted_text(candidate, provenance, quarantine) -> str:
    """The text a copy of a restricted source would repeat: a skill's body, or the whole file."""
    text = quarantine.get(provenance.source_digest).decode("utf-8", "replace")
    if candidate["kind"] == SKILL:
        try:
            return parse_skill(text).body
        except RenderRefused:
            return text
    return text


def restricted_copies(items, restricted, engine, threshold: float) -> dict:
    """Item key to the restricted source its text repeats, exactly or at the near-duplicate threshold.

    `restricted` holds (key, text, label) for every refused or outline-only
    file candidate of the run. A connection is written from facts and is never
    compared.
    """
    found = {}
    exact = {bytes_digest(normalized(text).encode("utf-8")): label for _key, text, label in restricted}
    documents, labels = {}, {}
    for key, text, label in restricted:
        value = shingles(text)
        if value:
            documents["restricted:" + key], labels["restricted:" + key] = value, label
    for item in items:
        if item.exact_only:
            continue
        key = item.candidate["candidate_key"]
        digest = bytes_digest(normalized(item.comparison).encode("utf-8"))
        if digest in exact:
            found[key] = exact[digest]
            continue
        value = shingles(item.comparison)
        if value:
            documents["item:" + key] = value
    if labels and len(documents) > len(labels):
        for left, right, _estimate in engine.pairs(documents, threshold):
            if left.startswith("item:") and right.startswith("restricted:"):
                found.setdefault(left[len("item:"):], labels[right])
    return found


def _outline(candidate, provenance, quarantine, engines, refusals, notes):
    text = quarantine.get(provenance.source_digest).decode("utf-8", "replace")
    for engine in (engines.outline, engines.fallback_outline):
        try:
            return engine.outline(candidate, text)
        except (CallCeilingReached, OutlineCallFailed) as error:
            notes.append(f"{engine.engine_id}:{type(error).__name__}")
        except RenderRefused as error:
            notes.append(f"{engine.engine_id}:{error.code}")
            if engine is engines.fallback_outline:
                _refuse(refusals, candidate, error.code, error.detail, "outline")
                return None
    _refuse(refusals, candidate, "outline_generation_failed", "no outline engine returned an outline", "outline")
    return None


def run_pipeline(batches, quarantine, engines: PipelineEngines, settings: PipelineSettings) -> dict:
    """Return library_ingestion_result/v1 for the given source batches."""
    rank = {source_id: index for index, source_id in enumerate(settings.source_order)}
    refusals, outlines, items, notes, restricted = [], [], [], [], []
    decisions = Counter()
    candidates = batch_refusals = 0
    for batch in batches:
        source_id = batch["source_id"]
        if batch.get("record_type"):
            read_candidate_batch(batch)
        refusals.extend(batch["refusals"])
        batch_refusals += len(batch["refusals"])
        for candidate in batch["candidates"]:
            candidates += 1
            provenance = read_outside_provenance(candidate["provenance"])
            decisions[provenance.decision] += 1
            if provenance.decision in (REFUSED, OUTLINE_ONLY) and candidate["kind"] != TOOL:
                restricted.append((candidate["candidate_key"], _restricted_text(candidate, provenance, quarantine),
                                   f"{provenance.repository}/{provenance.path} ({provenance.decision})"))
            if provenance.decision == REFUSED:
                _refuse(refusals, candidate, "licence_refused", provenance.licence_evidence["reason"], "licence")
            elif provenance.decision == OUTLINE_ONLY:
                _refuse(refusals, candidate, "licence_outline_only", provenance.licence_evidence["reason"],
                        "licence")
                outline = _outline(candidate, provenance, quarantine, engines, refusals, notes)
                if outline is not None:
                    outlines.append(outline)
            elif provenance.decision == VERBATIM:
                item = _prepare_file(candidate, source_id, provenance, quarantine, engines, settings, refusals)
                if item is not None:
                    items.append(item)
            elif provenance.decision == LINK_ONLY:
                item = _prepare_connection(candidate, source_id, provenance, quarantine, engines, refusals)
                if item is not None:
                    items.append(item)
    copies = restricted_copies(items, restricted, engines.near_duplicate, settings.near_duplicate_threshold)
    for item in items:
        if item.candidate["candidate_key"] in copies:
            _refuse(refusals, item.candidate, "copy_of_restricted_source",
                    f"repeats {copies[item.candidate['candidate_key']]}"[:300], "licence")
    items = [item for item in items if item.candidate["candidate_key"] not in copies]
    packages = {item.candidate["candidate_key"]: item.scan_files for item in items}
    findings = {key: [] for key in packages}
    for scanner in engines.scanners:
        for key, rows in scanner.scan_packages(packages).items():
            findings[key].extend(rows)
    survivors = []
    for item in items:
        blocking = sorted({row["rule"] for row in findings[item.candidate["candidate_key"]]
                           if row["severity"] == "blocking"})
        if blocking:
            _refuse(refusals, item.candidate, "safety_scan_blocked", ", ".join(blocking)[:280], "safety")
            continue
        item.triage += [f"{row['engine_id']}:{row['rule']}" for row in findings[item.candidate["candidate_key"]]]
        survivors.append(item)
    by_key = {item.candidate["candidate_key"]: item for item in survivors}
    subjects = [DuplicateSubject(key, (rank.get(item.source_id, len(rank)), item.candidate["provenance"]["path"],
                                       key), item.comparison, item.exact_only) for key, item in by_key.items()]
    kept, links = group_duplicates(subjects, engines.near_duplicate, settings.near_duplicate_threshold)
    merged: dict = {}
    for link in links:
        merged.setdefault(link["kept"], []).append(link["merged"])
    rows = []
    for key in kept:
        item = by_key[key]
        provenance_list = [item.candidate["provenance"]] + [by_key[other].candidate["provenance"]
                                                            for other in merged.get(key, ())]
        rows.append(specification_row(candidate=item.candidate, package=item.package,
                                      provenance_records=provenance_list, effects=item.effects.effects,
                                      triage=item.triage, tags=item.tags,
                                      license_expression=item.license_expression, authoring=item.authoring,
                                      roles=item.roles))
    after_licence = sum(1 for row in refusals if row["stage"] in ("format", "size", "safety", "render", "registry")
                        and row["candidate_key"] is not None)
    reasons = Counter(f"{row['stage']}/{row['reason']}" for row in refusals)
    counts = {"candidates": candidates, "batch_refusals": batch_refusals,
              "discovered": candidates + batch_refusals,
              "by_licence_decision": dict(sorted(decisions.items())),
              "licence_refused": decisions[REFUSED], "outline_only": decisions[OUTLINE_ONLY],
              "restricted_copies": len(copies),
              "outlines_written": len(outlines), "refused_after_licence": after_licence,
              "exact_duplicates": sum(1 for link in links if link["kind"] == "exact"),
              "near_duplicates": sum(1 for link in links if link["kind"] == "near"),
              "staged_rows": len(rows), "staged_by_kind": dict(Counter(row["kind"] for row in rows)),
              "refused_by_reason": dict(sorted(reasons.items())), "outline_notes": dict(Counter(notes))}
    calls = list(getattr(engines.outline, "calls", ()))
    return {"record_type": RESULT_RECORD_TYPE, "producer": PRODUCER, "counts": counts, "rows": rows,
            "refusals": refusals, "outlines": outlines, "duplicates": links,
            "engine_decisions": list(engines.decisions), "model_calls": calls}
