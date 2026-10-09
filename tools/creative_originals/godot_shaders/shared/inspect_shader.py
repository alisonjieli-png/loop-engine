"""Read a Godot 4 shader package and check it against its contract card, with the Python standard library only.

    python inspect_shader.py PACKAGE_DIR

prints the parsed shader and every problem found as JSON and exits 1 when there is a problem.

A package holds ``<identity>.gdshader``, ``material.tres`` (a ShaderMaterial) and ``demo.tscn`` (a scene that shows
the effect). In a Godot project the folder sits at ``res://baltor/godot_shaders/<identity>/``: the material loads the
shader from that path and the scene loads the material from it. This module checks, without an engine:

* the shader's ``shader_type``, ``render_mode`` list and uniforms (name, type, hint, default) equal the contract;
* ``material.tres`` loads the shader from the declared placement, the file is present, and the material sets only
  uniforms the shader declares, each with a value of a compatible type;
* every external resource ``demo.tscn`` loads is a file of the package at the placement, and the scene uses the
  material.

It is a reader, not a compiler: a shader that parses here can still fail to compile in Godot.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLACEMENT_PREFIX = "res://baltor/godot_shaders/"
SHADER_TYPES = ("spatial", "canvas_item", "particles", "sky", "fog")
MATERIAL_FILE = "material.tres"
SCENE_FILE = "demo.tscn"
#: Godot resource value constructors each uniform type accepts in a .tres file.
COMPATIBLE_VALUES = {
    "bool": ("bool",), "int": ("int",), "uint": ("int",), "float": ("int", "float"),
    "vec2": ("Vector2",), "vec3": ("Vector3", "Color"), "vec4": ("Vector4", "Color", "Quaternion", "Plane"),
    "ivec2": ("Vector2i",), "ivec3": ("Vector3i",), "ivec4": ("Vector4i",),
    "uvec2": ("Vector2i",), "uvec3": ("Vector3i",), "uvec4": ("Vector4i",),
    "bvec2": ("Vector2i",), "bvec3": ("Vector3i",), "bvec4": ("Vector4i",),
    "mat2": ("Transform2D",), "mat3": ("Basis",), "mat4": ("Projection", "Transform3D"),
}
SAMPLER_PREFIXES = ("sampler", "isampler", "usampler")
VECTOR_SIZES = {"vec2": 2, "vec3": 3, "vec4": 4, "ivec2": 2, "ivec3": 3, "ivec4": 4, "uvec2": 2, "uvec3": 3,
                "uvec4": 4, "bvec2": 2, "bvec3": 3, "bvec4": 4}
_NUMBER = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fu]?$")
_INTEGER = re.compile(r"^[+-]?\d+u?$")
_UNIFORM = re.compile(r"^(?:(global|instance)\s+)?uniform\s+(?:(lowp|mediump|highp)\s+)?(\w+)\s+(\w+)\s*"
                      r"(\[\s*\d*\s*\])?\s*(.*)$", re.S)
_VARYING = re.compile(r"^varying\s+(?:(flat|smooth)\s+)?(?:(lowp|mediump|highp)\s+)?(\w+)\s+(\w+)", re.S)
_FUNCTION = re.compile(r"^(?:(lowp|mediump|highp)\s+)?(\w+)\s+(\w+)\s*\((.*)\)$", re.S)
_SECTION = re.compile(r"^\[(\w+)((?:\s+\w+=(?:\"(?:[^\"\\]|\\.)*\"|[^\s\]]+))*)\s*\]$")
_ATTRIBUTE = re.compile(r"(\w+)=(\"(?:[^\"\\]|\\.)*\"|[^\s\]]+)")
_PROPERTY = re.compile(r"^([A-Za-z0-9_/:.\-]+)\s*=\s*(.*)$", re.S)
_REFERENCE = re.compile(r"\b(ExtResource|SubResource)\(\s*\"([^\"]*)\"\s*\)")
#: The two references _REFERENCE finds: a resource in another file, and a resource declared inside this file.
RESOURCE_REFERENCES = (EXT_RESOURCE, SUB_RESOURCE) = ("ExtResource", "SubResource")
#: The constructor of an untyped array value, which (like a Packed* array) can set an array uniform.
ARRAY_VALUE = "Array"


def strip_comments(text: str) -> str:
    """The shader text with ``//`` and ``/* */`` comments blanked out; newlines and string literals are kept."""
    out, index, length = [], 0, len(text)
    while index < length:
        char = text[index]
        if char == '"':
            end = index + 1
            while end < length and text[end] != '"' and text[end] != "\n":
                end += 2 if text[end] == "\\" else 1
            out.append(text[index:end + 1])
            index = end + 1
        elif text.startswith("//", index):
            end = text.find("\n", index)
            end = length if end < 0 else end
            out.append(" " * (end - index))
            index = end
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = length if end < 0 else end + 2
            out.append("".join("\n" if c == "\n" else " " for c in text[index:end]))
            index = end
        else:
            out.append(char)
            index += 1
    return "".join(out)


