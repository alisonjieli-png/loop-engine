"""Pipe run along a polyline: straight runs joined by bent elbows of a given bend radius, with flanges.

The core, build_geometry(**parameters), replaces every corner of the polyline by a circular arc tangent to both
runs: the arc starts R * tan(theta / 2) before the corner and ends as far after it, where theta is the turn
angle and R the bend radius, and its centre lies on the corner's bisector. The pipe section is swept along the
resulting centreline with rotation-minimising frames (the double reflection method), so the wall does not twist
through the bends, and both ends are capped. Optional flanges are short closed cylinders at the ends and at every
joint between a straight run and an elbow. It needs no Blender.

In Blender, create(context, **parameters) adds the pipe at the 3D cursor, and register() adds the operator
baltor.pipe_run_elbows to Add > Mesh. As a script:

    blender --background --python pipe_run_elbows.py -- --points "0,0,0; 3,0,0; 3,2,0; 3,2,2" --output pipe.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Pipe Run With Elbows",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Pipe Run",
    "description": "Pipe along a polyline with tangent elbows, twist-free sweep and flanges",
    "category": "Add Mesh",
}

OPERATOR = "baltor.pipe_run_elbows"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Pipe Run", "icon": "MESH_CYLINDER"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Pipe Run"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "points", "type": "string", "default": "0,0,0; 2.5,0,0; 2.5,2,0; 2.5,2,1.6; 0.5,2,1.6",
     "minimum": None, "maximum": None, "unit": "m", "description": "Centreline corners as x,y,z separated by semicolons."},
    {"name": "radius", "type": "float", "default": 0.08, "minimum": 0.002, "maximum": 5.0, "unit": "m",
     "description": "Outer radius of the pipe."},
    {"name": "bend_radius", "type": "float", "default": 0.24, "minimum": 0.004, "maximum": 50.0, "unit": "m",
     "description": "Centreline radius of every elbow; at least the pipe radius."},
    {"name": "sides", "type": "int", "default": 16, "minimum": 3, "maximum": 128, "unit": "count",
     "description": "Sides of the pipe section."},
    {"name": "bend_segments", "type": "int", "default": 10, "minimum": 1, "maximum": 96, "unit": "count",
     "description": "Segments along a 90 degree elbow; other angles scale."},
    {"name": "flanges", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Add flanges at both ends and at every elbow joint."},
    {"name": "flange_ratio", "type": "float", "default": 1.6, "minimum": 1.05, "maximum": 4.0, "unit": "ratio",
     "description": "Flange radius divided by the pipe radius."},
)


def parse_points(text):
    """[[x, y, z], ...] from text like "0,0,0; 1,0,0"; raises ValueError on malformed or repeated points."""
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
        raise ValueError("points needs at least two corners")
    if any(math.dist(a, b) < 1e-6 for a, b in zip(points, points[1:])):
        raise ValueError("consecutive points must differ")
    return points


def _extra_checks(p):
    parse_points(p["points"])
    if p["bend_radius"] < p["radius"]:
        raise ValueError("bend_radius must be at least the pipe radius")


# ------------------------------------------------------------------------------------------------ pure core
def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _unit(a):
    length = math.sqrt(_dot(a, a))
    return [x / length for x in a]


def _rotate(vector, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    cross, dot = _cross(axis, vector), _dot(axis, vector)
    return [vector[i] * c + cross[i] * s + axis[i] * dot * (1 - c) for i in range(3)]


def centreline(**values):
    """Samples [(point, tangent)], the joints where runs meet elbows, and the bends as (angle in degrees)."""
    p = _validate(values)
    points, bend = parse_points(p["points"]), p["bend_radius"]
    count = len(points)
    directions = [_unit(_sub(points[i + 1], points[i])) for i in range(count - 1)]
    cuts, arcs = [0.0] * count, {}
    for i in range(1, count - 1):
        d_in, d_out = directions[i - 1], directions[i]
        angle = math.acos(max(-1.0, min(1.0, _dot(d_in, d_out))))
        if angle > math.pi - 1e-3:
            raise ValueError(f"the path reverses at point {i}")
        if angle > 1e-6:
            cuts[i] = bend * math.tan(angle / 2.0)
            arcs[i] = angle
    for i in range(count - 1):
        if cuts[i] + cuts[i + 1] > math.dist(points[i], points[i + 1]) + 1e-9:
            raise ValueError(f"segment {i} is too short for the bend radius")
    samples, joints = [(points[0], directions[0])], [(points[0], directions[0])]
    for i in range(1, count - 1):
        d_in, d_out = directions[i - 1], directions[i]
        if i not in arcs:
            samples.append((points[i], d_in))
            continue
        angle = arcs[i]
        start = [points[i][k] - d_in[k] * cuts[i] for k in range(3)]
        bisector = _unit(_sub(d_out, d_in))
        centre = [points[i][k] + bisector[k] * bend / math.cos(angle / 2.0) for k in range(3)]
        axis = _unit(_cross(d_in, d_out))
        steps = max(1, int(math.ceil(p["bend_segments"] * angle / (math.pi / 2.0))))
        offset = _sub(start, centre)
        for step in range(steps + 1):
            phi = angle * step / steps
            point = [centre[k] + v for k, v in enumerate(_rotate(offset, axis, phi))]
            samples.append((point, _rotate(d_in, axis, phi)))
        joints += [samples[-steps - 1], samples[-1]]
    samples.append((points[-1], directions[-1]))
    joints.append(samples[-1])
    unique = [samples[0]]
    for sample in samples[1:]:
        if math.dist(sample[0], unique[-1][0]) > 1e-9:
            unique.append(sample)
    return unique, joints, [round(math.degrees(angle), 9) for _i, angle in sorted(arcs.items())]


def _frames(samples):
    """Rotation-minimising normals along the samples by the double reflection method."""
    tangent = samples[0][1]
    helper = [0.0, 0.0, 1.0] if abs(tangent[2]) < 0.9 else [1.0, 0.0, 0.0]
    normal = _unit(_cross(_cross(tangent, helper), tangent))
    normals = [normal]
    for (x0, t0), (x1, t1) in zip(samples, samples[1:]):
        v1 = _sub(x1, x0)
        c1 = _dot(v1, v1)
        r = normals[-1]
        r_l = [r[k] - 2.0 / c1 * _dot(v1, r) * v1[k] for k in range(3)]
        t_l = [t0[k] - 2.0 / c1 * _dot(v1, t0) * v1[k] for k in range(3)]
        v2 = _sub(t1, t_l)
        c2 = _dot(v2, v2)
        normals.append(_unit([r_l[k] - 2.0 / c2 * _dot(v2, r_l) * v2[k] for k in range(3)]) if c2 > 1e-18
                       else _unit(r_l))
    return normals


def _ring(centre, tangent, normal, radius, sides):
    binormal = _cross(tangent, normal)
    return [[centre[k] + radius * (math.cos(2 * math.pi * j / sides) * normal[k]
                                   + math.sin(2 * math.pi * j / sides) * binormal[k]) for k in range(3)]
            for j in range(sides)]


def _tube(vertices, faces, rings):
    base, sides = len(vertices), len(rings[0])
    for ring in rings:
        vertices.extend(ring)
    for r in range(len(rings) - 1):
        for j in range(sides):
            a, b = base + r * sides + j, base + r * sides + (j + 1) % sides
            faces.append([a, b, b + sides, a + sides])
    faces.append([base + j for j in reversed(range(sides))])
    faces.append([base + (len(rings) - 1) * sides + j for j in range(sides)])


def build_geometry(**values):
    """The pipe as {"vertices", "faces", "smooth", "report"} in the coordinates of the given points."""
    p = _validate(values)
    samples, joints, bends = centreline(**p)
    normals = _frames(samples)
    vertices, faces = [], []
    _tube(vertices, faces, [_ring(point, tangent, normal, p["radius"], p["sides"])
                            for (point, tangent), normal in zip(samples, normals)])
    if p["flanges"]:
        width = p["radius"] * 0.6
        for point, tangent in joints:
            helper = [0.0, 0.0, 1.0] if abs(tangent[2]) < 0.9 else [1.0, 0.0, 0.0]
            normal = _unit(_cross(_cross(tangent, helper), tangent))
            ends = [[point[k] - tangent[k] * width / 2 for k in range(3)],
                    [point[k] + tangent[k] * width / 2 for k in range(3)]]
            _tube(vertices, faces, [_ring(end, tangent, normal, p["radius"] * p["flange_ratio"], p["sides"])
                                    for end in ends])
    length = sum(math.dist(a[0], b[0]) for a, b in zip(samples, samples[1:]))
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    report = {"elbows": len(bends), "bend_angles_degrees": bends, "centreline_length_m": round(length, 6),
              "flanges": len(joints) if p["flanges"] else 0}
    return {"vertices": vertices, "faces": faces, "smooth": True, "report": report,
            "materials": [{"name": "Baltor Pipe Paint", "color": [0.12, 0.3, 0.55], "roughness": 0.45}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high]}}}


def create(context=None, **values):
    """Add the pipe at the 3D cursor and return the object."""
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
