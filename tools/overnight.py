#!/usr/bin/env python3
"""The 5 PM run: find the day's unfinished work, attempt it, report by morning.

    intake  ->  gameplan  ->  attempt  ->  verify  ->  morning report

WHY THE VERIFICATION ORACLE IS FREE HERE
Every other overnight system has to guess how to check its own work. This
one does not, because of where the work comes from: a `failing_gate`
candidate IS a command the engineer ran that exited non-zero. That command
is the acceptance test, already written, already trusted by the person who
will read the report. The night's job is to make it exit zero, and there is
no question about what success means.

That is the whole reason intake ranks gates above everything else. A
candidate without an executable gate can still be analysed, but it cannot
be verified, and this run says so rather than implying otherwise.

WHAT IT NEVER DOES
It does not commit, push, merge, or touch the working tree the engineer
left behind. Each attempt happens on its own branch created from the
recorded commit, and a branch that does not reach a passing gate is
reported as an unfinished attempt rather than deleted -- a failed attempt
with a real error in it is worth more to a morning reviewer than silence.

Usage:
    python3 tools/overnight.py --dry-run
    OLLAMA_API_KEY=... python3 tools/overnight.py --max-tasks 3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from session_intake import candidates, scan                # noqa: E402
from loop_engine.core.night_budget import NightBudget      # noqa: E402

REPORT_ROOT = Path(os.path.expanduser("~/.loop-engine/overnight"))
#: Worktrees live here, not inside the engineer's repository.
WORKTREE_ROOT = Path(os.path.expanduser("~/.loop-engine/worktrees"))


def _git(args, cwd, timeout=120):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, timeout=timeout)


def collect(since_days: int, limit: int) -> list:
    import glob
    cutoff = time.time() - since_days * 86400
    root = os.path.expanduser("~/.claude/projects")
    paths = [p for p in glob.glob(os.path.join(root, "**", "*.jsonl"),
                                  recursive=True)
             if os.path.getmtime(p) >= cutoff and "subagents" not in p]
    return candidates([scan(p) for p in paths], limit)


def gameplan(item: dict) -> dict:
    """State, before any model call, what this task is and how it ends.

    Written first and kept, so the morning report can show the intent
    beside the outcome. A plan produced after the attempt would be shaped
    by how the attempt went, which is the definition of a plan that cannot
    be wrong.
    """
    gate = item.get("command", "")
    return {
        "candidate": item.get("kind"),
        "confidence": item.get("confidence"),
        "workspace": item.get("cwd", ""),
        "gate_command": gate,
        "acceptance": (f"`{gate[:160]}` exits zero" if gate else
                       "NO EXECUTABLE GATE — analysis only, cannot be verified"),
        "evidence": item.get("evidence", ""),
        "observed_error": (item.get("last_error") or "")[:400],
        "verifiable": bool(gate),
    }


def attempt(plan: dict, model: str, attempts: int, budget) -> dict:
    """Run one candidate in its OWN WORKTREE; the gate decides the outcome.

    Not a branch switch in the engineer's checkout. An earlier version did
    that, and when the run was killed on a timeout the `finally: git
    checkout -` never ran, leaving the repository sitting on an overnight
    branch. An unattended process that can leave someone's checkout
    somewhere they did not put it is not one they will run again.

    A worktree is a separate directory sharing the same object store. The
    engineer's checkout, index, and current branch are never touched, which
    also makes their uncommitted work a non-issue rather than a reason to
    skip the candidate.
    """
    workspace = Path(plan["workspace"] or ".")
    if not (workspace / ".git").is_dir():
        return {"status": "skipped",
                "why": f"{workspace} is not a git repository; this run only "
                       "works in worktrees and will not edit an unversioned "
                       "tree"}
    # The engineer's HEAD, read but never moved.
    head = _git(["rev-parse", "--short", "HEAD"], workspace).stdout.strip()
    stamp = f"{time.strftime('%Y%m%d')}-{abs(hash(plan['gate_command'])) % 10000:04d}"
    branch = f"overnight/{stamp}"
    tree = WORKTREE_ROOT / stamp
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
    if tree.exists():
        _git(["worktree", "remove", "--force", str(tree)], workspace)
    made = _git(["worktree", "add", "-b", branch, str(tree), "HEAD"], workspace)
    if made.returncode != 0:
        return {"status": "skipped",
                "why": f"could not create a worktree at {tree}: "
                       f"{made.stderr.strip()[:200]}"}

    # Everything below runs in `tree`. Nothing touches `workspace`, so a
    # kill at any point leaves the engineer's checkout exactly as it was.
    before_ok, before_out = run_gate(plan["gate_command"], tree, budget)
    if before_ok:
        return {"status": "already_green", "branch": branch,
                "worktree": str(tree),
                "why": "the gate passes now; the failure the transcript "
                       "recorded is no longer reproducible",
                "gate_output": before_out[-600:]}
    result = solve(plan, tree, model, attempts, budget)
    after_ok, after_out = run_gate(plan["gate_command"], tree, budget)
    changed = _git(["status", "--porcelain", "--untracked-files=no"],
                   tree).stdout.strip()
    return {"status": "verified" if after_ok else "attempted",
            "branch": branch, "worktree": str(tree), "from_commit": head,
            "files_touched": _porcelain_paths(changed)[:20],
            "gate_before": before_out[-400:],
            "gate_after": after_out[-600:],
            "steps": result}


def _porcelain_paths(text: str) -> list:
    """Read filenames out of `git status --porcelain` without slicing.

    `line[3:]` is wrong the moment the status field is not exactly two
    characters plus a space, and it silently returns a filename that is
    almost right: a real run reported the fix it had just verified as
    touching "alc.py". A morning report naming a file that does not exist
    is worse than one naming none, because the reader stops trusting the
    rest of it.
    """
    paths = []
    for line in text.splitlines():
        body = line[2:].strip() if len(line) > 2 else ""
        if not body:
            continue
        # Renames and copies are recorded as "old -> new"; the new path is
        # the one a reader wants.
        paths.append(body.split(" -> ")[-1].strip().strip('"'))
    return paths


def run_gate(command: str, workspace: Path, budget=None):
    """Run the project's own gate. Its allowance comes from the night."""
    if not command:
        return False, "(no gate command)"
    began = time.time()
    # Not a fixed number. A gate that needs twenty minutes on a big test
    # suite is normal; capping it at fifteen decides in advance that such
    # a project cannot be worked on.
    allowance = budget.grant("gate") if budget is not None else 3600.0
    try:
        done = subprocess.run(command, shell=True, cwd=str(workspace),
                              capture_output=True, text=True,
                              timeout=allowance)
    except subprocess.TimeoutExpired:
        print(f"      gate exceeded its {allowance / 60:.0f} min allowance",
              flush=True)
        return False, (f"the gate did not finish within {allowance / 60:.0f} "
                       "minutes of the night's remaining budget")
    print(f"      gate exited {done.returncode} in "
          f"{time.time() - began:.1f}s", flush=True)
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def solve(plan, workspace, model, attempts, budget) -> list:
    """Drive the composed steps. Import is local so --dry-run needs no key."""
    from loop_engine.core.opencode_step_composition import (
        compose_instance, default_catalogue, default_core,
        default_skill_library, dynamic_step_layer, observation_step_layer)
    from loop_engine.core.opencode_step_session import (
        OpenCodeStepProfile, OpenCodeStepSession)

    class _Authority:
        max_model_calls = 4

    class _Req:
        def __init__(self, prompt): self.prompt = prompt

    task = (f"A project gate is failing.\n\nGate: {plan['gate_command']}\n\n"
            f"Recorded output:\n{plan['observed_error']}\n\n"
            "Make the gate pass. Change as little as possible.")
    core, catalogue, library = (default_core(), default_catalogue(),
                                default_skill_library())
    steps, observation = [], ""
    for index in range(1, attempts + 1):
        for name, schema in (
                ("orient", '{"what_is_failing": string, "likely_cause": string}'),
                ("implement", '{"files_written": [string], "what_changed": string}')):
            layer, _ = dynamic_step_layer(catalogue.select(name), task, library)
            instance = compose_instance(core, layer, workspace)
            profile = OpenCodeStepProfile(
                model=model, workspace=workspace,
                timeout_seconds=budget.grant(name),
                agent=instance.agent_name,
                additional_environment=("OLLAMA_API_KEY", "XDG_DATA_HOME"))
            session = OpenCodeStepSession(
                authority=_Authority(), profile=profile)
            body = task + (f"\n\nObserved previously:\n{observation}"
                           if observation else "")
            began = time.time()
            print(f"      [{time.strftime('%H:%M:%S')}] {name} "
                  f"(attempt {index}) started", flush=True)
            try:
                text = session.invoke(
                    _Req(f"{body}\n\nReturn one JSON object with keys: {schema}"),
                    None)
                elapsed = time.time() - began
                steps.append({"step": name, "attempt": index,
                              "seconds": round(elapsed, 1),
                              "value": json.loads(text)})
            except Exception as exc:                        # noqa: BLE001
                elapsed = time.time() - began
                steps.append({"step": name, "attempt": index,
                              "seconds": round(elapsed, 1),
                              "error": f"{type(exc).__name__}: {exc}"[:300]})
            # Printed and flushed per step, not collected for the end. A
            # run killed on a timeout previously produced no partial output
            # at all, so "where did the time go" had no answer but a guess.
            print(f"      [{time.strftime('%H:%M:%S')}] {name} "
                  f"(attempt {index}) took {elapsed:.1f}s", flush=True)
        ok, output = run_gate(plan["gate_command"], workspace, budget)
        if ok:
            return steps
        if index < attempts:
            # The failure changes the shape of the next step, not its wording.
            obs = observation_step_layer("gate", output)
            instance = compose_instance(core, obs, workspace)
            profile = OpenCodeStepProfile(
                model=model, workspace=workspace,
                timeout_seconds=budget.grant("observe"),
                agent=instance.agent_name,
                additional_environment=("OLLAMA_API_KEY", "XDG_DATA_HOME"))
            session = OpenCodeStepSession(
                authority=_Authority(), profile=profile)
            try:
                observation = session.invoke(_Req(
                    task + '\n\nReturn one JSON object with keys: '
                    '{"command_run": string, "output_observed": string, '
                    '"contradiction": string}'), None)[:1000]
                steps.append({"step": "observe", "attempt": index,
                              "value": observation[:400]})
            except Exception as exc:                        # noqa: BLE001
                steps.append({"step": "observe", "attempt": index,
                              "error": str(exc)[:200]})
    return steps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=1)
    ap.add_argument("--max-tasks", type=int, default=3)
    ap.add_argument("--attempts", type=int, default=2)
    ap.add_argument("--model", default="ollama-cloud/gemma4:31b")
    ap.add_argument("--dry-run", action="store_true",
                    help="intake and gameplan only; no model call, no branch")
    ap.add_argument("--gate", default="",
                    help="skip intake and attempt this exact gate command")
    ap.add_argument("--workspace", default="",
                    help="repository the --gate command runs in")
    ap.add_argument("--hours", type=float, default=12.0,
                    help="the night's total wall-clock budget (default 12)")
    args = ap.parse_args()

    if args.gate:
        if not args.workspace:
            raise SystemExit("--gate requires --workspace naming the repository")
        seeded = [{
            "kind": "failing_gate", "confidence": "seeded",
            "attempts": 1, "command": args.gate, "cwd": args.workspace,
            "branch": "", "last_error": "(supplied directly, not from a transcript)",
            "evidence": "supplied on the command line rather than discovered",
        }]

    started = time.strftime("%Y-%m-%d %H:%M")
    budget = NightBudget(hours=args.hours,
                         expected_steps=max(4, args.max_tasks * 3))
    found = seeded if args.gate else collect(args.since, args.max_tasks)
    print(f"overnight run {started} — {len(found)} candidate(s); "
          f"{args.hours:.0f}h budget\n", flush=True)
    if not found:
        print("  Nothing unresolved was observed today. Reporting that,")
        print("  rather than inventing work to look busy.")
        return 0

    report = {"started": started, "model": args.model,
              "dry_run": args.dry_run, "tasks": []}
    for index, item in enumerate(found, 1):
        plan = gameplan(item)
        print(f"{index}. [{plan['confidence']}] {plan['candidate']}")
        print(f"   gate     : {plan['gate_command'][:130] or '(none)'}")
        print(f"   accepts  : {plan['acceptance'][:130]}")
        print(f"   workspace: {plan['workspace']}")
        entry = {"plan": plan}
        if not args.dry_run and plan["verifiable"]:
            outcome = attempt(plan, args.model, args.attempts, budget)
            entry["outcome"] = outcome
            print(f"   -> {outcome['status']}"
                  + (f": {outcome.get('why','')[:110]}" if outcome.get("why") else ""))
            if outcome.get("branch"):
                print(f"      branch {outcome['branch']}")
        elif not plan["verifiable"]:
            print("   -> analysis only: no executable gate, so nothing here "
                  "can be verified")
        print()
        report["tasks"].append(entry)

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"{time.strftime('%Y-%m-%d')}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    verified = sum(1 for t in report["tasks"]
                   if t.get("outcome", {}).get("status") == "verified")
    report["time_spent"] = budget.spent()
    report["hours_used"] = round(budget.elapsed() / 3600, 2)
    print(f"  {verified}/{len(report['tasks'])} reached a passing gate "
          f"in {budget.elapsed() / 3600:.1f}h of {args.hours:.0f}h")
    if budget.spent():
        print(f"  time went to: {budget.spent()}")
    print(f"  report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
