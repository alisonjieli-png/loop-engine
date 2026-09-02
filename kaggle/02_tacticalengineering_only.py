# ============================================================
# Loop Engine - Kaggle single-provider solve (tacticalengineering)
#
# ONE cell. Requires Kaggle secret: tacticalhat_kaggle_key
#
# Time budget: targets 4-6 hours max (wall clock), enforced by a
# subprocess deadline so the notebook stops honestly instead of
# hitting the Kaggle session limit. At the deadline the solve gets
# SIGINT first, so the CLI records an honest CANCELLED outcome with
# its Run History; terminate and kill follow only if it ignores that.
#
# Output layout (under the Kaggle working directory):
#   submission.csv               the competition file, ready to submit
#   loop-engine/                 everything else, so the root stays readable
#     submissions/
#       submission-<stamp>.csv   one dated copy per attempt
#       root-submission.json     which attempt holds the root file, and why
#     logs/
#       LATEST.json              this run's record, for machines
#       reports/                 report-<stamp>.html and .md, for people
#       records/                 run-<stamp>.json, one per attempt
#       preflight/               provider API check records
#       solve/                   full solve stdout records (per attempt)
#       run-history/             Loop Engine Run History dirs
#       summary/                 one-page human report per attempt
#       master/                  chronological master log + artifact index
#       stage-<stamp>.json       what this cell did and where it stopped
#     solutions/                 best verified artifacts, versioned
#     src/                       the engine checkout this run used
#     workspace-<stamp>/         the solve's own working directory
#     providers.yaml             the settings the solve reads (no key values)
#     task.md                    the task text given to the solve
#
# Runs outside Kaggle too: kaggle/check_cells.py sets the
# LOOP_ENGINE_* variables read in the configuration block below.
#
# Based on loop-engine main (the cell installs the current main archive).
# ============================================================

from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from types import SimpleNamespace

import importlib.util
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
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

# Everything this cell writes lives under one directory, so the Kaggle
# working root holds the competition file and nothing to search through.
# The submit dialog lists that root; a reader should find one file there.
ENGINE_ROOT = KAGGLE_WORKING / "loop-engine"
ENGINE_ROOT.mkdir(parents=True, exist_ok=True)
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

REPOSITORY_DIR = (Path(SOURCE_DIR) if SOURCE_DIR
                  else ENGINE_ROOT / "src")
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


LOGS_DIR = ENGINE_ROOT / "logs"
PREFLIGHT_DIR = LOGS_DIR / "preflight"
SOLVE_LOG_DIR = LOGS_DIR / "solve"
RUN_HISTORY_LOG_DIR = LOGS_DIR / "run-history"
SUMMARY_DIR = LOGS_DIR / "summary"
MASTER_DIR = LOGS_DIR / "master"
SOLUTIONS_DIR = ENGINE_ROOT / "solutions"
SETUP_TEMP_DIR = KAGGLE_TEMP / "loop-engine-setup"

# tacticalengineering: the owner's PRIVATE direct-origin OpenAI-compatible
# API. The DNS-only hostname serves a Cloudflare Origin CA certificate, so
# the endpoint declares tls_verification: skip (typed curl -k, scoped to
# exactly this endpoint). tls_verification: ca_file with tls_ca_file
# pointing at the Origin CA root is the preferred alternative when that
# root is available. stream: auto self-orients to SSE if a proxy wall
# ever cuts a long generation. The URL may be the /v1 base or the full
# /chat/completions URL; both forms resolve to the same request.
TACTICAL_BASE_URL = os.environ.get(
    "LOOP_ENGINE_TACTICAL_BASE_URL",
    "https://ai.tacticalengineering.net:6969/v1/chat/completions").strip()
TACTICAL_MODEL = os.environ.get(
    "LOOP_ENGINE_TACTICAL_MODEL", "gemma-4-coding-abliterated").strip()
