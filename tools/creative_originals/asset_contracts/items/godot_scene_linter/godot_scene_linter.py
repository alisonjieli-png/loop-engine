"""Godot scene and resource linter: parse .tscn and .tres text files and find what breaks or vanishes on load.

    python3 godot_scene_linter.py FILE.tscn [--project PROJECT_FOLDER]

Parses Godot text scenes and resources (format 3 and 4, and the Godot 3 format 2 with a warning): the file header, [ext_resource], [sub_resource], [node],
[connection], [editable] and [resource] sections, header attributes and multi-line property values. Then checks the
references Godot resolves on load: external resource files that exist under the project root, ExtResource and
SubResource ids that are declared (sub-resources before their first use), node parents that exist, sibling names
that do not repeat, one root, a type or an instance for every node, and connections between existing nodes. Nodes
inside instanced scenes are known by parsing those scenes too. Prints one JSON report; exits 0 when no rule fails.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import asset_report

TOOL = "godot_scene_linter"
FORMATS = ("3", "4")
#: Godot 3 text format. Godot 4.7 converts its class names on load (Spatial becomes Node3D), so it is a warning.
LEGACY_FORMAT = "2"
#: ExtResource("id") and SubResource("id"), or the unquoted integer ids of the Godot 3 format.
REFERENCE = re.compile(r'\b(ExtResource|SubResource)\(\s*(?:"([^"]*)"|(\d+))\s*\)')
#: The two kinds REFERENCE finds: a resource in another file, and a resource declared inside this file.
EXT_RESOURCE, SUB_RESOURCE = "ExtResource", "SubResource"
FAILURES = ("file_unreadable", "syntax_invalid", "header_invalid", "format_unsupported", "ext_resource_invalid",
            "ext_resource_id_repeated", "ext_resource_missing_file", "ext_resource_reference_unknown",
            "sub_resource_id_repeated", "sub_resource_reference_unknown", "sub_resource_forward_reference",
            "root_node_count", "node_parent_missing", "node_name_repeated", "node_type_missing",
            "connection_node_missing", "resource_section_missing")
MAXIMUM_DEPTH = 8


class ParseError(ValueError):
    def __init__(self, line: int, detail: str) -> None:
        super().__init__(f"line {line}: {detail}")
        self.line, self.detail = line, detail


def _scan(text: str, position: int, stop_at_newline: bool) -> int:
    """The end of one value starting at ``position``: brackets balanced, strings closed, then a newline (or the
    closing bracket of a header when ``stop_at_newline`` is false)."""
    depth, in_string, start_line = 0, False, text.count("\n", 0, position) + 1
    while position < len(text):
        character = text[position]
        if in_string:
            if character == "\\":
                position += 2
                continue
            if character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "([{":
            depth += 1
        elif character in ")]}":
            depth -= 1
            if depth < 0:
                if not stop_at_newline and character == "]":
                    return position
                raise ParseError(text.count("\n", 0, position) + 1, f"unbalanced {character!r}")
        elif character == "\n" and depth == 0 and stop_at_newline:
            return position
        position += 1
    if in_string or depth:
        raise ParseError(start_line, "a string or bracket opened here is never closed")
    return position


def _attributes(header: str, line: int) -> dict:
    """key=value pairs of a section header; values keep their source text (quotes removed from plain strings)."""
    values, position = {}, 0
    while position < len(header):
        while position < len(header) and header[position] in " \t":
            position += 1
        if position >= len(header):
            break
        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)=", header[position:])
        if match is None:
            raise ParseError(line, f"cannot read header attribute at {header[position:position + 30]!r}")
        position += match.end()
        start = position
        depth, in_string = 0, False
        while position < len(header):
            character = header[position]
            if in_string:
                if character == "\\":
                    position += 2
                    continue
                in_string = character != '"'
            elif character == '"':
                in_string = True
            elif character in "([{":
                depth += 1
            elif character in ")]}":
                depth -= 1
            elif character in " \t" and depth == 0:
                break
            position += 1
        raw = header[start:position]
        values[match.group(1)] = raw[1:-1] if len(raw) >= 2 and raw[0] == raw[-1] == '"' else raw
    return values


def parse(text: str) -> list:
    """Sections in order: {kind, attributes, properties: [(key, raw value, line)], line}. Raises ParseError."""
    sections, position = [], 0
    while position < len(text):
        character = text[position]
        if character in " \t\r\n":
            position += 1
            continue
        line = text.count("\n", 0, position) + 1
        if character == ";":
            position = text.find("\n", position) if "\n" in text[position:] else len(text)
            continue
        if character == "[":
            end = _scan(text, position + 1, stop_at_newline=False)
            if end >= len(text) or text[end] != "]":
                raise ParseError(line, "a section header is not closed")
            header = text[position + 1:end].strip()
            kind = header.split(None, 1)[0] if header else ""
            if not re.fullmatch(r"[a-z_]+", kind):
                raise ParseError(line, f"section {kind!r} is not a Godot section name")
            sections.append({"kind": kind, "attributes": _attributes(header[len(kind):], line), "properties": [],
                             "line": line})
            position = end + 1
            continue
        match = re.match(r'("[^"\n]*"|[^\s=]+)\s*=\s*', text[position:])
        if match is None or not sections:
            raise ParseError(line, "expected a section header or a key = value line")
        start = position + match.end()
        end = _scan(text, start, stop_at_newline=True)
        sections[-1]["properties"].append((match.group(1), text[start:end].strip(), line))
        position = end
    return sections


def find_project(path: Path) -> "Path | None":
    for folder in [path.parent, *path.parent.parents]:
        if (folder / "project.godot").is_file():
            return folder
    return None


def resolve(project: "Path | None", resource_path: str) -> "Path | None":
    if project is None or not resource_path.startswith("res://"):
        return None
    return project / resource_path[len("res://"):]


def node_paths(path: Path, project: "Path | None", depth: int = 0) -> set:
    """Every node path a scene file defines, including the nodes of the scenes it instances."""
    try:
        sections = parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ParseError):
        return set()
    resources = {section["attributes"].get("id"): section["attributes"].get("path") for section in sections
                 if section["kind"] == "ext_resource"}
    paths = set()
    for section in sections:
        if section["kind"] != "node":
            continue
        attributes = section["attributes"]
        parent = attributes.get("parent")
        own = "." if parent is None else (attributes.get("name", "") if parent == "." else
                                          f"{parent}/{attributes.get('name', '')}")
        paths.add(own)
        instance = REFERENCE.search(attributes.get("instance", ""))
        if instance and depth < MAXIMUM_DEPTH:
            target = resolve(project, resources.get(instance.group(2) or instance.group(3)) or "")
            if target is not None and target.is_file():
                for inner in node_paths(target, project, depth + 1):
                    if inner != ".":
                        paths.add(inner if own == "." else f"{own}/{inner}")
    return paths


def lint(path, project=None) -> asset_report.Report:
    path = Path(path)
    report = asset_report.Report(TOOL, path.name)
    try:
        sections = parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        report.fail("file_unreadable", path.name, type(error).__name__)
        return report
    except ParseError as error:
        report.fail("syntax_invalid", f"line {error.line}", error.detail)
        return report
    project = Path(project) if project else find_project(path)
    if project is None:
        report.warn("project_root_unknown", path.name, "no project.godot found: res:// files are not checked")
    if not sections or sections[0]["kind"] not in ("gd_scene", "gd_resource"):
        report.fail("header_invalid", "line 1", "the first section is gd_scene or gd_resource")
        return report
    head = sections[0]
    version = head["attributes"].get("format")
    if version == LEGACY_FORMAT:
        report.warn("godot3_format", "line 1", "format 2 (Godot 3): Godot 4 converts class names on load; save the "
                                               "scene again from Godot 4")
    elif version not in FORMATS:
        report.fail("format_unsupported", "line 1", f"format {version!r}: Godot 4.7 reads {' and '.join(FORMATS)} "
                                                    "(and converts 2); a newer format does not load")
        return report
    externals, internals, used = {}, {}, set()
    for section in sections[1:]:
        attributes, where = section["attributes"], f"line {section['line']}"
        if section["kind"] == "ext_resource":
            identifier, resource = attributes.get("id"), attributes.get("path")
            if not identifier or not (resource or attributes.get("uid")):
                report.fail("ext_resource_invalid", where, "an ext_resource has an id and a path or uid")
                continue
            if identifier in externals:
                report.fail("ext_resource_id_repeated", where, identifier)
            target = resolve(project, resource or "")
            exists = None if target is None else target.is_file()
            if exists is False:
                report.fail("ext_resource_missing_file", where, f"{resource} does not exist under the project root")
            externals[identifier] = {"id": identifier, "type": attributes.get("type"), "path": resource,
                                     "exists": exists}
        elif section["kind"] == "sub_resource":
            if attributes.get("id") in internals:
                report.fail("sub_resource_id_repeated", where, attributes.get("id"))
            internals[attributes.get("id")] = {"id": attributes.get("id"), "type": attributes.get("type"),
                                               "line": section["line"]}
    declared = set()
    for section in sections[1:]:
        if section["kind"] == "sub_resource":
            declared.add(section["attributes"].get("id"))
        texts = [(value, line) for _key, value, line in section["properties"]]
        texts += [(value, section["line"]) for value in section["attributes"].values()]
        for value, line in texts:
            for kind, quoted, number in REFERENCE.findall(value):
                identifier = quoted or number
                used.add((kind, identifier))
                if kind == EXT_RESOURCE:
                    if identifier not in externals:
                        report.fail("ext_resource_reference_unknown", f"line {line}", f'ExtResource("{identifier}")')
                elif identifier not in internals:
                    report.fail("sub_resource_reference_unknown", f"line {line}", f'SubResource("{identifier}")')
                elif identifier not in declared:
                    report.fail("sub_resource_forward_reference", f"line {line}",
                                f'SubResource("{identifier}") is used before line {internals[identifier]["line"]}')
    nodes, known = _check_nodes(sections, externals, project, report)
    _check_connections(sections, known, report)
    if head["kind"] == "gd_resource" and not any(section["kind"] == "resource" for section in sections):
        report.fail("resource_section_missing", path.name, "a .tres holds one [resource] section")
    for identifier in sorted(set(externals) - {identifier for kind, identifier in used if kind == EXT_RESOURCE}):
        report.warn("ext_resource_unused", identifier, externals[identifier]["path"])
    for identifier in sorted(set(internals) - {identifier for kind, identifier in used if kind == SUB_RESOURCE}):
        report.warn("sub_resource_unused", identifier, internals[identifier]["type"])
    report.facts = {"kind": head["kind"], "format": head["attributes"].get("format"),
                    "project": project.name if project else None, "ext_resources": list(externals.values()),
                    "sub_resources": [{"id": row["id"], "type": row["type"]} for row in internals.values()],
                    "nodes": nodes, "connections": [section["attributes"] for section in sections
                                                    if section["kind"] == "connection"]}
    return report


def _check_nodes(sections: list, externals: dict, project, report: asset_report.Report) -> tuple:
    """(nodes as declared, every node path known, including the nodes of instanced scenes)."""
    nodes, known, siblings, roots = [], set(), set(), 0
    inherited = False
    for section in sections:
        if section["kind"] != "node":
            continue
        attributes, where = section["attributes"], f"line {section['line']}"
        parent, name = attributes.get("parent"), attributes.get("name", "")
        instance = REFERENCE.search(attributes.get("instance", ""))
        if parent is None:
            roots += 1
            path = "."
            inherited = inherited or instance is not None
        else:
            path = name if parent == "." else f"{parent}/{name}"
            if parent != "." and parent not in known:
                report.fail("node_parent_missing", where, f"parent {parent!r} of {name!r} is not a node of the scene")
            if (parent, name) in siblings:
                report.fail("node_name_repeated", where, f"{parent!r} already has a child named {name!r}")
            siblings.add((parent, name))
        if "type" not in attributes and instance is None and "instance_placeholder" not in attributes \
                and not inherited and path not in known:
            report.fail("node_type_missing", where, f"{name!r} has no type and no instance: Godot drops it")
        known.add(path)
        instance_id = (instance.group(2) or instance.group(3)) if instance else None
        if instance_id in externals:
            target = resolve(project, externals[instance_id]["path"] or "")
            if target is not None and target.is_file():
                for inner in node_paths(target, project):
                    if inner != ".":
                        known.add(inner if path == "." else f"{path}/{inner}")
        nodes.append({"path": path, "name": name, "type": attributes.get("type"),
                      "instance": externals.get(instance_id, {}).get("path") if instance else None})
    if roots != 1 and nodes:
        report.fail("root_node_count", "nodes", f"{roots} nodes have no parent; a scene has exactly one root")
    return nodes, known


def _check_connections(sections: list, known: set, report: asset_report.Report) -> None:
    for section in sections:
        if section["kind"] != "connection":
            continue
        for key in ("from", "to"):
            target = section["attributes"].get(key)
            if target not in known:
                report.fail("connection_node_missing", f"line {section['line']}",
                            f"{key}={target!r} names no node of the scene")


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    parser.add_argument("file", help="a .tscn or .tres text file")
    parser.add_argument("--project", help="the folder holding project.godot (found upwards when omitted)")
    arguments = parser.parse_args(argv)
    return lint(arguments.file, arguments.project).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
