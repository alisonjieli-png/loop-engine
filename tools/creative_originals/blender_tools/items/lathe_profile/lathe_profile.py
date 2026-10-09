"""Lathe: revolve a 2D profile around Z into a solid of revolution, optionally hollowed into a shell.

The core, build_geometry(**parameters), reads the profile as (radius, height) points from bottom to top. A point
on the axis (radius 0) becomes a single pole vertex with a triangle fan, so no zero-area faces appear. With a wall
thickness the profile is offset inward along its averaged normals and walked back down, which turns an open
vase outline into a closed wall with a rim; if the outline starts on the axis the inner surface also ends on the
axis above the floor, so the result stays one closed solid. Optional Chaikin corner cutting rounds the profile
first. U runs around the axis and V along the profile length. It needs no Blender.

In Blender, create(context, **parameters) adds the object at the 3D cursor, and register() adds the operator
baltor.lathe_profile to Add > Mesh. As a script:

    blender --background --python lathe_profile.py -- --profile "0,0; 0.2,0; 0.25,0.3; 0.1,0.5" --output vase.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Lathe Profile",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Lathe Profile",
    "description": "Revolve a radius-height profile into a solid or a shell with poles on the axis",
    "category": "Add Mesh",
}

OPERATOR = "baltor.lathe_profile"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Lathe Profile", "icon": "MOD_SCREW"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Lathe"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "profile", "type": "string",
     "default": "0,0; 0.09,0; 0.12,0.03; 0.15,0.12; 0.155,0.22; 0.12,0.32; 0.07,0.38; 0.06,0.44; 0.075,0.47",
     "minimum": None, "maximum": None, "unit": "m",
     "description": "Profile points as radius,height pairs from bottom to top, separated by semicolons."},
    {"name": "segments", "type": "int", "default": 48, "minimum": 3, "maximum": 512, "unit": "count",
     "description": "Segments around the axis."},
    {"name": "thickness", "type": "float", "default": 0.006, "minimum": 0.0, "maximum": 10.0, "unit": "m",
     "description": "Wall thickness of a hollow shell; 0 revolves the profile as given."},
    {"name": "rounding", "type": "int", "default": 2, "minimum": 0, "maximum": 5, "unit": "count",
     "description": "Chaikin corner-cutting passes applied to the profile first."},
    {"name": "angle", "type": "float", "default": 360.0, "minimum": 1.0, "maximum": 360.0, "unit": "degree",
     "description": "Sweep angle; below 360 the cut faces are left open."},
    {"name": "smooth", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Shade smooth."},
)


def parse_profile(text):
    """[[radius, height], ...] from "r,h; r,h"; refuses negative radii and repeated points."""
    points = []
    for chunk in text.split(";"):
        if not chunk.strip():
            continue
        parts = chunk.split(",")
        if len(parts) != 2:
            raise ValueError(f"profile point {chunk.strip()!r} needs radius,height")
        try:
            r, h = float(parts[0]), float(parts[1])
        except ValueError:
            raise ValueError(f"profile point {chunk.strip()!r} is not numeric") from None
        if not (math.isfinite(r) and math.isfinite(h)) or r < 0 or abs(h) > 1e5 or r > 1e5:
            raise ValueError("radii must be at least 0 and values finite")
        points.append([r, h])
    if len(points) < 2:
        raise ValueError("the profile needs at least two points")
    if any(math.dist(a, b) < 1e-9 for a, b in zip(points, points[1:])):
        raise ValueError("consecutive profile points must differ")
    if any(r == 0.0 for r, _h in points[1:-1]):
        raise ValueError("only the first and last profile points may lie on the axis")
    return points


def _extra_checks(p):
    points = parse_profile(p["profile"])
    if p["thickness"] > 0.0 and p["angle"] < 360.0:
        raise ValueError("a hollow shell needs a full 360 degree sweep")
    if p["thickness"] > 0.0 and points[-1][0] == 0.0:
        raise ValueError("a hollow shell needs an open top (last radius above 0)")


# ------------------------------------------------------------------------------------------------ pure core
def chaikin(points, passes):
    """Corner cutting that keeps both end points: each pass replaces a segment by its 1/4 and 3/4 points."""
    for _ in range(passes):
        refined = [points[0]]
        for a, b in zip(points, points[1:]):
            refined += [[0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]],
                        [0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]]]
        refined.append(points[-1])
        points = [refined[0]] + refined[2:-2] + [refined[-1]] if len(refined) > 4 else refined
    return points


def shell_profile(points, thickness):
    """The closed outline of a wall: the outer profile up, then the inner offset back down."""
    inner = []
    count = len(points)
    for index, (r, h) in enumerate(points):
        normals = []
        for a, b in ((points[index - 1], points[index]) if index > 0 else (None, None),
                     (points[index], points[index + 1]) if index < count - 1 else (None, None)):
            if a is not None:
                dr, dh = b[0] - a[0], b[1] - a[1]
                length = math.hypot(dr, dh)
                normals.append((dh / length, -dr / length))
        nr, nh = (sum(n[0] for n in normals) / len(normals), sum(n[1] for n in normals) / len(normals))
        length = math.hypot(nr, nh) or 1.0
        inner.append([r - thickness * nr / length, h - thickness * nh / length])
    if points[0][0] == 0.0:
        inner[0] = [0.0, points[0][1] + thickness]
    inner = [[max(0.0, r), h] for r, h in inner]
    if any(r <= 0.0 for r, _h in inner[1:]):
        raise ValueError("the wall thickness is larger than the profile allows")
    return points + list(reversed(inner))


def build_geometry(**values):
    """The solid as {"vertices", "faces", "uv", "smooth"}, axis along Z through the origin."""
    p = _validate(values)
    points = chaikin(parse_profile(p["profile"]), p["rounding"])
    closed_loop = p["thickness"] > 0.0
    outline = shell_profile(points, p["thickness"]) if closed_loop else points
    full = p["angle"] >= 360.0
    columns = p["segments"] if full else p["segments"] + 1
    sweep = math.radians(p["angle"])
    vertices, faces, uv, rows = [], [], [], []
    lengths = [0.0]
    for a, b in zip(outline, outline[1:]):
        lengths.append(lengths[-1] + math.dist(a, b))
    total = lengths[-1] or 1.0
    for r, h in outline:
        if r == 0.0:
            rows.append([len(vertices)])
            vertices.append([0.0, 0.0, h])
        else:
            row = []
            for k in range(columns):
                angle = sweep * k / p["segments"]
                row.append(len(vertices))
                vertices.append([r * math.cos(angle), r * math.sin(angle), h])
            rows.append(row)
    spans = p["segments"]
    pairs = [(index, index + 1) for index in range(len(outline) - 1)]
    if closed_loop and len(rows[0]) > 1 and len(rows[-1]) > 1:
        pairs.append((len(outline) - 1, 0))
        lengths.append(total + math.dist(outline[-1], outline[0]))
    for index, following in pairs:
        low, high = rows[index], rows[following]
        v0, v1 = lengths[index] / total, lengths[index + 1] / total
        for k in range(spans):
            k1 = (k + 1) % columns if full else k + 1
            u0, u1 = k / spans, (k + 1) / spans
            if len(low) == 1:
                faces.append([low[0], high[k1], high[k]])
                uv += [[(u0 + u1) / 2, v0], [u1, v1], [u0, v1]]
            elif len(high) == 1:
                faces.append([low[k], low[k1], high[0]])
                uv += [[u0, v0], [u1, v0], [(u0 + u1) / 2, v1]]
            else:
                faces.append([low[k], low[k1], high[k1], high[k]])
                uv += [[u0, v0], [u1, v0], [u1, v1], [u0, v1]]
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    return {"vertices": vertices, "faces": faces, "uv": uv, "smooth": p["smooth"],
            "materials": [{"name": "Baltor Glazed Ceramic", "color": [0.55, 0.18, 0.12], "roughness": 0.25}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "uv_layers": ["UVMap"]}}}


def create(context=None, **values):
    """Add the solid of revolution at the 3D cursor and return the object."""
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
