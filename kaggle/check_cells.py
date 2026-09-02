#!/usr/bin/env python3
"""Local harness for the Kaggle notebook cells.

Runs one cell (or all three) against a temporary Kaggle-shaped root with a
tiny synthetic competition dataset, stops at the requested stage, and checks
the files the stage must leave behind.

    python kaggle/check_cells.py --cell 01 --stage offline
    python kaggle/check_cells.py --cell all --stage offline
    python kaggle/check_cells.py --cell 02 --stage preflight
    python kaggle/check_cells.py --cell 03 --stage solve --verbose

Stage offline needs no provider key and no network: provider variables are
removed from the child's environment so nothing can be called by accident.
Stages preflight and solve need the provider keys of the chosen cell in the
environment; the harness refuses (exit 2) when they are missing and never
fabricates one.

Exit codes: 0 every check passed, 1 a check failed, 2 the run was refused.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parent

STAGES = ("offline", "preflight", "solve")

# Cell id -> (file name, keys it needs as (secret name, standard variable)).
CELLS = {
    "01": ("01_quickstart_ollama.py",
           (("ollama_kaggle_key", "OLLAMA_API_KEY"),)),
    "02": ("02_tacticalengineering_only.py",
           (("tacticalhat_kaggle_key", "TACTICAL_API_KEY"),)),
    "03": ("03_three_provider_failover.py",
           (("ollama_kaggle_key", "OLLAMA_API_KEY"),
            ("mistral_kaggle_key", "MISTRAL_API_KEY"),
            ("tacticalhat_kaggle_key", "TACTICAL_API_KEY"))),
}

# Every provider variable the cells know about. The offline stage removes
# all of them from the child's environment.
PROVIDER_VARIABLES = (
    "OLLAMA_API_KEY", "MISTRAL_API_KEY", "TACTICAL_API_KEY",
    "OLLAMA_KAGGLE_KEY", "MISTRAL_KAGGLE_KEY", "TACTICALHAT_KAGGLE_KEY",
    "TACTICALHAT_API_KEY", "LOOP_ENGINE_ENDPOINTS", "OPENWEBUI_API_KEY",
    "PRIVATE_OPENWEBUI_API_KEY", "OPENROUTER_API_KEY",
    "OPENCODE_ZEN_API_KEY", "OPENCODE_GO_API_KEY",
)

DATASET_ROWS = 200
DATASET_TEST_ROWS = 100
DATASET_SEED = 20260901
FEATURES = tuple(f"feature_{index}" for index in range(1, 7))


def key_available(secret_name: str, standard_env: str) -> bool:
    """True when either the secret-shaped or the standard variable is set."""
    return bool(os.environ.get(secret_name.upper(), "").strip()
                or os.environ.get(standard_env, "").strip())


def write_dataset(dataset_dir: Path) -> dict:
    """Write a tiny deterministic binary-classification competition."""
    dataset_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(DATASET_SEED)

    def make_rows(count: int, first_id: int, with_target: bool) -> list:
        rows = []
        for offset in range(count):
            values = [round(rng.gauss(0.0, 1.0), 4) for _ in FEATURES]
            row = {"id": first_id + offset}
            row.update(zip(FEATURES, values))
            if with_target:
                score = (0.8 * values[0] - 0.6 * values[1]
                         + 0.3 * values[2] + rng.gauss(0.0, 0.5))
                row["target"] = int(score > 0.0)
            rows.append(row)
        return rows

    train = make_rows(DATASET_ROWS, 0, True)
    test = make_rows(DATASET_TEST_ROWS, DATASET_ROWS, False)

    def write_csv(path: Path, fieldnames: list, rows: list) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(dataset_dir / "train.csv", ["id", *FEATURES, "target"], train)
    write_csv(dataset_dir / "test.csv", ["id", *FEATURES], test)
    write_csv(dataset_dir / "sample_submission.csv", ["id", "target"],
              [{"id": row["id"], "target": 0} for row in test])
    return {"train_rows": len(train), "test_rows": len(test),
            "feature_columns": len(FEATURES),
            "positives": sum(row["target"] for row in train)}


def child_environment(stage: str, root: Path, working: Path,
                      competition: str) -> dict:
    """Environment for one cell run; keys stay out of it for offline."""
    env = dict(os.environ)
    if stage == "offline":
        for name in PROVIDER_VARIABLES:
            env.pop(name, None)
    env.update({
        "LOOP_ENGINE_KAGGLE_WORKING": str(working),
        "LOOP_ENGINE_KAGGLE_INPUT": str(root / "input"),
        "LOOP_ENGINE_KAGGLE_TEMP": str(root / "temp"),
        "LOOP_ENGINE_KAGGLE_COMPETITION": competition,
        "LOOP_ENGINE_SOURCE_DIR": str(REPOSITORY_ROOT),
        "LOOP_ENGINE_KAGGLE_STAGE": stage,
        "PYTHONUNBUFFERED": "1",
    })
    return env


def run_cell(cell_id: str, stage: str, root: Path, working: Path,
             competition: str, log_path: Path, verbose: bool,
             timeout: float | None) -> dict:
    """Run one cell as a subprocess; stream or store its output."""
    cell_path = HERE / CELLS[cell_id][0]
    env = child_environment(stage, root, working, competition)
    working.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, str(cell_path)], cwd=str(working), env=env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1)
        try:
            for line in process.stdout:
                log.write(line)
                log.flush()
                if verbose:
                    print(line, end="", flush=True)
                if timeout and time.monotonic() - started > timeout:
                    process.kill()
                    timed_out = True
                    break
            exit_code = process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            raise
    return {"exit_code": exit_code, "timed_out": timed_out,
            "elapsed": time.monotonic() - started, "log": log_path}


def load_single_json(paths: list) -> dict | None:
    """Return the newest JSON document among paths, or None."""
    if not paths:
        return None
    newest = max(paths, key=lambda path: path.stat().st_mtime)
    try:
        return json.loads(newest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def check_stage(stage: str, working: Path, run: dict) -> list:
    """Return (name, passed, detail) triples for the stage's contract."""
    checks = []
    log_text = run["log"].read_text(encoding="utf-8", errors="replace")
    logs = working / "loop-engine-logs"
    stage_record = load_single_json(list(logs.glob("stage-*.json")))

    if run["timed_out"]:
        checks.append(("cell finished", False,
                       "killed by the harness timeout"))
    elif stage == "preflight" and run["exit_code"] != 0 \
            and stage_record and stage_record.get("preflight_ok") is False:
        checks.append(("cell finished", False,
                       "stopped honestly: no provider passed preflight"))
    else:
        checks.append(("cell exit 0", run["exit_code"] == 0,
                       f"exit {run['exit_code']}"))

    if stage_record is None:
        checks.append(("stage record", False,
                       f"no stage-*.json under {logs}"))
        return checks
    reached = stage_record.get("stage_reached")
    checks.append(("stage record", reached == stage,
                   f"stage_reached={reached!r}, "
                   f"install={stage_record.get('install_mode')!r}"))

    commands = stage_record.get("commands") or {}
    for name in ("doctor", "configure"):
        code = (commands.get(name) or {}).get("exit_code")
        checks.append((f"{name} exit 0", code == 0, f"exit {code}"))
    checks.append(("doctor answered", "Loop Engine doctor" in log_text,
                   "doctor banner seen in the cell output"
                   if "Loop Engine doctor" in log_text
                   else "doctor banner missing from the cell output"))
    if stage == "offline":
        return checks

    preflight = load_single_json(
        list((logs / "preflight").glob("preflight-*.json")))
    if preflight is None:
        checks.append(("preflight record", False,
                       "no preflight-*.json written"))
        return checks
    providers = preflight.get("providers") or []
    typed = all(isinstance(item.get("ok"), bool) for item in providers)
    ok_names = [item["provider"] for item in providers if item.get("ok")]
    failed_names = [item["provider"] for item in providers
                    if not item.get("ok")]
    checks.append(("preflight record", bool(providers) and typed,
                   f"{len(providers)} provider(s) with boolean ok flags"))
    checks.append(("provider probe ok", bool(ok_names),
                   f"ok={ok_names} failed={failed_names}"))
    if stage == "preflight":
        return checks

    outcomes = list((logs / "run-history").glob("*/outcome.json"))
    solve_record = load_single_json(
        list((logs / "solve").glob("solve-stdout-*.json*")))
    terminal = (solve_record or {}).get("terminal_code") \
        or stage_record.get("terminal_code")
    checks.append(("solve outcome", bool(outcomes) or bool(terminal),
                   f"{len(outcomes)} outcome.json under run-history; "
                   f"terminal={terminal!r}; "
                   f"solved={stage_record.get('solved')!r}"))
    return checks


