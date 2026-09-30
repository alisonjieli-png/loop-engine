"""A dated, source-linked MCP shortlist on the existing website.

GitHub stars are one public traction signal, not quality, active use or
Baltor adoption. Refresh is explicit, read-only and bounded to listed repos.
No repository text, private account data or credentials enter the snapshot.
"""
from __future__ import annotations

import argparse
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/loop_engine/core/service_runtime/web_assets"
DATA = ASSETS / "top-mcps.json"
PAGE = ASSETS / "index.html"
BEGIN, END = "<!-- generated:top-mcps -->", "<!-- /generated:top-mcps -->"


def validate(value):
    if value.get("record_type") != "mcp_shortlist/v1" or value.get("baltor_usage_state") != "not_measured":
        raise ValueError("unsupported_shortlist_or_unsubstantiated_usage")
    date.fromisoformat(value["checked_at"])
    identities = set()
    if not 1 <= len(value["items"]) <= 20:
        raise ValueError("shortlist_size")
    for row in value["items"]:
        repository = row["repository"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or repository in identities:
            raise ValueError("invalid_or_repeated_repository")
        if type(row["stars"]) is not int or row["stars"] < 0 or type(row["archived"]) is not bool:
            raise ValueError("unmeasured_popularity")
        if row["source"] != "https://github.com/" + repository or row["docs"] != row["source"] + "#readme":
            raise ValueError("source_mismatch")
        if row["relationship"] not in ("publisher", "community"):
            raise ValueError("publisher_relationship_unknown")
        for field in ("name", "publisher", "task", "reason", "caution"):
            if not isinstance(row[field], str) or not 1 <= len(row[field]) <= 500:
                raise ValueError("shortlist_text_invalid")
        identities.add(repository)
    return value


def render(value):
    validate(value)
    checked = escape(value["checked_at"])
    rows = sorted((row for row in value["items"] if not row["archived"]), key=lambda row: (-row["stars"], row["name"]))
    cards = []
    for index, row in enumerate(rows, 1):
        name, task, reason, caution, publisher, source, docs = (escape(row[field], quote=True) for field in
                                                              ("name", "task", "reason", "caution", "publisher", "source", "docs"))
        relationship = "Publisher-maintained" if row["relationship"] == "publisher" else "Community integration"
        cards.append(f'<li class="mcp-pick" data-mcp-repository="{escape(row["repository"])}"><div class="mcp-pick-heading"><span class="mcp-pick-rank">{index:02}</span><div><h2>{name}</h2><p>{task}</p></div></div><p>{reason}</p><dl class="mcp-pick-facts"><div><dt>GitHub stars</dt><dd>{row["stars"]:,}</dd></div><div><dt>Maintainer</dt><dd>{publisher}</dd></div></dl><p class="caption">{relationship} · Checked {checked}</p><p class="mcp-pick-caution">{caution}</p><div class="case-links"><a class="text-link" href="{docs}" rel="noopener noreferrer" target="_blank">Setup and documentation</a><a class="text-link" href="{source}" rel="noopener noreferrer" target="_blank">Source and activity</a></div></li>')
    return f'<p class="mcp-shortlist-date">Public repository signals checked <time datetime="{checked}">{checked}</time>. Stars rank this shortlist only.</p><ol class="mcp-shortlist">' + "\n".join(cards) + '</ol>'


def refresh(value, runner=subprocess.run):
    validate(value)
    updated = json.loads(json.dumps(value))
    for row in updated["items"]:
        result = runner(["gh", "api", "repos/" + row["repository"], "--jq",
                         "{full_name,html_url,stargazers_count,archived}"], capture_output=True, text=True,
                        timeout=30, check=True)
        facts = json.loads(result.stdout)
        if facts["full_name"].casefold() != row["repository"].casefold() or facts["html_url"].casefold() != row["source"].casefold():
            raise ValueError("repository_moved_requires_review")
        row["stars"], row["archived"] = facts["stargazers_count"], facts["archived"]
    updated["checked_at"] = date.today().isoformat()
    return validate(updated)


def built_page(value, current):
    if current.count(BEGIN) != 1 or current.count(END) != 1:
        raise ValueError("shortlist_marker_mismatch")
    before, tail = current.split(BEGIN)
    _previous, after = tail.split(END)
    return before + BEGIN + "\n" + render(value) + "\n" + END + after


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--authorize-network-reads", action="store_true")
    args = parser.parse_args(argv)
    value = json.loads(DATA.read_text())
    if args.refresh:
        if args.check or not args.authorize_network_reads:
            parser.error("refresh needs explicit network authority and cannot be a check")
        value = refresh(value)
    current = PAGE.read_text()
    built = built_page(value, current)
    if args.check:
        return 0 if current == built else 1
    if args.refresh:
        DATA.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    PAGE.write_text(built)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
