"""Engine API contract card: the Markdown documents and api.json of one card describe one surface.

```text
One card (one class of one engine version, or one function, method or property of one library version)
├── api.json       engine_api_surface/v1: the class, its inheritance, every item of every section as the engine
│                  itself reports it, and the renames the engine's own upgrade map lists for the class
└── README.md      the card a harness reads first; a large class continues in members-2.md, members-3.md, ...
    ├── "# <Class> (<Engine> <version>)", then the inheritance lines
    ├── "## Renamed from <Engine> <earlier version>": one "- " line per rename
    ├── "## <Section>" per section with items ("## <Section> (continued)" where a later document goes on)
    ├── "### `<item>`": one heading per item, written by item_line(), then its description
    └── "#### `<value>`": one heading per enumeration value, under its enumeration
```

Every checked line is written from api.json by the functions below, so a card agrees with its api.json exactly
when card_lines() and document_lines() return the same list. The functions read no file and use the standard
library only: the caller passes the parsed api.json and the documents' text in order.
"""
from __future__ import annotations

import re

SURFACE_RECORD = "engine_api_surface/v1"
#: The sections of a surface, in document order, and the heading each has in the documents.
#: A surface holds the sections it has: an engine class's nine, and a library's function card its "functions".
(CONSTRUCTORS, METHODS, OPERATORS, MEMBERS, SIGNALS, ENUMS, CONSTANTS, ANNOTATIONS, THEME_ITEMS, FUNCTIONS) = \
    SECTIONS = ("constructors", "methods", "operators", "members", "signals", "enums", "constants", "annotations",
                "theme_items", "functions")
HEADINGS = {CONSTRUCTORS: "Constructors", METHODS: "Methods", OPERATORS: "Operators", MEMBERS: "Properties",
            SIGNALS: "Signals", ENUMS: "Enumerations", CONSTANTS: "Constants", ANNOTATIONS: "Annotations",
            THEME_ITEMS: "Theme properties", FUNCTIONS: "Functions"}
#: The line kinds a card checks, each a level of the documents' structure.
TITLE, INHERITS, INHERITED_BY, RENAMES, RENAME, SECTION, ITEM, VALUE = LINE_KINDS = (
    "title", "inherits", "inherited_by", "renames", "rename", "section", "item", "value")
TITLE_PREFIX, SECTION_PREFIX, ITEM_PREFIX, VALUE_PREFIX, RENAME_PREFIX = "# ", "## ", "### ", "#### ", "- "
INHERITS_PREFIX, INHERITED_BY_PREFIX = "**Inherits:** ", "**Inherited by:** "
RENAMES_PREFIX, CONTINUED = "Renamed from ", " (continued)"
#: The kinds of rename an upgrade map lists; a renamed method is written with its call parentheses.
RENAME_KINDS = (CLASS_RENAME, METHOD_RENAME, PROPERTY_RENAME, SIGNAL_RENAME, CONSTANT_RENAME, ENUM_RENAME) = (
    "class", "method", "property", "signal", "constant", "enum")
#: The documents a card is written in: README.md, then members-2.md, members-3.md, ... for a large class.
README, MEMBERS_DOCUMENT = "README.md", "members-{}.md"
_MEMBERS_DOCUMENT = re.compile(r"members-([2-9]|[1-9][0-9]+)\.md")
#: The syntax a surface is written in, named by api.json's "syntax": Godot's class reference conventions
#: ("float get_floor_angle(up_direction: Vector3 = Vector3(0, 1, 0)) const"), a JavaScript library's JSDoc
#: conventions in TypeScript notation ("lerp(v: Vector3, alpha: number): Vector3"), or a Python signature as the
#: inspect module writes one ("linspace(start, stop, num=50, *, device=None) -> ndarray").
GODOT_SYNTAX, JAVASCRIPT_SYNTAX, PYTHON_SYNTAX = SYNTAXES = ("godot", "javascript", "python")
#: How a Python parameter is passed (inspect.Parameter.kind, by name).
PARAMETER_KINDS = (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD, VAR_POSITIONAL, KEYWORD_ONLY, VAR_KEYWORD) = (
    "positional_only", "positional_or_keyword", "var_positional", "keyword_only", "var_keyword")
