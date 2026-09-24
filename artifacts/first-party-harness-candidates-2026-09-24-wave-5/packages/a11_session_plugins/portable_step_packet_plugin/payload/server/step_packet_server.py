"""Effects: reads the step folder under the workspace root and writes new result files through the write-step-result skill script; answers tool calls on standard input and output; opens no network connection and starts no process.

A small local Model Context Protocol server for the portable step packet
plugin. It reads newline-delimited JSON-RPC 2.0 messages on standard input,
writes one answer line for each request on standard output, writes
diagnostics only to standard error, and stops when standard input closes.

Tools, each described by contracts/<tool>.input.schema.json:
  read_step_assignment  the assignment card of the current step
  read_step_file        one text file of the step folder
  write_step_result     check the result and save it as a new numbered file

The tools run the functions of the two portable skills of this plugin,
loaded by their exact paths, so the skills and the server give the same
answers. The workspace root is --root, else the folder that holds .baltor
when this file sits below a .baltor folder, else the current folder.

Usage: python3 -I -B step_packet_server.py [--root PATH] [--step-dir .baltor/step]
Python 3.10 or later, standard library only. Licence: MIT.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

SERVER_NAME = "portable_step_packet_plugin"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_LINE_BYTES = 1024 * 1024
MAX_ANSWER_BYTES = 256 * 1024
PLUGIN = Path(__file__).resolve().parent.parent
READER = PLUGIN / "skills" / "read-step-assignment" / "scripts" / "read_assignment.py"
WRITER = PLUGIN / "skills" / "write-step-result" / "scripts" / "write_result.py"
CONTRACTS = PLUGIN / "contracts"
INSTRUCTIONS = ("Call read_step_assignment first. Read node_context.md and checklist.md with read_step_file. "
                "Give the finished result to write_step_result; it never overwrites an earlier result.")
DESCRIPTIONS = {
    "read_step_assignment": "Read the assignment of the current focused step from .baltor/step: the task fields, "
                            "the packet files, the required output fields and earlier results. Call it first, "
                            "with no arguments.",
    "read_step_file": "Read one UTF-8 text file of the step folder .baltor/step, named relative to that folder, "
                      "for example node_context.md or contracts/output.schema.json. At most 32 KiB.",
    "write_step_result": "Check the step result against the required fields and top-level types of the packet's "
                         "output schema, then save it as a new numbered file that is never overwritten. Give the "
                         "whole result as the argument result.",
}
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603
TYPE_CHECKS = {"string": lambda value: isinstance(value, str), "object": lambda value: isinstance(value, dict),
               "array": lambda value: isinstance(value, list), "boolean": lambda value: isinstance(value, bool),
               "integer": lambda value: isinstance(value, int) and not isinstance(value, bool)}


class Duplicate(ValueError):
    """A JSON object repeats a key."""


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_line(data: bytes):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise Duplicate(f"duplicate key {key!r}"[:120])
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard number {name}")

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def load_contracts() -> dict:
    tools = {}
    for name, description in DESCRIPTIONS.items():
        schema = parse_line((CONTRACTS / f"{name}.input.schema.json").read_bytes())
        tools[name] = {"name": name, "description": description, "inputSchema": schema}
    return tools


def argument_problem(schema: dict, arguments) -> str:
    """The first way the arguments break the tool's contract, or an empty string."""
    if not isinstance(arguments, dict):
        return "arguments must be a JSON object"
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in arguments:
            return f"missing argument {name}"
    for name, value in arguments.items():
        if name not in properties:
            return f"unknown argument {str(name)[:60]}"
        rule = properties[name]
        check = TYPE_CHECKS.get(rule.get("type"))
        if check is not None and not check(value):
            return f"argument {name} must be {rule['type']}"
        if isinstance(value, str) and not rule.get("minLength", 0) <= len(value) <= rule.get("maxLength", 10 ** 9):
            return f"argument {name} has a length outside {rule.get('minLength', 0)} to {rule.get('maxLength')}"
    return ""


