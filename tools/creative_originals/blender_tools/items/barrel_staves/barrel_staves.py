"""Barrel built like a cooper's: bulged staves with gaps, flat hoops and recessed heads, each a closed solid.

The core, build_geometry(**parameters), gives the barrel a radius profile r(z) = r_head + (r_bilge - r_head) *
(1 - (2 z / H - 1)^2), a parabola that is widest at mid height (the bilge). Each stave is a curved slab between
two angles (minus half the gap on each side), between r(z) - thickness and r(z), split into rows along the
height; it is closed at both ends. Hoops are rectangular rings that follow the profile just outside the staves,
and the two heads are discs set into the ends at the croze depth. Staves, hoops and heads get separate material
slots. It needs no Blender.

In Blender, create(context, **parameters) adds the barrel at the 3D cursor, and register() adds the operator
baltor.barrel_staves to Add > Mesh. As a script:

    blender --background --python barrel_staves.py -- --staves 24 --hoops 6 --output barrel.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Barrel Staves",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Barrel",
    "description": "Barrel from bulged staves, hoops and recessed heads, each a closed solid",
    "category": "Add Mesh",
}

OPERATOR = "baltor.barrel_staves"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Barrel", "icon": "MESH_CYLINDER"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Barrel"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "height", "type": "float", "default": 0.9, "minimum": 0.05, "maximum": 20.0, "unit": "m",
     "description": "Height of the staves."},
    {"name": "head_radius", "type": "float", "default": 0.28, "minimum": 0.02, "maximum": 10.0, "unit": "m",
     "description": "Outer radius at the top and bottom."},
    {"name": "bilge_radius", "type": "float", "default": 0.34, "minimum": 0.02, "maximum": 10.0, "unit": "m",
     "description": "Outer radius at mid height; at least the head radius."},
    {"name": "staves", "type": "int", "default": 20, "minimum": 6, "maximum": 120, "unit": "count",
     "description": "Number of staves."},
    {"name": "stave_thickness", "type": "float", "default": 0.025, "minimum": 0.002, "maximum": 1.0, "unit": "m",
     "description": "Radial thickness of each stave."},
    {"name": "gap", "type": "float", "default": 0.002, "minimum": 0.0, "maximum": 0.05, "unit": "m",
     "description": "Gap between neighbouring staves at the head radius."},
    {"name": "rows", "type": "int", "default": 12, "minimum": 2, "maximum": 96, "unit": "count",
     "description": "Segments along the height of each stave and hoop."},
    {"name": "hoops", "type": "int", "default": 4, "minimum": 0, "maximum": 12, "unit": "count",
     "description": "Number of hoops, placed symmetrically."},
    {"name": "hoop_width", "type": "float", "default": 0.045, "minimum": 0.005, "maximum": 1.0, "unit": "m",
     "description": "Height of each hoop band."},
    {"name": "heads", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Close the barrel with two recessed head discs."},
)


def _extra_checks(p):
    if p["bilge_radius"] < p["head_radius"]:
        raise ValueError("bilge_radius must be at least head_radius")
    if p["stave_thickness"] >= p["head_radius"] * 0.5:
        raise ValueError("stave_thickness must be under half the head radius")
    circumference = 2 * math.pi * p["head_radius"]
    if p["gap"] * p["staves"] >= circumference * 0.5:
        raise ValueError("the gaps take more than half the circumference")
    if p["hoops"] * p["hoop_width"] > p["height"] * 0.8:
        raise ValueError("the hoops cover more than 80 percent of the height")


# ------------------------------------------------------------------------------------------------ pure core
def radius_at(z, p):
    """Outer radius of the staves at height z (a parabola widest at mid height)."""
    t = 2.0 * z / p["height"] - 1.0
    return p["head_radius"] + (p["bilge_radius"] - p["head_radius"]) * (1.0 - t * t)


def _grid_solid(vertices, faces, rows, columns, point):
    """A closed slab from point(row, column, side) over rows x columns, sides 0 (inner) and 1 (outer)."""
    base = len(vertices)
    for side in (0, 1):
        for row in range(rows + 1):
            for column in range(columns + 1):
                vertices.append(point(row, column, side))

    def index(side, row, column):
        return base + side * (rows + 1) * (columns + 1) + row * (columns + 1) + column

    for row in range(rows):
        for column in range(columns):
            faces.append([index(1, row, column), index(1, row, column + 1), index(1, row + 1, column + 1),
                          index(1, row + 1, column)])
            faces.append([index(0, row, column), index(0, row + 1, column), index(0, row + 1, column + 1),
                          index(0, row, column + 1)])
    for column in range(columns):
        faces.append([index(0, 0, column), index(0, 0, column + 1), index(1, 0, column + 1), index(1, 0, column)])
        faces.append([index(0, rows, column), index(1, rows, column), index(1, rows, column + 1),
                      index(0, rows, column + 1)])
    for row in range(rows):
        faces.append([index(0, row, 0), index(1, row, 0), index(1, row + 1, 0), index(0, row + 1, 0)])
        faces.append([index(0, row, columns), index(0, row + 1, columns), index(1, row + 1, columns),
                      index(1, row, columns)])


def build_geometry(**values):
    """The barrel as {"vertices", "faces", "face_materials", "materials", "report"}, base at z = 0."""
    p = _validate(values)
    vertices, faces, slots = [], [], []
    count, height, rows = p["staves"], p["height"], p["rows"]
    pitch = 2 * math.pi / count
    half_gap = p["gap"] / (2.0 * p["head_radius"])
    for stave in range(count):
        a0, a1 = stave * pitch + half_gap, (stave + 1) * pitch - half_gap

        def stave_point(row, column, side, a0=a0, a1=a1):
            z = height * row / rows
            angle = a0 + (a1 - a0) * column
            radius = radius_at(z, p) - (0.0 if side else p["stave_thickness"])
            return [radius * math.cos(angle), radius * math.sin(angle), z]

        before = len(faces)
        _grid_solid(vertices, faces, rows, 1, stave_point)
        slots += [0] * (len(faces) - before)
    segments = count * 2
    for hoop in range(p["hoops"]):
        centre = height * (0.07 + 0.86 * (hoop + 0.5) / p["hoops"]) if p["hoops"] > 1 else height / 2.0
        z0, z1 = centre - p["hoop_width"] / 2.0, centre + p["hoop_width"] / 2.0
        start = len(vertices)
        for z in (z0, z1):
            for side in (0, 1):
                radius = radius_at(z, p) + (0.004 if side else 0.0005)
                for k in range(segments):
                    angle = 2 * math.pi * k / segments
                    vertices.append([radius * math.cos(angle), radius * math.sin(angle), z])

        def ring(level, side, k):
            return start + (level * 2 + side) * segments + k % segments

        before = len(faces)
        for k in range(segments):
            faces.append([ring(0, 1, k), ring(0, 1, k + 1), ring(1, 1, k + 1), ring(1, 1, k)])
            faces.append([ring(0, 0, k), ring(1, 0, k), ring(1, 0, k + 1), ring(0, 0, k + 1)])
            faces.append([ring(0, 0, k), ring(0, 0, k + 1), ring(0, 1, k + 1), ring(0, 1, k)])
            faces.append([ring(1, 0, k), ring(1, 1, k), ring(1, 1, k + 1), ring(1, 0, k + 1)])
        slots += [1] * (len(faces) - before)
    if p["heads"]:
        for z in (0.06 * height, 0.94 * height):
            radius = radius_at(z, p) - p["stave_thickness"] * 0.999
            start = len(vertices)
            for level in (z - 0.012, z + 0.012):
                for k in range(segments):
                    angle = 2 * math.pi * k / segments
                    vertices.append([radius * math.cos(angle), radius * math.sin(angle), level])
            before = len(faces)
            for k in range(segments):
                k1 = (k + 1) % segments
                faces.append([start + k, start + k1, start + segments + k1, start + segments + k])
            faces.append([start + k for k in reversed(range(segments))])
            faces.append([start + segments + k for k in range(segments)])
            slots += [2] * (len(faces) - before)
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    volume = sum(math.pi * radius_at(height * (k + 0.5) / 200, p) ** 2 * height / 200 for k in range(200))
    report = {"staves": count, "hoops": p["hoops"], "outer_volume_litres": round(volume * 1000.0, 3)}
    materials = [{"name": "Baltor Oak Stave", "color": [0.42, 0.27, 0.14], "roughness": 0.7},
                 {"name": "Baltor Iron Hoop", "color": [0.18, 0.17, 0.16], "roughness": 0.45, "metallic": 1.0},
                 {"name": "Baltor Oak Head", "color": [0.36, 0.23, 0.12], "roughness": 0.75}]
    return {"vertices": vertices, "faces": faces, "face_materials": slots, "materials": materials, "report": report}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "material_indices": sorted(set(mesh["face_materials"]))}}}


def create(context=None, **values):
    """Add the barrel at the 3D cursor and return the object."""
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
