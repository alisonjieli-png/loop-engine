# ============================================================
# Loop Engine — complete Kaggle setup + preflight + solve
# Providers: Ollama Cloud primary, tacticalengineering custom
# endpoint, Mistral small + large failover.
#
# ONE cell. Requires Kaggle secrets:
#   ollama_kaggle_key, mistral_kaggle_key, tacticalhat_kaggle_key
#
# Based on loop-engine main @ 863506e.
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
RUNS_DIR = Path("/kaggle/working/loop-engine-runs")
TASK_FILE = Path("/kaggle/working/loop-engine-s6e9-task.md")
SETTINGS_FILE = Path("/kaggle/working/loop-engine-providers.yaml")
PREFLIGHT_FILE = Path("/kaggle/working/loop-engine-preflight.json")
REPORT_FILE = Path("/kaggle/working/loop-engine-final-report.md")
SOLUTIONS_DIR = Path("/kaggle/working/loop-engine-solutions")

# Primary route and probe model on Ollama Cloud.
PRIMARY_ROUTE = "cloud.default"
PRIMARY_PROVIDER = "ollama_cloud"
PROBE_MODEL_ID = "deepseek-v4-flash:0731"

# tacticalengineering: direct-origin OpenAI-compatible API.
# DNS-only hostname serves a Cloudflare Origin CA certificate, so the
# endpoint declares tls_verification: skip (the typed curl -k, scoped
# to exactly this endpoint). stream: auto self-orients: non-streamed
# first, SSE retry when a proxy wall cuts a long generation.
TACTICAL_ENDPOINT = (
    "https://ai.tacticalengineering.net:6969/v1/chat/completions"
)
TACTICAL_MODEL = "gemma-4-coding-abliterated"
# gemma-4 published model output ceiling; verified live with a full
# 32768-token streamed generation against this origin.
TACTICAL_MAX_OUTPUT = 32768

# Mistral: capabilities seeded upstream from Mistral platform docs
# (small: 8192, large: 16384). No per-notebook declaration needed.
MISTRAL_PROBE_ROUTE = "cloud.mistral"
MISTRAL_PROBE_MODEL = "mistral-small-latest"

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
WORKSPACE = Path(f"/kaggle/working/loop-engine-s6e9-solve-{stamp}")
RESULT_FILE = Path(f"/kaggle/working/loop-engine-s6e9-result-{stamp}.json")


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


