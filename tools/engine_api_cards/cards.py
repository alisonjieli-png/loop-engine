"""Write the files of one engine API card from a class's surface and documentation.

```text
one class (an engine adapter's ClassReference, its inheritance, its renames and its documentation)
├── api.json        engine_api_surface/v1, written here; every checked line of the documents comes from it
├── README.md       title, the "Use this card when" line, inheritance, description, renames, tutorials, every
│                   section's items with their descriptions, and the sources; a document that would pass
│                   MAXIMUM_DOCUMENT_BYTES continues in members-2.md, members-3.md, ...
├── api_card.py     the shared checker (card_files/api_card.py), the same bytes in every card
├── test_api_card.py the shared test (card_files/test_api_card.py): the documents agree with api.json, and
│                   known-wrong controls (a removed item, a changed default, an extra item, a lost heading)
│                   are each detected
└── component.json  engine_api_card/v1, the contract card, written after the native check (it names the
                    evidence), so the card digest the evidence binds leaves it out
```

The headings are written by the shipped api_card.py itself (loaded from card_files), so a card and its checker
cannot disagree about a format. Nothing here reads the network or runs an engine.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

from .godot_reference import ENUMS, ClassKind, ClassReference

CARD_FILES = Path(__file__).resolve().parent / "card_files"
MODULE_NAME, TEST_NAME = "api_card.py", "test_api_card.py"
API_NAME, COMPONENT_NAME, README_NAME = "api.json", "component.json", "README.md"
CARD_RECORD = "engine_api_card/v1"
#: The form and harness kind a card is served as (component_form/v1): a contract of an engine's API surface.
FORM, KIND = "schema", "contract_schema"
#: The largest document a card writes; the review bound is 256 KiB a file, and a document is cut between items.
MAXIMUM_DOCUMENT_BYTES = 240_000
NO_DESCRIPTION = "*No description in the class reference.*"
#: What a card's text says a kind of class is.
KIND_PHRASES = {ClassKind.OBJECT_CLASS: "the class", ClassKind.BUILTIN_TYPE: "the built-in type",
                ClassKind.GLOBAL_SCOPE: "the global scope"}
#: Documentation notes on a class or an item, in the order a card shows them, and their labels.
NOTE_LABELS = (("deprecated", "Deprecated"), ("experimental", "Experimental"))
KEYWORDS = "keywords"
_MODULE = None


def card_module():
    """The shipped checker, loaded from card_files once: the writer and the package test use the same code."""
    global _MODULE
    if _MODULE is None:
        specification = importlib.util.spec_from_file_location("engine_api_card_module", CARD_FILES / MODULE_NAME)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        _MODULE = module
    return _MODULE


def shared_files() -> dict:
    """{path: bytes} of the files every card carries byte for byte."""
    return {MODULE_NAME: (CARD_FILES / MODULE_NAME).read_bytes(), TEST_NAME: (CARD_FILES / TEST_NAME).read_bytes()}


@dataclass(frozen=True)
class EngineRelease:
    """The pinned engine a card describes: its identity, the build whose surface was read and its sources."""

    name: str  # godot
    title: str  # Godot
    release: str  # 4.7.2-stable, the tag
    version: str  # 4.7.2
    api_version: str  # 4.7, the version a card's job names
    repository: str  # godotengine/godot
    commit: str
    binary_name: str
    binary_sha256: str
    binary_version: str
    docs_address: str  # the documentation of the same version, which $DOCS_URL names
    syntax: str  # api_card.GODOT_SYNTAX or api_card.JAVASCRIPT_SYNTAX
    renames_from_version: str = ""
    #: Where the surface was read, as the Source section names it, and how the header describes that surface.
    surface_source: str = ""
    surface_phrase: str = "the surface the engine itself reports"
    #: The format the reference text was converted from, and the licence of that text.
    text_format: str = ""
    licence: str = "MIT"
    #: The api types whose classes exist only in the engine's editor, and what a card of such a class says.
    editor_api_types: tuple = ()
    editor_note: str = ""
    #: Where the text file was read, when it is not the repository at the tag (a package built from it).
    text_origin: str = ""
    #: The notice file every card carries beside the licence (Apache-2.0 section 4(d)), when there is one.
    notice_file: str = ""

    def identity(self) -> dict:
        return {"name": self.name, "title": self.title, "release": self.release, "version": self.version,
                "api_version": self.api_version, "repository": self.repository, "commit": self.commit,
                "binary": {"name": self.binary_name, "sha256": self.binary_sha256, "version": self.binary_version}}


@dataclass(frozen=True)
class CardSources:
    """Where one card's facts came from: the dump file, the class reference file and the renames map."""

    dump_path: str
    dump_sha256: str
    reference_path: str
    reference_sha256: str
    renames_path: str = ""
    renames_sha256: str = ""


