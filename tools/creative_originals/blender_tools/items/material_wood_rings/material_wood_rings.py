"""Procedural wood material: growth rings around the object's Z axis, warped by noise, with pores and bump.

The core, material_graph(**parameters), describes the shader node tree as plain data (nodes with types, input
values and properties, and links between named sockets) and needs no Blender. The ring profile is built from
math nodes rather than the Wave texture, so the earlywood to latewood ratio is one parameter:
ring = fract(rings_per_metre * |warped XY|), then a colour ramp from earlywood to latewood colour.

In Blender, create(context, **parameters) builds the material and assigns it to the active mesh object, and
register() adds the operator baltor.material_wood_rings to the Object menu. As a script:

    blender --background scene.blend --python material_wood_rings.py -- --rings_per_metre 80 --output wood.blend
"""
import math
import sys

bl_info = {
    "name": "Baltor Wood Rings Material",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Object > Wood Rings Material",
    "description": "Procedural wood with growth rings, latewood ratio, pores, roughness and bump",
    "category": "Material",
}

OPERATOR = "baltor.material_wood_rings"
# The object type whose data create() gives the material.
OBJECT_TYPE_MESH = "MESH"
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "material_name", "type": "string", "default": "Baltor Wood", "minimum": None, "maximum": None,
     "unit": "text", "description": "Name of the new material."},
    {"name": "rings_per_metre", "type": "float", "default": 60.0, "minimum": 2.0, "maximum": 600.0,
     "unit": "1/m", "description": "Growth rings per metre of radius from the object's Z axis."},
    {"name": "latewood_fraction", "type": "float", "default": 0.3, "minimum": 0.05, "maximum": 0.9,
     "unit": "ratio", "description": "Share of each ring taken by the dark latewood band."},
    {"name": "warp", "type": "float", "default": 0.02, "minimum": 0.0, "maximum": 0.3, "unit": "m",
     "description": "How far noise displaces the rings."},
    {"name": "warp_scale", "type": "float", "default": 3.0, "minimum": 0.1, "maximum": 60.0, "unit": "1/m",
     "description": "Frequency of the warping noise across the grain."},
    {"name": "grain_stretch", "type": "float", "default": 8.0, "minimum": 1.0, "maximum": 50.0, "unit": "ratio",
     "description": "How much longer noise features are along the grain (Z) than across it."},
    {"name": "earlywood_color", "type": "vector", "default": [0.6, 0.38, 0.2], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour of the light earlywood band."},
    {"name": "latewood_color", "type": "vector", "default": [0.28, 0.14, 0.06], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour of the dark latewood band."},
    {"name": "pore_strength", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0, "unit": "ratio",
     "description": "How much the stretched pore noise darkens the colour."},
    {"name": "roughness", "type": "vector", "default": [0.45, 0.62, 0.0], "minimum": 0.0, "maximum": 1.0,
     "unit": "ratio", "description": "Roughness in latewood and in earlywood (third value unused)."},
    {"name": "bump_strength", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0, "unit": "ratio",
     "description": "Strength of the ring bump."},
    {"name": "assign", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Assign the material to the active mesh object."},
)


# ------------------------------------------------------------------------------------------------ parameters
def _number(name, value, spec):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if spec["type"] == PARAMETER_TYPE_INT:
        if float(value) != int(value):
            raise ValueError(f"{name} must be a whole number")
        value = int(value)
    value = float(value) if spec["type"] != PARAMETER_TYPE_INT else value
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
        if spec["type"] == PARAMETER_TYPE_BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be true or false")
        elif spec["type"] == PARAMETER_TYPE_STRING:
            if not isinstance(value, str) or len(value) > 63:
                raise ValueError(f"{name} must be text of at most 63 characters")
        elif spec["type"] == PARAMETER_TYPE_VECTOR:
            if isinstance(value, (str, bytes)) or not hasattr(value, "__len__") or len(value) != 3:
                raise ValueError(f"{name} must hold three numbers")
            value = [_number(name, item, {"type": PARAMETER_TYPE_FLOAT, "minimum": spec["minimum"],
                                          "maximum": spec["maximum"]}) for item in value]
        else:
            value = _number(name, value, spec)
        result[name] = value
    if not result["material_name"].strip():
        raise ValueError("material_name must not be empty")
    return result


def parameters(**values):
    """The validated parameters with defaults filled in; raises ValueError on an unknown name or a bad value."""
    return _validate(values)


# ------------------------------------------------------------------------------------------------ pure core
def _layout(nodes, links):
    """Place nodes in columns by their longest distance from a source, left to right."""
    depth = {node["name"]: 0 for node in nodes}
    for _ in range(len(nodes)):
        for link in links:
            depth[link["to"][0]] = max(depth[link["to"][0]], depth[link["from"][0]] + 1)
    rows = {}
    for node in nodes:
        column = depth[node["name"]]
        node["location"] = [column * 240.0, -rows.get(column, 0) * 200.0]
        rows[column] = rows.get(column, 0) + 1


def material_graph(**values):
    """The material as {"trees": [{"name", "kind": "material", "nodes", "links"}]} in plain data."""
    p = _validate(values)
    early = p["earlywood_color"] + [1.0]
    late = p["latewood_color"] + [1.0]
    pore = [channel * 0.35 for channel in p["latewood_color"]] + [1.0]
    stretch = 1.0 / p["grain_stretch"]
    late_start = 1.0 - p["latewood_fraction"]
    nodes = [
        {"name": "Coordinates", "type": "ShaderNodeTexCoord"},
        {"name": "Grain Space", "type": "ShaderNodeMapping", "inputs": {"Scale": [1.0, 1.0, stretch]}},
        {"name": "Warp Noise", "type": "ShaderNodeTexNoise",
         "inputs": {"Scale": p["warp_scale"], "Detail": 3.0, "Roughness": 0.5}},
        {"name": "Center Warp", "type": "ShaderNodeVectorMath", "properties": {"operation": "SUBTRACT"},
         "inputs": {"Vector_001": [0.5, 0.5, 0.5]}},
        {"name": "Warp Amount", "type": "ShaderNodeVectorMath", "properties": {"operation": "SCALE"},
         "inputs": {"Scale": 2.0 * p["warp"]}},
        {"name": "Warped", "type": "ShaderNodeVectorMath", "properties": {"operation": "ADD"}},
        {"name": "Drop Z", "type": "ShaderNodeVectorMath", "properties": {"operation": "MULTIPLY"},
         "inputs": {"Vector_001": [1.0, 1.0, 0.0]}},
        {"name": "Radius", "type": "ShaderNodeVectorMath", "properties": {"operation": "LENGTH"}},
        {"name": "Ring Count", "type": "ShaderNodeMath", "properties": {"operation": "MULTIPLY"},
         "inputs": {"Value_001": p["rings_per_metre"]}},
        {"name": "Ring Phase", "type": "ShaderNodeMath", "properties": {"operation": "FRACT"}},
        {"name": "Ring Ramp", "type": "ShaderNodeValToRGB",
         "ramp": {"interpolation": "LINEAR", "stops": [[0.0, early], [late_start, early],
                                                        [min(1.0, late_start + 0.08), late], [1.0, late]]}},
        {"name": "Pore Noise", "type": "ShaderNodeTexNoise",
         "inputs": {"Scale": 140.0, "Detail": 2.0, "Roughness": 0.6}},
        {"name": "Pore Mask", "type": "ShaderNodeMapRange",
         "inputs": {"From Min": 0.55, "From Max": 0.75, "To Min": 0.0, "To Max": p["pore_strength"]}},
        {"name": "Pores", "type": "ShaderNodeMix",
         "properties": {"data_type": "RGBA", "blend_type": "MIX"}, "inputs": {"B_Color": pore}},
        {"name": "Ring Roughness", "type": "ShaderNodeMapRange",
         "inputs": {"From Min": late_start, "From Max": 1.0, "To Min": p["roughness"][1],
                    "To Max": p["roughness"][0]}},
        {"name": "Ring Bump", "type": "ShaderNodeBump",
         "inputs": {"Strength": p["bump_strength"], "Distance": 0.002}},
        {"name": "Wood", "type": "ShaderNodeBsdfPrincipled", "inputs": {"Specular IOR Level": 0.5}},
        {"name": "Output", "type": "ShaderNodeOutputMaterial"},
    ]
    links = [
        (("Coordinates", "Object"), ("Grain Space", "Vector")),
        (("Grain Space", "Vector"), ("Warp Noise", "Vector")),
        (("Warp Noise", "Color"), ("Center Warp", "Vector")),
        (("Center Warp", "Vector"), ("Warp Amount", "Vector")),
        (("Coordinates", "Object"), ("Warped", "Vector")),
        (("Warp Amount", "Vector"), ("Warped", "Vector_001")),
        (("Warped", "Vector"), ("Drop Z", "Vector")),
        (("Drop Z", "Vector"), ("Radius", "Vector")),
        (("Radius", "Value"), ("Ring Count", "Value")),
        (("Ring Count", "Value"), ("Ring Phase", "Value")),
        (("Ring Phase", "Value"), ("Ring Ramp", "Fac")),
        (("Grain Space", "Vector"), ("Pore Noise", "Vector")),
        (("Pore Noise", "Fac"), ("Pore Mask", "Value")),
        (("Pore Mask", "Result"), ("Pores", "Factor_Float")),
        (("Ring Ramp", "Color"), ("Pores", "A_Color")),
        (("Ring Phase", "Value"), ("Ring Roughness", "Value")),
        (("Ring Phase", "Value"), ("Ring Bump", "Height")),
        (("Pores", "Result_Color"), ("Wood", "Base Color")),
        (("Ring Roughness", "Result"), ("Wood", "Roughness")),
        (("Ring Bump", "Normal"), ("Wood", "Normal")),
        (("Wood", "BSDF"), ("Output", "Surface")),
    ]
    links = [{"from": list(source), "to": list(target)} for source, target in links]
    _layout(nodes, links)
    return {"trees": [{"name": p["material_name"], "kind": "material", "nodes": nodes, "links": links}]}


def ring_value(radius, **values):
    """The ring phase in [0, 1) the shader computes at a distance from the Z axis, before warping."""
    p = _validate(values)
    if not math.isfinite(radius) or radius < 0:
        raise ValueError("radius is a finite distance of at least 0")
    return (radius * p["rings_per_metre"]) % 1.0


def expectations(**values):
    """What Blender must hold after create() with these parameters on an active mesh."""
    graph = material_graph(**values)["trees"][0]
    return {"materials": {graph["name"]: {"nodes": len(graph["nodes"]), "links": len(graph["links"]),
                                          "output_linked": True, "users": 1}}}


# ------------------------------------------------------------------------------------------------ script mode
def _from_text(spec, text):
    if spec["type"] == PARAMETER_TYPE_BOOL:
        if text.lower() not in ("true", "false", "1", "0", "yes", "no"):
            raise ValueError(f"{spec['name']} takes true or false")
        return text.lower() in ("true", "1", "yes")
    if spec["type"] == PARAMETER_TYPE_INT:
        return int(text)
    if spec["type"] == PARAMETER_TYPE_FLOAT:
        return float(text)
    if spec["type"] == PARAMETER_TYPE_VECTOR:
        return [float(part) for part in text.split(",")]
    return text


def parse_arguments(argv):
    """(parameters, output path) from script arguments such as ["--warp", "0.05", "--output", "a.blend"]."""
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
def _socket(sockets, key):
    if isinstance(key, int):
        return sockets[key]
    for socket in sockets:
        if socket.identifier == key:
            return socket
    for socket in sockets:
        if socket.name == key and getattr(socket, "enabled", True):
            return socket
    raise KeyError(f"no socket {key!r} on {sockets.data.bl_idname if hasattr(sockets, 'data') else 'node'}")


def _build_tree(tree, description):
    tree.nodes.clear()
    made = {}
    for spec in description["nodes"]:
        node = tree.nodes.new(spec["type"])
        node.name = node.label = spec["name"]
        node.location = spec["location"]
        for key, value in spec.get("properties", {}).items():
            setattr(node, key, value)
        if "ramp" in spec:
            ramp = node.color_ramp
            ramp.interpolation = spec["ramp"]["interpolation"]
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


def create(context=None, **values):
    """Build the material, assign it to the active mesh object when asked, and return it."""
    import bpy
    context = context or bpy.context
    p = _validate(values)
    graph = material_graph(**p)["trees"][0]
    material = bpy.data.materials.new(graph["name"])
    if material.node_tree is None:
        material.use_nodes = True
    _build_tree(material.node_tree, graph)
    material.diffuse_color = p["earlywood_color"] + [1.0]
    target = context.active_object
    if p["assign"] and target is not None and target.type == OBJECT_TYPE_MESH:
        target.data.materials.clear()
        target.data.materials.append(material)
    else:
        material.use_fake_user = True
    return material


def _properties(bpy):
    annotations = {}
    for spec in PARAMETERS:
        label, kind = spec["name"].replace("_", " ").title(), spec["type"]
        common = {"name": label, "description": spec["description"]}
        if kind == PARAMETER_TYPE_BOOL:
            annotations[spec["name"]] = bpy.props.BoolProperty(default=spec["default"], **common)
        elif kind == PARAMETER_TYPE_STRING:
            annotations[spec["name"]] = bpy.props.StringProperty(default=spec["default"], **common)
        elif kind == PARAMETER_TYPE_VECTOR:
            annotations[spec["name"]] = bpy.props.FloatVectorProperty(
                size=3, default=spec["default"], min=spec["minimum"], max=spec["maximum"],
                subtype="COLOR" if spec["unit"] == "linear RGB" else "NONE", **common)
        else:
            annotations[spec["name"]] = bpy.props.FloatProperty(default=spec["default"], min=spec["minimum"],
                                                                max=spec["maximum"], **common)
    return annotations


_CLASSES = []


def _menu_entry(self, context):
    self.layout.operator(OPERATOR, text="Wood Rings Material", icon="MATERIAL")


def register():
    """Register the operator and its Object menu entry."""
    import bpy

    def execute(self, context):
        values = {}
        for spec in PARAMETERS:
            value = getattr(self, spec["name"])
            values[spec["name"]] = list(value) if spec["type"] == PARAMETER_TYPE_VECTOR else value
        try:
            create(context, **values)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    operator = type("BALTOR_OT_material_wood_rings", (bpy.types.Operator,), {
        "bl_idname": OPERATOR, "bl_label": "Wood Rings Material", "bl_description": bl_info["description"],
        "bl_options": {"REGISTER", "UNDO"}, "__annotations__": _properties(bpy), "execute": execute})
    bpy.utils.register_class(operator)
    _CLASSES.append(operator)
    bpy.types.VIEW3D_MT_object.append(_menu_entry)


def unregister():
    """Remove the menu entry and the operator."""
    import bpy
    bpy.types.VIEW3D_MT_object.remove(_menu_entry)
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
    """Script mode: build the material on the active object of the opened file, then save when asked."""
    import bpy
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    values, output = parse_arguments(argv)
    create(bpy.context, **values)
    if output:
        _save(output)


if __name__ == "__main__":
    main()
