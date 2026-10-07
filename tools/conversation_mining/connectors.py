"""Read-only connectors to local conversation corpora.

Each connector yields plain ``(locator, role, timestamp, text)`` tuples for
one transcript source. Locators are opaque local identifiers (never URLs).
Connectors never follow network links, never fetch images, and never write.

Supported sources:
- Claude Code project transcripts (``~/.claude/projects/**.jsonl``)
- Codex session rollouts (``~/.codex/sessions/**/rollout-*.jsonl``)
- ChatGPT account exports (``conversations.json`` inside a .zip, or a bare
  ``conversations.json``)
- plain prompt logs (one prompt per line, ``# role:`` comment prefixes allowed)

The connectors are deliberately tolerant: a malformed line or file yields a
``read_error`` row instead of raising, so one bad export never loses the rest.
"""
from __future__ import annotations

import json
import hashlib
import re
import zipfile
from pathlib import Path
from typing import Iterator, NamedTuple

READ_ERROR = "read_error"
MAX_DOCUMENT_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 4 * 1024 * 1024
MAX_TURN_CHARACTERS = 4000


def _bounded_lines(stream):
    """Consume a long physical line in bounded chunks, then report that line as refused."""
    number = 0
    while True:
        line = stream.readline(MAX_LINE_BYTES + 1)
        if not line:
            break
        number += 1
        if len(line) > MAX_LINE_BYTES:
            while line and not line.endswith("\n"):
                line = stream.readline(MAX_LINE_BYTES + 1)
            yield number, None
        else:
            yield number, line


def _locator(source, path):
    return source + ":" + hashlib.sha256(str(path.absolute()).encode()).hexdigest()[:24]


def _context_only(text):
    return text.startswith(("# AGENTS.md instructions", "<environment_context>", "<task-notification>",
                            "<local-command-", "<command-name>", "[Request interrupted"))


class Turn(NamedTuple):
    locator: str
    role: str            # "user" for owner lines, "assistant", or READ_ERROR
    timestamp: str
    text: str


def _clip(text: str, limit: int = MAX_TURN_CHARACTERS) -> str:
    """Bound memory per turn; long paste blobs are truncated, never dropped."""
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


def claude_code(path: Path) -> Iterator[Turn]:
    """One JSONL row per event; user text lives in message.content (str or block list)."""
    locator = _locator("claude", path)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for number, line in _bounded_lines(handle):
                if line is None:
                    yield Turn(locator, READ_ERROR, "", "line_exceeds_read_bound")
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    yield Turn(locator, READ_ERROR, "", "json_decode")
                    continue
                if not isinstance(rec, dict):
                    yield Turn(locator, READ_ERROR, "", "record_not_object")
                    continue
                if rec.get("type") != "user":
                    continue
                message = rec.get("message") or {}
                if not isinstance(message, dict):
                    yield Turn(locator, READ_ERROR, "", "message_not_object")
                    continue
                content = message.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "".join(
                        block.get("text", "") for block in content
                        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
                    )
                else:
                    text = ""
                text = text.strip()
                if not text or _context_only(text):
                    continue
                yield Turn(locator + f":line:{number}", "user", str(rec.get("timestamp", "")), _clip(text))
    except OSError as error:
        yield Turn(locator, READ_ERROR, "", f"os_error:{type(error).__name__}")


