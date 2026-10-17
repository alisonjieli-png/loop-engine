"""Turn a Python library's introspected surface into card units: one card per public function and class, and one per
documented public method or property of a carded class.

```text
the read result of python_introspect.py (one sandboxed import of the pinned wheels)
├── a module whose import touched the network, started a process or wrote a file: its objects are refused by name
│   (the library's first module doing so stops the whole release)
├── an object defined in another distribution (a re-export): left to that distribution's cards and counted
├── an object whose defining file is not the tag's bytes, or names another licence: refused by name
├── a class card: the constructor, the members the class itself holds or takes from a base no card describes
│   (each method and property with its first paragraph), constants and fields; its carded and outside ancestors
│   in method resolution order; the class docstring in full
├── a member card: one documented method or property of a carded class, its whole docstring (a member several
│   carded classes take from one base is carded once, under the first)
├── a function card: its signature and its whole docstring
└── the text: an object's own docstring, quoted verbatim in a fenced block, accepted when at least
    TRACED_SHARE of its lines occur in the release's licence-cleared source files at the tag (python_wheels.Corpus)
```

Characters a reader cannot see are written as escapes (\\u200b in a fenced block, &#x200B; in a sentence), and an
HTML comment opener as \\x3c!-- (the same string in Python), so the qualification safety rules see no hidden text.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .bbcode import invisible
from .godot_reference import SECTIONS, ClassKind, ClassReference

#: The share of a docstring's counted lines that must occur in the release's own source files.
TRACED_SHARE = 0.9
#: A docstring a card is written for holds at least this many words.
MINIMUM_WORDS = 3
#: The longest first paragraph a class card writes for one member; a longer one is cut between words.
MAXIMUM_SUMMARY = 400
NO_DOCSTRING = "*No docstring.*"
ELLIPSIS = "…"
CLASS, FUNCTION, METHOD, PROPERTY, FIELD, CONSTANT = "class", "function", "method", "property", "field", "constant"
EVENT_REFUSALS = {"network": "import_touches_network", "process": "import_starts_process",
                  "write": "import_writes_files"}
COMMENT_OPENER, COMMENT_WRITTEN = "<!--", "\\x3c!--"
_CONTROL_CATEGORY = "Cc"
ALLOWED_CONTROLS = ("\n", "\t")
FUNCTIONS = "functions"
BUILTINS_PREFIX = "builtins."


@dataclass(frozen=True)
class PyDocText:
    """The card writer's text interface for Python docstrings: every text is already Markdown when it reaches the
    writer (a sentence, or a docstring fenced as text), so markdown() returns it as it is."""

    no_description: str = NO_DOCSTRING

    def markdown(self, text: "str | None") -> str:
        return text or ""

    def title(self, text: str) -> str:
        return text

    def address(self, address: str) -> str:
        return address


def _hidden(character: str) -> bool:
    return invisible(character) or (unicodedata.category(character) == _CONTROL_CATEGORY and
                                    character not in ALLOWED_CONTROLS)


def _escape(character: str) -> str:
    code = ord(character)
    return f"\\x{code:02x}" if code < 0x100 else f"\\u{code:04x}" if code <= 0xFFFF else f"\\U{code:08x}"


def fenced(text: str) -> str:
    """A docstring verbatim as a fenced text block, fenced with more backticks than any run it holds; hidden and
    control characters are escapes, a carriage return ends a line, an HTML comment opener is \\x3c!--."""
    body = "".join(_escape(character) if _hidden(character) and character != "\r" else character
                   for character in text.replace("\r\n", "\n").replace("\r", "\n"))
    body = body.replace(COMMENT_OPENER, COMMENT_WRITTEN)
    runs = [len(run) for run in re.findall(r"`+", body)]
    fence = "`" * max(3, max(runs, default=0) + 1)
    return f"{fence}text\n{body}\n{fence}"


def sentence(text: str, limit: int = MAXIMUM_SUMMARY) -> str:
    """Prose on one line: the first paragraph of a docstring, its lines joined, cut between words, hidden characters
    as character references, a comment opener as &lt;!--, a leading # or > escaped so it is not a block."""
    paragraph = " ".join(str(text or "").strip().split("\n\n", 1)[0].split())
    if len(paragraph) > limit:
        cut = paragraph[:limit].rsplit(" ", 1)[0]
        paragraph = cut + ELLIPSIS
    paragraph = "".join(f"&#x{ord(character):04X};" if _hidden(character) else character for character in paragraph)
    paragraph = paragraph.replace(COMMENT_OPENER, "&lt;!--")
    if paragraph[:1] in ("#", ">", "=", "-", "+", "*", "|"):
        paragraph = "\\" + paragraph
    return paragraph


def documented(text: "str | None") -> bool:
    return bool(text) and len(str(text).split()) >= MINIMUM_WORDS


def display(key: str) -> str:
    """How a card names a class outside the library's cards: its module and qualified name, a builtin bare."""
    return key[len(BUILTINS_PREFIX):] if key.startswith(BUILTINS_PREFIX) else key


