"""Parametric table: a top with rounded corners, four legs (tapered, round or turned) and aprons.

The core, build_geometry(**parameters), builds the top as a rounded rectangle (quarter circles of the corner
radius) extruded to its thickness, places four legs inset from the corners, and joins the legs with aprons
under the top, set back slightly from the legs' outer faces. Legs are lofted from rings: a square frustum for
tapered legs, a slightly tapered cylinder for round legs, and a lathe-like radius profile with beads and a
square block under the apron for turned legs. Every part is a closed solid. It needs no Blender.

In Blender, create(context, **parameters) adds the table at the 3D cursor, and register() adds the operator
baltor.table_parametric to Add > Mesh. As a script:

    blender --background --python table_parametric.py -- --length 2.0 --leg_style turned --output table.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Parametric Table",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Parametric Table",
    "description": "Table with a rounded top, tapered, round or turned legs and aprons",
    "category": "Add Mesh",
}

OPERATOR = "baltor.table_parametric"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Parametric Table", "icon": "MESH_CUBE"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Table"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "length", "type": "float", "default": 1.6, "minimum": 0.3, "maximum": 10.0, "unit": "m",
     "description": "Length of the top along X."},
    {"name": "width", "type": "float", "default": 0.9, "minimum": 0.3, "maximum": 5.0, "unit": "m",
     "description": "Width of the top along Y."},
    {"name": "height", "type": "float", "default": 0.75, "minimum": 0.2, "maximum": 2.0, "unit": "m",
     "description": "Floor to the top surface."},
    {"name": "top_thickness", "type": "float", "default": 0.035, "minimum": 0.008, "maximum": 0.2, "unit": "m",
     "description": "Thickness of the top."},
    {"name": "corner_radius", "type": "float", "default": 0.06, "minimum": 0.0, "maximum": 2.5, "unit": "m",
     "description": "Radius of the rounded top corners; 0 for square corners."},
    {"name": "leg_style", "type": "choice", "default": "tapered", "minimum": None, "maximum": None, "unit": "style",
     "choices": ["tapered", "round", "turned"], "description": "Leg shape."},
    {"name": "leg_size", "type": "float", "default": 0.06, "minimum": 0.015, "maximum": 0.4, "unit": "m",
     "description": "Width of the legs at the top."},
    {"name": "leg_inset", "type": "float", "default": 0.05, "minimum": 0.0, "maximum": 1.0, "unit": "m",
     "description": "Distance from the top's edge to the legs' outer faces."},
    {"name": "apron_height", "type": "float", "default": 0.09, "minimum": 0.0, "maximum": 0.5, "unit": "m",
     "description": "Height of the aprons under the top; 0 leaves them out."},
    {"name": "corner_segments", "type": "int", "default": 6, "minimum": 1, "maximum": 32, "unit": "count",
     "description": "Segments per rounded corner and per quarter of a round leg."},
)


def _extra_checks(p):
    if p["corner_radius"] > min(p["length"], p["width"]) / 2.0 - 1e-6:
        raise ValueError("corner_radius must be less than half the smaller side")
    room = min(p["length"], p["width"]) / 2.0 - p["leg_inset"] - p["leg_size"]
    if room <= 0.01:
        raise ValueError("leg_inset and leg_size leave no room between the legs")
    if p["apron_height"] >= p["height"] - p["top_thickness"] - 0.05:
        raise ValueError("apron_height must leave at least 5 cm of leg below it")


# ------------------------------------------------------------------------------------------------ pure core
def _loft(vertices, faces, rings):
    """A closed solid through rings of equal length listed counter-clockwise from above, bottom to top."""
    base, count = len(vertices), len(rings[0])
    for ring in rings:
        vertices.extend(ring)
    for level in range(len(rings) - 1):
        for k in range(count):
            a, b = base + level * count + k, base + level * count + (k + 1) % count
            faces.append([a, b, b + count, a + count])
    faces.append([base + k for k in reversed(range(count))])
    faces.append([base + (len(rings) - 1) * count + k for k in range(count)])


def rounded_rectangle(length, width, radius, segments):
    """Outline of a rounded rectangle centred on the origin, counter-clockwise."""
    hx, hy = length / 2.0, width / 2.0
    if radius <= 0.0:
        return [[-hx, -hy], [hx, -hy], [hx, hy], [-hx, hy]]
    points = []
    for cx, cy, start in ((hx - radius, -hy + radius, -90.0), (hx - radius, hy - radius, 0.0),
                          (-hx + radius, hy - radius, 90.0), (-hx + radius, -hy + radius, 180.0)):
        for k in range(segments + 1):
            angle = math.radians(start + 90.0 * k / segments)
            points.append([cx + radius * math.cos(angle), cy + radius * math.sin(angle)])
    return points


def _square(cx, cy, half, z):
    return [[cx - half, cy - half, z], [cx + half, cy - half, z], [cx + half, cy + half, z], [cx - half, cy + half, z]]


def _circle(cx, cy, radius, z, sides):
    return [[cx + radius * math.cos(2 * math.pi * k / sides), cy + radius * math.sin(2 * math.pi * k / sides), z]
            for k in range(sides)]


TURNED = [(0.0, 0.36), (0.04, 0.42), (0.07, 0.34), (0.3, 0.27), (0.55, 0.37), (0.62, 0.42), (0.66, 0.33),
          (0.7, 0.4)]


def leg_rings(style, cx, cy, size, bottom, top, apron, sides):
    """Rings of one leg from the floor to the underside of the top."""
    height = top - bottom
    if style == "tapered":
        return [_square(cx, cy, size * 0.32, bottom), _square(cx, cy, size / 2.0, top)]
    if style == "round":
        return [_circle(cx, cy, size * 0.4, bottom, sides), _circle(cx, cy, size / 2.0, top, sides)]
    block = top - max(apron, 0.08 * height)
    rings = [_circle(cx, cy, size * radius, bottom + (block - bottom) * share / TURNED[-1][0], sides)
             for share, radius in TURNED]
    square = []
    for k in range(sides):
        angle = 2 * math.pi * k / sides
        scale = 0.5 / max(abs(math.cos(angle)), abs(math.sin(angle)))
        square.append([cx + size * scale * math.cos(angle), cy + size * scale * math.sin(angle)])
    rings.append([[x, y, block + 0.005] for x, y in square])
    rings.append([[x, y, top] for x, y in square])
    return rings


def build_geometry(**values):
    """The table as {"vertices", "faces", "smooth", "materials"}, standing on z = 0, centred on x = y = 0."""
    p = _validate(values)
    vertices, faces = [], []
    top_z, under = p["height"], p["height"] - p["top_thickness"]
    outline = rounded_rectangle(p["length"], p["width"], p["corner_radius"], p["corner_segments"])
    _loft(vertices, faces, [[[x, y, under] for x, y in outline], [[x, y, top_z] for x, y in outline]])
    size, sides = p["leg_size"], 4 * p["corner_segments"]
    lx = p["length"] / 2.0 - p["leg_inset"] - size / 2.0
    ly = p["width"] / 2.0 - p["leg_inset"] - size / 2.0
    for cx, cy in ((-lx, -ly), (lx, -ly), (lx, ly), (-lx, ly)):
        _loft(vertices, faces, leg_rings(p["leg_style"], cx, cy, size, 0.0, under, p["apron_height"], sides))
    if p["apron_height"] > 0.0:
        thickness, setback = 0.022, 0.012
        z0 = under - p["apron_height"]
        ox, oy = lx + size / 2.0 - setback, ly + size / 2.0 - setback
        for x0, x1, y0, y1 in ((-lx + size / 2, lx - size / 2, -oy, -oy + thickness),
                               (-lx + size / 2, lx - size / 2, oy - thickness, oy),
                               (-ox, -ox + thickness, -ly + size / 2, ly - size / 2),
                               (ox - thickness, ox, -ly + size / 2, ly - size / 2)):
            _loft(vertices, faces, [[[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]],
                                    [[x0, y0, under], [x1, y0, under], [x1, y1, under], [x0, y1, under]]])
    vertices = [[round(c, 10) for c in vertex] for vertex in vertices]
    return {"vertices": vertices, "faces": faces, "smooth": False,
            "materials": [{"name": "Baltor Table Wood", "color": [0.45, 0.28, 0.15], "roughness": 0.5}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "dimensions": [high[0] - low[0], high[1] - low[1],
                                                                            high[2] - low[2]]}}}


def create(context=None, **values):
    """Add the table at the 3D cursor and return the object."""
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