TACTICAL_SECRET_NAME = "tacticalhat_kaggle_key"
TACTICAL_KEY_ENV = "TACTICAL_API_KEY"
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

# Wall-clock budget for the whole solve phase (seconds). 5 hours is the
# middle of the 4-6 hour target. At the deadline the solve is asked to
# stop with SIGINT and gets STOP_GRACE_SECONDS to write its CANCELLED
# record before terminate() and kill() follow. The local harness can
# shorten the budget through LOOP_ENGINE_KAGGLE_DEADLINE_SECONDS to
# exercise that path; Kaggle runs keep the 5-hour default.
SOLVE_DEADLINE_SECONDS = int(os.environ.get(
    "LOOP_ENGINE_KAGGLE_DEADLINE_SECONDS", str(5 * 60 * 60)))
STOP_GRACE_SECONDS = 180
DEADLINE_LABEL = (f"{SOLVE_DEADLINE_SECONDS // 3600}h"
                  if SOLVE_DEADLINE_SECONDS >= 3600
                  else f"{SOLVE_DEADLINE_SECONDS}s")

# The Practitioner's own pass ceiling. This is an explicit owner-set
# work ceiling (allowed: the product sets none by default), sized so
# the escalation ladder and this ceiling together keep the run inside
# the wall-clock budget.
MAX_PASSES = 60

TASK_FILE = ENGINE_ROOT / "task.md"
SETTINGS_FILE = ENGINE_ROOT / "providers.yaml"

RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
#: Stale workspaces are removed; nothing else this cell ever wrote is
#: touched. A previous run's solutions directory can hold the only
#: copy of a verified submission, so cleanup stays narrow by design.
WORKSPACE_PREFIX = "workspace-"
STAGE_FILE = LOGS_DIR / f"stage-{RUN_STAMP}.json"

if STAGE not in ("offline", "preflight", "solve"):
    raise ValueError(
        "LOOP_ENGINE_KAGGLE_STAGE must be offline, preflight, or solve, "
        f"not {STAGE!r}")

STAGE_RECORD = {
    "record_type": "loop_engine_kaggle_stage/v1",
    "cell": "02_tacticalengineering_only",
    "attempt": RUN_STAMP,
    "stage_requested": STAGE,
    "stage_reached": "",
    "repository_dir": str(REPOSITORY_DIR),
    "install_mode": "",
    "commands": {},
}


#: Why a Kaggle secret lookup failed, by secret name. Recorded rather than
#: discarded, so a refusal can state the cause instead of guessing at one.
SECRET_LOOKUP_FAILURES: "dict[str, str]" = {}


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
        except Exception as exc:
            # Why the lookup failed is the whole diagnosis, and this line
            # used to assert a cause it never checked. A secret that is not
            # attached and a secrets service that refuses the request need
            # opposite answers; only the exception separates them.
            SECRET_LOOKUP_FAILURES[secret_name] = (
                f"{type(exc).__name__}: {str(exc)[:200]}")
            value = ""
    if not isinstance(value, str) or not value.strip():
        value = os.environ.get(secret_name.upper(), "")
    if not value.strip():
        value = os.environ.get(standard_env, "")
    return value.strip()


def require_key(value, secret_name, standard_env):
    """Stop with a clear message when a stage needs a key that is missing."""
    if not value:
        failure = SECRET_LOOKUP_FAILURES.get(secret_name)
        if failure:
            detail = (f" The Kaggle secret lookup failed with {failure}. A "
                      "batch run started through the Kaggle API cannot reach "
                      "the secrets service even when the secret is attached; "
                      "run the notebook from the Kaggle editor instead.")
        elif UserSecretsClient is None:
            detail = (" The kaggle_secrets module is unavailable here, so no "
                      "secret was looked up.")
        else:
            detail = (f" The lookup returned an empty value, so "
                      f"{secret_name!r} is attached but holds nothing.")
        raise RuntimeError(
            f"Stage {STAGE!r} needs a provider key, but secret "
            f"{secret_name!r} did not resolve and neither "
            f"{secret_name.upper()} nor {standard_env} is set.{detail}")


