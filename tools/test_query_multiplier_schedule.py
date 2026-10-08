"""The unattended search timer receives only its selected provider credential."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from query_multiplier.install_schedule import SERVICE, start_command
from query_multiplier import scheduled_credentials
from operator_credentials import CredentialError


class ScheduleCredential(unittest.TestCase):
    def test_unconfigured_schedule_keeps_public_lanes_available(self):
        self.assertEqual(start_command('/pinned', 2040),
                         '/bin/bash /pinned/tools/query_multiplier/scheduled-run.sh')

    def test_selected_reference_is_resolved_at_run_time(self):
        refs = {'api_keys': {'ollama-cloud-search': {'service': 'ollama-cloud', 'environment': 'OLLAMA_API_KEY'}}}
        command = start_command('/pinned', 2040, 'ollama-cloud-search', references=refs)
        unit = SERVICE.format(short='reviewed', checkout='/pinned', home='/owner', root='/private',
                              minutes=20, timeout=2100, start_command=command)
        self.assertIn('scheduled_credentials.py --ref ollama-cloud-search --timeout 2040', unit)
        self.assertNotIn('OLLAMA_API_KEY=', unit)
        self.assertIn('ExecStopPost=/bin/bash /pinned/tools/query_multiplier/scheduled-run.sh --finish', unit)

    def test_foreign_provider_and_injected_unit_line_are_refused(self):
        refs = {'api_keys': {'foreign': {'service': 'stripe', 'environment': 'STRIPE_API_KEY'},
                            'misbound': {'service': 'stripe', 'environment': 'OLLAMA_API_KEY'}}}
        for name in ('foreign', 'misbound', 'unknown', 'ollama\nExecStart=unexpected'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                start_command('/pinned', 2040, name, references=refs)

    def test_long_scheduled_pass_uses_fixed_command_and_existing_resolver(self):
        with patch.object(scheduled_credentials, 'validate_ollama_reference'), patch.object(
                scheduled_credentials, 'run_with_credentials', return_value=0) as run:
            self.assertEqual(scheduled_credentials.main(['--ref', 'ollama-cloud-search', '--timeout', '2040']), 0)
        names, command, timeout = run.call_args.args
        self.assertEqual(names, ['ollama-cloud-search'])
        self.assertEqual(timeout, 2040)
        self.assertEqual(command[0], '/bin/bash')
        self.assertTrue(command[1].endswith('/query_multiplier/scheduled-run.sh'))

    def test_post_dispatch_timeout_never_starts_a_public_fallback_pass(self):
        with patch.object(scheduled_credentials, 'validate_ollama_reference'), patch.object(
                scheduled_credentials, 'run_with_credentials', side_effect=CredentialError(
                    'child_timed_out_external_outcome_unknown_do_not_repeat')), patch.object(
                scheduled_credentials.subprocess, 'run') as fallback:
            self.assertEqual(scheduled_credentials.main(['--ref', 'ollama-cloud-search', '--timeout', '2040']), 2)
        fallback.assert_not_called()

    def test_missing_key_keeps_public_lanes_and_does_not_use_an_ambient_key(self):
        with (patch.object(scheduled_credentials, 'validate_ollama_reference'), patch.object(
                scheduled_credentials, 'run_with_credentials', side_effect=CredentialError('workstation_keyring_locked')),
                patch.object(scheduled_credentials.subprocess, 'run') as fallback):
            fallback.return_value.returncode = 0
            self.assertEqual(scheduled_credentials.main(['--ref', 'ollama-cloud-search', '--timeout', '2040']), 0)
        self.assertNotIn('OLLAMA_API_KEY', fallback.call_args.kwargs['env'])


if __name__ == '__main__':
    unittest.main()
