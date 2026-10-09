"""Bouncing animation with exact parabolic arcs, energy loss per bounce and optional squash at contacts.

The core, keyframes(**parameters), computes the bounce from free fall: each apex height is the previous one times
restitution squared, each flight lasts 2 * sqrt(2 h / g), and every arc between an apex and a contact is one
cubic Bezier segment whose handles sit a third of the way along, which reproduces the parabola exactly in time.
It returns keyframe channels with explicit handles and needs no Blender; evaluate(channel, frame) evaluates a
channel the way Blender evaluates an F-curve segment.

In Blender, create(context, **parameters) keys the active object (location Z, location X and scale), and
register() adds the operator baltor.anim_bounce to the Object menu. fixture(context) adds the demo ball the
native check animates. As a script:

    blender --background scene.blend --python anim_bounce.py -- --drop_height 3 --restitution 0.7 --output b.blend
"""
import math
import sys

bl_info = {
    "name": "Baltor Bounce Animation",
    "author": "Baltor",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Object > Bounce Animation",
    "description": "Key a physically timed bounce with exact parabolic arcs, restitution and squash",
    "category": "Animation",
}

OPERATOR = "baltor.anim_bounce"
FIXTURE_NAME = "Bounce Ball"
# The kinds of event in a bounce_timeline() row: the top of an arc and a ground contact.
EVENT_APEX = "apex"
EVENT_CONTACT = "contact"
# The parameter types the code below tests for; every other PARAMETERS row has the type "float".
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_INT = "int"
PARAMETERS = (
    {"name": "drop_height", "type": "float", "default": 2.0, "minimum": 0.01, "maximum": 1000.0, "unit": "m",
     "description": "Height of the object's lowest point above the ground at the first apex."},
    {"name": "ground_z", "type": "float", "default": 0.0, "minimum": -10000.0, "maximum": 10000.0, "unit": "m",
     "description": "Height of the ground plane."},
    {"name": "radius", "type": "float", "default": 0.25, "minimum": 0.001, "maximum": 1000.0, "unit": "m",
     "description": "Distance from the object origin down to its lowest point; measured when measure_radius."},
    {"name": "measure_radius", "type": "bool", "default": True, "minimum": None, "maximum": None, "unit": "flag",
     "description": "Measure the radius from the active object's bounding box instead of using radius."},
    {"name": "restitution", "type": "float", "default": 0.65, "minimum": 0.05, "maximum": 0.95, "unit": "ratio",
     "description": "Rebound speed divided by impact speed."},
    {"name": "gravity", "type": "float", "default": 9.81, "minimum": 0.1, "maximum": 100.0, "unit": "m/s^2",
     "description": "Gravitational acceleration."},
    {"name": "fps", "type": "float", "default": 24.0, "minimum": 1.0, "maximum": 240.0, "unit": "frame/s",
     "description": "Frames per second; the operator fills it from the scene."},
    {"name": "start_frame", "type": "int", "default": 1, "minimum": -100000, "maximum": 100000, "unit": "frame",
     "description": "Frame of the first apex."},
    {"name": "bounces", "type": "int", "default": 6, "minimum": 1, "maximum": 60, "unit": "count",
     "description": "Most rebounds to key after the first contact."},
    {"name": "min_height", "type": "float", "default": 0.02, "minimum": 0.0001, "maximum": 10.0, "unit": "m",
     "description": "Stop when a rebound apex would be lower than this."},
    {"name": "travel_speed", "type": "float", "default": 0.8, "minimum": 0.0, "maximum": 100.0, "unit": "m/s",
     "description": "Constant horizontal speed along +X."},
    {"name": "squash", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 0.6, "unit": "ratio",
     "description": "Vertical squash at the first contact, scaled down with impact speed for later contacts."},
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
        if spec["type"] == PARAMETER_TYPE_BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be true or false")
        else:
            value = _number(name, value, spec)
        result[name] = value
    return result


def parameters(**values):
    """The validated parameters with defaults filled in; raises ValueError on an unknown name or a bad value."""
    return _validate(values)


# ------------------------------------------------------------------------------------------------ pure core
def bounce_timeline(**values):
    """[(kind, time in seconds, height of the lowest point)] for the apexes and contacts, in time order."""
    p = _validate(values)
    g, height = p["gravity"], p["drop_height"]
    events = [(EVENT_APEX, 0.0, height)]
    time = math.sqrt(2.0 * height / g)
    events.append((EVENT_CONTACT, time, 0.0))
    for _bounce in range(p["bounces"]):
        height *= p["restitution"] ** 2
        if height < p["min_height"]:
            break
        half = math.sqrt(2.0 * height / g)
        events.append((EVENT_APEX, time + half, height))
        time += 2.0 * half
        events.append((EVENT_CONTACT, time, 0.0))
    return events


def keyframes(**values):
    """Keyframe channels with explicit Bezier handles (frames and metres) and a report of the bounce."""
    p = _validate(values)
    g, fps, start = p["gravity"], p["fps"], p["start_frame"]
    events = bounce_timeline(**p)
    base = p["ground_z"] + p["radius"]
    first_impact = math.sqrt(2.0 * g * p["drop_height"])
    keys, handles, scale_keys = [], [], []
    for index, (kind, time, height) in enumerate(events):
        frame = start + time * fps
        before = events[index - 1] if index else None
        after = events[index + 1] if index + 1 < len(events) else None
        if kind == EVENT_APEX:
            half = math.sqrt(2.0 * height / g) * fps
            value = base + height
            handles.append([frame - half / 3.0, value, frame + half / 3.0, value])
        else:
            speed = math.sqrt(2.0 * g * before[2])
            squash = p["squash"] * speed / first_impact
            value = base - p["radius"] * squash
            fall = math.sqrt(2.0 * before[2] / g) * fps
            rise = math.sqrt(2.0 * after[2] / g) * fps if after else fall
            rebound = after[2] if after else 0.0
            handles.append([frame - fall / 3.0, value + 2.0 * before[2] / 3.0, frame + rise / 3.0,
                            value + 2.0 * rebound / 3.0])
            gap = 1.5
            if squash > 0.0 and fall > 3.0 * gap and (after is None or rise > 3.0 * gap):
                scale_keys.append((frame, squash, gap))
        keys.append([frame, value])
    end = keys[-1][0]
    channels = [{"target": "active", "data_path": "location", "index": 2, "keys": keys, "handles": handles,
                 "interpolation": "BEZIER"},
                {"target": "active", "data_path": "location", "index": 0, "relative": True,
                 "keys": [[float(start), 0.0], [end, p["travel_speed"] * (end - start) / fps]],
                 "interpolation": "LINEAR"}]
    if scale_keys:
        rows = {0: [[float(start), 1.0]], 1: [[float(start), 1.0]], 2: [[float(start), 1.0]]}
        for frame, squash, gap in scale_keys:
            wide = 1.0 / math.sqrt(1.0 - squash)
            for axis, value in ((0, wide), (1, wide), (2, 1.0 - squash)):
                rows[axis] += [[frame - gap, 1.0], [frame, value], [frame + gap, 1.0]]
        for axis in (0, 1, 2):
            channels.append({"target": "active", "data_path": "scale", "index": axis, "keys": rows[axis],
                             "interpolation": "BEZIER"})
    report = {"contacts": sum(1 for event in events if event[0] == EVENT_CONTACT),
              "duration_s": round(events[-1][1], 9), "last_frame": math.ceil(end),
              "apex_heights_m": [round(event[2], 9) for event in events if event[0] == EVENT_APEX]}
    return {"channels": channels, "report": report}


def evaluate(channel, frame):
    """The channel's value at a frame: Bezier segments with explicit handles, or linear, held at the ends."""
    keys = channel["keys"]
    if frame <= keys[0][0]:
        return keys[0][1]
    if frame >= keys[-1][0]:
        return keys[-1][1]
    index = max(position for position in range(len(keys) - 1) if keys[position][0] <= frame)
    (t0, v0), (t3, v3) = keys[index], keys[index + 1]
    if channel.get("interpolation") == "LINEAR" or "handles" not in channel:
        return v0 + (v3 - v0) * (frame - t0) / (t3 - t0)
    t1, v1 = channel["handles"][index][2], channel["handles"][index][3]
    t2, v2 = channel["handles"][index + 1][0], channel["handles"][index + 1][1]
    low, high = 0.0, 1.0
    for _ in range(60):
        u = (low + high) / 2.0
        t = (1 - u) ** 3 * t0 + 3 * (1 - u) ** 2 * u * t1 + 3 * (1 - u) * u * u * t2 + u ** 3 * t3
        low, high = (u, high) if t < frame else (low, u)
    u = (low + high) / 2.0
    return (1 - u) ** 3 * v0 + 3 * (1 - u) ** 2 * u * v1 + 3 * (1 - u) * u * u * v2 + u ** 3 * v3


def expectations(**values):
    """What Blender must hold after create() on the demo ball: channels, key counts and sampled heights."""
    result = keyframes(**values)
    height = result["channels"][0]
    keyframes_found = {f"{channel['data_path']}[{channel['index']}]": len(channel["keys"])
                       for channel in result["channels"]}
    first, last = height["keys"][0][0], height["keys"][-1][0]
    frames = sorted({int(round(first + (last - first) * share)) for share in (0.0, 0.13, 0.31, 0.5, 0.77)})
    samples = [{"object": FIXTURE_NAME, "frame": frame, "path": "location", "index": 2,
                "value": evaluate(height, frame), "tolerance": 1e-3} for frame in frames]
    return {"objects": {FIXTURE_NAME: {"type": "MESH", "keyframes": keyframes_found}}, "samples": samples}


# ------------------------------------------------------------------------------------------------ script mode
def parse_arguments(argv):
    """(parameters, output path) from script arguments such as ["--bounces", "4", "--output", "a.blend"]."""
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
                values[name] = int(text) if kind == PARAMETER_TYPE_INT else float(text)
        else:
            raise ValueError(f"unknown argument {key}")
    return _validate(values), output


# ------------------------------------------------------------------------------------------------ Blender layer
def _fcurve(obj, data_path, index):
    data = obj.animation_data
    action = data.action
    if hasattr(action, "fcurves"):
        curves = action.fcurves
    else:
        from bpy_extras import anim_utils
        curves = anim_utils.action_get_channelbag_for_slot(action, data.action_slot).fcurves
    for curve in curves:
        if curve.data_path == data_path and curve.array_index == index:
            return curve
    raise KeyError(f"no F-curve {data_path}[{index}]")


def fixture(context=None):
    """Add the demo ball (radius 0.25 m) at the origin and make it active."""
    import bpy
    context = context or bpy.context
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.25, location=(0.0, 0.0, 0.0))
    ball = context.active_object
    ball.name = ball.data.name = FIXTURE_NAME
    return ball


