# ============================================================
# Loop Engine — Kaggle single-provider solve (tacticalengineering)
#
# ONE cell. Requires Kaggle secret: tacticalhat_kaggle_key
#
# Time budget: targets 4-6 hours max (wall clock), enforced by a
# subprocess deadline so the notebook stops honestly instead of
# hitting the Kaggle session limit.
#
# Output layout (all under /kaggle/working):
#   loop-engine-solutions/       best verified artifacts, versioned
#   loop-engine-logs/
#     preflight/                provider API check records
#     solve/                    full solve stdout records (per attempt)
#     run-history/              Loop Engine Run History dirs
#     summary/                  one-page human report per attempt
#     master/                   chronological master log + artifact index
#
# Based on loop-engine main @ a2f7102.
# ============================================================

from kaggle_secrets import UserSecretsClient
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from types import SimpleNamespace

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

import yaml


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

REPOSITORY_ARCHIVE_URL = (
    "https://github.com/alisonjieli-png/"
    "loop-engine/archive/refs/heads/main.zip"
)

REPOSITORY_DIR = Path("/kaggle/working/loop-engine-src")
DATASET_DIR = Path("/kaggle/input/competitions/playground-series-s6e9")

WORKING = Path("/kaggle/working")
LOGS_DIR = WORKING / "loop-engine-logs"
PREFLIGHT_DIR = LOGS_DIR / "preflight"
SOLVE_LOG_DIR = LOGS_DIR / "solve"
RUN_HISTORY_LOG_DIR = LOGS_DIR / "run-history"
SUMMARY_DIR = LOGS_DIR / "summary"
MASTER_DIR = LOGS_DIR / "master"
SOLUTIONS_DIR = WORKING / "loop-engine-solutions"

# tacticalengineering: direct-origin OpenAI-compatible API.
# DNS-only hostname serves a Cloudflare Origin CA certificate, so the
# endpoint declares tls_verification: skip (typed curl -k, scoped to
# exactly this endpoint). stream: auto self-orients to SSE if a proxy
# wall ever cuts a long generation.
TACTICAL_ENDPOINT = (
    "https://ai.tacticalengineering.net:6969/v1/chat/completions"
)
TACTICAL_MODEL = "gemma-4-coding-abliterated"
# gemma-4 published model output ceiling; verified live with a full
# 32768-token streamed generation against this origin.
TACTICAL_MAX_OUTPUT = 32768

# Wall-clock budget for the whole solve phase (seconds). 5 hours is the
# middle of the 4-6 hour target; the subprocess is killed honestly at the
# deadline and the run record is still saved.
SOLVE_DEADLINE_SECONDS = 5 * 60 * 60

# The Practitioner's own pass ceiling. This is an explicit owner-set
# work ceiling (allowed: the product sets none by default), sized so
# the escalation ladder and this ceiling together keep the run inside
# the wall-clock budget.
MAX_PASSES = 60

TASK_FILE = WORKING / "loop-engine-s6e9-task.md"
SETTINGS_FILE = WORKING / "loop-engine-providers.yaml"

RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def get_secret(client, name):
    """Read one required Kaggle secret without displaying its value."""
    value = client.get_secret(name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"Kaggle secret {name!r} is empty or unavailable. "
            "Create the secret and enable notebook access.")
    return value.strip()


def run_command(command, *, cwd=None, env=None, check=True,
                timeout=None):
    """Run one command without shell interpolation."""
    command = [str(part) for part in command]
    working_directory = Path(cwd or Path.cwd()).resolve()
    print(f"\n[{working_directory}]$ {shlex.join(command)}\n", flush=True)
    result = subprocess.run(
        command, cwd=str(working_directory), env=env,
        text=True, check=False, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command exited with status {result.returncode}: "
            f"{shlex.join(command)}")
    return result


