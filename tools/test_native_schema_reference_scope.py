"""Schema admission refuses external dynamic references without resolving them."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_review.native_prechecks import _schema


class NativeSchemaReferenceScope(unittest.TestCase):
    def check_schema(self, body):
        return _schema(SimpleNamespace(payload=json.dumps(body).encode()))

    def test_external_dynamic_reference_is_refused_even_when_nested(self):
        for reference in ("https://foreign.invalid/schema", "file:///outside/schema.json"):
            with self.subTest(reference=reference):
                body = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object", "properties": {"payload": {"$dynamicRef": reference}}}
                findings = self.check_schema(body)
                self.assertIn("native_external_schema_refused", [row[0] for row in findings])

    def test_local_dynamic_anchor_remains_supported(self):
        body = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                "$dynamicAnchor": "root", "type": "object",
                "properties": {"nested": {"$dynamicRef": "#root"}}}
        self.assertEqual(self.check_schema(body), [])


if __name__ == "__main__":
    unittest.main()
