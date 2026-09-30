"""Regenerate every generated view that continuous integration compares with its committed copy, in dependency order.

Kind: development tool. Release train 2 of September 27, 2026 passed its local gates and failed in continuous
integration: status-pages.json had been regenerated before a later commit added a release record, so the committed
record no longer matched what its builder writes. A committed file that a builder writes goes stale whenever its
inputs change after the builder ran, and a check of the working tree cannot see that, because the working tree is not
what is pushed.

VIEWS below is the one list of generated files, taken from what the workflow in .github/workflows/ci.yml runs: the
tools tests compare the documentation pages, the starter catalogue release folder, the decision red team record, the
development tracker, the continuation status, the records index and the public status pages with their builders; the
self-test compares the packaged contract copies and the architecture diagrams; the conformance gates compare the
semantic dictionary and the architecture map. The conformance manifest is written by the conformance gate and is
regenerated last, because it reads everything else. Dated records are evidence, not views, and are never regenerated.

Every builder runs in its own process with the target tree first on the import path, so an exported commit is
regenerated with its own code. The order is checked before anything runs: a view may not read the output of a view
that runs after it. After the run, every fast view runs a second time; a second run that changes anything means a
builder's inputs changed after it ran, and the tool fails and names the view. A file that changed and that no view
declares is refused as an undeclared write.

Usage:

    python tools/regenerate_all.py                  # regenerate in this checkout and report what changed
    python tools/regenerate_all.py --check          # report what would change, put every output back, exit 1 if any
    python tools/regenerate_all.py --pristine       # export HEAD, regenerate the export, exit 1 if anything differs
    python tools/regenerate_all.py --list           # every view, its outputs and the check that compares it
    python tools/regenerate_all.py --only status-pages,records-index

Exit status: 0 nothing changed (or, without --check, the changes were written), 1 a view differs from its committed
copy in --check or --pristine, 2 a builder failed, the order is wrong, a second run changed a view or a builder wrote
a file no view declares. It needs no network and no credential and grants no authority.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import difflib
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
#: Where the pristine check exports a commit: under the home folder, never /tmp, whose writes can come back empty on
#: the development machine.
PRISTINE_HOME = Path.home() / ".le-ci-tmp" / "pristine"
#: Folders never walked when a whole tree is compared.
SKIPPED_PARTS = ("__pycache__", ".git", "node_modules")
#: The exit status of the conformance gate when a gate fails: the manifest is still written.
CONFORMANCE_GATE_FAILED = 1


@dataclass(frozen=True)
class View:
    """One generated view: what writes it, what it reads and which check of continuous integration compares it."""

    name: str
    outputs: tuple            # repository paths; a folder ends with "/"
    reads: tuple              # repository glob patterns the builder reads; used for the order check
    command: tuple            # argv run from the tree root; "{python}" is this interpreter, "{self}" this file
    ci_check: str             # the workflow step and the check that fails when the committed copy is stale
    slow: bool = False        # not repeated by the second-run check


def _python_view(name):
    """A view built by this file in the target tree's own process ("{self}" is the running copy of this file)."""
    return ("{python}", "{self}", "--build", name, "--root", ".")


