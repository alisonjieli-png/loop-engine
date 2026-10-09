"""The Godot 3 to 4 renames the engine's own project upgrade tool applies, attached to the classes they name.

The source is ``editor/project_upgrade/renames_map_3_to_4.cpp`` at the same tag as the class reference: the tables
the editor's project converter rewrites Godot 3 code with. A rename reaches a card only where the map says so:

```text
renames_map_3_to_4.cpp
├── tables read (GDScript only; the C# tables repeat them in C# names, the shader, input map, project.godot
│   and theme override tables rename no class member)
│   ├── class_renames, builtin_types_renames      Area -> Area3D: the card of the new class
│   ├── gdscript_function_renames                 a method, on the classes its comment names
│   ├── gdscript_properties_renames               a property, on the classes its comment names
│   ├── gdscript_signals_renames                  a signal, on the classes its comment names
│   ├── enum_renames                              a constant or an enumeration, on the classes its comment
│   │                                             or the comment line above its block names (// @GlobalScope)
│   ├── color_renames                             a named colour constant of Color
│   └── project_settings_renames                  a setting, which ProjectSettings lists as a property
├── an entry commented out (// { ... }) is disabled in the converter and never read as a rename
└── a rename is kept only when its new name is on the class's surface at the tag (its own or an ancestor's),
    and is counted, not shown, when its comment names no class of the tag or the class lacks the new name
```
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .godot_reference import CONSTANTS, ENUMS, MEMBERS, METHODS, SIGNALS, ClassReference

MAP_PATH = "editor/project_upgrade/renames_map_3_to_4.cpp"
FROM_VERSION = "3"
#: The rename kinds a card shows (api_card.RENAME_KINDS).
CLASS_RENAME, METHOD_RENAME, PROPERTY_RENAME, SIGNAL_RENAME, CONSTANT_RENAME, ENUM_RENAME = KINDS = (
    "class", "method", "property", "signal", "constant", "enum")
#: The tables read, the kind of rename each holds and, for a table about one class, that class.
TABLES = {"class_renames": (CLASS_RENAME, None), "builtin_types_renames": (CLASS_RENAME, None),
          "gdscript_function_renames": (METHOD_RENAME, None),
          "gdscript_properties_renames": (PROPERTY_RENAME, None),
          "gdscript_signals_renames": (SIGNAL_RENAME, None), "enum_renames": (CONSTANT_RENAME, None),
          "color_renames": (CONSTANT_RENAME, "Color"), "project_settings_renames": (PROPERTY_RENAME, "ProjectSettings")}
#: The tables whose trailing comment is a note about the rename rather than the classes it applies to.
NOTE_TABLES = ("class_renames", "builtin_types_renames")
#: Which section of a class holds the new name of each kind of member rename.
SURFACE_SECTIONS = {METHOD_RENAME: (METHODS,), PROPERTY_RENAME: (MEMBERS,), SIGNAL_RENAME: (SIGNALS,),
                    CONSTANT_RENAME: (CONSTANTS, ENUMS)}
#: What a table entry that could not be attached is counted as.
UNATTRIBUTED, TARGET_MISSING, ATTACHED = "unattributed", "target_missing", "attached"

_TABLE = re.compile(r"const char \*RenamesMap3To4::(\w+)\[\]\[2\] = \{\n(.*?)\n\};", re.S)
_STRING = r'"((?:[^"\\]|\\.)*)"'
_ENTRY = re.compile(r"^\s*\{\s*" + _STRING + r"\s*,\s*" + _STRING + r"\s*\},?\s*(?://\s*(.*?))?\s*$")
_COMMENT = re.compile(r"^\s*//\s*(.*?)\s*$")
_DISABLED = re.compile(r"^\s*//\s*\{")
_TERMINATOR = re.compile(r"^\s*\{\s*nullptr\s*,\s*nullptr\s*\}")
#: Where a comment's list of classes ends and its note begins: " -- ", " - " or " -> ".
_NOTE = re.compile(r"\s+(?:--|-|->)\s+")
#: A class written for both dimensions at once, as Area(2D/3D).
_DIMENSIONS = re.compile(r"^([A-Za-z_]\w*)\((\w+(?:/\w+)+)\)$")


class RenamesMapError(ValueError):
    """A renames map that cannot be read, with a stable reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


@dataclass(frozen=True)
class MapEntry:
    """One active entry of a table: its old and new name, its comment and the class named above its block."""

    table: str
    kind: str
    old: str
    new: str
    comment: str
    block_class: str
    line: int


