"""Known-wrong and known-good controls for the three pilot scorers, run before any counted model call.

Each control is a project folder built from a frozen template, changed in one
declared way, and scored by `scoring.py` exactly as a trial would be. Every
known-wrong control must fail and every known-good control must pass, or the
design is not frozen. Usage:

    python3 controls.py --pilot-root DIR --python-env DIR --extra-bin DIR --output controls.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scoring  # noqa: E402

NAIVE_TLRU = '''

class TLRUCache(LRUCache):
    """Known-wrong control: an LRU cache that ignores the time-to-use function."""

    def __init__(self, maxsize, ttu, timer=time.monotonic, getsizeof=None):
        LRUCache.__init__(self, maxsize, getsizeof)
        self.__ttu = ttu
        self.__timer = timer

    @property
    def ttu(self):
        return self.__ttu

    @property
    def timer(self):
        return self.__timer

    def expire(self, time=None):
        return []
'''

TTL_TLRU = '''

class TLRUCache(TTLCache):
    """Known-wrong control: a TTL cache with a constant time-to-live instead of a time-to-use function."""

    def __init__(self, maxsize, ttu, timer=time.monotonic, getsizeof=None):
        TTLCache.__init__(self, maxsize, 600, timer, getsizeof)
        self.__ttu = ttu

    @property
    def ttu(self):
        return self.__ttu
'''

REGRESSION_TEST = '''import dotenv


def test_value_ending_in_backslash_round_trips(tmp_path):
    path = tmp_path / ".env"
    path.write_text("")
    dotenv.set_key(path, "WIN_DIR", "C:\\\\Users\\\\me\\\\")
    dotenv.set_key(path, "NEXT", "ok")
    assert dotenv.get_key(path, "WIN_DIR") == "C:\\\\Users\\\\me\\\\"
    assert dotenv.get_key(path, "NEXT") == "ok"
'''

ROOT_CAUSE = """# Root cause

