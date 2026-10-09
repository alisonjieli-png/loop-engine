"""Helical compression spring: a round wire swept along a helix with closed end coils and a spring rate report.

The core, build_geometry(**parameters), integrates the helix height over the turns: the closed end coils climb by
one wire diameter per turn so neighbouring wires touch, and the active coils between them climb by the pitch.
The wire section is swept in the frame of the helix (tangent, the inward radial direction and their cross
product), which never twists, and both wire ends are capped. The report gives the free length, the solid
length and the rate k = G d^4 / (8 D^3 n) for the active coils. It needs no Blender.

In Blender, create(context, **parameters) adds the spring at the 3D cursor, and register() adds the operator
baltor.coil_spring to Add > Mesh. As a script:

    blender --background --python coil_spring.py -- --active_coils 8 --pitch 0.012 --output spring.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Coil Spring",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Coil Spring",
    "description": "Compression spring with closed end coils, swept round wire and a spring rate report",
    "category": "Add Mesh",
}

OPERATOR = "baltor.coil_spring"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Coil Spring", "icon": "MOD_SCREW"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Coil Spring"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "mean_diameter", "type": "float", "default": 0.04, "minimum": 0.002, "maximum": 5.0, "unit": "m",
     "description": "Mean coil diameter D, centre of wire to centre of wire."},
    {"name": "wire_diameter", "type": "float", "default": 0.004, "minimum": 0.0002, "maximum": 0.5, "unit": "m",
     "description": "Wire diameter d."},
    {"name": "active_coils", "type": "float", "default": 6.0, "minimum": 0.5, "maximum": 200.0, "unit": "turns",
     "description": "Active coils n between the closed ends."},
    {"name": "pitch", "type": "float", "default": 0.011, "minimum": 0.0002, "maximum": 2.0, "unit": "m",
     "description": "Rise per active coil; must exceed the wire diameter."},
    {"name": "end_coils", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 5.0, "unit": "turns",
     "description": "Closed coils at each end, climbing one wire diameter per turn."},
    {"name": "clockwise", "type": "bool", "default": False, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Left-hand winding instead of right-hand."},
    {"name": "samples_per_turn", "type": "int", "default": 28, "minimum": 6, "maximum": 128, "unit": "count",
     "description": "Sweep samples per turn."},
    {"name": "wire_sides", "type": "int", "default": 10, "minimum": 3, "maximum": 48, "unit": "count",
     "description": "Sides of the round wire section."},
    {"name": "shear_modulus", "type": "float", "default": 79.3e9, "minimum": 1.0e6, "maximum": 500.0e9,
     "unit": "Pa", "description": "Shear modulus G of the wire material (spring steel is about 79.3 GPa)."},
)


def _extra_checks(p):
    if p["pitch"] <= p["wire_diameter"]:
        raise ValueError("pitch must exceed the wire diameter or the coils intersect")
    if p["wire_diameter"] >= p["mean_diameter"] * 0.5:
        raise ValueError("wire_diameter must be under half the mean diameter")


# ------------------------------------------------------------------------------------------------ pure core
def height_at(turn, p):
    """Height of the wire centre after a given number of turns, from the start of the first end coil."""
    ends, active, d = p["end_coils"], p["active_coils"], p["wire_diameter"]
    first = min(turn, ends) * d
    middle = min(max(turn - ends, 0.0), active) * p["pitch"]
    last = max(turn - ends - active, 0.0) * d
    return first + middle + last + d / 2.0


def report(**values):
    """Free length, solid length, total turns and spring rate (N/m) of the spring."""
    p = _validate(values)
    turns = p["active_coils"] + 2 * p["end_coils"]
    free = height_at(turns, p) + p["wire_diameter"] / 2.0
    rate = p["shear_modulus"] * p["wire_diameter"] ** 4 / (8.0 * p["mean_diameter"] ** 3 * p["active_coils"])
    return {"total_turns": turns, "free_length_m": round(free, 9),
            "solid_length_m": round((turns + 1) * p["wire_diameter"], 9),
            "spring_rate_n_per_m": round(rate, 6), "spring_index": round(p["mean_diameter"] / p["wire_diameter"], 6)}


def build_geometry(**values):
    """The spring as {"vertices", "faces", "smooth", "report"}, axis along +Z from z = 0."""
    p = _validate(values)
    radius, wire = p["mean_diameter"] / 2.0, p["wire_diameter"] / 2.0
    turns = p["active_coils"] + 2 * p["end_coils"]
    samples = max(2, int(math.ceil(turns * p["samples_per_turn"])))
    sides = p["wire_sides"]
    vertices, faces = [], []
    for sample in range(samples + 1):
        turn = turns * sample / samples
        angle = 2 * math.pi * turn
        centre = [radius * math.cos(angle), radius * math.sin(angle), height_at(turn, p)]
        step = 1e-4
        ahead = [radius * math.cos(angle + 2 * math.pi * step), radius * math.sin(angle + 2 * math.pi * step),
                 height_at(turn + step, p)]
        tangent = [b - a for a, b in zip(centre, ahead)]
        length = math.sqrt(sum(c * c for c in tangent))
        tangent = [c / length for c in tangent]
        inward = [-math.cos(angle), -math.sin(angle), 0.0]
        dot = sum(a * b for a, b in zip(inward, tangent))
        normal = [a - dot * b for a, b in zip(inward, tangent)]
        length = math.sqrt(sum(c * c for c in normal))
        normal = [c / length for c in normal]
        binormal = [tangent[1] * normal[2] - tangent[2] * normal[1], tangent[2] * normal[0] - tangent[0] * normal[2],
                    tangent[0] * normal[1] - tangent[1] * normal[0]]
        for side in range(sides):
            theta = 2 * math.pi * side / sides
            c, s = math.cos(theta) * wire, math.sin(theta) * wire
            vertices.append([centre[axis] + c * normal[axis] + s * binormal[axis] for axis in range(3)])
    for sample in range(samples):
        for side in range(sides):
            a = sample * sides + side
            b = sample * sides + (side + 1) % sides
            faces.append([a, b, b + sides, a + sides])
    faces.append(list(reversed(range(sides))))
    faces.append([samples * sides + side for side in range(sides)])
    if p["clockwise"]:
        vertices = [[-x, y, z] for x, y, z in vertices]
        faces = [list(reversed(face)) for face in faces]
    vertices = [[round(c, 12) for c in vertex] for vertex in vertices]
    return {"vertices": vertices, "faces": faces, "smooth": True, "report": report(**p),
            "materials": [{"name": "Baltor Spring Steel", "color": [0.55, 0.56, 0.58], "roughness": 0.3,
                           "metallic": 1.0}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "smooth_faces": len(mesh["faces"]), "tolerance": 1e-5}}}


def create(context=None, **values):
    """Add the spring at the 3D cursor and return the object."""
    import bpy
    context = context or bpy.context
    mesh = build_geometry(**values)
    obj = _link_mesh(context, OBJECT_NAME, mesh)
    obj["baltor_spring_rate_n_per_m"] = mesh["report"]["spring_rate_n_per_m"]
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