VIEWS = (
    View("top-mcp-shortlist",
         ("src/loop_engine/core/service_runtime/web_assets/index.html",),
         ("src/loop_engine/core/service_runtime/web_assets/top-mcps.json", "tools/build_top_mcp_page.py"),
         ("{python}", "tools/build_top_mcp_page.py"),
         "tools tests: test_top_mcp_page, dated popularity cards match their source record"),
    View("worker-site-files",
         ("src/loop_engine/core/service_runtime/web_assets/worker-compose.yaml",),
         ("containers/worker/compose.yaml", "tools/build_worker_site_files.py"),
         ("{python}", "-m", "tools.build_worker_site_files"),
         "tools tests: worker download configuration matches the container profile"),
    View("asset-site-previews",
         ("src/loop_engine/core/service_runtime/web_assets/procedural-bear-preview.svg",
          "src/loop_engine/core/service_runtime/web_assets/procedural-tree-preview.svg"),
         ("tools/procedural_assets/*.py", "tools/build_asset_site_previews.py"),
         ("{python}", "-m", "tools.build_asset_site_previews"),
         "tools tests: test_procedural_assets, website previews match the original constructors"),
    View("packaged-contracts",
         ("src/loop_engine/data/architecture.yaml", "src/loop_engine/data/terminology.yaml"),
         ("architecture.yaml", "terminology.yaml"),
         _python_view("packaged-contracts"),
         "self-test: architecture_contract installed_contract_projections_are_fresh"),
    View("semantic-dictionary",
         ("src/loop_engine/data/semantic_data_dictionary.yaml", "docs/architecture/SEMANTIC-IDENTITY-DICTIONARY.md"),
         ("terminology.yaml", "src/loop_engine/forbidden_paths.json", "src/loop_engine/semantic_conformance.py"),
         _python_view("semantic-dictionary"),
         "conformance gates: semantic_identity (semantic_projection, data_dictionary_freshness)"),
    View("architecture-map",
         ("src/loop_engine/ARCHITECTURE-MAP.md",),
         ("src/loop_engine/architecture_map.py",),
         _python_view("architecture-map"),
         "conformance gates: architecture_map_freshness"),
    View("architecture-diagrams",
         ("docs/ARCHITECTURE-DIAGRAMS.md",),
         ("src/loop_engine/code_nodes/architecture_diagram*.py",),
         _python_view("architecture-diagrams"),
         "self-test: architecture_diagram, the committed page matches the typed model"),
    View("documentation-index",
         ("src/loop_engine/core/service_runtime/web_assets/docs/",
          "src/loop_engine/core/service_runtime/documentation_pages.json"),
         ("docs/guides/*", "src/loop_engine/core/service_runtime/web_assets/documentation-index.json",
          "tools/build_documentation_index.py"),
         ("{python}", "tools/build_documentation_index.py", "--repository", "."),
         "tools tests: test_service_documentation, test_documentation_index"),
    View("host-catalogue-release",
         ("examples/29_intelligence_service/starter-catalogue/host-release/",),
         ("examples/29_intelligence_service/starter-catalogue/items.json",
          "examples/29_intelligence_service/starter-catalogue/reviews.json",
          "examples/29_intelligence_service/starter-catalogue/bodies/*", "tools/build_host_catalogue_manifest.py"),
         ("{python}", "tools/build_host_catalogue_manifest.py",
          "--catalogue", "examples/29_intelligence_service/starter-catalogue",
          "--output", "examples/29_intelligence_service/starter-catalogue/host-release",
          "--artifact-root", "/opt/baltor/catalogue", "--accept-license", "MIT",
          "--grant", "pilot-owner:bodies:required", "--write"),
         "tools tests: test_build_host_catalogue_manifest, the committed release folder matches the review record"),
    View("red-team-record",
         ("src/loop_engine/core/service_runtime/web_assets/case-studies/decision-red-team.json",),
         ("artifacts/decision-red-team-2026-09-25/run-*.json", "case-studies/decision-red-team-*/*",
          "tools/build_showcase_page.py"),
         ("{python}", "tools/build_showcase_page.py",
          "--run", "artifacts/decision-red-team-2026-09-25/run-2.json",
          "--run", "artifacts/decision-red-team-2026-09-25/run-3.json"),
         "tools tests: test_red_team_page, the packaged record is what the generator writes"),
    View("development-tracker",
         ("docs/roadmap/DEVELOPMENT-TRACKER.md", "docs/roadmap/development-tracker.json"),
         ("docs/roadmap/roadmap.yaml", "tools/build_development_tracker.py"),
         ("{python}", "tools/build_development_tracker.py"),
         "tools tests: test_build_development_tracker"),
    View("continuation-status",
         ("docs/roadmap/CONTINUATION-STATUS.md",),
         ("docs/roadmap/roadmap.yaml", "tools/build_continuation_status.py"),
         ("{python}", "tools/build_continuation_status.py", "--output", "docs/roadmap/CONTINUATION-STATUS.md"),
         "tools tests: test_build_continuation_status"),
    View("records-index",
         ("docs/RECORDS-INDEX.md",),
         ("docs/*",),
         ("{python}", "tools/build_records_index.py", "--output", "docs/RECORDS-INDEX.md"),
         "tools tests: test_build_records_index, the committed index is current"),
    View("demonstration-steps",
         ("src/loop_engine/core/service_runtime/web_assets/index.html",),
         ("examples/29_intelligence_service/starter-catalogue/host-release/manifest.json",
          "tools/record_demonstration_steps.py",
          "tools/test_homepage_demonstration.py"),
         ("{python}", "tools/record_demonstration_steps.py", "--write"),
         "tools tests: test_homepage_demonstration and test_showcase_pages, the recorded "
         "demonstrations match this release's library"),
    View("status-pages",
         ("src/loop_engine/core/service_runtime/web_assets/status-pages/status-pages.json",),
         ("artifacts/architecture-audit-2026-09-19/pilot-release-*.json", "artifacts/community-release-*/README.md",
          "CHANGELOG.md", "docs/roadmap/roadmap.yaml", "docs/roadmap/public-status-exclusions.json",
          "tools/public_wording_rules.mjs", "tools/build_public_status_pages.py",
          "src/loop_engine/core/service_runtime/web_site_map.json",
          "src/loop_engine/core/service_runtime/web_layout_standard.json",
          "src/loop_engine/core/service_runtime/web_assets/client-recipes.json",
          "src/loop_engine/core/service_runtime/http.py"),
         ("{python}", "tools/build_public_status_pages.py"),
          "tools tests: test_build_public_status_pages, the committed record is current"),
    View("conformance-manifest",
         ("src/loop_engine/architecture_conformance.json",),
         ("*",),
         ("{python}", "-m", "loop_engine", "--conformance"),
         "conformance gates: python -m loop_engine --conformance writes it; continuous integration does not "
         "compare it",
         slow=True),
)
VIEW_NAMES = tuple(view.name for view in VIEWS)


