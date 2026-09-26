#!/usr/bin/env python3
"""Generate variations of served library items as candidates, through the existing generation and review pipeline.

The owner, September 26, 2026: oracles that run on the server side "review our files and double check them and
generate variations of them automatically", without breaking anything. This command is that oracle for
variations. It reads the active release bundle (the newest ``daily-*`` folder under ``~/baltor-bundles``, whose
``items.jsonl`` names every served item and whose ``blobs`` hold the bodies), keeps a durable ledger of which
item digests already have a variation, and each run picks up to N served items that have none. For each it
writes one ``harness_idea_record/v1`` whose brief asks for a variation on a declared axis, with the served
item's own text as seed material the lane may copy (its licence allows copying, and the idea records the licence
and the attribution). The rest is the pipeline the overnight batch already uses: generation on the Tactical
lane, attribution, preparation, the native prechecks, one independent screening call by a family other than the
producer's, the reviewed Community folder, and a line in the reviewed-folders list so the next daily slot
publishes it.

```text
One run, each stage journaled in the run folder (a restart skips finished stages)
├── select      bundle + ledger -> ideas.json (harness_idea_batch/v1), selection.json, ledger rows
├── generate    tools/overnight_candidate_batch.start on the Tactical lane only, ceiling 1.3 x ideas
├── attribute   tools/native_proposals_from_overnight_candidates.attribute, committed in the factory repository
├── prepare     ... proposals, then tools/prepare_harness_candidates.prepare -> <run>/candidates
├── prechecks   community_campaign.py prechecks (deterministic, no model call) -> identities.txt
├── review      community_campaign.py review with claude_code.subscription, at most 24 items a run
└── write       tools/write_reviewed_catalogue.py --tier community -> <run>/reviewed, reviewed-folders.txt
```

Why a private factory repository: the factory reads an item's cited sources only as committed at a checkout's
HEAD, and the idea files here quote served bodies, which never enter the public repository. So the attribution
folders are committed to ``~/baltor-library/oracle/factory`` (created on first use with the same MIT LICENSE
bytes as this repository), and every later stage names that repository.

What a variation says about its source: the idea record's ``applicability.variation_of`` names the source
identity, digest and axis; the brief asks the file to state what it varies in its own text; and the reviewed
folder's provenance carries ``variation_of`` (``tools/write_reviewed_catalogue.py``). A served attribute for it
is planned, not built: a new well-known attribute changes the schema every daily bundle validates against.

A stage that cannot run today (an allowance, a missing program, an unreachable endpoint) is recorded in the
journal as an outage and the command stops cleanly with exit code 3. It never invents output. Every model call is
recorded by the lane runner and the review panel with its model, usage and outcome; the review counter under
``~/baltor-library/oracle`` keeps the subscription's total under the owner's cap of 150 review calls.

    PYTHONPATH=src:tools python tools/generate_item_variations.py --run 2026-09-26T1250Z --stage all --count 6

Tests: ``tools/test_generate_item_variations.py`` (fixture bundles and a scripted reviewer; no model call).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent
for entry in (str(HERE), str(REPOSITORY / "src"), str(REPOSITORY)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from build_volume_seed_ideas import _DATATYPE_WORDS, _OPERATION_WORDS, _USE_CASE_WORDS, _pick  # noqa: E402
from harness_idea_matrix import DATATYPES, FACET_DIMENSIONS, FILE_KINDS, OPERATIONS, USE_CASES  # noqa: E402
from loop_engine.core.library_ingestion.step_functions import STEP_FUNCTIONS  # noqa: E402
from loop_engine.core.service_runtime.catalogue_attributes import harness_kind_of  # noqa: E402

BATCH_RECORD_TYPE = "harness_idea_batch/v1"
IDEA_RECORD_TYPE = "harness_idea_record/v1"
BUNDLE_ITEM_RECORD_TYPE = "catalogue_bundle_item/v2"
LEDGER_RECORD_TYPE = "variation_ledger_row/v1"
VARIATION_RECORD_TYPE = "variation_of/v1"
SELECTION_RECORD_TYPE = "variation_selection/v1"
JOURNAL_RECORD_TYPE = "variation_run_event/v1"
#: The batch source kind; tools/overnight_candidate_batch.py treats it as self-grounded (no occupation rotation).
SOURCE_KIND = "served_release_bundle"
LANE_ID, LANE_FAMILY = "lane-tactical-gemma4", "google"
REVIEWER, REVIEW_BATCH, REVIEW_ITEMS_PER_RUN = "claude_code.subscription", 12, 24
#: The owner's cap on review calls through the Claude Code subscription (September 24, 2026).
CLAUDE_REVIEW_CALL_CAP = 150
DEFAULT_COUNT = 12
CEILING_FACTOR = 1.3
EXCERPT_BOUND = 6000
IDENTITY = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
#: Served kinds with a qualified native placement in the adapter (a skill file, an instruction file).
PLACED_KINDS = {"skill": "skill", "instruction_file": "harness_routing"}
OTHER_LAYOUT = {"skill": "harness_routing", "instruction_file": "skill"}
LAYOUT_WORDS = {"skill": "a skill (SKILL.md with YAML frontmatter, for Claude Code and Codex)",
                "harness_routing": "an instruction file (AGENTS.md with YAML frontmatter, for Codex, OpenCode and Pi)"}
AXES = ("alternative_approach", "other_harness_layout", "shorter_form", "stricter_checking", "step_function_version")
AXIS_SLUG = {"alternative_approach": "alt", "other_harness_layout": "layout", "shorter_form": "short",
             "stricter_checking": "strict", "step_function_version": "for"}
AXIS_BRIEF = {
    "alternative_approach": ("Keep the same purpose, the same inputs and the same outputs, but reach the result by "
                             "a different method than the source item uses: a different order of steps, a different "
                             "check, or a different tool a harness already has. Write the full procedure, every step "
                             "and its check, never a summary, and say in one sentence how the approach differs from "
                             "the source."),
    "other_harness_layout": ("Rewrite the item for a different harness's layout, as {layout}. Keep every step and "
                             "check; change the structure so that the other harness picks the file up."),
    "shorter_form": ("Write a shorter form: at most half the length of the source, keeping every step and every check "
                     "a harness needs and dropping examples, repetition and background."),
    "stricter_checking": ("Add stricter checking: every step names the check that shows it worked and what to do when "
                          "that check fails, and the known-wrong case is caught before any result is reported."),
    "step_function_version": ("Write a version for the {function} step function: the file serves a step whose kind "
                              "is {function}, and every instruction in it belongs to that kind of step."),
}
AXIS_KNOWN_WRONG = {
    "alternative_approach": "The variation restates the source item's own steps in new words and calls that a different approach.",
    "other_harness_layout": "The file keeps the source layout's structure, so the other harness does not pick it up.",
    "shorter_form": "The shorter form drops a step or a check the source procedure needs, so a harness following it gets a different result.",
    "stricter_checking": "A check is named but no failing outcome is described, so a harness reports success after a failed check.",
    "step_function_version": "The file claims to serve the {function} step but its instructions belong to another kind of step.",
}
FORMAT_RULES = ("Write the whole variation as one file. The frontmatter holds only name, description and license "
                "(MIT); the body links to no other file and sends the reader to no project file that is not in "
                "this one; describe any command in prose, never in a fenced shell block, and declare no effect "
                "beyond reading files. The datatype, operation and use case named above are search facets: where "
                "they do not fit the source item, follow the source item and keep them out of the file. Name what "
                "you vary in one line of the body: 'Varies {identity} ({licence}) on the axis {axis}; derived from "
                "{source_ref}, whose licence applies to the copied parts.'")
LICENCE_LINE = re.compile(r"^LICENCES=\((.*)\)\s*$", re.MULTILINE)
DEFAULT_LICENCE_SCRIPT = Path("/home/username/baltor-private/tools/daily_library_release.sh")
DEFAULT_BUNDLE_ROOT = Path.home() / "baltor-bundles"
DEFAULT_LIBRARY = Path.home() / "baltor-library"
DEFAULT_LANE_ROOT = Path.home() / ".le-library" / "variations" / "lanes"
CAMPAIGN = REPOSITORY / "artifacts/review-throughput-2026-09-24/community_campaign.py"
PANEL = HERE / "candidate_review/resources/panel.json"
OUTAGE_EXIT = 3


class VariationError(ValueError):
    """A stable refusal code for a run that cannot proceed as declared."""


class Outage(Exception):
    """A stage that cannot run today; recorded, never worked around."""


def refuse(code: str, message: str = "") -> None:
    raise VariationError(f"{code}: {message}" if message else code)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read_jsonl(path: Path) -> list:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


# -- the accepted licences and the bundle ---------------------------------------------------------------------

def accepted_licences(script: Path) -> tuple:
    """The licences the daily release accepts, read from its LICENCES line; a script without one refuses."""
    try:
        text = script.read_text(encoding="utf-8")
    except OSError:
        refuse("licence_list_unreadable", f"{script} cannot be read")
    found = LICENCE_LINE.search(text)
    if not found:
        refuse("licence_list_missing", f"{script} has no LICENCES=( ... ) line")
    licences = tuple(value.strip().strip('"\'') for value in found.group(1).split() if value.strip())
    if not licences:
        refuse("licence_list_missing", f"{script} declares no licence")
    return licences


def newest_bundle(root: Path) -> Path:
    """The newest daily release bundle folder: the last daily-* name in order, with items and blobs."""
    folders = sorted(path for path in root.glob("daily-*") if path.is_dir() and (path / "items.jsonl").is_file()
                     and (path / "blobs").is_dir())
    if not folders:
        refuse("bundle_missing", f"no daily-* bundle with items.jsonl and blobs under {root}")
    return folders[-1]


def read_bundle_items(bundle: Path) -> list:
    items = []
    for line in (bundle / "items.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("record_type") != BUNDLE_ITEM_RECORD_TYPE:
            refuse("bundle_item_unsupported", f"a bundle row is {row.get('record_type')!r}")
        items.append(row)
    if not items:
        refuse("bundle_empty", str(bundle))
    return items


def body_of(bundle: Path, digest: str) -> bytes:
    """The served bytes of one digest from the bundle's blob store, checked against the digest."""
    path = bundle / "blobs" / "sha256" / digest[:2] / digest
    if path.is_symlink() or not path.is_file():
        refuse("body_missing", digest)
    data = path.read_bytes()
    if _sha256(data) != digest:
        refuse("body_digest_mismatch", digest)
    return data


