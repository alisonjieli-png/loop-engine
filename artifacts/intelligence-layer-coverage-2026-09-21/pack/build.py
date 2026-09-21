"""Measure the coverage pack bodies and write its three derived records.

The files in ``bodies`` are the source of truth for the text, the digest and
the size of every item. The drafts below are the source of truth for every
other field. This tool measures each body through the engine's own
``item_from_body`` function, so no caller invents a digest, and it rewrites
only ``specifications.json``, ``items.json`` and ``source-tree.json`` inside
its own folder.

``source-tree.json`` is the git object name of every cited repository path at
``SOURCE_REVISION``, read with ``git ls-tree``. The check resolves a citation
there rather than asking whether the path exists in whichever tree it happens
to run in, which would pass a file added after that revision and fail a file
moved away from it. Without git, or without that revision in the clone, this
tool reports the listing as not derived and leaves the held one untouched. It
never guesses a citation into the pack.

It approves nothing, publishes nothing and grants nothing. Every item stays a
candidate.

Report what is stale without writing, then write with explicit authority:

    PYTHONPATH=src python \
      artifacts/intelligence-layer-coverage-2026-09-21/pack/build.py
    PYTHONPATH=src python \
      artifacts/intelligence-layer-coverage-2026-09-21/pack/build.py --write
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import subprocess

from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
from loop_engine.core.intelligence_tagging import TagSet

#: The revision every source reference in this pack is bound to.
SOURCE_REVISION = "6a489b2eff78d1e7251d65e143edbd89f7250c4e"
#: The version of every item in this pack. A changed body gets a new version.
ITEM_VERSION = "1.0.0"
#: The bodies whose text changed after the first build, and the version each
#: one carries now. On 2026-09-21 the ten User Feedback bodies were given a
#: Timing value from ``user_feedback_intelligence.TIMINGS`` in place of the
#: free prose that was there before. The fourteen Runtime History bodies did
#: not change, so they keep 1.0.0 rather than being bumped for someone else's
#: edit.
ITEM_VERSIONS: dict = {
    "recorded_direction_build_general_mechanisms": "1.1.0",
    "recorded_direction_decide_what_you_can_decide": "1.1.0",
    "recorded_direction_do_not_infer_behaviour_from_names_or_prose": "1.1.0",
    "recorded_direction_do_not_weaken_a_failing_check": "1.1.0",
    "recorded_direction_keep_failures_as_visible_as_successes": "1.1.0",
    "recorded_direction_marketing_language_is_not_a_factual_claim": "1.1.0",
    "recorded_direction_never_end_on_a_fixed_attempt_count": "1.1.0",
    "recorded_direction_offered_fetched_loaded_used_and_verified_are_separate": "1.1.0",
    "recorded_direction_state_observed_inferred_assumed_and_missing_separately": "1.1.0",
    "recorded_direction_write_public_pages_in_plain_english": "1.1.0",
}
SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v1"
ITEMS_RECORD_TYPE = "layer_coverage_candidate_items/v1"
SOURCE_TREE_RECORD_TYPE = "layer_coverage_source_tree/v1"
SPECIFICATIONS_FILE = "specifications.json"
ITEMS_FILE = "items.json"
SOURCE_TREE_FILE = "source-tree.json"
BODIES_FOLDER = "bodies"
BODY_SUFFIX = ".md"
TEMPORARY_SUFFIX = ".build"
#: A git object name: forty lowercase hexadecimal characters.
OBJECT_NAME_LENGTH = 40
#: These bodies are prose. None of them executes, reads a file or reaches a network.
NO_EFFECTS: tuple[str, ...] = ()
#: The repository is MIT licensed and these bodies were written from its own records.
LICENSE_NAME = "MIT"
LICENSE_STATE = "declared"
AUTHORING = "assistant_authored_from_repository_sources"


class CoveragePackError(ValueError):
    """The pack files are unsupported, inconsistent or unsafe to rewrite."""


@dataclass(frozen=True)
class PackItem:
    """One candidate item: its harness facts, its review facts and its body."""

    identity: str
    layer: str
    family: str
    title: str
    purpose: str
    source_ref: str
    tag_words: tuple[str, ...]
    sources: tuple[str, ...]
    provenance_note: str = ""
    kind: str = "instruction_file"
    styles: tuple[str, ...] = ()
    extra_tags: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.layer not in LAYER_SOURCE:
            raise CoveragePackError(
                f"{self.layer!r} is not one of {tuple(LAYER_SOURCE)}")
        if not self.sources:
            raise CoveragePackError(
                f"item {self.identity!r} must cite at least one repository source")

    @property
    def body_name(self) -> str:
        return self.identity + BODY_SUFFIX

    def draft(self) -> HarnessIntelligenceDraft:
        tags = {"lifecycle": ("candidate",), "language": ("en",),
                "data_sensitivity": ("public",), **self.extra_tags}
        return HarnessIntelligenceDraft(
            self.identity, self.kind, self.purpose, LAYER_SOURCE[self.layer],
            self.source_ref, LICENSE_NAME, NO_EFFECTS, self.styles,
            tags=TagSet(tags))


#: The staging vocabulary on the left, the harness source layer on the right.
LAYER_SOURCE = {
    "runtime_history_solution": "runtime_history_solution_intelligence",
    "user_feedback": "user_feedback_intelligence",
}

AUDIT = "artifacts/architecture-audit-2026-09-19/"

ITEMS: tuple[PackItem, ...] = (
    PackItem(
        "classify_a_failed_check_before_changing_the_work",
        "runtime_history_solution", "decision",
        "Classify a failed check before changing the work",
        "Deciding whether the work is wrong, the check is wrong, or the build "
        "environment is wrong: a recorded startup probe failure that was "
        "classified as a defect in the check rather than in the service, with the "
        "evidence that supported the classification and the control that was kept",
        AUDIT + "fly-service-container-attempt-1.json@" + SOURCE_REVISION,
        ("failure classification", "health check", "deployment", "probe", "repair"),
        (AUDIT + "fly-service-container-attempt-1.json",
         AUDIT + "fly-service-container-attempt-3.json"),
        "Recorded operator evidence, record type fly_service_container_failure_note/v1"),
    PackItem(
        "a_client_reader_that_assumes_one_response_encoding",
        "runtime_history_solution", "failure_remedy",
        "A client reader that assumes one response encoding",
        "A recorded browser check that never completed because its fetch assumed "
        "one complete document while the transport can answer with server sent "
        "events, and the repair that handles bounded frames and request identity",
        AUDIT + "guided-connection-browser-1.json@" + SOURCE_REVISION,
        ("protocol", "event stream", "browser", "client", "timeout"),
        (AUDIT + "guided-connection-browser-1.json",
         AUDIT + "guided-connection-browser-3.json",
         "src/loop_engine/core/service_runtime/web_assets/service.js"),
        "Local browser evidence with no external provider calls"),
    PackItem(
        "a_test_producer_that_returns_booleans_hides_which_check_ran",
        "runtime_history_solution", "failure_remedy",
        "A test producer that returns booleans hides which check ran",
        "A recorded repair where a self-test producer was changed to return "
        "identified records instead of a mapping of names to booleans, with the "
        "mutation control showing the collector still rejects the old shape",
        AUDIT + "runtime-regression-repairs.md@" + SOURCE_REVISION,
        ("test collector", "self test", "mutation control", "evidence", "repair"),
        (AUDIT + "runtime-regression-repairs.md",),
        "Focused repair record dated 2026-09-19"),
    PackItem(
        "build_a_test_fixture_from_the_real_typed_object",
        "runtime_history_solution", "failure_remedy",
        "Build a test fixture from the real typed object",
        "A recorded fixture drift where a hand-built stand-in lacked a newly "
        "required field, and the repair that built the fixture from typed intake "
        "instead of adding a production default",
        AUDIT + "runtime-regression-repairs.md@" + SOURCE_REVISION,
        ("test fixture", "typed request", "drift", "default value", "repair"),
        (AUDIT + "runtime-regression-repairs.md",),
        "Focused repair record dated 2026-09-19"),
    PackItem(
        "two_scanners_that_disagree_may_be_measuring_two_populations",
        "runtime_history_solution", "decision",
        "Two scanners that disagree may be measuring two populations",
        "A recorded investigation where two scanners disagreed about the same rule, "
        "one reporting zero findings and the other eighteen, and both answers were "
        "correct for different populations, so no waiver was taken",
        AUDIT + "runtime-regression-repairs.md@" + SOURCE_REVISION,
        ("conformance", "scope", "waiver", "test pollution", "population"),
        (AUDIT + "runtime-regression-repairs.md",),
        "Focused repair record dated 2026-09-19"),
    PackItem(
        "a_short_candidate_pool_can_hide_an_eligible_match",
        "runtime_history_solution", "repair",
        "A short candidate pool can hide an eligible match",
        "A recorded retrieval repair where filtering a small top-ranked pool "
        "reported an empty result while an eligible item sat further down the "
        "ranking, with the correctness cost stated rather than hidden",
        AUDIT + "intelligence-access-repairs.md@" + SOURCE_REVISION,
        ("retrieval", "filter", "ranking", "empty result", "tradeoff"),
        (AUDIT + "intelligence-access-repairs.md",
         "src/loop_engine/core/retrieval.py"),
        "Implemented repair and scoped verification dated 2026-09-19"),
    PackItem(
        "an_unavailable_backend_must_not_look_like_an_empty_result",
        "runtime_history_solution", "failure_remedy",
        "An unavailable backend must not look like an empty result",
        "A recorded repair where retrieval backends returned an empty list for an "
        "unreachable store, making absence and unavailability the same value to "
        "every caller, and the typed error that separated them",
        AUDIT + "intelligence-access-repairs.md@" + SOURCE_REVISION,
        ("retrieval", "unavailable", "empty result", "typed error", "silent failure"),
        (AUDIT + "intelligence-access-repairs.md",
         "src/loop_engine/core/retrieval.py"),
        "Implemented repair and scoped verification dated 2026-09-19"),
    PackItem(
        "a_fixture_that_asks_for_less_than_it_requires",
        "runtime_history_solution", "decision",
        "A fixture that asks for less than it requires",
        "A recorded test correction where a fixture passed only because a result "
        "limit was applied per layer, and the new check that still rejects the "
        "multiplied limit",
        AUDIT + "intelligence-access-repairs.md@" + SOURCE_REVISION,
        ("test correction", "result limit", "known wrong case", "regression", "search"),
        (AUDIT + "intelligence-access-repairs.md",),
        "Implemented repair and scoped verification dated 2026-09-19"),
    PackItem(
        "a_write_is_confirmed_by_an_acknowledgment_and_a_readback",
        "runtime_history_solution", "repair",
        "A write is confirmed by an acknowledgment and a readback",
        "How to know whether a row really committed and was really saved: a "
        "recorded storage repair that keeps written, refused and unknown apart, "
        "and reports an unconfirmed write as unknown rather than as a success or "
        "as an invented stale version",
        AUDIT + "storage-write-repairs.md@" + SOURCE_REVISION,
        ("storage", "acknowledgment", "readback", "unknown outcome", "versioning"),
        (AUDIT + "storage-write-repairs.md",),
        "Implemented repair and scoped verification dated 2026-09-19"),
    PackItem(
        "say_plainly_when_two_writes_are_not_one_transaction",
        "runtime_history_solution", "decision",
        "Say plainly when two writes are not one transaction",
        "A recorded decision to write down that a history write and a current "
        "write are deliberately not one transaction, and to name the exact state "
        "that can remain after a partial failure",
        AUDIT + "storage-write-repairs.md@" + SOURCE_REVISION,
        ("transaction", "revision history", "partial failure", "naming", "storage"),
        (AUDIT + "storage-write-repairs.md",),
        "Implemented repair and scoped verification dated 2026-09-19"),
    PackItem(
        "a_truthy_value_is_not_a_granted_permission",
        "runtime_history_solution", "repair",
        "A truthy value is not a granted permission",
        "A recorded repair that made operation capabilities require the boolean "
        "value true across three store adapters, so a truthy string or number "
        "grants nothing",
        AUDIT + "storage-write-repairs.md@" + SOURCE_REVISION,
        ("permission", "capability", "type confusion", "adapters", "guard"),
        (AUDIT + "storage-write-repairs.md",),
        "Implemented repair and scoped verification dated 2026-09-19"),
    PackItem(
        "run_the_restore_before_you_call_the_backup_a_backup",
        "runtime_history_solution", "failure_remedy",
        "Run the restore before you call the backup a backup",
        "Proving that a saved backup copy can be restored: two recorded recovery "
        "exercises minutes apart, the first failing its restore check and the "
        "second passing with its checks named, kept together with the limits the "
        "records state",
        AUDIT + "pilot-backup-restore-1.json@" + SOURCE_REVISION,
        ("backup", "restore", "recovery", "failed attempt", "limits"),
        (AUDIT + "pilot-backup-restore-1.json",
         AUDIT + "pilot-backup-restore-2.json"),
        "Recorded operator evidence, record type pilot_backup_restore_check/v1"),
    PackItem(
        "read_a_latency_report_by_its_population_and_its_limits",
        "runtime_history_solution", "measurement",
        "Read a latency report by its population and its limits",
        "A recorded response time report whose own fields state the sample count, "
        "the concurrency, the retry policy and the percentile method, and whose "
        "own limits say what it does not establish",
        AUDIT + "service-latency-1.json@" + SOURCE_REVISION,
        ("latency", "measurement", "percentile", "population", "limits"),
        (AUDIT + "service-latency-1.json",),
        "Recorded operator evidence, record type service_latency_report/v1"),
    PackItem(
        "paying_for_something_is_not_permission_to_see_it",
        "runtime_history_solution", "repair",
        "Paying for something is not permission to see it",
        "A recorded access repair that separates payment entitlement from the "
        "installed tenant grant, and makes an unapproved item absent from counts, "
        "listings, withheld identities, manifests and bodies alike",
        AUDIT + "provisioning-access-repairs.md@" + SOURCE_REVISION,
        ("authority", "entitlement", "disclosure", "tenant grant", "access control"),
        (AUDIT + "provisioning-access-repairs.md",),
        "Local component repair record dated 2026-09-19"),
    PackItem(
        "recorded_direction_do_not_weaken_a_failing_check",
        "user_feedback", "owner_constraint",
        "Recorded direction: do not weaken a failing check",
        "Recorded guidance that a failing check is classified before anything is "
        "edited, and that a revised check must still reject a known-wrong answer",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "verification", "known wrong case", "classification"),
        ("AGENTS.md",
         "docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md"),
        "Guidance recorded by the repository owner on 2026-09-14"),
    PackItem(
        "recorded_direction_build_general_mechanisms",
        "user_feedback", "owner_constraint",
        "Recorded direction: build general mechanisms",
        "Recorded guidance not to add control flow, prompts or checks written for "
        "one task, one dataset or one benchmark, such as a hardcoded column name "
        "for one customer",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "generality", "control flow", "benchmark"),
        ("AGENTS.md",),
        "Guidance recorded by the repository owner on 2026-09-14"),
    PackItem(
        "recorded_direction_never_end_on_a_fixed_attempt_count",
        "user_feedback", "owner_instruction",
        "Recorded direction: never end on a fixed attempt count",
        "Recorded guidance for when you have tried several times and the same "
        "error keeps coming back: change the approach rather than repeating the "
        "attempt, and name which of five reasons ended the work",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "persistence", "retry", "stopping condition"),
        ("AGENTS.md",),
        "Guidance recorded by the repository owner on 2026-09-14"),
    PackItem(
        "recorded_direction_decide_what_you_can_decide",
        "user_feedback", "owner_priority",
        "Recorded direction: decide what you can decide",
        "Recorded guidance to decide and record the reason rather than returning "
        "a question, with the named exceptions that must still be asked",
        "CLAUDE.md@" + SOURCE_REVISION,
        ("owner direction", "decision", "escalation", "research"),
        ("CLAUDE.md",),
        "Guidance recorded by the repository owner on 2026-09-20 in the evening"),
    PackItem(
        "recorded_direction_marketing_language_is_not_a_factual_claim",
        "user_feedback", "owner_correction",
        "Recorded direction: marketing language is not a factual claim",
        "Recorded guidance for a landing page or any public copy, separating free "
        "evaluative language from the checkable facts that need evidence every "
        "time, such as a saving nobody measured, with the test to apply",
        "docs/guides/product-style-guide.md@" + SOURCE_REVISION,
        ("owner direction", "public writing", "claims", "evidence"),
        ("docs/guides/product-style-guide.md",),
        "Guidance recorded by the repository owner on 2026-09-21"),
    PackItem(
        "recorded_direction_keep_failures_as_visible_as_successes",
        "user_feedback", "owner_constraint",
        "Recorded direction: keep failures as visible as successes",
        "Recorded guidance to save every report under a new name and to keep "
        "failed attempts and exclusions beside the result with equal prominence",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "evidence", "failed attempt", "reporting"),
        ("AGENTS.md",),
        "Guidance recorded by the repository owner on 2026-09-14"),
    PackItem(
        "recorded_direction_offered_fetched_loaded_used_and_verified_are_separate",
        "user_feedback", "owner_constraint",
        "Recorded direction: offered, fetched, loaded, used and verified are separate",
        "Recorded guidance that five facts about a piece of material are separate: "
        "an item that was downloaded is not an item a model read or used, and a "
        "count of passing checks is not a working customer journey",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "claims", "customer journey", "verification"),
        ("AGENTS.md",),
        "Guidance recorded by the repository owner on 2026-09-20"),
    PackItem(
        "recorded_direction_do_not_infer_behaviour_from_names_or_prose",
        "user_feedback", "owner_constraint",
        "Recorded direction: do not infer behaviour from names or prose",
        "Recorded guidance that permissions, contracts, routing, budgets, "
        "compatibility and lifecycle come from structured typed fields and never "
        "from prose, tags, labels, filenames, folder names, examples or comments",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "typed fields", "authority", "naming"),
        ("AGENTS.md", "CLAUDE.md"),
        "Guidance recorded by the repository owner on 2026-09-19"),
    PackItem(
        "recorded_direction_state_observed_inferred_assumed_and_missing_separately",
        "user_feedback", "owner_instruction",
        "Recorded direction: state observed, inferred, assumed and missing separately",
        "How to label the parts of a result you did not observe yourself: "
        "recorded guidance to sort every claim into observed, inferred, assumed, "
        "missing or disputed before writing it",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "evidence", "reporting", "uncertainty"),
        ("AGENTS.md", "ASTRA.md"),
        "Guidance recorded by the repository owner on 2026-09-14"),
    PackItem(
        "recorded_direction_write_public_pages_in_plain_english",
        "user_feedback", "owner_instruction",
        "Recorded direction: write public pages in plain English",
        "Recorded guidance for public writing: plain English for a reader using "
        "English as a second language, highest level first, ordinary names, and "
        "the exact runtime terms kept in the technical documents",
        "AGENTS.md@" + SOURCE_REVISION,
        ("owner direction", "public writing", "plain english", "naming"),
        ("AGENTS.md", "docs/guides/product-style-guide.md"),
        "Guidance recorded by the repository owner on 2026-09-19"),
)


def _regular_file(folder: Path, name: str) -> Path:
    path = folder / name
    if path.is_symlink() or not path.is_file() or path.resolve().parent != folder:
        raise CoveragePackError(f"{name} must be a regular file inside the pack folder")
    return path


def read_bodies(folder: Path) -> dict:
    """Every body by identity, refusing a link, a stray file or a missing one."""
    bodies_folder = folder / BODIES_FOLDER
    if bodies_folder.is_symlink() or not bodies_folder.is_dir():
        raise CoveragePackError(f"{BODIES_FOLDER} must be a directory inside the pack folder")
    held = sorted(path.name for path in bodies_folder.iterdir())
    wanted = sorted(item.body_name for item in ITEMS)
    if held != wanted:
        raise CoveragePackError(
            f"{BODIES_FOLDER} holds {held} but the drafts name {wanted}")
    bodies = {}
    for item in ITEMS:
        path = _regular_file(bodies_folder, item.body_name)
        bodies[item.identity] = path.read_bytes().decode("utf-8")
    return bodies


def cited_sources() -> tuple:
    """Every repository path the pack cites, once each, in a stable order."""
    return tuple(sorted({source for item in ITEMS for source in item.sources}))


class SourceTreeUnavailable(CoveragePackError):
    """The recorded revision could not be read out of this repository."""


def source_tree_from_git(root: Path) -> dict:
    """The object name of every cited path, read out of the recorded revision.

    This is what binds a citation to ``SOURCE_REVISION`` rather than to
    whatever the working tree happens to hold today. A path that was added
    after the revision, or moved away from it, is absent here and stays absent.
    """
    wanted = cited_sources()
    try:
        finished = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "-z", SOURCE_REVISION,
             "--", *wanted],
            capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise SourceTreeUnavailable(f"git could not be run: {error}") from error
    if finished.returncode != 0:
        raise SourceTreeUnavailable(
            f"git ls-tree {SOURCE_REVISION} failed with {finished.returncode}")
    found = {}
    for entry in finished.stdout.decode("utf-8").split("\0"):
        if not entry:
            continue
        facts, _, path = entry.partition("\t")
        parts = facts.split()
        if len(parts) == 3 and parts[1] == "blob":
            found[path] = parts[2]
    return found


def derive_source_tree(root: Path) -> dict:
    """The recorded listing, refusing to write a partial or malformed one."""
    found = source_tree_from_git(root)
    missing = [path for path in cited_sources() if path not in found]
    if missing:
        raise SourceTreeUnavailable(
            f"{len(missing)} cited path(s) are not in {SOURCE_REVISION}: {missing}")
    bad = sorted(path for path, name in found.items()
                 if len(name) != OBJECT_NAME_LENGTH
                 or any(character not in "0123456789abcdef" for character in name))
    if bad:
        raise SourceTreeUnavailable(f"git returned unreadable object names for {bad}")
    return {"record_type": SOURCE_TREE_RECORD_TYPE,
            "source_revision": SOURCE_REVISION,
            "note": "The object name of every cited path at that revision, read "
                    "with git ls-tree. The check resolves a citation here, so it "
                    "is bound to the revision and not to the working tree.",
            "sources": {path: found[path] for path in cited_sources()}}


def derive(bodies: dict) -> tuple[dict, dict]:
    """The two derived records, measured from the bodies and the drafts."""
    specifications, items = [], []
    for item in ITEMS:
        body = bodies[item.identity]
        measured = item_from_body(item.draft(), body)
        specifications.append({
            "id": item.identity, "layer": item.layer, "family": item.family,
            "title": item.title, "tags": list(item.tag_words), "text": body,
            "sources": list(item.sources)})
        items.append({
            "reference": measured.reference(), "body_path":
                BODIES_FOLDER + "/" + item.body_name,
            "item_version": ITEM_VERSIONS.get(item.identity, ITEM_VERSION),
            "lifecycle": "candidate",
            "license_state": LICENSE_STATE,
            "approval": {"approved": False, "approved_by": "", "approval_ref": ""},
            "provenance": {"authoring": AUTHORING,
                           "source_revision": SOURCE_REVISION,
                           "note": item.provenance_note,
                           "repository_sources": list(item.sources)}})
    return ({"record_type": SPECIFICATIONS_RECORD_TYPE,
             "specifications": specifications},
            {"record_type": ITEMS_RECORD_TYPE, "source_revision": SOURCE_REVISION,
             "publication": "not_published", "items": items})


def stale_identities(folder: Path, bodies: dict) -> list[str]:
    """The identities whose stored derived fields differ from their body."""
    new_specifications, new_items = derive(bodies)
    held_specifications = _load(folder, SPECIFICATIONS_FILE, SPECIFICATIONS_RECORD_TYPE)
    held_items = _load(folder, ITEMS_FILE, ITEMS_RECORD_TYPE)
    stale = []
    for index, item in enumerate(ITEMS):
        held_row = _row(held_specifications.get("specifications"), index)
        held_item = _row(held_items.get("items"), index)
        if (held_row != new_specifications["specifications"][index]
                or held_item != new_items["items"][index]):
            stale.append(item.identity)
    if (held_items.get("source_revision") != SOURCE_REVISION
            or held_items.get("publication") != "not_published"):
        stale.append("<pack header>")
    return stale


def _row(rows, index):
    return rows[index] if isinstance(rows, list) and index < len(rows) else None


def _load(folder: Path, name: str, record_type: str) -> dict:
    path = folder / name
    if not path.is_file():
        return {}
    try:
        held = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return held if isinstance(held, dict) and held.get("record_type") == record_type else {}


def _prepare(path: Path, value: dict, created: list) -> Path:
    """Write beside the record. Exclusive creation never follows a planted link."""
    temporary = path.with_name(path.name + TEMPORARY_SUFFIX)
    try:
        stream = temporary.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise CoveragePackError(
            f"{temporary.name} is left from an interrupted write; check that "
            f"{path.name} is intact, remove {temporary.name} and run again") from error
    created.append(temporary)
    with stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return temporary


def _replace_both(replacements: list) -> None:
    """Prepare both files before replacing either; remove what this run created on failure."""
    created: list = []
    try:
        prepared = [(_prepare(path, value, created), path) for path, value in replacements]
        for temporary, path in prepared:
            os.replace(temporary, path)
    except OSError as error:
        raise CoveragePackError(
            f"the write failed: {error}; run the tool again to see what is stale") from error
    finally:
        for temporary in created:
            temporary.unlink(missing_ok=True)


def build(folder: Path, *, write: bool = False) -> dict:
    """Report the stale identities and rewrite them only with explicit write authority."""
    if not isinstance(folder, Path) or type(write) is not bool:
        raise CoveragePackError("a pack folder and an explicit write flag are required")
    folder = folder.resolve()
    bodies = read_bodies(folder)
    stale = stale_identities(folder, bodies)
    held_tree = _load(folder, SOURCE_TREE_FILE, SOURCE_TREE_RECORD_TYPE)
    new_tree, source_tree_state = None, "recorded"
    try:
        new_tree = derive_source_tree(folder.parents[2])
    except SourceTreeUnavailable as error:
        # Without git the listing cannot be derived. The held record is left
        # exactly as it is; a build never guesses a citation into the pack.
        source_tree_state = f"not_derived: {error}"
    if new_tree is not None and held_tree != new_tree:
        stale.append("<source tree>")
    if stale and write:
        new_specifications, new_items = derive(bodies)
        replacements = [(folder / SPECIFICATIONS_FILE, new_specifications),
                        (folder / ITEMS_FILE, new_items)]
        if new_tree is not None:
            replacements.append((folder / SOURCE_TREE_FILE, new_tree))
        _replace_both(replacements)
    layers = {layer: sum(1 for item in ITEMS if item.layer == layer)
              for layer in LAYER_SOURCE}
    return {"record_type": "layer_coverage_pack_build/v1", "items": len(ITEMS),
            "items_per_layer": layers, "stale": stale,
            "cited_sources": len(cited_sources()),
            "source_tree": source_tree_state,
            "written": bool(stale and write), "approved": False, "published": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="Rewrite the derived records. Without it the tool only reports.")
    arguments = parser.parse_args(argv)
    result = build(Path(__file__).resolve().parent, write=arguments.write)
    print(json.dumps(result, indent=2))
    return 0 if not result["stale"] or result["written"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
