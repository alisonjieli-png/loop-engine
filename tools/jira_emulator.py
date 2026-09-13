#!/usr/bin/env python3
"""Generate realistic tickets WITH the code they refer to, and filter them.

Every task this harness has solved so far was "write a new module from a
description". Real tickets are not that. They reference code that already
exists, describe a defect in terms of observed behaviour, and their acceptance
criteria are often a sentence a person would judge. Two consequences:

* **Context layers.** A ticket without its code is a different, easier task. To
  test the real thing, each ticket here ships a repo fixture -- the existing
  modules, their tests, and any data files -- and the ticket text refers to
  them by name. This is also the case the harness handles worst: it authors
  into a CLEAN workspace and cannot edit in place, so a bug-fix ticket has to
  be expressed as "produce a corrected module", not "patch line 40".
* **Eligibility.** The harness's entire safety story is automated
  verification, so a ticket whose done-condition only a person can judge is not
  eligible, however well written. That is a product boundary, not a gap to
  paper over: measured today, model self-report is unreliable at every level,
  so "the model says it looks right" is not an acceptance criterion.

Ticket kinds and whether they are eligible unattended:

    bug        eligible  -- a failing case is the acceptance criterion
    feature    eligible  -- when the spec names checkable behaviour
    refactor   eligible  -- behaviour must be preserved, which is
                            differentially checkable against the original.
                            NOTE: if the ticket's real requirement is
                            non-functional (speed, memory), the acceptance
                            criterion must assert THAT. A correctness-only
                            criterion passes a refactor that changed nothing,
                            and the engine will report success -- measured
                            2026-09-06 on PERF-31.
    analytics  eligible  -- when the answer is a computed number a second
                            implementation can reproduce
    research   NOT       -- no executable done-condition; needs a human
    design     NOT       -- judged by taste

Usage:
    python3 tools/jira_emulator.py --out-dir DIR [--kinds bug,feature,...]
    python3 tools/jira_emulator.py --out-dir DIR --generate "area" --model M
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

ELIGIBLE_KINDS = ("bug", "feature", "refactor", "analytics")
INELIGIBLE_KINDS = ("research", "design")

#: Hand-written tickets with real context layers. Each defect is a genuine
#: mistake of the kind that reaches a tracker, not a syntax error.
TICKETS = [
    {
        "key": "DATA-118",
        "kind": "bug",
        "title": "Median returns the wrong value for even-length input",
        "body": ("`stats.median` returns the lower of the two middle values "
                 "for an even-length list instead of their mean.\n\n"
                 "Steps to reproduce:\n"
                 "  median([1, 2, 3, 4]) returns 2\n"
                 "Expected: 2.5\n\n"
                 "median() is correct for odd-length input. Do not change the "
                 "public signature."),
        "acceptance": "median([1,2,3,4]) == 2.5 and median([1,2,3]) == 2",
        "context": {
            "stats.py": (
                "def mean(values):\n"
                "    if not values:\n"
                "        raise ValueError('empty')\n"
                "    return sum(values) / len(values)\n\n\n"
                "def median(values):\n"
                "    if not values:\n"
                "        raise ValueError('empty')\n"
                "    ordered = sorted(values)\n"
                "    return ordered[(len(ordered) - 1) // 2]\n"),
            "test_stats.py": (
                "import unittest\n"
                "from stats import mean, median\n\n\n"
                "class TestStats(unittest.TestCase):\n"
                "    def test_mean(self):\n"
                "        self.assertEqual(mean([1, 2, 3]), 2)\n\n"
                "    def test_median_odd(self):\n"
                "        self.assertEqual(median([1, 2, 3]), 2)\n"),
        },
    },
    {
        "key": "DATA-204",
        "kind": "bug",
        "title": "percentile off-by-one on exact index boundaries",
        "body": ("`stats.percentile(values, p)` returns the element BELOW the "
                 "requested percentile when p lands exactly on an index.\n\n"
                 "  percentile([10,20,30,40,50], 50) returns 20, expected 30\n"
                 "  percentile([10,20,30,40,50], 100) returns 40, expected 50\n\n"
                 "Use nearest-rank: index = ceil(p/100 * n) - 1, clamped to "
                 "[0, n-1]. Keep the signature."),
        "acceptance": ("percentile([10,20,30,40,50],50)==30 and "
                       "percentile([10,20,30,40,50],100)==50 and "
                       "percentile([10,20,30,40,50],1)==10"),
        "context": {
            "stats.py": (
                "import math\n\n\n"
                "def percentile(values, p):\n"
                "    if not values:\n"
                "        raise ValueError('empty')\n"
                "    ordered = sorted(values)\n"
                "    index = int(p / 100 * len(ordered)) - 1\n"
                "    return ordered[max(0, index)]\n"),
        },
    },
    {
        "key": "REPORT-77",
        "kind": "feature",
        "title": "Add per-category percentage to the expense summary",
        "body": ("`summary.summarise(rows)` returns totals per category. Add a "
                 "`percentage` for each category: its share of the grand "
                 "total, rounded to one decimal place.\n\n"
                 "Return shape becomes "
                 "{category: {'total': float, 'percentage': float}}.\n"
                 "Percentages must sum to 100.0 (+/- 0.1) for any non-empty "
                 "input. An empty input still returns {}."),
        "acceptance": ("summarise([{'category':'a','amount':30},"
                       "{'category':'b','amount':10}])['a']['percentage']==75.0"),
        "context": {
            "summary.py": (
                "def summarise(rows):\n"
                "    totals = {}\n"
                "    for row in rows:\n"
                "        key = row['category']\n"
                "        totals[key] = totals.get(key, 0) + row['amount']\n"
                "    return totals\n"),
        },
    },
    {
        "key": "PERF-31",
        "kind": "refactor",
        "title": "find_duplicates is quadratic; make it linear",
        "body": ("`dedupe.find_duplicates(items)` is O(n^2) and times out on "
                 "our 200k-row export. Make it linear.\n\n"
                 "Behaviour must be IDENTICAL: same duplicates, same order of "
                 "first appearance, same handling of unhashable items (raise "
                 "TypeError). This is a refactor -- no behaviour change.\n\n"
                 "COMPLEXITY IS THE POINT: your tests must include a timing "
                 "assertion proving the new implementation is linear. Time it "
                 "on 4,000 and 40,000 random integers and assert the 10x "
                 "input costs under 20x the time. A correct but still "
                 "quadratic implementation does NOT satisfy this ticket."),
        # A correctness assertion does NOT test the thing this ticket asks
        # for. Measured 2026-09-06: the harness returned a behaviourally
        # perfect O(n^2) implementation, passed "find_duplicates([1,2,2,3,1])
        # == [2,1]", and the engine exited 0 -- the first over-report seen.
        # A non-functional requirement needs a non-functional assertion.
        "acceptance": ("find_duplicates([1,2,2,3,1]) == [2,1] and "
                       "find_duplicates([]) == [] and, timed on random input, "
                       "10x the input size costs under 20x the time (linear, "
                       "not quadratic)"),
        "context": {
            "dedupe.py": (
                "def find_duplicates(items):\n"
                "    seen_twice = []\n"
                "    for index, item in enumerate(items):\n"
                "        if item in items[:index] and item not in seen_twice:\n"
                "            seen_twice.append(item)\n"
                "    return seen_twice\n"),
        },
    },
    {
        "key": "ANALYTICS-9",
        "kind": "analytics",
        "title": "Compute weekly retention from the events log",
        "body": ("Given `events.csv` (user_id, event, day) compute weekly "
                 "retention: of the users active in week 0, what fraction are "
                 "active in week 1, week 2, week 3?\n\n"
                 "Week n covers days [7n, 7n+7). A user is active in a week if "
                 "they have at least one event in it. Expose "
                 "`retention(csv_path)` returning {1: float, 2: float, "
                 "3: float}, each rounded to 3 decimals."),
        "acceptance": "retention() reproduces on an independent implementation",
        "context": {
            "events.csv": (
                "user_id,event,day\n"
                "u1,open,0\nu2,open,1\nu3,open,2\nu4,open,3\n"
                "u1,open,8\nu2,open,9\n"
                "u1,open,15\n"
                "u1,open,22\n"),
        },
    },
    {
        "key": "RESEARCH-12",
        "kind": "research",
        "title": "Investigate why churn rose in Q3",
        "body": ("Churn is up 4 points quarter over quarter. Work out why and "
                 "recommend what we do about it."),
        "acceptance": "a person judges whether the analysis is convincing",
        "context": {},
    },
]


def eligible(ticket: dict) -> tuple:
    """Can this ticket be verified without a human? Say why if not."""
    kind = ticket.get("kind")
    if kind in INELIGIBLE_KINDS:
        return False, (f"kind '{kind}' has no executable done-condition; "
                       "verification would rest on model self-report, which "
                       "is measured unreliable")
    if kind not in ELIGIBLE_KINDS:
        return False, f"unknown kind '{kind}'"
    if not str(ticket.get("acceptance") or "").strip():
        return False, "no acceptance criterion stated"
    if not ticket.get("context"):
        return False, ("no context layer; a ticket without its code is a "
                       "different and easier task")
    return True, ""


def write_ticket(ticket: dict, out_dir: Path) -> str:
    """Write the task file and its context layer as a self-contained unit."""
    root = out_dir / ticket["key"]
    context_dir = root / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    for name, body in (ticket.get("context") or {}).items():
        (context_dir / name).write_text(body, encoding="utf-8")
    listing = "\n".join(
        f"--- {name} ---\n{body}"
        for name, body in (ticket.get("context") or {}).items())
    task = f"""{ticket['title']}

