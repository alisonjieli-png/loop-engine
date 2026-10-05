"""Check that this editable Godot project parses and that every resource it references is present.

project/ holds the demo project's text files (scenes, resources, scripts, shaders, import settings) byte for
byte; creative.json lists its media files (images, sounds, fonts, models), which creative_fetch.py downloads into
project/ at their recorded SHA-256. This check reads project.godot (Godot's ConfigFile text), the main scene it
names, and every quoted res:// path written in the project's text files, and reports each path that is neither a
file in project/ nor a media file the manifest pins. It reads text only and runs nothing.

    python godot_project_check.py          the project beside this file; prints each problem, exit status 1

A path Godot builds at run time (a format string, a folder) is not a file reference and is not checked; paths
under res://.godot/ are the editor's import cache, which Godot writes itself.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
import sys

HERE = Path(__file__).resolve().parent
PROJECT_FOLDER = HERE / "project"
MANIFEST = HERE / "creative.json"
#: The text files whose quoted res:// paths are references (Godot scenes, resources, scripts, shaders, project and
#: import settings, C# scripts and translations).
REFERENCE_SUFFIXES = (".tscn", ".tres", ".gd", ".godot", ".gdshader", ".gdshaderinc", ".import", ".cfg", ".cs",
                      ".material", ".escn")
_QUOTED = re.compile(r"""["'](res://[^"'\n]*)["']""")
_UID = re.compile(r"""uid=["'](uid://[A-Za-z0-9]+)["']""")
_SECTION = re.compile(r"\[([^\]]+)\]\s*$")
_KEY = re.compile(r"([^=\s][^=]*?)\s*=\s*(.*)$")


def read_config(text: str) -> dict:
    """{section: {key: raw value}} of a Godot ConfigFile text such as project.godot; keys before any section
    are under the empty section name. A line that is neither is refused with its number."""
    sections, current = {"": {}}, ""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        section = _SECTION.match(line)
        if section:
            current = section.group(1).strip()
            sections.setdefault(current, {})
            continue
        pair = _KEY.match(line)
        if not pair:
            raise ValueError(f"line {index} is neither a section nor a key")
        value = pair.group(2)
        # A value may continue on the next lines until its brackets close (arrays, dictionaries, strings).
        while _open_brackets(value) > 0 and index < len(lines):
            value += "\n" + lines[index]
            index += 1
        sections[current][pair.group(1).strip()] = value.strip()
    return sections


def _open_brackets(value: str) -> int:
    depth, quoted, escaped = 0, False, False
    for character in value:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "([{":
            depth += 1
        elif character in ")]}":
            depth -= 1
    return depth + (1 if quoted else 0)


def unquoted(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def main_scene(config: dict) -> "str | None":
    """The run/main_scene of the application section: a res:// path or a uid:// identity."""
    value = config.get("application", {}).get("run/main_scene")
    return unquoted(value) if value else None


def text_files(folder) -> list:
    folder = Path(folder)
    return sorted(path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in REFERENCE_SUFFIXES
                  and ".godot" not in path.relative_to(folder).parts[:-1])


def is_file_reference(path: str) -> bool:
    """A res:// path naming one file: not the editor's import cache, a folder or a path built at run time."""
    relative = path[len("res://"):].split("::", 1)[0]
    name = PurePosixPath(relative).name
    return bool(relative) and not relative.startswith(".godot/") and not relative.endswith("/") \
        and "." in name and not any(mark in relative for mark in ("%", "{", "}", "*"))


def references(folder) -> dict:
    """{project-relative path: [files that reference it]} of every quoted res:// file reference."""
    found = {}
    folder = Path(folder)
    for path in text_files(folder):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _QUOTED.finditer(text):
            if is_file_reference(match.group(1)):
                relative = match.group(1)[len("res://"):].split("::", 1)[0]
                found.setdefault(relative, []).append(path.relative_to(folder).as_posix())
    return found


def uid_owners(folder) -> dict:
    """{uid://...: project-relative path} from scene and resource headers, .uid files and import settings."""
    owners = {}
    folder = Path(folder)
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or ".godot" in path.relative_to(folder).parts[:-1]:
            continue
        relative = path.relative_to(folder).as_posix()
        if path.suffix.lower() == ".uid":
            owners.setdefault(path.read_text(encoding="utf-8", errors="replace").strip(), relative[:-len(".uid")])
        elif path.suffix.lower() in (".tscn", ".tres", ".import"):
            text = path.read_text(encoding="utf-8", errors="replace")
            head = text.split("\n[", 1)[0] if path.suffix.lower() != ".import" else text
            match = _UID.search(head)
            if match:
                owner = relative[:-len(".import")] if path.suffix.lower() == ".import" else relative
                owners.setdefault(match.group(1), owner)
    return owners


def pinned_paths(manifest: "dict | None") -> set:
    """The project-relative paths of the media files the manifest pins (placed under project/)."""
    found = set()
    for variant in (manifest or {}).get("variants") or ():
        for item in variant.get("files") or ():
            path = PurePosixPath(item["path"])
            if path.parts and path.parts[0] == "project":
                found.add(PurePosixPath(*path.parts[1:]).as_posix())
    return found


def problems(folder=PROJECT_FOLDER, manifest: "dict | None" = None) -> list:
    """Every problem of the project: an unreadable project.godot, a main scene that is not there, and each
    referenced file that is neither in the folder nor pinned."""
    folder = Path(folder)
    if manifest is None and MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pinned = pinned_paths(manifest)
    project = folder / "project.godot"
    if not project.is_file():
        return ["project.godot is missing"]
    try:
        config = read_config(project.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        return [f"project.godot does not parse: {error}"]
    found = []
    if "config_version" not in config[""]:
        found.append("project.godot names no config_version")

    def present(relative: str) -> bool:
        return (folder / relative).is_file() or relative in pinned

    scene = main_scene(config)
    if scene and scene.startswith("uid://"):
        owner = uid_owners(folder).get(scene)
        if owner is None or not present(owner):
            found.append(f"the main scene {scene} is not a file of the project")
    elif scene and not present(scene[len("res://"):]):
        found.append(f"the main scene {scene} is missing")
    for relative, sources in sorted(references(folder).items()):
        if not present(relative):
            found.append(f"res://{relative} is missing (referenced by {', '.join(sorted(set(sources))[:3])})")
    return found


def main(argv=None) -> int:
    found = problems()
    print("\n".join(found) if found else "the project parses and every referenced file is present or pinned")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
