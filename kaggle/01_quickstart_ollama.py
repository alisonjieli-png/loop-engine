# ============================================================
# Loop Engine - Kaggle minimal quickstart (Ollama Cloud only)
#
# ONE cell. Requires Kaggle secret: ollama_kaggle_key
#
# The smallest working surface: one provider, no custom endpoints,
# no failover, no settings file. Exact prompts and model outputs
# stream to stderr by default. Artifacts land in one solutions
# folder; logs land in one folder.
#
# Output layout (under the Kaggle working directory):
#   loop-engine-solutions/attempt-<stamp>/   verified artifacts
#   loop-engine-logs/
#     preflight/                provider API check record
#     solve/                    final solve stdout record
#     run-history/              Loop Engine Run History dirs
#     stage-<stamp>.json        what this cell did and where it stopped
#
# Runs outside Kaggle too: kaggle/check_cells.py sets the
# LOOP_ENGINE_* variables read in the configuration block below.
#
# Based on loop-engine main (the cell installs the current main archive).
# ============================================================

from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.request
import zipfile

try:
    from kaggle_secrets import UserSecretsClient
except ImportError:  # outside Kaggle: keys come from the environment
    UserSecretsClient = None


# ------------------------------------------------------------
# Configuration
#
# Every path, name, and switch lives in this block. On Kaggle the
# defaults apply unchanged. Outside Kaggle the LOOP_ENGINE_* variables
# point the cell at another root (kaggle/check_cells.py sets them).
# ------------------------------------------------------------

REPOSITORY_ARCHIVE_URL = (
    "https://github.com/alisonjieli-png/"
    "loop-engine/archive/refs/heads/main.zip"
)

KAGGLE_WORKING = Path(os.environ.get(
    "LOOP_ENGINE_KAGGLE_WORKING", "/kaggle/working"))
KAGGLE_INPUT = Path(os.environ.get(
    "LOOP_ENGINE_KAGGLE_INPUT", "/kaggle/input"))
KAGGLE_TEMP = Path(os.environ.get(
    "LOOP_ENGINE_KAGGLE_TEMP", "/kaggle/temp"))
COMPETITION = os.environ.get(
    "LOOP_ENGINE_KAGGLE_COMPETITION", "playground-series-s6e9").strip()
# When set, this checkout is installed instead of downloading main.zip.
SOURCE_DIR = os.environ.get("LOOP_ENGINE_SOURCE_DIR", "").strip()
# offline: stop after doctor and configure (no key, no network).
# preflight: stop after the provider probe. solve: the full run.
STAGE = os.environ.get("LOOP_ENGINE_KAGGLE_STAGE", "solve").strip() or "solve"

# Kaggle secret name and the standard variable the provider reads.
OLLAMA_SECRET_NAME = "ollama_kaggle_key"
OLLAMA_KEY_ENV = "OLLAMA_API_KEY"

REPOSITORY_DIR = (Path(SOURCE_DIR) if SOURCE_DIR
                  else KAGGLE_WORKING / "loop-engine-src")
# The cell does not guess where the data lives. It hands the whole attached
# input root to the solve and lets the Practitioner orient over the exact
# manifest the runtime admits, exactly as it would for any other source. An
# explicit LOOP_ENGINE_KAGGLE_DATASET_DIR narrows the root when the operator
# wants that; it is authority, not a guess. COMPETITION only names the run and
# is carried into the task text as a hint, never as a path.
DATASET_DIR_OVERRIDE = os.environ.get(
    "LOOP_ENGINE_KAGGLE_DATASET_DIR", "").strip()


