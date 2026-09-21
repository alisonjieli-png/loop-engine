"""Carry an approval across a change that is provably only a body's anchor line.

Every catalogue body ends with one sentence that names the revision the body was
anchored to. When a cited source file changes in the repository, the anchor tool
``examples/29_intelligence_service/starter-catalogue/refresh.py`` pins the
catalogue to a new revision and rewrites that one sentence in every body. The
bytes of each body change, so every digest changes, and an approval in
``reviews.json`` names the digest of the bytes its reviewers read.

Re-anchoring must not silently throw those approvals away, and it must not
silently keep them either. This command decides one item at a time, with no
judgement:

1. It reads the bytes the approval names, from the folder or the revision that
   holds them, and refuses to go on unless those bytes hash to the digest the
   approval names.
2. It compares those bytes with the body in the catalogue today. The approval is
   carried only when the sole difference is the trailing anchor line, and that
   line differs only in the revision it names. The comparison is in
   ``anchor_line_only`` and is the whole safety property of this command.
3. A carried approval is recorded as carried, never as freshly approved. The
   reviewers, their decisions and the digest they judged are kept, and the new
   digest, the new revision and the proof are added beside them.
4. Any other difference, anywhere, on any line, returns the item to candidate
   state with the exact reason written down. It is not served.

This command approves nothing, reviews nothing, reaches no network and grants no
effect. It lives beside ``tools/build_host_catalogue_manifest.py`` because both
read the same review record, and the generator refuses to serve anything this
command has returned to candidate state.

Check without writing (the default), then write with explicit authority:

    PYTHONPATH=src python tools/carry_catalogue_approvals.py \\
        --catalogue examples/29_intelligence_service/starter-catalogue \\
        --carried-at 2026-09-21
    PYTHONPATH=src python tools/carry_catalogue_approvals.py \\
        --catalogue examples/29_intelligence_service/starter-catalogue \\
        --carried-at 2026-09-21 --write
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

#: The review record this command reads and writes. Version one named no unreviewed
#: item and had no place for a carried approval, so a reader of version one must
#: refuse this record rather than reinterpret it.
REVIEW_RECORD_TYPE = "starter_catalogue_independent_review/v2"
ITEMS_RECORD_TYPE = "starter_catalogue_candidate_items/v2"
CARRY_RECORD_TYPE = "starter_catalogue_approval_carry/v1"
PROOF_RECORD_TYPE = "starter_catalogue_anchor_line_only_proof/v1"
REFUSAL_RECORD_TYPE = "starter_catalogue_approval_carry_refusal/v1"
REVIEW_FILE = "reviews.json"
ITEMS_FILE = "items.json"
BODY_SUFFIX = ".md"
TEMPORARY_SUFFIX = ".carry"
#: The outcomes a row may record. Only ``approved`` may be served.
APPROVED, REJECTED, NOT_REVIEWED, CARRY_REFUSED = "approved", "rejected", "not_reviewed", "carry_refused"
#: How an approval was reached. A reader tells a carried approval from a reviewed one here.
REVIEWED_STATE, CARRIED_STATE, NO_STATE = "reviewed", "carried", "none"
#: The sentence each kind of body carries, with the revision it was anchored to. The
#: anchor tool rewrites the revision inside these sentences and nothing else. A named
#: check requires that these are the sentences the anchor tool uses.
ANCHOR_SENTENCES = ("Compiled from revision {revision}.",
                    "Written for this catalogue at revision {revision}.")
#: How many characters of a revision a body names.
SHORT_REVISION = 7
#: One full revision.
REVISION = re.compile(r"[0-9a-f]{40}")
#: A date written the one way this record writes it.
CARRIED_AT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
#: How long this command waits for the version control command that reads one file.
GIT_SECONDS = 30
#: The rule a carried approval records. It is the reason an approval may survive at all.
CARRY_RULE = "an_approval_covers_only_the_bytes_that_were_reviewed"


class ApprovalCarryError(ValueError):
    """A stable refusal code and an operator message, with no item body."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _anchor_pattern(sentence: str):
    """One anchor sentence as a pattern whose only free part is the short revision."""
    before, _marker, after = sentence.partition("{revision}")
    return re.compile(re.escape(before) + f"([0-9a-f]{{{SHORT_REVISION}}})" + re.escape(after))


ANCHOR_PATTERNS = tuple((sentence, _anchor_pattern(sentence)) for sentence in ANCHOR_SENTENCES)


