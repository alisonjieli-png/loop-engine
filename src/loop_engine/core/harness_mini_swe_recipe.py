"""mini-SWE-agent SDK semantic profile for the existing isolated process boundary.

Owns: a private recipe and non-executing submission environment for the installed
DefaultAgent and LitellmTextbasedModel. Does not own model authority, task
acceptance or shell execution. Submitted means a semantic candidate only.
This is explicitly an SDK adapter profile, not the stock shell-agent benchmark.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit


def prepare_mini_swe_recipe(config, base_url):
    """Return the installed Python invocation, isolated environment and no stdin."""
    url = urlsplit(base_url)
    if url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port or url.username or url.password:
        raise ValueError("isolated_loopback_relay_required")
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if not workspace.is_absolute() or not task.is_absolute():
        raise ValueError("absolute_private_paths_required")
    private = workspace / "mini-semantic-config.json"
    private.write_text(json.dumps({"model": config["model"], "base_url": base_url,
        "task": task.read_text(encoding="utf-8"), "output_allowance": config["output_allowance"],
        "timeout_seconds": config["timeout_seconds"],
        "trajectory": str(workspace / "mini-trajectory.json")}, allow_nan=False), encoding="utf-8")
    environment = {"MSWEA_GLOBAL_CONFIG_DIR": str(workspace / "home/.config/mini-swe-agent"),
        "MSWEA_CONFIGURED": "true", "MSWEA_SILENT_STARTUP": "1", "MSWEA_COST_TRACKING": "ignore_errors",
        "OPENAI_API_KEY": "loop-engine-local-relay", "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "PYTHONNOUSERSITE": "1"}
    return tuple(config["command_prefix"]) + (str(Path(__file__).resolve()),
        "--execute-semantic", str(private)), environment, None


def _submission(action):
    if not isinstance(action, dict) or set(action) != {"command"}:
        raise ValueError("native_action_shape_refused")
    value = action["command"]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("empty_semantic_submission")
    return value


class SemanticSubmissionEnvironment:
    """Passive external-harness environment adapter; never executes a command."""
    config = None

    def execute(self, action, cwd=""):
        candidate = _submission(action)
        from minisweagent.exceptions import Submitted
        raise Submitted({"role": "exit", "content": candidate,
                         "extra": {"exit_status": "Submitted", "submission": candidate}})

    def get_template_vars(self, **kwargs):
        return dict(kwargs)

    def serialize(self):
        return {"info": {"environment": "semantic_submission_without_execution"}}


def execute_semantic(config_path):
    """Run the actual installed mini agent/model classes, with no shell backend."""
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.models.litellm_textbased_model import LitellmTextbasedModel
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    model = LitellmTextbasedModel(model_name="openai/" + config["model"],
        model_kwargs={"api_base": config["base_url"], "api_key": "loop-engine-local-relay",
            "max_tokens": config["output_allowance"], "timeout": config["timeout_seconds"], "num_retries": 0},
        action_regex=r"\A([\s\S]+)\Z", cost_tracking="ignore_errors")
    agent = DefaultAgent(model, SemanticSubmissionEnvironment(),
        system_template="Return the semantic response specified by the task. Native tools and commands are unavailable. Your response is submitted as a candidate for the owning Loop.",
        instance_template="{{ task }}", step_limit=1, cost_limit=0,
        max_consecutive_format_errors=1, output_path=Path(config["trajectory"]))
    result = agent.run(config["task"])
    assistant_messages = [m for m in agent.messages if m.get("role") == "assistant"]
    candidates = [m.get("content") for m in assistant_messages]
    candidate = candidates[-1] if candidates else None
    ok = (result.get("exit_status") == "Submitted" and isinstance(candidate, str)
          and result.get("submission") == candidate.strip()
          and not any(m.get("tool_calls") or m.get("function_call") for m in assistant_messages))
    print(json.dumps({"type": "mini_swe_semantic_result", "exit_status": result.get("exit_status"),
        "candidate": candidate if ok else None, "agent_calls": agent.n_calls,
        "native_execution": False, "cost_authority": "parent_broker_only", "ok": ok}))
    return 0 if ok else 1


def extract_mini_swe_output(stdout, expected):
    for line in reversed(stdout.split("\n")):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (ValueError, RecursionError):
            return ""
        if (isinstance(row, dict) and row.get("type") == "mini_swe_semantic_result"
                and row.get("ok") is True and row.get("native_execution") is False
                and row.get("exit_status") == "Submitted" and row.get("candidate") == expected):
            return expected
        return ""
    return ""


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--execute-semantic":
        raise SystemExit("exact semantic adapter invocation required")
    raise SystemExit(execute_semantic(sys.argv[2]))
