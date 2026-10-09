"""Fixtures for gltf_semantic_recovery: the door, its asset specification, and one variant per lost meaning."""
from __future__ import annotations

import copy
from pathlib import Path

import kit

OPEN_TIMES = 12

SPEC = {
    "record_type": "asset_specification/v1",
    "asset": "interior_door",
    "description": "An interior door in its frame, hinged on its left edge, with a lever handle.",
    "units": "metre", "up_axis": "+Y", "forward_axis": "+Z", "tolerance_m": 0.005,
    "parts": [
        {"name": "DoorFrame", "parent": None, "dimensions_m": [1.1, 2.1, 0.15], "pivot_m": [0.0, 0.0, 0.0],
         "material": "PaintedFrame"},
        {"name": "DoorPanel", "parent": "DoorFrame", "dimensions_m": [0.9, 2.0, 0.04], "pivot_m": [-0.45, 0.0, 0.0],
         "material": "Wood"},
        {"name": "DoorHandle", "parent": "DoorPanel", "dimensions_m": [0.12, 0.03, 0.04],
         "pivot_m": [0.33, 1.0, 0.02], "material": "BrushedSteel"}],
    "materials": [{"name": "PaintedFrame"}, {"name": "Wood"}, {"name": "BrushedSteel"}],
    "joints": [{"name": "door_hinge", "type": "revolute", "part": "DoorPanel", "axis": [0.0, 1.0, 0.0],
                "limits_deg": [0.0, 90.0]},
               {"name": "handle_lever", "type": "revolute", "part": "DoorHandle", "axis": [0.0, 0.0, 1.0],
                "limits_deg": [-30.0, 0.0]}],
    "clips": [{"name": "Open", "duration_s": 1.2, "targets": [{"part": "DoorPanel", "path": "rotation"}]},
              {"name": "Close", "duration_s": 1.2, "targets": [{"part": "DoorPanel", "path": "rotation"}]},
              {"name": "HandlePress", "duration_s": 0.4, "targets": [{"part": "DoorHandle", "path": "rotation"}]}],
    "behaviors": [{"name": "open_door", "joint": "door_hinge", "clip": "Open", "trigger": "interact"}]}


def build(item_dir: Path) -> list:
    fixtures = item_dir / "fixtures"
    door = kit.door()
    kit.write_json(fixtures / "door.spec.json", SPEC)
    broken_spec = copy.deepcopy(SPEC)
    del broken_spec["parts"][1]["name"]
    kit.write_json(fixtures / "bad_spec_part_without_name.spec.json", broken_spec)
    variants = {"door.gltf": door, "bad_centimetres.gltf": kit.door(unit=100.0),
                "bad_z_up.gltf": kit.door(axes=kit.z_up_axes), "bad_no_clips.gltf": kit.door(clips=())}
    flattened = copy.deepcopy(door)
    flattened["nodes"][1]["children"] = []
    flattened["nodes"][0]["children"] = [1, 2]
    flattened["nodes"][2]["translation"] = [kit.f32(0.33), 1.0, kit.f32(0.02)]
    variants["bad_flattened.gltf"] = flattened
    unnamed = copy.deepcopy(door)
    del unnamed["nodes"][1]["name"]
    variants["bad_unnamed_panel.gltf"] = unnamed
    renamed = copy.deepcopy(door)
    renamed["materials"][1]["name"] = "Material.001"
    variants["bad_renamed_material.gltf"] = renamed
    short = kit.patch_scalar(kit.patch_scalar(door, OPEN_TIMES, 1, 0.3), OPEN_TIMES, 2, 0.6)
    short["accessors"][OPEN_TIMES]["max"] = [kit.f32(0.6)]
    variants["bad_short_clip.gltf"] = short
    for name, document in variants.items():
        kit.write(fixtures / name, document)
    spec = "fixtures/door.spec.json"
    return [
        {"argv": ["fixtures/door.gltf", "--spec", spec], "expect": "pass"},
        {"argv": ["fixtures/door.gltf"], "expect": "pass"},
        {"argv": ["fixtures/bad_centimetres.gltf", "--spec", spec], "expect": "fail",
         "codes": ["part_dimensions_mismatch", "part_pivot_mismatch"]},
        {"argv": ["fixtures/bad_z_up.gltf", "--spec", spec], "expect": "fail", "codes": ["part_dimensions_mismatch"]},
        {"argv": ["fixtures/bad_flattened.gltf", "--spec", spec], "expect": "fail", "codes": ["part_parent_mismatch"]},
        {"argv": ["fixtures/bad_unnamed_panel.gltf", "--spec", spec], "expect": "fail",
         "codes": ["part_missing", "part_parent_mismatch"]},
        {"argv": ["fixtures/bad_no_clips.gltf", "--spec", spec], "expect": "fail", "codes": ["clip_missing"]},
        {"argv": ["fixtures/bad_renamed_material.gltf", "--spec", spec], "expect": "fail",
         "codes": ["material_missing", "part_material_mismatch"]},
        {"argv": ["fixtures/bad_short_clip.gltf", "--spec", spec], "expect": "fail",
         "codes": ["clip_duration_mismatch"]},
        {"argv": ["fixtures/door.gltf", "--spec", "fixtures/bad_spec_part_without_name.spec.json"], "expect": "fail",
         "codes": ["specification_invalid"]}]
