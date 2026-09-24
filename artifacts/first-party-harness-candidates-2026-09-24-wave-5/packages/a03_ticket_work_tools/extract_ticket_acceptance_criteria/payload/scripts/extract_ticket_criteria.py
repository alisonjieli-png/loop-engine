"""Effects: reads one ticket file under --root, or standard input, lists folder entries under --root to check named files, and prints one JSON object; writes no files and uses no network.

Turn a ticket exported as Markdown, plain text or JSON into a numbered checklist:
acceptance criteria, reproduction steps, expected and actual behavior, named files
and commands. Each criterion is marked checkable or not by fixed rules, so a ticket
that states no checkable outcome is flagged instead of being completed by guesswork.
The ticket is data: nothing in it is run or followed.

Exit status: 0 when at least one criterion is checkable, 1 when the ticket states no
checkable outcome, 2 when the input is refused (unsafe path, too large, not UTF-8,
unreadable JSON, or more than one ticket).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

RECORD_TYPE = "ticket_criteria/v1"
DEFAULT_MAX_BYTES = 4 * 1024 * 1024
HARD_MAX_BYTES = 64 * 1024 * 1024
MAX_WALK_ENTRIES = 50000
MAX_MATCHES = 5
MAX_FILES = 100
SKIP_FOLDERS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".nox",
                ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", "site-packages", ".idea"}

# Issue templates carry guidance in HTML comments; the opening marker is assembled so
# that this file itself holds no comment marker.
TEMPLATE_COMMENT = re.compile(re.escape("<" + "!--") + r".*?" + re.escape("--" + ">"), re.DOTALL)
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
BOLD_LINE = re.compile(r"^\s{0,3}(?:\*\*|__)(.+?)(?:\*\*|__)\s*:?\s*$")
SETEXT = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")
THEMATIC = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
LABEL = re.compile(r"^\s{0,3}([A-Za-z][A-Za-z /()'-]{1,40}?)\s*:\s*(.*)$")
ITEM = re.compile(r"^(\s*)(?:[-*+]|\d{1,3}[.)])\s+(?:\[( |x|X)\]\s+)?(.*\S)\s*$")
FENCE = re.compile(r"^\s{0,3}(```+|~~~+)\s*([\w+-]*)")
GHERKIN_START = re.compile(r"^\s*(?:[-*+]\s+)?(Given)\s+(.*\S)\s*$", re.IGNORECASE)
GHERKIN_NEXT = re.compile(r"^\s*(?:[-*+]\s+)?(When|Then|And|But)\s+(.*\S)\s*$", re.IGNORECASE)
SCENARIO = re.compile(r"^\s*(?:[-*+]\s+)?Scenario(?: Outline)?\s*:\s*(.*)$", re.IGNORECASE)
URL = re.compile(r"\b(?:https?|ftp)://\S+")
EXTENSIONS = ("py|pyi|ipynb|js|jsx|ts|tsx|mjs|cjs|go|rs|java|kt|kts|scala|rb|php|cs|fs|c|cc|cpp|cxx|h|hh|hpp|m|mm|"
              "swift|dart|lua|pl|r|jl|sql|sh|bash|zsh|ps1|json|jsonl|yaml|yml|toml|ini|cfg|conf|xml|html|htm|css|"
              "scss|less|vue|svelte|md|rst|txt|csv|tsv|lock|gradle|properties|proto|graphql|tf|hcl|env")
FILE_TOKEN = re.compile(r"(?<![\w/.@-])((?:\.{0,2}/)?(?:[\w.-]+/)*[\w-][\w.-]*\.(?:" + EXTENSIONS +
                        r"))(?::(\d+))?(?![\w/])", re.IGNORECASE)
BARE_FILES = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*(?:Dockerfile|Makefile|Procfile|Gemfile|Rakefile|Jenkinsfile|"
                        r"Containerfile|Justfile))(?![\w.])")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
COMMAND_WORDS = ("pytest", "python", "python3", "pip ", "npm ", "npx ", "yarn", "pnpm", "node ", "make", "go test",
                 "go run", "go build", "cargo", "mvn", "gradle", "./", "bash ", "sh ", "uv run", "poetry run", "tox",
                 "nox", "dotnet", "bundle exec", "rake", "ruby ", "php ", "java ", "deno", "bun ", "ctest", "cmake")
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?!\w|[.,]\d)|\b\d+(?:[.,]\d+)?\s*(?:%|ms|s|sec|seconds?|minutes?|"
                    r"hours?|kb|mb|gb|rows?|items?|times|px|bytes?)\b", re.IGNORECASE)
# Spelled-out numbers from two upward; "one" and "once" are left out because they are so
# often a pronoun or a conjunction.
NUMBER_WORDS = re.compile(r"\b(?:zero|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|"
                          r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|twice)\b", re.IGNORECASE)
# Values that ticket forms print for a field nobody filled in.
EMPTY_VALUES = {"no response", "n/a", "none", "-"}
TITLE_LABEL = re.compile(r"^\s{0,3}(?:subject|title)\s*:\s*(\S.*)$", re.IGNORECASE)
EMPHASIS = re.compile(r"(\*\*|__)(.+?)\1")
QUOTED = re.compile(r"\"[^\"\n]{1,200}\"|(?<![\w])'[^'\n]{1,200}'(?![\w])|`[^`\n]{1,200}`|"
                    "\u201c[^\u201d\n]{1,200}\u201d")
OBSERVABLE = re.compile(r"\b(?:return|returns|returned|show|shows|shown|display|displays|print|prints|output|outputs|"
                        r"exit|exits|raise|raises|throw|throws|log|logs|write|writes|save|saves|saved|create|creates|"
                        r"delete|deletes|contain|contains|equal|equals|match|matches|respond|responds|redirect|"
                        r"redirects|reject|rejects|refuse|refuses|accept|accepts|fail|fails|pass|passes|sort|sorts|"
                        r"sorted|round|rounds|keep|keeps|kept|preserve|preserves|appear|appears|disappear|disappears|"
                        r"list|lists|count|counts|send|sends|sent|store|stores|load|loads|parse|parses|skip|skips|"
                        r"include|includes|exclude|excludes|allow|allows|block|blocks|open|opens|close|closes|"
                        r"download|downloads|upload|uploads|error|message|status|unchanged|same|identical|remain|remains|"
                        r"stay|stays|change|changes|changed|no longer|does not|do not|doesn't|never|must not|"
                        r"cannot)\b", re.IGNORECASE)
VAGUE = re.compile(r"\b(?:fast|faster|fastest|quick|quicker|slow|slower|better|best|improve|improved|improves|"
                   r"improvement|nice|nicer|clean|cleaner|user[- ]friendly|intuitive|seamless|seamlessly|robust|"
                   r"reliable|reliably|easy|easier|simple|simpler|modern|good|great|properly|correctly|gracefully|"
                   r"appropriately|appropriate|optimal|optimized|efficient|efficiently|performant|reasonable|"
                   r"reasonably|smooth|smoother|polished|elegant|scalable|as expected|works well|look good|"
                   r"looks good|feel|feels|enhance|enhanced|streamline|streamlined|etc)\b", re.IGNORECASE)
MODAL = re.compile(r"\b(?:must|should|shall|needs to|need to|has to|have to|is required to|are required to)\b",
                   re.IGNORECASE)
BUG_WORDS = re.compile(r"\b(?:bug|error|crash|crashes|exception|traceback|broken|regression|wrong)\b", re.IGNORECASE)
SECTION_WORDS = (
    ("reproduction", ("steps to reproduce", "reproduction steps", "reproduction", "reproduce", "repro",
                      "how to trigger")),
    ("expected", ("expected behavior", "expected behaviour", "expected result", "expected results", "expected")),
    ("actual", ("actual behavior", "actual behaviour", "actual result", "actual results", "actual", "observed",
                "current behavior", "current behaviour", "current bug behavior", "current bug behaviour",
                "bug behavior", "bug behaviour", "what happens", "what actually happens")),
    ("acceptance", ("acceptance criteria", "acceptance", "definition of done", "done when", "success criteria",
                    "exit criteria", "requirements")),
    ("other", ("notes", "note", "relevant code", "links", "environment", "background", "see also", "related",
               "screenshots", "logs", "version", "versions", "additional information", "description", "summary",
               "workaround", "context")),
)
JSON_KEYS = {
    "title": ("title", "summary", "name", "subject", "headline"),
    "body": ("body", "description", "content", "text", "details"),
    "acceptance": ("acceptancecriteria", "acceptance", "criteria", "definitionofdone", "dod", "successcriteria"),
    "reproduction": ("stepstoreproduce", "reprosteps", "reproductionsteps", "reproduction", "steps"),
    "expected": ("expected", "expectedbehavior", "expectedbehaviour", "expectedresult"),
    "actual": ("actual", "actualbehavior", "actualbehaviour", "actualresult", "observed"),
}
ITEM_TEXT_KEYS = ("text", "title", "description", "summary", "name", "value")
RICH_MAX_DEPTH = 40


class Refused(Exception):
    """Raised for input the script will not read."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D401 - argparse hook
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": f"arguments: {message}"})
        raise SystemExit(2)


