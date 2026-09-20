"""Reuse named Baltor credentials from Secret Service without exporting secrets.

Run with system Python. Inventory and configuration output contain references
only. The headers command is a machine-only Claude Code headersHelper; never
run it in a chat tool or save its output. Operator use is not a runtime grant.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = Path(__file__).with_suffix(".json")


class CredentialError(RuntimeError):
    """A sanitized credential or connection error, with no provider body."""


def references():
    data = json.loads(REFERENCES.read_text("utf-8"))
    if data.get("record_type") != "operator_credential_references/v1":
        raise CredentialError("unsupported_reference_manifest")
    return data


def collection():
    import secretstorage
    held = secretstorage.get_default_collection(secretstorage.dbus_init())
    if held.is_locked():
        raise CredentialError("workstation_keyring_locked")
    return held


def select_item(saved, name, data):
    if name in data["api_keys"]:
        spec = data["api_keys"][name]
        attrs = {"application": "loop-engine", **{key: spec[key] for key in ("service", "account", "purpose")}}
        selected = list(saved.search_items(attrs))
    elif name in data["oauth"]:
        spec = data["oauth"][name]
        selected = [item for item in saved.get_all_items()
                    if item.get_label().startswith(spec["server_name"] + "|")
                    and "Codex MCP Credentials" in item.get_label()]
    else:
        raise CredentialError("unknown_credential_reference")
    if len(selected) != 1:
        raise CredentialError("credential_missing_or_ambiguous")
    return selected[0]


def validated_oauth(item, spec):
    try:
        held = json.loads(item.get_secret())
        if (held["server_name"] != spec["server_name"] or held["issuer"] != spec["issuer"]
                or held["url"] != spec["url"] or not isinstance(held["client_id"], str)
                or not held["client_id"] or type(held["expires_at"]) not in (int, float)):
            raise CredentialError("oauth_binding_mismatch")
        clean_token(held["token_response"]["access_token"])
        if not set(spec.get("required_scopes", ())) <= set(held["token_response"].get("scope", "").split()):
            raise CredentialError("required_oauth_scopes_not_granted")
        return held
    except (ValueError, KeyError, TypeError):
        raise CredentialError("invalid_saved_oauth_record") from None


def clean_token(value):
    if (not isinstance(value, str) or not value or not value.isascii() or len(value) > 32768
            or re.search(r"[\x00-\x1f\x7f]", value)):
        raise CredentialError("invalid_credential_value")
    return value


def validate_api_token(value, spec):
    value = clean_token(value)
    prefixes = spec.get("required_prefixes", [])
    if prefixes and not any(value.startswith(prefix) for prefix in prefixes):
        raise CredentialError("credential_mode_or_type_mismatch")
    if spec.get("value_pattern") and not re.fullmatch(spec["value_pattern"], value):
        raise CredentialError("masked_or_invalid_credential_value")
    return value


def request_refresh(spec, held):
    import httpx
    body = {"grant_type": "refresh_token", "refresh_token": held["token_response"].get("refresh_token", ""),
            "client_id": held["client_id"]}
    if not body["refresh_token"]:
        raise CredentialError("reauthorization_required_no_refresh_token")
    try:
        with httpx.Client(timeout=6, follow_redirects=False, trust_env=False) as client:
            with client.stream("POST", spec["token_endpoint"], data=body) as response:
                if response.status_code != 200:
                    raise CredentialError("token_refresh_refused_" + str(response.status_code))
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 32768:
                        raise CredentialError("token_refresh_response_too_large")
                result = json.loads(raw)
    except (httpx.HTTPError, ValueError):
        raise CredentialError("token_refresh_unavailable") from None
    return result


def renew(item, spec, held, now, refresh=request_refresh):
    """Persist a rotated grant in the same keyring item, not another store."""
    result = refresh(spec, held)
    if (not isinstance(result, dict) or str(result.get("token_type", "")).lower() != "bearer"
            or type(result.get("expires_in")) not in (int, float)
            or not 30 <= result["expires_in"] <= 365 * 86400):
        raise CredentialError("invalid_token_refresh_result")
    clean_token(result.get("access_token"))
    if "refresh_token" in result:
        clean_token(result["refresh_token"])
    previous = held["token_response"]
    if (result.get("scope") and previous.get("scope")
            and not set(result["scope"].split()) <= set(previous["scope"].split())):
        raise CredentialError("token_refresh_scope_expansion")
    if result.get("resource") and result["resource"] != previous.get("resource", spec["url"]):
        raise CredentialError("token_refresh_resource_mismatch")
    effective_scope = result.get("scope", previous.get("scope", ""))
    if not set(spec.get("required_scopes", ())) <= set(effective_scope.split()):
        raise CredentialError("required_oauth_scopes_not_granted")
    updated = {**held, "token_response": {**previous, **result}, "expires_at": int((now + result["expires_in"]) * 1000)}
    item.set_secret(json.dumps(updated).encode())
    return updated


def resolve(name, saved=None, data=None):
    data = data or references()
    saved = saved or collection()
    item = select_item(saved, name, data)
    if name in data["api_keys"]:
        return validate_api_token(item.get_secret().decode(), data["api_keys"][name])
    spec = data["oauth"][name]
    held = validated_oauth(item, spec)
    if held["expires_at"] / 1000 > time.time() + 30:
        return held["token_response"]["access_token"]
    folder = ROOT / ".loop-engine-dev" / "operator-auth-locks"
    if folder.is_symlink() or folder.parent.is_symlink():
        raise CredentialError("unsafe_refresh_lock_path")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if folder.stat().st_uid != os.getuid() or folder.stat().st_mode & 0o077:
        raise CredentialError("unsafe_refresh_lock_permissions")
    fd = os.open(folder / (name + ".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_uid != os.getuid() or os.fstat(fd).st_mode & 0o077:
            raise CredentialError("unsafe_refresh_lock_permissions")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise CredentialError("refresh_in_progress_reconnect_later") from None
        held = validated_oauth(item, spec)
        if held["expires_at"] / 1000 <= time.time() + 30:
            held = renew(item, spec, held, time.time())
        return held["token_response"]["access_token"]
    finally:
        os.close(fd)


def headers(name, environment, resolver=resolve, data=None):
    data = data or references()
    spec = data["mcp"].get(name)
    if (spec is None or environment.get("CLAUDE_CODE_MCP_SERVER_NAME") != name
            or environment.get("CLAUDE_CODE_MCP_SERVER_URL") != spec["url"]):
        raise CredentialError("refused_unbound_headers_helper")
    binding = data["oauth"].get(spec["credential"]) or data["api_keys"].get(spec["credential"], {})
    if spec["url"] != binding.get("mcp_url", binding.get("url")):
        raise CredentialError("credential_destination_mismatch")
    return {"Authorization": "Bearer " + resolver(spec["credential"])}


def claude_configuration(data=None):
    data = data or references()
    helper = shlex.quote(str(Path(__file__).resolve()))
    servers = {name: {"type": "http", "url": spec["url"],
                      "headersHelper": "/usr/bin/python3 " + helper + " headers " + shlex.quote(name)}
               for name, spec in data["mcp"].items()}
    servers["baltor-fly"] = {"type": "stdio", "command": "/usr/bin/python3",
                             "args": [str(ROOT / "tools/fly_operator.py"), "--account", "baltor", "--stdio", "--", "mcp", "server"]}
    for name, spec in data.get("native_mcp", {}).items():
        if name in servers:
            raise CredentialError("duplicate_connection_name")
        if (set(spec) != {"type", "url", "oauth"} or spec["type"] != "http"
                or not spec["url"].startswith("https://")
                or set(spec["oauth"]) != {"authServerMetadataUrl", "scopes"}
                or not spec["oauth"]["authServerMetadataUrl"].startswith("https://")):
            raise CredentialError("invalid_native_connection_configuration")
        servers[name] = {"type": "http", "url": spec["url"], "oauth": dict(spec["oauth"])}
    return {"mcpServers": servers}


def run_with_credentials(names, command, timeout, data=None):
    data = data or references()
    if not command:
        raise CredentialError("a_trusted_child_command_is_required")
    variables, secrets = {}, []
    for name in names:
        spec = data["api_keys"].get(name) or data["oauth"].get(name)
        if spec is None or spec["environment"] in variables:
            raise CredentialError("unknown_or_conflicting_credential_selection")
        value = resolve(name, data=data)
        variables[spec["environment"]] = value
        secrets.append(value)
    try:
        child = subprocess.run(command, env={**os.environ, **variables}, capture_output=True,
                               text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CredentialError("child_timed_out_external_outcome_unknown_do_not_repeat") from None
    for channel, output in ((sys.stdout, child.stdout), (sys.stderr, child.stderr)):
        for value in sorted(secrets, key=len, reverse=True):
            output = output.replace(value, "[credential suppressed]")
        channel.write(output)
    return child.returncode


def store_api_reference(name, value, saved=None, data=None):
    """Store a newly supplied reference; existing credentials are never overwritten."""
    data = data or references()
    saved = saved or collection()
    spec = data["api_keys"].get(name)
    if spec is None:
        raise CredentialError("only_declared_api_references_can_be_stored")
    value = validate_api_token(value, spec)
    attributes = {"application": "loop-engine", **{key: spec[key] for key in ("service", "account", "purpose")}}
    if list(saved.search_items(attributes)):
        raise CredentialError("existing_credential_preserved_no_overwrite")
    saved.create_item("Baltor operator / " + name, attributes, value.encode(), replace=False)
    held = select_item(saved, name, data)
    if held.get_secret().decode() != value:
        raise CredentialError("credential_storage_not_confirmed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("inventory")
    sub.add_parser("claude-config")
    put = sub.add_parser("store"); put.add_argument("--ref", required=True)
    h = sub.add_parser("headers"); h.add_argument("server")
    r = sub.add_parser("run"); r.add_argument("--ref", action="append", required=True)
    r.add_argument("--timeout", type=int, default=120); r.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.operation == "store":
            if not sys.stdin.isatty() or not sys.stderr.isatty():
                raise CredentialError("store_requires_your_interactive_terminal")
            import getpass
            value = getpass.getpass("Credential (hidden; saved to the system keyring): ")
            store_api_reference(args.ref, value)
            print(json.dumps({"reference": args.ref, "stored": True, "secret_printed": False})); return 0
        if args.operation == "claude-config":
            print(json.dumps(claude_configuration(), indent=2)); return 0
        if args.operation == "headers":
            if sys.stdout.isatty():
                raise CredentialError("headers_output_requires_a_bound_machine_pipe")
            print(json.dumps(headers(args.server, os.environ))); return 0
        if args.operation == "run":
            if not 1 <= args.timeout <= 300:
                raise CredentialError("timeout_out_of_range")
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            return run_with_credentials(args.ref, command, args.timeout)
        data, saved = references(), collection()
        rows = []
        for name in [*data["api_keys"], *data["oauth"]]:
            try:
                item = select_item(saved, name, data)
                row = {"reference": name, "present": True}
                if name in data["oauth"]:
                    held = validated_oauth(item, data["oauth"][name])
                    row.update(expires_at_ms=held["expires_at"], expired=held["expires_at"] / 1000 <= time.time(),
                               refresh_available=bool(held["token_response"].get("refresh_token")))
                else:
                    validate_api_token(item.get_secret().decode(), data["api_keys"][name])
                    row["format_valid"] = True
            except CredentialError as error:
                row = {"reference": name, "present": False, "reason": str(error)}
            rows.append(row)
        print(json.dumps({"references": rows, "excluded": data["excluded"], "secret_values_exported": False}, indent=2))
        return 0
    except CredentialError as error:
        print(str(error), file=sys.stderr); return 2
    except Exception:
        print("credential_operation_failed_without_disclosing_details", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
