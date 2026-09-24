"""Effects: reads one saved session log under --root, or standard input, and prints one JSON object; writes no files and uses no network.

Find assistant turns that write a tool call as plain text instead of making a
structured call, and report their rate. A small local model that cannot use a
harness's tool interface often answers with JSON such as {"name": "write",
"arguments": {...}}, with a tool name followed by a JSON object, or with a call
inside a Markdown code fence or a <tool_call> tag. The harness reads that reply as
a final answer and the step ends with no work done.

Session logs are read in these shapes: Claude Code JSONL, Codex rollout JSONL, Pi
session JSONL, Pi JSON event output, an OpenCode export, OpenAI-compatible chat
JSON or JSONL, a captured OpenAI-compatible stream of "data:" lines, Gemini
contents JSON, and a generic {"turns": [...]} document. Only turns with no
structured call are scanned, and hidden reasoning text is never scanned. By
default the output names tools and argument keys but quotes no text from the log.

Exit status: 0 when the rate of text-written calls is at or below --max-rate, 1 when
it is above it (or when --expect-calls is given and no structured call was made), 2
when the input is refused.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path

RECORD_TYPE = "text_tool_call_scan/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 512 * 1024 * 1024
SCAN_CHARACTERS = 256 * 1024
MAX_DECODE_ATTEMPTS = 2000
MAX_FLAGGED_LISTED = 50
NAME = re.compile(r"^[A-Za-z_][\w.\-:/]{0,63}$")
NAME_KEYS = ("name", "tool", "tool_name", "toolName", "function_name", "functionName", "action")
ARGUMENT_KEYS = ("arguments", "parameters", "args", "input", "arguments_json", "action_input", "params", "kwargs")
CALL_TYPES = ("function", "tool_use", "toolCall", "tool_call", "function_call")
# Small models sometimes write typographic double quotes inside otherwise valid JSON.
TYPOGRAPHIC_DOUBLE_QUOTES = str.maketrans({"“": '"', "”": '"'})
FENCE = re.compile(r"```[ \t]*([\w+-]*)[ \t]*\n(.*?)```", re.DOTALL)
TAGGED = (
    re.compile(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", re.DOTALL),
    re.compile(r"<function_call>\s*(.*?)\s*(?:</function_call>|$)", re.DOTALL),
    re.compile(r"<tool_use>\s*(.*?)\s*(?:</tool_use>|$)", re.DOTALL),
    re.compile(r"<\|tool_call\|>\s*(.*)", re.DOTALL),
    re.compile(r"<\|python_tag\|>\s*(.*)", re.DOTALL),
    re.compile(r"\[TOOL_CALLS\]\s*(.*)", re.DOTALL),
)
TAGGED_NAMED = (re.compile(r"<function=([\w.\-:/]{1,64})>"), re.compile(r"<invoke name=\"([\w.\-:/]{1,64})\""))
# A line that starts with a bare name and then a JSON object, such as: write {"path": "out.csv"}
NAME_THEN_OBJECT = re.compile(r"^[ \t>*-]*`?([A-Za-z_][\w.\-]{0,63})`?[ \t]*:?[ \t]*(?=\{)", re.MULTILINE)
# The start of call-shaped JSON that does not parse, for example because the reply was cut off
# or a command string holds unescaped quotes.
BROKEN_CALL = re.compile(
    r"\{\s*\"(?:name|tool|tool_name|function_name|function)\"\s*:\s*\"([A-Za-z_][\w.\-:/]{0,63})\"\s*,\s*"
    r"\"(?:arguments|parameters|args|input|action_input|params)\"\s*:")
INTENT = re.compile(r"\b(?:I will|I'll|I am going to|I'm going to|let me|now I will|next I will|calling|invoking|"
                    r"using)\b[^.\n]{0,40}?\b(?:call|use|run|invoke)?\s*(?:the\s+)?`?([\w.\-]{1,64})`?\s+(?:tool|function)\b",
                    re.IGNORECASE)
PYTHONIC = re.compile(r"^\s*\[?([A-Za-z_][\w.]{0,63})\((?:[\w]+\s*=|\"|'|\)|\{)", re.MULTILINE)
CODEX_CALL_TYPES = {"function_call", "custom_tool_call", "local_shell_call", "web_search_call", "tool_search_call",
                    "mcp_tool_call", "image_generation_call"}
CODEX_INPUT_TYPES = {"function_call_output", "custom_tool_call_output", "local_shell_call_output",
                     "mcp_tool_call_output", "tool_search_output"}
PI_EVENT_TYPES = {"message_end", "tool_execution_start", "tool_execution_end"}
KINDS = ("json_text", "broken_json_text", "tagged_text", "name_then_json", "unknown_name_then_json", "named_in_prose")
LOW_CONFIDENCE_KINDS = ("unknown_name_then_json", "named_in_prose")
FORMATS = ("auto", "claude_code", "codex", "pi", "pi_events", "opencode", "openai_chat", "openai_stream", "gemini",
           "generic")


class Refused(Exception):
    """Raised for input the script will not read."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D401 - argparse hook
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": f"arguments: {message}"})
        raise SystemExit(2)


