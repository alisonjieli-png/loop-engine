"""Spiral staircase: wedge treads around a central column, with balusters and a helical handrail.

The core, build_geometry(**parameters), returns one mesh as plain lists (vertices in metres, faces with outward
counter-clockwise winding, per-corner UVs at one UV unit per metre) and needs no Blender. Every tread, the
column, each baluster and the handrail is a separate closed solid inside that mesh.

In Blender, create(context, **parameters) links the mesh object to the active collection at the 3D cursor, and
register() adds the operator baltor.stairs_spiral to Add > Mesh. As a script:

    blender --background --python stairs_spiral.py -- --steps 18 --total_height 3.2 --output stairs.blend
"""
import math
import sys

bl_info = {
    "name": "Baltor Spiral Stairs",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Spiral Stairs",
    "description": "Spiral staircase with wedge treads, a central column, balusters and a helical handrail",
    "category": "Add Mesh",
}

OPERATOR = "baltor.stairs_spiral"
OBJECT_NAME = "Spiral Stairs"
# The parameter types the code below tests for; every other PARAMETERS row has the type "float".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETERS = (
    {"name": "steps", "type": "int", "default": 16, "minimum": 3, "maximum": 120, "unit": "count",
     "description": "Number of treads."},
    {"name": "total_height", "type": "float", "default": 3.0, "minimum": 0.5, "maximum": 20.0, "unit": "m",
     "description": "Floor to the top of the last tread."},
    {"name": "turn_degrees", "type": "float", "default": 360.0, "minimum": 30.0, "maximum": 1440.0,
     "unit": "degree", "description": "Total rotation from the first tread to the end of the last."},
    {"name": "inner_radius", "type": "float", "default": 0.15, "minimum": 0.05, "maximum": 2.0, "unit": "m",
     "description": "Radius of the central column, where the treads start."},
    {"name": "outer_radius", "type": "float", "default": 1.1, "minimum": 0.3, "maximum": 6.0, "unit": "m",
     "description": "Outer radius of the treads; must exceed inner_radius by at least 0.2 m."},
    {"name": "tread_thickness", "type": "float", "default": 0.05, "minimum": 0.01, "maximum": 0.3, "unit": "m",
     "description": "Thickness of each tread slab."},
    {"name": "arc_segments", "type": "int", "default": 2, "minimum": 1, "maximum": 12, "unit": "count",
     "description": "Segments along the outer arc of each tread and of the handrail per tread."},
    {"name": "column_sides", "type": "int", "default": 16, "minimum": 3, "maximum": 64, "unit": "count",
     "description": "Sides of the central column prism."},
    {"name": "handrail", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Add a square-section helical handrail and one baluster per tread."},
    {"name": "rail_height", "type": "float", "default": 0.9, "minimum": 0.5, "maximum": 1.5, "unit": "m",
     "description": "Height of the handrail above the tread nosing line."},
    {"name": "clockwise", "type": "bool", "default": False, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Climb clockwise seen from above instead of counter-clockwise."},
)


# ------------------------------------------------------------------------------------------------ parameters
def _validate(values):
    specs = {spec["name"]: spec for spec in PARAMETERS}
    unknown = sorted(set(values) - set(specs))
    if unknown:
        raise ValueError(f"unknown parameter: {', '.join(unknown)}")
    result = {}
    for name, spec in specs.items():
        value = values.get(name, spec["default"])
        if spec["type"] == PARAMETER_TYPE_BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be true or false")
        else:
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
        result[name] = value
    if result["outer_radius"] < result["inner_radius"] + 0.2:
        raise ValueError("outer_radius must exceed inner_radius by at least 0.2 m")
    if result["tread_thickness"] >= result["total_height"] / result["steps"]:
        raise ValueError("tread_thickness must be less than the rise of one step")
    return result


def parameters(**values):
    """The validated parameters with defaults filled in; raises ValueError on an unknown name or a bad value."""
    return _validate(values)


# ------------------------------------------------------------------------------------------------ pure core
def _box_uv(vertices, faces):
    """Per-corner UVs by the dominant axis of each face normal, one UV unit per metre."""
    uv = []
    for face in faces:
        nx = ny = nz = 0.0
        for position in range(len(face)):
            x1, y1, z1 = vertices[face[position]]
            x2, y2, z2 = vertices[face[(position + 1) % len(face)]]
            nx += (y1 - y2) * (z1 + z2)
            ny += (z1 - z2) * (x1 + x2)
            nz += (x1 - x2) * (y1 + y2)
        axis = max(range(3), key=lambda index: abs((nx, ny, nz)[index]))
        for index in face:
            x, y, z = vertices[index]
            uv.append([x, y] if axis == 2 else ([y, z] if axis == 0 else [x, z]))
    return uv


def _prism(vertices, faces, ring_low, ring_high):
    """Append a closed prism between two rings of equal length listed counter-clockwise from above."""
    base = len(vertices)
    count = len(ring_low)
    vertices.extend(ring_low)
    vertices.extend(ring_high)
    for index in range(count):
        following = (index + 1) % count
        faces.append([base + index, base + following, base + count + following, base + count + index])
    faces.append([base + index for index in reversed(range(count))])
    faces.append([base + count + index for index in range(count)])


def _tread(vertices, faces, start, end, inner, outer, bottom, top, segments):
    base = len(vertices)
    for step in range(segments + 1):
        angle = start + (end - start) * step / segments
        c, s = math.cos(angle), math.sin(angle)
        vertices.extend([[inner * c, inner * s, bottom], [outer * c, outer * s, bottom],
                         [inner * c, inner * s, top], [outer * c, outer * s, top]])
    for step in range(segments):
        a, b = base + 4 * step, base + 4 * (step + 1)
        faces.append([a + 2, a + 3, b + 3, b + 2])
        faces.append([a, b, b + 1, a + 1])
        faces.append([a + 1, b + 1, b + 3, a + 3])
        faces.append([a, a + 2, b + 2, b])
    last = base + 4 * segments
    faces.append([base, base + 1, base + 3, base + 2])
    faces.append([last, last + 2, last + 3, last + 1])


def _handrail(vertices, faces, radius, start, end, low, high, samples, half_width, half_height):
    base = len(vertices)
    for sample in range(samples + 1):
        t = sample / samples
        angle = start + (end - start) * t
        z = low + (high - low) * t
        c, s = math.cos(angle), math.sin(angle)
        for dr, dz in ((-half_width, -half_height), (half_width, -half_height), (half_width, half_height),
                       (-half_width, half_height)):
            vertices.append([(radius + dr) * c, (radius + dr) * s, z + dz])
    for sample in range(samples):
        a, b = base + 4 * sample, base + 4 * (sample + 1)
        for corner in range(4):
            following = (corner + 1) % 4
            faces.append([a + corner, b + corner, b + following, a + following])
    faces.append([base, base + 1, base + 2, base + 3])
    last = base + 4 * samples
    faces.append([last + 3, last + 2, last + 1, last])


def build_geometry(**values):
    """The staircase as {"vertices", "faces", "uv"}; vertices in metres around the Z axis from z = 0."""
    p = _validate(values)
    vertices, faces = [], []
    steps, rise = p["steps"], p["total_height"] / p["steps"]
    sweep = math.radians(p["turn_degrees"]) / steps
    sides = p["column_sides"]
    column = [[p["inner_radius"] * math.cos(2 * math.pi * k / sides), p["inner_radius"] * math.sin(
        2 * math.pi * k / sides), 0.0] for k in range(sides)]
    _prism(vertices, faces, column, [[x, y, p["total_height"]] for x, y, _z in column])
    for step in range(steps):
        top = (step + 1) * rise
        _tread(vertices, faces, step * sweep, (step + 1) * sweep, p["inner_radius"], p["outer_radius"],
               top - p["tread_thickness"], top, p["arc_segments"])
    if p["handrail"]:
        radius = p["outer_radius"] - 0.06
        for step in range(steps):
            angle = (step + 0.5) * sweep
            top = (step + 1) * rise
            rail = rise * (1.0 + (step + 0.5)) + p["rail_height"] - 0.025
            c, s = math.cos(angle), math.sin(angle)
            ring = []
            for du, dv in ((-0.015, -0.015), (0.015, -0.015), (0.015, 0.015), (-0.015, 0.015)):
                ring.append([(radius + du) * c - dv * s, (radius + du) * s + dv * c])
            _prism(vertices, faces, [[x, y, top] for x, y in ring], [[x, y, rail] for x, y in ring])
        _handrail(vertices, faces, radius, 0.0, steps * sweep, rise + p["rail_height"],
                  rise * (steps + 1) + p["rail_height"], steps * p["arc_segments"], 0.025, 0.025)
    if p["clockwise"]:
        vertices = [[-x, y, z] for x, y, z in vertices]
        faces = [list(reversed(face)) for face in faces]
    vertices = [[round(x, 9), round(y, 9), round(z, 9)] for x, y, z in vertices]
    return {"vertices": vertices, "faces": faces, "uv": _box_uv(vertices, faces)}


def expectations(**values):
    """What Blender must hold after create() with these parameters (the native check compares it)."""
    mesh = build_geometry(**values)
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": len(mesh["vertices"]),
                                      "faces": len(mesh["faces"]), "bounds": [low, high], "uv_layers": ["UVMap"]}}}