def split_top_level(text: str, separator: str = ",") -> list:
    """Split ``text`` at ``separator`` characters outside parentheses and brackets; parts are stripped."""
    parts, depth, current = [], 0, []
    for char in text:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == separator and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail or parts:
        parts.append(tail)
    return parts


def normalize_hint(text: str) -> "str | None":
    """A canonical hint list: no inner spaces, ", " between hints and between hint arguments; None when empty."""
    text = (text or "").strip()
    if not text:
        return None
    hints = []
    for part in split_top_level(text):
        compact = re.sub(r"\s+", "", part)
        hints.append(re.sub(r",", ", ", compact))
    return ", ".join(hints)


def parse_literal(text: str, type_name: str):
    """A uniform default as JSON: bool, int, float, a list of numbers for a vector, otherwise the compact text."""
    value = re.sub(r"\s+", " ", (text or "").strip())
    if not value:
        return None
    if value in ("true", "false"):
        return value == "true"
    base = type_name.split("[")[0]
    if _NUMBER.match(value):
        number = value.rstrip("fu") if not value.lower().startswith("0x") else value
        if base in ("int", "uint") and _INTEGER.match(value):
            return int(number)
        return float(number)
    match = re.match(r"^(\w+)\s*\((.*)\)$", value, re.S)
    if match and match.group(1) in VECTOR_SIZES:
        arguments = split_top_level(match.group(2))
        numbers = []
        for argument in arguments:
            if argument in ("true", "false"):
                numbers.append(argument == "true")
            elif _NUMBER.match(argument):
                integer = match.group(1)[0] in "iub" and _INTEGER.match(argument)
                numbers.append(int(argument.rstrip("u")) if integer else float(argument.rstrip("fu")))
            else:
                return value
        size = VECTOR_SIZES[match.group(1)]
        if len(numbers) == 1:
            numbers = numbers * size
        return numbers if len(numbers) == size else value
    return value


def _top_level(text: str) -> tuple:
    """Top-level statements (ending in ';') and the headers of top-level blocks (functions, structs)."""
    statements, headers, depth, current = [], [], 0, []
    for char in text:
        if char == "{":
            if depth == 0:
                headers.append("".join(current).strip())
                current = []
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                current = []
        elif depth == 0:
            if char == ";":
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
            else:
                current.append(char)
    return statements, headers


def parse_uniform(statement: str) -> "dict | None":
    """One ``uniform`` statement (without its ';') as name, type, hint, default and scope; None if it is not one."""
    match = _UNIFORM.match(statement.strip())
    if not match:
        return None
    scope, _precision, type_name, name, array, rest = match.groups()
    if array:
        type_name += re.sub(r"\s+", "", array)
    rest = rest.strip()
    hint_text, default_text = "", ""
    if rest.startswith(":"):
        depth, index = 0, 1
        while index < len(rest):
            char = rest[index]
            if char in "([":
                depth += 1
            elif char in ")]":
                depth -= 1
            elif char == "=" and depth == 0:
                break
            index += 1
        hint_text, rest = rest[1:index], rest[index:].strip()
    if rest.startswith("="):
        default_text = rest[1:]
    return {"name": name, "type": type_name, "hint": normalize_hint(hint_text),
            "default": parse_literal(default_text, type_name), "scope": scope or "material"}


