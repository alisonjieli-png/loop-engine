"""A counting proxy between the harness and the local Ollama server.

Every model request of the demonstration passes through this proxy. It is the
one place where requests are counted, limited and recorded:

- Each request is forwarded unchanged to the upstream OpenAI-compatible
  endpoint, and the response is streamed back unchanged.
- A request is counted as a physical request before it is forwarded. The
  ledger line that says so is written and flushed before the upstream
  connection opens, so a crash cannot hide a request that was sent.
- The proxy refuses, without forwarding, any request beyond the total ceiling
  or beyond the cap of the step that sent it. A refusal is recorded but is not
  a physical request.
- For each physical request the ledger records the step, model, times, HTTP
  status, provider-reported token usage when present and whether the step's
  material text was inside the request. Missing usage stays missing, never
  zero. Request and response bodies are saved in the run folder.

The step identity is part of the URL path, `/trial/<trial id>/v1/...`, so a
request can never be counted against another step. Only the Python standard
library is used. No authorization header is forwarded or recorded.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PATH_PATTERN = re.compile(r"^/trial/(?P<trial>[A-Za-z0-9_.-]+)/v1/(?P<rest>[A-Za-z0-9_/.-]+)$")
LEDGER_RECORD = "data_cleanup_model_request/v1"


def now_text():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class StepContext:
    trial_id: str
    model: str
    arm: str
    family: str
    repetition: int
    cap: int
    material_markers: tuple = ()
    physical: int = 0
    refused: int = 0
    statuses: list = field(default_factory=list)


class Meter:
    """Counts, limits and records model requests for registered steps."""

    def __init__(self, ledger_path, transcript_folder, ceiling, upstream_host="127.0.0.1",
                 upstream_port=11434, upstream_timeout=900):
        self.ledger_path = Path(ledger_path)
        self.transcript_folder = Path(transcript_folder)
        self.ceiling = int(ceiling)
        self.upstream = (upstream_host, int(upstream_port))
        self.upstream_timeout = upstream_timeout
        self.lock = threading.Lock()
        self.steps = {}
        self.physical_total, self.sequence = self._recover()
        self.server = None

    def _recover(self):
        """Physical requests and the last sequence number already in the ledger."""
        total = sequence = 0
        if self.ledger_path.is_file():
            for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                sequence = max(sequence, int(row.get("sequence", 0)))
                if row.get("event") == "sent":
                    total += 1
        return total, sequence

    # -- registration --------------------------------------------------------

    def open_step(self, context: StepContext):
        with self.lock:
            if context.trial_id in self.steps:
                raise ValueError(f"step {context.trial_id} is already open")
            self.steps[context.trial_id] = context

    def close_step(self, trial_id):
        with self.lock:
            return self.steps.pop(trial_id, None)

    def remaining(self):
        with self.lock:
            return self.ceiling - self.physical_total

    # -- ledger --------------------------------------------------------------

    def _write(self, row):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def admit(self, trial_id, model):
        """Return (context, sequence, refusal reason or None) under the lock."""
        with self.lock:
            self.sequence += 1
            sequence = self.sequence
            context = self.steps.get(trial_id)
            if context is None:
                reason = "unknown_or_closed_step"
            elif self.physical_total >= self.ceiling:
                reason = "total_ceiling_reached"
            elif context.physical >= context.cap:
                reason = "step_cap_reached"
            elif model != context.model:
                reason = "model_differs_from_step"
            else:
                reason = None
            if reason is None:
                self.physical_total += 1
                context.physical += 1
                total = self.physical_total
            else:
                total = self.physical_total
                if context is not None:
                    context.refused += 1
            base = dict(record_type=LEDGER_RECORD, sequence=sequence, trial_id=trial_id,
                        model=model, at=now_text(), physical_total=total)
            if context is not None:
                base.update(arm=context.arm, family=context.family,
                            repetition=context.repetition, step_request=context.physical)
            if reason is None:
                self._write(dict(base, event="sent"))
            else:
                self._write(dict(base, event="refused", reason=reason))
            return context, sequence, reason

    def complete(self, context, sequence, row):
        with self.lock:
            context.statuses.append(row.get("http_status"))
            self._write(dict(record_type=LEDGER_RECORD, sequence=sequence,
                             trial_id=context.trial_id, model=context.model, arm=context.arm,
                             family=context.family, repetition=context.repetition,
                             event="completed", at=now_text(), **row))

    # -- server --------------------------------------------------------------

    def start(self, port=0):
        meter = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def do_GET(self):
                self._reply(404, {"error": {"message": "meter: only chat completions are served"}})

            def do_POST(self):
                match = PATH_PATTERN.match(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                if not match or match.group("rest") != "chat/completions":
                    self._reply(404, {"error": {"message": "meter: unknown path"}})
                    return
                try:
                    request = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._reply(400, {"error": {"message": "meter: request is not JSON"}})
                    return
                trial_id = match.group("trial")
                model = str(request.get("model", ""))
                context, sequence, refusal = meter.admit(trial_id, model)
                if refusal is not None:
                    self._reply(429, {"error": {"message": f"meter refused the request: {refusal}",
                                                "type": "meter_refusal"}})
                    return
                meter.forward(self, context, sequence, body, request)

            def _reply(self, status, payload):
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        return self.server.server_address[1]

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

    # -- forwarding ----------------------------------------------------------

    def forward(self, handler, context, sequence, body, request):
        started = time.monotonic()
        started_at = now_text()
        folder = self.transcript_folder / context.trial_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{sequence:05d}-request.json").write_bytes(body)
        text = body.decode("utf-8", errors="replace")
        row = dict(
            started_at=started_at,
            request_sha256=hashlib.sha256(body).hexdigest(),
            request_bytes=len(body),
            stream=bool(request.get("stream")),
            messages=len(request.get("messages") or []),
            tools=len(request.get("tools") or []),
            max_tokens=request.get("max_tokens", request.get("max_completion_tokens")),
            temperature=request.get("temperature"),
            material_markers_present=[marker in text for marker in context.material_markers],
        )
        received = bytearray()
        status = None
        outcome = "ok"
        try:
            connection = http.client.HTTPConnection(*self.upstream, timeout=self.upstream_timeout)
            connection.request("POST", "/v1/chat/completions", body=body,
                               headers={"Content-Type": "application/json",
                                        "Accept": handler.headers.get("Accept", "*/*")})
            response = connection.getresponse()
            status = response.status
            handler.send_response(status)
            handler.send_header("Content-Type",
                                response.getheader("Content-Type", "application/json"))
            handler.end_headers()
            while True:
                chunk = response.read1(65536) if hasattr(response, "read1") else response.read(65536)
                if not chunk:
                    break
                received.extend(chunk)
                handler.wfile.write(chunk)
                handler.wfile.flush()
            connection.close()
            if status == 429:
                outcome = "rate_limited"
            elif status >= 500:
                outcome = "provider_error"
            elif status >= 400:
                outcome = "request_error"
        except (OSError, http.client.HTTPException) as error:
            outcome = "upstream_unreachable" if status is None else "stream_interrupted"
            row["error"] = type(error).__name__
            if status is None:
                try:
                    payload = json.dumps({"error": {"message": "meter: upstream unreachable"}})
                    handler.send_response(502)
                    handler.send_header("Content-Type", "application/json")
                    handler.end_headers()
                    handler.wfile.write(payload.encode("utf-8"))
                except OSError:
                    pass
        (folder / f"{sequence:05d}-response.txt").write_bytes(bytes(received))
        row.update(http_status=status, outcome=outcome,
                   elapsed_ms=int((time.monotonic() - started) * 1000),
                   response_bytes=len(received), **summarize_response(bytes(received)))
        self.complete(context, sequence, row)


def summarize_response(data):
    """Usage, finish reason and tool names from a streamed or plain response."""
    usage = None
    finish = None
    tools = []
    content_chars = reasoning_chars = 0
    text = data.decode("utf-8", errors="replace")
    payloads = []
    if text.lstrip().startswith("{"):
        try:
            payloads.append(json.loads(text))
        except json.JSONDecodeError:
            pass
    else:
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            item = line[5:].strip()
            if item == "[DONE]":
                continue
            try:
                payloads.append(json.loads(item))
            except json.JSONDecodeError:
                continue
    for payload in payloads:
        if isinstance(payload.get("usage"), dict):
            usage = {key: payload["usage"].get(key)
                     for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        for choice in payload.get("choices") or []:
            if choice.get("finish_reason"):
                finish = choice["finish_reason"]
            part = choice.get("delta") or choice.get("message") or {}
            content_chars += len(part.get("content") or "")
            reasoning_chars += len(part.get("reasoning") or part.get("reasoning_content") or "")
            for call in part.get("tool_calls") or []:
                name = (call.get("function") or {}).get("name")
                if name:
                    tools.append(name)
    return dict(usage=usage, finish_reason=finish, tool_calls=tools,
                content_chars=content_chars, reasoning_chars=reasoning_chars)
