"""Terrain material that blends grass, rock and snow by slope and height in world space.

The core, material_graph(**parameters), reads the world normal and world position from the Geometry node. The
normal's Z component is the cosine of the slope angle: a map range between cos(rock slope + blend / 2) and
cos(rock slope - blend / 2) gives a rock mask that is 1 on steep ground. The world height, shifted by a noise for a
ragged edge, gives a snow-line mask, which is multiplied by a flatness mask so snow stays off cliffs. Colours and
roughness are mixed grass to rock to snow. Because both inputs are world space, the blend follows the terrain
wherever it is placed and however it is scaled. It needs no Blender. fixture(context) adds a demo hill to shade.

In Blender, create(context, **parameters) builds the material and assigns it to the active object, and register()
adds the operator baltor.material_terrain_slope_height to the Object menu. As a script:

    blender --background land.blend --python material_terrain_slope_height.py -- --snow_height 6 --output t.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Terrain Slope Height Material",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Object > Terrain Slope Height Material",
    "description": "Grass, rock and snow blended by world slope and height with a ragged snow line",
    "category": "Material",
}

OPERATOR = "baltor.material_terrain_slope_height"
MENU = {"menu": "VIEW3D_MT_object", "label": "Terrain Slope Height Material", "icon": "MATERIAL"}
BLENDER_ENTRY = "create"
FIXTURE_NAME = "Terrain Demo Hill"
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
    {"name": "material_name", "type": "string", "default": "Baltor Terrain Blend", "minimum": None,
     "maximum": None, "unit": "text", "description": "Name of the new material."},
    {"name": "grass_color", "type": "vector", "default": [0.07, 0.16, 0.035], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour of flat low ground."},
    {"name": "rock_color", "type": "vector", "default": [0.2, 0.18, 0.16], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour of steep ground."},
    {"name": "snow_color", "type": "vector", "default": [0.85, 0.87, 0.9], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Colour of high flat ground."},
    {"name": "rock_slope", "type": "float", "default": 32.0, "minimum": 1.0, "maximum": 89.0, "unit": "degree",
     "description": "Slope angle where ground turns from grass to rock."},
    {"name": "slope_blend", "type": "float", "default": 10.0, "minimum": 0.5, "maximum": 60.0, "unit": "degree",
     "description": "Width of the grass to rock transition."},
    {"name": "snow_height", "type": "float", "default": 2.2, "minimum": -10000.0, "maximum": 10000.0,
     "unit": "m", "description": "World height of the snow line."},
    {"name": "snow_blend", "type": "float", "default": 0.4, "minimum": 0.001, "maximum": 1000.0, "unit": "m",
     "description": "Height over which snow fades in."},
    {"name": "snow_max_slope", "type": "float", "default": 40.0, "minimum": 1.0, "maximum": 89.0,
     "unit": "degree", "description": "Steepest slope that holds snow."},
    {"name": "breakup", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 100.0, "unit": "m",
     "description": "How far noise moves the snow line up and down."},
    {"name": "assign", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Assign the material to the active object."},
)


def _extra_checks(p):
    if not p["material_name"].strip() or len(p["material_name"]) > 63:
        raise ValueError("material_name must be 1 to 63 characters")
    if p["rock_slope"] + p["slope_blend"] / 2.0 >= 90.0 or p["rock_slope"] - p["slope_blend"] / 2.0 <= 0.0:
        raise ValueError("rock_slope plus or minus half the blend must stay between 0 and 90 degrees")


# ------------------------------------------------------------------------------------------------ pure core
def layer_weights(normal_z, height, noise=0.5, **values):
    """(grass, rock, snow) weights at a point from the normal's Z, the world height and a noise value."""
    p = _validate(values)
    steep = math.cos(math.radians(p["rock_slope"] + p["slope_blend"] / 2.0))
    gentle = math.cos(math.radians(p["rock_slope"] - p["slope_blend"] / 2.0))
    rock = min(1.0, max(0.0, (gentle - normal_z) / (gentle - steep)))
    raised = height + (noise - 0.5) * 2.0 * p["breakup"]
    line = min(1.0, max(0.0, (raised - (p["snow_height"] - p["snow_blend"])) / p["snow_blend"]))
    flat_low = math.cos(math.radians(p["snow_max_slope"]))
    flat = min(1.0, max(0.0, (normal_z - flat_low) / (1.0 - flat_low)))
    snow = line * flat
    return [(1.0 - rock) * (1.0 - snow), rock * (1.0 - snow), snow]


