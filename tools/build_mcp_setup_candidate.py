"""Build a candidate through the existing radar asset/native-proposal edge. No network, admission or publication.

The source date is the publisher file's review date, not today's request clock.
Use a new private output directory. The native preparation and independent
qualification steps remain separate and require a reviewed public source revision.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]
from knowledge_radar import packages
from knowledge_radar.assets.plan_mcp_service_setup.scripts.plan_mcp_service_setup import check_table
from mcp_directory import sources
from mcp_directory.records import AUTH_BITS, REMOTE_HTTP, SECURE_SCHEME, Exclusion

ASSET = "plan_mcp_service_setup"
PUBLISHER_SOURCE = "tools/resources/mcp-directory-publisher-documentation.json"
BUILDER_SOURCE = "tools/build_mcp_setup_candidate.py"
REVIEW_DAYS = 1
PRODUCER = {"producer_identity": "OpenAI Codex MCP setup skill author", "family": "openai",
            "method_identity": "original_mcp_setup_helper/v1"}


def build_table(repository=ROOT):
    record = json.loads((Path(repository) / PUBLISHER_SOURCE).read_bytes())
    if record.get("record_type") != "mcp_directory_publisher_documentation/v1":
        raise ValueError("unsupported_publisher_record")
    checked = date.fromisoformat(record["reviewed_on"])
    review_after = (checked + timedelta(days=REVIEW_DAYS)).isoformat()
    rows = []
    for original in record["offerings"]:
        listing = sources.publisher_listing(original)
        if isinstance(listing, Exclusion):
            raise ValueError("invalid_publisher_offering")
        for location in listing.locations:
            if location.kind != REMOTE_HTTP:
                continue
            auth = ("oauth_or_key" if listing.auth & AUTH_BITS["oauth"] and listing.auth & AUTH_BITS["key"] else
                    "oauth" if listing.auth & AUTH_BITS["oauth"] else "key" if listing.auth & AUTH_BITS["key"] else
                    "none_declared" if listing.auth == AUTH_BITS["none"] else "unknown")
            prefix = SECURE_SCHEME + "://"
            rows.append({"key": listing.key, "title": listing.name, "url": prefix + location.value,
                         "documentation": prefix + listing.reference, "publisher": listing.publisher,
                         "transport": location.transport, "authentication": auth, "capabilities": listing.description,
                         "compatibility_basis": "publisher_declared", "transport_conflict": False,
                         "source_updated_at": None, "last_verified_at": checked.isoformat(), "review_after": review_after})
    if not rows:
        raise ValueError("no_publisher_documented_remote_services")
    table = {"record_type": "knowledge_radar_table/v1", "question_id": "mcp_service_setup", "as_of": checked.isoformat(),
             "valid_until": review_after, "columns": sorted(rows[0]), "rows": rows}
    check_table(table)
    return table


def proposals(repository, revision):
    table = build_table(repository)
    proposal = packages.asset_proposal(Path(repository), ASSET, as_of=table["as_of"], table=table)
    # A later table updates this job; it does not create another capability.
    proposal["id"] = "radar_helper_plan_mcp_service_setup_v1"
    # The existing generic radar builder defaults to its original author's
    # family. This new source was written by OpenAI and must not inherit it.
    proposal["producer"] = dict(PRODUCER)
    proposal["sources"] += [PUBLISHER_SOURCE, BUILDER_SOURCE]
    return packages.proposals_record(Path(repository), revision, [proposal]), table


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write", action="store_true")
    options = parser.parse_args(argv)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    clean = not status.stdout.strip()
    proposal, table = proposals(ROOT, revision)
    summary = {"record_type": "mcp_setup_candidate_build/v1", "source_revision": revision,
               "candidate_packages": len(proposal["proposals"]), "source_rows": len(table["rows"]),
               "producer_family": PRODUCER["family"], "approved": False, "published": False, "network_calls": 0,
               "source_binding": "committed_tree" if clean else "uncommitted_preview", "working_tree_clean": clean}
    if options.write:
        if (options.output is None or not options.output.is_absolute() or options.output.exists()
                or options.output.is_symlink() or ".." in options.output.parts
                or options.output.resolve() != options.output or not options.output.parent.is_dir()):
            raise ValueError("a_new_absolute_output_directory_is_required")
        if not clean:
            raise ValueError("commit_the_exact_source_before_writing_a_candidate")
        options.output.mkdir(parents=True, exist_ok=False)
        for name, value in (("proposals.json", proposal), ("mcp-services-table.json", table), ("build-report.json", summary)):
            with (options.output / name).open("x", encoding="utf-8") as stream:
                json.dump(value, stream, indent=2)
                stream.write("\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