def resolve_dataset_dir(input_root, override=""):
    """Return the directory handed to the solve.

    This cell does not walk the input, does not describe it, and does not
    decide what any of it is. The runtime already enumerates the exact
    admitted manifest, states where each file is materialized, and asks a
    model what each one is; a listing written here would be a second, shallower
    answer to a question the run answers properly. So the cell checks only what
    an operator must fix before starting: that the directory exists and is not
    empty.
    """
    directory = Path(override) if override else input_root
    if not directory.is_dir():
        raise RuntimeError(
            f"No input directory at {directory}. Attach the competition or "
            "dataset to this notebook, or set "
            "LOOP_ENGINE_KAGGLE_DATASET_DIR to an existing directory.")
    if not any(directory.iterdir()):
        raise RuntimeError(
            f"The input directory {directory} is empty. Attach the "
            "competition or dataset to this notebook before the solve stage.")
    return directory

LOGS_DIR = KAGGLE_WORKING / "loop-engine-logs"
PREFLIGHT_DIR = LOGS_DIR / "preflight"
RUNS_DIR = LOGS_DIR / "run-history"
SOLVE_LOG_DIR = LOGS_DIR / "solve"
SOLUTIONS_DIR = KAGGLE_WORKING / "loop-engine-solutions"
TASK_FILE = KAGGLE_WORKING / f"loop-engine-{COMPETITION}-task.md"
SETUP_TEMP_DIR = KAGGLE_TEMP / "loop-engine-setup"

PROBE_MODEL_ID = "deepseek-v4-flash:0731"

RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
WORKSPACE_PREFIX = f"loop-engine-{COMPETITION}-solve-"
WORKSPACE = KAGGLE_WORKING / f"{WORKSPACE_PREFIX}{RUN_STAMP}"
STAGE_FILE = LOGS_DIR / f"stage-{RUN_STAMP}.json"

if STAGE not in ("offline", "preflight", "solve"):
    raise ValueError(
        "LOOP_ENGINE_KAGGLE_STAGE must be offline, preflight, or solve, "
        f"not {STAGE!r}")

for directory in (RUNS_DIR, PREFLIGHT_DIR, SOLVE_LOG_DIR, SOLUTIONS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

STAGE_RECORD = {
    "record_type": "loop_engine_kaggle_stage/v1",
    "cell": "01_quickstart_ollama",
    "attempt": RUN_STAMP,
    "stage_requested": STAGE,
    "stage_reached": "",
    "repository_dir": str(REPOSITORY_DIR),
    "install_mode": "",
    "commands": {},
}


def read_secret(secret_name, standard_env):
    """Return one key without ever displaying it.

    Order: the Kaggle secret, then an environment variable named like the
    secret in upper case, then the provider's standard variable. Returns
    an empty string when none is available; the caller decides whether
    that is fatal for the requested stage.
    """
    value = ""
    if UserSecretsClient is not None:
        try:
            value = UserSecretsClient().get_secret(secret_name)
        except Exception:  # secret not attached to this notebook
            value = ""
    if not isinstance(value, str) or not value.strip():
        value = os.environ.get(secret_name.upper(), "")
    if not value.strip():
        value = os.environ.get(standard_env, "")
    return value.strip()


def require_key(value, secret_name, standard_env):
    """Stop with a clear message when a stage needs a key that is missing."""
    if not value:
        raise RuntimeError(
            f"Stage {STAGE!r} needs a provider key, but Kaggle secret "
            f"{secret_name!r} is unavailable and neither "
            f"{secret_name.upper()} nor {standard_env} is set. Create the "
            "secret and enable notebook access, or set the variable.")


def run_command(command, *, cwd=None, env=None, check=True, capture=False):
    """Run one command without shell interpolation.

    With capture=True the command's stdout is kept on the result and
    echoed afterwards, so the notebook still shows it.
    """
    command = [str(part) for part in command]
    working_directory = Path(cwd or Path.cwd()).resolve()
    print(f"\n[{working_directory}]$ {shlex.join(command)}\n", flush=True)
    result = subprocess.run(
        command, cwd=str(working_directory), env=env, text=True,
        stdout=subprocess.PIPE if capture else None, check=False)
    if capture and result.stdout:
        print(result.stdout.rstrip("\n"), flush=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command exited with status {result.returncode}: "
            f"{shlex.join(command)}")
    return result


def install_loop_engine(repository_dir, env):
    """Install the checkout and return the install mode that was used.

    The Kaggle path installs with pip exactly as before. A local checkout
    (LOOP_ENGINE_SOURCE_DIR) also installs with pip when pip is present;
    when pip is missing or that install fails, the CLI runs from the
    checkout's src tree through PYTHONPATH so the cell stays testable in
    a pip-less virtual environment.
    """
    pip_present = importlib.util.find_spec("pip") is not None
    if pip_present:
        result = run_command(
            [sys.executable, "-m", "pip", "install",
             *([] if SOURCE_DIR else ["--upgrade"]),
             "--editable", str(repository_dir)],
            cwd=repository_dir, env=env, check=not SOURCE_DIR)
        if result.returncode == 0:
            return "pip_editable"
    if not SOURCE_DIR:
        raise RuntimeError("pip is not available in this interpreter")
    source_tree = repository_dir / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(source_tree), env.get("PYTHONPATH", ""))
        if part)
    print(f"\npip {'failed' if pip_present else 'is not available here'}; "
          f"the CLI runs from {source_tree} through PYTHONPATH.", flush=True)
    return "pythonpath"


