"""Keep the installed research scout's offline regressions in ordinary CI."""
from pathlib import Path
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceDiscoveryRotationTests(unittest.TestCase):
    def test_offline_scout_contracts(self):
        environment = {k: v for k, v in os.environ.items() if not k.startswith('BALTOR_RADAR_')}
        result = subprocess.run(
            [sys.executable, '-m', 'unittest', 'discover', '-s',
             str(ROOT / 'artifacts/source-discovery-2026-09-26'), '-p', 'test_*.py'],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Ran 36 tests', result.stderr)


if __name__ == '__main__':
    unittest.main()
