"""Height fog volume: a box whose fog density falls off exponentially with height and breaks up with noise.

The core, build_geometry(**parameters), returns the box as a closed mesh and its volume material as a node tree. The
density at world height z is d0 * exp(-(z - base) / h), where d0 is the density at the base and h the height over
which it falls to 1 / e, multiplied by a noise term between 1 - breakup and 1 + breakup so the fog drifts in
patches. A Principled Volume node scatters with the fog colour and anisotropy. The box shows only its bounds in the
viewport so it does not hide the scene. It needs no Blender.

In Blender, create(context, **parameters) adds the fog box at the 3D cursor, and register() adds the operator
baltor.fog_volume_height to the Add menu. As a script:

    blender --background scene.blend --python fog_volume_height.py -- --density 0.3 --falloff 2 --output fog.blend
"""
import json
import math
import sys

bl_info = {
    "name": "Baltor Height Fog Volume",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Height Fog Volume",
    "description": "Box of volumetric fog that thins exponentially with height, with noise breakup",
    "category": "Lighting",
}

OPERATOR = "baltor.fog_volume_height"
MENU = {"menu": "VIEW3D_MT_add", "label": "Height Fog Volume", "icon": "OUTLINER_DATA_VOLUME"}
BLENDER_ENTRY = "create"
OBJECT_NAME = "Height Fog"
MATERIAL_NAME = "Baltor Height Fog"
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
    {"name": "size", "type": "vector", "default": [6.0, 6.0, 3.0], "minimum": 0.01, "maximum": 100000.0,
     "unit": "m", "description": "Width, depth and height of the fog box."},
    {"name": "density", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 1000.0, "unit": "1/m",
     "description": "Fog density at the bottom of the box."},
    {"name": "falloff", "type": "float", "default": 1.2, "minimum": 0.001, "maximum": 100000.0, "unit": "m",
     "description": "Height over which the density falls to 1 / e (about 37 percent)."},
    {"name": "breakup", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0, "unit": "ratio",
     "description": "How much noise varies the density, as a share of it."},
    {"name": "noise_scale", "type": "float", "default": 0.35, "minimum": 0.001, "maximum": 1000.0, "unit": "1/m",
     "description": "Frequency of the noise patches."},
    {"name": "color", "type": "vector", "default": [0.85, 0.88, 0.92], "minimum": 0.0, "maximum": 1.0,
     "unit": "linear RGB", "description": "Scattering colour of the fog."},
    {"name": "anisotropy", "type": "float", "default": 0.3, "minimum": -0.95, "maximum": 0.95, "unit": "ratio",
     "description": "Forward (positive) or backward (negative) scattering."},
)


# ------------------------------------------------------------------------------------------------ pure core
def density_at(height, noise=0.5, **values):
    """Fog density at a height above the box base, for a noise value in [0, 1]."""
    p = _validate(values)
    return p["density"] * math.exp(-max(0.0, height) / p["falloff"]) * (1.0 + (2.0 * noise - 1.0) * p["breakup"])