def codex_rollout(path: Path) -> Iterator[Turn]:
    """Rollout JSONL; user text in payload.message(content=[{text}]) with role user."""
    locator = _locator("codex", path)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for number, line in _bounded_lines(handle):
                if line is None:
                    yield Turn(locator, READ_ERROR, "", "line_exceeds_read_bound")
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    yield Turn(locator, READ_ERROR, "", "json_decode")
                    continue
                if not isinstance(rec, dict):
                    yield Turn(locator, READ_ERROR, "", "record_not_object")
                    continue
                payload = rec.get("payload") or {}
                if not isinstance(payload, dict):
                    yield Turn(locator, READ_ERROR, "", "payload_not_object")
                    continue
                if payload.get("type") != "message" or payload.get("role") != "user":
                    continue
                content = payload.get("content") or []
                text = (content if isinstance(content, str) else " ".join(
                    item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str)
                ) if isinstance(content, list) else "").strip()
                if not text or _context_only(text):
                    continue
                yield Turn(locator + f":line:{number}", "user", str(rec.get("timestamp", "")), _clip(text))
    except OSError as error:
        yield Turn(locator, READ_ERROR, "", f"os_error:{type(error).__name__}")


def chatgpt_export(path: Path) -> Iterator[Turn]:
    """conversations.json (bare or inside a .zip); user text in mapping[].message."""
    locator = _locator("chatgpt", path)

    def read_document(raw) -> Iterator[Turn]:
        try:
            conversations = json.loads(raw)
        except json.JSONDecodeError:
            yield Turn(locator, READ_ERROR, "", "conversations_json_decode")
            return
        if not isinstance(conversations, list):
            yield Turn(locator, READ_ERROR, "", "conversations_not_list")
            return
        for number, conv in enumerate(conversations):
            if not isinstance(conv, dict):
                continue
            mapping = conv.get("mapping") or {}
            if not isinstance(mapping, dict):
                yield Turn(locator, READ_ERROR, "", "mapping_not_object")
                continue
            for node_id, node in mapping.items():
                if not isinstance(node, dict):
                    continue
                message = node.get("message") or {}
                if not isinstance(message, dict) or not isinstance(message.get("author") or {}, dict):
                    yield Turn(locator, READ_ERROR, "", "message_or_author_not_object")
                    continue
                author = ((message.get("author") or {}).get("role"))
                if author != "user":
                    continue
                content = message.get("content") or {}
                parts = content.get("parts") if isinstance(content, dict) else None
                if not isinstance(parts, list):
                    continue
                text = " ".join(str(part) for part in parts if isinstance(part, str)).strip()
                if not text:
                    continue
                stamp = message.get("create_time")
                suffix = hashlib.sha256(str(node_id).encode()).hexdigest()[:16]
                yield Turn(locator + f":conversation:{number}:turn:{suffix}", "user",
                           str(stamp or ""), _clip(text))

    try:
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                names = [n for n in archive.namelist() if n.endswith("conversations.json")]
                if len(names) != 1 or archive.getinfo(names[0]).file_size > MAX_DOCUMENT_BYTES:
                    yield Turn(locator, READ_ERROR, "", "no_conversations_json")
                    return
                yield from read_document(archive.read(names[0]).decode("utf-8", "replace"))
        else:
            if path.stat().st_size > MAX_DOCUMENT_BYTES:
                yield Turn(locator, READ_ERROR, "", "document_exceeds_read_bound")
                return
            yield from read_document(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, zipfile.BadZipFile) as error:
        yield Turn(locator, READ_ERROR, "", f"open_error:{type(error).__name__}")


def prompt_log(path: Path) -> Iterator[Turn]:
    """One non-empty, non-comment line per turn."""
    locator = _locator("promptlog", path)
    try:
        with path.open(encoding="utf-8", errors="replace") as stream:
            lines = _bounded_lines(stream)
            yield from _prompt_lines(locator, lines)
    except OSError as error:
        yield Turn(locator, READ_ERROR, "", f"os_error:{type(error).__name__}")


def _prompt_lines(locator, lines):
    for number, line in lines:
        if line is None:
            yield Turn(locator, READ_ERROR, "", "line_exceeds_read_bound")
            continue
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        yield Turn(locator + f":line:{number}", "user", "", _clip(text))


CONNECTORS = {
    "claude_code_jsonl": claude_code,
    "codex_rollout_jsonl": codex_rollout,
    "chatgpt_export_json": chatgpt_export,
    "prompt_log_text": prompt_log,
}
