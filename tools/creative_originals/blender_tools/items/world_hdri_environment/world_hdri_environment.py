"""Image-based lighting world: an equirectangular image with rotation, strength, saturation and a camera backdrop.

The core, world_graph(**parameters), maps the world direction through a rotation about Z into an Environment Texture,
adjusts saturation and strength, and, when the backdrop mode is solid, mixes in a plain colour only for camera rays
with the Light Path node: the image keeps lighting the scene and showing in reflections while the camera sees a
clean background. The demo fixture writes a small sky image (a horizon gradient with a bright sun spot) so the tool
can be checked without an HDRI file. It needs no Blender.

In Blender, create(context, **parameters) loads the image, builds the world and sets it as the scene world;
register() adds the operator baltor.world_hdri_environment to the Add menu. As a script:

    blender --background scene.blend --python world_hdri_environment.py -- --image_path //sky.exr --output w.blend
"""
import json
import math
import os
import sys

bl_info = {
    "name": "Baltor HDRI Environment",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > HDRI Environment",
    "description": "Equirectangular image world with rotation, strength, saturation and a solid camera backdrop",
    "category": "Lighting",
}

OPERATOR = "baltor.world_hdri_environment"
MENU = {"menu": "VIEW3D_MT_add", "label": "HDRI Environment", "icon": "WORLD"}
BLENDER_ENTRY = "create"
WORLD_NAME = "Baltor HDRI"
DEMO_IMAGE = "//textures/baltor_sky_demo.png"
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
    {"name": "image_path", "type": "string", "default": DEMO_IMAGE, "minimum": None, "maximum": None,
     "unit": "path", "description": "Equirectangular image (.hdr, .exr, .png, .jpg); // is relative to the .blend."},
    {"name": "rotation", "type": "float", "default": 0.0, "minimum": -360.0, "maximum": 360.0, "unit": "degree",
     "description": "Rotation of the environment about Z."},
    {"name": "strength", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 1000.0, "unit": "ratio",
     "description": "Strength of the environment light."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0, "unit": "ratio",
     "description": "Saturation of the image; 1 leaves it unchanged."},
    {"name": "backdrop", "type": "choice", "default": "image", "minimum": None, "maximum": None, "unit": "mode",
     "choices": ["image", "solid"], "description": "What camera rays see: the image or a solid colour."},
    {"name": "backdrop_color", "type": "vector", "default": [0.05, 0.05, 0.055], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour the camera sees in solid backdrop mode."},
)