def material_graph(**values):
    """The material as {"trees": [{"name", "kind": "material", "nodes", "links"}]} in plain data."""
    p = _validate(values)
    steep = math.cos(math.radians(p["rock_slope"] + p["slope_blend"] / 2.0))
    gentle = math.cos(math.radians(p["rock_slope"] - p["slope_blend"] / 2.0))
    nodes = [
        {"name": "Geometry", "type": "ShaderNodeNewGeometry"},
        {"name": "Normal Axes", "type": "ShaderNodeSeparateXYZ"},
        {"name": "Position Axes", "type": "ShaderNodeSeparateXYZ"},
        {"name": "Rock Mask", "type": "ShaderNodeMapRange",
         "inputs": {"From Min": gentle, "From Max": steep, "To Min": 0.0, "To Max": 1.0}},
        {"name": "Breakup Noise", "type": "ShaderNodeTexNoise", "inputs": {"Scale": 0.35, "Detail": 5.0}},
        {"name": "Ragged Height", "type": "ShaderNodeMath", "properties": {"operation": "MULTIPLY_ADD"},
         "inputs": {"Value_001": 2.0 * p["breakup"]}},
        {"name": "Recentre", "type": "ShaderNodeMath", "properties": {"operation": "SUBTRACT"},
         "inputs": {"Value_001": p["breakup"]}},
        {"name": "Snow Line", "type": "ShaderNodeMapRange",
         "inputs": {"From Min": p["snow_height"] - p["snow_blend"], "From Max": p["snow_height"], "To Min": 0.0,
                    "To Max": 1.0}},
        {"name": "Flatness", "type": "ShaderNodeMapRange",
         "inputs": {"From Min": math.cos(math.radians(p["snow_max_slope"])), "From Max": 1.0, "To Min": 0.0,
                    "To Max": 1.0}},
        {"name": "Snow Mask", "type": "ShaderNodeMath", "properties": {"operation": "MULTIPLY"}},
        {"name": "Grass Or Rock", "type": "ShaderNodeMix", "properties": {"data_type": "RGBA", "blend_type": "MIX"},
         "inputs": {"A_Color": p["grass_color"] + [1.0], "B_Color": p["rock_color"] + [1.0]}},
        {"name": "Add Snow", "type": "ShaderNodeMix", "properties": {"data_type": "RGBA", "blend_type": "MIX"},
         "inputs": {"B_Color": p["snow_color"] + [1.0]}},
        {"name": "Rock Roughness", "type": "ShaderNodeMix", "properties": {"data_type": "FLOAT"},
         "inputs": {"A_Float": 0.95, "B_Float": 0.72}},
        {"name": "Snow Roughness", "type": "ShaderNodeMix", "properties": {"data_type": "FLOAT"},
         "inputs": {"B_Float": 0.45}},
        {"name": "Ground", "type": "ShaderNodeBsdfPrincipled"},
        {"name": "Output", "type": "ShaderNodeOutputMaterial"},
    ]
    links = _links([
        (("Geometry", "Normal"), ("Normal Axes", "Vector")),
        (("Geometry", "Position"), ("Position Axes", "Vector")),
        (("Normal Axes", "Z"), ("Rock Mask", "Value")),
        (("Geometry", "Position"), ("Breakup Noise", "Vector")),
        (("Breakup Noise", "Fac"), ("Ragged Height", "Value")),
        (("Position Axes", "Z"), ("Ragged Height", "Value_002")),
        (("Ragged Height", "Value"), ("Recentre", "Value")),
        (("Recentre", "Value"), ("Snow Line", "Value")),
        (("Normal Axes", "Z"), ("Flatness", "Value")),
        (("Snow Line", "Result"), ("Snow Mask", "Value")),
        (("Flatness", "Result"), ("Snow Mask", "Value_001")),
        (("Rock Mask", "Result"), ("Grass Or Rock", "Factor_Float")),
        (("Snow Mask", "Value"), ("Add Snow", "Factor_Float")),
        (("Grass Or Rock", "Result_Color"), ("Add Snow", "A_Color")),
        (("Rock Mask", "Result"), ("Rock Roughness", "Factor_Float")),
        (("Snow Mask", "Value"), ("Snow Roughness", "Factor_Float")),
        (("Rock Roughness", "Result_Float"), ("Snow Roughness", "A_Float")),
        (("Add Snow", "Result_Color"), ("Ground", "Base Color")),
        (("Snow Roughness", "Result_Float"), ("Ground", "Roughness")),
        (("Ground", "BSDF"), ("Output", "Surface")),
    ])
    _layout(nodes, links)
    return {"trees": [{"name": p["material_name"], "kind": "material", "nodes": nodes, "links": links}]}


def expectations(**values):
    """What Blender must hold after create() on the demo hill."""
    tree = material_graph(**values)["trees"][0]
    return {"materials": {tree["name"]: {"nodes": len(tree["nodes"]), "links": len(tree["links"]),
                                         "output_linked": True, "users": 1}},
            "objects": {FIXTURE_NAME: {"type": "MESH", "materials": [tree["name"]]}}}


def fixture(context=None):
    """Add a demo hill (a Gaussian bump with a steep ridge, 3 m high) and make it active."""
    import bpy
    context = context or bpy.context
    size, cells = 8.0, 48
    vertices, faces = [], []
    for j in range(cells + 1):
        for i in range(cells + 1):
            x, y = (i / cells - 0.5) * size, (j / cells - 0.5) * size
            z = 3.0 * math.exp(-(x * x + y * y) / 4.0) + 0.6 * max(0.0, 1.0 - abs(x - 1.2) * 1.5) * (y > -1.0)
            vertices.append((x, y, z))
    for j in range(cells):
        for i in range(cells):
            a = j * (cells + 1) + i
            faces.append((a, a + 1, a + cells + 2, a + cells + 1))
    mesh = bpy.data.meshes.new(FIXTURE_NAME)
    mesh.from_pydata(vertices, [], faces)
    mesh.polygons.foreach_set("use_smooth", [True] * len(faces))
    obj = bpy.data.objects.new(FIXTURE_NAME, mesh)
    (context.collection or context.scene.collection).objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def create(context=None, **values):
    """Build the material, assign it to the active object when asked, and return it."""
    import bpy
    context = context or bpy.context
    p = _validate(values)
    material = _new_material(bpy, material_graph(**p)["trees"][0])
    material.diffuse_color = p["grass_color"] + [1.0]
    return _assign_material(context, material, p["assign"])


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