def surface_record(release: EngineRelease, reference: ClassReference, inherits: list, inherited_by: list,
                   renames: list, sources: CardSources) -> dict:
    """api.json: the class's surface as the engine binary reports it, and the renames that hold on it."""
    record = {"record_type": card_module().SURFACE_RECORD, "syntax": release.syntax, "engine": release.identity(),
              "class": reference.name, "kind": reference.kind.value, "api_type": reference.api_type,
              "inherits": list(inherits), "inherited_by": list(inherited_by),
              "dump": {"path": sources.dump_path, "sha256": sources.dump_sha256},
              "sections": {section: reference.sections[section] for section in card_module().SECTIONS}}
    if renames:
        record["renames"] = {"from_version": release.renames_from_version,
                             "source": {"path": sources.renames_path, "sha256": sources.renames_sha256},
                             "entries": [{key: row[key] for key in ("kind", "from", "to")} for row in renames]}
    return record


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def purpose(release: EngineRelease, reference: ClassReference, context) -> str:
    """The "Use this card when" line, written from the class's role (its brief description)."""
    code = card_module().code
    role = context.markdown(reference.documentation["brief"]).replace("\n\n", " ").strip()
    subject = f"{KIND_PHRASES[reference.kind]} {code(reference.name)}"
    line = f"Use this card when writing or checking {release.title} {release.api_version} code that uses {subject}."
    return line + (f" Its role: {role}" if role else " The class reference gives it no brief description.")


def _notes(documentation: dict, context) -> list:
    return [f"**{label}:** {context.markdown(documentation[key]) or label.lower()}"
            for key, label in NOTE_LABELS if key in documentation]


def _item_block(section: str, item: dict, documentation: dict, context, syntax: str) -> str:
    module = card_module()
    parts = [module.ITEM_PREFIX + module.item_line(section, item, syntax)]
    if section == ENUMS:
        for value, value_documentation in zip(item["values"], documentation["values"]):
            parts.append(module.VALUE_PREFIX + module.item_line(module.CONSTANTS, value, syntax))
            parts += _notes(value_documentation, context)
            parts.append(context.markdown(value_documentation["description"]) or NO_DESCRIPTION)
        return "\n\n".join(parts) + "\n\n"
    parts += _notes(documentation, context)
    parts.append(context.markdown(documentation["description"]) or NO_DESCRIPTION)
    return "\n\n".join(parts) + "\n\n"


def _head(api: dict, release: EngineRelease, reference: ClassReference, context) -> str:
    module = card_module()
    code = module.code
    lines = [module.TITLE_PREFIX + module.title_line(api), purpose(release, reference, context)]
    if api["inherits"]:
        lines.append(module.INHERITS_PREFIX + " < ".join(code(name) for name in api["inherits"]))
    if api["inherited_by"]:
        lines.append(module.INHERITED_BY_PREFIX + ", ".join(code(name) for name in api["inherited_by"]))
    lines += _notes(reference.documentation["notes"], context)
    if reference.api_type and reference.api_type in release.editor_api_types:
        lines.append(release.editor_note)
    lines.append(f"{release.title} {release.release}. Every heading below is written from `{API_NAME}`, "
                 f"{release.surface_phrase}; the text under it is the engine's own reference at the same release.")
    brief = context.markdown(reference.documentation["brief"])
    description = context.markdown(reference.documentation["description"])
    lines.append(module.SECTION_PREFIX + "Description")
    lines.append("\n\n".join(text for text in (brief, description) if text) or NO_DESCRIPTION)
    renames = (api.get("renames") or {}).get("entries") or []
    if renames:
        lines.append(module.SECTION_PREFIX + module.renames_heading(api))
        lines.append("\n".join(module.RENAME_PREFIX + module.rename_line(row) for row in renames))
        lines.append(f"From the engine's own project upgrade map (`{api['renames']['source']['path']}` at "
                     f"{release.release}): only the renames whose new name is on this surface, its own or an "
                     "ancestor's, are listed.")
    tutorials = reference.documentation["tutorials"]
    if tutorials:
        lines.append(module.SECTION_PREFIX + "Tutorials")
        lines.append("\n".join(f"- [{context.title(row['title']) or row['address']}]({context.address(row['address'])})"
                               for row in tutorials))
    return "\n\n".join(lines) + "\n\n"


def _source(api: dict, release: EngineRelease, sources: CardSources, copyright_lines: list) -> str:
    module = card_module()
    lines = [module.SECTION_PREFIX + "Source",
             f"- Surface: {release.surface_source}, and checked against the same build (`verification/native.json`).",
             f"- Text: `{sources.reference_path}` of "
             f"{release.text_origin or release.repository} at tag `{release.release}` (commit `{release.commit}`), "
             f"converted from {release.text_format}. " + "".join(f"{line} " for line in copyright_lines) +
             f"{release.licence}, see `UPSTREAM-LICENSE`" +
             (f" and `{release.notice_file}`." if release.notice_file else ".")]
    if api.get("renames"):
        lines.append(f"- Renames: `{sources.renames_path}` at the same commit.")
    lines.append(f"- `{TEST_NAME}` checks that every heading of this card agrees with `{API_NAME}`.")
    return "\n\n".join(lines[:1]) + "\n\n" + "\n".join(lines[1:]) + "\n"