class RegenerationError(RuntimeError):
    """A builder failed, the order is wrong or a view does not reach a fixed point."""


# The builders of the views that have no command of their own. Each runs in the target tree's own process.

def _write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def _build_packaged_contracts(root: Path) -> None:
    for name in ("architecture.yaml", "terminology.yaml"):
        source, target = root / name, root / "src" / "loop_engine" / "data" / name
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            target.write_bytes(source.read_bytes())


def _build_semantic_dictionary(root: Path) -> None:
    import yaml
    from loop_engine import semantic_conformance as semantic
    projection = root / "src" / "loop_engine" / "data" / "semantic_data_dictionary.yaml"
    if semantic.semantic_projection_violations():
        # The same projection semantic_projection_violations compares; written only when the parsed file differs, so
        # a committed file that is equal in content keeps its bytes.
        source = semantic.load_semantic_dictionary(root / "terminology.yaml")
        comparable = {"schema_version": "semantic_data_dictionary_projection/v1", "generated_from": "terminology.yaml",
                      "dictionary_version": source["dictionary_version"], "categories": source["categories"],
                      "decision_rules": source["decision_rules"], "entries": source["entries"]}
        digest = hashlib.sha256(json.dumps(comparable, sort_keys=True, separators=(",", ":"),
                                           ensure_ascii=False).encode("utf-8")).hexdigest()
        projection.write_text(yaml.safe_dump({**comparable, "source_digest": digest}, sort_keys=False,
                                             allow_unicode=True), encoding="utf-8")
        if semantic.semantic_projection_violations():
            raise RegenerationError("the semantic projection still differs from terminology.yaml after writing it")
    _write_if_changed(root / "docs" / "architecture" / "SEMANTIC-IDENTITY-DICTIONARY.md",
                      semantic.render_data_dictionary())


def _build_architecture_map(root: Path) -> None:
    from loop_engine.architecture_map import render_map
    # `python -m loop_engine --map` prints the map; the committed file is that output, final newline included.
    _write_if_changed(root / "src" / "loop_engine" / "ARCHITECTURE-MAP.md", render_map() + "\n")


def _build_architecture_diagrams(root: Path) -> None:
    from loop_engine.code_nodes.architecture_diagram import DOCUMENT_PATH, render_document
    _write_if_changed(root / DOCUMENT_PATH, render_document())


INTERNAL_BUILDERS = {"packaged-contracts": _build_packaged_contracts, "semantic-dictionary": _build_semantic_dictionary,
                     "architecture-map": _build_architecture_map, "architecture-diagrams": _build_architecture_diagrams}


# Snapshots of outputs and trees.

