"""The unattended search timer receives only its selected provider credential."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from query_multiplier.install_schedule import SERVICE, start_command
from query_multiplier import scheduled_credentials, install_schedule
from operator_credentials import CredentialError


class ScheduleCredential(unittest.TestCase):
    def test_active_timer_or_pass_is_refused_before_pinning_or_writes(self):
        for active in ("active", "activating", "reloading", "deactivating"):
            for suffix in ("timer", "service"):
                def answer(command, **kwargs):
                    from types import SimpleNamespace
                    state = active if command[3].endswith("." + suffix) else "inactive"
                    return SimpleNamespace(stdout="LoadState=loaded\nActiveState=" + state + "\n")
                with self.subTest(active=active, suffix=suffix), patch.object(
                        install_schedule.subprocess, "run", side_effect=answer), patch.object(
                        install_schedule, "pin") as pin, self.assertRaises(SystemExit):
                    install_schedule.main(["--revision", "HEAD"])
                pin.assert_not_called()

    def test_inactive_or_missing_units_allow_an_installation(self):
        from types import SimpleNamespace
        for load in ("loaded", "not-found"):
            with patch.object(install_schedule.subprocess, "run", return_value=SimpleNamespace(
                    stdout="LoadState=" + load + "\nActiveState=inactive\n")):
                install_schedule.require_stopped_schedule()

    def test_unknown_unit_state_is_not_treated_as_inactive(self):
        from types import SimpleNamespace
        with patch.object(install_schedule.subprocess, "run", return_value=SimpleNamespace(stdout="")), self.assertRaises(SystemExit):
            install_schedule.require_stopped_schedule()

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
