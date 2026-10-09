"""Physical sky world with a sun lamp that matches the sky's sun direction exactly.

The core, sky_setup(**parameters), gives the sun as an elevation above the horizon and a compass bearing measured
clockwise from +Y, the convention of Blender's Sky Texture sun rotation (measured on Blender 5.2.1 by rendering an
equirectangular panorama: rotation r and elevation e put the sun at (sin r cos e, cos r cos e, sin e)). The sun
lamp must shine the opposite way, which is the Euler rotation (90 - e, 0, 180 - r) in degrees. The sky's own sun
disc is off by default so the lamp alone gives direct sunlight and sharp shadows in every renderer, and the sky
gives the ambient light. It needs no Blender.

In Blender, create(context, **parameters) builds the world (the multiple scattering sky where available, the
Nishita sky on 4.x), adds or updates the lamp and sets it as the scene world; register() adds the operator
baltor.world_sky_sun to the Add menu. As a script:

    blender --background scene.blend --python world_sky_sun.py -- --elevation 12 --azimuth 250 --output sky.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Sky And Matching Sun",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Sky And Matching Sun",
    "description": "Physical sky world with a sun lamp aligned to the sky's sun",
    "category": "Lighting",
}

OPERATOR = "baltor.world_sky_sun"
MENU = {"menu": "VIEW3D_MT_add", "label": "Sky And Matching Sun", "icon": "LIGHT_SUN"}
BLENDER_ENTRY = "create"
WORLD_NAME = "Baltor Sky"
SUN_NAME = "Baltor Sky Sun"
# Sky Texture models: multiple scattering where the Blender build has it (5.x), Nishita before that (4.x).
SKY_TYPE_MULTIPLE_SCATTERING = "MULTIPLE_SCATTERING"
SKY_TYPE_NISHITA = "NISHITA"
# Object types whose data _assign_material() gives the material: meshes, curves, surfaces, metaballs and text.
MATERIAL_TARGET_TYPES = frozenset({"MESH", "CURVE", "SURFACE", "META", "FONT"})
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "elevation", "type": "float", "default": 28.0, "minimum": -10.0, "maximum": 90.0, "unit": "degree",
     "description": "Sun height above the horizon."},
    {"name": "azimuth", "type": "float", "default": 135.0, "minimum": 0.0, "maximum": 360.0, "unit": "degree",
     "description": "Compass bearing of the sun, clockwise from +Y (0 is +Y, 90 is +X)."},
    {"name": "sun_strength", "type": "float", "default": 2.2, "minimum": 0.0, "maximum": 1000.0, "unit": "W/m^2",
     "description": "Irradiance of the sun lamp."},
    {"name": "sun_angle", "type": "float", "default": 0.545, "minimum": 0.0, "maximum": 30.0, "unit": "degree",
     "description": "Angular diameter of the sun lamp; larger values soften shadows."},
    {"name": "world_strength", "type": "float", "default": 0.12, "minimum": 0.0, "maximum": 100.0, "unit": "ratio",
     "description": "Strength of the sky background."},
    {"name": "sky_sun_disc", "type": "bool", "default": False, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Also draw the sun disc in the sky texture (it then lights the scene as well)."},
    {"name": "air_density", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 10.0, "unit": "ratio",
     "description": "Air density of the sky model."},
    {"name": "haze", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 10.0, "unit": "ratio",
     "description": "Dust or aerosol density of the sky model."},
)


# ------------------------------------------------------------------------------------------------ pure core
def sun_direction(elevation, azimuth):
    """Unit vector toward the sun for an elevation and a compass bearing clockwise from +Y (degrees)."""
    e, r = math.radians(elevation), math.radians(azimuth)
    return [math.sin(r) * math.cos(e), math.cos(r) * math.cos(e), math.sin(e)]


def lamp_rotation(elevation, azimuth):
    """Euler XYZ degrees that make a sun lamp shine from that direction."""
    return [90.0 - elevation, 0.0, (180.0 - azimuth) % 360.0]


def sky_setup(**values):
    """The world tree, the sun lamp and a report, as plain data."""
    p = _validate(values)
    nodes = [
        {"name": "Sky", "type": "ShaderNodeTexSky",
         "sky": {"sun_elevation_degrees": p["elevation"], "sun_rotation_degrees": p["azimuth"],
                 "sun_disc": p["sky_sun_disc"], "air_density": p["air_density"], "haze": p["haze"]}},
        {"name": "Background", "type": "ShaderNodeBackground", "inputs": {"Strength": p["world_strength"]}},
        {"name": "World Output", "type": "ShaderNodeOutputWorld"},
    ]
    links = _links([(("Sky", "Color"), ("Background", "Color")), (("Background", "Background"),
                                                                   ("World Output", "Surface"))])
    _layout(nodes, links)
    direction = sun_direction(p["elevation"], p["azimuth"])
    lamp = {"name": SUN_NAME, "type": "LIGHT", "location": [0.0, 0.0, 10.0],
            "rotation": lamp_rotation(p["elevation"], p["azimuth"]),
            "light": {"type": "SUN", "energy": p["sun_strength"], "angle_degrees": p["sun_angle"]}}
    report = {"sun_direction": [round(value, 9) for value in direction],
              "light_travel_direction": [round(-value, 9) for value in direction],
              "sun_above_horizon": p["elevation"] > 0.0}
    return {"trees": [{"name": WORLD_NAME, "kind": "world", "nodes": nodes, "links": links}], "objects": [lamp],
            "report": report}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    setup = sky_setup(**values)
    tree, lamp = setup["trees"][0], setup["objects"][0]
    return {"worlds": {WORLD_NAME: {"nodes": len(tree["nodes"]), "links": len(tree["links"]), "output_linked": True,
                                    "users": 1}},
            "scene": {"world": WORLD_NAME},
            "objects": {SUN_NAME: {"type": "LIGHT", "rotation_euler": [math.radians(a) for a in lamp["rotation"]],
                                   "attributes": {"data.type": "SUN", "data.energy": lamp["light"]["energy"],
                                                  "data.angle": math.radians(lamp["light"]["angle_degrees"])}}}}


def _configure_sky(node, sky):
    """Set the sky model across Blender versions: multiple scattering (5.x) or Nishita (4.x)."""
    kinds = [item.identifier for item in node.bl_rna.properties["sky_type"].enum_items]
    node.sky_type = SKY_TYPE_MULTIPLE_SCATTERING if SKY_TYPE_MULTIPLE_SCATTERING in kinds else SKY_TYPE_NISHITA
    node.sun_elevation = math.radians(sky["sun_elevation_degrees"])
    node.sun_rotation = math.radians(sky["sun_rotation_degrees"])
    node.sun_disc = sky["sun_disc"]
    node.air_density = sky["air_density"]
    for name in ("aerosol_density", "dust_density"):
        if hasattr(node, name):
            setattr(node, name, sky["haze"])


def create(context=None, **values):
    """Build the sky world, add or update the matching sun lamp, and return the world."""
    import bpy
    context = context or bpy.context
    setup = sky_setup(**values)
    tree, lamp = setup["trees"][0], setup["objects"][0]
    world = bpy.data.worlds.get(WORLD_NAME) or bpy.data.worlds.new(WORLD_NAME)
    if world.node_tree is None:
        world.use_nodes = True
    made = _build_tree(world.node_tree, tree)
    _configure_sky(made["Sky"], tree["nodes"][0]["sky"])
    context.scene.world = world
    sun = bpy.data.objects.get(SUN_NAME)
    if sun is None:
        sun = bpy.data.objects.new(SUN_NAME, bpy.data.lights.new(SUN_NAME, "SUN"))
        (context.collection or context.scene.collection).objects.link(sun)
    sun.data.energy = lamp["light"]["energy"]
    sun.data.angle = math.radians(lamp["light"]["angle_degrees"])
    sun.location = lamp["location"]
    sun.rotation_euler = [math.radians(angle) for angle in lamp["rotation"]]
    return world


# ------------------------------------------------------------------------------------------------ node trees
def _layout(nodes, links):
    """Place nodes in columns by their longest distance from a source, left to right (pure)."""
    depth = {node["name"]: 0 for node in nodes}
    for _ in range(len(nodes)):
        for link in links:
            depth[link["to"][0]] = max(depth[link["to"][0]], depth[link["from"][0]] + 1)
    rows = {}
    for node in nodes:
        column = depth[node["name"]]
        node["location"] = [column * 240.0, -rows.get(column, 0) * 200.0]
        rows[column] = rows.get(column, 0) + 1


def _links(pairs):
    """Link descriptions from ((node, output), (node, input)) pairs (pure)."""
    return [{"from": list(source), "to": list(target)} for source, target in pairs]


def _socket(sockets, key):
    if isinstance(key, int):
        return sockets[key]
    for socket in sockets:
        if socket.identifier == key:
            return socket
    for socket in sockets:
        if socket.name == key and getattr(socket, "enabled", True):
            return socket
    raise KeyError(f"no socket {key!r}")


def _build_tree(tree, description):
    """Fill a Blender node tree from a description: nodes, properties, ramps, input values and links."""
    tree.nodes.clear()
    made = {}
    for spec in description["nodes"]:
        node = tree.nodes.new(spec["type"])
        node.name = node.label = spec["name"]
        node.location = spec.get("location", (0.0, 0.0))
        for key, value in spec.get("properties", {}).items():
            setattr(node, key, value)
        if "ramp" in spec:
            ramp = node.color_ramp
            ramp.interpolation = spec["ramp"].get("interpolation", "LINEAR")
            stops = spec["ramp"]["stops"]
            while len(ramp.elements) < len(stops):
                ramp.elements.new(0.5)
            for element, (position, color) in zip(ramp.elements, stops):
                element.position, element.color = position, color
        for key, value in spec.get("inputs", {}).items():
            _socket(node.inputs, key).default_value = value
        made[spec["name"]] = node
    for link in description["links"]:
        tree.links.new(_socket(made[link["from"][0]].outputs, link["from"][1]),
                       _socket(made[link["to"][0]].inputs, link["to"][1]))
    return made


def _new_material(bpy, description):
    material = bpy.data.materials.new(description["name"])
    if material.node_tree is None:
        material.use_nodes = True
    _build_tree(material.node_tree, description)
    for key, value in description.get("settings", {}).items():
        if hasattr(material, key):
            setattr(material, key, value)
    return material


def _assign_material(context, material, assign):
    """Put the material on the active mesh (replacing its slots) or keep it with a fake user."""
    target = context.active_object
    if assign and target is not None and target.type in MATERIAL_TARGET_TYPES:
        target.data.materials.clear()
        target.data.materials.append(material)
    else:
        material.use_fake_user = True
    return material


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
