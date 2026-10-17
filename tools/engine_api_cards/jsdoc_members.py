"""Read the JSDoc-documented members of a JavaScript library's CommonJS sources into card units (lodash's per-method
modules, Express's application, request and response).

```text
one source file of the published package (the tag's blob, byte for byte)
├── a JSDoc block (/** ... */) documents the declaration after it (blank lines and line comments between):
│   ├── function name( ... ) {                    a module-level function (lodash: chunk.js)
│   ├── var|let|const name = ...                  a module-level value built by a helper (lodash: camelCase.js)
│   ├── owner.name = [function ...]               a member of an exported object (Express: app.use, res.status)
│   └── defineGetter(owner, 'name', function ...  a read-only property of an exported object (Express: req.protocol)
├── public by the package's own marker: @memberOf of the export (lodash), or @public / @api public (Express); a
│   block marked @private, @ignore or @api private, or a name with a leading underscore, is not a surface
└── @param (a parameter written "@param-" is the library's hidden one and is not read), @returns, @example
```

Each file is read by a rule of javascript_packages.json: which files, the object each owner name stands for (Express's
app is express.application), and the public names of functions the package exports under another name (Express's
createApplication is express itself). Nothing here runs JavaScript; node_members.py asks the module itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .bbcode import invisible
from .godot_reference import SECTIONS, ClassKind, ClassReference
from .jsdoc_reference import DocBlock, parameter, parse_block, returned

FUNCTIONS, METHODS, MEMBERS = "functions", "methods", "members"
PRIVATE_TAGS = ("private", "ignore")
PUBLIC_TAG, API_TAG, MEMBER_OF_TAG, EXAMPLE_TAG, NAME_TAG, DEPRECATED_TAG = (
    "public", "api", "memberOf", "example", "name", "deprecated")
API_PUBLIC, API_PRIVATE = "public", "private"
READONLY = "readonly"
_FUNCTION = re.compile(r"^function\s+([A-Za-z_$][\w$]*)\s*\(")
_VALUE = re.compile(r"^(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=")
_MEMBER = re.compile(r"^([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\s*=(?!=)")
_GETTER = re.compile(r"^defineGetter\(\s*([A-Za-z_$][\w$]*)\s*,\s*['\"]([A-Za-z_$][\w$]*)['\"]")
#: The fence an @example becomes in a card: JavaScript code, as the library wrote it.
EXAMPLE_FENCE = "```js"
#: An HTML comment opener, which a renderer hides from a person and the qualification safety rules refuse, written
#: visibly: a character reference in a sentence, and the same string as a JavaScript escape in an example.
COMMENT_OPENER, COMMENT_IN_PROSE, COMMENT_IN_CODE = "<!--", "&lt;!--", "\\x3c!--"


def visible(text: str, *, code: bool = False) -> str:
    """Text whose invisible characters are written visibly with the same meaning: a \\u escape in an example
    (JavaScript reads it the same way inside a string), a numeric character reference in a sentence."""
    written = "".join((f"\\u{ord(character):04x}" if code else f"&#x{ord(character):04X};")
                      if invisible(character) else character for character in text)
    return written.replace(COMMENT_OPENER, COMMENT_IN_CODE if code else COMMENT_IN_PROSE)


@dataclass(frozen=True)
class Member:
    """One documented public member of one file: who owns it, its name, how it is declared, and its block."""

    owner: "str | None"  # the owner name in the source (app, req, res), or None for a module-level declaration
    name: str
    declaration: str  # function, value, member, getter
    block: DocBlock
    line: int
    #: The parameter names the declaration itself lists (function name(a, b)), read when the block has no @param.
    declared: tuple = ()


_PARAMETERS = re.compile(r"function\b[^(]*\(([^)]*)\)")


def declared_parameters(code: str) -> tuple:
    """The parameter names a function declaration lists on its own line (a rest parameter keeps its dots), without
    their defaults."""
    match = _PARAMETERS.search(code)
    if not match:
        return ()
    names = []
    for part in match.group(1).split(","):
        name = part.split("=", 1)[0].strip()
        rest = name.startswith("...")
        name = name[3:] if rest else name
        if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
            names.append(("..." if rest else "") + name)
    return tuple(names)


def declarations(text: str) -> list:
    """Every (line, block, declaration line) pair of a source file: a JSDoc block and the first code line after it."""
    lines = text.split("\n")
    found, index = [], 0
    while index < len(lines):
        if lines[index].strip().startswith("/**"):
            end = index
            while "*/" not in lines[end] and end + 1 < len(lines):
                end += 1
            block = parse_block("\n".join(lines[index:end + 1]))
            following = end + 1
            while following < len(lines) and (not lines[following].strip() or lines[following].strip().startswith(
                    "//")):
                following += 1
            if following < len(lines):
                found.append((following + 1, block, lines[following]))
            index = end + 1
            continue
        index += 1
    return found


def is_public(block: DocBlock, marker: str) -> bool:
    """Whether a block is public by the package's own marker: "memberOf:<export>" (lodash's @memberOf _) or "public"
    (Express's @public or @api public); never when it is marked private or ignored."""
    if any(block.has(tag) for tag in PRIVATE_TAGS) or (block.first(API_TAG) or "").strip() == API_PRIVATE:
        return False
    if marker.startswith(MEMBER_OF_TAG + ":"):
        return (block.first(MEMBER_OF_TAG) or "").strip() == marker.split(":", 1)[1]
    return block.has(PUBLIC_TAG) or (block.first(API_TAG) or "").strip() == API_PUBLIC


def read_members(text: str, marker: str) -> list:
    """Every documented public member a source file declares, in source order."""
    members = []
    for line, block, code in declarations(text):
        stripped = code.strip()
        if not is_public(block, marker):
            continue
        for pattern, kind in ((_GETTER, "getter"), (_MEMBER, "member"), (_FUNCTION, "function"), (_VALUE, "value")):
            match = pattern.match(stripped)
            if not match:
                continue
            owner, name = (match.group(1), match.group(2)) if match.lastindex == 2 else (None, match.group(1))
            # A documented value with a @type and no parameters is data (lodash's templateSettings), not a function.
            data = kind == "value" and block.has("type") and not block.all("param") and returned(block)[0] is None
            if not name.startswith("_") and not data:
                members.append(Member(owner, name, kind, block, line, declared_parameters(stripped)))
            break
    return members


def _examples(block: DocBlock) -> list:
    rows = []
    for text in block.all(EXAMPLE_TAG):
        body = "\n".join(line for line in text.split("\n")).strip("\n")
        if body.strip():
            rows.append(f"{EXAMPLE_FENCE}\n{visible(body.rstrip(), code=True)}\n```")
    return rows


def documentation(block: DocBlock) -> dict:
    """The text of one member: its description, each parameter's and its return value's text, and its examples."""
    parts = [visible(block.description)] if block.description else []
    rows = [row for row in (parameter(text) for text in block.all("param")) if row is not None]
    described = [row for row in rows if row.get("description")]
    if described:
        parts.append("\n".join(f"- `{row['name']}`: {visible(' '.join(row['description'].split()))}"
                               for row in described))
    _returns, returns_text = returned(block)
    returns_text = re.sub(r"^-\s*", "", returns_text.strip())
    if returns_text:
        parts.append(f"Returns: {visible(' '.join(returns_text.split()))}")
    examples = _examples(block)
    if examples:
        parts.append("Example:\n\n" + "\n\n".join(examples))
    notes = {DEPRECATED_TAG: block.first(DEPRECATED_TAG) or DEPRECATED_TAG} if block.has(DEPRECATED_TAG) else {}
    return {"description": "\n\n".join(parts), **notes}


def signature_item(name: str, block: DocBlock, declared: tuple = ()) -> dict:
    """A member's declaration: its @param rows, or the parameter names its own declaration lists when the block
    documents none (Express's res.sendFile), untyped."""
    rows = [row for row in (parameter(text) for text in block.all("param")) if row is not None]
    params = [{key: row[key] for key in row if key != "description"} for row in rows]
    if not block.all("param") and declared:
        params = [{"name": name} for name in declared]
    returns, _text = returned(block)
    return {"name": name, "params": params, "returns": returns}


def empty_sections() -> tuple:
    names = tuple(SECTIONS) + (FUNCTIONS,)
    return {name: [] for name in names}, {name: [] for name in names}


def brief(block: DocBlock) -> str:
    return visible(" ".join(block.description.split("\n\n", 1)[0].split())) if block.description else ""


@dataclass
class JsUnit:
    """One card before it is written: its reference, where Node finds its object, and the file its text is in."""

    name: str
    reference: ClassReference
    path: list  # property path from the module's export: [] is the export itself
    file: str
    members: list = field(default_factory=list)  # [(name, kind)] of an object card


def units(files: dict, rules: list, *, prefix: str) -> tuple:
    """({card name: JsUnit}, [(subject, reason, detail)]): a function card per module-level public function, an object
    card per owner (its methods and getters with their first paragraph) and a member card per documented member.
    ``prefix`` names the export in a card's name (lodash's "_")."""
    found, problems, objects, described = {}, [], {}, {}
    for rule in rules:
        owners = rule.get("owners", {})
        exported = rule.get("exports", {})
        for path, text in sorted(files.items()):
            if not re.fullmatch(rule["files"], path) or re.fullmatch(rule.get("exclude", "(?!)"), path):
                continue
            for member in read_members(text, rule["marker"]):
                if member.owner is None and member.name in owners:
                    # The owner object's own block ("Request prototype."), which describes its card.
                    described[member.name] = brief(member.block)
                    continue
                if member.owner is None:
                    public = exported.get(member.name, member.name)
                    if public is None:
                        continue
                    name = public if not prefix else f"{prefix}.{public}"
                    if not public:
                        name = rule["export_name"]
                    item = signature_item(public or rule["export_name"], member.block, member.declared)
                    sections, documents = empty_sections()
                    sections[FUNCTIONS].append(item)
                    documents[FUNCTIONS].append(documentation(member.block))
                    reference = ClassReference(name, None, None, ClassKind.FUNCTION, sections, {
                        "brief": brief(member.block), "description": "", "tutorials": [], "notes": {},
                        "items": documents})
                    if name in found:
                        problems.append((name, "duplicate_class", path))
                        continue
                    found[name] = JsUnit(name, reference, [public] if public else [], path)
                    continue
                if member.owner not in owners:
                    continue
                objects.setdefault(member.owner, []).append((member, path))
    for owner, rows in sorted(objects.items()):
        target = next(rule["owners"][owner] for rule in rules if owner in rule.get("owners", {}))
        sections, documents = empty_sections()
        listed = []
        for member, path in rows:
            card_name = f"{owner}.{member.name}"
            if member.declaration == "getter":
                section, item = MEMBERS, {"name": member.name, "type": (returned(member.block)[0] or {}).get(
                    "type", "any"), "qualifiers": [READONLY]}
            else:
                section, item = METHODS, signature_item(member.name, member.block, member.declared)
            if any(row["name"] == member.name for row in sections[section]):
                problems.append((card_name, "duplicate_class", path))
                continue
            sections[section].append(item)
            documents[section].append({"description": brief(member.block)})
            listed.append((member.name, "property" if section == MEMBERS else "method"))
            member_sections, member_documents = empty_sections()
            member_sections[section].append(item)
            member_documents[section].append(documentation(member.block))
            kind = ClassKind.PROPERTY if section == MEMBERS else ClassKind.METHOD
            reference = ClassReference(card_name, None, None, kind, member_sections, {
                "brief": brief(member.block), "description": "", "tutorials": [], "notes": {},
                "items": member_documents})
            found[card_name] = JsUnit(card_name, reference, [target, member.name], path)
        reference = ClassReference(owner, None, None, ClassKind.OBJECT, sections, {
            "brief": described.get(owner) or f"The members of `{owner}` the library documents as public.",
            "description": "",
            "tutorials": [], "notes": {}, "items": documents})
        found[owner] = JsUnit(owner, reference, [target], rows[0][1], listed)
    return found, problems


__all__ = ["Member", "JsUnit", "declarations", "is_public", "read_members", "documentation", "units"]