def run_command(command, *, cwd=None, env=None, check=True,
                timeout=None, capture=False):
    """Run one command without shell interpolation.

    With capture=True the command's stdout is kept on the result and
    echoed afterwards, so the notebook still shows it.
    """
    command = [str(part) for part in command]
    working_directory = Path(cwd or Path.cwd()).resolve()
    print(f"\n[{working_directory}]$ {shlex.join(command)}\n", flush=True)
    result = subprocess.run(
        command, cwd=str(working_directory), env=env, text=True,
        stdout=subprocess.PIPE if capture else None,
        check=False, timeout=timeout)
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
    log_line(f"pip {'failed' if pip_present else 'is not available here'}; "
             f"the CLI runs from {source_tree} through PYTHONPATH.")
    return "pythonpath"


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


def stop_solve_process(process, grace_seconds=STOP_GRACE_SECONDS):
    """Stop the solve at the deadline, gently first.

    SIGINT lets the CLI turn KeyboardInterrupt into an honest CANCELLED
    outcome with its Run History written. terminate() and kill() follow
    only while the process is still alive. Returns the level that was
    needed, so the summary can say how the run ended.
    """
    ladder = (
        ("SIGINT", lambda: process.send_signal(signal.SIGINT), grace_seconds),
        ("SIGTERM", process.terminate, 30),
        ("SIGKILL", process.kill, None),
    )
    used = "already_exited"
    for level, send, wait_seconds in ladder:
        if process.poll() is not None:
            return used
        send()
        used = level
        try:
            process.wait(timeout=wait_seconds)
            return used
        except subprocess.TimeoutExpired:
            log_line(f"  {level} did not stop the solve within "
                     f"{wait_seconds}s; escalating.")
    process.wait()
    return used


def log_line(message):
    """Append one line to the master log and echo it."""
    MASTER_LOG.write_text(
        MASTER_LOG.read_text(encoding="utf-8") + message + "\n",
        encoding="utf-8")
    print(message, flush=True)


def write_stage_record(stage_reached):
    """Save what the cell did so far; readable by people and by the harness."""
    STAGE_RECORD["stage_reached"] = stage_reached
    STAGE_FILE.write_text(
        json.dumps(STAGE_RECORD, indent=2) + "\n", encoding="utf-8")
    log_line(f"Stage record: {STAGE_FILE}")


def finish_stage(stage_reached):
    """Write the stage record; end the cell here when the stage asks for it."""
    write_stage_record(stage_reached)
    if STAGE == stage_reached and stage_reached != "solve":
        log_line(f"LOOP_ENGINE_KAGGLE_STAGE={STAGE}: stopping after the "
                 f"{stage_reached} stage.")
        sys.exit(0)


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
    f"Stage requested: {STAGE}\n"
    f"Wall-clock budget: {DEADLINE_LABEL}\n\n",
    encoding="utf-8")

log_line(f"Log hierarchy root: {LOGS_DIR}")
log_line(f"Stage requested: {STAGE}")

# Hand the attached input root to the solve and report what is in it. The
# runtime states the exact admitted manifest and a model call states what each
# file is; nothing here selects or describes a file. Only the solve stage needs
# data, so earlier stages report a miss and continue.
try:
    DATASET_DIR = resolve_dataset_dir(KAGGLE_INPUT, DATASET_DIR_OVERRIDE)
    log_line(f"Attached input root handed to the solve: {DATASET_DIR}")
    log_line(
        "  The run states the exact manifest and its own reading of each "
        "file; watch the source_manifest and source_roles runtime facts.")
