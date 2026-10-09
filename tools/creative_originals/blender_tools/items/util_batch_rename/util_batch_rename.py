"""Batch rename objects by rule: strip .001 suffixes, find and replace, case style, prefix, suffix, numbering.

The core, plan_renames(names, existing, **parameters), turns a list of names into a rename plan with no
collisions among the new names or with names outside the batch, and keeps every name within Blender's 63-byte
limit. It needs no Blender. Called without names it plans the built-in demo list, so the plan can be checked
anywhere.

In Blender, run(context, **parameters) renames the selected objects (or all objects) through temporary names so
Blender never appends .001 on the way, renames single-user object data to match, and returns the plan.
register() adds the operator baltor.util_batch_rename to the Object menu. As a script on a saved file:

    blender --background scene.blend --python util_batch_rename.py -- --prefix SM_ --case snake --output out.blend
"""
import re
import sys

bl_info = {
    "name": "Baltor Batch Rename",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Object > Batch Rename by Rule",
    "description": "Rename objects by rule with case styles, prefixes and collision-free numbering",
    "category": "Object",
}

OPERATOR = "baltor.util_batch_rename"
NAME_BYTES = 63
DEMO_NAMES = ["Cube", "Cube.001", "Cube.002", "Sphere", "lampPost", "Old Barrel", "SM_rock"]
# The values a PARAMETERS row can take in "type".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETERS = (
    {"name": "prefix", "type": "string", "default": "SM_", "minimum": None, "maximum": None, "unit": "text",
     "description": "Text put in front of every name (not repeated when already present)."},
    {"name": "suffix", "type": "string", "default": "", "minimum": None, "maximum": None, "unit": "text",
     "description": "Text put after every name, before any number."},
    {"name": "find", "type": "string", "default": "", "minimum": None, "maximum": None, "unit": "text",
     "description": "Text or regular expression to replace; empty skips this step."},
    {"name": "replace", "type": "string", "default": "", "minimum": None, "maximum": None, "unit": "text",
     "description": "Replacement for find; with use_regex it may use groups such as \\1."},
    {"name": "use_regex", "type": "bool", "default": False, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Treat find as a Python regular expression."},
    {"name": "case", "type": "choice", "default": "snake", "minimum": None, "maximum": None, "unit": "style",
     "choices": ["keep", "lower", "upper", "snake", "pascal"],
     "description": "Case style applied to the words of the name."},
    {"name": "strip_duplicate_suffix", "type": "bool", "default": True, "minimum": None, "maximum": None,
     "unit": "flag", "description": "Remove Blender's .001 style suffix first."},
    {"name": "numbering", "type": "choice", "default": "duplicates", "minimum": None, "maximum": None,
     "unit": "mode", "choices": ["none", "duplicates", "always"],
     "description": "Number every name, only names that would collide, or none."},
    {"name": "start", "type": "int", "default": 1, "minimum": 0, "maximum": 100000, "unit": "count",
     "description": "First number of a numbered group."},
    {"name": "padding", "type": "int", "default": 2, "minimum": 1, "maximum": 6, "unit": "digits",
     "description": "Digits of each number, padded with zeros."},
    {"name": "separator", "type": "string", "default": "_", "minimum": None, "maximum": None, "unit": "text",
     "description": "Text between a name and its number."},
    {"name": "scope", "type": "choice", "default": "selected", "minimum": None, "maximum": None, "unit": "mode",
     "choices": ["selected", "all"], "description": "Rename the selected objects or every object in the file."},
    {"name": "rename_data", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Give single-user object data (meshes, curves, lights) the new object name."},
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
        kind = spec["type"]
        if kind == PARAMETER_TYPE_BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be true or false")
        elif kind == PARAMETER_TYPE_CHOICE:
            if value not in spec["choices"]:
                raise ValueError(f"{name} must be one of {', '.join(spec['choices'])}")
        elif kind == PARAMETER_TYPE_STRING:
            if not isinstance(value, str) or len(value.encode("utf-8")) > NAME_BYTES:
                raise ValueError(f"{name} must be text of at most {NAME_BYTES} bytes")
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) != int(value):
                raise ValueError(f"{name} must be a whole number")
            value = int(value)
            if not spec["minimum"] <= value <= spec["maximum"]:
                raise ValueError(f"{name} must lie in [{spec['minimum']}, {spec['maximum']}]")
        result[name] = value
    if result["use_regex"] and result["find"]:
        try:
            re.compile(result["find"])
        except re.error as error:
            raise ValueError(f"find is not a valid regular expression: {error}") from None
    return result


def parameters(**values):
    """The validated parameters with defaults filled in; raises ValueError on an unknown name or a bad value."""
    return _validate(values)


# ------------------------------------------------------------------------------------------------ pure core
def words(text):
    """Words of a name, split at separators, case changes and digit runs: "lampPost2 x" -> lamp, Post, 2, x."""
    return re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+", text)


def styled(text, case):
    """A name in one case style."""
    if case == "keep":
        return text
    if case == "lower":
        return text.lower()
    if case == "upper":
        return text.upper()
    parts = words(text)
    if case == "snake":
        return "_".join(part.lower() for part in parts)
    return "".join(part[:1].upper() + part[1:].lower() for part in parts)


def _fit(text, room):
    data = text.encode("utf-8")[:max(0, room)]
    return data.decode("utf-8", "ignore")


def plan_renames(names=None, existing=None, **values):
    """A rename plan {"report": {"renames": [[old, new], ...], counts}} with unique new names."""
    p = _validate(values)
    names = list(DEMO_NAMES if names is None else names)
    existing = set(existing or ()) - set(names)
    if len(set(names)) != len(names):
        raise ValueError("names must be distinct")
    stems = {}
    for name in names:
        stem = re.sub(r"\.[0-9]{3,}$", "", name) if p["strip_duplicate_suffix"] else name
        if p["find"]:
            stem = re.sub(p["find"], p["replace"], stem) if p["use_regex"] else stem.replace(p["find"], p["replace"])
        if p["prefix"] and stem.startswith(p["prefix"]):
            stem = stem[len(p["prefix"]):]
        stem = styled(stem, p["case"]) or "unnamed"
        stems[name] = stem
    fixed = len((p["prefix"] + p["suffix"] + p["separator"]).encode("utf-8")) + p["padding"] + 1

    def compose(stem, number=None):
        tail = p["suffix"] + ("" if number is None else p["separator"] + str(number).zfill(p["padding"]))
        return p["prefix"] + _fit(stem, NAME_BYTES - fixed) + tail

    groups = {}
    for name in sorted(names):
        groups.setdefault(compose(stems[name]), []).append(name)
    plan, taken, numbered = {}, set(existing), 0
    for target, members in sorted(groups.items()):
        number_all = p["numbering"] == "always" or (p["numbering"] == "duplicates" and (
            len(members) > 1 or target in existing))
        counter = p["start"]
        for name in members:
            if number_all:
                candidate = compose(stems[name], counter)
                while candidate in taken:
                    counter += 1
                    candidate = compose(stems[name], counter)
                counter += 1
                numbered += 1
            else:
                candidate, extra = target, 2
                while candidate in taken:
                    candidate = compose(stems[name], extra)
                    extra += 1
            taken.add(candidate)
            plan[name] = candidate
    renames = [[name, plan[name]] for name in names]
    changed = sum(1 for old, new in renames if old != new)
    return {"report": {"renames": renames, "renamed": changed, "unchanged": len(renames) - changed,
                       "numbered": numbered}}


def expectations(**values):
    """What Blender must hold after run() on the demo objects that fixture() adds."""
    plan = plan_renames(**values)["report"]["renames"]
    data = parameters(**values)["rename_data"]
    return {"objects": {new: {"type": "MESH", "data_name": new if data else old} for old, new in plan},
            "counts": {"objects": len(plan)}}


# ------------------------------------------------------------------------------------------------ script mode
def parse_arguments(argv):
    """(parameters, output path) from script arguments such as ["--prefix", "SM_", "--output", "a.blend"]."""
    specs = {spec["name"]: spec for spec in PARAMETERS}
    values, output = {}, None
    if len(argv) % 2:
        raise ValueError("arguments come in --name value pairs")
    for key, text in zip(argv[0::2], argv[1::2]):
        name = key[2:].replace("-", "_") if key.startswith("--") else None
        if name == "output":
            output = text
        elif name in specs:
            kind = specs[name]["type"]
            if kind == PARAMETER_TYPE_BOOL:
                if text.lower() not in ("true", "false", "1", "0", "yes", "no"):
                    raise ValueError(f"{name} takes true or false")
                values[name] = text.lower() in ("true", "1", "yes")
            else:
                values[name] = int(text) if kind == PARAMETER_TYPE_INT else text
        else:
            raise ValueError(f"unknown argument {key}")
    return _validate(values), output


# ------------------------------------------------------------------------------------------------ Blender layer
def fixture(context=None):
    """Add the demo objects whose names plan_renames() plans by default, all selected."""
    import bpy
    context = context or bpy.context
    collection = context.collection or context.scene.collection
    for index, name in enumerate(DEMO_NAMES):
        mesh = bpy.data.meshes.new(name)
        size = 0.3
        mesh.from_pydata([(-size, -size, 0.0), (size, -size, 0.0), (size, size, 0.0), (-size, size, 0.0),
                          (-size, -size, 2 * size), (size, -size, 2 * size), (size, size, 2 * size),
                          (-size, size, 2 * size)], [],
                         [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.location = (index * 0.9 - 2.7, 0.0, 0.0)
        obj.select_set(True)
        context.view_layer.objects.active = obj
    return [obj for obj in collection.objects]


def run(context=None, **values):
    """Rename the objects in scope and return the plan's report."""
    import bpy
    context = context or bpy.context
    p = _validate(values)
    targets = [obj for obj in context.scene.objects if p["scope"] == "all" or obj.select_get()]
    names = [obj.name for obj in targets]
    existing = [obj.name for obj in bpy.data.objects if obj.name not in set(names)]
    report = plan_renames(names, existing, **p)["report"]
    lookup = {old: new for old, new in report["renames"]}
    for index, obj in enumerate(targets):
        obj.name = f"__baltor_rename_{index}"
    for obj, old in zip(targets, names):
        obj.name = lookup[old]
        if obj.name != lookup[old]:
            raise RuntimeError(f"Blender renamed {lookup[old]} to {obj.name}")
        if p["rename_data"] and obj.data is not None and obj.data.users == 1:
            obj.data.name = obj.name
    return report


def _properties(bpy):
    annotations = {}
    for spec in PARAMETERS:
        common = {"name": spec["name"].replace("_", " ").title(), "description": spec["description"]}
        if spec["type"] == PARAMETER_TYPE_BOOL:
            annotations[spec["name"]] = bpy.props.BoolProperty(default=spec["default"], **common)
        elif spec["type"] == PARAMETER_TYPE_STRING:
            annotations[spec["name"]] = bpy.props.StringProperty(default=spec["default"], **common)
        elif spec["type"] == PARAMETER_TYPE_CHOICE:
            annotations[spec["name"]] = bpy.props.EnumProperty(
                items=[(choice, choice.title(), "") for choice in spec["choices"]], default=spec["default"], **common)
        else:
            annotations[spec["name"]] = bpy.props.IntProperty(default=spec["default"], min=spec["minimum"],
                                                              max=spec["maximum"], **common)
    return annotations


_CLASSES = []


def _menu_entry(self, context):
    self.layout.operator(OPERATOR, text="Batch Rename by Rule", icon="SORTALPHA")


def register():
    """Register the operator and its Object menu entry."""
    import bpy

    def execute(self, context):
        try:
            report = run(context, **{spec["name"]: getattr(self, spec["name"]) for spec in PARAMETERS})
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Renamed {report['renamed']} objects, {report['numbered']} numbered")
        return {"FINISHED"}

    operator = type("BALTOR_OT_util_batch_rename", (bpy.types.Operator,), {
        "bl_idname": OPERATOR, "bl_label": "Batch Rename by Rule", "bl_description": bl_info["description"],
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


def main(argv=None):
    """Script mode: rename in the opened file, print the plan as JSON, then save when --output is given."""
    import json
    import bpy
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    values, output = parse_arguments(argv)
    print(json.dumps(run(bpy.context, **values)))
    if output:
        if output.endswith(".blend"):
            bpy.ops.wm.save_as_mainfile(filepath=output)
        elif output.endswith((".glb", ".gltf")):
            bpy.ops.export_scene.gltf(filepath=output, export_format="GLB" if output.endswith(".glb")
                                      else "GLTF_SEPARATE")
        else:
            raise ValueError("--output ends in .blend, .glb or .gltf")


if __name__ == "__main__":
    main()
