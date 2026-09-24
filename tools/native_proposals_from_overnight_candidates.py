"""Turn overnight batch candidates into version-two native proposals for the candidate factory.

The overnight candidate batch (``tools/overnight_candidate_batch.py``) writes one
Markdown file per idea under ``candidates/<lane>/<idea>.md`` and journals every
dispatch and outcome. This tool is the adapter between that layout and the
existing factory (``tools/prepare_harness_candidates.py``); it judges nothing and
approves nothing. It works in two steps, because the factory reads sources only
as committed at the checkout's commit:

1. ``attribute`` reads the batch without changing it. Each candidate file is
   attributed to the lane the journal records as having written it, and to the
   idea record the producer was given: the batch selected its ideas with
   ``select_stratified`` of ``tools/overnight_candidate_batch.py``, which
   replaces each idea's occupation and task statement with the next one of the
   pinned occupation rotation, so the matrix record alone is not the brief. Each
   matrix is declared with the time it took effect and the number of ideas the
   batch selected from it, and the adapter repeats that selection after
   checking that every pinned source still has the digest the matrix names. It
   writes each idea record as its own small source file, and one attribution
   record naming every candidate's bytes by digest, the lane, the model the
   batch status names for the lane, the family the operator declares for the
   lane (a family is never inferred from a name), the file kind the producer was
   asked for, and every file it could not attribute with the reason.
2. ``proposals`` reads the committed attribution record, checks every candidate
   file still has the recorded bytes, and writes one version-two proposal per
   candidate whose file kind has a qualified native placement: a skill becomes
   ``SKILL.md`` with the skill definition role, and a harness routing file
   becomes ``AGENTS.md`` with the instruction file role. Every proposal is then
   put through the factory's own preparation alone, into a temporary folder, and
   a proposal the factory refuses is kept out of the batch with the factory's
   refusal code, so one bad candidate cannot refuse the others.

The producers wrote their effects in prose only. Every converted package is
instruction-only and declares the read-only file effect, the narrowest effect
under which a harness can follow instructions on a step's files; the reviewers
judge whether that covers every operation the file asks for, and the effects
pre-check refuses a file that holds a shell block without the process effect.

    PYTHONPATH=src python tools/native_proposals_from_overnight_candidates.py attribute \\
        --batch-directory BATCH --matrix MATRIX.json@2026-09-24T04:49:38Z@1000 \\
        --matrix MATRIX-10K.json@2026-09-24T07:45:19Z@10000 --lane LANE=FAMILY --output FOLDER

    PYTHONPATH=src python tools/native_proposals_from_overnight_candidates.py proposals \\
        --repository . --attribution FOLDER/attribution.json --batch-directory BATCH --output proposals.json
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.native_proposals_from_overnight_candidates import main as canonical_main
    raise SystemExit(canonical_main())

from tools import prepare_harness_candidates as factory

ATTRIBUTION_TYPE = "overnight_candidate_attribution/v2"
REPOSITORY = Path(__file__).resolve().parents[1]
REPORT_TYPE = "overnight_candidate_conversion_report/v1"
IDEA_TYPE = "harness_idea_record/v1"
JOURNAL_EVENT_TYPE = "overnight_batch_event/v1"
STATUS_TYPE = "overnight_batch_status/v1"
MAXIMUM_CANDIDATE_BYTES = 64 * 1024
IDEA_IDENTITY = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
#: Where each file kind the producers were asked for is placed in a native package, with its role, its item
#: kind, the clients whose native layout reads it, and the specification family. A kind not named here has no
#: qualified native placement in this converter version and is recorded as not converted.
PLACEMENTS = {
    "skill": {"path": "SKILL.md", "role": "skill_definition", "kind": "skill", "styles": ["claude", "codex"],
              "family": "original_native_skill"},
    "harness_routing": {"path": "AGENTS.md", "role": "instruction_file", "kind": "instruction_file",
                        "styles": ["codex", "opencode", "pi"], "family": "original_native_instruction"},
}
DECLARED_EFFECTS = ["reads_fs"]
LAYER = "context"
LANGUAGE = "en"


class ConversionError(ValueError):
    """A stable, body-free reason the conversion cannot proceed."""


def refuse(code: str) -> None:
    raise ConversionError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _timestamp(text: str) -> datetime:
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        refuse("timestamp_invalid")
    if moment.tzinfo is None:
        refuse("timestamp_invalid")
    return moment.astimezone(timezone.utc)


def _regular(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        refuse("file_not_regular_or_too_large")
    return path.read_bytes()


def _journal(batch: Path) -> dict:
    """Each (lane, idea) the journal records as written, with the time of the last write."""
    written = {}
    raw = _regular(batch / "journal.jsonl", 512 * 1024 * 1024)
    for line in raw.decode("utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue  # a line still being written by the running batch
        if (type(event) is dict and event.get("record_type") == JOURNAL_EVENT_TYPE and event.get("event") == "outcome"
                and event.get("outcome") == "candidate_written"):
            written[(event.get("lane_id"), event.get("idea_id"))] = event.get("ts")
    return {"written": written, "sha256": digest(raw), "bytes": len(raw)}


def batch_selection(record: dict, count: int) -> list:
    """The ideas the batch selected from one matrix, with the rotated grounding each producer was given."""
    from tools.overnight_candidate_batch import select_stratified
    return select_stratified(record, count)


def _pinned_sources_unchanged(record: dict) -> None:
    """Every pinned source the selection reads must still have the digest the matrix names."""
    for source in record.get("sources", []):
        if not isinstance(source, dict) or source.get("kind") != "onet_pinned":
            continue
        path = REPOSITORY / str(source.get("path", ""))
        if not path.is_file() or digest(path.read_bytes()) != source.get("sha256"):
            refuse("pinned_source_changed")


def _matrices(values) -> list:
    """Declared matrices, each ``PATH@EFFECTIVE_FROM@SELECTED``, ordered by the time each took effect."""
    matrices = []
    for value in values:
        parts = value.rsplit("@", 2)
        if len(parts) != 3 or not parts[2].isdigit() or int(parts[2]) < 1:
            refuse("matrix_declaration_invalid")
        path, moment, count = parts[0], parts[1], int(parts[2])
        raw = _regular(Path(path), 256 * 1024 * 1024)
        record = json.loads(raw)
        _pinned_sources_unchanged(record)
        ideas = {idea["id"]: idea for idea in batch_selection(record, count)}
        matrices.append({"path": str(Path(path).resolve()), "sha256": digest(raw), "effective_from": moment,
                         "moment": _timestamp(moment), "ideas": ideas, "selected": count})
    if not matrices:
        refuse("matrix_required")
    return sorted(matrices, key=lambda matrix: matrix["moment"])


def _matrix_at(matrices, moment: datetime):
    """The matrix in effect at one write: the last one that took effect at or before it."""
    chosen = None
    for matrix in matrices:
        if matrix["moment"] <= moment:
            chosen = matrix
    return chosen


def attribute(batch: Path, matrices, lanes: dict, output: Path) -> dict:
    """Attribute every candidate of the named lanes; write idea sources and the attribution record."""
    batch = batch.resolve()
    status = json.loads(_regular(batch / "status.json", 16 * 1024 * 1024))
    if status.get("record_type") != STATUS_TYPE:
        refuse("batch_status_unsupported")
    journal = _journal(batch)
    declared = _matrices(matrices)
    output.mkdir(parents=True, exist_ok=False)
    (output / "ideas").mkdir()
    candidates, excluded = [], []
    for lane, family in sorted(lanes.items()):
        details = status.get("lanes", {}).get(lane)
        if type(details) is not dict or not details.get("model") or not details.get("provider"):
            refuse("lane_not_in_batch_status")
        folder = batch / "candidates" / lane
        for path in sorted(folder.glob("*.md")):
            idea_id = path.stem
            written_at = journal["written"].get((lane, idea_id))
            if written_at is None:
                excluded.append({"lane": lane, "file": path.name, "reason": "the journal records no write by this lane"})
                continue
            matrix = _matrix_at(declared, _timestamp(written_at))
            idea = matrix["ideas"].get(idea_id) if matrix is not None else None
            if idea is None or idea.get("record_type") != IDEA_TYPE or not IDEA_IDENTITY.fullmatch(idea_id):
                excluded.append({"lane": lane, "file": path.name,
                                 "reason": "no idea record in the matrix in effect at the recorded write"})
                continue
            raw = _regular(path, MAXIMUM_CANDIDATE_BYTES)
            idea_bytes = canonical(idea)
            idea_path = output / "ideas" / f"{idea_id}.json"
            if idea_path.exists():
                refuse("idea_attributed_twice")
            idea_path.write_bytes(idea_bytes)
            candidates.append({"lane": lane, "idea_id": idea_id, "file": f"candidates/{lane}/{path.name}",
                               "sha256": digest(raw), "size_bytes": len(raw), "written_at": written_at,
                               "file_kind": idea.get("file_kind", "skill"), "matrix_sha256": matrix["sha256"],
                               "idea_file": f"ideas/{idea_id}.json", "idea_sha256": digest(idea_bytes)})
    record = {"record_type": ATTRIBUTION_TYPE, "batch_directory": str(batch),
              "journal": {"sha256_at_read": journal["sha256"], "bytes_at_read": journal["bytes"]},
              "status_updated_at": status.get("updated_at"),
              "matrices": [{"path": matrix["path"], "sha256": matrix["sha256"],
                            "effective_from": matrix["effective_from"], "selected": matrix["selected"],
                            "selection": "tools/overnight_candidate_batch.py select_stratified, default seed"}
                           for matrix in declared],
              "lanes": {lane: {"family": family, "provider": status["lanes"][lane]["provider"],
                               "model": status["lanes"][lane]["model"]} for lane, family in sorted(lanes.items())},
              "candidates": candidates, "excluded": excluded,
              "limits": "Attribution reads the batch journal and files as they were at the read; the batch was "
                        "still running for other lanes. A family is the operator's declaration for the lane."}
    (output / "attribution.json").write_bytes(canonical(record))
    return {"candidates": len(candidates), "excluded": len(excluded)}


def _git(repository: Path, *arguments) -> bytes:
    finished = subprocess.run(["git", "-C", str(repository), *arguments], capture_output=True, check=False,
                              timeout=60)
    if finished.returncode != 0:
        refuse("git_read_failed")
    return finished.stdout


def _front_matter(text: str) -> "tuple[dict, str]":
    """The skill-style front matter's name and description as plain text, and the body after it."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    header, body = text[3:end], text[end + 4:]
    values = {}
    try:
        import yaml
        loaded = yaml.safe_load(header)
        if type(loaded) is dict:
            values = {key: value for key, value in loaded.items() if type(key) is str}
    except Exception:  # noqa: BLE001 - an unreadable header is judged by the pre-checks, not here
        values = {}
    return values, body


