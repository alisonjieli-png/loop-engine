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
    OLLAMA_API_KEY=... python3 tools/overnight.py --max-tasks 3 --allow-transcript-gates
    OLLAMA_API_KEY=... python3 tools/overnight.py --gate "pytest -q" --workspace /repo

WHAT AN UNATTENDED RUN IS ALLOWED TO DO
Every widening is a flag, off by default. --allow-transcript-gates before a
command harvested from a transcript is executed at all; --allow-compound-gates
before one carrying |, &&, ;, $( or a backtick is; --gate-env NAME or
--gate-inherit-env before a gate sees more than PATH, HOME, LANG, TERM and
TMPDIR; --prune-worktrees before any worktree is removed; --require-clean-tree
to skip a repository with modified tracked files. A --gate typed on the
command line is the operator's own choice and needs no flag.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from session_intake import (                              # noqa: E402
    COMPOUND_REFUSAL, candidates, is_compound, scan)
from loop_engine.core.night_budget import NightBudget      # noqa: E402
from loop_engine.core.overnight_outcome import (          # noqa: E402
    Outcome, classify, rank, summarise)
from loop_engine.core.multipath_select import (           # noqa: E402
    PathResult, select)
from concurrent.futures import ThreadPoolExecutor         # noqa: E402

REPORT_ROOT = Path(os.path.expanduser("~/.loop-engine/overnight"))
#: Worktrees live here, not inside the engineer's repository.
WORKTREE_ROOT = Path(os.path.expanduser("~/.loop-engine/worktrees"))

#: What a gate command's process may see. Built from nothing, by name. A
#: harvested command runs unattended with a shell, and the operator's
#: environment holds provider keys, tokens and whatever else the day left in
#: it; a gate that needs more names one with --gate-env, and --gate-inherit-env
#: restores the whole environment for a caller who wants what earlier
#: versions did.
GATE_ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "TERM", "TMPDIR")


def gate_environment(names=(), *, inherit: bool = False) -> dict:
    """The environment a gate runs with: an allowlist unless told otherwise."""
    if inherit:
        return dict(os.environ)
    admitted = tuple(GATE_ENV_ALLOWLIST) + tuple(names or ())
    return {name: os.environ[name] for name in admitted if name in os.environ}


class SharedCallCeiling:
    """A model-call ceiling that binds across every step of one solving path.

    ``OpenCodeStepSession`` reads ``authority.max_model_calls`` before it
    starts a process and compares it with its own ``calls_used``. A fresh
    session per step therefore starts every step at zero, and a per-step
    ceiling of four bounded nothing a path did over a night. One of these is
    handed to every session on a path as its authority and is charged with
    each session's calls after the step, so the ceiling it reports shrinks
    as the path spends. ``total=None`` keeps only the per-step ceiling,
    which is what every earlier version had.
    """

    def __init__(self, total, per_step=None):
        self.total = None if total is None else max(0, int(total))
        self.per_step = None if per_step is None else max(0, int(per_step))
        self.charged = 0
        self.ledger = []
        self.accounting_uncertain = False

    @property
    def remaining(self):
        if self.total is None:
            return None
        return max(0, self.total - self.charged)

    @property
    def max_model_calls(self):
        """What the next session may spend: the smaller of step and path."""
        if self.accounting_uncertain and (self.total is not None or self.per_step is not None):
            return 0
        remaining = self.remaining
        if remaining is None:
            return self.per_step
        if self.per_step is None:
            return remaining
        return min(self.per_step, remaining)

    @property
    def exhausted(self) -> bool:
        return (self.max_model_calls == 0
                or self.total is not None and self.charged >= self.total)

    def charge(self, session, label: str = "step") -> int:
        """Record what a finished session spent; returns the running total."""
        calls = session if isinstance(session, int) else getattr(
            session, "calls_used", 0)
        calls = max(0, int(calls or 0))
        uncertain = getattr(session, "accounting_uncertain", False) is True
        self.accounting_uncertain = self.accounting_uncertain or uncertain
        self.charged += calls
        self.ledger.append({"step": str(label), "calls": calls,
                            "accounting_complete": not uncertain,
                            "charged": self.charged})
        return self.charged

    def to_dict(self) -> dict:
        return {"total": self.total, "per_step": self.per_step,
                "charged": self.charged, "remaining": self.remaining,
                "accounting_uncertain": self.accounting_uncertain,
                "steps": list(self.ledger)}


def _git(args, cwd, timeout=120):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, timeout=timeout)


def collect(since_days: int, limit: int, allow_compound: bool = False) -> list:
    import glob
    cutoff = time.time() - since_days * 86400
    root = os.path.expanduser("~/.claude/projects")
    paths = [p for p in glob.glob(os.path.join(root, "**", "*.jsonl"),
                                  recursive=True)
             if os.path.getmtime(p) >= cutoff and "subagents" not in p]
    return candidates([scan(p) for p in paths], limit,
                      allow_compound=allow_compound)


