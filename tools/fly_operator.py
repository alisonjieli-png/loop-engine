"""Run an operator-selected Fly command with a named system-keyring credential.

This local development helper is not a public API or a Loop credential
resolver. It does not print the credential, add it to command arguments, or
silently retry an external mutation. Run with the system Python interpreter.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True)
    parser.add_argument("--purpose", choices=("organization-deploy", "application-deploy"), default="organization-deploy")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--docker-config")
    parser.add_argument("--stdio", action="store_true", help="Replace this process with the official local Fly MCP server")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    arguments = options.arguments
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if not arguments or not 1 <= options.timeout <= 900:
        parser.error("an exact Fly command and bounded timeout are required")
    if options.stdio and arguments != ["mcp", "server"]:
        parser.error("stdio forwarding is limited to the official local MCP server")
    if (arguments[0] == "tokens" or arguments[:2] in (["auth", "token"], ["auth", "login"], ["auth", "logout"])
            or any(value == "-t" or value.startswith("--access-token") for value in arguments)):
        parser.error("credential creation, printing and argument-based authentication are not supported")
    import secretstorage
    bus = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(bus)
    if collection.is_locked():
        parser.error("system credential collection is locked")
    selected = list(collection.search_items({"application": "loop-engine", "service": "fly.io",
        "account": options.account, "purpose": options.purpose}))
    if len(selected) != 1:
        parser.error("expected exactly one saved Fly credential")
    token = selected[0].get_secret().decode("utf-8")
    environment = os.environ.copy()
    environment["FLY_API_TOKEN"] = token
    environment["FLY_ACCESS_TOKEN"] = token
    if options.docker_config:
        environment["DOCKER_CONFIG"] = options.docker_config
    if options.stdio:
        os.execvpe("fly", ["fly", "mcp", "server"], environment)
    def redact(value):
        return re.sub(r"fm2_[A-Za-z0-9+/=_-]+", "[credential suppressed]", value.replace(token, "[credential suppressed]"))
    try:
        result = subprocess.run(["fly", *arguments], env=environment, capture_output=True,
                                text=True, timeout=options.timeout)
    except subprocess.TimeoutExpired:
        print("Fly command timed out. External outcome is unknown; inspect state before retrying.", file=sys.stderr)
        return 124
    sys.stdout.write(redact(result.stdout))
    sys.stderr.write(redact(result.stderr))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
