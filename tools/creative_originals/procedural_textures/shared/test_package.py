"""Tests for one procedural texture package, run from the package root with the standard library only.

The item module named in component.json is generated at small sizes and checked against the card: the declared
maps, channels and colour spaces, the same bytes for the same seed, seamless wrap-around, declared value ranges,
unit normals that face out of the surface, refused parameters, the command line, the Godot material template and
the Blender builder (on a stand-in for bpy that lists Blender 5.2's socket names). texkit and pngio are checked
with known answers.

Known-wrong controls: a left-to-right gradient and a non-periodic wave fail the seam check, a corrupted file fails
its digest, out-of-range and mistyped parameters are refused, a template pointing at another file is refused and a
folder missing a map is refused by the Blender builder.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import json
import math
import re
import tempfile
import types
import unittest
from pathlib import Path

import pngio
import texkit

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
IDENTITY = CARD["job"]["identity"]
CONTRACT = CARD["contract"]
MODULE = importlib.import_module(IDENTITY)
BUILDER = importlib.import_module("blender_material")
SMALL = 40
TEXTURE_PROPERTIES = {"albedo": "albedo_texture", "normal": "normal_texture", "roughness": "roughness_texture",
                      "metallic": "metallic_texture", "height": "heightmap_texture", "ao": "ao_texture",
                      "emissive": "emission_texture"}
_CACHE = {}


def maps_for(preset: str = "default", size: int = SMALL, seed: int = 0) -> dict:
    key = (preset, size, seed)
    if key not in _CACHE:
        _CACHE[key] = MODULE.generate(size, size, seed, preset)
    return _CACHE[key]


def declared(name: str) -> "dict | None":
    return next((row for row in MODULE.MAPS if row["name"] == name), None)


def template_problems(text: str, identity: str, names: list) -> list:
    """What is wrong with a Godot material template: an empty list when it is a StandardMaterial3D that points every
    declared map at res://baltor/textures/<identity>/<identity>_<map>.png and nothing else."""
    problems = []
    if not text.startswith('[gd_resource type="StandardMaterial3D"'):
        problems.append("not a StandardMaterial3D resource")
    paths = {key: path for path, key in re.findall(r'\[ext_resource type="Texture2D" path="([^"]+)" id="([^"]+)"\]',
                                                   text)}
    properties = dict(re.findall(r'^(\w+) = ExtResource\("([^"]+)"\)$', text, re.MULTILINE))
    expected = {TEXTURE_PROPERTIES[name]: f"res://baltor/textures/{identity}/{identity}_{name}.png" for name in names}
    for prop, path in expected.items():
        if paths.get(properties.get(prop)) != path:
            problems.append(f"{prop} does not load {path}")
    for prop in properties:
        if prop not in expected:
            problems.append(f"{prop} is not a declared map")
    if len(paths) != len(expected):
        problems.append("the template loads a texture that is not a declared map")
    return problems


# ----------------------------------------------------------------------------------------- a stand-in for bpy

#: Input and output sockets (name, identifier) of the nodes the builder may use, as Blender 5.2 lists them.
NODE_SOCKETS = {
    "ShaderNodeOutputMaterial": ([("Surface", "Surface"), ("Volume", "Volume"), ("Displacement", "Displacement"),
                                  ("Thickness", "Thickness")], []),
    "ShaderNodeBsdfPrincipled": ([(name, name) for name in (
        "Base Color", "Metallic", "Roughness", "IOR", "Alpha", "Thin Wall", "Normal", "Weight", "Diffuse Roughness",
        "Subsurface Weight", "Subsurface Radius", "Subsurface Scale", "Subsurface IOR", "Subsurface Anisotropy",
        "Specular IOR Level", "Specular Tint", "Anisotropic", "Anisotropic Rotation", "Tangent",
        "Transmission Weight", "Coat Weight", "Coat Roughness", "Coat IOR", "Coat Tint", "Coat Normal",
        "Sheen Weight", "Sheen Roughness", "Sheen Tint", "Emission Color", "Emission Strength",
        "Thin Film Thickness", "Thin Film IOR")], [("BSDF", "BSDF")]),
    "ShaderNodeTexImage": ([("Vector", "Vector")], [("Color", "Color"), ("Alpha", "Alpha")]),
    "ShaderNodeNormalMap": ([("Strength", "Strength"), ("Color", "Color")], [("Normal", "Normal")]),
    "ShaderNodeDisplacement": ([("Height", "Height"), ("Midlevel", "Midlevel"), ("Scale", "Scale"),
                                ("Normal", "Normal")], [("Displacement", "Displacement")]),
    "ShaderNodeMix": ([("Factor", "Factor_Float"), ("Factor", "Factor_Vector"), ("A", "A_Float"), ("B", "B_Float"),
                       ("A", "A_Vector"), ("B", "B_Vector"), ("A", "A_Color"), ("B", "B_Color"),
                       ("A", "A_Rotation"), ("B", "B_Rotation")],
                      [("Result", "Result_Float"), ("Result", "Result_Vector"), ("Result", "Result_Color"),
                       ("Result", "Result_Rotation")]),
    "ShaderNodeMath": ([("Value", "Value"), ("Value", "Value_001"), ("Value", "Value_002")], [("Value", "Value")]),
}


class _Socket:
    def __init__(self, node, name: str, identifier: str) -> None:
        self.node, self.name, self.identifier, self.default_value = node, name, identifier, None


class _Sockets(list):
    def __getitem__(self, key):
        if isinstance(key, str):
            for socket in self:
                if socket.name == key:
                    return socket
            raise KeyError(key)
        return list.__getitem__(self, key)