def probe_endpoint_raw(name, url, key, model, max_tokens=32, timeout=90):
    """One direct OpenAI-style probe against the custom endpoint.

    Returns a typed record: ok, latency, provider-reported usage, or the
    exact failure. Never raises; the preflight record carries the result.
    """
    import ssl
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user",
                      "content": f"Reply with exactly: {name.upper()} OK"}],
        "max_tokens": max_tokens, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    })
    started = time.monotonic()
    try:
        # Origin serves a private CA; verification skip is the operator's
        # documented direct-origin policy for this host.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context))
        with opener.open(req, timeout=timeout) as r:
            body = json.loads(r.read())
        elapsed = time.monotonic() - started
        usage = body.get("usage") or {}
        return {
            "endpoint": name, "ok": True,
            "elapsed_seconds": round(elapsed, 2),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "usage_accounting_complete": bool(
                usage.get("prompt_tokens")
                or usage.get("completion_tokens")),
            "content_preview": str(
                (body.get("choices") or [{}])[0]
                .get("message", {}).get("content", ""))[:80],
        }
    except Exception as exc:
        return {
            "endpoint": name, "ok": False,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
        }


def log_line(message):
    """Append one line to the master log and echo it."""
    MASTER_LOG.write_text(
        MASTER_LOG.read_text(encoding="utf-8") + message + "\n",
        encoding="utf-8")
    print(message, flush=True)


# ------------------------------------------------------------
# 0. Set up the log hierarchy
# ------------------------------------------------------------

