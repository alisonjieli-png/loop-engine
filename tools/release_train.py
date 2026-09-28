"""Pick reviewed commits onto a release train, regenerate every generated view, run the gates, and print the push and
release commands, without ever pushing.

Kind: development tool for the session that integrates reviewed work into main. Until September 27, 2026 a train was
built by hand: cherry-pick, resolve each conflict, regenerate some views, run some gates, push, and wait twenty
minutes for continuous integration to name what was missed. Train 2 of that day passed locally and failed in
continuous integration, because the status pages were built before a later record commit; train 5 hit the committed
shard estimates three times and a list both sides appended to. This script does the whole path in one command:

1. It refuses a worktree with uncommitted changes to tracked files, with a cherry-pick, merge or rebase in progress,
   or with a branch other than main checked out (parallel work uses detached worktrees; the checkpoint branch never
   moves).
2. It cherry-picks each commit with -x, in the order given, and skips a commit already on the train. On a conflict:
   - a generated file, one of the paths the train's tools/regenerate_all.py --outputs names, takes the train's
     side, because step 3 rebuilds it from its sources;
   - tools/ci_test_shards.json takes the side that is the version 2 manifest when the other side still lists modules,
     because the placement is computed at run time;
   - a YAML file where both sides appended whole entries to the same list keeps the train's entries, then the
     picked commit's. It is refused when a side changes a line that was already there, a side is not made of whole
     list entries, the result does not parse, or an identifier (finding_id or id) repeats that did not repeat on the
     train. This is the resolver the integrator used by hand for devtools/hardcoding-allowlist.yaml;
   - anything else stops the train. The conflict stays in place for a person, and the script names the files, the
     commit, and the command that continues with the commits still to pick.
3. It regenerates every view with the train's own tools/regenerate_all.py and commits what changed as one final
   "Regenerate generated views" commit.
4. It runs the train's own tools/pre_push_check.sh, whose gates include the pristine check of the exported HEAD, and
   repeats its result line, which says NOT EQUIVALENT TO CI whenever a step the workflow runs did not run. With
   --skip-gates it runs only the pristine check.
5. It prints the exact push command and the release commands of the guarded workflow
   .github/workflows/fly-pilot.yml. It never pushes, never changes a repository setting and never starts a workflow.

Usage:
    python tools/release_train.py --worktree PATH [--trailer "Name: value"] [--skip-gates] COMMIT [COMMIT ...]
Exit status: 0 the train is ready to push, 1 a gate or the pristine check failed, 2 the train stopped (a conflict it
does not resolve, a refused worktree, a builder that failed).
"""
from __future__ import annotations

import argparse
import collections
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

TOOLS = Path(__file__).resolve().parent
SHARD_MANIFEST = "tools/ci_test_shards.json"
SHARD_MANIFEST_V2 = "tools_test_shard_manifest/v2"
#: Keys that name one entry of a list; a resolved list append may not repeat one.
IDENTIFIER_KEYS = ("finding_id", "id")
REGENERATE_SUBJECT = "Regenerate generated views"
RELEASE_RECORDS = "artifacts/architecture-audit-2026-09-19/pilot-release-*.json"
DEPLOYMENT_SECTION = "docs/architecture/MVP-CLIENT-SERVER.md#current-deployment"
#: Every git command runs with these: conflicts in the diff3 form, so an append can be told from a change of an
#: existing line; no recorded resolution replayed; no editor waiting for a person.
GIT_SETTINGS = ("-c", "merge.conflictStyle=diff3", "-c", "rerere.enabled=false", "-c", "core.editor=true")
HUNK = re.compile(r"^<<<<<<< [^\n]*\n(?P<ours>.*?)^\|\|\|\|\|\|\| [^\n]*\n(?P<base>.*?)^=======\n(?P<theirs>.*?)"
                  r"^>>>>>>> [^\n]*\n", re.S | re.M)
ENTRY = re.compile(r"^(?P<indent> *)-(?: |$)")


class TrainStopped(Exception):
    """The train cannot go on without a person."""


class Unresolved(Exception):
    """One conflicted file this script does not resolve, with the reason."""