def create(context=None, **values):
    """Key the bounce on the active object and return it."""
    import bpy
    context = context or bpy.context
    obj = context.active_object
    if obj is None:
        raise ValueError("select the object to animate")
    p = _validate(values)
    if p["measure_radius"]:
        lowest = min(corner[2] for corner in obj.bound_box) * obj.scale[2]
        p["radius"] = max(1e-3, -lowest)
    result = keyframes(**p)
    origin_x = obj.location[0]
    for channel in result["channels"]:
        path, index = channel["data_path"], channel["index"]
        offset = origin_x if channel.get("relative") else 0.0
        for frame, value in channel["keys"]:
            getattr(obj, path)[index] = value + offset
            obj.keyframe_insert(data_path=path, index=index, frame=frame)
        curve = _fcurve(obj, path, index)
        points = sorted(curve.keyframe_points, key=lambda point: point.co[0])
        for number, point in enumerate(points):
            point.interpolation = channel["interpolation"]
            if "handles" in channel:
                handle = channel["handles"][number]
                point.handle_left_type = point.handle_right_type = "FREE"
                point.handle_left = (handle[0], handle[1])
                point.handle_right = (handle[2], handle[3])
        curve.update()
    context.scene.frame_end = max(context.scene.frame_end, result["report"]["last_frame"])
    return obj


