# ============================================================
# Loop Engine - complete Kaggle setup + preflight + solve
# Providers: Ollama Cloud primary, tacticalengineering custom
# endpoint, Mistral small + large failover.
#
# ONE cell. Requires Kaggle secrets:
#   ollama_kaggle_key, mistral_kaggle_key, tacticalhat_kaggle_key
#
# Output layout (under the Kaggle working directory):
#   loop-engine-solutions/attempt-<stamp>/   verified artifacts
#   loop-engine-logs/
#     preflight/                provider API check record
#     solve/                    final solve stdout record
#     run-history/              Loop Engine Run History dirs (kept)
#     summary/                  final one-page report per attempt
#     stage-<stamp>.json        what this cell did and where it stopped
#
# Runs outside Kaggle too: kaggle/check_cells.py sets the
# LOOP_ENGINE_* variables read in the configuration block below.
#
# Based on loop-engine main @ 863506e.
# ============================================================

from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from types import SimpleNamespace

import importlib.util
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
# preflight: stop after the provider probes. solve: the full run.
STAGE = os.environ.get("LOOP_ENGINE_KAGGLE_STAGE", "solve").strip() or "solve"

REPOSITORY_DIR = (Path(SOURCE_DIR) if SOURCE_DIR
                  else KAGGLE_WORKING / "loop-engine-src")
DATASET_DIR = KAGGLE_INPUT / "competitions" / COMPETITION
LOGS_DIR = KAGGLE_WORKING / "loop-engine-logs"
PREFLIGHT_DIR = LOGS_DIR / "preflight"
SOLVE_LOG_DIR = LOGS_DIR / "solve"
RUNS_DIR = LOGS_DIR / "run-history"
SUMMARY_DIR = LOGS_DIR / "summary"
SOLUTIONS_DIR = KAGGLE_WORKING / "loop-engine-solutions"
TASK_FILE = KAGGLE_WORKING / f"loop-engine-{COMPETITION}-task.md"
SETTINGS_FILE = KAGGLE_WORKING / "loop-engine-providers.yaml"
SETUP_TEMP_DIR = KAGGLE_TEMP / "loop-engine-setup"

# Kaggle secret names and the standard variables the providers read.
OLLAMA_SECRET_NAME = "ollama_kaggle_key"
OLLAMA_KEY_ENV = "OLLAMA_API_KEY"
MISTRAL_SECRET_NAME = "mistral_kaggle_key"
MISTRAL_KEY_ENV = "MISTRAL_API_KEY"
TACTICAL_SECRET_NAME = "tacticalhat_kaggle_key"
TACTICAL_KEY_ENV = "TACTICAL_API_KEY"

# Primary route and probe model on Ollama Cloud.
PRIMARY_ROUTE = "cloud.default"
PRIMARY_PROVIDER = "ollama_cloud"
PROBE_MODEL_ID = "deepseek-v4-flash:0731"

# tacticalengineering: the owner's PRIVATE direct-origin OpenAI-compatible
# API. The DNS-only hostname serves a Cloudflare Origin CA certificate, so
# the endpoint declares tls_verification: skip (the typed curl -k, scoped
# to exactly this endpoint). tls_verification: ca_file with tls_ca_file
# pointing at the Origin CA root is the preferred alternative when that
# root is available. stream: auto self-orients: non-streamed first, SSE
# retry when a proxy wall cuts a long generation. The URL may be the /v1
# base or the full /chat/completions URL; both resolve the same way.
TACTICAL_BASE_URL = os.environ.get(
    "LOOP_ENGINE_TACTICAL_BASE_URL",
    "https://ai.tacticalengineering.net:6969/v1/chat/completions").strip()
TACTICAL_MODEL = os.environ.get(
    "LOOP_ENGINE_TACTICAL_MODEL", "gemma-4-coding-abliterated").strip()
TACTICAL_ENDPOINT = (
    TACTICAL_BASE_URL.rstrip("/")
    if TACTICAL_BASE_URL.rstrip("/").endswith("/chat/completions")
    else TACTICAL_BASE_URL.rstrip("/") + "/chat/completions")
# gemma-4 published model output ceiling. Declared by this notebook, not
# measured by it.
TACTICAL_MAX_OUTPUT = 32768
TACTICAL_MAX_OUTPUT_SOURCE = (
    "gemma-4 published model output ceiling; declared by the notebook, "
    "not measured")