class _Node:
    def __init__(self, kind: str) -> None:
        if kind not in NODE_SOCKETS:
            raise RuntimeError(f"node type {kind} is not in the stand-in")
        inputs, outputs = NODE_SOCKETS[kind]
        self.bl_idname, self.label, self.image, self.location = kind, "", None, (0, 0)
        self.inputs = _Sockets(_Socket(self, name, key) for name, key in inputs)
        self.outputs = _Sockets(_Socket(self, name, key) for name, key in outputs)


class _Nodes(list):
    def new(self, kind: str) -> _Node:
        node = _Node(kind)
        self.append(node)
        return node

    def remove(self, node) -> None:
        list.remove(self, node)


class _Links(list):
    def new(self, output, target):
        if not any(output is socket for socket in output.node.outputs) or \
                not any(target is socket for socket in target.node.inputs):
            raise RuntimeError("a link joins an output to an input")
        self.append((output, target))
        return self[-1]


class _Material:
    def __init__(self, name: str) -> None:
        self.name, self.use_nodes = name, False
        self.node_tree = types.SimpleNamespace(nodes=_Nodes(), links=_Links())
        self.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        self.node_tree.nodes.new("ShaderNodeOutputMaterial")


class _Image:
    def __init__(self, path: str) -> None:
        if not Path(path).is_file():
            raise RuntimeError(f"cannot read {path}")
        self.filepath = path
        self.colorspace_settings = types.SimpleNamespace(name="sRGB")
        self.alpha_mode = "STRAIGHT"


class _Collection(list):
    def __init__(self, factory) -> None:
        super().__init__()
        self.factory = factory

    def new(self, name: str):
        self.append(self.factory(name))
        return self[-1]

    def load(self, path: str, check_existing: bool = False):
        return self.new(path)


def stand_in_bpy():
    return types.SimpleNamespace(data=types.SimpleNamespace(materials=_Collection(_Material),
                                                           images=_Collection(_Image)))


def reached(material, node) -> set:
    """(node type, input name) of the BSDF and output sockets that a node feeds, through any intermediate nodes."""
    found, pending, seen = set(), [node], set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        for output, target in material.node_tree.links:
            if output.node is current:
                kind = target.node.bl_idname
                if kind in ("ShaderNodeBsdfPrincipled", "ShaderNodeOutputMaterial"):
                    found.add((kind, target.name))
                else:
                    pending.append(target.node)
    return found


# ------------------------------------------------------------------------------------------------------ tests