VARARG, VOID, ELLIPSIS, ANY = "vararg", "void", "...", "any"
BITFIELD_WRAPPER, ARRAY_WRAPPER, ARRAY_SUFFIX = "BitField[{}]", "Array[{}]", "[]"
#: What a property heading adds after its declaration, and a theme item's data type.
MEMBER_NOTES = (("setter", "setter"), ("getter", "getter"), ("overrides", "overrides"))
_FENCE = re.compile(r"(`{3,}|~{3,})")


def code(text) -> str:
    """Text as a Markdown code span, fenced with more backticks than any run it holds."""
    text = str(text)
    runs = [len(run) for run in re.findall(r"`+", text)]
    fence = "`" * (max(runs, default=0) + 1)
    pad = " " if runs else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def type_text(declared) -> str:
    """A parameter's, a return value's or a property's type as the engine's class reference writes it."""
    enum = declared.get("enum")
    if enum:
        return BITFIELD_WRAPPER.format(enum) if declared.get("is_bitfield") else str(enum)
    name = str(declared.get("type", ""))
    return ARRAY_WRAPPER.format(name[:-len(ARRAY_SUFFIX)]) if name.endswith(ARRAY_SUFFIX) else name


def parameters_text(parameters, qualifiers=()) -> str:
    """A parameter list: name: Type = default, with ... closing a list that takes any further arguments."""
    parts = []
    for parameter in parameters:
        part = f"{parameter['name']}: {type_text(parameter)}"
        if "default" in parameter:
            part += f" = {parameter['default']}"
        parts.append(part)
    if VARARG in qualifiers:
        parts.append(ELLIPSIS)
    return ", ".join(parts)


def signature(section, item, syntax=GODOT_SYNTAX) -> str:
    """The declaration of one item, in the syntax its surface is written in."""
    return SIGNATURES[syntax](section, item)


def godot_signature(section, item) -> str:
    """The declaration of one item, in Godot's class reference syntax."""
    qualifiers = tuple(item.get("qualifiers", ()))
    tail = "".join(f" {word}" for word in qualifiers)
    if section in (CONSTRUCTORS, METHODS, OPERATORS, FUNCTIONS):
        returned = type_text(item["returns"]) if item.get("returns") else VOID
        return f"{returned} {item['name']}({parameters_text(item.get('params', ()), qualifiers)}){tail}"
    if section == ANNOTATIONS:
        return f"{item['name']}({parameters_text(item.get('params', ()), qualifiers)}){tail}"
    if section == SIGNALS:
        return f"{item['name']}({parameters_text(item.get('params', ()))})"
    if section in (MEMBERS, THEME_ITEMS):
        text = f"{type_text(item)} {item['name']}"
        return text + (f" = {item['default']}" if "default" in item else "")
    if section == ENUMS:
        return ("flags " if item.get("is_bitfield") else "enum ") + str(item["name"])
    return f"{item['name']} = {item['value']}"


def javascript_parameters(parameters) -> str:
    """A JavaScript parameter list in TypeScript notation: name: Type, name?: Type, or name: Type = default."""
    parts = []
    for parameter in parameters:
        optional = "?" if parameter.get("optional") and "default" not in parameter else ""
        part = f"{parameter['name']}{optional}: {parameter.get('type') or ANY}"
        if "default" in parameter:
            part += f" = {parameter['default']}"
        parts.append(part)
    return ", ".join(parts)


def javascript_signature(section, item) -> str:
    """The declaration of one item of a JavaScript library, its qualifiers (static, async, readonly) first."""
    prefix = "".join(f"{word} " for word in item.get("qualifiers", ()))
    if section == CONSTRUCTORS:
        return f"new {item['name']}({javascript_parameters(item.get('params', ()))})"
    if section in (METHODS, OPERATORS, ANNOTATIONS, FUNCTIONS):
        returned = item["returns"].get("type") or ANY if item.get("returns") else VOID
        return f"{prefix}{item['name']}({javascript_parameters(item.get('params', ()))}): {returned}"
    if section == SIGNALS:
        return f"{item['name']}({javascript_parameters(item.get('params', ()))})"
    if section in (MEMBERS, THEME_ITEMS):
        text = f"{prefix}{item['name']}: {item.get('type') or ANY}"
        return text + (f" = {item['default']}" if "default" in item else "")
    if section == ENUMS:
        return "enum " + str(item["name"])
    return f"{prefix}{item['name']} = {item['value']}"