for directory in (LOGS_DIR, PREFLIGHT_DIR, SOLVE_LOG_DIR,
                  RUN_HISTORY_LOG_DIR, SUMMARY_DIR, MASTER_DIR,
                  SOLUTIONS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

MASTER_LOG = MASTER_DIR / f"master-{RUN_STAMP}.log"
MASTER_LOG.write_text(
    f"Loop Engine Kaggle run {RUN_STAMP}\n"
    f"Provider: tacticalengineering only\n"
    f"Wall-clock budget: {SOLVE_DEADLINE_SECONDS // 3600}h\n\n",
    encoding="utf-8")

log_line(f"Log hierarchy root: {LOGS_DIR}")


# ------------------------------------------------------------
# 1. Load the Kaggle secret
# ------------------------------------------------------------

tactical_key = get_secret(
    UserSecretsClient(), "tacticalhat_kaggle_key")

# Strip every other provider variable so this run is single-provider.
for name in (
        "OLLAMA_API_KEY", "MISTRAL_API_KEY", "LOOP_ENGINE_ENDPOINTS",
        "TACTICALHAT_API_KEY", "OPENWEBUI_API_KEY",
        "PRIVATE_OPENWEBUI_API_KEY", "OPENROUTER_API_KEY",
        "OPENCODE_ZEN_API_KEY", "OPENCODE_GO_API_KEY"):
    os.environ.pop(name, None)

os.environ["TACTICAL_API_KEY"] = tactical_key
command_environment = os.environ.copy()
log_line("TACTICAL_API_KEY configured: True")


# ------------------------------------------------------------
# 2. Clean old run debris so the disk never fills again
# ------------------------------------------------------------

if REPOSITORY_DIR.exists():
    log_line(f"Removing previous checkout: {REPOSITORY_DIR}")
    shutil.rmtree(REPOSITORY_DIR, ignore_errors=True)
for stale in WORKING.glob("loop-engine-s6e9-solve-*"):
    shutil.rmtree(stale, ignore_errors=True)
for stale in WORKING.glob("loop-engine-s6e9-result-*.json"):
    stale.unlink(missing_ok=True)
# Keep solution versions and old logs; they are the troubleshooting record.


# ------------------------------------------------------------
# 3. Download and install current main
# ------------------------------------------------------------

temp_dir = Path("/kaggle/temp/loop-engine-setup")
if temp_dir.exists():
    shutil.rmtree(temp_dir)
temp_dir.mkdir(parents=True, exist_ok=True)
archive_path = temp_dir / "loop-engine-main.zip"

log_line("Downloading Loop Engine main...")
download_request = urllib.request.Request(
    REPOSITORY_ARCHIVE_URL,
    headers={"User-Agent": "Kaggle-Loop-Engine-Setup",
             "Accept": "application/zip"})
with urllib.request.urlopen(download_request, timeout=300) as response:
    with archive_path.open("wb") as output_file:
        shutil.copyfileobj(response, output_file)

if not zipfile.is_zipfile(archive_path):
    raise RuntimeError(f"Downloaded file is not a ZIP archive: {archive_path}")
log_line(
    f"Repository archive downloaded: "
    f"{archive_path.stat().st_size / (1024 ** 2):.1f} MB")

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

for required in (
        REPOSITORY_DIR / "pyproject.toml",
        REPOSITORY_DIR / "src" / "loop_engine"):
    if not required.exists():
        raise RuntimeError(f"Repository input missing: {required}")

run_command(
    [sys.executable, "-m", "pip", "install",
     "--upgrade", "--editable", str(REPOSITORY_DIR)],
    cwd=REPOSITORY_DIR, env=command_environment)

os.chdir(REPOSITORY_DIR)
log_line(f"Repository root: {REPOSITORY_DIR}")


# ------------------------------------------------------------
# 4. Offline diagnostics
# ------------------------------------------------------------

run_command(
    [sys.executable, "-m", "loop_engine", "doctor"],
    cwd=REPOSITORY_DIR, env=command_environment)

run_command(
    [sys.executable, "-m", "loop_engine", "configure"],
    cwd=REPOSITORY_DIR, env=command_environment)


# ------------------------------------------------------------
# 5. PREFLIGHT: test the tacticalengineering API before the solve
# ------------------------------------------------------------

log_line("\nPREFLIGHT: testing the tacticalengineering API")

preflight = {
    "record_type": "loop_engine_preflight/v1",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "attempt": RUN_STAMP,
    "providers": [],
}

tactical_result = probe_endpoint_raw(
    "tacticalengineering", TACTICAL_ENDPOINT, tactical_key, TACTICAL_MODEL)
preflight["providers"].append({
    "provider": "tacticalengineering",
    "probe_kind": "direct_openai_chat",
    "endpoint": TACTICAL_ENDPOINT,
    "model": TACTICAL_MODEL,
    "tls_verification": "skip",
    "stream": "auto",
    **tactical_result,
})

PREFLIGHT_FILE = PREFLIGHT_DIR / f"preflight-{RUN_STAMP}.json"
PREFLIGHT_FILE.write_text(
    json.dumps(preflight, indent=2) + "\n", encoding="utf-8")

status = "OK" if tactical_result.get("ok") else "FAIL"
detail = (
    f"usage {tactical_result.get('prompt_tokens')}in/"
    f"{tactical_result.get('completion_tokens')}out "
    f"in {tactical_result.get('elapsed_seconds')}s"
    if tactical_result.get("ok")
    else str(tactical_result.get("error", "failed"))[:120])
log_line(f"  [{status}] tacticalengineering: {detail}")
log_line(f"  Preflight record: {PREFLIGHT_FILE}")

if not tactical_result.get("ok"):
    raise RuntimeError(
        "The single provider failed preflight; not spending the time "
        "budget on a solve that cannot reach a model. Fix the endpoint "
        "and rerun. Detail is in the preflight record.")


# ------------------------------------------------------------
# 6. Runtime settings: tacticalengineering only
# ------------------------------------------------------------

settings = {
    "version": 1,
    "models": {
        "default_thinking_power": "medium",
        "providers": [
            {
                "id": "tacticalengineering",
                "kind": "custom",
                "enabled": True,
                "credential_env": "TACTICAL_API_KEY",
                "endpoint": TACTICAL_ENDPOINT,
                "model": TACTICAL_MODEL,
                "wire": "openai",
                "locality": "cloud",
                "stream": "auto",
                "tls_verification": "skip",
                "maximum_output_tokens": TACTICAL_MAX_OUTPUT,
                "maximum_output_source": (
                    "gemma-4 published model output ceiling; verified live "
                    "with a full 32768-token streamed generation against "
                    "this origin"),
                "counts_as_evidence": True,
                "auth_scheme": "bearer",
                "headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
                },
            },
        ],
    },
}

