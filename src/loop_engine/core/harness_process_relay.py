"""Private stdlib relay for a Loop-owned isolated harness process.

This is an internal adapter, not another executable graph vertex. It exposes
one local OpenAI-compatible endpoint inside an isolated network namespace.
Real model authority stays in the parent broker. This file runs standalone in
the sandbox so optional harness dependencies never enter the engine process.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _decode(value):
    return json.loads(value, object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError("nonfinite JSON")))


def _receive(sock, count):
    output = bytearray()
    while len(output) < count:
        part = sock.recv(min(65536, count - len(output)))
        if not part:
            raise ValueError("truncated broker frame")
        output.extend(part)
    return bytes(output)


def _exchange(config, request):
    data = _json(request)
    if len(data) > config["maximum_request_bytes"]:
        raise ValueError("request byte limit exceeded")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(config["timeout_seconds"])
        client.connect("/relay/broker.sock")
        client.sendall(len(data).to_bytes(8, "big") + data)
        size = int.from_bytes(_receive(client, 8), "big")
        if size > config["maximum_response_bytes"]:
            raise ValueError("response byte limit exceeded")
        return _decode(_receive(client, size))


def _stream_chunks(response):
    """Convert a completed broker response into an equivalent finite SSE stream."""
    common = {key: response[key] for key in ("id", "created", "model") if key in response}
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("broker response has no choices")
    initial, final = [], []
    for index, choice in enumerate(choices):
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ValueError("broker response has no assistant message")
        delta = dict(message)
        if isinstance(delta.get("tool_calls"), list):
            delta["tool_calls"] = [dict(call, index=i) for i, call in enumerate(delta["tool_calls"])]
        initial.append({"index": choice.get("index", index), "delta": delta,
                        "finish_reason": None})
        final.append({"index": choice.get("index", index), "delta": {},
                      "finish_reason": choice.get("finish_reason", "stop")})
    yield {**common, "object": "chat.completion.chunk", "choices": initial}
    yield {**common, "object": "chat.completion.chunk", "choices": final,
           **({"usage": response["usage"]} if "usage" in response else {})}


def _handler(config):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, status, value):
            data = _json(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path not in ("/models", "/v1/models"):
                self._reply(404, {"error": {"message": "unsupported relay endpoint"}})
                return
            self._reply(200, {"object": "list", "data": [
                {"id": config["model"], "object": "model"}]})

        def do_POST(self):
            try:
                self.connection.settimeout(config["timeout_seconds"])
                google = config["style"] == "gemini_cli"
                anthropic = config["style"] == "nanocode"
                # openinterpreter_rust runs the OpenAI chat wire (its recipe
                # declares wire_api "chat"); a Responses post from it still
                # takes the strict Responses decode. Model identity and the
                # tool ban are enforced host-side for both wires.
                responses = (config["style"] == "codex" or (
                    config["style"] == "openinterpreter_rust"
                    and self.path == "/v1/responses"))
                if (not google and not anthropic and not responses
                        and self.path not in ("/chat/completions", "/v1/chat/completions")):
                    self._reply(404, {"error": {"message": "unsupported relay endpoint"}})
                    return
                length = self.headers.get("Content-Length", "")
                if (not length.isdecimal() or not 0 < int(length) <= config["maximum_request_bytes"]
                        or self.headers.get("Transfer-Encoding")):
                    self._reply(413, {"error": {"message": "invalid request byte length"}})
                    return
                raw = self.rfile.read(int(length))
                if len(raw) != int(length):
                    raise ValueError("truncated request")
                request = _decode(raw)
                if not isinstance(request, dict):
                    raise ValueError("request must be an object")
                responses_stream = request.get("stream") is True
                if responses:
                    if __package__:
                        from .harness_responses_recipes import decode_responses_text_request, encode_responses_text_events
                    else:
                        from harness_responses_recipes import decode_responses_text_request, encode_responses_text_events
                    request = decode_responses_text_request(self.path, request, config["model"])
                if google:
                    if __package__:
                        from .harness_additional_recipes import decode_google_request, encode_google_response
                    else:
                        from harness_additional_recipes import decode_google_request, encode_google_response
                    request = decode_google_request(self.path, request, config["model"])
                if anthropic:
                    if __package__:
                        from .harness_lightweight_recipes import decode_anthropic_text_request, encode_anthropic_text_response
                    else:
                        from harness_lightweight_recipes import decode_anthropic_text_request, encode_anthropic_text_response
                    request = decode_anthropic_text_request(self.path, request, config["model"])
                request["_harness_wire"] = {
                    "protocol": ("google_generate_content" if google else "anthropic_messages"
                                 if anthropic else "openai_responses" if responses else "openai_chat_completions"),
                    "path": self.path, "body_sha256": hashlib.sha256(raw).hexdigest(),
                    "body_bytes": len(raw)}
                response = _exchange(config, request)
                if "error" in response:
                    self._reply(400, response)
                elif anthropic:
                    self._reply(200, encode_anthropic_text_response(response, config["model"]))
                elif responses:
                    events = encode_responses_text_events(response, config["model"])
                    if responses_stream:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        for event in events:
                            self.wfile.write(b"event: " + event["type"].encode("ascii")
                                + b"\ndata: " + _json(event) + b"\n\n")
                    else:
                        self._reply(200, events[-1]["response"])
                elif google:
                    converted = encode_google_response(response, config["model"])
                    if request.get("stream") is True:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        self.wfile.write(b"data: " + _json(converted) + b"\n\n")
                    else:
                        self._reply(200, converted)
                elif request.get("stream") is True:
                    chunks = tuple(_stream_chunks(response))
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    for chunk in chunks:
                        self.wfile.write(b"data: " + _json(chunk) + b"\n\n")
                    self.wfile.write(b"data: [DONE]\n\n")
                else:
                    self._reply(200, response)
            except (ValueError, TypeError, OSError, RecursionError):
                try:
                    self._reply(400, {"error": {"message": "harness relay refused request"}})
                except OSError:
                    pass
    return Handler


def _recipe(config, base):
    """Pinned style recipes; task content always travels through private files."""
    prefix, style, model = list(config["command_prefix"]), config["style"], config["model"]
    if style == "aider":
        return prefix + ["--model", "openai/" + model, "--openai-api-base", base,
            "--openai-api-key", "loop-engine-local-relay", "--no-check-update",
            "--no-analytics", "--no-show-release-notes", "--no-git", "--no-stream",
            "--no-pretty", "--no-show-model-warnings", "--no-check-model-accepts-settings",
            "--map-tokens", "0", "--edit-format", "ask", "--yes-always",
            "--message-file", "/relay/task.txt"]
    if style == "continue":
        body = {"name": "Loop Engine confined model adapter", "version": "1.0.0", "schema": "v1",
                "models": [{"name": "loop-engine-model", "provider": "openai", "model": model,
                    "apiKey": "loop-engine-local-relay", "apiBase": base, "roles": ["chat"],
                    "defaultCompletionOptions": {"maxTokens": config["output_allowance"]}}]}
        Path("/work/model-config.yaml").write_bytes(_json(body))
        return prefix + ["--config", "/work/model-config.yaml", "--exclude", "*",
            "-p", "--format", "json", "--prompt", "/relay/task.txt",
            "Follow the task in the supplied prompt file."]
    if style == "pi":
        models = {"providers": {"engine": {"baseUrl": base,
            "api": "openai-completions", "apiKey": "loop-engine-local-relay",
            "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False,
                       "supportsStore": False, "maxTokensField": "max_tokens"},
            "models": [{"id": model, "name": model, "reasoning": False, "input": ["text"],
                "contextWindow": config["context_capacity"],
                "maxTokens": config["output_capacity"]}]}}}
        agent = Path("/work/home/.pi/agent")
        agent.mkdir(parents=True, exist_ok=True)
        (agent / "models.json").write_bytes(_json(models))
        return prefix + ["--provider", "engine", "--model", model, "--mode", "json",
            "--print", "--no-session", "--no-tools", "--no-context-files", "--no-extensions",
            "--no-skills", "--no-prompt-templates", "--no-themes", "--no-approve", "@/relay/task.txt"]
    raise ValueError("uninstalled harness process style")


def main():
    config = _decode(Path("/relay/config.json").read_bytes())
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(config))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_port}/v1"
        if config["style"] in ("hermes_agent", "forgecode"):
            from harness_remaining_recipes import prepare_remaining_recipe
            command, overrides, prompt = prepare_remaining_recipe(config["style"], config, base)
            return subprocess.run(command, input=prompt, stdin=subprocess.DEVNULL if prompt is None else None,
                                  env={**os.environ, **overrides}).returncode
        if config["style"] in ("codex", "openinterpreter_rust"):
            from harness_responses_recipes import prepare_responses_recipe
            command, overrides, prompt = prepare_responses_recipe(config["style"], config, base)
            return subprocess.run(command, input=prompt, env={**os.environ, **overrides}).returncode
        if config["style"] in ("nanocode", "trae_agent"):
            from harness_lightweight_recipes import prepare_lightweight_recipe, prepare_trae_semantic_recipe
            command, overrides, prompt = (prepare_trae_semantic_recipe(config, base)
                if config["style"] == "trae_agent" else prepare_lightweight_recipe("nanocode", config, base))
            return subprocess.run(command, input=prompt, stdin=subprocess.DEVNULL if prompt is None else None,
                                  env={**os.environ, **overrides}).returncode
        if config["style"] in ("mini_swe_agent", "mistral_vibe", "gptme", "cline", "kilo"):
            if config["style"] == "mini_swe_agent":
                from harness_mini_swe_recipe import prepare_mini_swe_recipe
                command, overrides, prompt = prepare_mini_swe_recipe(config, base)
            elif config["style"] in ("mistral_vibe", "gptme"):
                from harness_python_recipes import prepare_python_recipe
                command, overrides, prompt = prepare_python_recipe(config["style"], config, base)
            else:
                from harness_cline_kilo_recipes import prepare_cline_kilo_recipe
                command, overrides, prompt = prepare_cline_kilo_recipe(config["style"], config, base)
            return subprocess.run(command, input=prompt, stdin=subprocess.DEVNULL if prompt is None else None,
                                  env={**os.environ, **overrides}).returncode
        if config["style"] == "opencode":
            from harness_opencode_recipe import prepare_opencode_recipe
            command, overrides, prompt = prepare_opencode_recipe(config, base)
            return subprocess.run(command, input=prompt, stdin=subprocess.DEVNULL if prompt is None else None,
                                  env={**os.environ, **overrides}).returncode
        if config["style"] == "goose":
            from harness_goose_recipe import prepare_goose_recipe
            command, overrides, prompt = prepare_goose_recipe(config, base)
            return subprocess.run(command, input=prompt, env={**os.environ, **overrides}).returncode
        if config["style"] in ("qwen_code", "gemini_cli"):
            from harness_additional_recipes import prepare_recipe
            command, overrides, prompt = prepare_recipe(config["style"], config, base)
            environment = {**os.environ, **overrides}
            return subprocess.run(command, input=prompt, env=environment).returncode
        return subprocess.call(_recipe(config, base), stdin=subprocess.DEVNULL, env=dict(os.environ))
    finally:
        server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
