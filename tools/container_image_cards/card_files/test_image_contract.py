"""The card's contract, schema, README, component card and registry evidence agree, and the helper refuses bad inputs.

Known-wrong controls: a changed index digest, a removed environment variable, port or platform, an extra platform,
a contract that lost a required field, and inputs that break the contract (an unknown platform, a port out of
range, a relative volume target, a malformed variable name, a credential given as a value) are each reported.
"""
import contextlib
import copy
import hashlib
import io
import json
import unittest
from pathlib import Path

import image_contract
import schema_check

HERE = Path(__file__).resolve().parent
OTHER_DIGEST = "sha256:" + "0" * 64


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def card_files():
    return {path.relative_to(HERE).as_posix(): path.read_bytes() for path in HERE.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts}


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = load("contract.json")
        self.readme = (HERE / "README.md").read_text(encoding="utf-8")

    def test_the_contract_matches_its_schema(self):
        self.assertEqual(schema_check.errors(self.contract, load("schema.json")), [])

    def test_the_readme_agrees_with_the_contract(self):
        self.assertEqual(image_contract.disagreements(self.contract, self.readme), [])

    def test_the_component_card_names_this_contract_and_its_files(self):
        component = load("component.json")
        image = self.contract["image"]
        self.assertEqual(component["job"], {"registry": image["registry"], "repository": image["repository"],
                                            "family": self.contract["family"]["identity"]})
        self.assertEqual(component["image"]["reference"], image["reference"])
        self.assertEqual(component["platforms"], image_contract.platforms(self.contract))
        files = card_files()
        for row in component["files"]:
            self.assertIn(row["path"], files)
            self.assertEqual(row["sha256"], hashlib.sha256(files[row["path"]]).hexdigest(), row["path"])

    def test_the_registry_evidence_binds_these_exact_files(self):
        evidence = load("verification/registry.json")
        self.assertEqual(evidence["state"], "passed")
        self.assertEqual(evidence["card_digest"], image_contract.card_digest(card_files()))
        self.assertEqual(evidence["index_digest"], self.contract["image"]["index"]["digest"])

    def test_the_default_command_runs_the_pinned_index(self):
        argv = image_contract.default_run(self.contract)
        self.assertEqual(argv[:3], [image_contract.DEFAULT_ENGINE, "run", "--rm"])
        self.assertIn(self.contract["image"]["reference"], argv)
        self.assertIn(image_contract.shell_line(argv), self.readme.split("\n"))

    def test_every_platform_renders_and_an_unknown_one_is_refused(self):
        command = [image_contract.COMMAND_PLACEHOLDER] if image_contract.needs_command(self.contract) else None
        for name in image_contract.platforms(self.contract):
            argv = image_contract.render_run(self.contract, platform=name, command=command)
            self.assertEqual(argv[argv.index("--platform") + 1], name)
            runtime = image_contract.platform_runtime(self.contract, name)
            self.assertTrue(set(runtime) >= {"entrypoint", "command", "environment", "ports", "volumes"})
        problems = image_contract.problems(self.contract, platform="plan9/sparc")
        self.assertTrue(any("plan9/sparc" in problem for problem in problems), problems)

    def test_known_inputs_render_with_their_flags(self):
        ports = self.contract["inputs"]["ports"]
        publish = [f"18080:{ports[0]['port']}/{ports[0]['protocol']}"] if ports else []
        argv = image_contract.render_run(self.contract, environment={"BALTOR_EXAMPLE": "1", "API_TOKEN": None},
                                         publish=publish, volumes=["baltor-data:/baltor-data:ro"], name="card-check",
                                         detach=True, command=["--version"])
        self.assertIn("BALTOR_EXAMPLE=1", argv)
        self.assertIn("API_TOKEN", argv)
        self.assertIn("baltor-data:/baltor-data:ro", argv)
        self.assertEqual(argv[-1], "--version")
        if publish:
            self.assertIn(publish[0], argv)
            self.assertFalse(any("does not expose" in notice
                                 for notice in image_contract.notices(self.contract, publish=publish)))
        # Known wrong: a port the image does not expose is a notice, not silence.
        self.assertTrue(any("does not expose" in notice
                            for notice in image_contract.notices(self.contract, publish=["18081:1/udp"])))

    def test_known_wrong_a_changed_index_digest_is_reported(self):
        changed = copy.deepcopy(self.contract)
        name = changed["image"]["reference"].split("@")[0]
        changed["image"]["reference"] = f"{name}@{OTHER_DIGEST}"
        self.assertTrue(image_contract.disagreements(changed, self.readme))
        self.assertEqual(image_contract.disagreements(self.contract, self.readme), [])

    def test_known_wrong_a_removed_variable_port_or_platform_is_reported(self):
        for section, key in (("inputs", "environment"), ("inputs", "ports"), (None, "platforms")):
            changed = copy.deepcopy(self.contract)
            rows = changed[section][key] if section else changed[key]
            if len(rows) < 2 and key == "platforms":
                rows.append(dict(rows[0], platform="linux/s390x", manifest=dict(rows[0]["manifest"],
                                                                                digest=OTHER_DIGEST)))
            elif rows:
                rows.pop(0)
            else:
                continue
            self.assertTrue(image_contract.disagreements(changed, self.readme), key)

    def test_known_wrong_a_contract_missing_a_field_fails_its_schema(self):
        schema = load("schema.json")
        for path in (("image", "reference"), ("platforms",), ("inputs", "ports")):
            changed = copy.deepcopy(self.contract)
            target = changed
            for key in path[:-1]:
                target = target[key]
            del target[path[-1]]
            self.assertTrue(schema_check.errors(changed, schema), path)
        changed = copy.deepcopy(self.contract)
        changed["platforms"][0]["config"]["digest"] = "sha256:not-a-digest"
        self.assertTrue(schema_check.errors(changed, schema))

    def test_known_wrong_inputs_are_refused(self):
        cases = [{"publish": ["8080:70000"]}, {"publish": ["8080:80/xtp"]}, {"volumes": ["data:relative/path"]},
                 {"environment": {"1BAD": "x"}}, {"environment": {"DB_PASSWORD": "hunter2"}},
                 {"platform": "linux/does-not-exist"}, {"name": "bad name"}, {"command": "not a list"}]
        for case in cases:
            self.assertTrue(image_contract.problems(self.contract, **case), case)
            with self.assertRaises(image_contract.InputError):
                image_contract.render_run(self.contract, **case)
        self.assertEqual(image_contract.problems(self.contract, environment={"DB_PASSWORD": None},
                                                 command=["true"]), [])

    def test_the_command_line_prints_the_command_or_the_problems(self):
        output, errors = io.StringIO(), io.StringIO()
        command = ["--", image_contract.COMMAND_PLACEHOLDER] if image_contract.needs_command(self.contract) else []
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = image_contract.main(["--contract", str(HERE / "contract.json")] + command)
        self.assertEqual(status, 0)
        self.assertIn(self.contract["image"]["reference"], output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
            status = image_contract.main(["--contract", str(HERE / "contract.json"), "--publish", "8080:0"])
        self.assertEqual(status, 2)
        self.assertIn("problem:", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