def probe_builtin_provider(provider, route, model_id, max_total_tokens, env):
    """Run one authorized built-in probe and return a typed record.

    The probe never aborts the cell: ok is decided from the exit code
    AFTER the command has run, and the printed record is summarized.
    """
    result = run_command(
        [sys.executable, "-m", "loop_engine", "models", "probe", provider,
         "--model-route", route, "--model-id", model_id,
         "--authorize-model-calls", "--max-model-calls", "1",
         "--max-total-tokens", str(max_total_tokens)],
        cwd=REPOSITORY_DIR, env=env, check=False, capture=True)
    record = {
        "provider": provider,
        "probe_kind": "builtin_models_probe",
        "route": route,
        "model": model_id,
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
    }
    try:
        body = json.loads(result.stdout or "")
    except json.JSONDecodeError:
        body = {}
    record["status"] = body.get("status")
    note = body.get("reason") or body.get("status") or ""
    if not note:
        lines = (result.stdout or "").strip().splitlines()
        note = lines[-1] if lines else "no output"
    record["note"] = str(note)[:200]
    return record


def write_stage_record(stage_reached):
    """Save what the cell did so far; readable by people and by the harness."""
    STAGE_RECORD["stage_reached"] = stage_reached
    STAGE_FILE.write_text(
        json.dumps(STAGE_RECORD, indent=2) + "\n", encoding="utf-8")
    print(f"\nStage record: {STAGE_FILE}", flush=True)


def finish_stage(stage_reached):
    """Write the stage record; end the cell here when the stage asks for it."""
    write_stage_record(stage_reached)
    if STAGE == stage_reached and stage_reached != "solve":
        print(f"LOOP_ENGINE_KAGGLE_STAGE={STAGE}: stopping after the "
              f"{stage_reached} stage.", flush=True)
        sys.exit(0)


# ------------------------------------------------------------
# 1. Configure the one provider
# ------------------------------------------------------------

ollama_key = read_secret(OLLAMA_SECRET_NAME, OLLAMA_KEY_ENV)
os.environ.pop(OLLAMA_KEY_ENV, None)
if ollama_key:
    os.environ[OLLAMA_KEY_ENV] = ollama_key
elif STAGE != "offline":
    require_key(ollama_key, OLLAMA_SECRET_NAME, OLLAMA_KEY_ENV)
command_environment = os.environ.copy()

print(f"{OLLAMA_KEY_ENV} configured:",
      bool(command_environment.get(OLLAMA_KEY_ENV)))
print("Stage requested:", STAGE)

