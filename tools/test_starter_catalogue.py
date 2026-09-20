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
from loop_engine.core.facets import EFFECTS
from loop_engine.core.harness_intelligence import KINDS, RECORD_TYPE as ITEM_RECORD_TYPE
from loop_engine.core.instance_instructions import STYLE_FILES
from loop_engine.core.intelligence_tagging import RECORD_TYPE as TAG_RECORD_TYPE
from loop_engine.core.retrieval import Retriever
from loop_engine.core.service_runtime.http_entrypoint import MANIFEST_VERSION, load_host_manifest
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from loop_engine.core.store_serve import StoreRecord
from tools.stage_intelligence_candidates import (
    CandidateStageRequest, compile_candidates, review_search, stage_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue"
NAMESPACE = "starter.catalogue"
MINIMUM_ITEMS, MINIMUM_WORDS, MAXIMUM_WORDS, MAXIMUM_MODEL_GENERATED_ROWS = 40, 150, 600, 8
IDENTITY = re.compile(r"[a-z][a-z0-9_]{2,79}")
#: The two layers that can hold compiled material today. The other two canonical
#: layers need real runs and real feedback, so an item there would be invented.
LAYERS = {"context": "context_intelligence", "code": "code_intelligence"}
MODEL_GENERATED_SOURCE = "src/loop_engine/governance/candidates/part-00000.jsonl"
LICENCE_STATES = {"declared": ("MIT", "assistant_authored_from_repository_sources", "Licence: MIT."),
                  "needs_review": ("unknown", "assistant_compiled_from_model_generated_candidates",
                                   "Licence state: needs review.")}
REVIEW_LICENCE = {"declared": "MIT, declared", "needs_review": "unknown, needs review"}
REVIEW_LAYER = {"context_intelligence": "Context Intelligence", "code_intelligence": "Code Intelligence"}
EMPTY_LAYERS = ("Runtime History and Solution Intelligence", "User Feedback Intelligence")
REQUIRED_PARTS = ("## When to use it", "## Steps", "## Checks", "## Known-wrong example",
                  "## What to record", "## Source")
ITEM_FIELDS = {"reference", "body_path", "lifecycle", "license_state", "provenance"}
#: The two dash characters that public prose never uses, written as code points
#: so that this source file stays free of them.
DASHES = "[" + chr(0x2014) + chr(0x2013) + "]"
def _patterns(*patterns):
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


#: Internal runtime vocabulary that a customer-facing body, title, purpose or tag never uses.
#: Cited source paths are removed before a body is read, because a path is not wording.
INTERNAL_VOCABULARY = _patterns(
    r"(?<![a-z0-9])loops?(?![a-z0-9])", r"(?<![a-z0-9])practitioners?(?![a-z0-9])",
    r"role[\s_-]+profiles?", r"runtime[\s_-]+classification", r"solution[\s_-]+canvas", r"code[\s_-]+nodes?")
#: The retired public language and the dash characters that continuous integration
#: refuses in every published document, so they also apply to the review sheet.
RETIRED_PUBLIC_LANGUAGE = _patterns(
    r"(?<![a-z0-9])child(?:ren)?(?![a-z0-9])", DASHES, r"stop[\s_-]+conditions?",
    r"(?<![a-z0-9])receipts?(?![a-z0-9])", r"(?<![a-z0-9])chronicles?(?![a-z0-9])",
    r"what[\s_-]*is[\s_-]*next|what[\s_-]+next|whats[\s_-]*next")
FORBIDDEN = INTERNAL_VOCABULARY + RETIRED_PUBLIC_LANGUAGE
REVIEW_FORBIDDEN = RETIRED_PUBLIC_LANGUAGE


@dataclass(frozen=True)
class CatalogueSnapshot:
    """Everything the rules read, held in memory so a known-wrong copy is cheap."""

    specifications: dict
    items: dict
    bodies: dict
    review: str
    repository: Path

    def rows(self):
        return list(zip(self.specifications.get("specifications") or (), self.items.get("items") or ()))


def load_snapshot(folder: Path = CATALOGUE) -> CatalogueSnapshot:
    bodies = {path.stem: path.read_bytes() for path in sorted((folder / "bodies").iterdir())}
    return CatalogueSnapshot(json.loads((folder / "specifications.json").read_text(encoding="utf-8")),
                             json.loads((folder / "items.json").read_text(encoding="utf-8")), bodies,
                             (folder / "REVIEW.md").read_text(encoding="utf-8"), ROOT)


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
        licence, authoring, sentence = LICENCE_STATES[state]
        generated = MODEL_GENERATED_SOURCE in (row.get("sources") or ())
        if item.get("reference", {}).get("license") != licence:
            found.append(f"{identity}: the licence must be {licence!r} in the state {state!r}")
        if generated != (state == "needs_review"):
            found.append(f"{identity}: model generated material needs review, and only such material")
        if (item.get("provenance") or {}).get("authoring") != authoring:
            found.append(f"{identity}: the provenance does not say how the body was authored")
        if sentence not in snapshot.bodies.get(identity, b"").decode("utf-8"):
            found.append(f"{identity}: the body does not state its licence")
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
                 " ".join(map(str, row.get("tags") or ()))]
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


def rule_specification_loads_through_the_staging_tool(snapshot):
    try:
        records = compile_candidates(snapshot.specifications, CandidateStageRequest(snapshot.repository, NAMESPACE))
    except ValueError as error:
        return [f"the staging tool refuses the specification: {error}"]
    found = []
    if len(records) != len(snapshot.specifications["specifications"]):
        found.append("the staging tool did not compile one record for each row")
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