except RuntimeError as dataset_error:
    if STAGE == "solve":
        raise
    DATASET_DIR = Path(DATASET_DIR_OVERRIDE) if DATASET_DIR_OVERRIDE \
        else KAGGLE_INPUT
    log_line(
        f"No attached input yet ({dataset_error}); the {STAGE} stage does "
        "not read it, so the run continues.")


# ------------------------------------------------------------
# 1. Load the Kaggle secret
# ------------------------------------------------------------

tactical_key = read_secret(TACTICAL_SECRET_NAME, TACTICAL_KEY_ENV)

# Strip every other provider variable so this run is single-provider.
for name in (
        "OLLAMA_API_KEY", "MISTRAL_API_KEY", "LOOP_ENGINE_ENDPOINTS",
        "TACTICALHAT_API_KEY", "OPENWEBUI_API_KEY",
        "PRIVATE_OPENWEBUI_API_KEY", "OPENROUTER_API_KEY",
        "OPENCODE_ZEN_API_KEY", "OPENCODE_GO_API_KEY", TACTICAL_KEY_ENV):
    os.environ.pop(name, None)

if tactical_key:
    os.environ[TACTICAL_KEY_ENV] = tactical_key
elif STAGE != "offline":
    require_key(tactical_key, TACTICAL_SECRET_NAME, TACTICAL_KEY_ENV)
command_environment = os.environ.copy()
log_line(f"{TACTICAL_KEY_ENV} configured: {bool(tactical_key)}")


# ------------------------------------------------------------
# 2. Clean old run debris so the disk never fills again
# ------------------------------------------------------------

if not SOURCE_DIR and REPOSITORY_DIR.exists():
    log_line(f"Removing previous checkout: {REPOSITORY_DIR}")
    shutil.rmtree(REPOSITORY_DIR, ignore_errors=True)
for stale in ENGINE_ROOT.glob(f"{WORKSPACE_PREFIX}*"):
    shutil.rmtree(stale, ignore_errors=True)
# Keep solution versions, Run History, and old logs; they are the
# troubleshooting record.


# ------------------------------------------------------------
# 3. Download and install current main
#    (or install the local checkout named by LOOP_ENGINE_SOURCE_DIR)
# ------------------------------------------------------------

if SOURCE_DIR:
    log_line(f"Using local checkout: {REPOSITORY_DIR}")
else:
    if SETUP_TEMP_DIR.exists():
        shutil.rmtree(SETUP_TEMP_DIR)
    SETUP_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = SETUP_TEMP_DIR / "loop-engine-main.zip"

    log_line("Downloading Loop Engine main...")
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
log_line(f"Repository root: {REPOSITORY_DIR}")


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
# The probe result comes first so the explicit fields below (the real
# endpoint URL among them) are never overwritten by it.
preflight["providers"].append({
    **tactical_result,
    "provider": "tacticalengineering",
    "probe_kind": "direct_openai_chat",
    "endpoint": TACTICAL_ENDPOINT,
    "model": TACTICAL_MODEL,
    "tls_verification": "skip",
    "stream": "auto",
})

