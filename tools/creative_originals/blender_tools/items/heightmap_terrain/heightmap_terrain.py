"""Terrain from fractal gradient noise on a grid: ridges, island falloff, terraces, sea level and a solid base.

The core, build_geometry(**parameters), samples 2D gradient noise (unit gradients picked by an integer hash at
lattice points, dotted with the offset, blended with the quintic fade) over a square grid and sums octaves with
the given lacunarity and gain. Ridged mode folds each octave as 1 - |n|. An island falloff lowers the edges with
a smoothstep of the distance from the centre, terraces quantise the height with a softened step, and everything
below sea level is flattened. With a base depth the grid gets side walls and a bottom, which makes a closed
solid for printing or cut-away views. It needs no Blender.

In Blender, create(context, **parameters) adds the terrain at the 3D cursor, and register() adds the operator
baltor.heightmap_terrain to Add > Mesh. As a script:

    blender --background --python heightmap_terrain.py -- --resolution 128 --ridged true --output land.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Heightmap Terrain",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Heightmap Terrain",
    "description": "Grid terrain from fractal gradient noise with ridges, island falloff, terraces and a base",
    "category": "Add Mesh",
}

OPERATOR = "baltor.heightmap_terrain"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Heightmap Terrain", "icon": "RNDCURVE"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Terrain"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "size", "type": "float", "default": 20.0, "minimum": 0.5, "maximum": 100000.0, "unit": "m",
     "description": "Side of the square terrain."},
    {"name": "resolution", "type": "int", "default": 64, "minimum": 2, "maximum": 1024, "unit": "count",
     "description": "Grid cells along each side."},
    {"name": "height", "type": "float", "default": 4.0, "minimum": 0.0, "maximum": 10000.0, "unit": "m",
     "description": "Height of the highest possible point above the lowest."},
    {"name": "feature_size", "type": "float", "default": 9.0, "minimum": 0.01, "maximum": 100000.0, "unit": "m",
     "description": "Width of the largest hills (one noise cell of the first octave)."},
    {"name": "octaves", "type": "int", "default": 5, "minimum": 1, "maximum": 12, "unit": "count",
     "description": "Noise octaves."},
    {"name": "lacunarity", "type": "float", "default": 2.0, "minimum": 1.1, "maximum": 4.0, "unit": "ratio",
     "description": "Frequency multiplier per octave."},
    {"name": "gain", "type": "float", "default": 0.5, "minimum": 0.1, "maximum": 0.9, "unit": "ratio",
     "description": "Amplitude multiplier per octave."},
    {"name": "ridged", "type": "bool", "default": False, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Fold each octave as 1 - |noise| for sharp ridges."},
    {"name": "island", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0, "unit": "ratio",
     "description": "Strength of the falloff that lowers the edges; 0 turns it off."},
    {"name": "terraces", "type": "int", "default": 0, "minimum": 0, "maximum": 64, "unit": "count",
     "description": "Number of terrace levels; 0 turns terracing off."},
    {"name": "sea_level", "type": "float", "default": 0.12, "minimum": 0.0, "maximum": 1.0, "unit": "ratio",
     "description": "Share of the height below which the ground is flattened."},
    {"name": "base_depth", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 10000.0, "unit": "m",
     "description": "Depth of side walls and a bottom below z = 0; 0 leaves an open sheet."},
    {"name": "seed", "type": "int", "default": 4, "minimum": 0, "maximum": 1000000, "unit": "seed",
     "description": "Random seed."},
)


# ------------------------------------------------------------------------------------------------ pure core
def _hash(x, y, seed):
    value = (x * 0x8DA6B343 ^ y * 0xD8163841 ^ seed * 0xCB1AB31F) & 0xFFFFFFFF
    value = ((value ^ (value >> 15)) * 0x2C1B3C6D) & 0xFFFFFFFF
    value = ((value ^ (value >> 12)) * 0x297A2D39) & 0xFFFFFFFF
    return value ^ (value >> 15)


def gradient_noise(x, y, seed):
    """2D gradient noise in about [-1, 1]: hashed unit gradients at lattice points, quintic blend."""
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    total = 0.0
    ux, uy = (t * t * t * (t * (t * 6 - 15) + 10) for t in (fx, fy))
    for dx in (0, 1):
        for dy in (0, 1):
            angle = _hash(ix + dx, iy + dy, seed) / 0xFFFFFFFF * 2.0 * math.pi
            dot = math.cos(angle) * (fx - dx) + math.sin(angle) * (fy - dy)
            total += dot * (ux if dx else 1 - ux) * (uy if dy else 1 - uy)
    return total * 1.4142135623730951


def height_field(**values):
    """Heights in metres on the (resolution + 1)^2 grid, rows along +Y, before the base is added."""
    p = _validate(values)
    n = p["resolution"]
    rows = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x, y = (i / n - 0.5) * p["size"], (j / n - 0.5) * p["size"]
            total, amplitude, frequency, norm = 0.0, 1.0, 1.0 / p["feature_size"], 0.0
            for octave in range(p["octaves"]):
                value = gradient_noise(x * frequency, y * frequency, p["seed"] + 31 * octave)
                if p["ridged"]:
                    value = 1.0 - 2.0 * abs(value)
                total += amplitude * value
                norm += amplitude
                amplitude *= p["gain"]
                frequency *= p["lacunarity"]
            h = 0.5 + 0.5 * max(-1.0, min(1.0, total / norm))
            if p["island"] > 0.0:
                distance = min(1.0, math.hypot(i / n - 0.5, j / n - 0.5) * 2.0)
                edge = distance * distance * (3 - 2 * distance)
                h *= 1.0 - p["island"] * edge
            if p["terraces"] > 0:
                level = h * p["terraces"]
                step = math.floor(level)
                fraction = level - step
                h = (step + fraction ** 4) / p["terraces"]
            h = max(h, p["sea_level"])
            row.append((h - p["sea_level"]) / (1.0 - p["sea_level"]) * p["height"] if p["sea_level"] < 1 else 0.0)
        rows.append(row)
    return rows


def build_geometry(**values):
    """The terrain as {"vertices", "faces", "uv", "groups", "report"}, centred on x = y = 0, sea level at z = 0."""
    p = _validate(values)
    n, size = p["resolution"], p["size"]
    heights = height_field(**p)
    vertices, faces, uv = [], [], []
    for j in range(n + 1):
        for i in range(n + 1):
            vertices.append([round((i / n - 0.5) * size, 9), round((j / n - 0.5) * size, 9), round(heights[j][i], 9)])
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            faces.append([a, a + 1, a + n + 2, a + n + 1])
            uv += [[i / n, j / n], [(i + 1) / n, j / n], [(i + 1) / n, (j + 1) / n], [i / n, (j + 1) / n]]
    sea = [index for index, vertex in enumerate(vertices) if vertex[2] == 0.0]
    if p["base_depth"] > 0.0:
        ring = (list(range(n + 1)) + [i * (n + 1) + n for i in range(1, n + 1)]
                + [n * (n + 1) + i for i in range(n - 1, -1, -1)] + [i * (n + 1) for i in range(n - 1, 0, -1)])
        base = len(vertices)
        for index in ring:
            x, y, _z = vertices[index]
            vertices.append([x, y, -p["base_depth"]])
        count = len(ring)
        for k in range(count):
            top_a, top_b = ring[k], ring[(k + 1) % count]
            faces.append([top_b, top_a, base + k, base + (k + 1) % count])
            uv += [[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
        faces.append([base + k for k in reversed(range(count))])
        uv += [[0.5 + 0.5 * vertices[base + k][0] / size * 2, 0.5 + 0.5 * vertices[base + k][1] / size * 2]
               for k in reversed(range(count))]
    peak = max(max(row) for row in heights)
    report = {"peak_m": round(peak, 6), "sea_vertices": len(sea), "grid_vertices": (n + 1) ** 2,
              "land_share": round(1.0 - len(sea) / (n + 1) ** 2, 6)}
    return {"vertices": vertices, "faces": faces, "uv": uv, "groups": {"sea": sea}, "smooth": True, "report": report,
            "materials": [{"name": "Baltor Terrain", "color": [0.25, 0.3, 0.16], "roughness": 0.9}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "vertex_groups": ["sea"], "uv_layers": ["UVMap"]}}}


def create(context=None, **values):
    """Add the terrain at the 3D cursor and return the object."""
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
