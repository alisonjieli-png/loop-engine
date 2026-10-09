"""Read TypeScript declaration files (.d.ts) and their TSDoc comments into a class's surface and documentation
(Babylon.js).

```text
one declaration file of a published package (Maths/math.vector.pure.d.ts)
├── a TSDoc block (/** ... */) documents the declaration right after it
├── export declare [abstract] class Name<T> extends Parent<T> implements ... {
│   ├── constructor(x?: number, ...);                 a constructor (one item per overload)
│   ├── [static] [abstract] name<T>(a: A, b?: B): R;  a method (one item per overload)
│   ├── [static] [readonly] name?: Type;              a property
│   ├── get name(): Type;  set name(value: Type);     an accessor property, read-only without a setter
│   └── private, protected, an index signature, a name that starts with an underscore, and a member whose
│       block says @internal, @hidden or @ignore are not the public surface and are left out
└── }   (a line holding only "}" closes the class)
```

A member may run over several lines (an object literal type): it ends at the first ";" outside brackets. The
types are the declaration's own; @param and @returns give each parameter's and the return value's text. The
surface has the shape api_card.py writes in its "javascript" syntax (TypeScript notation). Nothing here runs
JavaScript: which properties the published module does not hold is observed by importing it in Node
(node_native.observe), and mark_declared writes that observation onto the surface as "declare".
"""
from __future__ import annotations

import re

from .godot_reference import CONSTRUCTORS, MEMBERS, METHODS, SECTIONS, ClassKind, ClassReference
from .jsdoc_reference import DEPRECATED, DocBlock, parse_block

#: TSDoc tags the reader interprets, and the ones that keep a member off the public surface.
PARAM, RETURNS, RETURN = "param", "returns", "return"
SKIP_TAGS = ("internal", "hidden", "ignore", "private")
#: Modifiers a member declaration may start with, and the ones that are not public.
STATIC, READONLY, ABSTRACT, PRIVATE, PROTECTED, PUBLIC, DECLARE, OVERRIDE, ACCESSOR = MODIFIERS = (
    "static", "readonly", "abstract", "private", "protected", "public", "declare", "override", "accessor")
HIDDEN_MODIFIERS = (PRIVATE, PROTECTED)
#: Qualifiers a surface item keeps, in the order a declaration writes them. The reader keeps the ones a declaration
#: states; "declare" is never read from a declaration: it marks a property the running module was observed not to
#: hold (mark_declared), which exists once a caller assigns it.
QUALIFIER_ORDER = (DECLARE, STATIC, READONLY, ABSTRACT)
STATED_QUALIFIERS = (STATIC, READONLY, ABSTRACT)
GETTER, SETTER, CONSTRUCTOR = "get", "set", "constructor"
MEMBER_INDENT, CLASS_END = "    ", "}"
INTERNAL_PREFIX = "_"
OPENERS, CLOSERS = "({[", ")}]"
#: Type arguments open and close with angle brackets; an arrow's ">" follows "=" and closes nothing.
ANGLE_OPEN, ANGLE_CLOSE, ARROW_START = "<", ">", "="
DEFAULT_TYPE = "any"
_CLASS = re.compile(r"^export\s+declare\s+(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)(.*)\{\s*$")
_EXTENDS = re.compile(r"^extends\s+([A-Za-z_$][\w$.]*)")
_NAME = re.compile(r"^(?:(get|set)\s+)?([A-Za-z_$][\w$]*)(\??)")


def _depth_split(text: str, separator: str) -> list:
    """Text split at a separator outside brackets and angle brackets of type arguments."""
    parts, depth, angle, current = [], 0, 0, []
    for position, character in enumerate(text):
        if character in OPENERS:
            depth += 1
        elif character in CLOSERS:
            depth -= 1
        elif character == ANGLE_OPEN:
            angle += 1
        elif character == ANGLE_CLOSE and text[position - 1:position] != ARROW_START and angle:
            angle -= 1
        if character == separator and depth == 0 and angle == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    parts.append("".join(current))
    return parts


