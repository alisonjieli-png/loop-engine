"""The engine_api_cards supply line end to end: the licence decision, the packages it builds from a fixture release, its
refusals by name, and every qualification check on the stored bytes (the sandbox and mutation checks when bubblewrap
is available).

Known-wrong controls: a file under another licence's stanza, a licence answer for another blob, a class reference
whose structure differs from the build's, a class with no surface, and missing, stale and failed native evidence are
each refused by name; a second card of one class and version is the same job; a package whose test cannot fail is
refused by mutation.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from engine_api_cards import godot_native, godot_renames  # noqa: E402
from engine_api_cards.godot_reference import inheritance, read_reference  # noqa: E402
from supply_lines import engine_api_cards as line  # noqa: E402
from supply_lines.records import ENGINE_API_CARDS, REFUSAL_REASONS  # noqa: E402
from tools.component_qualification import checks, components  # noqa: E402
from tools.component_qualification.sandbox import SandboxSettings  # noqa: E402
from tools.test_engine_api_cards import (BODY_DUMP, BODY_TEXT, COMMIT, GLOBAL_DUMP, OBJECT_DUMP, RENAMES_MAP,  # noqa: E402
                                         ENGINE, THING_DUMP, VARIANT_DUMP, VECTOR_DUMP, documented,
                                         release)

REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
SANDBOX = SandboxSettings()
HAS_SANDBOX = bool(REVISION) and SANDBOX.works()


class LicenceTests(unittest.TestCase):
    COPYRIGHT = ("Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n\n"
                 "Files: *\nComment: Godot Engine\nCopyright: 2014-present, Godot Engine contributors\n"
                 "License: Expat\n\nFiles: doc/classes/Odd.xml\n doc/classes/Odder.xml\nLicense: CC-BY-3.0\n\n"
                 "Files: core/mixed.cpp\nLicense: Expat and Zlib\n\nLicense: Expat\n Permission is hereby granted\n")

    def test_the_last_matching_stanza_decides_and_another_licence_is_refused(self):
        stanzas = line.copyright_stanzas(self.COPYRIGHT)
        self.assertEqual(stanzas, [(["*"], "Expat"), (["doc/classes/Odd.xml", "doc/classes/Odder.xml"], "CC-BY-3.0"),
                                   (["core/mixed.cpp"], "Expat and Zlib")])
        self.assertEqual(line.governing_licence("doc/classes/Node.xml", stanzas), line.EXPAT)
        self.assertEqual(line.governing_licence("doc/classes/Odder.xml", stanzas), "CC-BY-3.0")
        self.assertEqual(line.governing_licence("core/mixed.cpp", stanzas), "Expat and Zlib")
        self.assertIsNone(line.governing_licence("x", []))
        self.assertEqual(line.release_numbers("4.7.2-stable"), ("4.7.2", "4.7"))

    def test_the_default_branch_answer_counts_only_for_the_same_licence_blob(self):
        mit = (ROOT / "LICENSE").read_bytes()

        class Reader:
            def __init__(self, blob):
                self.blob = blob

            def licence_text(self, repository, commit):
                return "LICENSE", mit, "NOASSERTION"

            def github(self, path):
                body = json.dumps({"sha": self.blob, "path": "LICENSE", "license": {"spdx_id": "MIT"}}).encode()
                return type("Answer", (), {"status": 200, "body": body})()

        decision, basis = line.tag_licence(Reader("abc"), "godotengine/godot", COMMIT, {"blob": "abc"})
        self.assertEqual((decision.spdx, basis), ("MIT", line.LICENCE_OF_THE_SAME_BLOB))
        # Known wrong: the default branch's licence file is another blob, so its answer says nothing of these bytes.
        decision, basis = line.tag_licence(Reader("other"), "godotengine/godot", COMMIT, {"blob": "abc"})
        self.assertFalse(decision.allowed)


def pinned(path: str, data: bytes) -> dict:
    return {"url": f"https://raw.githubusercontent.com/godotengine/godot/{COMMIT}/{path}", "bytes": data,
            "sha256": hashlib.sha256(data).hexdigest(), "retrieved_at": "2026-10-09T00:00:00Z", "blob": "0" * 40}


def sources(*, structure_differs: bool = True) -> line.EngineSources:
    dumps = {"Body": BODY_DUMP, "Thing": THING_DUMP, "Object": OBJECT_DUMP, "Vector3": VECTOR_DUMP,
             "@GDScript": GLOBAL_DUMP, "Variant": VARIANT_DUMP}
    texts = dict(dumps, Body=documented(BODY_DUMP, BODY_TEXT))
    if structure_differs:
        texts["Thing"] = THING_DUMP.replace('default="true"', 'default="false"')
    paths = {name: f"doc/classes/{name}.xml" for name in dumps}
    found = {name: read_reference(text.encode()) for name, text in dumps.items()}
    licence = pinned(line.LICENCE_PATH, (ROOT / "LICENSE").read_bytes())
    files = {paths[name]: pinned(paths[name], text.encode()) for name, text in texts.items()}
    files.update({line.LICENCE_PATH: licence, line.COPYRIGHT_PATH: pinned(line.COPYRIGHT_PATH, b"Files: *\n"
                                                                                               b"License: Expat\n"),
                  godot_renames.MAP_PATH: pinned(godot_renames.MAP_PATH, RENAMES_MAP.encode())})
    chains, _children = inheritance(found)
    renames, _outcomes = godot_renames.attach(godot_renames.read_map(RENAMES_MAP, set(found)), found, chains)
    return line.EngineSources(
        release=release(), dump={name: (paths[name], text.encode()) for name, text in dumps.items()},
        references=found, documentation={name: read_reference(text.encode()) for name, text in texts.items()},
        reference_paths=paths, pinned=files, licence=dict(licence, evidence={}, basis=line.LICENCE_AT_THE_TAG),
        copyright=files[line.COPYRIGHT_PATH], renames=renames, renames_map=files[godot_renames.MAP_PATH],
        release_asset={"url": "https://github.com/godotengine/godot/releases/download/4.7.2-stable/x.zip",
                       "sha256": "9" * 64, "size_bytes": 10, "retrieved_at": "2026-10-09T00:00:00Z", "member": "x"})


class LineTests(unittest.TestCase):
    ENGINE = ENGINE

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def verifier(self, *, missing=(), stale=(), failing=()):
        def verify(prepared):
            records = {}
            for name, card in prepared.items():
                if name in missing:
                    continue
                answer = {"known": True, "parent": (card.api["inherits"] or [""])[0], "missing": {
                    key: [] for key in ("methods", "members", "overridden_members", "signals", "constants", "enums")}}
                if name in failing:
                    answer["missing"]["methods"] = [card.api["sections"]["methods"][0]["name"]]
                digest = "f" * 64 if name in stale else card.digest
                records[name] = godot_native.evidence_bytes(godot_native.evidence(self.ENGINE, card.api, answer,
                                                                                  digest))
            return records
        return verify

    def generate(self, **verifier):
        return line.generate(sources(), verifier=self.verifier(**verifier), code_revision=REVISION,
                             licence_text=(ROOT / "LICENSE").read_bytes(), generated_on="2026-10-09",
                             staging=self.root / "staging", workers=2)

    def component(self, built):
        payload, bodies = built
        folder = self.root / "package" / payload["record_id"]
        for entry in payload["package"]["files"]:
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[entry["digest"]])
        (folder / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
        return components.from_folder(folder)

    def test_every_class_with_a_surface_and_holding_evidence_is_packaged_and_the_rest_refused_by_name(self):
        built, refusals, facts, summary = self.generate()
        names = sorted(payload["repository"]["class"] for payload, _bodies in built)
        self.assertEqual(names, ["@GDScript", "Body", "Object", "Vector3"])
        self.assertEqual(sorted((row["reason"], row["subject"]) for row in refusals),
                         [("documentation_structure_differs", "Thing"), ("no_api_surface", "Variant")])
        self.assertTrue(set(row["reason"] for row in refusals) <= set(REFUSAL_REASONS[ENGINE_API_CARDS]))
        self.assertEqual(summary["packaged_by_kind"], {"global_scope": 1, "class": 2, "builtin_type": 1})
        payload = next(payload for payload, _bodies in built if payload["repository"]["class"] == "Body")
        self.assertEqual((payload["line"], payload["kind"], payload["component_form"]["form"]),
                         (ENGINE_API_CARDS, "contract_schema", "schema"))
        origins = {row["path"]: (row["origin"], row["role"]) for row in payload["files"]}
        self.assertEqual(origins["UPSTREAM-LICENSE"], ("licence_text", "other"))
        self.assertEqual(origins["api_card.py"], ("generated", "executable_tool"))
        self.assertEqual(payload["declared_effects"], ["spawns_process"])
        self.assertEqual([fact["role"] for fact in payload["provenance"]["facts"]],
                         ["licence_text", "licence_evidence", "data_source", "data_source", "release"])
        self.assertIn(hashlib.sha256(RENAMES_MAP.encode()).hexdigest(), facts)

    def test_missing_stale_and_failed_evidence_are_refused_by_name(self):
        _built, refusals, _facts, _summary = self.generate(missing=("Body",), stale=("Vector3",),
                                                           failing=("@GDScript",))
        reasons = {row["subject"]: row["reason"] for row in refusals}
        self.assertEqual((reasons["Body"], reasons["Vector3"], reasons["@GDScript"]),
                         ("native_evidence_missing", "native_evidence_stale", "native_check_failed"))

    def test_every_static_check_passes_on_the_stored_bytes_and_one_card_is_one_job(self):
        built, _refusals, _facts, _summary = self.generate()
        population = [self.component(row) for row in built]
        context = checks.QualificationContext.load(ROOT)
        context.duplicates = checks.duplicate_findings(population, context.policy)
        for component in population:
            for check in checks.CHECKS:
                if check.check_id in ("sandbox", "mutation"):
                    continue
                result = check.run(component, context)
                self.assertEqual(result.status, checks.PASSED, (component.identity, check.check_id, result.findings))
        self.assertEqual(checks.job_key(population[0], context.policy).split("|")[:3],
                         [ENGINE_API_CARDS, "godot", "4.7"])
        # Known wrong: a second card of one class and API version is the same job, whatever its bytes.
        twin = population[0].replaced(identity=population[0].identity[:-16] + "0" * 16,
                                      payloads={**population[0].payloads, "README.md": b"# other bytes\n"})
        duplicates = checks.duplicate_findings(population + [twin], context.policy)
        self.assertTrue(any(code == "same_job_as" for row in duplicates.values() for code, _detail in row))

    @unittest.skipUnless(HAS_SANDBOX, "bubblewrap and the system interpreter are needed for the sandbox checks")
    def test_sandbox_and_mutation_pass_and_a_test_that_cannot_fail_is_refused(self):
        built, _refusals, _facts, _summary = self.generate()
        component = self.component(next(row for row in built if row[0]["repository"]["class"] == "Body"))
        context = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work")
        by_id = {check.check_id: check for check in checks.CHECKS}
        self.assertEqual(by_id["sandbox"].run(component, context).status, checks.PASSED)
        self.assertEqual(by_id["mutation"].run(component, context).status, checks.PASSED)
        weak = component.replaced(payloads={**component.payloads, "test_api_card.py": (
            b"import unittest\nimport api_card\n\n\nclass T(unittest.TestCase):\n    def test_nothing(self):\n"
            b"        self.assertTrue(True)\n")})
        self.assertEqual(by_id["mutation"].run(weak, context).status, checks.REFUSED)


class CommandTests(unittest.TestCase):
    def test_the_builder_has_the_command_and_its_paths_are_generator_paths(self):
        import build_library_supply
        options = build_library_supply.parser().parse_args(
            ["engine-api-cards", "--run-folder", "/tmp/x", "--authorize-network-reads", "--class", "Node"])
        self.assertEqual((options.engine, options.engine_class), ("godot", ["Node"]))
        self.assertIn("tools/engine_api_cards", build_library_supply.GENERATOR_PATHS)


if __name__ == "__main__":
    unittest.main()
