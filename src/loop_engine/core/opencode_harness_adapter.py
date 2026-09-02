"""OpenCode as a Loop realization: one bounded headless run, normalized.

Architectural role: the first process-level external harness adapter. The
canonical ``Loop`` created by ``run_external_harness`` owns the goal,
contract, budget, evidence, and terminal vocabulary; this adapter is the
realization inside its one step. It performs a handshake (binary version and
model listing), renders the default starting intelligence for the harness
from the versioned prompt resource, runs ``opencode run --format json`` in an
isolated working directory, normalizes the raw JSON events into the
provider-neutral ``HarnessRunResult`` (model calls with tokens and cost, tool
events without bodies, changed files as artifact references, the raw event
stream stored by digest), and honors the request's wall-clock budget by
interrupting the process. It claims nothing about acceptance: the spawning
Loop verifies the result independently.

Owns:
    - OpenCodeProcessAdapter: the ExternalHarnessAdapter for OpenCode.
    - parse_opencode_events(): the deterministic event normalization.
    - render_opencode_message(): the packet-to-message rendering.

Does not own: the harness result contract (core.external_harness), the Loop
that wraps the run (core.external_harness.run_external_harness), or the
instruction text (strings.prompt_fragments).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .external_harness import (HarnessAdapterInfo, HarnessArtifactRef,
                               HarnessError, HarnessModelCall,
                               HarnessRunRequest, HarnessRunResult,
                               HarnessServices, HarnessToolEvent)

OPENCODE_HARNESS_ID = "opencode"
ADAPTER_VERSION = "1.0.0"
_DEFAULT_MAX_SECONDS = 600.0
_INTERRUPT_GRACE_SECONDS = 15.0
_IGNORED_DIRECTORIES = frozenset({".git", "__pycache__", "node_modules",
                                  ".opencode", ".venv"})
#: OpenCode tool names mapped to the LoopContract effect vocabulary.
_TOOL_EFFECTS = {
    "write": "writes_fs", "edit": "writes_fs", "patch": "writes_fs",
    "bash": "spawns_process", "task": "spawns_process",
    "read": "reads_fs", "glob": "reads_fs", "grep": "reads_fs",
    "list": "reads_fs", "webfetch": "network", "websearch": "network",
    "todowrite": "pure", "todoread": "pure",
}


class OpenCodeAdapterError(HarnessError):
    """The adapter could not honor the request as declared."""


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot(root: Path) -> dict:
    """Relative path to content digest for every regular file under root."""
    files = {}
    for path in root.rglob("*"):
        if any(part in _IGNORED_DIRECTORIES for part in path.parts):
            continue
        if path.is_file() and not path.is_symlink():
            try:
                files[str(path.relative_to(root))] = _digest_bytes(
                    path.read_bytes())
            except OSError:
                continue
    return files


def render_opencode_message(request: HarnessRunRequest) -> str:
    """Compose the message: default instructions, goal, contract, inputs."""
    from ..strings.prompt_fragments import external_harness_instruction_bundle
    instructions = external_harness_instruction_bundle(
        OPENCODE_HARNESS_ID).render({}, provenance={})
    instruction_text = getattr(instructions, "text", None) or str(instructions)
    contract = request.contract
    lines = [
        instruction_text.strip(),
        "",
        f"Task: {request.goal.strip()}",
        f"Input roles: {', '.join(contract.input_roles) or 'none'}.",
        f"Output roles: {', '.join(contract.output_roles) or 'result'}.",
    ]
    if request.input_data:
        lines.append("Inputs (JSON): " + json.dumps(
            dict(request.input_data), sort_keys=True, default=str))
    return "\n".join(lines)


@dataclass(frozen=True)
class ParsedOpenCodeEvents:
    """Normalized view of one headless run's JSON event stream."""

    texts: tuple
    model_calls: tuple
    tool_events: tuple
    session_id: str
    event_count: int
    unmapped_types: tuple
    final_json: "dict | None"


