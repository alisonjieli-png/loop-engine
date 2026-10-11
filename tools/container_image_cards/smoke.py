"""An optional smoke run of a few container image cards on a local engine: pull the platform image by its index
digest, compare the engine's own reading of its config with the card, and run the command the card's helper writes.

```text
smoke(card, engine) -> container_image_smoke/v1 (verification/smoke.json of the package)
├── pulled: <engine> pull --platform P <reference by index digest>; the engine names the index digest it holds
│   (a pull costs the registry's anonymous allowance: two manifest reads were counted per pull on October 9, 2026)
├── config_matches_card: <engine> image inspect's Config, read by verify.observed_runtime, equals the card's
│   runtime of that platform
├── runs: the selected engine's argument list, only after pull and config checks pass, with --network none so the
│   container reaches nothing; an image that exposes no port runs to its end and exits 0, one that exposes a port
│   is started detached, must still be running after a few seconds, and is stopped with its stop signal
└── cleanup addresses only the container ID the engine wrote in this invocation's private cidfile; pulled images
    remain cached because the image store may have concurrent users
```

Only images a caller names are run, small ones; every other card says it was not run. The record holds no time
stamp and no output text, so the same engine and image give the same bytes.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .verify import observed_runtime, runtime_differences

SMOKE_RECORD = "container_image_smoke/v1"
PASSED, FAILED = "passed", "failed"
PULL_CHECK, CONFIG_CHECK, RUN_CHECK = "pulled", "config_matches_card", "runs"
CLEANUP_CHECK = "owned_container_removed"
DEFAULT_PLATFORM = "linux/amd64"
NETWORK_NONE = ("--network", "none")
#: Execution bounds of this optional probe; these do not change the card's general run recipe.
RESOURCE_FLAGS = ("--memory", "256m", "--cpus", "1", "--pids-limit", "128",
                  "--security-opt", "no-new-privileges")
CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")
#: How long a one-shot run may take, how long a service is given to start, and how long it is given to stop.
RUN_SECONDS, START_SECONDS, STOP_SECONDS = 120, 5, 20
STATE_TEMPLATE, CONFIG_TEMPLATE, IDENTITY_TEMPLATE = "{{json .State}}", "{{json .Config}}", "{{.Id}}"


def engine_version(engine: str, run=subprocess.run) -> "str | None":
    """The engine's client version, or None when it is not installed or does not answer."""
    if not shutil.which(engine):
        return None
    try:
        done = run([engine, "version", "--format", "{{.Client.Version}}"], capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return done.stdout.strip() or None if done.returncode == 0 else None


def _check(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail[:300]}


def _created_id(path: Path) -> str:
    """Only a full engine-written ID is cleanup authority; a name or an error message never is."""
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128:
        raise ValueError("container_identity_missing")
    identity = path.read_text(encoding="ascii").strip()
    if not CONTAINER_ID.fullmatch(identity):
        raise ValueError("container_identity_invalid")
    return identity


def _run_owned(contract, module, *, engine, platform, run, sleep, checks, record):
    with tempfile.TemporaryDirectory(prefix="baltor-container-smoke-") as folder:
        cidfile = Path(folder) / "container.id"
        service = bool(contract["inputs"]["ports"])
        # Keep the stopped container until cleanup so every outcome has one exact owned identity.
        argv = module.render_run(contract, engine=engine, platform=platform, detach=service, remove=False)
        argv[2:2] = [*NETWORK_NONE, *RESOURCE_FLAGS, "--cidfile", str(cidfile)]
        try:
            completed = run(argv, capture_output=True, text=True, timeout=RUN_SECONDS)
            identity = _created_id(cidfile)
            if service and completed.returncode == 0:
                sleep(START_SECONDS)
                state = run([engine, "container", "inspect", "--format", STATE_TEMPLATE, identity],
                            capture_output=True, text=True, timeout=60)
                running = state.returncode == 0 and json.loads(state.stdout or "{}").get("Running") is True
                stopped = run([engine, "stop", "--time", str(STOP_SECONDS), identity], capture_output=True,
                              text=True, timeout=STOP_SECONDS + 60)
                checks.append(_check(RUN_CHECK, running and stopped.returncode == 0,
                                     f"running {running}, stopped {stopped.returncode}"))
            else:
                checks.append(_check(RUN_CHECK, completed.returncode == 0,
                                     f"exit status {completed.returncode}"))
        finally:
            identity = None
            try:
                identity = _created_id(cidfile)
                removed = run([engine, "container", "rm", "--force", "--volumes", identity],
                              capture_output=True, text=True, timeout=STOP_SECONDS + 60)
                checks.append(_check(CLEANUP_CHECK, removed.returncode == 0,
                                     f"exit status {removed.returncode}"))
                if removed.returncode != 0:
                    record["unreconciled_container_id"] = identity
            except (subprocess.TimeoutExpired, OSError, ValueError) as error:
                checks.append(_check(CLEANUP_CHECK, False, type(error).__name__))
                if identity is not None:
                    record["unreconciled_container_id"] = identity


def smoke(contract: dict, card_digest: str, module, *, engine: str = "docker", platform: str = DEFAULT_PLATFORM,
          run=subprocess.run, sleep=time.sleep) -> dict:
    """The smoke record of one card on one platform (``module`` is the shipped image_contract module)."""
    version = engine_version(engine, run)
    record = {"record_type": SMOKE_RECORD, "card_digest": card_digest, "index_digest":
              contract["image"]["index"]["digest"], "engine": {"name": engine, "version": version},
              "platform": platform, "checks": []}
    if version is None or platform not in module.platforms(contract):
        record["checks"].append(_check(PULL_CHECK, False, "no engine" if version is None else "no such platform"))
        record["state"] = FAILED
        return record
    reference = contract["image"]["reference"]
    checks = record["checks"]
    try:
        pulled = run([engine, "pull", "--quiet", "--platform", platform, reference], capture_output=True, text=True,
                     timeout=600)
        identity = run([engine, "image", "inspect", "--format", IDENTITY_TEMPLATE, reference], capture_output=True,
                       text=True, timeout=60).stdout.strip()
        checks.append(_check(PULL_CHECK, pulled.returncode == 0, pulled.stderr.strip()[-200:]))
        if pulled.returncode != 0:
            record["state"] = FAILED
            return record
        inspected = run([engine, "image", "inspect", "--platform", platform, "--format", CONFIG_TEMPLATE, reference],
                        capture_output=True, text=True, timeout=60)
        if inspected.returncode == 0:
            withheld = {row["name"] for row in contract["inputs"]["environment"] if row["withheld"]}
            differences = runtime_differences(module.platform_runtime(contract, platform),
                                              observed_runtime({"config": json.loads(inspected.stdout)}), withheld)
            checks.append(_check(CONFIG_CHECK, not differences, "; ".join(differences)))
        else:
            checks.append(_check(CONFIG_CHECK, False, inspected.stderr.strip()[-200:]))
        if not checks[-1]["passed"]:
            record["state"] = FAILED
            return record
        _run_owned(contract, module, engine=engine, platform=platform, run=run, sleep=sleep, checks=checks,
                   record=record)
        record["image_id"] = identity or None
    except (subprocess.TimeoutExpired, OSError, ValueError) as error:
        checks.append(_check(RUN_CHECK, False, type(error).__name__))
    record["state"] = PASSED if checks and all(check["passed"] for check in checks) else FAILED
    return record


def smoke_bytes(record: dict) -> bytes:
    return (json.dumps(record, indent=1, sort_keys=True) + "\n").encode("utf-8")


__all__ = ["smoke", "smoke_bytes", "engine_version", "SMOKE_RECORD", "PASSED", "FAILED"]