# Hand the attached input root to the solve and report what is in it. The
# runtime states the exact admitted manifest and a model call states what each
# file is; nothing here selects or describes a file. Only the solve stage needs
# data, so earlier stages report a miss and continue.
try:
    DATASET_DIR = resolve_dataset_dir(KAGGLE_INPUT, DATASET_DIR_OVERRIDE)
    print(f"Attached input root handed to the solve: {DATASET_DIR}")
    print(
        "  The run states the exact manifest and its own reading of each "
        "file; watch the source_manifest and source_roles runtime facts.")
except RuntimeError as dataset_error:
    if STAGE == "solve":
        raise
    DATASET_DIR = Path(DATASET_DIR_OVERRIDE) if DATASET_DIR_OVERRIDE \
        else KAGGLE_INPUT
    print(
        f"No attached input yet ({dataset_error}); the {STAGE} stage does "
        "not read it, so the run continues.")


# ------------------------------------------------------------
# 2. Clean old debris, then download and install main
#    (or install the local checkout named by LOOP_ENGINE_SOURCE_DIR)
# ------------------------------------------------------------

if not SOURCE_DIR and REPOSITORY_DIR.exists():
    shutil.rmtree(REPOSITORY_DIR, ignore_errors=True)
for stale in KAGGLE_WORKING.glob(f"{WORKSPACE_PREFIX}*"):
    shutil.rmtree(stale, ignore_errors=True)

if SOURCE_DIR:
    print("\nUsing local checkout:", REPOSITORY_DIR, flush=True)
else:
    if SETUP_TEMP_DIR.exists():
        shutil.rmtree(SETUP_TEMP_DIR)
    SETUP_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = SETUP_TEMP_DIR / "loop-engine-main.zip"

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
        archive.extractall(SETUP_TEMP_DIR)

    shutil.move(str(SETUP_TEMP_DIR / next(iter(roots))), str(REPOSITORY_DIR))
    shutil.rmtree(SETUP_TEMP_DIR, ignore_errors=True)

for required in (
        REPOSITORY_DIR / "pyproject.toml",
        REPOSITORY_DIR / "src" / "loop_engine"):
    if not required.exists():
        raise RuntimeError(f"Repository input missing: {required}")

STAGE_RECORD["install_mode"] = install_loop_engine(
    REPOSITORY_DIR, command_environment)
os.chdir(REPOSITORY_DIR)


# ------------------------------------------------------------
# 3. Diagnostics (offline, zero provider calls)
# ------------------------------------------------------------

doctor = run_command(
    [sys.executable, "-m", "loop_engine", "doctor"],
    cwd=REPOSITORY_DIR, env=command_environment)
STAGE_RECORD["commands"]["doctor"] = {"exit_code": doctor.returncode}

configure = run_command(
    [sys.executable, "-m", "loop_engine", "configure"],
    cwd=REPOSITORY_DIR, env=command_environment)
STAGE_RECORD["commands"]["configure"] = {"exit_code": configure.returncode}

finish_stage("offline")


# ------------------------------------------------------------
# 4. Preflight: one authorized provider probe, recorded after it runs
# ------------------------------------------------------------

preflight = {
    "record_type": "loop_engine_preflight/v1",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "attempt": RUN_STAMP,
    "providers": [
        probe_builtin_provider(
            "ollama_cloud", "cloud.default", PROBE_MODEL_ID, 70000,
            command_environment),
    ],
}

