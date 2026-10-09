"""Fixtures for axes_units_converter: the door in glTF axes and metres, and three wrong conventions."""
from __future__ import annotations

from pathlib import Path

import kit


def mirrored() -> dict:
    """X negated in every position, normal and translation, triangle order unchanged: inside-out faces."""
    document = kit.door(clips=())
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            for name in ("POSITION", "NORMAL"):
                kit.rewrite_vec3(document, primitive["attributes"][name], lambda v: (-v[0], v[1], v[2]))
    for node in document["nodes"]:
        if "translation" in node:
            node["translation"][0] = -node["translation"][0]
    return document


def build(item_dir: Path) -> list:
    fixtures = item_dir / "fixtures"
    variants = {"door.gltf": kit.door(), "door_z_up.gltf": kit.door(axes=kit.z_up_axes),
                "door_centimetres.gltf": kit.door(unit=100.0), "door_mirrored.gltf": mirrored()}
    for name, document in variants.items():
        kit.write(fixtures / name, document)
    expect = ["--expect-dimensions", "1.1", "2.1", "0.15"]
    return [{"argv": ["check", "fixtures/door.gltf", *expect], "expect": "pass"},
            {"argv": ["check", "fixtures/door_z_up.gltf"], "expect": "pass"},
            {"argv": ["check", "fixtures/door_z_up.gltf", *expect], "expect": "fail", "codes": ["up_axis_mismatch"]},
            {"argv": ["check", "fixtures/door_centimetres.gltf", *expect], "expect": "fail",
             "codes": ["unit_scale_mismatch"]},
            {"argv": ["check", "fixtures/door_mirrored.gltf", *expect], "expect": "fail", "codes": ["winding_inverted"]},
            {"argv": ["check", "fixtures/door.gltf", "--expect-dimensions", "1.1", "2.1", "-1"], "expect": "fail",
             "codes": ["expectation_invalid"]}]
