"""Checks for the candidate pack that covers the two thin intelligence layers.

The pack lives in ``artifacts/intelligence-layer-coverage-2026-09-21/pack``.
It adds material to Runtime History and Solution Intelligence and to User
Feedback Intelligence, which hold nothing in the built-in population.

Every rule here has a known-wrong case. A mutated copy of the pack must be
reported by the rule's own name, so a rule that stops rejecting the behaviour
it exists to prevent fails these checks rather than passing quietly.

    PYTHONPATH=src:tools python -m unittest tools.test_intelligence_layer_coverage
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from loop_engine.core.harness_intelligence import (
    HarnessIntelligenceCatalogue, HarnessIntelligenceError, HarnessIntelligenceItem)
from loop_engine.core.intelligence_tagging import TagSet
from loop_engine.core.retrieval import Retriever
from loop_engine.core.service_runtime.http_entrypoint import (
    DEFAULT_ACCEPTED_LICENSES, REVIEW_LICENSE_MARKERS, UNKNOWN_LICENSE_MARKERS)
from loop_engine.core.store_serve import StoreRecord
from loop_engine.core.user_feedback_intelligence import (
    GUIDANCE_TYPES, SCOPES, STRENGTHS, TIMINGS)

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "artifacts" / "intelligence-layer-coverage-2026-09-21" / "pack"
ITEMS_RECORD_TYPE = "layer_coverage_candidate_items/v1"
QUERIES_RECORD_TYPE = "layer_coverage_search_queries/v1"
SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v1"
SOURCE_TREE_RECORD_TYPE = "layer_coverage_source_tree/v1"
#: The two layers this pack exists to fill.
COVERED_LAYERS = ("runtime_history_solution_intelligence", "user_feedback_intelligence")
#: The pack is worth shipping only if it carries real material in both layers.
MINIMUM_PER_LAYER = 5
MINIMUM_QUERIES = 30
#: The author wrote the queries against purposes the author also wrote, so the
#: reviewer-written queries carry the evidence. They get their own floor, and
#: so does the record of which queries missed before a purpose was widened,
#: because a suite that can drop either one stops proving what it claims.
MINIMUM_REVIEWER_QUERIES = 10
MINIMUM_RECORDED_MISSES = 5
TOP_N = 3
#: A User Feedback body states its guidance in a small table. Each of these
#: rows must carry a value from the owning module's closed vocabulary, so a
#: table that looks typed is typed. Prose belongs on a separate note row.
GUIDANCE_FIELD_VOCABULARY = {
    "Guidance type": GUIDANCE_TYPES,
    "Scope": SCOPES,
    "Strength": STRENGTHS,
    "Timing": TIMINGS,
}
USER_FEEDBACK_LAYER = "user_feedback_intelligence"


def _read(name: str) -> dict:
    return json.loads(PACK.joinpath(name).read_bytes().decode("utf-8"))


def guidance_fields(body: str) -> dict:
    """The declared value of each guidance row, exactly as the body writes it.

    A row is read only in its backticked form. Prose in the row is not a value
    and is reported as one that is not in the vocabulary.
    """
    found: dict = {}
    for line in body.split("\n"):
        parts = [cell.strip() for cell in line.split("|")]
        if len(parts) == 4 and parts[1] in GUIDANCE_FIELD_VOCABULARY:
            value = parts[2]
            found[parts[1]] = (value[1:-1] if value.startswith("`")
                               and value.endswith("`") and len(value) > 2
                               else value)
    return found


class Snapshot:
    """One readable copy of the pack, so a rule can be run against a mutant."""

    def __init__(self, items: dict, specifications: dict, bodies: dict,
                 queries: dict, source_tree: dict):
        self.items, self.specifications, self.bodies = items, specifications, bodies
        self.queries, self.source_tree = queries, source_tree

    @classmethod
    def load(cls) -> "Snapshot":
        items = _read("items.json")
        specifications = _read("specifications.json")
        bodies = {path.name: path.read_bytes().decode("utf-8")
                  for path in sorted((PACK / "bodies").iterdir())}
        return cls(items, specifications, bodies, _read("search-queries.json"),
                   _read("source-tree.json"))

    def copy(self) -> "Snapshot":
        return Snapshot(deepcopy(self.items), deepcopy(self.specifications),
                        dict(self.bodies), deepcopy(self.queries),
                        deepcopy(self.source_tree))

    def rows(self):
        return self.items.get("items", [])

    def query_rows(self):
        return self.queries.get("queries", [])


def _digest_matches_its_body(snapshot: Snapshot) -> list:
    """Every digest and size is the measured body, recomputed here independently."""
    found = []
    for row in snapshot.rows():
        body = snapshot.bodies.get(Path(row.get("body_path", "")).name)
        if body is None:
            found.append(row["reference"]["identity"])
            continue
        encoded = body.encode("utf-8")
        if (row["reference"]["digest"] != hashlib.sha256(encoded).hexdigest()
                or row["reference"]["size_bytes"] != len(encoded)):
            found.append(row["reference"]["identity"])
    return found


def _specification_text_equals_its_body(snapshot: Snapshot) -> list:
    """The staged text and the shipped body are one body, never two that drift."""
    bodies = {row["reference"]["identity"]:
              snapshot.bodies.get(Path(row.get("body_path", "")).name)
              for row in snapshot.rows()}
    return [row["id"] for row in snapshot.specifications.get("specifications", [])
            if bodies.get(row["id"]) != row.get("text")]


def _reference_loads_through_the_engine_contract(snapshot: Snapshot) -> list:
    """Each reference rebuilds into a typed item that the catalogue accepts."""
    found, catalogue = [], HarnessIntelligenceCatalogue()
    for row in snapshot.rows():
        reference = row["reference"]
        try:
            catalogue.register(HarnessIntelligenceItem(
                reference["identity"], reference["kind"], reference["purpose"],
                reference["digest"], reference["source_layer"],
                reference["source_ref"], reference["size_bytes"],
                reference["license"], tuple(reference["declared_effects"]),
                tuple(reference["styles"]), reference["exposure"],
                reference["availability"],
                family=reference.get("family", ""),
                tags=TagSet({key: value for key, value in reference["tags"].items()
                        if key != "record_type"})))
        except (HarnessIntelligenceError, KeyError, TypeError):
            found.append(reference.get("identity", "<unreadable>"))
    return found


def _both_thin_layers_are_covered(snapshot: Snapshot) -> list:
    """The pack exists to fill two layers. One layer filled is half the work."""
    held = {layer: sum(1 for row in snapshot.rows()
                       if row["reference"]["source_layer"] == layer)
            for layer in COVERED_LAYERS}
    outside = {row["reference"]["source_layer"] for row in snapshot.rows()
               } - set(COVERED_LAYERS)
    return ([layer for layer, count in held.items() if count < MINIMUM_PER_LAYER]
            + sorted(outside))


def _licence_is_one_the_default_host_accepts(snapshot: Snapshot) -> list:
    """A state is not a licence, and a host may not accept one that is missing."""
    found = []
    for row in snapshot.rows():
        name = row["reference"].get("license", "")
        if (not name or name.lower() in UNKNOWN_LICENSE_MARKERS
                or name.lower() in REVIEW_LICENSE_MARKERS
                or name not in DEFAULT_ACCEPTED_LICENSES):
            found.append(row["reference"]["identity"])
    return found


def _every_item_is_an_unapproved_candidate(snapshot: Snapshot) -> list:
    """Nothing here is approved or published, and nothing here may say it is."""
    found = []
    if snapshot.items.get("publication") != "not_published":
        found.append("<pack header>")
    for row in snapshot.rows():
        approval = row.get("approval", {})
        if (row.get("lifecycle") != "candidate"
                or row["reference"]["tags"].get("lifecycle") != ["candidate"]
                or approval.get("approved") is not False
                or approval.get("approved_by") or approval.get("approval_ref")):
            found.append(row["reference"]["identity"])
    return found


def _every_item_declares_a_version_and_its_effects(snapshot: Snapshot) -> list:
    """A version and an effect list are required before an item can be active."""
    return [row["reference"]["identity"] for row in snapshot.rows()
            if not str(row.get("item_version", "")).strip()
            or not isinstance(row["reference"].get("declared_effects"), list)
            or row["reference"]["declared_effects"]
            or not str(row.get("license_state", "")).strip()]


def _provenance_names_a_revision_and_real_repository_sources(snapshot: Snapshot) -> list:
    """Every cited source is a file in the recorded revision, not in this tree.

    A citation is resolved through ``source-tree.json``, the listing of object
    names read out of ``source_revision`` itself. Existence in whatever tree
    the check happens to run in proves nothing about the revision an item is
    bound to: a file added after it would pass, and a file moved away from it
    would fail for a reason that has nothing to do with the item.
    """
    revision = snapshot.items.get("source_revision", "")
    listing = snapshot.source_tree
    if (listing.get("record_type") != SOURCE_TREE_RECORD_TYPE
            or listing.get("source_revision") != revision
            or not isinstance(listing.get("sources"), dict)):
        return ["<source tree>"]
    at_revision = listing["sources"]
    found = []
    for row in snapshot.rows():
        provenance = row.get("provenance", {})
        sources = provenance.get("repository_sources") or []
        confined = all(
            isinstance(source, str) and not Path(source).is_absolute()
            and ".." not in Path(source).parts
            and not any(part.startswith(".") for part in Path(source).parts)
            and source in at_revision for source in sources)
        if (not sources or not confined
                or provenance.get("source_revision") != revision
                or not str(provenance.get("authoring", "")).strip()
                or not row["reference"]["source_ref"].endswith("@" + revision)):
            found.append(row["reference"]["identity"])
    return found


def _guidance_fields_use_the_engine_vocabularies(snapshot: Snapshot) -> list:
    """A User Feedback body states its guidance in the engine's own values.

    ``user_feedback_intelligence`` refuses an unknown strength or timing at the
    store boundary. A body that a reviewer approves, or that a later change
    turns into an ``AdviceStore`` record, must not carry a field the store
    would reject, and a row that looks typed must not be free prose.
    """
    found = []
    for row in snapshot.rows():
        if row["reference"]["source_layer"] != USER_FEEDBACK_LAYER:
            continue
        identity = row["reference"]["identity"]
        body = snapshot.bodies.get(Path(row.get("body_path", "")).name)
        if body is None:
            found.append(identity)
            continue
        declared = guidance_fields(body)
        for field_name, vocabulary in GUIDANCE_FIELD_VOCABULARY.items():
            if declared.get(field_name) not in vocabulary:
                found.append(f"{identity}:{field_name}")
    return found


def _the_query_set_keeps_its_adversarial_record(snapshot: Snapshot) -> list:
    """The reviewer queries and the recorded misses both keep a floor.

    The author-written queries were written against purposes the same author
    wrote, so they are the weaker half of the evidence. Five reviewer queries
    missed on their first run and were kept, with the purpose widened rather
    than the query softened. Both facts have to survive an edit to this file.
    """
    rows = snapshot.query_rows()
    written_by = [row.get("written_by") for row in rows]
    misses = [row for row in rows if row.get("missed_before_purpose_was_widened")]
    found = []
    if snapshot.queries.get("record_type") != QUERIES_RECORD_TYPE:
        found.append("<query record type>")
    if len(rows) < MINIMUM_QUERIES:
        found.append(f"<{len(rows)} queries, {MINIMUM_QUERIES} required>")
    if written_by.count("reviewer") < MINIMUM_REVIEWER_QUERIES:
        found.append(f"<{written_by.count('reviewer')} reviewer queries, "
                     f"{MINIMUM_REVIEWER_QUERIES} required>")
    if len(misses) < MINIMUM_RECORDED_MISSES:
        found.append(f"<{len(misses)} recorded misses, "
                     f"{MINIMUM_RECORDED_MISSES} required>")
    return found


RULES = {
    "digest_matches_its_body": _digest_matches_its_body,
    "specification_text_equals_its_body": _specification_text_equals_its_body,
    "reference_loads_through_the_engine_contract":
        _reference_loads_through_the_engine_contract,
    "both_thin_layers_are_covered": _both_thin_layers_are_covered,
    "licence_is_one_the_default_host_accepts": _licence_is_one_the_default_host_accepts,
    "every_item_is_an_unapproved_candidate": _every_item_is_an_unapproved_candidate,
    "every_item_declares_a_version_and_its_effects":
        _every_item_declares_a_version_and_its_effects,
    "provenance_names_a_revision_and_real_repository_sources":
        _provenance_names_a_revision_and_real_repository_sources,
    "guidance_fields_use_the_engine_vocabularies":
        _guidance_fields_use_the_engine_vocabularies,
    "the_query_set_keeps_its_adversarial_record":
        _the_query_set_keeps_its_adversarial_record,
}


def _edit_first_row(snapshot: Snapshot, **fields) -> Snapshot:
    mutant = snapshot.copy()
    mutant.rows()[0].update(fields)
    return mutant


def _edit_first_reference(snapshot: Snapshot, **fields) -> Snapshot:
    mutant = snapshot.copy()
    mutant.rows()[0]["reference"].update(fields)
    return mutant


def _drop_one_layer(snapshot: Snapshot) -> Snapshot:
    mutant = snapshot.copy()
    mutant.items["items"] = [
        row for row in mutant.rows()
        if row["reference"]["source_layer"] != COVERED_LAYERS[1]]
    return mutant


def _move_one_item_to_another_layer(snapshot: Snapshot) -> Snapshot:
    return _edit_first_reference(snapshot, source_layer="context_intelligence")


def _edit_a_body_without_rebuilding(snapshot: Snapshot) -> Snapshot:
    mutant = snapshot.copy()
    name = Path(mutant.rows()[0]["body_path"]).name
    mutant.bodies[name] = mutant.bodies[name] + "\nAn edit nobody measured.\n"
    return mutant


def _first_user_feedback_row(snapshot: Snapshot) -> dict:
    for row in snapshot.rows():
        if row["reference"]["source_layer"] == USER_FEEDBACK_LAYER:
            return row
    raise AssertionError("the pack holds no User Feedback item to mutate")


def _rewrite_a_guidance_row(snapshot: Snapshot, field_name: str,
                            value: str) -> Snapshot:
    """Put a value the owning module does not accept in one guidance row."""
    mutant = snapshot.copy()
    name = Path(_first_user_feedback_row(mutant)["body_path"]).name
    rewritten = []
    for line in mutant.bodies[name].split("\n"):
        parts = [cell.strip() for cell in line.split("|")]
        if len(parts) == 4 and parts[1] == field_name:
            rewritten.append(f"| {field_name} | {value} |")
        else:
            rewritten.append(line)
    mutant.bodies[name] = "\n".join(rewritten)
    return mutant


def _drop_the_source_tree_entry(snapshot: Snapshot) -> Snapshot:
    """Cite a path that is not in the recorded revision."""
    mutant = snapshot.copy()
    cited = mutant.rows()[0]["provenance"]["repository_sources"][0]
    mutant.source_tree["sources"].pop(cited, None)
    return mutant


def _keep_only_author_queries(snapshot: Snapshot) -> Snapshot:
    mutant = snapshot.copy()
    kept = [row for row in mutant.query_rows() if row.get("written_by") != "reviewer"]
    mutant.queries["queries"] = kept + kept[:MINIMUM_QUERIES - len(kept)]
    return mutant


def _forget_which_queries_missed(snapshot: Snapshot) -> Snapshot:
    mutant = snapshot.copy()
    for row in mutant.query_rows():
        row.pop("missed_before_purpose_was_widened", None)
    return mutant


#: Each rule and the known-wrong cases it must report. A rule with no case here
#: is a rule nobody has shown to work.
KNOWN_WRONG = {
    "digest_matches_its_body": (
        ("a body was edited and the pack was not rebuilt", _edit_a_body_without_rebuilding),
        ("a digest was copied from another item",
         lambda s: _edit_first_reference(s, digest="a" * 64)),
        ("a size was rounded", lambda s: _edit_first_reference(s, size_bytes=1000)),
    ),
    "specification_text_equals_its_body": (
        ("the staged text drifted from the shipped body",
         lambda s: _replace_first_specification_text(s, "A shorter summary.")),
    ),
    "reference_loads_through_the_engine_contract": (
        ("a digest that is not sixty four hexadecimal characters",
         lambda s: _edit_first_reference(s, digest="short")),
        ("an unknown kind", lambda s: _edit_first_reference(s, kind="pamphlet")),
        ("an empty source reference", lambda s: _edit_first_reference(s, source_ref="")),
        ("an effect that is not in the declared vocabulary",
         lambda s: _edit_first_reference(s, declared_effects=["reads_mind"])),
    ),
    "both_thin_layers_are_covered": (
        ("one of the two layers was emptied", _drop_one_layer),
        ("an item was filed under a layer this pack does not cover",
         _move_one_item_to_another_layer),
    ),
    "licence_is_one_the_default_host_accepts": (
        ("the licence is missing", lambda s: _edit_first_reference(s, license="")),
        ("a review state was written where a licence belongs",
         lambda s: _edit_first_reference(s, license="pending_review")),
        ("an unknown marker was written where a licence belongs",
         lambda s: _edit_first_reference(s, license="unknown")),
        ("a licence the default host policy does not list",
         lambda s: _edit_first_reference(s, license="GPL-3.0-only")),
    ),
    "every_item_is_an_unapproved_candidate": (
        ("an item promoted itself", lambda s: _edit_first_row(s, lifecycle="registered")),
        ("an item claimed an approval nobody gave",
         lambda s: _edit_first_row(s, approval={"approved": True,
                                                "approved_by": "the author",
                                                "approval_ref": "self"})),
        ("the pack claimed it was published",
         lambda s: _edit_header(s, publication="published")),
        ("the lifecycle tag was promoted while the row stayed a candidate",
         lambda s: _edit_first_reference(s, tags={"record_type": "intelligence_tags/v1",
                                                  "lifecycle": ["qualified"]})),
    ),
    "every_item_declares_a_version_and_its_effects": (
        ("the version was removed", lambda s: _edit_first_row(s, item_version="")),
        ("an effect was declared on prose",
         lambda s: _edit_first_reference(s, declared_effects=["writes_fs"])),
        ("the licence state was removed", lambda s: _edit_first_row(s, license_state="")),
    ),
    "provenance_names_a_revision_and_real_repository_sources": (
        ("a cited source does not exist",
         lambda s: _edit_provenance(s, repository_sources=["docs/no-such-file.md"])),
        ("a cited source escapes the repository",
         lambda s: _edit_provenance(s, repository_sources=["../outside.md"])),
        ("the provenance names a different revision",
         lambda s: _edit_provenance(s, source_revision="0" * 40)),
        ("the source reference lost its revision",
         lambda s: _edit_first_reference(s, source_ref="AGENTS.md")),
        ("a cited source is not in the recorded revision",
         _drop_the_source_tree_entry),
        ("the recorded listing is bound to another revision",
         lambda s: _edit_source_tree(s, source_revision="0" * 40)),
        ("the recorded listing lost its record type",
         lambda s: _edit_source_tree(s, record_type="a listing")),
    ),
    "guidance_fields_use_the_engine_vocabularies": (
        ("the timing is prose rather than a value the store accepts",
         lambda s: _rewrite_a_guidance_row(
             s, "Timing", "before verification, and again when a check fails")),
        ("the guidance type is not in GUIDANCE_TYPES",
         lambda s: _rewrite_a_guidance_row(s, "Guidance type", "`reminder`")),
        ("the scope is not in SCOPES",
         lambda s: _rewrite_a_guidance_row(s, "Scope", "`company`")),
        ("the strength is not in STRENGTHS",
         lambda s: _rewrite_a_guidance_row(s, "Strength", "`strong`")),
        ("a guidance row was removed altogether",
         lambda s: _rewrite_a_guidance_row(s, "Timing", "")),
    ),
    "the_query_set_keeps_its_adversarial_record": (
        ("the reviewer queries were dropped and the count padded with the "
         "author's own", _keep_only_author_queries),
        ("the record of which queries first missed was dropped",
         _forget_which_queries_missed),
        ("the query set was trimmed below its floor",
         lambda s: _trim_queries(s, 5)),
        ("the query record lost its record type",
         lambda s: _edit_query_header(s, record_type="some queries")),
    ),
}


def _replace_first_specification_text(snapshot: Snapshot, text: str) -> Snapshot:
    mutant = snapshot.copy()
    mutant.specifications["specifications"][0]["text"] = text
    return mutant


def _edit_header(snapshot: Snapshot, **fields) -> Snapshot:
    mutant = snapshot.copy()
    mutant.items.update(fields)
    return mutant


def _edit_provenance(snapshot: Snapshot, **fields) -> Snapshot:
    mutant = snapshot.copy()
    mutant.rows()[0]["provenance"].update(fields)
    return mutant


def _edit_source_tree(snapshot: Snapshot, **fields) -> Snapshot:
    mutant = snapshot.copy()
    mutant.source_tree.update(fields)
    return mutant


def _edit_query_header(snapshot: Snapshot, **fields) -> Snapshot:
    mutant = snapshot.copy()
    mutant.queries.update(fields)
    return mutant


def _trim_queries(snapshot: Snapshot, keep: int) -> Snapshot:
    mutant = snapshot.copy()
    mutant.queries["queries"] = mutant.query_rows()[:keep]
    return mutant


def _pack_build():
    """The pack's own build tool, loaded from its folder rather than copied."""
    import sys
    from importlib.util import module_from_spec, spec_from_file_location
    name = "layer_coverage_build"
    if name not in sys.modules:
        spec = spec_from_file_location(name, PACK / "build.py")
        module = module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def problems(snapshot: Snapshot) -> dict:
    """Every rule that reports something, with what it reported."""
    return {name: found for name, rule in RULES.items() if (found := rule(snapshot))}


