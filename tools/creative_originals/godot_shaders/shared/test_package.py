"""This shader package checked against its own contract card with inspect_shader (standard library only).

The shader's type, render modes and uniforms must equal the contract; the material and the demo scene must load only
files of this package from the placement folder. Known-wrong controls: the shader with one uniform removed, a material
that points at a missing shader, a material that sets an undeclared uniform and a scene that loads a missing file must
each be refused.
"""
import contextlib
import hashlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import inspect_shader

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
IDENTITY = CARD["job"]["identity"]
CONTRACT = CARD["contract"]
SHADER_TEXT = (ROOT / f"{IDENTITY}.gdshader").read_text(encoding="utf-8")

KNOWN_SNIPPET = """shader_type canvas_item; // a comment with uniform float hidden;
render_mode unshaded, blend_add;
/* uniform float also_hidden = 1.0; */
uniform vec4 tint : source_color = vec4(1.0, 0.5, 0.25, 1.0);
uniform float amount : hint_range(0.0,1.0, 0.05) = 0.5;
uniform int steps : hint_range(1, 8) = 3;
uniform bool enabled = true;
uniform sampler2D ramp : source_color, filter_linear;
varying vec2 local_uv;
float wave(float x) { return sin(x); }
void fragment() { COLOR = tint * amount; }
"""


def _copy_package(target: Path) -> Path:
    copy = target / "package"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
    return copy


class ParserKnownAnswers(unittest.TestCase):
    def test_snippet_declarations(self):
        parsed = inspect_shader.parse_shader(KNOWN_SNIPPET)
        self.assertEqual(parsed["shader_type"], "canvas_item")
        self.assertEqual(parsed["render_modes"], ["unshaded", "blend_add"])
        self.assertEqual([inspect_shader.contract_uniform(row) for row in parsed["uniforms"]], [
            {"name": "tint", "type": "vec4", "hint": "source_color", "default": [1.0, 0.5, 0.25, 1.0]},
            {"name": "amount", "type": "float", "hint": "hint_range(0.0, 1.0, 0.05)", "default": 0.5},
            {"name": "steps", "type": "int", "hint": "hint_range(1, 8)", "default": 3},
            {"name": "enabled", "type": "bool", "hint": None, "default": True},
            {"name": "ramp", "type": "sampler2D", "hint": "source_color, filter_linear", "default": None}])
        self.assertEqual([row["name"] for row in parsed["varyings"]], ["local_uv"])
        self.assertEqual(parsed["functions"], ["wave", "fragment"])

    def test_value_kinds(self):
        self.assertTrue(inspect_shader.value_fits("float", inspect_shader.value_kind("0.25")))
        self.assertTrue(inspect_shader.value_fits("vec3", inspect_shader.value_kind("Color(1, 0, 0, 1)")))
        self.assertTrue(inspect_shader.value_fits("sampler2D", inspect_shader.value_kind('SubResource("noise")')))
        self.assertFalse(inspect_shader.value_fits("int", inspect_shader.value_kind("0.5")))
        self.assertFalse(inspect_shader.value_fits("bool", inspect_shader.value_kind("1")))


class PackageAgainstContract(unittest.TestCase):
    def test_card_digests_match_files(self):
        for row in CARD["files"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])

    def test_shader_matches_contract(self):
        parsed = inspect_shader.parse_shader(SHADER_TEXT)
        self.assertEqual(parsed["shader_type"], CONTRACT["shader_type"])
        self.assertEqual(parsed["render_modes"], CONTRACT["render_modes"])
        self.assertEqual([(row["name"], row["type"]) for row in parsed["uniforms"]],
                         [(row["name"], row["type"]) for row in CONTRACT["uniforms"]])
        self.assertEqual(inspect_shader.contract_mismatches(parsed, CONTRACT, IDENTITY), [])

    def test_material_and_scene_resolve(self):
        report = inspect_shader.check_package(ROOT)
        self.assertEqual(report["problems"], [])
        self.assertEqual(CONTRACT["placement"], inspect_shader.placement_for(IDENTITY))

    def test_command_line_report(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = inspect_shader.main([str(ROOT)])
        self.assertEqual(status, 0)
        report = json.loads(output.getvalue())
        self.assertEqual((report["identity"], report["problems"]), (IDENTITY, []))
        self.assertEqual(report["shader"]["shader_type"], CONTRACT["shader_type"])


class KnownWrongControls(unittest.TestCase):
    def test_removed_uniform_is_a_contract_mismatch(self):
        self.assertTrue(CONTRACT["uniforms"], "every shader of this family declares uniforms")
        name = CONTRACT["uniforms"][0]["name"]
        pattern = r"uniform\s+(?:(?:lowp|mediump|highp)\s+)?\w+\s+" + re.escape(name) + r"\b[^;]*;"
        broken, count = re.subn(pattern, "", SHADER_TEXT, count=1)
        self.assertEqual(count, 1)
        problems = inspect_shader.contract_mismatches(inspect_shader.parse_shader(broken), CONTRACT, IDENTITY)
        self.assertIn(f"uniform_missing: {name}", problems)

    def test_changed_shader_type_is_a_contract_mismatch(self):
        other = "sky" if CONTRACT["shader_type"] != "sky" else "spatial"
        broken = re.sub(r"shader_type\s+\w+", f"shader_type {other}", SHADER_TEXT, count=1)
        problems = inspect_shader.contract_mismatches(inspect_shader.parse_shader(broken), CONTRACT, IDENTITY)
        self.assertTrue(any(problem.startswith("shader_type_mismatch") for problem in problems))

    def test_material_pointing_at_a_missing_shader_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = _copy_package(Path(folder))
            material = copy / "material.tres"
            text = material.read_text(encoding="utf-8")
            self.assertIn(f"{IDENTITY}.gdshader", text)
            material.write_text(text.replace(f"{IDENTITY}.gdshader", "missing_shader.gdshader"), encoding="utf-8")
            problems = inspect_shader.check_package(copy)["problems"]
            self.assertTrue(any(problem.startswith("material_shader_path_wrong") for problem in problems), problems)
            (copy / f"{IDENTITY}.gdshader").unlink()
            material.write_text(text, encoding="utf-8")
            problems = inspect_shader.check_package(copy)["problems"]
            self.assertTrue(any(problem.startswith("material_shader_missing") for problem in problems), problems)

    def test_undeclared_parameter_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = _copy_package(Path(folder))
            material = copy / "material.tres"
            material.write_text(material.read_text(encoding="utf-8").rstrip("\n")
                                + "\nshader_parameter/not_declared_anywhere = 1.0\n", encoding="utf-8")
            problems = inspect_shader.check_package(copy)["problems"]
            self.assertIn("material_parameter_undeclared: not_declared_anywhere", problems)

    def test_scene_loading_a_missing_file_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = _copy_package(Path(folder))
            scene = copy / "demo.tscn"
            text = scene.read_text(encoding="utf-8")
            self.assertIn("material.tres", text)
            scene.write_text(text.replace("material.tres", "gone.tres"), encoding="utf-8")
            problems = inspect_shader.check_package(copy)["problems"]
            self.assertTrue(any(problem.startswith("scene_resource_missing") for problem in problems), problems)
            self.assertIn("scene_material_unused", problems)


if __name__ == "__main__":
    unittest.main()