@dataclass(frozen=True)
class AnchorLineProof:
    """What was compared, and what the single permitted difference was."""

    lines: int
    anchor_line_number: int
    sentence: str
    reviewed_anchor_line: str
    carried_anchor_line: str
    reviewed_revision_named: str
    carried_revision_named: str

    def as_record(self) -> dict:
        return {"record_type": PROOF_RECORD_TYPE, "lines": self.lines,
                "anchor_line_number": self.anchor_line_number,
                "identical_lines": self.lines - 1,
                "sentence": self.sentence,
                "reviewed_anchor_line": self.reviewed_anchor_line,
                "carried_anchor_line": self.carried_anchor_line,
                "reviewed_revision_named": self.reviewed_revision_named,
                "carried_revision_named": self.carried_revision_named}


def _anchor_occurrences(lines: list) -> list:
    """Every place a line names an anchor revision, as (line index, sentence, match)."""
    return [(index, sentence, match) for index, line in enumerate(lines)
            for sentence, pattern in ANCHOR_PATTERNS for match in pattern.finditer(line)]


def anchor_line_only(reviewed: str, carried: str):
    """Return (proof, "") when the only difference is the trailing anchor line's revision.

    Otherwise return (None, reason). Every refusal names what differed. This
    function is the whole safety property: it decides whether an approval given
    for ``reviewed`` still covers ``carried``.
    """
    if reviewed == carried:
        return None, "the two bodies are the same bytes, so there is nothing to carry"
    reviewed_lines, carried_lines = reviewed.splitlines(keepends=True), carried.splitlines(keepends=True)
    if len(reviewed_lines) != len(carried_lines):
        return None, (f"the body now has {len(carried_lines)} lines and the approved body had "
                      f"{len(reviewed_lines)}")
    for label, lines in (("approved", reviewed_lines), ("current", carried_lines)):
        found = _anchor_occurrences(lines)
        if not found:
            return None, f"the {label} body names no anchor revision"
        if len(found) > 1:
            places = ", ".join(str(index + 1) for index, _sentence, _match in found)
            return None, f"the {label} body names an anchor revision on lines {places}; exactly one is required"
    index, sentence, match = _anchor_occurrences(reviewed_lines)[0]
    carried_index, carried_sentence, carried_match = _anchor_occurrences(carried_lines)[0]
    last = len(reviewed_lines) - 1
    if index != last or carried_index != last:
        return None, (f"the anchor revision is on line {index + 1} of the approved body and line "
                      f"{carried_index + 1} of the current one, and a body has {last + 1} lines; "
                      "it must be on the trailing line of both")
    if sentence != carried_sentence:
        return None, "the two bodies name their anchor revision in different sentences"
    differing = [number for number, (before, after) in enumerate(zip(reviewed_lines, carried_lines))
                 if before != after]
    elsewhere = [number + 1 for number in differing if number != index]
    if elsewhere:
        return None, "lines other than the anchor line differ: " + ", ".join(str(number) for number in elsewhere)
    line = reviewed_lines[index]
    # The one permitted difference, written out: the approved line with the carried
    # revision put in place of the approved one. Anything else on that line, including a
    # changed word and changed trailing whitespace, makes the two unequal here. The two
    # lines differ, so the two revisions differ as well.
    rebuilt = line[:match.start(1)] + carried_match.group(1) + line[match.end(1):]
    if rebuilt != carried_lines[index]:
        return None, "the anchor line differs by more than the revision it names"
    return AnchorLineProof(len(reviewed_lines), index + 1, sentence,
                           line.rstrip("\r\n"), carried_lines[index].rstrip("\r\n"),
                           match.group(1), carried_match.group(1)), ""