def _one_line(value) -> str:
    return " ".join(str(value).split()) if isinstance(value, str) else ""


def _words(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def proposal_for(row: dict, raw: bytes, idea: dict, lane: dict, idea_source: str) -> dict:
    """One version-two proposal for one attributed candidate whose file kind has a qualified placement."""
    placement = PLACEMENTS[row["file_kind"]]
    text = raw.decode("utf-8")
    header, body = _front_matter(text)
    heading = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), "")
    title = heading if heading and len(heading) <= 160 else _words(row["idea_id"]).capitalize()
    description = _one_line(header.get("description"))
    applicability = idea.get("applicability", {})
    purpose = description if 1 <= len(description) <= 1024 else (
        f"Catch a known-wrong result when a step performs {_words(idea['operation'])} on "
        f"{_words(idea['datatype'])} data for {_words(idea['use_case'])} work: {idea['known_wrong']}")
    occupation = _one_line(applicability.get("occupation_title", "")).lower()
    tags = [_words(idea["datatype"]), _words(idea["operation"]), _words(idea["use_case"])]
    if occupation:
        tags.append(occupation)
    search_tags = list(dict.fromkeys(tag[:160] for tag in tags if tag))
    return {"id": row["idea_id"].replace("-", "_"), "title": title, "purpose": purpose[:1024],
            "sources": [idea_source], "layer": LAYER, "family": placement["family"], "search_tags": search_tags,
            "tags": {"role": [occupation] if occupation else [], "domain": [_words(idea["use_case"])],
                     "language": [LANGUAGE]},
            "symbols": [], "declared_effects": list(DECLARED_EFFECTS), "kind": placement["kind"],
            "styles": list(placement["styles"]), "dependencies": [],
            "producer": {"producer_identity": f"{lane['provider']}:{lane['model']}", "family": lane["family"],
                         "method_identity": f"overnight_candidate_batch/{row['file_kind']}/v1"},
            "files": [{"path": placement["path"], "role": placement["role"], "media_type": "text/markdown",
                       "digest": digest(raw), "size_bytes": len(raw),
                       "content_base64": base64.b64encode(raw).decode("ascii")}]}


