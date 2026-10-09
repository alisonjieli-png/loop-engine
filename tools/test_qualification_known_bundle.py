"""Known-component comparison accepts complete native bundle versions and rejects tampering."""
import json
from pathlib import Path
import tempfile
import unittest

from tools import qualify_generated_components as cli
import reconcile_catalogue_bundle as reconcile
from test_reconcile_catalogue_bundle import bundle, line, observation, request
from loop_engine.core.service_runtime.catalogue_segments import SEGMENTED_BUNDLE_RECORD_TYPE


class KnownBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.base = bundle(self.root / "base", [line("existing", "existing bytes")], ["existing bytes"])
        self.addition = bundle(self.root / "addition", [line("added", "new bytes")], ["new bytes"])
        self.segmented = self.root / "segmented"
        reconcile.write_reconciled(self.base, (self.addition,), request(self.base, additions=("added",)),
            self.segmented, observation(self.base), bundle_format=SEGMENTED_BUNDLE_RECORD_TYPE,
            segment_target=16)

    def test_complete_segmented_bundle_is_compared_without_flat_items_file(self):
        self.assertFalse((self.segmented / "items.jsonl").exists())
        expected = {entry.item.digest: entry.identity
                    for entry in reconcile.load_bundle(self.segmented, ("MIT",)).items}
        self.assertEqual(cli._known_digests(self.segmented), expected)

    def test_flat_bundle_preserves_the_exact_reference_digests(self):
        expected = {entry.item.digest: entry.identity for entry in self.base.items}
        self.assertEqual(cli._known_digests(self.base.folder), expected)
        self.assertEqual(cli._known_digests(None), {})

    def test_changed_flat_item_is_not_trusted_as_a_known_component(self):
        path = self.base.folder / "items.jsonl"
        row = json.loads(path.read_text())
        row["reference"]["digest"] = "a" * 64
        path.write_text(json.dumps(row) + "\n")
        with self.assertRaises(Exception):
            cli._known_digests(self.base.folder)

    def test_missing_carried_segment_is_not_partial_global_coverage(self):
        digest = reconcile.load_bundle(self.segmented, ("MIT",)).segments[0].digest
        (self.segmented / "segments" / "sha256" / digest[:2] / digest).unlink()
        with self.assertRaises(Exception):
            cli._known_digests(self.segmented)


if __name__ == "__main__":
    unittest.main()
