"""Checks for tools/measure_catalogue_serving.py on a small fixture bundle, without the real bundle.

The measurement path runs end to end on eight fixture items, at the real size
and doubled: the fixture bundle is published into a temporary service store
with the service's own code, the view is built and measured, a second release
is swapped in, and the synthetic copies of the doubling are checked to be
labelled, to carry new identities and digests, and to leave the source
bundle untouched. The known-wrong cases are a root inside this repository, a
root on the live service's volume, a root inside the bundle or around it, a
root that already holds files, and a folder that is not a bundle. A removed
repository rule fails its own named check.
"""
from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import measure_catalogue_serving as tool  # noqa: E402
from loop_engine.core.service_runtime.catalogue_bundle import write_bundle  # noqa: E402
from loop_engine.core.service_runtime.catalogue_packages import sha256_hex  # noqa: E402
from loop_engine.core.service_runtime.catalogue_release_checks import bundle_line, skill  # noqa: E402
from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema  # noqa: E402

SCHEMA = {"record_type": "catalogue_attribute_schema/v1", "attributes": [
    {"name": "batch", "type": "keyword", "visibility": "internal"},
    {"name": "origin_layer", "type": "choice", "choices": ["context_intelligence", "code_intelligence"],
     "filterable": True, "shown": True},
    {"name": "tier", "type": "choice", "choices": ["verified", "community"], "filterable": True, "shown": True}]}
PURPOSES = ("Clean column names and normalise whitespace in a data frame before profiling",
            "Profile every column of a table and report null share and distinct counts",
            "Write a release note from the change list with one line for each item",
            "Check a sitemap for pages the active release does not serve",
            "Retry a failed provider call with the same request and record the outcome",
            "Summarise a long transcript into the decisions taken and the open questions")


def fixture_lines():
    """Eight items: six single-file skills, two of them Community, and two multi-file packages."""
    lines, payloads = [], []
    for index, purpose in enumerate(PURPOSES):
        body = f"# Skill {index}\n\n{purpose}\n"
        tier = "community" if index >= 4 else "verified"
        line = skill(f"fixture_skill_{index}", body, purpose=purpose,
                     attributes={"batch": "fixture", "origin_layer": "context_intelligence", "tier": tier})
        line["approval"]["tier"] = tier
        lines.append(line)
        payloads.append(body.encode())
    package_files = [("SKILL.md", b"# Package\n\nBuild the report from the notes.\n", "text/markdown",
                      "skill_definition"),
                     ("references/notes.md", b"Notes for the report.\n", "text/markdown", "skill_reference"),
                     ("assets/example.json", b'{"example": true}\n', "application/json", "skill_asset")]
    lines.append(bundle_line("fixture_package", package_files, purpose="Build a report from notes and an example",
                             attributes={"batch": "fixture", "origin_layer": "code_intelligence", "tier": "verified"}))
    payloads.extend(data for _path, data, _media, _role in package_files)
    runnable_files = package_files + [("scripts/run.py", b"print('run')\n", "text/x-python", "skill_script")]
    lines.append(bundle_line("fixture_runnable", runnable_files, effects=("spawns_process",),
                             purpose="Run the report script after the notes are checked",
                             attributes={"batch": "fixture", "origin_layer": "code_intelligence", "tier": "community"}))
    lines[-1]["approval"]["tier"] = "community"
    payloads.append(runnable_files[-1][1])
    return lines, payloads


def write_fixture_bundle(folder):
    lines, payloads = fixture_lines()
    write_bundle(folder, schema=CatalogueAttributeSchema.from_dict(SCHEMA), lines=lines, payloads=payloads,
                 notes="fixture bundle for the serving measurement checks")
    return folder


def folder_digest(folder):
    """One digest over every file name and every byte under a folder."""
    checksum = hashlib.sha256()
    for path in sorted(Path(folder).rglob("*")):
        if path.is_file():
            checksum.update(str(path.relative_to(folder)).encode())
            checksum.update(path.read_bytes())
    return checksum.hexdigest()