def _digest_file(path: Path) -> str:
    if path.is_symlink():
        return "link:" + os.readlink(path)
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _files_under(root: Path, relative: str) -> list:
    """The repository paths of the files an output names: the file, or every file under the folder."""
    target = root / relative
    if relative.endswith("/"):
        if not target.is_dir():
            return []
        found = []
        for folder, folders, files in os.walk(target):
            folders[:] = [name for name in folders if name not in SKIPPED_PARTS]
            found += [Path(folder, name).relative_to(root).as_posix() for name in files]
        return sorted(found)
    return [relative] if target.is_file() or target.is_symlink() else []


def snapshot(root: Path, outputs) -> dict:
    """{repository path: digest} of every file the outputs name."""
    return {path: _digest_file(root / path) for relative in outputs for path in _files_under(root, relative)}


def tree_digests(root: Path) -> dict:
    """{repository path: digest} of every file of a tree, the skipped folders left out."""
    found = {}
    for folder, folders, files in os.walk(root):
        folders[:] = [name for name in folders if name not in SKIPPED_PARTS]
        for name in files:
            path = Path(folder, name)
            found[path.relative_to(root).as_posix()] = _digest_file(path)
    return found


def differences(before: dict, after: dict) -> list:
    """Sorted (path, change) pairs between two snapshots; change is added, removed or changed."""
    rows = [(path, "removed") for path in before if path not in after]
    rows += [(path, "added") for path in after if path not in before]
    rows += [(path, "changed") for path in before if path in after and before[path] != after[path]]
    return sorted(rows)


# Order, selection and running.

def _matches(pattern: str, output: str) -> bool:
    """Whether a read pattern covers an output path or folder."""
    if output.endswith("/"):
        return fnmatch.fnmatch(output, pattern) or fnmatch.fnmatch(output + "x", pattern) or pattern.startswith(output)
    return fnmatch.fnmatch(output, pattern)


def order_problems(views=VIEWS) -> list:
    """A view that reads the output of a view that runs after it would be built from inputs that are about to change."""
    problems = []
    for index, view in enumerate(views):
        for later in views[index + 1:]:
            for output in later.outputs:
                if any(_matches(pattern, output) for pattern in view.reads):
                    problems.append(f"{view.name} reads {output}, which {later.name} writes after it")
    names = [view.name for view in views]
    problems += [f"two views are named {name}" for name in sorted({name for name in names if names.count(name) > 1})]
    return problems


def select(only=(), skip=(), views=VIEWS) -> tuple:
    known = {view.name for view in views}
    unknown = sorted((set(only) | set(skip)) - known)
    if unknown:
        names = ", ".join(view.name for view in views)
        raise RegenerationError(f"no view is named {', '.join(unknown)}; the views are {names}")
    return tuple(view for view in views if (not only or view.name in only) and view.name not in skip)


def _environment(root: Path) -> dict:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join([str(root / "src"), str(root / "tools")]
                                                + [part for part in [environment.get("PYTHONPATH", "")] if part])
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def run_view(view: View, root: Path) -> dict:
    """Run one builder from the tree root and return what it changed; a failing builder raises."""
    placeholders = {"{python}": sys.executable, "{self}": str(Path(__file__).resolve())}
    argv = [placeholders.get(part, part) for part in view.command]
    before = snapshot(root, view.outputs)
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=root, env=_environment(root), capture_output=True, text=True, check=False)
    seconds = round(time.monotonic() - started, 1)
    note = ""
    if completed.returncode != 0:
        if view.name == "conformance-manifest" and completed.returncode == CONFORMANCE_GATE_FAILED:
            note = "the conformance gates failed; the manifest was still written"
        else:
            tail = "\n".join((completed.stdout + completed.stderr).strip().splitlines()[-12:])
            raise RegenerationError(f"{view.name}: {' '.join(view.command)} exited {completed.returncode}\n{tail}")
    return {"view": view.name, "seconds": seconds, "changed": differences(before, snapshot(root, view.outputs)),
            "note": note}


def git_changes(root: Path):
    """{path: digest} of every file git reports as changed or untracked in a checkout, or None outside one."""
    completed = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True, check=False)
    if completed.returncode != 0 or Path(completed.stdout.strip()).resolve() != root:
        return None
    completed = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "-z", "--untracked-files=all"],
                               capture_output=True, check=False)
    entries, paths = completed.stdout.split(b"\0"), []
    index = 0
    while index < len(entries):
        entry = entries[index].decode("utf-8", "surrogateescape")
        index += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            index += 1  # a rename names its old path in the next field
    return {path: (_digest_file(root / path) if (root / path).is_file() else "absent") for path in paths}