def _extra_checks(p):
    if not p["image_path"].lower().endswith((".hdr", ".exr", ".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        raise ValueError("image_path must name an .hdr, .exr, .png, .jpg or .tif image")


# ------------------------------------------------------------------------------------------------ pure core
def equirect_pixel(direction, width, height, rotation=0.0):
    """Pixel (column, row from the top) looked up for a world direction in an equirectangular image with +X at the
    centre column, +Y a quarter of the width to its left and +Z on the top row, after the Z rotation."""
    x, y, z = direction
    length = math.sqrt(x * x + y * y + z * z)
    if length == 0.0:
        raise ValueError("direction must not be zero")
    angle = math.atan2(y, x) + math.radians(rotation)
    u = (-angle / (2 * math.pi) + 0.5) % 1.0
    v = math.acos(max(-1.0, min(1.0, z / length))) / math.pi
    return min(width - 1, int(u * width)), min(height - 1, int(v * height))


def world_graph(**values):
    """The world tree and the image it needs, as plain data."""
    p = _validate(values)
    nodes = [
        {"name": "Direction", "type": "ShaderNodeTexCoord"},
        {"name": "Rotate", "type": "ShaderNodeMapping",
         "inputs": {"Rotation": [0.0, 0.0, math.radians(p["rotation"])]}},
        {"name": "Environment", "type": "ShaderNodeTexEnvironment", "image": {"path": p["image_path"]}},
        {"name": "Saturation", "type": "ShaderNodeHueSaturation", "inputs": {"Saturation": p["saturation"]}},
        {"name": "Light", "type": "ShaderNodeBackground", "inputs": {"Strength": p["strength"]}},
        {"name": "World Output", "type": "ShaderNodeOutputWorld"},
    ]
    pairs = [(("Direction", "Generated"), ("Rotate", "Vector")), (("Rotate", "Vector"), ("Environment", "Vector")),
             (("Environment", "Color"), ("Saturation", "Color")), (("Saturation", "Color"), ("Light", "Color"))]
    if p["backdrop"] == "solid":
        nodes[-1:-1] = [{"name": "Backdrop", "type": "ShaderNodeBackground",
                         "inputs": {"Color": p["backdrop_color"] + [1.0], "Strength": 1.0}},
                        {"name": "Camera Rays", "type": "ShaderNodeLightPath"},
                        {"name": "Camera Sees Backdrop", "type": "ShaderNodeMixShader"}]
        pairs += [(("Camera Rays", "Is Camera Ray"), ("Camera Sees Backdrop", "Fac")),
                  (("Light", "Background"), ("Camera Sees Backdrop", "Shader")),
                  (("Backdrop", "Background"), ("Camera Sees Backdrop", "Shader_001")),
                  (("Camera Sees Backdrop", "Shader"), ("World Output", "Surface"))]
    else:
        pairs.append((("Light", "Background"), ("World Output", "Surface")))
    links = _links(pairs)
    _layout(nodes, links)
    return {"trees": [{"name": WORLD_NAME, "kind": "world", "nodes": nodes, "links": links}],
            "images": [{"path": p["image_path"]}]}


def expectations(**values):
    """What Blender must hold after fixture() and create() with the defaults."""
    graph = world_graph(**values)
    tree = graph["trees"][0]
    name = graph["images"][0]["path"].replace("\\", "/").rsplit("/", 1)[-1]
    return {"worlds": {WORLD_NAME: {"nodes": len(tree["nodes"]), "links": len(tree["links"]), "output_linked": True,
                                    "users": 1}},
            "scene": {"world": WORLD_NAME},
            "images": {name: {"source": "FILE", "size": [128, 64]}}}


def _resolve(path):
    import bpy
    return os.path.abspath(bpy.path.abspath(path))


def fixture(context=None):
    """Write a 128 x 64 demo sky (horizon gradient, ground, sun spot) to the default path and add a test sphere."""
    import bpy
    context = context or bpy.context
    target = _resolve(DEMO_IMAGE)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    width, height = 128, 64
    image = bpy.data.images.new("baltor_sky_demo_source", width, height)
    sun_column, sun_row = equirect_pixel([0.6, -0.6, 0.5], width, height)
    pixels = []
    for row in range(height - 1, -1, -1):
        for column in range(width):
            t = row / (height - 1)
            if t < 0.5:
                colour = [0.25 + 0.5 * t, 0.45 + 0.6 * t, 0.85, 1.0]
            else:
                colour = [0.22, 0.2, 0.16, 1.0]
            if abs(column - sun_column) <= 1 and abs(row - sun_row) <= 1:
                colour = [1.0, 0.95, 0.85, 1.0]
            pixels += colour
    image.pixels = pixels
    image.filepath_raw = target
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0, location=(0.0, 0.0, 1.0))
    sphere = context.active_object
    sphere.name = sphere.data.name = "HDRI Test Sphere"
    material = bpy.data.materials.new("HDRI Test Chrome")
    if material.node_tree is None:
        material.use_nodes = True
    shader = next(node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 1.0
    shader.inputs["Roughness"].default_value = 0.08
    sphere.data.materials.append(material)
    return sphere


def create(context=None, **values):
    """Load the image, build the world, make it the scene world and return it."""
    import bpy
    context = context or bpy.context
    graph = world_graph(**values)
    tree = graph["trees"][0]
    world = bpy.data.worlds.get(WORLD_NAME) or bpy.data.worlds.new(WORLD_NAME)
    if world.node_tree is None:
        world.use_nodes = True
    made = _build_tree(world.node_tree, tree)
    path = _resolve(graph["images"][0]["path"])
    if not os.path.isfile(path):
        raise ValueError(f"image not found: {path}")
    made["Environment"].image = bpy.data.images.load(path, check_existing=True)
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
