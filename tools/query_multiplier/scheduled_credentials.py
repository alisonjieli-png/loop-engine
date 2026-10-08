"""Resolve only the scheduled search credential for the fixed, bounded research pass.

The general operator CLI keeps its five-minute command ceiling. This wrapper
owns the longer timer lifecycle, never accepts an arbitrary command, and
leaves public lanes available when the named key cannot be resolved. A timeout
after dispatch never triggers another pass.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from operator_credentials import CredentialError, run_with_credentials
from query_multiplier.install_schedule import validate_ollama_reference

MAXIMUM_SCHEDULED_SECONDS = 4200  # Longest supported 55-minute pass plus the timer's 15-minute shutdown allowance.


def run(reference, timeout):
    validate_ollama_reference(reference)
    if type(timeout) is not int or not 1 <= timeout <= MAXIMUM_SCHEDULED_SECONDS:
        raise ValueError('scheduled_timeout_out_of_range')
    command = ['/bin/bash', str(Path(__file__).with_name('scheduled-run.sh'))]
    try:
        return run_with_credentials([reference], command, timeout)
    except CredentialError as error:
        if str(error) == 'child_timed_out_external_outcome_unknown_do_not_repeat':
            raise
        # All other credential failures happen before the helper dispatches.
        # A missing selected key holds that lane; it cannot select an ambient key.
        import os
        environment = {key: value for key, value in os.environ.items() if key != 'OLLAMA_API_KEY'}
        print(json.dumps({'credential_reference': reference, 'available': False,
                          'reason': str(error), 'public_lanes_continue': True}), flush=True)
        return subprocess.run(command, env=environment, timeout=timeout, check=False).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', required=True)
    parser.add_argument('--timeout', required=True, type=int)
    args = parser.parse_args(argv)
    try:
        return run(args.ref, args.timeout)
    except (CredentialError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'state': 'stopped', 'error_class': type(error).__name__,
                          'reconcile_before_another_pass': True}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
