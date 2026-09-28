"""Counting proxy between a harness and a declared OpenAI-compatible model endpoint.

Kind: measurement instrument for tools/showcase_3d. Every physical model call passes through it and is written as
one JSON line: run id, sequence, start and end time, HTTP status, model, prompt and completion tokens as the
server reported them (null when it did not) and the outcome. Prompts, answers and credentials are never written.

Limits, enforced before a call leaves the machine: a session ceiling, a per-run ceiling read from a limits file
(run id to number of calls) and an optional deadline. A refused call is answered with HTTP 400 and recorded as
refused; it is not a model call and nothing is invented in its place.

Transport adapter: the owner's Tactical server streams tool-call arguments in a form no OpenAI-compatible client
parses (September 27, 2026), while its complete answer is correct. A streamed request is therefore sent upstream
as a complete request, and the same answer is passed back as a stream. The adapter is applied to every run.

The endpoint comes from tools/opencode_generation_lanes.DECLARED_ENDPOINTS. Its key is resolved in this process
through tools/operator_credentials.py. The Tactical Origin certificate does not match the served host name, so
host name verification is off for that endpoint only, as the generation lanes do, and the leaf certificate seen
at start is pinned: a different leaf later refuses the call.

Usage: python proxy.py --endpoint tactical --port 18912 --ledger CALLS.jsonl --limits LIMITS.json --session-ceiling N
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
import socket
import ssl
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

TOOLS = Path(__file__).resolve().parents[1]
PHYSICAL = ("ok", "upstream_error", "transport_error")


def _module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses in the loaded module look themselves up here
    spec.loader.exec_module(module)
    return module


def declared_endpoint(name: str) -> dict:
    return _module("opencode_generation_lanes", TOOLS / "opencode_generation_lanes.py").DECLARED_ENDPOINTS[name]


def resolve_key(reference: str) -> str:
    credentials = _module("operator_credentials", TOOLS / "operator_credentials.py")
    value = credentials.resolve(reference, data=json.loads((TOOLS / "operator_credentials.json").read_text(encoding="utf-8")))
    return value if isinstance(value, str) else getattr(value, "value", "")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def usage_of(data: bytes) -> dict:
    try:
        usage = json.loads(data).get("usage")
    except Exception:
        usage = None
    if not usage:
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    return {key: usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}


def as_event_stream(data: bytes) -> bytes:
    """One complete chat answer re-emitted as OpenAI-style stream chunks, with the same message."""
    completion = json.loads(data)
    base = {"id": completion.get("id"), "object": "chat.completion.chunk", "created": completion.get("created"),
            "model": completion.get("model")}
    choice = (completion.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    delta = {"role": "assistant"}
    if message.get("content"):
        delta["content"] = message["content"]
    frames = [{**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}]
    for index, call in enumerate(message.get("tool_calls") or []):
        function = call.get("function") or {}
        frames.append({**base, "choices": [{"index": 0, "delta": {"tool_calls": [{
            "index": index, "id": call.get("id"), "type": "function",
            "function": {"name": function.get("name"), "arguments": function.get("arguments") or "{}"}}]},
            "finish_reason": None}]})
    finish = choice.get("finish_reason") or "stop"
    if message.get("tool_calls") and finish == "stop":
        finish = "tool_calls"
    frames.append({**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
    if completion.get("usage"):
        frames.append({**base, "choices": [], "usage": completion["usage"]})
    return ("".join("data: " + json.dumps(frame) + "\n\n" for frame in frames) + "data: [DONE]\n\n").encode()


class Proxy:
    def __init__(self, endpoint: str, ledger: Path, limits: Path, session_ceiling: int, deadline: str | None):
        declared = declared_endpoint(endpoint)
        address = urlsplit(declared["base_url"])
        self.host, self.port = address.hostname, address.port or 443
        self.prefix = address.path.rstrip("/")
        self.unverified_host = bool(declared.get("disable_node_tls_verification"))
        self.key = resolve_key(declared["credential_reference"])
        self.ledger, self.limits, self.session_ceiling = ledger, limits, session_ceiling
        self.deadline = datetime.fromisoformat(deadline) if deadline else None
        self.lock = threading.Lock()
        self.sent, self.per_run = 0, {}
        if ledger.exists():
            for line in ledger.read_text().splitlines():
                row = json.loads(line)
                if row.get("outcome") in PHYSICAL:
                    self.sent += 1
                    self.per_run[row["run_id"]] = self.per_run.get(row["run_id"], 0) + 1
        self.pinned = self.leaf() if self.unverified_host else None

    def context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        if self.unverified_host:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def leaf(self) -> str:
        with socket.create_connection((self.host, self.port), timeout=20) as raw:
            with self.context().wrap_socket(raw, server_hostname=self.host) as tls:
                return hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()

    def record(self, row: dict) -> None:
        with self.lock:
            with self.ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    def run_limit(self, run_id: str) -> int:
        try:
            data = json.loads(self.limits.read_text())
            return int(data.get(run_id, data.get("*", 0)))
        except Exception:
            return 0

    def admit(self, run_id: str):
        with self.lock:
            if self.deadline and datetime.now(timezone.utc) >= self.deadline:
                return "deadline_reached", None
            if self.sent >= self.session_ceiling:
                return "session_ceiling_reached", None
            if self.per_run.get(run_id, 0) >= self.run_limit(run_id):
                return "run_ceiling_reached", None
            self.sent += 1
            self.per_run[run_id] = self.per_run.get(run_id, 0) + 1
            return None, (self.sent, self.per_run[run_id])


def handler_for(proxy: Proxy):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            return

        def reply(self, status: int, payload: bytes, content_type: str = "application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()

        def do_GET(self):
            self.forward("GET")

        def do_POST(self):
            self.forward("POST")

        def forward(self, method: str) -> None:
            parts = self.path.split("/")
            if len(parts) < 4 or parts[1] != "r":
                self.reply(404, b"{}"); return
            run_id, rest = parts[2], "/" + "/".join(parts[3:])
            if rest.startswith("/v1"):
                rest = rest[3:]
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            is_call = method == "POST" and rest.startswith("/chat/completions")
            streamed, model, sequence = False, None, (None, None)
            if is_call:
                try:
                    request = json.loads(body)
                    streamed, model = bool(request.get("stream")), request.get("model")
                    if streamed:
                        request["stream"] = False
                        request.pop("stream_options", None)
                        body = json.dumps(request).encode()
                except Exception:
                    pass
                reason, sequence = proxy.admit(run_id)
                if reason:
                    message = {"error": {"message": "proxy refused the model call: " + reason, "type": "invalid_request_error", "code": reason}}
                    self.reply(400, json.dumps(message).encode())
                    proxy.record({"run_id": run_id, "at": now(), "outcome": "refused", "reason": reason})
                    return
            started, t0 = now(), time.time()
            status, data, outcome, error = 0, b"", "ok", None
            try:
                connection = http.client.HTTPSConnection(proxy.host, proxy.port, context=proxy.context(), timeout=600)
                connection.connect()
                if proxy.pinned and hashlib.sha256(connection.sock.getpeercert(binary_form=True)).hexdigest() != proxy.pinned:
                    raise ssl.SSLError("leaf certificate changed during the session")
                headers = {"Content-Type": "application/json", "Authorization": "Bearer " + proxy.key, "Accept": "application/json"}
                connection.request(method, proxy.prefix + rest, body=body if body else None, headers=headers)
                response = connection.getresponse()
                status, data = response.status, response.read()
                if streamed and status < 400:
                    self.reply(status, as_event_stream(data), "text/event-stream")
                else:
                    self.reply(status, data, response.getheader("Content-Type", "application/json"))
                if status >= 400:
                    outcome = "upstream_error"
            except Exception as exc:
                outcome = "transport_error"
                error = (type(exc).__name__ + ": " + str(exc)[:200]).replace(proxy.key or "\0", "<key>")
                if not status:
                    try:
                        self.reply(502, json.dumps({"error": {"message": "upstream transport failed", "type": "server_error"}}).encode())
                    except Exception:
                        pass
            if is_call:
                row = {"run_id": run_id, "seq": sequence[0], "run_seq": sequence[1], "started": started, "ended": now(),
                       "seconds": round(time.time() - t0, 2), "status": status, "model": model, "streamed_request": streamed,
                       "adapter": "complete_answer_reemitted_as_stream" if streamed else "none", "outcome": outcome,
                       "error": error, "response_bytes": len(data), "request_bytes": len(body)}
                row.update(usage_of(data))
                if status >= 400 and len(data) < 2000:
                    row["upstream_error_text"] = data.decode("utf-8", "replace")[:300]
                proxy.record(row)
    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--limits", type=Path, required=True)
    parser.add_argument("--session-ceiling", type=int, required=True)
    parser.add_argument("--deadline", default=None, help="ISO time after which no call is sent.")
    args = parser.parse_args(argv)
    proxy = Proxy(args.endpoint, args.ledger, args.limits, args.session_ceiling, args.deadline)
    proxy.record({"event": "proxy_start", "at": now(), "endpoint": args.endpoint, "pinned_leaf_sha256": proxy.pinned,
                  "session_ceiling": args.session_ceiling, "calls_already_in_ledger": proxy.sent, "key_present": bool(proxy.key)})
    ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(proxy)).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
