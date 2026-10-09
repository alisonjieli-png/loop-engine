"""Quarter-turn (L-shaped) stairs: two straight flights joined by a square landing or by three winder treads.

The core, build_geometry(**parameters), builds the first flight along +Y, then fills the corner square either with
one landing slab or with three winders: wedges cut from the corner square by rays from the inner corner at 30
degree steps, each one rise higher. The second flight continues along +X (turn right) or -X (turn left). Every
tread is a closed prism with outward faces. It needs no Blender.

In Blender, create(context, **parameters) adds the stairs at the 3D cursor, and register() adds the operator
baltor.stairs_l_shaped to Add > Mesh. As a script:

    blender --background --python stairs_l_shaped.py -- --corner winders --turn left --output stairs.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor L-Shaped Stairs",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > L-Shaped Stairs",
    "description": "Quarter-turn stairs with a landing or three winder treads",
    "category": "Add Mesh",
}

OPERATOR = "baltor.stairs_l_shaped"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "L-Shaped Stairs", "icon": "MESH_CUBE"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "L-Shaped Stairs"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "first_steps", "type": "int", "default": 6, "minimum": 1, "maximum": 60, "unit": "count",
     "description": "Treads in the first flight, along +Y."},
    {"name": "second_steps", "type": "int", "default": 5, "minimum": 1, "maximum": 60, "unit": "count",
     "description": "Treads in the second flight, after the turn."},
    {"name": "corner", "type": "choice", "default": "winders", "minimum": None, "maximum": None, "unit": "mode",
     "choices": ["landing", "winders"], "description": "Fill the corner with one landing or three winder treads."},
    {"name": "turn", "type": "choice", "default": "right", "minimum": None, "maximum": None, "unit": "mode",
     "choices": ["right", "left"], "description": "Direction of the second flight seen from the first."},
    {"name": "rise", "type": "float", "default": 0.18, "minimum": 0.05, "maximum": 0.4, "unit": "m",
     "description": "Height of one step, also between the landing and its neighbours."},
    {"name": "going", "type": "float", "default": 0.27, "minimum": 0.1, "maximum": 0.6, "unit": "m",
     "description": "Horizontal depth of one straight tread."},
    {"name": "width", "type": "float", "default": 0.9, "minimum": 0.3, "maximum": 6.0, "unit": "m",
     "description": "Width of both flights; the corner square has this side."},
    {"name": "tread_thickness", "type": "float", "default": 0.05, "minimum": 0.01, "maximum": 0.3, "unit": "m",
     "description": "Thickness of every tread and of the landing."},
    {"name": "support", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Add a block under the corner from the floor to the corner treads."},
)


def _extra_checks(p):
    if p["tread_thickness"] >= p["rise"]:
        raise ValueError("tread_thickness must be less than the rise")


# ------------------------------------------------------------------------------------------------ pure core
def _prism(vertices, faces, profile, height_low, height_high):
    """Append a vertical closed prism over a planar (x, y) polygon, faces wound outward."""
    area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(profile, profile[1:] + profile[:1]))
    if area < 0:
        profile = list(reversed(profile))
    base, count = len(vertices), len(profile)
    vertices.extend([[x, y, height_low] for x, y in profile])
    vertices.extend([[x, y, height_high] for x, y in profile])
    for index in range(count):
        following = (index + 1) % count
        faces.append([base + index, base + following, base + count + following, base + count + index])
    faces.append([base + index for index in reversed(range(count))])
    faces.append([base + count + index for index in range(count)])


def winder_outlines(width):
    """The three winder outlines in the corner square [-w/2, w/2] x [0, w], pivot at (w/2, 0), turning right."""
    pivot = (width / 2.0, 0.0)
    near = width * math.tan(math.radians(30.0))
    first = [pivot, (-width / 2.0, 0.0), (-width / 2.0, near)]
    second = [pivot, (-width / 2.0, near), (-width / 2.0, width), (width / 2.0 - near, width)]
    third = [pivot, (width / 2.0 - near, width), (width / 2.0, width)]
    return [first, second, third]


def build_geometry(**values):
    """The stairs as {"vertices", "faces", "report"}; the first flight starts at y = 0 centred on x = 0."""
    p = _validate(values)
    vertices, faces = [], []
    rise, going, width, thick = p["rise"], p["going"], p["width"], p["tread_thickness"]
    half = width / 2.0
    level = 0
    for step in range(p["first_steps"]):
        level += 1
        _prism(vertices, faces, [(-half, step * going), (half, step * going), (half, (step + 1) * going),
                                 (-half, (step + 1) * going)], level * rise - thick, level * rise)
    corner_y = p["first_steps"] * going
    corner_levels = []
    if p["corner"] == "landing":
        level += 1
        corner_levels.append(level)
        _prism(vertices, faces, [(-half, corner_y), (half, corner_y), (half, corner_y + width),
                                 (-half, corner_y + width)], level * rise - thick, level * rise)
    else:
        for outline in winder_outlines(width):
            level += 1
            corner_levels.append(level)
            _prism(vertices, faces, [(x, y + corner_y) for x, y in outline], level * rise - thick, level * rise)
    if p["support"]:
        _prism(vertices, faces, [(-half, corner_y + 0.02), (half - 0.02, corner_y + 0.02),
                                 (half - 0.02, corner_y + width - 0.02), (-half, corner_y + width - 0.02)],
               0.0, min(corner_levels) * rise - thick)
    for step in range(p["second_steps"]):
        level += 1
        x0 = half + step * going
        _prism(vertices, faces, [(x0, corner_y), (x0 + going, corner_y), (x0 + going, corner_y + width),
                                 (x0, corner_y + width)], level * rise - thick, level * rise)
    if p["turn"] == "left":
        vertices = [[-x, y, z] for x, y, z in vertices]
        faces = [list(reversed(face)) for face in faces]
    vertices = [[round(c, 9) for c in vertex] for vertex in vertices]
    report = {"total_rises": level, "total_height_m": round(level * rise, 9),
              "corner_treads": len(corner_levels), "walking_line_turn_degrees": 90.0}
    return {"vertices": vertices, "faces": faces, "report": report,
            "materials": [{"name": "Baltor Stair Concrete", "color": [0.62, 0.6, 0.57], "roughness": 0.8}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "materials": ["Baltor Stair Concrete"]}}}


def create(context=None, **values):
    """Add the stairs at the 3D cursor and return the object."""
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
