"""Studio gradient world: ground, horizon and zenith colours blended by the height of the view direction.

The core, world_graph(**parameters), takes the world direction from the Texture Coordinate node, reads its Z
component (the sine of the elevation), maps it from [-1, 1] to [0, 1] and passes it through a colour ramp with
stops for the ground, the horizon band and the zenith. The horizon height and the softness of the band are
parameters. A second strength for camera rays (through the Light Path node) lets the backdrop look darker or
brighter than the light it casts. It needs no Blender.

In Blender, create(context, **parameters) builds the world and sets it as the scene world; register() adds the
operator baltor.world_gradient_studio to the Add menu. As a script:

    blender --background scene.blend --python world_gradient_studio.py -- --zenith_color 0.1,0.15,0.3 --output g.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Gradient Studio World",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Gradient Studio World",
    "description": "Ground, horizon and zenith gradient world with separate camera strength",
    "category": "Lighting",
}

OPERATOR = "baltor.world_gradient_studio"
MENU = {"menu": "VIEW3D_MT_add", "label": "Gradient Studio World", "icon": "WORLD"}
BLENDER_ENTRY = "create"
WORLD_NAME = "Baltor Gradient Studio"
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
    {"name": "ground_color", "type": "vector", "default": [0.06, 0.055, 0.05], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour below the horizon."},
    {"name": "horizon_color", "type": "vector", "default": [0.55, 0.55, 0.58], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour of the horizon band."},
    {"name": "zenith_color", "type": "vector", "default": [0.12, 0.16, 0.28], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour straight up."},
    {"name": "horizon_height", "type": "float", "default": 0.0, "minimum": -60.0, "maximum": 60.0,
     "unit": "degree", "description": "Elevation of the horizon band."},
    {"name": "softness", "type": "float", "default": 12.0, "minimum": 0.5, "maximum": 90.0, "unit": "degree",
     "description": "Half the height of the horizon band."},
    {"name": "strength", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 100.0, "unit": "ratio",
     "description": "Strength of the light the world casts."},
    {"name": "camera_strength", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 100.0, "unit": "ratio",
     "description": "Strength of the backdrop as the camera sees it."},
)


def _extra_checks(p):
    if not (-90.0 < p["horizon_height"] - p["softness"] and p["horizon_height"] + p["softness"] < 90.0):
        raise ValueError("the horizon band must stay between straight down and straight up")


# ------------------------------------------------------------------------------------------------ pure core
def ramp_positions(horizon_height, softness):
    """Colour ramp positions of the band edges for the mapped value (sin(elevation) + 1) / 2."""
    low = (math.sin(math.radians(horizon_height - softness)) + 1.0) / 2.0
    high = (math.sin(math.radians(horizon_height + softness)) + 1.0) / 2.0
    middle = (math.sin(math.radians(horizon_height)) + 1.0) / 2.0
    return low, middle, high


def world_graph(**values):
    """The world tree as plain data."""
    p = _validate(values)
    low, middle, high = ramp_positions(p["horizon_height"], p["softness"])
    stops = [[low, p["ground_color"] + [1.0]], [middle, p["horizon_color"] + [1.0]], [high,
                                                                                       p["zenith_color"] + [1.0]]]
    if high < 0.999:
        stops.append([1.0, p["zenith_color"] + [1.0]])
    nodes = [
        {"name": "Direction", "type": "ShaderNodeTexCoord"},
        {"name": "Axes", "type": "ShaderNodeSeparateXYZ"},
        {"name": "Elevation", "type": "ShaderNodeMapRange",
         "inputs": {"From Min": -1.0, "From Max": 1.0, "To Min": 0.0, "To Max": 1.0}},
        {"name": "Gradient", "type": "ShaderNodeValToRGB", "ramp": {"interpolation": "EASE", "stops": stops}},
        {"name": "Camera Rays", "type": "ShaderNodeLightPath"},
        {"name": "Strength", "type": "ShaderNodeMix", "properties": {"data_type": "FLOAT"},
         "inputs": {"A_Float": p["strength"], "B_Float": p["camera_strength"]}},
        {"name": "Backdrop", "type": "ShaderNodeBackground"},
        {"name": "World Output", "type": "ShaderNodeOutputWorld"},
    ]
    links = _links([
        (("Direction", "Generated"), ("Axes", "Vector")),
        (("Axes", "Z"), ("Elevation", "Value")),
        (("Elevation", "Result"), ("Gradient", "Fac")),
        (("Camera Rays", "Is Camera Ray"), ("Strength", "Factor_Float")),
        (("Gradient", "Color"), ("Backdrop", "Color")),
        (("Strength", "Result_Float"), ("Backdrop", "Strength")),
        (("Backdrop", "Background"), ("World Output", "Surface")),
    ])
    _layout(nodes, links)
    return {"trees": [{"name": WORLD_NAME, "kind": "world", "nodes": nodes, "links": links}]}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    tree = world_graph(**values)["trees"][0]
    return {"worlds": {WORLD_NAME: {"nodes": len(tree["nodes"]), "links": len(tree["links"]), "output_linked": True,
                                    "users": 1}},
            "scene": {"world": WORLD_NAME}}


def create(context=None, **values):
    """Build the gradient world, make it the scene world and return it."""
    import bpy
    context = context or bpy.context
    tree = world_graph(**values)["trees"][0]
    world = bpy.data.worlds.get(WORLD_NAME) or bpy.data.worlds.new(WORLD_NAME)
    if world.node_tree is None:
        world.use_nodes = True
    _build_tree(world.node_tree, tree)
    context.scene.world = world
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