def _properties(bpy):
    annotations = {}
    for spec in PARAMETERS:
        common = {"name": spec["name"].replace("_", " ").title(), "description": spec["description"]}
        if spec["type"] == PARAMETER_TYPE_BOOL:
            annotations[spec["name"]] = bpy.props.BoolProperty(default=spec["default"], **common)
        elif spec["type"] == PARAMETER_TYPE_INT:
            annotations[spec["name"]] = bpy.props.IntProperty(default=spec["default"], min=spec["minimum"],
                                                              max=spec["maximum"], **common)
        else:
            annotations[spec["name"]] = bpy.props.FloatProperty(default=spec["default"], min=spec["minimum"],
                                                                max=spec["maximum"], **common)
    return annotations


_CLASSES = []


def _menu_entry(self, context):
    self.layout.operator(OPERATOR, text="Bounce Animation", icon="ANIM")


def register():
    """Register the operator and its Object menu entry."""
    import bpy

    def execute(self, context):
        try:
            create(context, **{spec["name"]: getattr(self, spec["name"]) for spec in PARAMETERS})
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, _event):
        self.fps = context.scene.render.fps / context.scene.render.fps_base
        self.start_frame = context.scene.frame_current
        return self.execute(context)

    operator = type("BALTOR_OT_anim_bounce", (bpy.types.Operator,), {
        "bl_idname": OPERATOR, "bl_label": "Bounce Animation", "bl_description": bl_info["description"],
        "bl_options": {"REGISTER", "UNDO"}, "__annotations__": _properties(bpy), "execute": execute,
        "invoke": invoke})
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
    """Script mode: key the active object of the opened file, then save when --output is given."""
    import bpy
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    values, output = parse_arguments(argv)
    create(bpy.context, **values)
    if output:
        _save(output)


if __name__ == "__main__":
    main()
