"""Read ES class declarations and their JSDoc comments into a class's surface and documentation (three.js).

```text
one source file of the engine (src/math/Vector3.js at the pinned commit)
├── a JSDoc block (/** ... */) documents the code line right after it
├── class Name extends Parent {          the class: its description, @deprecated, @hideconstructor
│   ├── constructor( ... ) {             the constructor: @param {Type} [name=default] - text
│   │   ├── this.name = ...;             an instance property: @type, @default, @readonly
│   │   └── this.name = function ( ... ) an instance method (defined in the constructor)
│   ├── static { Name.prototype.flag = ...; Name.member = ...; }   prototype flags and static properties
│   ├── [static] [async] name( ... ) {   a method: @param, @return(s), @abstract, @deprecated
│   ├── get name() / set name( value )   an accessor property: @type, @readonly when there is no setter
│   └── [static] name = ...;             a class field
└── }   (a line holding only "}" closes the class)
```

Only documented, public members reach a surface: a member without a JSDoc block, one tagged @private or
@ignore, and a name that starts with an underscore or # are left out. The surface has the shape api_card.py writes
in its "javascript" syntax; the documentation keeps every description, parameter and return text for the card.
Nothing here runs JavaScript.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .godot_reference import (ANNOTATIONS, CONSTANTS, CONSTRUCTORS, ENUMS, MEMBERS, METHODS, OPERATORS, SECTIONS,
                              SIGNALS, THEME_ITEMS, ClassKind, ClassReference)

#: JSDoc tags the reader interprets.
(PARAM, RETURN, RETURNS, TYPE, DEFAULT, READONLY, STATIC, ABSTRACT, DEPRECATED, PRIVATE, IGNORE, HIDE_CONSTRUCTOR,
 ASYNC) = ("param", "return", "returns", "type", "default", "readonly", "static", "abstract", "deprecated", "private",
           "ignore", "hideconstructor", "async")
RETURN_TAGS = (RETURN, RETURNS)
SKIP_TAGS = (PRIVATE, IGNORE)
#: Qualifiers a JavaScript surface item may carry, in the order a declaration writes them.
QUALIFIER_ORDER = (STATIC, ASYNC, READONLY, ABSTRACT)
PRIVATE_PREFIXES = ("_", "#")
CONSTRUCTOR_NAME = "constructor"
GETTER, SETTER = "get", "set"
_CLASS = re.compile(r"^(?:export\s+)?class\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+([A-Za-z_$][\w$.]*))?\s*\{\s*$")
_METHOD = re.compile(r"^\t(static\s+)?(async\s+)?(?:(get|set)\s+)?(\*\s*)?([#A-Za-z_$][\w$]*)\s*\((.*)$")
_STATIC_BLOCK = re.compile(r"^\tstatic\s*\{\s*$")
_FIELD = re.compile(r"^\t(static\s+)?([#A-Za-z_$][\w$]*)\s*=")
_THIS_METHOD = re.compile(r"^\t\tthis\.([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\b")
_THIS_FIELD = re.compile(r"^\t\tthis\.([A-Za-z_$][\w$]*)\s*=")
_STATIC_ASSIGNMENT = re.compile(r"^\t\t([A-Za-z_$][\w$]*)\.(prototype\.)?([A-Za-z_$][\w$]*)\s*=")
_TAG = re.compile(r"^@([A-Za-z]+)\b\s?(.*)$")
OPEN_BRACE, CLOSE_BRACE = "{", "}"
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_LINK = re.compile(r"\{@link\s+([^}\s|]+)(?:\s*\|?\s*([^}]*))?\}")


@dataclass
class DocBlock:
    """One JSDoc comment: its description and its tags, in order."""

    description: str
    tags: list = field(default_factory=list)  # [(tag, text)]

    def has(self, tag: str) -> bool:
        return any(name == tag for name, _text in self.tags)

    def first(self, *names) -> "str | None":
        return next((text for name, text in self.tags if name in names), None)

    def all(self, tag: str) -> list:
        return [text for name, text in self.tags if name == tag]


def parse_block(comment: str) -> DocBlock:
    """A /** ... */ comment as its description and tags; a tag's text continues on the lines after it."""
    body = comment.strip()
    body = body[3:] if body.startswith("/**") else body
    body = body[:-2] if body.endswith("*/") else body
    lines = [re.sub(r"^\s*\*? ?", "", line, count=1) for line in body.split("\n")]
    description, tags = [], []
    for line in lines:
        match = _TAG.match(line.strip())
        if match:
            tags.append([match.group(1), match.group(2)])
        elif tags:
            tags[-1][1] += "\n" + line
        else:
            description.append(line)
    return DocBlock("\n".join(description).strip(), [(name, text.strip()) for name, text in tags])