def emit(document: dict) -> None:
    sys.stdout.write(json.dumps(document, indent=1, ensure_ascii=False) + "\n")


def read_input(name: str, root: Path, max_bytes: int) -> tuple[bytes, str]:
    if name == "-":
        data = sys.stdin.buffer.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise Refused(f"standard input is larger than {max_bytes} bytes")
        return data, "-"
    if not name or "\x00" in name:
        raise Refused("the ticket path is empty or holds a NUL character")
    given = Path(name)
    if ".." in given.parts:
        raise Refused("the ticket path may not contain '..'")
    real_root = root.resolve(strict=True)
    try:
        real = (given if given.is_absolute() else real_root / given).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise Refused(f"the ticket path cannot be resolved: {type(error).__name__}") from error
    if real_root not in real.parents:
        raise Refused("the ticket path leaves --root, directly or through a symbolic link")
    descriptor = os.open(real, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise Refused("the ticket is not a regular file")
        if info.st_size > max_bytes:
            raise Refused(f"the ticket is {info.st_size} bytes, above the limit of {max_bytes}")
        chunks, total = [], 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise Refused(f"the ticket grew above the limit of {max_bytes} bytes while it was read")
            chunks.append(chunk)
        return b"".join(chunks), real.relative_to(real_root).as_posix()
    finally:
        os.close(descriptor)


# ---------------------------------------------------------------------------
# JSON tickets
# ---------------------------------------------------------------------------

def strict_json(text: str):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def plain_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def inline_text(value) -> str:
    if isinstance(value, dict):
        if value.get("type") == "text":
            text = str(value.get("text", ""))
            marks = {mark.get("type") for mark in value.get("marks", []) if isinstance(mark, dict)}
            return f"`{text}`" if "code" in marks else text
        if value.get("type") == "hardBreak":
            return " "
        if isinstance(value.get("content"), list):
            return "".join(inline_text(item) for item in value["content"])
    return ""


def rich_text(node, depth: int = 0) -> list[str]:
    """Flatten a rich-text document whose nodes carry type and content fields into Markdown lines."""
    if depth > RICH_MAX_DEPTH:
        raise Refused("the rich-text document is nested too deeply")
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        lines = []
        for part in node:
            lines.extend(rich_text(part, depth + 1))
        return lines
    if not isinstance(node, dict):
        return []
    kind = str(node.get("type", ""))
    parts = node.get("content") if isinstance(node.get("content"), list) else []
    if kind == "text":
        return [inline_text(node)]
    if kind == "heading":
        attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
        level = attrs.get("level", 2)
        level = level if isinstance(level, int) and 1 <= level <= 6 else 2
        return ["", "#" * level + " " + "".join(inline_text(part) for part in parts), ""]
    if kind == "paragraph":
        return ["".join(inline_text(part) for part in parts), ""]
    if kind in ("bulletList", "orderedList", "taskList"):
        lines = []
        for number, entry in enumerate(parts, 1):
            text = " ".join(line.strip() for line in rich_text(entry, depth + 1) if line.strip())
            if kind == "orderedList":
                prefix = f"{number}. "
            elif kind == "taskList":
                attrs = entry.get("attrs") if isinstance(entry, dict) and isinstance(entry.get("attrs"), dict) else {}
                prefix = "- [x] " if attrs.get("state") == "DONE" else "- [ ] "
            else:
                prefix = "- "
            lines.append(prefix + text)
        return lines + [""]
    if kind in ("listItem", "taskItem"):
        return [" ".join(line.strip() for line in rich_text(parts, depth + 1) if line.strip())]
    if kind == "codeBlock":
        return ["```", "".join(inline_text(part) for part in parts), "```", ""]
    lines = []
    for part in parts:
        lines.extend(rich_text(part, depth + 1))
    return lines


def field_text(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, list) and value and all(isinstance(item, dict) and "type" not in item for item in value):
        lines = []
        for item in value:
            text = next((item[key] for key in ITEM_TEXT_KEYS if isinstance(item.get(key), str)), None)
            if text:
                lines.append(f"- {' '.join(text.split())}")
        return "\n".join(lines)
    if isinstance(value, (dict, list)):
        return "\n".join(rich_text(value))
    return None


def json_chunks(document) -> tuple[str | None, list[tuple[str, str, str | None]]]:
    if isinstance(document, list):
        raise Refused(f"the JSON holds a list of {len(document)} values; give one ticket per run")
    if not isinstance(document, dict):
        raise Refused("the JSON ticket is not an object")
    merged = dict(document)
    for nested in ("fields", "issue", "ticket", "data"):
        if isinstance(document.get(nested), dict):
            for key, value in document[nested].items():
                merged.setdefault(key, value)
    by_plain = {}
    for key, value in merged.items():
        by_plain.setdefault(plain_key(str(key)), (key, value))
    title, chunks = None, []
    for role, names in JSON_KEYS.items():
        for name in names:
            if name not in by_plain:
                continue
            key, value = by_plain[name]
            text = field_text(value)
            if text is None or not text.strip():
                continue
            if role == "title":
                title = " ".join(text.split())[:300]
            else:
                chunks.append((str(key), text, None if role == "body" else role))
            break
    if not chunks and title is None:
        raise Refused("the JSON object has no title, body, description or criteria field")
    return title, chunks


# ---------------------------------------------------------------------------
# Markdown and plain text
# ---------------------------------------------------------------------------

def section_kind(label: str) -> str | None:
    text = " ".join(re.sub(r"[^a-z0-9' ]", " ", label.lower()).split())
    for kind, words in SECTION_WORDS:
        for word in words:
            if f" {word} " in f" {text} ":
                return kind
    return None


class ChunkParser:
    """Reads one Markdown or plain text chunk into items, scenarios, paragraphs and code blocks."""

    def __init__(self, state: dict, field: str | None, default_section: str | None):
        self.state, self.field, self.section = state, field, default_section
        self.item = self.paragraph = self.scenario = self.fence = None
        self.section_id = self.next_section_id()

    def next_section_id(self) -> int:
        self.state["section_counter"] += 1
        return self.state["section_counter"]

    def entry(self, kind: str, where, text: str, **extra) -> dict:
        self.state["sequence"] += 1
        return {"kind": kind, "section": self.section, "section_id": self.section_id, "field": self.field,
                "line": where, "text": text, "order": self.state["sequence"], "checkbox": False, **extra}

    def flush(self) -> None:
        for name in ("item", "paragraph"):
            value = getattr(self, name)
            if value is not None:
                self.state["items"].append(value)
                setattr(self, name, None)
        if self.scenario is not None:
            steps = self.scenario["steps"]
            kind = "scenario" if len(steps) >= 2 else "paragraph"
            self.state["items"].append(self.entry(kind, self.scenario["line"], " ".join(steps)))
            self.scenario = None

    def start_section(self, kind: str | None, heading_text: str, is_heading: bool) -> None:
        self.flush()
        self.section_id = self.next_section_id()
        if kind is None or kind == "other":
            self.section = "other"
            if is_heading and kind is None and self.state["title"] is None \
                    and self.state["first_heading_level"] == 1:
                self.state["title"] = heading_text.strip()
        else:
            self.section = kind
            self.state["sections_seen"].add(kind)

    def feed(self, number: int, raw: str) -> None:
        line = raw.rstrip()
        where = number if self.field is None else None
        fence_match = FENCE.match(line)
        if self.fence is not None:
            if fence_match and fence_match.group(1)[0] == self.fence["marker"][0] \
                    and len(fence_match.group(1)) >= len(self.fence["marker"]):
                self.state["code_blocks"].append(self.fence)
                self.fence = None
            else:
                self.fence["lines"].append(line)
            return
        if fence_match:
            self.flush()
            self.fence = {"marker": fence_match.group(1), "language": fence_match.group(2).lower(), "lines": [],
                          "section": self.section, "line": where}
            return
        if SETEXT.match(line) and self.paragraph is not None and self.paragraph["single_line"]:
            text = self.paragraph["text"]
            self.paragraph = None
            self.state["first_heading_level"] = self.state["first_heading_level"] or (1 if line.strip()[0] == "=" else 2)
            self.start_section(section_kind(text), text, True)
            return
        if THEMATIC.match(line):
            self.flush()
            return
        self.state["plain_lines"].append((where, self.field, line))
        heading = HEADING.match(line)
        bold = BOLD_LINE.match(line) if not heading else None
        if heading or bold:
            text = heading.group(2) if heading else bold.group(1)
            if heading and self.state["first_heading_level"] is None:
                self.state["first_heading_level"] = len(heading.group(1))
            self.start_section(section_kind(text), text, True)
            return
        label = LABEL.match(line)
        if label and not ITEM.match(line) and len(label.group(1).split()) <= 5 and section_kind(label.group(1)):
            self.start_section(section_kind(label.group(1)), label.group(1), False)
            if label.group(2).strip():
                self.paragraph = self.entry("paragraph", where, label.group(2).strip(), single_line=False)
            return
        if not line.strip():
            self.flush()
            return
        if SCENARIO.match(line):
            self.flush()
            self.scenario = {"line": where, "steps": []}
            return
        start = GHERKIN_START.match(line)
        follow = GHERKIN_NEXT.match(line)
        if self.section != "reproduction" and (start or (follow and self.scenario is not None)):
            if self.item is not None or self.paragraph is not None:
                pending, self.scenario = self.scenario, None
                self.flush()
                self.scenario = pending
            if self.scenario is None or (start and self.scenario["steps"]):
                if self.scenario is not None:
                    self.flush()
                self.scenario = {"line": where, "steps": []}
            match = start or follow
            self.scenario["steps"].append(f"{match.group(1).capitalize()} {match.group(2).strip()}")
            return
        if self.scenario is not None:
            self.flush()
        item_match = ITEM.match(line)
        if item_match:
            self.flush()
            self.item = self.entry("item", where, item_match.group(3).strip(),
                                   checkbox=item_match.group(2) is not None,
                                   done=(item_match.group(2) or "").lower() == "x")
            return
        if self.item is not None and raw.startswith((" ", "\t")):
            self.item["text"] += " " + line.strip()
            return
        if self.item is not None:
            self.flush()
        if self.paragraph is None:
            self.paragraph = self.entry("paragraph", where, line.strip(), single_line=True)
        else:
            self.paragraph["text"] += " " + line.strip()
            self.paragraph["single_line"] = False

    def close(self) -> None:
        self.flush()
        if self.fence is not None:
            self.state["code_blocks"].append(self.fence)
            self.fence = None


def parse_chunk(field: str | None, text: str, default_section: str | None, state: dict) -> None:
    parser = ChunkParser(state, field, default_section)
    for number, raw in enumerate(text.splitlines(), 1):
        parser.feed(number, raw)
    parser.close()


# ---------------------------------------------------------------------------
# criteria, files and commands
# ---------------------------------------------------------------------------

def normalized(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def judge(text: str) -> dict:
    cleaned = URL.sub(" ", text)
    signals = []
    if NUMBER.search(cleaned) or NUMBER_WORDS.search(cleaned):
        signals.append("number")
    if QUOTED.search(cleaned):
        signals.append("literal")
    if FILE_TOKEN.search(cleaned) or BARE_FILES.search(cleaned):
        signals.append("file")
    if any(span.strip().lower().startswith(COMMAND_WORDS) for span in CODE_SPAN.findall(cleaned)):
        signals.append("command")
    if OBSERVABLE.search(cleaned):
        signals.append("observable_result")
    vague = sorted({match.group(0).lower() for match in VAGUE.finditer(cleaned)})
    concrete = [signal for signal in signals if signal != "observable_result"]
    checkable = bool(concrete) or ("observable_result" in signals and not vague)
    return {"checkable": checkable, "signals": signals, "vague_terms": vague}


def build_criteria(state: dict) -> tuple[list[dict], list[dict], list[str], list[str]]:
    explicit, expected, actual, reproduction = [], [], [], []
    listed = {entry["section_id"] for entry in state["items"] if entry["kind"] in ("item", "scenario")}
    for entry in state["items"]:
        section = entry["section"]
        if entry["text"].strip().strip("_*`").strip().lower() in EMPTY_VALUES:
            continue  # a form field nobody filled in, such as _No response_
        if section in ("acceptance", "expected") and entry["kind"] == "paragraph" \
                and entry["section_id"] in listed:
            continue  # a section that lists its points keeps its paragraphs as commentary
        if section == "reproduction" and entry["kind"] in ("item", "paragraph"):
            reproduction.append(entry)
        elif entry["kind"] == "scenario":
            explicit.append(dict(entry, source="scenario"))
        elif section == "acceptance":
            explicit.append(dict(entry, source="acceptance_section"))
        elif entry.get("checkbox"):
            explicit.append(dict(entry, source="checkbox"))
        elif section == "expected":
            expected.append(dict(entry, source="expected_behavior"))
        elif section == "actual":
            actual.append(entry["text"])
    candidates = explicit + expected
    if not candidates:
        for entry in state["items"]:
            if entry["section"] in (None, "other") and entry["kind"] in ("item", "paragraph"):
                for sentence in re.split(r"(?<=[.!?])\s+", entry["text"]):
                    if MODAL.search(sentence):
                        candidates.append(dict(entry, text=sentence.strip(), source="modal_statement"))
    criteria, seen = [], set()
    for entry in sorted(candidates, key=lambda value: value["order"]):
        key = normalized(entry["text"])
        if not key or key in seen:
            continue
        seen.add(key)
        record = {"id": f"AC{len(criteria) + 1}", "text": entry["text"], "source": entry["source"],
                  "line": entry["line"]}
        if entry["field"] is not None:
            record["field"] = entry["field"]
        if entry.get("checkbox"):
            record["already_checked"] = bool(entry.get("done"))
        record.update(judge(entry["text"]))
        criteria.append(record)
    steps = [{"id": f"R{index}", "text": entry["text"], "line": entry["line"]}
             for index, entry in enumerate(sorted(reproduction, key=lambda value: value["order"]), 1)]
    return criteria, steps, [entry["text"] for entry in expected], actual


def commands_from(state: dict) -> list[str]:
    found = []
    for block in state["code_blocks"]:
        if block["language"] not in ("", "bash", "sh", "shell", "console", "zsh", "text"):
            continue
        for line in block["lines"]:
            command = re.sub(r"^\s*(?:\$|>|#)\s+", "", line).strip()
            if command and command.lower().startswith(COMMAND_WORDS):
                found.append(command)
    for _where, _field, line in state["plain_lines"]:
        for span in CODE_SPAN.findall(line):
            if span.strip().lower().startswith(COMMAND_WORDS):
                found.append(span.strip())
    unique = []
    for command in found:
        if command not in unique:
            unique.append(command)
    return unique[:20]


def safe_relative(path: str) -> str | None:
    candidate = path[2:] if path.startswith("./") else path
    parts = candidate.split("/")
    if not candidate or candidate.startswith("/") or any(part in ("", ".", "..") for part in parts):
        return None
    return candidate


def exists_under(root: Path, relative: str) -> bool | None:
    real_root = root.resolve()
    try:
        real = (real_root / relative).resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    if real_root not in real.parents:
        return None
    return real.is_file() or real.is_dir()


def basename_index(root: Path) -> tuple[dict[str, list[str]], bool]:
    index, entries = {}, 0
    for current, folders, names in os.walk(root, followlinks=False):
        folders[:] = sorted(folder for folder in folders if folder not in SKIP_FOLDERS)
        for name in sorted(names):
            entries += 1
            if entries > MAX_WALK_ENTRIES:
                return index, False
            relative = (Path(current) / name).relative_to(root).as_posix()
            index.setdefault(name.lower(), []).append(relative)
    return index, True


def named_files(state: dict, root: Path | None, search: bool) -> tuple[list[dict], list[str]]:
    found, order = {}, []

    def add(token: str, where, field, line_number=None) -> None:
        if token in found:
            return
        record = {"path": token, "mentioned_at_line": where}
        if field is not None:
            record["field"] = field
        if line_number:
            record["line_in_file"] = int(line_number)
        found[token] = record
        order.append(token)

    for where, field, line in state["plain_lines"]:
        cleaned = URL.sub(" ", line)
        spans = CODE_SPAN.findall(cleaned)
        for match in FILE_TOKEN.finditer(cleaned):
            token = match.group(1)
            if token.lower().endswith(".js") and "/" not in token and token[:1].isupper() \
                    and not any(token in span for span in spans):
                continue  # product names such as Node.js are not files
            add(token, where, field, match.group(2))
        for match in BARE_FILES.finditer(cleaned):
            add(match.group(1), where, field)
    for block in state["code_blocks"]:
        for line in block["lines"]:
            for match in FILE_TOKEN.finditer(URL.sub(" ", line)):
                if "/" in match.group(1):
                    add(match.group(1), None, None, match.group(2))
    notes, index = [], None
    results = []
    for token in order[:MAX_FILES]:
        record = found[token]
        relative = safe_relative(token)
        if root is None:
            record["exists"] = None
        elif relative is None:
            record["exists"] = None
            record["note"] = "not checked: the path is absolute or holds '..'"
        else:
            record["exists"] = exists_under(root, relative)
            if record["exists"] is False and search:
                if index is None:
                    index, complete = basename_index(root.resolve())
                    if not complete:
                        notes.append(f"the name search stopped after {MAX_WALK_ENTRIES} entries; matches may be missing")
                matches = index.get(relative.rsplit("/", 1)[-1].lower(), [])
                if matches:
                    record["matches"] = matches[:MAX_MATCHES]
        results.append(record)
    if len(order) > MAX_FILES:
        notes.append(f"{len(order) - MAX_FILES} more file names were mentioned and are not listed")
    return results, notes


def checklist_markdown(title, criteria, steps, files) -> str:
    lines = [f"Ticket: {title}" if title else "Ticket: (no title found)", "", "Acceptance criteria:"]
    for record in criteria:
        mark = "" if record["checkable"] else " (not checkable as written)"
        lines.append(f"{record['id'][2:]}. [ ] {record['text']}{mark}")
    if not criteria:
        lines.append("(none found)")
    if steps:
        lines += ["", "Reproduction steps:"] + [f"{index}. {step['text']}" for index, step in enumerate(steps, 1)]
    if files:
        lines += ["", "Named files:"]
        for record in files:
            state = {True: "exists", False: "not found", None: "not checked"}[record["exists"]]
            extra = f"; same name at {', '.join(record['matches'])}" if record.get("matches") else ""
            lines.append(f"- {record['path']} ({state}{extra})")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(description="Extract acceptance criteria and reproduction steps from one ticket.")
    parser.add_argument("ticket", nargs="?", default="-", help="ticket file, or - for standard input")
    parser.add_argument("--format", choices=("auto", "markdown", "text", "json"), default="auto")
    parser.add_argument("--root", default=".", help="workspace folder: the ticket must be inside it, and named "
                                                     "files are checked against it")
    parser.add_argument("--no-file-check", action="store_true", help="do not look up named files under --root")
    parser.add_argument("--no-search", action="store_true", help="do not search for files with the same name")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    options = parser.parse_args(argv)
    try:
        if not 0 < options.max_bytes <= HARD_MAX_BYTES:
            raise Refused(f"--max-bytes must be between 1 and {HARD_MAX_BYTES}")
        root = Path(options.root)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        data, shown = read_input(options.ticket, root, options.max_bytes)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise Refused(f"the ticket is not UTF-8 text (first bad byte at offset {error.start})") from error
        text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        if not text.strip():
            raise Refused("the ticket is empty")
        fmt = options.format
        if fmt == "auto":
            fmt = "json" if text.lstrip()[:1] in ("{", "[") else "markdown"
        state = {"items": [], "code_blocks": [], "plain_lines": [], "title": None, "sections_seen": set(),
                 "sequence": 0, "section_counter": 0, "first_heading_level": None}
        if fmt == "json":
            try:
                document = strict_json(text)
            except ValueError as error:
                raise Refused(f"the ticket is not valid JSON: {error}") from error
            title, chunks = json_chunks(document)
            state["title"] = title
            if title:
                state["plain_lines"].append((None, "title", title))
            for field, chunk, default in chunks:
                parse_chunk(field, TEMPLATE_COMMENT.sub("", chunk), default, state)
        else:
            text = TEMPLATE_COMMENT.sub("", text)
            parse_chunk(None, text, None, state)
            if state["title"] is None:
                first = next((line.strip() for line in text.splitlines() if line.strip()), "")
                labelled = TITLE_LABEL.match(first)
                if labelled:
                    state["title"] = labelled.group(1).strip()[:300]
                elif first and not first.startswith("#") and not ITEM.match(first) and not LABEL.match(first) \
                        and len(first) <= 160:
                    state["title"] = first
        if state["title"]:
            state["title"] = EMPHASIS.sub(r"\2", state["title"])
        criteria, steps, expected, actual = build_criteria(state)
        files, notes = named_files(state, None if options.no_file_check else root, not options.no_search)
        commands = commands_from(state)
    except Refused as error:
        emit({"record_type": RECORD_TYPE, "status": "refused", "reason": str(error)})
        return 2
    flags = []
    if not any(record["source"] in ("acceptance_section", "checkbox", "scenario") for record in criteria):
        flags.append("no_acceptance_section")
    checkable = [record for record in criteria if record["checkable"]]
    if not checkable:
        flags.append("no_checkable_outcome")
    elif len(checkable) < len(criteria):
        flags.append("some_criteria_not_checkable")
    whole = "\n".join(line for _where, _field, line in state["plain_lines"])
    if not steps and (actual or BUG_WORDS.search(whole)):
        flags.append("bug_without_reproduction_steps")
    if any(record.get("exists") is False for record in files):
        flags.append("named_file_not_found")
    document = {
        "record_type": RECORD_TYPE,
        "status": "ok" if checkable else "no_checkable_outcome",
        "source": {"path": shown, "format": fmt, "sha256": hashlib.sha256(data).hexdigest()},
        "title": state["title"],
        "acceptance_criteria": criteria,
        "reproduction_steps": steps,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "named_files": files,
        "commands": commands,
        "flags": flags,
        "notes": notes,
        "checklist_markdown": checklist_markdown(state["title"], criteria, steps, files),
    }
    emit(document)
    return 0 if checkable else 1


if __name__ == "__main__":
    raise SystemExit(main())
