"""Private stdlib relay for a Loop-owned isolated harness process.

This is an internal adapter, not another executable graph vertex. It exposes
one local model endpoint inside an isolated network namespace. Real model
authority stays in the parent broker. This file runs standalone in the sandbox
so optional harness dependencies never enter the engine process.
The recipe record and the codec records of its wires arrive in the private
configuration. The relay chooses a wire by request path from those records and
loads only the modules mounted beside it, each after its catalogue digest
matches; it names no harness style.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import importlib.util
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


def _select_wire(wires, path):
    """The one declared wire whose request paths match, or None.

    ``wires`` are the ``harness_wire_codec/v1`` records of the recipe; the
    catalogue already refused a recipe whose wires' paths overlap."""
    for wire in wires:
        paths = wire["request_paths"]
        if wire["path_match"] == "exact" and path in paths:
            return wire
        if wire["path_match"] == "prefix" and any(path.startswith(prefix) for prefix in paths):
            return wire
    return None


def _load_mounted_module(name, sha256, directory=None):
    """Load one recipe or codec module mounted beside the relay, after its
    bytes match the digest the recipe catalogue recorded."""
    if not isinstance(name, str) or not name.isidentifier() or not isinstance(sha256, str):
        raise ValueError("a mounted module needs an exact name and digest")
    path = Path(directory or Path(__file__).parent) / (name + ".py")
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        raise ValueError("mounted module differs from its catalogue digest")
    qualified = "loop_engine_mounted_" + name + "_" + sha256[:16]
    if qualified in sys.modules:
        return sys.modules[qualified]
    spec = importlib.util.spec_from_file_location(qualified, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(qualified, None)
        raise
    return module


#: How an answer is written back, by the framing a wire record declares.
_FRAMINGS = ("openai_chat_chunks", "responses_events", "single_data_event", "none")


def _wire_table(config, directory=None):
    """The recipe's declared wires, each with its decoder and encoder loaded."""
    records = {wire["wire_protocol"]: wire for wire in config["wire_codecs"]}
    table = []
    for name in config["recipe"]["wire_protocols"]:
        wire = dict(records[name])
        if wire["stream_framing"] not in _FRAMINGS:
            raise ValueError("unknown stream framing")
        if wire["module"] is None:
            wire["decode"], wire["encode"] = None, None
        else:
            module = _load_mounted_module(wire["module"], wire["module_sha256"], directory)
            wire["decode"] = getattr(module, wire["decode_function"])
            wire["encode"] = getattr(module, wire["encode_function"])
        table.append(wire)
    return table


def _handler(config, wires):
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

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

        def do_GET(self):
            if self.path not in ("/models", "/v1/models"):
                self._reply(404, {"error": {"message": "unsupported relay endpoint"}})
                return
            self._reply(200, {"object": "list", "data": [
                {"id": config["model"], "object": "model"}]})

        def _answer(self, wire, response, streamed):
            framing = wire["stream_framing"]
            if framing == "openai_chat_chunks":
                if not streamed:
                    self._reply(200, response)
                    return
                chunks = tuple(_stream_chunks(response))
                self._events()
                for chunk in chunks:
                    self.wfile.write(b"data: " + _json(chunk) + b"\n\n")
                self.wfile.write(b"data: [DONE]\n\n")
                return
            encoded = wire["encode"](response, config["model"])
            if framing == "responses_events":
                if not streamed:
                    self._reply(200, encoded[-1]["response"])
                    return
                self._events()
                for event in encoded:
                    self.wfile.write(b"event: " + event["type"].encode("ascii")
                        + b"\ndata: " + _json(event) + b"\n\n")
            elif framing == "single_data_event" and streamed:
                self._events()
                self.wfile.write(b"data: " + _json(encoded) + b"\n\n")
            else:
                self._reply(200, encoded)

        def do_POST(self):
            try:
                self.connection.settimeout(config["timeout_seconds"])
                wire = _select_wire(wires, self.path)
                if wire is None:
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
                streamed = request.get("stream") is True
                if wire["decode"] is not None:
                    request = wire["decode"](self.path, request, config["model"])
                streamed = streamed or request.get("stream") is True
                request["_harness_wire"] = {
                    "protocol": wire["wire_protocol"], "path": self.path,
                    "body_sha256": hashlib.sha256(raw).hexdigest(), "body_bytes": len(raw)}
                response = _exchange(config, request)
                if "error" in response:
                    self._reply(400, response)
                else:
                    self._answer(wire, response, streamed)
            except (ValueError, TypeError, OSError, RecursionError):
                try:
                    self._reply(400, {"error": {"message": "harness relay refused request"}})
                except OSError:
                    pass
    return Handler


def main():
    """Prepare the recipe the configuration names, serve its wires, run it."""
    config = _decode(Path("/relay/config.json").read_bytes())
    recipe = config["recipe"]
    wires = _wire_table(config)
    module = _load_mounted_module(recipe["module"], recipe["module_sha256"])
    prepare = getattr(module, recipe["prepare_function"])
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(config, wires))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_port}/v1"
        command, overrides, prompt = prepare(recipe["style"], config, base)
        return subprocess.run(list(command), input=prompt,
                              stdin=subprocess.DEVNULL if prompt is None else None,
                              env={**os.environ, **overrides}).returncode
    finally:
        server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