PREFLIGHT_FILE = PREFLIGHT_DIR / f"preflight-{RUN_STAMP}.json"
PREFLIGHT_FILE.write_text(
    json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
STAGE_RECORD["preflight_file"] = str(PREFLIGHT_FILE)
STAGE_RECORD["preflight_ok"] = any(
    item["ok"] for item in preflight["providers"])

print("\nPreflight summary:")
for item in preflight["providers"]:
    status = "OK " if item["ok"] else "FAIL"
    print(f"  [{status}] {item['provider']}: exit {item['exit_code']}; "
          f"{item['note']}")
print("Preflight record:", PREFLIGHT_FILE)

if not STAGE_RECORD["preflight_ok"]:
    write_stage_record("preflight")
    raise RuntimeError(
        "The single provider failed preflight; not starting a solve that "
        "cannot reach a model. Detail is in the preflight record.")

finish_stage("preflight")


# ------------------------------------------------------------
# 5. Task
# ------------------------------------------------------------

TASK = f"""
Build and verify a reproducible baseline solution for the supplied Kaggle
competition dataset ({COMPETITION}).

This is an execution task, not merely a high-level modeling plan.

Do not assume any file name, directory layout, or column name. The attached
input root is supplied as a source; the runtime states the admitted manifest
and its own reading of each file under runtime_facts, and core.source.inspect
admits exactly those paths.

Read source_roles in the runtime facts before deciding anything about the
data. It records what each supplied file was read to be and the evidence for
that reading. Where a path is listed as unresolved, inspect it and settle it
from the observed bytes rather than from its name. If what you observe
contradicts a recorded role, say so and act on the observation.

Decide the target, the identifier, the prediction field, the task type, and
the submission contract from the observed schemas: the values a field actually
holds, not the word in its header. A field whose values are labels is not a
continuous target, and the file that defines the submission contract fixes the
column order, the identifier order, and the value type. Check missing values,
duplicates, leakage, suspicious unique fields, and schema differences between
the training and prediction files.

Generated code runs in the workspace, not beside the source. Open each input
at the sandbox_paths value the runtime states for it, never at its admitted
manifest path.

Build a CPU-compatible preprocessing pipeline. Compare at least two reasonable
baseline models with reproducible three-fold cross-validation and an
appropriate local validation metric. Fit the selected model on all training
rows and create submission.csv matching the discovered submission contract
exactly, in its column order and identifier order.

Write solution.py and verification.py yourself, inside the assigned
workspace. Running them must produce submission.csv, metrics.json, report.md
and verification.json: declare those four as expected artifacts, never as
files you author. An output you typed is not an output you produced, and the
run refuses any path that appears as both. Every number in metrics.json and
report.md must come from the run, not from you.

Verify schema, row count, column order, identifier order, missing predictions,
infinite predictions, prediction type, and prediction range against the
discovered contract. Treat everything under {DATASET_DIR} as read-only. Do not submit anything to
Kaggle. Use fixed seeds and do not run a large hyperparameter search. The
environment has no Docker: generated code must run with the preinstalled
Python packages directly and must not use dependency-install network
commands.

Return COMPLETED_VERIFIED only after all required artifacts exist and all
verification checks pass.
""".strip()

TASK_FILE.write_text(TASK + "\n", encoding="utf-8")
print("\nTask file:", TASK_FILE)
print("Workspace:", WORKSPACE)


# ------------------------------------------------------------
# 6. Solve: Ollama only, exact model IO traced to stderr
# ------------------------------------------------------------

command = [
    sys.executable, "-m", "loop_engine", "solve",
    "--file", str(TASK_FILE),
    "--dataset", str(DATASET_DIR),
    "--workspace", str(WORKSPACE),
    "--runs-dir", str(RUNS_DIR),
    "--compile-provider", "ollama_cloud",
    "--provider-key-env", OLLAMA_KEY_ENV,
    "--model-route", "cloud.default",
    "--authorize-model-calls",
    "--allow-source-to-model",
    # Kaggle has no Docker: generated code runs as a host process and the
    # run record labels the weaker isolation.
    "--allow-local-execution",
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

STAGE_RECORD["commands"]["solve"] = {"exit_code": completed.returncode}
STAGE_RECORD["solve_stdout_record"] = str(stdout_log)
STAGE_RECORD["terminal_code"] = final_record.get("terminal_code")
STAGE_RECORD["solved"] = final_record.get("solved")
STAGE_RECORD["run_id"] = final_record.get("run_id")


# ------------------------------------------------------------
# 7. Save artifacts and summarize
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

finish_stage("solve")