def _braced(text: str) -> tuple:
    """(type, rest) of a tag text that starts with a {type}, braces balanced; ("", text) without one."""
    text = text.strip()
    if not text.startswith(OPEN_BRACE):
        return "", text
    depth = 0
    for position, character in enumerate(text):
        depth += 1 if character == OPEN_BRACE else -1 if character == CLOSE_BRACE else 0
        if depth == 0:
            # A type may be written across lines (a record type); it is one declaration, read as one line.
            return " ".join(text[1:position].split()), text[position + 1:].strip()
    return "", text


def parameter(text: str) -> "dict | None":
    """One @param: {"name", "type", "optional", "default"} and its description; None for a dotted (field) name."""
    kind, rest = _braced(text)
    match = re.match(r"^(\[[^\]]*\]|[A-Za-z_$][\w$.]*)\s*(?:-\s*)?(.*)$", rest, re.S)
    if not match:
        return None
    name, description = match.group(1), match.group(2).strip()
    row = {"type": kind or "any"}
    if name.startswith("["):
        inner = name[1:-1]
        name, _, default = inner.partition("=")
        row["optional"] = True
        if default.strip():
            row["default"] = default.strip()
    name = name.strip()
    if "." in name:
        return None
    return {"name": name, **row, "description": description}


def returned(block: DocBlock) -> tuple:
    """({"type"} or None, description) of a block's @return or @returns."""
    text = block.first(*RETURN_TAGS)
    if text is None:
        return None, ""
    kind, rest = _braced(text)
    return {"type": kind or "any"}, rest


@dataclass
class _Class:
    name: str
    parent: "str | None"
    block: "DocBlock | None"
    sections: dict = field(default_factory=lambda: {section: [] for section in SECTIONS})
    documents: dict = field(default_factory=lambda: {section: [] for section in SECTIONS})
    accessors: dict = field(default_factory=dict)


def _public(name: str, block: "DocBlock | None") -> bool:
    return block is not None and not name.startswith(PRIVATE_PREFIXES) and not any(block.has(tag)
                                                                                    for tag in SKIP_TAGS)


def _qualifiers(*flags) -> list:
    return [name for name in QUALIFIER_ORDER if name in flags]


def _documentation(block: DocBlock, parameters: list, returns_text: str) -> dict:
    """The documentation of one item: its description with its parameters' and return value's texts after it."""
    parts = [block.description] if block.description else []
    described = [row for row in parameters if row.get("description")]
    if described:
        parts.append("\n".join(f"- `{row['name']}`: {row['description']}" for row in described))
    if returns_text:
        parts.append(f"Returns: {returns_text}")
    notes = {}
    if block.has(DEPRECATED):
        notes[DEPRECATED] = block.first(DEPRECATED) or DEPRECATED
    return {"description": "\n\n".join(parts), **notes}


def _parameters(block: DocBlock) -> list:
    rows = [parameter(text) for text in block.all(PARAM)]
    return [row for row in rows if row is not None]


def _method(owner: _Class, name: str, block: DocBlock, *, static: bool, asynchronous: bool) -> None:
    parameters = _parameters(block)
    returns, returns_text = returned(block)
    item = {"name": name, "params": [{key: row[key] for key in row if key != "description"} for row in parameters],
            "returns": returns}
    # The code decides what is static: a JSDoc @static on a method the class body declares without the keyword
    # (KeyframeTrack's interpolant factories in r186) contradicts the running class, which the native check reads.
    qualifiers = _qualifiers(*(flag for flag, on in ((STATIC, static), (ASYNC, asynchronous or block.has(ASYNC)),
                                                     (ABSTRACT, block.has(ABSTRACT))) if on))
    if qualifiers:
        item["qualifiers"] = qualifiers
    owner.sections[METHODS].append(item)
    owner.documents[METHODS].append(_documentation(block, parameters, returns_text))


def _member(owner: _Class, name: str, block: DocBlock, *, static: bool, readonly: bool = False,
            kind: str = "") -> None:
    item = {"name": name, "type": _braced(block.first(TYPE) or "")[0] or kind or "any"}
    default = block.first(DEFAULT)
    if default is not None and default.strip():
        item["default"] = default.strip()
    qualifiers = _qualifiers(*(flag for flag, on in ((STATIC, static), (READONLY, readonly or block.has(READONLY)))
                               if on))
    if qualifiers:
        item["qualifiers"] = qualifiers
    owner.sections[MEMBERS].append(item)
    owner.documents[MEMBERS].append(_documentation(block, [], ""))


