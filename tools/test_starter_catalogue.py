"""The starter catalogue stays a set of truthful, measured and unapproved candidates.

Every rule below has known-wrong cases and a named check that reports them. A
mutant control patches each rule away and requires that named check to fail. The
specification is loaded through the real staging tool, and the items are loaded
through the real host manifest reader.
"""
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
from importlib import import_module
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.code_nodes.text_conformance import load_packaged_catalogs, merge_layers
from loop_engine.core.facets import EFFECTS
from loop_engine.core.harness_intelligence import KINDS, RECORD_TYPE as ITEM_RECORD_TYPE
from loop_engine.core.instance_instructions import STYLE_FILES
from loop_engine.core.intelligence_tagging import RECORD_TYPE as TAG_RECORD_TYPE
from loop_engine.core.retrieval import Retriever
from loop_engine.core.service_runtime.http_entrypoint import (
    DEFAULT_LICENSE_POLICY, LICENSE_MISSING, LICENSE_NOT_ACCEPTED, LICENSE_UNKNOWN, MANIFEST_VERSION,
    load_host_manifest,
)
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from loop_engine.core.store_serve import StoreRecord
from tools.stage_intelligence_candidates import (
    CandidateStageRequest, compile_candidates, review_search, stage_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue"
NAMESPACE = "starter.catalogue"
#: The 49 items of the first catalogue plus the 60 the expansion had to add. The bound keeps a
#: later change from thinning the catalogue back out; adding items never needs it raised.
MINIMUM_ITEMS, MINIMUM_WORDS, MAXIMUM_WORDS, MAXIMUM_MODEL_GENERATED_ROWS = 109, 150, 600, 8
#: A required part that holds fewer words than this is a heading without content.
MINIMUM_PART_WORDS = 8
#: ``compile_candidates`` accepts one bounded population of at most this many rows, so the
#: catalogue is committed as several population files that the tool accepts as they stand.
#: A separate check proves that the tool refuses a population larger than this bound.
STAGING_POPULATION = 50
#: The message the staging tool gives when one population is empty or larger than the bound.
POPULATION_REFUSAL = "One bounded population of specifications is required"
#: The committed population files and the contract they carry. A check requires that the
#: refresh tool beside the catalogue uses the same three values, so they cannot drift apart.
SPECIFICATIONS_PREFIX = "specifications-"
SPECIFICATIONS_GLOB = SPECIFICATIONS_PREFIX + "[0-9][0-9][0-9].json"
SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v1"
QUERIES_FILE, QUERIES_RECORD_TYPE, MINIMUM_QUERIES = "search-queries.json", "starter_catalogue_search_queries/v1", 100
EXAMPLES_FILE, EXAMPLES_RECORD_TYPE = "executed-examples.json", "starter_catalogue_executed_examples/v1"
#: An absolute floor for the executed examples, not a share of the catalogue. Most items
#: describe a working method and can have no row at all, so this number does not rise with
#: the catalogue. What a body may quote is governed by
#: ``rule_bodies_list_the_quotations_no_example_proves``, which reads every body.
MINIMUM_EXAMPLES, MINIMUM_EXAMPLE_ITEMS = 40, 10
#: One span between single backticks, which is how a body writes a path, a name or a value.
QUOTATION = re.compile(r"`([^`\n]+)`")
IDENTITY = re.compile(r"[a-z][a-z0-9_]{2,79}")
#: The two layers that can hold compiled material today. The other two canonical
#: layers need real runs and real feedback, so an item there would be invented.
LAYERS = {"context": "context_intelligence", "code": "code_intelligence"}
MODEL_GENERATED_SOURCE = "src/loop_engine/governance/candidates/part-00000.jsonl"
#: Each licence state, with the licence the reference must carry and the sentence the body states.
LICENCE_STATES = {"declared": ("MIT", "Licence: MIT."),
                  "needs_review": ("unknown", "Licence state: needs review.")}
REVIEW_LICENCE = {"declared": "MIT, declared", "needs_review": "unknown, needs review"}
#: How a body relates to the file it cites, and the sentence the body must carry so that a
#: reader is never told that general engineering practice was read out of the cited code.
GROUNDINGS = {"restates_cited_source": "Compiled from revision {revision}.",
              "general_practice_beside_cited_source": "Written for this catalogue at revision {revision}."}
GENERAL_PRACTICE = "general_practice_beside_cited_source"
GENERAL_PRACTICE_SENTENCE = ("The steps above are ordinary engineering practice, "
                             "written for this catalogue in its own words.")
#: How each licence state and grounding pair was authored. The two facts are decided
#: together, so a body of general engineering practice cannot record that its words were
#: taken from a repository source. Both values under the state `declared` carry the
#: licence MIT and the same licence sentence; they differ only in where the words come from.
AUTHORING = {("declared", "restates_cited_source"): "assistant_authored_from_repository_sources",
             ("declared", GENERAL_PRACTICE): "assistant_authored_from_general_practice",
             ("needs_review", "restates_cited_source"): "assistant_compiled_from_model_generated_candidates"}
#: The items compiled from model generated statements. They record the licence
#: `unknown`, so the default host licence policy refuses them before registration
#: and they cannot be served until their rights are settled. The names are listed
#: here so that the refusal is proven for each of them by name.
LICENCE_REFUSED_ITEMS = ("check_a_table_join_before_trusting_it", "make_a_data_pipeline_safe_to_run_again")
#: Licence values that a host must refuse, with the refusal code each one produces.
#: `GPL-3.0-only` is a real licence identifier that this host does not list.
UNACCEPTABLE_LICENCES = (("unknown", LICENSE_UNKNOWN), ("", LICENSE_MISSING), ("   ", LICENSE_MISSING),
                         ("GPL-3.0-only", LICENSE_NOT_ACCEPTED))
REVIEW_LAYER = {"context_intelligence": "Context Intelligence", "code_intelligence": "Code Intelligence"}
EMPTY_LAYERS = ("Runtime History and Solution Intelligence", "User Feedback Intelligence")
REQUIRED_PARTS = ("## When to use it", "## Steps", "## Checks", "## Known-wrong example",
                  "## What to record", "## Source")
ITEM_FIELDS = {"reference", "body_path", "lifecycle", "license_state", "provenance"}
#: The dash characters (em dash, en dash, horizontal bar, minus sign) that public prose never uses, written as code points
#: so that this source file stays free of them.
DASHES = "[" + chr(0x2014) + chr(0x2013) + chr(0x2015) + chr(0x2212) + "]"
#: The retired heading, assembled from its three words, so that this source file
#: does not itself hold the retired term that the conformance gate refuses.
RETIRED_HEADING = " ".join(("what", "is", "next"))
def _patterns(*patterns):
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


#: Internal runtime vocabulary that a customer-facing body, title, purpose or tag never uses.
#: Cited source paths are removed before a body is read, because a path is not wording.
INTERNAL_VOCABULARY = _patterns(
    r"(?<![a-z0-9])loops?(?![a-z0-9])", r"(?<![a-z0-9])practitioners?(?![a-z0-9])",
    r"role[\s_-]+profiles?", r"runtime[\s_-]+classification", r"solution[\s_-]+canvas", r"code[\s_-]+nodes?",
    r"(?<![a-z0-9])spawn(?:s|ed|ing)?(?![a-z0-9])", r"starting[\s_-]+(?:solution|intelligence)(?![a-z0-9])",
    r"run[\s_-]+history", r"runtime[\s_-]+(?:memory|history)",
    r"(?:context|code|solution|feedback)[\s_-]+intelligence", r"intelligence[\s_-]+(?:items?|quer(?:y|ies)|layers?)")
#: The retired public language and the dash characters that continuous integration
#: refuses in every published document, so they also apply to the review sheet.
RETIRED_PUBLIC_LANGUAGE = _patterns(
    r"(?<![a-z0-9])(?:grand)?child(?:ren)?(?![a-z0-9])", DASHES, r"stop[\s_-]+conditions?",
    r"(?<![a-z0-9])receipts?(?![a-z0-9])", r"(?<![a-z0-9])chronicles?(?![a-z0-9])",
    r"what[\s_-]*is[\s_-]*next|what[\s_-]+next|whats[\s_-]*next")
FORBIDDEN = INTERNAL_VOCABULARY + RETIRED_PUBLIC_LANGUAGE
REVIEW_FORBIDDEN = RETIRED_PUBLIC_LANGUAGE


@dataclass(frozen=True)
class CatalogueSnapshot:
    """Everything the rules read, held in memory so a known-wrong copy is cheap."""

    populations: tuple
    items: dict
    bodies: dict
    review: str
    repository: Path
    examples: dict

    @property
    def specifications(self) -> dict:
        """Every committed population's rows in file order, under one record.

        The staging tool refuses this combined record, because it holds more rows
        than one population may hold. It exists so that a rule about the whole
        catalogue reads one list. A rule about staging reads ``populations``.
        """
        return {"record_type": SPECIFICATIONS_RECORD_TYPE,
                "specifications": [row for _name, record in self.populations
                                   for row in record.get("specifications") or ()]}

    def rows(self):
        return list(zip(self.specifications["specifications"], self.items.get("items") or ()))


def load_populations(folder: Path) -> tuple:
    """The committed population files with their records, in file name order."""
    return tuple((path.name, json.loads(path.read_text(encoding="utf-8")))
                 for path in sorted(folder.glob(SPECIFICATIONS_GLOB)))


def load_snapshot(folder: Path = CATALOGUE) -> CatalogueSnapshot:
    bodies = {path.stem: path.read_bytes() for path in sorted((folder / "bodies").iterdir())}
    return CatalogueSnapshot(load_populations(folder),
                             json.loads((folder / "items.json").read_text(encoding="utf-8")), bodies,
                             (folder / "REVIEW.md").read_text(encoding="utf-8"), ROOT,
                             json.loads((folder / EXAMPLES_FILE).read_text(encoding="utf-8")))


def word_count(text: str) -> int:
    return sum(1 for token in text.split() if re.search(r"[A-Za-z0-9]", token))


def _source_section(text: str) -> str:
    return text.split("\n## Source\n", 1)[1] if "\n## Source\n" in text else ""


def rule_identities_are_unique(snapshot):
    spec_ids = [row.get("id") for row in snapshot.specifications.get("specifications") or ()]
    item_ids = [row.get("reference", {}).get("identity") for row in snapshot.items.get("items") or ()]
    found = [f"identity {identity!r} is not a plain lower case name" for identity in spec_ids
             if not isinstance(identity, str) or not IDENTITY.fullmatch(identity)]
    found += [f"identity {identity!r} repeats" for identity in sorted(set(spec_ids), key=str)
              if spec_ids.count(identity) > 1]
    if spec_ids != item_ids:
        found.append("the specifications and the items do not list the same identities in the same order")
    if sorted(snapshot.bodies) != sorted(set(map(str, spec_ids))):
        found.append("every identity needs exactly one body and no other body may be present")
    return found


def rule_digests_and_sizes_match_the_bodies(snapshot):
    refresh = _refresh_module()
    found = []
    for row, item in snapshot.rows():
        identity, reference = row.get("id"), item.get("reference", {})
        body = snapshot.bodies.get(identity)
        if body is None:
            found.append(f"{identity}: no body to measure")
            continue
        if reference.get("digest") != hashlib.sha256(body).hexdigest():
            found.append(f"{identity}: the digest does not match the body")
        if reference.get("size_bytes") != len(body):
            found.append(f"{identity}: the size does not match the body")
        if row.get("text") != body.decode("utf-8"):
            found.append(f"{identity}: the staged text is not the body")
        if item.get("body_path") != f"bodies/{identity}.md":
            found.append(f"{identity}: the body path does not name the body")
        try:
            measured = refresh.measured_reference(reference, body.decode("utf-8"))
        except (KeyError, TypeError, ValueError) as error:
            found.append(f"{identity}: the engine refuses the reference: {error}")
        else:
            if measured != reference:
                found.append(f"{identity}: the engine measures a different reference")
    return found


def rule_every_item_carries_a_licence(snapshot):
    found = []
    for row, item in snapshot.rows():
        identity, state = row.get("id"), item.get("license_state")
        if state not in LICENCE_STATES:
            found.append(f"{identity}: licence state {state!r} is not declared")
            continue
        licence, sentence = LICENCE_STATES[state]
        grounding = (item.get("provenance") or {}).get("grounding")
        authoring = AUTHORING.get((state, grounding))
        generated = MODEL_GENERATED_SOURCE in (row.get("sources") or ())
        if item.get("reference", {}).get("license") != licence:
            found.append(f"{identity}: the licence must be {licence!r} in the state {state!r}")
        if generated != (state == "needs_review"):
            found.append(f"{identity}: model generated material needs review, and only such material")
        if authoring is None:
            found.append(f"{identity}: the licence state {state!r} and the grounding {grounding!r} are not a "
                         f"pair this catalogue supports, so no authoring value fits them")
        elif (item.get("provenance") or {}).get("authoring") != authoring:
            found.append(f"{identity}: a body that is {grounding!r} under the licence state {state!r} was "
                         f"authored as {authoring!r}, not {(item.get('provenance') or {}).get('authoring')!r}")
        if sentence not in snapshot.bodies.get(identity, b"").decode("utf-8"):
            found.append(f"{identity}: the body does not state its licence")
    return found


def rule_bodies_say_how_they_relate_to_their_source(snapshot):
    """A body either restates the file it cites or says that it is general practice beside it."""
    revision = str(snapshot.items.get("source_revision"))[:7]
    found = []
    for row, item in snapshot.rows():
        identity = row.get("id")
        grounding = (item.get("provenance") or {}).get("grounding")
        body = snapshot.bodies.get(identity, b"").decode("utf-8")
        if grounding not in GROUNDINGS:
            found.append(f"{identity}: the provenance must say how the body relates to its source, "
                         f"one of {sorted(GROUNDINGS)}, not {grounding!r}")
            continue
        for name, sentence in GROUNDINGS.items():
            if (sentence.format(revision=revision) in body) != (name == grounding):
                found.append(f"{identity}: a body declared as {grounding!r} must carry "
                             f"{GROUNDINGS[grounding].format(revision=revision)!r} and no other grounding sentence")
                break
        if (GENERAL_PRACTICE_SENTENCE in body) != (grounding == GENERAL_PRACTICE):
            found.append(f"{identity}: only a body written from general practice may say that it was")
    return found


def rule_every_item_is_a_candidate(snapshot):
    found = []
    if snapshot.items.get("publication") != "not_published":
        found.append("the items record must say that nothing is published")
    for row, item in snapshot.rows():
        identity = row.get("id")
        if set(item) != ITEM_FIELDS:
            found.append(f"{identity}: an item carries exactly {sorted(ITEM_FIELDS)}, never an approval or a grant")
        tags = item.get("reference", {}).get("tags") or {}
        if item.get("lifecycle") != "candidate" or tags.get("lifecycle") != ["candidate"]:
            found.append(f"{identity}: the lifecycle must be candidate in the item and in its tags")
    return found


def rule_no_forbidden_vocabulary(snapshot):
    found = []
    for row, item in snapshot.rows():
        identity = row.get("id")
        body = snapshot.bodies.get(identity, b"").decode("utf-8")
        for path in sorted(row.get("sources") or (), key=len, reverse=True):
            body = body.replace(path, "")
        texts = [body, str(row.get("title")), str(item.get("reference", {}).get("purpose")),
                 " ".join(map(str, row.get("tags") or ())), str(identity)]
        for pattern in FORBIDDEN:
            for text in texts:
                match = pattern.search(text)
                if match:
                    found.append(f"{identity}: forbidden wording {match.group(0)!r}")
    found += [f"REVIEW.md: forbidden wording {pattern.search(snapshot.review).group(0)!r}"
              for pattern in REVIEW_FORBIDDEN if pattern.search(snapshot.review)]
    return found


def rule_bodies_stay_in_the_word_range(snapshot):
    counts = {identity: word_count(body.decode("utf-8")) for identity, body in snapshot.bodies.items()}
    return [f"{identity}: {count} words is outside {MINIMUM_WORDS} to {MAXIMUM_WORDS}"
            for identity, count in sorted(counts.items()) if not MINIMUM_WORDS <= count <= MAXIMUM_WORDS]


def compile_every_population(populations: tuple, request) -> tuple[list, list]:
    """Every compiled record, with the refusal of any committed population file the tool rejects.

    Each file is handed to the staging tool exactly as it is committed, which is
    what an operator does with the command in the review sheet. Nothing is split
    here, so a file the tool would refuse is reported instead of being worked around.
    """
    records, refusals = [], []
    for name, record in populations:
        try:
            records += compile_candidates(record, request)
        except ValueError as error:
            refusals.append(f"{name}: the staging tool refuses the population: {error}")
    return records, refusals


def rule_every_population_file_loads_through_the_staging_tool(snapshot):
    """Every committed population file is accepted by the staging tool as it stands."""
    found = []
    names = [name for name, _record in snapshot.populations]
    expected = [f"{SPECIFICATIONS_PREFIX}{number:03d}.json" for number in range(1, len(names) + 1)]
    if names != expected:
        return [f"the population files must be numbered from one without a gap: {expected}, not {names}"]
    for number, (name, record) in enumerate(snapshot.populations, start=1):
        rows = record.get("specifications")
        if record.get("record_type") != SPECIFICATIONS_RECORD_TYPE:
            found.append(f"{name}: record type {record.get('record_type')!r} is not the one the staging tool accepts")
        if record.get("population") != number or record.get("populations") != len(names):
            found.append(f"{name}: the record must say that it is population {number} of {len(names)}")
        if not isinstance(rows, list) or not 1 <= len(rows) <= STAGING_POPULATION:
            found.append(f"{name}: a population holds one to {STAGING_POPULATION} rows, "
                         f"not {len(rows) if isinstance(rows, list) else 'a list'}")
    if found:
        return found
    records, found = compile_every_population(
        snapshot.populations, CandidateStageRequest(snapshot.repository, NAMESPACE))
    if found:
        return found
    if len(records) != len(snapshot.specifications["specifications"]):
        found.append("the staging tool did not compile one record for each row")
    identities = [record["record_id"] for record in records]
    found += [f"{identity}: the same record identity is staged twice"
              for identity in sorted(set(identities)) if identities.count(identity) > 1]
    found += [f"{record['record_id']}: staged as something other than an unexecutable candidate"
              for record in records if record["lifecycle"] != "candidate"
              or record["payload"]["lifecycle"] != "candidate" or record["payload"]["execution_available"] is not False
              or not record["record_id"].startswith(NAMESPACE + ".")]
    return found


def rule_bodies_have_the_required_parts(snapshot):
    found = []
    for row, _item in snapshot.rows():
        identity = row.get("id")
        text = snapshot.bodies.get(identity, b"").decode("utf-8")
        if text.splitlines()[:1] != [f"# {row.get('title')}"]:
            found.append(f"{identity}: the first line is not the title")
        positions = [text.find(f"\n{part}\n") for part in REQUIRED_PARTS]
        if -1 in positions or positions != sorted(positions):
            found.append(f"{identity}: the body needs these parts in this order: {', '.join(REQUIRED_PARTS)}")
        else:
            ends = positions[1:] + [len(text)]
            found += [f"{identity}: the part {part!r} needs at least {MINIMUM_PART_WORDS} words of content"
                      for part, start, end in zip(REQUIRED_PARTS, positions, ends)
                      if word_count(text[start + len(part) + 2:end]) < MINIMUM_PART_WORDS]
        cited = set(re.findall(r"`((?:src|integrations)/[^`]+)`", _source_section(text)))
        if cited != set(row.get("sources") or ()):
            found.append(f"{identity}: the Source part must cite exactly the listed sources")
        if not text.endswith("\n") or text.endswith("\n\n"):
            found.append(f"{identity}: the body must end with one line break")
    return found


def rule_layers_kinds_effects_and_styles_are_declared(snapshot):
    styles = {entry.style for entry in STYLE_FILES}
    found = []
    for row, item in snapshot.rows():
        identity, reference = row.get("id"), item.get("reference", {})
        if LAYERS.get(row.get("layer")) is None or reference.get("source_layer") != LAYERS.get(row.get("layer")):
            found.append(f"{identity}: only compiled context and code material exists; history and feedback need "
                         "real runs and real feedback")
        if reference.get("record_type") != ITEM_RECORD_TYPE or reference.get("kind") not in KINDS:
            found.append(f"{identity}: the reference is not a current item of a known kind")
        effects = reference.get("declared_effects")
        if (not isinstance(effects, list) or any(effect not in EFFECTS or effect == EFFECTS[0] for effect in effects)
                or len(set(effects)) != len(effects)):
            found.append(f"{identity}: effects come from the declared vocabulary, and an item without effects "
                         f"declares an empty list, never {EFFECTS[0]!r}, which a step would have to hold")
        if not isinstance(reference.get("styles"), list) or set(reference["styles"]) - styles:
            found.append(f"{identity}: a harness style must be a registered style")
        if ((reference.get("tags") or {}).get("record_type") != TAG_RECORD_TYPE
                or reference.get("body_included") is not False):
            found.append(f"{identity}: the reference needs current tags and never carries the body")
    return found


def rule_source_references_are_pinned(snapshot):
    revision = snapshot.items.get("source_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        return ["the items record must name one full source revision"]
    found = []
    for row, item in snapshot.rows():
        sources = row.get("sources") or [""]
        if item.get("reference", {}).get("source_ref") != f"{sources[0]}@{revision}":
            found.append(f"{row.get('id')}: the source reference must be the first listed source at the full revision")
        if revision[:7] not in snapshot.bodies.get(row.get("id"), b"").decode("utf-8"):
            found.append(f"{row.get('id')}: the body does not name the revision it was compiled from")
    earlier = snapshot.items.get("previous_source_revisions")
    if (not isinstance(earlier, list) or not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value)
                                                 for value in earlier) or revision in earlier
            or len(set(earlier)) != len(earlier)):
        return found + ["the items record must keep the earlier anchor revisions, each one full, distinct and "
                        "not the current one"]
    # The sheet may name the revision the catalogue is anchored to and any anchor it was moved from.
    # Naming anything else means the sheet was left behind by an anchor change.
    allowed = {revision[:7]} | {value[:7] for value in earlier}
    named = set(re.findall(r"revision [`]?([0-9a-f]{7})[`]?", snapshot.review))
    found += [f"REVIEW.md names revision {other!r}, which is neither the revision the catalogue is anchored to "
              f"nor one it was anchored to before" for other in sorted(named - allowed)]
    if revision[:7] not in named:
        found.append("REVIEW.md does not name the revision the catalogue is anchored to")
    return found


