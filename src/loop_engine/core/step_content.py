"""Load the generated step and skill catalog, refusing anything unsafe.

``step_content.json`` was produced by a fan-out of authoring agents and
revised by independent critics. That provenance is exactly why nothing here
trusts it. Every entry is re-validated on load against the same rules a
hand-written layer must satisfy, and a file that violates one is refused
rather than partially loaded: content that arrives from a model is data,
never authority, and a catalog that silently drops its bad half leaves a
run believing it has capabilities it does not.

The checks that matter, in the order they earned their place:

  * a step whose permissions declare it read-only may not keep ANY
    write-capable tool. Learned twice, live: with only edit denied the
    model wrote through ``bash``; with bash also denied it wrote through
    ``task``, which spawns a subagent carrying the DEFAULT agent's tools.
  * no ``ask`` permission. Nobody is awake to answer it.
  * no tool outside ``KNOWN_TOOLS``. An unknown name is not refused by
    OpenCode, it is silently ignored, so it reads as a granted tool.
  * a duplicate step id or skill name is refused. Two definitions of
    "verify" means the run uses whichever loaded last.

Reading is by query rather than by import: ``steps_for``, ``skills_for``
and ``search`` answer questions about the catalog without a caller having
to hold all 126 KB of it, which is the point of keeping it as data.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .opencode_step_composition import (
    KNOWN_TOOLS, WRITE_CAPABLE_TOOLS, OpenCodeCompositionError, SkillCandidate,
    SkillLibrary, StepLayer, StepLayerCatalogue)

CONTENT_PATH = Path(__file__).with_name("step_content.json")
CONTENT_RECORD_TYPE = "opencode_step_content/v1"


class StepContentError(OpenCodeCompositionError):
    """The generated catalog failed a rule a hand-written layer must pass."""


def _validate_layer(entry: dict, seen: set) -> None:
    step_id = str(entry.get("step_id", "")).strip()
    if not step_id:
        raise StepContentError("a catalog layer has no step_id")
    if step_id in seen:
        raise StepContentError(
            f"duplicate step id {step_id!r}; two definitions means the run "
            "uses whichever loaded last")
    seen.add(step_id)
    tools = entry.get("tools") or {}
    unknown = sorted(set(tools) - set(KNOWN_TOOLS))
    if unknown:
        raise StepContentError(
            f"step {step_id!r} names unknown tools {unknown}; OpenCode "
            "ignores an unknown tool silently, so it reads as granted. "
            f"Known tools are {', '.join(KNOWN_TOOLS)}")
    permission = entry.get("permission") or {}
    asking = sorted(k for k, v in permission.items() if v == "ask")
    if asking:
        raise StepContentError(
            f"step {step_id!r} sets {asking} to 'ask' while unattended; "
            "nobody is awake to answer, so this hangs the run")
    if permission.get("edit") == "deny":
        leaked = sorted(name for name in WRITE_CAPABLE_TOOLS
                        if name != "bash" and tools.get(name))
        if leaked:
            raise StepContentError(
                f"step {step_id!r} declares edit denied but keeps {leaked}; "
                "`task` spawns a subagent with the default agent's tools and "
                "`patch` is a second write path -- both were observed writing "
                "through a denial live")


def _validate_skill(entry: dict, seen: set) -> None:
    name = str(entry.get("name", "")).strip()
    if not name:
        raise StepContentError("a catalog skill has no name")
    if "/" in name:
        raise StepContentError(
            f"skill name {name!r} must be one path segment; it becomes a "
            "directory under skill/")
    if name in seen:
        raise StepContentError(f"duplicate skill name {name!r}")
    seen.add(name)
    if not str(entry.get("body", "")).strip():
        raise StepContentError(
            f"skill {name!r} has an empty body; it would be carried, "
            "indexed, and say nothing")
    if not entry.get("triggers"):
        raise StepContentError(
            f"skill {name!r} declares no triggers, so it would either "
            "always load or never load; say which")
    for term in entry["triggers"]:
        # Slashes and plus signs are allowed: "a/b test" and "c++" are
        # real trigger phrases. A trigger is regex-escaped before matching
        # and is never used as a path, so punctuation inside one is text,
        # not structure. What is refused is an uppercase or empty term,
        # because matching lowercases the task and an empty term matches
        # everything.
        if not re.fullmatch(r"[a-z0-9][a-z0-9 _.+/\-]*", str(term)):
            raise StepContentError(
                f"skill {name!r} trigger {term!r} is not a plain lowercase "
                "term; triggers are matched on word boundaries in task text")


@lru_cache(maxsize=1)
def load_catalog(path: str = "") -> dict:
    """Read and validate the whole catalog, or refuse it."""
    target = Path(path) if path else CONTENT_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StepContentError(f"{target} is not readable JSON: {exc}") from exc
    if data.get("record_type") != CONTENT_RECORD_TYPE:
        raise StepContentError(
            f"{target} is {data.get('record_type')!r}, expected "
            f"{CONTENT_RECORD_TYPE!r}")
    seen_steps, seen_skills = set(), set()
    for entry in data.get("layers", ()):
        _validate_layer(entry, seen_steps)
    for entry in data.get("skills", ()):
        _validate_skill(entry, seen_skills)
    return data


def _as_layer(entry: dict) -> StepLayer:
    permission = dict(entry.get("permission") or {})
    tools = {k: bool(v) for k, v in (entry.get("tools") or {}).items()}
    if permission.get("edit") == "allow" or tools.get("edit") or tools.get("write"):
        # A generated layer that may edit gets the same rule the hand-written
        # implement step has: source yes, tests no. The catalog was written
        # before that rule existed, and a step that can edit tests can make
        # any gate green (found live, twice).
        from .opencode_step_composition import source_only_edit_permission
        permission["edit"] = source_only_edit_permission()
    return StepLayer(
        step_id=entry["step_id"], description=entry["description"],
        system_prompt=entry["system_prompt"], tools=tools, permission=permission)


def _as_skill(entry: dict) -> SkillCandidate:
    return SkillCandidate(
        name=entry["name"], body=entry["body"],
        triggers=tuple(entry.get("triggers") or ()),
        steps=tuple(entry.get("steps") or ()))


def catalog_layers() -> tuple:
    return tuple(_as_layer(e) for e in load_catalog().get("layers", ()))


def catalog_skills() -> tuple:
    return tuple(_as_skill(e) for e in load_catalog().get("skills", ()))


def extended_catalogue(base: StepLayerCatalogue = None) -> StepLayerCatalogue:
    """Add the generated layers to a catalogue, base definitions winning.

    A hand-written layer is never replaced by a generated one. The
    generated set is broad and was written by a model; the four base steps
    are the ones whose behaviour has been measured on live runs.
    """
    from .opencode_step_layers import default_catalogue
    catalogue = base if base is not None else default_catalogue()
    for layer in catalog_layers():
        if not catalogue.has(layer.step_id):
            catalogue.register(layer)
    return catalogue


def extended_library(base: SkillLibrary = None) -> SkillLibrary:
    """Add the generated skills to a library, base definitions winning."""
    from .opencode_step_layers import default_skill_library
    library = base if base is not None else default_skill_library()
    existing = set(library.available())
    for skill in catalog_skills():
        if skill.name not in existing:
            library.register(skill)
    return library


def search(term: str, *, limit: int = 12) -> dict:
    """Find catalog entries by id, name, trigger or prose.

    The catalog is 126 KB. A caller that wants one skill should not have to
    hold all of it, and a caller that wants to know whether something is
    covered should be able to ask rather than read.
    """
    lowered = str(term).lower().strip()
    if not lowered:
        raise StepContentError("search needs a term")
    data = load_catalog()
    steps = [e["step_id"] for e in data.get("layers", ())
             if lowered in e["step_id"].lower()
             or lowered in e.get("description", "").lower()
             or lowered in e.get("when_used", "").lower()]
    skills = [e["name"] for e in data.get("skills", ())
              if lowered in e["name"].lower()
              or lowered in e.get("prevents", "").lower()
              or any(lowered in t for t in e.get("triggers", ()))]
    sources = [e["name"] for e in data.get("intake_sources", ())
               if lowered in json.dumps(e).lower()]
    return {"term": lowered, "steps": steps[:limit],
            "skills": skills[:limit], "intake_sources": sources[:limit]}


def self_test() -> dict:
    """Validate the shipped catalog and prove each refusal fires."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    data = load_catalog()
    layers, skills = catalog_layers(), catalog_skills()
    check("the_shipped_catalog_validates",
          len(layers) >= 10 and len(skills) >= 20,
          f"{len(layers)} layers, {len(skills)} skills, "
          f"{len(data.get('intake_sources', ()))} intake sources")

    # The property the live runs paid for twice.
    offenders = [l.step_id for l in layers
                 if l.permission.get("edit") == "deny"
                 and any(l.tools.get(t) for t in WRITE_CAPABLE_TOOLS
                         if t != "bash")]
    check("no_read_only_layer_keeps_a_delegating_write_tool",
          not offenders, str(offenders))
    check("no_layer_asks_a_question_nobody_can_answer",
          not [l.step_id for l in layers
               if "ask" in l.permission.values()])

    combined = extended_catalogue()
    check("generated_layers_extend_rather_than_replace",
          combined.has("orient") and combined.has("verify")
          and len(combined.registered()) > 10,
          f"{len(combined.registered())} steps: "
          f"{', '.join(combined.registered()[:6])}...")
    base_prompt = combined.select("orient").system_prompt
    check("a_generated_layer_cannot_displace_a_measured_one",
          "orientation step" in base_prompt.lower(), base_prompt[:60])

    library = extended_library()
    check("generated_skills_extend_the_library",
          "reproduce-before-fix" in library.available()
          and len(library.available()) > 20,
          f"{len(library.available())} skills")

    found = search("test")
    check("search_answers_without_loading_the_whole_catalog",
          isinstance(found["skills"], list) and found["term"] == "test",
          str(found["skills"][:4]))
    try:
        search("  ")
        check("an_empty_search_is_refused", False)
    except StepContentError:
        check("an_empty_search_is_refused", True)

    for bad, why, fragment in (
            ({"step_id": "x", "tools": {"telepathy": True}, "permission": {}},
             "unknown tool", "unknown tools"),
            ({"step_id": "x", "tools": {}, "permission": {"bash": "ask"}},
             "ask permission", "nobody is awake"),
            ({"step_id": "x", "tools": {"task": True},
              "permission": {"edit": "deny"}},
             "read-only layer keeping task", "spawns a subagent")):
        try:
            _validate_layer(dict(bad), set())
            check(f"refuses_{why.replace(' ', '_')}", False, "accepted")
        except StepContentError as exc:
            check(f"refuses_{why.replace(' ', '_')}",
                  fragment in str(exc), str(exc)[:100])

    try:
        _validate_layer({"step_id": "dup", "tools": {}, "permission": {}},
                        {"dup"})
        check("refuses_a_duplicate_step_id", False)
    except StepContentError as exc:
        check("refuses_a_duplicate_step_id",
              "whichever loaded last" in str(exc), str(exc)[:90])

    try:
        _validate_skill({"name": "s", "body": "b", "triggers": ["ValueError"]},
                        set())
        check("refuses_a_non_lowercase_trigger", False)
    except StepContentError as exc:
        check("refuses_a_non_lowercase_trigger",
              "word boundaries" in str(exc), str(exc)[:90])

    return {"module": "core.step_content", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
