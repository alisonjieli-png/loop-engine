"""Check the published Compose mount as parsed configuration, without provider secrets."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'containers/worker/compose.yaml'


class WorkerComposeTests(unittest.TestCase):
    def test_tmpfs_options_belong_to_one_absolute_mount(self):
        mounts = yaml.safe_load(SOURCE.read_text())['services']['worker']['tmpfs']
        self.assertEqual(len(mounts), 1)
        target, options = mounts[0].split(':', 1)
        self.assertEqual(target, '/tmp')
        self.assertEqual(set(options.split(',')), {'rw', 'nosuid', 'size=512m'})

    def test_known_wrong_unquoted_flow_list_splits_options_into_mounts(self):
        bad = SOURCE.read_text().replace('["/tmp:rw,nosuid,size=512m"]', '[/tmp:rw,nosuid,size=512m]')
        self.assertNotEqual(bad, SOURCE.read_text())
        self.assertEqual(yaml.safe_load(bad)['services']['worker']['tmpfs'], ['/tmp:rw', 'nosuid', 'size=512m'])

    @unittest.skipUnless(shutil.which('docker'), 'Docker is not installed; YAML check still runs')
    def test_real_compose_parser_preserves_one_mount_without_credentials(self):
        # Never render the operator environment into a diagnostic. No containers are started.
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'BALTOR_UID': '65534', 'BALTOR_GID': '65534'}
        probe = subprocess.run(['docker', 'compose', 'version', '--short'], env=env, capture_output=True, timeout=15)
        if probe.returncode:
            self.skipTest('Docker Compose plugin is unavailable')
        result = subprocess.run(['docker', 'compose', '-f', str(SOURCE), 'config', '--format', 'json'],
                                cwd=ROOT, env=env, capture_output=True, timeout=30, check=True)
        worker = json.loads(result.stdout)['services']['worker']
        self.assertEqual(worker['tmpfs'], ['/tmp:rw,nosuid,size=512m'])
        self.assertTrue(worker['read_only'])
        self.assertTrue(all(value is None for value in worker.get('environment', {}).values()))


if __name__ == '__main__':
    unittest.main()