# ------------------------------------------------------------------------------------------------ script mode
def _from_text(spec, text):
    if spec["type"] == PARAMETER_TYPE_BOOL:
        if text.lower() not in ("true", "false", "1", "0", "yes", "no"):
            raise ValueError(f"{spec['name']} takes true or false")
        return text.lower() in ("true", "1", "yes")
    if spec["type"] == PARAMETER_TYPE_INT:
        return int(text)
    return float(text)


def parse_arguments(argv):
    """(parameters, output path) from script arguments such as ["--steps", "18", "--output", "a.blend"]."""
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


# ------------------------------------------------------------------------------------------------ Blender layer
def create(context=None, **values):
    """Build the staircase mesh object in the open Blender file and return it."""
    import bpy
    context = context or bpy.context
    mesh_data = build_geometry(**values)
    mesh = bpy.data.meshes.new(OBJECT_NAME)
    mesh.from_pydata(mesh_data["vertices"], [], mesh_data["faces"])
    layer = mesh.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", [value for corner in mesh_data["uv"] for value in corner])
    mesh.update()
    obj = bpy.data.objects.new(OBJECT_NAME, mesh)
    (context.collection or context.scene.collection).objects.link(obj)
    obj.location = context.scene.cursor.location
    for other in context.view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def _properties(bpy):
    annotations = {}
    for spec in PARAMETERS:
        label = spec["name"].replace("_", " ").title()
        if spec["type"] == PARAMETER_TYPE_BOOL:
            annotations[spec["name"]] = bpy.props.BoolProperty(name=label, description=spec["description"],
                                                               default=spec["default"])
        elif spec["type"] == PARAMETER_TYPE_INT:
            annotations[spec["name"]] = bpy.props.IntProperty(name=label, description=spec["description"],
                                                              default=spec["default"], min=spec["minimum"],
                                                              max=spec["maximum"])
        else:
            annotations[spec["name"]] = bpy.props.FloatProperty(
                name=label, description=spec["description"], default=spec["default"], min=spec["minimum"],
                max=spec["maximum"], unit="LENGTH" if spec["unit"] == "m" else "NONE")
    return annotations


_CLASSES = []


def _menu_entry(self, context):
    self.layout.operator(OPERATOR, text="Spiral Stairs", icon="MESH_CYLINDER")


def register():
    """Register the operator and its Add > Mesh menu entry."""
    import bpy

    def execute(self, context):
        try:
            create(context, **{spec["name"]: getattr(self, spec["name"]) for spec in PARAMETERS})
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    operator = type("BALTOR_OT_stairs_spiral", (bpy.types.Operator,), {
        "bl_idname": OPERATOR, "bl_label": "Spiral Stairs", "bl_description": bl_info["description"],
        "bl_options": {"REGISTER", "UNDO"}, "__annotations__": _properties(bpy), "execute": execute})
    bpy.utils.register_class(operator)
    _CLASSES.append(operator)
    bpy.types.VIEW3D_MT_mesh_add.append(_menu_entry)


def unregister():
    """Remove the menu entry and the operator."""
    import bpy
    bpy.types.VIEW3D_MT_mesh_add.remove(_menu_entry)
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
    """Script mode: build with the given parameters, then save when --output is given."""
    import bpy
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    values, output = parse_arguments(argv)
    create(bpy.context, **values)
    if output:
        _save(output)


if __name__ == "__main__":
    main()
