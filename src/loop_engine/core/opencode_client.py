"""OpenCode-as-agent — delegate a multi-step coding task to a headless worker.

The Ollama client in this package makes one deliberation call: it asks a model
to select the next action and parses typed moves back. That is right for planning,
but some moves are *do the work*: implement this DSL primitive, write and run its
tests, fix it until it passes.  That is an agent loop, not one call — and OpenCode
(``opencode``, installed here at 1.18.21) is exactly a headless agent loop that
can read files, write code, run it, read the error, and iterate, driving any of
the account's Ollama Cloud models.

This wrapper spawns ``opencode run`` as a worker and returns what it produced.  It
keeps the two roles honest and separate:

  * **measurement / evidence** stays with ``ollama_client`` — direct calls return
    provider-reported token counts, which is what the doctrine admits as evidence;
  * **agent work** (writing + running code) goes here — the value is the code that
    results and passes an independent oracle, not a token count.

Model execution stays CLOUD-ONLY: the worker uses ``ollama-cloud/<model>`` against
``https://ollama.com`` (the sanctioned hosted endpoint), never a local model.

This module shells out; its self-test is fully offline (it validates command
construction and model-name handling, and never spawns a worker or hits network).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Sequence

OPENCODE_BIN = os.path.expanduser("~/.opencode/bin/opencode")

# A strong hosted coding model as the default worker brain.  Kimi K2.7 Code is
# the code specialist in the account's catalog; override per call as needed.
DEFAULT_WORKER_MODEL = "ollama-cloud/kimi-k2.7-code:cloud"

# Models that must never be used (policy — kimi-k3 is forbidden repo-wide).
FORBIDDEN = ("kimi-k3",)


@dataclass
class AgentResult:
    """What a headless OpenCode worker produced."""
    ok: bool
    model: str
    output: str
    exit_code: int
    seconds: float
    error: str = ""
    files_changed: list = field(default_factory=list)


def _load_key(explicit: str | None = None) -> str:
    if explicit is not None:
        return explicit
    key = os.environ.get("OLLAMA_API_KEY", "")
    if key:
        return key
    # Fall back to the repo .env, same source the ollama client reads.
    for path in (".env",):
        try:
            with open(path) as fh:
                for line in fh:
                    if line.startswith("OLLAMA_API_KEY"):
                        return line.split("=", 1)[1].strip().strip('"\'')
        except OSError:
            continue
    return ""


def build_command(task: str, *, model: str = DEFAULT_WORKER_MODEL,
                  pure: bool = True, continue_session: str | None = None,
                  command: str | None = None) -> list[str]:
    """Construct the ``opencode run`` argv for a task (pure = no plugins).

    Raises on a forbidden model so a policy violation fails loudly rather than
    silently executing.  Kept separate from ``run_agent`` so the self-test can
    check argv construction without spawning anything."""
    short = model.split("/")[-1]
    if any(bad in short for bad in FORBIDDEN):
        raise ValueError(f"model {model!r} is forbidden by policy")
    argv = [OPENCODE_BIN, "run"]
    if pure:
        argv.append("--pure")
    argv += ["-m", model]
    if continue_session:
        argv += ["--session", continue_session]
    if command:
        argv += ["--command", command]
    argv.append(task)
    return argv


def run_agent(task: str, *, model: str = DEFAULT_WORKER_MODEL,
              cwd: str | None = None, timeout: int = 600, pure: bool = True,
              api_key: str | None = None,
              continue_session: str | None = None) -> AgentResult:
    """Run one headless OpenCode worker on a task and return what it produced.

    ``cwd`` is the directory the worker operates in (where it reads/writes code);
    ``timeout`` bounds the agent loop.  Never raises on worker failure — returns
    ``ok=False`` with the captured error, so a caller can fall back or retry.  The
    Ollama Cloud key is injected into the spawned environment (cloud-only)."""
    import time
    try:
        argv = build_command(task, model=model, pure=pure,
                             continue_session=continue_session)
    except ValueError as exc:
        return AgentResult(ok=False, model=model, output="", exit_code=-1,
                           seconds=0.0, error=str(exc))
    env = dict(os.environ)
    key = _load_key(api_key)
    if key:
        env["OLLAMA_API_KEY"] = key
    # Snapshot the working tree so we can report what the worker changed.
    before = _snapshot(cwd) if cwd else {}
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                              text=True, timeout=timeout)
        secs = time.monotonic() - t0
        ok = proc.returncode == 0
        changed = _changed(before, _snapshot(cwd)) if cwd else []
        return AgentResult(ok=ok, model=model, output=proc.stdout.strip(),
                           exit_code=proc.returncode, seconds=secs,
                           error="" if ok else proc.stderr.strip()[:2000],
                           files_changed=changed)
    except subprocess.TimeoutExpired:
        return AgentResult(ok=False, model=model, output="", exit_code=-2,
                           seconds=time.monotonic() - t0,
                           error=f"worker exceeded {timeout}s timeout")
    except FileNotFoundError:
        return AgentResult(ok=False, model=model, output="", exit_code=-3,
                           seconds=0.0,
                           error=f"opencode binary not found at {OPENCODE_BIN}")


def _snapshot(cwd: str) -> dict:
    """Cheap mtime snapshot of a directory tree (for change detection)."""
    out: dict = {}
    for root, _dirs, files in os.walk(cwd):
        if "/.git" in root or "/node_modules" in root:
            continue
        for f in files:
            path = os.path.join(root, f)
            try:
                out[path] = os.path.getmtime(path)
            except OSError:
                pass
    return out


def _changed(before: dict, after: dict) -> list:
    changed = [p for p, m in after.items() if before.get(p) != m]
    return sorted(changed)[:50]


def parallel_agents(tasks: Sequence[dict], *, max_workers: int = 4) -> list:
    """Run several OpenCode workers concurrently (independent coding tasks).

    Each task dict is kwargs for ``run_agent`` (must include ``task``).  Workers
    that write the SAME directory must not run together — give each its own
    ``cwd`` — since they are independent processes with no shared lock.  Returns
    results in task order."""
    from concurrent.futures import ThreadPoolExecutor
    results: list = [None] * len(tasks)

    def _one(i_t):
        i, t = i_t
        return i, run_agent(**t)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for i, res in ex.map(_one, list(enumerate(tasks))):
            results[i] = res
    return results


# ---------------------------------------------------------------------------
# Self-test — offline: command construction + policy, no worker, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    argv = build_command("implement the primitive", model="ollama-cloud/glm-5.2",
                         pure=True)
    check("the_run_command_is_constructed_headless_pure_with_the_model",
          argv[:2] == [OPENCODE_BIN, "run"] and "--pure" in argv
          and "-m" in argv and "ollama-cloud/glm-5.2" in argv
          and argv[-1] == "implement the primitive",
          "opencode run --pure -m <model> <task>")

    raised = False
    try:
        build_command("x", model="ollama-cloud/kimi-k3")
    except ValueError:
        raised = True
    check("a_forbidden_model_is_rejected_before_any_spawn", raised,
          "kimi-k3 (forbidden repo-wide) raises at command construction, so a "
          "policy violation cannot reach a subprocess")

    argv2 = build_command("t", model="ollama-cloud/kimi-k2.7-code:cloud",
                          continue_session="ses_123")
    check("a_session_can_be_continued_for_a_multi_step_worker",
          "--session" in argv2 and "ses_123" in argv2,
          "continue_session threads --session so a worker can resume its context")

    # Change detection over a temp dir (no network, no worker).
    import tempfile, time
    with tempfile.TemporaryDirectory() as d:
        before = _snapshot(d)
        p = os.path.join(d, "new.py")
        with open(p, "w") as fh:
            fh.write("x=1\n")
        changed = _changed(before, _snapshot(d))
        check("files_written_by_a_worker_are_detected_as_changes",
              p in changed,
              "a new file in the worker's cwd is reported in files_changed")

    check("the_default_worker_model_is_a_hosted_cloud_coding_model",
          DEFAULT_WORKER_MODEL.startswith("ollama-cloud/")
          and "code" in DEFAULT_WORKER_MODEL,
          f"default worker brain is {DEFAULT_WORKER_MODEL} (cloud, code "
          f"specialist) — never a local model")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "opencode_client_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
