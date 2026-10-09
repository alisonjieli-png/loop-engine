"""Rock generator: a subdivided icosahedron displaced by fractal value noise, cut by random planes, flattened below.

The core, build_geometry(**parameters), starts from an icosahedron, splits every triangle into four
`subdivisions` times while projecting new vertices onto the unit sphere, then moves each vertex along its radius
by fractal 3D value noise (a hashed integer lattice with quintic interpolation, summed over octaves), applies the
length, width and height, pushes vertices beyond a few random planes back onto them to make flat fractured
facets, and clamps everything below the base height onto a flat bottom. The topology never changes, so the rock
stays one closed surface. It returns plain lists and needs no Blender; the same seed gives the same rock.

In Blender, create(context, **parameters) adds the rock at the 3D cursor, and register() adds the operator
baltor.rock_displaced to Add > Mesh. As a script:

    blender --background --python rock_displaced.py -- --seed 7 --subdivisions 4 --output rock.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Displaced Rock",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Displaced Rock",
    "description": "Closed rock mesh from a noise-displaced icosphere with fractured facets and a flat base",
    "category": "Add Mesh",
}

OPERATOR = "baltor.rock_displaced"
MENU = {"menu": "VIEW3D_MT_mesh_add", "label": "Displaced Rock", "icon": "MESH_ICOSPHERE"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Rock"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "seed", "type": "int", "default": 3, "minimum": 0, "maximum": 1000000, "unit": "seed",
     "description": "Random seed; the same seed gives the same rock."},
    {"name": "subdivisions", "type": "int", "default": 3, "minimum": 1, "maximum": 6, "unit": "count",
     "description": "Times each triangle is split in four (10 * 4^n + 2 vertices)."},
    {"name": "radius", "type": "float", "default": 0.5, "minimum": 0.01, "maximum": 100.0, "unit": "m",
     "description": "Radius before noise and scaling."},
    {"name": "dimensions", "type": "vector", "default": [1.3, 1.0, 0.75], "minimum": 0.05, "maximum": 10.0,
     "unit": "ratio", "description": "Scale along X, Y and Z applied after the noise."},
    {"name": "roughness", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 0.9, "unit": "ratio",
     "description": "Largest radial displacement as a share of the radius."},
    {"name": "frequency", "type": "float", "default": 1.6, "minimum": 0.1, "maximum": 20.0, "unit": "1/radius",
     "description": "Base frequency of the noise on the unit sphere."},
    {"name": "octaves", "type": "int", "default": 4, "minimum": 1, "maximum": 8, "unit": "count",
     "description": "Noise octaves; each doubles the frequency and halves the amplitude."},
    {"name": "cuts", "type": "int", "default": 5, "minimum": 0, "maximum": 20, "unit": "count",
     "description": "Random planes that shear off flat facets."},
    {"name": "cut_depth", "type": "float", "default": 0.18, "minimum": 0.0, "maximum": 0.6, "unit": "ratio",
     "description": "How deep each cut reaches, as a share of the radius."},
    {"name": "flat_base", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 0.9, "unit": "ratio",
     "description": "Share of the height below which vertices are flattened onto the base; 0 keeps it round."},
    {"name": "smooth", "type": "bool", "default": False, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Shade smooth instead of flat."},
)


# ------------------------------------------------------------------------------------------------ pure core
def _mix(value):
    value &= 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    return value ^ (value >> 16)


def _lattice(x, y, z, seed):
    return _mix(x * 0x1B873593 ^ _mix(y * 0x27D4EB2F ^ _mix(z * 0x165667B1 ^ seed))) / 0xFFFFFFFF * 2.0 - 1.0


def value_noise(x, y, z, seed):
    """Smooth value noise in [-1, 1]: lattice values blended with the quintic fade 6t^5 - 15t^4 + 10t^3."""
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    ux, uy, uz = (t * t * t * (t * (t * 6 - 15) + 10) for t in (fx, fy, fz))
    total = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                weight = (ux if dx else 1 - ux) * (uy if dy else 1 - uy) * (uz if dz else 1 - uz)
                total += weight * _lattice(ix + dx, iy + dy, iz + dz, seed)
    return total


def fractal_noise(point, seed, octaves, frequency):
    """Sum of octaves of value noise, normalised to [-1, 1]."""
    total, amplitude, norm = 0.0, 1.0, 0.0
    for octave in range(octaves):
        scale = frequency * 2 ** octave
        total += amplitude * value_noise(point[0] * scale, point[1] * scale, point[2] * scale, seed + octave * 101)
        norm += amplitude
        amplitude *= 0.5
    return total / norm


def icosphere(subdivisions):
    """Unit icosphere as (vertices, faces) with outward counter-clockwise triangles."""
    t = (1.0 + math.sqrt(5.0)) / 2.0
    raw = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
           (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    vertices = [[c / math.sqrt(1 + t * t) for c in vertex] for vertex in raw]
    faces = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
             [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11],
             [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    for _ in range(subdivisions):
        middle, split = {}, []

        def midpoint(a, b):
            key = (a, b) if a < b else (b, a)
            if key not in middle:
                point = [(p + q) / 2.0 for p, q in zip(vertices[a], vertices[b])]
                length = math.sqrt(sum(c * c for c in point))
                vertices.append([c / length for c in point])
                middle[key] = len(vertices) - 1
            return middle[key]

        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            split += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        faces = split
    return vertices, faces


def _cut_planes(seed, count, depth):
    planes = []
    for index in range(count):
        z = _mix(seed * 7919 + index * 104729 + 1) / 0xFFFFFFFF * 2.0 - 1.0
        angle = _mix(seed * 6007 + index * 3001 + 2) / 0xFFFFFFFF * 2.0 * math.pi
        side = math.sqrt(max(0.0, 1.0 - z * z))
        normal = [side * math.cos(angle), side * math.sin(angle), z * 0.6]
        length = math.sqrt(sum(c * c for c in normal))
        jitter = _mix(seed * 1301 + index * 7 + 3) / 0xFFFFFFFF
        planes.append(([c / length for c in normal], 1.0 - depth * (0.5 + jitter)))
    return planes


def _uv(vertices, faces):
    corners = []
    for face in faces:
        row = []
        for index in face:
            x, y, z = vertices[index]
            length = math.sqrt(x * x + y * y + z * z) or 1.0
            row.append([math.atan2(y, x) / (2 * math.pi) + 0.5, math.acos(max(-1.0, min(1.0, z / length))) / math.pi])
        us = [u for u, _v in row]
        if max(us) - min(us) > 0.5:
            row = [[u + 1.0 if u < 0.5 else u, v] for u, v in row]
        corners += row
    return corners


def build_geometry(**values):
    """The rock as {"vertices", "faces", "uv", "smooth", "materials"}, centred on the origin, base at the bottom."""
    p = _validate(values)
    vertices, faces = icosphere(p["subdivisions"])
    shaped = []
    for vertex in vertices:
        offset = 1.0 + p["roughness"] * fractal_noise(vertex, p["seed"], p["octaves"], p["frequency"])
        shaped.append([c * offset for c in vertex])
    for normal, distance in _cut_planes(p["seed"], p["cuts"], p["cut_depth"]):
        for vertex in shaped:
            excess = sum(a * b for a, b in zip(vertex, normal)) - distance
            if excess > 0.0:
                for axis in range(3):
                    vertex[axis] -= excess * normal[axis]
    scale = [p["radius"] * factor for factor in p["dimensions"]]
    shaped = [[c * s for c, s in zip(vertex, scale)] for vertex in shaped]
    low = min(vertex[2] for vertex in shaped)
    high = max(vertex[2] for vertex in shaped)
    base = low + (high - low) * p["flat_base"] * 0.5
    for vertex in shaped:
        vertex[2] = max(vertex[2], base) - base
    shaped = [[round(c, 9) for c in vertex] for vertex in shaped]
    return {"vertices": shaped, "faces": faces, "uv": _uv(shaped, faces), "smooth": p["smooth"],
            "materials": [{"name": "Baltor Rock", "color": [0.33, 0.31, 0.29], "roughness": 0.85}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]), "faces": len(mesh["faces"]),
                                      "bounds": [low, high], "materials": ["Baltor Rock"], "uv_layers": ["UVMap"]}}}


def create(context=None, **values):
    """Add the rock at the 3D cursor and return the object."""
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
