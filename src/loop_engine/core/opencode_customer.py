"""Confined native customer profile over the existing harness process boundary.

The host retains model access, ordinary-account MCP access and durable effect
accounting. This adapter carries native tool messages, never flattens them to
text and never authorizes a raw host process. Its shared per-operation budget
is a backstop beside the host's durable pre-dispatch model and request ledger.
"""
from dataclasses import dataclass, field
import base64
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
from threading import Event, Lock
import time
from urllib.parse import urlsplit

from .harness_process import HarnessProcessError
from .harness_customer_resources import CustomerResourceLimits, CustomerResourceScope

PROFILE = "opencode_customer_profile/v1"
NATIVE_TOOLS = frozenset(("read", "glob", "grep", "write", "edit", "bash", "skill"))
MCP_TOOLS = frozenset(("intelligence_search", "provisioning_read"))
MODEL_TOOLS = NATIVE_TOOLS | frozenset("baltor_" + name for name in MCP_TOOLS)
MCP_METHODS = frozenset(("initialize", "notifications/initialized", "tools/list", "tools/call"))
EFFECTS = frozenset(("reads_fs", "writes_fs", "spawns_process"))
HTTP_ROUTES = {"/api/v1/capabilities": "GET", "/api/v1/retrieval": "POST",
               "/api/v1/provisioning": "POST", "/api/v1/download": "POST"}
MODEL_FIELDS = frozenset(("model", "messages", "tools", "tool_choice", "temperature", "top_p", "max_tokens",
                         "max_completion_tokens", "stream", "stream_options", "parallel_tool_calls", "reasoning_effort",
                         "stop", "seed", "frequency_penalty", "presence_penalty", "n", "_harness_wire"))


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _path(value):
    if type(value) is not str:
        raise HarnessProcessError("customer_artifact_path_refused")
    path = Path(value)
    if (not value or len(value.encode("utf-8")) > 200 or len(path.parts) > 16 or path.is_absolute() or str(path) != value
            or any(part in ("", ".", "..") or part.startswith(".") for part in value.split("/"))
            or path.parts[0] == "home" or any(ord(char) < 32 for char in value)):
        raise HarnessProcessError("customer_artifact_path_refused")
    return path


@dataclass(frozen=True)
class CustomerFile:
    """An explicitly selected private file snapshot, not a path to follow."""
    path: str
    body: bytes = field(repr=False)

    def __post_init__(self):
        _path(self.path)
        if type(self.body) is not bytes:
            raise HarnessProcessError("customer_file_bytes_required")

    @property
    def sha256(self):
        return hashlib.sha256(self.body).hexdigest()


@dataclass
class CustomerOperationBudget:
    """One shared budget across fresh-process use, revision and recovery."""
    maximum_model_requests: int
    maximum_mcp_requests: int
    timeout_seconds: float
    started_at: float = field(default_factory=time.monotonic)
    model_requests: int = 0
    mcp_requests: int = 0
    cancelled: Event = field(default_factory=Event, repr=False)
    receipts: list = field(default_factory=list, repr=False)
    lock: Lock = field(default_factory=Lock, repr=False)

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in (self.maximum_model_requests, self.maximum_mcp_requests)):
            raise HarnessProcessError("customer_request_ceiling_required")
        if type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise HarnessProcessError("customer_deadline_required")

    @property
    def remaining_seconds(self):
        return max(0.0, self.timeout_seconds - (time.monotonic() - self.started_at))

    def admit(self, kind, body):
        with self.lock:
            if self.cancelled.is_set() or not self.remaining_seconds:
                raise HarnessProcessError("customer_cancelled_or_expired")
            field_name = kind + "_requests"
            if getattr(self, field_name) >= getattr(self, "maximum_" + field_name):
                raise HarnessProcessError("customer_" + kind + "_budget_exhausted")
            setattr(self, field_name, getattr(self, field_name) + 1)
            sequence = len(self.receipts) + 1
            self.receipts.append({"record_type": "customer_broker_attempt/v1", "kind": kind,
                                  "sequence": sequence, "request_digest": _digest(body), "outcome": "reserved"})
            return sequence

    def finish(self, sequence, **values):
        with self.lock:
            record = self.receipts[sequence - 1]
            if record["sequence"] != sequence or record["outcome"] != "reserved":
                raise HarnessProcessError("customer_receipt_already_finished")
            record.update(values)


