#!/usr/bin/env python3
"""Find overnight candidates in the day's Claude Code sessions.

The 5 PM trigger needs work to do, and asking a human to supply it defeats
the purpose. This reads the engineer's own session transcripts and proposes
candidates, each carrying the evidence that produced it, so a morning
reviewer can judge the proposal without replaying the session.

WHAT COUNTS AS A CANDIDATE
The strongest available signal is a command that failed and was never
subsequently seen succeeding in that session. It is strong because it is
observed rather than inferred: the transcript records the exit, not an
opinion about it. A command that failed and later passed is a thread the
engineer already closed, and proposing it would waste the night.

Weaker signals are recorded but ranked below it:
  * a failure repeated three or more times -- the engineer fought it and
    may have run out of day rather than out of problem;
  * an explicit deferral in the engineer's own words ("TODO", "later",
    "come back to").

WHAT THIS DELIBERATELY DOES NOT DO
It does not read the assistant's prose for claims about what was left
undone. Assistant text is the least reliable thing in the file: it asserts
outcomes it did not verify, and a candidate built from it inherits that. The
signals above are all drawn from tool results and the engineer's own words.

Everything stays on this machine. Nothing here sends a transcript anywhere.

Usage:
    python3 tools/session_intake.py [--since today] [--limit 10] [--json]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import time

TRANSCRIPT_ROOT = os.path.expanduser("~/.claude/projects")

#: The engineer deferring something in their own words.
_DEFERRAL = re.compile(
    r"\b(TODO|FIXME|come back to (this|it)|for (now|later)|later on|"
    r"leave (this|that) for|punt on|revisit)\b", re.IGNORECASE)

#: Noise that is never worth a night's work.
_TRIVIAL = re.compile(
    r"^\s*(ls|cd|pwd|echo|cat|clear|which|whoami|date)\b", re.IGNORECASE)

#: A GATE is a command whose failure means the project is broken, as
#: opposed to a command the engineer ran to look around. Observed on the
#: first real scan: "failed once and never succeeded" alone surfaces
#: `cat` of a missing path and a timed-out version-probe loop alongside
#: three genuine lint failures. The difference between them is not how
#: often they failed -- it is whether anyone would care that they did.
_GATE = re.compile(
    r"\b(pytest|jest|vitest|mocha|go test|cargo test|npm test|yarn test|"
    r"pnpm test|make test|tox|nox|"
    r"biome|eslint|ruff|flake8|pylint|clippy|"
    r"tsc|mypy|pyright|typecheck|type-check|"
    r"npm run build|yarn build|pnpm build|make build|cargo build|"
    r"docker build|terraform (plan|validate)|"
    # The data stack. An analytics or pipeline engineer's gate is a dbt
    # test or a schema check, not pytest, and intake that does not know
    # these words silently reports "nothing unresolved" to exactly the
    # people whose work it was meant to find.
    r"dbt (test|build|run|compile|snapshot)|sqlfluff|"
    r"great_expectations|great-expectations|pandera|soda scan|"
    r"airflow (dags |tasks )?test|dagster (job|asset) |prefect deployment|"
    r"dvc (repro|exp run)|kedro run|mlflow run|"
    r"papermill|nbconvert --execute|nbmake|pytest --nbmake|"
    r"alembic (upgrade|check)|sqlmesh (plan|audit)|"
    r"spark-submit|pyspark)\b", re.IGNORECASE)

#: A timeout says the command was slow, not that the code is wrong, and a
#: night spent on one is a night spent on a timeout.
_TIMEOUT = re.compile(r"timed out|Exit code 143|SIGTERM", re.IGNORECASE)


def _blocks(record):
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _text_of(block) -> str:
    value = block.get("text") or block.get("content") or ""
    if isinstance(value, list):
        value = " ".join(
            str(p.get("text", "")) for p in value if isinstance(p, dict))
    return str(value)


def scan(path: str) -> dict:
    """Pull observed failure and deferral signals out of one transcript."""
    commands = {}          # tool_use id -> command text
    failed = collections.OrderedDict()   # command -> [error excerpts]
    succeeded = set()
    deferrals = []
    cwd = branch = ""
    with open(path, errors="ignore") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            cwd = record.get("cwd") or cwd
            branch = record.get("gitBranch") or branch
            for block in _blocks(record):
                kind = block.get("type")
                if kind == "tool_use" and block.get("name") == "Bash":
                    command = str((block.get("input") or {}).get("command", ""))
                    if command and not _TRIVIAL.match(command):
                        commands[block.get("id")] = command.strip()
                elif kind == "tool_result":
                    command = commands.get(block.get("tool_use_id"))
                    if not command:
                        continue
                    if block.get("is_error"):
                        failed.setdefault(command, []).append(
                            " ".join(_text_of(block).split())[:300])
                    else:
                        succeeded.add(command)
                elif kind == "text" and record.get("type") == "user":
                    for match in _DEFERRAL.finditer(_text_of(block)):
                        sentence = _text_of(block)
                        start = max(0, match.start() - 90)
                        deferrals.append(
                            " ".join(sentence[start:match.end() + 110].split()))
    unresolved = {c: errs for c, errs in failed.items() if c not in succeeded}
    return {"path": path, "cwd": cwd, "branch": branch,
            "unresolved": unresolved, "resolved_count": len(succeeded),
            "deferrals": deferrals[:6]}


def candidates(scans, limit: int) -> list:
    """Rank candidates by how well the evidence supports spending a night."""
    found = []
    for item in scans:
        for command, errors in item["unresolved"].items():
            attempts = len(errors)
            last = errors[-1] if errors else ""
            if _TIMEOUT.search(last):
                continue
            is_gate = bool(_GATE.search(command))
            if not is_gate and attempts < 3:
                # Failed once, and nobody had declared it a gate. That is
                # what looking around looks like, not what broken looks
                # like. Dropped rather than ranked low: a candidate list
                # padded with exploration teaches the morning reviewer to
                # skim, and then the real ones get skimmed too.
                continue
            found.append({
                "kind": "failing_gate" if is_gate else "unresolved_failure",
                "confidence": ("high" if is_gate and attempts >= 2
                               else "medium" if is_gate else "low"),
                "attempts": attempts,
                "command": command[:400],
                "last_error": errors[-1] if errors else "",
                "cwd": item["cwd"], "branch": item["branch"],
                "evidence": (
                    f"failed {attempts}x in {os.path.basename(item['path'])} "
                    "and was never observed succeeding in that session"),
            })
        for note in item["deferrals"]:
            found.append({
                "kind": "explicit_deferral", "confidence": "low",
                "attempts": 0, "command": "", "last_error": "",
                "cwd": item["cwd"], "branch": item["branch"],
                "note": note[:300],
                "evidence": "the engineer deferred this in their own words",
            })
    order = {"high": 0, "medium": 1, "low": 2}
    found.sort(key=lambda c: (order[c["confidence"]], -c["attempts"]))
    return found[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="today",
                    help="'today', 'yesterday', or a number of days")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=TRANSCRIPT_ROOT)
    args = ap.parse_args()

    days = {"today": 1, "yesterday": 2}.get(args.since)
    if days is None:
        days = max(1, int(args.since))
    cutoff = time.time() - days * 86400
    paths = [p for p in glob.glob(os.path.join(args.root, "**", "*.jsonl"),
                                  recursive=True)
             if os.path.getmtime(p) >= cutoff and "subagents" not in p]

    scans = [scan(p) for p in paths]
    found = candidates(scans, args.limit)

    if args.json:
        print(json.dumps({"sessions": len(paths), "candidates": found},
                         indent=2))
        return 0

    print(f"{len(paths)} session(s) in the last {days} day(s); "
          f"{len(found)} candidate(s)\n")
    if not found:
        print("  Nothing unresolved was observed. That is a real result:")
        print("  a night spent on invented work is worse than a night idle.")
        return 0
    for index, item in enumerate(found, 1):
        print(f"{index}. [{item['confidence']}] {item['kind']}")
        if item.get("command"):
            print(f"   $ {item['command'][:150]}")
        if item.get("note"):
            print(f"   \"{item['note'][:150]}\"")
        if item.get("last_error"):
            print(f"   last error: {item['last_error'][:150]}")
        print(f"   why: {item['evidence']}")
        print(f"   where: {item['cwd']} ({item['branch'] or 'no branch'})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