settings_text = yaml.safe_dump(settings, sort_keys=False, allow_unicode=True)
if tactical_key in settings_text:
    raise RuntimeError(
        "Refusing to serialize an API key into the settings file.")
SETTINGS_FILE.write_text(settings_text, encoding="utf-8")
log_line(f"Runtime settings: {SETTINGS_FILE}")


# ------------------------------------------------------------
# 7. Confirm the route plan before spending the time budget
# ------------------------------------------------------------

source_root = REPOSITORY_DIR / "src"
if str(source_root) not in sys.path:
    sys.path.insert(0, str(source_root))

from loop_engine.core.settings_loader import load_runtime_settings
from loop_engine.solve_cli import _solve_route_plan

gateway = (
    load_runtime_settings(str(SETTINGS_FILE))
    .settings.build_gateway(command_environment))

if set(gateway.providers) != {"tacticalengineering"}:
    raise RuntimeError(
        "Expected exactly tacticalengineering, found: "
        + ", ".join(sorted(gateway.providers)))

# Single provider: no failover routes, so build the plan directly from
# the one route and confirm it resolves.
route_plan = _solve_route_plan(
    SimpleNamespace(allow_model_failover=True, model_id=""),
    gateway, "custom.tacticalengineering")

log_line(f"\nRoute plan ({len(route_plan)} route(s)):")
for index, route_name in enumerate(route_plan, start=1):
    route = gateway.registry.get(route_name)
    log_line(
        f"  {index}. {route.name} -> {route.provider} / {route.model}")

if not route_plan:
    raise RuntimeError(
        "The tacticalengineering route did not resolve into the plan.")


# ------------------------------------------------------------
# 8. Task
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
log_line(f"Task file: {TASK_FILE}")


# ------------------------------------------------------------
# 9. Solve: tacticalengineering only, with a hard wall-clock deadline
# ------------------------------------------------------------

WORKSPACE = WORKING / f"loop-engine-s6e9-solve-{RUN_STAMP}"
RUNS_DIR = RUN_HISTORY_LOG_DIR  # Run History lives under logs/run-history

solve_command = [
    sys.executable, "-m", "loop_engine", "solve",
    "--file", str(TASK_FILE),
    "--dataset", str(DATASET_DIR),
    "--workspace", str(WORKSPACE),
    "--runs-dir", str(RUNS_DIR),
    "--settings-file", str(SETTINGS_FILE),
    "--compile-provider", "tacticalengineering",
    "--provider-key-env", "TACTICAL_API_KEY",
    "--model-route", "custom.tacticalengineering",
    "--authorize-model-calls",
    "--allow-source-to-model",
    "--no-default-extensions",
    # Owner-set pass ceiling sized with the wall-clock budget. The
    # non-progress escalation ladder (soft reset -> cold restart ->
    # honest stop) still bounds stuck runs earlier.
    "--max-passes", str(MAX_PASSES),
    # The exact prompt and raw model output trace to stderr BY DEFAULT.
    # stderr is captured to the solve log; see the tee below.
    "--format", "json",
]

log_line(f"\nRunning solve with a "
         f"{SOLVE_DEADLINE_SECONDS // 3600}-hour deadline:")
log_line(shlex.join(solve_command) + "\n")

SOLVE_STDOUT_LOG = SOLVE_LOG_DIR / f"solve-stdout-{RUN_STAMP}.jsonl"
SOLVE_STDERR_LOG = SOLVE_LOG_DIR / f"solve-stderr-{RUN_STAMP}.log"

import threading

process = subprocess.Popen(
    solve_command,
    cwd=str(REPOSITORY_DIR),
    env=command_environment,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=1,
)