def python_parameters(parameters) -> str:
    """A Python parameter list as inspect writes one: "/" after the positional-only parameters, "*" before the first
    keyword-only one when no *args comes first, name: type = default (name=default without a type). A signature the
    interpreter cannot report (None) is "..."."""
    if parameters is None:
        return ELLIPSIS
    parts, positional_only, starred = [], False, False
    for parameter in parameters:
        kind = parameter.get("kind", POSITIONAL_OR_KEYWORD)
        if positional_only and kind != POSITIONAL_ONLY:
            parts.append("/")
        if kind == KEYWORD_ONLY and not starred:
            parts.append("*")
            starred = True
        text = str(parameter["name"])
        if kind == VAR_POSITIONAL:
            text, starred = "*" + text, True
        elif kind == VAR_KEYWORD:
            text = "**" + text
        if parameter.get("type"):
            text += f": {parameter['type']}" + (f" = {parameter['default']}" if "default" in parameter else "")
        elif "default" in parameter:
            text += f"={parameter['default']}"
        parts.append(text)
        positional_only = kind == POSITIONAL_ONLY
    if positional_only:
        parts.append("/")
    return ", ".join(parts)


def python_signature(section, item) -> str:
    """The declaration of one item of a Python library, its qualifiers (async, classmethod, staticmethod,
    readonly) first and its return annotation after "->"."""
    prefix = "".join(f"{word} " for word in item.get("qualifiers", ()))
    if section == CONSTRUCTORS:
        return f"{item['name']}({python_parameters(item.get('params', ()))})"
    if section in (METHODS, OPERATORS, ANNOTATIONS, FUNCTIONS, SIGNALS):
        returned = (item.get("returns") or {}).get("type")
        return (f"{prefix}{item['name']}({python_parameters(item.get('params', ()))})" +
                (f" -> {returned}" if returned else ""))
    if section in (MEMBERS, THEME_ITEMS):
        text = f"{prefix}{item['name']}" + (f": {item['type']}" if item.get("type") else "")
        return text + (f" = {item['default']}" if "default" in item else "")
    if section == ENUMS:
        return "enum " + str(item["name"])
    return f"{prefix}{item['name']} = {item['value']}"


#: How each syntax writes a declaration.
SIGNATURES = {GODOT_SYNTAX: godot_signature, JAVASCRIPT_SYNTAX: javascript_signature, PYTHON_SYNTAX: python_signature}


def item_line(section, item, syntax=GODOT_SYNTAX) -> str:
    """The heading line of one item: its declaration as code, then what the declaration does not show."""
    line = code(signature(section, item, syntax))
    if section == MEMBERS:
        for label, key in MEMBER_NOTES:
            if item.get(key):
                line += f" {label} {code(item[key])}"
    elif section == THEME_ITEMS:
        line += f" ({item['data_type']})"
    elif item.get("returns_errors"):
        line += " returns errors " + ", ".join(code(number) for number in item["returns_errors"])
    return line


def rename_line(rename) -> str:
    """One rename the engine's upgrade map lists: what the earlier version called it and what it is called now."""
    suffix = "()" if rename["kind"] == METHOD_RENAME else ""
    return f"{rename['kind']} {code(rename['from'] + suffix)} → {code(rename['to'] + suffix)}"


def title_line(api) -> str:
    """The card's title: the class, the engine and the version whose surface it lists."""
    engine = api["engine"]
    return f"{api['class']} ({engine['title']} {engine['api_version']})"


def renames_heading(api) -> str:
    """The heading of the renames section: the engine and the earlier version the map converts from."""
    renames = api.get("renames") or {}
    return f"{RENAMES_PREFIX}{api['engine']['title']} {renames.get('from_version', '')}".rstrip()