def _declared(path: str, views) -> bool:
    return any(path == output or (output.endswith("/") and path.startswith(output))
               for view in views for output in view.outputs)


def regenerate(root: Path = ROOT, *, views=VIEWS, registry=VIEWS, verify: bool = True, check: bool = False,
               git_check: bool = True, log=print) -> dict:
    """Run the views in order and report what changed; with check, put every output back afterwards."""
    root = Path(root).resolve()
    problems = order_problems(registry)
    if problems:
        raise RegenerationError("the view order is wrong:\n  " + "\n  ".join(problems))
    outputs = [output for view in views for output in view.outputs]
    saved = {path: (root / path).read_bytes()
             for relative in outputs for path in _files_under(root, relative)} if check else {}
    git_before = git_changes(root) if git_check else None
    results = []
    try:
        for view in views:
            result = run_view(view, root)
            results.append(result)
            state = f"{len(result['changed'])} files changed" if result["changed"] else "unchanged"
            log(f"  {view.name:24} {state:18} {result['seconds']:6.1f}s  {result['note']}".rstrip())
        second = []
        if verify:
            for view in views:
                if view.slow:
                    continue
                again = run_view(view, root)
                if again["changed"]:
                    second.append((view.name, again["changed"]))
        if second:
            lines = [f"{name}: a second run changed {', '.join(path for path, _change in changed[:5])}"
                     for name, changed in second]
            raise RegenerationError("a builder's inputs changed after it ran:\n  " + "\n  ".join(lines))
        if git_before is not None:
            git_after = git_changes(root) or {}
            undeclared = sorted(path for path, digest in git_after.items()
                                if git_before.get(path) != digest and not _declared(path, views))
            if undeclared:
                raise RegenerationError("a builder wrote files no view declares: " + ", ".join(undeclared[:10]))
    finally:
        if check:
            for relative in outputs:
                for path in _files_under(root, relative):
                    if path not in saved:
                        (root / path).unlink()
            for path, payload in saved.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.is_file() or target.read_bytes() != payload:
                    target.write_bytes(payload)
    changed = [(result["view"], path, change) for result in results for path, change in result["changed"]]
    return {"views": [result["view"] for result in results], "changed": changed, "results": results}


# The pristine check: the exact committed tree, never the working tree.

def export_commit(root: Path, revision: str, target: Path) -> None:
    """Write the files of one commit into an empty folder with git archive."""
    target.mkdir(parents=True)
    archive = subprocess.Popen(["git", "-C", str(root), "archive", "--format=tar", revision], stdout=subprocess.PIPE)
    unpack = subprocess.run(["tar", "-x", "-C", str(target)], stdin=archive.stdout, capture_output=True, check=False)
    archive.stdout.close()
    if archive.wait() != 0 or unpack.returncode != 0:
        raise RegenerationError(f"git archive of {revision} could not be unpacked: {unpack.stderr.decode()[-300:]}")


def _text_diff(before_tree: dict, tree: Path, path: str, committed: bytes) -> str:
    try:
        old, new = committed.decode("utf-8").splitlines(), (tree / path).read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, FileNotFoundError):
        return f"  {path}: binary or removed"
    lines = list(difflib.unified_diff(old, new, f"committed/{path}", f"regenerated/{path}", lineterm="", n=1))
    return "\n".join(lines[:40]) + ("\n  (diff shortened)" if len(lines) > 40 else "")