def _matching(text: str, start: int) -> int:
    """The position of the bracket that closes the one at ``start``, or -1."""
    depth = 0
    for position in range(start, len(text)):
        if text[position] in OPENERS:
            depth += 1
        elif text[position] in CLOSERS:
            depth -= 1
            if depth == 0:
                return position
    return -1


def parameters(text: str) -> list:
    """The parameters of a declaration's parameter list: name, type, and optional or rest."""
    rows = []
    for part in _depth_split(text, ","):
        part = " ".join(part.split())
        if not part:
            continue
        rest = part.startswith("...")
        name_part, _, kind = part[3:].partition(":") if rest else part.partition(":")
        name = name_part.strip()
        row = {"name": ("..." if rest else "") + name.rstrip("?"), "type": kind.strip() or DEFAULT_TYPE}
        if name.endswith("?"):
            row["optional"] = True
        rows.append(row)
    return rows


def _modifiers(declaration: str) -> tuple:
    words, rest = [], declaration
    while True:
        head, _, tail = rest.partition(" ")
        if head in MODIFIERS and tail:
            words.append(head)
            rest = tail
        else:
            return words, rest


def _qualifiers(words) -> list:
    return [word for word in QUALIFIER_ORDER if word in words]


def _stated(words) -> list:
    return [word for word in words if word in STATED_QUALIFIERS]


def _documentation(block: DocBlock, rows: list) -> dict:
    """A member's text: its description, then each documented parameter's and the return value's text."""
    parts = [block.description] if block.description else []
    described = {}
    for text in block.all(PARAM):
        name, _, description = text.partition(" ")
        described[name.strip()] = description.strip()
    listed = [f"- `{row['name']}`: {described[row['name'].lstrip('.')]}" for row in rows
              if described.get(row["name"].lstrip("."))]
    if listed:
        parts.append("\n".join(listed))
    returned = block.first(RETURNS, RETURN)
    if returned:
        parts.append(f"Returns: {returned}")
    notes = {DEPRECATED: block.first(DEPRECATED) or DEPRECATED} if block.has(DEPRECATED) else {}
    return {"description": "\n\n".join(parts), **notes}


class _Class:
    def __init__(self, name: str, parent: "str | None", block: "DocBlock | None") -> None:
        self.name, self.parent, self.block = name, parent, block
        self.sections = {section: [] for section in SECTIONS}
        self.documents = {section: [] for section in SECTIONS}
        self.accessors = {}

    def add(self, section: str, item: dict, documentation: dict) -> None:
        self.sections[section].append(item)
        self.documents[section].append(documentation)


def _member(owner: _Class, declaration: str, block: "DocBlock | None") -> None:
    """Read one member declaration (without its final ";") into the class's surface, or leave it out."""
    words, rest = _modifiers(" ".join(declaration.split()))
    if any(word in HIDDEN_MODIFIERS for word in words) or rest.startswith("["):
        return
    if block is not None and any(block.has(tag) for tag in SKIP_TAGS):
        return
    match = _NAME.match(rest)
    if not match:
        return
    accessor, name, optional = match.groups()
    after = rest[match.end():].lstrip()
    if name.startswith(INTERNAL_PREFIX):
        return
    if accessor == SETTER:
        if name in owner.accessors:
            row = owner.sections[MEMBERS][owner.accessors[name]]
            kept = [word for word in row.get("qualifiers", []) if word != READONLY]
            if kept:
                row["qualifiers"] = kept
            else:
                row.pop("qualifiers", None)
        return
    if block is None:
        return
    if after.startswith(ANGLE_OPEN):
        after = after[_matching(after.replace(ANGLE_OPEN, "(").replace(ANGLE_CLOSE, ")"), 0) + 1:].lstrip()
    if accessor == GETTER or not after.startswith("("):
        kind = after.partition(":")[2].strip() if accessor != GETTER else after[_matching(after, 0) + 1:].partition(
            ":")[2].strip()
        qualifiers = _stated(words) + ([READONLY] if accessor == GETTER else [])
        item = {"name": name, "type": kind or DEFAULT_TYPE}
        if _qualifiers(qualifiers):
            item["qualifiers"] = _qualifiers(qualifiers)
        if accessor == GETTER:
            owner.accessors[name] = len(owner.sections[MEMBERS])
        owner.add(MEMBERS, item, _documentation(block, []))
        return
    close = _matching(after, 0)
    rows = parameters(after[1:close])
    returned = after[close + 1:].partition(":")[2].strip()
    if name == CONSTRUCTOR and not optional:
        owner.add(CONSTRUCTORS, {"name": owner.name, "params": rows}, _documentation(block, rows))
        return
    item = {"name": name, "params": rows, "returns": {"type": returned} if returned else None}
    if _qualifiers(_stated(words)):
        item["qualifiers"] = _qualifiers(_stated(words))
    owner.add(METHODS, item, _documentation(block, rows))