@dataclass(frozen=True)
class ReviewedBodies:
    """Where the bytes an approval covers are read from.

    A folder holds them directly. A revision reads them out of this repository's
    own history, which is the strongest provenance available and is how the
    committed record names them. Either way the digest decides: bytes that do
    not hash to the digest the approval names are never treated as reviewed.
    """

    folder: Path | None = None
    repository: Path | None = None
    revision: str = ""
    path_in_revision: str = ""

    @classmethod
    def in_folder(cls, folder: Path) -> "ReviewedBodies":
        return cls(folder=Path(folder).resolve())

    @classmethod
    def at_revision(cls, repository: Path, revision: str, path_in_revision: str) -> "ReviewedBodies":
        if not REVISION.fullmatch(revision or ""):
            raise ApprovalCarryError("reviewed_bodies_unreadable",
                                     "the reviewed bodies revision is one full forty character revision")
        return cls(repository=Path(repository).resolve(), revision=revision,
                   path_in_revision=path_in_revision.strip("/"))

    def describe(self) -> str:
        if self.folder is not None:
            return str(self.folder)
        return f"{self.path_in_revision} at revision {self.revision[:SHORT_REVISION]}"

    def read(self, identity: str) -> bytes | None:
        """The bytes an approval covers, or None when they are not there to read."""
        if self.folder is not None:
            path = self.folder / (identity + BODY_SUFFIX)
            if path.is_symlink() or not path.is_file() or path.resolve().parent != self.folder:
                return None
            return path.read_bytes()
        target = f"{self.revision}:{self.path_in_revision}/{identity}{BODY_SUFFIX}"
        try:
            finished = subprocess.run(["git", "-C", str(self.repository), "show", target],
                                      capture_output=True, timeout=GIT_SECONDS, check=False)
        except (OSError, subprocess.SubprocessError) as error:
            raise ApprovalCarryError("reviewed_bodies_unreadable",
                                     f"the repository history could not be read: {error}") from None
        return finished.stdout if finished.returncode == 0 else None


@dataclass(frozen=True)
class CarryRequest:
    """One catalogue folder, where the reviewed bytes are, the date and the write authority."""

    catalogue: Path
    reviewed: ReviewedBodies
    carried_at: str
    write: bool = False

    def __post_init__(self):
        if not isinstance(self.catalogue, Path) or not isinstance(self.reviewed, ReviewedBodies):
            raise ApprovalCarryError("invalid_request", "a carry needs a catalogue folder and a reviewed source")
        if type(self.write) is not bool:
            raise ApprovalCarryError("invalid_request", "a carry needs an explicit write flag")
        if not CARRIED_AT.fullmatch(self.carried_at or ""):
            raise ApprovalCarryError("invalid_request", "a carry records the date it happened, as YYYY-MM-DD")


def _read_json(path: Path, label: str):
    if path.is_symlink() or not path.is_file():
        raise ApprovalCarryError("catalogue_file_missing", f"{label} must be a regular file at {path}")
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApprovalCarryError("catalogue_file_unreadable", f"{label} is not readable UTF-8 JSON: {error}") from None


def _body(folder: Path, relative: str) -> Path:
    """One body inside the catalogue folder, refusing traversal, a link and any other suffix."""
    candidate = Path(relative)
    target = folder / candidate
    if (candidate.is_absolute() or ".." in candidate.parts or candidate.suffix != BODY_SUFFIX
            or target.resolve() != target or folder not in target.parents or target.is_symlink()
            or not target.is_file()):
        raise ApprovalCarryError("unsafe_body_path",
                                 f"body path {relative!r} must name a regular {BODY_SUFFIX} file "
                                 "inside the catalogue folder")
    return target


def _measured(payload: bytes) -> tuple:
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _reviewed_measure(row: dict) -> tuple:
    """The digest and size of the bytes the reviewers actually read.

    For a row that was never carried this is the row's own digest. For a row
    that was carried before, the row's digest is the carried one, so the bytes
    the reviewers read are the ones the carry record names. Carrying again is
    judged against those same original bytes, never against a carried copy.
    """
    carry = row.get("carry") or {}
    return (carry.get("reviewed_body_digest", row["body_digest"]),
            carry.get("reviewed_body_size_bytes", row["body_size_bytes"]))


def _refused(row: dict, reason: str, reviewed_digest, reviewed_size, reviewed_revision: str,
             current_digest: str, current_size: int) -> dict:
    """The row an item returns to: a candidate again, with the reason and both digests kept."""
    returned = deepcopy(row)
    returned["body_digest"] = None
    returned["body_size_bytes"] = None
    returned["outcome"] = CARRY_REFUSED
    returned["approval_state"] = NO_STATE
    returned["rule_applied"] = CARRY_RULE
    returned["approval_ref"] = ""
    returned.pop("carry", None)
    returned["carry_refusal"] = {"record_type": REFUSAL_RECORD_TYPE, "reason": reason,
                                 "reviewed_body_digest": reviewed_digest,
                                 "reviewed_body_size_bytes": reviewed_size,
                                 "reviewed_revision": reviewed_revision,
                                 "current_body_digest": current_digest,
                                 "current_body_size_bytes": current_size}
    return returned


