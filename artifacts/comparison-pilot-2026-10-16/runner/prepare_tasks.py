"""Build the three frozen pilot task workspaces and their hidden acceptance material.

No model call and no network access: the inputs are local clones of the two
upstream repositories and the Spaceship Titanic training file that the Kaggle
command line downloaded. Every output is written under one new folder:

    OUT/templates/<task>/project   the starting project the harness receives (a fresh Git repository)
    OUT/hidden/<task>/              acceptance material the harness never sees (never mounted in the sandbox)
    OUT/task-manifest.json          the SHA-256 digest of every template and hidden file

Usage:
    python3 prepare_tasks.py --cachetools-repo DIR --dotenv-repo DIR --spaceship-train FILE \
        --python-env DIR --out NEW_DIR
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent / "design"

CACHETOOLS_TAG, CACHETOOLS_COMMIT = "v7.2.2", "be0b2eba99f676fbd525a8bc83a4dd62611c6821"
DOTENV_TAG, DOTENV_COMMIT = "v1.2.4", "a565c2cc41599c48eabc6b7b7f5b826d43c5a6d7"
# The upstream fix whose library half is withheld in the debugging task: theskumar/python-dotenv#680.
DOTENV_FIX_COMMIT = "f7b18d9c72d1abcc2ad4023424b84f5bee30d266"
SPACESHIP_TRAIN_SHA256 = "17336d553f49ebdf6ecb266d2b5d3746e5dd308445f7c7864141c4f28d2a88d0"
SPLIT_SEED = 20261016
GIT_IDENTITY = {"GIT_AUTHOR_NAME": "Pilot", "GIT_AUTHOR_EMAIL": "pilot@example.invalid",
                "GIT_COMMITTER_NAME": "Pilot", "GIT_COMMITTER_EMAIL": "pilot@example.invalid",
                "GIT_AUTHOR_DATE": "2026-10-16T12:00:00Z", "GIT_COMMITTER_DATE": "2026-10-16T12:00:00Z"}


def run(argv, cwd=None, env=None, capture=False):
    merged = dict(os.environ, **(env or {}))
    result = subprocess.run(argv, cwd=cwd, env=merged, check=True,
                            stdout=subprocess.PIPE if capture else None, text=True if capture else None)
    return result.stdout if capture else None


def export_tree(repo, tag, commit, target):
    resolved = run(["git", "-C", str(repo), "rev-parse", tag + "^{commit}"], capture=True).strip()
    if resolved != commit:
        raise SystemExit(f"{repo}: {tag} resolves to {resolved}, expected {commit}")
    target.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit], check=True,
                             stdout=subprocess.PIPE).stdout
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive, check=True)


def fresh_git(project):
    """One commit of the starting state and no upstream history, so `git log -p` reveals nothing held out."""
    run(["git", "init", "-q", "-b", "main"], cwd=project)
    run(["git", "add", "-A"], cwd=project)
    run(["git", "commit", "-q", "-m", "Starting point"], cwd=project, env=GIT_IDENTITY)


def remove_class(source, name):
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == name)
    lines = source.splitlines(keepends=True)
    start, end = node.lineno - 1, node.end_lineno
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return "".join(lines[:start] + lines[end:]), "".join(lines[start:node.end_lineno])


def write_task_file(project, task_id):
    text = (DESIGN / "tasks" / task_id / "prompt.txt").read_text(encoding="utf-8")
    (project / "TASK.md").write_text("# Task\n\n" + text, encoding="utf-8")


def prepare_tlru(repo, out):
    task = "a-cachetools-tlru"
    upstream = out / "upstream" / task
    export_tree(repo, CACHETOOLS_TAG, CACHETOOLS_COMMIT, upstream)
    project = out / "templates" / task / "project"
    shutil.copytree(upstream, project)
    init = project / "src" / "cachetools" / "__init__.py"
    source, removed = remove_class(init.read_text(encoding="utf-8"), "TLRUCache")
    if '    "TLRUCache",\n' not in source:
        raise SystemExit("TLRUCache export line not found")
    init.write_text(source.replace('    "TLRUCache",\n', "", 1), encoding="utf-8")
    (project / "tests" / "test_tlru.py").unlink()
    write_task_file(project, task)
    fresh_git(project)
    hidden = out / "hidden" / task
    shutil.copytree(upstream / "tests", hidden / "tests")
    (hidden / "reference").mkdir()
    shutil.copy2(upstream / "src" / "cachetools" / "__init__.py", hidden / "reference" / "__init__.py")
    (hidden / "removed_class.py.txt").write_text(removed, encoding="utf-8")
    return task


def fix_hunk(repo, path):
    patch = run(["git", "-C", str(repo), "show", "--format=", DOTENV_FIX_COMMIT, "--", path], capture=True)
    if not patch.strip():
        raise SystemExit(f"no hunk for {path}")
    return patch


def prepare_dotenv(repo, out):
    task = "b-dotenv-backslash"
    upstream = out / "upstream" / task
    export_tree(repo, DOTENV_TAG, DOTENV_COMMIT, upstream)
    project = out / "templates" / task / "project"
    shutil.copytree(upstream, project)
    # Withhold the parser half of the upstream fix and its parser tests; keep its set_key half and set_key tests.
    for path in ("src/dotenv/parser.py", "tests/test_parser.py"):
        patch_file = out / f"withheld-{Path(path).name}.patch"
        patch_file.write_text(fix_hunk(repo, path), encoding="utf-8")
        run(["git", "apply", "-R", "--whitespace=nowarn", str(patch_file)], cwd=project)
    changelog = project / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    full = ("- `set_key` now escapes backslashes, so values containing them (Windows paths, regular expressions) "
            "survive a write/read round-trip. Quoted values ending in an escaped backslash are no longer mis-parsed "
            "as an escaped quote, which used to swallow the following lines by [@dchaudhari7177] in [#680]")
    short = ("- `set_key` now escapes backslashes, so values containing them (Windows paths, regular expressions) "
             "survive a write/read round-trip by [@dchaudhari7177] in [#680]")
    if full not in text:
        raise SystemExit("changelog entry not found")
    changelog.write_text(text.replace(full, short, 1), encoding="utf-8")
    write_task_file(project, task)
    fresh_git(project)
    hidden = out / "hidden" / task
    shutil.copytree(upstream / "tests", hidden / "tests")
    (hidden / "reference").mkdir()
    shutil.copy2(upstream / "src" / "dotenv" / "parser.py", hidden / "reference" / "parser.py")
    shutil.copytree(project / "src", hidden / "seeded-src")
    return task


def prepare_spaceship(train_file, python_env, out):
    task = "c-spaceship-titanic"
    digest = hashlib.sha256(train_file.read_bytes()).hexdigest()
    if digest != SPACESHIP_TRAIN_SHA256:
        raise SystemExit(f"train.csv digest {digest} differs from the frozen digest")
    project = out / "templates" / task / "project"
    data = project / "data"
    data.mkdir(parents=True)
    hidden = out / "hidden" / task
    hidden.mkdir(parents=True)
    run([str(python_env / "bin" / "python"), "-I", str(HERE / "split_spaceship.py"), str(train_file), str(data),
         str(hidden), str(SPLIT_SEED)], env={"OMP_NUM_THREADS": "2"})
    write_task_file(project, task)
    fresh_git(project)
    return task


def digests(root):
    rows = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            rows[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cachetools-repo", type=Path, required=True)
    parser.add_argument("--dotenv-repo", type=Path, required=True)
    parser.add_argument("--spaceship-train", type=Path, required=True)
    parser.add_argument("--python-env", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit("use a new output folder")
    out.mkdir(parents=True)
    tasks = [prepare_tlru(args.cachetools_repo, out), prepare_dotenv(args.dotenv_repo, out),
             prepare_spaceship(args.spaceship_train, args.python_env, out)]
    manifest = {"record_type": "comparison_pilot_task_manifest/v1",
                "inputs": {"cachetools": {"tag": CACHETOOLS_TAG, "commit": CACHETOOLS_COMMIT},
                           "python_dotenv": {"tag": DOTENV_TAG, "commit": DOTENV_COMMIT,
                                             "withheld_fix_commit": DOTENV_FIX_COMMIT},
                           "spaceship_titanic_train_sha256": SPACESHIP_TRAIN_SHA256, "split_seed": SPLIT_SEED},
                "tasks": {}}
    for task in tasks:
        manifest["tasks"][task] = {
            "template_head": run(["git", "-C", str(out / "templates" / task / "project"), "rev-parse", "HEAD"],
                                 capture=True).strip(),
            "template_files": digests(out / "templates" / task / "project"),
            "hidden_files": digests(out / "hidden" / task)}
    (out / "task-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({task: {"template_files": len(row["template_files"]), "hidden_files": len(row["hidden_files"]),
                             "template_head": row["template_head"]} for task, row in manifest["tasks"].items()},
                     indent=1))


if __name__ == "__main__":
    sys.exit(main())
