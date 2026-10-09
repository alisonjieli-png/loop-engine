"""Brick wall in a chosen bond: stretcher, stack, English, Flemish or common, with mortar joints and cut ends.

The core, build_geometry(**parameters), lays bricks course by course. Each bond is a rule for one course:
stretcher bond shifts every other course by half a brick; English bond alternates a course of stretchers in two
leaves with a course of headers that starts with a queen closer; Flemish bond alternates headers and stretchers
inside each course and shifts every other course by half a pattern; common bond adds a header course every few
stretcher courses. Bricks past the wall ends are cut, every brick is a closed box, a recessed mortar core fills
the joints, and three colour slots are spread over the bricks by a seeded hash. It needs no Blender.

In Blender, create(context, **parameters) adds the wall at the 3D cursor, and register() adds the operator
baltor.brick_wall_bonds to Add > Mesh. As a script:

    blender --background --python brick_wall_bonds.py -- --bond flemish --length 3 --courses 20 --output wall.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Brick Wall Bonds",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Brick Wall",
    "description": "Brick wall in stretcher, stack, English, Flemish or common bond with mortar and cut ends",
    "category": "Add Mesh",
}

OPERATOR = "baltor.brick_wall_bonds"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Brick Wall", "icon": "MOD_BUILD"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Brick Wall"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "bond", "type": "choice", "default": "english", "minimum": None, "maximum": None, "unit": "pattern",
     "choices": ["stretcher", "stack", "english", "flemish", "common"], "description": "Bond pattern."},
    {"name": "length", "type": "float", "default": 2.0, "minimum": 0.3, "maximum": 30.0, "unit": "m",
     "description": "Wall length along +X."},
    {"name": "courses", "type": "int", "default": 12, "minimum": 1, "maximum": 200, "unit": "count",
     "description": "Number of brick courses."},
    {"name": "brick", "type": "vector", "default": [0.215, 0.1025, 0.065], "minimum": 0.01, "maximum": 1.0,
     "unit": "m", "description": "Brick length, width and height."},
    {"name": "joint", "type": "float", "default": 0.01, "minimum": 0.002, "maximum": 0.05, "unit": "m",
     "description": "Mortar joint thickness."},
    {"name": "header_every", "type": "int", "default": 6, "minimum": 2, "maximum": 12, "unit": "count",
     "description": "Common bond: one header course in every this many courses."},
    {"name": "recess", "type": "float", "default": 0.006, "minimum": 0.0, "maximum": 0.03, "unit": "m",
     "description": "How far the mortar core sits behind the brick faces."},
    {"name": "seed", "type": "int", "default": 1, "minimum": 0, "maximum": 1000000, "unit": "seed",
     "description": "Seed for the spread of the three brick colours."},
)


def _extra_checks(p):
    length, width, _height = p["brick"]
    if length < 2 * width:
        raise ValueError("brick length must be at least twice its width")
    if p["recess"] * 2 >= width:
        raise ValueError("recess must be less than half the brick width")


# ------------------------------------------------------------------------------------------------ pure core
def _hash(*numbers):
    value = 0x9E3779B9
    for number in numbers:
        value = ((value ^ (number & 0xFFFFFFFF)) * 0x01000193) & 0xFFFFFFFF
        value ^= value >> 13
    return value


def _run(start, pieces, joint, length):
    """Place pieces [(width along X, kind, y0, y1), ...] repeatedly from start until past length."""
    row, x, index = [], start, 0
    while x < length:
        width, kind, y0, y1 = pieces[index % len(pieces)]
        row.append((x, x + width, y0, y1, kind))
        x += width + joint
        index += 1
    return row


def course_layout(bond, course, length, brick, joint, header_every):
    """Bricks of one course as (x0, x1, y0, y1, kind) before cutting at the wall ends."""
    l, w, _h = brick
    module = l + joint
    two_leaf = (0.0, 2 * w + joint)
    if bond == "stack":
        return _run(0.0, [(l, "stretcher", 0.0, w)], joint, length)
    if bond == "stretcher":
        return _run(-module / 2.0 if course % 2 else 0.0, [(l, "stretcher", 0.0, w)], joint, length)
    if bond == "english" or (bond == "common" and course % header_every == header_every - 1):
        if course % 2 == 0 and bond == "english":
            return (_run(0.0, [(l, "stretcher", 0.0, w)], joint, length)
                    + _run(0.0, [(l, "stretcher", w + joint, 2 * w + joint)], joint, length))
        closer = (w - joint) / 2.0
        return [(0.0, closer, *two_leaf, "closer")] + _run(closer + joint, [(w, "header", *two_leaf)], joint, length)
    if bond == "common":
        start = -module / 2.0 if course % 2 else 0.0
        return (_run(start, [(l, "stretcher", 0.0, w)], joint, length)
                + _run(start, [(l, "stretcher", w + joint, 2 * w + joint)], joint, length))
    unit = w + l + 2 * joint
    start = -unit / 2.0 if course % 2 else 0.0
    row = _run(start, [(w, "header", *two_leaf), (l, "stretcher", 0.0, w)], joint, length)
    backs = [(x0, x1, w + joint, 2 * w + joint, "stretcher") for x0, x1, _y0, _y1, kind in row if kind == "stretcher"]
    return row + backs


def _box(vertices, faces, low, high):
    base = len(vertices)
    (x0, y0, z0), (x1, y1, z1) = low, high
    vertices.extend([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                     [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    for face in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        faces.append([base + index for index in face])


def build_geometry(**values):
    """The wall as {"vertices", "faces", "face_materials", "materials", "report"}; front face at y = 0."""
    p = _validate(values)
    l, w, h = p["brick"]
    joint, length = p["joint"], p["length"]
    vertices, faces, slots = [], [], []
    counts = {"stretcher": 0, "header": 0, "closer": 0, "cut": 0}
    thickness = w
    for course in range(p["courses"]):
        z0 = course * (h + joint)
        for number, (x0, x1, y0, y1, kind) in enumerate(course_layout(p["bond"], course, length, p["brick"],
                                                                       joint, p["header_every"])):
            cut0, cut1 = max(x0, 0.0), min(x1, length)
            if cut1 - cut0 < 0.02:
                continue
            thickness = max(thickness, y1)
            counts["cut" if (cut0, cut1) != (x0, x1) else kind] += 1
            _box(vertices, faces, [cut0, y0, z0], [cut1, y1, z0 + h])
            slots += [1 + _hash(p["seed"], course, number) % 3] * 6
    top = p["courses"] * (h + joint) - joint
    _box(vertices, faces, [0.0, p["recess"], 0.0], [length, thickness - p["recess"], top])
    slots += [0] * 6
    vertices = [[round(c, 9) for c in vertex] for vertex in vertices]
    bricks = sum(counts.values())
    report = {"bricks": bricks, **{f"{kind}s": count for kind, count in counts.items()},
              "wall_thickness_m": round(thickness, 9), "face_area_m2": round(length * top, 6),
              "bricks_per_m2_of_face": round(bricks / (length * top), 3)}
    materials = [{"name": "Baltor Mortar", "color": [0.55, 0.53, 0.5], "roughness": 0.95},
                 {"name": "Baltor Brick Red", "color": [0.42, 0.13, 0.07], "roughness": 0.85},
                 {"name": "Baltor Brick Brown", "color": [0.36, 0.15, 0.09], "roughness": 0.85},
                 {"name": "Baltor Brick Orange", "color": [0.5, 0.2, 0.09], "roughness": 0.85}]
    return {"vertices": vertices, "faces": faces, "face_materials": slots, "materials": materials, "report": report}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "material_indices": sorted(set(mesh["face_materials"])),
                                      "materials": [spec["name"] for spec in mesh["materials"]]}}}


def create(context=None, **values):
    """Add the wall at the 3D cursor and return the object."""
    import bpy
    return _link_mesh(context or bpy.context, OBJECT_NAME, build_geometry(**values))


# ------------------------------------------------------------------------------------------------ mesh objects
def _material(bpy, spec):
    """A Principled material from {"name", "color", "roughness", "metallic"}, reused when the name exists."""
    material = bpy.data.materials.get(spec["name"])
    if material is None:
        material = bpy.data.materials.new(spec["name"])
        if material.node_tree is None:
            material.use_nodes = True
        color = list(spec.get("color", [0.8, 0.8, 0.8])) + [1.0]
        material.diffuse_color = color
        shader = next((node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"),
                      None)
        if shader is not None:
            shader.inputs["Base Color"].default_value = color
            shader.inputs["Roughness"].default_value = spec.get("roughness", 0.6)
            shader.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
    return material


def _mesh_from(bpy, name, data):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(vertex) for vertex in data["vertices"]], [], [tuple(face) for face in data["faces"]])
    if data.get("uv"):
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", [value for corner in data["uv"] for value in corner])
    if data.get("smooth"):
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    for spec in data.get("materials", []):
        mesh.materials.append(_material(bpy, spec))
    if data.get("face_materials"):
        mesh.polygons.foreach_set("material_index", data["face_materials"])
    mesh.update()
    return mesh


def _link_mesh(context, name, data, select=True):
    """A mesh object from a core mesh dict, linked to the active collection at the 3D cursor and selected."""
    import bpy
    obj = bpy.data.objects.new(name, _mesh_from(bpy, name, data))
    for group, indices in data.get("groups", {}).items():
        obj.vertex_groups.new(name=group).add(list(indices), 1.0, "REPLACE")
    (context.collection or context.scene.collection).objects.link(obj)
    obj.location = context.scene.cursor.location
    if select:
        for other in context.view_layer.objects:
            other.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
    return obj


def _link_parts(context, parts, root_name):
    """One object per part under an empty named root_name at the 3D cursor; returns the empty."""
    import bpy
    collection = context.collection or context.scene.collection
    root = bpy.data.objects.new(root_name, None)
    root.empty_display_type = "PLAIN_AXES"
    collection.objects.link(root)
    root.location = context.scene.cursor.location
    made = {root_name: root}
    for part in parts:
        obj = bpy.data.objects.new(part["name"], _mesh_from(bpy, part["name"], part))
        for group, indices in part.get("groups", {}).items():
            obj.vertex_groups.new(name=group).add(list(indices), 1.0, "REPLACE")
        collection.objects.link(obj)
        obj.parent = made[part.get("parent") or root_name]
        obj.location = part.get("location", [0.0, 0.0, 0.0])
        obj.rotation_euler = [math.radians(angle) for angle in part.get("rotation", [0.0, 0.0, 0.0])]
        made[part["name"]] = obj
    for other in context.view_layer.objects:
        other.select_set(False)
    root.select_set(True)
    context.view_layer.objects.active = root
    return root


# ------------------------------------------------------------------------------------------------ parameters
def _number(name, value, spec):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if spec["type"] == PARAMETER_TYPE_INT:
        if float(value) != int(value):
            raise ValueError(f"{name} must be a whole number")
        value = int(value)
    else:
        value = float(value)
    if not (math.isfinite(value) and spec["minimum"] <= value <= spec["maximum"]):
        raise ValueError(f"{name} must lie in [{spec['minimum']}, {spec['maximum']}]")
    return value


def _validate(values):
    specs = {spec["name"]: spec for spec in PARAMETERS}
    unknown = sorted(set(values) - set(specs))
    if unknown:
        raise ValueError(f"unknown parameter: {', '.join(unknown)}")
    result = {}
    for name, spec in specs.items():
        value = values.get(name, spec["default"])
        kind = spec["type"]
        if kind == PARAMETER_TYPE_BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be true or false")
        elif kind == PARAMETER_TYPE_CHOICE:
            if value not in spec["choices"]:
                raise ValueError(f"{name} must be one of {', '.join(spec['choices'])}")
        elif kind == PARAMETER_TYPE_STRING:
            if not isinstance(value, str) or len(value) > 1024:
                raise ValueError(f"{name} must be text of at most 1024 characters")
        elif kind == PARAMETER_TYPE_VECTOR:
            if isinstance(value, (str, bytes)) or not hasattr(value, "__len__") or len(value) != 3:
                raise ValueError(f"{name} must hold three numbers")
            value = [_number(name, item, {"type": PARAMETER_TYPE_FLOAT, "minimum": spec["minimum"],
                                          "maximum": spec["maximum"]}) for item in value]
        else:
            value = _number(name, value, spec)
        result[name] = value
    extra = globals().get("_extra_checks")
    if extra is not None:
        extra(result)
    return result


def parameters(**values):
    """The validated parameters with defaults filled in; raises ValueError on an unknown name or a bad value."""
    return _validate(values)


# ------------------------------------------------------------------------------------------------ script mode
def _from_text(spec, text):
    kind = spec["type"]
    if kind == PARAMETER_TYPE_BOOL:
        if text.lower() not in ("true", "false", "1", "0", "yes", "no"):
            raise ValueError(f"{spec['name']} takes true or false")
        return text.lower() in ("true", "1", "yes")
    if kind == PARAMETER_TYPE_INT:
        return int(text)
    if kind == PARAMETER_TYPE_FLOAT:
        return float(text)
    if kind == PARAMETER_TYPE_VECTOR:
        return [float(part) for part in text.split(",")]
    return text


def parse_arguments(argv):
    """(parameters, output path) from script arguments: --name value pairs and an optional --output path."""
    specs = {spec["name"]: spec for spec in PARAMETERS}
    values, output = {}, None
    if len(argv) % 2:
        raise ValueError("arguments come in --name value pairs")
    for key, text in zip(argv[0::2], argv[1::2]):
        name = key[2:].replace("-", "_") if key.startswith("--") else None
        if name == "output":
            output = text
        elif name in specs:
            values[name] = _from_text(specs[name], text)
        else:
            raise ValueError(f"unknown argument {key}")
    return _validate(values), output


# ------------------------------------------------------------------------------------------------ add-on
def _properties(bpy):
    annotations = {}
    for spec in PARAMETERS:
        kind = spec["type"]
        common = {"name": spec["name"].replace("_", " ").title(), "description": spec["description"]}
        if kind == PARAMETER_TYPE_BOOL:
            prop = bpy.props.BoolProperty(default=spec["default"], **common)
        elif kind == PARAMETER_TYPE_STRING:
            prop = bpy.props.StringProperty(default=spec["default"], **common)
        elif kind == PARAMETER_TYPE_CHOICE:
            prop = bpy.props.EnumProperty(items=[(choice, choice.replace("_", " ").title(), "")
                                                 for choice in spec["choices"]], default=spec["default"], **common)
        elif kind == PARAMETER_TYPE_VECTOR:
            subtype = {"linear RGB": "COLOR", "m": "TRANSLATION"}.get(spec["unit"], "NONE")
            prop = bpy.props.FloatVectorProperty(size=3, default=spec["default"], min=spec["minimum"],
                                                 max=spec["maximum"], subtype=subtype, **common)
        elif kind == PARAMETER_TYPE_INT:
            prop = bpy.props.IntProperty(default=spec["default"], min=spec["minimum"], max=spec["maximum"],
                                         **common)
        else:
            prop = bpy.props.FloatProperty(default=spec["default"], min=spec["minimum"], max=spec["maximum"],
                                           unit="LENGTH" if spec["unit"] == "m" else "NONE", **common)
        annotations[spec["name"]] = prop
    return annotations


_CLASSES = []


def _menu_entry(self, context):
    self.layout.operator(OPERATOR, text=MENU["label"], icon=MENU["icon"])


def register():
    """Register the operator and its menu entry."""
    import bpy

    def execute(self, context):
        values = {spec["name"]: list(getattr(self, spec["name"])) if spec["type"] == PARAMETER_TYPE_VECTOR
                  else getattr(self, spec["name"]) for spec in PARAMETERS}
        try:
            result = globals()[BLENDER_ENTRY](context, **values)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if isinstance(result, dict) and "report" in result:
            self.report({"INFO"}, json.dumps(result["report"], default=str)[:240])
        return {"FINISHED"}

    namespace = {"bl_idname": OPERATOR, "bl_label": MENU["label"], "bl_description": bl_info["description"],
                 "bl_options": {"REGISTER", "UNDO"}, "__annotations__": _properties(bpy), "execute": execute}
    if globals().get("_invoke") is not None:
        namespace["invoke"] = globals()["_invoke"]
    operator = type("BALTOR_OT_" + OPERATOR.split(".", 1)[1], (bpy.types.Operator,), namespace)
    bpy.utils.register_class(operator)
    _CLASSES.append(operator)
    getattr(bpy.types, MENU["menu"]).append(_menu_entry)


def unregister():
    """Remove the menu entry and the operator."""
    import bpy
    getattr(bpy.types, MENU["menu"]).remove(_menu_entry)
    while _CLASSES:
        bpy.utils.unregister_class(_CLASSES.pop())


def _save(output):
    import bpy
    if output.endswith(".blend"):
        bpy.ops.wm.save_as_mainfile(filepath=output)
    elif output.endswith((".glb", ".gltf")):
        bpy.ops.export_scene.gltf(filepath=output, export_format="GLB" if output.endswith(".glb")
                                  else "GLTF_SEPARATE")
    else:
        raise ValueError("--output ends in .blend, .glb or .gltf")


def main(argv=None):
    """Script mode: run on the opened file with --name value arguments, then save when --output is given."""
    import bpy
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    values, output = parse_arguments(argv)
    result = globals()[BLENDER_ENTRY](bpy.context, **values)
    if isinstance(result, dict) and "report" in result:
        print(json.dumps(result["report"], default=str))
    if output:
        _save(output)


if __name__ == "__main__":
    main()
