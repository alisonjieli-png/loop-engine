"""Fixtures for articulation_manifest_godot_builder: the door and a toolbox with their manifests, and known-wrong
manifests (plus one asset whose node names repeat)."""
from __future__ import annotations

import copy
from pathlib import Path

import gltfio
import kit

DOOR_MANIFEST = {
    "record_type": "articulation_manifest/v1", "asset": "door.gltf",
    "joints": [{"name": "door_hinge", "type": "hinge", "node": "DoorPanel", "axis": [0.0, 1.0, 0.0],
                "pivot": [0.0, 0.0, 0.0], "limits": [0.0, 95.0], "rest": 0.0},
               {"name": "handle_lever", "type": "hinge", "node": "DoorHandle", "axis": [0.0, 0.0, 1.0],
                "pivot": [0.0, 0.0, 0.0], "limits": [-35.0, 0.0], "rest": 0.0}]}

TOOLBOX_MANIFEST = {
    "record_type": "articulation_manifest/v1", "asset": "toolbox.gltf",
    "joints": [{"name": "lid_hinge", "type": "hinge", "node": "Lid", "axis": [1.0, 0.0, 0.0],
                "pivot": [0.0, -0.01, -0.15], "limits": [-110.0, 0.0], "rest": 0.0},
               {"name": "tray_slide", "type": "slider", "node": "Tray", "axis": [0.0, 0.0, 1.0],
                "pivot": [0.0, 0.0, 0.0], "limits": [0.0, 0.2], "rest": 0.0}]}


def toolbox() -> dict:
    """Box (root, open top) with a Lid whose origin is at the lid's centre and a Tray that slides out of the front."""
    document = {"asset": {"version": "2.0", "generator": "asset_contracts fixture builder"}, "scene": 0,
                "scenes": [{"name": "Toolbox", "nodes": [0]}],
                "materials": [kit.material("PaintedSteel", (0.75, 0.1, 0.1, 1.0), 0.6, 0.5),
                              kit.material("Plastic", (0.15, 0.15, 0.15, 1.0), 0.0, 0.6)]}
    builder = gltfio.BufferBuilder(document)
    shell = kit.merge(kit.box_geometry((-0.25, 0.0, -0.15), (0.25, 0.02, 0.15)),
                      kit.box_geometry((-0.25, 0.02, -0.15), (-0.23, 0.25, 0.15)),
                      kit.box_geometry((0.23, 0.02, -0.15), (0.25, 0.25, 0.15)),
                      kit.box_geometry((-0.23, 0.02, -0.15), (0.23, 0.25, -0.13)))
    lid = kit.box_geometry((-0.25, -0.01, -0.15), (0.25, 0.01, 0.15))
    tray = kit.box_geometry((-0.2, -0.04, -0.12), (0.2, 0.04, 0.13))
    document["meshes"] = [{"name": "BoxMesh", "primitives": [kit.add_primitive(builder, shell, 0)]},
                          {"name": "LidMesh", "primitives": [kit.add_primitive(builder, lid, 0)]},
                          {"name": "TrayMesh", "primitives": [kit.add_primitive(builder, tray, 1)]}]
    document["nodes"] = [{"name": "Box", "mesh": 0, "children": [1, 2]},
                         {"name": "Lid", "mesh": 1, "translation": [0.0, kit.f32(0.26), 0.0]},
                         {"name": "Tray", "mesh": 2, "translation": [0.0, kit.f32(0.07), kit.f32(0.02)]}]
    return builder.finish()


def manifest_variant(change) -> dict:
    value = copy.deepcopy(DOOR_MANIFEST)
    change(value)
    return value


BAD = {
    "bad_node_missing.articulation.json": (lambda m: m["joints"][0].update(node="Door"), ["node_missing"]),
    "bad_axis_zero.articulation.json": (lambda m: m["joints"][0].update(axis=[0.0, 0.0, 0.0]), ["axis_invalid"]),
    "bad_limits_reversed.articulation.json": (lambda m: m["joints"][0].update(limits=[95.0, 0.0]),
                                              ["limits_invalid"]),
    "bad_joint_type.articulation.json": (lambda m: m["joints"][1].update(type="ball"), ["joint_type_invalid"]),
    "bad_node_jointed_twice.articulation.json": (lambda m: m["joints"][1].update(node="DoorPanel"),
                                                 ["node_jointed_twice"]),
    "bad_record_type.articulation.json": (lambda m: m.update(record_type="joints/v0"), ["manifest_invalid"]),
}


def build(item_dir: Path) -> list:
    fixtures = item_dir / "fixtures"
    door = kit.door()
    kit.write(fixtures / "door.gltf", door)
    kit.write(fixtures / "toolbox.gltf", toolbox())
    duplicated = copy.deepcopy(door)
    duplicated["nodes"][2]["name"] = "DoorPanel"
    kit.write(fixtures / "bad_duplicate_names.gltf", duplicated)
    kit.write_json(fixtures / "door.articulation.json", DOOR_MANIFEST)
    kit.write_json(fixtures / "toolbox.articulation.json", TOOLBOX_MANIFEST)
    rows = [{"argv": ["fixtures/door.gltf", "--manifest", "fixtures/door.articulation.json"], "expect": "pass"},
            {"argv": ["fixtures/toolbox.gltf", "--manifest", "fixtures/toolbox.articulation.json"], "expect": "pass"},
            {"argv": ["fixtures/bad_duplicate_names.gltf", "--manifest", "fixtures/door.articulation.json"],
             "expect": "fail", "codes": ["node_ambiguous"]}]
    for name, (change, codes) in BAD.items():
        kit.write_json(fixtures / name, manifest_variant(change))
        rows.append({"argv": ["fixtures/door.gltf", "--manifest", f"fixtures/{name}"], "expect": "fail",
                     "codes": codes})
    return rows