ENTRY_ROLES = {"skill": "skill_definition", "instruction_file": "instruction_file"}
ATTRIBUTION_FILE, ATTRIBUTION_BOUND = "ATTRIBUTION.md", 1500


def entry_file(item: dict) -> dict:
    """The one package file a harness picks up (the skill definition or the instruction file), or empty."""
    role = ENTRY_ROLES.get(item["reference"]["kind"], "")
    files = [entry for entry in (item.get("package") or {}).get("files", []) if entry.get("role") == role]
    return files[0] if len(files) == 1 else {}


def attribution_text(bundle: Path, item: dict) -> str:
    """The package's own attribution file, bounded, when the imported package carries one."""
    for entry in (item.get("package") or {}).get("files", []):
        if entry.get("path") == ATTRIBUTION_FILE:
            try:
                return body_of(bundle, entry["digest"]).decode("utf-8", "replace")[:ATTRIBUTION_BOUND]
            except VariationError:
                return ""
    return ""


def snapshot_provenance(snapshot: Path) -> dict:
    """identity -> provenance of the combined snapshot the bundle was built from, when it is readable here."""
    path = snapshot / "items.json"
    if not path.is_file():
        return {}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    found = {}
    for item in record.get("items", []):
        provenance = item.get("provenance")
        identity = (item.get("reference") or {}).get("identity")
        if identity and isinstance(provenance, dict):
            found[identity] = provenance
    return found