def _signature_item(name: str, signature: "dict | None", qualifiers=()) -> dict:
    item = {"name": name, "params": None if signature is None else signature["params"]}
    returned = None if signature is None else signature.get("returns")
    item["returns"] = {"type": returned} if returned else None
    if qualifiers:
        item["qualifiers"] = list(qualifiers)
    return item


def member_item(row: dict) -> tuple:
    """(section, api.json item) of one member record."""
    if row["kind"] == METHOD:
        return "methods", _signature_item(row["name"], row.get("signature"), row.get("qualifiers", ()))
    if row["kind"] == CONSTANT:
        return "constants", {"name": row["name"], "value": row["value"]}
    item = {"name": row["name"], "kind": row["kind"]}
    if row.get("type"):
        item["type"] = row["type"]
    if row.get("qualifiers"):
        item["qualifiers"] = list(row["qualifiers"])
    if "default" in row:
        item["default"] = row["default"]
    return "members", item


def empty_sections() -> tuple:
    names = tuple(SECTIONS) + (FUNCTIONS,)
    return {name: [] for name in names}, {name: [] for name in names}


@dataclass
class Unit:
    """One card before it is written: the reference the card writer reads, where the native check finds the object,
    and which files its surface and its text came from."""

    name: str
    reference: ClassReference
    location: dict  # module, qualname, member, ancestors (keys of the listed ancestors)
    surface_file: str  # the wheel file the object is defined in
    text_file: "str | None"  # the repository file most of its text is found in
    text_share: float
    inherits: list
    owner_key: str = ""


