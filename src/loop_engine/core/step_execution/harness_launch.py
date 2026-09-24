"""Start one declared harness for one step attempt, in a fresh folder and a sandbox.

Owns the attempt's launch folder (an empty home, the harness's own
configuration folder, the step folder holding the step's material at the
manifest's native places, the capture folder and the input and output files),
the LaunchPlan, the Bubblewrap arguments, the parent's side of the loopback
model endpoint (the broker socket, the model identity, the native tools rule
and the model-call ceiling), and the reading of a declared output. Every
attempt gets a new folder that is never reused. The sandbox shares no network,
mounts the system read-only, mounts only the harness software the host
installation pins, and lets the harness write only its launch folder; the
wall-time limit is enforced by killing the whole process group.
Belongs to the step execution component (roadmap S-6.31, S-6.42). Does not
own selection, the step edge, qualification or any grant: the step's
authority decides whether a broker is bound at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import secrets
import select
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time

from ..configuration_capabilities import digest
from ..engines.records import EngineRecordError
from ..harness_fresh_instances import FreshInstanceLayout, configuration_files
from . import harness_manifest as manifests

BUBBLEWRAP = "/usr/bin/bwrap"
SYSTEM_PYTHON = "/usr/bin/python3"
#: The fixed places inside the sandbox; the host launch folder is mounted at LAUNCH.
LAUNCH = "/launch"
INSIDE = {"empty_home": LAUNCH + "/home", "configuration_folder": LAUNCH + "/configuration",
          "step_folder": LAUNCH + "/step", "step_request_file": LAUNCH + "/io/request.json",
          "step_result_file": LAUNCH + "/io/result.json"}
ENDPOINT_PORT = 18080
MODEL_BASE_URL = f"http://127.0.0.1:{ENDPOINT_PORT}/v1"
#: A fixed, obviously fake credential: the step's harness speaks only to the loopback relay.
LOOPBACK_CREDENTIAL = "loopback-relay-no-secret"
MAXIMUM_OUTPUT_BYTES = 1024 * 1024
MAXIMUM_REQUEST_BYTES = 4 * 1024 * 1024
#: Configuration writers a step launch supports today; the others always declare a
#: protocol server and wait for step protocol-server material (roadmap S-6.44).
STEP_CONFIGURATION_WRITERS = ("none", "pi_models_json")
ENDPOINT_MODES = ("none", "no_model", "broker")
_SYSTEM_FILES = ("/etc/ssl", "/etc/ld.so.cache", "/etc/passwd", "/etc/group", "/etc/nsswitch.conf")


def tree_digest(path: Path) -> str:
    """Content-pin software, including symbolic link targets, without importing it."""
    value = hashlib.sha256()
    root = path.resolve(strict=True)
    entries = [root] if root.is_file() else sorted(root.rglob("*"))
    for entry in entries:
        relative = entry.name if root.is_file() else entry.relative_to(root).as_posix()
        value.update(relative.encode("utf-8") + b"\x00")
        if entry.is_symlink():
            value.update(b"link:" + os.readlink(entry).encode("utf-8"))
        elif entry.is_file():
            with entry.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    value.update(chunk)
        value.update(b"\x00")
    return value.hexdigest()


def sandbox_available() -> bool:
    return Path(BUBBLEWRAP).is_file() and Path(SYSTEM_PYTHON).is_file()


@dataclass(frozen=True)
class HarnessSoftware:
    """What a host installation pins: the program's real path and the read-only software mounts."""

    executable: str
    software_paths: tuple
    identities: tuple = field(default=(), compare=False)

    def __post_init__(self):
        for value in (self.executable,) + tuple(self.software_paths):
            path = Path(value)
            if not path.is_absolute() or ".." in path.parts or len(path.parts) < 3:
                raise EngineRecordError("invalid_path", "software is named by exact absolute paths")
            if path.parts[1] in ("etc", "proc", "dev", "run", "sys", "tmp"):
                raise EngineRecordError("invalid_path", "a software mount is too broad")
        object.__setattr__(self, "software_paths", tuple(self.software_paths))

    def pinned(self) -> "HarnessSoftware":
        """The same software with the digest of every mount, read now."""
        paths = sorted({self.executable, *self.software_paths})
        return HarnessSoftware(self.executable, self.software_paths,
                               tuple((item, tree_digest(Path(item))) for item in paths))

    def changed_since(self, earlier: "HarnessSoftware") -> bool:
        return self.pinned().identities != earlier.identities

    def present(self) -> bool:
        return all(Path(item).exists() for item in (self.executable, *self.software_paths))