def proposals(repository: Path, attribution_path: Path, batch: Path, output: Path) -> dict:
    """Write the proposals the factory accepts one by one, and a report of every candidate left out."""
    repository = repository.resolve()
    revision = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    folder = attribution_path.resolve().parent
    try:
        relative = folder.relative_to(repository).as_posix()
    except ValueError:
        refuse("attribution_outside_repository")
    attribution_raw = attribution_path.read_bytes()
    listed = _git(repository, "ls-tree", "--name-only", revision, f"{relative}/attribution.json")
    if not listed.strip() or _git(repository, "show", f"{revision}:{relative}/attribution.json") != attribution_raw:
        refuse("attribution_not_committed")
    record = json.loads(attribution_raw)
    if record.get("record_type") != ATTRIBUTION_TYPE:
        refuse("attribution_unsupported")
    license_digest = digest((repository / "LICENSE").read_bytes())
    accepted, left_out, sources = [], [], {}
    for row in record["candidates"]:
        entry = {"lane": row["lane"], "idea_id": row["idea_id"], "sha256": row["sha256"]}
        if row["file_kind"] not in PLACEMENTS:
            left_out.append({**entry, "reason": f"the file kind {row['file_kind']} has no qualified native placement "
                                                "in this converter version"})
            continue
        raw = _regular(batch / row["file"], MAXIMUM_CANDIDATE_BYTES)
        if digest(raw) != row["sha256"]:
            left_out.append({**entry, "reason": "the candidate bytes changed after attribution"})
            continue
        idea_source = f"{relative}/{row['idea_file']}"
        idea_raw = (repository / idea_source).read_bytes()
        if digest(idea_raw) != row["idea_sha256"]:
            refuse("idea_source_changed")
        try:
            proposal = proposal_for(row, raw, json.loads(idea_raw), record["lanes"][row["lane"]], idea_source)
        except (UnicodeDecodeError, KeyError, TypeError) as error:
            left_out.append({**entry, "reason": f"the candidate could not be read as a proposal: {type(error).__name__}"})
            continue
        single = {"record_type": factory.NATIVE_INPUT_TYPE, "source_revision": revision,
                  "license": {"expression": "MIT", "path": "LICENSE", "sha256": license_digest},
                  "sources": {idea_source: row["idea_sha256"]}, "proposals": [proposal]}
        refusal = _factory_refusal(repository, single)
        if refusal:
            left_out.append({**entry, "reason": f"the factory refuses it: {refusal}"})
            continue
        accepted.append(proposal)
        sources[idea_source] = row["idea_sha256"]
    if not accepted:
        refuse("no_candidate_converted")
    batch_record = {"record_type": factory.NATIVE_INPUT_TYPE, "source_revision": revision,
                    "license": {"expression": "MIT", "path": "LICENSE", "sha256": license_digest},
                    "sources": dict(sorted(sources.items())), "proposals": accepted}
    output.write_bytes(canonical(batch_record))
    report = {"record_type": REPORT_TYPE, "attribution_sha256": digest(attribution_raw), "source_revision": revision,
              "proposals_sha256": digest(output.read_bytes()), "converted": len(accepted),
              "left_out": left_out, "declared_effects_policy": DECLARED_EFFECTS,
              "placements": PLACEMENTS}
    output.with_name(output.stem + "-report.json").write_bytes(canonical(report))
    return {"converted": len(accepted), "left_out": len(left_out)}