class Builder:
    """Everything one release's units are decided from: the read result, the corpus and the wheel's proofs."""

    def __init__(self, result: dict, *, proven: dict, members: dict, corpus, excluded: dict, refusal) -> None:
        self.result, self.proven, self.members, self.corpus = result, proven, members, corpus
        self.excluded = excluded  # repository path -> licence reason
        self.refusal = refusal
        self.refusals = []
        self.counts = {"objects": 0, "re_exported": 0, "classes": 0, "functions": 0, "members": 0}

    # -- one text --------------------------------------------------------------------------------------------------
    def traced(self, name: str, text: "str | None") -> "tuple | None":
        """(share, file) when the text occurs in the release's sources, else None with the refusal recorded."""
        share, counted, holder = self.corpus.trace(text)
        if share < TRACED_SHARE:
            self.refusals.append(self.refusal("text_not_traced_to_the_tag", name,
                                              f"{share:.2f} of {counted} lines found in the sources at the tag"))
            return None
        return share, holder

    def surface_file(self, name: str, source: "dict | None") -> "str | None":
        """The wheel file an object is defined in, when it is the tag's bytes (or a compiled module of the wheel)
        and its licence is the repository's; else None with the refusal recorded."""
        if not source or source.get("root") != 0 or source.get("file") not in self.members:
            self.refusals.append(self.refusal("source_unreadable", name, "no defining file in the wheel"))
            return None
        path = source["file"]
        if source.get("compiled"):
            return path
        repository_path = self.proven.get(path)
        if repository_path is None:
            self.refusals.append(self.refusal("published_source_differs", name, path))
            return None
        if repository_path in self.excluded:
            self.refusals.append(self.refusal(self.excluded[repository_path], name, repository_path))
            return None
        return path

    # -- the population --------------------------------------------------------------------------------------------
    def units(self, top_module: str) -> tuple:
        """({card name: Unit}, chains, children): every card of the release, and its refusals in self.refusals."""
        tainted = {}
        for event in self.result.get("events", ()):
            if event.get("kind") in EVENT_REFUSALS:
                tainted.setdefault(event["module"], EVENT_REFUSALS[event["kind"]])
        for module in self.result.get("modules", ()):
            if not module.get("ok"):
                self.refusals.append(self.refusal("import_failed", module["name"], module.get("error", "")))
        objects = [row for row in self.result["objects"] if not row.get("error")]
        for row in self.result["objects"]:
            if row.get("error"):
                self.refusals.append(self.refusal("source_unreadable", row["path"], row["error"]))
        owned = [row for row in objects if (row.get("source") or {}).get("root") == 0]
        self.counts.update(objects=len(objects), re_exported=len(objects) - len(owned))
        carded = {row["key"]: row["path"] for row in owned if row["kind"] == CLASS}
        units, seen_members = {}, set()
        for row in owned:
            reason = next((reason for prefix, reason in tainted.items()
                           if row["path"] == prefix or row["path"].startswith(prefix + ".")
                           or row["module"] == prefix), None)
            if reason:
                self.refusals.append(self.refusal(reason, row["path"], "the import or read of its module did it"))
                continue
            if row["kind"] == FUNCTION:
                unit = self.function_unit(row)
                if unit is not None:
                    units[unit.name] = unit
                continue
            unit, members = self.class_units(row, carded, seen_members)
            if unit is not None:
                units[unit.name] = unit
            for member in members:
                units[member.name] = member
        chains = {name: unit.inherits for name, unit in units.items()}
        children = {name: [] for name in units}
        for name, unit in units.items():
            if unit.reference.kind == ClassKind.OBJECT_CLASS and unit.inherits and unit.inherits[0] in children:
                children[unit.inherits[0]].append(name)
        return units, chains, {name: sorted(rows) for name, rows in children.items()}

    def function_unit(self, row: dict) -> "Unit | None":
        name = row["path"]
        surface = self.surface_file(name, row.get("source"))
        if surface is None:
            return None
        if not documented(row.get("doc")):
            self.refusals.append(self.refusal("no_documentation", name, "no docstring of three words"))
            return None
        traced = self.traced(name, row["doc"])
        if traced is None:
            return None
        sections, documents = empty_sections()
        sections[FUNCTIONS].append(_signature_item(row["qualname"], row.get("signature"), row.get("qualifiers", ())))
        documents[FUNCTIONS].append({"description": fenced(row["doc"])})
        reference = ClassReference(name, None, None, ClassKind.FUNCTION, sections, {
            "brief": sentence(row["doc"]), "description": "", "tutorials": [], "notes": {}, "items": documents})
        self.counts["functions"] += 1
        return Unit(name, reference, {"module": row["module"], "qualname": row["qualname"]}, surface, traced[1],
                    traced[0], [])

    def class_units(self, row: dict, carded: dict, seen_members: set) -> tuple:
        name = row["path"]
        surface = self.surface_file(name, row.get("source"))
        if surface is None:
            return None, []
        folded = {row["key"]} | {entry["key"] for entry in row.get("mro", ()) if entry.get("owned") and
                                 entry["key"] not in carded}
        listed = [entry for entry in row.get("mro", ()) if entry["key"] in carded or not entry.get("owned")]
        inherits = [carded.get(entry["key"]) or display(entry["key"]) for entry in listed]
        members = [member for member in row.get("members", ()) if member["owner"] in folded]
        sections, documents = empty_sections()
        sections["constructors"].append({"name": row["qualname"], "params": (row.get("constructor") or {}).get(
            "params") if row.get("constructor") is not None else None})
        documents["constructors"].append({"description": ""})
        member_units = []
        for member in members:
            section, item = member_item(member)
            sections[section].append(item)
            documents[section].append({"description": sentence(member["doc"]) if documented(member.get("doc"))
                                       else ""})
            card = self.member_unit(row, member, seen_members)
            if card is not None:
                member_units.append(card)
        class_doc = row.get("doc") if documented(row.get("doc")) else None
        if class_doc is None and not any(documented(member.get("doc")) for member in members):
            self.refusals.append(self.refusal("no_documentation", name, "no docstring and no documented member"))
            return None, member_units
        share, holder = 1.0, self.proven.get(surface)
        if class_doc is not None:
            traced = self.traced(name, class_doc)
            if traced is None:
                return None, member_units
            share, holder = traced[0], traced[1] or holder
        reference = ClassReference(name, inherits[0] if inherits else None, None, ClassKind.OBJECT_CLASS, sections, {
            "brief": sentence(class_doc) if class_doc else "", "description": fenced(class_doc) if class_doc else "",
            "tutorials": [], "notes": {}, "items": documents})
        self.counts["classes"] += 1
        location = {"module": row["module"], "qualname": row["qualname"],
                    "ancestors": [entry["key"] for entry in listed]}
        return Unit(name, reference, location, surface, holder, share, inherits, row["key"]), member_units

    def member_unit(self, row: dict, member: dict, seen: set) -> "Unit | None":
        if member["kind"] not in (METHOD, PROPERTY) or not documented(member.get("doc")):
            return None
        identity = (member["owner"], member["name"])
        if identity in seen:
            return None
        seen.add(identity)
        name = f"{row['path']}.{member['name']}"
        surface = self.surface_file(name, member.get("source") or row.get("source"))
        if surface is None:
            return None
        traced = self.traced(name, member["doc"])
        if traced is None:
            return None
        section, item = member_item(member)
        sections, documents = empty_sections()
        sections[section].append(item)
        documents[section].append({"description": fenced(member["doc"])})
        kind = ClassKind.METHOD if member["kind"] == METHOD else ClassKind.PROPERTY
        reference = ClassReference(name, None, None, kind, sections, {
            "brief": sentence(member["doc"]), "description": "", "tutorials": [], "notes": {}, "items": documents})
        self.counts["members"] += 1
        return Unit(name, reference, {"module": row["module"], "qualname": row["qualname"], "member": member["name"]},
                    surface, traced[1], traced[0], [], member["owner"])


__all__ = ["PyDocText", "Builder", "Unit", "fenced", "sentence", "documented", "member_item", "TRACED_SHARE",
           "NO_DOCSTRING"]
