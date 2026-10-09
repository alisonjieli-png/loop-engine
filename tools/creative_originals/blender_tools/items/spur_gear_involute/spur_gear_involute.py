"""Involute spur gear from module, tooth count and pressure angle, extruded with an optional bore.

The core, build_geometry(**parameters), traces each tooth flank as the involute of the base circle, which is
what makes two gears of the same module and pressure angle mesh at a constant speed ratio. A flank point at
radius r sits at the polar angle inv(phi) = tan(phi) - phi with cos(phi) = r_base / r, offset so that the tooth
is half the circular pitch thick on the pitch circle (minus the backlash). Below the base circle the flank runs
radially to the root circle. The outline is extruded to the face width; the caps are triangulated to the bore
circle with a merge by angle (both outlines are star-shaped around the axis), or closed by one n-gon each
without a bore. It needs no Blender.

In Blender, create(context, **parameters) adds the gear at the 3D cursor, and register() adds the operator
baltor.spur_gear_involute to Add > Mesh. As a script:

    blender --background --python spur_gear_involute.py -- --teeth 32 --module 2 --output gear.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Involute Spur Gear",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Involute Spur Gear",
    "description": "Spur gear with true involute flanks from module, teeth and pressure angle",
    "category": "Add Mesh",
}

OPERATOR = "baltor.spur_gear_involute"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Involute Spur Gear", "icon": "SETTINGS"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Spur Gear"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "teeth", "type": "int", "default": 18, "minimum": 6, "maximum": 300, "unit": "count",
     "description": "Number of teeth."},
    {"name": "module", "type": "float", "default": 0.01, "minimum": 0.0002, "maximum": 1.0, "unit": "m",
     "description": "Module: pitch diameter divided by teeth (0.01 m is a module 10 gear)."},
    {"name": "pressure_angle", "type": "float", "default": 20.0, "minimum": 10.0, "maximum": 35.0,
     "unit": "degree", "description": "Pressure angle of the involute."},
    {"name": "face_width", "type": "float", "default": 0.04, "minimum": 0.0005, "maximum": 5.0, "unit": "m",
     "description": "Thickness of the gear along Z."},
    {"name": "bore_diameter", "type": "float", "default": 0.03, "minimum": 0.0, "maximum": 10.0, "unit": "m",
     "description": "Diameter of the central hole; 0 for a solid gear."},
    {"name": "backlash", "type": "float", "default": 0.0002, "minimum": 0.0, "maximum": 0.05, "unit": "m",
     "description": "Tooth thickness removed on the pitch circle, measured along the arc."},
    {"name": "flank_samples", "type": "int", "default": 6, "minimum": 2, "maximum": 40, "unit": "count",
     "description": "Points along each involute flank."},
    {"name": "smooth_bore_sides", "type": "int", "default": 32, "minimum": 8, "maximum": 256, "unit": "count",
     "description": "Segments of the bore circle."},
)


def _extra_checks(p):
    m, z = p["module"], p["teeth"]
    root = m * (z - 2.5) / 2.0
    if p["bore_diameter"] / 2.0 > root - m:
        raise ValueError("bore_diameter must leave at least one module of material under the teeth")
    if p["backlash"] >= math.pi * m / 2.0:
        raise ValueError("backlash must be smaller than half the circular pitch")


# ------------------------------------------------------------------------------------------------ pure core
def involute(angle):
    """inv(a) = tan(a) - a, the polar angle of the involute point whose pressure angle is a (radians)."""
    return math.tan(angle) - angle


def dimensions(teeth, module, pressure_angle):
    """Pitch, base, tip and root radii in metres for standard full-depth teeth (addendum m, dedendum 1.25 m)."""
    pitch = module * teeth / 2.0
    return {"pitch_radius": pitch, "base_radius": pitch * math.cos(math.radians(pressure_angle)),
            "tip_radius": pitch + module, "root_radius": pitch - 1.25 * module,
            "circular_pitch": math.pi * module}


def outline(**values):
    """The gear outline as (x, y) points counter-clockwise, one tooth after another, starting before tooth 0."""
    p = _validate(values)
    z, alpha = p["teeth"], math.radians(p["pressure_angle"])
    size = dimensions(z, p["module"], p["pressure_angle"])
    base, tip, root, pitch = size["base_radius"], size["tip_radius"], size["root_radius"], size["pitch_radius"]
    half = math.pi / (2.0 * z) - p["backlash"] / (2.0 * pitch)
    start = max(base, root)
    radii = [start + (tip - start) * index / (p["flank_samples"] - 1) for index in range(p["flank_samples"])]

    def flank_angle(radius):
        phi = math.acos(min(1.0, base / radius))
        return half + involute(alpha) - involute(phi)

    points = []
    for tooth in range(z):
        centre = 2.0 * math.pi * tooth / z
        right = []
        if root < base:
            right.append((root, centre - flank_angle(base)))
        right += [(radius, centre - flank_angle(radius)) for radius in radii]
        tip_half = flank_angle(tip)
        top = [(tip, centre - tip_half + 2 * tip_half * k / 3.0) for k in (1, 2)]
        left = [(radius, 2 * centre - angle) for radius, angle in reversed(right)]
        for radius, angle in right + top + left:
            points.append((radius * math.cos(angle), radius * math.sin(angle)))
    return points


def _zip_cap(outer, inner):
    """Triangles joining two closed star-shaped loops (lists of (index, angle)) by merging their angles."""
    triangles = []
    count_o, count_i = len(outer), len(inner)
    o = i = 0
    while o < count_o or i < count_i:
        next_o = outer[(o + 1) % count_o][1] + (2 * math.pi if o + 1 >= count_o else 0.0)
        next_i = inner[(i + 1) % count_i][1] + (2 * math.pi if i + 1 >= count_i else 0.0)
        if i >= count_i or (o < count_o and next_o <= next_i):
            triangles.append([outer[o % count_o][0], outer[(o + 1) % count_o][0], inner[i % count_i][0]])
            o += 1
        else:
            triangles.append([outer[o % count_o][0], inner[(i + 1) % count_i][0], inner[i % count_i][0]])
            i += 1
    return triangles


def build_geometry(**values):
    """The gear as {"vertices", "faces", "report"}, centred on the origin, faces from z = -w/2 to z = +w/2."""
    p = _validate(values)
    ring = outline(**p)
    half_width = p["face_width"] / 2.0
    vertices, faces = [], []
    count = len(ring)
    for z in (-half_width, half_width):
        vertices += [[x, y, z] for x, y in ring]
    for index in range(count):
        following = (index + 1) % count
        faces.append([index, following, count + following, count + index])
    angles = [math.atan2(y, x) % (2 * math.pi) for x, y in ring]
    shift = min(range(count), key=lambda index: angles[index])
    order = list(range(shift, count)) + list(range(shift))
    if p["bore_diameter"] > 0.0:
        sides, radius = p["smooth_bore_sides"], p["bore_diameter"] / 2.0
        bore = len(vertices)
        for z in (-half_width, half_width):
            vertices += [[radius * math.cos(2 * math.pi * k / sides), radius * math.sin(2 * math.pi * k / sides), z]
                         for k in range(sides)]
        for k in range(sides):
            following = (k + 1) % sides
            faces.append([bore + following, bore + k, bore + sides + k, bore + sides + following])
        for level, flip in ((0, True), (1, False)):
            outer = [(level * count + index, angles[index]) for index in order]
            inner = [(bore + level * sides + k, 2 * math.pi * k / sides) for k in range(sides)]
            for triangle in _zip_cap(outer, inner):
                faces.append(list(reversed(triangle)) if flip else triangle)
    else:
        faces.append(list(reversed(range(count))))
        faces.append(list(range(count, 2 * count)))
    vertices = [[round(c, 12) for c in vertex] for vertex in vertices]
    size = dimensions(p["teeth"], p["module"], p["pressure_angle"])
    report = {"pitch_diameter_m": round(2 * size["pitch_radius"], 9),
              "tip_diameter_m": round(2 * size["tip_radius"], 9),
              "root_diameter_m": round(2 * size["root_radius"], 9),
              "base_diameter_m": round(2 * size["base_radius"], 9),
              "circular_pitch_m": round(size["circular_pitch"], 9),
              "centre_distance_to_same_gear_m": round(2 * size["pitch_radius"], 9)}
    return {"vertices": vertices, "faces": faces, "report": report,
            "materials": [{"name": "Baltor Gear Steel", "color": [0.62, 0.63, 0.65], "roughness": 0.35,
                           "metallic": 1.0}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "materials": ["Baltor Gear Steel"], "tolerance": 1e-5}}}


def create(context=None, **values):
    """Add the gear at the 3D cursor and return the object."""
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
