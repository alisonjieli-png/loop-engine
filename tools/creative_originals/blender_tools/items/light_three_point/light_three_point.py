"""Three-point light rig: key, fill and rim area lights aimed at a target, with powers set from ratios.

The core, rig_layout(**parameters), places the lights on a sphere around the target by azimuth and elevation,
computes the Euler rotation that points each light's -Z axis at the target, and sets the fill and rim powers so
that the illuminance ratios at the target hold at their distances (power scales with distance squared). It
returns plain data and needs no Blender.

In Blender, create(context, **parameters) adds an empty named "Three Point Rig" at the target and parents the
three lights to it with Track To constraints, so moving or rotating the empty moves the whole rig. register()
adds the operator baltor.light_three_point to the Add menu. As a script:

    blender --background scene.blend --python light_three_point.py -- --key_power 800 --output lit.blend
"""
import math
import sys

bl_info = {
    "name": "Baltor Three Point Light Rig",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Three Point Light Rig",
    "description": "Key, fill and rim area lights aimed at a target, with powers from illuminance ratios",
    "category": "Lighting",
}

OPERATOR = "baltor.light_three_point"
RIG_NAME = "Three Point Rig"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETERS = (
    {"name": "target", "type": "vector", "default": [0.0, 0.0, 1.0], "minimum": -10000.0, "maximum": 10000.0,
     "unit": "m", "description": "Point the three lights aim at; the rig empty sits here."},
    {"name": "key_distance", "type": "float", "default": 4.0, "minimum": 0.1, "maximum": 1000.0, "unit": "m",
     "description": "Distance from the target to the key light."},
    {"name": "fill_distance", "type": "float", "default": 4.5, "minimum": 0.1, "maximum": 1000.0, "unit": "m",
     "description": "Distance from the target to the fill light."},
    {"name": "rim_distance", "type": "float", "default": 4.0, "minimum": 0.1, "maximum": 1000.0, "unit": "m",
     "description": "Distance from the target to the rim light."},
    {"name": "key_azimuth", "type": "float", "default": 40.0, "minimum": -180.0, "maximum": 180.0,
     "unit": "degree", "description": "Key light angle around Z; 0 is in front (-Y), positive toward +X."},
    {"name": "key_elevation", "type": "float", "default": 35.0, "minimum": -30.0, "maximum": 89.0,
     "unit": "degree", "description": "Key light angle above the target's horizontal plane."},
    {"name": "fill_azimuth", "type": "float", "default": -55.0, "minimum": -180.0, "maximum": 180.0,
     "unit": "degree", "description": "Fill light angle around Z."},
    {"name": "fill_elevation", "type": "float", "default": 12.0, "minimum": -30.0, "maximum": 89.0,
     "unit": "degree", "description": "Fill light angle above the horizontal plane."},
    {"name": "rim_azimuth", "type": "float", "default": 160.0, "minimum": -180.0, "maximum": 180.0,
     "unit": "degree", "description": "Rim light angle around Z; near 180 places it behind the subject."},
    {"name": "rim_elevation", "type": "float", "default": 45.0, "minimum": -30.0, "maximum": 89.0,
     "unit": "degree", "description": "Rim light angle above the horizontal plane."},
    {"name": "key_power", "type": "float", "default": 120.0, "minimum": 1.0, "maximum": 1000000.0, "unit": "W",
     "description": "Power of the key area light."},
    {"name": "key_fill_ratio", "type": "float", "default": 3.0, "minimum": 1.0, "maximum": 32.0, "unit": "ratio",
     "description": "Key illuminance divided by fill illuminance at the target."},
    {"name": "rim_ratio", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 8.0, "unit": "ratio",
     "description": "Rim illuminance relative to the key at the target."},
    {"name": "light_size", "type": "float", "default": 1.0, "minimum": 0.01, "maximum": 50.0, "unit": "m",
     "description": "Edge of the square key and fill area lights; the rim light is half this size."},
    {"name": "key_color", "type": "vector", "default": [1.0, 0.92, 0.82], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Key light colour."},
    {"name": "fill_color", "type": "vector", "default": [0.82, 0.9, 1.0], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Fill light colour."},
    {"name": "rim_color", "type": "vector", "default": [1.0, 1.0, 1.0], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Rim light colour."},
)


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
        if spec["type"] == PARAMETER_TYPE_VECTOR:
            if isinstance(value, (str, bytes)) or not hasattr(value, "__len__") or len(value) != 3:
                raise ValueError(f"{name} must hold three numbers")
            value = [_number(name, item, {"type": PARAMETER_TYPE_FLOAT, "minimum": spec["minimum"],
                                          "maximum": spec["maximum"]}) for item in value]
        else:
            value = _number(name, value, spec)
        result[name] = value
    return result


def parameters(**values):
    """The validated parameters with defaults filled in; raises ValueError on an unknown name or a bad value."""
    return _validate(values)


# ------------------------------------------------------------------------------------------------ pure core
def aim_rotation(position, target):
    """Euler XYZ angles in degrees that turn a light's -Z axis from position toward target."""
    direction = [b - a for a, b in zip(position, target)]
    length = math.sqrt(sum(value * value for value in direction))
    if length < 1e-9:
        raise ValueError("a light cannot aim at its own position")
    x, y, z = (value / length for value in direction)
    pitch = math.degrees(math.acos(max(-1.0, min(1.0, -z))))
    heading = math.degrees(math.atan2(-x, y)) if abs(x) + abs(y) > 1e-12 else 0.0
    return [pitch, 0.0, heading]


def rotate_minus_z(rotation):
    """Where the -Z axis points after the Euler XYZ rotation (degrees); used to check aim_rotation."""
    rx, ry, rz = (math.radians(angle) for angle in rotation)
    vector = [0.0, 0.0, -1.0]
    for axis, angle in ((0, rx), (1, ry), (2, rz)):
        c, s = math.cos(angle), math.sin(angle)
        x, y, z = vector
        if axis == 0:
            vector = [x, c * y - s * z, s * y + c * z]
        elif axis == 1:
            vector = [c * x + s * z, y, -s * x + c * z]
        else:
            vector = [c * x - s * y, s * x + c * y, z]
    return vector


def _spherical(target, distance, azimuth, elevation):
    a, e = math.radians(azimuth), math.radians(elevation)
    return [target[0] + distance * math.sin(a) * math.cos(e), target[1] - distance * math.cos(a) * math.cos(e),
            target[2] + distance * math.sin(e)]


def rig_layout(**values):
    """The rig as {"objects": [...], "report": {...}}; light locations are relative to the rig empty."""
    p = _validate(values)
    target = p["target"]
    key, fill, rim = p["key_distance"], p["fill_distance"], p["rim_distance"]
    powers = {"Key Light": p["key_power"],
              "Fill Light": p["key_power"] / p["key_fill_ratio"] * (fill / key) ** 2,
              "Rim Light": p["key_power"] * p["rim_ratio"] * (rim / key) ** 2}
    rows = (("Key Light", key, p["key_azimuth"], p["key_elevation"], p["light_size"], p["key_color"]),
            ("Fill Light", fill, p["fill_azimuth"], p["fill_elevation"], p["light_size"], p["fill_color"]),
            ("Rim Light", rim, p["rim_azimuth"], p["rim_elevation"], p["light_size"] * 0.5, p["rim_color"]))
    objects = [{"name": RIG_NAME, "type": "EMPTY", "location": list(target), "rotation": [0.0, 0.0, 0.0],
                "parent": None}]
    for name, distance, azimuth, elevation, size, color in rows:
        position = _spherical(target, distance, azimuth, elevation)
        objects.append({"name": name, "type": "LIGHT", "parent": RIG_NAME,
                        "location": [round(a - b, 9) for a, b in zip(position, target)],
                        "world_location": [round(value, 9) for value in position],
                        "rotation": [round(angle, 9) for angle in aim_rotation(position, target)],
                        "light": {"type": "AREA", "energy": round(powers[name], 6), "size": size, "color": color}})
    report = {"powers_w": {name: round(power, 6) for name, power in powers.items()},
              "illuminance_relative_to_key": {"Key Light": 1.0, "Fill Light": round(1.0 / p["key_fill_ratio"], 9),
                                              "Rim Light": p["rim_ratio"]}}
    return {"objects": objects, "report": report}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    layout = rig_layout(**values)
    objects, samples = {}, []
    for item in layout["objects"]:
        spec = {"type": item["type"], "parent": item["parent"], "location": item["location"],
                "rotation_euler": [math.radians(angle) for angle in item["rotation"]]}
        if item["type"] == "LIGHT":
            spec["constraints"] = ["TRACK_TO"]
            spec["attributes"] = {"data.type": "AREA", "data.energy": item["light"]["energy"],
                                  "data.size": item["light"]["size"], "data.color": item["light"]["color"]}
            samples.append({"object": item["name"], "frame": 1, "path": "matrix_world.translation",
                            "value": item["world_location"], "tolerance": 1e-4})
        else:
            spec["children"] = ["Fill Light", "Key Light", "Rim Light"]
        objects[item["name"]] = spec
    return {"objects": objects, "samples": samples}


# ------------------------------------------------------------------------------------------------ script mode
def parse_arguments(argv):
    """(parameters, output path) from script arguments such as ["--key_power", "800", "--output", "a.blend"]."""
    specs = {spec["name"]: spec for spec in PARAMETERS}
    values, output = {}, None
    if len(argv) % 2:
        raise ValueError("arguments come in --name value pairs")
    for key, text in zip(argv[0::2], argv[1::2]):
        name = key[2:].replace("-", "_") if key.startswith("--") else None
        if name == "output":
            output = text
        elif name in specs:
            values[name] = [float(part) for part in text.split(",")] if specs[name]["type"] == PARAMETER_TYPE_VECTOR \
                else float(text)
        else:
            raise ValueError(f"unknown argument {key}")
    return _validate(values), output


# ------------------------------------------------------------------------------------------------ Blender layer
def create(context=None, **values):
    """Add the rig empty and its three aimed area lights; return the empty."""
    import bpy
    context = context or bpy.context
    layout = rig_layout(**values)
    collection = context.collection or context.scene.collection
    made = {}
    for item in layout["objects"]:
        if item["type"] == "EMPTY":
            obj = bpy.data.objects.new(item["name"], None)
            obj.empty_display_type = "SPHERE"
            obj.empty_display_size = 0.25
        else:
            light = bpy.data.lights.new(item["name"], "AREA")
            light.energy = item["light"]["energy"]
            light.size = item["light"]["size"]
            light.color = item["light"]["color"]
            obj = bpy.data.objects.new(item["name"], light)
        collection.objects.link(obj)
        obj.location = item["location"]
        obj.rotation_euler = [math.radians(angle) for angle in item["rotation"]]
        if item["parent"]:
            obj.parent = made[item["parent"]]
            constraint = obj.constraints.new("TRACK_TO")
            constraint.target = made[item["parent"]]
            constraint.track_axis = "TRACK_NEGATIVE_Z"
            constraint.up_axis = "UP_Y"
        made[item["name"]] = obj
    rig = made[RIG_NAME]
    for other in context.view_layer.objects:
        other.select_set(False)
    rig.select_set(True)
    context.view_layer.objects.active = rig
    return rig


def _properties(bpy):
    annotations = {}
    for spec in PARAMETERS:
        common = {"name": spec["name"].replace("_", " ").title(), "description": spec["description"]}
        if spec["type"] == PARAMETER_TYPE_VECTOR:
            annotations[spec["name"]] = bpy.props.FloatVectorProperty(
                size=3, default=spec["default"], min=spec["minimum"], max=spec["maximum"],
                subtype="COLOR" if spec["unit"] == "linear RGB" else "TRANSLATION", **common)
        else:
            annotations[spec["name"]] = bpy.props.FloatProperty(default=spec["default"], min=spec["minimum"],
                                                                max=spec["maximum"], **common)
    return annotations


_CLASSES = []


def _menu_entry(self, context):
    self.layout.operator(OPERATOR, text="Three Point Light Rig", icon="LIGHT_AREA")


def register():
    """Register the operator and its Add menu entry."""
    import bpy

    def execute(self, context):
        values = {spec["name"]: list(getattr(self, spec["name"])) if spec["type"] == PARAMETER_TYPE_VECTOR
                  else getattr(self, spec["name"]) for spec in PARAMETERS}
        try:
            create(context, **values)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    operator = type("BALTOR_OT_light_three_point", (bpy.types.Operator,), {
        "bl_idname": OPERATOR, "bl_label": "Three Point Light Rig", "bl_description": bl_info["description"],
        "bl_options": {"REGISTER", "UNDO"}, "__annotations__": _properties(bpy), "execute": execute})
    bpy.utils.register_class(operator)
    _CLASSES.append(operator)
    bpy.types.VIEW3D_MT_add.append(_menu_entry)


def unregister():
    """Remove the menu entry and the operator."""
    import bpy
    bpy.types.VIEW3D_MT_add.remove(_menu_entry)
    while _CLASSES:
        bpy.utils.unregister_class(_CLASSES.pop())


def main(argv=None):
    """Script mode: add the rig to the opened file, then save when --output is given."""
    import bpy
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    values, output = parse_arguments(argv)
    create(bpy.context, **values)
    if output:
        _save(output)


def _save(output):
    import bpy
    if output.endswith(".blend"):
        bpy.ops.wm.save_as_mainfile(filepath=output)
    elif output.endswith((".glb", ".gltf")):
        bpy.ops.export_scene.gltf(filepath=output, export_format="GLB" if output.endswith(".glb")
                                  else "GLTF_SEPARATE", export_lights=True)
    else:
        raise ValueError("--output ends in .blend, .glb or .gltf")


if __name__ == "__main__":
    main()