def parse_shader(text: str) -> dict:
    """The declarations of a .gdshader: shader_type, render_modes (in order), uniforms, varyings, functions, includes.

    Preprocessor lines are read for ``#include`` and otherwise ignored; keep declarations outside ``#if`` blocks."""
    clean = strip_comments(text)
    includes = re.findall(r"(?m)^\s*#include\s+\"([^\"]+)\"", clean)
    clean = re.sub(r"(?m)^\s*#.*$", "", clean)
    statements, headers = _top_level(clean)
    shader_type, render_modes, uniforms, varyings, constants = None, [], [], [], []
    for statement in statements:
        words = statement.split(None, 1)
        keyword = words[0]
        if keyword == "shader_type" and len(words) == 2:
            shader_type = words[1].strip()
        elif keyword == "render_mode" and len(words) == 2:
            render_modes += [mode for mode in split_top_level(words[1]) if mode]
        elif keyword in ("uniform", "global", "instance"):
            uniform = parse_uniform(statement)
            if uniform is not None:
                uniforms.append(uniform)
        elif keyword == "varying":
            match = _VARYING.match(statement)
            if match:
                varyings.append({"name": match.group(4), "type": match.group(3),
                                 "interpolation": match.group(1) or "smooth"})
        elif keyword == "const":
            match = re.match(r"^const\s+(?:(?:lowp|mediump|highp)\s+)?(\w+)\s+(\w+)", statement)
            if match:
                constants.append(match.group(2))
    functions = []
    for header in headers:
        match = _FUNCTION.match(header)
        if match and match.group(2) != "struct":
            functions.append(match.group(3))
    return {"shader_type": shader_type, "render_modes": render_modes, "uniforms": uniforms, "varyings": varyings,
            "constants": constants, "functions": functions, "includes": includes}


def contract_uniform(uniform: dict) -> dict:
    """The four keys a contract records for a uniform."""
    return {key: uniform.get(key) for key in ("name", "type", "hint", "default")}


def placement_for(identity: str) -> str:
    """The folder a package is installed at inside a Godot project."""
    return f"{PLACEMENT_PREFIX}{identity}/"


def contract_mismatches(parsed: dict, contract: dict, identity: "str | None" = None) -> list:
    """Every difference between a parsed shader and a contract, as 'reason: detail' strings (empty when they agree)."""
    problems = []
    if parsed.get("shader_type") not in SHADER_TYPES:
        problems.append(f"shader_type_unknown: {parsed.get('shader_type')!r}")
    if parsed.get("shader_type") != contract.get("shader_type"):
        problems.append(f"shader_type_mismatch: shader {parsed.get('shader_type')!r}, "
                        f"contract {contract.get('shader_type')!r}")
    if list(parsed.get("render_modes", [])) != list(contract.get("render_modes", [])):
        problems.append(f"render_modes_mismatch: shader {parsed.get('render_modes')}, "
                        f"contract {contract.get('render_modes')}")
    declared = {row["name"]: contract_uniform(row) for row in parsed.get("uniforms", [])}
    promised = {row.get("name"): row for row in contract.get("uniforms", [])}
    for name in promised:
        if name not in declared:
            problems.append(f"uniform_missing: {name}")
    for name, row in declared.items():
        if name not in promised:
            problems.append(f"uniform_undeclared: {name}")
            continue
        for key in ("type", "hint", "default"):
            if row[key] != promised[name].get(key):
                problems.append(f"uniform_{key}_mismatch: {name} shader {row[key]!r}, "
                                f"contract {promised[name].get(key)!r}")
    if [row["name"] for row in parsed.get("uniforms", [])] != [row.get("name") for row in
                                                              contract.get("uniforms", [])] and not problems:
        problems.append("uniform_order_mismatch")
    if identity is not None and contract.get("placement") != placement_for(identity):
        problems.append(f"placement_mismatch: contract {contract.get('placement')!r}, "
                        f"expected {placement_for(identity)!r}")
    return problems


