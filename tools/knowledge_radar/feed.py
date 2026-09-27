"""The radar's index and its public teaser feeds: which questions have an answer, of what kind, until when.

The index names an honest answer state for every declared question, so a
harness is never handed the nearest popular option to hide a gap:

```text
answer states
├── approved_result_available       an independent review approved the package (never set by this pipeline)
├── candidate_available             a package was prepared and passed every deterministic check; review pending
├── needs_research                  a declared gap, or a package that failed a check other than policy
├── needs_local_evaluation          the answer depends on the caller's own constraints or data: run the tool
│                                   or helper locally
├── blocked_by_policy               a licence, safety or secret check refused the package
└── no_eligible_option_established  no claim could be verified in this run
```

The teaser feeds (JSON Feed 1.1 and RSS 2.0) carry only titles, dates,
answer states and counts composed here; the briefs themselves are served
through the catalogue to accounts that may download them.
"""
from __future__ import annotations

import json
from xml.sax.saxutils import escape

INDEX_RECORD_TYPE = "knowledge_radar_index/v1"
ANSWER_STATES = ("approved_result_available", "candidate_available", "needs_research", "needs_local_evaluation",
                 "blocked_by_policy", "no_eligible_option_established")
POLICY_KINDS = ("licence", "safety", "secrets")
PUBLIC_PAGE = "https://baltor.ai/radar"


def answer_state(question, brief: "dict | None", vetting: "dict | None", prechecks: "dict | None") -> str:
    if question.status == "declared_gap":
        return "needs_research"
    if brief is not None and brief.get("state") != "current":
        return "no_eligible_option_established"
    if prechecks is not None and prechecks.get("refused"):
        kinds = {reason.split(":", 1)[0] for reason in prechecks.get("reasons", [])}
        return "blocked_by_policy" if kinds & set(POLICY_KINDS) else "needs_research"
    if vetting is not None and "failed" in vetting["dimensions"].values():
        return "needs_research"
    if vetting is None:
        return "needs_research"
    if brief is None or "decision_helper" in question.delivery:
        return "needs_local_evaluation"
    return "candidate_available"


def index_record(registry, as_of: str, rows: list) -> dict:
    counts = {state: sum(1 for row in rows if row["answer_state"] == state) for state in ANSWER_STATES}
    return {"record_type": INDEX_RECORD_TYPE, "as_of": as_of, "registry_version": registry.registry_version,
            "questions": rows, "answer_states": counts, "approved": 0}


def _summary(row: dict) -> str:
    if row["answer_state"] == "needs_research":
        return "No answer yet: " + (row.get("gap_reason") or "the package did not pass its checks.")
    parts = [f"As of {row['as_of']}"]
    if row.get("valid_until"):
        parts.append(f"valid until {row['valid_until']}")
    parts.append(f"answer state {row['answer_state'].replace('_', ' ')}")
    if row.get("confidence"):
        parts.append(f"confidence {row['confidence']}")
    if row.get("claims") is not None:
        parts.append(f"{row['claims']} dated claims from {row['sections']} sources")
    return ", ".join(parts) + "."


def json_feed(index: dict) -> dict:
    items = []
    for row in index["questions"]:
        items.append({"id": f"{row['question_id']}@{index['as_of']}", "url": f"{PUBLIC_PAGE}#{row['question_id']}",
                      "title": row["title"], "content_text": _summary(row), "date_published": f"{index['as_of']}T00:00:00Z",
                      "tags": [row["area"], row["answer_state"]]})
    return {"version": "https://jsonfeed.org/version/1.1", "title": "Baltor knowledge radar",
            "home_page_url": PUBLIC_PAGE, "description": "Dated answers to recurring engineering questions.",
            "items": items}


def rss(index: dict) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0">', "<channel>",
             "<title>Baltor knowledge radar</title>", f"<link>{PUBLIC_PAGE}</link>",
             "<description>Dated answers to recurring engineering questions.</description>"]
    for row in index["questions"]:
        lines += ["<item>", f"<title>{escape(row['title'])}</title>",
                  f"<link>{PUBLIC_PAGE}#{escape(row['question_id'])}</link>",
                  f"<guid isPermaLink=\"false\">{escape(row['question_id'])}@{index['as_of']}</guid>",
                  f"<description>{escape(_summary(row))}</description>",
                  f"<category>{escape(row['area'])}</category>", "</item>"]
    lines += ["</channel>", "</rss>", ""]
    return "\n".join(lines)


STATE_WORDS = {"approved_result_available": "Approved", "candidate_available": "Ready for review",
               "needs_research": "Not answered yet", "needs_local_evaluation": "Answer depends on your constraints",
               "blocked_by_policy": "Held by a policy check", "no_eligible_option_established": "No current answer"}


def teaser_html(index: dict) -> str:
    """A static public teaser: question titles, areas, answer states and dates. No brief body is shown."""
    rows = []
    for row in sorted(index["questions"], key=lambda item: (item["area"], item["title"])):
        rows.append("<tr id=\"{0}\"><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td></tr>".format(
            escape(row["question_id"]), escape(row["title"]), escape(row["area"].replace("_", " ")),
            escape(STATE_WORDS.get(row["answer_state"], row["answer_state"])), escape(row["as_of"] or ""),
            escape(row.get("valid_until") or "")))
    return "\n".join([
        "<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Knowledge radar</title>", "<style>body{font-family:system-ui,sans-serif;margin:16px;max-width:960px}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccc;padding:6px;text-align:left;"
        "vertical-align:top}</style>", "</head>", "<body>", "<h1>Knowledge radar</h1>",
        f"<p>Dated answers to recurring engineering questions, as of {escape(index['as_of'])}. Each answer names the "
        "day it stops being current. Signed-in harnesses fetch the full briefs, data files and tools through Baltor.</p>",
        "<table>", "<thead><tr><th>Question</th><th>Area</th><th>State</th><th>As of</th><th>Valid until</th></tr></thead>",
        "<tbody>", *rows, "</tbody>", "</table>", "</body>", "</html>", ""])


def dumps(value) -> bytes:
    return (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