def _int(value) -> "int | None":
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_opencode_events(lines, *, provider_id: str, model_id: str
                          ) -> ParsedOpenCodeEvents:
    """Normalize raw ``opencode run --format json`` lines.

    A ``step_finish`` part is one physical model turn; its ``tokens`` object
    carries input, output, reasoning, and cache counts, and ``cost`` the
    provider-reported cost when known. ``text`` parts accumulate the model's
    visible output; the last text line that parses as a JSON object becomes
    ``final_json``. Tool parts become tool events with the effect class of
    the tool name and no bodies. Unknown event types are counted, never
    dropped silently.
    """
    texts, calls, tools, unmapped = [], [], [], {}
    session_id = ""
    count = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except ValueError:
            unmapped["unparsable_line"] = unmapped.get("unparsable_line", 0) + 1
            continue
        count += 1
        if not isinstance(event, dict):
            unmapped["non_object"] = unmapped.get("non_object", 0) + 1
            continue
        session_id = session_id or str(event.get("sessionID") or "")
        kind = str(event.get("type") or "")
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        if kind == "text":
            texts.append(str(part.get("text") or ""))
        elif kind == "step_finish":
            tokens = part.get("tokens") if isinstance(part.get("tokens"), dict) else {}
            cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
            input_tokens = _int(tokens.get("input"))
            if input_tokens is not None:
                input_tokens += (_int(cache.get("read")) or 0)
            output_tokens = _int(tokens.get("output"))
            if output_tokens is not None:
                output_tokens += (_int(tokens.get("reasoning")) or 0)
            cost = part.get("cost")
            calls.append(HarnessModelCall(
                provider_id, model_id, str(part.get("reason") or "") != "error",
                input_tokens=input_tokens, output_tokens=output_tokens,
                cost=float(cost) if isinstance(cost, (int, float)) else None,
                error_code="" if str(part.get("reason") or "") != "error"
                else "step_error"))
        elif kind in ("tool", "tool_use", "tool_result") or str(
                part.get("type") or "").startswith("tool"):
            name = str(part.get("tool") or part.get("name") or "tool")
            state = part.get("state") if isinstance(part.get("state"), dict) else {}
            payload = json.dumps(state.get("input", {}), sort_keys=True,
                                 default=str).encode("utf-8")
            tools.append(HarnessToolEvent(
                name, str(state.get("status") or kind),
                effect=_TOOL_EFFECTS.get(name, "unknown"),
                input_digest=_digest_bytes(payload)))
        elif kind in ("step_start", "session", "message", "reasoning"):
            continue
        else:
            unmapped[kind or "untyped"] = unmapped.get(kind or "untyped", 0) + 1
    final_json = None
    for text in reversed(texts):
        candidate = text.strip().splitlines()[-1] if text.strip() else ""
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                parsed = json.loads(candidate)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                final_json = parsed
                break
    return ParsedOpenCodeEvents(
        tuple(texts), tuple(calls), tuple(tools), session_id, count,
        tuple(sorted(unmapped.items())), final_json)