class CardTests(unittest.TestCase):
    def test_files_match_the_card(self):
        for row in CARD["files"]:
            self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"], row["path"])

    def test_a_corrupted_copy_is_refused(self):
        row = next(row for row in CARD["files"] if row["path"] == f"{IDENTITY}.py")
        data = bytearray((ROOT / row["path"]).read_bytes())
        data[len(data) // 2] ^= 0x01
        self.assertNotEqual(hashlib.sha256(bytes(data)).hexdigest(), row["sha256"])

    def test_declarations_match_the_contract(self):
        self.assertEqual(CONTRACT["entry_point"], "generate")
        self.assertIs(CONTRACT["tileable"], True)
        self.assertEqual(CONTRACT["maps"], MODULE.MAPS)
        self.assertEqual(CONTRACT["parameters"], MODULE.PARAMETERS)
        self.assertEqual(CONTRACT["presets"], [{"name": name, **body} for name, body in MODULE.PRESETS.items()])
        names = [row["name"] for row in MODULE.MAPS]
        self.assertEqual(names, [name for name in texkit.MAP_NAMES if name in names], "maps in the documented order")
        self.assertTrue({"albedo", "normal", "roughness", "height"} <= set(names))
        self.assertIn("default", MODULE.PRESETS)
        self.assertGreaterEqual(len(MODULE.PRESETS), 2)
        for row in MODULE.MAPS:
            self.assertEqual(row["colour_space"], "srgb" if row["name"] in ("albedo", "emissive") else "linear")
            self.assertIn(row["channels"], (1, 3, 4))
        for row in MODULE.PARAMETERS:
            self.assertIn(row["type"], ("int", "float"))
            self.assertLessEqual(row["minimum"], row["default"])
            self.assertLessEqual(row["default"], row["maximum"])
            self.assertTrue(row["meaning"].strip())
        self.assertGreater(CONTRACT["cost_seconds_1024"], 0)


class MapTests(unittest.TestCase):
    def test_declared_maps_are_generated_and_encode(self):
        maps = maps_for()
        self.assertEqual(sorted(maps), sorted(row["name"] for row in MODULE.MAPS))
        for row in MODULE.MAPS:
            entry = maps[row["name"]]
            self.assertEqual((entry["channels"], entry["colour_space"]), (row["channels"], row["colour_space"]))
            self.assertEqual(len(entry["pixels"]), SMALL * SMALL * row["channels"])
            image = pngio.decode(pngio.encode(SMALL, SMALL, entry["pixels"], row["channels"]))
            self.assertEqual(image["pixels"], entry["pixels"])

    def test_same_seed_same_bytes_and_another_seed_differs(self):
        first = MODULE.generate(32, 32, 11, "default")
        self.assertEqual(first, MODULE.generate(32, 32, 11, "default"))
        other = MODULE.generate(32, 32, 12, "default")
        self.assertTrue(any(first[name]["pixels"] != other[name]["pixels"] for name in first))

    def test_non_square_sizes_are_supported(self):
        maps = MODULE.generate(24, 16, 3, "default")
        for name, entry in maps.items():
            self.assertEqual(len(entry["pixels"]), 24 * 16 * entry["channels"], name)

    def test_every_preset_tiles_without_a_seam(self):
        for preset in MODULE.PRESETS:
            for name, entry in maps_for(preset).items():
                report = texkit.seam_report(entry["pixels"], SMALL, SMALL, entry["channels"])
                self.assertTrue(report["passed"], f"{preset} {name}: {report}")

    def test_seam_check_refuses_non_periodic_images(self):
        gradient = bytes(int(255 * x / (SMALL - 1)) for _y in range(SMALL) for x in range(SMALL))
        self.assertFalse(texkit.seam_report(gradient, SMALL, SMALL, 1)["passed"])
        wave = bytes(int(127.5 + 127 * math.sin(math.pi * 1.5 * y / SMALL)) for y in range(SMALL) for _x in range(SMALL))
        self.assertFalse(texkit.seam_report(wave, SMALL, SMALL, 1)["rows"]["passed"])
        periodic = bytes(int(127.5 + 127 * math.sin(2 * math.pi * 2 * x / SMALL)) for _y in range(SMALL)
                         for x in range(SMALL))
        self.assertTrue(texkit.seam_report(periodic, SMALL, SMALL, 1)["passed"])

    def test_values_stay_in_declared_ranges(self):
        for preset in MODULE.PRESETS:
            maps = maps_for(preset)
            for row in MODULE.MAPS:
                if "range" not in row:
                    continue
                low, high = (int(bound * 255.0 + 0.5) for bound in row["range"])
                pixels = maps[row["name"]]["pixels"]
                colour = [value for index, value in enumerate(pixels) if row["channels"] != 4 or index % 4 != 3]
                self.assertGreaterEqual(min(colour), low, f"{preset} {row['name']}")
                self.assertLessEqual(max(colour), high, f"{preset} {row['name']}")

    def test_maps_carry_detail(self):
        for preset in MODULE.PRESETS:
            maps = maps_for(preset)
            albedo = maps["albedo"]["pixels"]
            step = maps["albedo"]["channels"]
            luma = [albedo[k] + albedo[k + 1] + albedo[k + 2] for k in range(0, len(albedo), step)]
            mean = sum(luma) / len(luma)
            spread = math.sqrt(sum((value - mean) ** 2 for value in luma) / len(luma))
            self.assertGreater(spread, 1.5, f"{preset} albedo is flat")
            heights = maps["height"]["pixels"]
            self.assertGreater(max(heights) - min(heights), 8, f"{preset} height is flat")

    def test_normals_have_unit_length_and_face_out(self):
        for preset in MODULE.PRESETS:
            pixels = maps_for(preset)["normal"]["pixels"]
            for k in range(0, len(pixels), 3):
                x, y, z = (pixels[k + c] / 127.5 - 1.0 for c in range(3))
                self.assertAlmostEqual(math.sqrt(x * x + y * y + z * z), 1.0, delta=0.025)
                self.assertGreater(z, 0.0)

    def test_presets_are_distinct(self):
        albedos = {name: maps_for(name)["albedo"]["pixels"] for name in MODULE.PRESETS}
        names = sorted(albedos)
        for index, first in enumerate(names):
            for second in names[index + 1:]:
                difference = sum(abs(a - b) for a, b in zip(albedos[first], albedos[second])) / len(albedos[first])
                self.assertGreater(difference, 1.0, f"presets {first} and {second} look the same")

    def test_directx_output_flips_green_only(self):
        opengl = MODULE.generate(24, 24, 5, "default")
        directx = MODULE.generate(24, 24, 5, "default", directx_normal=True)
        for name in opengl:
            if name != "normal":
                self.assertEqual(opengl[name], directx[name])
        a, b = opengl["normal"]["pixels"], directx["normal"]["pixels"]
        self.assertEqual(a[0::3], b[0::3])
        self.assertEqual(a[2::3], b[2::3])
        self.assertTrue(all(abs(p + q - 255) <= 1 for p, q in zip(a[1::3], b[1::3])))


class ParameterTests(unittest.TestCase):
    def test_out_of_range_and_mistyped_values_are_refused(self):
        for row in MODULE.PARAMETERS:
            span = row["maximum"] - row["minimum"]
            step = 1 if row["type"] == "int" else max(span * 0.01, 1e-6)
            bad = [row["maximum"] + step, row["minimum"] - step, str(row["default"]), True, float("nan")]
            if row["type"] == "int":
                bad.append(row["default"] + 0.5)
            for value in bad:
                with self.subTest(parameter=row["name"], value=value), self.assertRaises(ValueError):
                    MODULE.generate(8, 8, 0, "default", **{row["name"]: value})

    def test_unknown_names_sizes_seeds_and_presets_are_refused(self):
        calls = [lambda: MODULE.generate(8, 8, 0, "default", not_a_parameter=1),
                 lambda: MODULE.generate(8, 8, 0, "no_such_preset"), lambda: MODULE.generate(0, 8),
                 lambda: MODULE.generate(8, texkit.MAX_SIDE + 1), lambda: MODULE.generate(8.0, 8),
                 lambda: MODULE.generate(8, 8, -1), lambda: MODULE.generate(8, 8, 1.5)]
        for index, call in enumerate(calls):
            with self.subTest(call=index), self.assertRaises(ValueError):
                call()

    def test_presets_name_declared_parameters_within_bounds(self):
        names = {row["name"] for row in MODULE.PARAMETERS}
        for preset, body in MODULE.PRESETS.items():
            self.assertTrue(body["description"].strip(), preset)
            self.assertLessEqual(set(body["values"]), names, preset)
            texkit.resolve(MODULE.PARAMETERS, MODULE.PRESETS, preset, {})

    def test_bounds_generate_valid_maps(self):
        for row in MODULE.PARAMETERS:
            for value in (row["minimum"], row["maximum"]):
                with self.subTest(parameter=row["name"], value=value):
                    maps = MODULE.generate(16, 16, 2, "default", **{row["name"]: value})
                    for entry in maps.values():
                        self.assertEqual(len(entry["pixels"]), 16 * 16 * entry["channels"])
                    pixels = maps["normal"]["pixels"]
                    self.assertTrue(all(pixels[k] > 127 for k in range(2, len(pixels), 3)))


class CommandLineTests(unittest.TestCase):
    def test_command_line_writes_the_generated_maps(self):
        preset = sorted(MODULE.PRESETS)[-1]
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as printed:
            status = MODULE.main(["--size", "20", "--seed", "4", "--preset", preset, "--out", folder, "--orm"])
            self.assertEqual(status, 0)
            summary = json.loads(printed.getvalue().strip().splitlines()[-1])
            self.assertEqual((summary["identity"], summary["width"], summary["preset"]), (IDENTITY, 20, preset))
            expected = MODULE.generate(20, 20, 4, preset)
            for name, entry in expected.items():
                image = pngio.decode((Path(folder) / f"{IDENTITY}_{name}.png").read_bytes())
                self.assertEqual((image["width"], image["height"], image["channels"]), (20, 20, entry["channels"]))
                self.assertEqual(image["pixels"], entry["pixels"], name)
            orm = pngio.decode((Path(folder) / f"{IDENTITY}_orm.png").read_bytes())["pixels"]
            self.assertEqual(orm[1::3], expected["roughness"]["pixels"])
            occlusion = expected["ao"]["pixels"] if "ao" in expected else bytes([255]) * 400
            self.assertEqual(orm[0::3], occlusion)

    def test_command_line_refuses_a_bad_parameter(self):
        row = MODULE.PARAMETERS[0]
        too_big = row["maximum"] + (1 if row["type"] == "int" else abs(row["maximum"]) + 1.0)
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit) as caught:
            MODULE.main(["--size", "16", "--set", f"{row['name']}={too_big}", "--out", folder])
        self.assertEqual(caught.exception.code, 2)


