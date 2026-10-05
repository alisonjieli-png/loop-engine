"""Checks for segmented catalogue releases (catalogue_segments.py): format, negotiation and tampering.

Every check runs against a real temporary service store and body folder, as
`catalogue_release_checks` does; no network, model or provider is used. Each
guard is shown twice: the known-wrong case is refused, and a removed-guard
control reruns the case with the guard patched away and requires the check's
own predicate to fail.

```text
Known-wrong case                                                   Guard
├── a stored segment whose pairs were changed after publication    segment digest checked at every read
├── a bundle segment list with two lines swapped                   the header's segment list digest
├── a bundle whose segment list was rewritten consistently but     identity order across segments and the
│   out of order, with a segment twice, or with merged segments    canonical cuts of the segmentation
├── a stored release record whose segment list was reordered       the release digest over the ordered list
└── an image that reads only version 1 against a segmented store   catalogue state version 3
```
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from . import catalogue_releases, catalogue_segments
from .catalogue_bundle import canonical_bytes, validate_item
from .catalogue_releases import RELEASE_KIND, load_release, read_pointer, status, withdraw
from .catalogue_schema import CatalogueAttributeSchema
from .catalogue_segment_publish import publish_segmented
from .catalogue_segments import (SEGMENT_KIND, Carried, ContentDigest, Segmentation, SegmentRef, catalogue_formats,
                                 negotiate_bundle_format, read_segmented_bundle, segment_document,
                                 write_segmented_bundle)
from .records import ServiceRuntimeError

#: A small target so a fixture of a few dozen items has several segments.
TARGET = 16


def refused(action, code=None):
    try:
        action()
    except ServiceRuntimeError as error:
        return code is None or error.code == code
    except Exception:  # noqa: BLE001 - a crash is not a typed refusal
        return False
    return False


class SegmentFixture:
    """A catalogue release fixture that publishes version 2 bundles of `count` single-file skills."""

    def __init__(self, root):
        from .catalogue_release_checks import SCHEMA, Fixture
        self.base = Fixture(root)
        self.root = Path(root)
        self.schema = CatalogueAttributeSchema.from_dict(SCHEMA)
        self.count = 0

    def lines(self, names, text=lambda name: f"Skill {name} explains one testing step."):
        return [self.base.line(name, text(name)) for name in names]

    def versions(self, lines):
        return [(line, validate_item(line, self.schema, license_policy=self.base.license_policy,
                                     family_policy=self.base.family_policy).version) for line in lines]

    def payloads(self, lines):
        return [data for line in lines for data in self.base._bytes[line["reference"]["identity"]]]

    def write(self, lines, *, carry_items=None, withdrawals=(), payloads=None, segmentation=None):
        self.count += 1
        folder = self.root / f"segmented-{self.count}"
        write_segmented_bundle(folder, schema=self.schema, items=self.versions(lines),
                               payloads=self.payloads(lines) if payloads is None else payloads,
                               segmentation=segmentation or Segmentation(TARGET), withdrawals=list(withdrawals),
                               carry=Carried(items=None if carry_items is None else frozenset(carry_items)))
        return folder

    def read(self, folder):
        return read_segmented_bundle(folder, license_policy=self.base.license_policy,
                                     family_policy=self.base.family_policy)

    def publish(self, lines, **fields):
        expected = fields.pop("expected", None)
        return publish_segmented(self.base.context, self.read(self.write(lines, **fields)),
                                 expected_release=expected)

    def active(self):
        with self.base.context.binding.store() as store:
            _row, pointer = read_pointer(self.base.context.binding, store)
        return pointer["release_id"] if pointer else ""


@contextmanager
def segment_fixture():
    with tempfile.TemporaryDirectory(prefix="catalogue-segment-checks-") as directory:
        yield SegmentFixture(directory)


NAMES = [f"skill_{index:03d}" for index in range(60)]


def _segmentation_checks(check):
    segmentation = Segmentation(TARGET)
    pairs = [(name, f"{index:064x}") for index, name in enumerate(NAMES)]
    first = [ref for ref, _document in catalogue_segments.membership_segments(pairs, segmentation)]
    again = [ref for ref, _document in catalogue_segments.membership_segments(list(pairs), segmentation)]
    check("the_same_membership_always_gives_the_same_segments", first == again and len(first) > 1)
    changed = list(pairs)
    changed[30] = (changed[30][0], "f" * 64)
    after = [ref for ref, _document in catalogue_segments.membership_segments(changed, segmentation)]
    check("a_changed_item_version_changes_only_its_own_segment",
          sum(1 for old, new in zip(first, after) if old != new) == 1 and len(first) == len(after))
    inserted = sorted(pairs + [("skill_030a", "e" * 64)])
    restored = [ref for ref, _document in catalogue_segments.membership_segments(
        [pair for pair in inserted if pair[0] != "skill_030a"], segmentation)]
    check("segments_depend_on_the_membership_and_not_on_its_history", restored == first)
    from .catalogue_releases import content_digest
    stream = ContentDigest("a" * 64)
    for identity, version in pairs:
        stream.add(identity, version)
    check("the_streamed_content_digest_equals_the_version_1_content_digest",
          stream.hexdigest() == content_digest("a" * 64, tuple(pairs)))
    long_run = [(f"x{index:05d}", "0" * 64) for index in range(400)]
    sizes = [len(segment) for segment in segmentation.split(long_run)]
    check("no_segment_holds_more_than_its_maximum", max(sizes) <= segmentation.maximum_items
          and sum(sizes) == len(long_run))
    check("a_segmentation_outside_the_declared_targets_is_refused",
          refused(lambda: Segmentation(100), "catalogue_segmentation_unsupported")
          and refused(lambda: Segmentation.from_dict({"rule": "catalogue_segmentation/v1", "target_items": 16,
                                                      "maximum_items": 99}), "catalogue_segmentation_unsupported"))


def _negotiation_checks(check):
    formats = catalogue_formats()
    check("this_image_states_both_bundle_versions_it_reads",
          formats["bundle_record_types"] == ["catalogue_release_bundle/v1", "catalogue_release_bundle/v2"]
          and 3 in formats["catalogue_state_versions"])
    check("a_service_without_the_formats_command_is_sent_version_1",
          negotiate_bundle_format(None) == "catalogue_release_bundle/v1")
    check("a_service_that_reads_version_2_is_sent_version_2",
          negotiate_bundle_format(formats) == "catalogue_release_bundle/v2")
    check("an_unreadable_formats_record_is_refused_before_any_upload",
          refused(lambda: negotiate_bundle_format({"record_type": "something/v9"}), "catalogue_format_unsupported"))
    check("a_service_with_no_common_bundle_version_is_refused",
          refused(lambda: negotiate_bundle_format({**formats, "bundle_record_types": ["catalogue_release_bundle/v3"]}),
                  "catalogue_format_unsupported"))


def _publish_checks(check):
    with segment_fixture() as case:
        lines = case.lines(NAMES)
        first_v1 = case.base.publish(lines)
        first = case.publish(lines)
        check("a_version_2_release_of_a_version_1_library_serves_the_same_content_digest",
              first["content_digest"] == first_v1["content_digest"] and first["items_written"] == 0
              and first["segments_written"] == first["segments"] > 1)
        view = case.base.view()
        check("a_version_2_release_is_served_with_every_item", len(view.catalogue.items) == len(NAMES)
              and view.release_id == first["release_id"])
        again = case.publish(lines, expected=first["release_id"])
        check("publishing_the_same_content_again_changes_nothing", again["state"] == "unchanged")
        changed = [case.base.line("skill_031", "Skill thirty one, changed.") if line["reference"]["identity"]
                   == "skill_031" else line for line in lines if line["reference"]["identity"] != "skill_040"]
        changed.append(case.base.line("skill_100", "A new skill."))
        carried = {version for _line, version in case.versions(changed)} - {
            version for _line, version in case.versions(lines)}
        delta = case.publish(changed, expected=first["release_id"], carry_items=carried,
                             payloads=case.payloads([line for line in changed if line["reference"]["identity"]
                                                     in ("skill_031", "skill_100")]),
                             withdrawals=[{"identity": "skill_040", "note": "withdrawn by the check"}])
        check("a_delta_publish_writes_only_the_new_segments_and_item_versions",
              delta["items_written"] == 2 and 0 < delta["segments_written"] < delta["segments"]
              and delta["added"] == 1 and delta["changed"] == 1 and delta["withdrawn"] == 1
              and delta["durable_withdrawals"] == 1)
        with case.base.context.binding.store() as store:
            state = catalogue_releases.read_state(case.base.context.binding, store)[1]
        check("the_first_version_2_publish_raises_the_state_to_3", state["state_version"] == 3)
        relisted = case.lines(["skill_040"]) + [line for line in changed]
        check("a_version_2_release_never_lists_a_withdrawn_item_version",
              refused(lambda: case.publish(relisted, expected=delta["release_id"]),
                      "catalogue_release_lists_withdrawn_item")
              and case.active() == delta["release_id"])
        rolled = catalogue_releases.rollback(case.base.context, to_release=first["release_id"],
                                             expected_release=delta["release_id"])
        check("a_rollback_to_a_version_2_release_keeps_the_withdrawal",
              rolled["withdrawn_items_kept_withheld"] == ["skill_040"]
              and "skill_040" not in case.base.view().catalogue.items)
        reported = status(case.base.context)
        check("status_counts_the_items_and_changes_of_both_release_versions",
              {row["record_type"] for row in reported["releases"]} == {"catalogue_release/v1", "catalogue_release/v2"}
              and all(row["items"] in (len(NAMES), len(changed)) for row in reported["releases"]))
        withdraw(case.base.context, identity="skill_001", note_text="report")
        check("a_withdrawal_finds_its_item_in_a_version_2_release_without_reading_the_release",
              "skill_001" not in case.base.view().catalogue.items)


def _tamper_checks(check):
    with segment_fixture() as case:
        lines = case.lines(NAMES)
        first = case.publish(lines)
        # A second release holds another version of skill_031, so a forged segment can name a version the store
        # holds: only the segment and content digests stand between the forgery and the customer.
        changed = [case.base.line("skill_031", "Skill thirty one, changed.") if line["reference"]["identity"]
                   == "skill_031" else line for line in lines]
        second = case.publish(changed, expected=first["release_id"])
        binding = case.base.context.binding
        with binding.store() as store:
            header = catalogue_releases.load_release_header(binding, store, first["release_id"])
            newer = catalogue_releases.load_release_header(binding, store, second["release_id"])
            victim = header.segment_for("skill_031")
            row = binding.read(store, SEGMENT_KIND, victim.digest)
            other_version = newer.version_of("skill_031", catalogue_releases.segment_reader(binding, store))
        forged = json.loads(json.dumps(row["payload"]))
        forged["items"] = [[identity, other_version if identity == "skill_031" else version]
                           for identity, version in forged["items"]]

        def write_forged():
            with binding.store(write=True) as store:
                held = binding.read(store, SEGMENT_KIND, victim.digest)
                binding.commit(store, (binding.record(SEGMENT_KIND, victim.digest, forged),), (binding.guard(held),))

        def load():
            with binding.store() as store:
                return load_release(binding, store, first["release_id"])
        write_forged()
        check("a_stored_segment_changed_after_publication_is_refused",
              refused(load, "catalogue_segment_digest_mismatch"))
        real_digest = catalogue_segments.segment_digest

        forged_bytes = canonical_bytes(forged)

        def forged_digest(document):
            return victim.digest if canonical_bytes(document) == forged_bytes else real_digest(document)
        # The content digest over every pair is a second guard; the control removes both to show they are the rule.
        with patch.object(catalogue_segments, "segment_digest", forged_digest), \
                patch.object(catalogue_segments.ContentDigest, "hexdigest", lambda self: header.content_digest):
            check("removed_segment_and_content_digest_rules_are_detected", not refused(load))
        with binding.store(write=True) as store:
            held = binding.read(store, SEGMENT_KIND, victim.digest)
            binding.commit(store, (binding.record(SEGMENT_KIND, victim.digest, row["payload"]),), (binding.guard(held),))
        with binding.store() as store:
            release_row = binding.read(store, RELEASE_KIND, first["release_id"])
        reordered = json.loads(json.dumps(release_row["payload"]))
        reordered["segments"][0], reordered["segments"][1] = reordered["segments"][1], reordered["segments"][0]
        with binding.store(write=True) as store:
            held = binding.read(store, RELEASE_KIND, first["release_id"])
            binding.commit(store, (binding.record(RELEASE_KIND, first["release_id"], reordered),), (binding.guard(held),))
        check("a_stored_release_whose_segment_list_was_reordered_is_refused",
              refused(load, "catalogue_release_digest_mismatch"))
        with patch.object(catalogue_releases, "release_digest", lambda document: first["release_id"]):
            check("removed_release_digest_rule_is_detected_by_the_segment_order_rule",
                  refused(load, "catalogue_release_digest_mismatch"))
        with patch.object(catalogue_releases, "release_digest", lambda document: first["release_id"]), \
                patch.object(catalogue_segments, "require_segment_list", lambda refs, segmentation, code: tuple(refs)), \
                patch.object(catalogue_segments.SegmentedRelease, "entries",
                             lambda self, read: (pair for ref in self.segments for pair in
                                                 catalogue_segments.segment_entries(read(ref.digest), ref.digest))):
            check("removed_segment_order_rules_are_detected", not refused(load))
    with segment_fixture() as case:
        lines = case.lines(NAMES)
        base = case.publish(lines)
        before = case.active()
        folder = case.write(case.lines(NAMES[:-1] + ["skill_200"]))
        listing = (folder / "release-segments.jsonl").read_bytes().splitlines(keepends=True)
        swapped = listing[1:2] + listing[0:1] + listing[2:]
        (folder / "release-segments.jsonl").write_bytes(b"".join(swapped))
        check("a_bundle_whose_segment_lines_were_swapped_is_refused_before_any_write",
              refused(lambda: case.read(folder), "bundle_segments_changed") and case.active() == before)

        def consistent(rewrite):
            """A bundle whose segment list was rewritten and whose header was updated to match it."""
            target = case.write(case.lines(NAMES[:-1] + ["skill_200"]))
            refs = [SegmentRef.from_list(json.loads(line)) for line in
                    (target / "release-segments.jsonl").read_bytes().splitlines()]
            refs = rewrite(refs, target)
            body = b"".join(canonical_bytes(ref.to_list()) + b"\n" for ref in refs)
            (target / "release-segments.jsonl").write_bytes(body)
            header = json.loads((target / "bundle.json").read_text())
            from .catalogue_packages import sha256_hex
            header["segment_list"] = {"count": len(refs), "bytes": len(body), "digest": sha256_hex(body)}
            header["release_items"] = sum(ref.count for ref in refs)
            (target / "bundle.json").write_text(json.dumps(header, indent=1, sort_keys=True) + "\n")
            return lambda: publish_segmented(case.base.context, case.read(target), expected_release=base["release_id"])

        def reorder(refs, _target):
            return [refs[1], refs[0]] + refs[2:]

        def duplicate(refs, _target):
            return refs[:2] + [refs[1]] + refs[2:]

        def merge(refs, target):
            first_pairs = catalogue_segments.segment_entries(json.loads(
                (target / "segments/sha256" / refs[0].digest[:2] / refs[0].digest).read_bytes()))
            second_pairs = catalogue_segments.segment_entries(json.loads(
                (target / "segments/sha256" / refs[1].digest[:2] / refs[1].digest).read_bytes()))
            document = segment_document(first_pairs + second_pairs)
            digest = catalogue_segments.segment_digest(document)
            path = target / "segments/sha256" / digest[:2] / digest
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical_bytes(document))
            return [SegmentRef(digest, first_pairs[0][0], len(first_pairs) + len(second_pairs))] + refs[2:]
        check("a_consistently_rewritten_list_out_of_identity_order_is_refused",
              refused(consistent(reorder), "bundle_segments_changed") and case.active() == before)
        check("a_consistently_rewritten_list_naming_a_segment_twice_is_refused",
              refused(consistent(duplicate), "bundle_segments_changed") and case.active() == before)
        check("a_consistently_rewritten_list_with_merged_segments_is_refused",
              refused(consistent(merge), "catalogue_segment_not_canonical") and case.active() == before)
        with patch.object(Segmentation, "require_canonical", lambda self, entries, last: None):
            check("removed_canonical_cut_rule_is_detected", not refused(consistent(merge)))
        # The guard above was removed for the control only; the store moved, so the next case starts afresh.
    with segment_fixture() as case:
        lines = case.lines(NAMES)
        case.publish(lines)
        with patch.object(catalogue_releases, "SUPPORTED_CATALOGUE_STATE_VERSIONS", (1, 2)):
            check("an_image_that_reads_only_version_1_refuses_to_start_on_a_segmented_store",
                  refused(lambda: case.base.view(), "catalogue_state_version_unsupported"))


def run_checks(check=None):
    tests = []
    if check is None:
        def check(name, passed):
            tests.append({"test": name, "passed": bool(passed),
                          "detail": "real temporary service store and body folder; no provider"})
    _segmentation_checks(check)
    _negotiation_checks(check)
    for group in (_publish_checks, _tamper_checks):
        try:
            group(check)
        except Exception:  # noqa: BLE001 - a group that stops part way is a failure with a name
            check(f"the_{group.__name__.strip('_')}_ran_to_completion", False)
    return {"record_type": "catalogue_segment_checks/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}


def self_test():
    return run_checks()
