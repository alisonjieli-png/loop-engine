"""Stage named runtime credentials as deployment secrets without showing them.

The hosted service reads provider credentials only from environment
references. This operator command copies selected credentials from the
workstation keyring to the deployment's staged secrets. Values travel on the
child's standard input, never on a command line, and are never printed. Only
runtime credentials may be staged: an operator or management credential is
refused, because the service must never hold one.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import operator_credentials  # noqa: E402

RUNTIME_PURPOSES = ("publishable-api", "secret-api", "transactional-email",
                    "runtime-test-api", "runtime-live-api", "webhook-signing")
APPLICATION = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")


class StagingError(RuntimeError):
    pass


def selected(names, data):
    """Environment name and keyring reference for each requested runtime credential."""
    pairs = {}
    for name in names:
        spec = data["api_keys"].get(name)
        if spec is None or spec.get("purpose") not in RUNTIME_PURPOSES:
            raise StagingError("only_runtime_credentials_may_be_staged:" + name)
        if spec["environment"] in pairs:
            raise StagingError("conflicting_environment_name:" + spec["environment"])
        pairs[spec["environment"]] = name
    if not pairs:
        raise StagingError("no_credential_selected")
    return pairs


def deployment_token(account):
    import secretstorage
    saved = secretstorage.get_default_collection(secretstorage.dbus_init())
    if saved.is_locked():
        raise StagingError("system_credential_collection_is_locked")
    found = list(saved.search_items({"application": "loop-engine", "service": "fly.io",
                                     "account": account, "purpose": "organization-deploy"}))
    if len(found) != 1:
        raise StagingError("expected_exactly_one_saved_deployment_credential")
    return found[0].get_secret().decode("utf-8")


def stage(application, pairs, token, resolve, run=subprocess.run, timeout=120):
    """Send NAME=value lines on standard input; report names only."""
    values = {name: resolve(reference) for name, reference in pairs.items()}
    if any(not isinstance(value, str) or not value or "\n" in value or "\r" in value for value in values.values()):
        raise StagingError("credential_value_is_not_a_single_line")
    lines = "".join(name + "=" + value + "\n" for name, value in values.items())
    command = ["fly", "secrets", "import", "--app", application, "--stage"]
    if any(value in " ".join(command) for value in values.values()):
        raise StagingError("credential_would_reach_the_command_line")
    environment = {**os.environ, "FLY_API_TOKEN": token, "FLY_ACCESS_TOKEN": token}
    try:
        done = run(command, input=lines, env=environment, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise StagingError("timed_out_external_outcome_unknown_inspect_before_repeating") from None
    output = (done.stdout or "") + (done.stderr or "")
    for secret in sorted([*values.values(), token], key=len, reverse=True):
        output = output.replace(secret, "[credential suppressed]")
    return {"exit_code": done.returncode, "staged_names": sorted(values), "output": output.strip()[-600:]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", required=True)
    parser.add_argument("--account", required=True, help="Keyring account of the deployment credential.")
    parser.add_argument("--ref", action="append", default=[], help="Named runtime credential; repeat for several.")
    parser.add_argument("--confirm-stage", action="store_true", help="Required before anything is sent.")
    options = parser.parse_args(argv)
    if not APPLICATION.fullmatch(options.app):
        parser.error("the application name is not valid")
    try:
        pairs = selected(options.ref, operator_credentials.references())
        if not options.confirm_stage:
            print(json.dumps({"dry_run": True, "would_stage": sorted(pairs), "application": options.app}))
            return 0
        result = stage(options.app, pairs, deployment_token(options.account), operator_credentials.resolve)
    except (StagingError, operator_credentials.CredentialError) as error:
        print(json.dumps({"refused": str(error)}))
        return 1
    print(json.dumps({"application": options.app, **result}))
    return 0 if result["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