def _accessor(owner: _Class, name: str, block: DocBlock, *, static: bool, setter: bool) -> None:
    """A getter and its setter are one property: the first documented one declares it; a getter alone is
    read-only."""
    if name in owner.accessors:
        position = owner.accessors[name]
        if setter:
            qualifiers = [word for word in owner.sections[MEMBERS][position].get("qualifiers", []) if word != READONLY]
            if qualifiers:
                owner.sections[MEMBERS][position]["qualifiers"] = qualifiers
            else:
                owner.sections[MEMBERS][position].pop("qualifiers", None)
        return
    owner.accessors[name] = len(owner.sections[MEMBERS])
    _member(owner, name, block, static=static, readonly=not setter)


def read_classes(text: str) -> list:
    """Every documented class of one source file, as [(name, parent, ClassReference)] in source order."""
    lines = text.split("\n")
    found, owner, pending, in_constructor, in_static = [], None, None, False, False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("/**"):
            end = index
            while "*/" not in lines[end] and end + 1 < len(lines):
                end += 1
            pending = parse_block("\n".join(lines[index:end + 1]))
            index = end + 1
            continue
        if not stripped or stripped.startswith("//"):
            index += 1
            continue
        declared = _CLASS.match(line)
        if declared and owner is None:
            owner = _Class(declared.group(1), declared.group(2), pending)
            found.append(owner)
        elif owner is not None and line == "}":
            owner, in_constructor, in_static = None, False, False
        elif owner is not None:
            in_constructor, in_static = _member_line(owner, line, pending, in_constructor, in_static)
        pending = None
        index += 1
    return [(row.name, row.parent, _reference(row)) for row in found]


def _member_line(owner: _Class, line: str, block: "DocBlock | None", in_constructor: bool, in_static: bool) -> tuple:
    """Read one code line inside a class; returns whether the constructor or a static block is open after it."""
    if line.startswith("\t}") and not line.startswith("\t\t"):
        return False, False
    if _STATIC_BLOCK.match(line):
        return False, True
    if in_static:
        assignment = _STATIC_ASSIGNMENT.match(line)
        if assignment and assignment.group(1) == owner.name and _public(assignment.group(3), block):
            _member(owner, assignment.group(3), block, static=not assignment.group(2))
        return False, True
    if in_constructor:
        method, field_line = _THIS_METHOD.match(line), _THIS_FIELD.match(line)
        if method and _public(method.group(1), block):
            _method(owner, method.group(1), block, static=False, asynchronous=False)
        elif field_line and not method and _public(field_line.group(1), block):
            _member(owner, field_line.group(1), block, static=False)
        return True, False
    declared = _METHOD.match(line)
    if declared:
        static, asynchronous, accessor, _generator, name, _rest = declared.groups()
        if name == CONSTRUCTOR_NAME:
            if block is not None and not block.has(HIDE_CONSTRUCTOR):
                parameters = _parameters(block)
                owner.sections[CONSTRUCTORS].append({"name": owner.name, "params": [
                    {key: row[key] for key in row if key != "description"} for row in parameters]})
                owner.documents[CONSTRUCTORS].append(_documentation(block, parameters, ""))
            return True, False
        if accessor == SETTER and name in owner.accessors:
            # A setter usually has no block of its own: it makes its documented getter writable.
            _accessor(owner, name, block, static=bool(static), setter=True)
        elif _public(name, block):
            if accessor:
                _accessor(owner, name, block, static=bool(static), setter=accessor == SETTER)
            else:
                _method(owner, name, block, static=bool(static), asynchronous=bool(asynchronous))
        return False, False
    field_line = _FIELD.match(line)
    if field_line and _public(field_line.group(2), block):
        _member(owner, field_line.group(2), block, static=bool(field_line.group(1)))
    return in_constructor, in_static


def _reference(row: _Class) -> ClassReference:
    block = row.block or DocBlock("")
    notes = {DEPRECATED: block.first(DEPRECATED) or DEPRECATED} if block.has(DEPRECATED) else {}
    brief, _, rest = block.description.partition("\n\n")
    # The first paragraph is the class's role; JSDoc wraps it across lines, which Markdown reads as spaces.
    brief = " ".join(line.strip() for line in brief.split("\n") if line.strip())
    documentation = {"brief": brief, "description": rest.strip(), "tutorials": [], "notes": notes,
                     "items": row.documents}
    sections = {section: row.sections[section] for section in SECTIONS}
    return ClassReference(row.name, row.parent, None, ClassKind.OBJECT_CLASS, sections, documentation)