class MeasurementPathTest(unittest.TestCase):
    def test_the_measurement_runs_on_a_fixture_bundle_at_one_and_two_times(self):
        with tempfile.TemporaryDirectory(prefix="serving-measurement-") as directory:
            bundle = write_fixture_bundle(Path(directory).resolve() / "bundle")
            before = folder_digest(bundle)
            root = Path(directory).resolve() / "root"
            record = tool.measure(bundle, root, factors=(1, 2), queries=6, repetitions=2, accepted_licenses=("MIT",))
            self.assertEqual(folder_digest(bundle), before, "the source bundle is only read")
            self.assertEqual(record["record_type"], tool.RESULT_RECORD_TYPE)
            self.assertTrue(record["bundle"]["read_only"])
            self.assertEqual(record["queries"]["count"], 6)
            self.assertEqual([size["items"] for size in record["sizes"]], [8, 16])
            self.assertEqual([size["synthetic_items"] for size in record["sizes"]], [0, 8])
            real, doubled = record["sizes"]
            self.assertNotIn("write_synthetic_bundle", real["prepare"]["seconds"])
            self.assertIn("write_synthetic_bundle", doubled["prepare"]["seconds"])
            for size in record["sizes"]:
                served, traced, prepared = size["serve"], size["trace"], size["prepare"]
                self.assertEqual(prepared["publish_state"], "published")
                self.assertGreater(prepared["store"]["total_bytes"], 0)
                self.assertGreater(prepared["store"]["body_store_files"], 0)
                self.assertEqual(served["items_in_view"], size["items"])
                self.assertGreaterEqual(served["view_build_seconds"], 0)
                self.assertGreater(served["memory_after_build"]["peak_rss_kib_resource"], 0)
                self.assertEqual(served["index"]["entries"], size["items"])
                for mode in ("search_lexical", "search_hybrid", "search_lexical_with_filter",
                             "search_lexical_client_declares_no_effects"):
                    self.assertEqual(served[mode]["samples"], 6, mode)
                    self.assertLessEqual(served[mode]["p50_ms"], served[mode]["p95_ms"], mode)
                for mode in ("search_lexical", "search_hybrid"):
                    self.assertGreaterEqual(served[mode]["queries_with_hits"], 1, mode)
                # A client that declares every effect is offered every item; the runnable one is withheld otherwise.
                self.assertEqual(served["listing"]["items_offered"], size["items"])
                self.assertEqual(served["listing"]["items_withheld"], 0)
                self.assertLess(served["listing"]["items_offered_when_no_effect_is_declared"], size["items"])
                self.assertEqual(served["listing"]["samples"], 2)
                self.assertTrue(served["hot_swap"]["changed"])
                self.assertIsNone(served["hot_swap"]["failure"])
                self.assertTrue(served["hot_swap"]["release_is_second"])
                self.assertNotEqual(served["second_publish"]["release_id"], prepared["release_id"])
                self.assertEqual(served["second_publish"]["added"], prepared["second_bundle"]["added"])
                self.assertEqual(served["second_publish"]["changed"], prepared["second_bundle"]["changed"])
                self.assertEqual(served["hot_swap"]["items_in_view"], size["items"] + served["second_publish"]["added"])
                self.assertGreater(traced["tracemalloc_peak_bytes"], 0)
                self.assertEqual(traced["items_in_view"], size["items"])
            synthetic_bundle = root / "size-2x" / "bundle-2x"
            originals = {line["reference"]["identity"]: line for line in tool.load_rows(bundle)}
            copies = [line for line in tool.load_rows(synthetic_bundle) if tool.is_synthetic(line)]
            self.assertEqual(len(copies), 8)
            for line in copies:
                original = originals[line["reference"]["identity"].removesuffix("_synthetic_1")]
                self.assertTrue(line["reference"]["purpose"].startswith("Synthetic copy 1: "))
                self.assertTrue(line["approval"]["approval_ref"].startswith("synthetic-measurement-2026-09-26:"))
                self.assertEqual(line["attributes"]["batch"], tool.SYNTHETIC_BATCH)
                self.assertNotEqual(line["reference"]["digest"], original["reference"]["digest"])
                self.assertEqual(line["approval"]["approved_digest"], line["reference"]["digest"])
            self.assertEqual(sum(1 for line in tool.load_rows(synthetic_bundle) if not tool.is_synthetic(line)), 8)
            self.assertFalse(any(str(path).startswith(str(tool.REPOSITORY)) for path in root.rglob("*")))


