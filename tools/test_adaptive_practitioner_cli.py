"""The OpenCode step's credential variable comes from the provider
specification, never from a name written into the command line module."""
from __future__ import annotations

import unittest

from loop_engine.adaptive_practitioner_cli import credential_environment_names


class CredentialEnvironmentNames(unittest.TestCase):
    def test_builtin_provider_names_its_own_variable(self):
        self.assertEqual(credential_environment_names("ollama-cloud/gemma4:31b"),
                         ("OLLAMA_API_KEY",))
        self.assertEqual(credential_environment_names("mistral/mistral-large"),
                         ("MISTRAL_API_KEY",))

    def test_unknown_provider_contributes_no_name(self):
        self.assertEqual(credential_environment_names("acme-local/model"), ())

    def test_explicit_names_are_added_once_and_validated(self):
        names = credential_environment_names(
            "ollama-cloud/gemma4:31b", ("ACME_TOKEN", "OLLAMA_API_KEY"))
        self.assertEqual(names, ("OLLAMA_API_KEY", "ACME_TOKEN"))
        with self.assertRaises(ValueError):
            credential_environment_names("ollama-cloud/gemma4:31b", ("not upper",))

    def test_module_source_names_no_credential_variable_by_hand(self):
        import inspect
        from loop_engine import adaptive_practitioner_cli
        source = inspect.getsource(adaptive_practitioner_cli)
        self.assertNotIn('"OLLAMA_API_KEY"', source)


if __name__ == "__main__":
    unittest.main()