def rule_cited_source_bytes_are_the_pinned_bytes(snapshot):
    """Every cited file in the tree is byte for byte the file the record pins.

    ``compile_candidates`` hashes the working tree into ``sources[].sha256`` of the
    staged record, while ``reference.source_ref`` names a revision. If the tree moves
    on, one staged record carries two provenance facts about different bytes. The
    items record therefore pins the digest of every cited file at its own
    ``source_revision``, and this rule compares those digests with the tree. When a
    cited file changes, anchor the catalogue again with the refresh tool, which reads
    the file at the new revision before it writes anything.
    """
    digests = snapshot.items.get("source_digests")
    if not isinstance(digests, dict):
        return ["the items record must pin the digest of every cited source"]
    cited = sorted({source for row, _item in snapshot.rows() for source in row.get("sources") or ()})
    found = [f"{source}: no digest is pinned for a cited source" for source in cited if source not in digests]
    found += [f"{source}: a digest is pinned for a file that no item cites" for source in sorted(digests)
              if source not in cited]
    for source in cited:
        if source not in digests:
            continue
        path = snapshot.repository / source
        if not path.is_file():
            found.append(f"{source}: a cited source is not a file of this repository")
            continue
        measured = hashlib.sha256(path.read_bytes()).hexdigest()
        if measured != digests[source]:
            found.append(f"{source}: the file in the tree is not the file the record pins at "
                         f"{str(snapshot.items.get('source_revision'))[:7]}; anchor the catalogue again")
    return found