# Stream stderr (progress + exact model IO) into the notebook AND the
# solve log, so live troubleshooting and post-hoc debugging use the
# same record.
def tee_stderr():
    with SOLVE_STDERR_LOG.open("w", encoding="utf-8") as stderr_file:
        for line in process.stderr:
            stderr_file.write(line)
            stderr_file.flush()
            print(line, end="", flush=True)

stderr_thread = threading.Thread(target=tee_stderr, daemon=True)
stderr_thread.start()

deadline_hit = False
try:
    stdout_text = process.communicate(
        timeout=SOLVE_DEADLINE_SECONDS)[0]
except subprocess.TimeoutExpired:
    deadline_hit = True
    process.kill()
    stdout_text, _ = process.communicate()
    log_line(
        f"\nDEADLINE: the solve did not finish within "
        f"{SOLVE_DEADLINE_SECONDS // 3600} hours and was stopped. "
        "Everything completed so far is saved below.")
stderr_thread.join(timeout=30)

raw_output = (stdout_text or "").strip()
SOLVE_STDOUT_LOG.write_text(
    raw_output + ("\n" if raw_output else ""), encoding="utf-8")

exit_note = "deadline-stopped" if deadline_hit else (
    f"exit {process.returncode}")
log_line(f"Solve finished ({exit_note}).")
log_line(f"  Solve stdout record: {SOLVE_STDOUT_LOG}")
log_line(f"  Solve stderr trace:  {SOLVE_STDERR_LOG}")

try:
    final_record = json.loads(raw_output) if raw_output else {}
except json.JSONDecodeError:
    final_record = {}
    log_line(
        "  NOTE: final output was not one JSON object; saved raw output "
        "for inspection.")


# ------------------------------------------------------------
# 10. Save the best solution artifacts, versioned
# ------------------------------------------------------------

# Solutions are versioned by run stamp. "Best" is the latest attempt that
# reached COMPLETED_VERIFIED; earlier attempts stay for comparison.
attempt_dir = SOLUTIONS_DIR / f"attempt-{RUN_STAMP}"
attempt_dir.mkdir(parents=True, exist_ok=True)

solved = bool(final_record.get("solved"))
solved_workspace = Path(
    str(final_record.get("workspace") or WORKSPACE))

artifacts_copied = []
EXPECTED_FILES = (
    "solution.py", "submission.csv", "metrics.json",
    "report.md", "verification.json",
)

for expected in EXPECTED_FILES:
    for found in solved_workspace.glob(f"**/{expected}"):
        if found.name == expected:
            destination = attempt_dir / found.name
            shutil.copy2(found, destination)
            artifacts_copied.append({
                "file": found.name,
                "bytes": destination.stat().st_size,
                "source": str(found),
                "saved_to": str(destination),
            })

for artifact in final_record.get("artifacts") or []:
    artifact_path = Path(str(artifact.get("path", "")))
    if artifact_path.is_file() and artifact_path.name in EXPECTED_FILES:
        destination = attempt_dir / artifact_path.name
        if not destination.exists():
            shutil.copy2(artifact_path, destination)
            artifacts_copied.append({
                "file": artifact_path.name,
                "bytes": destination.stat().st_size,
                "verified": bool(artifact.get("verified")),
                "source": str(artifact_path),
                "saved_to": str(destination),
            })

# Update the pointer to the best attempt: a solved attempt always wins;
# otherwise the most recent attempt with a submission.csv wins.
BEST_POINTER = SOLUTIONS_DIR / "BEST.txt"
best_reason = ""
if solved:
    best_reason = f"solved at {RUN_STAMP}"
    BEST_POINTER.write_text(
        f"attempt-{RUN_STAMP}\nreason: {best_reason}\n",
        encoding="utf-8")
