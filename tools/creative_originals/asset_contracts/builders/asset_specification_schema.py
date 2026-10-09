"""Fixtures for asset_specification_schema: two valid specifications and one known-wrong copy per rule."""
from __future__ import annotations

import copy
from pathlib import Path

import kit

CABINET = {
    "record_type": "asset_specification/v1", "asset": "cabinet_with_drawer",
    "description": "A low cabinet with a drawer that slides out of the front and a door hinged on its left edge.",
    "units": "metre", "up_axis": "+Y", "forward_axis": "+Z", "tolerance_m": 0.005,
    "parts": [
        {"name": "Cabinet", "parent": None, "dimensions_m": [0.8, 0.9, 0.5], "center_m": [0.0, 0.45, 0.0],
         "pivot_m": [0.0, 0.0, 0.0], "material": "Oak", "role": "static"},
        {"name": "Drawer", "parent": "Cabinet", "dimensions_m": [0.7, 0.18, 0.46], "center_m": [0.0, 0.76, 0.02],
         "pivot_m": [0.0, 0.76, 0.25], "material": "Oak", "role": "moving"},
        {"name": "DrawerPull", "parent": "Drawer", "dimensions_m": [0.16, 0.025, 0.03],
         "center_m": [0.0, 0.76, 0.265], "pivot_m": [0.0, 0.76, 0.265], "material": "Brass", "role": "handle"},
        {"name": "CabinetDoor", "parent": "Cabinet", "dimensions_m": [0.38, 0.55, 0.02],
         "center_m": [-0.2, 0.33, 0.26], "pivot_m": [-0.39, 0.33, 0.26], "material": "Oak", "role": "moving"}],
    "materials": [{"name": "Oak", "base_color": [0.6, 0.45, 0.3, 1.0], "roughness": 0.7},
                  {"name": "Brass", "base_color": [0.8, 0.65, 0.3, 1.0], "metallic": 1.0, "roughness": 0.3}],
    "joints": [{"name": "drawer_slide", "type": "prismatic", "part": "Drawer", "axis": [0.0, 0.0, 1.0],
                "limits_m": [0.0, 0.35], "rest": 0.0},
               {"name": "door_hinge", "type": "revolute", "part": "CabinetDoor", "axis": [0.0, 1.0, 0.0],
                "limits_deg": [-110.0, 0.0], "rest": 0.0}],
    "clips": [{"name": "OpenDrawer", "duration_s": 0.8, "targets": [{"part": "Drawer", "path": "translation"}]},
              {"name": "OpenDoor", "duration_s": 1.0, "targets": [{"part": "CabinetDoor", "path": "rotation"}]}],
    "behaviors": [{"name": "pull_drawer", "joint": "drawer_slide", "clip": "OpenDrawer", "trigger": "interact"},
                  {"name": "open_door", "joint": "door_hinge", "clip": "OpenDoor", "trigger": "interact"}]}

LAMP = {
    "record_type": "asset_specification/v1", "asset": "desk_lamp",
    "description": "A desk lamp: a weighted base, two arms and a shade, each tilting about the X axis.",
    "units": "metre", "up_axis": "+Y", "forward_axis": "+Z",
    "parts": [
        {"name": "Base", "dimensions_m": [0.2, 0.03, 0.2], "center_m": [0.0, 0.015, 0.0], "pivot_m": [0.0, 0.0, 0.0],
         "material": "Metal"},
        {"name": "LowerArm", "parent": "Base", "dimensions_m": [0.03, 0.3, 0.03], "center_m": [0.0, 0.18, 0.0],
         "pivot_m": [0.0, 0.03, 0.0], "material": "Metal"},
        {"name": "UpperArm", "parent": "LowerArm", "dimensions_m": [0.03, 0.3, 0.03], "center_m": [0.0, 0.48, 0.0],
         "pivot_m": [0.0, 0.33, 0.0], "material": "Metal"},
        {"name": "Shade", "parent": "UpperArm", "dimensions_m": [0.12, 0.1, 0.12], "center_m": [0.0, 0.66, 0.0],
         "pivot_m": [0.0, 0.63, 0.0], "material": ["ShadeFabric"]}],
    "materials": [{"name": "Metal", "metallic": 1.0, "roughness": 0.4}, {"name": "ShadeFabric", "roughness": 0.9}],
    "joints": [{"name": "lower_tilt", "type": "revolute", "part": "LowerArm", "axis": [1.0, 0.0, 0.0],
                "limits_deg": [-45.0, 45.0]},
               {"name": "elbow", "type": "revolute", "part": "UpperArm", "axis": [1.0, 0.0, 0.0],
                "limits_deg": [-100.0, 0.0]},
               {"name": "shade_tilt", "type": "revolute", "part": "Shade", "axis": [1.0, 0.0, 0.0],
                "limits_deg": [-60.0, 30.0]}],
    "behaviors": [{"name": "aim", "joint": "lower_tilt", "trigger": "script"}]}


def broken(change) -> dict:
    spec = copy.deepcopy(CABINET)
    change(spec)
    return spec


VARIANTS = {
    "bad_parent_cycle.spec.json": (lambda s: s["parts"][0].update(parent="DrawerPull"), ["parent_cycle"]),
    "bad_unknown_parent.spec.json": (lambda s: s["parts"][2].update(parent="Drawers"), ["parent_unknown"]),
    "bad_joint_unknown_part.spec.json": (lambda s: s["joints"][0].update(part="Drawers"), ["joint_part_unknown"]),
    "bad_limits_reversed.spec.json": (lambda s: s["joints"][1].update(limits_deg=[0.0, -110.0]),
                                      ["joint_limits_invalid"]),
    "bad_axis_zero.spec.json": (lambda s: s["joints"][0].update(axis=[0.0, 0.0, 0.0]), ["joint_axis_zero"]),
    "bad_clip_target.spec.json": (lambda s: s["clips"][1]["targets"][0].update(part="Door"), ["clip_target_unknown"]),
    "bad_behavior_reference.spec.json": (lambda s: s["behaviors"][0].update(clip="OpenLid"),
                                         ["behavior_reference_unknown"]),
    "bad_negative_dimension.spec.json": (lambda s: s["parts"][1]["dimensions_m"].__setitem__(0, -0.7),
                                         ["schema_violation"]),
    "bad_unknown_field.spec.json": (lambda s: s["parts"][1].update(colour="red"), ["schema_violation"]),
    "bad_material_unknown.spec.json": (lambda s: s["parts"][3].update(material="Walnut"), ["material_unknown"]),
    "bad_dotted_name.spec.json": (lambda s: s["parts"][2].update(name="DrawerPull.001"), ["schema_violation"]),
}


def build(item_dir: Path) -> list:
    fixtures = item_dir / "fixtures"
    kit.write_json(fixtures / "cabinet_with_drawer.spec.json", CABINET)
    kit.write_json(fixtures / "desk_lamp.spec.json", LAMP)
    rows = [{"argv": ["fixtures/cabinet_with_drawer.spec.json"], "expect": "pass"},
            {"argv": ["fixtures/desk_lamp.spec.json"], "expect": "pass"}]
    for name, (change, codes) in VARIANTS.items():
        kit.write_json(fixtures / name, broken(change))
        rows.append({"argv": [f"fixtures/{name}"], "expect": "fail", "codes": codes})
    return rows