def _parent(header: str) -> "str | None":
    """The class a header extends: read after the class's own type parameters, whose constraints may say extends."""
    header = header.strip()
    if header.startswith(ANGLE_OPEN):
        depth = 0
        for position, character in enumerate(header):
            depth += 1 if character == ANGLE_OPEN else -1 if character == ANGLE_CLOSE and \
                header[position - 1:position] != ARROW_START else 0
            if depth == 0:
                header = header[position + 1:]
                break
    extends = _EXTENDS.match(header.strip())
    return extends.group(1) if extends else None


def read_declarations(text: str) -> list:
    """Every class a declaration file declares, as [(name, parent, ClassReference)] in source order."""
    lines = text.split("\n")
    found, owner, pending = [], None, None
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
        if owner is None and declared:
            owner = _Class(declared.group(1), _parent(declared.group(2)), pending)
            found.append(owner)
        elif owner is not None and line.rstrip() == CLASS_END:
            owner = None
        elif owner is not None and line.startswith(MEMBER_INDENT) and not line.startswith(MEMBER_INDENT + " "):
            declaration, end = line.strip(), index
            while not _complete(declaration) and end + 1 < len(lines):
                end += 1
                declaration += " " + lines[end].strip()
            _member(owner, declaration.rstrip().rstrip(";"), pending)
            index = end
        pending = None
        index += 1
    return [(row.name, row.parent, _reference(row)) for row in found]


def _complete(declaration: str) -> bool:
    """Whether a declaration has reached its final ";" outside brackets."""
    depth = 0
    for character in declaration:
        depth += 1 if character in OPENERS else -1 if character in CLOSERS else 0
    return depth <= 0 and declaration.rstrip().endswith(";")


def _reference(row: _Class) -> ClassReference:
    block = row.block or DocBlock("")
    notes = {DEPRECATED: block.first(DEPRECATED) or DEPRECATED} if block.has(DEPRECATED) else {}
    brief, _, rest = block.description.partition("\n\n")
    brief = " ".join(line.strip() for line in brief.split("\n") if line.strip())
    documentation = {"brief": brief, "description": rest.strip(), "tutorials": [], "notes": notes,
                     "items": row.documents}
    return ClassReference(row.name, row.parent, None, ClassKind.OBJECT_CLASS,
                          {section: row.sections[section] for section in SECTIONS}, documentation)


def mark_declared(references: dict, unheld: dict) -> int:
    """Mark "declare" on every property the running module was observed not to hold ({class: [property names]},
    from node_native.observe), in the order a declaration writes qualifiers, and return how many were marked. A name
    a class gives a static and an instance property alike is not marked: the observation names properties, not
    which of the two it means, and the native check then refuses the class instead of guessing."""
    marked = 0
    for name, reference in references.items():
        absent = set(unheld.get(name) or ())
        rows = reference.sections[MEMBERS]
        statics = {}
        for row in rows:
            statics.setdefault(row["name"], set()).add(STATIC in row.get("qualifiers", ()))
        for row in rows:
            words = row.get("qualifiers", [])
            if row["name"] in absent and len(statics[row["name"]]) == 1 and DECLARE not in words \
                    and ABSTRACT not in words:
                row["qualifiers"] = _qualifiers([DECLARE, *words])
                marked += 1
    return marked


__all__ = ["read_declarations", "parameters", "mark_declared"]
