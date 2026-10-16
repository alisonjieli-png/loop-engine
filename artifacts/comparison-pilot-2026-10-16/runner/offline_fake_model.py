"""A scripted OpenAI-compatible endpoint for plumbing checks, never a model.

The pilot runner's offline check points the counting proxy at this server
instead of Ollama Cloud, so that the sandbox, the harness configuration, the
egress proxy and the event capture can be exercised with zero provider calls.
Each request receives the next scripted reply as a streamed chat completion:
a tool call while the script lasts, then a final text answer. Every request
body is saved for inspection. Evidence produced this way is labelled as a
fixture, not task-solving model evidence.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class FakeModel:
    def __init__(self, script, save_folder):
        self.script = list(script)
        self.save_folder = Path(save_folder)
        self.calls = 0
        self.lock = threading.Lock()
        self.server = None

    def next_reply(self):
        with self.lock:
            index = self.calls
            self.calls += 1
        if index < len(self.script):
            return index, self.script[index]
        return index, {"text": "DONE"}

    def start(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                index, reply = fake.next_reply()
                fake.save_folder.mkdir(parents=True, exist_ok=True)
                (fake.save_folder / f"{index:03d}-request.json").write_bytes(body)
                chunks = []
                base = {"id": f"fake-{index}", "object": "chat.completion.chunk", "model": "fixture"}
                if "tool" in reply:
                    call = {"index": 0, "id": f"call_{index}", "type": "function",
                            "function": {"name": reply["tool"], "arguments": json.dumps(reply["arguments"])}}
                    chunks.append(dict(base, choices=[{"index": 0, "delta": {"role": "assistant", "tool_calls": [call]},
                                                       "finish_reason": None}]))
                    finish = "tool_calls"
                else:
                    chunks.append(dict(base, choices=[{"index": 0, "delta": {"role": "assistant",
                                                                            "content": reply["text"]},
                                                       "finish_reason": None}]))
                    finish = "stop"
                chunks.append(dict(base, choices=[{"index": 0, "delta": {}, "finish_reason": finish}]))
                chunks.append(dict(base, choices=[], usage={"prompt_tokens": 10, "completion_tokens": 2,
                                                            "total_tokens": 12}))
                data = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(data.encode("utf-8"))

            def do_GET(self):
                payload = json.dumps({"object": "list", "data": [{"id": "fixture", "object": "model"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self.server.server_address[1]

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