def pristine_check(root: Path = ROOT, *, revision: str = "HEAD", only=(), skip=(), keep: bool = False,
                   work_home: Path = PRISTINE_HOME, log=print) -> int:
    """Export a commit, regenerate every view there with the commit's own tools and compare the tree with the commit."""
    root = Path(root).resolve()
    resolved = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", f"{revision}^{{commit}}"],
                              capture_output=True, text=True, check=False).stdout.strip()
    if not resolved:
        raise RegenerationError(f"{revision} is not a commit of {root}")
    work = Path(work_home) / f"{resolved[:12]}-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    tree = work / "tree"
    export_commit(root, resolved, tree)
    try:
        committed = tree_digests(tree)
        tool = tree / "tools" / "regenerate_all.py"
        argv = [sys.executable, str(tool if tool.is_file() else Path(__file__)), "--root", str(tree), "--no-git"]
        argv += ["--only", ",".join(only)] if only else []
        argv += ["--skip", ",".join(skip)] if skip else []
        completed = subprocess.run(argv, cwd=tree, env=_environment(tree), capture_output=True, text=True, check=False)
        log(completed.stdout.rstrip())
        if completed.returncode not in (0,):
            log(completed.stderr.rstrip())
            log(f"pristine check of {resolved[:12]}: regeneration failed (exit {completed.returncode})")
            return 2
        after = tree_digests(tree)
        rows = differences(committed, after)
        if not rows:
            log(f"pristine check of {resolved[:12]}: the committed tree regenerates to itself")
            return 0
        report = [f"pristine check of {resolved[:12]}: {len(rows)} files differ from the commit after regeneration"]
        for path, change in rows:
            report.append(f"  {change:8} {path}")
        for path, change in rows[:6]:
            if change == "changed":
                blob = subprocess.run(["git", "-C", str(root), "show", f"{resolved}:{path}"],
                                      capture_output=True, check=False).stdout
                report.append(_text_diff(committed, tree, path, blob))
        report.append("regenerate with python tools/regenerate_all.py and commit the result")
        work.mkdir(parents=True, exist_ok=True)
        (work / "differences.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        log("\n".join(report))
        log(f"report kept at {work / 'differences.txt'}")
        return 1
    finally:
        if not keep:
            shutil.rmtree(tree, ignore_errors=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="the tree to regenerate (default: this checkout)")
    parser.add_argument("--check", action="store_true", help="report what would change and put every output back")
    parser.add_argument("--pristine", action="store_true", help="regenerate an export of HEAD and compare it")
    parser.add_argument("--revision", default="HEAD", help="the commit the pristine check exports")
    parser.add_argument("--keep", action="store_true", help="keep the pristine export for inspection")
    parser.add_argument("--only", default="", help="comma-separated view names to run, in registry order")
    parser.add_argument("--skip", default="", help="comma-separated view names to leave out")
    parser.add_argument("--no-verify", action="store_true", help="leave out the second run of the fast views")
    parser.add_argument("--no-git", action="store_true", help="leave out the undeclared-write check (no checkout)")
    parser.add_argument("--list", action="store_true", help="print the views and exit")
    parser.add_argument("--outputs", action="store_true",
                        help="print every generated path, one a line, a folder ending in /, and exit")
    parser.add_argument("--build", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    only = tuple(name for name in arguments.only.split(",") if name)
    skip = tuple(name for name in arguments.skip.split(",") if name)
    try:
        if arguments.build:
            INTERNAL_BUILDERS[arguments.build](arguments.root.resolve())
            return 0
        if arguments.outputs:
            # For tools/release_train.py, which takes the train's side of a conflict in any of these paths and
            # regenerates it, instead of asking a person to merge two generated copies.
            print("\n".join(output for view in VIEWS for output in view.outputs))
            return 0
        if arguments.list:
            for view in VIEWS:
                print(f"{view.name:24} {', '.join(view.outputs)}")
                print(f"{'':24} compared by {view.ci_check}")
            return 0
        if arguments.pristine:
            return pristine_check(arguments.root, revision=arguments.revision, only=only, skip=skip,
                                  keep=arguments.keep)
        views = select(only, skip)
        print(f"regenerating {len(views)} views in {arguments.root.resolve()}")
        result = regenerate(arguments.root, views=views, verify=not arguments.no_verify, check=arguments.check,
                            git_check=not arguments.no_git, log=print)
    except RegenerationError as error:
        print(f"REGENERATION FAILED: {error}", file=sys.stderr)
        return 2
    for view, path, change in result["changed"]:
        print(f"  {change:8} {path}  ({view})")
    if not result["changed"]:
        print("no generated view changed")
        return 0
    if arguments.check:
        print(f"{len(result['changed'])} generated files differ from their committed copies; every output was put back")
        return 1
    print(f"{len(result['changed'])} generated files were written; commit them as one generated-views commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