def gameplan(item: dict, policy=None) -> dict:
    """State, before any model call, what this task is and how it ends.

    Written first and kept, so the morning report can show the intent
    beside the outcome. A plan produced after the attempt would be shaped
    by how the attempt went, which is the definition of a plan that cannot
    be wrong.

    A compound command harvested from a transcript is planned but marked
    unverifiable, with the refusal spelled out, unless the policy allows
    compound gates. A gate typed on the command line (confidence "seeded")
    is the operator's own and is never refused here.
    """
    gate = item.get("command", "")
    seeded = item.get("confidence") == "seeded"
    compound = bool(gate) and (bool(item.get("compound")) or is_compound(gate))
    allowed = bool(policy is not None
                   and getattr(policy, "allow_compound_gates", False))
    refused = ""
    if compound and not seeded and not allowed:
        refused = "compound command refused: it " + COMPOUND_REFUSAL
    verifiable = bool(gate) and not refused
    return {
        "candidate": item.get("kind"),
        "confidence": item.get("confidence"),
        "workspace": item.get("cwd", ""),
        "gate_command": gate,
        "acceptance": (f"`{gate[:160]}` exits zero" if verifiable else
                       refused or
                       "NO EXECUTABLE GATE — analysis only, cannot be verified"),
        "evidence": item.get("evidence", ""),
        "observed_error": (item.get("last_error") or "")[:400],
        "verifiable": verifiable,
        "source": "seeded" if seeded else "transcript",
        "compound": compound,
        "refused": refused,
    }


#: How long a finished worktree is kept. Long enough that a morning
#: reviewer can still open last night's attempt and the one before it;
#: short enough that a run killed every night does not fill the disk. A
#: killed run left a 62 MB worktree behind, and nothing removed it: at one
#: a night that is 22 GB a year on a disk with 66 GB free.
WORKTREE_KEEP_DAYS = 3


@dataclass
class NightPolicy:
    """What an unattended run may do. Each default is the safer choice.

    Every field is set by a flag in main(), and every earlier behaviour is
    still reachable by setting the field, so nothing an operator relied on
    is gone; it is no longer the default.
    """

    require_clean_tree: bool = False
    prune_worktrees: bool = False
    keep_days: float = WORKTREE_KEEP_DAYS
    prune_force: bool = False
    #: None means the allowlist from gate_environment(); a mapping is used
    #: as given, so --gate-inherit-env can pass the whole environment.
    gate_environment: "dict | None" = None
    #: Model calls one path may make over all its steps. None derives it
    #: from the planned steps; 0 or less means no path ceiling at all.
    max_model_calls: "int | None" = None
    step_model_calls: int = 4
    allow_compound_gates: bool = False

    def environment(self) -> dict:
        if self.gate_environment is not None:
            return dict(self.gate_environment)
        return gate_environment()

    def path_ceiling(self, attempts: int, provisioning: str = "static"):
        """Model calls one path may spend, or None for no path ceiling.

        The default is the per-step ceiling times the steps the path can
        take: orient and implement per attempt, an observation between
        attempts, and two provisioning steps per attempt when a
        provisioner runs. That is the spend every earlier version allowed
        and never enforced.
        """
        if self.max_model_calls is not None:
            return self.max_model_calls if self.max_model_calls > 0 else None
        planned = attempts * 2 + max(0, attempts - 1)
        if provisioning == "model":
            planned += attempts * 2
        return self.step_model_calls * planned

    def to_dict(self) -> dict:
        """For the report: names of admitted environment variables, never values."""
        return {"require_clean_tree": self.require_clean_tree,
                "prune_worktrees": self.prune_worktrees,
                "keep_days": self.keep_days, "prune_force": self.prune_force,
                "gate_environment_names": sorted(self.environment()),
                "max_model_calls": self.max_model_calls,
                "step_model_calls": self.step_model_calls,
                "allow_compound_gates": self.allow_compound_gates}


def registered_worktrees(workspace) -> list:
    """Parse `git worktree list --porcelain` for this repository.

    Each entry is {"path", "head", "branch", "detached"}; the first is the
    main worktree. Only a path in this list is ever a candidate for
    pruning: a directory under WORKTREE_ROOT that git does not know about
    is not this tool's to delete, whatever its name looks like.
    """
    done = _git(["worktree", "list", "--porcelain"], workspace)
    if done.returncode != 0:
        return []
    entries, current = [], {}
    for line in done.stdout.splitlines():
        if not line.strip():
            if current:
                entries.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            if current:
                entries.append(current)
            current = {"path": value, "head": "", "branch": "",
                       "detached": False}
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = (value[len("refs/heads/"):]
                                 if value.startswith("refs/heads/") else value)
        elif key == "detached":
            current["detached"] = True
    if current:
        entries.append(current)
    return entries


