"""Rollback checks distinguish legacy schema refusal from an owner-aware image."""
import unittest
from unittest.mock import patch

import check_rollback_key_version as drill


class RollbackRefusalTests(unittest.TestCase):
    def test_each_image_profile_requires_its_exact_refusal(self):
        for owner_aware, expected in ((True, "unauthorized"), (False, "unsupported_or_corrupt_record")):
            for result in ("accepted", "reader_failed", "refused:unauthorized", "refused:unsupported_or_corrupt_record"):
                with self.subTest(profile=owner_aware, result=result):
                    self.assertEqual(drill.expected_refusal({"customer": result}, owner_aware=owner_aware),
                                     result == "refused:" + expected)

    def test_removing_refusal_validation_admits_the_known_wrong_image(self):
        unsafe = {"customer": "accepted", "host": "accepted"}
        self.assertFalse(drill.expected_refusal(unsafe, owner_aware=True))
        with patch.object(drill, "expected_refusal", return_value=True):
            self.assertTrue(drill.expected_refusal(unsafe, owner_aware=True))


if __name__ == "__main__":
    unittest.main()