def read_map(text: str, known_classes) -> list:
    """Every active entry of the tables read, in the map's order; raises RenamesMapError when a table is missing."""
    tables = {name: (body, text.count("\n", 0, match.start(2)) + 1)
              for match in _TABLE.finditer(text) for name, body in [(match.group(1), match.group(2))]}
    missing = sorted(set(TABLES) - set(tables))
    if missing:
        raise RenamesMapError("renames_table_missing", ", ".join(missing))
    entries = []
    for table, (kind, _owner) in TABLES.items():
        body, first_line = tables[table]
        block_class = ""
        for offset, line in enumerate(body.split("\n")):
            if not line.strip():
                block_class = ""
                continue
            if _DISABLED.match(line) or _TERMINATOR.match(line):
                continue
            entry = _ENTRY.match(line)
            if entry:
                entries.append(MapEntry(table, kind, entry.group(1), entry.group(2), entry.group(3) or "",
                                        block_class, first_line + offset))
                continue
            comment = _COMMENT.match(line)
            if comment and comment.group(1) in known_classes:
                block_class = comment.group(1)
    return entries


def comment_classes(comment: str, known_classes, earlier_names: dict) -> list:
    """The classes of the tag a comment names before its note: each name as written when the tag has that class,
    and its Godot 4 name when it is a Godot 3 name the class table renames."""
    head = _NOTE.split(comment, maxsplit=1)[0]
    found = []
    for token in head.split(","):
        token = token.strip().rstrip(".")
        dimensions = _DIMENSIONS.match(token)
        names = [dimensions.group(1) + part for part in dimensions.group(2).split("/")] if dimensions else [token]
        for name in names:
            for candidate in (name, earlier_names.get(name)):
                if candidate and candidate in known_classes and candidate not in found:
                    found.append(candidate)
    return found


def _surface_names(reference: ClassReference, sections) -> set:
    names = set()
    for section in sections:
        for item in reference.sections.get(section, ()):
            names.add(item["name"])
            if section == ENUMS:
                names.update(value["name"] for value in item["values"])
    return names


def attach(entries, references: dict, chains: dict) -> tuple:
    """({class: [rename, ...]}, {table: Counter of outcomes}): every entry that holds on the tag's surface."""
    earlier_names = {entry.old: entry.new for entry in entries if entry.kind == CLASS_RENAME}
    known = set(references)
    renames, outcomes = {}, {table: Counter() for table in TABLES}
    for entry in entries:
        _kind, owner = TABLES[entry.table]
        if entry.kind == CLASS_RENAME:
            targets = [entry.new] if entry.new in known else []
        elif owner:
            targets = [owner] if owner in known else []
        else:
            targets = comment_classes(entry.comment, known, earlier_names) if entry.comment else (
                [entry.block_class] if entry.block_class else [])
        if not targets:
            outcomes[entry.table][UNATTRIBUTED] += 1
            continue
        attached = False
        for target in targets:
            row = _rename(entry, target, references, chains)
            if row is not None:
                renames.setdefault(target, []).append(row)
                attached = True
        outcomes[entry.table][ATTACHED if attached else TARGET_MISSING] += 1
    return {name: _ordered(rows) for name, rows in renames.items()}, {
        table: dict(counter) for table, counter in outcomes.items()}


def _rename(entry: MapEntry, target: str, references: dict, chains: dict) -> "dict | None":
    if entry.kind == CLASS_RENAME:
        row = {"kind": CLASS_RENAME, "from": entry.old, "to": entry.new, "table": entry.table, "line": entry.line}
        if entry.table in NOTE_TABLES and entry.comment:
            row["note"] = entry.comment
        return row
    lineage = [target] + list(chains.get(target, ()))
    sections = SURFACE_SECTIONS[entry.kind]
    holders = [name for name in lineage if name in references
               and entry.new in _surface_names(references[name], sections)]
    if not holders:
        return None
    kind = entry.kind
    if kind == CONSTANT_RENAME and any(entry.new in {item["name"] for item in references[name].sections[ENUMS]}
                                       for name in holders):
        kind = ENUM_RENAME
    return {"kind": kind, "from": entry.old, "to": entry.new, "table": entry.table, "line": entry.line}


def _ordered(rows: list) -> list:
    order = {kind: position for position, kind in enumerate(KINDS)}
    unique, seen = [], set()
    for row in sorted(rows, key=lambda row: (order[row["kind"]], row["line"])):
        key = (row["kind"], row["from"], row["to"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


__all__ = ["MAP_PATH", "FROM_VERSION", "TABLES", "MapEntry", "RenamesMapError", "read_map", "comment_classes",
           "attach"]