def parse_resource_text(text: str) -> list:
    """Sections of a Godot text resource or scene: each has kind, attributes and properties (raw value text)."""
    sections, current, pending_key, pending_value = [], None, None, []

    def balanced(value: str) -> bool:
        depth, quoted, escaped = 0, False, False
        for char in value:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
        return depth <= 0 and not quoted

    for line in text.splitlines():
        if pending_key is not None:
            pending_value.append(line)
            joined = "\n".join(pending_value)
            if balanced(joined):
                current["properties"][pending_key] = joined.strip()
                pending_key, pending_value = None, []
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        header = _SECTION.match(stripped)
        if header:
            attributes = {key: value[1:-1] if value.startswith('"') else value
                          for key, value in _ATTRIBUTE.findall(header.group(2))}
            current = {"kind": header.group(1), "attributes": attributes, "properties": {}}
            sections.append(current)
            continue
        match = _PROPERTY.match(stripped)
        if match and current is not None:
            key, value = match.group(1), match.group(2)
            if balanced(value):
                current["properties"][key] = value.strip()
            else:
                pending_key, pending_value = key, [value]
    if pending_key is not None:
        raise ValueError(f"unterminated value for {pending_key}")
    return sections


def value_kind(text: str) -> str:
    """The Godot type of a resource property value: bool, int, float, a constructor name, string or other."""
    value = text.strip()
    if value in ("true", "false"):
        return "bool"
    if re.match(r"^[+-]?\d+$", value):
        return "int"
    if re.match(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:e[+-]?\d+)?$", value) or value in ("inf", "-inf", "nan", "inf_neg"):
        return "float"
    if value.startswith('"'):
        return "string"
    match = re.match(r"^&?(\w+)\s*\(", value)
    return match.group(1) if match else "other"


def value_fits(uniform_type: str, kind: str) -> bool:
    """Whether a .tres value of ``kind`` can set a uniform of ``uniform_type``."""
    base = uniform_type.split("[")[0]
    if "[" in uniform_type:
        return kind.startswith("Packed") or kind == ARRAY_VALUE
    if base.startswith(SAMPLER_PREFIXES):
        return kind in RESOURCE_REFERENCES
    return kind in COMPATIBLE_VALUES.get(base, ())


def resolve_resource(path: str, identity: str, package_dir: Path) -> "Path | None":
    """The package file a ``res://`` path names when it lies inside the placement folder, otherwise None."""
    placement = placement_for(identity)
    if not path.startswith(placement):
        return None
    relative = path[len(placement):]
    parts = relative.split("/")
    if not relative or any(part in ("", ".", "..") for part in parts):
        return None
    target = Path(package_dir).joinpath(*parts)
    return target if target.is_file() else None


def _references(sections: list) -> list:
    found = []
    for section in sections:
        for value in section["properties"].values():
            found += _REFERENCE.findall(value)
    return found


def _ids(sections: list, kind: str) -> dict:
    return {section["attributes"].get("id"): section for section in sections if section["kind"] == kind}


