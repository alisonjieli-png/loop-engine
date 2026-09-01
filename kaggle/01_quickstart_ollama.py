# ============================================================
# Loop Engine — Kaggle minimal quickstart (Ollama Cloud only)
#
# ONE cell. Requires Kaggle secret: ollama_kaggle_key
#
# The smallest working surface: one provider, no custom endpoints,
# no failover, no settings file. Exact prompts and model outputs
# stream to stderr by default. Artifacts land in one solutions
# folder; logs land in one folder.
#
# Based on loop-engine main.
# ============================================================

from kaggle_secrets import UserSecretsClient
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.request
import zipfile


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

REPOSITORY_ARCHIVE_URL = (
    "https://github.com/alisonjieli-png/"
    "loop-engine/archive/refs/heads/main.zip"
)

REPOSITORY_DIR = Path("/kaggle/working/loop-engine-src")
DATASET_DIR = Path("/kaggle/input/competitions/playground-series-s6e9")
RUNS_DIR = Path("/kaggle/working/loop-engine-logs/run-history")
SOLUTIONS_DIR = Path("/kaggle/working/loop-engine-solutions")
SOLVE_LOG_DIR = Path("/kaggle/working/loop-engine-logs/solve")
TASK_FILE = Path("/kaggle/working/loop-engine-s6e9-task.md")

PROBE_MODEL_ID = "deepseek-v4-flash:0731"

RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
WORKSPACE = Path(f"/kaggle/working/loop-engine-s6e9-solve-{RUN_STAMP}")

