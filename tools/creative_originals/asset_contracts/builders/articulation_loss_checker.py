"""Fixtures for articulation_loss_checker: a reference door that carries its joints, and one export per loss."""
from __future__ import annotations

import copy
from pathlib import Path

import gltfio
import kit

RECORDS = {1: {"name": "door_hinge", "type": "hinge", "axis": [0.0, 1.0, 0.0], "pivot": [0.0, 0.0, 0.0],
               "limits": [0.0, 95.0]},
           2: {"name": "handle_lever", "type": "hinge", "axis": [0.0, 0.0, 1.0], "pivot": [0.0, 0.0, 0.0],
               "limits": [-35.0, 0.0]}}
MANIFEST = {"record_type": "articulation_manifest/v1", "asset": "door_reference.gltf",
            "joints": [{"name": "door_hinge", "type": "hinge", "node": "DoorPanel", "axis": [0.0, 1.0, 0.0],
                        "pivot": [0.0, 0.0, 0.0], "limits": [0.0, 95.0], "rest": 0.0},
                       {"name": "handle_lever", "type": "hinge", "node": "DoorHandle", "axis": [0.0, 0.0, 1.0],
                        "pivot": [0.0, 0.0, 0.0], "limits": [-35.0, 0.0], "rest": 0.0}]}


def reference() -> dict:
    document = kit.door(clips=())
    for index, record in RECORDS.items():
        document["nodes"][index]["extras"] = {"joint": record}
    return document


def reorder(document: dict, order: list) -> dict:
    """The same scene with its nodes stored in another order (order lists old indices in their new places)."""
    document = copy.deepcopy(document)
    new = {old: position for position, old in enumerate(order)}
    nodes = [document["nodes"][old] for old in order]
    for node in nodes:
        if "children" in node:
            node["children"] = [new[child] for child in node["children"]]
    document["nodes"] = nodes
    for scene in document["scenes"]:
        scene["nodes"] = [new[root] for root in scene["nodes"]]
    return document


def joined() -> dict:
    """Panel and handle joined into the frame's mesh: one node, three primitives, the world geometry unchanged."""
    document = {"asset": {"version": "2.0", "generator": "asset_contracts fixture builder"}, "scene": 0,
                "scenes": [{"name": "DoorScene", "nodes": [0]}],
                "materials": copy.deepcopy(kit.door()["materials"])}
    builder = gltfio.BufferBuilder(document)
    frame = kit.merge(kit.box_geometry((-0.55, 0.0, -0.075), (-0.45, 2.1, 0.075)),
                      kit.box_geometry((0.45, 0.0, -0.075), (0.55, 2.1, 0.075)),
                      kit.box_geometry((-0.45, 2.0, -0.075), (0.45, 2.1, 0.075)))
    panel = kit.box_geometry((-0.45, 0.0, -0.02), (0.45, 2.0, 0.02))
    handle = kit.box_geometry((0.27, 0.985, 0.02), (0.39, 1.015, 0.06))
    document["meshes"] = [{"name": "FrameMesh", "primitives": [kit.add_primitive(builder, frame, 0),
                                                               kit.add_primitive(builder, panel, 1),
                                                               kit.add_primitive(builder, handle, 2)]}]
    document["nodes"] = [{"name": "DoorFrame", "mesh": 0}]
    return builder.finish()


def build(item_dir: Path) -> list:
    fixtures = item_dir / "fixtures"
    good = reference()
    without = copy.deepcopy(good)
    for node in without["nodes"]:
        node.pop("extras", None)
    mismatch = copy.deepcopy(good)
    mismatch["nodes"][1]["extras"]["joint"]["limits"] = [0.0, 180.0]
    flattened = copy.deepcopy(good)
    flattened["nodes"][1]["children"] = []
    flattened["nodes"][0]["children"] = [1, 2]
    flattened["nodes"][2]["translation"] = [kit.f32(0.33), 1.0, kit.f32(0.02)]
    exports = {
        "door_reference.gltf": good,
        "door_reordered.gltf": reorder(good, [2, 0, 1]),
        "export_without_extras.gltf": without,
        "export_extras_mismatch.gltf": mismatch,
        "export_origin_to_geometry.gltf": kit.rebase_node(good, 1, gltfio.compose((0.45, 1.0, 0.0))),
        "export_frame_rotated.gltf": kit.rebase_node(good, 1, gltfio.compose(
            rotation=kit.quat_axis_angle((1.0, 0.0, 0.0), 90))),
        "export_joined.gltf": joined(),
        "export_flattened.gltf": flattened}
    for name, document in exports.items():
        kit.write(fixtures / name, document)
    kit.write_json(fixtures / "door_reference.articulation.json", MANIFEST)
    kit.write_json(fixtures / "bad_manifest.articulation.json", {"record_type": "articulation_manifest/v1",
                                                                 "joints": [{"name": "door_hinge", "node": "DoorPanel"}]})
    flags = ["--manifest", "fixtures/door_reference.articulation.json", "--reference", "fixtures/door_reference.gltf"]
    strict = flags + ["--extras", "required"]
    return [
        {"argv": ["fixtures/door_reference.gltf", *strict], "expect": "pass"},
        {"argv": ["fixtures/door_reordered.gltf", *strict], "expect": "pass"},
        {"argv": ["fixtures/export_without_extras.gltf", *flags], "expect": "pass"},
        {"argv": ["fixtures/export_without_extras.gltf", *strict], "expect": "fail", "codes": ["joint_extras_missing"]},
        {"argv": ["fixtures/export_extras_mismatch.gltf", *strict], "expect": "fail", "codes": ["joint_extras_mismatch"]},
        {"argv": ["fixtures/export_origin_to_geometry.gltf", *strict], "expect": "fail", "codes": ["pivot_moved"]},
        {"argv": ["fixtures/export_frame_rotated.gltf", *strict], "expect": "fail", "codes": ["joint_axis_changed"]},
        {"argv": ["fixtures/export_joined.gltf", *strict], "expect": "fail", "codes": ["joint_node_missing"]},
        {"argv": ["fixtures/export_flattened.gltf", *strict], "expect": "fail", "codes": ["joint_parent_changed"]},
        {"argv": ["fixtures/door_reference.gltf", "--manifest", "fixtures/bad_manifest.articulation.json"],
         "expect": "fail", "codes": ["manifest_invalid"]}]
