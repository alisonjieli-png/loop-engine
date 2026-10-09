"""Fixtures for godot_scene_linter: a small Godot 4 project with good scenes and one broken scene per rule."""
from __future__ import annotations

from pathlib import Path

PROJECT = '''config_version=5

[application]
config/name="Scene linter fixtures"

[rendering]
renderer/rendering_method="gl_compatibility"
'''

SCRIPT = '''extends Node3D
## Opens the door when its timer fires.

signal opened


func open() -> void:
	opened.emit()
'''

WOOD = '''[gd_resource type="StandardMaterial3D" format=3]

[resource]
resource_name = "Wood"
albedo_color = Color(0.55, 0.35, 0.2, 1)
roughness = 0.8
'''

BRASS_WITH_MISSING_TEXTURE = '''[gd_resource type="StandardMaterial3D" format=3]

[ext_resource type="Texture2D" path="res://textures/brass_albedo.png" id="1_albedo"]

[resource]
resource_name = "Brass"
albedo_texture = ExtResource("1_albedo")
metallic = 1.0
'''

DOOR = '''[gd_scene format=3]

[ext_resource type="Script" path="res://scripts/door_controller.gd" id="1_script"]
[ext_resource type="Material" path="res://materials/wood.tres" id="2_wood"]

[sub_resource type="BoxMesh" id="BoxMesh_panel"]
size = Vector3(0.9, 2, 0.04)

[sub_resource type="BoxMesh" id="BoxMesh_handle"]
size = Vector3(0.12, 0.03, 0.04)

[node name="Door" type="Node3D"]
script = ExtResource("1_script")

[node name="Panel" type="MeshInstance3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0)
mesh = SubResource("BoxMesh_panel")
surface_material_override/0 = ExtResource("2_wood")

[node name="Handle" type="MeshInstance3D" parent="Panel"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0.33, 0, 0.04)
mesh = SubResource("BoxMesh_handle")

[node name="Timer" type="Timer" parent="."]
wait_time = 2.0

[connection signal="timeout" from="Timer" to="." method="open"]
'''

GODOT3_DOOR = '''[gd_scene load_steps=3 format=2]

[ext_resource path="res://scripts/door_controller.gd" type="Script" id=1]

[sub_resource type="CubeMesh" id=1]
size = Vector3( 0.9, 2, 0.04 )

[node name="Door" type="Spatial"]
script = ExtResource( 1 )

[node name="Panel" type="MeshInstance" parent="."]
mesh = SubResource( 1 )

[node name="Timer" type="Timer" parent="."]

[connection signal="timeout" from="Timer" to="." method="open"]
'''

ROOM = '''[gd_scene format=3]

[ext_resource type="PackedScene" path="res://scenes/door.tscn" id="1_door"]

[sub_resource type="Environment" id="Environment_room"]
background_mode = 1
background_color = Color(0.1, 0.1, 0.12, 1)

[node name="Room" type="Node3D"]

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("Environment_room")

[node name="Sun" type="DirectionalLight3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 0.707107, 0.707107, 0, -0.707107, 0.707107, 0, 4, 0)

[node name="Camera" type="Camera3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.6, 4)

[node name="DoorA" parent="." instance=ExtResource("1_door")]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -1.5, 0, 0)

[node name="DoorB" parent="." instance=ExtResource("1_door")]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 1.5, 0, 0)

[node name="Panel" parent="DoorB"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.1, 0)

[connection signal="opened" from="DoorA" to="Camera" method="make_current"]

[editable path="DoorB"]
'''


HANDLE_MESH = '[sub_resource type="BoxMesh" id="BoxMesh_handle"]\nsize = Vector3(0.12, 0.03, 0.04)\n'


def broken(name: str, old: str, new: str, base: str = DOOR) -> tuple:
    assert old in base, old
    return name, base.replace(old, new, 1)


SCENES = [
    broken("bad_missing_material.tscn", "res://materials/wood.tres", "res://materials/walnut.tres"),
    broken("bad_unknown_ext_id.tscn", 'surface_material_override/0 = ExtResource("2_wood")',
           'surface_material_override/0 = ExtResource("9_walnut")'),
    broken("bad_unknown_sub_id.tscn", 'mesh = SubResource("BoxMesh_handle")', 'mesh = SubResource("BoxMesh_knob")'),
    ("bad_forward_sub_resource.tscn", DOOR.replace(HANDLE_MESH, "") + "\n" + HANDLE_MESH),
    broken("bad_parent_path.tscn", '[node name="Handle" type="MeshInstance3D" parent="Panel"]',
           '[node name="Handle" type="MeshInstance3D" parent="Panel/Hinge"]'),
    broken("bad_duplicate_sibling.tscn", '[node name="Timer" type="Timer" parent="."]',
           '[node name="Handle" type="MeshInstance3D" parent="Panel"]\n\n[node name="Timer" type="Timer" parent="."]'),
    broken("bad_connection.tscn", 'from="Timer"', 'from="CloseTimer"'),
    broken("bad_syntax.tscn", "size = Vector3(0.9, 2, 0.04)", "size = Vector3(0.9, 2, 0.04"),
    broken("bad_two_roots.tscn", '[node name="Timer" type="Timer" parent="."]', '[node name="Timer" type="Timer"]'),
    broken("bad_untyped_node.tscn", '[node name="Timer" type="Timer" parent="."]', '[node name="Timer" parent="."]'),
    broken("bad_future_format.tscn", "[gd_scene format=3]", "[gd_scene format=9]"),
]
CODES = {"bad_missing_material.tscn": ["ext_resource_missing_file"],
         "bad_unknown_ext_id.tscn": ["ext_resource_reference_unknown"],
         "bad_unknown_sub_id.tscn": ["sub_resource_reference_unknown"],
         "bad_forward_sub_resource.tscn": ["sub_resource_forward_reference"],
         "bad_parent_path.tscn": ["node_parent_missing"], "bad_duplicate_sibling.tscn": ["node_name_repeated"],
         "bad_connection.tscn": ["connection_node_missing"], "bad_syntax.tscn": ["syntax_invalid"],
         "bad_two_roots.tscn": ["root_node_count"], "bad_untyped_node.tscn": ["node_type_missing"],
         "bad_future_format.tscn": ["format_unsupported"]}


def build(item_dir: Path) -> list:
    project = item_dir / "fixtures" / "project"
    files = {"project.godot": PROJECT, "scripts/door_controller.gd": SCRIPT, "materials/wood.tres": WOOD,
             "materials/bad_brass_missing_texture.tres": BRASS_WITH_MISSING_TEXTURE, "scenes/door.tscn": DOOR,
             "scenes/godot3_door.tscn": GODOT3_DOOR,
             "scenes/room.tscn": ROOM}
    files.update({f"scenes/{name}": text for name, text in SCENES})
    for relative, text in files.items():
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    rows = [{"argv": ["fixtures/project/scenes/door.tscn"], "expect": "pass"},
            {"argv": ["fixtures/project/scenes/room.tscn"], "expect": "pass"},
            {"argv": ["fixtures/project/materials/wood.tres"], "expect": "pass"},
            {"argv": ["fixtures/project/scenes/godot3_door.tscn"], "expect": "pass"},
            {"argv": ["fixtures/project/materials/bad_brass_missing_texture.tres"], "expect": "fail",
             "codes": ["ext_resource_missing_file"]}]
    rows += [{"argv": [f"fixtures/project/scenes/{name}"], "expect": "fail", "codes": CODES[name]}
             for name, _text in SCENES]
    return rows
