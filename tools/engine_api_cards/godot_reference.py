"""Read Godot class reference XML into one class's surface and its documentation.

The same reader reads both sources of a Godot card, so the two can be compared exactly:

```text
<class name inherits api_type>              the engine's --doctool dump (structure only, no text) or the
├── brief_description, description          repository's doc/classes, modules/*/doc_classes and
├── tutorials/link                          platform/*/doc_classes files at the same tag (structure and text)
├── constructors, methods, operators        name, return (type, enum, is_bitfield), returns_error, param
│                                           (index, name, type, enum, is_bitfield, default), qualifiers
├── members                                 name, type, setter, getter, default, enum, is_bitfield, overrides
├── signals                                 name, param
├── constants                               name, value, enum, is_bitfield: grouped into enumerations by enum
├── annotations                             name, param, qualifiers
└── theme_items                             name, data_type, type, default
```

The surface is JSON-ready and engine-neutral in shape (api_card.py writes its lines); the documentation keeps the
raw description text of every item, aligned with the surface, for the BBCode converter. deprecated, experimental
and keywords are documentation, never surface: the engine binary does not carry them.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from enum import Enum


class ClassKind(str, Enum):
    """What a class of the reference is, which decides how the engine itself is asked about it."""

    OBJECT_CLASS = "class"  # a class ClassDB registers (it has an api_type)
    BUILTIN_TYPE = "builtin_type"  # a Variant type (Vector3, String, Array, ...)
    GLOBAL_SCOPE = "global_scope"  # @GlobalScope or @GDScript: global functions, constants and annotations


#: The surface sections and the XML element of each item (constants are grouped into enumerations after reading).
CONSTRUCTORS, METHODS, OPERATORS, MEMBERS, SIGNALS, ENUMS, CONSTANTS, ANNOTATIONS, THEME_ITEMS = SECTIONS = (
    "constructors", "methods", "operators", "members", "signals", "enums", "constants", "annotations",
    "theme_items")
ITEM_TAGS = {CONSTRUCTORS: "constructor", METHODS: "method", OPERATORS: "operator", MEMBERS: "member",
             SIGNALS: "signal", CONSTANTS: "constant", ANNOTATIONS: "annotation", THEME_ITEMS: "theme_item"}
CALLABLE_SECTIONS = (CONSTRUCTORS, METHODS, OPERATORS)
CLASS_TAG, BRIEF_TAG, DESCRIPTION_TAG, TUTORIALS_TAG, LINK_TAG = (
    "class", "brief_description", "description", "tutorials", "link")
RETURN_TAG, PARAM_TAG, RETURNS_ERROR_TAG = "return", "param", "returns_error"
#: Attributes of a declared type, in the order the surface keeps them.
BITFIELD_ATTRIBUTE = "is_bitfield"
TYPE_ATTRIBUTES = ("type", "enum", BITFIELD_ATTRIBUTE)
#: Documentation attributes: the repository writes them, the engine binary does not know them.
NOTE_ATTRIBUTES = ("deprecated", "experimental")
KEYWORDS_ATTRIBUTE = "keywords"
TRUE_TEXT = "true"
GLOBAL_PREFIX = "@"
#: A document type or entity declaration can expand without bound; class reference files never hold one.
_DECLARATION = re.compile(rb"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)


class ReferenceError(ValueError):
    """A class reference file that cannot be read as one, with a stable reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


@dataclass(frozen=True)
class ClassReference:
    """One class: its identity, its surface (JSON-ready) and its documentation (raw description text)."""

    name: str
    parent: "str | None"
    api_type: "str | None"
    kind: ClassKind
    sections: dict
    documentation: dict = field(compare=False)

    def structure(self) -> tuple:
        """What both sources must agree on: identity and surface, never text."""
        return self.name, self.parent, self.api_type, self.kind.value, _frozen(self.sections)

    @property
    def is_empty(self) -> bool:
        return not self.parent and not any(self.sections.values())