# -- the ledger ----------------------------------------------------------------------------------------------

def ledger_digests(path: Path) -> set:
    """Every source digest that already has a variation idea, from the durable ledger."""
    return {row["source_digest"] for row in _read_jsonl(path)
            if row.get("record_type") == LEDGER_RECORD_TYPE and row.get("source_digest")}


# -- selection ------------------------------------------------------------------------------------------------

def _harness_kind(item: dict) -> str:
    reference = item["reference"]
    attributes = item.get("attributes") or {}
    roles = tuple(entry.get("role", "") for entry in (item.get("package") or {}).get("files", []))
    return harness_kind_of(reference["kind"], tuple(reference.get("styles") or ()), roles,
                           str(attributes.get("harness_kind") or ""))


def select_items(items: list, done: set, count: int, licences: tuple) -> tuple:
    """(picked, skipped): up to ``count`` served items with no variation yet.

    Order: items with step-function tags first, the most tags first, then by identity; then the rest by identity,
    interleaved across harness kinds so one run does not draw one kind only. An item is skipped, with its reason,
    when its licence is not accepted, when its kind has no native placement, or when the ledger already holds it."""
    if count < 1:
        refuse("count_invalid", "a run picks at least one item")
    eligible, skipped, seen = [], [], set()
    for item in sorted(items, key=lambda row: row["reference"]["identity"]):
        reference = item["reference"]
        entry = {"identity": reference["identity"], "digest": reference["digest"], "kind": reference["kind"],
                 "license": reference.get("license", "")}
        if reference["digest"] in seen:
            continue
        seen.add(reference["digest"])
        if reference["digest"] in done:
            skipped.append({**entry, "reason": "already_varied"})
        elif reference.get("license") not in licences:
            skipped.append({**entry, "reason": "licence_not_accepted"})
        elif reference["kind"] not in PLACED_KINDS:
            skipped.append({**entry, "reason": "kind_without_native_placement"})
        elif not entry_file(item):
            skipped.append({**entry, "reason": "package_without_one_entry_file"})
        else:
            eligible.append(item)
    tagged = [item for item in eligible if (item.get("attributes") or {}).get("step_functions")]
    tagged.sort(key=lambda item: (-len(item["attributes"]["step_functions"]), item["reference"]["identity"]))
    rest = [item for item in eligible if item not in tagged]
    by_kind = {}
    for item in rest:
        by_kind.setdefault(_harness_kind(item), []).append(item)
    interleaved, cursors = [], {kind: 0 for kind in sorted(by_kind)}
    while len(interleaved) < len(rest):
        for kind in sorted(by_kind):
            if cursors[kind] < len(by_kind[kind]):
                interleaved.append(by_kind[kind][cursors[kind]])
                cursors[kind] += 1
    picked = (tagged + interleaved)[:count]
    return picked, skipped