for directory in (RUNS_DIR, SOLUTIONS_DIR, SOLVE_LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def get_secret(client, name):
    """Read one required Kaggle secret without displaying its value."""
    value = client.get_secret(name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"Kaggle secret {name!r} is empty or unavailable. "
            "Create the secret and enable notebook access.")
    return value.strip()


def run_command(command, *, cwd=None, env=None, check=True):
    """Run one command without shell interpolation."""
    command = [str(part) for part in command]
    working_directory = Path(cwd or Path.cwd()).resolve()
    print(f"\n[{working_directory}]$ {shlex.join(command)}\n", flush=True)
    result = subprocess.run(
        command, cwd=str(working_directory), env=env,
        text=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command exited with status {result.returncode}: "
            f"{shlex.join(command)}")
    return result


# ------------------------------------------------------------
# 1. Configure the one provider
# ------------------------------------------------------------

ollama_key = get_secret(UserSecretsClient(), "ollama_kaggle_key")
os.environ["OLLAMA_API_KEY"] = ollama_key
command_environment = os.environ.copy()

print("OLLAMA_API_KEY configured:",
      bool(command_environment.get("OLLAMA_API_KEY")))


# ------------------------------------------------------------
# 2. Clean old debris, download and install main
# ------------------------------------------------------------

if REPOSITORY_DIR.exists():
    shutil.rmtree(REPOSITORY_DIR, ignore_errors=True)
for stale in Path("/kaggle/working").glob("loop-engine-s6e9-solve-*"):
    shutil.rmtree(stale, ignore_errors=True)

temp_dir = Path("/kaggle/temp/loop-engine-setup")
if temp_dir.exists():
    shutil.rmtree(temp_dir)
temp_dir.mkdir(parents=True, exist_ok=True)
archive_path = temp_dir / "loop-engine-main.zip"

print("\nDownloading Loop Engine main...", flush=True)
download_request = urllib.request.Request(
    REPOSITORY_ARCHIVE_URL,
    headers={"User-Agent": "Kaggle-Loop-Engine-Setup",
             "Accept": "application/zip"})
with urllib.request.urlopen(download_request, timeout=300) as response:
    with archive_path.open("wb") as output_file:
        shutil.copyfileobj(response, output_file)

with zipfile.ZipFile(archive_path, "r") as archive:
    roots = {
        PurePosixPath(name).parts[0]
        for name in archive.namelist()
        if name and PurePosixPath(name).parts
    }
    if len(roots) != 1:
        raise RuntimeError(f"Archive had multiple roots: {sorted(roots)}")
    archive.extractall(temp_dir)

shutil.move(str(temp_dir / next(iter(roots))), str(REPOSITORY_DIR))
shutil.rmtree(temp_dir, ignore_errors=True)

run_command(
    [sys.executable, "-m", "pip", "install",
     "--upgrade", "--editable", str(REPOSITORY_DIR)],
    cwd=REPOSITORY_DIR, env=command_environment)
os.chdir(REPOSITORY_DIR)


# ------------------------------------------------------------
# 3. Diagnostics + one authorized provider probe
# ------------------------------------------------------------

run_command(
    [sys.executable, "-m", "loop_engine", "doctor"],
    cwd=REPOSITORY_DIR, env=command_environment)

run_command(
    [sys.executable, "-m", "loop_engine", "configure"],
    cwd=REPOSITORY_DIR, env=command_environment)

run_command(
    [sys.executable, "-m", "loop_engine", "models", "probe",
     "ollama_cloud",
     "--model-route", "cloud.default",
     "--model-id", PROBE_MODEL_ID,
     "--authorize-model-calls", "--max-model-calls", "1",
     "--max-total-tokens", "70000"],
    cwd=REPOSITORY_DIR, env=command_environment)


# ------------------------------------------------------------
# 4. Task
# ------------------------------------------------------------

TASK = """
Build and verify a reproducible baseline solution for the supplied Kaggle
Playground Series S6E9 competition dataset.

This is an execution task, not merely a high-level modeling plan.

When using core.source.inspect:
1. Request the source manifest first without guessing paths.
2. Read the exact relative paths returned by the manifest.
3. Inspect file contents using only those returned paths.

Inspect train.csv, test.csv, and sample_submission.csv. Infer the target,
identifier, prediction fields, task type, and submission contract from the
actual schemas. Check missing values, duplicates, leakage, suspicious unique
fields, and train/test schema differences.

Build a CPU-compatible preprocessing pipeline. Compare at least two reasonable
baseline models with reproducible three-fold cross-validation and an
appropriate local validation metric. Fit the selected model on all training
rows and create submission.csv matching sample_submission.csv exactly.

Write these files inside the assigned workspace:

- solution.py
- submission.csv
- metrics.json
- report.md
- verification.json

Verify schema, row count, column order, identifier order, missing predictions,
infinite predictions, prediction type, and prediction range. Treat
/kaggle/input as read-only. Do not submit anything to Kaggle. Use fixed seeds
and do not run a large hyperparameter search. The environment has no Docker:
generated code must run with the preinstalled Python packages directly and
must not use dependency-install network commands.

Return COMPLETED_VERIFIED only after all required artifacts exist and all
verification checks pass.
""".strip()

TASK_FILE.write_text(TASK + "\n", encoding="utf-8")
print("\nTask file:", TASK_FILE)
print("Workspace:", WORKSPACE)


# ------------------------------------------------------------
# 5. Solve: Ollama only, exact model IO traced to stderr
# ------------------------------------------------------------

command = [
    sys.executable, "-m", "loop_engine", "solve",
    "--file", str(TASK_FILE),
    "--dataset", str(DATASET_DIR),
    "--workspace", str(WORKSPACE),
    "--runs-dir", str(RUNS_DIR),
    "--compile-provider", "ollama_cloud",
    "--provider-key-env", "OLLAMA_API_KEY",
    "--model-route", "cloud.default",
    "--authorize-model-calls",
    "--allow-source-to-model",
    "--no-default-extensions",
    "--format", "json",
]

print("\nRunning:\n", shlex.join(command), "\n", flush=True)

completed = subprocess.run(
    command, cwd=str(REPOSITORY_DIR), env=command_environment,
    text=True, stdout=subprocess.PIPE, stderr=None, check=False)

raw_output = completed.stdout.strip()
stdout_log = SOLVE_LOG_DIR / f"solve-stdout-{RUN_STAMP}.json"
stdout_log.write_text(raw_output + "\n", encoding="utf-8")

print("\n" + "=" * 72)
print("FINAL LOOP ENGINE RECORD")
print("=" * 72)
print(raw_output or "(Loop Engine produced no stdout.)")

try:
    final_record = json.loads(raw_output) if raw_output else {}
except json.JSONDecodeError:
    final_record = {}


# ------------------------------------------------------------
# 6. Save artifacts and summarize
# ------------------------------------------------------------

solved_workspace = Path(
    str(final_record.get("workspace") or WORKSPACE))
attempt_dir = SOLUTIONS_DIR / f"attempt-{RUN_STAMP}"
attempt_dir.mkdir(parents=True, exist_ok=True)

print("\nSolution artifacts:", attempt_dir)
for expected in ("solution.py", "submission.csv", "metrics.json",
                 "report.md", "verification.json"):
    for found in solved_workspace.glob(f"**/{expected}"):
        if found.name == expected:
            shutil.copy2(found, attempt_dir / found.name)
            print(f"  {found.name} ({found.stat().st_size} bytes)")

print("\n" + "-" * 60)
print("Terminal:", final_record.get("terminal_code"))
print("Solved:", final_record.get("solved"))
print("Model calls:", final_record.get("model_calls"))
for artifact in final_record.get("artifacts") or []:
    print(f"  artifact: {artifact.get('path')} "
          f"verified={artifact.get('verified')}")
for limitation in final_record.get("limitations") or []:
    print("  limitation:", limitation)
run_id = final_record.get("run_id")
if run_id:
    print(f"\nInspect: loop-engine report {run_id} --runs-dir {RUNS_DIR}")
print("\nRun History:", RUNS_DIR)
print("Solve stdout record:", stdout_log)