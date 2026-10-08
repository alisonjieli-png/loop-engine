"""Build a local per-agent reading profile from current curated source collections.

Default: validate and print a plan without writing. Output is profile.json
plus READING.md, not a live digest, account setting, subscription or schedule.
Reads only local packaged source definitions. No credential, model or network calls.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "src", ROOT / "tools"):
    if str(directory) not in sys.path:sys.path.insert(0, str(directory))

from knowledge_radar.feed_profiles import FORMATS, MODES, PARTIAL_POLICIES, STALE_POLICIES, FeedProfileError, ProfileRequest, inventory
from knowledge_radar.feed_profile_files import check_folder, compile_files, write_new


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--list", action="store_true", help="List current collection IDs and existing topic-group labels.")
    modes.add_argument("--check", type=Path, help="Read-only validation of an existing profile folder against the current packaged directory.")
    parser.add_argument("--agent-label")
    parser.add_argument("--collection", action="append", default=[])
    parser.add_argument("--topic", action="append", default=[], help="Exact existing group label from --list; union with selected collections.")
    parser.add_argument("--format", choices=FORMATS, dest="report_format", help="Requested future review output; default markdown. Profile files are always JSON plus Markdown.")
    parser.add_argument("--mode", choices=MODES, help="Default both; this does not schedule either review.")
    parser.add_argument("--max-items", type=int, help="Maximum distinct curated source references, not collected articles; default 20.")
    parser.add_argument("--max-bytes", type=int, help="Maximum combined profile-file bytes, 1024-65536; default 32768.")
    parser.add_argument("--max-age-days", type=int, help="Maximum documentation-review age, not upstream freshness; default 30.")
    parser.add_argument("--on-stale", choices=STALE_POLICIES, help="Default refuse; hold permits a profile that still needs source-documentation review.")
    parser.add_argument("--on-partial", choices=PARTIAL_POLICIES, help="Default refuse; disclose explicitly permits a bounded subset.")
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat(), help="Reference date; defaults to today's UTC date and does not refresh evidence.")
    parser.add_argument("--output-root", type=Path, help="Existing local folder; only a new named child may be created.")
    parser.add_argument("--name", help="New child folder name, lowercase letters/digits/hyphens.")
    parser.add_argument("--authorize-local-writes", action="store_true")
    args = parser.parse_args(argv)
    build_options = (args.report_format, args.mode, args.max_items, args.max_bytes, args.max_age_days, args.on_stale, args.on_partial)
    if (args.list or args.check) and (args.agent_label or args.collection or args.topic or args.output_root or args.name or args.authorize_local_writes
                                    or any(value is not None for value in build_options)):
        parser.error("listing/checking cannot also build or write a profile")
    if args.authorize_local_writes and not (args.output_root and args.name):parser.error("writes require --output-root and --name")
    if bool(args.output_root) != bool(args.name):parser.error("--output-root and --name go together")
    try:
        if args.list:report = inventory()
        elif args.check:report = check_folder(args.check, as_of=args.as_of)
        else:
            if not args.agent_label:parser.error("building needs --agent-label and a collection or topic")
            request = ProfileRequest(args.agent_label, tuple(args.collection), tuple(args.topic), args.report_format or "markdown",
                args.mode or "both", 20 if args.max_items is None else args.max_items, 32768 if args.max_bytes is None else args.max_bytes,
                30 if args.max_age_days is None else args.max_age_days, args.on_stale or "refuse", args.on_partial or "refuse", args.as_of)
            profile, bodies, native = compile_files(request)
            output = write_new(args.output_root, args.name, bodies, authorized=True) if args.authorize_local_writes else None
            report = {"record_type": "agent_feed_profile_build/v1", "status": "written" if output else "validated_only",
                "profile_digest": profile["profile_digest"], "directory": profile["source_directory"], "coverage": profile["coverage"],
                "freshness": profile["freshness"], "native_package": native, "output": str(output) if output else None,
                "network_calls": 0, "hosted_settings_saved": False, "scheduled": False}
    except (ValueError, OSError) as error:
        print(json.dumps({"status": "refused", "reason": error.code if isinstance(error, FeedProfileError) else type(error).__name__,
                          "recovery": "No existing file was overwritten. If a write failed, retain its partial folder and choose a new name."}))
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 2 if report.get("status") == "needs_source_docs_recheck" else 0


if __name__ == "__main__":raise SystemExit(main())