def _carried(row: dict, proof: AnchorLineProof, carried_at: str, reviewed_revision: str,
             carried_revision: str, digest: str, size: int) -> dict:
    """The row a carried approval becomes: the same decisions, a new digest and the proof."""
    kept = deepcopy(row)
    first_digest, first_size = _reviewed_measure(row)
    first_revision = reviewed_revision
    kept["body_digest"] = digest
    kept["body_size_bytes"] = size
    kept["outcome"] = APPROVED
    kept["approval_state"] = CARRIED_STATE
    kept.pop("carry_refusal", None)
    kept["carry"] = {"record_type": CARRY_RECORD_TYPE, "carried_at": carried_at,
                     "reviewed_body_digest": first_digest, "reviewed_body_size_bytes": first_size,
                     "reviewed_revision": first_revision,
                     "carried_body_digest": digest, "carried_body_size_bytes": size,
                     "carried_revision": carried_revision,
                     "decisions_unchanged": True, "reviewed_again": False,
                     "proof": proof.as_record()}
    return kept


def _totals(rows: list) -> dict:
    outcomes = [row["outcome"] for row in rows]
    return {"items_in_catalogue": len(rows),
            "items_reviewed": sum(1 for row in rows if row["outcome"] != NOT_REVIEWED),
            "approved": outcomes.count(APPROVED),
            "approved_as_reviewed": sum(1 for row in rows if row["outcome"] == APPROVED
                                        and row["approval_state"] == REVIEWED_STATE),
            "approved_by_carry": sum(1 for row in rows if row["outcome"] == APPROVED
                                     and row["approval_state"] == CARRIED_STATE),
            "rejected": outcomes.count(REJECTED),
            "carry_refused": outcomes.count(CARRY_REFUSED),
            "not_reviewed": outcomes.count(NOT_REVIEWED)}


def carried_record(request: CarryRequest):
    """Return the new review record and one report row for every approval considered."""
    if not isinstance(request, CarryRequest):
        raise ApprovalCarryError("invalid_request", "a typed carry request is required")
    folder = request.catalogue.resolve()
    record = _read_json(folder / REVIEW_FILE, "the independent review record")
    items = _read_json(folder / ITEMS_FILE, "the candidate item file")
    if not isinstance(record, dict) or record.get("record_type") != REVIEW_RECORD_TYPE:
        raise ApprovalCarryError("review_record_unsupported",
                                 f"this command reads the review record {REVIEW_RECORD_TYPE} only")
    if not isinstance(items, dict) or items.get("record_type") != ITEMS_RECORD_TYPE:
        raise ApprovalCarryError("catalogue_record_unsupported",
                                 f"this command reads the candidate item file {ITEMS_RECORD_TYPE} only")
    # Where the catalogue is anchored now, and the revision the reviewed bytes name in
    # their own anchor line. The second one describes the bytes the reviewers read, so it
    # never moves when the catalogue is anchored again and a repeated carry changes nothing.
    record_revision = str(record.get("catalogue_source_revision") or "")
    reviewed_revision = str(record.get("reviewed_bodies_anchor_revision") or "")
    carried_revision = str(items.get("source_revision") or "")
    for label, revision in (("review record", record_revision),
                            ("reviewed bodies of the review record", reviewed_revision),
                            ("candidate item file", carried_revision)):
        if not REVISION.fullmatch(revision):
            raise ApprovalCarryError("revision_unsupported",
                                     f"the {label} must name one full forty character revision")
    new_record = deepcopy(record)
    rows, report = [], []
    for row in record["rows"]:
        if row["outcome"] != APPROVED:
            rows.append(deepcopy(row))
            continue
        identity = row["identity"]
        current = _body(folder, row["body_path"]).read_bytes()
        digest, size = _measured(current)
        named_digest, named_size = _reviewed_measure(row)
        payload = request.reviewed.read(identity)
        if payload is None:
            reason = f"the bytes this approval names are not in {request.reviewed.describe()}"
            rows.append(_refused(row, reason, named_digest, named_size, reviewed_revision, digest, size))
            report.append({"identity": identity, "carried": False, "reason": reason})
            continue
        held_digest, held_size = _measured(payload)
        if held_digest != named_digest or held_size != named_size:
            reason = (f"the bytes held for this approval hash to {held_digest} and the approval names "
                      f"{named_digest}, so what the reviewers read cannot be established")
            rows.append(_refused(row, reason, named_digest, named_size, reviewed_revision, digest, size))
            report.append({"identity": identity, "carried": False, "reason": reason})
            continue
        if payload == current:
            rows.append(deepcopy(row))
            report.append({"identity": identity, "carried": False, "unchanged": True,
                           "reason": "the body is the bytes the reviewers read"})
            continue
        try:
            proof, reason = anchor_line_only(payload.decode("utf-8"), current.decode("utf-8"))
        except UnicodeDecodeError:
            proof, reason = None, "one of the two bodies is not UTF-8 text"
        if proof is not None and proof.reviewed_revision_named != reviewed_revision[:SHORT_REVISION]:
            proof, reason = None, (f"the approved body names the revision {proof.reviewed_revision_named} "
                                   f"and the bytes the reviewers read are anchored at "
                                   f"{reviewed_revision[:SHORT_REVISION]}")
        if proof is not None and proof.carried_revision_named != carried_revision[:SHORT_REVISION]:
            proof, reason = None, (f"the body names the revision {proof.carried_revision_named} and the "
                                   f"catalogue is anchored at {carried_revision[:SHORT_REVISION]}")
        if proof is None:
            rows.append(_refused(row, reason, named_digest, named_size, reviewed_revision, digest, size))
            report.append({"identity": identity, "carried": False, "reason": reason})
            continue
        rows.append(_carried(row, proof, request.carried_at, reviewed_revision, carried_revision, digest, size))
        report.append({"identity": identity, "carried": True,
                       "reviewed_body_digest": named_digest, "carried_body_digest": digest})
    new_record["rows"] = rows
    new_record["catalogue_source_revision"] = carried_revision
    earlier = list(record.get("previous_catalogue_source_revisions") or [])
    if record_revision not in earlier:
        earlier.append(record_revision)
    new_record["previous_catalogue_source_revisions"] = [value for value in earlier if value != carried_revision]
    new_record["totals"] = _totals(rows)
    return new_record, report