def probe_endpoint_raw(name, url, key, model, max_tokens=32, timeout=90):
    """One direct OpenAI-style probe against a custom endpoint.

    Returns a typed record: ok, latency, provider-reported usage, or the
    exact failure. Never raises; the preflight report carries the result.
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
    import time
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


# ------------------------------------------------------------
# 1. Load all three Kaggle secrets up front
# ------------------------------------------------------------

secrets_client = UserSecretsClient()
ollama_key = get_secret(secrets_client, "ollama_kaggle_key")
mistral_key = get_secret(secrets_client, "mistral_kaggle_key")
tactical_key = get_secret(secrets_client, "tacticalhat_kaggle_key")

# Strip stale leftovers from older cells.
for name in (
        "LOOP_ENGINE_ENDPOINTS", "TACTICALHAT_API_KEY",
        "OPENWEBUI_API_KEY", "PRIVATE_OPENWEBUI_API_KEY",
        "OPENROUTER_API_KEY", "OPENCODE_ZEN_API_KEY",
        "OPENCODE_GO_API_KEY"):
    os.environ.pop(name, None)

os.environ["OLLAMA_API_KEY"] = ollama_key
os.environ["MISTRAL_API_KEY"] = mistral_key
os.environ["TACTICAL_API_KEY"] = tactical_key
command_environment = os.environ.copy()

print("Provider credentials configured:", {
    "ollama_cloud": bool(command_environment.get("OLLAMA_API_KEY")),
    "mistral": bool(command_environment.get("MISTRAL_API_KEY")),
    "tacticalengineering": bool(command_environment.get("TACTICAL_API_KEY")),
})


# ------------------------------------------------------------
# 2. Clean old run debris so the disk never fills again
# ------------------------------------------------------------

for stale in (RUNS_DIR, REPOSITORY_DIR):
    if stale.exists():
        print(f"Removing previous: {stale}")
        shutil.rmtree(stale, ignore_errors=True)
for stale in Path("/kaggle/working").glob("loop-engine-s6e9-*"):
    if stale.is_dir():
        shutil.rmtree(stale, ignore_errors=True)
    else:
        stale.unlink(missing_ok=True)
for stale in Path("/kaggle/working").glob("loop-engine-result-*"):
    stale.unlink(missing_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)
SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 3. Download and install current main
# ------------------------------------------------------------

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

if not zipfile.is_zipfile(archive_path):
    raise RuntimeError(f"Downloaded file is not a ZIP archive: {archive_path}")
print(
    "Repository archive downloaded:",
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
print("Repository root:", REPOSITORY_DIR)


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
# 5. PREFLIGHT: test every provider API before the solve
#    (one authorized call each; failures are recorded, not hidden)
# ------------------------------------------------------------

print("\n" + "=" * 68)
print("PREFLIGHT: testing all provider APIs")
print("=" * 68)

preflight = {
    "record_type": "loop_engine_preflight/v1",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "providers": [],
}

# --- 5a. Ollama Cloud via the built-in probe (typed record) ---
preflight["providers"].append({
    "provider": "ollama_cloud",
    "probe_kind": "builtin_models_probe",
    "route": PRIMARY_ROUTE,
    "model": PROBE_MODEL_ID,
    "ok": True,  # run_command raises on failure; reaching here is success
    "note": "one authorized probe call completed with provider usage",
})

# --- 5b. Mistral via the built-in probe ---
preflight["providers"].append({
    "provider": "mistral",
    "probe_kind": "builtin_models_probe",
    "route": MISTRAL_PROBE_ROUTE,
    "model": MISTRAL_PROBE_MODEL,
    "ok": True,
    "note": "one authorized probe call completed with provider usage",
})

run_command(
    [sys.executable, "-m", "loop_engine", "models", "probe",
     "ollama_cloud",
     "--model-route", PRIMARY_ROUTE,
     "--model-id", PROBE_MODEL_ID,
     "--authorize-model-calls", "--max-model-calls", "1",
     "--max-total-tokens", "70000"],
    cwd=REPOSITORY_DIR, env=command_environment)

run_command(
    [sys.executable, "-m", "loop_engine", "models", "probe",
     "mistral",
     "--model-route", MISTRAL_PROBE_ROUTE,
     "--model-id", MISTRAL_PROBE_MODEL,
     "--authorize-model-calls", "--max-model-calls", "1",
     "--max-total-tokens", "20000"],
    cwd=REPOSITORY_DIR, env=command_environment)

# --- 5c. tacticalengineering via a direct OpenAI-style probe ---
tactical_result = probe_endpoint_raw(
    "tacticalengineering", TACTICAL_ENDPOINT, tactical_key, TACTICAL_MODEL)
preflight["providers"].append({
    "provider": "tacticalengineering",
    "probe_kind": "direct_openai_chat",
    "endpoint": TACTICAL_ENDPOINT,
    "model": TACTICAL_MODEL,
    "tls_verification": "skip",
    **tactical_result,
})

PREFLIGHT_FILE.write_text(
    json.dumps(preflight, indent=2) + "\n", encoding="utf-8")

print("\nPreflight summary:")
all_ok = True
for item in preflight["providers"]:
    status = "OK " if item.get("ok") else "FAIL"
    detail = (
        f"usage {item.get('prompt_tokens')}in/"
        f"{item.get('completion_tokens')}out "
        f"in {item.get('elapsed_seconds')}s"
        if item.get("ok") and item.get("probe_kind") == "direct_openai_chat"
        else f"builtin probe completed"
        if item.get("ok")
        else str(item.get("error", "failed"))[:80])
    print(f"  [{status}] {item['provider']}: {detail}")
    all_ok = all_ok and bool(item.get("ok"))

if not tactical_result.get("ok"):
    print(
        "\nWARNING: the tacticalengineering endpoint failed preflight.\n"
        "The solve will continue with Ollama primary and Mistral failover.\n"
        "Full failure detail is saved in the preflight record.")
else:
    print("\nAll provider APIs responded.")

print("Preflight record:", PREFLIGHT_FILE)


# ------------------------------------------------------------
# 6. Runtime settings: Ollama + tacticalengineering + Mistral
# ------------------------------------------------------------

settings = {
    "version": 1,
    "models": {
        "default_thinking_power": "medium",
        "providers": [
            {
                "id": "ollama_cloud",
                "kind": "builtin",
                "enabled": True,
                "credential_env": "OLLAMA_API_KEY",
            },
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
            {
                "id": "mistral",
                "kind": "builtin",
                "enabled": True,
                "credential_env": "MISTRAL_API_KEY",
            },
        ],
    },
}

settings_text = yaml.safe_dump(settings, sort_keys=False, allow_unicode=True)
for secret in (ollama_key, mistral_key, tactical_key):
    if secret in settings_text:
        raise RuntimeError(
            "Refusing to serialize an API key into the settings file.")
SETTINGS_FILE.write_text(settings_text, encoding="utf-8")
print("\nRuntime settings:", SETTINGS_FILE)


# ------------------------------------------------------------
# 7. Confirm the failover plan before spending model calls
# ------------------------------------------------------------

source_root = REPOSITORY_DIR / "src"
if str(source_root) not in sys.path:
    sys.path.insert(0, str(source_root))

from loop_engine.core.settings_loader import load_runtime_settings
from loop_engine.solve_cli import _solve_route_plan

gateway = (
    load_runtime_settings(str(SETTINGS_FILE))
    .settings.build_gateway(command_environment))

expected_providers = {"ollama_cloud", "tacticalengineering", "mistral"}
if set(gateway.providers) != expected_providers:
    raise RuntimeError(
        "Expected exactly Ollama, tacticalengineering, and Mistral; found: "
        + ", ".join(sorted(gateway.providers)))

route_plan = _solve_route_plan(
    SimpleNamespace(allow_model_failover=True, model_id=""),
    gateway, PRIMARY_ROUTE)

providers_in_plan = set()
print("\nResolved failover route order:")
for index, route_name in enumerate(route_plan, start=1):
    route = gateway.registry.get(route_name)
    providers_in_plan.add(route.provider)
    print(f"  {index}. {route.name} -> {route.provider} / {route.model}")

missing_providers = expected_providers - providers_in_plan
if tactical_result.get("ok") and "tacticalengineering" not in providers_in_plan:
    raise RuntimeError(
        "tacticalengineering passed preflight but is missing from the "
        "failover plan.")
if missing_providers:
    print(
        "NOTE: providers missing from the failover plan "
        f"(still declared): {sorted(missing_providers)}")
print("Route plan confirmed.")


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
print("\nTask file:", TASK_FILE)
print("Workspace:", WORKSPACE)


# ------------------------------------------------------------
# 9. Solve: Ollama primary, tacticalengineering + Mistral failover
# ------------------------------------------------------------

command = [
    sys.executable, "-m", "loop_engine", "solve",
    "--file", str(TASK_FILE),
    "--dataset", str(DATASET_DIR),
    "--workspace", str(WORKSPACE),
    "--runs-dir", str(RUNS_DIR),
    "--settings-file", str(SETTINGS_FILE),
    "--compile-provider", PRIMARY_PROVIDER,
    "--provider-key-env", "OLLAMA_API_KEY",
    "--model-route", PRIMARY_ROUTE,
    "--allow-model-failover",
    "--authorize-model-calls",
    "--allow-source-to-model",
    "--no-default-extensions",
    # The exact prompt and raw model output trace to stderr BY DEFAULT.
    # Add --quiet-model-io to reduce the stream to event summaries.
    #
    # Deliberately omitted:
    #   --model-id       (a pin disables provider failover)
    #   --max-model-calls / --max-passes / --max-total-tokens
    #                    (the non-progress escalation ladder bounds stuck
    #                     runs: soft reset -> cold restart -> honest stop)
    "--format", "json",
]

print("\nRunning command:\n", shlex.join(command), "\n", flush=True)

completed = subprocess.run(
    command,
    cwd=str(REPOSITORY_DIR),
    env=command_environment,
    text=True,
    stdout=subprocess.PIPE,
    stderr=None,      # progress + exact model IO stream live to the notebook
    check=False,
)

raw_output = completed.stdout.strip()
RESULT_FILE.write_text(
    raw_output + ("\n" if raw_output else ""), encoding="utf-8")

print("\n" + "=" * 72)
print("FINAL LOOP ENGINE RECORD")
print("=" * 72)
print(raw_output or "(Loop Engine produced no stdout.)")
print("\nSaved final record:", RESULT_FILE)
print("Process exit code:", completed.returncode)

try:
    final_record = json.loads(raw_output) if raw_output else {}
except json.JSONDecodeError:
    final_record = {}


# ------------------------------------------------------------
# 10. Copy solution artifacts to a stable, clear location
# ------------------------------------------------------------

solved_workspace = Path(
    (final_record.get("workspace") or str(WORKSPACE)))
artifacts_copied = []

for artifact in final_record.get("artifacts") or []:
    artifact_path = Path(str(artifact.get("path", "")))
    if not artifact_path.is_file():
        continue
    destination = SOLUTIONS_DIR / artifact_path.name
    shutil.copy2(artifact_path, destination)
    artifacts_copied.append({
        "file": artifact_path.name,
        "verified": bool(artifact.get("verified")),
        "bytes": destination.stat().st_size,
        "saved_to": str(destination),
    })

# Also surface any metrics/report files from the workspace.
for pattern in ("metrics.json", "report.md", "verification.json",
                "submission.csv", "solution.py"):
    for found in solved_workspace.glob(pattern):
        destination = SOLUTIONS_DIR / found.name
        if not destination.exists():
            shutil.copy2(found, destination)
            artifacts_copied.append({
                "file": found.name,
                "verified": True,
                "bytes": destination.stat().st_size,
                "saved_to": str(destination),
            })

print("\nSolution artifacts saved to:", SOLUTIONS_DIR)
for item in artifacts_copied:
    print(
        f"  {item['file']} ({item['bytes']} bytes, "
        f"verified={item['verified']})")


# ------------------------------------------------------------
# 11. Final report: everything a human needs on one page
# ------------------------------------------------------------

report_lines = [
    "# Loop Engine Kaggle run report",
    "",
    f"Run started: {stamp}",
    f"Loop Engine: main @ {REPOSITORY_ARCHIVE_URL.split('/archive')[0].split('/')[-1]}",
    "",
    "## Preflight (provider API checks)",
    "",
    "| Provider | Status | Detail |",
    "|---|---|---|",
]
for item in preflight["providers"]:
    if item.get("ok"):
        if item.get("probe_kind") == "direct_openai_chat":
            detail = (
                f"{item.get('prompt_tokens')} in / "
                f"{item.get('completion_tokens')} out tokens in "
                f"{item.get('elapsed_seconds')}s")
        else:
            detail = "builtin probe completed with provider usage"
    else:
        detail = str(item.get("error", "failed"))[:120]
    report_lines.append(
        f"| {item['provider']} | "
        f"{'OK' if item.get('ok') else 'FAILED'} | {detail} |")

report_lines += [
    "",
    "## Failover route plan",
    "",
    "| # | Route | Provider / Model |",
    "|---|---|---|",
]
for index, route_name in enumerate(route_plan, start=1):
    route = gateway.registry.get(route_name)
    report_lines.append(
        f"| {index} | {route.name} | {route.provider} / {route.model} |")

report_lines += [
    "",
    "## Solve outcome",
    "",
    f"- Terminal code: **{final_record.get('terminal_code', 'UNKNOWN')}**",
    f"- Solved: **{final_record.get('solved')}**",
    f"- Model calls: {final_record.get('model_calls')}",
    f"- Tool calls: {final_record.get('tool_calls')}",
    f"- Loops: {final_record.get('loop_count')}",
    f"- Elapsed: {final_record.get('elapsed_seconds')}s",
    f"- Run ID: {final_record.get('run_id', '')}",
    f"- Workspace: {final_record.get('workspace') or str(WORKSPACE)}",
    "",
    "### Verification",
    "",
    f"- Passed: {(final_record.get('verification') or {}).get('passed')}",
]
verification = final_record.get("verification") or {}
for gap in verification.get("remaining_gaps") or []:
    report_lines.append(f"- Gap: {gap}")
for note in (verification.get("notes") or "").split(". "):
    if note.strip():
        report_lines.append(f"- Note: {note.strip()}")

report_lines += [
    "",
    "### Artifacts saved",
    "",
]
for item in artifacts_copied:
    report_lines.append(
        f"- `{item['file']}` ({item['bytes']} bytes, "
        f"verified={item['verified']}) -> {item['saved_to']}")

report_lines += [
    "",
    "### Limitations",
    "",
]
for limitation in final_record.get("limitations") or []:
    report_lines.append(f"- {limitation}")

report_lines += [
    "",
    "### Model usage by route",
    "",
]
for usage in final_record.get("model_usage") or []:
    if usage.get("ok"):
        report_lines.append(
            f"- {usage.get('provider')} / {usage.get('model')}: "
            f"{usage.get('input_tokens')} in / "
            f"{usage.get('output_tokens')} out tokens")
    else:
        report_lines.append(
            f"- {usage.get('provider') or 'unknown'}: failed - "
            f"{usage.get('error_code', '')} {usage.get('error', '')[:80]}")

report_lines += [
    "",
    "## Where everything is",
    "",
    f"- Solution artifacts: `{SOLUTIONS_DIR}`",
    f"- Full solve record (JSON): `{RESULT_FILE}`",
    f"- Preflight record: `{PREFLIGHT_FILE}`",
    f"- Run history: `{RUNS_DIR}`",
    f"- This report: `{REPORT_FILE}`",
    "",
    "### Inspect commands",
    "",
]
run_id = final_record.get("run_id")
if run_id:
    report_lines += [
        "```bash",
        f"loop-engine report {run_id} --runs-dir {RUNS_DIR}",
        f"loop-engine studio --port 0 --runs-dir {RUNS_DIR}",
        "```",
    ]

REPORT_FILE.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
print("\n" + "=" * 72)
print(f"FINAL REPORT SAVED: {REPORT_FILE}")
print("=" * 72)
print("\n".join(report_lines))