# Honest identification on every request; no browser spoofing.
TACTICAL_USER_AGENT = "Loop-Engine-Kaggle"
PREFLIGHT_USER_AGENT = "Loop-Engine-Kaggle-Preflight"

# Mistral: capabilities seeded upstream from Mistral platform docs
# (small: 8192, large: 16384). No per-notebook declaration needed.
MISTRAL_PROBE_ROUTE = "cloud.mistral"
MISTRAL_PROBE_MODEL = "mistral-small-latest"

RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
WORKSPACE_PREFIX = f"loop-engine-{COMPETITION}-solve-"
WORKSPACE = KAGGLE_WORKING / f"{WORKSPACE_PREFIX}{RUN_STAMP}"
PREFLIGHT_FILE = PREFLIGHT_DIR / f"preflight-{RUN_STAMP}.json"
RESULT_FILE = SOLVE_LOG_DIR / f"solve-stdout-{RUN_STAMP}.json"
REPORT_FILE = SUMMARY_DIR / f"final-report-{RUN_STAMP}.md"
STAGE_FILE = LOGS_DIR / f"stage-{RUN_STAMP}.json"

if STAGE not in ("offline", "preflight", "solve"):
    raise ValueError(
        "LOOP_ENGINE_KAGGLE_STAGE must be offline, preflight, or solve, "
        f"not {STAGE!r}")

STAGE_RECORD = {
    "record_type": "loop_engine_kaggle_stage/v1",
    "cell": "03_three_provider_failover",
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
        "User-Agent": PREFLIGHT_USER_AGENT,
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
        preview = str(
            (body.get("choices") or [{}])[0]
            .get("message", {}).get("content", ""))[:80]
        return {
            "endpoint": name, "ok": True, "exit_code": None,
            "elapsed_seconds": round(elapsed, 2),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "usage_accounting_complete": bool(
                usage.get("prompt_tokens")
                or usage.get("completion_tokens")),
            "content_preview": preview,
            "note": f"replied in {round(elapsed, 2)}s: {preview}",
        }
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:200]}"
        return {
            "endpoint": name, "ok": False, "exit_code": None,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "error": error,
            "note": error,
        }


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
# 1. Load all three Kaggle secrets up front
# ------------------------------------------------------------

SECRETS = (
    ("ollama_cloud", OLLAMA_SECRET_NAME, OLLAMA_KEY_ENV),
    ("mistral", MISTRAL_SECRET_NAME, MISTRAL_KEY_ENV),
    ("tacticalengineering", TACTICAL_SECRET_NAME, TACTICAL_KEY_ENV),
)
keys = {provider: read_secret(secret_name, key_env)
        for provider, secret_name, key_env in SECRETS}
ollama_key = keys["ollama_cloud"]
mistral_key = keys["mistral"]
tactical_key = keys["tacticalengineering"]

# Strip stale leftovers from older cells.
for name in (
        "LOOP_ENGINE_ENDPOINTS", "TACTICALHAT_API_KEY",
        "OPENWEBUI_API_KEY", "PRIVATE_OPENWEBUI_API_KEY",
        "OPENROUTER_API_KEY", "OPENCODE_ZEN_API_KEY",
        "OPENCODE_GO_API_KEY", OLLAMA_KEY_ENV, MISTRAL_KEY_ENV,
        TACTICAL_KEY_ENV):
    os.environ.pop(name, None)

missing = [
    f"{secret_name!r} (or {secret_name.upper()} / {key_env})"
    for provider, secret_name, key_env in SECRETS if not keys[provider]]
if missing and STAGE != "offline":
    raise RuntimeError(
        f"Stage {STAGE!r} needs all three provider keys. Missing Kaggle "
        "secrets: " + ", ".join(missing) + ". Create each secret and "
        "enable notebook access, or set the variables.")

for provider, secret_name, key_env in SECRETS:
    if keys[provider]:
        os.environ[key_env] = keys[provider]
command_environment = os.environ.copy()