The pattern `_single_quoted_value` in `src/dotenv/parser.py` treats a backslash followed by a quote as an
escaped quote, but it does not treat `\\\\` as an escaped backslash. `set_key` in `main.py` now writes every
backslash as `\\\\`, so a value that ends in a backslash is written as `...\\\\'`, and the parser reads the
last backslash and the closing quote as an escaped quote. The value then runs on into the next line, the
binding fails to parse and the next key disappears. The symptom shows up when the value is read back, but
the writer is correct; the single-quoted value regex is wrong, and the double-quoted pattern has the same flaw.
"""

SINGLE_OLD = '_single_quoted_value = make_regex(r"\'((?:\\\\\'|[^\'])*)\'")'
SINGLE_NEW = '_single_quoted_value = make_regex(r"\'((?:\\\\.|[^\'\\\\])*)\'", extra_flags=re.DOTALL)'
SET_KEY_OLD = 'escaped = value_to_set.replace("\\\\", "\\\\\\\\").replace("\'", "\\\\\'")'
SET_KEY_NEW = 'escaped = value_to_set.replace("\'", "\\\\\'")'


def copy_template(pilot_root, task, folder, name):
    target = Path(folder) / name
    shutil.copytree(Path(pilot_root) / "templates" / task / "project", target, ignore=shutil.ignore_patterns(".git"))
    return target


def replace_once(path, old, new):
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"control edit target not found exactly once in {path}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def tlru_controls(pilot_root, folder):
    task = "a-cachetools-tlru"
    rows = []
    unchanged = copy_template(pilot_root, task, folder, "a-k1-unchanged")
    rows.append(("a-K1", "template unchanged: no TLRUCache", False, unchanged))
    naive = copy_template(pilot_root, task, folder, "a-k2-lru-ignores-ttu")
    init = naive / "src" / "cachetools" / "__init__.py"
    replace_once(init, '    "TTLCache",\n', '    "TTLCache",\n    "TLRUCache",\n')
    init.write_text(init.read_text(encoding="utf-8") + NAIVE_TLRU, encoding="utf-8")
    rows.append(("a-K2", "an LRU cache that ignores ttu", False, naive))
    ttl = copy_template(pilot_root, task, folder, "a-k3-constant-ttl")
    init = ttl / "src" / "cachetools" / "__init__.py"
    replace_once(init, '    "TTLCache",\n', '    "TTLCache",\n    "TLRUCache",\n')
    init.write_text(init.read_text(encoding="utf-8") + TTL_TLRU, encoding="utf-8")
    rows.append(("a-K3", "a TTL cache with a constant time-to-live", False, ttl))
    good = copy_template(pilot_root, task, folder, "a-p1-upstream")
    shutil.copy2(Path(pilot_root) / "hidden" / task / "reference" / "__init__.py",
                 good / "src" / "cachetools" / "__init__.py")
    rows.append(("a-P1", "the upstream TLRUCache restored", True, good))
    return task, rows


def dotenv_controls(pilot_root, folder):
    task = "b-dotenv-backslash"
    reference = Path(pilot_root) / "hidden" / task / "reference" / "parser.py"
    rows = []
    rows.append(("b-K1", "seeded tree unchanged, no test, no explanation", False,
                 copy_template(pilot_root, task, folder, "b-k1-unchanged")))
    misleading = copy_template(pilot_root, task, folder, "b-k2-misleading-set-key-fix")
    replace_once(misleading / "src" / "dotenv" / "main.py", SET_KEY_OLD, SET_KEY_NEW)
    (misleading / "tests" / "test_regression_backslash.py").write_text(REGRESSION_TEST, encoding="utf-8")
    (misleading / "ROOT_CAUSE.md").write_text("set_key in main.py double-escaped backslashes.\n", encoding="utf-8")
    rows.append(("b-K2", "the misleading fix: stop escaping backslashes in set_key", False, misleading))
    narrow = copy_template(pilot_root, task, folder, "b-k3-single-quoted-only")
    replace_once(narrow / "src" / "dotenv" / "parser.py", SINGLE_OLD, SINGLE_NEW)
    (narrow / "tests" / "test_regression_backslash.py").write_text(REGRESSION_TEST, encoding="utf-8")
    (narrow / "ROOT_CAUSE.md").write_text(ROOT_CAUSE, encoding="utf-8")
    rows.append(("b-K3", "only the single-quoted pattern repaired", False, narrow))
    untested = copy_template(pilot_root, task, folder, "b-k4-fix-without-test-or-explanation")
    shutil.copy2(reference, untested / "src" / "dotenv" / "parser.py")
    rows.append(("b-K4", "the upstream parser restored without a regression test or explanation", False, untested))
    wide = copy_template(pilot_root, task, folder, "b-k5-fix-with-unrelated-change")
    shutil.copy2(reference, wide / "src" / "dotenv" / "parser.py")
    replace_once(wide / "src" / "dotenv" / "main.py", SET_KEY_OLD, SET_KEY_OLD + "  # unrelated edit")
    (wide / "tests" / "test_regression_backslash.py").write_text(REGRESSION_TEST, encoding="utf-8")
    (wide / "ROOT_CAUSE.md").write_text(ROOT_CAUSE, encoding="utf-8")
    rows.append(("b-K5", "the right fix plus an unrelated change to main.py", False, wide))
    good = copy_template(pilot_root, task, folder, "b-p1-upstream-fix")
    shutil.copy2(reference, good / "src" / "dotenv" / "parser.py")
    (good / "tests" / "test_regression_backslash.py").write_text(REGRESSION_TEST, encoding="utf-8")
    (good / "ROOT_CAUSE.md").write_text(ROOT_CAUSE, encoding="utf-8")
    rows.append(("b-P1", "the upstream parser fix with a regression test and an explanation", True, good))
    return task, rows


def spaceship_controls(pilot_root, folder, python_env):
    task = "c-spaceship-titanic"
    rows = []
    base = copy_template(pilot_root, task, folder, "c-base")
    labels = Path(pilot_root) / "hidden" / task / "holdout_labels.csv"
    generator = Path(__file__).resolve().parent / "spaceship_reference.py"
    names = {"c-K1": ("all passengers predicted True", "all_true"),
             "c-K2": ("the CryoSleep rule", "cryosleep"),
             "c-K3": ("plain logistic regression on unengineered numeric columns", "logistic"),
             "c-K4": ("the reference predictions shuffled across passengers", "shuffled"),
             "c-K5": ("the reference predictions with ten passengers missing", "missing_rows"),
             "c-K6": ("the reference predictions written as yes and no", "yes_no")}
    for key, (label, mode) in names.items():
        project = copy_template(pilot_root, task, folder, key.lower())
        subprocess.run([str(Path(python_env) / "bin" / "python"), "-I", str(generator), "--mode", mode,
                        "--data", str(base / "data"), "--output", str(project / "predictions.csv")],
                       check=True, env={"OMP_NUM_THREADS": "2", "PATH": "/usr/bin:/bin"})
        rows.append((key, label, False, project))
    good = copy_template(pilot_root, task, folder, "c-p1-reference")
    shutil.copy2(generator, good / "solution.py")
    subprocess.run([str(Path(python_env) / "bin" / "python"), "-I", "solution.py"], cwd=good, check=True,
                   env={"OMP_NUM_THREADS": "2", "PATH": "/usr/bin:/bin"})
    rows.append(("c-P1", "gradient boosting on engineered features (reference solution.py)", True, good))
    del labels
    return task, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--python-env", type=Path, required=True)
    parser.add_argument("--extra-bin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix="pilot-controls-") as folder:
        for task, rows in (tlru_controls(args.pilot_root, folder), dotenv_controls(args.pilot_root, folder),
                           spaceship_controls(args.pilot_root, folder, args.python_env)):
            for key, label, expected, project in rows:
                outcome = scoring.score(task, project, args.pilot_root, args.python_env, args.extra_bin)
                results.append({"control": key, "task": task, "description": label, "expected_pass": expected,
                                "scored_pass": outcome["passed"], "as_expected": outcome["passed"] == expected,
                                "outcome": outcome})
                print(f"{key}: expected {'pass' if expected else 'fail'}, scored {'pass' if outcome['passed'] else 'fail'}")
    report = {"record_type": "comparison_pilot_scorer_controls/v1", "model_calls": 0,
              "all_as_expected": all(row["as_expected"] for row in results), "controls": results}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print("all as expected:", report["all_as_expected"])
    return 0 if report["all_as_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
