"""(p, q) torus knot tube, closed seamlessly with parallel transport and a distributed holonomy correction.

The core, build_geometry(**parameters), samples the knot curve x = (R + a cos(q t)) cos(p t),
y = (R + a cos(q t)) sin(p t), z = a sin(q t) for t in [0, 2 pi), which winds p times around the Z axis and q
times through the hole; p and q must be coprime or the curve is a link of several loops. A section is carried
along the closed curve by parallel transport (each normal is the previous one with its tangent component
removed). After one loop the transported normal comes back rotated by some angle about the tangent; that angle is
removed in equal steps along the loop, so the last ring joins the first without a twist seam. The tube is one
closed surface of genus one. It needs no Blender.

In Blender, create(context, **parameters) adds the knot at the 3D cursor, and register() adds the operator
baltor.torus_knot to Add > Mesh. As a script:

    blender --background --python torus_knot.py -- --p 3 --q 5 --output knot.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Torus Knot",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Torus Knot",
    "description": "Closed (p, q) torus knot tube without a twist seam",
    "category": "Add Mesh",
}

OPERATOR = "baltor.torus_knot"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Torus Knot", "icon": "MESH_TORUS"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Torus Knot"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "p", "type": "int", "default": 2, "minimum": 1, "maximum": 30, "unit": "count",
     "description": "Turns around the Z axis."},
    {"name": "q", "type": "int", "default": 3, "minimum": 1, "maximum": 30, "unit": "count",
     "description": "Turns through the hole; coprime with p."},
    {"name": "major_radius", "type": "float", "default": 1.0, "minimum": 0.01, "maximum": 1000.0, "unit": "m",
     "description": "Radius R of the torus the knot lies on."},
    {"name": "minor_radius", "type": "float", "default": 0.42, "minimum": 0.001, "maximum": 1000.0, "unit": "m",
     "description": "Radius a of the torus tube the knot winds around; less than R."},
    {"name": "tube_radius", "type": "float", "default": 0.13, "minimum": 0.0005, "maximum": 100.0, "unit": "m",
     "description": "Radius of the swept tube."},
    {"name": "samples", "type": "int", "default": 240, "minimum": 16, "maximum": 4000, "unit": "count",
     "description": "Rings along the knot."},
    {"name": "sides", "type": "int", "default": 12, "minimum": 3, "maximum": 64, "unit": "count",
     "description": "Sides of the tube section."},
)


def _extra_checks(p):
    if math.gcd(p["p"], p["q"]) != 1:
        raise ValueError("p and q must be coprime; otherwise the curve is a link of several loops")
    if p["minor_radius"] >= p["major_radius"]:
        raise ValueError("minor_radius must be less than major_radius")


# ------------------------------------------------------------------------------------------------ pure core
def knot_point(t, p, q, major, minor):
    """A point of the (p, q) torus knot at parameter t."""
    radius = major + minor * math.cos(q * t)
    return [radius * math.cos(p * t), radius * math.sin(p * t), minor * math.sin(q * t)]


def _unit(vector):
    length = math.sqrt(sum(c * c for c in vector))
    return [c / length for c in vector]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def transported_frames(points):
    """Tangents and twist-corrected normals along a closed polyline."""
    count = len(points)
    tangents = [_unit([points[(i + 1) % count][k] - points[i - 1][k] for k in range(3)]) for i in range(count)]
    helper = [0.0, 0.0, 1.0] if abs(tangents[0][2]) < 0.9 else [1.0, 0.0, 0.0]
    normal = _unit(_cross(_cross(tangents[0], helper), tangents[0]))
    normals = []
    for tangent in tangents + [tangents[0]]:
        dot = sum(n * t for n, t in zip(normal, tangent))
        normal = _unit([n - dot * t for n, t in zip(normal, tangent)])
        normals.append(normal)
    first, last = normals[0], normals[-1]
    binormal = _cross(tangents[0], first)
    mismatch = math.atan2(sum(a * b for a, b in zip(last, binormal)), sum(a * b for a, b in zip(last, first)))
    corrected = []
    for index in range(count):
        angle = -mismatch * index / count
        tangent, normal = tangents[index], normals[index]
        side = _cross(tangent, normal)
        corrected.append([math.cos(angle) * normal[k] + math.sin(angle) * side[k] for k in range(3)])
    return tangents, corrected, mismatch


def build_geometry(**values):
    """The knot as {"vertices", "faces", "smooth", "report"} centred on the origin."""
    p = _validate(values)
    count, sides = p["samples"], p["sides"]
    points = [knot_point(2 * math.pi * i / count, p["p"], p["q"], p["major_radius"], p["minor_radius"])
              for i in range(count)]
    tangents, normals, mismatch = transported_frames(points)
    vertices, faces = [], []
    for point, tangent, normal in zip(points, tangents, normals):
        side = _cross(tangent, normal)
        for j in range(sides):
            angle = 2 * math.pi * j / sides
            vertices.append([point[k] + p["tube_radius"] * (math.cos(angle) * normal[k] + math.sin(angle) * side[k])
                             for k in range(3)])
    for i in range(count):
        i1 = (i + 1) % count
        for j in range(sides):
            j1 = (j + 1) % sides
            faces.append([i * sides + j, i * sides + j1, i1 * sides + j1, i1 * sides + j])
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    length = sum(math.dist(points[i], points[(i + 1) % count]) for i in range(count))
    report = {"curve_length_m": round(length, 6), "transport_twist_degrees": round(math.degrees(mismatch), 6),
              "crossing_number": min(p["p"] * (p["q"] - 1), p["q"] * (p["p"] - 1))}
    return {"vertices": vertices, "faces": faces, "smooth": True, "report": report,
            "materials": [{"name": "Baltor Knot", "color": [0.7, 0.45, 0.1], "roughness": 0.3, "metallic": 1.0}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "smooth_faces": len(mesh["faces"])}}}


def create(context=None, **values):
    """Add the knot at the 3D cursor and return the object."""
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