def _body(api: dict, reference: ClassReference, context) -> list:
    """(section, heading block or None, item block) in document order: one row per item."""
    module = card_module()
    rows = []
    for section in module.SECTIONS:
        items = api["sections"][section]
        documentation = reference.documentation["items"][section]
        for index, item in enumerate(items):
            rows.append((section, module.SECTION_PREFIX + module.HEADINGS[section] + "\n\n" if not index else None,
                         _item_block(section, item, documentation[index], context, api["syntax"])))
    return rows


def documents(api: dict, release: EngineRelease, reference: ClassReference, context,
              sources: CardSources, copyright_lines: list, *, maximum: int = MAXIMUM_DOCUMENT_BYTES) -> dict:
    """{document name: text}: README.md alone, or README.md and members-N.md when the class is large."""
    module = card_module()
    head, source, body = _head(api, release, reference, context), _source(api, release, sources, copyright_lines), \
        _body(api, reference, context)
    whole = head + "".join((heading or "") + block for _section, heading, block in body) + source
    if len(whole.encode("utf-8")) <= maximum:
        return {README_NAME: whole}
    parts, current, size, number = [], [], 0, 1
    reserve = len(source.encode("utf-8")) + 400
    budget = maximum - len(head.encode("utf-8")) - reserve
    for section, heading, block in body:
        text = (heading or "") + block
        if current and size + len(text.encode("utf-8")) > budget:
            parts.append(current)
            current, size, number, budget = [], 0, number + 1, maximum - 400
            if heading is None:
                text = module.SECTION_PREFIX + module.HEADINGS[section] + module.CONTINUED + "\n\n" + block
        current.append(text)
        size += len(text.encode("utf-8"))
    parts.append(current)
    names = [README_NAME] + [module.MEMBERS_DOCUMENT.format(number) for number in range(2, len(parts) + 1)]
    pointer = ("This card continues in " + ", ".join(f"`{name}`" for name in names[1:]) +
               ", in order; every document is part of the card.\n\n")
    texts = {README_NAME: head + pointer + "".join(parts[0]) + source}
    for position, name in enumerate(names[1:], start=1):
        texts[name] = (f"Part {position + 1} of the {api['class']} card ({release.title} {release.api_version}); "
                       f"start with `{README_NAME}`.\n\n" + "".join(parts[position]))
    return texts


def card_digest(files: dict) -> str:
    """The digest native evidence binds: every card file's path and SHA-256, except the files written after the
    check (component.json, the evidence itself and the attribution)."""
    rows = sorted((path, hashlib.sha256(data).hexdigest()) for path, data in files.items())
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


def surface_counts(api: dict) -> dict:
    counts = {section: len(api["sections"][section]) for section in card_module().SECTIONS}
    counts["enum_values"] = sum(len(item["values"]) for item in api["sections"][ENUMS])
    return counts


def tags(release: EngineRelease, reference: ClassReference) -> list:
    words = [release.name, f"{release.name} {release.api_version}", "api reference", reference.kind.value.replace(
        "_", " ")]
    if reference.api_type:
        words.append(f"{reference.api_type} api")
    words += [word.strip().lower() for word in reference.documentation["notes"].get(KEYWORDS, "").split(",")]
    unique = []
    for word in words:
        if word and len(word) <= 40 and word not in unique:
            unique.append(word)
    return unique[:16]


def component_card(api: dict, release: EngineRelease, reference: ClassReference, context,
                   files: dict, evidence: dict, *, generator: dict, limits: str) -> dict:
    """component.json (engine_api_card/v1): the small contract card a harness reads first."""
    module = card_module()
    return {"record_type": CARD_RECORD,
            "job": {"engine": release.name, "version": release.api_version, "class": reference.name},
            "title": module.title_line(api), "purpose": purpose(release, reference, context), "form": FORM,
            "kind": KIND, "engine": release.identity(),
            "class": {"name": reference.name, "kind": reference.kind.value, "api_type": reference.api_type,
                      "inherits": api["inherits"]},
            "surface": surface_counts(api),
            "renamed": {"from_version": (api.get("renames") or {}).get("from_version"),
                        "count": len((api.get("renames") or {}).get("entries") or [])},
            "documents": module.documents(files),
            "files": [{"path": path, "sha256": hashlib.sha256(data).hexdigest()} for path, data in sorted(files.items())],
            "verification": {"native": {"state": evidence["state"], "record": "verification/native.json",
                                        "checks": [check["name"] for check in evidence["checks"]],
                                        "engine": evidence["engine"], "card_digest": evidence["card_digest"]},
                             "tests": TEST_NAME},
            "tags": tags(release, reference), "limits": limits, "generator": dict(generator),
            "authoring": "generated_from_the_engine_binary_and_its_class_reference"}


__all__ = ["EngineRelease", "CardSources", "card_module", "shared_files", "surface_record", "json_bytes", "purpose",
           "documents", "card_digest", "component_card", "tags", "FORM", "KIND", "API_NAME", "COMPONENT_NAME",
           "README_NAME", "MODULE_NAME", "TEST_NAME", "MAXIMUM_DOCUMENT_BYTES"]