def _replace(path: Path, value: dict) -> None:
    """Write the new record beside the old one, then replace it. Exclusive creation follows no link."""
    temporary = path.with_name(path.name + TEMPORARY_SUFFIX)
    try:
        stream = temporary.open("x", encoding="utf-8")
    except FileExistsError:
        raise ApprovalCarryError("leftover_temporary_file",
                                 f"{temporary.name} is left from an interrupted write; check that "
                                 f"{path.name} is intact, remove {temporary.name} and run again") from None
    try:
        with stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def carry(request: CarryRequest) -> dict:
    """Report what carries and what does not, and rewrite the record only with write authority."""
    new_record, report = carried_record(request)
    folder = request.catalogue.resolve()
    current = _read_json(folder / REVIEW_FILE, "the independent review record")
    moved = new_record != current
    if moved and request.write:
        _replace(folder / REVIEW_FILE, new_record)
    return {"record_type": "starter_catalogue_approval_carry_report/v1",
            "reviewed_bodies": request.reviewed.describe(),
            "reviewed_revision": current.get("catalogue_source_revision"),
            "carried_revision": new_record["catalogue_source_revision"],
            "totals": new_record["totals"],
            "carried": sorted(entry["identity"] for entry in report if entry.get("carried")),
            "did_not_carry": [{"identity": entry["identity"], "reason": entry["reason"]}
                              for entry in report if not entry.get("carried")
                              and not entry.get("unchanged")],
            "unchanged": sorted(entry["identity"] for entry in report if entry.get("unchanged")),
            "changed": moved, "written": bool(moved and request.write),
            "approved": False, "published": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalogue", type=Path, required=True, help="The reviewed candidate catalogue folder.")
    parser.add_argument("--carried-at", required=True, help="The date this carry happened, as YYYY-MM-DD.")
    parser.add_argument("--reviewed-bodies", type=Path,
                        help="A folder holding the bytes each approval names. Without it the bytes are "
                             "read from the revision the review record names.")
    parser.add_argument("--repository", type=Path, default=Path.cwd(),
                        help="The repository whose history holds the reviewed bodies.")
    parser.add_argument("--write", action="store_true", help="Rewrite the review record instead of checking it.")
    options = parser.parse_args(argv)
    try:
        folder = options.catalogue.resolve()
        if options.reviewed_bodies is not None:
            reviewed = ReviewedBodies.in_folder(options.reviewed_bodies)
        else:
            record = _read_json(folder / REVIEW_FILE, "the independent review record")
            reviewed = ReviewedBodies.at_revision(options.repository,
                                                  str(record.get("reviewed_bodies_revision") or ""),
                                                  str(record.get("reviewed_bodies_folder") or ""))
        result = carry(CarryRequest(folder, reviewed, options.carried_at, options.write))
    except ApprovalCarryError as error:
        print(json.dumps({"record_type": "starter_catalogue_approval_carry_report/v1", "refused": True,
                          "code": error.code, "message": str(error)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["written"] or not result["changed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