def validate_native_request(body, model):
    """Validate native roles and tool declarations without rewriting history."""
    if (not isinstance(body, dict) or set(body) - MODEL_FIELDS or body.get("model") != model or not isinstance(body.get("messages"), list)
            or not body["messages"] or type(body.get("n", 1)) is not int or body.get("n", 1) != 1):
        raise HarnessProcessError("customer_model_identity_or_history_refused")
    pending_calls = set()
    seen_calls = set()
    for message in body["messages"]:
        if not isinstance(message, dict) or message.get("role") not in ("system", "user", "assistant", "tool"):
            raise HarnessProcessError("customer_message_role_refused")
        if set(message) - {"role", "content", "tool_calls", "tool_call_id"}:
            raise HarnessProcessError("customer_message_fields_refused")
        content = message.get("content")
        if content is not None and not isinstance(content, str):
            if (not isinstance(content, list) or any(not isinstance(part, dict) or part.get("type") != "text"
                                                    or not isinstance(part.get("text"), str) for part in content)):
                raise HarnessProcessError("customer_nontext_material_refused")
        _tool_calls(message.get("tool_calls", []))
        if message["role"] == "tool":
            identity = message.get("tool_call_id")
            if not isinstance(identity, str) or identity not in pending_calls or message.get("tool_calls"):
                raise HarnessProcessError("customer_tool_result_identity_required")
            pending_calls.remove(identity)
        else:
            if "tool_call_id" in message or pending_calls or (message.get("tool_calls") and message["role"] != "assistant"):
                raise HarnessProcessError("customer_tool_history_sequence_refused")
            for call in message.get("tool_calls", []):
                if not call["id"] or call["id"] in seen_calls:
                    raise HarnessProcessError("customer_tool_call_identity_reused")
                seen_calls.add(call["id"])
                pending_calls.add(call["id"])
    if pending_calls:
        raise HarnessProcessError("customer_tool_result_missing")
    tools = body.get("tools", [])
    if not isinstance(tools, list):
        raise HarnessProcessError("customer_tools_shape_refused")
    names = []
    for tool in tools:
        if (not isinstance(tool, dict) or tool.get("type") != "function" or not isinstance(tool.get("function"), dict)
                or set(tool) != {"type", "function"} or set(tool["function"]) - {"name", "description", "parameters", "strict"}
                or not isinstance(tool["function"].get("name"), str) or tool["function"]["name"] not in MODEL_TOOLS
                or not isinstance(tool["function"].get("parameters"), dict)):
            raise HarnessProcessError("customer_tool_not_authorized")
        names.append(tool["function"]["name"])
    if len(names) != len(set(names)):
        raise HarnessProcessError("customer_duplicate_tool_declaration")
    choice = body.get("tool_choice", "auto")
    if choice not in ("auto", "none", "required") and not (isinstance(choice, dict) and set(choice) == {"type", "function"}
            and choice["type"] == "function" and isinstance(choice["function"], dict) and set(choice["function"]) == {"name"}
            and choice["function"]["name"] in names):
        raise HarnessProcessError("customer_tool_choice_refused")
    for name in ("max_tokens", "max_completion_tokens"):
        if name in body and (type(body[name]) is not int or body[name] < 1):
            raise HarnessProcessError("customer_output_allocation_refused")
    for name in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
        if name in body and (type(body[name]) not in (int, float) or not math.isfinite(body[name])):
            raise HarnessProcessError("customer_sampling_value_refused")
    for name in ("stream", "parallel_tool_calls"):
        if name in body and type(body[name]) is not bool:
            raise HarnessProcessError("customer_native_flag_refused")
    if "stream_options" in body and (not isinstance(body["stream_options"], dict) or set(body["stream_options"]) - {"include_usage"}
                                      or type(body["stream_options"].get("include_usage", False)) is not bool):
        raise HarnessProcessError("customer_stream_option_refused")
    if "reasoning_effort" in body and body["reasoning_effort"] not in ("none", "minimal", "low", "medium", "high"):
        raise HarnessProcessError("customer_reasoning_option_refused")
    for tool in tools:
        pending = [tool["function"]["parameters"]]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if any(key in value and (not isinstance(value[key], str) or not value[key].startswith("#"))
                       for key in ("$ref", "$dynamicRef", "$recursiveRef")):
                    raise HarnessProcessError("customer_external_schema_reference_refused")
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)


def _tool_calls(calls):
    if not isinstance(calls, list):
        raise HarnessProcessError("customer_tool_calls_shape_refused")
    for call in calls:
        if (not isinstance(call, dict) or call.get("type") != "function" or not isinstance(call.get("id"), str)
                or not isinstance(call.get("function"), dict) or not isinstance(call["function"].get("name"), str)
                or call["function"]["name"] not in MODEL_TOOLS
                or not isinstance(call["function"].get("arguments"), str)):
            raise HarnessProcessError("customer_tool_call_refused")
        try:
            from .harness_process_relay import _decode
            arguments = _decode(call["function"]["arguments"])
        except (ValueError, RecursionError):
            raise HarnessProcessError("customer_tool_arguments_invalid") from None
        if not isinstance(arguments, dict):
            raise HarnessProcessError("customer_tool_arguments_invalid")


