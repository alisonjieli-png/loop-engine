"""Independent scorers for the three pilot tasks.

A scorer reads only the final project folder the harness left behind and the
hidden acceptance material. It never reads the transcript or the harness's
claim of success. Any code that came from the harness (its source, its tests,
its solution script) runs inside a Bubblewrap sandbox without network access.
The thresholds and rules here are frozen in design/design.json before the
first counted model call.
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

SPACESHIP_ACCURACY_FLOOR = 0.790
DOTENV_MAX_CHANGED_SOURCE_LINES = 12
DOTENV_ALLOWED_SOURCE_FILES = frozenset({"dotenv/parser.py"})
TLRU_HIDDEN_TEST_FILE = "tests/test_tlru.py"
TLRU_HIDDEN_TEST_COUNT = 34
DOTENV_HIDDEN_TEST_FILE = "tests/test_parser.py"
SCORE_ROOT = "/score"
IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".opencode"}


def sandboxed(python_env, extra_bin, score_dir, command, timeout, env_extra=None):
    """Run a command over a scoring folder with no network and nothing else of the workstation mounted."""
    env = {"HOME": SCORE_ROOT, "PATH": f"{extra_bin}:{python_env}/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
           "LC_ALL": "C.UTF-8", "TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "2",
           "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"}
    env.update(env_extra or {})
    argv = ["bwrap", "--die-with-parent", "--new-session", "--unshare-all", "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/etc", "/etc", "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--symlink", "usr/sbin", "/sbin", "--proc", "/proc",
            "--dev", "/dev", "--tmpfs", "/tmp", "--ro-bind", str(python_env), str(python_env),
            "--ro-bind", str(extra_bin), str(extra_bin), "--bind", str(score_dir), SCORE_ROOT,
            "--chdir", SCORE_ROOT, "--"] + list(command)
    try:
        completed = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                   timeout=timeout)
        return completed.returncode, completed.stdout[-20000:], completed.stderr[-20000:]
    except subprocess.TimeoutExpired:
        return "timeout", "", ""


def parse_junit(path):
    if not Path(path).is_file():
        return None
    root = ElementTree.parse(path).getroot()
    cases = []
    for case in root.iter("testcase"):
        outcome = "passed"
        for child in case:
            if child.tag in ("failure", "error"):
                outcome = child.tag
            elif child.tag == "skipped":
                outcome = "skipped"
        cases.append({"file": case.get("file") or case.get("classname", "").replace(".", "/"),
                      "classname": case.get("classname"), "name": case.get("name"), "outcome": outcome})
    return cases


def pytest_counts(cases, prefix=None):
    rows = [case for case in cases if prefix is None or case["classname"].startswith(prefix)]
    counts = {"passed": 0, "failure": 0, "error": 0, "skipped": 0}
    for case in rows:
        counts[case["outcome"]] += 1
    counts["total"] = len(rows)
    return counts


def run_pytest(python_env, extra_bin, score_dir, targets, timeout=600, pythonpath=SCORE_ROOT + "/src"):
    report = Path(score_dir) / ".score-junit.xml"
    if report.exists():
        report.unlink()
    status, out, err = sandboxed(python_env, extra_bin, score_dir,
                                 ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                  "--junitxml=" + SCORE_ROOT + "/.score-junit.xml", *targets],
                                 timeout, env_extra={"PYTHONPATH": pythonpath})
    cases = parse_junit(report)
    return {"exit_status": status, "cases": cases, "tail": out[-3000:]}


def tree_files(root, below=None):
    root = Path(root)
    base = root / below if below else root
    result = {}
    if not base.exists():
        return result
    for path in sorted(base.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not (set(relative.parts) & IGNORED_PARTS) and not path.name.endswith(".pyc"):
            result[str(relative)] = path.read_bytes()
    return result


def changed_files(before_root, after_root, below=None):
    before, after = tree_files(before_root, below), tree_files(after_root, below)
    changes = {}
    for name in sorted(set(before) | set(after)):
        if before.get(name) != after.get(name):
            old = before.get(name, b"").decode("utf-8", "replace").splitlines()
            new = after.get(name, b"").decode("utf-8", "replace").splitlines()
            diff = list(difflib.unified_diff(old, new, lineterm="", n=0))
            added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
            removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
            state = "added" if name not in before else "deleted" if name not in after else "modified"
            changes[name] = {"state": state, "lines_added": added, "lines_removed": removed}
    return changes


def unified_patch(before_root, after_root, below=None, limit=60000):
    before, after = tree_files(before_root, below), tree_files(after_root, below)
    chunks = []
    for name in sorted(set(before) | set(after)):
        if before.get(name) != after.get(name):
            old = before.get(name, b"").decode("utf-8", "replace").splitlines(keepends=True)
            new = after.get(name, b"").decode("utf-8", "replace").splitlines(keepends=True)
            chunks.append("".join(difflib.unified_diff(old, new, "a/" + name, "b/" + name)))
    text = "".join(chunks)
    return text if len(text) <= limit else text[:limit] + "\n[patch truncated by the scorer]\n"


def overlay(upstream_root, project, target, parts):
    shutil.copytree(upstream_root, target)
    for part in parts:
        destination = target / part
        if destination.exists():
            shutil.rmtree(destination)
        if (project / part).exists():
            shutil.copytree(project / part, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


# -- task a ------------------------------------------------------------------

def score_tlru(project, hidden, upstream, python_env, extra_bin):
    project, hidden, upstream = Path(project), Path(hidden), Path(upstream)
    with tempfile.TemporaryDirectory(prefix="score-a-") as folder:
        tree = Path(folder) / "tree"
        overlay(upstream, project, tree, ["src"])
        result = run_pytest(python_env, extra_bin, tree, ["tests"])
    cases = result["cases"]
    if cases is None:
        return {"passed": False, "reason": "test_run_produced_no_report", "exit_status": result["exit_status"],
                "tail": result["tail"]}
    hidden_cases = [case for case in cases if case["classname"].startswith("tests.test_tlru")]
    hidden_counts = pytest_counts(hidden_cases)
    suite = pytest_counts(cases)
    passed = (suite["failure"] == 0 and suite["error"] == 0 and hidden_counts["passed"] == TLRU_HIDDEN_TEST_COUNT)
    return {"passed": passed, "suite": suite, "hidden_tlru": hidden_counts,
            "hidden_tlru_pass_fraction": round(hidden_counts["passed"] / TLRU_HIDDEN_TEST_COUNT, 4),
            "exit_status": result["exit_status"],
            "failing_tests": [case["classname"] + "::" + case["name"] for case in cases
                              if case["outcome"] in ("failure", "error")][:60]}


# -- task b ------------------------------------------------------------------

ROOT_CAUSE_FILE = re.compile(r"parser\.py")
ROOT_CAUSE_PATTERN = re.compile(r"_single_quoted_value|single[- ]quoted[^.\n]{0,80}(regex|regular expression|pattern)|"
                                r"(regex|regular expression|pattern)[^.\n]{0,80}single[- ]quoted", re.IGNORECASE)


def score_dotenv(project, hidden, upstream, template, python_env, extra_bin):
    project, hidden, upstream, template = Path(project), Path(hidden), Path(upstream), Path(template)
    outcome = {}
    with tempfile.TemporaryDirectory(prefix="score-b-") as folder:
        tree = Path(folder) / "upstream-tests"
        overlay(upstream, project, tree, ["src"])
        result = run_pytest(python_env, extra_bin, tree, ["tests"])
        cases = result["cases"] or []
        outcome["hidden_suite"] = pytest_counts(cases)
        outcome["hidden_parser_tests"] = pytest_counts([case for case in cases
                                                        if case["classname"].startswith("tests.test_parser")])
        outcome["hidden_suite_failing"] = [case["classname"] + "::" + case["name"] for case in cases
                                           if case["outcome"] in ("failure", "error")][:60]
        outcome["hidden_suite_ok"] = bool(cases) and outcome["hidden_suite"]["failure"] == 0 \
            and outcome["hidden_suite"]["error"] == 0
        source_changes = changed_files(template, project, "src")
        outcome["source_changes"] = source_changes
        changed_names = {name[len("src/"):] for name in source_changes}
        changed_lines = sum(row["lines_added"] + row["lines_removed"] for row in source_changes.values())
        outcome["source_changed_lines"] = changed_lines
        outcome["scope_ok"] = bool(changed_names) and changed_names <= DOTENV_ALLOWED_SOURCE_FILES \
            and changed_lines <= DOTENV_MAX_CHANGED_SOURCE_LINES
        test_changes = changed_files(template, project, "tests")
        regression_files = sorted(name for name, row in test_changes.items()
                                  if row["state"] != "deleted" and name.endswith(".py"))
        outcome["test_changes"] = test_changes
        outcome["regression_files"] = regression_files
        regression = {"before_fix": None, "after_fix": None}
        if regression_files:
            seeded = Path(folder) / "seeded"
            shutil.copytree(template, seeded, ignore=shutil.ignore_patterns(".git"))
            shutil.rmtree(seeded / "tests")
            shutil.copytree(project / "tests", seeded / "tests", ignore=shutil.ignore_patterns("__pycache__"))
            before = run_pytest(python_env, extra_bin, seeded, regression_files)
            fixed = Path(folder) / "fixed"
            shutil.copytree(project, fixed, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            after = run_pytest(python_env, extra_bin, fixed, regression_files)
            regression = {"before_fix": pytest_counts(before["cases"] or []),
                          "after_fix": pytest_counts(after["cases"] or [])}
        outcome["regression"] = regression
        outcome["regression_ok"] = bool(regression_files) and regression["before_fix"] is not None \
            and (regression["before_fix"]["failure"] + regression["before_fix"]["error"]) >= 1 \
            and regression["after_fix"]["total"] >= 1 \
            and regression["after_fix"]["failure"] == 0 and regression["after_fix"]["error"] == 0
    explanation = project / "ROOT_CAUSE.md"
    text = explanation.read_text(encoding="utf-8", errors="replace") if explanation.is_file() else ""
    outcome["root_cause_file_present"] = bool(text.strip())
    outcome["root_cause_names_parser"] = bool(ROOT_CAUSE_FILE.search(text))
    outcome["root_cause_names_pattern"] = bool(ROOT_CAUSE_PATTERN.search(text))
    outcome["explanation_ok"] = outcome["root_cause_names_parser"] and outcome["root_cause_names_pattern"]
    outcome["passed"] = all(outcome[key] for key in ("hidden_suite_ok", "scope_ok", "regression_ok", "explanation_ok"))
    return outcome


# -- task c ------------------------------------------------------------------

TRUE_WORDS, FALSE_WORDS = {"true", "1"}, {"false", "0"}


def read_labels(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return {row["PassengerId"]: row["Transported"] == "True" for row in csv.DictReader(handle)}


def read_predictions(path, expected_ids):
    if not Path(path).is_file():
        return None, "predictions_missing"
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or [name.strip() for name in reader.fieldnames] != ["PassengerId",
                                                                                              "Transported"]:
                return None, "columns_not_exactly_PassengerId_Transported"
            predictions = {}
            for row in reader:
                key = (row.get("PassengerId") or "").strip()
                value = (row.get("Transported") or "").strip().lower()
                if key in predictions:
                    return None, "duplicate_passenger"
                if value in TRUE_WORDS:
                    predictions[key] = True
                elif value in FALSE_WORDS:
                    predictions[key] = False
                else:
                    return None, "label_not_boolean"
    except (UnicodeDecodeError, csv.Error):
        return None, "unreadable_csv"
    if set(predictions) != set(expected_ids):
        return None, "passenger_set_differs"
    return predictions, None


def score_spaceship(project, hidden, python_env, extra_bin, rerun=True):
    project, hidden = Path(project), Path(hidden)
    labels = read_labels(hidden / "holdout_labels.csv")
    predictions, refusal = read_predictions(project / "predictions.csv", labels)
    outcome = {"valid": predictions is not None, "refusal": refusal}
    if predictions is not None:
        correct = sum(predictions[key] == labels[key] for key in labels)
        outcome["accuracy"] = round(correct / len(labels), 4)
        outcome["rows"] = len(labels)
    outcome["passed"] = predictions is not None and outcome["accuracy"] >= SPACESHIP_ACCURACY_FLOOR
    outcome["solution_script_present"] = (project / "solution.py").is_file()
    if rerun and outcome["solution_script_present"] and predictions is not None:
        with tempfile.TemporaryDirectory(prefix="score-c-") as folder:
            tree = Path(folder) / "rerun"
            shutil.copytree(project, tree, ignore=shutil.ignore_patterns(".git", "__pycache__", "predictions.csv"))
            status, out, err = sandboxed(python_env, extra_bin, tree, ["python", "solution.py"], 900)
            again, again_refusal = read_predictions(tree / "predictions.csv", labels)
            outcome["rerun"] = {"exit_status": status, "valid": again is not None, "refusal": again_refusal}
            if again is not None:
                outcome["rerun"]["agreement_with_submitted"] = round(
                    sum(again[key] == predictions[key] for key in labels) / len(labels), 4)
                outcome["rerun"]["accuracy"] = round(sum(again[key] == labels[key] for key in labels) / len(labels), 4)
    return outcome


def score(task, project, pilot_root, python_env, extra_bin, rerun=True):
    pilot_root = Path(pilot_root)
    hidden = pilot_root / "hidden" / task
    if task == "a-cachetools-tlru":
        return score_tlru(project, hidden, pilot_root / "upstream" / task, python_env, extra_bin)
    if task == "b-dotenv-backslash":
        return score_dotenv(project, hidden, pilot_root / "upstream" / task,
                            pilot_root / "templates" / task / "project", python_env, extra_bin)
    if task == "c-spaceship-titanic":
        return score_spaceship(project, hidden, python_env, extra_bin, rerun=rerun)
    raise ValueError(task)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("project", type=Path)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--python-env", type=Path, required=True)
    parser.add_argument("--extra-bin", type=Path, required=True)
    parser.add_argument("--no-rerun", action="store_true")
    args = parser.parse_args()
    print(json.dumps(score(args.task, args.project, args.pilot_root, args.python_env, args.extra_bin,
                           rerun=not args.no_rerun), indent=1))