@dataclass(frozen=True)
class LaunchFolder:
    """One attempt's fresh folder on the host; mounted at LAUNCH inside the sandbox."""

    root: Path

    @classmethod
    def create(cls, work_root: Path) -> "LaunchFolder":
        work_root.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="launch-", dir=str(work_root)))
        for name in ("home", "configuration", "step", "capture", "io"):
            (root / name).mkdir()
        return cls(root)

    def host(self, inside: str) -> Path:
        return self.root / inside[len(LAUNCH) + 1:]


def _write_new(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as handle:
        handle.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def step_instructions(request) -> str:
    """The step's instruction file: its goal, instructions, inputs and output ports."""
    lines = ["# Step instructions", "", request.goal.strip(), ""]
    if request.instructions.strip():
        lines += [request.instructions.strip(), ""]
    for item in request.material:
        if item.kind == "instruction_file":
            lines += [f"## {item.name}", "", item.body.strip(), ""]
    if request.inputs:
        lines += ["## Inputs", ""]
        for item in request.inputs:
            lines += [f"### {item.name} ({item.media_type})", "", item.text, ""]
    lines += ["## Output", ""]
    lines += [f"- {port.name}: {port.media_type}" for port in request.output_ports]
    return "\n".join(lines).rstrip() + "\n"


def skill_file(item) -> str:
    """A skill file with the name and description header Agent Skills clients read."""
    body = item.body.strip()
    if body.startswith("---\n"):
        return body + "\n"
    purpose = next((line.strip() for line in body.splitlines() if line.strip()), item.name)[:200]
    return f"---\nname: {item.name}\ndescription: {purpose}\n---\n\n{body}\n"


def place_material(folder: LaunchFolder, manifest, request, *, model_name: str) -> dict:
    """Write the instruction files, skills and configuration; return each placed file's digest."""
    placed = {}
    instructions = step_instructions(request)
    for name, body in manifest.layout.instruction_files:
        text = instructions if body == "step_instructions" else "@AGENTS.md\n"
        placed["step/" + name] = _write_new(folder.host(INSIDE["step_folder"]) / name, text)
    for item in request.material:
        if item.kind == "skill":
            if manifest.layout.skills_directory is None:
                raise EngineRecordError("material_has_no_place", "the manifest names no skill folder")
            relative = f"step/{manifest.layout.skills_directory}/{item.name}/SKILL.md"
            placed[relative] = _write_new(folder.root / relative, skill_file(item))
        elif item.kind == "protocol_server":
            raise EngineRecordError("material_has_no_place", "protocol server material is not placed yet")
    writer = manifest.launch.configuration_writer
    if writer not in STEP_CONFIGURATION_WRITERS:
        raise EngineRecordError("configuration_writer_not_supported_for_steps", writer)
    layout = FreshInstanceLayout(
        empty_home=INSIDE["empty_home"], configuration_folder=INSIDE["configuration_folder"],
        step_folder=INSIDE["step_folder"], step_parent=LAUNCH, model_origin=MODEL_BASE_URL[:-3],
        model_name=model_name, model_credential=LOOPBACK_CREDENTIAL, probe_prompt="step",
        protocol_server_name="baltor_step", protocol_server_command=(SYSTEM_PYTHON,),
        model_context_capacity=32768, model_output_capacity=4096)
    for inside, text in configuration_files(manifest.launch, layout):
        relative = inside[len(LAUNCH) + 1:]
        placed[relative] = _write_new(folder.root / relative, text)
    return placed


def template_values(folder: LaunchFolder, software: HarnessSoftware, *, model_name: str, prompt: str) -> dict:
    return {**INSIDE, "model_base_url": MODEL_BASE_URL, "model_name": model_name,
            "model_credential": LOOPBACK_CREDENTIAL, "step_prompt": prompt,
            "software_root": software.software_paths[0] if software.software_paths else software.executable}


@dataclass(frozen=True)
class LaunchPlan:
    """Everything one sandboxed start needs, digested into its identities."""

    folder: LaunchFolder
    command: tuple
    environment: tuple
    software: HarnessSoftware
    endpoint_mode: str
    model_wire: str
    model_name: str
    timeout_seconds: float
    model_call_ceiling: "int | None"
    refuse_native_tools: bool
    stdin_inside: str = ""
    decoy_binds: tuple = ()

    def __post_init__(self):
        if self.endpoint_mode not in ENDPOINT_MODES:
            raise EngineRecordError("invalid_field", "unknown endpoint mode")
        if self.endpoint_mode != "none" and self.model_wire == "none":
            raise EngineRecordError("invalid_field", "a model endpoint serves a declared wire")


def _relay_files(model_wire: str) -> tuple:
    """(host path, name) of the relay and of the codec module the declared wire needs."""
    from .. import harness_process_relay
    from ..harness_recipes import release_recipe_catalog
    relay = Path(harness_process_relay.__file__)
    files = [(relay, "harness_process_relay.py")]
    codecs = []
    if model_wire != "none":
        catalog = release_recipe_catalog()
        codec = next((item for item in catalog.wire_codecs if item.wire_protocol == model_wire), None)
        if codec is None:
            raise EngineRecordError("model_wire_not_served", model_wire)
        codecs.append(codec.to_dict())
        if codec.module is not None:
            files.append((relay.parent / (codec.module + ".py"), codec.module + ".py"))
    return tuple(files), tuple(codecs)


def sandbox_arguments(plan: LaunchPlan, *, config_path: Path, socket_path: "Path | None") -> list:
    """The complete Bubblewrap command line for one attempt."""
    endpoint = Path(__file__).with_name("harness_endpoint.py")
    args = [BUBBLEWRAP, "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    for path in _SYSTEM_FILES:
        if Path(path).exists():
            args += ["--ro-bind", path, path]
    for path in sorted({plan.software.executable, *plan.software.software_paths}):
        args += ["--ro-bind", path, path]
    args += ["--bind", str(plan.folder.root), LAUNCH, "--ro-bind", str(endpoint), "/relay/run.py",
             "--ro-bind", str(config_path), "/relay/config.json"]
    # Decoys go on top of the launch folder, so one beside the step is not hidden by it.
    for source, target in plan.decoy_binds:
        args += ["--ro-bind", str(source), str(target)]
    relay_files, _ = _relay_files(plan.model_wire)
    for host, name in relay_files:
        args += ["--ro-bind", str(host), "/relay/" + name]
    if socket_path is not None:
        args += ["--ro-bind", str(socket_path), "/relay/broker.sock"]
    args += ["--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8",
             "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--chdir", INSIDE["step_folder"],
             "--", SYSTEM_PYTHON, "-s", "-B", "/relay/run.py"]
    return args


def _endpoint_config(plan: LaunchPlan) -> dict:
    relay_files, codecs = _relay_files(plan.model_wire)
    return {"mode": plan.endpoint_mode, "port": ENDPOINT_PORT, "model": plan.model_name,
            "recipe": {"wire_protocols": [plan.model_wire] if plan.model_wire != "none" else []},
            "wire_codecs": list(codecs), "timeout_seconds": plan.timeout_seconds,
            "maximum_request_bytes": MAXIMUM_REQUEST_BYTES, "maximum_response_bytes": MAXIMUM_REQUEST_BYTES,
            "relay_sha256": hashlib.sha256(relay_files[0][0].read_bytes()).hexdigest(),
            "command": list(plan.command), "environment": dict(plan.environment),
            "cwd": INSIDE["step_folder"], "stdin": plan.stdin_inside, "capture": LAUNCH + "/capture",
            "stdout": LAUNCH + "/io/stdout.txt", "stderr": LAUNCH + "/io/stderr.txt",
            "exit": LAUNCH + "/io/exit.json"}


def process_identity(plan: LaunchPlan, manifest_digest: str) -> str:
    """Digest what was started: the program, arguments, environment, pinned software and relay."""
    relay_files, _ = _relay_files(plan.model_wire)
    return digest({"record_type": "step_harness_process/v1", "manifest_digest": manifest_digest,
                   "command": list(plan.command), "environment": dict(plan.environment),
                   "software": [list(item) for item in plan.software.identities],
                   "endpoint": hashlib.sha256(Path(__file__).with_name("harness_endpoint.py").read_bytes())
                   .hexdigest(),
                   "relay": [hashlib.sha256(host.read_bytes()).hexdigest() for host, _ in relay_files]})


def sandbox_profile_digest(arguments: list, plan: LaunchPlan, config_path: Path, socket_path) -> str:
    """Digest the sandbox profile with the attempt's own paths written as placeholders."""
    replacements = {str(plan.folder.root): "<launch>", str(config_path): "<config>"}
    if socket_path is not None:
        replacements[str(socket_path)] = "<broker>"
    return digest([replacements.get(item, item) for item in arguments])


@dataclass
class LaunchOutcome:
    """What the parent observed; the harness's own claims are read separately."""

    exit_code: "int | None"
    timed_out: bool
    stdout: str
    stderr: str
    captured_requests: tuple
    exchanges: list
    model_calls: int
    input_tokens: "int | None"
    output_tokens: "int | None"
    refusals: list
    elapsed_seconds: float
    process_identity: str
    sandbox_profile_digest: str


def _broker_answer(plan: LaunchPlan, broker, request: dict, state: dict) -> dict:
    """Admit one model request on the parent's side, or refuse it with a code."""
    if request.get("model") != plan.model_name:
        return {"error": {"message": "model broker refused request", "code": "request_identity_mismatch"}}
    if plan.refuse_native_tools and (request.get("tools") or request.get("functions")):
        return {"error": {"message": "model broker refused request", "code": "native_tools_not_authorized"}}
    if plan.model_call_ceiling is not None and state["calls"] >= plan.model_call_ceiling:
        return {"error": {"message": "model broker refused request", "code": "model_call_budget_exhausted"}}
    forwarded = {key: value for key, value in request.items() if key != "_harness_wire"}
    forwarded["stream"] = False
    state["calls"] += 1
    answer = broker(forwarded)
    usage = answer.get("usage") if isinstance(answer, dict) else None
    for name, field_name in (("input", "prompt_tokens"), ("output", "completion_tokens")):
        value = usage.get(field_name) if isinstance(usage, dict) else None
        state[name] = None if value is None or state[name] is None else state[name] + value
    return answer if isinstance(answer, dict) else {"error": {"message": "broker answer is not an object"}}


def _serve_broker(listener, process, plan, broker, state, deadline):
    from ..harness_process_relay import _decode, _receive
    while process.poll() is None and time.monotonic() < deadline:
        if not select.select([listener], [], [], 0.05)[0]:
            continue
        client, _ = listener.accept()
        with client:
            client.settimeout(min(5.0, plan.timeout_seconds))
            try:
                size = int.from_bytes(_receive(client, 8), "big")
                if not 0 < size <= MAXIMUM_REQUEST_BYTES:
                    raise ValueError("request_byte_limit")
                request = _decode(_receive(client, size))
                answer = _broker_answer(plan, broker, request, state) if isinstance(request, dict) else {
                    "error": {"message": "request is not an object"}}
            except Exception as exc:
                state["refusals"].append(type(exc).__name__)
                answer = {"error": {"message": "model broker refused request"}}
            if "error" in answer and answer["error"].get("code"):
                state["refusals"].append(answer["error"]["code"])
            data = json.dumps(answer, ensure_ascii=False, allow_nan=False).encode("utf-8")
            state["exchanges"].append(hashlib.sha256(data).hexdigest())
            try:
                client.sendall(len(data).to_bytes(8, "big") + data)
            except OSError:
                state["refusals"].append("relay_disconnected")


def _read_bounded(path: Path) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as handle:
        data = handle.read(MAXIMUM_OUTPUT_BYTES + 1)
    return data[:MAXIMUM_OUTPUT_BYTES].decode("utf-8", errors="replace")


def launch(plan: LaunchPlan, *, manifest_digest: str, broker=None) -> LaunchOutcome:
    """Start the sandbox, serve the broker, stop everything at the deadline, and read what happened."""
    if not sandbox_available():
        raise EngineRecordError("sandbox_unavailable", "Bubblewrap and the system Python are required")
    if plan.endpoint_mode == "broker" and not callable(broker):
        raise EngineRecordError("broker_required", "a broker endpoint needs the owning Loop's broker")
    config_path = plan.folder.root.parent / (plan.folder.root.name + "-relay.json")
    config_path.write_text(json.dumps(_endpoint_config(plan)), encoding="utf-8")
    state = {"calls": 0, "input": 0, "output": 0, "exchanges": [], "refusals": []}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="le-sh-", dir=_socket_root(plan)) as sockets:
        socket_path = Path(sockets) / "broker.sock" if plan.endpoint_mode == "broker" else None
        listener = None
        if socket_path is not None:
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(socket_path))
            os.chmod(socket_path, 0o600)
            listener.listen(4)
        arguments = sandbox_arguments(plan, config_path=config_path, socket_path=socket_path)
        process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE, env={"PATH": "/usr/bin:/bin"}, start_new_session=True)
        deadline = started + plan.timeout_seconds + 10
        timer = threading.Timer(plan.timeout_seconds + 10, lambda: _kill(process))
        timer.start()
        try:
            if listener is not None:
                _serve_broker(listener, process, plan, broker, state, deadline)
            process.wait()
        finally:
            timer.cancel()
            _kill(process)
            process.wait()
            sandbox_error = process.stderr.read(4096).decode("utf-8", errors="replace")
            process.stderr.close()
            if listener is not None:
                listener.close()
    exit_record = plan.folder.host(LAUNCH + "/io/exit.json")
    ended = json.loads(exit_record.read_text("utf-8")) if exit_record.is_file() else {
        "exit_code": None, "timed_out": True}
    captured = tuple(path.read_text("utf-8", errors="replace")
                     for path in sorted(plan.folder.host(LAUNCH + "/capture").glob("request-*.json")))
    if sandbox_error and not exit_record.is_file():
        state["refusals"].append("sandbox_failed")
    return LaunchOutcome(
        ended.get("exit_code"), bool(ended.get("timed_out")), _read_bounded(plan.folder.host(LAUNCH + "/io/stdout.txt")),
        _read_bounded(plan.folder.host(LAUNCH + "/io/stderr.txt")), captured, state["exchanges"], state["calls"],
        state["input"], state["output"], state["refusals"], round(time.monotonic() - started, 6),
        process_identity(plan, manifest_digest), sandbox_profile_digest(arguments, plan, config_path, socket_path))


