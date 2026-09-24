"""Check that one unattended ticket keeps git history safe. Effects: runs local git commands, reads the repository and writes one state file under .baltor/state/unattended-git-rules/; no network, no model call.

    begin  --ticket KEY
        Record where the ticket starts: the commit, the branch, every other
        reference, the number of HEAD movements and the files that were already
        changed or untracked. Refused while a merge, rebase, cherry-pick, revert
        or bisect is in progress, or when tracked files are already changed
        other than the root instruction files (AGENTS.md, CLAUDE.md, GEMINI.md)
        and the paths the host lists in .baltor/unattended-git-rules/host-placed.json.
    verify --ticket KEY [--require-commit | --no-change]
        Compare the repository with the recorded start. It fails when the history
        before the ticket changed, HEAD moved by anything other than a plain
        commit, a branch or tag was created, deleted or rewritten, a
        remote-tracking reference changed, the stash was used, more than one
        commit was made, the commit does not name the ticket key, the commit
        holds .baltor/ files or files that were changed before the ticket, a
        file that was changed before the ticket is now different, or a file
        that was untracked before the ticket is gone. With --require-commit it
        also fails until exactly one commit exists and no tracked change is left
        outside it. With --no-change it fails when any commit or tracked change
        exists, for a ticket that needs no change.

The host list is one JSON object, {"record_type": "unattended_git_host_placed/v1",
"paths": [...]}, written by the host after it places or merges files for the
step. Each path is relative to the workspace root; a path that ends in "/"
covers every file below that folder. Listed files may be changed before the
ticket; they are then protected like every other earlier change.

Run it from the workspace root, or name the root with --root. Every answer is
one JSON object on standard output with a "next" field. Exit 0: pass. Exit 1: a
rule failed. Exit 2: the input was refused.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

STATE_FOLDERS = (".baltor", "state", "unattended-git-rules")
HARNESS_FOLDER = ".baltor"
HOST_PLACED = (".baltor", "unattended-git-rules", "host-placed.json")
HOST_PLACED_TYPE = "unattended_git_host_placed/v1"
RECORD_TYPE = "unattended_git_ticket_start/v2"
TICKET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
ROOT_INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
IN_PROGRESS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG", "rebase-merge", "rebase-apply")
PLAIN_COMMIT = ("commit: ", "commit (initial): ")
MAX_GIT_OUTPUT = 8 * 1024 * 1024
MAX_STATE_BYTES = 4 * 1024 * 1024
MAX_HOST_PLACED_BYTES = 1024 * 1024
MAX_HOST_PATHS = 2000
MAX_CHANGED = 2000
MAX_HASHED_BYTES = 256 * 1024 * 1024
MAX_FILE_HASHED = 16 * 1024 * 1024
MAX_LISTED = 50
GIT_TIMEOUT = 60
NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
NEXT_COMMIT = ("Stage the files you changed by name, commit once with the ticket key in the message, "
               "then run verify --ticket KEY --require-commit.")
NEXT_NOTHING = ("Nothing is changed for this ticket yet. Commit only when the ticket needs a change and its checks "
                "pass. If the ticket needs no change, run verify --ticket KEY --no-change.")
NEXT_LEFT_OUT = ("Tracked changes are outside the ticket commit. Do not make a second commit. "
                 "Record the ticket as blocked and include this answer.")
NEXT_DONE = "The git rules hold for this ticket."
NEXT_NO_CHANGE = "The ticket changed nothing and made no commit. The git rules hold for this ticket."
NEXT_FAIL = ("Do not try to repair the history. Leave the repository as it is, "
             "record the ticket as blocked and include this answer.")
NEXT_INPUT = "Fix the command and run it again. If it is refused again, record the ticket as blocked with this answer."
NEXT_REFUSED = {
    "ticket_already_begun": "An earlier attempt began this ticket. Run verify --ticket KEY to see its state. "
                            "Do not run begin again.",
    "tree_not_clean": "Tracked files were changed before this ticket. Do not commit them and do not discard them. "
                      "Record the ticket as blocked and include this answer.",
    "operation_in_progress": "Git is in the middle of another operation. Do not finish or abort it yourself. "
                             "Record the ticket as blocked and include this answer.",
    "host_placed_invalid": "The host's list of placed files cannot be used. Do not edit it. "
                           "Record the ticket as blocked and include this answer.",
}
#: Marks a file that was untracked before the ticket: kept out of the ticket, never fingerprinted.
UNTRACKED = "untracked"


class Refusal(Exception):
    """A refused command: the exit status, a stable code and a short detail."""

    def __init__(self, status: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status, self.code, self.detail = status, code, detail


def rule(code: str, detail: str) -> Refusal:
    return Refusal(1, code, detail)


def bad_input(code: str, detail: str) -> Refusal:
    return Refusal(2, code, detail)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # an argument error is refused input, answered as JSON
        raise bad_input("arguments_invalid", message)


def parse(argv) -> argparse.Namespace:
    parser = Parser(prog="git_ticket_check.py", description="Git safety checks for one unattended ticket.")
    commands = parser.add_subparsers(dest="command", required=True)
    begin = commands.add_parser("begin", help="record where the ticket starts")
    verify = commands.add_parser("verify", help="compare the repository with the recorded start")
    ending = verify.add_mutually_exclusive_group()
    ending.add_argument("--require-commit", action="store_true", help="the ticket ends with exactly one commit")
    ending.add_argument("--no-change", action="store_true", help="the ticket ends with no commit and no change")
    for command in (begin, verify):
        command.add_argument("--ticket", required=True)
        command.add_argument("--root", default=".")
    return parser.parse_args(argv)


def capped(values) -> list:
    return list(values)[:MAX_LISTED]


def git(root: Path, *arguments: str, allowed=(0,)) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment.update({"LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
    try:
        finished = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, env=environment,
                                  timeout=GIT_TIMEOUT, check=False)
    except FileNotFoundError:
        raise bad_input("git_missing", "the git command was not found") from None
    except subprocess.TimeoutExpired:
        raise bad_input("git_timeout", f"git {arguments[0]} did not finish in {GIT_TIMEOUT} seconds") from None
    if len(finished.stdout) > MAX_GIT_OUTPUT:
        raise bad_input("git_output_too_large", f"git {arguments[0]} printed more than {MAX_GIT_OUTPUT} bytes")
    if finished.returncode not in allowed:
        message = finished.stderr.decode("utf-8", "replace").strip().splitlines()
        raise bad_input("git_failed", f"git {arguments[0]} exited {finished.returncode}: {(message or [''])[-1][:200]}")
    return finished


def text(finished: subprocess.CompletedProcess) -> str:
    return finished.stdout.decode("utf-8", "surrogateescape").strip()


def workspace(value: str) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        raise bad_input("root_missing", "the --root folder does not exist") from None
    if not root.is_dir():
        raise bad_input("root_missing", "the --root path is not a folder")
    if text(git(root, "rev-parse", "--is-inside-work-tree", allowed=(0, 128))) != "true":
        raise bad_input("not_a_repository", "the workspace is not inside a git work tree")
    return root


def ticket_key(value: str) -> str:
    if not TICKET.fullmatch(value or ""):
        raise bad_input("ticket_invalid", "a ticket key is 1 to 64 letters, digits, dots, dashes or underscores, "
                                          "starting with a letter or digit")
    return value


def state_path(root: Path, ticket: str, create: bool) -> Path:
    """Return the state file path; refuse a symbolic link or a file where a folder belongs.

    Two commands may create the folders at the same moment, so a folder that
    appears between the check and the creation is accepted, then checked again.
    """
    current = root
    for part in STATE_FOLDERS:
        current = current / part
        shown = current.relative_to(root).as_posix()
        if current.is_symlink():
            raise bad_input("unsafe_state_path", f"{shown} is a symbolic link")
        if create and not current.exists():
            try:
                current.mkdir(exist_ok=True)
            except OSError:
                raise bad_input("unsafe_state_path", f"{shown} cannot be created as a folder") from None
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise bad_input("unsafe_state_path", f"{shown} is not a folder")
    path = current / f"{ticket}.json"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise bad_input("unsafe_state_path", f"the state file of {ticket} is not a regular file")
    return path


def strict_json(data: bytes):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def host_placed(root: Path) -> list:
    """The workspace-relative paths the host placed or merged for this step, or an empty list without a host list."""
    path = root.joinpath(*HOST_PLACED)
    shown = "/".join(HOST_PLACED)
    for parent in (path.parent.parent, path.parent):
        if parent.is_symlink():
            raise bad_input("host_placed_invalid", f"{parent.relative_to(root).as_posix()} is a symbolic link")
    if not path.exists() and not path.is_symlink():
        return []
    if path.is_symlink() or not path.is_file():
        raise bad_input("host_placed_invalid", f"{shown} is not a regular file")
    if path.stat().st_size > MAX_HOST_PLACED_BYTES:
        raise bad_input("host_placed_invalid", f"{shown} is larger than {MAX_HOST_PLACED_BYTES} bytes")
    try:
        record = strict_json(path.read_bytes())
    except (UnicodeDecodeError, ValueError):
        raise bad_input("host_placed_invalid", f"{shown} is not strict JSON") from None
    if not isinstance(record, dict) or set(record) != {"record_type", "paths"} \
            or record["record_type"] != HOST_PLACED_TYPE or not isinstance(record["paths"], list) \
            or len(record["paths"]) > MAX_HOST_PATHS:
        raise bad_input("host_placed_invalid", f"{shown} is not an {HOST_PLACED_TYPE} record "
                                               f"with at most {MAX_HOST_PATHS} paths")
    paths = []
    for value in record["paths"]:
        pure = Path(value) if isinstance(value, str) else None
        if (pure is None or not value or len(value) > 300 or "\\" in value or value.startswith("/")
                or any(ord(character) < 32 for character in value) or not pure.parts or ".." in pure.parts
                or pure.parts[0] in (HARNESS_FOLDER, ".git")):
            raise bad_input("host_placed_invalid", f"{value!r} is not a file or folder path inside the workspace "
                                                   "and outside .baltor/")
        paths.append(pure.as_posix() + ("/" if value.endswith("/") else ""))
    return paths


def is_listed(path: str, listed: list, prefix: str) -> bool:
    """True when a repository-relative path is one of the listed workspace paths or below a listed folder."""
    for value in listed:
        target = prefix + value
        if path == target or (value.endswith("/") and path.startswith(target)):
            return True
    return False


def write_state(path: Path, record: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    if temporary.is_symlink() or (temporary.exists() and not temporary.is_file()):
        raise bad_input("unsafe_state_path", "a leftover temporary state file is not a regular file")
    if temporary.exists():
        temporary.unlink()
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NO_FOLLOW, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=1, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_state(path: Path, ticket: str) -> dict:
    if not path.exists():
        raise bad_input("state_missing", f"no begin record for {ticket}; run begin --ticket {ticket} first")
    if path.stat().st_size > MAX_STATE_BYTES:
        raise bad_input("state_unreadable", "the state file is too large")
    try:
        record = strict_json(path.read_bytes())
    except (UnicodeDecodeError, ValueError):
        raise bad_input("state_unreadable", "the state file is not strict JSON") from None
    expected = {"record_type", "ticket", "base", "branch", "prefix", "references", "reflog_entries",
                "preexisting", "host_placed", "begun_at"}
    if not isinstance(record, dict) or set(record) != expected or record["record_type"] != RECORD_TYPE \
            or record["ticket"] != ticket or not isinstance(record["references"], dict) \
            or not isinstance(record["preexisting"], dict) or not isinstance(record["host_placed"], list):
        raise bad_input("state_unreadable", "the state file is not a begin record for this ticket")
    return record


def operations_in_progress(root: Path) -> list:
    found = []
    for name in IN_PROGRESS:
        location = Path(text(git(root, "rev-parse", "--git-path", name)))
        if not location.is_absolute():
            location = root / location
        if location.exists():
            found.append(name)
    return found


def head_commit(root: Path):
    finished = git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}", allowed=(0, 1, 128))
    return text(finished) if finished.returncode == 0 else None


def current_branch(root: Path):
    finished = git(root, "symbolic-ref", "--quiet", "HEAD", allowed=(0, 1))
    return text(finished) if finished.returncode == 0 else None


def references(root: Path) -> dict:
    values = {}
    for line in text(git(root, "for-each-ref", "--format=%(refname)%09%(objectname)")).splitlines():
        name, _tab, digest = line.partition("\t")
        if name:
            values[name] = digest
    return values


def worktree_branches(root: Path) -> set:
    """Branches checked out in any worktree of this repository."""
    branches = set()
    for line in text(git(root, "worktree", "list", "--porcelain")).splitlines():
        if line.startswith("branch "):
            branches.add(line[len("branch "):])
    return branches


def reflog_subjects(root: Path):
    """Subjects of HEAD movements, newest first; an empty list before the first commit."""
    finished = git(root, "reflog", "show", "--format=%gs", "HEAD", allowed=(0, 128))
    if finished.returncode != 0:
        return []
    return finished.stdout.decode("utf-8", "replace").splitlines()


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return git(root, "merge-base", "--is-ancestor", older, newer, allowed=(0, 1, 128)).returncode == 0


def under_harness_folder(path: str, prefix: str) -> bool:
    folder = prefix + HARNESS_FOLDER
    return path == folder or path.startswith(folder + "/")


def status_entries(root: Path, prefix: str) -> list:
    """(code, path) pairs from git status, paths relative to the repository top, .baltor/ left out."""
    raw = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    fields = raw.split(b"\0")
    entries, index = [], 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if len(field) < 4:
            continue
        code = field[:2].decode("ascii", "replace")
        paths = [field[3:].decode("utf-8", "surrogateescape")]
        if code[0] in "RC" and index < len(fields):
            paths.append(fields[index].decode("utf-8", "surrogateescape"))
            index += 1
        for path in paths:
            if not under_harness_folder(path, prefix):
                entries.append((code, path))
    if len(entries) > MAX_CHANGED:
        raise bad_input("too_many_changed_files", f"more than {MAX_CHANGED} changed or untracked files")
    return entries


class Hasher:
    """Fingerprints of files, with a total byte budget so a huge tree cannot stall the check."""

    def __init__(self, top: Path) -> None:
        self.top, self.remaining = top, MAX_HASHED_BYTES

    def state(self, relative: str) -> str:
        path = self.top / relative
        try:
            info = path.lstat()
        except FileNotFoundError:
            return "missing"
        if stat.S_ISLNK(info.st_mode):
            target = os.readlink(path).encode("utf-8", "surrogateescape")
            return "link:" + hashlib.sha256(target).hexdigest()
        if stat.S_ISDIR(info.st_mode):
            return "folder"
        if not stat.S_ISREG(info.st_mode):
            return "special"
        if info.st_size > MAX_FILE_HASHED or info.st_size > self.remaining:
            return f"unhashed:{info.st_size}:{info.st_mtime_ns}"
        self.remaining -= info.st_size
        with open(path, "rb") as stream:
            return "sha256:" + hashlib.sha256(stream.read()).hexdigest()


def repository_top(root: Path) -> Path:
    return Path(text(git(root, "rev-parse", "--show-toplevel")))


def command_begin(root: Path, ticket: str) -> dict:
    path = state_path(root, ticket, create=True)
    if path.exists():
        raise rule("ticket_already_begun", f"{ticket} already has a begin record; run verify instead")
    busy = operations_in_progress(root)
    if busy:
        raise rule("operation_in_progress", f"git has an operation in progress: {busy}")
    prefix = text(git(root, "rev-parse", "--show-prefix"))
    listed = list(ROOT_INSTRUCTION_FILES) + host_placed(root)
    entries = status_entries(root, prefix)
    blocking = sorted({entry_path for code, entry_path in entries
                       if code != "??" and not is_listed(entry_path, listed, prefix)})
    if blocking:
        raise rule("tree_not_clean", f"tracked files were changed before the ticket and the host did not list "
                                     f"them as placed: {blocking[:10]}")
    hasher = Hasher(repository_top(root))
    base, branch = head_commit(root), current_branch(root)
    record = {"record_type": RECORD_TYPE, "ticket": ticket, "base": base, "branch": branch, "prefix": prefix,
              "references": {name: digest for name, digest in references(root).items() if name != branch},
              "reflog_entries": len(reflog_subjects(root)),
              "preexisting": {entry_path: UNTRACKED if code == "??" else hasher.state(entry_path)
                              for code, entry_path in entries},
              "host_placed": listed[len(ROOT_INSTRUCTION_FILES):],
              "begun_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()}
    write_state(path, record)
    return {"result": "begun", "ticket": ticket, "base": base, "branch": branch,
            "preexisting": capped(sorted(record["preexisting"])),
            "state_file": "/".join(STATE_FOLDERS + (f"{ticket}.json",)),
            "next": f"Work on the ticket. Before you commit, run verify --ticket {ticket}."}


def reference_problems(root: Path, before: dict, after: dict, branch) -> list:
    problems, checked_out = [], None
    for name in sorted((set(before) | set(after)) - {branch}):
        old, new = before.get(name), after.get(name)
        if old == new:
            continue
        if name.startswith("refs/remotes/"):
            problems.append(("remote_refs_changed", f"{name} changed; pushing and fetching are not allowed"))
        elif name == "refs/stash":
            problems.append(("stash_used", "the stash changed; stashing hides or discards work"))
        elif name.startswith("refs/tags/"):
            if old is None:
                problems.append(("tag_created", f"{name} was created; tickets create no tags"))
            else:
                problems.append(("tag_moved_or_deleted", f"{name} was moved or deleted"))
        elif name.startswith("refs/heads/"):
            if new is None:
                problems.append(("branch_deleted", f"{name} was deleted"))
            elif old is None:
                if checked_out is None:
                    checked_out = worktree_branches(root)
                if name not in checked_out:  # a branch another worktree has checked out belongs to that worktree
                    problems.append(("branch_created", f"{name} was created; tickets create no branches"))
            elif not is_ancestor(root, old, new):
                problems.append(("branch_rewritten", f"{name} moved to a commit that does not contain its old commit"))
        else:
            problems.append(("other_reference_changed", f"{name} was added, moved or deleted"))
    return problems


def names_ticket(subject: str, ticket: str) -> bool:
    """True when the subject names the whole key: no key character touches it on either side.

    A dot counts as part of a key only when a key character follows it, so "Fix ABC-7." names ABC-7
    and "ABC-7.2: ..." does not.
    """
    pattern = (r"(?<![A-Za-z0-9._-])" + re.escape(ticket) + r"(?![A-Za-z0-9_-])(?!\.[A-Za-z0-9_-])")
    return re.search(pattern, subject) is not None


def commit_paths(root: Path, base, head: str) -> list:
    if base is None:
        raw = git(root, "diff-tree", "--root", "-r", "--name-only", "-z", "--no-commit-id", "--no-renames", head).stdout
    else:
        raw = git(root, "diff", "--name-only", "-z", "--no-renames", base, head).stdout
    return [part.decode("utf-8", "surrogateescape") for part in raw.split(b"\0") if part]


def command_verify(root: Path, ticket: str, require_commit: bool, no_change: bool) -> tuple:
    state = read_state(state_path(root, ticket, create=False), ticket)
    prefix = text(git(root, "rev-parse", "--show-prefix"))
    if prefix != state["prefix"]:
        raise bad_input("root_changed", "verify runs from the same workspace root as begin")
    violations = []

    def fail(code: str, detail: str) -> None:
        violations.append({"code": code, "detail": detail})

    busy = operations_in_progress(root)
    if busy:
        fail("operation_in_progress", f"git has an operation in progress: {busy}")
    branch = current_branch(root)
    if branch != state["branch"]:
        fail("branch_changed", f"the ticket began on {state['branch'] or 'a detached HEAD'} "
                               f"and is now on {branch or 'a detached HEAD'}")
    head, base = head_commit(root), state["base"]
    count = None
    if base is not None and (head is None or not is_ancestor(root, base, head)):
        fail("history_rewritten", "the commit the ticket began from is no longer in the current history")
    elif head is not None:
        span = head if base is None else f"{base}..{head}"
        count = int(text(git(root, "rev-list", "--count", span)))
    else:
        count = 0
    subjects = reflog_subjects(root)
    added = len(subjects) - int(state["reflog_entries"] or 0)
    if added < 0:
        fail("reflog_shortened", "entries of the HEAD movement log were removed")
    for subject in subjects[:max(added, 0)]:
        if not subject.startswith(PLAIN_COMMIT):
            fail("head_moved_by_other_command", subject[:160])
    for code, detail in reference_problems(root, state["references"], references(root), state["branch"]):
        fail(code, detail)
    subject, paths = None, []
    if count is not None and count > 1:
        fail("too_many_commits", f"{count} commits since the ticket began; the rule allows one")
    elif count == 1:
        subject = text(git(root, "log", "-1", "--format=%s", head))
        if not names_ticket(subject, ticket):
            fail("commit_missing_ticket_key", f"the commit message does not name {ticket}: {subject[:120]}")
        paths = commit_paths(root, base, head)
        harness = [path for path in paths if under_harness_folder(path, prefix)]
        if harness:
            fail("commit_includes_harness_files", f"the commit holds files of {prefix}{HARNESS_FOLDER}/: {harness[:10]}")
        earlier = [path for path in paths if path in state["preexisting"]]
        if earlier:
            fail("commit_includes_preexisting_changes", f"the commit holds files changed before the ticket: {earlier[:10]}")
    top = repository_top(root)
    hasher = Hasher(top)
    altered = sorted(path for path, value in state["preexisting"].items()
                     if value != UNTRACKED and not value.startswith("unhashed:") and hasher.state(path) != value)
    if altered:
        fail("preexisting_change_altered", f"files changed before the ticket are now different: {altered[:10]}")
    removed = sorted(path for path, value in state["preexisting"].items()
                     if value == UNTRACKED and not os.path.lexists(top / path))
    if removed:
        fail("preexisting_untracked_removed", f"files that were untracked before the ticket are gone, for example "
                                              f"after git clean: {removed[:10]}")
    staged, unstaged, untracked = set(), set(), set()
    for code, path in status_entries(root, prefix):
        if path in state["preexisting"]:
            continue
        if code == "??":
            untracked.add(path)
            continue
        if code[0] not in " ?!":
            staged.add(path)
        if code[1] not in " ?!":
            unstaged.add(path)
    if require_commit:
        if count == 0:
            fail("missing_commit", "no commit was made for the ticket")
        if staged or unstaged:
            fail("uncommitted_ticket_changes", f"tracked changes are not in the commit: {sorted(staged | unstaged)[:10]}")
    if no_change:
        if count:
            fail("unexpected_commit", f"{count} commit(s) exist, but the ticket was to change nothing")
        if staged or unstaged:
            fail("uncommitted_ticket_changes", f"tracked changes exist, but the ticket was to change nothing: "
                                               f"{sorted(staged | unstaged)[:10]}")
    passed = not violations
    if not passed:
        next_step = NEXT_FAIL
    elif no_change:
        next_step = NEXT_NO_CHANGE
    elif count == 1:
        next_step = NEXT_LEFT_OUT if staged or unstaged else NEXT_DONE
    else:
        next_step = NEXT_COMMIT if staged or unstaged else NEXT_NOTHING
    answer = {"result": "pass" if passed else "fail", "ticket": ticket, "base": base, "head": head,
              "commits_since_base": count, "commit_subject": subject, "commit_paths": capped(sorted(paths)),
              "staged": capped(sorted(staged)), "unstaged": capped(sorted(unstaged)),
              "new_untracked_files": capped(sorted(untracked)), "violations": capped(violations),
              "next": next_step}
    return answer, passed


def main(argv=None) -> int:
    ticket = "KEY"
    try:
        options = parse(sys.argv[1:] if argv is None else argv)
        ticket = ticket_key(options.ticket)
        root = workspace(options.root)
        if options.command == "begin":
            answer, status = command_begin(root, ticket), 0
        else:
            answer, passed = command_verify(root, ticket, options.require_commit, options.no_change)
            status = 0 if passed else 1
    except OSError as error:  # an unexpected file system failure is still answered as one JSON object
        return answer_refusal(bad_input("file_system_error", f"{type(error).__name__}: {error.strerror or error}"[:300]),
                              ticket)
    except Refusal as refusal:
        return answer_refusal(refusal, ticket)
    answer["next"] = answer["next"].replace("KEY", ticket)
    print(json.dumps(answer, ensure_ascii=True, sort_keys=True))
    return status


def answer_refusal(refusal: Refusal, ticket: str) -> int:
    next_step = NEXT_REFUSED.get(refusal.code, NEXT_FAIL if refusal.status == 1 else NEXT_INPUT)
    print(json.dumps({"result": "refused", "code": refusal.code, "detail": refusal.detail,
                      "next": next_step.replace("KEY", ticket)}, ensure_ascii=True, sort_keys=True))
    return refusal.status


if __name__ == "__main__":
    raise SystemExit(main())