{ticket['body']}

EXISTING CODE (this is the current state of the repository):
{listing}

WHAT TO PRODUCE: this runtime authors files into a clean workspace and cannot
edit in place, so emit the COMPLETE corrected version of every file you change,
with the same filenames, plus unittest tests that cover the reported case AND
the behaviour that already worked (it must not regress).

ACCEPTANCE (must hold): {ticket['acceptance']}

# ENVIRONMENT: bare Python interpreter, standard library ONLY. Use unittest and
# `python3 -m unittest`; pytest is NOT installed. No third-party imports.
"""
    path = root / "task.txt"
    path.write_text(task, encoding="utf-8")
    return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--kinds", default=",".join(ELIGIBLE_KINDS))
    args = parser.parse_args()
    wanted = {k.strip() for k in args.kinds.split(",") if k.strip()}
    out_dir = Path(args.out_dir)

    accepted, refused = [], []
    for ticket in TICKETS:
        ok, why = eligible(ticket)
        if not ok:
            refused.append((ticket["key"], ticket["kind"], why))
            continue
        if ticket["kind"] not in wanted:
            continue
        accepted.append((ticket, write_ticket(ticket, out_dir)))

    print(f"{len(accepted)} ticket(s) admitted, {len(refused)} refused\n")
    for ticket, path in accepted:
        print(f"  {ticket['key']:14} {ticket['kind']:10} {ticket['title'][:52]}")
    for key, kind, why in refused:
        print(f"  {key:14} {kind:10} REFUSED: {why[:70]}")
    manifest = out_dir / "queue.txt"
    manifest.write_text("\n".join(p for _, p in accepted) + "\n",
                        encoding="utf-8")
    (out_dir / "tickets.json").write_text(json.dumps(
        {"record_type": "ticket_batch/v1",
         "admitted": [t["key"] for t, _ in accepted],
         "refused": [{"key": k, "kind": c, "reason": w}
                     for k, c, w in refused]}, indent=1), encoding="utf-8")
    print(f"\nqueue: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
