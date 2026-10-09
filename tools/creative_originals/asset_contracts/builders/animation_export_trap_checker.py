"""Fixtures for animation_export_trap_checker: the door's declared clips and one export per trap."""
from __future__ import annotations

import copy
from pathlib import Path

import kit

DECLARATION = {
    "record_type": "animation_declaration/v1", "source": "door.blend", "fps": 24.0,
    "clips": [{"name": "Open", "duration_s": 1.2, "targets": [{"node": "DoorPanel", "path": "rotation"}]},
              {"name": "Close", "duration_s": 1.2, "targets": [{"node": "DoorPanel", "path": "rotation"}]},
              {"name": "HandlePress", "duration_s": 0.4, "targets": [{"node": "DoorHandle", "path": "rotation"}]}]}


def build(item_dir: Path) -> list:
    fixtures = item_dir / "fixtures"
    library = kit.door_clips()
    identity = kit.quat_axis_angle((0.0, 1.0, 0.0), 0)
    quarter = kit.quat_axis_angle((0.0, 1.0, 0.0), 90)
    half = kit.quat_axis_angle((0.0, 1.0, 0.0), 45)
    unresolved = kit.door()
    del unresolved["animations"][0]["channels"][0]["target"]["node"]
    exports = {
        "door.gltf": kit.door(),
        "bad_no_animations.gltf": kit.door(clips=()),
        "bad_active_action_only.gltf": kit.door(clips=("Close",)),
        "bad_unresolved_target.gltf": unresolved,
        "bad_static_clip.gltf": kit.door(clips=(("Open", [(1, "rotation", [0.0, 0.6, 1.2], [identity] * 3, "LINEAR")]),
                                                "Close", "HandlePress")),
        "bad_merged_clips.gltf": kit.door(clips=(("Animation", library["Open"] + library["HandlePress"]),)),
        "bad_scene_range_bake.gltf": kit.door(clips=(("Open", [(1, "rotation", [0.0, 0.6, 1.2, 10.375],
                                                               [identity, half, quarter, quarter], "LINEAR")]),
                                                     "Close", "HandlePress")),
    }
    for name, document in exports.items():
        kit.write(fixtures / name, document)
    kit.write_json(fixtures / "door.clips.json", DECLARATION)
    broken = copy.deepcopy(DECLARATION)
    broken["clips"][0]["targets"][0]["path"] = "rotation_euler"
    kit.write_json(fixtures / "bad_declaration_path.clips.json", broken)
    declared = "fixtures/door.clips.json"
    return [
        {"argv": ["fixtures/door.gltf", "--declared", declared], "expect": "pass"},
        {"argv": ["fixtures/bad_no_animations.gltf", "--declared", declared], "expect": "fail",
         "codes": ["animations_missing", "clip_missing"]},
        {"argv": ["fixtures/bad_active_action_only.gltf", "--declared", declared], "expect": "fail",
         "codes": ["clip_missing"]},
        {"argv": ["fixtures/bad_unresolved_target.gltf", "--declared", declared], "expect": "fail",
         "codes": ["channel_target_unresolved", "clip_target_missing"]},
        {"argv": ["fixtures/bad_static_clip.gltf", "--declared", declared], "expect": "fail", "codes": ["clip_static"]},
        {"argv": ["fixtures/bad_merged_clips.gltf", "--declared", declared], "expect": "fail",
         "codes": ["clips_merged", "clip_missing"]},
        {"argv": ["fixtures/bad_scene_range_bake.gltf", "--declared", declared], "expect": "fail",
         "codes": ["clip_duration_mismatch"]},
        {"argv": ["fixtures/door.gltf", "--declared", "fixtures/bad_declaration_path.clips.json"], "expect": "fail",
         "codes": ["declaration_invalid"]}]
