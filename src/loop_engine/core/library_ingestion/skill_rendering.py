"""Render an imported skill or instruction file into its native files.

For a skill, the body of the source file is kept byte for byte. The
frontmatter is rewritten to the fields the Agent Skills specification
allows: name, description, license, compatibility, allowed-tools and
metadata. Fields the specification does not allow move into metadata under
an upstream prefix; the licence is written as the SPDX expression of the
licence evidence; the source repository, commit, path and digest and a note
of the change are written into metadata, so attribution travels inside the
file; and the licence file travels beside SKILL.md. An instruction file is
copied verbatim to its native path with its licence file beside it.
Rendering refuses, with a named reason, what cannot become a valid file.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from .rendering_types import RenderedPackage, RenderRefused

SKILL_FIELDS = ("name", "description", "license", "compatibility", "allowed-tools", "metadata")
MAXIMUM_NAME_CHARACTERS = 64
MAXIMUM_DESCRIPTION_CHARACTERS = 1024
MAXIMUM_COMPATIBILITY_CHARACTERS = 500
CHANGE_NOTE = ("Baltor rewrote the frontmatter to the Agent Skills fields and moved other fields "
               "into metadata; the body is unchanged.")
_DELIMITER = re.compile(r"---[ \t]*\r?\n")
_HEADING = re.compile(r"^#[ \t]+(.+?)[ \t#]*$", re.M)


@dataclass(frozen=True)
class ParsedSkill:
    frontmatter: dict
    body: str


def parse_skill(text: str) -> ParsedSkill:
    """Split frontmatter from body. The body is everything after the closing line, unchanged."""
    opening = _DELIMITER.match(text)
    if not opening:
        raise RenderRefused("frontmatter_missing", "the file does not open with a frontmatter block")
    position = opening.end()
    closing = None
    for match in re.finditer(r"^---[ \t]*(?:\r?\n|\Z)", text[position:], re.M):
        closing = match
        break
    if closing is None:
        raise RenderRefused("frontmatter_invalid", "the frontmatter block is not closed")
    import yaml

    try:
        values = yaml.safe_load(text[position:position + closing.start()])
    except yaml.YAMLError:
        raise RenderRefused("frontmatter_invalid", "the frontmatter is not valid YAML") from None
    if not isinstance(values, dict):
        raise RenderRefused("frontmatter_invalid", "the frontmatter is not a mapping")
    return ParsedSkill(values, text[position + closing.end():])


def normalized_name(value) -> str:
    """Lower case letters, digits and single inner hyphens, at most 64 characters."""
    if not isinstance(value, str) or not value.strip():
        raise RenderRefused("name_invalid", "the skill names no name")
    name = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not name or len(name) > MAXIMUM_NAME_CHARACTERS:
        raise RenderRefused("name_invalid", f"{value[:80]!r} cannot become a valid skill name")
    return name


def _text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and all(isinstance(item, (str, int, float, bool)) for item in value):
        return ", ".join(str(item) for item in value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def first_heading(body: str) -> "str | None":
    match = _HEADING.search(body)
    if not match:
        return None
    heading = re.sub(r"[*_`]", "", match.group(1)).strip()
    return heading[:120] or None


def _dump(values: dict) -> str:
    import yaml

    text = yaml.safe_dump(values, sort_keys=False, allow_unicode=True, width=1_000_000,
                          default_flow_style=False)
    if any(line.strip() == "---" for line in text.splitlines()):
        raise RenderRefused("frontmatter_invalid", "a value would close the frontmatter early")
    return text


def render_skill(parsed: ParsedSkill, provenance, *, licence_file, notice_files=()) -> RenderedPackage:
    """One skill as SKILL.md with Agent Skills frontmatter, plus its licence and notice files."""
    upstream = parsed.frontmatter
    name = normalized_name(upstream.get("name"))
    description = upstream.get("description")
    if not isinstance(description, str) or not description.strip():
        raise RenderRefused("description_missing", "the skill has no description")
    description = description.strip()
    if len(description) > MAXIMUM_DESCRIPTION_CHARACTERS:
        raise RenderRefused("description_too_long", f"{len(description)} characters")
    rendered = {"name": name, "description": description, "license": provenance.spdx}
    changes = ["frontmatter_rewritten_to_agent_skills_fields", "attribution_metadata_added"]
    if "compatibility" in upstream:
        compatibility = _text(upstream["compatibility"]).strip()
        if len(compatibility) > MAXIMUM_COMPATIBILITY_CHARACTERS:
            raise RenderRefused("compatibility_too_long", f"{len(compatibility)} characters")
        if compatibility:
            rendered["compatibility"] = compatibility
    if upstream.get("allowed-tools") not in (None, ""):
        tools = upstream["allowed-tools"]
        if isinstance(tools, (list, tuple)):
            tools = " ".join(str(tool) for tool in tools)
        if not isinstance(tools, str):
            raise RenderRefused("frontmatter_invalid", "allowed-tools is neither text nor a list")
        rendered["allowed-tools"] = tools.strip()
    metadata = {}
    if isinstance(upstream.get("metadata"), dict):
        metadata.update({str(key): _text(value) for key, value in upstream["metadata"].items()})
    elif upstream.get("metadata") is not None:
        metadata["upstream-metadata"] = _text(upstream["metadata"])
    moved = [key for key in upstream if key not in SKILL_FIELDS]
    for key in moved:
        metadata[f"upstream-{key}"] = _text(upstream[key])
    if moved:
        changes.append("upstream_fields_moved_to_metadata")
    if str(upstream.get("name")) != name:
        metadata["upstream-name"] = str(upstream.get("name"))
        changes.append("name_normalized")
    if upstream.get("license") not in (None, "", provenance.spdx):
        metadata["upstream-license"] = _text(upstream["license"])
    licence_name = PurePosixPath(licence_file[0]).name if licence_file else ""
    metadata.update({
        "baltor-source-repository": f"{provenance.origin_host}/{provenance.repository}",
        "baltor-source-commit": provenance.immutable_revision,
        "baltor-source-path": provenance.path,
        "baltor-source-sha256": provenance.source_digest,
        "baltor-licence-file": licence_name,
        "baltor-changes": CHANGE_NOTE})
    rendered["metadata"] = metadata
    text = "---\n" + _dump(rendered) + "---\n" + parsed.body
    files = [(f"{name}/SKILL.md", text.encode("utf-8"))]
    if licence_file:
        files.append((f"{name}/{licence_name}", licence_file[1]))
    for path, data in notice_files:
        files.append((f"{name}/{PurePosixPath(path).name}", data))
    title = first_heading(parsed.body) or name.replace("-", " ").capitalize()
    return RenderedPackage(name, f"{name}/SKILL.md", tuple(files), tuple(changes), title)


_NATIVE_PATHS = {"copilot_instructions": ".github/instructions/{name}.instructions.md",
                 "cursor_rules": ".cursor/rules/{name}.mdc"}


def render_instruction(text: str, provenance, native_format: str, name: str, licence_file,
                       notice_files=()) -> RenderedPackage:
    """An instruction file copied verbatim to its native path, its licence file kept beside it."""
    if native_format not in _NATIVE_PATHS:
        raise RenderRefused("render_failed", f"{native_format} is not an instruction format")
    safe = normalized_name(name)
    if _DELIMITER.match(text):
        try:
            values = parse_skill(text).frontmatter
        except RenderRefused:
            raise RenderRefused("instruction_frontmatter_invalid", "the frontmatter does not parse") from None
        scope = values.get("applyTo", values.get("globs"))
        if scope is not None and not isinstance(scope, (str, list)):
            raise RenderRefused("instruction_frontmatter_invalid", "the file scope is neither text nor a list")
    main = _NATIVE_PATHS[native_format].format(name=safe)
    files = [(main, text.encode("utf-8"))]
    if licence_file:
        files.append((f"licenses/{safe}/{PurePosixPath(licence_file[0]).name}", licence_file[1]))
    for path, data in notice_files:
        files.append((f"licenses/{safe}/{PurePosixPath(path).name}", data))
    body = parse_skill(text).body if _DELIMITER.match(text) else text
    title = first_heading(body) or safe.replace("-", " ").capitalize()
    return RenderedPackage(safe, main, tuple(files), ("copied_verbatim",), title)