class RefusalTest(unittest.TestCase):
    def test_a_root_inside_the_repository_the_live_volume_or_the_bundle_is_refused_before_writing(self):
        with tempfile.TemporaryDirectory(prefix="serving-measurement-") as directory:
            bundle = write_fixture_bundle(Path(directory).resolve() / "bundle")
            inside = tool.REPOSITORY / "artifacts" / "serving-measurement-check-root"
            self.assertEqual(tool.root_refusal(inside, bundle), "root_inside_repository")
            self.assertEqual(tool.root_refusal(tool.REPOSITORY, bundle), "root_inside_repository")
            self.assertEqual(tool.root_refusal(Path("/data/measurement"), bundle), "root_is_live_volume")
            self.assertEqual(tool.root_refusal(bundle / "inside", bundle), "root_inside_bundle")
            self.assertEqual(tool.root_refusal(bundle.parent, bundle), "bundle_inside_root")
            occupied = Path(directory).resolve() / "occupied"
            occupied.mkdir()
            (occupied / "held.txt").write_text("held")
            self.assertEqual(tool.root_refusal(occupied, bundle), "root_not_empty")
            self.assertEqual(tool.root_refusal(Path(directory).resolve() / "fresh", bundle), "")
            for phase in ("all", "prepare"):
                with self.assertRaises(SystemExit) as stopped, redirect_stderr(io.StringIO()) as printed:
                    tool.main(["--bundle", str(bundle), "--root", str(inside), "--factors", "1", "--phase", phase])
                self.assertEqual(stopped.exception.code, 2)
                self.assertIn("refused: root_inside_repository", printed.getvalue())
                self.assertFalse(inside.exists())
            with self.assertRaises(tool.MeasurementRefused) as refused:
                tool.measure(bundle, inside, factors=(1,), accepted_licenses=("MIT",))
            self.assertEqual(refused.exception.code, "root_inside_repository")
            self.assertFalse(inside.exists())
            not_a_bundle = Path(directory).resolve() / "not-a-bundle"
            not_a_bundle.mkdir()
            with self.assertRaises(tool.MeasurementRefused) as refused:
                tool.measure(not_a_bundle, Path(directory).resolve() / "fresh", factors=(1,),
                             accepted_licenses=("MIT",))
            self.assertEqual(refused.exception.code, "bundle_folder_invalid")
            with self.assertRaises(tool.MeasurementRefused) as refused:
                tool.measure(bundle, Path(directory).resolve() / "fresh", factors=(1, 1), accepted_licenses=("MIT",))
            self.assertEqual(refused.exception.code, "factors_invalid")
            self.assertFalse((Path(directory).resolve() / "fresh").exists())

    def test_removed_repository_rule_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="serving-measurement-") as directory:
            bundle = write_fixture_bundle(Path(directory).resolve() / "bundle")
            inside = tool.REPOSITORY / "artifacts" / "serving-measurement-check-root"
            with patch.object(tool, "REPOSITORY", Path("/no-such-repository")):
                self.assertEqual(tool.root_refusal(inside, bundle), "",
                                 "without the repository rule an in-repository root passes, so the rule is load-bearing")


class SyntheticCopyTest(unittest.TestCase):
    def test_a_synthetic_copy_is_labelled_and_carries_new_bytes_while_a_changed_item_keeps_its_identity(self):
        lines, payloads = fixture_lines()
        bytes_by_digest = {sha256_hex(data): data for data in payloads}

        def read_bytes(digest, size_bytes):
            data = bytes_by_digest[digest]
            self.assertEqual(len(data), size_bytes)
            return data
        row = lines[-1]
        copy, copy_payloads = tool.rewritten_line(row, 3, read_bytes)
        self.assertEqual(copy["reference"]["identity"], "fixture_runnable_synthetic_3")
        self.assertTrue(copy["reference"]["purpose"].startswith("Synthetic copy 3: "))
        self.assertTrue(copy["reference"]["source_ref"].startswith("synthetic-copy-3:"))
        self.assertTrue(tool.is_synthetic(copy))
        self.assertEqual(copy["attributes"]["batch"], tool.SYNTHETIC_BATCH)
        self.assertEqual(copy["approval"]["tier"], row["approval"]["tier"])
        self.assertNotEqual(copy["reference"]["digest"], row["reference"]["digest"])
        self.assertEqual(copy["approval"]["approved_digest"], copy["reference"]["digest"])
        self.assertEqual(len(copy_payloads), len(row["package"]["files"]))
        for entry, original, data in zip(copy["package"]["files"], row["package"]["files"], copy_payloads):
            self.assertEqual(data, bytes_by_digest[original["digest"]] + tool.marker(3))
            self.assertEqual(entry["digest"], sha256_hex(data))
            self.assertEqual(entry["size_bytes"], len(data))
            self.assertEqual((entry["path"], entry["media_type"], entry["role"]),
                             (original["path"], original["media_type"], original["role"]))
        changed, _payloads = tool.rewritten_line(row, 3, read_bytes, keep_identity=True)
        self.assertEqual(changed["reference"]["identity"], row["reference"]["identity"])
        self.assertEqual(changed["reference"]["purpose"], row["reference"]["purpose"])
        self.assertEqual(changed["attributes"], row["attributes"])
        self.assertFalse(tool.is_synthetic(changed))
        self.assertNotEqual(changed["reference"]["digest"], row["reference"]["digest"])
        self.assertNotEqual(changed["reference"]["digest"], copy["reference"]["digest"])

    def test_queries_and_percentiles_are_deterministic(self):
        lines, _payloads = fixture_lines()
        first = tool.build_queries(lines, 12, 7)
        self.assertEqual(first, tool.build_queries(lines, 12, 7))
        self.assertEqual(len(first), 12)
        self.assertTrue(all(1 <= len(query.split()) <= 5 for query in first))
        self.assertNotEqual(first, tool.build_queries(lines, 12, 8))
        self.assertEqual(tool.percentile(list(range(1, 51)), 0.95), 48)
        self.assertEqual(tool.percentile(list(range(1, 21)), 0.95), 19)
        self.assertEqual(tool.percentile([4.0], 0.95), 4.0)


if __name__ == "__main__":
    unittest.main()
