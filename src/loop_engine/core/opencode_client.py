"""Deprecated OpenCode compatibility surface with execution quarantined.

The original helper launched a host process directly, selected an Ollama Cloud
model, inherited the caller's environment, and read a repository ``.env``
file. Those behaviors bypass the typed external-harness boundary and cannot
prove tool, context, credential, isolation, or budget enforcement.

The public function names remain temporarily importable for compatibility,
but no function in this module starts a process, reads credentials, selects a
provider, or performs network work. New integrations must use the governed
external-harness contract after an execution profile has been independently
qualified.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

# Retained only so old imports fail safely instead of selecting a provider.
OPENCODE_BIN = ""
DEFAULT_WORKER_MODEL = ""
FORBIDDEN = ("kimi-k3",)
_QUARANTINE_ERROR = (
    "legacy_opencode_process_execution_is_quarantined_use_typed_harness"
)


class OpenCodeClientQuarantined(RuntimeError):
    """Legacy process execution is unavailable at this boundary."""


@dataclass
class AgentResult:
    """Compatibility result for a refused legacy OpenCode request."""

    ok: bool
    model: str
    output: str
    exit_code: int
    seconds: float
    error: str = ""
    files_changed: list = field(default_factory=list)


def _load_key(explicit: str | None = None) -> str:
    """Refuse legacy credential loading without inspecting any source."""
    del explicit
    raise OpenCodeClientQuarantined(_QUARANTINE_ERROR)


def build_command(task: str, *, model: str = DEFAULT_WORKER_MODEL,
                  pure: bool = True, continue_session: str | None = None,
                  command: str | None = None) -> list[str]:
    """Refuse construction of an ungoverned prompt-bearing process argv."""
    del task, model, pure, continue_session, command
    raise OpenCodeClientQuarantined(_QUARANTINE_ERROR)


def run_agent(task: str, *, model: str = DEFAULT_WORKER_MODEL,
              cwd: str | None = None, timeout: int = 600, pure: bool = True,
              api_key: str | None = None,
              continue_session: str | None = None) -> AgentResult:
    """Return a fixed refusal without reading state or starting a worker."""
    del task, cwd, timeout, pure, api_key, continue_session
    return AgentResult(
        ok=False,
        model=model,
        output="",
        exit_code=-4,
        seconds=0.0,
        error=_QUARANTINE_ERROR,
    )


def _snapshot(cwd: str) -> dict:
    """Retired compatibility helper; filesystem discovery is disabled."""
    del cwd
    return {}


def _changed(before: dict, after: dict) -> list:
    """Retired compatibility helper; no worker changes can be admitted."""
    del before, after
    return []


def parallel_agents(tasks: Sequence[dict], *, max_workers: int = 4) -> list:
    """Return one fixed refusal per request without creating worker threads."""
    del max_workers
    results = []
    for task in tasks:
        model = task.get("model", "") if isinstance(task, dict) else ""
        results.append(run_agent("", model=model))
    return results


def self_test() -> dict:
    """Prove the compatibility surface cannot execute or expose inputs."""
    from unittest.mock import patch

    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    private_marker = "PRIVATE_LEGACY_OPENCODE_MARKER"
    with patch("subprocess.run") as run, patch("subprocess.Popen") as popen:
        result = run_agent(
            private_marker,
            model="fixture-provider/fixture-model",
            cwd="/private/workspace",
            api_key=private_marker,
            continue_session=private_marker,
        )
        batch = parallel_agents(({
            "task": private_marker,
            "model": "fixture-provider/fixture-model",
        },))
    check(
        "legacy_agent_returns_fixed_quarantine_without_subprocess",
        not result.ok and result.exit_code == -4
        and result.error == _QUARANTINE_ERROR
        and not result.output and not result.files_changed
        and not run.called and not popen.called,
    )
    check(
        "private_inputs_do_not_enter_the_compatibility_result",
        private_marker not in repr(result),
    )
    check(
        "parallel_compatibility_surface_creates_no_workers",
        len(batch) == 1 and batch[0].error == _QUARANTINE_ERROR
        and not batch[0].ok,
    )

    refused = []
    for operation in (
        lambda: _load_key(private_marker),
        lambda: build_command(private_marker, model="fixture/model"),
    ):
        try:
            operation()
            refused.append(False)
        except OpenCodeClientQuarantined as exc:
            refused.append(str(exc) == _QUARANTINE_ERROR)
    check(
        "credential_loading_and_command_construction_are_quarantined",
        all(refused),
    )
    check(
        "no_default_provider_or_binary_is_selected",
        DEFAULT_WORKER_MODEL == "" and OPENCODE_BIN == "",
    )

    passed = sum(1 for result in results if result["passed"])
    return {
        "record_type": "opencode_client_quarantine_self_test/v1",
        "tests": results,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results),
        "provider_calls": 0,
        "subprocess_calls": 0,
    }