PREFLIGHT_FILE = PREFLIGHT_DIR / f"preflight-{RUN_STAMP}.json"
PREFLIGHT_FILE.write_text(
    json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
STAGE_RECORD["preflight_file"] = str(PREFLIGHT_FILE)
STAGE_RECORD["preflight_ok"] = bool(tactical_result.get("ok"))

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
    write_stage_record("preflight")
    raise RuntimeError(
        "The single provider failed preflight; not spending the time "
        "budget on a solve that cannot reach a model. Fix the endpoint "
        "and rerun. Detail is in the preflight record.")

finish_stage("preflight")


# ------------------------------------------------------------
# 6. Runtime settings: tacticalengineering only
# ------------------------------------------------------------

# credential_env is the variable the solve reads for this provider id;
# --compile-provider tacticalengineering resolves its key through it.
settings = {
    "version": 1,
    "models": {
        "default_thinking_power": "medium",
        "providers": [
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

TASK = f"""
Build and verify a reproducible baseline solution for the supplied Kaggle
competition dataset ({COMPETITION}).

This is an execution task, not merely a high-level modeling plan.

Decide the target, the identifier, the prediction field, the task type, and
the submission contract from the supplied data itself. Check missing values,
duplicates, leakage, suspicious unique fields, and schema differences between
the files you train on and the files you predict for.

Build a CPU-compatible preprocessing pipeline. Compare at least two reasonable
baseline models with reproducible three-fold cross-validation and an
appropriate local validation metric. Fit the selected model on all training
rows and create submission.csv matching the discovered submission contract
exactly, in its column order and identifier order.

The run must produce submission.csv, metrics.json, report.md and
verification.json, alongside the code that produces them.

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
log_line(f"Task file: {TASK_FILE}")


# ------------------------------------------------------------
# 9. Solve: tacticalengineering only, with a hard wall-clock deadline
# ------------------------------------------------------------

WORKSPACE = ENGINE_ROOT / f"workspace-{RUN_STAMP}"
RUNS_DIR = RUN_HISTORY_LOG_DIR  # Run History lives under logs/run-history

solve_command = [
    sys.executable, "-m", "loop_engine", "solve",
    "--file", str(TASK_FILE),
    "--dataset", str(DATASET_DIR),
    "--workspace", str(WORKSPACE),
    "--runs-dir", str(RUNS_DIR),
    "--settings-file", str(SETTINGS_FILE),
    # A settings-declared provider id; its credential_env names the key
    # variable, and --provider-key-env repeats it explicitly.
    "--compile-provider", "tacticalengineering",
    "--provider-key-env", TACTICAL_KEY_ENV,
    "--model-route", "custom.tacticalengineering",
    "--authorize-model-calls",
    "--allow-source-to-model",
    # Kaggle has no Docker: generated code runs as a host process and the
    # run record labels the weaker isolation.
    "--allow-local-execution",
    "--no-default-extensions",
    # Owner-set pass ceiling sized with the wall-clock budget. The
    # non-progress escalation ladder (soft reset -> cold restart ->
    # honest stop) still bounds stuck runs earlier.
    "--max-passes", str(MAX_PASSES),
    # The exact prompt and raw model output trace to stderr BY DEFAULT.
    # stderr is captured to the solve log; see the tee below.
    "--format", "json",
]

log_line(f"\nRunning solve with a {DEADLINE_LABEL} wall-clock deadline:")
log_line(shlex.join(solve_command) + "\n")

SOLVE_STDOUT_LOG = SOLVE_LOG_DIR / f"solve-stdout-{RUN_STAMP}.jsonl"
SOLVE_STDERR_LOG = SOLVE_LOG_DIR / f"solve-stderr-{RUN_STAMP}.log"

process = subprocess.Popen(
    solve_command,
    cwd=str(REPOSITORY_DIR),
    env=command_environment,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=1,
)

# Both pipes are drained by their own reader threads so neither can
# block the child, and so the deadline wait below stays a plain wait().
stdout_lines = []


def collect_stdout():
    for line in process.stdout:
        stdout_lines.append(line)


# Stream stderr (progress + exact model IO) into the notebook AND the
# solve log, so live troubleshooting and post-hoc debugging use the
# same record.
def tee_stderr():
    with SOLVE_STDERR_LOG.open("w", encoding="utf-8") as stderr_file:
        for line in process.stderr:
            stderr_file.write(line)
            stderr_file.flush()
            print(line, end="", flush=True)


stdout_thread = threading.Thread(target=collect_stdout, daemon=True)
stderr_thread = threading.Thread(target=tee_stderr, daemon=True)
stdout_thread.start()
stderr_thread.start()

deadline_hit = False
stop_level = ""
try:
    process.wait(timeout=SOLVE_DEADLINE_SECONDS)
except subprocess.TimeoutExpired:
    deadline_hit = True
    log_line(
        f"\nDEADLINE: the solve did not finish within {DEADLINE_LABEL}. "
        "Sending SIGINT so it can record an honest CANCELLED outcome...")
    stop_level = stop_solve_process(process)
    log_line(
        f"DEADLINE: the solve stopped after {stop_level}. "
        "Everything completed so far is saved below.")
stdout_thread.join(timeout=30)
stderr_thread.join(timeout=30)

raw_output = "".join(stdout_lines).strip()
SOLVE_STDOUT_LOG.write_text(
    raw_output + ("\n" if raw_output else ""), encoding="utf-8")

exit_note = (f"deadline-stopped by {stop_level}" if deadline_hit
             else f"exit {process.returncode}")
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

STAGE_RECORD["commands"]["solve"] = {
    "exit_code": process.returncode,
    "deadline_hit": deadline_hit,
    "stop_level": stop_level,
}
STAGE_RECORD["solve_stdout_record"] = str(SOLVE_STDOUT_LOG)
STAGE_RECORD["terminal_code"] = final_record.get("terminal_code")
STAGE_RECORD["solved"] = final_record.get("solved")
STAGE_RECORD["run_id"] = final_record.get("run_id")


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
    "stop_level": stop_level,
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
    f"- Stop level needed: {stop_level or 'none (finished on its own)'}",
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
    f"- Stage record: `{STAGE_FILE}`",
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

# ------------------------------------------------------------
# Publish this run's outputs where their readers are
# ------------------------------------------------------------
# The competition file at the working root, a dated copy in submissions/,
# reports in HTML and Markdown, one JSON record, and a console block that
# says what happened without scrolling. Every figure is measured from the
# run's own output; a submission that never varies is published and named
# as one rather than withheld or dressed up.

PUBLISHED_PROVIDER_LABEL = "tacticalengineering"
PUBLISHED_MODEL_LABEL = str(final_record.get("model") or "")
PUBLISHED_DEADLINE_HIT = deadline_hit
PUBLISHED_STOP_LEVEL = stop_level
PUBLISHED_LOG_PATHS = {"run history": str(RUNS_DIR),
     "solve stdout": str(SOLVE_STDOUT_LOG),
     "solve stderr": str(SOLVE_STDERR_LOG),
     "master log": str(MASTER_LOG),
     "summary": str(SUMMARY_FILE)}

from loop_engine.kaggle_report import (
    KaggleReportRequest, publish_run_outputs, render_terminal_block)

published_record = publish_run_outputs(
    KaggleReportRequest(
        working_root=str(KAGGLE_WORKING),
        engine_root=str(ENGINE_ROOT),
        run_stamp=RUN_STAMP,
        solved=bool(final_record.get("solved")),
        terminal_code=str(final_record.get("terminal_code") or ""),
        run_id=str(final_record.get("run_id") or ""),
        provider_label=PUBLISHED_PROVIDER_LABEL,
        model_label=PUBLISHED_MODEL_LABEL,
        model_calls=final_record.get("model_calls"),
        loop_count=final_record.get("loop_count"),
        elapsed_seconds=final_record.get("elapsed_seconds"),
        deadline_hit=bool(PUBLISHED_DEADLINE_HIT),
        stop_level=str(PUBLISHED_STOP_LEVEL or ""),
        artifacts=tuple(final_record.get("artifacts") or ()),
        verification=dict(final_record.get("verification") or {}),
        limitations=tuple(final_record.get("limitations") or ()),
        failures=tuple(final_record.get("failures") or ()),
        source_roles=dict(final_record.get("source_roles") or {}),
        option_selection=dict(final_record.get("option_selection") or {}),
        log_paths=PUBLISHED_LOG_PATHS),
    workspace=str(final_record.get("workspace") or WORKSPACE))

print(render_terminal_block(published_record))

finish_stage("solve")
