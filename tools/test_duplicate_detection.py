"""An email key is one well-formed address; a malformed value never matches another.

code_nodes/duplicate_detection is parked on main (forbidden_paths.json
suite_collection_exceptions), so its own checks are not collected here; this
owning check runs on main.
"""
import unittest

from loop_engine.code_nodes.duplicate_detection import (
    BLOCKING_KEYS, DuplicateFieldSpec, DuplicatePolicy, email_key, find_duplicates)
from loop_engine.code_nodes.text_conformance import load_packaged_catalogs, merge_layers


class EmailKey(unittest.TestCase):
    def test_only_one_well_formed_address_is_a_key(self):
        # Known-wrong control: any normalized value that contained "@" was a
        # key, including values the address normalizer had refused.
        for value in ("bad@", "@", "a@b", "n/a@", "x@y@z.com", "a@b.com; c@d.com", "a@b.com, c@d.com",
                      "first last@example.com", "", "nobody"):
            with self.subTest(value=value):
                self.assertEqual(email_key(value), "")
        for value, key in (("Sales@Acme.example", "sales@acme.example"),
                           ("mailto:<Ops@Example.org>", "ops@example.org"),
                           ("  a.b+c@sub.example.co  ", "a.b+c@sub.example.co")):
            with self.subTest(value=value):
                self.assertEqual(email_key(value), key)

    def test_a_shared_malformed_email_is_not_an_exact_email_match(self):
        rows = [{"id": "a", "company": "Acme Widgets", "email": "n/a@"},
                {"id": "b", "company": "Zeta Logistics", "email": "n/a@"},
                {"id": "c", "company": "Delta Freight", "email": "ops@delta.example"},
                {"id": "d", "company": "Delta Shipping", "email": "OPS@delta.example"}]
        report = find_duplicates(rows, DuplicateFieldSpec(name="company", email="email", identity="id"),
                                 DuplicatePolicy(blocking_keys=(BLOCKING_KEYS[3],)),
                                 catalogs=merge_layers((load_packaged_catalogs(),)))
        self.assertEqual([(pair.left, pair.right) for pair in report.pairs], [("c", "d")])


if __name__ == "__main__":
    unittest.main()
