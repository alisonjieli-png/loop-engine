"""A custom provider in a settings file cannot take the name of a built-in provider.

Ported from cab477d of the September 23, 2026 branch archive. A settings file could declare a custom provider called
mistral, openrouter or ollama_cloud: the refusal lived only in register_endpoint, which the settings loader never
reaches, so `loop-engine settings check` accepted `id: mistral` with `kind: custom` pointing at a local address and
then listed the cloud routes cloud.mistral and cloud.mistral.large as usable. A record naming that provider would then
mean a server the operator chose. ProviderSettings now refuses such an id, reading the one constant
provider_failover.BUILTIN_PROVIDER_NAMES that register_endpoint and unregister_endpoint read too.

In the archive this check was a new entry of settings_loader.self_test(). The starter catalogue cites
src/loop_engine/core/settings_loader.py and pins its exact bytes, so that file stays as it is and the check lives
here, where the continuous integration tools stage runs it.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.custom_endpoint import CustomEndpoint, EndpointError, register_endpoint  # noqa: E402
from loop_engine.core.provider_failover import PROVIDERS  # noqa: E402
from loop_engine.core.runtime_settings import SettingsError  # noqa: E402
from loop_engine.core.settings_loader import runtime_settings_from_mapping  # noqa: E402


def custom_provider(identity):
    return {"models": {"providers": [{"id": identity, "kind": "custom", "endpoint": "http://localhost:11434/v1",
                                      "model": "qwen2.5:7b", "locality": "local"}]}}


class BuiltInProviderNameTests(unittest.TestCase):
    def test_a_custom_provider_cannot_take_a_built_in_provider_name(self):
        # The names are read from PROVIDERS rather than from BUILTIN_PROVIDER_NAMES, so that emptying that constant,
        # which would disable the guard, cannot also empty the population this check walks.
        taken = sorted(PROVIDERS)
        self.assertGreaterEqual(len(taken), 3, taken)
        for name in taken:
            with self.subTest(name=name):
                with self.assertRaises(SettingsError) as refused:
                    runtime_settings_from_mapping(custom_provider(name))
                self.assertIn("built-in provider", str(refused.exception))

    def test_a_built_in_provider_and_a_custom_provider_with_its_own_name_still_load(self):
        builtin = runtime_settings_from_mapping({"models": {"providers": [
            {"id": "mistral", "kind": "builtin", "credential_env": "MISTRAL_API_KEY"}]}})
        self.assertEqual(builtin.models.providers[0].kind, "builtin")
        own = runtime_settings_from_mapping(custom_provider("local_ollama"))
        self.assertEqual((own.models.providers[0].provider_id, own.models.providers[0].kind), ("local_ollama", "custom"))

    def test_the_programmatic_registration_refuses_the_same_names(self):
        for name in sorted(PROVIDERS):
            with self.subTest(name=name), self.assertRaises(EndpointError):
                register_endpoint(CustomEndpoint(name=name, base_url="http://localhost:11434/v1", model="qwen2.5:7b"))


if __name__ == "__main__":
    unittest.main()