def _frozen(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _frozen(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def _declared(element) -> dict:
    """A declared type: type, enum and is_bitfield where present."""
    found = {}
    for attribute in TYPE_ATTRIBUTES:
        value = element.get(attribute)
        if value is not None:
            found[attribute] = value == TRUE_TEXT if attribute == BITFIELD_ATTRIBUTE else value
    return found


def _parameters(element) -> list:
    rows = []
    for parameter in element.findall(PARAM_TAG):
        row = {"name": parameter.get("name", ""), **_declared(parameter)}
        if parameter.get("default") is not None:
            row["default"] = parameter.get("default")
        rows.append((int(parameter.get("index", "0")), row))
    return [row for _index, row in sorted(rows, key=lambda pair: pair[0])]


def _notes(element) -> dict:
    notes = {name: element.get(name) for name in NOTE_ATTRIBUTES if element.get(name) is not None}
    if element.get(KEYWORDS_ATTRIBUTE):
        notes[KEYWORDS_ATTRIBUTE] = element.get(KEYWORDS_ATTRIBUTE)
    return notes


def _text(element) -> str:
    return element.text or "" if element is not None else ""


def _callable(element, section: str) -> tuple:
    item = {"name": element.get("name", "")}
    if section != ANNOTATIONS:
        returned = element.find(RETURN_TAG)
        item["returns"] = _declared(returned) if returned is not None else None
    item["params"] = _parameters(element)
    qualifiers = (element.get("qualifiers") or "").split()
    if qualifiers:
        item["qualifiers"] = qualifiers
    errors = [int(row.get("number", "0")) for row in element.findall(RETURNS_ERROR_TAG)]
    if errors:
        item["returns_errors"] = errors
    return item, {"description": _text(element.find(DESCRIPTION_TAG)), **_notes(element)}


def _member(element) -> tuple:
    item = {"name": element.get("name", ""), **_declared(element), "setter": element.get("setter", ""),
            "getter": element.get("getter", "")}
    for attribute in ("default", "overrides"):
        if element.get(attribute) is not None:
            item[attribute] = element.get(attribute)
    return item, {"description": _text(element), **_notes(element)}


def _theme_item(element) -> tuple:
    item = {"name": element.get("name", ""), "data_type": element.get("data_type", ""),
            "type": element.get("type", "")}
    if element.get("default") is not None:
        item["default"] = element.get("default")
    return item, {"description": _text(element), **_notes(element)}


def _signal(element) -> tuple:
    return ({"name": element.get("name", ""), "params": _parameters(element)},
            {"description": _text(element.find(DESCRIPTION_TAG)), **_notes(element)})


def class_kind(name: str, api_type: "str | None") -> ClassKind:
    """A class ClassDB registers carries an api_type; the global scopes are named with @; the rest are Variant
    types."""
    if name.startswith(GLOBAL_PREFIX):
        return ClassKind.GLOBAL_SCOPE
    return ClassKind.OBJECT_CLASS if api_type else ClassKind.BUILTIN_TYPE


def read_reference(data: bytes) -> ClassReference:
    """One class reference file, or ReferenceError naming why it cannot be read."""
    if _DECLARATION.search(data):
        raise ReferenceError("reference_declaration_refused", "a document type or entity declaration")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise ReferenceError("reference_unreadable", str(error)[:120]) from None
    if root.tag != CLASS_TAG or not root.get("name"):
        raise ReferenceError("reference_not_a_class", root.tag)
    name = root.get("name")
    sections = {section: [] for section in SECTIONS}
    documents = {section: [] for section in SECTIONS}
    enums, enum_documents = {}, {}
    readers = {MEMBERS: _member, SIGNALS: _signal, THEME_ITEMS: _theme_item}
    for section, tag in ITEM_TAGS.items():
        for element in root.iter(tag):
            if section == CONSTANTS:
                value = {"name": element.get("name", ""), "value": element.get("value", "")}
                documentation = {"description": _text(element), **_notes(element)}
                enum = element.get("enum")
                if enum:
                    if enum not in enums:
                        enums[enum] = {"name": enum, "is_bitfield": element.get(BITFIELD_ATTRIBUTE) == TRUE_TEXT,
                                       "values": []}
                        enum_documents[enum] = {"description": "", "values": []}
                    enums[enum]["values"].append(value)
                    enum_documents[enum]["values"].append(documentation)
                else:
                    sections[CONSTANTS].append(value)
                    documents[CONSTANTS].append(documentation)
                continue
            reader = readers.get(section)
            item, documentation = reader(element) if reader else _callable(element, section)
            sections[section].append(item)
            documents[section].append(documentation)
    sections[ENUMS] = list(enums.values())
    documents[ENUMS] = [enum_documents[key] for key in enums]
    tutorials = [{"title": link.get("title", ""), "address": (link.text or "").strip()}
                 for link in root.iter(LINK_TAG)]
    documentation = {"brief": _text(root.find(BRIEF_TAG)), "description": _text(root.find(DESCRIPTION_TAG)),
                     "tutorials": tutorials, "notes": _notes(root), "items": documents}
    api_type = root.get("api_type")
    return ClassReference(name, root.get("inherits"), api_type, class_kind(name, api_type),
                          {key: value for key, value in sections.items()}, documentation)


def inheritance(references: dict) -> tuple:
    """({class: [parent, grandparent, ...]}, {class: [direct children, sorted]}) over every class read."""
    chains, children = {}, {name: [] for name in references}
    for name, reference in references.items():
        chain, seen, parent = [], {name}, reference.parent
        while parent and parent not in seen:
            chain.append(parent)
            seen.add(parent)
            parent = references[parent].parent if parent in references else None
        chains[name] = chain
        if reference.parent in children:
            children[reference.parent].append(name)
    return chains, {name: sorted(rows) for name, rows in children.items()}


__all__ = ["ClassKind", "ClassReference", "ReferenceError", "SECTIONS", "ITEM_TAGS", "read_reference",
           "inheritance", "class_kind"]