RULES = {function.__name__[5:]: function for function in (
    rule_identities_are_unique, rule_digests_and_sizes_match_the_bodies, rule_every_item_carries_a_licence,
    rule_every_item_is_a_candidate, rule_no_forbidden_vocabulary, rule_bodies_stay_in_the_word_range,
    rule_specification_loads_through_the_staging_tool, rule_bodies_have_the_required_parts,
    rule_layers_kinds_effects_and_styles_are_declared, rule_source_references_are_pinned,
    rule_model_generated_material_is_bounded, rule_the_review_sheet_lists_every_item,
    rule_the_catalogue_is_large_enough)}


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


def _changed(snapshot, *, specifications=None, items=None, body=None, review=None):
    """A deep copy with one deliberate defect; the committed files are never touched."""
    new_specifications, new_items = deepcopy(snapshot.specifications), deepcopy(snapshot.items)
    bodies = dict(snapshot.bodies)
    if specifications:
        specifications(new_specifications["specifications"])
    if items:
        items(new_items)
    if body:
        identity = new_specifications["specifications"][0]["id"]
        bodies[identity] = body(bodies[identity].decode("utf-8")).encode("utf-8")
    return replace(snapshot, specifications=new_specifications, items=new_items, bodies=bodies,
                   review=snapshot.review if review is None else review(snapshot.review))


def _generated(items):
    return next(item for item in items["items"] if item["license_state"] == "needs_review")


def _set(target, key, value):
    target[key] = value


def _first_reference(items):
    return items["items"][0]["reference"]


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
                                    _set(_generated(items)["reference"], "license", "MIT"))))),
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
            s, body=lambda text: text + f"A pause {chr(0x2014)} then more.\n"))),
    "bodies_stay_in_the_word_range": (
        ("a body is one sentence long", lambda s: _changed(s, body=lambda text: "# Short\n\nOne sentence only.\n")),
        ("a body is an essay", lambda s: _changed(s, body=lambda text: text + "more words " * 400 + "\n"))),
    "specification_loads_through_the_staging_tool": (
        ("a row carries a field the staging tool does not accept", lambda s: _changed(
            s, specifications=lambda rows: _set(rows[0], "license", "MIT"))),
        ("a row claims to be active", lambda s: _changed(
            s, specifications=lambda rows: _set(rows[0], "lifecycle", "active"))),
        ("a source is not a file in the repository", lambda s: _changed(
            s, specifications=lambda rows: _set(rows[0], "sources", ["src/loop_engine/no_such_file.py"])))),
    "bodies_have_the_required_parts": (
        ("the known-wrong example is missing", lambda s: _changed(
            s, body=lambda text: text.replace("\n## Known-wrong example\n", "\n## Another part\n"))),
        ("a listed source is not cited", lambda s: _changed(
            s, specifications=lambda rows: rows[0]["sources"].append("src/loop_engine/core/facets.py")))),
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
            s, items=lambda items: _set(items, "source_revision", items["source_revision"][:7])))),
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

    def test_the_specification_stages_and_review_search_finds_every_item(self):
        request = CandidateStageRequest(ROOT, NAMESPACE, True)
        records = compile_candidates(self.snapshot.specifications, request)
        with tempfile.TemporaryDirectory() as directory:
            with closing(SQLiteRecordStore(str(Path(directory) / "candidates.db"))) as store:
                self.assertTrue(stage_candidates(store, records, request).committed)
        review = review_search(records)
        self.assertEqual(review["normal_search_hits"], 0)
        self.assertEqual(review["normal_search_excluded"], len(records))
        self.assertTrue(all(probe["found_in_first_three"] for probe in review["probes"]))
        self.assertEqual(sum(probe["physical_model_calls"] for probe in review["probes"]), 0)

    def _manifest(self, directory: Path, artifact_root: Path) -> Path:
        manifest = {"record_type": MANIFEST_VERSION, "artifact_root": str(artifact_root), "items": [
            {"reference": item["reference"], "body_path": item["body_path"],
             "approval_ref": "test_only:not_an_owner_approval", "grants": []}
            for item in self.snapshot.items["items"]]}
        path = directory / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_the_items_load_through_the_host_manifest_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            catalogue, _resolver, read, grants = load_host_manifest(self._manifest(folder, CATALOGUE.resolve()))
            self.assertEqual(list(catalogue.items), [row["id"] for row, _item in self.snapshot.rows()])
            self.assertEqual(grants, {})
            first = next(iter(catalogue.items.values()))
            self.assertEqual(read(first).encode("utf-8"), self.snapshot.bodies[first.identity])
            copied = folder / "copy"
            shutil.copytree(CATALOGUE / "bodies", copied / "bodies")
            target = copied / "bodies" / f"{first.identity}.md"
            target.write_bytes(target.read_bytes().replace(b"a", b"b", 1))
            with self.assertRaises(ServiceRuntimeError):
                load_host_manifest(self._manifest(folder, copied))

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

    def test_purposes_answer_plain_queries_the_way_the_hosted_search_reads_them(self):
        queries = {"remove duplicate customers from a contact export": "find_duplicate_records_with_blocking_keys",
                   "names are in all caps fix the casing": "restore_capitalisation_of_names",
                   "fix typos in email domains": "normalize_and_recover_email_addresses",
                   "is my model overfitting": "read_the_train_validation_gap",
                   "the agent keeps retrying the same failing fix": "diagnose_a_stall_and_change_strategy",
                   "make my data pipeline idempotent": "make_a_data_pipeline_safe_to_run_again"}

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