def prune_worktrees(workspace, keep_days: float = WORKTREE_KEEP_DAYS, *,
                    force: bool = False, ledger=None) -> list:
    """Remove registered overnight worktrees older than the keep window.

    Only paths that `git worktree list --porcelain` reports for this
    repository, under WORKTREE_ROOT, are touched. Removal goes through
    `git worktree remove`, which refuses a tree holding uncommitted work,
    and the branch through `git branch -d`, which refuses unmerged commits;
    a refusal is recorded in ``ledger["skipped"]`` with git's reason rather
    than overridden. ``force=True`` (--prune-force) is the earlier
    behaviour: `--force` and `-D`. Directories under WORKTREE_ROOT that git
    does not list are recorded as ``unregistered`` and never deleted.

    Callers run this only behind --prune-worktrees. Returns the names of
    the worktrees removed, as it always did; ``ledger`` receives the rest.
    """
    ledger = ledger if ledger is not None else {}
    for key in ("removed", "skipped", "kept", "unregistered",
                "branches_removed"):
        ledger.setdefault(key, [])
    if not WORKTREE_ROOT.is_dir():
        return []
    try:
        root = WORKTREE_ROOT.resolve()
    except OSError:
        return []
    cutoff = time.time() - float(keep_days) * 86400
    listed = registered_worktrees(workspace)
    known = set()
    removed = []
    for entry in listed[1:]:
        path = Path(entry["path"])
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if root not in resolved.parents:
            continue
        known.add(resolved)
        if not path.exists():
            ledger["skipped"].append({
                "path": str(path), "why": "registered but missing on disk; "
                "`git worktree prune` drops the record"})
            continue
        try:
            if path.stat().st_mtime >= cutoff:
                ledger["kept"].append(path.name)
                continue
        except OSError:
            continue
        args = ["worktree", "remove"] + (["--force"] if force else []) + [str(path)]
        done = _git(args, workspace)
        if done.returncode != 0:
            ledger["skipped"].append({
                "path": str(path),
                "why": (done.stderr or done.stdout).strip()[:200]
                or "git worktree remove refused"})
            continue
        if path.exists():
            ledger["skipped"].append({
                "path": str(path), "why": "path remains after git removal; "
                "not deleting unregistered contents"})
            continue
        removed.append(path.name)
        branch = entry.get("branch", "")
        if branch.startswith("overnight/"):
            gone = _git(["branch", "-D" if force else "-d", branch], workspace)
            if gone.returncode != 0:
                ledger["skipped"].append({
                    "branch": branch,
                    "why": (gone.stderr or gone.stdout).strip()[:200]
                    or "git branch -d refused"})
            else:
                ledger["branches_removed"].append(branch)
    try:
        for tree in sorted(WORKTREE_ROOT.iterdir()):
            if tree.is_dir() and tree.resolve() not in known:
                ledger["unregistered"].append(tree.name)
    except OSError:
        pass
    if removed:
        _git(["worktree", "prune"], workspace)
    ledger["removed"] = list(removed)
    return removed


#: Models for independent paths, most different first. Diversity is the
#: point: three runs of one model share its blind spots. Model names live
#: here, in the tool's configuration, not in engine source.
PATH_MODELS = (
    "ollama-cloud/gemma4:31b",
    "ollama-cloud/kimi-k3",
    "ollama-cloud/glm-5.3",
    "ollama-cloud/deepseek-v4-flash",
    "ollama-cloud/gpt-oss:120b",
)


def _make_worktree(workspace, stamp, label):
    """Create one path's worktree. Called SEQUENTIALLY, never concurrently.

    Two paths creating worktrees at the same instant against one .git
    raced: the second failed with "failed to read .git/worktrees/<first>/
    commondir" and was graded skipped. Creation takes milliseconds and the
    solve takes minutes, so serialising creation costs nothing and removes
    the race entirely.
    """
    branch = f"overnight/{stamp}-{label}"
    tree = WORKTREE_ROOT / f"{stamp}-{label}"
    if tree.exists():
        _git(["worktree", "remove", "--force", str(tree)], workspace)
    made = _git(["worktree", "add", "-b", branch, str(tree), "HEAD"], workspace)
    if made.returncode != 0:
        why = f"could not create a worktree: {made.stderr.strip()[:160]}"
        # Said now, not only in the report. A path that fails to start is
        # the least visible failure there is, and the first version of this
        # printed nothing for it.
        print(f"      [{label}] SKIPPED: {why}", flush=True)
        return branch, tree, why
    return branch, tree, ""


def _run_path(plan, model, label, attempts, budget, workspace, head, stamp,
              branch, tree, creation_error, provisioning="static",
              policy=None):
    """One independent attempt in a worktree created beforehand."""
    policy = policy if policy is not None else NightPolicy()
    began = time.time()
    if creation_error:
        return PathResult(label=label, model=model,
                          outcome=classify(gate_passed=False,
                                           skipped_reason=creation_error),
                          error=creation_error), ""
    print(f"      [{label}] {model} started in {tree.name}", flush=True)
    try:
        result, final_state = solve(plan, tree, model, attempts, budget,
                                    provisioning, policy=policy)
    except Exception as exc:                                # noqa: BLE001
        why = f"{type(exc).__name__}: {exc}"[:200]
        return PathResult(label=label, model=model, branch=branch,
                          worktree=str(tree),
                          outcome=Outcome("no_progress", why, {}),
                          seconds=time.time() - began, error=why), ""
    after_ok, after_out = run_gate(plan["gate_command"], tree, budget,
                                   environment=policy.environment())
    changed = _git(["status", "--porcelain", "--untracked-files=no"],
                   tree).stdout.strip()
    files = _porcelain_paths(changed)
    if final_state is not None:
        final_state = final_state.apply({"files_changed": files})
    graded = classify(gate_passed=after_ok, state=final_state)
    diff = _git(["diff", "HEAD"], tree).stdout
    lines = sum(1 for l in diff.splitlines()
                if l[:1] in "+-" and not l.startswith(("+++", "---")))
    print(f"      [{label}] -> {graded.rung}  ({time.time() - began:.0f}s, "
          f"{len(files)} file(s), {lines} line(s))", flush=True)
    return PathResult(label=label, model=model, outcome=graded, branch=branch,
                      worktree=str(tree), files_changed=tuple(files),
                      lines_changed=lines, seconds=time.time() - began), diff