class EngineFileTests(unittest.TestCase):
    def test_godot_template_points_at_every_generated_map(self):
        text = (ROOT / "material.tres").read_text(encoding="utf-8")
        names = [row["name"] for row in MODULE.MAPS]
        self.assertEqual(template_problems(text, IDENTITY, names), [])

    def test_a_template_pointing_elsewhere_is_refused(self):
        text = (ROOT / "material.tres").read_text(encoding="utf-8")
        names = [row["name"] for row in MODULE.MAPS]
        self.assertTrue(template_problems(text.replace(f"{IDENTITY}_albedo.png", "other_albedo.png"), IDENTITY, names))
        self.assertTrue(template_problems(text.replace("StandardMaterial3D", "ShaderMaterial", 1), IDENTITY, names))

    def test_blender_builder_wires_every_map(self):
        names = [row["name"] for row in MODULE.MAPS]
        with tempfile.TemporaryDirectory() as folder:
            texkit.write_maps(MODULE.generate(16, 16, 1, "default"), 16, 16, folder, IDENTITY)
            self.assertEqual(sorted(BUILDER.map_paths(folder)), sorted(names))
            material = BUILDER.build_material(folder, bpy_module=stand_in_bpy())
            images = {node.label: node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeTexImage"}
            self.assertEqual(sorted(images), sorted(names))
            for name, node in images.items():
                self.assertEqual(node.image.colorspace_settings.name,
                                 "sRGB" if name in ("albedo", "emissive") else "Non-Color", name)
            bsdf = "ShaderNodeBsdfPrincipled"
            targets = {"albedo": (bsdf, "Base Color"), "normal": (bsdf, "Normal"), "roughness": (bsdf, "Roughness"),
                       "metallic": (bsdf, "Metallic"), "height": ("ShaderNodeOutputMaterial", "Displacement"),
                       "emissive": (bsdf, "Emission Color")}
            for name in names:
                if name in targets:
                    self.assertIn(targets[name], reached(material, images[name]), name)
            principled = next(node for node in material.node_tree.nodes if node.bl_idname == bsdf)
            self.assertIn(("ShaderNodeOutputMaterial", "Surface"), reached(material, principled))
            if declared("albedo")["channels"] == 4:
                alpha_links = [target for output, target in material.node_tree.links
                               if output.node is images["albedo"] and output.name == "Alpha"]
                self.assertTrue(alpha_links, "the albedo alpha drives the material alpha")

    def test_blender_builder_refuses_a_folder_missing_a_map(self):
        with tempfile.TemporaryDirectory() as folder:
            texkit.write_maps(MODULE.generate(8, 8, 1, "default"), 8, 8, folder, IDENTITY)
            (Path(folder) / f"{IDENTITY}_normal.png").unlink()
            with self.assertRaises(FileNotFoundError):
                BUILDER.build_material(folder, bpy_module=stand_in_bpy())


class TexkitTests(unittest.TestCase):
    """Known answers for the shared toolkit, so a broken helper fails here whichever item uses it."""

    def test_hashes_and_random_numbers(self):
        self.assertEqual(texkit.hash_u32(1, 2, 3), texkit.hash_u32(1, 2, 3))
        self.assertNotEqual(texkit.hash_u32(1, 2, 3), texkit.hash_u32(1, 2, 4))
        self.assertEqual(texkit.hash_u32(0), 493009611)
        self.assertEqual(texkit.hash_u32(-1, 7), texkit.hash_u32(0xFFFFFFFF, 7))
        values = [texkit.hash_float(k, 9) for k in range(400)]
        self.assertTrue(all(0.0 <= v < 1.0 for v in values))
        self.assertAlmostEqual(sum(values) / len(values), 0.5, delta=0.06)
        first, second = texkit.Rng(5, 1), texkit.Rng(5, 1)
        self.assertEqual([first.random() for _ in range(5)], [second.random() for _ in range(5)])
        rng = texkit.Rng(3)
        draws = [rng.integer(2, 4) for _ in range(300)]
        self.assertEqual(set(draws), {2, 3, 4})
        self.assertTrue(all(1.0 <= rng.uniform(1.0, 2.0) <= 2.0 for _ in range(50)))
        self.assertIn(rng.choice("abc"), "abc")
        gauss = [rng.gauss(10.0, 2.0) for _ in range(2000)]
        self.assertAlmostEqual(sum(gauss) / len(gauss), 10.0, delta=0.25)
        self.assertTrue(rng.chance(1.0))
        self.assertFalse(rng.chance(0.0))
        self.assertNotEqual(texkit.Rng(5, 1).random(), texkit.Rng(5, 2).random())

    def test_validation(self):
        self.assertEqual(texkit.check_size(4, 4096), (4, 4096))
        self.assertEqual(texkit.check_seed(0), 0)
        for bad in ((3, 8), (8, 4097), (True, 8), (8.0, 8)):
            with self.assertRaises(ValueError):
                texkit.check_size(*bad)
        for bad in (-1, texkit.MAX_SEED + 1, 2.0, False):
            with self.assertRaises(ValueError):
                texkit.check_seed(bad)
        rows = [{"name": "a", "type": "int", "default": 2, "minimum": 1, "maximum": 5, "meaning": "count"},
                {"name": "b", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0, "meaning": "amount"}]
        presets = {"default": {"description": "d", "values": {}}, "other": {"description": "o", "values": {"a": 4}}}
        self.assertEqual(texkit.resolve(rows, presets, "other", {"b": 1}), {"a": 4, "b": 1.0})
        for preset, overrides in (("missing", {}), ("default", {"c": 1}), ("default", {"a": 6}),
                                  ("default", {"a": 2.0}), ("default", {"b": "0.5"}), ("default", {"b": math.inf})):
            with self.assertRaises(ValueError):
                texkit.resolve(rows, presets, preset, overrides)

    def test_scalar_helpers(self):
        self.assertEqual((texkit.clamp(-1.0), texkit.clamp(2.0), texkit.clamp(0.3)), (0.0, 1.0, 0.3))
        self.assertEqual(texkit.lerp(2.0, 4.0, 0.25), 2.5)
        self.assertEqual((texkit.smoothstep(0, 1, -1), texkit.smoothstep(0, 1, 0.5), texkit.smoothstep(0, 1, 2)),
                         (0.0, 0.5, 1.0))
        self.assertEqual((texkit.smoothstep(1, 1, 0.5), texkit.smoothstep(1, 1, 1.5)), (0.0, 1.0))
        self.assertEqual((texkit.fade(0.0), texkit.fade(0.5), texkit.fade(1.0)), (0.0, 0.5, 1.0))
        self.assertAlmostEqual(texkit.wrap_delta(0.75), -0.25)
        self.assertAlmostEqual(texkit.wrap_delta(-0.6), 0.4)
        self.assertAlmostEqual(texkit.torus_distance(0.95, 0.5, 0.05, 0.5), 0.1)
        self.assertAlmostEqual(texkit.torus_distance(0.1, 0.1, 0.9, 0.9), math.hypot(0.2, 0.2))
        self.assertAlmostEqual(texkit.segment_distance(0.5, 0.6, 0.4, 0.5, 0.6, 0.5), 0.1)
        self.assertAlmostEqual(texkit.segment_distance(0.02, 0.5, 0.9, 0.5, 0.95, 0.5), 0.07)

    def test_shape_distances_and_points(self):
        self.assertEqual(texkit.box_distance(0.0, 0.0, 1.0, 0.5), -0.5)
        self.assertEqual(texkit.box_distance(2.0, 0.0, 1.0, 0.5), 1.0)
        self.assertAlmostEqual(texkit.box_distance(2.0, 1.5, 1.0, 0.5), math.sqrt(2.0))
        self.assertAlmostEqual(texkit.box_distance(1.0, 0.5, 1.0, 0.5, 0.25), 0.25 * math.sqrt(2.0) - 0.25)
        square = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]
        self.assertEqual(texkit.polygon_distance(0.0, 0.0, square), -1.0)
        self.assertEqual(texkit.polygon_distance(3.0, 0.0, square), 2.0)
        self.assertEqual(texkit.polygon_distance(0.5, 0.0, square[::-1]), -0.5)
        notch = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (2.0, 1.0), (0.0, 4.0)]
        self.assertGreater(texkit.polygon_distance(2.0, 2.0, notch), 0.0, "the notch of a concave polygon is outside")
        self.assertLess(texkit.polygon_distance(0.5, 0.5, notch), 0.0)
        self.assertEqual(texkit.smooth_min(1.0, 2.0, 0.0), 1.0)
        self.assertEqual(texkit.smooth_min(1.0, 1.0, 1.0), 0.75)
        self.assertEqual(texkit.smooth_min(1.0, 3.0, 1.0), 1.0)
        points = texkit.poisson_points(0.08, 4)
        self.assertEqual(points, texkit.poisson_points(0.08, 4))
        self.assertNotEqual(points, texkit.poisson_points(0.08, 5))
        closest = min(texkit.torus_distance(*a, *b) for index, a in enumerate(points) for b in points[index + 1:])
        self.assertGreaterEqual(closest, 0.08)
        gaps = max(min(texkit.torus_distance((i + 0.5) / 16, (j + 0.5) / 16, u, v) for u, v in points)
                   for i in range(16) for j in range(16))
        self.assertLess(gaps, 0.16, "the tile is filled up to the spacing, also across the edges")
        with self.assertRaises(ValueError):
            texkit.poisson_points(0.001)

    def test_noise_ranges_periodicity_and_seeds(self):
        for field, low, high in ((texkit.value_noise(32, 32, 4, 4, 1), 0.0, 1.0),
                                 (texkit.gradient_noise(32, 32, 4, 2, 1), -1.0001, 1.0001),
                                 (texkit.fbm(32, 32, 2, 4, 1), -1.0, 1.0),
                                 (texkit.fbm(32, 32, 2, 3, 1, kind="value"), 0.0, 1.0),
                                 (texkit.ridged(32, 32, 2, 3, 1), 0.0, 1.0),
                                 (texkit.turbulence(32, 32, 2, 3, 1), 0.0, 1.0),
                                 (texkit.white_noise(32, 32, 1), 0.0, 1.0)):
            self.assertEqual(len(field), 32 * 32)
            self.assertTrue(low <= min(field) and max(field) <= high)
            self.assertGreater(max(field) - min(field), 0.05)
            self.assertTrue(texkit.seam_report(texkit.to_bytes(texkit.normalize(field)), 32, 32, 1)["passed"])
        self.assertNotEqual(texkit.gradient_noise(16, 16, 4, 4, 1), texkit.gradient_noise(16, 16, 4, 4, 2))
        plain = texkit.gradient_noise(32, 32, 4, 4, 1)
        shifted = texkit.value_noise(32, 32, 4, 4, 1, (1.0, 2.0))
        rolled = texkit.value_noise(32, 32, 4, 4, 1)
        self.assertTrue(all(abs(shifted[y * 32 + x] - rolled[((y + 16) % 32) * 32 + (x + 8) % 32]) < 1e-9
                            for y in range(32) for x in range(32)), "a whole-cell lattice shift is a roll")
        self.assertNotEqual(texkit.gradient_noise(32, 32, 4, 4, 1, (0.5, 0.25)), plain)
        smooth = texkit.to_bytes(texkit.normalize(texkit.fbm(48, 48, 3, 3, 4)))
        self.assertTrue(texkit.seam_report(smooth, 48, 48, 1)["passed"])
        with self.assertRaises(ValueError):
            texkit.value_noise(8, 8, 0)
        with self.assertRaises(ValueError):
            texkit.fbm(8, 8, 2, 2, kind="sparse")

    def test_voronoi_known_answer(self):
        result = texkit.voronoi(4, 4, 4, 4, seed=3, jitter=0.0)
        self.assertTrue(all(abs(value) < 1e-12 for value in result["f1"]))
        self.assertTrue(all(abs(value - 1.0) < 1e-12 for value in result["f2"]))
        self.assertTrue(all(abs(value - 0.5) < 1e-12 for value in result["edge"]))
        self.assertEqual(result["cell"], list(range(16)))
        xs, ys = texkit.cell_points(3, 2, 7, 0.8)
        self.assertEqual(len(xs), 6)
        self.assertTrue(all(i % 3 <= x < i % 3 + 1 for i, x in enumerate(xs)))
        self.assertTrue(all(i // 3 <= y < i // 3 + 1 for i, y in enumerate(ys)))
        jittered = texkit.voronoi(24, 24, 3, 3, seed=5, jitter=0.9)
        self.assertTrue(all(a <= b + 1e-12 for a, b in zip(jittered["f1"], jittered["f2"])))
        self.assertTrue(all(e >= -1e-9 for e in jittered["edge"]))
        self.assertIsNone(texkit.voronoi(8, 8, 2, seed=1, edges=False)["edge"])
        self.assertEqual((texkit.hex_rows(7), texkit.hex_rows(12), texkit.hex_rows(3)), (8, 14, 4))
        hx, hy = texkit.hex_points(4, 4)
        self.assertEqual((hx[0], hy[0], hx[4], hy[4]), (0.25, 0.5, 0.75, 1.5))
        with self.assertRaises(ValueError):
            texkit.hex_points(4, 3)
        hexes = texkit.voronoi(48, 48, 4, 4, points=texkit.hex_points(4, 4))
        self.assertEqual(len(set(hexes["cell"])), 16)
        self.assertTrue(texkit.seam_report(texkit.to_bytes(hexes["edge"]), 48, 48, 1)["passed"])
        self.assertTrue(texkit.seam_report(texkit.to_bytes(jittered["f1"]), 24, 24, 1)["passed"])

    def test_painting_wraps_around(self):
        field = [0.0] * 100
        texkit.stamp(field, 10, 10, 0.0, 0.0, 0.15, 0.15, lambda s, t: 1.0 if s * s + t * t <= 1.0 else None)
        for index in (0, 9, 90, 99):
            self.assertEqual(field[index], 1.0)
        self.assertEqual(field[55], 0.0)
        texkit.stamp(field, 10, 10, 0.55, 0.55, 0.06, 0.06, lambda s, t: 0.25, mode="add")
        self.assertEqual(field[55], 0.25)
        line = [0.0] * 100
        texkit.draw_segment(line, 10, 10, 0.85, 0.55, 1.15, 0.55, 0.05)
        self.assertGreater(line[5 * 10 + 9], 0.5)
        self.assertGreater(line[5 * 10 + 0], 0.5)
        self.assertEqual(line[5 * 10 + 4], 0.0)
        path = [0.0] * 100
        texkit.draw_path(path, 10, 10, [(0.05, 0.05), (0.55, 0.05), (0.55, 0.55)], 0.04, mode="set")
        self.assertGreater(path[0 * 10 + 3], 0.5)
        self.assertGreater(path[3 * 10 + 5], 0.5)
        with self.assertRaises(ValueError):
            texkit.stamp(field, 10, 10, 0.5, 0.5, 0.6, 0.1, lambda s, t: 1.0)
        footprint = texkit.ellipse_pixels(10, 10, 0.95, 0.05, 0.12, 0.12)
        self.assertIn(0, [index for index, s, t in footprint], "the footprint wraps to the opposite corner")
        centre = [(s, t) for index, s, t in texkit.ellipse_pixels(10, 10, 0.55, 0.55, 0.2, 0.1) if index == 55][0]
        self.assertEqual(centre, (0.0, 0.0))
        along = texkit.segment_pixels(10, 10, 0.05, 0.55, 0.95, 0.55, 0.06)
        on_axis = sorted((index, round(d, 6), round(t, 3)) for index, d, t in along if index in (50, 59))
        self.assertEqual(on_axis, [(50, 0.0, 0.0), (59, 0.0, 1.0)])
        with self.assertRaises(ValueError):
            texkit.segment_pixels(10, 10, 0.1, 0.1, 0.2, 0.2, 0.0)

    def test_field_operations(self):
        impulse = [0.0] * 64
        impulse[0] = 64.0
        blurred = texkit.blur(impulse, 8, 8, 0.125, passes=1)
        self.assertAlmostEqual(sum(blurred), 64.0)
        self.assertAlmostEqual(blurred[7], blurred[1])
        self.assertAlmostEqual(blurred[7 * 8], blurred[8])
        self.assertTrue(all(abs(value - 0.25) < 1e-12 for value in texkit.blur([0.25] * 36, 6, 6, 0.2)))
        self.assertEqual(texkit.normalize([2.0, 4.0, 6.0]), [0.0, 0.5, 1.0])
        self.assertEqual(texkit.normalize([3.0, 3.0]), [0.5, 0.5])
        ramp = [float(x) for _y in range(4) for x in range(4)]
        self.assertAlmostEqual(texkit.sample(ramp, 4, 4, 0.25, 0.5), 0.5)
        self.assertAlmostEqual(texkit.sample(ramp, 4, 4, 1.0 / 8.0, 0.5), 0.0)
        self.assertEqual(texkit.warp(ramp, 4, 4, [0.0] * 16, [0.0] * 16, 0.3), ramp)
        shifted = texkit.warp(ramp, 4, 4, [1.0] * 16, [0.0] * 16, 0.25)
        self.assertEqual(shifted[:4], [1.0, 2.0, 3.0, 0.0])
        self.assertEqual(texkit.resample([0.7] * 16, 4, 4, 9, 7), [0.7] * 63)
        self.assertEqual(texkit.resample(ramp, 4, 4, 4, 4), ramp)
        self.assertEqual(texkit.upscale_nearest([1, 2, 3, 4], 2, 2, 4, 2), [1, 1, 2, 2, 3, 3, 4, 4])
        self.assertEqual(texkit.upscale_nearest_bytes(bytes([1, 2, 3, 4, 5, 6]), 3, 2, 1, 4, 2),
                         bytes([1, 2, 3, 1, 2, 3, 4, 5, 6, 4, 5, 6] * 2))
        with self.assertRaises(ValueError):
            texkit.upscale_nearest_bytes(bytes(5), 3, 2, 1, 4, 2)
        wave = [math.sin(2 * math.pi * (x + 0.5) / 32) for _y in range(4) for x in range(32)]
        distance = texkit.isoline_distance(wave, 32, 4)
        self.assertLess(distance[15], 0.02, "the zero crossing near the middle is about a pixel away")
        self.assertAlmostEqual(distance[0], 0.5 / 32, delta=0.004)
        self.assertGreater(distance[8], 0.1)

    def test_normals_and_occlusion(self):
        flat = texkit.normal_map([0.5] * 16, 4, 4, 0.05)
        self.assertEqual(flat, bytes([128, 128, 255]) * 16)
        rising_right = [x / 8.0 for _y in range(8) for x in range(8)]
        normals = texkit.normal_map(rising_right, 8, 8, 0.05)
        self.assertLess(normals[3 * 8 * 3 + 3 * 3], 128, "a surface rising to the right faces left")
        rising_down = [y / 8.0 for y in range(8) for _x in range(8)]
        opengl = texkit.normal_map(rising_down, 8, 8, 0.05)
        directx = texkit.normal_map(rising_down, 8, 8, 0.05, directx=True)
        self.assertGreater(opengl[3 * 8 * 3 + 3 * 3 + 1], 128, "rising toward the bottom faces +V (up)")
        self.assertLess(directx[3 * 8 * 3 + 3 * 3 + 1], 128)
        self.assertTrue(all(value > 0.999999 for value in texkit.ambient_occlusion([0.5] * 64, 8, 8, 0.25)))
        pit = [0.8] * 256
        pit[8 * 16 + 8] = 0.0
        occlusion = texkit.ambient_occlusion(pit, 16, 16, 0.2)
        self.assertLess(occlusion[8 * 16 + 8], 0.9)
        self.assertAlmostEqual(occlusion[0], 1.0, places=6)

    def test_colour(self):
        self.assertEqual(texkit.hex_rgb("#ff8000"), (1.0, 128 / 255, 0.0))
        with self.assertRaises(ValueError):
            texkit.hex_rgb("#fff")
        self.assertAlmostEqual(texkit.srgb_to_linear(0.5), 0.214041, places=5)
        self.assertAlmostEqual(texkit.linear_to_srgb(texkit.srgb_to_linear(0.3)), 0.3)
        self.assertAlmostEqual(texkit.linear_to_srgb(0.001), 0.01292)
        r, g, b = texkit.ramp([0.0, 0.5, 1.0, 2.0], [(0.0, "#000000"), (1.0, (1.0, 0.5, 0.0))])
        self.assertEqual((r[0], r[2], r[3]), (0.0, 1.0, 1.0))
        self.assertAlmostEqual(r[1], 0.5, delta=0.002)
        self.assertAlmostEqual(g[2], 0.5)
        mixed = texkit.mix_rgb((0.0, [0.0, 1.0], 1.0), ([1.0, 1.0], 0.0, 1.0), [0.5, 1.0])
        self.assertEqual(mixed, ([0.5, 1.0], [0.0, 0.0], [1.0, 1.0]))
        self.assertEqual(texkit.mix_rgb("#000000", "#ffffff", [0.5])[1], [0.5])
        self.assertEqual(texkit.shade(([1.0, 0.5], [0.2, 0.2], [0.0, 1.0]), [0.5, 2.0]), ([0.5, 1.0], [0.1, 0.4],
                                                                                          [0.0, 2.0]))
        self.assertAlmostEqual(texkit.luminance(([1.0], [1.0], [1.0]))[0], 1.0)
        colour = ([0.8, 0.1], [0.4, 0.5], [0.2, 0.9])
        self.assertEqual(texkit.grade(colour), colour)
        grey = texkit.grade(colour, saturation=0.0)
        self.assertAlmostEqual(grey[0][0], grey[2][0], places=3)
        darker = texkit.grade(colour, brightness=0.5)
        self.assertAlmostEqual(darker[0][0], 0.4, delta=0.01)
        turned = texkit.grade(colour, hue_shift=1.0)
        self.assertAlmostEqual(turned[1][1], 0.5, delta=0.01)
        self.assertNotAlmostEqual(texkit.grade(colour, hue_shift=0.33)[0][0], 0.8, delta=0.05)
        self.assertEqual(texkit.nearest_palette(([0.1, 0.9], [0.1, 0.9], [0.1, 0.8]), ["#000000", "#ffffff"]), [0, 1])
        thresholds = [texkit.bayer4(x, y) for y in range(4) for x in range(4)]
        self.assertEqual(len(set(thresholds)), 16)
        self.assertTrue(all(0.0 < t < 1.0 for t in thresholds))
        self.assertEqual(texkit.bayer4(5, 6), texkit.bayer4(1, 2))

    def test_encoding_and_map_files(self):
        self.assertEqual(texkit.to_bytes([-1.0, 0.0, 0.5, 1.0, 2.0]), bytes([0, 0, 128, 255, 255]))
        self.assertEqual(texkit.to_bytes([0.0, 1.0], 0.2, 0.8), bytes([51, 204]))
        self.assertEqual(texkit.interleave(b"ab", b"cd"), b"acbd")
        with self.assertRaises(ValueError):
            texkit.interleave(b"ab", b"c")
        rows = [{"name": "albedo", "channels": 3, "colour_space": "srgb", "range": [0.1, 0.9]},
                {"name": "normal", "channels": 3, "colour_space": "linear"},
                {"name": "roughness", "channels": 1, "colour_space": "linear"},
                {"name": "height", "channels": 1, "colour_space": "linear"},
                {"name": "ao", "channels": 1, "colour_space": "linear"}]
        heights = [0.5] * 16
        maps = texkit.finish(4, 4, rows, albedo=([1.0] * 16, [0.0] * 16, [0.5] * 16), heights=heights, roughness=0.6)
        self.assertEqual(maps["albedo"]["pixels"][:3], bytes([230, 26, 128]))
        self.assertEqual(maps["roughness"]["pixels"], bytes([153]) * 16)
        self.assertEqual(maps["ao"]["pixels"], bytes([255]) * 16)
        self.assertEqual(texkit.pack_orm(maps, 4, 4)[:3], bytes([255, 153, 0]))
        tilted = bytes([100, 150, 230]) * 16
        given = texkit.finish(4, 4, rows, albedo=([0.5] * 16,) * 3, heights=heights, roughness=0.6, normal=tilted)
        self.assertEqual(given["normal"]["pixels"], tilted, "precomputed normal bytes are used as given")
        with self.assertRaises(ValueError):
            texkit.finish(4, 4, [{"name": "gloss", "channels": 1, "colour_space": "linear"}], albedo=None)
        with tempfile.TemporaryDirectory() as folder:
            paths = texkit.write_maps(maps, 4, 4, folder, "sample", orm=True)
            self.assertEqual(sorted(path.name for path in paths), ["sample_albedo.png", "sample_ao.png",
                                                                   "sample_height.png", "sample_normal.png",
                                                                   "sample_orm.png", "sample_roughness.png"])
            self.assertEqual(pngio.decode(paths[0].read_bytes())["pixels"], maps["albedo"]["pixels"])

    def test_png_codec(self):
        for channels in (1, 3, 4):
            pixels = bytes((k * 37) % 256 for k in range(5 * 3 * channels))
            data = pngio.encode(5, 3, pixels, channels)
            self.assertEqual(pngio.decode(data)["pixels"], pixels)
        image = pngio.decode(pngio.encode(2, 1, bytes([0, 255]), 1))
        self.assertEqual(pngio.statistics(image)["channels"][0], {"minimum": 0, "maximum": 255, "mean": 127.5})
        broken = bytearray(pngio.encode(4, 4, bytes(48), 3))
        broken[-20] ^= 0xFF
        with self.assertRaises(pngio.PngError):
            pngio.decode(bytes(broken))


if __name__ == "__main__":
    unittest.main()
