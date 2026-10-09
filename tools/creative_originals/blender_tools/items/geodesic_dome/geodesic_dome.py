"""Geodesic dome of any frequency: struts and hubs or a thick panel shell, with its strut length classes.

The core, build_geometry(**parameters), turns an icosahedron so one vertex points up, splits every face into a
triangular grid of the chosen frequency (class I subdivision), projects the grid points onto the sphere and keeps
the triangles of the upper half. With an even frequency the cut follows grid edges on the equator, so the rim is
flat; with an odd frequency the kept triangles end in a stepped rim, and the dome is lifted to stand on z = 0.
Struts mode builds a hexagonal prism for every edge and a small icosphere hub at every vertex; panels mode
offsets the surface inward by the thickness and closes the rim. The report lists the distinct strut lengths with
their counts and chord factors, which is what a builder cuts. It needs no Blender.

In Blender, create(context, **parameters) adds the dome at the 3D cursor, and register() adds the operator
baltor.geodesic_dome to Add > Mesh. As a script:

    blender --background --python geodesic_dome.py -- --frequency 4 --mode panels --output dome.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Geodesic Dome",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Geodesic Dome",
    "description": "Geodesic dome of any frequency as struts and hubs or a panel shell, with strut lengths",
    "category": "Add Mesh",
}

OPERATOR = "baltor.geodesic_dome"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Geodesic Dome", "icon": "MESH_ICOSPHERE"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Geodesic Dome"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "frequency", "type": "int", "default": 2, "minimum": 1, "maximum": 10, "unit": "count",
     "description": "Divisions of each icosahedron edge; even values give a flat rim."},
    {"name": "radius", "type": "float", "default": 3.0, "minimum": 0.05, "maximum": 1000.0, "unit": "m",
     "description": "Radius of the sphere the hubs lie on."},
    {"name": "mode", "type": "choice", "default": "struts", "minimum": None, "maximum": None, "unit": "mode",
     "choices": ["struts", "panels"], "description": "Struts with hubs, or a closed panel shell."},
    {"name": "strut_radius", "type": "float", "default": 0.035, "minimum": 0.001, "maximum": 10.0, "unit": "m",
     "description": "Radius of each hexagonal strut (struts mode)."},
    {"name": "hub_radius", "type": "float", "default": 0.07, "minimum": 0.001, "maximum": 20.0, "unit": "m",
     "description": "Radius of each hub (struts mode)."},
    {"name": "thickness", "type": "float", "default": 0.08, "minimum": 0.001, "maximum": 50.0, "unit": "m",
     "description": "Shell thickness (panels mode)."},
)


def _extra_checks(p):
    if p["mode"] == "panels" and p["thickness"] >= p["radius"] * 0.5:
        raise ValueError("thickness must be under half the radius")
    if p["mode"] == "struts" and p["hub_radius"] < p["strut_radius"]:
        raise ValueError("hub_radius must be at least strut_radius")


# ------------------------------------------------------------------------------------------------ pure core
def icosahedron_vertex_up():
    """The 12 unit icosahedron vertices turned so that one lies on +Z, and its 20 faces."""
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    raw = [(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0), (0, -1, phi), (0, 1, phi), (0, -1, -phi),
           (0, 1, -phi), (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)]
    alpha = math.atan2(1.0, phi)
    c, s = math.cos(alpha), math.sin(alpha)
    norm = math.sqrt(1.0 + phi * phi)
    vertices = [[x / norm, (y * c - z * s) / norm, (y * s + z * c) / norm] for x, y, z in raw]
    faces = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
             [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11],
             [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    return vertices, faces


def dome_surface(frequency, radius):
    """Hub positions and outward triangles of the upper half of a class I geodesic sphere."""
    base, faces = icosahedron_vertex_up()
    index, points, triangles = {}, [], []

    def point(a, b, c, i, j):
        k = frequency - i - j
        raw = [(base[a][n] * k + base[b][n] * i + base[c][n] * j) / frequency for n in range(3)]
        length = math.sqrt(sum(value * value for value in raw))
        unit = [value / length for value in raw]
        key = tuple(round(value, 9) for value in unit)
        if key not in index:
            index[key] = len(points)
            points.append([value * radius for value in unit])
        return index[key]

    for a, b, c in faces:
        for i in range(frequency):
            for j in range(frequency - i):
                triangles.append([point(a, b, c, i, j), point(a, b, c, i + 1, j), point(a, b, c, i, j + 1)])
                if i + j < frequency - 1:
                    triangles.append([point(a, b, c, i + 1, j), point(a, b, c, i + 1, j + 1),
                                      point(a, b, c, i, j + 1)])
    keep = [tri for tri in triangles if min(points[v][2] for v in tri) >= -1e-9 * radius]
    used = sorted({v for tri in keep for v in tri})
    remap = {old: new for new, old in enumerate(used)}
    hubs = [points[old] for old in used]
    lift = -min(hub[2] for hub in hubs)
    hubs = [[x, y, z + lift] for x, y, z in hubs]
    return hubs, [[remap[v] for v in tri] for tri in keep], lift


def strut_classes(hubs, triangles, radius):
    """Distinct strut lengths with counts and chord factors (length divided by radius)."""
    edges = {tuple(sorted((tri[k], tri[(k + 1) % 3]))) for tri in triangles for k in range(3)}
    classes = {}
    for a, b in edges:
        key = round(math.dist(hubs[a], hubs[b]), 6)
        classes[key] = classes.get(key, 0) + 1
    return edges, [{"length_m": length, "count": count, "chord_factor": round(length / radius, 6)}
                   for length, count in sorted(classes.items())]


def _hub(vertices, faces, centre, radius):
    t = (1.0 + math.sqrt(5.0)) / 2.0
    raw = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
           (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    norm = math.sqrt(1 + t * t)
    base = len(vertices)
    vertices.extend([[centre[n] + radius * v[n] / norm for n in range(3)] for v in raw])
    unit_faces = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
                   [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5],
                   [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    faces.extend([[base + v for v in face] for face in unit_faces])


def _strut(vertices, faces, start, end, radius):
    axis = [b - a for a, b in zip(start, end)]
    length = math.sqrt(sum(v * v for v in axis))
    axis = [v / length for v in axis]
    helper = [0.0, 0.0, 1.0] if abs(axis[2]) < 0.9 else [1.0, 0.0, 0.0]
    u = [axis[1] * helper[2] - axis[2] * helper[1], axis[2] * helper[0] - axis[0] * helper[2],
         axis[0] * helper[1] - axis[1] * helper[0]]
    norm = math.sqrt(sum(v * v for v in u))
    u = [v / norm for v in u]
    w = [axis[1] * u[2] - axis[2] * u[1], axis[2] * u[0] - axis[0] * u[2], axis[0] * u[1] - axis[1] * u[0]]
    base = len(vertices)
    for end_point in (start, end):
        for k in range(6):
            angle = math.pi * k / 3.0
            vertices.append([end_point[n] + radius * (math.cos(angle) * u[n] + math.sin(angle) * w[n])
                             for n in range(3)])
    for k in range(6):
        k1 = (k + 1) % 6
        faces.append([base + k, base + k1, base + 6 + k1, base + 6 + k])
    faces.append([base + k for k in reversed(range(6))])
    faces.append([base + 6 + k for k in range(6)])


def build_geometry(**values):
    """The dome as {"vertices", "faces", "report"}, centred on x = y = 0 and standing on z = 0."""
    p = _validate(values)
    hubs, triangles, lift = dome_surface(p["frequency"], p["radius"])
    edges, classes = strut_classes(hubs, triangles, p["radius"])
    vertices, faces = [], []
    if p["mode"] == "struts":
        for a, b in sorted(edges):
            direction = [hb - ha for ha, hb in zip(hubs[a], hubs[b])]
            length = math.sqrt(sum(v * v for v in direction))
            inset = min(p["hub_radius"] * 0.6, length * 0.25)
            start = [ha + direction[n] / length * inset for n, ha in enumerate(hubs[a])]
            end = [hb - direction[n] / length * inset for n, hb in enumerate(hubs[b])]
            _strut(vertices, faces, start, end, p["strut_radius"])
        for hub in hubs:
            _hub(vertices, faces, hub, p["hub_radius"])
    else:
        count = len(hubs)
        scale = (p["radius"] - p["thickness"]) / p["radius"]
        vertices = [list(hub) for hub in hubs]
        vertices += [[x * scale, y * scale, (z - lift) * scale + lift] for x, y, z in hubs]
        faces = [list(tri) for tri in triangles] + [[count + tri[0], count + tri[2], count + tri[1]]
                                                    for tri in triangles]
        boundary = {}
        for tri in triangles:
            for k in range(3):
                a, b = tri[k], tri[(k + 1) % 3]
                boundary[(a, b)] = boundary.get((a, b), 0) + 1
        for (a, b), _uses in sorted(boundary.items()):
            if (b, a) not in boundary:
                faces.append([b, a, count + a, count + b])
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    report = {"hubs": len(hubs), "struts": len(edges), "panels": len(triangles), "strut_classes": classes,
              "rim": "flat" if p["frequency"] % 2 == 0 else "stepped", "height_m": round(max(h[2] for h in hubs), 6)}
    return {"vertices": vertices, "faces": faces, "report": report,
            "materials": [{"name": "Baltor Dome Frame", "color": [0.8, 0.8, 0.82], "roughness": 0.35,
                           "metallic": 0.8}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "tolerance": 1e-4}}}


def create(context=None, **values):
    """Add the dome at the 3D cursor and return the object."""
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