else:
    has_submission = any(
        item["file"] == "submission.csv" for item in artifacts_copied)
    previous_best = BEST_POINTER.read_text(
        encoding="utf-8").splitlines()[0].strip() \
        if BEST_POINTER.exists() else ""
    if has_submission and previous_best:
        best_reason = (
            f"kept previous best ({previous_best}); this attempt "
            "produced a submission but did not verify")
        BEST_POINTER.write_text(
            previous_best + f"\nreason: {best_reason}\n", encoding="utf-8")
    elif has_submission and not previous_best:
        best_reason = "first attempt with a submission file"
        BEST_POINTER.write_text(
            f"attempt-{RUN_STAMP}\nreason: {best_reason}\n",
            encoding="utf-8")
    else:
        best_reason = "no submission produced; no best pointer change"

# Artifact index for quick troubleshooting.
ARTIFACT_INDEX = SOLUTIONS_DIR / "index.json"
index_rows = []
if ARTIFACT_INDEX.exists():
    try:
        index_rows = json.loads(ARTIFACT_INDEX.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        index_rows = []
index_rows.append({
    "attempt": RUN_STAMP,
    "solved": solved,
    "terminal_code": final_record.get("terminal_code", ""),
    "deadline_hit": deadline_hit,
    "best_reason": best_reason,
    "artifacts": artifacts_copied,
})
ARTIFACT_INDEX.write_text(
    json.dumps(index_rows, indent=2) + "\n", encoding="utf-8")

log_line(f"\nSolution artifacts: {attempt_dir}")
for item in artifacts_copied:
    log_line(
        f"  {item['file']} ({item['bytes']} bytes)")
log_line(f"Best pointer: {BEST_POINTER} ({best_reason})")
log_line(f"Artifact index: {ARTIFACT_INDEX}")


# ------------------------------------------------------------
# 11. One-page summary for this attempt
# ------------------------------------------------------------

summary_lines = [
    f"# Solve attempt {RUN_STAMP} (tacticalengineering only)",
    "",
    f"- Terminal code: **{final_record.get('terminal_code', 'UNKNOWN')}**",
    f"- Solved: **{solved}**",
    f"- Deadline hit: {deadline_hit}",
    f"- Model calls: {final_record.get('model_calls')}",
    f"- Loops: {final_record.get('loop_count')}",
    f"- Elapsed: {final_record.get('elapsed_seconds')}s",
    f"- Run ID: {final_record.get('run_id', '')}",
    f"- Best pointer: {best_reason}",
    "",
    "## Verification",
    "",
    f"- Passed: {(final_record.get('verification') or {}).get('passed')}",
]
verification = final_record.get("verification") or {}
for gap in verification.get("remaining_gaps") or []:
    summary_lines.append(f"- Gap: {gap[:200]}")
for artifact in final_record.get("artifacts") or []:
    summary_lines.append(
        f"- Artifact: {artifact.get('path')} "
        f"verified={artifact.get('verified')}")
for limitation in final_record.get("limitations") or []:
    summary_lines.append(f"- Limitation: {limitation[:200]}")

summary_lines += [
    "",
    "## Files",
    "",
    f"- Attempt artifacts: `{attempt_dir}`",
    f"- Solve stdout: `{SOLVE_STDOUT_LOG}`",
    f"- Solve stderr (exact model IO): `{SOLVE_STDERR_LOG}`",
    f"- Preflight: `{PREFLIGHT_FILE}`",
    f"- Run History: `{RUNS_DIR}`",
    f"- Master log: `{MASTER_LOG}`",
]
run_id = final_record.get("run_id")
if run_id:
    summary_lines += [
        "",
        "```bash",
        f"loop-engine report {run_id} --runs-dir {RUNS_DIR}",
        f"loop-engine studio --port 0 --runs-dir {RUNS_DIR}",
        "```",
    ]

SUMMARY_FILE = SUMMARY_DIR / f"summary-{RUN_STAMP}.md"
SUMMARY_FILE.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
log_line(f"\nSummary saved: {SUMMARY_FILE}")

print("\n" + "=" * 72)
print(SUMMARY_FILE.read_text(encoding="utf-8"))
print("=" * 72)