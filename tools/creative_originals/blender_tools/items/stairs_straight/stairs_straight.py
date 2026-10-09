"""Straight stair flight: treads with nosing, optional risers and sloped side stringers, plus a comfort report.

The core, build_geometry(**parameters), lays out `steps` treads climbing along +Y, each a closed box whose front
overhangs by the nosing, optional riser boards, and two stringers whose top edge follows the nosing line and
whose foot is cut level with the floor. Every part is a closed solid with outward counter-clockwise faces. The
core also reports the rise, going, pitch and the step formula 2R + G, which comfortable stairs keep between about
0.60 and 0.65 m. It needs no Blender.

In Blender, create(context, **parameters) adds the flight at the 3D cursor, and register() adds the operator
baltor.stairs_straight to Add > Mesh. As a script:

    blender --background --python stairs_straight.py -- --steps 14 --rise 0.18 --going 0.27 --output stairs.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Straight Stairs",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Straight Stairs",
    "description": "Straight stair flight with nosing, risers, stringers and a 2R + G comfort report",
    "category": "Add Mesh",
}

OPERATOR = "baltor.stairs_straight"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Straight Stairs", "icon": "MESH_CUBE"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Straight Stairs"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "steps", "type": "int", "default": 12, "minimum": 1, "maximum": 100, "unit": "count",
     "description": "Number of treads; the flight climbs steps times the rise."},
    {"name": "rise", "type": "float", "default": 0.175, "minimum": 0.05, "maximum": 0.4, "unit": "m",
     "description": "Height of one step."},
    {"name": "going", "type": "float", "default": 0.28, "minimum": 0.1, "maximum": 0.6, "unit": "m",
     "description": "Horizontal depth of one step, nosing to nosing."},
    {"name": "width", "type": "float", "default": 1.0, "minimum": 0.3, "maximum": 10.0, "unit": "m",
     "description": "Width of the treads between the stringers."},
    {"name": "tread_thickness", "type": "float", "default": 0.04, "minimum": 0.01, "maximum": 0.2, "unit": "m",
     "description": "Thickness of each tread board; must be less than the rise."},
    {"name": "nosing", "type": "float", "default": 0.025, "minimum": 0.0, "maximum": 0.1, "unit": "m",
     "description": "How far each tread overhangs the step below."},
    {"name": "risers", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Close each step with a vertical riser board."},
    {"name": "stringers", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Add a sloped stringer on each side."},
    {"name": "stringer_depth", "type": "float", "default": 0.25, "minimum": 0.05, "maximum": 1.0, "unit": "m",
     "description": "Vertical depth of each stringer below its top edge."},
    {"name": "stringer_thickness", "type": "float", "default": 0.04, "minimum": 0.01, "maximum": 0.2, "unit": "m",
     "description": "Thickness of each stringer board."},
)


def _extra_checks(p):
    if p["tread_thickness"] >= p["rise"]:
        raise ValueError("tread_thickness must be less than the rise")


# ------------------------------------------------------------------------------------------------ pure core
def _prism(vertices, faces, profile, extrusion):
    """Append a closed prism: a planar polygon swept along extrusion, faces wound outward."""
    nx = ny = nz = 0.0
    for index, (x1, y1, z1) in enumerate(profile):
        x2, y2, z2 = profile[(index + 1) % len(profile)]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    if nx * extrusion[0] + ny * extrusion[1] + nz * extrusion[2] < 0:
        profile = list(reversed(profile))
    base, count = len(vertices), len(profile)
    vertices.extend([list(point) for point in profile])
    vertices.extend([[point[axis] + extrusion[axis] for axis in range(3)] for point in profile])
    for index in range(count):
        following = (index + 1) % count
        faces.append([base + index, base + following, base + count + following, base + count + index])
    faces.append([base + index for index in reversed(range(count))])
    faces.append([base + count + index for index in range(count)])


def _box(vertices, faces, low, high):
    _prism(vertices, faces, [[low[0], low[1], low[2]], [high[0], low[1], low[2]], [high[0], high[1], low[2]],
                             [low[0], high[1], low[2]]], [0.0, 0.0, high[2] - low[2]])


def stringer_profile(steps, rise, going, depth):
    """The stringer outline in (y, z): top edge on the nosing line, level top end, cut at the floor (z >= 0)."""
    height, last, length = steps * rise, (steps - 1) * going, steps * going
    outline = [[length, height], [last, height], [0.0, rise], [0.0, rise - depth], [last, height - depth],
               [length, height - depth]]
    clipped = []
    for index, current in enumerate(outline):
        following = outline[(index + 1) % len(outline)]
        if current[1] >= 0.0:
            clipped.append(current)
        if (current[1] >= 0.0) != (following[1] >= 0.0):
            t = current[1] / (current[1] - following[1])
            clipped.append([current[0] + t * (following[0] - current[0]), 0.0])
    profile = []
    for point in clipped:
        if not profile or abs(point[0] - profile[-1][0]) + abs(point[1] - profile[-1][1]) > 1e-9:
            profile.append([round(point[0], 9), round(point[1], 9)])
    if len(profile) > 1 and abs(profile[0][0] - profile[-1][0]) + abs(profile[0][1] - profile[-1][1]) <= 1e-9:
        profile.pop()
    return profile


def comfort(rise, going):
    """Rise, going, pitch in degrees, 2R + G in metres, and whether 2R + G lies in [0.60, 0.65]."""
    step = 2.0 * rise + going
    return {"rise_m": rise, "going_m": going, "pitch_degrees": round(math.degrees(math.atan2(rise, going)), 6),
            "two_rise_plus_going_m": round(step, 9), "comfortable": 0.60 <= round(step, 9) <= 0.65}


def build_geometry(**values):
    """The flight as {"vertices", "faces", "report"}; it climbs along +Y from y = 0, centred on x = 0."""
    p = _validate(values)
    vertices, faces = [], []
    half, rise, going = p["width"] / 2.0, p["rise"], p["going"]
    for step in range(p["steps"]):
        top = (step + 1) * rise
        _box(vertices, faces, [-half, step * going - p["nosing"], top - p["tread_thickness"]],
             [half, (step + 1) * going, top])
        if p["risers"]:
            _box(vertices, faces, [-half, step * going, step * rise],
                 [half, step * going + 0.018, top - p["tread_thickness"]])
    if p["stringers"]:
        profile = stringer_profile(p["steps"], rise, going, p["stringer_depth"])
        for side in (-1, 1):
            x0 = half if side > 0 else -half - p["stringer_thickness"]
            _prism(vertices, faces, [[x0, y, z] for y, z in profile], [p["stringer_thickness"], 0.0, 0.0])
    vertices = [[round(c, 9) for c in vertex] for vertex in vertices]
    return {"vertices": vertices, "faces": faces, "report": comfort(rise, going),
            "materials": [{"name": "Baltor Stair Wood", "color": [0.55, 0.38, 0.22], "roughness": 0.55}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "materials": ["Baltor Stair Wood"]}}}


def create(context=None, **values):
    """Add the flight at the 3D cursor and return the object."""
    import bpy
    context = context or bpy.context
    mesh = build_geometry(**values)
    obj = _link_mesh(context, OBJECT_NAME, mesh)
    obj["baltor_two_rise_plus_going_m"] = mesh["report"]["two_rise_plus_going_m"]
    return obj


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
