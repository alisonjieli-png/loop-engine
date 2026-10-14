"""Build and verify local multi-harness starter kits and post-cutoff drift linters.

Default behavior validates and prints a starter kit build plan without writing
to disk. Writes require --output-root, --name, and --authorize-local-writes.
No network requests, credentials, or model calls are performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "src", ROOT / "tools"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from harness_kits.builder import (
    StarterKitError,
    build_starter_kit,
    check_starter_kit_folder,
    write_starter_kit,
)
from harness_kits.catalog import (
    HARNESS_CHOICES,
    STARTER_KIT_RECORD_TYPE,
    list_starter_kits,
)
from harness_kits.drift_linters import (
    check_llm_sdk_drift,
    check_mcp_server_safety,
    check_nextjs_react19_tailwind4_drift,
    check_pydantic_v2_fastapi_drift,
    run_all_drift_linters,
)

LINTER_MAP = {
    "all": run_all_drift_linters,
    "llm_sdk_drift": check_llm_sdk_drift,
    "pydantic_v2_fastapi_drift": check_pydantic_v2_fastapi_drift,
    "nextjs_react19_tailwind4_drift": check_nextjs_react19_tailwind4_drift,
    "mcp_server_safety": check_mcp_server_safety,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--list", action="store_true", help="List all 10 AgentFoundry multi-harness starter kits.")
    modes.add_argument("--check", type=Path, help="Read-only validation of an existing starter kit folder.")
    modes.add_argument("--lint", type=Path, help="Run deterministic post-cutoff drift linters on a source file.")
    parser.add_argument("--kit", "--kit-id", dest="kit_id", help="Starter kit identifier from --list.")
    parser.add_argument(
        "--harness",
        choices=HARNESS_CHOICES,
        default="all",
        help="Target harness to generate files for; default all.",
    )
    parser.add_argument(
        "--linter",
        choices=tuple(LINTER_MAP.keys()),
        default="all",
        help="Specific drift linter to run with --lint; default all.",
    )
    parser.add_argument("--as-of", help="Reference UTC date (YYYY-MM-DD) for AgentFeeds profile validation.")
    parser.add_argument("--output-root", type=Path, help="Existing local directory under which --name is created.")
    parser.add_argument("--name", help="New child folder name (lowercase letters, digits, dots, underscores, hyphens).")
    parser.add_argument("--authorize-local-writes", action="store_true", help="Explicitly authorize writing files to disk.")
    args = parser.parse_args(argv)

    if (args.list or args.check or args.lint) and (
        args.kit_id or args.output_root or args.name or args.authorize_local_writes
    ):
        parser.error("--list, --check, and --lint cannot be combined with kit build or write options")

    if args.authorize_local_writes and not (args.output_root and args.name):
        parser.error("--authorize-local-writes requires --output-root and --name")

    if bool(args.output_root) != bool(args.name):
        parser.error("--output-root and --name must be provided together")

    try:
        if args.list:
            kits = list_starter_kits()
            report = {
                "record_type": "agent_foundry_starter_kit_inventory/v1",
                "kit_count": len(kits),
                "supported_harnesses": list(HARNESS_CHOICES),
                "kits": kits,
            }
            print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
            return 0

        if args.check:
            report = check_starter_kit_folder(args.check, as_of=args.as_of)
            print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
            return 0

        if args.lint:
            source_text = args.lint.read_text(encoding="utf-8")
            linter_fn = LINTER_MAP[args.linter]
            report = linter_fn(source_text, str(args.lint))
            print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
            return 0 if report["passed"] else 1

        if not args.kit_id:
            parser.error("building a starter kit requires --kit <kit-id>")

        bundle = build_starter_kit(args.kit_id, harness=args.harness, as_of=args.as_of)
        written_path = None
        if args.authorize_local_writes:
            written_path = write_starter_kit(
                args.output_root,
                args.name,
                bundle,
                authorized=True,
            )
        record = bundle["record"]
        report = {
            "record_type": STARTER_KIT_RECORD_TYPE,
            "status": "written" if written_path else "validated_only",
            "kit_id": record["kit_id"],
            "target_harnesses": record["target_harnesses"],
            "package_digest": record["package_digest"],
            "payload_files": record["payload_files"],
            "payload_bytes": record["payload_bytes"],
            "feed_profile": record["feed_profile"],
            "verification": record["verification"],
            "output": str(written_path) if written_path else None,
            "approved": False,
            "published": False,
            "effects_granted": [],
            "network_calls": 0,
        }
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (StarterKitError, PermissionError, ValueError, OSError) as exc:
        reason = exc.code if isinstance(exc, StarterKitError) else type(exc).__name__
        print(
            json.dumps(
                {
                    "status": "refused",
                    "reason": reason,
                    "detail": str(exc),
                    "recovery": "No existing file was overwritten. Provide valid arguments and --authorize-local-writes for a new child directory.",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
