"""PBR material from a folder of texture maps: each file is classified by the words in its name and wired up.

The core, classify(names), splits each file name into lower-case tokens and matches them against a synonym table:
base colour (basecolor, albedo, diffuse, col), roughness, gloss (inverted into roughness), metallic, normal, height
(displacement, bump), ambient occlusion, opacity and emission. A normal map named with dx or directx is treated as
DirectX and its green channel is inverted; gl or opengl, or no hint, is treated as OpenGL. The first file wins
when two match one channel and the others are reported. material_graph(files) then builds the node tree: shared
UV mapping, one image node per channel with the right colour space, ambient occlusion multiplied into the base
colour, a Normal Map node and a Displacement node on the material output. It needs no Blender.

In Blender, create(context, **parameters) lists the folder, loads the images and builds the material on the active
object; register() adds the operator baltor.material_pbr_from_folder to the Object menu. As a script:

    blender --background scene.blend --python material_pbr_from_folder.py -- --folder //textures/rock --output r.blend
"""
import json
import math
import os
import re
import sys

bl_info = {
    "name": "Baltor PBR From Folder",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Object > PBR Material From Folder",
    "description": "Build a PBR material from a folder of maps detected by file name",
    "category": "Material",
}

OPERATOR = "baltor.material_pbr_from_folder"
MENU = {"menu": "VIEW3D_MT_object", "label": "PBR Material From Folder", "icon": "MATERIAL"}
BLENDER_ENTRY = "create"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga", ".bmp", ".webp")
SYNONYMS = {
    "base_color": ("basecolor", "albedo", "diffuse", "diff", "col", "color", "colour", "basecolour"),
    "roughness": ("roughness", "rough", "rgh"),
    "gloss": ("gloss", "glossiness", "smoothness"),
    "metallic": ("metallic", "metalness", "metal", "mtl"),
    "normal": ("normal", "nrm", "nor", "norm", "normalgl", "normaldx"),
    "height": ("height", "displacement", "disp", "bump", "depth"),
    "ao": ("ao", "ambientocclusion", "occlusion", "occ"),
    "alpha": ("opacity", "alpha", "transparency"),
    "emission": ("emission", "emissive", "emit", "glow"),
}
DEMO_FILES = ["rock_wall_basecolor.png", "rock_wall_roughness.png", "rock_wall_normal_dx.png", "rock_wall_height.png",
              "rock_wall_ao.png", "rock_wall_preview.txt"]
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
    {"name": "material_name", "type": "string", "default": "Baltor PBR", "minimum": None, "maximum": None,
     "unit": "text", "description": "Name of the new material."},
    {"name": "folder", "type": "string", "default": "//textures/pbr_demo", "minimum": None, "maximum": None,
     "unit": "path", "description": "Folder with the maps; // is relative to the .blend file."},
    {"name": "uv_scale", "type": "float", "default": 1.0, "minimum": 0.001, "maximum": 10000.0, "unit": "repeats",
     "description": "Repeats of the maps per UV unit."},
    {"name": "normal_strength", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 10.0, "unit": "ratio",
     "description": "Strength of the normal map."},
    {"name": "displacement_scale", "type": "float", "default": 0.02, "minimum": 0.0, "maximum": 10.0, "unit": "m",
     "description": "Height of the displacement from the height map."},
    {"name": "ao_strength", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 1.0, "unit": "ratio",
     "description": "How strongly ambient occlusion darkens the base colour."},
    {"name": "assign", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Assign the material to the active object."},
)


def _extra_checks(p):
    if not p["material_name"].strip() or len(p["material_name"]) > 63:
        raise ValueError("material_name must be 1 to 63 characters")
    if not p["folder"].strip():
        raise ValueError("folder must name a folder")


# ------------------------------------------------------------------------------------------------ pure core
def tokens(name):
    """Lower-case word tokens of a file name without its suffix, splitting camel case and separators."""
    stem = name.rsplit(".", 1)[0]
    stem = re.sub(r"([a-z])([A-Z])", r"\1_\2", stem)
    return [token for token in re.split(r"[^A-Za-z0-9]+", stem.lower()) if token]