def build_geometry(**values):
    """The fog box (closed mesh, base at z = 0) and its volume material as plain data."""
    p = _validate(values)
    hx, hy, sz = p["size"][0] / 2.0, p["size"][1] / 2.0, p["size"][2]
    vertices = [[-hx, -hy, 0.0], [hx, -hy, 0.0], [hx, hy, 0.0], [-hx, hy, 0.0],
                [-hx, -hy, sz], [hx, -hy, sz], [hx, hy, sz], [-hx, hy, sz]]
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    nodes = [
        {"name": "Geometry", "type": "ShaderNodeNewGeometry"},
        {"name": "Object Base", "type": "ShaderNodeObjectInfo"},
        {"name": "Point Axes", "type": "ShaderNodeSeparateXYZ"},
        {"name": "Base Axes", "type": "ShaderNodeSeparateXYZ"},
        {"name": "Height", "type": "ShaderNodeMath", "properties": {"operation": "SUBTRACT"}},
        {"name": "Scaled Height", "type": "ShaderNodeMath", "properties": {"operation": "DIVIDE"},
         "inputs": {"Value_001": -p["falloff"]}},
        {"name": "Falloff", "type": "ShaderNodeMath", "properties": {"operation": "EXPONENT"}},
        {"name": "Base Density", "type": "ShaderNodeMath", "properties": {"operation": "MULTIPLY"},
         "inputs": {"Value_001": p["density"]}},
        {"name": "Drift Noise", "type": "ShaderNodeTexNoise", "inputs": {"Scale": p["noise_scale"], "Detail": 3.0}},
        {"name": "Breakup", "type": "ShaderNodeMapRange",
         "inputs": {"From Min": 0.0, "From Max": 1.0, "To Min": 1.0 - p["breakup"], "To Max": 1.0 + p["breakup"]}},
        {"name": "Density", "type": "ShaderNodeMath", "properties": {"operation": "MULTIPLY"}},
        {"name": "Fog", "type": "ShaderNodeVolumePrincipled",
         "inputs": {"Color": p["color"] + [1.0], "Anisotropy": p["anisotropy"]}},
        {"name": "Output", "type": "ShaderNodeOutputMaterial"},
    ]
    links = _links([
        (("Geometry", "Position"), ("Point Axes", "Vector")),
        (("Object Base", "Location"), ("Base Axes", "Vector")),
        (("Point Axes", "Z"), ("Height", "Value")),
        (("Base Axes", "Z"), ("Height", "Value_001")),
        (("Height", "Value"), ("Scaled Height", "Value")),
        (("Scaled Height", "Value"), ("Falloff", "Value")),
        (("Falloff", "Value"), ("Base Density", "Value")),
        (("Geometry", "Position"), ("Drift Noise", "Vector")),
        (("Drift Noise", "Fac"), ("Breakup", "Value")),
        (("Base Density", "Value"), ("Density", "Value")),
        (("Breakup", "Result"), ("Density", "Value_001")),
        (("Density", "Value"), ("Fog", "Density")),
        (("Fog", "Volume"), ("Output", "Volume")),
    ])
    _layout(nodes, links)
    return {"vertices": vertices, "faces": faces,
            "trees": [{"name": MATERIAL_NAME, "kind": "material", "nodes": nodes, "links": links}],
            "report": {"density_at_base": p["density"], "density_at_top": round(p["density"] * math.exp(
                -sz / p["falloff"]), 9), "visibility_at_base_m": round(3.0 / p["density"], 6) if p["density"] else None}}


def expectations(**values):
    """What Blender must hold after create() with these parameters."""
    mesh = build_geometry(**values)
    tree = mesh["trees"][0]
    low = [min(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    high = [max(vertex[axis] for vertex in mesh["vertices"]) for axis in range(3)]
    return {"objects": {OBJECT_NAME: {"type": "MESH", "vertices": 8, "faces": 6, "bounds": [low, high],
                                      "materials": [MATERIAL_NAME], "attributes": {"display_type": "BOUNDS"}}},
            "materials": {MATERIAL_NAME: {"nodes": len(tree["nodes"]), "links": len(tree["links"]),
                                          "output_linked": True, "users": 1}}}


def create(context=None, **values):
    """Add the fog box with its volume material at the 3D cursor and return the object."""
    import bpy
    context = context or bpy.context
    mesh = build_geometry(**values)
    material = bpy.data.materials.new(MATERIAL_NAME)
    if material.node_tree is None:
        material.use_nodes = True
    _build_tree(material.node_tree, mesh["trees"][0])
    obj = _link_mesh(context, OBJECT_NAME, {"vertices": mesh["vertices"], "faces": mesh["faces"]})
    obj.data.materials.append(material)
    obj.display_type = "BOUNDS"
    return obj


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
