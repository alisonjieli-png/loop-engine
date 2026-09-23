"""Temporary signup passwords meet every admitted host minimum without disclosure."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from loop_engine.core.service_runtime import account_email


class GeneratedSignupPasswordPolicy(unittest.TestCase):
    def usable_for_every_supported_minimum(self):
        generated = [account_email.generated_signup_password() for _ in range(16)]
        return (len(set(generated)) == len(generated)
                and all(value.isascii() and 72 <= len(value.encode()) <= account_email.MAXIMUM_PASSWORD_BYTES
                        and all(any(char in group for char in value) for group in account_email.GENERATED_PASSWORD_GROUPS)
                        for value in generated))

    def test_random_signup_secret_covers_the_largest_admitted_minimum(self):
        self.assertTrue(self.usable_for_every_supported_minimum(), "generated secret is below an admitted host minimum")

    def test_reducing_random_bytes_to_the_old_count_is_detected(self):
        with patch.object(account_email, "GENERATED_PASSWORD_BYTES", 32):
            self.assertFalse(self.usable_for_every_supported_minimum())


if __name__ == "__main__":
    unittest.main()
