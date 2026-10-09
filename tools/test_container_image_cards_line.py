"""The container_image_cards supply line end to end: the packages it builds from a fixture library, documentation
folder and registry, its refusals by name, and every qualification check on the stored bytes (the sandbox and
mutation checks when bubblewrap is available).

Known-wrong controls: a tag the registry does not hold, bytes that differ from their digest, a credential-shaped
value outside an environment value and a run's request ceiling are refused by name; a credential-shaped
environment value is withheld; missing, stale and failed registry evidence, and a failed smoke run, are refused by
name; a second card of one family is the same job; a package whose test cannot fail is refused by mutation.
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

from container_image_cards import cards  # noqa: E402
from container_image_cards import verify as native  # noqa: E402
from supply_lines import container_image_cards as line  # noqa: E402
from supply_lines.records import CONTAINER_IMAGE_CARDS, REFUSAL_REASONS  # noqa: E402
from tools.component_qualification import checks, components  # noqa: E402
from tools.component_qualification.sandbox import SandboxSettings  # noqa: E402
from tools.test_container_image_cards import (ANNOTATIONS, COMMIT, DOCS_FILES, LIBRARY_TEXT, SECRET_VALUE,  # noqa: E402
                                              config, demo_hub, reader)

REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
SANDBOX = SandboxSettings()
HAS_SANDBOX = bool(REVISION) and SANDBOX.works()
MIT = (ROOT / "LICENSE").read_bytes()
APACHE = (ROOT / "tools/fixtures/licence-texts/docker-library-official-images-LICENSE.txt").read_bytes()
EXTRA_LIBRARY = (f"GitRepo: https://github.com/example/docker-other.git\n\nTags: 3.0, latest\nArchitectures: amd64\n"
                 f"GitCommit: {COMMIT}\nDirectory: 3\n\nTags: 3.0-missing\nArchitectures: amd64\nGitCommit: {COMMIT}\n"
                 f"Directory: missing\n\nTags: 3.0-leaky\nArchitectures: amd64\nGitCommit: {COMMIT}\nDirectory: leaky\n")


def pinned(repository: str, path: str, data: bytes, spdx: "str | None" = None) -> dict:
    row = {"repository": repository, "commit": COMMIT, "path": path, "blob": "0" * 40,
           "url": f"https://raw.githubusercontent.com/{repository}/{COMMIT}/{path}", "bytes": data,
           "sha256": hashlib.sha256(data).hexdigest(), "retrieved_at": "2026-10-09T00:00:00Z"}
    if spdx:
        row.update(spdx=spdx, evidence={})
    return row


def collection() -> line.CollectionSources:
    docs_files = {name: pinned(line.DOCS_REPOSITORY, f"demo/{name}", data) for name, data in DOCS_FILES.items()}
    return line.CollectionSources(
        library_commit=COMMIT, docs_commit=COMMIT,
        library_files={"demo": pinned(line.LIBRARY_REPOSITORY, "library/demo", LIBRARY_TEXT.encode()),
                       "other": pinned(line.LIBRARY_REPOSITORY, "library/other", EXTRA_LIBRARY.encode())},
        docs_files={"demo": docs_files},
        library_licence=pinned(line.LIBRARY_REPOSITORY, "LICENSE", APACHE, "Apache-2.0"),
        docs_licence=pinned(line.DOCS_REPOSITORY, "LICENSE", MIT, "MIT"))


def hub():
    """The demo repository, and the other repository: one family with a secret-shaped environment value, one tag
    never pushed, one family whose label holds a credential-shaped value."""
    value = demo_hub()
    value.image("other", "3.0", [("linux", "amd64", None, config("amd64", env_extra=(
        f"OTHER_HINT={SECRET_VALUE}", "OTHER_INDEX=https://reader:index-pass-7Kq@packages.example.invalid/simple")),
        dict(ANNOTATIONS))])
    value.image("other", "3.0-leaky", [("linux", "amd64", None, config("amd64", label_extra={"note": SECRET_VALUE}),
                                        {})])
    return value


class LineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def generate(self, source=None, **settings):
        source = source or hub()
        registry = reader(source, self.root / "registry", **settings.pop("reader", {}))
        return line.generate(collection(), registry, code_revision=REVISION, licence_text=MIT,
                             generated_on="2026-10-09", staging=self.root / "staging", secret=line.secret_patterns(),
                             workers=2, registry_workers=settings.pop("registry_workers", 1),
                             evidence_folder=self.root / "evidence", **settings)

    def component(self, built):
        payload, bodies = built
        folder = self.root / "package" / payload["record_id"]
        for entry in payload["package"]["files"]:
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[entry["digest"]])
        (folder / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
        return components.from_folder(folder)

    def test_every_family_held_by_the_registry_is_packaged_and_the_rest_refused_by_name(self):
        built, refusals, facts, summary = self.generate(registry_workers=3)
        names = sorted(payload["repository"]["resolved_tag"] for payload, _bodies in built)
        self.assertEqual(names, ["1.9.9", "2.4.1", "2.4.1-alpine", "3.0"])
        self.assertEqual(sorted((row["reason"], row["subject"]) for row in refusals),
                         [("credential_shaped_value_in_image", "other:3.0-leaky"), ("tag_not_found", "other:3.0-missing")])
        self.assertTrue(set(row["reason"] for row in refusals) <= set(REFUSAL_REASONS[CONTAINER_IMAGE_CARDS]))
        self.assertEqual((summary["packaged"], summary["platform_images"]), (4, 5))
        payload, bodies = next(row for row in built if row[0]["repository"]["resolved_tag"] == "2.4.1")
        self.assertEqual((payload["line"], payload["kind"], payload["component_form"]["form"]),
                         (CONTAINER_IMAGE_CARDS, "contract_schema", "schema"))
        origins = {row["path"]: (row["origin"], row["role"]) for row in payload["files"]}
        self.assertEqual(origins["UPSTREAM-LICENSE"], ("licence_text", "other"))
        self.assertEqual(origins["image_contract.py"], ("generated", "executable_tool"))
        self.assertEqual(payload["declared_effects"], ["reads_fs", "spawns_process"])
        roles = [fact["role"] for fact in payload["provenance"]["facts"]]
        self.assertEqual(roles[:3], ["licence_text", "licence_evidence", "data_source"])
        self.assertEqual(roles.count("registry_entry"), 5)
        self.assertEqual(payload["tests"]["smoke"], "not_run")
        self.assertIn(payload["provenance"]["facts"][-1]["sha256"], facts)
        # The secret-shaped value is withheld; its name stays in the card.
        other = next(row for row in built if row[0]["repository"]["resolved_tag"] == "3.0")
        texts = b"".join(other[1].values()).decode("utf-8", "replace")
        self.assertNotIn(SECRET_VALUE, texts)
        self.assertIn("OTHER_HINT", texts)
        # An address carrying a user and a password is a credential too: withheld, its name kept.
        self.assertNotIn("index-pass-7Kq", texts)
        card = {entry["path"]: other[1][entry["digest"]] for entry in other[0]["package"]["files"]}
        self.assertIn(b"OTHER_INDEX", card["contract.json"])
        self.assertIn(b"OTHER_INDEX", card["README.md"])

    def test_known_wrong_tampered_bytes_and_the_request_ceiling_are_refused_by_name(self):
        source = hub()
        source.tampered.add(source.tags[("demo", "1.9.9")])
        _built, refusals, _facts, _summary = self.generate(source)
        self.assertIn(("document_digest_mismatch", "demo:1.9.9"), {(row["reason"], row["subject"]) for row in refusals})
        built, refusals, _facts, _summary = self.generate(hub(), reader={"maximum_requests": 12})
        reasons = {row["reason"] for row in refusals}
        self.assertIn(line.REQUEST_CEILING, reasons)
        self.assertTrue(set(line.UNREAD_REASONS) & reasons)

    def test_missing_stale_and_failed_evidence_and_a_failed_smoke_run_are_refused_by_name(self):
        source = hub()
        registry = reader(source, self.root / "registry")
        families, _refusals = line.read_families(collection(), registry, line.secret_patterns())
        prepared = line.prepare(families, collection(), MIT)
        evidence = line.registry_evidence(prepared, registry)
        identities = sorted(prepared)
        evidence.pop(identities[0])
        evidence[identities[1]] = native.evidence_bytes(dict(json.loads(evidence[identities[1]]), card_digest="0" * 64))
        failed = json.loads(evidence[identities[2]])
        failed["checks"][0]["passed"], failed["state"] = False, native.FAILED
        evidence[identities[2]] = native.evidence_bytes(failed)
        smoke = {identities[3]: json.dumps({"state": "failed", "checks": []}).encode()}
        built, refusals = line.package(prepared, evidence, smoke, collection(), code_revision=REVISION,
                                       generated_on="2026-10-09", staging=self.root / "staging", workers=2)
        self.assertEqual(built, [])
        self.assertEqual(sorted(row["reason"] for row in refusals),
                         ["native_check_failed", "native_evidence_missing", "native_evidence_stale",
                          "smoke_check_failed"])

    def test_every_static_check_passes_on_the_stored_bytes_and_one_family_is_one_job(self):
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
        keys = [checks.job_key(component, context.policy) for component in population]
        self.assertEqual(len(set(keys)), len(keys))
        self.assertTrue(all(key.split("|")[0] == CONTAINER_IMAGE_CARDS for key in keys))
        # Known wrong: a second card of one family is the same job, whatever its bytes.
        twin = population[0].replaced(identity=population[0].identity[:-16] + "0" * 16,
                                      payloads={**population[0].payloads, "README.md": b"# other bytes\n"})
        duplicates = checks.duplicate_findings(population + [twin], context.policy)
        self.assertTrue(any(code == "same_job_as" for row in duplicates.values() for code, _detail in row))

    @unittest.skipUnless(HAS_SANDBOX, "bubblewrap and the system interpreter are needed for the sandbox checks")
    def test_sandbox_and_mutation_pass_and_a_test_that_cannot_fail_is_refused(self):
        built, _refusals, _facts, _summary = self.generate()
        component = self.component(next(row for row in built if row[0]["repository"]["resolved_tag"] == "2.4.1"))
        context = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work")
        by_id = {check.check_id: check for check in checks.CHECKS}
        self.assertEqual(by_id["sandbox"].run(component, context).status, checks.PASSED)
        self.assertEqual(by_id["mutation"].run(component, context).status, checks.PASSED)
        weak = component.replaced(payloads={**component.payloads, cards.TEST_NAME: (
            b"import unittest\nimport image_contract\n\n\nclass T(unittest.TestCase):\n    def test_nothing(self):\n"
            b"        self.assertTrue(True)\n")})
        self.assertEqual(by_id["mutation"].run(weak, context).status, checks.REFUSED)


class CommandTests(unittest.TestCase):
    def test_the_builder_has_the_command_and_its_paths_are_generator_paths(self):
        import build_library_supply
        options = build_library_supply.parser().parse_args(
            ["container-image-cards", "--run-folder", "/tmp/x", "--authorize-network-reads", "--repository", "nginx",
             "--smoke", "hello-world:linux", "--registry-workers", "4"])
        self.assertEqual((options.registry, options.repository, options.smoke, options.registry_workers),
                         ("docker_hub", ["nginx"], ["hello-world:linux"], 4))
        self.assertIn("tools/container_image_cards", build_library_supply.GENERATOR_PATHS)

    def test_the_policy_names_the_line_and_its_job_key(self):
        policy = json.loads((ROOT / "tools/component_qualification/resources/qualification-policy.json").read_text())
        entry = policy["lines"][CONTAINER_IMAGE_CARDS]
        self.assertEqual(entry["job_key"]["fields"], ["job.registry", "job.repository", "job.family"])
        self.assertIn("verification/registry.json", entry["required_files"])


if __name__ == "__main__":
    unittest.main()