# -- ideas ----------------------------------------------------------------------------------------------------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def variation_identity(source_identity: str, axis: str, function: str = "", taken: set = frozenset()) -> str:
    suffix = AXIS_SLUG[axis] + (f"-{_slug(function)}" if axis == "step_function_version" else "")
    base = _slug(source_identity)
    if not base or not base[0].isalpha():
        base = "v-" + base
    limit = 64 - len(suffix) - 1
    identity = f"{base[:limit].rstrip('-')}-{suffix}"
    if identity in taken:
        short = _sha256(f"{source_identity}|{axis}|{function}".encode())[:6]
        identity = f"{base[:limit - 7].rstrip('-')}-{short}-{suffix}"
    if not IDENTITY.match(identity):
        refuse("identity_invalid", identity)
    return identity


def facets_for(text: str, name: str) -> tuple:
    words = (name + " " + text).lower()
    datatype = _pick(words, _DATATYPE_WORDS, "text")
    operation = _pick(words, _OPERATION_WORDS, "transformation")
    use_case = _pick(words, _USE_CASE_WORDS, "software_development")
    assert datatype in DATATYPES and operation in OPERATIONS and use_case in USE_CASES
    return datatype, operation, use_case


def _step_function_for(item: dict, position: int) -> str:
    functions = (item.get("attributes") or {}).get("step_functions") or ()
    return functions[0] if functions else STEP_FUNCTIONS[position % len(STEP_FUNCTIONS)]


def idea_for(item: dict, body: bytes, axis: str, *, bundle_name: str, bundle_digest: str, position: int,
             taken: set, upstream: dict | None = None, attribution_note: str = "") -> dict:
    """One harness_idea_record/v1 asking for a variation of one served item on one declared axis."""
    reference = item["reference"]
    identity, digest, kind, licence = reference["identity"], reference["digest"], reference["kind"], reference["license"]
    function = _step_function_for(item, position) if axis == "step_function_version" else ""
    file_kind = OTHER_LAYOUT[kind] if axis == "other_harness_layout" else PLACED_KINDS[kind]
    variation_id = variation_identity(identity, axis, function, taken)
    text = body.decode("utf-8", "replace")
    # Search facets come from the item's purpose and name only: a word deep in the body (an example about an
    # image) must not become a claim about the item's input, as the first review showed on September 26, 2026.
    datatype, operation, use_case = facets_for(str(reference.get("purpose") or ""), identity)
    axis_brief = AXIS_BRIEF[axis].format(layout=LAYOUT_WORDS[file_kind], function=function)
    brief = (f"Write a variation of the served library item {identity} (a {kind.replace('_', ' ')} under the "
             f"{licence} licence) on the axis {axis}. {axis_brief} "
             + FORMAT_RULES.format(identity=identity, licence=licence, axis=axis,
                                   source_ref=reference.get("source_ref", "") or "the served item"))
    entry = entry_file(item)
    variation_of = {"record_type": VARIATION_RECORD_TYPE, "identity": identity, "digest": digest, "axis": axis,
                    "entry_path": entry.get("path", ""), "entry_digest": entry.get("digest", ""),
                    "kind": kind, "license": licence, "source_ref": reference.get("source_ref", ""),
                    "bundle": bundle_name, "bundle_items_digest": bundle_digest,
                    "tier": (item.get("approval") or {}).get("tier", ""),
                    **({"step_function": function} if function else {})}
    attribution = {"identity": identity, "digest": digest, "license": licence,
                   "source_ref": reference.get("source_ref", ""), "approval_ref": (item.get("approval") or {}).get("approval_ref", ""),
                   "cited_source": (item.get("attributes") or {}).get("cited_source", "")}
    if upstream:
        attribution["upstream"] = {key: upstream[key] for key in ("repository", "path", "immutable_revision", "origin_host")
                                   if key in upstream}
    if attribution_note:
        attribution["attribution_text"] = attribution_note
    origin = (f"a served library item, {identity}, under the {licence} licence, which allows copying; the idea "
              f"record carries its attribution")
    return {
        "record_type": IDEA_RECORD_TYPE, "id": variation_id, "file_kind": file_kind, "datatype": datatype,
        "operation": operation, "use_case": use_case, "lifecycle": "candidate",
        "applicability": {"occupation_code": "", "occupation_title": "", "task_reference": brief,
                          "facet_dimensions": list(FACET_DIMENSIONS), "facet": {},
                          "variation_of": variation_of, "seed_origin": origin, "seed_licence": licence,
                          "seed_attribution": attribution, "seed_excerpt": text[:EXCERPT_BOUND]},
        "method_signature": _sha256(f"{identity}|{digest}|{axis}|{function}".encode()),
        "brief": brief, "known_wrong": AXIS_KNOWN_WRONG[axis].format(function=function),
    }


