"""Run one pinned OpenCode process for one pilot trial inside a Bubblewrap sandbox.

Both arms use this module unchanged. The sandbox sees only the system folders
(read only), the shared Python environment (read only), the pinned OpenCode
binary (read only) and the trial's own home folder, which holds the project
the harness works on. The hidden acceptance material, the repository and the
rest of the workstation home are not mounted, so the harness cannot read them.

The model is reached through the counting proxy on the loopback address; the
provider key never enters the sandbox. Every proxy variable points at the
trial's egress proxy. The only configuration difference between the arms is
the Baltor connection entry that the published OpenCode quickstart adds, and
the Baltor key in the environment of the Baltor arm.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

SANDBOX_HOME = "/home/dev"
SANDBOX_PROJECT = SANDBOX_HOME + "/project"
OPENCODE_IN_SANDBOX = "/opt/opencode/opencode"
PROVIDER_ID = "ollama-cloud"


def opencode_config(meter_port, trial_id, model, baltor_entry=None, context_limit=262144, output_limit=32768):
    """The trial's opencode.json. `baltor_entry` is the quickstart's `mcp.baltor` object or None."""
    config = {
        "$schema": "https://opencode.ai/config.json",
        "autoupdate": False,
        "share": "disabled",
        "model": f"{PROVIDER_ID}/{model}",
        "small_model": f"{PROVIDER_ID}/{model}",
        "enabled_providers": [PROVIDER_ID],
        "provider": {
            PROVIDER_ID: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama Cloud",
                "options": {
                    "baseURL": f"http://127.0.0.1:{meter_port}/trial/{trial_id}/v1",
                    # The counting proxy replaces this with the provider key; the key never enters the sandbox.
                    "apiKey": "replaced-by-the-counting-proxy",
                    "includeUsage": True,
                },
                "models": {model: {"name": model, "tool_call": True,
                                   "limit": {"context": context_limit, "output": output_limit}}},
            }
        },
        "permission": {"edit": "allow", "bash": "allow", "webfetch": "deny",
                       "external_directory": "allow", "doom_loop": "allow"},
    }
    if baltor_entry is not None:
        config["mcp"] = {"baltor": baltor_entry}
    return config


def write_config(home, config):
    folder = Path(home) / ".config" / "opencode"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "opencode.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def sandbox_environment(proxy_port, python_env, extra_bin, pythonpath=None, baltor_token=None):
    proxy = f"http://127.0.0.1:{proxy_port}"
    env = {
        "HOME": SANDBOX_HOME, "USER": "dev", "LOGNAME": "dev", "SHELL": "/bin/bash",
        "PATH": f"{extra_bin}:{python_env}/bin:/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TERM": "dumb", "TMPDIR": "/tmp",
        "XDG_CONFIG_HOME": SANDBOX_HOME + "/.config", "XDG_DATA_HOME": SANDBOX_HOME + "/.local/share",
        "XDG_CACHE_HOME": SANDBOX_HOME + "/.cache", "XDG_STATE_HOME": SANDBOX_HOME + "/.local/state",
        "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
        "HTTP_PROXY": proxy, "HTTPS_PROXY": proxy, "ALL_PROXY": proxy,
        "http_proxy": proxy, "https_proxy": proxy, "all_proxy": proxy,
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
        "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_MODELS_FETCH": "1",
        "OPENCODE_DISABLE_LSP_DOWNLOAD": "1", "OPENCODE_DISABLE_SHARE": "1",
        "OPENCODE_DISABLE_CLAUDE_CODE": "1", "OPENCODE_DISABLE_AUTOCOMPACT": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    if baltor_token is not None:
        env["BALTOR_SERVICE_TOKEN"] = baltor_token
    return env


def bwrap_argv(trial_home, python_env, extra_bin, opencode_binary, command):
    """The sandbox command line. It carries no environment values, so no secret appears in a process listing:
    the environment is handed to bwrap itself, which passes it to the sandboxed process unchanged."""
    argv = ["bwrap", "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
            "--hostname", "dev", "--ro-bind", "/usr", "/usr", "--ro-bind", "/etc", "/etc"]
    argv += ["--symlink", "usr/bin", "/bin", "--symlink", "usr/sbin", "/sbin",
             "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
             "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
             "--ro-bind", str(python_env), str(python_env),
             "--ro-bind", str(extra_bin), str(extra_bin),
             "--ro-bind", str(opencode_binary), OPENCODE_IN_SANDBOX,
             "--bind", str(trial_home), SANDBOX_HOME,
             "--chdir", SANDBOX_PROJECT, "--"]
    return argv + list(command)


def _stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return process.wait()
    try:
        return process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        return process.wait()


def run(trial_home, python_env, extra_bin, opencode_binary, env, prompt, title, timeout_seconds,
        stdout_path, stderr_path, should_stop=None):
    """Run `opencode run` once. `should_stop()` is polled every second; when it returns a reason, such as the
    counting proxy refusing a request beyond the step's cap, the harness is stopped and the reason recorded."""
    command = [OPENCODE_IN_SANDBOX, "run", "--format", "json", "--title", title, "--dir", SANDBOX_PROJECT, prompt]
    argv = bwrap_argv(trial_home, python_env, extra_bin, opencode_binary, command)
    started = time.monotonic()
    stop_reason = None
    with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
        process = subprocess.Popen(argv, stdout=out, stderr=err, stdin=subprocess.DEVNULL, start_new_session=True,
                                   env=env)
        status = None
        while status is None:
            try:
                status = process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                if time.monotonic() - started > timeout_seconds:
                    stop_reason = "wall_clock_limit"
                elif should_stop is not None:
                    stop_reason = should_stop()
                if stop_reason:
                    status = _stop(process)
    return {"exit_status": status, "elapsed_seconds": round(time.monotonic() - started, 3),
            "timed_out": stop_reason == "wall_clock_limit", "stopped_by_runner": stop_reason,
            "sandbox_argv_without_prompt": argv[:-1], "environment_names": sorted(env)}


def shell_in_sandbox(trial_home, python_env, extra_bin, opencode_binary, env, script, timeout_seconds,
                     stdout_path, stderr_path):
    """Run a setup script in the same sandbox, used for the Baltor arm's published quickstart steps."""
    argv = bwrap_argv(trial_home, python_env, extra_bin, opencode_binary, ["/bin/bash", "-c", script])
    started = time.monotonic()
    with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
        try:
            completed = subprocess.run(argv, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                       timeout=timeout_seconds, env=env)
            status = completed.returncode
        except subprocess.TimeoutExpired:
            status = "timeout"
    return {"exit_status": status, "elapsed_seconds": round(time.monotonic() - started, 3)}