print("Provider credentials configured:", {
    "ollama_cloud": bool(command_environment.get(OLLAMA_KEY_ENV)),
    "mistral": bool(command_environment.get(MISTRAL_KEY_ENV)),
    "tacticalengineering": bool(command_environment.get(TACTICAL_KEY_ENV)),
})
print("Stage requested:", STAGE)


# ------------------------------------------------------------
# 2. Clean old run debris so the disk never fills again
#    Run History is kept: it is the replayable record of every attempt.
# ------------------------------------------------------------

if not SOURCE_DIR and REPOSITORY_DIR.exists():
    print(f"Removing previous checkout: {REPOSITORY_DIR}")
    shutil.rmtree(REPOSITORY_DIR, ignore_errors=True)
for stale in KAGGLE_WORKING.glob(f"{WORKSPACE_PREFIX}*"):
    shutil.rmtree(stale, ignore_errors=True)
for directory in (RUNS_DIR, PREFLIGHT_DIR, SOLVE_LOG_DIR, SUMMARY_DIR,
                  SOLUTIONS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 3. Download and install current main
#    (or install the local checkout named by LOOP_ENGINE_SOURCE_DIR)
# ------------------------------------------------------------

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

    if not zipfile.is_zipfile(archive_path):
        raise RuntimeError(
            f"Downloaded file is not a ZIP archive: {archive_path}")
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
print("Repository root:", REPOSITORY_DIR)


# ------------------------------------------------------------
# 4. Offline diagnostics
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
# 5. PREFLIGHT: test every provider API before the solve
#    (one authorized call each; each result is recorded AFTER it runs,
#     failures are recorded, not hidden, and never abort the cell)
# ------------------------------------------------------------

print("\n" + "=" * 68)
print("PREFLIGHT: testing all provider APIs")
print("=" * 68)

preflight = {
    "record_type": "loop_engine_preflight/v1",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "attempt": RUN_STAMP,
    "providers": [],
}

# --- 5a. Ollama Cloud via the built-in probe (typed record) ---
preflight["providers"].append(probe_builtin_provider(
    PRIMARY_PROVIDER, PRIMARY_ROUTE, PROBE_MODEL_ID, 70000,
    command_environment))

# --- 5b. Mistral via the built-in probe ---
preflight["providers"].append(probe_builtin_provider(
    "mistral", MISTRAL_PROBE_ROUTE, MISTRAL_PROBE_MODEL, 20000,
    command_environment))

# --- 5c. tacticalengineering via a direct OpenAI-style probe ---
tactical_result = probe_endpoint_raw(
    "tacticalengineering", TACTICAL_ENDPOINT, tactical_key, TACTICAL_MODEL)
# The probe result comes first so the explicit fields below (the real
# endpoint URL among them) are never overwritten by it.
preflight["providers"].append({
    **tactical_result,
    "provider": "tacticalengineering",
    "probe_kind": "direct_openai_chat",
    "endpoint": TACTICAL_ENDPOINT,
    "model": TACTICAL_MODEL,
    "tls_verification": "skip",
})

# The record is always written, whatever the probes returned.
PREFLIGHT_FILE.write_text(
    json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
STAGE_RECORD["preflight_file"] = str(PREFLIGHT_FILE)

print("\nPreflight summary:")
providers_ok = []
providers_failed = []
for item in preflight["providers"]:
    status = "OK " if item.get("ok") else "FAIL"
    exit_note = ("" if item.get("exit_code") is None
                 else f"exit {item['exit_code']}; ")
    print(f"  [{status}] {item['provider']}: {exit_note}{item.get('note')}")
    (providers_ok if item.get("ok") else providers_failed).append(
        item["provider"])
STAGE_RECORD["preflight_ok"] = bool(providers_ok)
STAGE_RECORD["preflight_providers_ok"] = providers_ok
STAGE_RECORD["preflight_providers_failed"] = providers_failed

print("Preflight record:", PREFLIGHT_FILE)

if not providers_ok:
    write_stage_record("preflight")
    raise RuntimeError(
        "No provider passed preflight; not starting a solve that cannot "
        "reach any model. Fix the keys or endpoints and rerun. Detail is "
        "in the preflight record.")
if providers_failed:
    print(
        f"\nWARNING: {', '.join(providers_failed)} failed preflight.\n"
        f"The solve continues with {', '.join(providers_ok)}; "
        "failover skips routes that cannot answer.\n"
        "Full failure detail is saved in the preflight record.")
else:
    print("\nAll provider APIs responded.")

finish_stage("preflight")


# ------------------------------------------------------------
# 6. Runtime settings: Ollama + tacticalengineering + Mistral
# ------------------------------------------------------------

# Each credential_env names the variable the solve reads for that
# provider id; the custom id resolves its key through it.
settings = {
    "version": 1,
    "models": {
        "default_thinking_power": "medium",
        "providers": [
            {
                "id": "ollama_cloud",
                "kind": "builtin",
                "enabled": True,
                "credential_env": OLLAMA_KEY_ENV,
            },
            {
                "id": "tacticalengineering",
                "kind": "custom",
                "enabled": True,
                "credential_env": TACTICAL_KEY_ENV,
                "endpoint": TACTICAL_ENDPOINT,
                "model": TACTICAL_MODEL,
                "wire": "openai",
                "locality": "cloud",
                "stream": "auto",
                "tls_verification": "skip",
                "maximum_output_tokens": TACTICAL_MAX_OUTPUT,
                "maximum_output_source": TACTICAL_MAX_OUTPUT_SOURCE,
                "counts_as_evidence": True,
                "auth_scheme": "bearer",
                "headers": {"User-Agent": TACTICAL_USER_AGENT},
            },
            {
                "id": "mistral",
                "kind": "builtin",
                "enabled": True,
                "credential_env": MISTRAL_KEY_ENV,
            },
        ],
    },
}

settings_text = yaml.safe_dump(settings, sort_keys=False, allow_unicode=True)
for secret in (ollama_key, mistral_key, tactical_key):
    if secret and secret in settings_text:
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

TASK = f"""
Build and verify a reproducible baseline solution for the supplied Kaggle
competition dataset ({COMPETITION}).

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
infinite predictions, prediction type, and prediction range. Treat the
dataset directory {DATASET_DIR} as read-only. Do not submit anything to
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
    "--provider-key-env", OLLAMA_KEY_ENV,
    "--model-route", PRIMARY_ROUTE,
    "--allow-model-failover",
    "--authorize-model-calls",
    "--allow-source-to-model",
    # Kaggle has no Docker: generated code runs as a host process and the
    # run record labels the weaker isolation.
    "--allow-local-execution",
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

STAGE_RECORD["commands"]["solve"] = {"exit_code": completed.returncode}
STAGE_RECORD["solve_stdout_record"] = str(RESULT_FILE)
STAGE_RECORD["terminal_code"] = final_record.get("terminal_code")
STAGE_RECORD["solved"] = final_record.get("solved")
STAGE_RECORD["run_id"] = final_record.get("run_id")


# ------------------------------------------------------------
# 10. Copy solution artifacts to a stable, clear location
# ------------------------------------------------------------

attempt_dir = SOLUTIONS_DIR / f"attempt-{RUN_STAMP}"
attempt_dir.mkdir(parents=True, exist_ok=True)
solved_workspace = Path(
    (final_record.get("workspace") or str(WORKSPACE)))
artifacts_copied = []

for artifact in final_record.get("artifacts") or []:
    artifact_path = Path(str(artifact.get("path", "")))
    if not artifact_path.is_file():
        continue
    destination = attempt_dir / artifact_path.name
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
        destination = attempt_dir / found.name
        if not destination.exists():
            shutil.copy2(found, destination)
            artifacts_copied.append({
                "file": found.name,
                "verified": False,
                "bytes": destination.stat().st_size,
                "saved_to": str(destination),
            })

print("\nSolution artifacts saved to:", attempt_dir)
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
    f"Run started: {RUN_STAMP}",
    f"Loop Engine: {REPOSITORY_DIR}",
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
            detail = f"builtin probe exit {item.get('exit_code')}: {item.get('note')}"
    else:
        detail = str(item.get("note") or item.get("error", "failed"))[:120]
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
    f"- Solution artifacts: `{attempt_dir}`",
    f"- Full solve record (JSON): `{RESULT_FILE}`",
    f"- Preflight record: `{PREFLIGHT_FILE}`",
    f"- Run history: `{RUNS_DIR}`",
    f"- Stage record: `{STAGE_FILE}`",
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

finish_stage("solve")