def classify(names):
    """{"channels": {channel: file}, "normal_convention", "ignored": [...], "duplicates": [...]} from file names."""
    channels, ignored, duplicates, convention = {}, [], [], "opengl"
    for name in sorted(names):
        if not name.lower().endswith(IMAGE_SUFFIXES):
            ignored.append(name)
            continue
        words = tokens(name)
        joined = set(words) | {a + b for a, b in zip(words, words[1:])}
        found = [channel for channel, synonyms in SYNONYMS.items() if joined & set(synonyms)]
        if not found:
            ignored.append(name)
            continue
        channel = found[0] if "normal" not in found else "normal"
        if channel in channels:
            duplicates.append(name)
            continue
        channels[channel] = name
        if channel == "normal" and (set(words) & {"dx", "directx", "normaldx"}):
            convention = "directx"
    if "gloss" in channels and "roughness" not in channels:
        channels["roughness_from_gloss"] = channels.pop("gloss")
    elif "gloss" in channels:
        duplicates.append(channels.pop("gloss"))
    return {"channels": channels, "normal_convention": convention, "ignored": ignored, "duplicates": duplicates}


def _image_node(name, channel, file, colorspace):
    return {"name": name, "type": "ShaderNodeTexImage",
            "image": {"file": file, "colorspace": colorspace, "channel": channel}}


def material_graph(files=None, **values):
    """The material for a list of file names (the demo list when None), as plain data."""
    p = _validate(values)
    found = classify(DEMO_FILES if files is None else files)
    channels = found["channels"]
    if "base_color" not in channels and "roughness" not in channels and "normal" not in channels:
        raise ValueError("no base colour, roughness or normal map was recognised")
    nodes = [{"name": "UV", "type": "ShaderNodeTexCoord"},
             {"name": "Repeat", "type": "ShaderNodeMapping", "inputs": {"Scale": [p["uv_scale"]] * 3}},
             {"name": "Surface", "type": "ShaderNodeBsdfPrincipled"},
             {"name": "Output", "type": "ShaderNodeOutputMaterial"}]
    pairs = [(("UV", "UV"), ("Repeat", "Vector")), (("Surface", "BSDF"), ("Output", "Surface"))]
    images = []

    def add_image(channel, colorspace):
        name = channel.replace("_", " ").title() + " Texture"
        nodes.append(_image_node(name, channel, channels[channel], colorspace))
        pairs.append((("Repeat", "Vector"), (name, "Vector")))
        images.append({"file": channels[channel], "colorspace": colorspace})
        return name

    if "base_color" in channels:
        base = add_image("base_color", "sRGB")
        if "ao" in channels:
            ao = add_image("ao", "Non-Color")
            nodes.append({"name": "Apply AO", "type": "ShaderNodeMix",
                          "properties": {"data_type": "RGBA", "blend_type": "MULTIPLY"},
                          "inputs": {"Factor_Float": p["ao_strength"]}})
            pairs += [((base, "Color"), ("Apply AO", "A_Color")), ((ao, "Color"), ("Apply AO", "B_Color")),
                      (("Apply AO", "Result_Color"), ("Surface", "Base Color"))]
        else:
            pairs.append(((base, "Color"), ("Surface", "Base Color")))
    if "roughness" in channels:
        pairs.append(((add_image("roughness", "Non-Color"), "Color"), ("Surface", "Roughness")))
    elif "roughness_from_gloss" in channels:
        gloss = add_image("roughness_from_gloss", "Non-Color")
        nodes.append({"name": "Gloss To Roughness", "type": "ShaderNodeInvert", "inputs": {"Fac": 1.0}})
        pairs += [((gloss, "Color"), ("Gloss To Roughness", "Color")),
                  (("Gloss To Roughness", "Color"), ("Surface", "Roughness"))]
    if "metallic" in channels:
        pairs.append(((add_image("metallic", "Non-Color"), "Color"), ("Surface", "Metallic")))
    if "alpha" in channels:
        pairs.append(((add_image("alpha", "Non-Color"), "Color"), ("Surface", "Alpha")))
    if "emission" in channels:
        pairs.append(((add_image("emission", "sRGB"), "Color"), ("Surface", "Emission Color")))
        nodes[2].setdefault("inputs", {})["Emission Strength"] = 1.0
    if "normal" in channels:
        normal = add_image("normal", "Non-Color")
        nodes.append({"name": "Normal Map", "type": "ShaderNodeNormalMap",
                      "inputs": {"Strength": p["normal_strength"]}})
        if found["normal_convention"] == "directx":
            nodes += [{"name": "Split Normal", "type": "ShaderNodeSeparateColor"},
                      {"name": "Flip Green", "type": "ShaderNodeMath", "properties": {"operation": "SUBTRACT"},
                       "inputs": {"Value": 1.0}},
                      {"name": "OpenGL Normal", "type": "ShaderNodeCombineColor"}]
            pairs += [((normal, "Color"), ("Split Normal", "Color")),
                      (("Split Normal", "Red"), ("OpenGL Normal", "Red")),
                      (("Split Normal", "Green"), ("Flip Green", "Value_001")),
                      (("Flip Green", "Value"), ("OpenGL Normal", "Green")),
                      (("Split Normal", "Blue"), ("OpenGL Normal", "Blue")),
                      (("OpenGL Normal", "Color"), ("Normal Map", "Color"))]
        else:
            pairs.append(((normal, "Color"), ("Normal Map", "Color")))
        pairs.append((("Normal Map", "Normal"), ("Surface", "Normal")))
    if "height" in channels:
        height = add_image("height", "Non-Color")
        nodes.append({"name": "Displacement", "type": "ShaderNodeDisplacement",
                      "inputs": {"Midlevel": 0.5, "Scale": p["displacement_scale"]}})
        pairs += [((height, "Color"), ("Displacement", "Height")),
                  (("Displacement", "Displacement"), ("Output", "Displacement"))]
    links = _links(pairs)
    _layout(nodes, links)
    report = {"channels": channels, "normal_convention": found["normal_convention"], "ignored": found["ignored"],
              "duplicates": found["duplicates"]}
    return {"trees": [{"name": p["material_name"], "kind": "material", "nodes": nodes, "links": links}],
            "images": images, "report": report}


