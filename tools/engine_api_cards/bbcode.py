"""Godot's class reference BBCode, written as Markdown with the meaning the engine's own generator gives each tag.

The engine writes its online class reference from the same XML with ``doc/tools/make_rst.py`` (reStructuredText).
This converter follows that generator tag by tag and writes Markdown instead:

```text
description text (one XML element, lines indented with tabs)
├── a line that opens [codeblock], [codeblock lang=text], [gdscript] or [csharp] starts a code block that runs
│   to its closing tag; its lines are copied verbatim, less the opening line's indentation ([codeblocks] only
│   groups a GDScript and a C# block): a fenced block, gdscript by default as the engine's documentation sets
├── every other line is a paragraph (a line break in the XML is a paragraph break, as make_rst writes it)
└── inside a paragraph
    ├── [ClassName] (a class of the engine) -> `ClassName`
    ├── [method X], [member X], [signal X], [constant X], [enum X], [annotation X], [theme_item X],
    │   [constructor X], [operator X], [param X] -> `X` (a method with "()"; Class. dropped for the class's own)
    ├── [code]...[/code] and [kbd]...[/kbd] -> a code span of the literal text inside
    ├── [b] -> **, [i] -> *, [u], [center] -> nothing, [br] -> a paragraph break, [lb] [rb] -> [ ]
    ├── [url=address]title[/url] -> [title](address), [url]address[/url] -> <address>; $DOCS_URL -> the
    │   documentation of the same engine version
    └── anything else in brackets is kept as written, escaped; plain text is escaped where Markdown would
        otherwise read it as markup
```

Nothing here reads a file or the network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: The tags that open a code block when they start a line, and the language of each block.
CODEBLOCK, GDSCRIPT, CSHARP, CODEBLOCKS = "codeblock", "gdscript", "csharp", "codeblocks"
BLOCK_TAGS = (CODEBLOCK, GDSCRIPT, CSHARP)
DEFAULT_LANGUAGE, TEXT_LANGUAGE, TEXT_ARGUMENT = "gdscript", "text", "lang=text"
#: Cross-reference tags (make_rst.py RESERVED_CROSSLINK_TAGS) and the ones written with call parentheses.
METHOD, CONSTRUCTOR, OPERATOR, MEMBER, SIGNAL, CONSTANT, ENUM, ANNOTATION, THEME_ITEM, PARAM = CROSS_REFERENCES = (
    "method", "constructor", "operator", "member", "signal", "constant", "enum", "annotation", "theme_item", "param")
#: Formatting tags (make_rst.py RESERVED_FORMATTING_TAGS) and what each becomes.
BOLD, ITALIC, UNDERLINE, LEFT_BRACKET, RIGHT_BRACKET, CODE, KEYBOARD, CENTER, URL, BREAK = (
    "b", "i", "u", "lb", "rb", "code", "kbd", "center", "url", "br")
EMPHASIS = {BOLD: "**", ITALIC: "*", UNDERLINE: "", CENTER: ""}
LITERAL_SPANS = (CODE, KEYBOARD)
#: The lines that only group a GDScript and a C# block ([codeblocks] and its closing tag).
GROUP_LINES = frozenset({f"[{CODEBLOCKS}]", f"[/{CODEBLOCKS}]"})
#: The documentation address placeholder of the class reference's links.
DOCS_PLACEHOLDER = "$DOCS_URL"
PARAGRAPH_BREAK = "\n\n"
#: Characters plain text escapes, and the line starts Markdown would read as a block.
_ESCAPED = {"\\": "\\\\", "`": "\\`", "*": "\\*", "[": "\\[", "]": "\\]"}
_BLOCK_START = re.compile(r"^(#|>|[-+*](?=\s)|=|~|\d+(?=[.)](?:\s|$)))")
_HTML_START = re.compile(r"<(?=[A-Za-z/!?])")


@dataclass(frozen=True)
class Context:
    """What a description is read against: the engine's classes, the class it belongs to and the documentation
    address that replaces $DOCS_URL."""

    classes: frozenset
    current_class: str
    docs_address: str = ""
    code: object = None  # the card module's code(), so code spans are written one way everywhere
    unresolved: list = field(default_factory=list)


def _code(context: Context, text: str) -> str:
    if context.code is not None:
        return context.code(text)
    fence = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if "`" in text else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def escape_text(text: str, line_start: bool = False) -> str:
    """Plain text with every character Markdown would read as markup escaped."""
    out = []
    for index, character in enumerate(text):
        if character in _ESCAPED:
            out.append(_ESCAPED[character])
        elif character == "_":
            before = text[index - 1] if index else " "
            after = text[index + 1] if index + 1 < len(text) else " "
            out.append("_" if before.isalnum() and after.isalnum() else "\\_")
        else:
            out.append(character)
    escaped = _HTML_START.sub("\\\\<", "".join(out))
    if line_start:
        stripped = escaped.lstrip(" ")
        match = _BLOCK_START.match(stripped)
        if match:
            prefix = escaped[:len(escaped) - len(stripped)]
            if match.group(1)[0].isdigit():
                end = len(match.group(1))
                escaped = prefix + stripped[:end] + "\\" + stripped[end:]
            else:
                escaped = prefix + "\\" + stripped
    return escaped


def _tag(text: str) -> tuple:
    """(name, arguments, closing) of a tag's text, split as make_rst.py's get_tag_and_args splits it."""
    space, assign = text.find(" "), text.find("=")
    delimiter = space if space >= 0 else -1
    if assign >= 0 and (delimiter < 0 or assign < delimiter):
        delimiter = assign
    name, arguments = (text[:delimiter], text[delimiter + 1:].strip()) if delimiter >= 0 else (text, "")
    closing = name.startswith("/")
    return (name[1:] if closing else name), arguments, closing


def _reference(context: Context, name: str, target: str) -> str:
    """A cross-reference's text, as make_rst.py writes it: the item, its class first when another class's."""
    if name == PARAM:
        return _code(context, target)
    if name == ENUM:
        return _code(context, target.rsplit(".", 1)[-1])
    owner, _, item = target.rpartition(".")
    shown = item if not owner or owner == context.current_class else target
    if owner and owner not in context.classes:
        context.unresolved.append(target)
    return _code(context, shown + ("()" if name == METHOD else ""))


def _address(context: Context, address: str) -> str:
    return address.replace(DOCS_PLACEHOLDER, context.docs_address) if context.docs_address else address


def inline(text: str, context: Context) -> str:
    """One paragraph of BBCode as Markdown."""
    out, position, line_start = [], 0, True
    while position < len(text):
        opening = text.find("[", position)
        if opening < 0:
            out.append(escape_text(text[position:], line_start))
            break
        closing = text.find("]", opening + 1)
        if closing < 0:
            out.append(escape_text(text[position:], line_start))
            break
        if opening > position:
            out.append(escape_text(text[position:opening], line_start))
            line_start = False
        tag_text = text[opening + 1:closing]
        name, arguments, is_closing = _tag(tag_text)
        after = closing + 1
        if tag_text in context.classes:
            out.append(_code(context, tag_text))
        elif not is_closing and name in LITERAL_SPANS:
            end = text.find(f"[/{name}]", after)
            end = len(text) if end < 0 else end
            out.append(_code(context, text[after:end]))
            after = min(len(text), end + len(name) + 3)
        elif not is_closing and name == URL:
            end = text.find("[/url]", after)
            end = len(text) if end < 0 else end
            title = text[after:end]
            if arguments:
                out.append(f"[{inline(title, context) if title else escape_text(arguments)}]"
                           f"({_address(context, arguments)})")
            else:
                out.append(f"<{_address(context, title)}>")
            after = min(len(text), end + len("[/url]"))
        elif name in EMPHASIS:
            out.append(EMPHASIS[name])
        elif name == BREAK and not is_closing:
            out.append(PARAGRAPH_BREAK)
            while after < len(text) and text[after] == " ":
                after += 1
            position, line_start = after, True
            continue
        elif name == LEFT_BRACKET and not is_closing:
            out.append(_ESCAPED["["])
        elif name == RIGHT_BRACKET and not is_closing:
            out.append(_ESCAPED["]"])
        elif name in CROSS_REFERENCES and not is_closing and arguments:
            out.append(_reference(context, name, arguments))
        else:
            context.unresolved.append(tag_text)
            out.append(escape_text(f"[{tag_text}]", line_start))
        position, line_start = after, False
    return "".join(out)


def _block_tag(stripped: str) -> "tuple | None":
    """(tag name, arguments) when a line opens a code block, else None."""
    if not stripped.startswith("["):
        return None
    end = stripped.find("]")
    if end < 0:
        return None
    name, arguments, closing = _tag(stripped[1:end])
    return (name, arguments) if name in BLOCK_TAGS and not closing else None


def _fence(lines: list) -> str:
    longest = max((len(run) for line in lines for run in re.findall(r"`{3,}", line)), default=2)
    return "`" * (longest + 1)


def to_markdown(text: "str | None", context: Context) -> str:
    """A whole description element as Markdown paragraphs and fenced code blocks; empty text gives ""."""
    if not text or not text.strip():
        return ""
    blocks, lines = [], text.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip("\t")
        indent = len(line) - len(stripped)
        opened = _block_tag(stripped.strip())
        if opened is None:
            if stripped.strip() and stripped.strip() not in GROUP_LINES:
                blocks.append(inline(stripped.strip(), context))
            index += 1
            continue
        name, arguments = opened
        language = TEXT_LANGUAGE if TEXT_ARGUMENT in arguments.split(" ") else (
            name if name != CODEBLOCK else DEFAULT_LANGUAGE)
        body, index = [], index + 1
        while index < len(lines) and not lines[index].lstrip("\t").startswith(f"[/{name}"):
            raw = lines[index]
            tabs = len(raw) - len(raw.lstrip("\t"))
            body.append("\t" * max(0, tabs - indent) + raw.lstrip("\t") if raw.strip() else "")
            index += 1
        index += 1
        while body and not body[-1]:
            body.pop()
        fence = _fence(body)
        blocks.append(f"{fence}{language}\n" + "\n".join(body) + f"\n{fence}")
    return PARAGRAPH_BREAK.join(block for block in blocks if block)


__all__ = ["Context", "escape_text", "inline", "to_markdown", "CROSS_REFERENCES", "DOCS_PLACEHOLDER"]