#: A Unix socket path must stay under the operating system's limit of about 108 bytes.
SOCKET_PATH_LIMIT = 100


def _socket_root(plan: LaunchPlan) -> str:
    """A folder short enough for the broker socket: the launch folder's parent, else the temporary folder."""
    for candidate in (str(plan.folder.root.parent), tempfile.gettempdir(), "/tmp"):
        if len(os.fsencode(candidate)) + len("/le-sh-xxxxxxxx/broker.sock") < SOCKET_PATH_LIMIT \
                and os.path.isdir(candidate):
            return candidate
    raise EngineRecordError("socket_path_too_long", "no folder is short enough for the broker socket")


def _kill(process) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def read_output(completion, stdout: str, result_text: str) -> "tuple[str | None, str]":
    """The answer text a manifest's completion rule reads, or None with the reason."""
    if completion.output_format == manifests.TEXT:
        text = stdout.strip()
        return (text, "") if text else (None, "empty_harness_output")
    if completion.output_format == manifests.STEP_RESULT_JSON:
        return (result_text, "") if result_text.strip() else (None, "missing_step_result")
    try:
        documents = ([json.loads(line) for line in stdout.splitlines() if line.strip()]
                     if completion.output_format == manifests.JSON_LINES else [json.loads(stdout)])
    except (ValueError, RecursionError):
        return None, "invalid_harness_output"
    if completion.output_format == manifests.JSON_LINES:
        documents = [item for item in documents if isinstance(item, dict)
                     and item.get(completion.event_field) == completion.event_value]
    if not documents:
        return None, "no_output_event"
    chosen = documents[-1] if completion.occurrence == "last" else documents[0]
    value = resolve_pointer(chosen, completion.text_pointer)
    return (value, "") if isinstance(value, str) and value.strip() else (None, "output_not_text")


def resolve_pointer(document, pointer: str):
    """An RFC 6901 JSON pointer; a missing member reads as None, never as an empty text."""
    value = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            value = value.get(token)
        elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
            value = value[int(token)]
        else:
            return None
    return value


def new_attempt_token() -> str:
    return secrets.token_hex(8)


def remove_folder(folder: LaunchFolder) -> None:
    """Remove one attempt's folder after its result is recorded; never another attempt's."""
    shutil.rmtree(folder.root, ignore_errors=True)
    config = folder.root.parent / (folder.root.name + "-relay.json")
    if config.is_file():
        config.unlink()


def self_test():
    """Run the step execution checks, which cover the launcher."""
    from .engines_checks import self_test as run_engine_checks
    return run_engine_checks()