def expectations(**values):
    """What Blender must hold after fixture() and create() with the defaults."""
    graph = material_graph(**values)
    tree = graph["trees"][0]
    return {"materials": {tree["name"]: {"nodes": len(tree["nodes"]), "links": len(tree["links"]),
                                         "output_linked": True, "users": 1}},
            "images": {image["file"]: {"source": "FILE", "size": [16, 16]} for image in graph["images"]}}


def _folder(path):
    import bpy
    return os.path.abspath(bpy.path.abspath(path))


def fixture(context=None):
    """Write 16 x 16 demo maps named like DEMO_FILES into the default folder and add a UV sphere to shade."""
    import bpy
    context = context or bpy.context
    folder = _folder(PARAMETERS[1]["default"])
    os.makedirs(folder, exist_ok=True)
    for name in DEMO_FILES:
        target = os.path.join(folder, name)
        if not name.endswith(".png"):
            with open(target, "w", encoding="utf-8") as stream:
                stream.write("not a texture\n")
            continue
        image = bpy.data.images.new("baltor_demo_" + name, 16, 16)
        pixels = []
        for y in range(16):
            for x in range(16):
                checker = ((x // 4) + (y // 4)) % 2
                if "basecolor" in name:
                    pixels += [0.35 + 0.2 * checker, 0.3 + 0.15 * checker, 0.25, 1.0]
                elif "normal" in name:
                    pixels += [0.5 + 0.2 * (checker - 0.5), 0.5, 1.0, 1.0]
                else:
                    pixels += [0.3 + 0.4 * checker] * 3 + [1.0]
        image.pixels = pixels
        image.filepath_raw = target
        image.file_format = "PNG"
        image.save()
        bpy.data.images.remove(image)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0, location=(0.0, 0.0, 1.0))
    sphere = context.active_object
    sphere.name = sphere.data.name = "PBR Demo Sphere"
    return sphere


def create(context=None, **values):
    """Build the material from the folder's maps, assign it to the active object when asked, and return it."""
    import bpy
    context = context or bpy.context
    p = _validate(values)
    folder = _folder(p["folder"])
    if not os.path.isdir(folder):
        raise ValueError(f"folder not found: {folder}")
    graph = material_graph(sorted(os.listdir(folder)), **p)
    material = _new_material(bpy, graph["trees"][0])
    for spec in graph["trees"][0]["nodes"]:
        if "image" in spec:
            image = bpy.data.images.load(os.path.join(folder, spec["image"]["file"]), check_existing=True)
            image.colorspace_settings.name = spec["image"]["colorspace"]
            material.node_tree.nodes[spec["name"]].image = image
    _assign_material(context, material, p["assign"])
    return {"material": material.name, "report": graph["report"]}


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