def git_mismatches(snapshot: Snapshot):
    """The cited paths whose recorded object name is not what git holds.

    Returns ``None`` when git or the revision is unavailable, so a caller
    reports an unconfirmed listing rather than an empty list of problems.
    """
    revision = snapshot.source_tree.get("source_revision", "")
    listed = snapshot.source_tree.get("sources") or {}
    try:
        finished = subprocess.run(
            ["git", "-C", str(ROOT), "ls-tree", "-r", "-z", revision,
             "--", *sorted(listed)],
            capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if finished.returncode != 0:
        return None
    held = {}
    for entry in finished.stdout.decode("utf-8").split("\0"):
        if not entry:
            continue
        facts, _, path = entry.partition("\t")
        parts = facts.split()
        if len(parts) == 3 and parts[1] == "blob":
            held[path] = parts[2]
    return sorted(path for path, name in listed.items() if held.get(path) != name)


def first_three(rows, query) -> list:
    """What the hosted search reads: identity and purpose, never the body."""
    records = [StoreRecord(
        row["reference"]["identity"], "context", row["reference"]["purpose"],
        body={"description": row["reference"]["purpose"],
              "keywords": [row["reference"]["identity"], row["reference"]["kind"],
                           row["reference"]["source_layer"]]}) for row in rows]
    return [hit["record_id"] for hit in
            Retriever(records).search(query, mode="lexical", top_n=TOP_N)["hits"]]


class LayerCoverageChecks(unittest.TestCase):
    """The shipped pack passes every rule, and every rule rejects its mutants."""

    @classmethod
    def setUpClass(cls):
        cls.snapshot = Snapshot.load()

    def test_the_pack_records_carry_their_declared_contracts(self):
        self.assertEqual(self.snapshot.items.get("record_type"), ITEMS_RECORD_TYPE)
        self.assertEqual(self.snapshot.specifications.get("record_type"),
                         SPECIFICATIONS_RECORD_TYPE)
        self.assertEqual(len(self.snapshot.rows()),
                         len(self.snapshot.specifications["specifications"]))
        self.assertEqual(len(self.snapshot.rows()), len(self.snapshot.bodies))

    def test_the_shipped_pack_reports_no_problem(self):
        self.assertEqual(problems(self.snapshot), {})

    def test_the_pack_is_not_stale_against_its_bodies(self):
        self.assertEqual(_pack_build().build(PACK)["stale"], [])

    def test_plain_customer_queries_find_their_item(self):
        rows = self.snapshot.query_rows()
        identities = {row["reference"]["identity"] for row in self.snapshot.rows()}
        self.assertLessEqual({row["expected"] for row in rows}, identities)
        for row in rows:
            with self.subTest(query=row["query"]):
                self.assertIn(row["expected"],
                              first_three(self.snapshot.rows(), row["query"]))

    def test_the_recorded_source_tree_is_what_git_holds_at_that_revision(self):
        """The listing the provenance rule trusts is not the pack's own word.

        Without git, or without the revision in this clone, the listing cannot
        be confirmed here and the check says so instead of passing quietly.
        """
        mismatched = git_mismatches(self.snapshot)
        if mismatched is None:
            self.skipTest(f"git could not read {self.snapshot.items['source_revision']} "
                          "in this checkout, so the recorded listing is unconfirmed")
        self.assertEqual(mismatched, [])

    def test_a_planted_object_name_is_reported_against_git(self):
        """The known-wrong case for the listing: a name nobody could produce."""
        if git_mismatches(self.snapshot) is None:
            self.skipTest("git could not read the recorded revision in this checkout")
        mutant = self.snapshot.copy()
        cited = mutant.rows()[0]["provenance"]["repository_sources"][0]
        mutant.source_tree["sources"][cited] = "0" * 40
        self.assertEqual(git_mismatches(mutant), [cited])

    def test_a_pack_of_vague_purposes_finds_nothing(self):
        """The known-wrong case for the query check: without real purposes,
        the same search must return nothing rather than a confident wrong item."""
        vague = deepcopy(self.snapshot.rows())
        for index, row in enumerate(vague):
            row["reference"]["identity"] = f"item_{index}"
            row["reference"]["purpose"] = "Reviewed material"
        self.assertEqual(first_three(vague, "did my row actually commit"), [])
        self.assertEqual(
            first_three(vague, "server sent events break my fetch"), [])


def _known_wrong_check(name):
    def check(self):
        for label, make in KNOWN_WRONG[name]:
            with self.subTest(case=label):
                self.assertIn(name, problems(make(self.snapshot)),
                              f"the rule {name} did not report: {label}")
    return check


for _name in RULES:
    setattr(LayerCoverageChecks, f"test_{_name}_rejects_its_known_wrong_cases",
            _known_wrong_check(_name))


if __name__ == "__main__":
    unittest.main()