class Server:
    def __init__(self, root: Path, step_relative: str) -> None:
        self.root = root
        self.step = step_relative
        self.reader = load_module(READER, "portable_step_read_assignment")
        self.writer = load_module(WRITER, "portable_step_write_result")
        self.tools = load_contracts()

    def call_tool(self, name: str, arguments: dict) -> dict:
        refusal_types = (self.reader.Refused, self.writer.Refused)
        try:
            if name == "read_step_assignment":
                answer, failed = self.reader.read_assignment(self.root, self.step), False
            elif name == "read_step_file":
                answer, failed = self.reader.read_step_file(self.root, arguments["name"], self.step), False
            else:
                code, answer = self.writer.write_result(self.root, arguments["result"], self.step)
                failed = code != 0
        except refusal_types as error:
            answer, failed = {"error": error.code, "detail": error.detail}, True
        except OSError as error:
            answer, failed = {"error": "os_error", "detail": type(error).__name__}, True
        return {"content": [{"type": "text", "text": json.dumps(answer, ensure_ascii=False, separators=(",", ":"))}],
                "structuredContent": answer, "isError": failed}

    def handle(self, message) -> dict | None:
        if isinstance(message, list):
            return error_answer(None, INVALID_REQUEST, "batch requests are not supported")
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            request_id = message.get("id") if isinstance(message, dict) and valid_id(message.get("id")) else None
            return error_answer(request_id, INVALID_REQUEST, "expected a JSON-RPC 2.0 request object")
        if "id" not in message:
            return None  # a notification, such as notifications/initialized, gets no answer
        request_id = message["id"]
        if not valid_id(request_id):
            return error_answer(None, INVALID_REQUEST, "id must be a string or an integer")
        method, params = message["method"], message.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return error_answer(request_id, INVALID_PARAMS, "params must be a JSON object")
        if method == "initialize":
            asked = params.get("protocolVersion")
            version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
            return result_answer(request_id, {"protocolVersion": version,
                                              "capabilities": {"tools": {"listChanged": False}},
                                              "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                                              "instructions": INSTRUCTIONS})
        if method == "ping":
            return result_answer(request_id, {})
        if method == "tools/list":
            return result_answer(request_id, {"tools": list(self.tools.values())})
        if method == "tools/call":
            name, arguments = params.get("name"), params.get("arguments", {})
            if not isinstance(name, str) or name not in self.tools:
                return error_answer(request_id, INVALID_PARAMS, f"unknown tool {str(name)[:60]}")
            problem = argument_problem(self.tools[name]["inputSchema"], {} if arguments is None else arguments)
            if problem:
                return error_answer(request_id, INVALID_PARAMS, problem)
            return result_answer(request_id, self.call_tool(name, arguments or {}))
        return error_answer(request_id, METHOD_NOT_FOUND, f"method not found: {method[:60]}")


def valid_id(value) -> bool:
    return isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool))


def result_answer(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_answer(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def encode(answer: dict) -> bytes:
    """One answer line within the byte limit. A tool answer that is too large becomes a tool error."""
    data = json.dumps(answer, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(data) <= MAX_ANSWER_BYTES:
        return data
    if "result" in answer and "content" in answer["result"]:
        refusal = {"error": "answer_too_large", "detail": f"above {MAX_ANSWER_BYTES} bytes"}
        small = {"content": [{"type": "text", "text": json.dumps(refusal)}], "structuredContent": refusal,
                 "isError": True}
        return encode(result_answer(answer["id"], small))
    return encode(error_answer(answer.get("id"), INTERNAL_ERROR, "answer too large"))


def read_line(stream) -> tuple[bytes | None, bool]:
    """(line, too_long). A line above the limit is read to its end and dropped. None means input closed."""
    line = stream.readline(MAX_LINE_BYTES + 1)
    if not line:
        return None, False
    if len(line) <= MAX_LINE_BYTES or line.endswith(b"\n"):
        return line, False
    while True:
        rest = stream.readline(MAX_LINE_BYTES)
        if not rest or rest.endswith(b"\n"):
            return b"", True


def serve(server: Server, source, sink) -> int:
    while True:
        line, too_long = read_line(source)
        if line is None:
            return 0
        if too_long:
            answer = error_answer(None, INVALID_REQUEST, f"a request line is above {MAX_LINE_BYTES} bytes")
        elif not line.strip():
            continue
        else:
            try:
                message = parse_line(line)
            except (ValueError, UnicodeDecodeError, RecursionError) as error:
                answer = error_answer(None, PARSE_ERROR, f"unreadable JSON: {type(error).__name__}")
            else:
                try:
                    answer = server.handle(message)
                except Exception as error:  # noqa: BLE001 - one bad request must not stop the server
                    sys.stderr.write(f"{SERVER_NAME}: internal error {type(error).__name__}\n")
                    answer = error_answer(message.get("id") if isinstance(message, dict) and valid_id(message.get("id"))
                                          else None, INTERNAL_ERROR, "internal error")
        if answer is not None:
            sink.write(encode(answer))
            sink.flush()


def default_root(script: Path, cwd: Path) -> Path:
    parts = script.parts
    if ".baltor" in parts:
        return Path(*parts[: parts.index(".baltor")])
    return cwd


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Local standard-input server for the portable step packet plugin.")
    parser.add_argument("--root", help="workspace root; default the folder that holds .baltor, else the current folder")
    parser.add_argument("--step-dir", default=".baltor/step", help="step folder relative to the root")
    options = parser.parse_args(argv)
    root = Path(options.root).resolve() if options.root else default_root(Path(__file__).resolve(), Path.cwd().resolve())
    try:
        server = Server(root, options.step_dir)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"{SERVER_NAME}: cannot start: {type(error).__name__}: {str(error)[:200]}\n")
        return 2
    sys.stderr.write(f"{SERVER_NAME}: serving the step folder {options.step_dir} under {root}\n")
    try:
        return serve(server, sys.stdin.buffer, sys.stdout.buffer)
    except (BrokenPipeError, KeyboardInterrupt):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