def material_problems(text: str, parsed: dict, identity: str, package_dir: Path) -> list:
    """Problems of ``material.tres``: its shader path, the file behind it, and every parameter it sets."""
    problems = []
    try:
        sections = parse_resource_text(text)
    except ValueError as error:
        return [f"material_unreadable: {error}"]
    if not sections or sections[0]["kind"] != "gd_resource" or \
            sections[0]["attributes"].get("type") != "ShaderMaterial":
        problems.append("material_not_shader_material")
    external, internal = _ids(sections, "ext_resource"), _ids(sections, "sub_resource")
    expected = f"{placement_for(identity)}{identity}.gdshader"
    shader_ids = [key for key, row in external.items() if row["attributes"].get("type") == "Shader"]
    resource = next((section for section in sections if section["kind"] == "resource"), None)
    if resource is None:
        return problems + ["material_resource_section_missing"]
    assigned = _REFERENCE.findall(resource["properties"].get("shader", ""))
    if len(shader_ids) != 1 or assigned != [(EXT_RESOURCE, shader_ids[0])]:
        problems.append("material_shader_not_assigned")
    for key in shader_ids:
        path = external[key]["attributes"].get("path", "")
        if path != expected:
            problems.append(f"material_shader_path_wrong: {path!r}, expected {expected!r}")
        elif resolve_resource(path, identity, package_dir) is None:
            problems.append(f"material_shader_missing: {path!r}")
    for key, row in external.items():
        path = row["attributes"].get("path", "")
        if row["attributes"].get("type") != "Shader" and resolve_resource(path, identity, package_dir) is None:
            problems.append(f"material_resource_missing: {path!r}")
    for kind, key in _references(sections):
        if key not in (external if kind == EXT_RESOURCE else internal):
            problems.append(f"material_reference_missing: {kind}({key!r})")
    uniforms = {row["name"]: row for row in parsed.get("uniforms", [])}
    for prop, value in resource["properties"].items():
        if not prop.startswith("shader_parameter/"):
            continue
        name = prop.split("/", 1)[1]
        if name not in uniforms:
            problems.append(f"material_parameter_undeclared: {name}")
        elif not value_fits(uniforms[name]["type"], value_kind(value)):
            problems.append(f"material_parameter_type_mismatch: {name} is {uniforms[name]['type']}, "
                            f"value {value_kind(value)}")
    return problems


def scene_problems(text: str, identity: str, package_dir: Path) -> list:
    """Problems of ``demo.tscn``: external files outside the package, unknown references, an unused material."""
    problems = []
    try:
        sections = parse_resource_text(text)
    except ValueError as error:
        return [f"scene_unreadable: {error}"]
    if not sections or sections[0]["kind"] != "gd_scene":
        problems.append("scene_header_missing")
    external, internal = _ids(sections, "ext_resource"), _ids(sections, "sub_resource")
    material_ids = []
    for key, row in external.items():
        path = row["attributes"].get("path", "")
        if resolve_resource(path, identity, package_dir) is None:
            problems.append(f"scene_resource_missing: {path!r}")
        if path == f"{placement_for(identity)}{MATERIAL_FILE}":
            material_ids.append(key)
    for kind, key in _references(sections):
        if key not in (external if kind == EXT_RESOURCE else internal):
            problems.append(f"scene_reference_missing: {kind}({key!r})")
    used = {key for kind, key in _references(sections) if kind == EXT_RESOURCE}
    if not material_ids or not used & set(material_ids):
        problems.append("scene_material_unused")
    nodes = [section for section in sections if section["kind"] == "node"]
    if not nodes or "parent" in nodes[0]["attributes"]:
        problems.append("scene_root_missing")
    return problems


def check_item_files(directory: Path, identity: str, contract: dict) -> dict:
    """Parse the shader in ``directory`` and check it, its material and its scene against ``contract``."""
    directory = Path(directory)
    report = {"identity": identity, "shader": None, "problems": []}
    shader_path = directory / f"{identity}.gdshader"
    if shader_path.is_file():
        parsed = parse_shader(shader_path.read_text(encoding="utf-8"))
        report["shader"] = parsed
        report["problems"] += contract_mismatches(parsed, contract, identity)
    else:
        parsed = parse_shader("")
        report["problems"].append(f"shader_missing: {shader_path.name}")
    for name, check in ((MATERIAL_FILE, lambda text: material_problems(text, parsed, identity, directory)),
                        (SCENE_FILE, lambda text: scene_problems(text, identity, directory))):
        path = directory / name
        if not path.is_file():
            report["problems"].append(f"file_missing: {name}")
        else:
            report["problems"] += check(path.read_text(encoding="utf-8"))
    return report


def check_package(directory: Path) -> dict:
    """Check a package folder against the contract in its own ``component.json``."""
    directory = Path(directory)
    card = json.loads((directory / "component.json").read_text(encoding="utf-8"))
    return check_item_files(directory, card["job"]["identity"], card["contract"])


def main(argv: "list | None" = None) -> int:
    """Command line entry: print the report for one package folder and return 1 when it has a problem."""
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: python inspect_shader.py PACKAGE_DIR", file=sys.stderr)
        return 2
    report = check_package(Path(arguments[0]))
    print(json.dumps(report, indent=1, sort_keys=True))
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