def rule_model_generated_material_is_bounded(snapshot):
    path = snapshot.repository / MODEL_GENERATED_SOURCE
    known = {json.loads(line)["digest"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    found, used = [], []
    for row, item in snapshot.rows():
        identity = row.get("id")
        digests = (item.get("provenance") or {}).get("model_generated_row_digests")
        if not isinstance(digests, list):
            found.append(f"{identity}: the provenance must list its model generated rows, even when there are none")
            continue
        if bool(digests) != (MODEL_GENERATED_SOURCE in (row.get("sources") or ())):
            found.append(f"{identity}: model generated rows and the model generated source go together")
        found += [f"{identity}: row {digest!r} is not in the model generated source" for digest in digests
                  if digest not in known]
        found += [f"{identity}: the body does not cite row {digest!r}" for digest in digests
                  if f"`{digest}`" not in _source_section(snapshot.bodies.get(identity, b"").decode("utf-8"))]
        used += digests
    if len(used) != len(set(used)) or len(used) > MAXIMUM_MODEL_GENERATED_ROWS:
        found.append(f"at most {MAXIMUM_MODEL_GENERATED_ROWS} distinct model generated rows may be used")
    return found


def rule_the_review_sheet_lists_every_item(snapshot):
    listed = re.findall(r"^\| \[([a-z0-9_]+)\]\(bodies/([a-z0-9_]+)\.md\) \| ([^|]+) \|[^|]*\| `([^`]+)` \| ([^|]+) \|",
                        snapshot.review, re.MULTILINE)
    expected = [(row.get("id"), row.get("id"), REVIEW_LAYER.get(item.get("reference", {}).get("source_layer")),
                 str(item.get("reference", {}).get("source_ref")).split("@")[0],
                 REVIEW_LICENCE.get(item.get("license_state"))) for row, item in snapshot.rows()]
    found = [] if [tuple(cell.strip() for cell in row) for row in listed] == expected else [
        "the review table must list every item once, in order, with its layer, source and licence state"]
    found += [f"the review sheet must say why {layer} has no items" for layer in EMPTY_LAYERS
              if layer not in snapshot.review]
    return found


def rule_the_catalogue_is_large_enough(snapshot):
    count = len(snapshot.specifications.get("specifications") or ())
    return [] if count >= MINIMUM_ITEMS else [f"{count} items is fewer than {MINIMUM_ITEMS}"]


def _observed_field(result, name):
    """Whether a result carries a named field, and its value.

    The name `value` means the whole result. Any other name must be a key that
    the result really holds or an attribute that it really has, so an absent
    field is reported instead of being compared as nothing against nothing.
    """
    if name == "value":
        return True, result
    if isinstance(result, dict):
        return name in result, result.get(name)
    return hasattr(result, name), getattr(result, name, None)


def _module_source_path(module_name, repository: Path):
    """The repository path of an imported module, or None when it is not a file of this repository."""
    try:
        path = Path(import_module(module_name).__file__).resolve()
    except (AttributeError, ImportError, TypeError, ValueError):
        return None
    try:
        return path.relative_to(repository).as_posix()
    except ValueError:
        return None


def rule_quoted_examples_reproduce(snapshot):
    """Every quoted example runs against the code that its own item cites, and observes what the body says.

    A row is bound to one item: the module it names must be one of that item's
    own sources, and the function must be one of that item's own symbols. A row
    that asserts nothing, or that names a field the result does not have, is
    refused, so the file cannot be hollowed out while every named check is green.
    """
    record = snapshot.examples
    if record.get("record_type") != EXAMPLES_RECORD_TYPE:
        return [f"{EXAMPLES_FILE}: record type {record.get('record_type')!r} is not supported"]
    modules, token = record.get("modules") or {}, record.get("packaged_catalogs_token")
    rows = record.get("examples") or ()
    declared = {row.get("id"): (set(row.get("sources") or ()), set(row.get("symbols") or ()))
                for row in snapshot.specifications.get("specifications") or ()}
    found = []
    if len(rows) < MINIMUM_EXAMPLES or len({row.get("identity") for row in rows}) < MINIMUM_EXAMPLE_ITEMS:
        found.append(f"{EXAMPLES_FILE}: at least {MINIMUM_EXAMPLES} executed examples over "
                     f"{MINIMUM_EXAMPLE_ITEMS} items are required")
    catalogs = merge_layers([load_packaged_catalogs()])
    for row in rows:
        identity, quote = row.get("identity"), row.get("quote")
        body = snapshot.bodies.get(identity)
        if body is None:
            found.append(f"{identity}: an executed example names an item that has no body")
            continue
        if not isinstance(quote, str) or quote not in body.decode("utf-8"):
            found.append(f"{identity}: the body does not say {quote!r} word for word")
        sources, symbols = declared.get(identity, (set(), set()))
        module_name = modules.get(row.get("module"))
        source_path = _module_source_path(module_name, snapshot.repository) if module_name else None
        if source_path is None or source_path not in sources:
            found.append(f"{identity}: an executed example runs {module_name!r}, which is not one of the "
                         f"{len(sources)} sources this item cites")
            continue
        function = getattr(import_module(module_name), row.get("function"), None)
        if function is None:
            found.append(f"{identity}: {row.get('module')}.{row.get('function')} is not a cited function")
            continue
        if row.get("function") not in symbols:
            found.append(f"{identity}: an executed example calls {row.get('function')!r}, which is not one of the "
                         f"symbols this item names")
        expected_fields = row.get("expect")
        if not isinstance(expected_fields, dict) or not expected_fields:
            found.append(f"{identity}: an executed example that expects no field asserts nothing")
            continue
        arguments = [catalogs if value == token else value for value in row.get("arguments") or ()]
        try:
            result = function(*arguments, **(row.get("keywords") or {}))
        except Exception as error:  # the body must not quote a call the code refuses
            found.append(f"{identity}: {row.get('function')} refused the example: {error}")
            continue
        for name, expected in expected_fields.items():
            present, observed = _observed_field(result, name)
            if not present:
                found.append(f"{identity}: {row.get('function')} gives no field {name!r}, so the body's "
                             f"{expected!r} is not observed")
                continue
            if isinstance(observed, tuple):
                observed = list(observed)
            if observed != expected:
                found.append(f"{identity}: {row.get('function')} gives {name}={observed!r}, "
                             f"the body says {expected!r}")
    return found


def rule_bodies_list_the_quotations_no_example_proves(snapshot):
    """Every quotation in a body is proven by an executed example or listed by its own item.

    ``rule_quoted_examples_reproduce`` runs from the executed examples to the bodies. This
    rule runs the other way. It collects every span in backticks that is not a source the
    item cites, not a symbol the item names and not a model generated row the item cites,
    drops the ones that an executed example of this item proves word for word, and requires
    the item to list exactly what is left. So a body cannot gain a quoted value that nothing
    ran while every named check stays green: the record has to say so.

    The list is mechanical. It also holds ordinary terms such as a file name or a setting
    name, not only values that the body claims the code returns.
    """
    proven = {}
    for row in snapshot.examples.get("examples") or ():
        proven.setdefault(row.get("identity"), []).append(row.get("quote"))
    found = []
    for row, item in snapshot.rows():
        identity = row.get("id")
        provenance = item.get("provenance") or {}
        listed = provenance.get("unexecuted_quotations")
        if not isinstance(listed, list) or not all(isinstance(value, str) for value in listed):
            found.append(f"{identity}: the item must list the quotations that no executed example proves, "
                         f"even when there are none, not {listed!r}")
            continue
        known = (set(row.get("sources") or ()) | set(row.get("symbols") or ())
                 | set(provenance.get("model_generated_row_digests") or ()))
        quotes = [quote for quote in proven.get(identity, ()) if isinstance(quote, str)]
        body = snapshot.bodies.get(identity, b"").decode("utf-8")
        measured = sorted(token for token in set(QUOTATION.findall(body)) - known
                          if not any(token in quote for quote in quotes))
        if sorted(listed) != measured:
            found.append(f"{identity}: the body carries {sorted(set(measured) - set(listed))} that the item "
                         f"does not list, and the item lists {sorted(set(listed) - set(measured))} that no "
                         f"quotation of the body needs")
    return found


RULES = {function.__name__[5:]: function for function in (
    rule_identities_are_unique, rule_digests_and_sizes_match_the_bodies, rule_every_item_carries_a_licence,
    rule_bodies_say_how_they_relate_to_their_source,
    rule_every_item_is_a_candidate, rule_no_forbidden_vocabulary, rule_bodies_stay_in_the_word_range,
    rule_every_population_file_loads_through_the_staging_tool, rule_bodies_have_the_required_parts,
    rule_layers_kinds_effects_and_styles_are_declared, rule_source_references_are_pinned,
    rule_cited_source_bytes_are_the_pinned_bytes,
    rule_model_generated_material_is_bounded, rule_the_review_sheet_lists_every_item,
    rule_the_catalogue_is_large_enough, rule_quoted_examples_reproduce,
    rule_bodies_list_the_quotations_no_example_proves)}


def problems(snapshot) -> dict:
    """Every rule that reports something, with what it reports."""
    return {name: found for name, found in ((name, rule(snapshot)) for name, rule in RULES.items()) if found}


def _refresh_module():
    """The refresh tool beside the catalogue, loaded once; its folder is not a package."""
    name = "starter_catalogue_refresh"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, CATALOGUE / "refresh.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[name]
            raise
    return sys.modules[name]


def _repack(populations: tuple, rows: list) -> tuple:
    """The rows put back into population files of at most the bound, keeping the file names.

    A change that adds rows past the last committed file gets one more file, named
    after its number, so a known-wrong copy still looks like a committed catalogue.
    """
    names = [name for name, _record in populations]
    chunks = [rows[start:start + STAGING_POPULATION] for start in range(0, len(rows), STAGING_POPULATION)] or [[]]
    while len(names) < len(chunks):
        names.append(f"{SPECIFICATIONS_PREFIX}{len(names) + 1:03d}.json")
    return tuple((names[number - 1],
                  {"record_type": SPECIFICATIONS_RECORD_TYPE, "population": number, "populations": len(chunks),
                   "specifications": chunk})
                 for number, chunk in enumerate(chunks, start=1))


def _changed(snapshot, *, specifications=None, populations=None, items=None, body=None, review=None,
             examples=None):
    """A deep copy with one deliberate defect; the committed files are never touched."""
    new_populations, new_items = deepcopy(snapshot.populations), deepcopy(snapshot.items)
    new_examples = deepcopy(snapshot.examples)
    bodies = dict(snapshot.bodies)
    if specifications:
        rows = [row for _name, record in new_populations for row in record["specifications"]]
        specifications(rows)
        new_populations = _repack(new_populations, rows)
    if populations:
        new_populations = populations(new_populations)
    if items:
        items(new_items)
    if examples:
        examples(new_examples["examples"])
    if body:
        identity = new_populations[0][1]["specifications"][0]["id"]
        bodies[identity] = body(bodies[identity].decode("utf-8")).encode("utf-8")
    return replace(snapshot, populations=new_populations, items=new_items, bodies=bodies,
                   examples=new_examples,
                   review=snapshot.review if review is None else review(snapshot.review))


def _one_oversized_population(populations: tuple) -> tuple:
    """Every row in one population file, which is the shape the staging tool refuses."""
    rows = [row for _name, record in populations for row in record["specifications"]]
    return ((populations[0][0], {"record_type": SPECIFICATIONS_RECORD_TYPE, "population": 1, "populations": 1,
                                 "specifications": rows}),)


def _first_population_emptied(populations: tuple) -> tuple:
    """The first population file with no rows left in it, which the staging tool also refuses."""
    name, record = populations[0]
    return ((name, {**record, "specifications": []}),) + populations[1:]


def _generated(items):
    return next(item for item in items["items"] if item["license_state"] == "needs_review")


def _general_practice_item(items):
    """The first item whose body is general engineering practice written beside its cited file."""
    return next(item for item in items["items"] if item["provenance"]["grounding"] == GENERAL_PRACTICE)


def _restating_item(items):
    """The first item under the licence state `declared` whose body restates the file it cites."""
    return next(item for item in items["items"] if item["license_state"] == "declared"
                and item["provenance"]["grounding"] == "restates_cited_source")


def _general_practice_identity(snapshot):
    """The first item whose body is general practice written beside the file it cites."""
    return next(row["id"] for row, item in snapshot.rows()
                if item["provenance"]["grounding"] == GENERAL_PRACTICE)


def _changed_body(snapshot, identity, change):
    """A deep copy in which one named body carries a deliberate defect."""
    text = change(snapshot.bodies[identity].decode("utf-8"))
    return replace(snapshot, bodies={**snapshot.bodies, identity: text.encode("utf-8")})


def _set(target, key, value):
    target[key] = value


def _first_reference(items):
    return items["items"][0]["reference"]


def _without_the_capitalisation_examples(rows):
    """Every executed example of the capitalisation item removed, so its values lose their proof."""
    rows[:] = [row for row in rows if row["identity"] != "restore_capitalisation_of_names"]


def _capitalisation_example(rows):
    """The executed example that the adversarial review corrected, whatever its position."""
    return next(row for row in rows if row["identity"] == "restore_capitalisation_of_names"
                and row["arguments"][0] == "iPhone Repair")


def _wording(sentence: str):
    """A known-wrong case that puts one forbidden sentence into the first body.

    Each sentence is written so that exactly one forbidden pattern matches it.
    Removing that one pattern then leaves the sentence accepted, which is what
    the per-pattern control requires.
    """
    return lambda snapshot: _changed(
        snapshot, body=lambda text: text.replace("\n## Steps\n", f"\n{sentence}\n\n## Steps\n"))


def _foreign_module_row(snapshot):
    """A call that succeeds in every respect, listed under an item that does not cite the module it runs."""
    cited = _module_source_path(snapshot.examples["modules"]["operations"], snapshot.repository)
    identity = next(row["id"] for row in snapshot.specifications["specifications"]
                    if cited not in (row.get("sources") or ()))
    return {"identity": identity, "quote": snapshot.bodies[identity].decode("utf-8").splitlines()[0],
            "module": "operations", "function": "whitespace_normalize", "arguments": ["a  b"],
            "expect": {"output": "a b"}}


def _without_the_first_examples_source(snapshot):
    """The item of the first executed example stops citing the module that the example runs."""
    row = snapshot.examples["examples"][0]
    path = _module_source_path(snapshot.examples["modules"][row["module"]], snapshot.repository)
    return _changed(snapshot, specifications=lambda rows: next(
        entry for entry in rows if entry["id"] == row["identity"])["sources"].remove(path))


def _renamed_first_identity(snapshot):
    """The first item under an identity with internal vocabulary; every derived field follows the new name."""
    old, new = snapshot.specifications["specifications"][0]["id"], "practitioner_loop_profile"
    changed = _changed(snapshot, specifications=lambda rows: _set(rows[0], "id", new),
                       items=lambda items: (_set(_first_reference(items), "identity", new),
                                            _set(items["items"][0], "body_path", f"bodies/{new}.md")))
    bodies = {(new if identity == old else identity): body for identity, body in snapshot.bodies.items()}
    return replace(changed, bodies=bodies, review=snapshot.review.replace(old, new))


KNOWN_WRONG = {
    "identities_are_unique": (
        ("an identity repeats", lambda s: _changed(
            s, specifications=lambda rows: rows.append(deepcopy(rows[0])),
            items=lambda items: items["items"].append(deepcopy(items["items"][0])))),
        ("a body has no item", lambda s: replace(s, bodies={**s.bodies, "stray_body": b"# Stray\n"}))),
    "digests_and_sizes_match_the_bodies": (
        ("a body was edited without a refresh", lambda s: _changed(s, body=lambda text: text + "One more sentence.\n")),
        ("a digest was typed by hand", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items), "digest", "0" * 64)))),
    "every_item_carries_a_licence": (
        ("an item has no licence", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items), "license", ""))),
        ("model generated material claims the repository licence", lambda s: _changed(
            s, items=lambda items: (_set(_generated(items), "license_state", "declared"),
                                    _set(_generated(items)["reference"], "license", "MIT")))),
        ("general practice says that its words came from a repository source", lambda s: _changed(
            s, items=lambda items: _set(_general_practice_item(items)["provenance"], "authoring",
                                        AUTHORING[("declared", "restates_cited_source")]))),
        ("a body that restates its source claims to be general practice authoring", lambda s: _changed(
            s, items=lambda items: _set(_restating_item(items)["provenance"], "authoring",
                                        AUTHORING[("declared", GENERAL_PRACTICE)]))),
        ("an authoring value that this catalogue does not know", lambda s: _changed(
            s, items=lambda items: _set(_general_practice_item(items)["provenance"], "authoring",
                                        "assistant_authored_from_another_project")))),
    "bodies_say_how_they_relate_to_their_source": (
        ("an item does not say how its body relates to its source", lambda s: _changed(
            s, items=lambda items: _set(items["items"][0]["provenance"], "grounding", "read_from_the_source"))),
        ("general practice claims to be compiled from the file it cites", lambda s: _changed_body(
            s, _general_practice_identity(s),
            lambda text: text.replace("Written for this catalogue at revision", "Compiled from revision"))),
        ("general practice does not say that it is general practice", lambda s: _changed_body(
            s, _general_practice_identity(s), lambda text: text.replace(GENERAL_PRACTICE_SENTENCE + "\n\n", ""))),
        ("a body compiled from its source claims to be general practice", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Source\n", f"\n{GENERAL_PRACTICE_SENTENCE}\n\n## Source\n")))),
    "every_item_is_a_candidate": (
        ("an item calls itself qualified", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items)["tags"], "lifecycle", ["qualified"]))),
        ("an item carries an approval", lambda s: _changed(
            s, items=lambda items: _set(items["items"][0], "approval_ref", "owner:approved")))),
    "no_forbidden_vocabulary": (
        ("a body uses internal runtime vocabulary", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Steps\n", "\nThe Practitioner Loop decides.\n\n## Steps\n"))),
        ("a purpose names a role profile", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items), "purpose", "Select the role profile for a task"))),
        ("a body uses a dash character", lambda s: _changed(
            s, body=lambda text: text + f"A pause {chr(0x2014)} then more.\n")),
        ("a body uses a horizontal bar", lambda s: _changed(
            s, body=lambda text: text + f"A pause {chr(0x2015)} then more.\n")),
        ("an identity carries internal runtime vocabulary", _renamed_first_identity),
        *((f"a body uses the wording {label}", _wording(sentence)) for label, sentence in (
            ("of the runtime type", "The task runs in a loop until it is done."),
            ("of a runtime role", "A Practitioner owns this work."),
            ("of the runtime classification", "The runtime classification decides the shape."),
            ("of a compiled canvas", "Compile the Solution Canvas first."),
            ("of the engine's own modules", "Reuse the code nodes of the engine."),
            ("of a graph relationship", "It was spawned by the step before it."),
            ("of a starting relationship", "A Starting Solution runs the pipeline."),
            ("of the run record store", "Keep the outcome in Run History."),
            ("of a retired condition name", "Write the stop condition before you start."),
            ("of a retired word for a record", "Keep the receipt of the change."),
            ("of a retired word for a history", "Add the decision to the chronicle."),
            ("of a retired heading", f"Then decide {RETIRED_HEADING}."))),
        ("a body names the temporary run store", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Steps\n", "\nKeep the value in Runtime Memory.\n\n## Steps\n"))),
        ("a body uses a longer family word", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Steps\n", "\nPass it to the grandchildren.\n\n## Steps\n"))),
        ("a body uses a minus sign as punctuation", lambda s: _changed(
            s, body=lambda text: text + f"A pause {chr(0x2212)} then more.\n")),
        ("a purpose names an intelligence layer", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items), "purpose",
                                        "Serve material from Context Intelligence to a step"))),
        ("a body names a stored query", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Steps\n", "\nRun an Intelligence Query first.\n\n## Steps\n")))),
    "bodies_stay_in_the_word_range": (
        ("a body is one sentence long", lambda s: _changed(s, body=lambda text: "# Short\n\nOne sentence only.\n")),
        ("a body is an essay", lambda s: _changed(s, body=lambda text: text + "more words " * 400 + "\n"))),
    "every_population_file_loads_through_the_staging_tool": (
        ("a row carries a field the staging tool does not accept", lambda s: _changed(
            s, specifications=lambda rows: _set(rows[0], "license", "MIT"))),
        ("a row claims to be active", lambda s: _changed(
            s, specifications=lambda rows: _set(rows[0], "lifecycle", "active"))),
        ("a source is not a file in the repository", lambda s: _changed(
            s, specifications=lambda rows: _set(rows[0], "sources", ["src/loop_engine/no_such_file.py"]))),
        ("the same identity is staged again in a later population", lambda s: _changed(
            s, specifications=lambda rows: rows.append(deepcopy(rows[0])),
            items=lambda items: items["items"].append(deepcopy(items["items"][0])))),
        ("a population file holds more rows than the staging tool accepts", lambda s: _changed(
            s, populations=_one_oversized_population)),
        ("a population file is empty", lambda s: _changed(s, populations=_first_population_emptied)),
        ("a population file does not say which population it is", lambda s: _changed(
            s, populations=lambda populations: tuple(
                (name, {**record, "population": record["population"] + 1}) if number == 1 else (name, record)
                for number, (name, record) in enumerate(populations, start=1)))),
        ("a population file is missing from the middle of the set", lambda s: _changed(
            s, populations=lambda populations: populations[:1] + populations[2:]))),
    "bodies_have_the_required_parts": (
        ("the known-wrong example is missing", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Known-wrong example\n", "\n## Another part\n"))),
        ("a listed source is not cited", lambda s: _changed(
            s, specifications=lambda rows: rows[0]["sources"].append("src/loop_engine/core/facets.py"))),
        ("the known-wrong example is a heading without text", lambda s: _changed(
            s, body=lambda text: re.sub(r"(\n## Known-wrong example\n).*?(\n## What to record\n)", r"\1\2", text,
                                        flags=re.DOTALL)))),
    "layers_kinds_effects_and_styles_are_declared": (
        ("an invented history item", lambda s: _changed(
            s, specifications=lambda rows: _set(rows[0], "layer", "runtime_history_solution"),
            items=lambda items: _set(_first_reference(items), "source_layer",
                                     "runtime_history_solution_intelligence"))),
        ("pure is declared as an effect to hold", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items), "declared_effects", [EFFECTS[0]]))),
        ("an unknown harness style", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items), "styles", ["some_other_harness"])))),
    "source_references_are_pinned": (
        ("a source reference has no revision", lambda s: _changed(
            s, items=lambda items: _set(_first_reference(items), "source_ref",
                                        _first_reference(items)["source_ref"].split("@")[0]))),
        ("the revision is abbreviated", lambda s: _changed(
            s, items=lambda items: _set(items, "source_revision", items["source_revision"][:7]))),
        ("the review sheet names a revision the record does not know", lambda s: _changed(
            s, review=lambda text: text.replace(f"revision `{s.items['source_revision'][:7]}`",
                                                "revision `0ddba11`", 1))),
        ("an earlier anchor revision is abbreviated in the record", lambda s: _changed(
            s, items=lambda items: _set(items, "previous_source_revisions",
                                        [items["previous_source_revisions"][0][:7]]))),
        ("the current revision is also listed as an earlier one", lambda s: _changed(
            s, items=lambda items: items["previous_source_revisions"].append(items["source_revision"]))),
        ("the review sheet names no revision at all", lambda s: _changed(
            s, review=lambda text: text.replace(s.items["source_revision"][:7], "an earlier commit")))),
    "cited_source_bytes_are_the_pinned_bytes": (
        ("a cited file in the tree is not the file the record pins", lambda s: _changed(
            s, items=lambda items: _set(items["source_digests"],
                                        sorted(items["source_digests"])[0], "0" * 64))),
        ("a cited source has no pinned digest", lambda s: _changed(
            s, items=lambda items: items["source_digests"].pop(sorted(items["source_digests"])[0]))),
        ("a digest is pinned for a file that no item cites", lambda s: _changed(
            s, items=lambda items: _set(items["source_digests"], "src/loop_engine/core/facets.py", "0" * 64))),
        ("the record pins no digests at all", lambda s: _changed(
            s, items=lambda items: _set(items, "source_digests", None)))),
    "model_generated_material_is_bounded": (
        ("a row that the source does not hold", lambda s: _changed(
            s, items=lambda items: _generated(items)["provenance"]["model_generated_row_digests"].append("f" * 16))),
        ("model generated rows are hidden", lambda s: _changed(
            s, items=lambda items: _set(_generated(items)["provenance"], "model_generated_row_digests", [])))),
    "the_review_sheet_lists_every_item": (
        ("an item is missing from the review table", lambda s: _changed(
            s, review=lambda text: "\n".join(line for line in text.splitlines()
                                             if "(bodies/normalize_phone_numbers.md)" not in line))),
        ("the sheet is silent about the empty layers", lambda s: _changed(
            s, review=lambda text: text.replace(EMPTY_LAYERS[1], "the fourth layer")))),
    "the_catalogue_is_large_enough": (
        ("only a handful of items", lambda s: _changed(
            s, specifications=lambda rows: rows.__delitem__(slice(MINIMUM_ITEMS - 1, None)))),),
    "quoted_examples_reproduce": (
        ("a body quotes a value the code does not produce", lambda s: _changed(
            s, examples=lambda rows: _set(_capitalisation_example(rows)["expect"], "output", "iPhone Repair"))),
        ("a body quotes a confidence the code does not produce", lambda s: _changed(
            s, examples=lambda rows: _set(_capitalisation_example(rows)["expect"], "confidence", 0.8))),
        ("an executed example is not in its body word for word", lambda s: _changed(
            s, examples=lambda rows: _set(rows[0], "quote", "`2026-09-18` becomes `9-9-9`"))),
        ("an executed example names a function that is not there", lambda s: _changed(
            s, examples=lambda rows: _set(rows[0], "function", "induce_patterns"))),
        ("an executed example names an item without a body", lambda s: _changed(
            s, examples=lambda rows: _set(rows[0], "identity", "a_name_with_no_body"))),
        ("the executed examples are thinned out", lambda s: _changed(
            s, examples=lambda rows: rows.__delitem__(slice(1, None)))),
        ("an executed example runs code that its own item does not cite", _without_the_first_examples_source),
        ("an executed example is listed under another item", lambda s: _changed(
            s, examples=lambda rows: rows.append(_foreign_module_row(s)))),
        ("an executed example calls a function that its own item does not name", lambda s: _changed(
            s, examples=lambda rows: rows[0].update(function="whitespace_normalize", arguments=["a  b"],
                                                    keywords={}, expect={"output": "a b"}))),
        ("an executed example asserts nothing", lambda s: _changed(
            s, examples=lambda rows: _set(rows[0], "expect", {}))),
        ("an executed example names a field that the result does not have", lambda s: _changed(
            s, examples=lambda rows: _set(rows[0], "expect", {"no_such_field": None}))),
        ("the record type is not the supported one", lambda s: replace(
            s, examples={**s.examples, "record_type": "starter_catalogue_executed_examples/v2"}))),
    "bodies_list_the_quotations_no_example_proves": (
        ("a body gains a value that no executed example proves", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Checks\n", "\nThe call returns `41.7 seconds`.\n\n## Checks\n"))),
        ("an item lists a quotation that its body does not carry", lambda s: _changed(
            s, items=lambda items: items["items"][0]["provenance"]["unexecuted_quotations"].append("never_written"))),
        ("an item does not list its quotations at all", lambda s: _changed(
            s, items=lambda items: _set(items["items"][0]["provenance"], "unexecuted_quotations", None))),
        ("an executed example is dropped, so the value it proved is no longer proven", lambda s: _changed(
            s, examples=_without_the_capitalisation_examples))),
}


class StarterCatalogueChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = load_snapshot()

    def test_the_committed_catalogue_passes_every_rule(self):
        self.assertEqual(problems(self.snapshot), {})
        self.assertGreaterEqual(len(self.snapshot.rows()), MINIMUM_ITEMS)

    def test_every_rule_has_a_known_wrong_case(self):
        self.assertEqual(set(KNOWN_WRONG), set(RULES))

    def test_a_removed_rule_fails_its_named_check(self):
        """The mutant control: with one rule patched away, its own named check must fail."""
        for name, cases in KNOWN_WRONG.items():
            check = f"test_{name}_rejects_its_known_wrong_cases"
            with self.subTest(rule=name):
                intact = unittest.TestResult()
                StarterCatalogueChecks(check).run(intact)
                self.assertTrue(intact.wasSuccessful() and intact.testsRun == 1)
                with mock.patch.dict(RULES, {name: lambda snapshot: []}):
                    mutant = unittest.TestResult()
                    StarterCatalogueChecks(check).run(mutant)
                self.assertEqual(len(mutant.failures), len(cases), f"{check} survived the removal of {name}")
                self.assertEqual(mutant.errors, [])

    def test_the_staging_tool_refuses_the_whole_catalogue_as_one_population(self):
        """The bound is an asserted fact, not a number this file repeats.

        The combined record of every committed population holds more rows than one
        population may hold, so the staging tool refuses it by name. This is why the
        catalogue is committed as population files instead of as one file.
        """
        combined = self.snapshot.specifications
        self.assertGreater(len(combined["specifications"]), STAGING_POPULATION)
        with self.assertRaises(ValueError) as refusal:
            compile_candidates(combined, CandidateStageRequest(ROOT, NAMESPACE))
        self.assertEqual(str(refusal.exception), POPULATION_REFUSAL)
        # The same refusal for an empty population, so the bound is proven at both ends.
        with self.assertRaises(ValueError) as empty:
            compile_candidates({**combined, "specifications": []}, CandidateStageRequest(ROOT, NAMESPACE))
        self.assertEqual(str(empty.exception), POPULATION_REFUSAL)
        # Every committed file stays inside the bound and is accepted as it stands.
        for name, record in self.snapshot.populations:
            with self.subTest(population=name):
                self.assertLessEqual(len(record["specifications"]), STAGING_POPULATION)
                self.assertEqual(len(compile_candidates(record, CandidateStageRequest(ROOT, NAMESPACE))),
                                 len(record["specifications"]))

    def test_the_refresh_tool_and_this_check_name_the_same_population_files(self):
        """One contract for the committed population files, so the two tools cannot drift apart."""
        refresh = _refresh_module()
        self.assertEqual(
            (refresh.SPECIFICATIONS_PREFIX, refresh.SPECIFICATIONS_GLOB, refresh.SPECIFICATIONS_RECORD_TYPE,
             refresh.POPULATION_SIZE),
            (SPECIFICATIONS_PREFIX, SPECIFICATIONS_GLOB, SPECIFICATIONS_RECORD_TYPE, STAGING_POPULATION))
        self.assertEqual([name for name, _record in self.snapshot.populations],
                         refresh.population_names(CATALOGUE))

    def test_the_specification_stages_and_review_search_finds_every_item(self):
        request = CandidateStageRequest(ROOT, NAMESPACE, True)
        records, refusals = compile_every_population(self.snapshot.populations, request)
        self.assertEqual(refusals, [])
        self.assertEqual(len(records), len(self.snapshot.rows()))
        with tempfile.TemporaryDirectory() as directory:
            with closing(SQLiteRecordStore(str(Path(directory) / "candidates.db"))) as store:
                self.assertTrue(stage_candidates(store, records, request).committed)
        review = review_search(records)
        self.assertEqual(review["normal_search_hits"], 0)
        self.assertEqual(review["normal_search_excluded"], len(records))
        self.assertTrue(all(probe["found_in_first_three"] for probe in review["probes"]))
        self.assertEqual(sum(probe["physical_model_calls"] for probe in review["probes"]), 0)

    def _manifest(self, directory: Path, artifact_root: Path, items, name: str = "manifest.json") -> Path:
        manifest = {"record_type": MANIFEST_VERSION, "artifact_root": str(artifact_root), "items": [
            {"reference": item["reference"], "body_path": item["body_path"],
             "approval_ref": "test_only:not_an_owner_approval", "grants": []}
            for item in items]}
        path = directory / name
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def _licence_partition(self):
        """The items the default host licence policy accepts, and the ones it refuses with the refusal code.

        The partition is read from the engine's own policy, so it follows the
        policy rather than repeating it. No policy that accepts a state such as
        `unknown` is ever built here; the conservative default decides.
        """
        accepted, refused = [], []
        for item in self.snapshot.items["items"]:
            code = DEFAULT_LICENSE_POLICY.refusal(item["reference"]["license"])
            (refused if code else accepted).append((item, code))
        return [item for item, _code in accepted], refused

    def test_the_items_the_host_licence_policy_accepts_load_through_the_manifest_reader(self):
        accepted, refused = self._licence_partition()
        # The catalogue's own record of each licence state and the engine's policy agree.
        self.assertEqual([item["reference"]["identity"] for item, _code in refused],
                         [item["reference"]["identity"] for item in self.snapshot.items["items"]
                          if item["license_state"] != "declared"])
        self.assertEqual(len(accepted) + len(refused), len(self.snapshot.items["items"]))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            catalogue, _resolver, read, grants = load_host_manifest(
                self._manifest(folder, CATALOGUE.resolve(), accepted))
            self.assertEqual(list(catalogue.items), [item["reference"]["identity"] for item in accepted])
            self.assertEqual(set(catalogue.items) & {item["reference"]["identity"] for item, _code in refused}, set())
            self.assertEqual(grants, {})
            first = next(iter(catalogue.items.values()))
            self.assertEqual(read(first).encode("utf-8"), self.snapshot.bodies[first.identity])
            copied = folder / "copy"
            shutil.copytree(CATALOGUE / "bodies", copied / "bodies")
            target = copied / "bodies" / f"{first.identity}.md"
            target.write_bytes(target.read_bytes().replace(b"a", b"b", 1))
            with self.assertRaises(ServiceRuntimeError):
                load_host_manifest(self._manifest(folder, copied, accepted))

    def test_an_item_without_an_accepted_licence_is_refused_by_name(self):
        """The behaviour a customer depends on: an item this host may not serve never reaches the catalogue."""
        accepted, refused = self._licence_partition()
        self.assertEqual([item["reference"]["identity"] for item, _code in refused], list(LICENCE_REFUSED_ITEMS))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            for index, (item, code) in enumerate(refused):
                identity = item["reference"]["identity"]
                with self.subTest(item=identity):
                    self.assertEqual(code, LICENSE_UNKNOWN)
                    path = self._manifest(folder, CATALOGUE.resolve(), accepted + [item], f"refused_{index}.json")
                    with self.assertRaises(ServiceRuntimeError) as refusal:
                        load_host_manifest(path)
                    self.assertEqual(refusal.exception.code, LICENSE_UNKNOWN)
                    self.assertIn(identity, str(refusal.exception))
            # A control that cannot become empty: the licence of an accepted item is
            # replaced by each value a host must refuse, and the refusal names its code.
            for index, (licence, code) in enumerate(UNACCEPTABLE_LICENCES):
                with self.subTest(licence=licence):
                    changed = deepcopy(accepted[0])
                    changed["reference"]["license"] = licence
                    path = self._manifest(folder, CATALOGUE.resolve(), [changed], f"licence_{index}.json")
                    with self.assertRaises(ServiceRuntimeError) as refusal:
                        load_host_manifest(path)
                    self.assertEqual(refusal.exception.code, code)
                    self.assertIn(changed["reference"]["identity"], str(refusal.exception))

    def _cited_tree(self, directory: str) -> Path:
        """A tree that holds only the cited files, at their own paths, copied from this repository."""
        root = Path(directory).resolve() / "tree"
        for source in self.snapshot.items["source_digests"]:
            target = root / source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / source).read_bytes())
        return root

    def test_the_pinned_digests_are_read_from_the_tree_and_not_from_the_record(self):
        """The known-wrong tree: one cited file is edited, and the rule names that file.

        The rule hashes the files of the repository it is given, so a copy of the
        cited files with one byte changed must be reported. Without this the rule
        could be comparing the record with itself.
        """
        rule = RULES["cited_source_bytes_are_the_pinned_bytes"]
        with tempfile.TemporaryDirectory() as directory:
            root = self._cited_tree(directory)
            self.assertEqual(rule(replace(self.snapshot, repository=root)), [])
            edited = sorted(self.snapshot.items["source_digests"])[0]
            (root / edited).write_bytes((root / edited).read_bytes() + b"\n# one more line\n")
            found = rule(replace(self.snapshot, repository=root))
            self.assertEqual(len(found), 1)
            self.assertIn(edited, found[0])
            # A cited file that is missing from the tree is reported as well, not passed over.
            (root / edited).unlink()
            self.assertIn("is not a file of this repository", " ".join(rule(replace(self.snapshot, repository=root))))

    def test_the_anchor_tool_refuses_a_revision_whose_cited_bytes_differ(self):
        """Anchoring reads each cited file at the named revision before it writes anything."""
        refresh = _refresh_module()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve() / "starter-catalogue"
            shutil.copytree(CATALOGUE, folder, ignore=shutil.ignore_patterns("__pycache__"))
            before = (folder / "items.json").read_bytes()
            revision = self.snapshot.items["source_revision"]
            self.assertFalse(refresh.anchor(refresh.AnchorRequest(folder, ROOT, revision))["written"])
            with self.assertRaises(refresh.CatalogueRefreshError):
                refresh.anchor(refresh.AnchorRequest(folder, ROOT, "0" * 40, True))
            with self.assertRaisesRegex(refresh.CatalogueRefreshError, "forty character revision"):
                refresh.anchor(refresh.AnchorRequest(folder, ROOT, revision[:7], True))
            self.assertEqual((folder / "items.json").read_bytes(), before)

    def test_the_refresh_tool_reports_and_repairs_a_stale_body(self):
        refresh = _refresh_module()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve() / "starter-catalogue"
            shutil.copytree(CATALOGUE, folder)
            self.assertEqual(refresh.refresh(refresh.RefreshRequest(folder))["stale"], [])
            identity = self.snapshot.rows()[0][0]["id"]
            with (folder / "bodies" / f"{identity}.md").open("a", encoding="utf-8") as stream:
                stream.write("One more sentence.\n")
            report = refresh.refresh(refresh.RefreshRequest(folder))
            self.assertEqual((report["stale"], report["written"]), ([identity], False))
            self.assertIn("digests_and_sizes_match_the_bodies", problems(load_snapshot(folder)))
            self.assertTrue(refresh.refresh(refresh.RefreshRequest(folder, True))["written"])
            self.assertNotIn("digests_and_sizes_match_the_bodies", problems(load_snapshot(folder)))
            (folder / "items.json").write_text(json.dumps({"record_type": "another_record/v1"}), encoding="utf-8")
            with self.assertRaises(refresh.CatalogueRefreshError):
                refresh.refresh(refresh.RefreshRequest(folder, True))

    def _stale_copy(self, directory: str) -> tuple[Path, Path]:
        folder = Path(directory).resolve() / "starter-catalogue"
        shutil.copytree(CATALOGUE, folder, ignore=shutil.ignore_patterns("__pycache__"))
        body = folder / "bodies" / f"{self.snapshot.rows()[0][0]['id']}.md"
        with body.open("a", encoding="utf-8") as stream:
            stream.write("One more sentence.\n")
        return folder, body

    def test_the_refresh_tool_refuses_a_leftover_temporary_file_and_keeps_it(self):
        refresh = _refresh_module()
        with tempfile.TemporaryDirectory() as directory:
            folder, _body = self._stale_copy(directory)
            names = [name for name, _record in self.snapshot.populations] + ["items.json"]
            before = {name: (folder / name).read_bytes() for name in names}
            leftover = folder / ("items.json" + refresh.TEMPORARY_SUFFIX)
            leftover.write_text("left by an interrupted write", encoding="utf-8")
            with self.assertRaisesRegex(refresh.CatalogueRefreshError, "interrupted write"):
                refresh.refresh(refresh.RefreshRequest(folder, True))
            # Neither record changed, the file of the other run is kept, and this run's own file is gone.
            self.assertEqual(before, {name: (folder / name).read_bytes() for name in before})
            self.assertEqual(leftover.read_text(encoding="utf-8"), "left by an interrupted write")
            for name in names[:-1]:
                self.assertFalse((folder / (name + refresh.TEMPORARY_SUFFIX)).exists())
            leftover.unlink()
            self.assertTrue(refresh.refresh(refresh.RefreshRequest(folder, True))["written"])
            self.assertEqual(problems(load_snapshot(folder)).get("digests_and_sizes_match_the_bodies"), None)

    def _plant_link(self, folder: Path, relative: str, outside: Path) -> Path:
        """Move one part of a copied catalogue outside the folder and leave a link in its place."""
        target, moved = folder / relative, outside / Path(relative).name
        outside.mkdir(parents=True, exist_ok=True)
        target.rename(moved)
        target.symlink_to(moved, target_is_directory=moved.is_dir())
        return moved

    def test_the_refresh_tool_refuses_a_planted_symbolic_link(self):
        """Path confinement: a link in place of a record, the bodies folder or one body is refused."""
        refresh = _refresh_module()
        identity = self.snapshot.rows()[0][0]["id"]
        planted = ["items.json", "bodies", f"bodies/{identity}.md"]
        planted += [name for name, _record in self.snapshot.populations]
        for relative in planted:
            with self.subTest(planted=relative), tempfile.TemporaryDirectory() as directory:
                folder, _body = self._stale_copy(directory)
                moved = self._plant_link(folder, relative, Path(directory).resolve() / "outside")
                before = sorted((path.relative_to(moved).as_posix(), path.read_bytes())
                                for path in (moved.rglob("*") if moved.is_dir() else [moved]) if path.is_file())
                with self.assertRaises(refresh.CatalogueRefreshError):
                    refresh.refresh(refresh.RefreshRequest(folder, True))
                # Nothing was written through the link, so the material outside the folder is untouched.
                self.assertEqual(before, sorted((path.relative_to(moved).as_posix(), path.read_bytes())
                                                for path in (moved.rglob("*") if moved.is_dir() else [moved])
                                                if path.is_file()))

    def test_the_refresh_tool_gives_a_typed_refusal_for_unreadable_files(self):
        refresh = _refresh_module()
        with tempfile.TemporaryDirectory() as directory:
            folder, body = self._stale_copy(directory)
            body.write_bytes(b"\xff\xfe not text")
            with self.assertRaisesRegex(refresh.CatalogueRefreshError, "UTF-8"):
                refresh.refresh(refresh.RefreshRequest(folder))
        with tempfile.TemporaryDirectory() as directory:
            folder, _body = self._stale_copy(directory)
            (folder / "items.json").write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(refresh.CatalogueRefreshError, "valid JSON"):
                refresh.refresh(refresh.RefreshRequest(folder))

    def test_purposes_answer_plain_queries_the_way_the_hosted_search_reads_them(self):
        record = json.loads((CATALOGUE / QUERIES_FILE).read_text(encoding="utf-8"))
        self.assertEqual(record.get("record_type"), QUERIES_RECORD_TYPE)
        queries = {row["query"]: row["expected"] for row in record["queries"]}
        self.assertGreaterEqual(len(queries), MINIMUM_QUERIES)
        self.assertLessEqual(set(queries.values()), {row["id"] for row, _item in self.snapshot.rows()})
        self.assertIn("reviewer", {row["written_by"] for row in record["queries"]})

        def first_three(items, query):
            records = [StoreRecord(row["reference"]["identity"], "context", row["reference"]["purpose"], body={
                "description": row["reference"]["purpose"],
                "keywords": [row["reference"]["identity"], row["reference"]["kind"], row["reference"]["source_layer"]]})
                for row in items]
            return [hit["record_id"] for hit in Retriever(records).search(query, mode="lexical", top_n=3)["hits"]]

        for query, expected in queries.items():
            with self.subTest(query=query):
                self.assertIn(expected, first_three(self.snapshot.items["items"], query))
        vague = deepcopy(self.snapshot.items["items"])
        for row in vague:
            row["reference"]["identity"], row["reference"]["purpose"] = f"item_{vague.index(row)}", "Reviewed material"
        self.assertEqual(first_three(vague, "is my model overfitting"), [])


def _known_wrong_check(name):
    def check(self):
        for label, make in KNOWN_WRONG[name]:
            with self.subTest(case=label):
                found = problems(make(self.snapshot))
                self.assertIn(name, found, f"the rule {name} did not report: {label}")
    return check


for _name in RULES:
    setattr(StarterCatalogueChecks, f"test_{_name}_rejects_its_known_wrong_cases", _known_wrong_check(_name))


if __name__ == "__main__":
    unittest.main()
