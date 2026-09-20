"""Read-only OpenCode connection qualification without starting a model turn.

Temporary command-scoped configuration disables other discovered servers.
The service token comes from the system keyring and is never saved or printed.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from measure_service_latency import validated_origin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--authorize-connection-check", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    host = validated_origin(args.origin)
    if not args.authorize_connection_check or args.output.exists():
        parser.error("Explicit connection authority and a new report path are required")
    report = {"record_type": "native_client_connection_check/v1", "client": "opencode",
              "origin": args.origin, "observed_at": datetime.now(timezone.utc).isoformat(),
              "model_turns_started": 0, "file_bodies_requested": 0, "persistent_client_configuration_changed": False,
              "scope": "Native client startup handshake and tool discovery only; not native material loading or task success",
              "checks": []}
    root = Path(__file__).resolve().parents[1]
    recipe = next(row for row in json.loads((root / "src/loop_engine/core/service_runtime/web_assets/client-recipes.json").read_text())["recipes"] if row["id"] == "opencode")
    baseline = {"autoupdate": False, "plugin": [], "share": "disabled"}
    environment = dict(os.environ)
    def command(arguments, config):
        environment["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
        return subprocess.run(["opencode", *arguments, "--pure"], cwd=working, env=environment,
                              capture_output=True, text=True, timeout=50)
    try:
        version = subprocess.run(["opencode", "--version"], capture_output=True, text=True, timeout=10)
        report["client_version"] = version.stdout.strip() if re.fullmatch(r"[0-9.]+\s*", version.stdout) else "unknown"
        with tempfile.TemporaryDirectory(prefix="native-connection-", dir=root / ".loop-engine-dev") as working:
            discovered = command(["debug", "config"], baseline)
            if discovered.returncode:
                raise RuntimeError("configuration_discovery_failed")
            existing = json.loads(discovered.stdout).get("mcp", {})
            config = {**baseline, "mcp": {name: {"enabled": False} for name in existing}}
            selected = recipe["configuration"]["mcp"]["baltor"]
            config["mcp"]["baltor_connection_probe"] = {**selected, "url": args.origin + "/mcp"}
            resolved = command(["debug", "config"], config)
            effective = json.loads(resolved.stdout).get("mcp", {})
            enabled = [name for name, value in effective.items() if value.get("enabled", True)]
            if resolved.returncode or enabled != ["baltor_connection_probe"]:
                raise RuntimeError("unrelated_servers_not_isolated")
            report["checks"].append({"name": "only_the_declared_server_is_enabled", "passed": True})
            import secretstorage
            collection = secretstorage.get_default_collection(secretstorage.dbus_init())
            items = list(collection.search_items({"application": "loop-engine", "service": host,
                                                 "account": args.account, "purpose": "service-access"}))
            if len(items) != 1:
                raise RuntimeError("credential_reference_unavailable")
            token = items[0].get_secret().decode()
            environment["BALTOR_SERVICE_TOKEN"] = token
            result = command(["mcp", "list"], config)
            text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", result.stdout + "\n" + result.stderr).replace(token, "[redacted]")
            # Keep only the selected native status line, never configuration output.
            lines = [line.strip() for line in text.splitlines() if "baltor_connection_probe" in line]
            report["native_status_lines"] = [line[:250] for line in lines]
            report["process_exit_code"] = result.returncode
            connected = bool(lines) and any(re.search(r"\bconnected\b", line, re.I) for line in lines)
            report["checks"].append({"name": "native_client_reports_connected", "passed": result.returncode == 0 and connected})
            if not connected:
                report["failure_excerpt"] = "\n".join(line for line in text.splitlines() if re.search(r"failed|error|unsupported|handshake", line, re.I))[:1000]
    except Exception as error:
        report["checks"].append({"name": "bounded_connection_journey_completed", "passed": False, "error_type": type(error).__name__})
    report["all_passed"] = bool(report["checks"]) and all(row["passed"] for row in report["checks"])
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2); stream.write("\n")
    print(json.dumps(report))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
