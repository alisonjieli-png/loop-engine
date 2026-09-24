"""Count the Baltor harness library exactly, from each source's own records.

The inventory reads manifests, package.json files, candidate item records,
review and pre-check records, generation run journals and the overnight batch
journal. It never decides a unit, a kind or a state from a file name. It
changes no source: it opens files for reading, lists folders, and asks git two
read-only questions (``rev-parse HEAD`` and ``ls-files``). It makes no network
request and no model call, and it writes only its own two output files.

Words used in the output
    unit         one logical harness package or single-file candidate, as the
                 source's records count it. A newer version of the same
                 identity is the same unit; older versions are listed as
                 version history.
    unit files   the files a harness would receive for the current version of
                 each unit (the payload). Review notes, reports, run records
                 and manifests are not unit files.
    all files    every regular file under the source's folders.
    kind         one of CANONICAL_KINDS, mapped from a declared field that the
                 source's ``kind_basis`` names. A value the mapping does not
                 know stays "unknown"; nothing defaults to "skill".
    state        one of STATES, taken from the source's review, pre-check,
                 manifest or journal records. "passed a precheck" means a
                 recorded review pre-check passed: the wave 5
                 ``check_package.py check-all`` report or the candidate review
                 native pre-checks. A generation-time shape check or package
                 preparation is not a review pre-check, so those units stay
                 "candidate".
    identity key the identity lowercased, with the ``baltor.<group>.`` and
                 ``codex.component.supply.<date>.`` prefixes and a trailing
                 ``.v<number>`` removed, and every run of other characters
                 turned into one underscore. Overlaps are exact matches of
                 this key (or of an alias a record declares). Two differently
                 named methods that do the same work are not detected.

Run from the repository root:

    python3 tools/inventory_harness_library.py --replace

The live overnight batch keeps writing while this runs. The inventory reads
its journal once, up to the last complete line, and reports candidate files
that appear on disk without a journaled outcome instead of counting them.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

RECORD_TYPE = "harness_library_inventory/v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHARED_CHECKOUT = Path("/home/username/loop-engine")
DEFAULT_TACTICAL_WORKTREE = Path("/home/username/.le-tactical-blocks-20260924")
DEFAULT_SESSION_ARCHIVE = Path("/home/username/.le-safety/session-4d86b429-scratchpad-20260924")
DEFAULT_PRIVATE_GENERATION = Path("/home/username/baltor-private/generation-2026-09-23")
DEFAULT_OUTPUT = ROOT / "artifacts" / "library-inventory-2026-09-24"

SKILL = "skill"
INSTRUCTION = "instruction file or fragment"
SUBAGENT = "subagent definition"
COMMAND = "command or workflow recipe"
HOOK = "hook"
RULES = "rules file"
PLUGIN = "plugin manifest"
PROTOCOL = "protocol server configuration or server"
PERMISSIONS = "permission settings"
PACKET = "step packet"
TOOL = "tool or script"
VERIFIER = "verifier"
OTHER = "other"
UNKNOWN = "unknown"
CANONICAL_KINDS = (
    SKILL, INSTRUCTION, SUBAGENT, COMMAND, HOOK, RULES, PLUGIN, PROTOCOL,
    PERMISSIONS, PACKET, TOOL, VERIFIER, OTHER, UNKNOWN,
)

SERVED = "approved and served"
CANDIDATE = "candidate"
REFUSED = "refused by a precheck"
PASSED = "passed a precheck"
STATE_UNKNOWN = "unknown"
STATES = (SERVED, CANDIDATE, REFUSED, PASSED, STATE_UNKNOWN)
# When one identity appears in several sources, the deduplicated totals take
# the kind and state of its most advanced record, in this order.
STATE_RANK = {SERVED: 0, PASSED: 1, CANDIDATE: 2, REFUSED: 3, STATE_UNKNOWN: 4}

# Each declared vocabulary maps to the canonical kinds. A value missing here
# maps to "unknown", never to a guessed kind.
KIND_VOCABULARIES: dict[str, dict[str, str]] = {
    "catalogue reference kind": {
        "skill": SKILL, "instruction_file": INSTRUCTION, "tool": TOOL,
    },
    "wave 5 file class": {
        "skill_with_scripts_and_tests": SKILL,
        "task_packet": PACKET,
        "verifier_package": VERIFIER,
        "hook_with_script": HOOK,
        "subagent_definition": SUBAGENT,
        "command_file": COMMAND,
        "protocol_server_config_local": PROTOCOL,
        "rules_file": RULES,
        "plugin_bundle": PLUGIN,
        "settings_fragment": PERMISSIONS,
        "root_instruction_fragment": INSTRUCTION,
    },
    "proposal family": {
        "original_native_tool": TOOL,
        "deterministic_native_method": TOOL,
        "harness_plugin": PLUGIN,
        "original_native_skill": SKILL,
        "original_native_subagent": SUBAGENT,
        "original_native_command": COMMAND,
        "original_native_hook": HOOK,
        "original_native_packet": PACKET,
        "original_native_task_packet": PACKET,
    },
    "format pilot kind": {
        "native_step_instructions": INSTRUCTION,
        "skill_with_python_tool": SKILL,
        "local_protocol_server_connection": PROTOCOL,
    },
    "package tree role": {"skill_entry": SKILL},
    "generation guide declaration": {"Agent Skills package with SKILL.md entry": SKILL},
    "idea file kind": {
        "skill": SKILL,
        "subagent": SUBAGENT,
        "harness_routing": INSTRUCTION,
        "workflow": COMMAND,
        "hook": HOOK,
        "rules": RULES,
        "plugin_manifest": PLUGIN,
    },
    "research category": {
        "skill": SKILL,
        "plugin": PLUGIN,
        "tool": PROTOCOL,
        "contract": OTHER,
    },
    "plugin inventory record type": {"native_plugin_candidate_inventory/v1": PLUGIN},
}

_IDENTITY_PREFIXES = (
    re.compile(r"^baltor\.(?:context|tool|connection)\."),
    re.compile(r"^codex\.component\.supply\.\d+\."),
)


def map_kind(vocabulary: str, value: object) -> str:
    """Return the canonical kind for a declared value, or "unknown"."""
    if not isinstance(value, str):
        return UNKNOWN
    return KIND_VOCABULARIES[vocabulary].get(value, UNKNOWN)


def identity_key(raw: str) -> str:
    """Normalize an identity for cross-source matching (see module notes)."""
    text = raw.strip().lower()
    for pattern in _IDENTITY_PREFIXES:
        text = pattern.sub("", text)
    text = re.sub(r"\.v\d+$", "", text)
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


NAME_STOP_WORDS = frozenset({"a", "an", "and", "before", "by", "for", "from", "in", "into",
                             "of", "on", "or", "the", "to", "with"})


def name_words(key: str) -> frozenset:
    """Content words of an identity key, for the name-neighbour diagnostic."""
    return frozenset(word for word in key.split("_") if word and word not in NAME_STOP_WORDS)


def extension_of(path: str) -> str:
    suffix = os.path.splitext(os.path.basename(path))[1].lower()
    return suffix if suffix else "(none)"


def load_json(path: Path) -> object:
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def read_jsonl_prefix(path: Path) -> tuple[list[dict], dict]:
    """Read complete JSON lines only; a line still being written is ignored."""
    data = path.read_bytes()
    cut = data.rfind(b"\n") + 1
    complete = data[:cut]
    events: list[dict] = []
    unparsed = 0
    for line in complete.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            unparsed += 1
            continue
        if isinstance(value, dict):
            events.append(value)
        else:
            unparsed += 1
    snapshot = {
        "path": str(path),
        "bytes_read": cut,
        "bytes_after_last_complete_line": len(data) - cut,
        "sha256_of_bytes_read": hashlib.sha256(complete).hexdigest(),
        "events": len(events),
        "unparsed_lines": unparsed,
    }
    return events, snapshot


def list_files(root: Path) -> list[Path]:
    """Every regular file (or file symlink) under root, without following links."""
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            found.append(Path(dirpath) / name)
    return found


@dataclass(frozen=True)
class FileEntry:
    path: str
    size: int | None
    sha256: str | None
    declared_sha256: str | None = None

    @property
    def missing(self) -> bool:
        return self.sha256 is None

    @property
    def mismatch(self) -> bool:
        return (self.sha256 is not None and self.declared_sha256 is not None
                and self.sha256 != self.declared_sha256)


def file_entry(path: Path, declared: str | None = None) -> FileEntry:
    try:
        data = path.read_bytes()
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError):
        return FileEntry(str(path), None, None, declared)
    return FileEntry(str(path), len(data), hashlib.sha256(data).hexdigest(), declared)


@dataclass
class Unit:
    identity: str
    kind: str
    kind_value: str
    state: str
    state_detail: str
    files: list[FileEntry]
    version: str = ""
    group: str = ""
    aliases: tuple[str, ...] = ()
    producer_family: str = ""

    @property
    def key(self) -> str:
        return identity_key(self.identity)


@dataclass
class Source:
    name: str
    label: str
    scope: str
    library: bool
    roots: list[Path]
    unit_definition: str
    kind_basis: str
    state_basis: str
    units: list[Unit] = field(default_factory=list)
    versions: list[dict] = field(default_factory=list)
    attempts: Counter = field(default_factory=Counter)
    records: set = field(default_factory=set)
    notes: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    list_identities: bool = True


def _read_proposal_families(path: Path, source: Source) -> dict[str, str]:
    if not path.is_file():
        return {}
    source.records.add(str(path))
    document = load_json(path)
    proposals = document.get("proposals", []) if isinstance(document, dict) else []
    return {p.get("id"): p.get("family") for p in proposals if isinstance(p, dict)}


def _read_v3_items(items_path: Path, source: Source) -> list[dict]:
    """Candidate items (record types v3) with their package files on disk."""
    source.records.add(str(items_path))
    document = load_json(items_path)
    base = items_path.parent
    result = []
    for item in document.get("items", []):
        reference = item["reference"]
        package = item.get("package") or {}
        files = []
        if package.get("files"):
            package_root = base / item.get("package_root", "")
            for row in package["files"]:
                files.append(file_entry(package_root / row["path"], row.get("digest")))
        else:
            files.append(file_entry(base / item["body_path"], reference.get("digest")))
        result.append({
            "identity": reference["identity"],
            "digest": reference.get("digest", ""),
            "reference_kind": reference.get("kind"),
            "files": files,
            "producer_family": (item.get("producer") or {}).get("family", ""),
        })
    return result


def _summarize_generation_journal(journal: Path, source: Source) -> dict:
    """Outcome counts of one original native generation run journal."""
    events, snapshot = read_jsonl_prefix(journal)
    source.records.add(str(journal))
    dispatched: list[tuple] = []
    completed: dict[tuple, dict] = {}
    for event in events:
        key = (event.get("method_id"), event.get("attempt"))
        if event.get("kind") == "dispatch":
            dispatched.append(key)
        elif event.get("kind") == "complete":
            completed[key] = event.get("data") or {}
    outcomes: Counter = Counter()
    prepared: list[dict] = []
    for key, data in sorted(completed.items(), key=lambda pair: str(pair[0])):
        if data.get("prepared_path"):
            outcomes["prepared"] += 1
            prepared.append({"method_id": key[0], "attempt": key[1],
                             "prepared_path": data["prepared_path"],
                             "package_digest": data.get("package_digest", "")})
        else:
            admission = data.get("response_admission") or {}
            code = (data.get("error_code") or admission.get("failure_code")
                    or "refused_without_a_recorded_code")
            outcomes[code] += 1
    pending = sorted({key for key in dispatched if key not in completed}, key=str)
    if pending:
        outcomes["dispatched_without_a_recorded_completion"] += len(pending)
    return {"journal": snapshot, "dispatches": len(dispatched),
            "completions": len(completed), "outcomes": dict(sorted(outcomes.items())),
            "prepared": prepared,
            "pending": [{"method_id": k[0], "attempt": k[1]} for k in pending]}


# -- requested sources ----------------------------------------------------

def read_served_catalogue(folder: Path, release_record: Path | None = None) -> Source:
    source = Source(
        name="served starter catalogue",
        label="examples/29_intelligence_service/starter-catalogue",
        scope="requested", library=True, roots=[folder],
        unit_definition=("one catalogue item in items.json; the host release "
                         "manifest names the served ones"),
        kind_basis="items.json reference.kind",
        state_basis=("reviews.json outcome per identity, and whether "
                     "host-release/manifest.json names the identity"),
    )
    items = load_json(folder / "items.json")
    reviews = load_json(folder / "reviews.json")
    manifest = load_json(folder / "host-release" / "manifest.json")
    for name in ("items.json", "reviews.json", "host-release/manifest.json"):
        source.records.add(str(folder / name))
    outcome = {row["identity"]: row.get("outcome") for row in reviews["rows"]}
    served = {row["reference"]["identity"]: row for row in manifest["items"]}
    for item in items["items"]:
        reference = item["reference"]
        identity = reference["identity"]
        verdict = outcome.get(identity, "no review row")
        if identity in served and verdict == "approved":
            state, detail = SERVED, "approved by the independent review and named by the host release manifest"
        elif identity in served:
            state, detail = STATE_UNKNOWN, f"named by the host release manifest, review outcome {verdict}"
        elif verdict == "approved":
            state, detail = STATE_UNKNOWN, "approved by the independent review, not named by the host release manifest"
        elif verdict == "rejected":
            state, detail = CANDIDATE, "rejected by the independent review, which keeps it a candidate"
        elif verdict == "not_reviewed":
            state, detail = CANDIDATE, "not reviewed"
        else:
            state, detail = STATE_UNKNOWN, f"review outcome {verdict}"
        source.units.append(Unit(
            identity=identity,
            kind=map_kind("catalogue reference kind", reference.get("kind")),
            kind_value=f"catalogue reference kind: {reference.get('kind')}",
            state=state, state_detail=detail,
            files=[file_entry(folder / item["body_path"], reference.get("digest"))],
            version=reference.get("digest", ""),
        ))
    known = {item["reference"]["identity"] for item in items["items"]}
    source.extra["review_outcomes"] = dict(sorted(Counter(
        outcome.get(identity, "no review row") for identity in sorted(known)).items()))
    served_bodies = [(file_entry(folder / "host-release" / row["body_path"],
                                 row["reference"].get("digest")),
                      file_entry(folder / row["body_path"])) for row in manifest["items"]]
    source.extra["host_release_manifest"] = {
        "items": len(manifest["items"]),
        "items_missing_from_items_json": sorted(set(served) - known),
        "host_release_bodies_matching_their_digest": sum(
            1 for entry, _ in served_bodies if not entry.missing and not entry.mismatch),
        "host_release_bodies_identical_to_the_bodies_folder": sum(
            1 for entry, body in served_bodies if entry.sha256 and entry.sha256 == body.sha256),
        "note": ("identical host-release/bodies copies are counted in all files, "
                 "not as more unit files"),
    }
    if release_record is not None and release_record.is_file():
        record = load_json(release_record)
        source.records.add(str(release_record))
        published = record.get("catalogue_release_published") or {}
        source.extra["live_release_record"] = {
            "path": str(release_record),
            "fly_release": record.get("fly_release"),
            "catalogue_release_id": published.get("release_id"),
            "items": published.get("items"),
            "reason": published.get("reason"),
            "note": "read from the committed release record; the live service was not queried",
        }
    served_units = sum(1 for unit in source.units if unit.state == SERVED)
    source.notes.append(
        f"The folder holds {len(source.units)} catalogue items. The {served_units} "
        "approved ones named by the host release manifest are the served library; "
        "the others stay candidates (see review_outcomes).")
    return source


GENERATION_GUIDE_PHRASES = ("Agent Skills format", "SKILL.md")


def read_first_party_waves(folders: list[Path], guide: Path) -> Source:
    source = Source(
        name="first-party waves 1 to 4",
        label="artifacts/first-party-harness-candidates-2026-09-22 (and -wave-2, -wave-3, -wave-4-ops)",
        scope="requested", library=True, roots=list(folders),
        unit_definition="one manifest.json entry: one native package and its separate review note",
        kind_basis=("the shared GENERATION-GUIDE.md, which each wave README names as governing, "
                    "requires one Agent Skills package with a SKILL.md entry; each manifest "
                    "entry's package_path must be that entry file"),
        state_basis="manifest.json entry state (candidate_only) and approval_state",
    )
    guide_text = guide.read_text(encoding="utf-8") if guide.is_file() else ""
    source.records.add(str(guide))
    guide_declares = all(phrase in guide_text for phrase in GENERATION_GUIDE_PHRASES)
    per_wave = {}
    for folder in folders:
        manifest = load_json(folder / "manifest.json")
        source.records.add(str(folder / "manifest.json"))
        readme = (folder / "README.md").read_text(encoding="utf-8") if (folder / "README.md").is_file() else ""
        governed = "GENERATION-GUIDE.md" in readme
        listed = {str(folder / entry["package_path"]) for entry in manifest.get("entries", [])}
        unlisted = [str(p) for p in list_files(folder / "packages") if str(p) not in listed]
        per_wave[folder.name] = {"entries": len(manifest.get("entries", [])),
                                 "package_count": manifest.get("package_count"),
                                 "approval_state": manifest.get("approval_state"),
                                 "rights_state": manifest.get("rights_state"),
                                 "files_under_packages_not_in_the_manifest": len(unlisted)}
        for entry in manifest.get("entries", []):
            entry_is_skill_file = os.path.basename(entry["package_path"]) == "SKILL.md"
            declared = guide_declares and governed and entry_is_skill_file
            value = "Agent Skills package with SKILL.md entry" if declared else "not declared"
            state_value = entry.get("state")
            if state_value == "candidate_only" and manifest.get("approval_state") == "none":
                state, detail = CANDIDATE, "manifest state candidate_only, approval_state none"
            else:
                state, detail = STATE_UNKNOWN, f"manifest state {state_value}"
            source.units.append(Unit(
                identity=entry["name"],
                kind=map_kind("generation guide declaration", value),
                kind_value=f"generation guide declaration: {value}",
                state=state, state_detail=detail,
                files=[file_entry(folder / entry["package_path"], entry.get("package_sha256"))],
                version=entry.get("package_sha256", ""), group=folder.name,
            ))
    source.extra["per_wave"] = per_wave
    return source


def read_wave5(folder: Path) -> Source:
    source = Source(
        name="first-party wave 5",
        label="artifacts/first-party-harness-candidates-2026-09-24-wave-5",
        scope="requested", library=True, roots=[folder],
        unit_definition="one packages/<assignment>/<identity>/package.json multi-file package",
        kind_basis="package.json wave5.file_class",
        state_basis=("the newest reports/precheck-all-*.json that names the package "
                     "(passed_for_wave_gate or refused), checked against the package's "
                     "own newest review/precheck-*.json"),
    )
    reports = []
    for path in sorted((folder / "reports").glob("precheck-all-*.json")):
        document = load_json(path)
        source.records.add(str(path))
        reports.append((str(document.get("checked_at", "")), path.name, document))
    reports.sort(key=lambda row: (row[0], row[1]))
    verdict: dict[str, tuple[str, str]] = {}
    for checked_at, name, document in reports:
        for identity in document.get("passed_for_wave_gate", []):
            verdict[identity] = ("passed", name)
        for identity in document.get("refused", []):
            verdict[identity] = ("refused", name)
    if reports:
        newest = reports[-1]
        source.extra["newest_check_all_report"] = {
            "file": newest[1], "checked_at": newest[0],
            "packages": newest[2].get("packages"),
            "passed_for_wave_gate": len(newest[2].get("passed_for_wave_gate", [])),
            "refused": len(newest[2].get("refused", [])),
        }
    drift = Counter()
    for package_json in sorted(folder.glob("packages/*/*/package.json")):
        document = load_json(package_json)
        source.records.add(str(package_json))
        proposal = document["proposal"]
        wave = document.get("wave5", {})
        identity = proposal["id"]
        payload_root = package_json.parent / "payload"
        declared = {row["path"]: row.get("digest") for row in proposal.get("files", [])}
        on_disk = {str(p.relative_to(payload_root)) for p in list_files(payload_root)}
        files = [file_entry(payload_root / path, declared.get(path))
                 for path in sorted(set(declared) | on_disk)]
        drift["declared payload files"] += len(declared)
        drift["payload files on disk"] += len(on_disk)
        drift["declared but missing on disk"] += len(set(declared) - on_disk)
        drift["on disk but not declared"] += len(on_disk - set(declared))
        mismatches = sum(1 for f in files if f.mismatch)
        drift["digest differs from package.json"] += mismatches
        own_reports = []
        for report_path in sorted((package_json.parent / "review").glob("precheck-*.json")):
            report = load_json(report_path)
            own_reports.append((str(report.get("checked_at", "")), report_path.name,
                                report_path, report))
        own = None
        if own_reports:
            _, _, own_path, own_document = max(own_reports, key=lambda row: (row[0], row[1]))
            source.records.add(str(own_path))
            own = ("passed" if own_document.get("passed_for_wave_gate")
                   else "refused" if own_document.get("refused") else "unknown")
        result = verdict.get(identity)
        if result is None:
            state, detail = STATE_UNKNOWN, "no check-all report names this package"
        elif own is not None and own != result[0]:
            state, detail = STATE_UNKNOWN, (f"check-all {result[1]} says {result[0]}, "
                                            f"the package's own newest report says {own}")
        elif result[0] == "passed":
            state, detail = PASSED, "passed the deterministic wave 5 pre-checks (not an approval)"
        else:
            state, detail = REFUSED, "refused by the deterministic wave 5 pre-checks"
        if mismatches:
            drift[f"digest differs from package.json, in packages whose state is {state}"] += mismatches
        source.units.append(Unit(
            identity=identity,
            kind=map_kind("wave 5 file class", wave.get("file_class")),
            kind_value=f"wave 5 file class: {wave.get('file_class')}",
            state=state, state_detail=detail, files=files,
            version=str(wave.get("package_digest", "")),
            group=wave.get("assignment_id", ""),
            producer_family=(proposal.get("producer") or {}).get("family", ""),
        ))
    source.extra["payload_inventory"] = dict(sorted(drift.items()))
    source.notes.append(
        "Unit files are the payload/ files of each package (declared or present). "
        "package.json, review/ reports and review notes are records, not unit files.")
    return source


def read_format_pilots(first: Path, second: Path) -> Source:
    source = Source(
        name="format pilots",
        label="artifacts/harness-intelligence-format-pilot-2026-09-22 and -wave-2",
        scope="requested", library=True, roots=[first, second],
        unit_definition="one logical item in candidate-items.json",
        kind_basis=("pilot one: candidate-items.json item kind; pilot two: the "
                    "manifest.json package_trees entry role"),
        state_basis="candidate-items.json state and approval_state",
    )
    catalog = load_json(first / "candidate-items.json")
    manifest = load_json(first / "manifest.json")
    source.records.update({str(first / "candidate-items.json"), str(first / "manifest.json")})
    digests = {row["path"]: row.get("sha256") for row in manifest.get("entries", [])}
    candidate_only = (catalog.get("state") == "candidate_only"
                      and catalog.get("approval_state") == "none")
    for item in catalog["items"]:
        paths = set(item.get("source_files", []))
        for variant in (item.get("delivery_variants") or {}).values():
            paths.update(variant)
        source.units.append(Unit(
            identity=item["id"],
            kind=map_kind("format pilot kind", item.get("kind")),
            kind_value=f"format pilot kind: {item.get('kind')}",
            state=CANDIDATE if candidate_only else STATE_UNKNOWN,
            state_detail="candidate_only, approval_state none" if candidate_only else "state not recorded",
            files=[file_entry(first / path, digests.get(path)) for path in sorted(paths)],
            group=first.name,
        ))
    catalog2 = load_json(second / "candidate-items.json")
    manifest2 = load_json(second / "manifest.json")
    source.records.update({str(second / "candidate-items.json"), str(second / "manifest.json")})
    trees = manifest2.get("package_trees", {})
    candidate_only2 = catalog2.get("approval_state") == "candidate_only"
    for item in catalog2["items"]:
        tree = trees.get(item["id"], [])
        roles = {row.get("role") for row in tree}
        entry_role = "skill_entry" if "skill_entry" in roles else "no entry role"
        tree_digests = {row["path"]: row.get("sha256") for row in tree}
        source.units.append(Unit(
            identity=item["id"],
            kind=map_kind("package tree role", entry_role),
            kind_value=f"package tree role: {entry_role}",
            state=CANDIDATE if candidate_only2 else STATE_UNKNOWN,
            state_detail="approval_state candidate_only" if candidate_only2 else "state not recorded",
            files=[file_entry(second / path, tree_digests.get(path))
                   for path in sorted(item.get("delivery_files", []))],
            group=second.name,
        ))
    source.extra["pilot_one_manifest"] = {
        "physical_files": manifest.get("physical_file_count"),
        "delivery_payload_files": manifest.get("delivery_payload_file_count"),
        "file_roles": dict(sorted(Counter(r.get("file_role") for r in manifest.get("entries", [])).items())),
    }
    source.extra["pilot_two_manifest"] = {
        "logical_packages": manifest2.get("logical_packages"),
        "physical_delivery_paths": manifest2.get("physical_delivery_paths"),
        "distinct_delivery_body_digests": manifest2.get("distinct_delivery_body_digests"),
    }
    source.notes.append(
        "Pilot one unit files are its delivery variants for every client plus "
        "canonical connection sources; a client installs one variant, not all.")
    return source


def read_native_preparation(preparation: Path, first_batch: Path) -> Source:
    source = Source(
        name="native candidate preparation",
        label=("artifacts/native-candidate-preparation-2026-09-23 and "
               "artifacts/tactical-first-batch-2026-09-24"),
        scope="requested", library=True, roots=[preparation, first_batch],
        unit_definition="one prepared candidate item (items.json, record type v3)",
        kind_basis="the proposal family in plugin-fixture-proposals.json",
        state_basis=("preparation and staging records; no review pre-check record "
                     "exists for the fixture"),
    )
    families = _read_proposal_families(preparation / "plugin-fixture-proposals.json", source)
    binding_path = preparation / "fixture-source-binding.json"
    binding = load_json(binding_path) if binding_path.is_file() else {}
    if binding:
        source.records.add(str(binding_path))
    items_path = preparation / "prepared-plugin-fixture" / "items.json"
    if items_path.is_file():
        for item in _read_v3_items(items_path, source):
            family = families.get(item["identity"])
            aliases = (binding["original_package_id"],) if binding.get("original_package_id") else ()
            source.units.append(Unit(
                identity=item["identity"],
                kind=map_kind("proposal family", family),
                kind_value=f"proposal family: {family}",
                state=CANDIDATE,
                state_detail=("prepared and staged in an isolated test catalogue; "
                              "repackages an existing plugin with zero new logical package credit"),
                files=item["files"], version=item["digest"], group=preparation.name,
                aliases=aliases, producer_family=item["producer_family"],
            ))
    if binding:
        source.extra["fixture_source_binding"] = {
            "original_package_id": binding.get("original_package_id"),
            "new_logical_package_count": binding.get("new_logical_package_count"),
            "payload_files": binding.get("payload_files"),
            "reason": binding.get("reason"),
        }
    runs = {}
    for journal in sorted(first_batch.glob("*/journal.jsonl")):
        summary = _summarize_generation_journal(journal, source)
        runs[journal.parent.name] = {k: summary[k] for k in ("dispatches", "completions", "outcomes")}
        for code, count in summary["outcomes"].items():
            if code != "prepared":
                source.attempts[f"tactical first batch: {code}"] += count
        if summary["prepared"]:
            source.notes.append(f"{journal.parent.name} prepared {len(summary['prepared'])} "
                                "candidates that are not in any items.json here")
    source.extra["tactical_first_batch_runs"] = runs
    source.notes.append(
        "The Tactical blocks batch (artifacts/native-blocks-batch-2026-09-24) is "
        "counted once, as its own source, not here.")
    if binding:
        source.notes.append(
            f"The fixture repackages {binding.get('original_package_id')}; its source binding "
            f"records {binding.get('new_logical_package_count')} new logical packages. The "
            "fixture's identity carries that name as an alias, so the two count once.")
    return source


def _panel_records(batch_dir: Path, source: Source) -> list[dict]:
    """Review records of one prepared batch, oldest first."""
    records = []
    for path in sorted(batch_dir.glob("review-*.json")):
        document = load_json(path)
        if not isinstance(document, dict) or not str(document.get("record_type", "")).startswith(
                "starter_catalogue_panel_review/"):
            continue
        source.records.add(str(path))
        started = sorted(str(run.get("started_at")) for run in document.get("runs", [])
                         if isinstance(run, dict) and run.get("started_at"))
        records.append({"path": path, "started": started[-1] if started else "",
                        "document": document})
    records.sort(key=lambda row: (row["started"], row["path"].name))
    return records


def compare_trees(first: Path, second: Path) -> dict:
    """Paths and byte digests present in one folder tree and not the other."""
    def index(root: Path) -> dict[str, str | None]:
        return {str(p.relative_to(root)): file_entry(p).sha256 for p in list_files(root)}
    here, there = index(first), index(second)
    return {
        "compared_with": str(second), "exists": second.is_dir(),
        "files_here": len(here), "files_there": len(there),
        "only_here": sorted(set(here) - set(there)),
        "only_there": sorted(set(there) - set(here)),
        "same_path_different_bytes": sorted(k for k in set(here) & set(there) if here[k] != there[k]),
    }


def read_tactical_blocks(folder: Path, alternate: Path | None = None) -> Source:
    source = Source(
        name="Tactical blocks batch",
        label="artifacts/native-blocks-batch-2026-09-24",
        scope="requested", library=True, roots=[folder],
        unit_definition=("one method identity; its current version is the package in "
                         "the most recently reviewed prepared batch that holds it"),
        kind_basis="the proposal family in each batch's merged-proposals.json",
        state_basis=("prechecks.refused in the newest review record of the batch "
                     "(review-prechecks.json or a later review-panel attempt)"),
    )
    versions: dict[str, dict[str, dict]] = {}
    batches = {}
    reviewed_batches = []
    for prechecks in sorted(folder.glob("*/review-prechecks.json")):
        records = _panel_records(prechecks.parent, source)
        if records:
            reviewed_batches.append((records[-1]["started"], prechecks.parent.name,
                                     prechecks.parent, records[-1]))
    # Oldest review first, so a package seen in several batches ends with the
    # state its newest review recorded.
    for _, _, batch_dir, newest in sorted(reviewed_batches, key=lambda row: (row[0], row[1])):
        document = newest["document"]
        producers = document.get("producers") or {}
        identities = [producers.get("default_producer", {}).get("producer_identity", "")]
        identities += [row.get("producer_identity", "") for row in producers.get("item_producers", [])]
        synthetic = all(identity.endswith(":synthetic") for identity in identities if identity)
        catalogue = batch_dir / Path(document.get("catalogue_folder", "")).name
        batches[batch_dir.name] = {
            "reviewed_at": newest["started"], "review_record": newest["path"].name,
            "synthetic_fixtures_not_candidates": synthetic,
            "totals": document.get("totals"),
        }
        if synthetic:
            continue
        families = _read_proposal_families(batch_dir / "merged-proposals.json", source)
        rows = {row["identity"]: row for row in document.get("rows", [])}
        for item in _read_v3_items(catalogue / "items.json", source):
            row = rows.get(item["identity"], {})
            prechecks_row = row.get("prechecks") or {}
            outcome = row.get("outcome", "no review row")
            if prechecks_row.get("refused") is True:
                state = REFUSED
                detail = "refused by the native pre-checks: " + ", ".join(
                    sorted(set(prechecks_row.get("reasons", []))))
            elif prechecks_row.get("refused") is False and outcome in (
                    "not_started", "panel_incomplete"):
                state = PASSED
                detail = f"passed the native pre-checks; panel outcome {outcome}"
            elif prechecks_row.get("refused") is False and outcome == "rejected":
                state = CANDIDATE
                detail = "passed the native pre-checks, then rejected by the review panel"
            elif outcome == "approved":
                state, detail = STATE_UNKNOWN, "approved by the review panel, not named by a host manifest"
            else:
                state, detail = STATE_UNKNOWN, f"panel outcome {outcome}"
            family = families.get(item["identity"])
            record = versions.setdefault(item["identity"], {}).setdefault(item["digest"], {
                "identity": item["identity"], "version": item["digest"], "batches": [],
                "files": item["files"], "family": family,
                "producer_family": item["producer_family"],
            })
            record["batches"].append((newest["started"], batch_dir.name))
            record["state"], record["detail"] = state, detail
    for identity in sorted(versions):
        ordered = sorted(versions[identity].values(), key=lambda v: max(v["batches"]))
        current = ordered[-1]
        source.units.append(Unit(
            identity=identity,
            kind=map_kind("proposal family", current["family"]),
            kind_value=f"proposal family: {current['family']}",
            state=current["state"], state_detail=current["detail"],
            files=current["files"], version=current["version"],
            group=max(current["batches"])[1], producer_family=current["producer_family"],
        ))
        for version in ordered:
            source.versions.append({
                "identity": identity, "package_digest": version["version"],
                "batches": [name for _, name in sorted(version["batches"])],
                "state": version["state"], "current": version is current,
            })
    runs = {}
    prepared_digests = set()
    for journal in sorted(folder.glob("*/journal.jsonl")):
        summary = _summarize_generation_journal(journal, source)
        runs[journal.parent.name] = {k: summary[k] for k in ("dispatches", "completions", "outcomes")}
        for code, count in summary["outcomes"].items():
            if code != "prepared":
                source.attempts[f"{journal.parent.name}: {code}"] += count
        prepared_digests.update(p["package_digest"] for p in summary["prepared"])
    reviewed = {v["package_digest"] for v in source.versions}
    source.extra["generation_runs"] = runs
    source.extra["prepared_batches"] = batches
    source.extra["run_prepared_packages"] = {
        "distinct_package_digests": len(prepared_digests),
        "found_in_a_reviewed_batch": len(prepared_digests & reviewed),
        "not_found_in_a_reviewed_batch": len(prepared_digests - reviewed),
    }
    if alternate is not None and alternate.is_dir():
        source.extra["copy_in_the_tactical_worktree"] = compare_trees(folder, alternate)
    source.notes.append(
        "plan-preflight holds synthetic layout fixtures (producer "
        "layout-preflight:synthetic); they are counted in all files, not as units.")
    return source


def read_prepared_cohort(name: str, label: str, folder: Path, items_path: Path,
                         proposals_path: Path, staging_report: Path | None,
                         scope: str = "requested") -> Source:
    source = Source(
        name=name, label=label, scope=scope, library=True, roots=[folder],
        unit_definition="one prepared candidate item (items.json, record type v3)",
        kind_basis=f"the proposal family in {proposals_path.name}",
        state_basis=("preparation report and staging report; no review pre-check "
                     "record exists for these bytes"),
    )
    families = _read_proposal_families(proposals_path, source)
    staged = None
    if staging_report is not None and staging_report.is_file():
        report = load_json(staging_report)
        source.records.add(str(staging_report))
        staged = report
        source.extra["staging_report"] = {
            key: report.get(key) for key in ("records", "committed", "hosted_publication",
                                             "independent_qualification")}
    detail = ("prepared and staged in an isolated candidate catalogue, excluded from "
              "normal search; no review pre-check" if staged and staged.get("committed")
              else "prepared; no review pre-check")
    report_path = items_path.parent / "preparation-report.json"
    if report_path.is_file():
        report = load_json(report_path)
        source.records.add(str(report_path))
        source.extra["counts_declared_by_the_preparation_report"] = {
            key: report.get(key) for key in ("candidates", "payload_files",
                                             "unique_payload_digests", "approved")}
    for item in _read_v3_items(items_path, source):
        family = families.get(item["identity"])
        source.units.append(Unit(
            identity=item["identity"],
            kind=map_kind("proposal family", family),
            kind_value=f"proposal family: {family}",
            state=CANDIDATE, state_detail=detail, files=item["files"],
            version=item["digest"], producer_family=item["producer_family"],
        ))
    return source


def read_gemma4_components(folder: Path) -> Source:
    source = Source(
        name="Gemma 4 harness components",
        label="artifacts/gemma4-harness-components-2026-09-23 (shared checkout, uncommitted)",
        scope="requested", library=True, roots=[folder],
        unit_definition="one method named in authors/contracts-first.json",
        kind_basis=("no kind is declared; the author note cites the Agent Skills format, "
                    "but no SKILL.md or implementation exists yet, so the kind stays unknown"),
        state_basis="README (candidate supply lane) and contracts-first.json executables_exist",
    )
    record_path = folder / "authors" / "contracts-first.json"
    record = load_json(record_path)
    source.records.add(str(record_path))
    complete = bool(record.get("executables_exist"))
    by_method: dict[str, list[FileEntry]] = {name: [] for name in record.get("cases", {})}
    for path, digest in sorted((record.get("files") or {}).items()):
        parts = Path(path).parts
        method = parts[1] if len(parts) > 1 and parts[0] == "packages" else ""
        if method in by_method:
            by_method[method].append(file_entry(folder / path, digest))
    for method, files in sorted(by_method.items()):
        source.units.append(Unit(
            identity=method, kind=UNKNOWN,
            kind_value="not declared (intended Agent Skills layout, incomplete)",
            state=CANDIDATE,
            state_detail=("incomplete candidate: contracts, examples and cases only"
                          if not complete else "candidate"),
            files=files,
        ))
    source.extra["executables_exist"] = complete
    source.extra["cases_per_method"] = record.get("cases")
    return source


def _licence_text(value: object) -> str:
    if value is None:
        return "(not reported)"
    if isinstance(value, dict):
        return str(value.get("name") or "(unnamed licence object)")
    if isinstance(value, list):
        return "; ".join(sorted(_licence_text(v) for v in value)) or "(empty list)"
    return str(value)


def read_harness_research(folder: Path) -> Source:
    source = Source(
        name="harness source research",
        label="artifacts/harness-source-research-2026-09-23 (shared checkout, uncommitted)",
        scope="requested", library=False, roots=[folder],
        unit_definition=("one research record about outside material (a skill, plugin, "
                         "contract or tool integration); not a Baltor package"),
        kind_basis="the research record category",
        state_basis=("research-index-manifest.json lifecycle (candidate) and each row's "
                     "qualification_status; these are outside leads, not library candidates"),
        list_identities=False,
    )
    manifest_path = folder / "research-index-manifest.json"
    manifest = load_json(manifest_path)
    source.records.add(str(manifest_path))
    lifecycle = manifest.get("lifecycle")
    collections = {}
    for category, spec in sorted((manifest.get("sources") or {}).items()):
        path = folder / spec["filename"]
        data = path.read_bytes()
        source.records.add(str(path))
        rows = [json.loads(line) for line in data.splitlines() if line.strip()]
        licences = Counter(_licence_text(row.get("license_reported")) for row in rows)
        verified = Counter(str(row.get("license_verified")) for row in rows)
        qualification = Counter(str(row.get("qualification_status")) for row in rows)
        collections[category] = {
            "file": spec["filename"],
            "rows": len(rows),
            "rows_declared_by_manifest": spec.get("rows"),
            "sha256_matches_manifest": hashlib.sha256(data).hexdigest() == spec.get("sha256"),
            "distinct_research_ids": len({row.get("research_id") for row in rows}),
            "distinct_names": len({identity_key(str(row.get("name", ""))) for row in rows}),
            "licence_verified": dict(sorted(verified.items())),
            "licence_reported": dict(sorted(licences.items(), key=lambda kv: (-kv[1], kv[0]))),
            "qualification_status": dict(sorted(qualification.items())),
        }
        for row in rows:
            state = CANDIDATE if lifecycle == "candidate" else STATE_UNKNOWN
            source.units.append(Unit(
                identity=str(row.get("name", "")),
                kind=map_kind("research category", row.get("category")),
                kind_value=f"research category: {row.get('category')}",
                state=state,
                state_detail=(f"outside research record, lifecycle {lifecycle}, "
                              f"qualification {row.get('qualification_status')}, "
                              f"licence verified {row.get('license_verified')}"),
                files=[], version=str(row.get("research_id", "")),
            ))
    source.extra["collections"] = collections
    source.extra["research_index"] = {
        key: manifest.get(key) for key in ("records", "active_store_rows", "lifecycle",
                                           "execution_available", "database_path")}
    source.notes.append(
        "These records describe outside material. The raw third-party content is "
        "kept outside the repository; no file here is a harness payload, so unit "
        "files are zero. Licence declarations are unverified for every record.")
    return source


def read_overnight_batch(batch: Path, matrix: Path) -> Source:
    source = Source(
        name="overnight batch",
        label=".loop-engine-dev/overnight-2026-09-24/batch (shared checkout, running)",
        scope="requested", library=True, roots=[batch],
        unit_definition=("one idea whose journaled outcome is candidate_written; its "
                         "candidates/<lane>/<idea>.md file is the unit file"),
        kind_basis="the idea's declared file_kind in the batch matrix",
        state_basis=("journal.jsonl outcome events; a written candidate passed only the "
                     "generation-time shape check, so it is a candidate"),
    )
    events, snapshot = read_jsonl_prefix(batch / "journal.jsonl")
    source.records.add(str(batch / "journal.jsonl"))
    source.extra["journal_snapshot"] = snapshot
    last_ts = ""
    outcomes: dict[str, tuple[str, str]] = {}
    repeated = 0
    dispatched = set()
    for event in events:
        last_ts = max(last_ts, str(event.get("ts", "")))
        if event.get("event") == "dispatch":
            dispatched.add(event.get("idea_id"))
        if event.get("event") == "outcome":
            if event.get("idea_id") in outcomes:
                repeated += 1
            outcomes[event.get("idea_id")] = (event.get("lane_id"), event.get("outcome"))
    source.extra["journal_snapshot"]["last_event_ts"] = last_ts
    kinds: dict[str, str] = {}
    defaulted = 0
    if matrix.is_file():
        document = load_json(matrix)
        source.records.add(str(matrix))
        for idea in document.get("ideas", []):
            if "file_kind" in idea:
                kinds[idea["id"]] = idea["file_kind"]
            else:
                # tools/opencode_generation_lanes.py treats a missing field as skill.
                kinds[idea["id"]] = "skill"
                defaulted += 1
    written_paths = set()
    per_lane = Counter()
    for idea, (lane, outcome) in sorted(outcomes.items()):
        if outcome != "candidate_written":
            source.attempts[outcome] += 1
            continue
        path = batch / "candidates" / str(lane) / f"{idea}.md"
        written_paths.add(str(path))
        per_lane[str(lane)] += 1
        entry = file_entry(path)
        value = kinds.get(idea)
        source.units.append(Unit(
            identity=idea,
            kind=map_kind("idea file kind", value) if value is not None else UNKNOWN,
            kind_value=f"idea file kind: {value}",
            state=CANDIDATE,
            state_detail="written after the generation-time shape check; no review pre-check",
            files=[entry], version=entry.sha256 or "", group=str(lane),
        ))
    in_flight = sorted(i for i in dispatched if i not in outcomes)
    if in_flight:
        source.attempts["dispatched, no outcome journaled yet"] += len(in_flight)
    on_disk = {str(p) for p in (batch / "candidates").glob("*/*.md")}
    status_path = batch / "status.json"
    if status_path.is_file():
        status = load_json(status_path)
        source.records.add(str(status_path))
        source.extra["status_as_reported_by_the_batch"] = {
            key: status.get(key) for key in ("state", "updated_at", "ideas_total", "candidates",
                                             "failed", "remaining", "calls_used", "calls_ceiling")}
        lanes = status.get("lanes") or {}
        source.extra["lanes"] = {
            lane: {"provider": info.get("provider"), "model": info.get("model"),
                   "units_in_this_inventory": per_lane.get(lane, 0)}
            for lane, info in sorted(lanes.items())}
    source.extra["candidate_files_on_disk"] = len(on_disk)
    source.extra["candidate_files_on_disk_without_a_journaled_outcome"] = len(on_disk - written_paths)
    source.extra["journaled_candidates_without_a_file"] = len(written_paths - on_disk)
    source.extra["ideas_with_more_than_one_outcome"] = repeated
    source.extra["ideas_whose_file_kind_defaulted_to_skill"] = defaulted
    source.notes.append(
        "The batch is still running. Counts are as of the journal snapshot above; "
        "files written after it are reported, not counted.")
    return source


def _parse_status_file(path: Path) -> dict:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def read_ollama_wave(search_roots: list[Path]) -> Source:
    source = Source(
        name="Ollama wave drafts",
        label="original native generation runs through Ollama Cloud (drafts outside the repository)",
        scope="requested", library=True, roots=[],
        unit_definition=("one prepared candidate (METHOD.attempt-N/candidates/items.json) "
                         "in a run folder whose run.json names provider ollama_cloud"),
        kind_basis="the proposal family in the attempt's proposals.json",
        state_basis=("run journals; prepared drafts were packaged by the generator but "
                     "never put through a review pre-check"),
    )
    searched = []
    run_folders: list[Path] = []
    for root in search_roots:
        found_here = []
        if root.is_dir():
            for pattern in ("*/run.json", "*/*/run.json"):
                for run_path in sorted(root.glob(pattern)):
                    try:
                        run = load_json(run_path)
                    except (OSError, ValueError):
                        continue
                    if (isinstance(run, dict)
                            and str(run.get("record_type", "")).startswith("original_native_generation_run/")
                            and run.get("provider") == "ollama_cloud"
                            and (run_path.parent / "journal.jsonl").is_file()):
                        found_here.append(run_path.parent)
        searched.append({"root": str(root), "exists": root.is_dir(),
                         "run_folders_found": [str(p) for p in found_here]})
        run_folders.extend(found_here)
    source.roots = sorted(set(run_folders))
    runs = {}
    for folder in source.roots:
        run = load_json(folder / "run.json")
        source.records.add(str(folder / "run.json"))
        summary = _summarize_generation_journal(folder / "journal.jsonl", source)
        runs[folder.name] = {
            "model": run.get("model"), "producer_family": run.get("producer_family"),
            "call_ceiling": run.get("call_ceiling"), "dispatches": summary["dispatches"],
            "completions": summary["completions"], "outcomes": summary["outcomes"],
            "pending": summary["pending"],
        }
        for code, count in summary["outcomes"].items():
            if code != "prepared":
                source.attempts[f"{folder.name}: {code}"] += count
        for prepared in summary["prepared"]:
            candidates = folder / prepared["prepared_path"]
            items_path = candidates / "items.json"
            if not items_path.is_file():
                source.attempts[f"{folder.name}: prepared in the journal, items.json missing"] += 1
                continue
            families = _read_proposal_families(candidates.parent / "proposals.json", source)
            for item in _read_v3_items(items_path, source):
                family = families.get(item["identity"])
                source.units.append(Unit(
                    identity=item["identity"],
                    kind=map_kind("proposal family", family),
                    kind_value=f"proposal family: {family}",
                    state=CANDIDATE,
                    state_detail="prepared by the generator; no review pre-check",
                    files=item["files"], version=item["digest"], group=folder.name,
                    producer_family=item["producer_family"],
                ))
    refused_runs = {}
    for root in search_roots:
        if not root.is_dir():
            continue
        for status_path in sorted(root.glob("*.status")):
            values = _parse_status_file(status_path)
            if values.get("output_folder_created") == "no":
                source.records.add(str(status_path))
                refused_runs[status_path.stem] = {
                    "model": values.get("model"), "family": values.get("family"),
                    "dispatches": values.get("dispatches"),
                    "stop_reason": values.get("stop_reason"),
                }
    source.extra["searched_roots"] = searched
    source.extra["runs"] = runs
    source.extra["runs_refused_before_any_dispatch"] = refused_runs
    return source


# -- folders found outside the requested list -------------------------------

def read_mixed_native_originals(first: Path, successor: Path, review_folder: Path) -> Source:
    source = Source(
        name="mixed native originals",
        label=("artifacts/mixed-native-originals-2026-09-23 and "
               "artifacts/mixed-native-originals-contract-v2-2026-09-23"),
        scope="additional", library=True, roots=[first, successor],
        unit_definition=("one method identity; the current version is the contract "
                         "successor, earlier prepared trees are version history"),
        kind_basis="the proposal family in the cohort's proposals file",
        state_basis=("native pre-check records in artifacts/native-package-review-2026-09-23, "
                     "matched to package bytes by digest"),
    )
    # Order from the two READMEs: prepared/ is the earlier version retained beside
    # prepared-final/, and the contract successor replaces prepared-final/.
    ordered = [("prepared", first / "prepared" / "items.json"),
               ("prepared-final", first / "prepared-final" / "items.json"),
               ("contract-v2", successor / "prepared" / "items.json")]
    families = {}
    for proposals in sorted(list(first.glob("proposals*.json")) + list(successor.glob("proposals*.json"))):
        families.update(_read_proposal_families(proposals, source))
    checks: dict[str, tuple[bool, str]] = {}
    # The three records carry no timestamps and arrived in one commit. The
    # review README describes the first refusal and the repair that passed; the
    # passive-path record came after that repair. A later record wins.
    ordered_checks = ("mixed-native-originals-prechecks-first.json",
                      "mixed-native-originals-prechecks-after-profile-repair.json",
                      "mixed-native-originals-after-passive-path-repair.json")
    for path in (review_folder / name for name in ordered_checks):
        if not path.is_file():
            continue
        document = load_json(path)
        source.records.add(str(path))
        for row in document.get("rows", []):
            checks[row.get("package_digest")] = (bool((row.get("prechecks") or {}).get("refused")), path.name)
    history: dict[str, list] = {}
    for label, items_path in ordered:
        if not items_path.is_file():
            continue
        for item in _read_v3_items(items_path, source):
            seen = history.setdefault(item["identity"], [])
            if seen and seen[-1][1]["digest"] == item["digest"]:
                continue
            seen.append((label, item))
    for identity in sorted(history):
        versions = history[identity]
        label, item = versions[-1]
        check = checks.get(item["digest"])
        if check is None:
            earlier = [checks[v["digest"]] for _, v in versions[:-1] if v["digest"] in checks]
            state = CANDIDATE
            detail = "no pre-check record for these bytes"
            if earlier and not earlier[-1][0]:
                detail += f"; an earlier version passed ({earlier[-1][1]})"
        elif check[0]:
            state, detail = REFUSED, f"refused ({check[1]})"
        else:
            state, detail = PASSED, f"passed the native pre-checks ({check[1]})"
        family = families.get(identity)
        source.units.append(Unit(
            identity=identity, kind=map_kind("proposal family", family),
            kind_value=f"proposal family: {family}", state=state, state_detail=detail,
            files=item["files"], version=item["digest"], group=label,
            producer_family=item["producer_family"],
        ))
        for version_label, version in versions:
            source.versions.append({"identity": identity, "package_digest": version["digest"],
                                    "batches": [version_label], "current": version is item,
                                    "state": ("passed" if version["digest"] in checks
                                              and not checks[version["digest"]][0] else
                                              "refused" if version["digest"] in checks else
                                              "no pre-check record")})
    return source


def read_original_native_generation(folder: Path) -> Source:
    source = Source(
        name="original native generation live runs",
        label="artifacts/original-native-generation-2026-09-23",
        scope="additional", library=True, roots=[folder],
        unit_definition="one prepared candidate in a live run attempt folder",
        kind_basis="the proposal family in the attempt's proposals.json",
        state_basis="run journal and run record; no review pre-check",
    )
    for journal in sorted(folder.glob("*/journal.jsonl")):
        summary = _summarize_generation_journal(journal, source)
        for code, count in summary["outcomes"].items():
            if code != "prepared":
                source.attempts[f"{journal.parent.name}: {code}"] += count
        for prepared in summary["prepared"]:
            candidates = journal.parent / prepared["prepared_path"]
            families = _read_proposal_families(candidates.parent / "proposals.json", source)
            for item in _read_v3_items(candidates / "items.json", source):
                family = families.get(item["identity"])
                source.units.append(Unit(
                    identity=item["identity"], kind=map_kind("proposal family", family),
                    kind_value=f"proposal family: {family}", state=CANDIDATE,
                    state_detail="prepared by the generator; no review pre-check",
                    files=item["files"], version=item["digest"], group=journal.parent.name,
                    producer_family=item["producer_family"],
                ))
    return source


def read_plugin_context(folder: Path) -> Source:
    source = Source(
        name="harness plugin context",
        label="artifacts/harness-plugin-context-2026-09-23",
        scope="additional", library=True, roots=[folder],
        unit_definition="one plugin package in candidate-manifest.json",
        kind_basis="candidate-manifest.json record_type",
        state_basis="candidate-manifest.json status and independently_approved",
    )
    manifest_path = folder / "candidate-manifest.json"
    manifest = load_json(manifest_path)
    source.records.add(str(manifest_path))
    candidate = manifest.get("status") == "candidate_only" and not manifest.get("independently_approved")
    source.units.append(Unit(
        identity=manifest["package_id"],
        kind=map_kind("plugin inventory record type", manifest.get("record_type")),
        kind_value=f"plugin inventory record type: {manifest.get('record_type')}",
        state=CANDIDATE if candidate else STATE_UNKNOWN,
        state_detail="status candidate_only, not independently approved" if candidate else "status not recorded",
        files=[file_entry(folder / "plugin" / row["path"], row.get("sha256"))
               for row in manifest.get("files", [])],
        producer_family=str(manifest.get("producer_model_family", "")).lower(),
    ))
    return source


# -- summaries and totals -----------------------------------------------------

def _counter_in_order(counter: Counter, order: tuple) -> dict:
    result = {name: counter[name] for name in order if counter.get(name)}
    for name in sorted(counter):
        if name not in result and counter[name]:
            result[name] = counter[name]
    return result


def _git_output(arguments: list[str]) -> str | None:
    try:
        completed = subprocess.run(arguments, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


def describe_root(path: Path, worktree: Path | None, shared: Path | None,
                  revision: str | None) -> dict:
    info = {"path": str(path), "exists": path.exists()}
    for repository, label in ((worktree, "inventory worktree"), (shared, "shared checkout")):
        if repository is None:
            continue
        try:
            relative = path.resolve().relative_to(repository.resolve())
        except ValueError:
            continue
        output = _git_output(["git", "-C", str(repository), "ls-files", "-z", "--", str(relative)])
        tracked = None if output is None else len([p for p in output.split("\0") if p])
        if label == "inventory worktree":
            info["location"] = f"committed tree of the inventory worktree at {revision}"
        else:
            info["location"] = "shared checkout /home/username/loop-engine"
        info["files_tracked_by_git_here"] = tracked
        return info
    info["location"] = "outside any repository checkout"
    return info


def summarize_source(source: Source, context: dict | None = None) -> dict:
    context = context or {}
    kinds = Counter(unit.kind for unit in source.units)
    states = Counter(unit.state for unit in source.units)
    details = Counter(f"{unit.state}: {unit.state_detail}" for unit in source.units)
    declared = Counter(f"{unit.kind_value} -> {unit.kind}" for unit in source.units)
    unit_files = [entry for unit in source.units for entry in unit.files]
    present = [entry for entry in unit_files if not entry.missing]
    keys = Counter(unit.key for unit in source.units)
    all_files = []
    for root in source.roots:
        all_files.extend(list_files(root))
    all_by_extension = Counter(extension_of(str(p)) for p in all_files)
    summary = {
        "name": source.name,
        "label": source.label,
        "scope": source.scope,
        "part_of_the_library": source.library,
        "roots": [describe_root(root, context.get("worktree"), context.get("shared"),
                                context.get("revision")) if context else {"path": str(root)}
                  for root in source.roots],
        "unit_definition": source.unit_definition,
        "kind_basis": source.kind_basis,
        "state_basis": source.state_basis,
        "units": len(source.units),
        "distinct_identities": len(keys),
        "identity_keys_repeated_within_this_source": sorted(k for k, n in keys.items() if n > 1)
        if source.list_identities else sum(1 for n in keys.values() if n > 1),
        "files": len(present),
        "unit_files_declared_but_missing": sum(1 for e in unit_files if e.missing),
        "unit_files_whose_digest_differs_from_the_record": sum(1 for e in unit_files if e.mismatch),
        "unit_file_bytes": sum(e.size or 0 for e in present),
        "unit_files_distinct_digests": len({e.sha256 for e in present}),
        "unit_files_by_extension": dict(sorted(Counter(extension_of(e.path) for e in present).items())),
        "all_files": len(all_files),
        "all_files_by_extension": dict(sorted(all_by_extension.items())),
        "kinds": _counter_in_order(kinds, CANONICAL_KINDS),
        "declared_kind_values": dict(sorted(declared.items())),
        "states": {state: states.get(state, 0) for state in STATES},
        "state_details": dict(sorted(details.items())),
        "producer_families": dict(sorted(Counter(u.producer_family or "(not recorded)"
                                                 for u in source.units).items())),
        "attempts_without_a_unit": dict(sorted(source.attempts.items())),
        "package_versions": len(source.versions) if source.versions else None,
        "version_history": source.versions or None,
        "records_read": sorted(source.records),
        "notes": source.notes,
        "details": source.extra,
    }
    if source.list_identities:
        summary["identities"] = sorted(unit.identity for unit in source.units)
    return summary


def aggregate(sources: list[Source]) -> dict:
    """Totals over library sources with identities deduplicated across sources."""
    order = {source.name: index for index, source in enumerate(sources)}
    parent: dict[str, str] = {}

    def find(key: str) -> str:
        parent.setdefault(key, key)
        root = key
        while parent[root] != root:
            root = parent[root]
        while parent[key] != root:
            parent[key], key = root, parent[key]
        return root

    def union(first: str, second: str) -> None:
        a, b = find(first), find(second)
        if a != b:
            parent[max(a, b)] = min(a, b)

    members: list[tuple[str, Unit]] = []
    for source in sources:
        for unit in source.units:
            find(unit.key)
            for alias in unit.aliases:
                union(unit.key, identity_key(alias))
            members.append((source.name, unit))
    groups: dict[str, list[tuple[str, Unit]]] = {}
    for name, unit in members:
        groups.setdefault(find(unit.key), []).append((name, unit))
    by_kind: Counter = Counter()
    by_state: Counter = Counter()
    overlaps = []
    for root, group in sorted(groups.items()):
        best = min(group, key=lambda pair: (STATE_RANK[pair[1].state], order[pair[0]]))
        by_kind[best[1].kind] += 1
        by_state[best[1].state] += 1
        names = sorted({name for name, _ in group}, key=lambda n: order[n])
        if len(names) > 1:
            overlaps.append({
                "identity_key": root,
                "identity_keys": sorted({unit.key for _, unit in group}
                                        | {identity_key(a) for _, unit in group for a in unit.aliases}),
                "sources": names,
                "raw_identities": sorted({f"{name}: {unit.identity}" for name, unit in group}),
                "kinds": sorted({unit.kind for _, unit in group}),
                "states": sorted({unit.state for _, unit in group}),
                "counted_as": {"source": best[0], "kind": best[1].kind, "state": best[1].state},
            })
    neighbours = []
    tokens = [(name, unit.identity, name_words(unit.key)) for name, unit in members]
    for index, (name, identity, words) in enumerate(tokens):
        for other_name, other_identity, other_words in tokens[index + 1:]:
            if other_name == name:
                continue
            shared = words & other_words
            shortest = min(len(words), len(other_words))
            if len(shared) >= 3 and shortest and len(shared) / shortest >= 0.75:
                neighbours.append({
                    "first": f"{name}: {identity}", "second": f"{other_name}: {other_identity}",
                    "shared_words": sorted(shared)})
    files = [entry for _, unit in members for entry in unit.files if not entry.missing]
    digest_sources: dict[str, set] = {}
    for name, unit in members:
        for entry in unit.files:
            if entry.sha256:
                digest_sources.setdefault(entry.sha256, set()).add(name)
    return {
        "sources": [source.name for source in sources],
        "units_sum": len(members),
        "distinct_identities": len(groups),
        "overlap_count": len(overlaps),
        "overlaps": overlaps,
        "name_neighbours_not_counted_as_overlaps": sorted(
            neighbours, key=lambda row: (row["first"], row["second"])),
        "by_kind_deduplicated": _counter_in_order(by_kind, CANONICAL_KINDS),
        "by_state_deduplicated": {state: by_state.get(state, 0) for state in STATES},
        "by_kind_sum": _counter_in_order(Counter(u.kind for _, u in members), CANONICAL_KINDS),
        "by_state_sum": {state: sum(1 for _, u in members if u.state == state) for state in STATES},
        "unit_files_sum": len(files),
        "unit_files_distinct_digests": len({e.sha256 for e in files}),
        "unit_file_digests_shared_by_more_than_one_source": sum(
            1 for names in digest_sources.values() if len(names) > 1),
        "unit_files_by_extension_sum": dict(sorted(Counter(extension_of(e.path) for e in files).items())),
    }


def research_collisions(library: list[Source], research: Source) -> list[dict]:
    names: dict[str, list[str]] = {}
    for unit in research.units:
        names.setdefault(unit.key, []).append(unit.kind)
    collisions = []
    for source in library:
        for unit in source.units:
            if unit.key in names:
                collisions.append({"identity_key": unit.key, "library_source": source.name,
                                   "library_identity": unit.identity,
                                   "research_kinds": sorted(set(names[unit.key]))})
    return sorted(collisions, key=lambda row: (row["identity_key"], row["library_source"]))


# -- assembly -------------------------------------------------------------------

def build_sources(worktree: Path, shared: Path, private_generation: Path,
                  session_archive: Path, tactical_worktree: Path | None = None,
                  ) -> tuple[list[Source], Source, list[Source]]:
    artifacts = worktree / "artifacts"
    shared_artifacts = shared / "artifacts"
    requested = [
        read_served_catalogue(
            worktree / "examples" / "29_intelligence_service" / "starter-catalogue",
            artifacts / "architecture-audit-2026-09-19" / "pilot-release-24.json"),
        read_first_party_waves(
            [artifacts / name for name in (
                "first-party-harness-candidates-2026-09-22",
                "first-party-harness-candidates-2026-09-22-wave-2",
                "first-party-harness-candidates-2026-09-22-wave-3",
                "first-party-harness-candidates-2026-09-22-wave-4-ops")],
            artifacts / "first-party-harness-candidates-2026-09-22" / "GENERATION-GUIDE.md"),
        read_wave5(artifacts / "first-party-harness-candidates-2026-09-24-wave-5"),
        read_format_pilots(artifacts / "harness-intelligence-format-pilot-2026-09-22",
                           artifacts / "harness-intelligence-format-pilot-2026-09-22-wave-2"),
        read_native_preparation(artifacts / "native-candidate-preparation-2026-09-23",
                                artifacts / "tactical-first-batch-2026-09-24"),
        read_tactical_blocks(
            artifacts / "native-blocks-batch-2026-09-24",
            (tactical_worktree / "artifacts" / "native-blocks-batch-2026-09-24"
             if tactical_worktree is not None else None)),
        read_prepared_cohort(
            "Codex component supply",
            "artifacts/codex-component-supply-2026-09-23 (shared checkout, uncommitted)",
            shared_artifacts / "codex-component-supply-2026-09-23",
            shared_artifacts / "codex-component-supply-2026-09-23" / "prepared-v2" / "items.json",
            shared_artifacts / "codex-component-supply-2026-09-23" / "proposals-v2.json",
            shared_artifacts / "codex-component-supply-2026-09-23" / "staging-report-v2.json"),
        read_prepared_cohort(
            "Codex research-inspired components",
            "artifacts/codex-research-inspired-components-2026-09-23 (shared checkout, uncommitted)",
            shared_artifacts / "codex-research-inspired-components-2026-09-23",
            shared_artifacts / "codex-research-inspired-components-2026-09-23" / "prepared-v1" / "items.json",
            shared_artifacts / "codex-research-inspired-components-2026-09-23" / "proposals-v1.json",
            shared_artifacts / "codex-research-inspired-components-2026-09-23" / "staging-report-v1.json"),
        read_gemma4_components(shared_artifacts / "gemma4-harness-components-2026-09-23"),
        read_overnight_batch(shared / ".loop-engine-dev" / "overnight-2026-09-24" / "batch",
                             shared / ".loop-engine-dev" / "overnight-2026-09-24" / "matrix-10k.json"),
        read_ollama_wave([session_archive, private_generation]),
    ]
    research = read_harness_research(shared_artifacts / "harness-source-research-2026-09-23")
    additional = [
        read_mixed_native_originals(artifacts / "mixed-native-originals-2026-09-23",
                                    artifacts / "mixed-native-originals-contract-v2-2026-09-23",
                                    artifacts / "native-package-review-2026-09-23"),
        read_original_native_generation(artifacts / "original-native-generation-2026-09-23"),
        read_plugin_context(artifacts / "harness-plugin-context-2026-09-23"),
    ]
    return requested, research, additional


EXCLUDED_FOLDERS = [
    {"folder": "artifacts/intelligence-layer-coverage-2026-09-21/pack",
     "reason": "24 candidate items of the loop_native family (Runtime History and User "
               "Feedback layers), not harness intelligence"},
    {"folder": "artifacts/focused-step-packet-2026-09-23",
     "reason": "two example step packets; its README records zero persistent library items"},
    {"folder": "/home/username/baltor-private/generation-2026-09-23/<plan folders>",
     "reason": "plan-building work for the Ollama wave (plans, builders and checks), not drafts"},
]


def build_inventory(worktree: Path, shared: Path, private_generation: Path,
                    session_archive: Path, tactical_worktree: Path | None = None) -> dict:
    revision = (_git_output(["git", "-C", str(worktree), "rev-parse", "HEAD"]) or "").strip() or None
    context = {"worktree": worktree, "shared": shared, "revision": revision}
    requested, research, additional = build_sources(worktree, shared, private_generation,
                                                    session_archive, tactical_worktree)
    requested_library = [s for s in requested if s.library]
    return {
        "record_type": RECORD_TYPE,
        "generated_by": "tools/inventory_harness_library.py",
        "inventory_worktree_revision": revision,
        "method": {
            "reads_only": True, "network_requests": 0, "model_calls": 0,
            "canonical_kinds": list(CANONICAL_KINDS), "states": list(STATES),
            "kind_vocabularies": KIND_VOCABULARIES,
            "identity_key": ("lowercase; remove baltor.<context|tool|connection>. and "
                             "codex.component.supply.<digits>. prefixes and a trailing "
                             ".v<digits>; replace each run of other characters with '_'"),
            "deduplication": ("identities are grouped by identity key and declared aliases; "
                              "a group counts once, with the kind and state of its most "
                              "advanced record (approved and served, then passed a "
                              "precheck, then candidate, then refused, then unknown)"),
            "passed_a_precheck_means": ("a recorded review pre-check passed: wave 5 "
                                        "check_package.py check-all or the candidate review "
                                        "native pre-checks; not a generation-time shape check"),
        },
        "sources": [summarize_source(s, context) for s in requested]
        + [summarize_source(research, context)],
        "additional_sources_not_in_the_requested_list": [summarize_source(s, context)
                                                        for s in additional],
        "excluded_folders": EXCLUDED_FOLDERS,
        "totals": {
            "library_requested_sources": aggregate(requested_library),
            "library_with_additional_sources": aggregate(requested_library + additional),
            "outside_research": {
                "records": len(research.units),
                "by_kind": _counter_in_order(Counter(u.kind for u in research.units), CANONICAL_KINDS),
                "by_state": {s: sum(1 for u in research.units if u.state == s) for s in STATES},
                "name_collisions_with_library_identities": research_collisions(
                    requested_library + additional, research),
            },
        },
    }


def render_markdown(inventory: dict) -> str:
    """A short human summary; inventory.json holds every basis and list."""
    def states_text(states: dict) -> str:
        return ", ".join(f"{k} {v}" for k, v in states.items() if v) or "none"

    def kinds_text(kinds: dict) -> str:
        return ", ".join(f"{k} {v}" for k, v in kinds.items()) or "none"

    summaries = inventory["sources"] + inventory["additional_sources_not_in_the_requested_list"]
    by_name = {summary["name"]: summary for summary in summaries}
    lines = [
        "# Harness library inventory, September 24, 2026",
        "",
        "Generated by `tools/inventory_harness_library.py` from the worktree at "
        f"revision `{(inventory.get('inventory_worktree_revision') or 'unknown')[:10]}`. "
        "[inventory.json](inventory.json) holds every basis, identity list and version "
        "history. The script reads records only. It made no network request and no model "
        "call, and it changed no source.",
        "",
        "A unit is one logical package or single-file candidate, as the source's records "
        "count it. Unit files are the files a harness receives for the current version of "
        "each unit. \"Passed a precheck\" means a recorded review pre-check passed; a "
        "generation-time shape check or package preparation does not count.",
        "",
        "## Totals",
        "",
    ]
    served = by_name.get("served starter catalogue")
    if served:
        release = served["details"].get("live_release_record") or {}
        lines += [
            f"**Served now.** {served['states'][SERVED]} approved items, named by the committed "
            f"host release manifest; the release record for Fly release {release.get('fly_release')} "
            f"names catalogue release `{str(release.get('catalogue_release_id'))[:12]}` with "
            f"{release.get('items')} items. The live service was not queried.",
            "",
        ]
    for label, key in (("Requested sources", "library_requested_sources"),
                       ("Requested sources plus the additional folders found",
                        "library_with_additional_sources")):
        total = inventory["totals"][key]
        lines += [
            f"**{label}.** {total['units_sum']} units, {total['distinct_identities']} distinct "
            f"identities after deduplication, {total['overlap_count']} identities in more than one "
            f"source, {total['unit_files_sum']} unit files "
            f"({total['unit_files_distinct_digests']} distinct file digests).",
            "",
            f"- Kinds, deduplicated: {kinds_text(total['by_kind_deduplicated'])}.",
            f"- States, deduplicated: {states_text(total['by_state_deduplicated'])}.",
            "",
        ]
    research = inventory["totals"]["outside_research"]
    research_summary = by_name.get("harness source research")
    verified = 0
    if research_summary:
        verified = sum(int(c["licence_verified"].get("True", 0))
                       for c in research_summary["details"]["collections"].values())
    lines += [
        f"**Outside research, not library units.** {research['records']} research records about "
        f"outside material: {kinds_text(research['by_kind'])}. Licence verified for {verified} "
        f"of them. {len(research['name_collisions_with_library_identities'])} library identities "
        "share a name with a research record.",
        "",
        "## Per source",
        "",
        "| Source | Units | Identities | Unit files | All files | Kinds | States |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for summary in summaries:
        name = summary["name"]
        if summary["scope"] == "additional":
            name += " (additional folder)"
        if not summary["part_of_the_library"]:
            name += " (outside research)"
        lines.append(
            f"| {name} | {summary['units']} | {summary['distinct_identities']} | "
            f"{summary['files']} | {summary['all_files']} | {kinds_text(summary['kinds'])} | "
            f"{states_text(summary['states'])} |")
    lines += ["", "## Overlaps", ""]
    requested = inventory["totals"]["library_requested_sources"]
    extended = inventory["totals"]["library_with_additional_sources"]
    for label, total in (("Requested sources", requested),
                         ("With the additional folders", extended)):
        if total["overlaps"]:
            for row in total["overlaps"]:
                lines.append(f"- {label}: `{', '.join(row['identity_keys'])}` in "
                             f"{', '.join(row['sources'])}; counted once as "
                             f"{row['counted_as']['kind']}, {row['counted_as']['state']}.")
        else:
            lines.append(f"- {label}: no identity key appears in more than one source.")
    for row in extended["name_neighbours_not_counted_as_overlaps"]:
        lines.append(f"- Name neighbours, not counted as overlaps: {row['first']} and "
                     f"{row['second']} share {', '.join(row['shared_words'])}.")
    lines += ["", "## Notes and limits", ""]
    for summary in summaries:
        if summary.get("package_versions"):
            lines.append(f"- {summary['name']}: {summary['units']} identities in "
                         f"{summary['package_versions']} package versions; states are for the "
                         "current version of each identity.")
    for summary in summaries:
        attempts = summary["attempts_without_a_unit"]
        if attempts:
            lines.append(f"- {summary['name']}: {sum(attempts.values())} generation attempts "
                         "produced no unit (outcomes by code are in inventory.json).")
    overnight = by_name.get("overnight batch")
    if overnight:
        details = overnight["details"]
        lines.append(
            "- The overnight batch is still running. This count reads its journal up to "
            f"{details['journal_snapshot'].get('last_event_ts')}. "
            f"{details['candidate_files_on_disk_without_a_journaled_outcome']} candidate files on "
            "disk had no journaled outcome yet and are not counted.")
    wave = by_name.get("Ollama wave drafts")
    if wave:
        roots = wave["details"]["searched_roots"]
        found = [r["root"] for r in roots if r["run_folders_found"]]
        empty = [r["root"] for r in roots if not r["run_folders_found"]]
        lines.append(
            f"- The Ollama wave run folders were found in {', '.join(found) or 'no searched folder'}"
            + (f"; the named archive {', '.join(empty)} holds none." if empty else "."))
    wave5 = by_name.get("first-party wave 5")
    if wave5:
        drift = wave5["details"].get("payload_inventory", {})
        prefix = "digest differs from package.json, in packages whose state is "
        split = "; ".join(f"{key[len(prefix):]} {value}" for key, value in drift.items()
                          if key.startswith(prefix)) or "none"
        lines.append(
            f"- First-party wave 5: {drift.get('digest differs from package.json', 0)} payload "
            "files differ from the digest their package.json records (by package state: "
            f"{split}); {drift.get('declared but missing on disk', 0)} declared files are "
            f"missing and {drift.get('on disk but not declared', 0)} files on disk are not declared.")
    lines += [
        "- Overlaps are exact matches of the normalized identity key or of an alias a record "
        "declares. Two differently named methods that do the same work are not detected.",
        "- Kinds come from the declared fields each source's `kind_basis` names. A value "
        "without a mapping stays unknown.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--worktree", type=Path, default=ROOT)
    parser.add_argument("--shared-checkout", type=Path, default=DEFAULT_SHARED_CHECKOUT)
    parser.add_argument("--private-generation", type=Path, default=DEFAULT_PRIVATE_GENERATION)
    parser.add_argument("--session-archive", type=Path, default=DEFAULT_SESSION_ARCHIVE)
    parser.add_argument("--tactical-worktree", type=Path, default=DEFAULT_TACTICAL_WORKTREE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true",
                        help="replace an existing inventory.json and inventory.md")
    arguments = parser.parse_args(argv)
    json_path = arguments.output_dir / "inventory.json"
    markdown_path = arguments.output_dir / "inventory.md"
    if not arguments.replace and (json_path.exists() or markdown_path.exists()):
        print(f"refusing to replace {json_path} without --replace", file=sys.stderr)
        return 2
    inventory = build_inventory(arguments.worktree, arguments.shared_checkout,
                                arguments.private_generation, arguments.session_archive,
                                arguments.tactical_worktree)
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(inventory, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    markdown_path.write_text(render_markdown(inventory), encoding="utf-8")
    totals = inventory["totals"]["library_requested_sources"]
    print(json.dumps({"json": str(json_path), "markdown": str(markdown_path),
                      "units_sum": totals["units_sum"],
                      "distinct_identities": totals["distinct_identities"],
                      "overlap_count": totals["overlap_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