def card_lines(api) -> list:
    """Every line the documents of a card must hold, in order, as (kind, section, text)."""
    lines = [(TITLE, "", title_line(api))]
    if api.get("inherits"):
        lines.append((INHERITS, "", " < ".join(code(name) for name in api["inherits"])))
    if api.get("inherited_by"):
        lines.append((INHERITED_BY, "", ", ".join(code(name) for name in api["inherited_by"])))
    entries = (api.get("renames") or {}).get("entries") or []
    if entries:
        lines.append((RENAMES, "", renames_heading(api)))
        lines += [(RENAME, RENAMES, rename_line(entry)) for entry in entries]
    for section in SECTIONS:
        items = api["sections"].get(section) or []
        if not items:
            continue
        lines.append((SECTION, section, HEADINGS[section]))
        for item in items:
            lines.append((ITEM, section, item_line(section, item, api["syntax"])))
            if section == ENUMS:
                lines += [(VALUE, section, item_line(CONSTANTS, value, api["syntax"]))
                          for value in item.get("values", ())]
    return lines


def _closes(line: str, fence: str) -> bool:
    """Whether a line closes a fenced block opened with ``fence``: the same character, at least as many times."""
    stripped = line.strip()
    return len(stripped) >= len(fence) and set(stripped) == {fence[0]}


def document_lines(texts) -> list:
    """The checked lines the documents hold, in order, as (kind, section, text); fenced code is skipped."""
    by_heading = {heading: section for section, heading in HEADINGS.items()}
    found, section, fence = [], "", ""
    for text in texts:
        for line in str(text).split("\n"):
            if fence:
                fence = "" if _closes(line, fence) else fence
                continue
            opening = _FENCE.match(line)
            if opening:
                fence = opening.group(1)
            elif line.startswith(VALUE_PREFIX):
                found.append((VALUE, section, line[len(VALUE_PREFIX):]))
            elif line.startswith(ITEM_PREFIX):
                found.append((ITEM, section, line[len(ITEM_PREFIX):]))
            elif line.startswith(SECTION_PREFIX):
                heading = line[len(SECTION_PREFIX):]
                continued = heading[:-len(CONTINUED)] if heading.endswith(CONTINUED) else None
                if continued in by_heading:
                    section = by_heading[continued]
                elif heading in by_heading:
                    section = by_heading[heading]
                    found.append((SECTION, section, heading))
                elif heading.startswith(RENAMES_PREFIX):
                    section = RENAMES
                    found.append((RENAMES, "", heading))
                else:
                    section = ""
            elif line.startswith(TITLE_PREFIX):
                section = ""
                found.append((TITLE, "", line[len(TITLE_PREFIX):]))
            elif line.startswith(INHERITS_PREFIX):
                found.append((INHERITS, "", line[len(INHERITS_PREFIX):]))
            elif line.startswith(INHERITED_BY_PREFIX):
                found.append((INHERITED_BY, "", line[len(INHERITED_BY_PREFIX):]))
            elif section == RENAMES and line.startswith(RENAME_PREFIX):
                found.append((RENAME, RENAMES, line[len(RENAME_PREFIX):]))
    return found


def disagreements(api, texts) -> list:
    """Every difference between api.json and the documents: lines missing, lines the surface does not hold, and
    lines out of order. An empty list means the card agrees with its surface."""
    if api.get("record_type") != SURFACE_RECORD:
        return [f"api.json is not {SURFACE_RECORD}"]
    if api.get("syntax") not in SYNTAXES:
        return [f"api.json uses the syntax {api.get('syntax')!r}, which this module does not write"]
    expected, found = card_lines(api), document_lines(texts)
    problems, remaining = [], list(found)
    for line in expected:
        if line in remaining:
            remaining.remove(line)
        else:
            problems.append("missing: " + " | ".join(line))
    problems += ["not in api.json: " + " | ".join(line) for line in remaining]
    if not problems and expected != found:
        position = next(index for index, (left, right) in enumerate(zip(expected, found)) if left != right)
        problems.append("out of order at: " + " | ".join(found[position]))
    return problems


def documents(names) -> list:
    """The documents of a card in reading order: README.md, then members-2.md, members-3.md, ... by number."""
    numbered = sorted((int(match.group(1)), name) for name in map(str, names)
                      for match in [_MEMBERS_DOCUMENT.fullmatch(name)] if match)
    return [README] + [name for _number, name in numbered]
