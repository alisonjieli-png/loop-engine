"""Known-wrong checks for the deterministic harness intelligence idea matrix."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.harness_idea_matrix import (  # noqa: E402
    DATATYPES,
    DEFAULT_OPPORTUNITIES,
    FACET_DIMENSIONS,
    OPERATIONS,
    USE_CASES,
    Idea,
    MatrixError,
    MatrixSource,
    build_ideas,
    main,
    operation_fits_datatype,
    render_batch,
)


class DatatypeOperationPairChecks(unittest.TestCase):
    def test_matrix_multiplication_is_possible(self):
        self.assertTrue(operation_fits_datatype("matrix", "multiplication"))

    def test_person_name_multiplication_is_refused(self):
        self.assertFalse(operation_fits_datatype("person_name", "multiplication"))

    def test_inverted_log_lines_are_refused(self):
        self.assertFalse(operation_fits_datatype("log_lines", "inversion"))

    def test_matrix_formatting_is_refused(self):
        self.assertFalse(operation_fits_datatype("matrix", "formatting"))

    def test_unknown_datatype_raises(self):
        with self.assertRaises(MatrixError):
            operation_fits_datatype("telepathy", "sorting")

    def test_unknown_operation_is_refused_by_build(self):
        # Unknown operations never enter the declared vocabulary, so the
        # matrix cannot emit a record carrying an undeclared operation.
        self.assertNotIn("multiply_matrices_in_place", OPERATIONS)


class SourceChecks(unittest.TestCase):
    def test_unknown_source_kind_is_refused(self):
        with self.assertRaises(MatrixError):
            MatrixSource("scraped_forum", Path("/tmp/whatever.json"))

    def test_missing_source_file_is_refused(self):
        with self.assertRaises(MatrixError):
            MatrixSource("onet_pinned", ROOT / "does-not-exist.json")

    def test_digest_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(MatrixError):
                MatrixSource("onet_pinned", path, sha256="0" * 64)

    def test_pinned_default_source_is_readable(self):
        source = MatrixSource("onet_pinned", DEFAULT_OPPORTUNITIES)
        self.assertEqual(source.kind, "onet_pinned")


class BuildChecks(unittest.TestCase):
    def test_build_deduplicates_by_method_signature(self):
        ideas = build_ideas(MatrixSource("onet_pinned", DEFAULT_OPPORTUNITIES))
        signatures = [idea.signature for idea in ideas]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_no_source_is_refused(self):
        with self.assertRaises(MatrixError):
            build_ideas(MatrixSource("none", Path("")))

    def test_every_idea_carries_a_known_wrong_case(self):
        ideas = build_ideas(MatrixSource("onet_pinned", DEFAULT_OPPORTUNITIES))
        for idea in ideas:
            self.assertTrue(idea.known_wrong.strip(), idea.signature)
            self.assertTrue(idea.brief.strip(), idea.signature)

    def test_every_idea_carries_real_task_reference(self):
        ideas = build_ideas(MatrixSource("onet_pinned", DEFAULT_OPPORTUNITIES))
        for idea in ideas:
            self.assertNotEqual(idea.task_reference.strip(), "", idea.signature)
            self.assertIn(".", idea.occupation_code)

    def test_facets_do_not_create_new_methods(self):
        # Title, employer, location and model are facets; two ideas with the
        # same datatype, operation and use case are the same method.
        first = Idea("string", "sorting", "text_processing", "13-1081.00",
                     "Logisticians", "task", "job_title", "brief", "wrong")
        second = Idea("string", "sorting", "text_processing", "15-1252.00",
                      "Software Developers", "other task", "location", "brief 2", "wrong 2")
        self.assertEqual(first.signature, second.signature)

    def test_declared_dimensions_are_complete(self):
        # The user's named operations must be present in the vocabulary.
        for operation in ("standardization", "multiplication", "matching",
                          "linking", "monitoring", "planning", "reviewing",
                          "training_material".replace("training_material", "explanation")):
            self.assertIn(operation, OPERATIONS)
        for datatype in ("string", "string_column", "sql_table", "matrix"):
            self.assertIn(datatype, DATATYPES)
        for use_case in ("agentic_task", "agentic_benchmark", "record_linkage",
                         "database_operations", "matrix_mathematics", "training_material"):
            self.assertIn(use_case, USE_CASES)
        for facet in ("job_title", "location", "model"):
            self.assertIn(facet, FACET_DIMENSIONS)


class BatchRenderChecks(unittest.TestCase):
    def setUp(self):
        self.source = MatrixSource("onet_pinned", DEFAULT_OPPORTUNITIES)
        self.ideas = build_ideas(self.source)

    def test_batch_records_are_unique_and_candidate(self):
        batch = render_batch(self.ideas, [self.source])
        identities = [record["id"] for record in batch["ideas"]]
        signatures = [record["method_signature"] for record in batch["ideas"]]
        self.assertEqual(len(identities), len(set(identities)))
        self.assertEqual(len(signatures), len(set(signatures)))
        for record in batch["ideas"]:
            self.assertEqual(record["lifecycle"], "candidate")

    def test_batch_carries_source_digest(self):
        batch = render_batch(self.ideas, [self.source])
        self.assertTrue(batch["sources"])
        for source in batch["sources"]:
            self.assertEqual(len(source["sha256"]), 64)
            self.assertEqual(source["kind"], "onet_pinned")

    def test_batch_digest_is_stable(self):
        first = render_batch(self.ideas, [self.source])
        second = render_batch(self.ideas, [self.source])
        self.assertEqual(first["batch_sha256"], second["batch_sha256"])

    def test_command_writes_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "matrix.json"
            output.write_text("{}", encoding="utf-8")
            with self.assertRaises(MatrixError):
                main(["--output", str(output)])

    def test_command_produces_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "matrix.json"
            code = main(["--output", str(output)])
            self.assertEqual(code, 0)
            batch = json.loads(output.read_text(encoding="utf-8"))
            self.assertGreater(batch["idea_count"], 0)
            self.assertEqual(batch["idea_count"], batch["unique_method_signatures"])


if __name__ == "__main__":
    unittest.main()