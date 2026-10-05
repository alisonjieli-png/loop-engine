"""Offline tests of the loaders this asset package carries: blender_load.py and godot_load.gd.

Blender is not needed: a recording stand-in for the bpy module checks that every variant of the package loads the
way its asset type needs (the HDRI as the world's environment texture, a model through the importer of its format
or appended from its .blend file, a texture or material set as a material on a plane, built from the package's own
.blend file or from its maps with the data maps marked Non-Color). Known wrong: a variant that was not fetched is
refused before bpy is touched, and an unknown variant is refused. The Godot script must be well formed GDScript and
read the file roles this package records; when Godot 4 is installed (godot or godot4 on the path) its own parser
must accept the script.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import blender_load  # noqa: E402

MANIFEST = blender_load.read_manifest(HERE / "creative.json")
GODOT_SCRIPT = (HERE / "godot_load.gd").read_text(encoding="utf-8")
BLOCK_WORDS = ("func", "static func", "if", "elif", "else", "for", "while", "match")
#: The roles each loader reads for each asset type; the package's every variant must provide one of them.
LOADED_ROLES = {"hdri": ("environment",), "model": ("model",), "texture": ("diffuse", "blend"),
                "material": ("diffuse", "blend")}


class _Record:
    """An object that keeps whatever is assigned to it."""

    def __init__(self, **values):
        self.__dict__.update(values)


class _Sockets(dict):
    def __missing__(self, name):
        self[name] = _Record(name=name, default_value=None)
        return self[name]


class _Nodes(list):
    def new(self, kind):
        node = _Record(kind=kind, inputs=_Sockets(), outputs=_Sockets(), image=None)
        self.append(node)
        return node

    def get(self, name):
        return self.new(name)


class _Links(list):
    def new(self, output, socket):
        self.append((output, socket))


class _Datablock:
    def __init__(self, name):
        self.name, self.use_nodes = name, False
        self.node_tree = _Record(nodes=_Nodes(), links=_Links())


class _Library:
    def __init__(self, bpy, path, link):
        self.bpy, self.path, self.link = bpy, path, link
        self.source = _Record(objects=["Model"], materials=["Material"])
        self.target = _Record()

    def __enter__(self):
        self.bpy.calls.append(("libraries.load", self.path, self.link))
        return self.source, self.target

    def __exit__(self, *_exception):
        for name in ("objects", "materials"):
            if hasattr(self.target, name):
                setattr(self.target, name, [_Datablock(item) for item in getattr(self.target, name)])
        return False


class FakeBpy(types.ModuleType):
    """The parts of bpy the loaders call, recording each call."""

    def __init__(self):
        super().__init__("bpy")
        self.calls = []
        linked, selected = [], [_Record(name="Imported")]
        plane = _Record(name="Plane", data=_Record(materials=[]))
        self.context = _Record(scene=_Record(world=None, collection=_Record(objects=_Record(link=linked.append))),
                               selected_objects=selected, active_object=plane)
        self.linked, self.plane = linked, plane
        images = []
        self.images = images

        def load_image(path, check_existing=False):
            image = _Record(filepath=path, colorspace_settings=_Record(name="sRGB"))
            images.append(image)
            return image

        def new_world(name):
            return _Datablock(name)

        def new_material(name):
            material = _Datablock(name)
            self.calls.append(("materials.new", name))
            return material

        self.data = _Record(images=_Record(load=load_image), worlds=_Record(new=new_world),
                            materials=_Record(new=new_material),
                            libraries=_Record(load=lambda path, link=False: _Library(self, path, link)))

        def operator(name):
            return lambda **options: self.calls.append((name, options))

        self.ops = _Record(import_scene=_Record(gltf=operator("import_scene.gltf"), fbx=operator("import_scene.fbx")),
                           wm=_Record(obj_import=operator("wm.obj_import"), usd_import=operator("wm.usd_import")),
                           mesh=_Record(primitive_plane_add=operator("mesh.primitive_plane_add")))


def _placeholders(folder, variant):
    """Empty files at every path the variant puts in place (an archive's members in place of the archive)."""
    for item in variant["files"]:
        for row in (item.get("members") or []) if item.get("unpack") else [item]:
            path = Path(folder).joinpath(*PurePosixPath(row["path"]).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")


class BlenderLoaderTest(unittest.TestCase):
    def setUp(self):
        self.bpy = FakeBpy()
        self.saved = sys.modules.get("bpy")
        sys.modules["bpy"] = self.bpy
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        if self.saved is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = self.saved
        shutil.rmtree(self.folder)

    def test_every_variant_loads_the_way_its_asset_type_needs(self):
        kind = MANIFEST["asset"]["type"]
        self.assertTrue(MANIFEST["variants"])
        for variant in MANIFEST["variants"]:
            self.bpy.__init__()
            _placeholders(self.folder, variant)
            files = blender_load.files_by_role(self.folder, variant)
            result = blender_load.load(self.folder, variant["id"], manifest=MANIFEST)
            if kind == "hdri":
                [texture] = [node for node in result.node_tree.nodes if node.kind == "ShaderNodeTexEnvironment"]
                self.assertEqual(texture.image.filepath, str(files["environment"]))
                self.assertIn((texture.outputs["Color"], next(node for node in result.node_tree.nodes
                                                              if node.kind == "ShaderNodeBackground").inputs["Color"]),
                              result.node_tree.links)
            elif kind == "model":
                suffix = files["model"].suffix.lower()
                if suffix == ".blend":
                    self.assertIn(("libraries.load", str(files["model"]), False), self.bpy.calls)
                    self.assertTrue(self.bpy.linked)
                else:
                    group, operator = blender_load.MODEL_IMPORTERS[suffix]
                    self.assertIn((f"{group}.{operator}", {"filepath": str(files["model"])}), self.bpy.calls)
            else:
                self.assertIs(result, self.bpy.plane)
                self.assertEqual(len(result.data.materials), 1)
                self.assertIn(("mesh.primitive_plane_add", {"size": blender_load.plane_size(MANIFEST)}), self.bpy.calls)
                if "blend" in files:
                    self.assertIn(("libraries.load", str(files["blend"]), False), self.bpy.calls)
                else:
                    loaded = {image.filepath: image.colorspace_settings.name for image in self.bpy.images}
                    self.assertEqual(loaded.get(str(files["diffuse"])), "sRGB")
                    for role in ("roughness", "normal_gl", "metalness"):
                        if role in files:
                            self.assertEqual(loaded.get(str(files[role])), "Non-Color", role)
            shutil.rmtree(self.folder)
            Path(self.folder).mkdir()

    def test_known_wrong_a_variant_that_was_not_fetched_touches_nothing(self):
        variant = MANIFEST["variants"][0]
        with self.assertRaises(FileNotFoundError) as caught:
            blender_load.load(self.folder, variant["id"], manifest=MANIFEST)
        self.assertIn("creative_fetch.py fetch", str(caught.exception))
        self.assertEqual((self.bpy.calls, self.bpy.images, self.bpy.linked), ([], [], []))

    def test_known_wrong_an_unknown_variant_is_refused(self):
        with self.assertRaises(ValueError):
            blender_load.load(self.folder, "no-such-variant", manifest=MANIFEST)

    def test_the_command_line_takes_the_words_after_the_separator(self):
        self.assertEqual(blender_load.arguments(["blender", "--python", "blender_load.py", "--", "assets/x", "v1"]),
                         ("assets/x", "v1"))
        self.assertEqual(blender_load.arguments(["blender"]), (".", None))


def gdscript_problems(text: str) -> list:
    """A structural reading of GDScript: tab indentation, balanced brackets and strings, blocks that open with a
    colon and are followed by deeper lines. It is no parser; Godot's own parser runs when Godot is installed."""
    problems, depth, lines = [], 0, text.splitlines()
    code = [(number, line) for number, line in enumerate(lines, 1) if line.strip() and not line.strip().startswith("#")]
    if not code or code[0][1].strip() != "extends Node3D":
        problems.append("the script does not start with extends Node3D")
    for position, (number, line) in enumerate(code):
        indentation = line[:len(line) - len(line.lstrip())]
        if indentation.strip("\t"):
            problems.append(f"line {number} is indented with spaces")
        body, quoted = "", None
        for character in line.lstrip():
            if quoted:
                if character == quoted:
                    quoted = None
                continue
            if character in "\"'":
                quoted = character
            elif character == "#":
                break
            else:
                body += character
        if quoted:
            problems.append(f"line {number} leaves a string open")
        depth += sum(body.count(mark) for mark in "([{") - sum(body.count(mark) for mark in ")]}")
        if depth < 0:
            problems.append(f"line {number} closes a bracket that is not open")
            depth = 0
        word = body.strip()
        if depth == 0 and any(word == opener or word.startswith(opener + " ") or word.startswith(opener + "(")
                              for opener in BLOCK_WORDS):
            if not word.endswith(":"):
                problems.append(f"line {number} opens a block without a colon")
            elif position + 1 >= len(code) or len(code[position + 1][1]) - len(code[position + 1][1].lstrip()) \
                    <= len(indentation):
                problems.append(f"line {number} opens a block with no deeper line after it")
    if depth:
        problems.append("a bracket is left open at the end")
    return problems


class GodotLoaderTest(unittest.TestCase):
    def test_the_script_is_well_formed_gdscript(self):
        self.assertEqual(gdscript_problems(GODOT_SCRIPT), [])

    def test_known_wrong_broken_scripts_are_caught(self):
        for broken in (GODOT_SCRIPT.replace("func _ready() -> void:", "func _ready() -> void"),
                       GODOT_SCRIPT.replace("\tvar manifest: Dictionary", "    var manifest: Dictionary", 1),
                       GODOT_SCRIPT.replace("add_child(environment(", "add_child((environment(", 1),
                       GODOT_SCRIPT.replace("extends Node3D", "extends Node")):
            self.assertNotEqual(broken, GODOT_SCRIPT)
            self.assertTrue(gdscript_problems(broken))

    def test_the_script_reads_the_roles_this_package_records(self):
        roles = set(re.findall(r'files\.(?:has|get)\("([a-z_]+)"', GODOT_SCRIPT))
        wanted = LOADED_ROLES[MANIFEST["asset"]["type"]]
        for variant in MANIFEST["variants"]:
            recorded = {row.get("role") for item in variant["files"]
                        for row in ((item.get("members") or []) if item.get("unpack") else [item])}
            self.assertTrue(recorded & set(wanted), (variant["id"], sorted(recorded)))
        self.assertTrue(set(wanted) - {"blend"} <= roles, sorted(roles))

    @unittest.skipUnless(shutil.which("godot") or shutil.which("godot4"), "Godot 4 is not installed on this machine")
    def test_godot_parses_the_script(self):
        godot = shutil.which("godot") or shutil.which("godot4")
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "project.godot").write_text('config_version=5\n\n[application]\nconfig/name="check"\n',
                                                        encoding="utf-8")
            shutil.copyfile(HERE / "godot_load.gd", Path(folder) / "godot_load.gd")
            done = subprocess.run([godot, "--headless", "--path", folder, "--check-only", "--script", "godot_load.gd"],
                                  capture_output=True, text=True, timeout=120, check=False)
        self.assertEqual(done.returncode, 0, done.stderr[-600:])
        self.assertNotIn("SCRIPT ERROR", done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