def refuse(message: str) -> int:
    print(f"REFUSED: {message}", file=sys.stderr)
    return 2


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--cell", default="01",
                        choices=(*CELLS, "all"),
                        help="which cell to run (default 01)")
    parser.add_argument("--stage", default="offline", choices=STAGES,
                        help="where the cell stops (default offline)")
    parser.add_argument("--competition", default="playground-series-s6e9",
                        help="competition slug for the synthetic dataset")
    parser.add_argument("--root", metavar="DIR",
                        help="parent directory for the temporary root "
                             "(default: the system temp directory)")
    parser.add_argument("--keep", action="store_true",
                        help="keep the temporary root after a passing run "
                             "(a failing run always keeps it)")
    parser.add_argument("--verbose", action="store_true",
                        help="stream the cell output live as well as to "
                             "the log file")
    parser.add_argument("--timeout", type=float, default=0.0,
                        metavar="SECONDS",
                        help="kill a cell that runs longer than this "
                             "(default: no limit)")
    args = parser.parse_args(argv)

    cells = list(CELLS) if args.cell == "all" else [args.cell]

    if not (REPOSITORY_ROOT / "pyproject.toml").exists():
        return refuse(f"{REPOSITORY_ROOT} is not the loop-engine checkout "
                      "(pyproject.toml missing)")

    if args.stage != "offline":
        missing = []
        for cell_id in cells:
            for secret_name, standard_env in CELLS[cell_id][1]:
                if not key_available(secret_name, standard_env):
                    missing.append(
                        f"cell {cell_id}: set {secret_name.upper()} "
                        f"or {standard_env}")
        if missing:
            return refuse(
                f"stage {args.stage!r} needs provider keys that are not "
                "in the environment. No key is ever fabricated.\n  "
                + "\n  ".join(sorted(set(missing))))

    parent = Path(args.root).resolve() if args.root else None
    if parent is not None:
        parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="loop-engine-kaggle-",
                                 dir=str(parent) if parent else None))
    (root / "temp").mkdir()
    dataset_dir = root / "input" / "competitions" / args.competition
    dataset = write_dataset(dataset_dir)

    print("Loop Engine Kaggle cell check")
    print(f"  interpreter : {sys.executable}")
    print(f"  repository  : {REPOSITORY_ROOT} (LOOP_ENGINE_SOURCE_DIR)")
    print(f"  root        : {root}")
    print(f"  dataset     : {dataset_dir.relative_to(root)} "
          f"(train {dataset['train_rows']} rows, "
          f"test {dataset['test_rows']} rows, "
          f"{dataset['feature_columns']} numeric columns + id, "
          f"{dataset['positives']} positives, seed {DATASET_SEED})")
    print(f"  stage       : {args.stage}"
          + (" (no provider key, no network)" if args.stage == "offline"
             else " (live provider calls; may take a long time)"))
    if args.stage != "offline" and not args.verbose:
        print("  note        : cell output goes to the log files below; "
              "add --verbose to watch it live")
    print()

    results = []
    for cell_id in cells:
        working = root / f"working-{cell_id}"
        log_path = root / f"cell-{cell_id}-{args.stage}.log"
        print(f"  running cell {cell_id} ({CELLS[cell_id][0]}) ...",
              flush=True)
        run = run_cell(cell_id, args.stage, root, working, args.competition,
                       log_path, args.verbose, args.timeout or None)
        checks = check_stage(args.stage, working, run)
        results.append((cell_id, run, checks))

    all_passed = all(passed for _, _, checks in results
                     for _, passed, _ in checks)

    print()
    print(f"  {'cell':<5} {'result':<7} {'exit':<5} {'time':<8} checks")
    for cell_id, run, checks in results:
        passed = all(item[1] for item in checks)
        print(f"  {cell_id:<5} {'PASS' if passed else 'FAIL':<7} "
              f"{run['exit_code']:<5} {run['elapsed']:>6.1f}s "
              + "; ".join(
                  f"{name} {'ok' if ok else 'FAILED'} ({detail})"
                  for name, ok, detail in checks))
        print(f"  {'':<5} log: {run['log']}")
    print()

    if all_passed and not args.keep:
        shutil.rmtree(root, ignore_errors=True)
        print(f"  temporary root removed (use --keep to keep it): {root}")
    else:
        print(f"  temporary root kept: {root}")
    print(f"  RESULT: {'PASS' if all_passed else 'FAIL'} "
          f"({len(results)} cell(s), stage {args.stage})")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