@dataclass
class Pick:
    commit: str
    subject: str
    result: str = ""
    notes: list = field(default_factory=list)


class ConflictStop(TrainStopped):
    """A pick with conflicts this script does not resolve; the cherry-pick is left in place."""

    def __init__(self, record: Pick, unresolved: list):
        super().__init__(f"{record.commit[:12]} {record.subject}: " + "; ".join(unresolved))
        self.record, self.unresolved = record, unresolved


def git(worktree: Path, *args, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess:
    if args and args[0] == "push":
        raise AssertionError("the release train never pushes")
    completed = subprocess.run(["git", *GIT_SETTINGS, "-C", str(worktree), *args], capture_output=True, text=True,
                               input=input_text, check=False)
    if check and completed.returncode != 0:
        raise TrainStopped(f"git {' '.join(args)} failed: {(completed.stderr or completed.stdout).strip()[-800:]}")
    return completed


def head(worktree: Path) -> str:
    return git(worktree, "rev-parse", "HEAD").stdout.strip()


def git_folder(worktree: Path) -> Path:
    folder = Path(git(worktree, "rev-parse", "--git-dir").stdout.strip())
    return folder if folder.is_absolute() else worktree / folder


def check_worktree(worktree: Path) -> str:
    """What HEAD is ("main" or "detached HEAD"); refuses a worktree the train cannot safely build in."""
    top = Path(git(worktree, "rev-parse", "--show-toplevel").stdout.strip())
    if top.resolve() != worktree.resolve():
        raise TrainStopped(f"{worktree} is inside the worktree {top}; give its top folder")
    folder = git_folder(worktree)
    for marker in ("CHERRY_PICK_HEAD", "MERGE_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
        if (folder / marker).exists():
            raise TrainStopped(f"{marker} exists in {folder}: finish or abort that operation first")
    changed = git(worktree, "status", "--porcelain", "--untracked-files=no").stdout
    if changed.strip():
        raise TrainStopped(f"the worktree has uncommitted changes to tracked files:\n{changed.rstrip()}")
    branch = git(worktree, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).stdout.strip()
    if branch and branch != "main":
        raise TrainStopped(f"{worktree} has the branch {branch} checked out; build a train on main or a detached "
                           "HEAD (the checkpoint branch never moves)")
    return branch or "detached HEAD"


def resolve_commits(worktree: Path, names) -> list:
    commits = []
    for name in names:
        full = git(worktree, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}", check=False).stdout.strip()
        if not full:
            raise TrainStopped(f"{name} is not a commit in this repository")
        if len(git(worktree, "rev-list", "--parents", "-n", "1", full).stdout.split()) > 2:
            raise TrainStopped(f"{name} is a merge commit; pick the commits it merged instead")
        commits.append(full)
    return commits


def tool_environment(worktree: Path) -> dict:
    return {**os.environ, "PYTHONPATH": os.pathsep.join([str(worktree / "src"), str(worktree / "tools")]),
            "PYTHONDONTWRITEBYTECODE": "1"}


def train_tool(worktree: Path, name: str) -> Path:
    """The train's own copy of a tool, or this script's sibling when the train does not have it yet."""
    own = worktree / "tools" / name
    return own if own.is_file() else TOOLS / name


def generated_outputs(worktree: Path, python: str) -> tuple:
    completed = subprocess.run([python, str(train_tool(worktree, "regenerate_all.py")), "--outputs"], cwd=worktree,
                               env=tool_environment(worktree), capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise TrainStopped(f"tools/regenerate_all.py --outputs failed: {completed.stderr.strip()[-600:]}")
    return tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())


def is_generated(path: str, outputs) -> bool:
    return any(path == output or (output.endswith("/") and path.startswith(output)) for output in outputs)


def unmerged_paths(worktree: Path) -> list:
    return sorted(path for path in git(worktree, "diff", "--name-only", "-z", "--diff-filter=U").stdout.split("\0")
                  if path)


def stages(worktree: Path, path: str) -> dict:
    """{stage number: blob} of one unmerged path: 1 the common ancestor, 2 the train, 3 the picked commit."""
    found = {}
    for entry in git(worktree, "ls-files", "-u", "-z", "--", path).stdout.split("\0"):
        if entry:
            info, _, _name = entry.partition("\t")
            _mode, blob, stage = info.split()
            found[int(stage)] = blob
    return found


def blob_text(worktree: Path, blob: str) -> str:
    return git(worktree, "cat-file", "blob", blob).stdout


def take_side(worktree: Path, path: str, stage: int, found: dict) -> None:
    """Resolve one path to the train's side (2) or the picked commit's side (3), a deletion included."""
    if stage in found:
        git(worktree, "checkout", "--ours" if stage == 2 else "--theirs", "--", path)
        git(worktree, "add", "--", path)
    else:
        git(worktree, "rm", "--quiet", "--force", "--", path)


def manifest_version(text: str):
    """2 for the manifest that names shards only, 1 for one that lists modules, None for anything else."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("shards"), dict):
        return 1
    return 2 if data.get("record_type") == SHARD_MANIFEST_V2 else None


def resolve_shard_manifest(worktree: Path, path: str, found: dict) -> str:
    ours = manifest_version(blob_text(worktree, found[2])) if 2 in found else None
    theirs = manifest_version(blob_text(worktree, found[3])) if 3 in found else None
    if (ours, theirs) == (2, 1):
        take_side(worktree, path, 2, found)
        return f"{path}: kept the train's version 2 manifest; the module lists of the picked commit are not needed"
    if (ours, theirs) == (1, 2):
        take_side(worktree, path, 3, found)
        return f"{path}: took the picked commit's version 2 manifest; the train's module lists are not needed"
    raise Unresolved(f"both sides changed the shard manifest (versions {ours} and {theirs}); only a version 1 "
                     "against a version 2 conflict is resolved here")


def _indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def entry_indent(side: str) -> str:
    """The indentation of the list entries one side of a hunk consists of; refuses anything else."""
    lines = side.splitlines()
    first = ENTRY.match(lines[0])
    if not first:
        raise Unresolved(f"a side does not start with a list entry: {lines[0][:80]!r}")
    indent = first.group("indent")
    for line in lines[1:]:
        entry = ENTRY.match(line)
        blank_or_comment = not line.strip() or line.lstrip().startswith("#")
        if blank_or_comment or (entry and entry.group("indent") == indent) or _indentation(line) > len(indent):
            continue
        raise Unresolved(f"a side holds a line outside its list entries: {line[:80]!r}")
    return indent


def resolve_list_appends(text: str) -> tuple:
    """(resolved text, hunk count) for a file whose every conflict appends whole entries to the same list."""
    hunks = list(HUNK.finditer(text))
    if not hunks:
        raise Unresolved("no conflict in the diff3 form")
    pieces, position = [], 0
    for hunk in hunks:
        if hunk.group("base").strip():
            raise Unresolved("a side changes lines that were already there, so this is not an append")
        indents = {entry_indent(side) for side in (hunk.group("ours"), hunk.group("theirs")) if side.strip()}
        if len(indents) != 1:
            raise Unresolved("the two sides append at different indentation")
        indent = indents.pop()
        following = next((line for line in text[hunk.end():].splitlines()
                          if line.strip() and not line.lstrip().startswith("#")), "")
        if following and _indentation(following) > len(indent):
            raise Unresolved(f"the conflict ends inside an entry: {following[:80]!r}")
        pieces += [text[position:hunk.start()], hunk.group("ours"), hunk.group("theirs")]
        position = hunk.end()
    resolved = "".join(pieces) + text[position:]
    if re.search(r"^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|) ", resolved, re.M):
        raise Unresolved("conflict markers remain outside the hunks this resolver reads")
    return resolved, len(hunks)


def identifier_repeats(data) -> set:
    """(list path, key, value) for every identifier that names more than one entry of the same list."""
    repeats = set()

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, path + (str(key),))
        elif isinstance(node, list):
            for key in IDENTIFIER_KEYS:
                counts = collections.Counter(str(item[key]) for item in node
                                             if isinstance(item, dict) and item.get(key) is not None)
                repeats.update((path, key, value) for value, count in counts.items() if count > 1)
            for item in node:
                walk(item, path + ("[]",))

    walk(data, ())
    return repeats


def resolve_yaml_appends(worktree: Path, path: str, found: dict) -> str:
    import yaml
    if 2 not in found or 3 not in found:
        raise Unresolved("one side deleted the file")
    resolved, count = resolve_list_appends((worktree / path).read_text(encoding="utf-8"))
    try:
        merged = yaml.safe_load(resolved)
    except yaml.YAMLError as error:
        raise Unresolved(f"the file does not parse after the append: {str(error).splitlines()[0]}") from None
    ours = yaml.safe_load(blob_text(worktree, found[2]))
    new = sorted(identifier_repeats(merged) - identifier_repeats(ours))
    if new:
        shown = ", ".join(f"{key} {value} in {'.'.join(where) or 'the top list'}" for where, key, value in new[:5])
        raise Unresolved(f"an identifier repeats after the append: {shown}")
    (worktree / path).write_text(resolved, encoding="utf-8")
    git(worktree, "add", "--", path)
    return f"{path}: {count} list appends kept, the train's entries first"


def nothing_staged(worktree: Path) -> bool:
    return git(worktree, "diff", "--cached", "--quiet", check=False).returncode == 0


def pick(worktree: Path, commit: str, python: str) -> Pick:
    """Cherry-pick one commit with -x, resolving the conflicts this script resolves; raises when it stops."""
    record = Pick(commit, git(worktree, "log", "-1", "--format=%s", commit).stdout.strip())
    attempt = git(worktree, "cherry-pick", "-x", commit, check=False)
    if attempt.returncode == 0:
        record.result = head(worktree)
        return record
    in_progress = (git_folder(worktree) / "CHERRY_PICK_HEAD").exists()
    conflicted = unmerged_paths(worktree)
    if not conflicted:
        if in_progress and nothing_staged(worktree):
            git(worktree, "cherry-pick", "--skip")
            record.notes.append("already on the train; skipped")
            return record
        raise TrainStopped(f"git cherry-pick -x {commit[:12]} failed without a conflict:\n"
                           f"{(attempt.stderr or attempt.stdout).strip()[-800:]}")
    outputs = generated_outputs(worktree, python)
    unresolved = []
    for path in conflicted:
        found = stages(worktree, path)
        try:
            if is_generated(path, outputs):
                take_side(worktree, path, 2, found)
                record.notes.append(f"{path}: generated; took the train's side, regenerated after the last pick")
            elif path == SHARD_MANIFEST:
                record.notes.append(resolve_shard_manifest(worktree, path, found))
            elif path.endswith((".yaml", ".yml")):
                record.notes.append(resolve_yaml_appends(worktree, path, found))
            else:
                raise Unresolved("not a generated file, the shard manifest or a list both sides appended to")
        except Unresolved as reason:
            unresolved.append(f"{path}: {reason}")
    if unresolved:
        raise ConflictStop(record, unresolved)
    if nothing_staged(worktree):
        git(worktree, "cherry-pick", "--skip")
        record.notes.append("nothing left after the resolution; skipped")
        return record
    git(worktree, "cherry-pick", "--continue")
    record.result = head(worktree)
    return record


def changed_paths(worktree: Path) -> list:
    """Tracked files that differ from HEAD and untracked files, as git status names them."""
    paths = []
    entries = git(worktree, "status", "--porcelain", "-z", "--untracked-files=all").stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            index += 1
    return sorted(paths)


def run_streamed(command: list, *, cwd: Path, env: dict, log) -> tuple:
    """(exit status, output lines), each line logged as it arrives."""
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = []
    for line in process.stdout:
        lines.append(line.rstrip("\n"))
        log(f"    {lines[-1]}")
    return process.wait(), lines


def regenerate(worktree: Path, python: str, skip_views: tuple, trailers: tuple, log) -> str:
    """Regenerate every view; commit what changed as one final commit; the new commit or ""."""
    before = set(changed_paths(worktree))
    command = [python, str(train_tool(worktree, "regenerate_all.py")), "--root", str(worktree)]
    if skip_views:
        command += ["--skip", ",".join(skip_views)]
    status, _lines = run_streamed(command, cwd=worktree, env=tool_environment(worktree), log=log)
    if status != 0:
        raise TrainStopped(f"tools/regenerate_all.py exited {status}; the train has no regenerated views")
    outputs = generated_outputs(worktree, python)
    changed = [path for path in changed_paths(worktree) if path not in before]
    stray = [path for path in changed if not is_generated(path, outputs)]
    if stray:
        raise TrainStopped(f"the regeneration changed files that are not generated views: {', '.join(stray)}")
    if not changed:
        return ""
    git(worktree, "add", "-A", "--", *changed)
    body = "\n".join(f"- {path}" for path in changed)
    message = (f"{REGENERATE_SUBJECT}\n\ntools/regenerate_all.py rewrote these files after the last pick of the "
               f"release train, so that every generated view matches the commit it is pushed with:\n{body}\n")
    if trailers:
        message += "\n" + "\n".join(trailers) + "\n"
    git(worktree, "commit", "-q", "-F", "-", input_text=message)
    return head(worktree)


def check_gates(worktree: Path, python: str, skip_gates: bool, skip_views: tuple, log) -> tuple:
    """(exit status, result line) of the full pre-push gates, or of the pristine check alone."""
    if skip_gates:
        command = [python, str(train_tool(worktree, "regenerate_all.py")), "--root", str(worktree), "--pristine"]
        if skip_views:
            command += ["--skip", ",".join(skip_views)]
        status, _lines = run_streamed(command, cwd=worktree, env=tool_environment(worktree), log=log)
        verdict = "the pristine check passed" if status == 0 else f"the pristine check FAILED (exit {status})"
        left_out = f"; views left out: {', '.join(skip_views)}" if skip_views else ""
        return status, f"RESULT: {verdict}; NOT EQUIVALENT TO CI (--skip-gates ran no gate of the workflow{left_out})"
    environment = {**os.environ, "PY": os.environ.get("PY") or python}
    status, lines = run_streamed(["bash", str(worktree / "tools" / "pre_push_check.sh"), "--tree", str(worktree)],
                                 cwd=worktree, env=environment, log=log)
    result = next((line.strip() for line in reversed(lines) if line.startswith("RESULT:")),
                  f"RESULT: the pre-push check printed no result line (exit {status})")
    return status, result


def newest_release(worktree: Path) -> tuple:
    """(application name, next release number) from the newest pilot release record, or placeholders."""
    newest = None
    for path in worktree.glob(RELEASE_RECORDS):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data.get("release"), int) and (newest is None or data["release"] > newest["release"]):
            newest = data
    if not newest:
        return "FLY_APP", "N"
    return str(newest.get("app") or "FLY_APP"), newest["release"] + 1


def repository_slug(worktree: Path) -> str:
    remote = git(worktree, "remote", "get-url", "origin", check=False).stdout.strip()
    found = re.search(r"github\.com[:/](?P<slug>[^/\s]+/[^/\s]+?)(?:\.git)?/?$", remote)
    return found.group("slug") if found else "OWNER/REPOSITORY"


def push_and_release_commands(worktree: Path, revision: str) -> list:
    """The commands a person runs after the train is ready; none of them is run here."""
    repository = repository_slug(worktree)
    app, release = newest_release(worktree)
    tree = shlex.quote(str(worktree))
    on = f"--repo {repository}"
    ci_run = (f"gh run list {on} --workflow ci.yml --commit {revision} --limit 1 --json databaseId "
              "--jq '.[0].databaseId'")
    deploy_run = (f"gh run list {on} --workflow fly-pilot.yml --event workflow_dispatch --limit 1 --json databaseId "
                  "--jq '.[0].databaseId'")
    return [
        "# 1. Push: reviewed work goes to main without asking (AGENTS.md, commit, push and release authority).",
        f"git -C {tree} push origin HEAD:main",
        "# 2. Wait for continuous integration on this exact revision; release only when it passed.",
        f"gh run watch {on} --exit-status \"$({ci_run})\"",
        "# 3. Release through the guarded workflow: the deployment setting on for the run, off again whatever the",
        "#    result, then read back as false.",
        f"gh variable set FLY_DEPLOY_ENABLED {on} --env pilot --body true",
        f"gh workflow run fly-pilot.yml {on} --ref main -f operation=deploy -f app_confirmation={app} "
        f"-f revision={revision}",
        f"sleep 15; gh run watch {on} --exit-status \"$({deploy_run})\"",
        f"gh variable set FLY_DEPLOY_ENABLED {on} --env pilot --body false",
        f"gh variable list {on} --env pilot",
        f"# 4. Run the automated live checks on every hostname {DEPLOYMENT_SECTION} lists, then record",
        f"#    release {release} with its revision, image digest and rollback image, and update that section in the",
        "#    same change.",
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("commits", nargs="+", help="the commits to pick, in order")
    parser.add_argument("--worktree", type=Path, required=True, help="the worktree the train is built in")
    parser.add_argument("--python", default=sys.executable, help="the interpreter with the project's extras")
    parser.add_argument("--trailer", action="append", default=[],
                        help="a trailer line for the regeneration commit, such as Co-Authored-By: ... (repeatable)")
    parser.add_argument("--skip-view", default="",
                        help="comma-separated views the regeneration and the --skip-gates pristine check leave out")
    parser.add_argument("--skip-gates", action="store_true",
                        help="run only the pristine check, not the pre-push gates (the result is not equivalent to CI)")
    arguments = parser.parse_args(argv)
    worktree = arguments.worktree.resolve()
    skip_views = tuple(view for view in arguments.skip_view.split(",") if view)
    log = print
    started = time.monotonic()
    picks = []
    try:
        where = check_worktree(worktree)
        commits = resolve_commits(worktree, arguments.commits)
        log(f"release train in {worktree} ({where}) on {head(worktree)[:12]}: {len(commits)} commits")
        for position, commit in enumerate(commits):
            try:
                record = pick(worktree, commit, arguments.python)
            except ConflictStop as stop:
                log(f"STOPPED at {commit[:12]} {stop.record.subject}")
                log("  these conflicts need a person; the cherry-pick is left in place:")
                log("\n".join(f"    {line}" for line in stop.unresolved))
                log("  resolved here: " + ("; ".join(stop.record.notes) or "nothing"))
                rest = " ".join(commits[position + 1:])
                log(f"  after resolving: git -C {shlex.quote(str(worktree))} add FILES && "
                    f"git -C {shlex.quote(str(worktree))} cherry-pick --continue")
                if rest:
                    log(f"  then continue the train: python {Path(__file__).name} --worktree {worktree} {rest}")
                log(f"  or give up this pick: git -C {shlex.quote(str(worktree))} cherry-pick --abort")
                return 2
            picks.append(record)
            shown = f"-> {record.result[:12]}" if record.result else "(no commit)"
            log(f"  picked {commit[:12]} {shown}  {record.subject}")
            for note in record.notes:
                log(f"         {note}")
        log("regenerating every generated view")
        regenerated = regenerate(worktree, arguments.python, skip_views, tuple(arguments.trailer), log)
        log(f"  {REGENERATE_SUBJECT}: {regenerated[:12]}" if regenerated else "  every generated view was current")
    except TrainStopped as stop:
        log(f"STOPPED: {stop}")
        return 2
    log("running the gates" if not arguments.skip_gates else "running the pristine check (--skip-gates)")
    status, result = check_gates(worktree, arguments.python, arguments.skip_gates, skip_views, log)
    revision = head(worktree)
    minutes = (time.monotonic() - started) / 60
    log(f"train of {len(picks)} picks on {revision} in {minutes:.1f} minutes")
    log(result)
    if status != 0:
        log("NOT READY: repair what failed above, then run the gates again; nothing was pushed")
        return 1
    behind = git(worktree, "merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode
    if behind == 1:
        log("WARNING: origin/main is not an ancestor of the train, so a push would be refused; fetch and rebuild")
    log("READY. This script never pushes; the commands, in order:")
    log("\n".join(f"  {line}" for line in push_and_release_commands(worktree, revision)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