@dataclass
class OpenCodeCustomerBoundary:
    """Explicit authority for one confined native customer attempt.

    ``mcp`` returns a sanitized JSON-RPC result/error envelope for the fixed
    host-owned ordinary account. It must enforce scopes, exact resources,
    effect declarations, request identities and durable quota before dispatch.
    They must hold an unknown external outcome for explicit reconciliation:
    neither this boundary nor its client automatically retries that outcome.
    Neither callback credential nor provider credential enters the child.
    """
    budget: CustomerOperationBudget
    mcp: object = field(repr=False)
    authority_effects: frozenset
    files: tuple[CustomerFile, ...] = ()
    artifact_paths: tuple[str, ...] = ()
    maximum_file_bytes: int = 1024 * 1024
    http: object = field(default=None, repr=False)
    origin: str = "https://baltor.ai"
    captured: list = field(default_factory=list, init=False, repr=False)
    active_receipt: int | None = field(default=None, init=False, repr=False)
    lease: Lock = field(default_factory=Lock, init=False, repr=False)
    resource_limits: CustomerResourceLimits = CustomerResourceLimits()
    resources: object = field(default=None, init=False, repr=False)
    published_client: bytes = field(default=b"", init=False, repr=False)
    client_snapshot: str = field(default="", init=False, repr=False)
    pending_artifacts: object = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.budget, CustomerOperationBudget) or not callable(self.mcp) or self.authority_effects != EFFECTS:
            raise HarnessProcessError("explicit_customer_effect_authority_required")
        if not isinstance(self.resource_limits, CustomerResourceLimits):
            raise HarnessProcessError("customer_resource_limits_required")
        if type(self.maximum_file_bytes) is not int or self.maximum_file_bytes < 1:
            raise HarnessProcessError("customer_file_budget_required")
        origin = urlsplit(self.origin)
        if (origin.scheme != "https" or not origin.hostname or origin.port or origin.username or origin.password
                or origin.path or origin.query or origin.fragment or (self.http is not None and not callable(self.http))):
            raise HarnessProcessError("customer_service_binding_refused")
        if (type(self.files) is not tuple or len(self.files) > 64 or any(not isinstance(item, CustomerFile) for item in self.files)
                or len({item.path for item in self.files}) != len(self.files)
                or sum(len(item.body) for item in self.files) > self.maximum_file_bytes):
            raise HarnessProcessError("customer_file_snapshot_refused")
        if type(self.artifact_paths) is not tuple or len(set(self.artifact_paths)) != len(self.artifact_paths) or len(self.artifact_paths) > 64:
            raise HarnessProcessError("customer_artifact_selection_refused")
        for path in self.artifact_paths:
            _path(path)
        source = Path(__file__).parent / "service_runtime/web_assets/baltor-library/scripts/baltor.py.txt"
        self.published_client = source.read_bytes()

    def configuration(self):
        return {"record_type": PROFILE, "native_tools": sorted(NATIVE_TOOLS), "mcp_tools": sorted(MCP_TOOLS),
                "origin": self.origin, "authority_effects": sorted(self.authority_effects), "rest_available": self.http is not None,
                "seed_files": [item.path for item in self.files], "artifact_paths": list(self.artifact_paths),
                "maximum_file_bytes": self.maximum_file_bytes, "workspace_bytes": self.resource_limits.workspace_bytes,
                "temporary_bytes": self.resource_limits.temporary_bytes}

    def validate_transport(self, request):
        # Base64 increases raw artifact bytes by 4/3. Allow the worst case
        # rounding and exact path/digest envelopes without enlarging callers'
        # transport or whole-operation ceilings implicitly.
        if request.spec.style != "opencode_customer":
            raise HarnessProcessError("confined_customer_profile_required")
        required = 4 * ((self.maximum_file_bytes + 2) // 3) + 64 * 512 + 1024
        if request.maximum_request_bytes < required:
            raise HarnessProcessError("customer_artifact_wire_allowance_insufficient")
        if {item.path for item in self.files} & {item.name for item in request.instruction_material}:
            raise HarnessProcessError("customer_seed_instruction_collision")

    @contextmanager
    def operation(self):
        if not self.lease.acquire(blocking=False):
            raise HarnessProcessError("customer_boundary_already_in_use")
        try:
            if self.resources is not None and not self.resources.cleanup_confirmed:
                raise HarnessProcessError("customer_previous_cleanup_unconfirmed")
            self.resources = CustomerResourceScope(self.resource_limits)
            self.pending_artifacts = None
            self.captured.clear()
            yield
        finally:
            if self.resources is not None and not self.resources.dispatched:
                self.resources.cleanup_confirmed = True
            self.lease.release()

    @property
    def read_only_files(self):
        if not self.client_snapshot:
            raise HarnessProcessError("customer_client_snapshot_required")
        return ((self.client_snapshot, "/relay/baltor_library_client.py"),)

    def snapshot_client(self, run):
        # A concurrent public-asset rebuild cannot change executed bytes after
        # identity creation: the recorded bytes themselves are mounted.
        target = run / "baltor_library_client.py"
        with target.open("xb") as stream:
            stream.write(self.published_client)
        target.chmod(0o400)
        self.client_snapshot = str(target)

    def identity(self):
        return {**self.configuration(), "authority_effects": sorted(self.authority_effects),
                "files": [{"path": item.path, "sha256": item.sha256} for item in self.files],
                "artifacts": list(self.artifact_paths), "maximum_file_bytes": self.maximum_file_bytes,
                "model_ceiling": self.budget.maximum_model_requests, "mcp_ceiling": self.budget.maximum_mcp_requests,
                "resource_limits": {"memory_bytes": self.resource_limits.memory_bytes, "tasks": self.resource_limits.tasks,
                                    "cpu_percent": self.resource_limits.cpu_percent, "workspace_bytes": self.resource_limits.workspace_bytes,
                                    "temporary_bytes": self.resource_limits.temporary_bytes},
                "published_client_sha256": hashlib.sha256(self.published_client).hexdigest()}

    def seed(self, work):
        for item in self.files:
            if not self.budget.remaining_seconds or self.budget.cancelled.is_set():
                raise HarnessProcessError("customer_cancelled_or_expired")
            target = work / _path(item.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(item.body)
            target.chmod(0o600)

    def admit(self, body, request):
        self.active_receipt = None
        if "_workspace_artifacts" in body:
            if set(body) != {"_workspace_artifacts"} or self.pending_artifacts is not None:
                raise HarnessProcessError("customer_artifact_export_duplicate_or_mixed")
            self._validate_artifacts(body["_workspace_artifacts"])
        elif "_workspace_http" in body:
            value = body["_workspace_http"]
            if (self.http is None or set(body) != {"_workspace_http"} or not isinstance(value, dict)
                    or set(value) != {"method", "path", "payload"}
                    or not isinstance(value.get("path"), str) or value["path"] not in HTTP_ROUTES or value.get("method") != HTTP_ROUTES[value["path"]]
                    or (value["method"] == "GET" and value["payload"] is not None)
                    or (value["method"] == "POST" and not isinstance(value["payload"], dict))):
                raise HarnessProcessError("customer_http_scope_refused")
            self.active_receipt = self.budget.admit("mcp", value)
        elif "_workspace_mcp" in body:
            if set(body) != {"_workspace_mcp"}:
                raise HarnessProcessError("customer_mcp_envelope_refused")
            message = body["_workspace_mcp"]
            if (not isinstance(message, dict) or message.get("jsonrpc") != "2.0"
                    or not isinstance(message.get("method"), str) or message["method"] not in MCP_METHODS or not isinstance(message.get("params", {}), dict)
                    or set(message) - {"jsonrpc", "id", "method", "params"}):
                raise HarnessProcessError("customer_mcp_method_refused")
            if message["method"] == "tools/call" and (not isinstance(message.get("params", {}).get("name"), str)
                                                     or message["params"]["name"] not in MCP_TOOLS):
                raise HarnessProcessError("customer_mcp_tool_refused")
            self.active_receipt = self.budget.admit("mcp", message)
        else:
            validate_native_request(body, request.model)
            self.active_receipt = self.budget.admit("model", body)

    def invoke_service(self, body):
        if "_workspace_artifacts" in body:
            self.pending_artifacts = self._validate_artifacts(body["_workspace_artifacts"])
            return {"result": {"record_type": "customer_artifact_ack/v1", "files": len(self.pending_artifacts)}}
        if "_workspace_http" in body:
            value = body["_workspace_http"]
            return self.http(value["method"], value["path"], value["payload"])
        message = body["_workspace_mcp"]
        return self.mcp(message["method"], message.get("params", {}))

    def observe(self, body, response):
        if "_workspace_artifacts" in body:
            if response != {"result": {"record_type": "customer_artifact_ack/v1", "files": len(self.pending_artifacts)}}:
                raise HarnessProcessError("customer_artifact_ack_refused")
            return False
        elif "_workspace_http" in body:
            if (not isinstance(response, dict) or set(response) != {"status", "headers", "body_base64"}
                    or type(response["status"]) is not int or not 100 <= response["status"] <= 599
                    or not isinstance(response["headers"], dict) or any(not isinstance(key, str) or not isinstance(value, str)
                        or any(char in key + value for char in "\r\n\x00") for key, value in response["headers"].items())
                    or not isinstance(response["body_base64"], str)):
                raise HarnessProcessError("customer_http_response_refused")
            try:
                base64.b64decode(response["body_base64"], validate=True)
            except ValueError:
                raise HarnessProcessError("customer_http_encoding_refused") from None
            is_model = False
        elif "_workspace_mcp" in body:
            if not isinstance(response, dict) or set(response) not in ({"result"}, {"error"}):
                raise HarnessProcessError("customer_mcp_response_refused")
            if body["_workspace_mcp"]["method"] == "tools/list" and "result" in response:
                result = response["result"]
                if not isinstance(result, dict) or not isinstance(result.get("tools"), list) or any(
                        not isinstance(tool, dict) or tool.get("name") not in MCP_TOOLS for tool in result["tools"]):
                    raise HarnessProcessError("customer_mcp_tool_list_refused")
            is_model = False
        else:
            choices = response.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise HarnessProcessError("customer_native_response_refused")
            message = choices[0].get("message")
            if not isinstance(message, dict) or message.get("role") != "assistant" or message.get("function_call"):
                raise HarnessProcessError("customer_native_response_refused")
            if message.get("content") is not None and not isinstance(message["content"], str):
                raise HarnessProcessError("customer_native_response_refused")
            _tool_calls(message.get("tool_calls", []))
            declared = {tool["function"]["name"] for tool in body.get("tools", [])}
            if any(call["function"]["name"] not in declared for call in message.get("tool_calls", [])):
                raise HarnessProcessError("customer_undeclared_tool_response")
            if not message.get("tool_calls") and not message.get("content"):
                raise HarnessProcessError("customer_empty_native_response")
            is_model = True
        self.budget.finish(self.active_receipt, outcome="answered", response_digest=_digest(response))
        self.active_receipt = None
        return is_model

    def failed(self, body, code):
        if self.active_receipt is not None:
            self.budget.finish(self.active_receipt, outcome="unknown_or_refused", error_code=code)
            self.active_receipt = None
        if code.startswith("customer_") and ("budget_exhausted" in code or "expired" in code):
            self.budget.cancelled.set()

    def capture(self, work):
        from .opencode_customer_recipe import artifact_snapshot
        try:
            self.captured[:] = self._validate_artifacts(artifact_snapshot(work, self.artifact_paths, self.maximum_file_bytes))
        except ValueError as error:
            raise HarnessProcessError(str(error)) from None

    def release_artifacts(self):
        if not self.resources.cleanup_confirmed:
            raise HarnessProcessError("customer_capture_requires_confirmed_cleanup")
        if self.pending_artifacts is None:
            raise HarnessProcessError("customer_artifact_export_missing")
        self.captured[:] = self.pending_artifacts

    def _validate_artifacts(self, snapshot):
        if (not isinstance(snapshot, dict) or set(snapshot) != {"record_type", "files"}
                or snapshot["record_type"] != "customer_artifact_snapshot/v1" or not isinstance(snapshot["files"], list)
                or len(snapshot["files"]) > len(self.artifact_paths)):
            raise HarnessProcessError("customer_artifact_export_shape")
        total = 0
        captured = []
        names = set()
        for item in snapshot["files"]:
            if (not isinstance(item, dict) or set(item) != {"path", "body_base64", "sha256"}
                    or not isinstance(item["path"], str) or item["path"] not in self.artifact_paths or item["path"] in names
                    or not isinstance(item["body_base64"], str) or len(item["body_base64"]) > 4 * ((self.maximum_file_bytes + 2) // 3)):
                raise HarnessProcessError("customer_artifact_export_selection")
            try:
                body = base64.b64decode(item["body_base64"], validate=True)
            except ValueError:
                raise HarnessProcessError("customer_artifact_export_encoding") from None
            total += len(body)
            if total > self.maximum_file_bytes:
                raise HarnessProcessError("customer_artifact_byte_limit")
            if hashlib.sha256(body).hexdigest() != item["sha256"]:
                raise HarnessProcessError("customer_artifact_export_digest")
            names.add(item["path"])
            captured.append(CustomerFile(item["path"], body))
        return captured
