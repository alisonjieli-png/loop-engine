"""Fixtures for gltf_structural_validator: two known-good assets and one known-wrong copy per defect."""
from __future__ import annotations

import copy
from pathlib import Path

import kit

# Accessor indices of the door (kit.door) and of the skinned strip (kit.skinned_strip).
PANEL_NORMAL, PANEL_INDICES, PANEL_POSITION, HANDLE_NORMAL, OPEN_TIMES = 5, 7, 4, 9, 12
STRIP_INVERSE_BINDS, BEND_OUTPUT = 13, 15


def variants() -> dict:
    door, strip = kit.door(), kit.skinned_strip()
    out = {"good_door.gltf": door, "good_skinned_strip.gltf": strip}

    def edit(base, change):
        document = copy.deepcopy(base)
        change(document)
        return document

    out["bad_accessor_out_of_bounds.gltf"] = edit(door, lambda d: d["accessors"][PANEL_NORMAL].update(byteOffset=16))
    out["bad_index_out_of_range.gltf"] = kit.patch_scalar(door, PANEL_INDICES, 5, 99)
    out["bad_node_cycle.gltf"] = edit(door, lambda d: d["nodes"][2].update(children=[1]))
    out["bad_inverse_bind_count.gltf"] = edit(strip, lambda d: d["accessors"][STRIP_INVERSE_BINDS].update(count=1))
    out["bad_key_times.gltf"] = kit.patch_scalar(door, OPEN_TIMES, 1, 0.0)
    out["bad_cubic_output_count.gltf"] = edit(strip, lambda d: d["accessors"][BEND_OUTPUT].update(count=3))
    out["bad_position_bounds.gltf"] = edit(door, lambda d: d["accessors"][PANEL_POSITION]["max"].__setitem__(1, 2.5))
    out["bad_buffer_length.gltf"] = edit(door, lambda d: d["buffers"][0].update(byteLength=d["buffers"][0]["byteLength"] + 64))
    out["bad_texture_reference.gltf"] = edit(strip, lambda d: d["materials"][0]["pbrMetallicRoughness"]
                                             ["baseColorTexture"].update(index=3))
    out["bad_attribute_counts.gltf"] = edit(door, lambda d: d["accessors"][HANDLE_NORMAL].update(count=23))
    out["bad_rotation_not_unit.gltf"] = edit(door, lambda d: d["nodes"][1].update(rotation=[0.0, 0.5, 0.0, 0.5]))
    out["bad_skin_attributes_missing.gltf"] = edit(strip, lambda d: d["meshes"][0]["primitives"][0]["attributes"]
                                                   .pop("JOINTS_0"))
    return out


EXPECTED = {"bad_accessor_out_of_bounds.gltf": ["accessor_out_of_bounds"],
            "bad_index_out_of_range.gltf": ["index_out_of_range"],
            "bad_node_cycle.gltf": ["node_cycle"],
            "bad_inverse_bind_count.gltf": ["skin_inverse_bind_count_mismatch"],
            "bad_key_times.gltf": ["animation_input_not_increasing"],
            "bad_cubic_output_count.gltf": ["animation_output_count_mismatch"],
            "bad_position_bounds.gltf": ["accessor_min_max_mismatch"],
            "bad_buffer_length.gltf": ["buffer_length_mismatch"],
            "bad_texture_reference.gltf": ["texture_reference_invalid"],
            "bad_attribute_counts.gltf": ["attribute_count_mismatch"],
            "bad_rotation_not_unit.gltf": ["node_rotation_not_unit"],
            "bad_skin_attributes_missing.gltf": ["skin_attributes_missing"]}


def build(item_dir: Path) -> list:
    rows = []
    for name, document in variants().items():
        kit.write(item_dir / "fixtures" / name, document)
        row = {"argv": [f"fixtures/{name}"], "expect": "pass" if name.startswith("good_") else "fail"}
        if name in EXPECTED:
            row["codes"] = EXPECTED[name]
        rows.append(row)
    return rows