_EXPORT_LIST = re.compile(r"^export\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]", re.M)
_EXPORT_ALL = re.compile(r"^export\s*\*\s*from\s*['\"]([^'\"]+)['\"]", re.M)
_EXPORT_LOCAL = re.compile(r"^export\s*\{([^}]*)\}\s*;?\s*$", re.M)
_IMPORT_LIST = re.compile(r"^import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]", re.M)
_EXPORT_DECLARATION = re.compile(r"^export\s+(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?(?:async\s+)?"
                                 r"(?:class|function\*?|const|let|var|enum)\s+([A-Za-z_$][\w$]*)", re.M)


def module_exports(entry: str, read) -> dict:
    """{exported name: source path} of an entry module, following ``export { A, B as C } from`` and
    ``export * from`` through the modules ``read(path)`` returns (None for one it does not have)."""
    found, seen = {}, set()

    def follow(path):
        if path in seen:
            return
        seen.add(path)
        text = read(path)
        if text is None:
            return
        folder = path.rsplit("/", 1)[0] if "/" in path else ""
        for names, target in _EXPORT_LIST.findall(text):
            source = _join(folder, target)
            for part in names.split(","):
                original, _, alias = part.strip().partition(" as ")
                exported = (alias or original).strip()
                if exported and exported not in found:
                    found[exported] = _origin(source, original.strip(), read)
        imported = {}
        for names, target in _IMPORT_LIST.findall(text):
            for part in names.split(","):
                original, _, alias = part.strip().partition(" as ")
                if original.strip():
                    imported[(alias or original).strip()] = (_join(folder, target), original.strip())
        for names in _EXPORT_LOCAL.findall(text):
            for part in names.split(","):
                local, _, alias = part.strip().partition(" as ")
                exported = (alias or local).strip()
                if exported and exported not in found:
                    origin = imported.get(local.strip())
                    found[exported] = _origin(origin[0], origin[1], read) if origin else (path, local.strip())
        for name in _EXPORT_DECLARATION.findall(text):
            found.setdefault(name, (path, name))
        for target in _EXPORT_ALL.findall(text):
            follow(_join(folder, target))

    follow(entry)
    return found


def _origin(path: str, name: str, read, depth: int = 0) -> tuple:
    """(source path, local name) where a re-exported name is declared, following re-exports of it."""
    text = read(path) if depth < 8 else None
    if text is None:
        return path, name
    folder = path.rsplit("/", 1)[0] if "/" in path else ""
    for names, target in _EXPORT_LIST.findall(text):
        for part in names.split(","):
            original, _, alias = part.strip().partition(" as ")
            if (alias or original).strip() == name:
                return _origin(_join(folder, target), original.strip(), read, depth + 1)
    return path, name


#: Path segments a module specifier resolves: the current folder and its parent.
CURRENT_FOLDER, PARENT_FOLDER = ".", ".."


def _join(folder: str, target: str) -> str:
    parts = (folder.split("/") if folder else []) + target.split("/")
    resolved = []
    for part in parts:
        if not part or part == CURRENT_FOLDER:
            continue
        if part == PARENT_FOLDER:
            resolved = resolved[:-1]
        else:
            resolved.append(part)
    return "/".join(resolved)


@dataclass(frozen=True)
class JsDocText:
    """The card writer's text interface for JSDoc: descriptions are Markdown already, with {@link} tags to write."""

    code: object  # the card module's code()

    def markdown(self, text: "str | None") -> str:
        return jsdoc_markdown(text or "", self.code)

    def title(self, text: str) -> str:
        return text

    def address(self, address: str) -> str:
        return address


def closed_fences(text: str) -> str:
    """Markdown whose last code fence is closed: a description that opens a fence and never closes it (r186's
    PositionalAudio) would otherwise hold every heading after it as code."""
    fence = ""
    for line in text.split("\n"):
        stripped = line.strip()
        if fence:
            if stripped and set(stripped) == {fence[0]} and len(stripped) >= len(fence):
                fence = ""
        else:
            opening = _FENCE.match(line)
            fence = opening.group(1) if opening else ""
    return f"{text}\n{fence}" if fence else text


def jsdoc_markdown(text: str, code) -> str:
    """JSDoc text as Markdown: {@link Name}, {@link Name#member} and {@link Name text} become code or a link, and a
    code fence the text leaves open is closed."""
    def link(match):
        target, label = match.group(1), (match.group(2) or "").strip()
        if re.match(r"https?://", target):
            return f"[{label or target}]({target})"
        return code(target.replace("#", ".")) + (f" ({label})" if label and label != target else "")
    return closed_fences(_LINK.sub(link, text or "").strip())


__all__ = ["DocBlock", "JsDocText", "parse_block", "parameter", "returned", "read_classes", "jsdoc_markdown",
           "module_exports",
           "CONSTRUCTORS", "METHODS", "MEMBERS", "OPERATORS", "SIGNALS", "ENUMS", "CONSTANTS", "ANNOTATIONS",
           "THEME_ITEMS"]
