"""Picket fence along a path: posts with pyramid caps, two rails per bay and pickets with a chosen top.

The core, build_geometry(**parameters), walks the path segment by segment. Each segment gets posts at both ends
and as many evenly spaced intermediate posts as needed to keep bays at or under the post spacing. Two rails run
between neighbouring posts on the front side, following the slope of the ground between the path points, and
pickets are spaced evenly along the bay in front of the rails with their bottoms on the sloped ground. Pickets
are extruded profiles (pointed, flat, rounded or dog-ear tops); posts and rails are closed hexahedra. It needs
no Blender.

In Blender, create(context, **parameters) adds the fence at the 3D cursor, and register() adds the operator
baltor.picket_fence to Add > Mesh. As a script:

    blender --background --python picket_fence.py -- --points "0,0,0; 6,0,0; 6,4,0.5" --top round --output f.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Picket Fence",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Picket Fence",
    "description": "Picket fence along a path with capped posts, sloped rails and shaped picket tops",
    "category": "Add Mesh",
}

OPERATOR = "baltor.picket_fence"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Picket Fence", "icon": "MOD_LATTICE"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Picket Fence"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "points", "type": "string", "default": "0,0,0; 4,0,0; 4,3,0.3", "minimum": None, "maximum": None,
     "unit": "m", "description": "Ground path as x,y,z points separated by semicolons."},
    {"name": "height", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 5.0, "unit": "m",
     "description": "Height of the pickets above the ground."},
    {"name": "post_spacing", "type": "float", "default": 2.0, "minimum": 0.5, "maximum": 10.0, "unit": "m",
     "description": "Largest distance between neighbouring posts."},
    {"name": "post_size", "type": "float", "default": 0.09, "minimum": 0.02, "maximum": 0.5, "unit": "m",
     "description": "Side of the square posts."},
    {"name": "picket_width", "type": "float", "default": 0.075, "minimum": 0.01, "maximum": 0.5, "unit": "m",
     "description": "Width of each picket."},
    {"name": "picket_gap", "type": "float", "default": 0.05, "minimum": 0.005, "maximum": 0.5, "unit": "m",
     "description": "Target gap between pickets; the actual gap is adjusted to fill each bay evenly."},
    {"name": "picket_thickness", "type": "float", "default": 0.02, "minimum": 0.005, "maximum": 0.2, "unit": "m",
     "description": "Thickness of each picket."},
    {"name": "top", "type": "choice", "default": "pointed", "minimum": None, "maximum": None, "unit": "style",
     "choices": ["pointed", "flat", "round", "dog_ear"], "description": "Shape of the picket tops."},
)


def parse_points(text):
    """[[x, y, z], ...] from text like "0,0,0; 4,0,0"; raises ValueError on malformed input."""
    points = []
    for chunk in text.split(";"):
        if not chunk.strip():
            continue
        parts = chunk.split(",")
        if len(parts) != 3:
            raise ValueError(f"point {chunk.strip()!r} needs three numbers")
        try:
            point = [float(part) for part in parts]
        except ValueError:
            raise ValueError(f"point {chunk.strip()!r} is not numeric") from None
        if not all(math.isfinite(value) and abs(value) <= 1e5 for value in point):
            raise ValueError("points must be finite and within 100 km")
        points.append(point)
    if len(points) < 2:
        raise ValueError("points needs at least two points")
    return points


def _extra_checks(p):
    points = parse_points(p["points"])
    for a, b in zip(points, points[1:]):
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 2.5 * p["post_size"]:
            raise ValueError("every path segment must be longer than two and a half post sizes horizontally")
    if p["picket_width"] + p["picket_gap"] > p["post_spacing"] - p["post_size"]:
        raise ValueError("a picket and its gap must fit in one bay")


# ------------------------------------------------------------------------------------------------ pure core
def _hexa(vertices, faces, origin, a, b, c):
    """A closed hexahedron origin + i a + j b + k c, assuming (a x b) . c > 0."""
    base = len(vertices)
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                vertices.append([origin[n] + i * a[n] + j * b[n] + k * c[n] for n in range(3)])

    def at(i, j, k):
        return base + i * 4 + j * 2 + k

    for face in (((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
                 ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
                 ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))):
        faces.append([at(*corner) for corner in face])


def _extrude(vertices, faces, profile, extrusion):
    """A closed prism from a planar polygon swept along extrusion, wound outward."""
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


def picket_outline(width, height, top):
    """The picket outline in (along, up) coordinates from the bottom left, counter-clockwise."""
    if top == "flat":
        return [[0.0, 0.0], [width, 0.0], [width, height], [0.0, height]]
    if top == "pointed":
        return [[0.0, 0.0], [width, 0.0], [width, height - width * 0.6], [width / 2, height],
                [0.0, height - width * 0.6]]
    if top == "dog_ear":
        cut = width * 0.3
        return [[0.0, 0.0], [width, 0.0], [width, height - cut], [width - cut, height], [cut, height],
                [0.0, height - cut]]
    radius = width / 2.0
    arc = [[radius + radius * math.cos(math.pi * k / 8), height - radius + radius * math.sin(math.pi * k / 8)]
           for k in range(9)]
    return [[0.0, 0.0], [width, 0.0]] + arc[:-1] + [[0.0, height - radius]]


def _post(vertices, faces, centre, size, height):
    half = size / 2.0
    base = len(vertices)
    ring = [[-half, -half], [half, -half], [half, half], [-half, half]]
    vertices += [[centre[0] + x, centre[1] + y, centre[2]] for x, y in ring]
    vertices += [[centre[0] + x, centre[1] + y, centre[2] + height] for x, y in ring]
    vertices.append([centre[0], centre[1], centre[2] + height + size * 0.5])
    faces.append([base + 3, base + 2, base + 1, base])
    for k in range(4):
        k1 = (k + 1) % 4
        faces.append([base + k, base + k1, base + 4 + k1, base + 4 + k])
        faces.append([base + 4 + k, base + 4 + k1, base + 8])


def build_geometry(**values):
    """The fence as {"vertices", "faces", "face_materials", "materials", "report"} in path coordinates."""
    p = _validate(values)
    points = parse_points(p["points"])
    vertices, faces, slots = [], [], []
    posts = pickets = rails = 0
    outline = picket_outline(p["picket_width"], p["height"], p["top"])
    size = p["post_size"]
    placed = []
    for a, b in zip(points, points[1:]):
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        length = math.hypot(dx, dy)
        u = [dx / length, dy / length, 0.0]
        n = [-u[1], u[0], 0.0]
        bays = max(1, math.ceil(length / p["post_spacing"] - 1e-9))
        for bay in range(bays + 1):
            t = bay / bays
            centre = [a[0] + dx * t, a[1] + dy * t, a[2] + dz * t]
            if not any(math.dist(centre, other) < 1e-6 for other in placed):
                before = len(faces)
                _post(vertices, faces, centre, size, p["height"] + 0.08)
                slots += [0] * (len(faces) - before)
                placed.append(centre)
                posts += 1
        for bay in range(bays):
            t0, t1 = bay / bays, (bay + 1) / bays
            start = [a[0] + dx * t0 + u[0] * size / 2, a[1] + dy * t0 + u[1] * size / 2, a[2] + dz * t0]
            span = length / bays - size
            rise = dz / bays * (span / (length / bays))
            front = size / 2.0
            for level in (0.22, 0.72):
                origin = [start[0] + n[0] * front, start[1] + n[1] * front, start[2] + level * p["height"]]
                before = len(faces)
                _hexa(vertices, faces, origin, [u[0] * span, u[1] * span, rise], [n[0] * 0.03, n[1] * 0.03, 0.0],
                      [0.0, 0.0, 0.07])
                slots += [1] * (len(faces) - before)
                rails += 1
            count = max(1, int((span + p["picket_gap"]) // (p["picket_width"] + p["picket_gap"])))
            gap = (span - count * p["picket_width"]) / (count + 1)
            for k in range(count):
                offset = gap + k * (p["picket_width"] + gap)
                ground = start[2] + rise * (offset + p["picket_width"] / 2) / span
                corner = [start[0] + u[0] * offset + n[0] * (front + 0.03), start[1] + u[1] * offset
                          + n[1] * (front + 0.03), ground + 0.03]
                profile = [[corner[0] + u[0] * x, corner[1] + u[1] * x, corner[2] + y] for x, y in outline]
                before = len(faces)
                _extrude(vertices, faces, profile, [n[0] * p["picket_thickness"], n[1] * p["picket_thickness"],
                                                    0.0])
                slots += [2] * (len(faces) - before)
                pickets += 1
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))
    report = {"posts": posts, "rails": rails, "pickets": pickets, "path_length_m": round(length, 6)}
    materials = [{"name": "Baltor Fence Post", "color": [0.82, 0.82, 0.8], "roughness": 0.6},
                 {"name": "Baltor Fence Rail", "color": [0.78, 0.78, 0.76], "roughness": 0.6},
                 {"name": "Baltor Fence Picket", "color": [0.9, 0.9, 0.88], "roughness": 0.55}]
    return {"vertices": vertices, "faces": faces, "face_materials": slots, "materials": materials, "report": report}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "material_indices": [0, 1, 2]}}}


def create(context=None, **values):
    """Add the fence at the 3D cursor and return the object."""
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