def build_batch(ideas: list, bundle: Path, bundle_digest: str) -> dict:
    if not ideas:
        refuse("no_idea", "no served item was eligible")
    batch_digest = _sha256(json.dumps(ideas, sort_keys=True, separators=(",", ":")).encode())
    return {"record_type": BATCH_RECORD_TYPE,
            "matrix": {"record_type": "harness_idea_matrix/v1", "datatypes": len(DATATYPES), "operations": len(OPERATIONS),
                       "use_cases": len(USE_CASES), "facet_dimensions": list(FACET_DIMENSIONS)},
            "sources": [{"kind": SOURCE_KIND, "path": str(bundle / "items.jsonl"), "sha256": bundle_digest}],
            "ideas": ideas, "idea_count": len(ideas),
            "unique_method_signatures": len({idea["method_signature"] for idea in ideas}),
            "unique_ids": len({idea["id"] for idea in ideas}), "file_kinds": len(FILE_KINDS), "batch_sha256": batch_digest}


# -- the run --------------------------------------------------------------------------------------------------

class Run:
    """One run folder with its journal and stage markers."""

    def __init__(self, options):
        self.options = options
        self.name = options.run
        self.folder = Path(options.library) / "variations" / self.name
        self.folder.mkdir(parents=True, exist_ok=True)
        self.journal = self.folder / "journal.jsonl"
        self.ledger = Path(options.ledger)
        self.factory = Path(options.factory)
        self.oracle = Path(options.library) / "oracle"
        self.oracle.mkdir(parents=True, exist_ok=True)

    def note(self, stage: str, event: str, **extra) -> None:
        _append_jsonl(self.journal, {"record_type": JOURNAL_RECORD_TYPE, "at": _now(), "run": self.name,
                                     "stage": stage, "event": event, **extra})
        print(json.dumps({"stage": stage, "event": event, **extra}, sort_keys=True, default=str))

    def done(self, stage: str) -> bool:
        return (self.folder / f"{stage}.done").is_file()

    def finish(self, stage: str) -> None:
        (self.folder / f"{stage}.done").write_text(_now() + "\n", encoding="utf-8")
        self.note(stage, "done")

    def outage(self, stage: str, reason: str, **extra) -> None:
        self.note(stage, "outage", reason=reason, **extra)
        raise Outage(f"{stage}: {reason}")

    # -- select
    def select(self) -> None:
        if self.done("select"):
            return
        options = self.options
        licences = accepted_licences(Path(options.licence_script))
        bundle = newest_bundle(Path(options.bundle_root))
        items = read_bundle_items(bundle)
        bundle_digest = _sha256((bundle / "items.jsonl").read_bytes())
        done = ledger_digests(self.ledger)
        picked, skipped = select_items(items, done, options.count, licences)
        provenance = snapshot_provenance(Path(options.library) / "release-folders" / bundle.name)
        ideas, taken, rows = [], set(), []
        for position, item in enumerate(picked):
            axis = AXES[position % len(AXES)]
            body = body_of(bundle, entry_file(item)["digest"])
            upstream = (provenance.get(item["reference"]["identity"]) or {}).get("upstream")
            idea = idea_for(item, body, axis, bundle_name=bundle.name, bundle_digest=bundle_digest, position=position,
                            taken=taken, upstream=upstream, attribution_note=attribution_text(bundle, item))
            taken.add(idea["id"])
            ideas.append(idea)
            rows.append({"record_type": LEDGER_RECORD_TYPE, "at": _now(), "run": self.name, "bundle": bundle.name,
                         "source_identity": item["reference"]["identity"], "source_digest": item["reference"]["digest"],
                         "axis": axis, "variation_id": idea["id"], "stage": "idea_written"})
        selection = {"record_type": SELECTION_RECORD_TYPE, "run": self.name, "bundle": str(bundle),
                     "bundle_items_digest": bundle_digest, "items_in_bundle": len(items), "already_varied": len(done),
                     "requested": options.count, "picked": len(picked),
                     "skipped": dict(Counter(row["reason"] for row in skipped)),
                     "axes": dict(Counter(idea["applicability"]["variation_of"]["axis"] for idea in ideas)),
                     "file_kinds": dict(Counter(idea["file_kind"] for idea in ideas)),
                     "picked_items": [{"identity": idea["applicability"]["variation_of"]["identity"], "variation_id": idea["id"],
                                       "axis": idea["applicability"]["variation_of"]["axis"], "file_kind": idea["file_kind"]}
                                      for idea in ideas],
                     "accepted_licences": list(licences)}
        (self.folder / "selection.json").write_text(json.dumps(selection, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        if not ideas:
            self.note("select", "nothing_to_do", items_in_bundle=len(items), already_varied=len(done))
            self.finish("select")
            (self.folder / "nothing-to-do").write_text(_now() + "\n", encoding="utf-8")
            return
        batch = build_batch(ideas, bundle, bundle_digest)
        (self.folder / "ideas.json").write_text(json.dumps(batch, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        for row in rows:
            _append_jsonl(self.ledger, row)
        self.note("select", "ideas_written", ideas=len(ideas), bundle=bundle.name, skipped=selection["skipped"],
                  axes=selection["axes"])
        self.finish("select")

    def _ideas(self) -> dict:
        path = self.folder / "ideas.json"
        if not path.is_file():
            refuse("ideas_missing", "run the select stage first")
        return json.loads(path.read_text(encoding="utf-8"))

    def _nothing(self, stage: str) -> bool:
        if (self.folder / "nothing-to-do").is_file():
            self.note(stage, "skipped", reason="nothing_to_do")
            return True
        return False

    # -- generate
    def generate(self) -> None:
        if self.done("generate") or self._nothing("generate"):
            return
        from tools.opencode_generation_lanes import DECLARED_ENDPOINTS, DEFAULT_LANE_SPECS, OPENCODE_EXECUTABLE
        from tools import overnight_candidate_batch as batch_tool
        if not OPENCODE_EXECUTABLE.is_file():
            self.outage("generate", "program_missing", program=str(OPENCODE_EXECUTABLE))
        endpoint = urlsplit(DECLARED_ENDPOINTS["tactical"]["base_url"])
        try:
            with socket.create_connection((endpoint.hostname, endpoint.port or 443), timeout=15):
                pass
        except OSError as error:
            self.outage("generate", "endpoint_unreachable", endpoint=endpoint.netloc, error=type(error).__name__)
        batch = self._ideas()
        count = batch["idea_count"]
        ceiling = int(math.ceil(count * CEILING_FACTOR))
        specs = [spec for spec in DEFAULT_LANE_SPECS if spec["lane_id"] == LANE_ID]
        batch_directory = self.folder / "batch"
        batch_directory.mkdir(exist_ok=True)
        (self.folder / "generation.json").write_text(json.dumps(
            {"effective_from": _now(), "ideas": count, "max_calls": ceiling, "lane": LANE_ID,
             "lane_root": str(Path(self.options.lane_root))}, indent=1) + "\n", encoding="utf-8")
        self.note("generate", "started", ideas=count, max_calls=ceiling, lane=LANE_ID)
        status = batch_tool.start(batch_directory, self.folder / "ideas.json", specs, count, ceiling,
                                  Path(self.options.lane_root))
        self.note("generate", "finished", candidates=status["candidates"], failed=status["failed"],
                  calls_used=status["calls_used"], ceiling_reached=status["ceiling_reached"])
        if status["candidates"] == 0:
            self.outage("generate", "no_candidate_written", failed=status["failed"], calls_used=status["calls_used"])
        self.finish("generate")

    # -- attribute
    def _factory_git(self, *arguments: str) -> str:
        finished = subprocess.run(["git", "-C", str(self.factory), "-c", "user.name=oracle-variations",
                                   "-c", "user.email=oracle-variations@baltor.invalid", *arguments],
                                  capture_output=True, text=True, timeout=120)
        if finished.returncode != 0:
            refuse("factory_git_failed", f"git {arguments[0]}: {finished.stderr.strip()[:300]}")
        return finished.stdout.strip()

    def _ensure_factory(self) -> None:
        """The private factory repository: the public LICENSE bytes at its root, committed once."""
        if (self.factory / ".git").is_dir():
            return
        self.factory.mkdir(parents=True, exist_ok=True)
        self._factory_git("init", "-q")
        shutil.copyfile(REPOSITORY / "LICENSE", self.factory / "LICENSE")
        (self.factory / "README.md").write_text(
            "# Variation factory\n\nPrivate: the idea records here quote served library bodies. Written by "
            "tools/generate_item_variations.py of the Loop Engine repository; never published.\n", encoding="utf-8")
        self._factory_git("add", "LICENSE", "README.md")
        self._factory_git("commit", "-q", "-m", "Start the private variation factory with the MIT licence")

    def attribute(self) -> None:
        if self.done("attribute") or self._nothing("attribute"):
            return
        from tools import native_proposals_from_overnight_candidates as adapter
        self._ensure_factory()
        generation = json.loads((self.folder / "generation.json").read_text(encoding="utf-8"))
        output = self.factory / "runs" / self.name / "attribution"
        if output.exists():
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            summary = adapter.attribute(self.folder / "batch",
                                        [f"{self.folder / 'ideas.json'}@{generation['effective_from']}@{generation['ideas']}"],
                                        {LANE_ID: LANE_FAMILY}, output)
        except adapter.ConversionError as error:
            refuse("attribution_refused", str(error))
        self._factory_git("add", "-A", str(output.relative_to(self.factory)))
        self._factory_git("commit", "-q", "-m", f"Attribute the variation run {self.name}")
        revision = self._factory_git("rev-parse", "HEAD")
        self.note("attribute", "committed", candidates=summary["candidates"], excluded=summary["excluded"],
                  factory_revision=revision)
        if summary["candidates"] == 0:
            self.outage("attribute", "no_candidate_attributed")
        self.finish("attribute")

    # -- prepare
    def prepare(self) -> None:
        if self.done("prepare") or self._nothing("prepare"):
            return
        from tools import native_proposals_from_overnight_candidates as adapter
        from tools import prepare_harness_candidates as factory
        attribution = self.factory / "runs" / self.name / "attribution" / "attribution.json"
        proposals = self.folder / "proposals.json"
        try:
            summary = adapter.proposals(self.factory, attribution, self.folder / "batch", proposals)
        except adapter.ConversionError as error:
            if str(error) == "no_candidate_converted":
                self.outage("prepare", "no_candidate_converted")
            refuse("proposals_refused", str(error))
        candidates = self.folder / "candidates"
        if candidates.exists():
            shutil.rmtree(candidates)
        try:
            report = factory.prepare(factory.PreparationRequest(self.factory, proposals, candidates, True))
        except factory.PreparationError as error:
            refuse("preparation_refused", str(error))
        self.note("prepare", "prepared", converted=summary["converted"], left_out=summary["left_out"],
                  candidates=report["candidates"])
        self.finish("prepare")

    # -- prechecks
    def _campaign(self, *arguments: str) -> dict:
        argv = [sys.executable, str(CAMPAIGN), *arguments, "--repository", str(self.factory)]
        environment = {**os.environ, "PYTHONPATH": f"{REPOSITORY / 'src'}:{REPOSITORY / 'tools'}"}
        finished = subprocess.run(argv, capture_output=True, text=True, cwd=str(REPOSITORY), env=environment,
                                  timeout=self.options.review_timeout)
        (self.folder / f"{arguments[0]}.log").write_text(finished.stdout + finished.stderr, encoding="utf-8")
        if finished.returncode != 0:
            refuse(f"{arguments[0]}_failed", (finished.stderr or finished.stdout).strip()[-400:])
        return json.loads(finished.stdout.strip().splitlines()[-1])

    def prechecks(self) -> None:
        if self.done("prechecks") or self._nothing("prechecks"):
            return
        summary = self._campaign("prechecks", "--catalogue", str(self.folder / "candidates"),
                                 "--output", str(self.folder / "prechecks.json"),
                                 "--scratch-ledger", str(self.folder / "prechecks-scratch.jsonl"))
        rows = json.loads((self.folder / "prechecks.json").read_text(encoding="utf-8"))["rows"]
        passed = [row["identity"] for row in rows if not row["refused"]][:REVIEW_ITEMS_PER_RUN]
        (self.folder / "identities.txt").write_text("".join(identity + "\n" for identity in passed), encoding="utf-8")
        self.note("prechecks", "checked", items=summary["items"], refused=summary["refused"], to_review=len(passed))
        if not passed:
            self.outage("prechecks", "nothing_passed_prechecks", refused=summary["refused"])
        self.finish("prechecks")

    # -- review
    def _claude_calls_used(self) -> int:
        path = Path(self.options.claude_counter)
        if not path.is_file():
            self.outage("review", "counter_missing", counter=str(path))
        return sum(int(row.get("calls", 0)) for row in _read_jsonl(path))

    def review(self) -> None:
        if self.done("review") or self._nothing("review"):
            return
        if shutil.which("claude") is None:
            self.outage("review", "program_missing", program="claude")
        identities = [line.strip() for line in (self.folder / "identities.txt").read_text(encoding="utf-8").splitlines()
                      if line.strip()]
        calls = int(math.ceil(len(identities) / REVIEW_BATCH))
        used = self._claude_calls_used()
        if used + calls > CLAUDE_REVIEW_CALL_CAP:
            self.outage("review", "review_call_cap_reached", used=used, planned=calls, cap=CLAUDE_REVIEW_CALL_CAP)
        panel = json.loads(PANEL.read_text(encoding="utf-8"))
        exclusions = []
        for installation in panel["installations"]:
            if installation["installation_id"] != REVIEWER:
                exclusions += ["--exclude-installation", f"{installation['installation_id']}=not_the_reviewer_of_this_run"]
        summary = self._campaign("review", "--catalogue", str(self.folder / "candidates"),
                                 "--output", str(self.folder / "review.json"), "--ledger", str(self.folder / "ledger.jsonl"),
                                 "--reviewer", REVIEWER, "--calls-left", str(calls + 1), "--batch-size", str(REVIEW_BATCH),
                                 "--authorize-model-calls", "--identities-file", str(self.folder / "identities.txt"),
                                 "--call-ceiling", str(calls + 1), *exclusions)
        _append_jsonl(Path(self.options.claude_counter), {"at": _now(), "run": self.name, "calls": summary["calls"],
                                                          "items": summary["items"]})
        self.note("review", "reviewed", **summary)
        if summary["calls"] == 0 or summary["items"] == 0:
            self.outage("review", "no_review_answered", stop_reason=summary.get("stop_reason", ""))
        self.finish("review")

    # -- write
    def write(self) -> None:
        if self.done("write") or self._nothing("write"):
            return
        reviewed = self.folder / "reviewed"
        if reviewed.exists():
            shutil.rmtree(reviewed)
        argv = [sys.executable, str(HERE / "write_reviewed_catalogue.py"), "--repository", str(self.factory),
                "--catalogue", str(self.folder / "candidates"), "--ledger", str(self.folder / "ledger.jsonl"),
                "--reviewer", REVIEWER, "--tier", "community", "--output", str(reviewed),
                "--recorded-at", self.options.recorded_at, "--identities-file", str(self.folder / "identities.txt")]
        environment = {**os.environ, "PYTHONPATH": f"{REPOSITORY / 'src'}:{REPOSITORY / 'tools'}"}
        finished = subprocess.run(argv, capture_output=True, text=True, cwd=str(REPOSITORY), env=environment, timeout=600)
        (self.folder / "write.log").write_text(finished.stdout + finished.stderr, encoding="utf-8")
        if finished.returncode != 0:
            refuse("write_failed", (finished.stdout or finished.stderr).strip()[-400:])
        summary = json.loads(finished.stdout.strip().splitlines()[-1])
        folder_list = Path(self.options.folder_list)
        listed = folder_list.read_text(encoding="utf-8").splitlines() if folder_list.is_file() else []
        if str(reviewed) not in listed:
            with folder_list.open("a", encoding="utf-8") as stream:
                stream.write(str(reviewed) + "\n")
        review = json.loads((reviewed / "reviews.json").read_text(encoding="utf-8"))
        ideas = {idea["id"].replace("-", "_"): idea for idea in self._ideas()["ideas"]}
        for row in review["rows"]:
            idea = ideas.get(row["identity"], {})
            source = (idea.get("applicability") or {}).get("variation_of", {})
            _append_jsonl(self.ledger, {"record_type": LEDGER_RECORD_TYPE, "at": _now(), "run": self.name,
                                        "source_identity": source.get("identity", ""), "source_digest": source.get("digest", ""),
                                        "axis": source.get("axis", ""), "variation_id": row["identity"], "stage": "reviewed",
                                        "outcome": row["outcome"], "reviewed_folder": str(reviewed)})
        self.note("write", "written", approved=summary["approved"], rejected=summary["rejected"],
                  left_out=summary["left_out"], reviewed_folder=str(reviewed))
        self.finish("write")


STAGES = ("select", "generate", "attribute", "prepare", "prechecks", "review", "write")
#: The stages that call a model (generation on the Tactical lane, the one screening review). They run only with
#: --authorize-model-calls, so a run without that explicit authority stops before any call.
MODEL_STAGES = ("generate", "review")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="the run name, for example 2026-09-26T0550Z")
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="served items to vary this run")
    parser.add_argument("--bundle-root", default=str(DEFAULT_BUNDLE_ROOT))
    parser.add_argument("--library", default=str(DEFAULT_LIBRARY))
    parser.add_argument("--ledger", default=str(DEFAULT_LIBRARY / "oracle" / "variations-ledger.jsonl"))
    parser.add_argument("--factory", default=str(DEFAULT_LIBRARY / "oracle" / "factory"))
    parser.add_argument("--claude-counter", default=str(DEFAULT_LIBRARY / "oracle" / "claude-review-calls.jsonl"))
    parser.add_argument("--folder-list", default=str(DEFAULT_LIBRARY / "release-folders" / "reviewed-folders.txt"))
    parser.add_argument("--lane-root", default=str(DEFAULT_LANE_ROOT))
    parser.add_argument("--licence-script", default=str(DEFAULT_LICENCE_SCRIPT))
    parser.add_argument("--recorded-at", default=time.strftime("%Y-%m-%d", time.gmtime()))
    parser.add_argument("--review-timeout", type=float, default=3600.0)
    parser.add_argument("--authorize-model-calls", action="store_true",
                        help="the explicit authority for the generation and review stages, which call models")
    options = parser.parse_args(argv)
    stages = STAGES if options.stage == "all" else (options.stage,)
    if any(stage in MODEL_STAGES for stage in stages) and not options.authorize_model_calls:
        print(json.dumps({"refused": True, "code": "model_calls_not_authorized",
                          "stages": [stage for stage in stages if stage in MODEL_STAGES]}))
        return 2
    if not os.environ.get("TMPDIR"):
        scratch = Path.home() / ".le-ci-tmp" / "oracle-variations"
        scratch.mkdir(parents=True, exist_ok=True)
        os.environ["TMPDIR"] = str(scratch)
        tempfile.tempdir = str(scratch)
    run = Run(options)
    try:
        for stage in stages:
            getattr(run, stage)()
    except Outage as outage:
        print(json.dumps({"outage": str(outage)}))
        return OUTAGE_EXIT
    except VariationError as error:
        run.note(options.stage, "failed", error=str(error))
        print(json.dumps({"refused": True, "code": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