@dataclass
class OpenCodeProcessAdapter:
    """Run OpenCode headlessly for one bounded request."""

    binary: str = "opencode"
    auto_approve: bool = True
    listed_models: "tuple | None" = None
    version_timeout_seconds: float = 20.0
    _version: str = field(default="", init=False, repr=False)

    def _binary_path(self) -> "str | None":
        return shutil.which(self.binary) if not os.path.isabs(
            self.binary) else (self.binary if os.path.exists(self.binary)
                               else None)

    def _read_version(self) -> str:
        if self._version:
            return self._version
        path = self._binary_path()
        if path is None:
            return ""
        try:
            completed = subprocess.run(
                [path, "--version"], capture_output=True, text=True,
                timeout=self.version_timeout_seconds)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        self._version = (completed.stdout.strip().splitlines() or [""])[-1]
        return self._version

    def _models(self) -> tuple:
        if self.listed_models is not None:
            return tuple(self.listed_models)
        path = self._binary_path()
        if path is None:
            return ()
        try:
            completed = subprocess.run(
                [path, "models"], capture_output=True, text=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired):
            return ()
        return tuple(line.strip() for line in completed.stdout.splitlines()
                     if "/" in line and not line.startswith(" "))

    def info(self) -> HarnessAdapterInfo:
        path = self._binary_path()
        version = self._read_version() if path else ""
        return HarnessAdapterInfo(
            harness_id=OPENCODE_HARNESS_ID, adapter_version=ADAPTER_VERSION,
            package_name="opencode", package_version=version,
            features=("headless_json_events", "isolated_directory",
                      "model_listing_handshake", "wall_clock_cancellation",
                      "changed_file_artifacts"),
            limitations=(
                "tool events carry names, states, and input digests, not "
                "bodies",
                "permissions inside the isolated directory are "
                "auto-approved when auto_approve is set",
                "the harness's own model turns cannot be capped from outside; "
                "the Loop budget marks an overrun after the fact",
                "session resume and fork are not exercised"),
            available=path is not None and bool(version),
            availability_reason=("" if path and version
                                 else f"{self.binary} binary not found or "
                                      "did not report a version"))

    def run(self, request: HarnessRunRequest,
            services: HarnessServices) -> HarnessRunResult:
        info = self.info()
        base = dict(request_id=request.request_id,
                    harness_id=OPENCODE_HARNESS_ID,
                    adapter_version=ADAPTER_VERSION,
                    provider_id=request.provider_id, model_id=request.model_id)
        if not info.available:
            return HarnessRunResult(status="unavailable",
                                    error_code="binary_unavailable",
                                    error=info.availability_reason, **base)
        if not request.provider_id or not request.model_id:
            return HarnessRunResult(status="refused",
                                    error_code="model_required",
                                    error="an OpenCode run needs provider_id "
                                          "and model_id", **base)
        model = f"{request.provider_id}/{request.model_id}"
        listed = self._models()
        if model not in listed:
            return HarnessRunResult(
                status="refused", error_code="model_not_listed",
                error=f"{model} is not in the harness model listing "
                      f"({len(listed)} models listed)", **base)
        workspace = Path(request.workspace_ref) if request.workspace_ref else None
        if workspace is None or not workspace.is_dir():
            return HarnessRunResult(
                status="refused", error_code="workspace_required",
                error="workspace_ref must name an existing isolated "
                      "directory", **base)
        before = _snapshot(workspace)
        message = render_opencode_message(request)
        command = [self._binary_path(), "run", "--format", "json",
                   "--dir", str(workspace), "-m", model,
                   "--title", request.request_id[:48]]
        if self.auto_approve:
            command.append("--auto")
        command.append(message)
        deadline = float(request.budget.max_seconds or _DEFAULT_MAX_SECONDS)
        started = time.monotonic()
        process = subprocess.Popen(
            command, cwd=str(workspace), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        status = "completed"
        error_code = ""
        error = ""
        try:
            stdout, stderr = process.communicate(timeout=deadline)
        except subprocess.TimeoutExpired:
            process.send_signal(signal.SIGINT)
            try:
                stdout, stderr = process.communicate(
                    timeout=_INTERRUPT_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            status, error_code = "cancelled", "deadline_exceeded"
            error = (f"opencode did not finish within {deadline:.0f} s; "
                     "interrupted")
        elapsed = round(time.monotonic() - started, 3)
        parsed = parse_opencode_events(
            stdout.splitlines(), provider_id=request.provider_id,
            model_id=request.model_id)
        if status == "completed" and process.returncode != 0:
            status, error_code = "failed", "harness_exit_nonzero"
            error = (stderr.strip().splitlines() or [f"exit {process.returncode}"])[-1][:200]
        if status == "completed" and not parsed.model_calls:
            status, error_code = "failed", "no_model_turn_reported"
            error = "the harness reported no completed model turn"
        raw_ref = ""
        if services.artifact_store is not None and stdout:
            stored = services.artifact_store.store.put(
                stdout.encode("utf-8"), media_type="application/x-ndjson",
                encoding="utf-8", artifact_kind="external_harness_raw_events")
            raw_ref = stored.object_key
        after = _snapshot(workspace)
        artifacts = tuple(
            HarnessArtifactRef(
                artifact_id=relative, uri=(workspace / relative).resolve().as_uri(),
                digest=digest, media_type="text/plain",
                size_bytes=(workspace / relative).stat().st_size)
            for relative, digest in sorted(after.items())
            if before.get(relative) != digest)
        inputs = [c.input_tokens for c in parsed.model_calls]
        outputs = [c.output_tokens for c in parsed.model_calls]
        costs = [c.cost for c in parsed.model_calls]
        return HarnessRunResult(
            status=status, error_code=error_code, error=error,
            output={"session_id": parsed.session_id,
                    "text": "\n".join(parsed.texts)[-4000:],
                    "final_json": parsed.final_json,
                    "unmapped_event_types": list(parsed.unmapped_types),
                    "changed_files": [item.artifact_id for item in artifacts]},
            model_calls=parsed.model_calls, tool_events=parsed.tool_events,
            artifacts=artifacts, raw_events_ref=raw_ref,
            elapsed_seconds=elapsed, call_count_complete=True,
            reported_model_call_count=len(parsed.model_calls),
            aggregate_input_tokens=(sum(inputs) if inputs and all(
                v is not None for v in inputs) else None),
            aggregate_output_tokens=(sum(outputs) if outputs and all(
                v is not None for v in outputs) else None),
            aggregate_cost=(sum(costs) if costs and all(
                v is not None for v in costs) else None),
            **base)


_FIXTURE_EVENTS = (
    '{"type":"step_start","timestamp":1,"sessionID":"ses_fixture","part":'
    '{"id":"prt_1","messageID":"msg_1","sessionID":"ses_fixture",'
    '"type":"step-start"}}',
    '{"type":"tool","timestamp":2,"sessionID":"ses_fixture","part":'
    '{"id":"prt_2","type":"tool","tool":"write","state":{"status":"completed",'
    '"input":{"filePath":"tiny_math.py"}}}}',
    '{"type":"text","timestamp":3,"sessionID":"ses_fixture","part":'
    '{"id":"prt_3","type":"text","text":"Done.\\n{\\"status\\": \\"ok\\", '
    '\\"summary\\": \\"implemented clamp\\", \\"files\\": [\\"tiny_math.py\\"]}"}}',
    '{"type":"step_finish","timestamp":4,"sessionID":"ses_fixture","part":'
    '{"id":"prt_4","reason":"stop","type":"step-finish","tokens":{"input":120,'
    '"output":30,"reasoning":5,"cache":{"read":40,"write":0}},"cost":0.0012}}',
    '{"type":"mystery","timestamp":5,"sessionID":"ses_fixture","part":{}}',
)


def self_test() -> dict:
    """Prove normalization, the message contract, and fail-closed refusals."""
    import tempfile
    from ..loop.loop_contract import LoopContract
    from .external_harness import HarnessBudget

    parsed = parse_opencode_events(
        _FIXTURE_EVENTS, provider_id="ollama-cloud", model_id="deepseek-v4-flash")
    call = parsed.model_calls[0]
    contract = LoopContract(
        name="implement clamp", execution_mode="model_led",
        input_roles=("repository",), output_roles=("changed_files",),
        effects=("writes_fs", "spawns_process"), role="solution")
    request = HarnessRunRequest(
        "req-1", OPENCODE_HARNESS_ID, "Implement clamp so the tests pass.",
        contract, HarnessBudget(max_model_calls=4, max_seconds=60),
        provider_id="ollama-cloud", model_id="deepseek-v4-flash",
        input_data={"tests": "test_tiny_math.py"}, workspace_ref="/nonexistent",
        authorize_model_calls=True)
    message = render_opencode_message(request)
    missing_binary = OpenCodeProcessAdapter(binary="/nonexistent/opencode")
    unavailable = missing_binary.run(request, HarnessServices())
    fake = OpenCodeProcessAdapter(listed_models=("ollama-cloud/other",))
    fake._version = "0.0.0-test"
    fake._binary_path = lambda: "/bin/true"  # handshake only; never run
    unlisted = fake.run(request, HarnessServices())
    listed = OpenCodeProcessAdapter(listed_models=("ollama-cloud/deepseek-v4-flash",))
    listed._version = "0.0.0-test"
    listed._binary_path = lambda: "/bin/true"
    no_workspace = listed.run(request, HarnessServices())
    with tempfile.TemporaryDirectory() as root:
        (Path(root) / "a.py").write_text("x = 1\n")
        snapshot = _snapshot(Path(root))
    tests = [{
        "test": "step_finish_becomes_one_model_call_with_tokens_cost_and_cache_reads",
        "passed": (len(parsed.model_calls) == 1 and call.ok
                   and call.input_tokens == 160 and call.output_tokens == 35
                   and call.cost == 0.0012 and parsed.session_id == "ses_fixture"),
        "detail": f"in={call.input_tokens} out={call.output_tokens}",
    }, {
        "test": "tool_parts_become_effect_typed_events_and_unknown_types_are_counted",
        "passed": (len(parsed.tool_events) == 1
                   and parsed.tool_events[0].tool_name == "write"
                   and parsed.tool_events[0].effect == "writes_fs"
                   and parsed.tool_events[0].status == "completed"
                   and parsed.unmapped_types == (("mystery", 1),)
                   and parsed.event_count == 5),
        "detail": str(parsed.unmapped_types),
    }, {
        "test": "final_json_line_is_extracted_from_the_visible_text",
        "passed": (parsed.final_json or {}).get("status") == "ok"
        and (parsed.final_json or {}).get("files") == ["tiny_math.py"],
        "detail": str(parsed.final_json),
    }, {
        "test": "message_carries_default_instructions_goal_contract_and_inputs",
        "passed": ("bounded coding task" in message and "Task: Implement clamp"
                   in message and "Output roles: changed_files" in message
                   and '"tests": "test_tiny_math.py"' in message
                   and "Do not claim verification" in message),
        "detail": message[:120],
    }, {
        "test": "missing_binary_unlisted_model_and_missing_workspace_fail_closed",
        "passed": (unavailable.status == "unavailable"
                   and unlisted.status == "refused"
                   and unlisted.error_code == "model_not_listed"
                   and no_workspace.status == "refused"
                   and no_workspace.error_code == "workspace_required"),
        "detail": f"{unavailable.status} {unlisted.error_code} {no_workspace.error_code}",
    }, {
        "test": "workspace_snapshot_digests_regular_files_only",
        "passed": list(snapshot) == ["a.py"] and len(snapshot["a.py"]) == 64,
        "detail": str(list(snapshot)),
    }]
    return {"module": "core.opencode_harness_adapter",
            "passed": all(item["passed"] for item in tests), "tests": tests}