def emit(document: dict) -> None:
    sys.stdout.write(json.dumps(document, indent=1, ensure_ascii=False) + "\n")


def read_input(name: str, root: Path, max_bytes: int) -> bytes:
    if name == "-":
        data = sys.stdin.buffer.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise Refused(f"standard input is larger than {max_bytes} bytes")
        return data
    if not name or "\x00" in name:
        raise Refused("the log path is empty or holds a NUL character")
    given = Path(name)
    if ".." in given.parts:
        raise Refused("the log path may not contain '..'")
    real_root = root.resolve(strict=True)
    try:
        real = (given if given.is_absolute() else real_root / given).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise Refused(f"the log path cannot be resolved: {type(error).__name__}") from error
    if real_root not in real.parents:
        raise Refused("the log path leaves --root, directly or through a symbolic link")
    descriptor = os.open(real, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise Refused("the log is not a regular file")
        if info.st_size > max_bytes:
            raise Refused(f"the log is {info.st_size} bytes, above the limit of {max_bytes}")
        chunks, total = [], 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise Refused(f"the log grew above the limit of {max_bytes} bytes while it was read")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


# ---------------------------------------------------------------------------
# normalizing logs into turns
# ---------------------------------------------------------------------------

class Turns:
    """Collects assistant turns in order; an input event closes the open turn."""

    def __init__(self):
        self.turns: list[dict] = []
        self.open: dict | None = None
        self.known_tools: set[str] = set()

    def output(self, key, line, text: str = "", call: str | None = None) -> None:
        if self.open is None or (key is not None and self.open["key"] is not None and self.open["key"] != key):
            self.close()
            self.open = {"key": key, "line": line, "text": [], "calls": []}
        if text:
            self.open["text"].append(text)
        if call is not None:
            self.open["calls"].append(call)
            if call:
                self.known_tools.add(call)

    def boundary(self) -> None:
        self.close()

    def close(self) -> None:
        if self.open is not None:
            self.turns.append({"line": self.open["line"], "text": "\n".join(self.open["text"]),
                               "calls": self.open["calls"]})
            self.open = None

    def done(self) -> list[dict]:
        self.close()
        return self.turns


def text_of(content) -> list[str]:
    """Visible text of OpenAI or generic content: a string, or a list of text parts."""
    if isinstance(content, str):
        return [content]
    parts = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") in ("text", "output_text") and isinstance(item.get("text"), str):
                parts.append(item["text"])
    return parts


def openai_message(message: dict, turns: Turns, line) -> None:
    role = message.get("role")
    if role == "assistant":
        calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []
        names = []
        for call in calls:
            function = call.get("function") if isinstance(call, dict) else None
            names.append(function.get("name", "") if isinstance(function, dict) else "")
        if isinstance(message.get("function_call"), dict):
            names.append(message["function_call"].get("name", ""))
        turns.output(None, line, "\n".join(text_of(message.get("content"))))
        for name in names:
            turns.output(None, line, call=str(name))
        turns.close()
    elif role in ("user", "tool", "function", "system", "developer"):
        turns.boundary()


def declared_tools(document: dict, turns: Turns) -> None:
    for tool in document.get("tools", []) if isinstance(document.get("tools"), list) else []:
        if isinstance(tool, dict):
            function = tool.get("function") if isinstance(tool.get("function"), dict) else tool
            if isinstance(function.get("name"), str):
                turns.known_tools.add(function["name"])


def from_openai(documents: list[tuple[int | None, object]]) -> Turns:
    turns = Turns()
    responses = [(line, doc) for line, doc in documents if isinstance(doc, dict)
                 and (isinstance(doc.get("choices"), list) or isinstance(doc.get("message"), dict)
                      or isinstance(doc.get("response"), dict))]
    for _line, doc in documents:
        if isinstance(doc, dict):
            declared_tools(doc, turns)
            if isinstance(doc.get("request"), dict):
                declared_tools(doc["request"], turns)
    if responses:
        for line, doc in responses:
            body = doc.get("response") if isinstance(doc.get("response"), dict) else doc
            if isinstance(body.get("choices"), list):
                for choice in body["choices"]:
                    if isinstance(choice, dict) and isinstance(choice.get("message"), dict):
                        openai_message(choice["message"], turns, line)
            elif isinstance(body.get("message"), dict):
                openai_message(body["message"], turns, line)
        return turns
    histories = [(line, doc) for line, doc in documents if isinstance(doc, dict) and isinstance(doc.get("messages"), list)]
    if histories:
        line, doc = max(histories, key=lambda item: len(item[1]["messages"]))
        for message in doc["messages"]:
            if isinstance(message, dict):
                openai_message(message, turns, line)
        return turns
    for line, doc in documents:
        if isinstance(doc, list):
            for message in doc:
                if isinstance(message, dict):
                    openai_message(message, turns, line)
    return turns


def from_openai_stream(documents) -> Turns:
    """Join streamed chunk deltas into turns; a finish reason or a [DONE] line ends a turn."""
    turns = Turns()
    pending = {"line": None, "text": [], "calls": []}

    def finish():
        if pending["line"] is not None:
            key = ("stream", pending["line"])
            turns.output(key, pending["line"], "".join(pending["text"]))
            for name in pending["calls"]:
                turns.output(key, pending["line"], call=name)
            turns.close()
        pending.update({"line": None, "text": [], "calls": []})

    for line, doc in documents:
        if doc == "[DONE]":
            finish()
            continue
        if not isinstance(doc, dict):
            continue
        for choice in doc.get("choices", []) if isinstance(doc.get("choices"), list) else []:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
            if pending["line"] is None:
                pending["line"] = line
            if isinstance(delta.get("content"), str):
                pending["text"].append(delta["content"])
            for call in delta.get("tool_calls") or []:
                function = call.get("function") if isinstance(call, dict) else None
                if isinstance(function, dict) and function.get("name"):
                    pending["calls"].append(str(function["name"]))
            if choice.get("finish_reason"):
                finish()
    finish()
    return turns


def from_claude_code(documents) -> Turns:
    turns = Turns()
    for line, doc in documents:
        if not isinstance(doc, dict) or not isinstance(doc.get("message"), dict):
            continue
        message = doc["message"]
        if doc.get("type") == "assistant" and message.get("role") == "assistant":
            key = message.get("id") or doc.get("requestId") or doc.get("uuid")
            content = message.get("content")
            blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
            if not blocks:
                turns.output(key, line)
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    turns.output(key, line, block["text"])
                elif block.get("type") in ("tool_use", "server_tool_use"):
                    turns.output(key, line, call=str(block.get("name", "")))
                else:
                    turns.output(key, line)
        elif doc.get("type") == "user":
            turns.boundary()
    return turns


def from_codex(documents) -> Turns:
    turns = Turns()
    for line, doc in documents:
        if not isinstance(doc, dict) or doc.get("type") != "response_item" or not isinstance(doc.get("payload"), dict):
            continue
        payload = doc["payload"]
        kind = payload.get("type")
        if kind == "message":
            if payload.get("role") == "assistant":
                turns.output(None, line, "\n".join(text_of(payload.get("content"))))
            else:
                turns.boundary()
        elif kind in CODEX_CALL_TYPES:
            turns.output(None, line, call=str(payload.get("name") or kind))
        elif kind in CODEX_INPUT_TYPES:
            turns.boundary()
    return turns


def pi_message(message: dict, turns: Turns, key, line) -> None:
    """One Pi message object: an assistant reply becomes a turn; any other role is an input."""
    if message.get("role") != "assistant":
        turns.boundary()
        return
    content = message.get("content") if isinstance(message.get("content"), list) else []
    turns.output(key, line)
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            turns.output(key, line, block["text"])
        elif block.get("type") == "toolCall":
            turns.output(key, line, call=str(block.get("name", "")))
    turns.close()


def from_pi(documents) -> Turns:
    turns = Turns()
    for line, doc in documents:
        if not isinstance(doc, dict) or doc.get("type") != "message" or not isinstance(doc.get("message"), dict):
            continue
        pi_message(doc["message"], turns, ("pi", line), line)
    return turns


def from_pi_events(documents) -> Turns:
    """Pi JSON event output: whole messages arrive in message_end events.

    A tool_execution_start event names a tool the harness ran. When the assistant
    turn just before it recorded no call block, the call is credited to that turn.
    """
    turns = Turns()
    last_assistant = None
    for line, doc in documents:
        if not isinstance(doc, dict):
            continue
        kind = doc.get("type")
        if kind == "tool_execution_start":
            name = doc.get("toolName")
            if isinstance(name, str) and name:
                turns.known_tools.add(name)
                if last_assistant is not None and not turns.turns[last_assistant]["calls"]:
                    turns.turns[last_assistant]["calls"].append(name)
            continue
        if kind != "message_end" or not isinstance(doc.get("message"), dict):
            continue
        message = doc["message"]
        pi_message(message, turns, ("pi_events", line), line)
        last_assistant = len(turns.turns) - 1 if message.get("role") == "assistant" else None
    return turns


def from_opencode(document: dict) -> Turns:
    turns = Turns()
    for number, message in enumerate(document.get("messages", [])):
        if not isinstance(message, dict):
            continue
        info = message.get("info") if isinstance(message.get("info"), dict) else {}
        if info.get("role") != "assistant":
            turns.boundary()
            continue
        step = 0
        for part in message.get("parts", []) if isinstance(message.get("parts"), list) else []:
            if not isinstance(part, dict):
                continue
            kind = part.get("type")
            if kind == "step-start":
                step += 1
                turns.output(("opencode", number, step), None)
            elif kind == "text" and isinstance(part.get("text"), str):
                turns.output(("opencode", number, step), None, part["text"])
            elif kind == "tool":
                turns.output(("opencode", number, step), None, call=str(part.get("tool", "")))
        turns.close()
    return turns


def from_gemini(contents: list) -> Turns:
    turns = Turns()
    for number, content in enumerate(contents):
        if not isinstance(content, dict):
            continue
        if content.get("role") == "model":
            key = ("gemini", number)
            turns.output(key, None)
            for part in content.get("parts", []) if isinstance(content.get("parts"), list) else []:
                if not isinstance(part, dict):
                    continue
                if isinstance(part.get("functionCall"), dict):
                    turns.output(key, None, call=str(part["functionCall"].get("name", "")))
                elif isinstance(part.get("text"), str) and not part.get("thought"):
                    turns.output(key, None, part["text"])
            turns.close()
        else:
            turns.boundary()
    return turns


def from_generic(items: list) -> Turns:
    turns = Turns()
    for number, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if item.get("role") == "assistant":
            calls = item.get("tool_calls") if isinstance(item.get("tool_calls"), list) else []
            turns.output(("generic", number), None, str(item.get("text") or ""))
            for call in calls:
                name = call.get("name") if isinstance(call, dict) else call
                turns.output(("generic", number), None, call=str(name or ""))
            turns.close()
        else:
            turns.boundary()
    return turns


def parse_documents(text: str) -> tuple[str, object, list[tuple[int | None, object]], int]:
    """Return ('json', value, [], 0) for one JSON value, ('jsonl', None, lines, bad) for JSON Lines,
    or ('stream', None, lines, bad) for a captured stream of data: lines."""
    stripped = text.strip()
    if not stripped:
        raise Refused("the log is empty")
    events = [line for line in text.splitlines() if line.strip()]
    if sum(1 for line in events if line.startswith("data:")) >= max(1, int(len(events) * 0.8)):
        documents, bad = [], 0
        for number, line in enumerate(text.splitlines(), 1):
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                documents.append((number, "[DONE]"))
                continue
            try:
                documents.append((number, json.loads(payload)))
            except ValueError:
                bad += 1
        return "stream", None, documents, bad
    try:
        value = json.loads(stripped)
    except ValueError:
        value = None
    else:
        line_types = PI_EVENT_TYPES | {"message", "response_item", "session_meta", "assistant", "user", "session"}
        if isinstance(value, dict) and value.get("type") in line_types:
            return "jsonl", None, [(1, value)], 0  # a JSON Lines log with a single line
        return "json", value, [], 0
    documents, bad = [], 0
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            documents.append((number, json.loads(line)))
        except ValueError:
            bad += 1
    if not documents:
        raise Refused("the log is neither JSON nor JSON Lines")
    if bad > max(10, len(documents) // 10):
        raise Refused(f"{bad} lines are not JSON; the log is not a JSON Lines session file")
    return "jsonl", None, documents, bad


def looks_generic(items: list) -> bool:
    return bool(items) and all(isinstance(item, dict) and "role" in item and "content" not in item
                               and "parts" not in item and ("text" in item or "tool_calls" in item)
                               for item in items[:20])


def detect(kind: str, value, documents) -> str:
    if kind == "stream":
        return "openai_stream"
    if kind == "json":
        if isinstance(value, dict) and isinstance(value.get("turns"), list):
            return "generic"
        if isinstance(value, dict) and isinstance(value.get("messages"), list) and value["messages"] and all(
                isinstance(item, dict) and "parts" in item and "info" in item for item in value["messages"][:5]):
            return "opencode"
        contents = value if isinstance(value, list) else (value.get("contents") or value.get("history")) \
            if isinstance(value, dict) else None
        if isinstance(contents, list) and contents and all(isinstance(item, dict) and "parts" in item and
                                                            item.get("role") in ("user", "model")
                                                            for item in contents[:5]):
            return "gemini"
        if isinstance(value, list) and looks_generic(value):
            return "generic"
        return "openai_chat"
    sample = [doc for _line, doc in documents[:200] if isinstance(doc, dict)]
    if any(doc.get("type") in PI_EVENT_TYPES for doc in sample):
        return "pi_events"
    if any(doc.get("type") in ("response_item", "session_meta") for doc in sample):
        return "codex"
    if any(doc.get("type") == "message" and isinstance(doc.get("message"), dict) for doc in sample):
        return "pi"
    if any(doc.get("type") in ("assistant", "user") and isinstance(doc.get("message"), dict) for doc in sample):
        return "claude_code"
    return "openai_chat"


def normalize(fmt: str, kind: str, value, documents) -> Turns:
    if fmt == "generic":
        items = value.get("turns") if isinstance(value, dict) else value
        if not isinstance(items, list):
            raise Refused("a generic log is {\"turns\": [...]} or a list of turns")
        turns = from_generic(items)
        tools = value.get("tools") if isinstance(value, dict) and isinstance(value.get("tools"), list) else []
        turns.known_tools.update(str(tool) for tool in tools if isinstance(tool, str))
        return turns
    if fmt == "opencode":
        if not isinstance(value, dict):
            raise Refused("an OpenCode export is one JSON object with messages")
        return from_opencode(value)
    if fmt == "gemini":
        contents = value if isinstance(value, list) else (value.get("contents") or value.get("history")) \
            if isinstance(value, dict) else None
        if not isinstance(contents, list):
            raise Refused("a Gemini log is a list of contents, or an object with contents or history")
        return from_gemini(contents)
    if fmt == "openai_stream":
        if kind != "stream":
            raise Refused("an OpenAI-compatible stream is a series of 'data:' lines")
        return from_openai_stream(documents)
    rows = documents if kind in ("jsonl", "stream") else [(None, value)]
    if fmt == "claude_code":
        return from_claude_code(rows)
    if fmt == "codex":
        return from_codex(rows)
    if fmt == "pi":
        return from_pi(rows)
    if fmt == "pi_events":
        return from_pi_events(rows)
    return from_openai(rows)


# ---------------------------------------------------------------------------
# finding calls written as text
# ---------------------------------------------------------------------------

def argument_keys(value) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    if isinstance(value, dict):
        return sorted(str(key)[:40] for key in value)[:10]
    return []


def call_shape(value, depth: int = 0) -> tuple[str, list[str]] | None:
    """Return (tool name, argument keys) when a parsed JSON value looks like a tool call."""
    if depth > 3:
        return None
    if isinstance(value, list):
        for item in value[:5]:
            shape = call_shape(item, depth + 1)
            if shape:
                return shape
        return None
    if not isinstance(value, dict):
        return None
    function = value.get("function")
    if isinstance(function, dict) and isinstance(function.get("name"), str) and NAME.match(function["name"]):
        return function["name"], argument_keys(function.get("arguments", function.get("parameters")))
    if isinstance(value.get("tool_calls"), list):
        return call_shape(value["tool_calls"], depth + 1)
    for name_key in NAME_KEYS:
        name = value.get(name_key)
        if isinstance(name, str) and NAME.match(name):
            for argument_key in ARGUMENT_KEYS:
                if argument_key in value and isinstance(value[argument_key], (dict, str, list)):
                    return name, argument_keys(value[argument_key])
    if value.get("type") in CALL_TYPES and isinstance(value.get("name"), str) and NAME.match(value["name"]):
        return value["name"], argument_keys(value.get("input", value.get("arguments")))
    return None


def json_candidates(text: str):
    """Yield (parsed value, start, end, in_fence) for JSON values in code fences, then in the rest of the text."""
    decoder = json.JSONDecoder()
    budget = [MAX_DECODE_ATTEMPTS]

    def values(body: str, offset: int, in_fence: bool):
        index = 0
        while index < len(body) and budget[0] > 0:
            if body[index] in "{[":
                budget[0] -= 1
                try:
                    value, end = decoder.raw_decode(body, index)
                except ValueError:
                    index += 1
                    continue
                yield value, offset + index, offset + end, in_fence
                index = end
                continue
            index += 1

    fences = list(FENCE.finditer(text))
    for match in fences:
        yield from values(match.group(2), match.start(2), True)
    outside, cursor = [], 0
    for match in fences:
        outside.append((cursor, text[cursor:match.start()]))
        cursor = match.end()
    outside.append((cursor, text[cursor:]))
    for offset, part in outside:
        yield from values(part, offset, False)


def in_any_fence(text: str, position: int) -> bool:
    return any(match.start() <= position < match.end() for match in FENCE.finditer(text))


def finding(kind: str, tool: str, keys: list[str], in_fence: bool, window: str, start: int, excerpts: bool) -> dict:
    record = {"kind": kind, "confidence": "low" if kind in LOW_CONFIDENCE_KINDS else "high", "in_fence": in_fence,
              "tool": tool, "argument_keys": keys}
    if excerpts:
        record["excerpt"] = window[start:start + 160]
    return record


def scan_turn(text: str, known: set[str], excerpts: bool) -> dict | None:
    """Return the strongest sign in one turn's visible text that a call was written as text, or None."""
    window = text[:SCAN_CHARACTERS].translate(TYPOGRAPHIC_DOUBLE_QUOTES)
    known_lower = {name.lower() for name in known}
    decoder = json.JSONDecoder()
    for pattern in TAGGED:
        for match in pattern.finditer(window):
            try:
                shape = call_shape(decoder.raw_decode(match.group(1).lstrip())[0])
            except ValueError:
                shape = None
            if shape:
                return finding("tagged_text", shape[0], shape[1], False, window, match.start(), excerpts)
            # a tag that holds no call-shaped JSON is prose about the format, not a call
    for pattern in TAGGED_NAMED:
        match = pattern.search(window)
        if match:
            return finding("tagged_text", match.group(1), [], False, window, match.start(), excerpts)
    for value, start, _end, in_fence in json_candidates(window):
        shape = call_shape(value)
        if shape:
            return finding("json_text", shape[0], shape[1], in_fence, window, start, excerpts)
    unknown = None
    for match in NAME_THEN_OBJECT.finditer(window):
        name, brace = match.group(1), match.end()
        try:
            value = decoder.raw_decode(window, brace)[0]
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        if name.lower() in known_lower:
            return finding("name_then_json", name, argument_keys(value), in_any_fence(window, brace), window,
                           match.start(1), excerpts)
        if unknown is None:
            unknown = finding("unknown_name_then_json", name, argument_keys(value), in_any_fence(window, brace),
                              window, match.start(1), excerpts)
    broken = BROKEN_CALL.search(window)
    if broken:
        return finding("broken_json_text", broken.group(1), [], in_any_fence(window, broken.start()), window,
                       broken.start(), excerpts)
    if unknown is not None:
        return unknown
    if known_lower:
        for pattern in (INTENT, PYTHONIC):
            for match in pattern.finditer(window):
                if match.group(1).lower() in known_lower:
                    return finding("named_in_prose", match.group(1), [], False, window, match.start(), excerpts)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(description="Detect tool calls written as plain text in a saved session log.")
    parser.add_argument("log", nargs="?", default="-", help="session log file, or - for standard input")
    parser.add_argument("--format", default="auto", choices=FORMATS)
    parser.add_argument("--tool", action="append", default=[], help="a tool name the harness offered; repeatable")
    parser.add_argument("--max-rate", type=float, default=0.0, help="highest accepted share of turns, 0 to 1")
    parser.add_argument("--count-low-confidence", action="store_true",
                        help="also count low-confidence findings, such as a tool named in prose")
    parser.add_argument("--expect-calls", action="store_true",
                        help="fail when the log holds no structured call at all")
    parser.add_argument("--excerpts", action="store_true", help="include up to 160 characters of each finding")
    parser.add_argument("--root", default=".", help="folder the log path must stay inside")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    options = parser.parse_args(argv)
    try:
        if not 0.0 <= options.max_rate <= 1.0:
            raise Refused("--max-rate must be between 0 and 1")
        if not 0 < options.max_bytes <= HARD_MAX_BYTES:
            raise Refused(f"--max-bytes must be between 1 and {HARD_MAX_BYTES}")
        root = Path(options.root)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        data = read_input(options.log, root, options.max_bytes)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise Refused("the log is not UTF-8 text") from error
        kind, value, documents, bad_lines = parse_documents(text)
        fmt = detect(kind, value, documents) if options.format == "auto" else options.format
        turns_collector = normalize(fmt, kind, value, documents)
        turns = turns_collector.done()
        if not turns:
            raise Refused(f"no assistant turn was found when reading the log as {fmt}; check --format")
    except Refused as error:
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": str(error)})
        return 2
    known = set(turns_collector.known_tools) | set(options.tool)
    known.discard("")
    flagged, structured, low_confidence, long_turns = [], 0, 0, 0
    kinds = {name: 0 for name in KINDS}
    kinds["json_text_in_fence"] = 0
    last_flagged = False
    for number, turn in enumerate(turns, 1):
        last_flagged = False
        if turn["calls"]:
            structured += 1
            continue
        if len(turn["text"]) > SCAN_CHARACTERS:
            long_turns += 1
        found = scan_turn(turn["text"], known, options.excerpts)
        if found is None:
            continue
        kinds[found["kind"]] += 1
        if found["kind"] == "json_text" and found["in_fence"]:
            kinds["json_text_in_fence"] += 1
        counted = found["confidence"] == "high" or options.count_low_confidence
        if found["confidence"] == "low":
            low_confidence += 1
        if counted:
            last_flagged = number == len(turns)
        found["known_tool"] = found["tool"].lower() in {name.lower() for name in known} if known else None
        flagged.append(dict(found, turn=number, line=turn["line"], counted=counted))
    counted_items = [item for item in flagged if item["counted"]]
    rate = round(len(counted_items) / len(turns), 4)
    notes = []
    if bad_lines:
        notes.append(f"{bad_lines} lines that are not JSON were left out")
    if long_turns:
        notes.append(f"{long_turns} turns are longer than {SCAN_CHARACTERS} characters; only their start was scanned")
    if not known:
        notes.append("no tool names were known, so a bare name before JSON and prose mentions stay low confidence; "
                     "pass --tool")
    if fmt in ("opencode", "gemini"):
        notes.append(f"the {fmt} shape was built from documented or stored records, not from a saved export "
                     "observed with this script")
    if rate > options.max_rate:
        status, code = "text_calls_detected", 1
    elif structured == 0 and options.expect_calls:
        status, code = "no_structured_calls", 1
    elif structured == 0:
        status, code = "no_tool_calls", 0
    else:
        status, code = "structured_calls_work", 0
    document = {
        "record_type": RECORD_TYPE, "status": status, "format": fmt, "assistant_turns": len(turns),
        "turns_with_structured_calls": structured, "text_call_turns": len(counted_items), "rate": rate,
        "max_rate": options.max_rate, "kinds": kinds, "low_confidence_turns": low_confidence,
        "last_turn_flagged": last_flagged, "known_tools": sorted(known)[:50],
        "flagged": flagged[:MAX_FLAGGED_LISTED], "omitted_flagged": max(len(flagged) - MAX_FLAGGED_LISTED, 0),
        "notes": notes,
    }
    emit(document)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
