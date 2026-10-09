"""Hanging cable between two points: the catenary for a given length, swept as a round tube.

The core, build_geometry(**parameters), solves for the catenary y = a cosh((x - x0) / a) + c through both
anchors with arc length L = slack * chord. With horizontal span h and height difference v, the shape parameter a
satisfies sqrt(L^2 - v^2) = 2 a sinh(h / (2 a)), found by bisection on a; then
x0 = h / 2 - a asinh(v / (2 a sinh(h / (2 a)))). Points are sampled evenly along x in the vertical plane through
both anchors, and a round section is swept along them with parallel transported frames and capped. The report
gives the sag below the chord and the tension ratio at the anchors. It needs no Blender.

In Blender, create(context, **parameters) adds the cable, and register() adds the operator baltor.catenary_cable
to Add > Mesh. As a script:

    blender --background --python catenary_cable.py -- --start 0,0,4 --end 8,0,3 --slack 1.04 --output cable.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Catenary Cable",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Catenary Cable",
    "description": "Cable hanging between two points as an exact catenary of a given length",
    "category": "Add Mesh",
}

OPERATOR = "baltor.catenary_cable"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Catenary Cable", "icon": "CURVE_PATH"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Catenary Cable"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "start", "type": "vector", "default": [0.0, 0.0, 3.0], "minimum": -100000.0, "maximum": 100000.0,
     "unit": "m", "description": "First anchor point."},
    {"name": "end", "type": "vector", "default": [6.0, 1.5, 2.4], "minimum": -100000.0, "maximum": 100000.0,
     "unit": "m", "description": "Second anchor point; must differ horizontally from start."},
    {"name": "slack", "type": "float", "default": 1.05, "minimum": 1.0001, "maximum": 5.0, "unit": "ratio",
     "description": "Cable length divided by the straight distance between the anchors."},
    {"name": "radius", "type": "float", "default": 0.015, "minimum": 0.0005, "maximum": 2.0, "unit": "m",
     "description": "Radius of the cable."},
    {"name": "segments", "type": "int", "default": 48, "minimum": 4, "maximum": 1000, "unit": "count",
     "description": "Segments along the cable."},
    {"name": "sides", "type": "int", "default": 8, "minimum": 3, "maximum": 64, "unit": "count",
     "description": "Sides of the cable section."},
)


def _extra_checks(p):
    if math.hypot(p["end"][0] - p["start"][0], p["end"][1] - p["start"][1]) < 1e-3:
        raise ValueError("the anchors must be at least 1 mm apart horizontally")


# ------------------------------------------------------------------------------------------------ pure core
def solve_parameter(span, rise, length):
    """The catenary parameter a for horizontal span, height difference and arc length (bisection on a).

    f(a) = 2 a sinh(span / (2 a)) falls from infinity toward span as a grows, so one root exists when
    sqrt(length^2 - rise^2) > span."""
    target = math.sqrt(length * length - rise * rise)
    if target <= span:
        raise ValueError("the cable is not longer than the straight distance")

    def chord(a):
        return 2.0 * a * math.sinh(min(span / (2.0 * a), 700.0))

    high = span
    while chord(high) > target:
        high *= 2.0
    low = high
    while chord(low) < target and low > span / 1400.0:
        low /= 2.0
    for _ in range(200):
        middle = (low + high) / 2.0
        low, high = (middle, high) if chord(middle) > target else (low, middle)
    return (low + high) / 2.0


def curve(**values):
    """Sample points of the catenary in world space and its shape numbers."""
    p = _validate(values)
    start, end = p["start"], p["end"]
    dx, dy = end[0] - start[0], end[1] - start[1]
    span = math.hypot(dx, dy)
    rise = end[2] - start[2]
    length = p["slack"] * math.sqrt(span * span + rise * rise)
    a = solve_parameter(span, rise, length)
    x0 = span / 2.0 - a * math.asinh(rise / (2 * a * math.sinh(span / (2 * a))))
    c = -a * math.cosh(-x0 / a)
    ux, uy = dx / span, dy / span
    points = []
    for index in range(p["segments"] + 1):
        x = span * index / p["segments"]
        z = a * math.cosh((x - x0) / a) + c
        points.append([start[0] + ux * x, start[1] + uy * x, start[2] + z])
    lowest = c + a if 0.0 <= x0 <= span else min(0.0, rise)
    sag = max(rise * x / span - (a * math.cosh((x - x0) / a) + c) for x in (span * k / 200 for k in range(201)))
    slope_start = abs(math.sinh(-x0 / a))
    slope_end = abs(math.sinh((span - x0) / a))
    return points, {"parameter_a_m": round(a, 9), "length_m": round(length, 9), "sag_below_chord_m": round(sag, 9),
                    "lowest_point_z_m": round(start[2] + lowest, 9),
                    "anchor_tension_over_horizontal": [round(math.sqrt(1 + slope_start ** 2), 9),
                                                       round(math.sqrt(1 + slope_end ** 2), 9)]}


def build_geometry(**values):
    """The cable as {"vertices", "faces", "smooth", "report"} in world coordinates of the anchors."""
    p = _validate(values)
    points, numbers = curve(**p)
    tangents = []
    for index in range(len(points)):
        a = points[max(index - 1, 0)]
        b = points[min(index + 1, len(points) - 1)]
        vector = [y - x for x, y in zip(a, b)]
        length = math.sqrt(sum(v * v for v in vector))
        tangents.append([v / length for v in vector])
    helper = [0.0, 0.0, 1.0]
    first = tangents[0]
    normal = [helper[k] - sum(h * t for h, t in zip(helper, first)) * first[k] for k in range(3)]
    if math.sqrt(sum(v * v for v in normal)) < 1e-6:
        normal = [1.0, 0.0, 0.0]
    vertices, faces = [], []
    sides = p["sides"]
    for point, tangent in zip(points, tangents):
        dot = sum(n * t for n, t in zip(normal, tangent))
        normal = [n - dot * t for n, t in zip(normal, tangent)]
        length = math.sqrt(sum(v * v for v in normal))
        normal = [v / length for v in normal]
        binormal = [tangent[1] * normal[2] - tangent[2] * normal[1], tangent[2] * normal[0] - tangent[0] * normal[2],
                    tangent[0] * normal[1] - tangent[1] * normal[0]]
        for side in range(sides):
            angle = 2 * math.pi * side / sides
            vertices.append([point[k] + p["radius"] * (math.cos(angle) * normal[k] + math.sin(angle) * binormal[k])
                             for k in range(3)])
    rings = len(points)
    for ring in range(rings - 1):
        for side in range(sides):
            a, b = ring * sides + side, ring * sides + (side + 1) % sides
            faces.append([a, b, b + sides, a + sides])
    faces.append(list(reversed(range(sides))))
    faces.append([(rings - 1) * sides + side for side in range(sides)])
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    return {"vertices": vertices, "faces": faces, "smooth": True, "report": numbers,
            "materials": [{"name": "Baltor Cable Rubber", "color": [0.03, 0.03, 0.035], "roughness": 0.5}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "location": [0.0, 0.0, 0.0]}}}


def create(context=None, **values):
    """Add the cable between the anchors (world coordinates) and return the object."""
    import bpy
    context = context or bpy.context
    obj = _link_mesh(context, OBJECT_NAME, build_geometry(**values))
    obj.location = (0.0, 0.0, 0.0)
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
