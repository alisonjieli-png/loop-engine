"""Pinned process mechanics for an externally realized canonical Loop.

The caller owns Loop identity, model grants, budgets, and the broker callback.
This internal adapter provides isolated CLI mechanics only. It never discovers
credentials, selects a provider, qualifies a harness, or accepts a task result.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import math
import os
from pathlib import Path
import select
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from typing import Callable


class HarnessProcessError(ValueError):
    """A process identity, confinement, or transport contract was refused."""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _path_digest(path: Path) -> str:
    """Content-pin software, including symlink identities, without importing it."""
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(os.readlink(path).encode())
    root = path.resolve(strict=True)
    entries = [root] if root.is_file() else sorted(root.rglob("*"))
    for entry in entries:
        relative = entry.name if root.is_file() else entry.relative_to(root).as_posix()
        digest.update(relative.encode() + b"\x00")
        if entry.is_symlink():
            digest.update(b"link:" + os.readlink(entry).encode())
        elif entry.is_file():
            digest.update(b"file:")
            with entry.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            digest.update(b"directory")
        digest.update(b"\x00")
    return digest.hexdigest()


def _absolute(value):
    if (not isinstance(value, str) or not Path(value).is_absolute()
            or ".." in Path(value).parts or "\x00" in value):
        raise HarnessProcessError("process paths must be explicit absolute paths")
    return Path(value)


@dataclass(frozen=True)
class HarnessProcessSpec:
    """Explicit installed software, with frozen command and mount identities."""
    harness_id: str
    package_version: str
    command_prefix: tuple[str, ...]
    read_only_paths: tuple[str, ...]
    style: str
    software_identities: tuple[tuple[str, str], ...] = field(init=False)

    def __post_init__(self):
        from .harness_execution_contracts import valid_harness_id
        if (not valid_harness_id(self.harness_id) or not isinstance(self.package_version, str)
                or not self.package_version.strip() or self.style not in (
                    "aider", "continue", "pi", "qwen_code", "gemini_cli", "goose", "opencode",
                    "mini_swe_agent", "mistral_vibe", "gptme", "cline", "kilo",
                    "nanocode", "trae_agent", "codex", "openinterpreter_rust", "hermes_agent", "forgecode")):
            raise HarnessProcessError("exact harness identity and installed style are required")
        if (not isinstance(self.command_prefix, tuple) or not self.command_prefix
                or any(not isinstance(part, str) or not part or "\x00" in part for part in self.command_prefix)
                or not isinstance(self.read_only_paths, tuple)
                or len(set(self.read_only_paths)) != len(self.read_only_paths)):
            raise HarnessProcessError("command and mounts must be explicit unique tuples")
        executable = _absolute(self.command_prefix[0])
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise HarnessProcessError("harness executable is unavailable")
        paths = list(self.read_only_paths)
        for value in paths:
            path = _absolute(value)
            if (len(path.parts) < 4 or path.parts[1] in ("etc", "proc", "dev", "run", "sys")
                    or not path.exists()):
                raise HarnessProcessError("software mount is absent or too broad")
        paths.extend(part for part in self.command_prefix if part.startswith("/"))
        object.__setattr__(self, "software_identities", tuple(
            (value, _path_digest(_absolute(value))) for value in sorted(set(paths))))

    @property
    def digest(self):
        return _sha(_json({"record_type": "harness_process_spec/v1", "harness_id": self.harness_id,
            "package_version": self.package_version, "command_prefix": self.command_prefix,
            "read_only_paths": self.read_only_paths, "style": self.style,
            "software_identities": self.software_identities}).encode())

    def validate_unchanged(self):
        if any(_path_digest(Path(path)) != digest for path, digest in self.software_identities):
            raise HarnessProcessError("installed harness software changed after binding")


@dataclass(frozen=True)
class HarnessProcessRequest:
    spec: HarnessProcessSpec
    prompt: str = field(repr=False)
    model: str
    output_capacity: int
    output_allowance: int | None
    timeout_seconds: float
    work_dir: str
    maximum_output_bytes: int = 1024 * 1024
    maximum_request_bytes: int = 2 * 1024 * 1024
    maximum_response_bytes: int = 4 * 1024 * 1024
    maximum_request_history_bytes: int = 16 * 1024 * 1024
    context_capacity: int | None = None
    socket_directory: str = ""

    def __post_init__(self):
        if (not isinstance(self.spec, HarnessProcessSpec) or not isinstance(self.prompt, str)
                or not self.prompt or not isinstance(self.model, str) or not self.model.strip()):
            raise HarnessProcessError("typed spec, task, and exact model are required")
        for name in ("output_capacity", "maximum_output_bytes", "maximum_request_bytes",
                     "maximum_response_bytes", "maximum_request_history_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise HarnessProcessError(name + " must be a positive integer")
        if self.output_allowance is None:
            object.__setattr__(self, "output_allowance", self.output_capacity)
        if (type(self.output_allowance) is not int
                or not 0 < self.output_allowance <= self.output_capacity
                or type(self.timeout_seconds) not in (int, float)
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0):
            raise HarnessProcessError("invalid output allocation or process deadline")
        if self.context_capacity is not None and (
                type(self.context_capacity) is not int or self.context_capacity < 1):
            raise HarnessProcessError("context capacity must be explicitly source-backed")
        if self.spec.style == "pi" and self.context_capacity is None:
            raise HarnessProcessError("Pi model configuration needs an explicit context capacity")
        if len(self.prompt.encode("utf-8")) > self.maximum_request_bytes:
            raise HarnessProcessError("private task exceeds request byte allowance")
        work = _absolute(self.work_dir)
        if (len(work.parts) < 4 or not work.is_dir()
                or any(part.is_symlink() for part in (work, *work.parents))):
            raise HarnessProcessError("work directory must already exist without symlink traversal")
        for value in self.spec.read_only_paths:
            mount = Path(value)
            if work == mount or work in mount.parents or mount in work.parents:
                raise HarnessProcessError("software and writable work directories must be separate")
        socket_root = _absolute(self.socket_directory or self.work_dir)
        if (not socket_root.is_dir()
                or any(part.is_symlink() for part in (socket_root, *socket_root.parents))):
            raise HarnessProcessError("socket directory must exist without symlink traversal")
        if len(os.fsencode(str(socket_root))) + len("/le-hp-xxxxxxxx/broker.sock") >= 108:
            raise HarnessProcessError("Unix socket path is too long; supply a short socket_directory")


@dataclass(frozen=True)
class HarnessProcessExchange:
    """Private in-memory request evidence; public summaries use digests only."""
    request_json: str = field(repr=False)
    request_digest: str
    response_digest: str = ""
    error_code: str = ""
    broker_called: bool = False


@dataclass(frozen=True)
class HarnessProcessResult:
    exit_code: int | None
    timed_out: bool
    output: str = field(repr=False)
    stdout: str = field(repr=False)
    stderr: str = field(repr=False)
    errors: tuple[str, ...]
    process_identity: str
    elapsed_seconds: float
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    exchanges: tuple[HarnessProcessExchange, ...] = field(default=(), repr=False)

    @property
    def ok(self):
        return self.exit_code == 0 and not self.timed_out and not self.errors and bool(self.output)

    @property
    def broker_request_count(self):
        return sum(item.broker_called for item in self.exchanges)

    @property
    def received_request_count(self):
        return len(self.exchanges)


def _write_private(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
        handle.write(value)


def _sandbox(request, run, socket_path):
    relay = Path(__file__).with_name("harness_process_relay.py")
    args = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    for path in ("/etc/ssl", "/etc/ld.so.cache", "/etc/passwd", "/etc/group"):
        if Path(path).exists():
            args += ["--ro-bind", path, path]
    for path in request.spec.read_only_paths:
        args += ["--ro-bind", path, path]
    args += ["--bind", str(run / "work"), "/work", "--ro-bind", str(relay), "/relay/run.py",
             "--ro-bind", str(run / "config.json"), "/relay/config.json",
             "--ro-bind", str(run / "task.txt"), "/relay/task.txt",
             "--ro-bind", str(socket_path), "/relay/broker.sock"]
    additional = Path(__file__).with_name("harness_additional_recipes.py")
    args += ["--ro-bind", str(additional), "/relay/harness_additional_recipes.py"]
    goose = Path(__file__).with_name("harness_goose_recipe.py")
    args += ["--ro-bind", str(goose), "/relay/harness_goose_recipe.py"]
    opencode = Path(__file__).with_name("harness_opencode_recipe.py")
    args += ["--ro-bind", str(opencode), "/relay/harness_opencode_recipe.py"]
    for module in ("harness_mini_swe_recipe.py", "harness_python_recipes.py", "harness_cline_kilo_recipes.py",
                   "harness_lightweight_recipes.py", "harness_responses_recipes.py", "harness_remaining_recipes.py"):
        args += ["--ro-bind", str(Path(__file__).with_name(module)), "/relay/" + module]
    # The sandbox's own layout and consent switches are a typed, digest-bound
    # record; see harness_confinement for what each variable means.
    from .harness_confinement import default_confined_environment
    args += default_confined_environment().setenv_arguments()
    if request.spec.style == "aider":
        args += ["--setenv", "COLUMNS", str(request.maximum_output_bytes)]
    return args + ["--chdir", "/work", "--", "/usr/bin/python3", "/relay/run.py"]


def _output(style, stdout, last_response):
    if style in ("hermes_agent", "forgecode"):
        from .harness_remaining_recipes import extract_remaining_output
        choices = (last_response or {}).get("choices", [])
        expected = choices[-1].get("message", {}).get("content") if choices else None
        return extract_remaining_output(style, stdout, expected)
    if style in ("codex", "openinterpreter_rust"):
        from .harness_responses_recipes import extract_responses_output
        choices = (last_response or {}).get("choices", [])
        expected = choices[-1].get("message", {}).get("content") if choices else None
        return extract_responses_output(style, stdout, expected)
    if style in ("nanocode", "trae_agent"):
        from .harness_lightweight_recipes import extract_lightweight_output
        choices = (last_response or {}).get("choices", [])
        expected = choices[-1].get("message", {}).get("content") if choices else None
        return extract_lightweight_output(style, stdout, expected)
    if style in ("mini_swe_agent", "mistral_vibe", "gptme", "cline", "kilo"):
        choices = (last_response or {}).get("choices", [])
        expected = choices[-1].get("message", {}).get("content") if choices else None
        if style == "mini_swe_agent":
            from .harness_mini_swe_recipe import extract_mini_swe_output
            return extract_mini_swe_output(stdout, expected)
        if style in ("mistral_vibe", "gptme"):
            from .harness_python_recipes import extract_python_output
            return extract_python_output(style, stdout, expected)
        from .harness_cline_kilo_recipes import extract_cline_kilo_output
        return extract_cline_kilo_output(style, stdout, expected)
    if style == "opencode":
        from .harness_opencode_recipe import extract_opencode_output
        choices = (last_response or {}).get("choices", [])
        expected = choices[-1].get("message", {}).get("content") if choices else None
        return extract_opencode_output(stdout, expected)
    if style == "goose":
        from .harness_goose_recipe import extract_goose_output
        choices = (last_response or {}).get("choices", [])
        expected = choices[-1].get("message", {}).get("content") if choices else None
        return extract_goose_output(stdout, expected)
    if style in ("qwen_code", "gemini_cli"):
        from .harness_additional_recipes import extract_additional_output
        choices = (last_response or {}).get("choices", [])
        expected = choices[-1].get("message", {}).get("content") if choices else None
        return extract_additional_output(style, stdout, expected)
    choices = (last_response or {}).get("choices", [])
    content = choices[-1].get("message", {}).get("content") if choices else None
    if not isinstance(content, str) or not content:
        return ""
    if style == "continue":
        value = json.loads(stdout)
        if isinstance(value, dict) and value.get("status") == "success" and value.get("response") == content:
            return value["response"]
        # Continue returns valid JSON assistant output directly without a wrapper.
        if isinstance(value, (dict, list)) and value == json.loads(content):
            return stdout.strip()
    elif style == "aider":
        if content in stdout:
            start = stdout.rfind(content)
            return stdout[start:start + len(content)]
    elif style == "pi":
        for line in reversed(stdout.splitlines()):
            value = json.loads(line)
            if value.get("type") == "message_end" and value.get("message", {}).get("role") == "assistant":
                message = value["message"]
                actual = "".join(item["text"] for item in message.get("content", []) if item.get("type") == "text")
                return actual if actual == content and message.get("stopReason") == "stop" else ""
    return ""


def run_harness_process(request: HarnessProcessRequest,
                        broker: Callable[[dict], dict]) -> HarnessProcessResult:
    """Execute private text-only harness mechanics; broker stays on caller thread.

    Process cancellation kills and waits for the whole PID namespace. An
    already-dispatched broker callback must enforce its own provider deadline;
    process cancellation cannot undo or reclassify that physical model attempt.
    """
    if not isinstance(request, HarnessProcessRequest) or not callable(broker):
        raise HarnessProcessError("typed request and explicit model broker are required")
    request.spec.validate_unchanged()
    if shutil.which("bwrap") != "/usr/bin/bwrap":
        raise HarnessProcessError("qualified Bubblewrap executable is unavailable")
    from .harness_process_relay import _decode, _receive
    started = time.monotonic()
    run = Path(tempfile.mkdtemp(prefix="harness-", dir=request.work_dir))
    (run / "work" / "home").mkdir(parents=True)
    config = {name: getattr(request, name) for name in (
        "model", "output_capacity", "output_allowance", "timeout_seconds", "maximum_request_bytes",
        "maximum_response_bytes", "context_capacity")}
    config.update(command_prefix=request.spec.command_prefix, style=request.spec.style,
                  package_version=request.spec.package_version)
    _write_private(run / "config.json", _json(config).encode())
    _write_private(run / "task.txt", request.prompt.encode())
    identity = _sha(_json({"spec": request.spec.digest, "model": request.model,
        "output_capacity": request.output_capacity, "output_allowance": request.output_allowance,
        "prompt_digest": _sha(request.prompt.encode()), "context_capacity": request.context_capacity,
        "timeout_seconds": request.timeout_seconds, "run": str(run),
        "relay_digest": _path_digest(Path(__file__).with_name("harness_process_relay.py")),
        "codec_digest": _path_digest(Path(__file__).with_name("harness_additional_recipes.py")),
        "goose_recipe_digest": _path_digest(Path(__file__).with_name("harness_goose_recipe.py")),
        "opencode_recipe_digest": _path_digest(Path(__file__).with_name("harness_opencode_recipe.py")),
        "other_recipe_digests": {name: _path_digest(Path(__file__).with_name(name)) for name in (
            "harness_mini_swe_recipe.py", "harness_python_recipes.py", "harness_cline_kilo_recipes.py",
            "harness_lightweight_recipes.py", "harness_responses_recipes.py",
            "harness_remaining_recipes.py")}}).encode())
    errors, exchanges, buffers = [], [], [bytearray(), bytearray()]
    truncated, expired, stop = [False, False], threading.Event(), threading.Event()
    last_response, history_size = None, 0

    def drain(pipe, index):
        while True:
            data = pipe.read(65536)
            if not data:
                break
            left = max(0, request.maximum_output_bytes - len(buffers[index]))
            buffers[index].extend(data[:left])
            if len(data) > left:
                truncated[index] = True

    with tempfile.TemporaryDirectory(prefix="le-hp-", dir=request.socket_directory or request.work_dir) as socket_dir:
        socket_path = Path(socket_dir) / "broker.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(socket_path))
            os.chmod(socket_path, 0o600)
            listener.listen(4)
            proc = subprocess.Popen(_sandbox(request, run, socket_path),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={"PATH": "/usr/bin:/bin"}, start_new_session=True)

            def kill():
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

            def watchdog():
                if not stop.wait(request.timeout_seconds):
                    expired.set()
                    kill()

            readers = [threading.Thread(target=drain, args=(pipe, index), daemon=True)
                       for index, pipe in enumerate((proc.stdout, proc.stderr))]
            timer = threading.Thread(target=watchdog, daemon=True)
            for thread in (*readers, timer):
                thread.start()
            try:
                while proc.poll() is None and not expired.is_set():
                    if not select.select([listener], [], [], 0.05)[0]:
                        continue
                    client, _ = listener.accept()
                    with client:
                        client.settimeout(min(1.0, request.timeout_seconds))
                        entry = None
                        try:
                            size = int.from_bytes(_receive(client, 8), "big")
                            if not 0 < size <= request.maximum_request_bytes:
                                raise HarnessProcessError("request_byte_limit")
                            raw = _receive(client, size)
                            history_size += size
                            if history_size > request.maximum_request_history_bytes:
                                raise HarnessProcessError("request_history_byte_limit")
                            body = _decode(raw)
                            if not isinstance(body, dict):
                                raise HarnessProcessError("request_not_object")
                            serialized = _json(body)
                            entry = HarnessProcessExchange(serialized, _sha(serialized.encode()))
                            exchanges.append(entry)  # Retain the exact attempt before calling its broker.
                            if body.get("model") != request.model or not isinstance(body.get("messages"), list):
                                raise HarnessProcessError("request_identity_mismatch")
                            if body.get("tools") or body.get("functions"):
                                raise HarnessProcessError("native_tools_not_authorized")
                            forwarded = dict(body)
                            forwarded.pop("max_completion_tokens", None)
                            forwarded["max_tokens"] = request.output_allowance
                            forwarded["stream"] = False
                            exchanges[-1] = replace(entry, broker_called=True)
                            response = broker(forwarded)
                            if not isinstance(response, dict):
                                raise HarnessProcessError("broker_response_not_object")
                            data = _json(response).encode()
                            if len(data) > request.maximum_response_bytes:
                                raise HarnessProcessError("response_byte_limit")
                            exchanges[-1] = replace(exchanges[-1], response_digest=_sha(data))
                            choices = response.get("choices")
                            if (not isinstance(choices, list) or len(choices) != 1
                                    or not isinstance(choices[0], dict)
                                    or not isinstance(choices[0].get("message"), dict)
                                    or choices[0]["message"].get("role") != "assistant"
                                    or not isinstance(choices[0]["message"].get("content"), str)
                                    or choices[0]["message"].get("tool_calls")
                                    or choices[0]["message"].get("function_call")):
                                raise HarnessProcessError("broker_response_not_text")
                            last_response = response
                        except Exception as exc:
                            code = str(exc) if isinstance(exc, HarnessProcessError) else "broker_" + type(exc).__name__
                            errors.append(code)
                            if entry is not None:
                                exchanges[-1] = replace(exchanges[-1], error_code=code)
                            data = _json({"error": {"message": "model broker refused request", "code": code}}).encode()
                        try:
                            client.sendall(len(data).to_bytes(8, "big") + data)
                        except OSError:
                            errors.append("relay_disconnected")
                proc.wait()
            finally:
                kill()
                proc.wait()
                stop.set()
                for thread in (*readers, timer):
                    thread.join(timeout=2)
                proc.stdout.close()
                proc.stderr.close()
    from .workspace_contracts import _bounded_text
    decoded = [_bounded_text(bytes(value).decode("utf-8", errors="replace"),
                             request.maximum_output_bytes) for value in buffers]
    stdout, stderr = (value[0] for value in decoded)
    truncated = [original or value[1] for original, value in zip(truncated, decoded)]
    output = ""
    if not expired.is_set() and proc.returncode == 0 and not any(truncated):
        try:
            output = _output(request.spec.style, stdout, last_response)
        except (ValueError, TypeError, KeyError, RecursionError):
            errors.append("invalid_harness_output")
    if expired.is_set():
        errors.append("process_timeout")
    if any(truncated):
        errors.append("process_output_limit")
    if not output and not errors:
        errors.append("empty_harness_output" if proc.returncode == 0 else "process_failed")
    return HarnessProcessResult(proc.returncode, expired.is_set(), output, stdout, stderr,
        tuple(dict.fromkeys(errors)), identity, round(time.monotonic() - started, 6),
        *truncated, tuple(exchanges))