def _factory_refusal(repository: Path, record: dict) -> str:
    """The factory's refusal code for one proposal prepared alone, or empty when it prepares."""
    with tempfile.TemporaryDirectory(prefix="factory-dry-run-") as directory:
        path = Path(directory) / "proposals.json"
        path.write_bytes(canonical(record))
        try:
            factory.prepare(factory.PreparationRequest(repository, path, Path(directory) / "prepared", True))
        except factory.PreparationError as error:
            return str(error).split(":")[0] or "refused"
    return ""


def _lanes(values) -> dict:
    lanes = {}
    for value in values:
        lane, separator, family = value.partition("=")
        if not separator or not lane or not family or lane in lanes:
            refuse("lane_declaration_invalid")
        lanes[lane] = family
    return lanes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    first = commands.add_parser("attribute")
    first.add_argument("--batch-directory", type=Path, required=True)
    first.add_argument("--matrix", action="append", default=[], help="PATH@EFFECTIVE_FROM, one per matrix.")
    first.add_argument("--lane", action="append", default=[], help="LANE=FAMILY, one per lane to attribute.")
    first.add_argument("--output", type=Path, required=True)
    second = commands.add_parser("proposals")
    second.add_argument("--repository", type=Path, required=True)
    second.add_argument("--attribution", type=Path, required=True)
    second.add_argument("--batch-directory", type=Path, required=True)
    second.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    try:
        if options.command == "attribute":
            summary = attribute(options.batch_directory, options.matrix, _lanes(options.lane), options.output)
        else:
            summary = proposals(options.repository, options.attribution, options.batch_directory, options.output)
    except ConversionError as error:
        print(json.dumps({"refused": True, "code": str(error)}))
        return 2
    print(json.dumps(summary))
    return 0
