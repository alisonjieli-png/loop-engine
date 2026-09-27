"""Tests for provider key resolution behind ``--compile-provider``.

``--compile-provider`` names the exact provider a solve or a task compilation
uses. A provider declared in the settings file resolves its key from the
variable its ``credential_env`` names. A local inference server usually wants
no key at all and declares ``auth_scheme: none``; the settings file refuses a
``credential_env`` beside that scheme, so before this repair a keyless
provider had no spelling that ``--compile-provider`` accepted, and the proving
call in the overnight local-model guide was refused with "declares no
credential_env".

Each test names the known wrong behaviour it rejects. Nothing here opens a
socket or calls a model: the functions under test only read the settings file
and the process environment.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from loop_engine.cli_operations import (  # noqa: E402
    _compile_provider_key, _temporary_provider_key,
)

KEY_VARIABLE = "LOOP_ENGINE_TEST_COMPILE_PROVIDER_KEY"
UNUSED_VARIABLE = "LOOP_ENGINE_TEST_COMPILE_PROVIDER_UNUSED"

SETTINGS = f"""\
models:
  providers:
    - id: test_keyless
      kind: custom
      auth_scheme: none
      locality: local
      endpoint: http://127.0.0.1:9
      model: test-model
    - id: test_needs_a_key
      kind: custom
      auth_scheme: bearer
      endpoint: https://gateway.example.test/v1/chat/completions
      model: test-model
    - id: test_with_a_key
      kind: custom
      credential_env: {KEY_VARIABLE}
      endpoint: https://gateway.example.test/v1/chat/completions
      model: test-model
"""


class CompileProviderKeyChecks(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="compile-provider-keys-")
        self.settings = Path(self.folder.name) / "settings.yaml"
        self.settings.write_text(SETTINGS, encoding="utf-8")
        self.saved = {name: os.environ.get(name)
                      for name in (KEY_VARIABLE, UNUSED_VARIABLE)}
        for name in self.saved:
            os.environ.pop(name, None)

    def tearDown(self):
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.folder.cleanup()

    def _args(self, provider: str, **overrides) -> SimpleNamespace:
        values = {"compile_provider": provider, "provider_key_env": "",
                  "prompt_for_provider_key": False,
                  "settings_file": str(self.settings)}
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_a_keyless_settings_provider_is_selectable_and_installs_no_variable(self):
        before = dict(os.environ)
        variable, key = _compile_provider_key(self._args("test_keyless"))
        self.assertEqual((variable, key), ("", ""),
                         "a provider declaring auth_scheme none sends no credential")
        with _temporary_provider_key(variable, key):
            self.assertEqual(dict(os.environ), before,
                             "nothing may be placed in the environment for it")
        self.assertEqual(dict(os.environ), before)

    def test_a_key_supplied_for_a_keyless_provider_is_refused(self):
        os.environ[UNUSED_VARIABLE] = "a-key-that-would-reach-nothing"
        supplied = (
            {"provider_key_env": UNUSED_VARIABLE},
            {"prompt_for_provider_key": True},
            {"_provider_key_value": "a-key-that-would-reach-nothing"},
        )
        for overrides in supplied:
            with self.subTest(**{name: bool(value) for name, value in overrides.items()}):
                with self.assertRaises(ValueError) as refused:
                    _compile_provider_key(self._args("test_keyless", **overrides))
                self.assertIn("sends no credential", str(refused.exception))

    def test_a_credentialed_provider_naming_no_variable_is_still_refused(self):
        with self.assertRaises(ValueError) as refused:
            _compile_provider_key(self._args("test_needs_a_key"))
        self.assertIn("no credential_env", str(refused.exception))

    def test_a_settings_declared_provider_still_resolves_its_credential_env(self):
        os.environ[KEY_VARIABLE] = "test-value"
        self.assertEqual(_compile_provider_key(self._args("test_with_a_key")),
                         (KEY_VARIABLE, "test-value"))

    def test_an_undeclared_provider_is_refused(self):
        with self.assertRaises(ValueError) as refused:
            _compile_provider_key(self._args("never_declared"))
        self.assertIn("neither a builtin provider", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
