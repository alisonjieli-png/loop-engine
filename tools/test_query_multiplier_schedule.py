"""The unattended search timer receives only its selected provider credential."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from query_multiplier.install_schedule import SERVICE, start_command


class ScheduleCredential(unittest.TestCase):
    def test_unconfigured_schedule_keeps_public_lanes_available(self):
        self.assertEqual(start_command('/pinned', 2040),
                         '/bin/bash /pinned/tools/query_multiplier/scheduled-run.sh')

    def test_selected_reference_is_resolved_at_run_time(self):
        refs = {'api_keys': {'ollama-cloud-search': {'service': 'ollama-cloud', 'environment': 'OLLAMA_API_KEY'}}}
        command = start_command('/pinned', 2040, 'ollama-cloud-search', references=refs)
        unit = SERVICE.format(short='reviewed', checkout='/pinned', home='/owner', root='/private',
                              minutes=20, timeout=2100, start_command=command)
        self.assertIn('operator_credentials.py run --ref ollama-cloud-search --timeout 2040 -- /bin/bash', unit)
        self.assertNotIn('OLLAMA_API_KEY=', unit)
        self.assertIn('ExecStopPost=/bin/bash /pinned/tools/query_multiplier/scheduled-run.sh --finish', unit)

    def test_foreign_provider_and_injected_unit_line_are_refused(self):
        refs = {'api_keys': {'foreign': {'service': 'stripe', 'environment': 'STRIPE_API_KEY'},
                            'misbound': {'service': 'stripe', 'environment': 'OLLAMA_API_KEY'}}}
        for name in ('foreign', 'misbound', 'unknown', 'ollama\nExecStart=unexpected'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                start_command('/pinned', 2040, name, references=refs)


if __name__ == '__main__':
    unittest.main()
