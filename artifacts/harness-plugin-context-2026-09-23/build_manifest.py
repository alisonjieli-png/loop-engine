"""Inventory candidate native files; never promote or install them."""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROLES = {
    ".claude-plugin/plugin.json": ("plugin_manifest", "native_discovery"),
    "hooks/hooks.json": ("hook_configuration", "native_registration"),
    "commands/check-brief.md": ("command_definition", "native_discovery_then_explicit_invocation"),
    "agents/brief-reviewer.md": ("agent_definition", "native_discovery_then_authorized_model_invocation"),
    "scripts/session_start.py": ("hook_entrypoint", "event_invocation"),
    "scripts/check_brief.py": ("deterministic_tool", "explicit_process_invocation"),
    "scripts/protocol.py": ("tool_dependency", "entrypoint_import"),
    "contracts/brief-input.schema.json": ("input_contract", "referenced_resource"),
    "contracts/brief-output.schema.json": ("output_contract", "referenced_resource"),
    "contracts/hook-input.schema.json": ("hook_input_contract_subset", "review_resource"),
    "contracts/hook-output.schema.json": ("hook_output_contract_subset", "review_resource"),
    "contracts/example-brief.json": ("example_input", "explicit_test_input"),
    "LICENSE": ("license_notice", "package_resource"),
}


def build():
    package = ROOT / "plugin"
    if not stat.S_ISDIR(package.lstat().st_mode):
        raise ValueError("candidate package root must be a regular directory")
    paths = list(package.rglob("*"))
    actual = set()
    for path in paths:
        kind = path.lstat().st_mode
        relative = path.relative_to(package).as_posix()
        if stat.S_ISREG(kind):
            actual.add(relative)
        elif not stat.S_ISDIR(kind):
            raise ValueError("candidate nonregular path refused")
    if actual != set(ROLES):
        raise ValueError("missing or unexpected candidate file")
    files = []
    for path, (role, pickup) in sorted(ROLES.items()):
        body = (ROOT / "plugin" / path).read_bytes()
        files.append({"path": path, "role": role, "pickup": pickup,
                      "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                      "license": "MIT"})
    return {"record_type": "native_plugin_candidate_inventory/v1",
            "package_id": "baltor-focused-brief-candidate", "version": "0.1.0",
            "status": "candidate_only", "independently_approved": False,
            "hosted": False, "producer": "Codex live_baltor_review task",
            "producer_model_family": "OpenAI", "original_work": True,
            "client": {"name": "Claude Code", "observed_version": "2.1.280"},
            "logical_packages": 1, "physical_package_files": len(files),
            "approved_package_count_contribution": 0,
            "runtime_dependencies": ["Linux", "/usr/bin/python3 >=3.10, trusted immutable host interpreter"],
            "declared_effects": ["start_authorized_local_process", "read_package_source",
                                 "read_standard_input", "write_standard_output_and_error"],
            "optional_agent_effects": ["authorized_model_call"],
            "files": files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    path = ROOT / "candidate-manifest.json"
    if args.write:
        path.write_text(json.dumps(expected, indent=2) + "\n")
    elif json.loads(path.read_text()) != expected:
        raise SystemExit("candidate manifest does not match exact files")
    print(json.dumps({"logical_packages": 1, "physical_package_files": len(expected["files"]),
                      "status": "candidate_only", "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