def attempt(plan: dict, model: str, attempts: int, budget, paths: int = 1,
            provisioning: str = "static", policy=None) -> dict:
    """Run one candidate in its OWN WORKTREE; the gate decides the outcome.

    ``policy`` (a NightPolicy) carries what the operator allowed: a clean
    tree requirement, worktree pruning, the gate environment and the
    path's model-call ceiling. Absent, the defaults apply, and every one
    of them is the safer choice.

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
        reason = (f"{workspace} is not a git repository; this run only "
                  "works in worktrees and will not edit an unversioned tree")
        return {"status": "skipped", "why": reason,
                "outcome": classify(gate_passed=False,
                                    skipped_reason=reason).to_dict()}
    policy = policy if policy is not None else NightPolicy()
    if policy.require_clean_tree:
        # Tracked modifications only. Untracked files are what running the
        # gate leaves behind (__pycache__, build output), and a check that
        # counted them disabled itself after its own first run.
        dirty = _git(["status", "--porcelain", "--untracked-files=no"],
                     workspace).stdout.strip()
        if dirty:
            reason = (f"{workspace} has {len(dirty.splitlines())} modified "
                      "tracked file(s) and --require-clean-tree is set; "
                      "skipped so the attempt starts from a committed state")
            return {"status": "skipped", "why": reason,
                    "outcome": classify(gate_passed=False,
                                        skipped_reason=reason).to_dict()}
    # The engineer's HEAD, read but never moved.
    head = _git(["rev-parse", "--short", "HEAD"], workspace).stdout.strip()
    # Stamped by gate AND workspace. Hashing the gate alone gave two repos
    # that both run `pytest -q` the same worktree name, and the second run
    # would `worktree remove --force` the first one's tree mid-flight.
    import hashlib as _hl
    # ...and by the moment it started. Same repo, same gate, twice in one
    # day -- an engineer re-triggering a run -- must not reuse branch names:
    # `worktree add -b` refuses an existing branch, and a rerun where every
    # path failed to create its worktree reported "no_progress" with no
    # explanation of why.
    key = f"{workspace.resolve()}::{plan['gate_command']}".encode()
    stamp = (f"{time.strftime('%Y%m%d-%H%M%S')}-"
             f"{_hl.sha256(key).hexdigest()[:6]}")
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
    prune_ledger = {}
    if policy.prune_worktrees:
        pruned = prune_worktrees(workspace, policy.keep_days,
                                 force=policy.prune_force, ledger=prune_ledger)
        if pruned:
            print(f"      pruned {len(pruned)} stale worktree(s): "
                  f"{', '.join(pruned)}", flush=True)
        for item in prune_ledger.get("skipped", ()):
            print(f"      prune skipped {item.get('path') or item.get('branch')}: "
                  f"{item.get('why', '')[:100]}", flush=True)
    environment = policy.environment()

    # Gate-before is checked once, in a probe worktree at the same HEAD
    # every path will start from. If it already passes there is nothing to
    # attempt and no path should be spent finding that out.
    probe = WORKTREE_ROOT / f"{stamp}-probe"
    if probe.exists():
        _git(["worktree", "remove", "--force", str(probe)], workspace)
    made = _git(["worktree", "add", "--detach", str(probe), "HEAD"], workspace)
    if made.returncode != 0:
        return {"status": "skipped",
                "why": f"could not create a worktree at {probe}: "
                       f"{made.stderr.strip()[:200]}",
                "worktree_prune": prune_ledger}
    before_ok, before_out = run_gate(plan["gate_command"], probe, budget,
                                     environment=environment)
    _git(["worktree", "remove", "--force", str(probe)], workspace)
    if before_ok:
        graded = classify(gate_passed=True, gate_before_failed=False)
        return {"status": graded.rung, "outcome": graded.to_dict(),
                "why": graded.because, "gate_output": before_out[-600:],
                "worktree_prune": prune_ledger}

    # Fan out. Each path is its own worktree and its own model; they run
    # concurrently because each is bound by a subprocess, not by this
    # interpreter. The night budget is wall-clock, so concurrent paths share
    # it honestly rather than each believing it has the whole night.
    count = max(1, paths)
    models = list(PATH_MODELS[:count]) if count > 1 else [model]
    if count > len(PATH_MODELS):
        models += [PATH_MODELS[i % len(PATH_MODELS)]
                   for i in range(count - len(PATH_MODELS))]
    labels = [f"p{i + 1}" for i in range(count)]
    print(f"      {count} path(s): " + ", ".join(
        f"{lab}={m.split('/')[-1]}" for lab, m in zip(labels, models)),
        flush=True)
    # Worktrees first, one at a time; then the slow part in parallel.
    trees = [(lab, m, *_make_worktree(workspace, stamp, lab))
             for lab, m in zip(labels, models)]
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(_run_path, plan, m, lab, attempts, budget,
                               workspace, head, stamp, branch, tree, err,
                               provisioning, policy)
                   for lab, m, branch, tree, err in trees]
        outcomes = [f.result() for f in futures]
    results = [r for r, _ in outcomes]
    diffs = {r.label: d for r, d in outcomes}
    chosen = select(results, diffs=diffs)

    # Every branch is kept. The chosen one is a recommendation with its
    # reasons; the others are the evidence a reviewer needs to weigh it.
    best = chosen.chosen
    return {"status": chosen.rung,
            "outcome": (best.outcome.to_dict() if best else
                        Outcome("no_progress",
                                "no path produced anything usable", {}).to_dict()),
            "branch": best.branch if best else "",
            "worktree": best.worktree if best else "",
            "from_commit": head,
            "files_touched": list(best.files_changed) if best else [],
            "gate_before": before_out[-400:],
            "mergeable": chosen.mergeable,
            "selection": chosen.to_dict(),
            "worktree_prune": prune_ledger}


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


def run_gate(command: str, workspace: Path, budget=None, *,
             environment: "dict | None" = None):
    """Run the project's own gate. Its allowance comes from the night.

    The gate runs with ``environment``, or with the allowlist from
    ``gate_environment()`` when none is given: never the operator's whole
    environment unless a caller built one with ``inherit=True``.
    """
    if not command:
        return False, "(no gate command)"
    began = time.time()
    # Not a fixed number. A gate that needs twenty minutes on a big test
    # suite is normal; capping it at fifteen decides in advance that such
    # a project cannot be worked on.
    allowance = budget.grant("gate") if budget is not None else 3600.0
    env = environment if environment is not None else gate_environment()
    try:
        done = subprocess.run(command, shell=True, cwd=str(workspace),
                              capture_output=True, text=True,
                              timeout=allowance, env=env)
    except subprocess.TimeoutExpired:
        print(f"      gate exceeded its {allowance / 60:.0f} min allowance",
              flush=True)
        return False, (f"the gate did not finish within {allowance / 60:.0f} "
                       "minutes of the night's remaining budget")
    print(f"      gate exited {done.returncode} in "
          f"{time.time() - began:.1f}s", flush=True)
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def _observe_gate(command: str, workspace, *, timeout: float,
                  environment: dict) -> dict:
    """Engine-observed gate output, run with the gate's own environment.

    ``engine_observed_output`` re-runs the gate so the observation step
    needs no shell of its own. It is used whenever the guard module accepts
    an environment; until it does, the same observation is made here, in
    the same shape, so the observation never sees what the gate itself was
    refused. Import is local so --dry-run needs no engine module.
    """
    import hashlib
    import inspect
    from loop_engine.core.opencode_step_guard import engine_observed_output
    try:
        accepted = inspect.signature(engine_observed_output).parameters
    except (TypeError, ValueError):
        accepted = {}
    for name in ("environment", "env"):
        if name in accepted:
            return engine_observed_output(command, workspace, timeout=timeout,
                                          **{name: environment})
    try:
        done = subprocess.run(command, shell=True, cwd=str(workspace),
                              capture_output=True, text=True,
                              timeout=timeout, env=environment)
    except subprocess.TimeoutExpired:
        return {"command": command, "exit_code": None, "timed_out": True,
                "output": (f"no result after {timeout:.0f}s; a hang is an "
                           "observation, not a missing one"),
                "observed_by": "tools/overnight.py"}
    output = (done.stdout + done.stderr).strip()
    return {"command": command, "exit_code": done.returncode,
            "timed_out": False, "output": output[-4000:],
            "digest": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "observed_by": "tools/overnight.py"}


def solve(plan, workspace, model, attempts, budget,
          provisioning: str = "static", policy=None) -> list:
    """Drive the composed steps. Import is local so --dry-run needs no key."""
    from loop_engine.core.opencode_step_composition import (
        compose_instance, default_catalogue, default_core,
        default_skill_library, dynamic_step_layer, observation_step_layer)
    from loop_engine.core.opencode_step_session import (
        OpenCodeStepProfile, OpenCodeStepSession)
    from loop_engine.core.step_state import StepState, render_step_prompt
    from loop_engine.core.opencode_step_provision import (
        PROVISION_SCHEMA, ProvisionError, admit_provision, apply_provision,
        provision_step_layer)

    policy = policy if policy is not None else NightPolicy()
    # One ceiling for the whole path, not a fresh four per step. Each step
    # still gets its own session and its own composed instance; what they
    # share is the authority they are handed, which is charged after every
    # step and therefore shrinks. Before this, a local `_Authority` with
    # `max_model_calls = 4` was compared against a counter that started at
    # zero on every step, so it bounded nothing a path did over a night.
    ceiling = SharedCallCeiling(policy.path_ceiling(attempts, provisioning),
                                per_step=policy.step_model_calls)
    environment = policy.environment()

    class _Req:
        def __init__(self, prompt): self.prompt = prompt

    task = "A project gate is failing. Make it pass, changing as little as possible."
    # The full repertoire -- 18 steps, 30 skills -- not the 4 base steps.
    # Found live: the provisioner asked to `reproduce` before implementing,
    # which is right, and the engine refused it as unknown because this run
    # only knew the base catalogue. Built and not wired, again.
    from loop_engine.core.step_content import extended_catalogue, extended_library
    core = default_core()
    catalogue = extended_catalogue(default_catalogue())
    library = extended_library(default_skill_library())
    # Structured state, not an accumulating transcript. Each step receives
    # the procedure, the current state and the latest observation, and
    # returns a patch; the reasoning that produced it is discarded.
    # Measured over 40 steps: an accumulating transcript grows 29.6x while
    # this grows 1.3x -- a 5.8x reduction in cumulative characters. Over a
    # twelve-hour run that is the difference between a loop that keeps
    # working and one that runs out of context.
    state = StepState.start(task, plan["gate_command"])
    state = state.apply({"observed_failure": plan["observed_error"]})
    steps, observation = [], ""
    PATCHABLE = ("hypothesis, ruled_out, files_examined, files_changed, "
                 "commands_run, unknowns, blocked_on, observed_failure")
    def run_provisioner(planned: str):
        """The alternative architecture: a read-only step decides what the
        next step is and what it gets. Static selection is the default;
        this runs only when a caller asks, and it never grants anything --
        admit_provision does, against the registered catalogue."""
        prov_layer = provision_step_layer(planned, catalogue, library)
        instance = compose_instance(core, prov_layer, workspace)
        profile = OpenCodeStepProfile(
            model=model, workspace=workspace,
            timeout_seconds=budget.grant("provision"),
            agent=instance.agent_name,
            additional_environment=("OLLAMA_API_KEY", "XDG_DATA_HOME"))
        session = OpenCodeStepSession(authority=ceiling, profile=profile)
        began = time.time()
        try:
            text = session.invoke(_Req(render_step_prompt(
                state, prov_layer.system_prompt, observation, PROVISION_SCHEMA)), None)
        finally:
            ceiling.charge(session, f"provision:{planned}")
        outcome = admit_provision(text, planned_next=planned, catalogue=catalogue,
                                  library=library, workspace=workspace)
        print(f"      [{time.strftime('%H:%M:%S')}] provision -> {outcome.next_step}"
              + (f" (plan said {planned})" if outcome.next_step != planned else "")
              + f", skills={sorted(outcome.granted_skills)}, "
              f"context={sorted(outcome.context_files)}  "
              f"({time.time() - began:.1f}s)", flush=True)
        if outcome.refusal_message():
            print(f"        refused: {outcome.refusal_message()[:140]}", flush=True)
        return outcome

    def ceiling_reached(index, name) -> bool:
        """Stop the path when its call ceiling is spent, and say so."""
        if not ceiling.exhausted:
            return False
        steps.append({"step": "ceiling", "attempt": index, "before": name,
                      "why": ("path model-call ceiling reached: "
                              f"{ceiling.charged}/{ceiling.total}")})
        print(f"      [{time.strftime('%H:%M:%S')}] {name} (attempt {index}) "
              f"not started: {ceiling.charged}/{ceiling.total} model calls "
              "spent on this path", flush=True)
        return True

    for index in range(1, attempts + 1):
        for name, schema in (("orient", PATCHABLE), ("implement", PATCHABLE)):
            if ceiling_reached(index, name):
                steps.append({"step": "state", "final": state.for_prompt()[:800],
                              "model_calls": ceiling.to_dict()})
                return steps, state
            if provisioning == "model":
                try:
                    prov = run_provisioner(name)
                    steps.append({"step": "provision", "attempt": index,
                                  "planned": name, "outcome": prov.to_dict()})
                    name = prov.next_step
                    layer = apply_provision(catalogue.select(name), prov)
                except (ProvisionError, Exception) as exc:      # noqa: BLE001
                    # A failed provisioner falls back to the static
                    # architecture for this step. It is an optimisation of
                    # what the step receives, never a gate on whether it runs.
                    steps.append({"step": "provision", "attempt": index,
                                  "planned": name, "error": str(exc)[:200]})
                    layer, _ = dynamic_step_layer(catalogue.select(name), task, library)
            else:
                layer, _ = dynamic_step_layer(catalogue.select(name), task, library)
            instance = compose_instance(core, layer, workspace)
            profile = OpenCodeStepProfile(
                model=model, workspace=workspace,
                timeout_seconds=budget.grant(name),
                agent=instance.agent_name,
                additional_environment=("OLLAMA_API_KEY", "XDG_DATA_HOME"))
            session = OpenCodeStepSession(
                authority=ceiling, profile=profile)
            began = time.time()
            print(f"      [{time.strftime('%H:%M:%S')}] {name} "
                  f"(attempt {index}) started", flush=True)
            try:
                text = session.invoke(_Req(render_step_prompt(
                    state, layer.system_prompt, observation, schema)), None)
                elapsed = time.time() - began
                patch = json.loads(text)
                try:
                    state = state.apply(patch)
                except Exception as exc:                    # noqa: BLE001
                    # A rejected patch is recorded and the state kept.
                    # Discarding the state because one step returned a bad
                    # field would lose every earlier observation.
                    steps.append({"step": name, "attempt": index,
                                  "patch_rejected": str(exc)[:200]})
                steps.append({"step": name, "attempt": index,
                              "seconds": round(elapsed, 1),
                              "state_chars": state.size(), "value": patch})
            except Exception as exc:                        # noqa: BLE001
                elapsed = time.time() - began
                steps.append({"step": name, "attempt": index,
                              "seconds": round(elapsed, 1),
                              "error": f"{type(exc).__name__}: {exc}"[:300]})
            ceiling.charge(session, f"{name}#{index}")
            # Printed and flushed per step, not collected for the end. A
            # run killed on a timeout previously produced no partial output
            # at all, so "where did the time go" had no answer but a guess.
            print(f"      [{time.strftime('%H:%M:%S')}] {name} "
                  f"(attempt {index}) took {elapsed:.1f}s", flush=True)
        ok, output = run_gate(plan["gate_command"], workspace, budget,
                              environment=environment)
        if ok:
            steps.append({"step": "state", "final": state.for_prompt()[:800],
                          "model_calls": ceiling.to_dict()})
            return steps, state
        if state.blocked():
            # A run that knows it is blocked says so and stops, rather than
            # spending the rest of the night proving it again.
            steps.append({"step": "blocked", "attempt": index,
                          "why": state.get("blocked_on")})
            return steps, state
        if index < attempts:
            # The failure changes the SHAPE of the next step, not its wording.
            #
            # The engine already ran the gate, so it hands the step the real
            # output and composes it with no shell at all. Using the bash
            # variant here was a live mistake with two costs: it left a write
            # path open on a step that must not write, and OpenCode installed
            # @opencode-ai/plugin into the instance directory -- 62 MB per
            # worktree -- because a step that can run commands gets plugin
            # support set up for it.
            if ceiling_reached(index, "observe"):
                break
            observed = _observe_gate(
                plan["gate_command"], workspace,
                timeout=budget.grant("observe-gate"), environment=environment)
            obs = observation_step_layer("gate", output,
                                         engine_observed=observed)
            instance = compose_instance(core, obs, workspace)
            profile = OpenCodeStepProfile(
                model=model, workspace=workspace,
                timeout_seconds=budget.grant("observe"),
                agent=instance.agent_name,
                additional_environment=("OLLAMA_API_KEY", "XDG_DATA_HOME"))
            session = OpenCodeStepSession(
                authority=ceiling, profile=profile)
            try:
                observation = session.invoke(_Req(render_step_prompt(
                    state, obs.system_prompt, observed.get("output", ""),
                    "observed_failure, unknowns, blocked_on")), None)[:1000]
                try:
                    state = state.apply(json.loads(observation))
                except Exception:                           # noqa: BLE001
                    pass    # prose is acceptable from an observation step
                steps.append({"step": "observe", "attempt": index,
                              "state_chars": state.size(),
                              "value": observation[:400]})
            except Exception as exc:                        # noqa: BLE001
                steps.append({"step": "observe", "attempt": index,
                              "error": str(exc)[:200]})
            ceiling.charge(session, f"observe#{index}")
    steps.append({"step": "state", "final": state.for_prompt()[:800],
                  "model_calls": ceiling.to_dict()})
    return steps, state


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
    ap.add_argument("--provisioning", choices=("static", "model"), default="static",
                    help="static: skills chosen from task text, fixed step order. "
                         "model: a read-only provisioning step runs between "
                         "cognitive steps and decides the next step, its skills "
                         "and its context files; the engine admits the request")
    ap.add_argument("--paths", type=int, default=1,
                    help="independent attempts per candidate, each its own "
                         "model and worktree; the gate picks (default 1)")
    ap.add_argument("--allow-transcript-gates", action="store_true",
                    help="execute gate commands harvested from Claude Code "
                         "transcripts. Without it they are planned and "
                         "reported, never run; a --gate you typed needs no flag")
    ap.add_argument("--allow-compound-gates", action="store_true",
                    help="attempt harvested commands that contain |, &&, ;, "
                         "$( or a backtick. Refused by default: one transcript "
                         "line can carry several commands and a shell")
    ap.add_argument("--gate-env", action="append", default=[], metavar="NAME",
                    help="admit one more environment variable into gate "
                         f"commands beyond {', '.join(GATE_ENV_ALLOWLIST)}; "
                         "repeatable")
    ap.add_argument("--gate-inherit-env", action="store_true",
                    help="run gates with the whole operator environment, as "
                         "earlier versions did")
    ap.add_argument("--require-clean-tree", action="store_true",
                    help="skip a candidate whose repository has modified "
                         "tracked files (untracked files never count)")
    ap.add_argument("--prune-worktrees", action="store_true",
                    help="remove registered overnight worktrees older than "
                         "--keep-days with `git worktree remove` and `git "
                         "branch -d`; both refuse unfinished work and the "
                         "report lists what was refused")
    ap.add_argument("--keep-days", type=float, default=WORKTREE_KEEP_DAYS,
                    help="with --prune-worktrees: age in days below which a "
                         f"worktree is kept (default {WORKTREE_KEEP_DAYS})")
    ap.add_argument("--prune-force", action="store_true",
                    help="with --prune-worktrees: force removal of worktrees "
                         "holding uncommitted changes and of branches with "
                         "unmerged commits, as earlier versions did")
    ap.add_argument("--max-model-calls", type=int, default=None,
                    help="model calls one solving path may make across all "
                         "its steps (default: --step-model-calls times the "
                         "planned steps); 0 means no path ceiling")
    ap.add_argument("--step-model-calls", type=int, default=4,
                    help="model calls one step may make (default 4)")
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
                         expected_steps=max(4, args.max_tasks * 3 * max(1, args.paths)))
    found = (seeded if args.gate else
             collect(args.since, args.max_tasks,
                     allow_compound=args.allow_compound_gates))
    policy = NightPolicy(
        require_clean_tree=args.require_clean_tree,
        prune_worktrees=args.prune_worktrees, keep_days=args.keep_days,
        prune_force=args.prune_force,
        gate_environment=gate_environment(args.gate_env,
                                          inherit=args.gate_inherit_env),
        max_model_calls=args.max_model_calls,
        step_model_calls=args.step_model_calls,
        allow_compound_gates=args.allow_compound_gates)
    print(f"overnight run {started} — {len(found)} candidate(s); "
          f"{args.hours:.0f}h budget\n", flush=True)
    if not found:
        print("  Nothing unresolved was observed today. Reporting that,")
        print("  rather than inventing work to look busy.")
        return 0

    report = {"started": started, "model": args.model,
              "dry_run": args.dry_run, "policy": policy.to_dict(),
              "allow_transcript_gates": bool(args.allow_transcript_gates),
              "tasks": []}
    for index, item in enumerate(found, 1):
        plan = gameplan(item, policy)
        print(f"{index}. [{plan['confidence']}] {plan['candidate']}")
        print(f"   gate     : {plan['gate_command'][:130] or '(none)'}")
        print(f"   accepts  : {plan['acceptance'][:130]}")
        print(f"   workspace: {plan['workspace']}")
        entry = {"plan": plan}
        harvested = plan.get("source") == "transcript"
        if (not args.dry_run and plan["verifiable"] and harvested
                and not args.allow_transcript_gates):
            # A command read out of a transcript would be executed here
            # with a shell and nobody watching. That is the operator's
            # call to make, once, on the command line; not this tool's to
            # assume.
            why = ("harvested from a transcript; pass "
                   "--allow-transcript-gates to execute it unattended")
            entry["outcome"] = {"status": "not_attempted", "why": why}
            print(f"   -> not attempted: {why}")
        elif not args.dry_run and plan["verifiable"]:
            outcome = attempt(plan, args.model, args.attempts, budget,
                              paths=args.paths, provisioning=args.provisioning,
                              policy=policy)
            entry["outcome"] = outcome
            print(f"   -> {outcome['status']}"
                  + (f": {outcome.get('why','')[:110]}" if outcome.get("why") else ""))
            if outcome.get("branch"):
                print(f"      branch {outcome['branch']}"
                      + ("  (mergeable)" if outcome.get("mergeable") else ""))
            sel = outcome.get("selection")
            if sel and len(sel.get("paths", [])) > 1:
                print(f"      chose {sel['chosen']}: {sel['why'][:140]}")
                if sel.get("chosen") is None:
                    # Nothing usable: say what each path actually did, so
                    # "no_progress" is never the whole story.
                    for path in sel.get("paths", []):
                        note = path.get("error") or path.get("rung")
                        print(f"        {path['label']} {path['model'].split('/')[-1]}: "
                              f"{note[:110]}")
        elif not plan["verifiable"]:
            print("   -> analysis only: " + (
                plan.get("refused")
                or "no executable gate, so nothing here can be verified"))
        print()
        report["tasks"].append(entry)

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"{time.strftime('%Y-%m-%d')}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    # entry["outcome"] is the attempt() result; the graded rung is nested
    # inside it under the same name. Reading the outer one crashed with
    # KeyError: 'rung' on the first real run.
    graded = [t["outcome"]["outcome"] for t in report["tasks"]
              if isinstance(t.get("outcome"), dict)
              and isinstance(t["outcome"].get("outcome"), dict)]
    report["time_spent"] = budget.spent()
    report["hours_used"] = round(budget.elapsed() / 3600, 2)

    from loop_engine.core.overnight_outcome import Outcome
    outcomes = [Outcome(g["rung"], g["because"], g.get("evidence", {}))
                for g in graded]
    summary = summarise(outcomes)
    report["summary"] = summary
    print(f"\n  {summary['headline']}")
    for item in rank(outcomes):
        mark = "*" if item.actionable else " "
        print(f"   {mark} {item.rung:16} {item.meaning}")
        print(f"     {item.because[:150]}")
    print(f"\n  {budget.elapsed() / 3600:.1f}h of {args.hours:.0f}h used")
    if budget.spent():
        print(f"  time went to: {budget.spent()}")
    print(f"  report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
