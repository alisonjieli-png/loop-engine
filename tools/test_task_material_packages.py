"""Offline exact-file intake and real local solve-use checks; no provider call."""
from __future__ import annotations

import hashlib
import json
import os
import io
import contextlib
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.core.task_material_packages import (
    MaterialPackageError, load_material_package, load_material_packages)
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile
from loop_engine.core.adaptive_practitioner_records import AdaptivePractitionerRequest
from loop_engine.core.adaptive_practitioner_source import (
    inventory_source_files, read_inventory_source, source_inspection_operation)
from loop_engine.core.adaptive_practitioner_project import _local_project_inputs
from loop_engine.core.source_profile import source_profile_operation
from loop_engine.core.practitioner_runtime_facts import granted_permissions
from loop_engine.code_nodes.solve_runtime import SolveRequest, solve_task
from loop_engine.templates.intake import TaskIntake


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stage(root, *, body_form="package", revision=1):
    root.mkdir()
    values = {"SKILL.md": (b"---\nname: exact-reference\ndescription: Read the selected values.\n---\nUse the reference table as data.\n", "skill_definition", "text/markdown"),
              "references/table.json": (json.dumps({"unit_scale": 7 * revision, "values": [2, 5]}).encode(), "skill_reference", "application/json"),
              "scripts/never.py": (b"raise RuntimeError('UNSELECTED_SCRIPT_SENTINEL')\n", "skill_script", "text/x-python"),
              "assets/pattern.bin": (b"\x00\xff\x01", "skill_asset", "application/octet-stream"),
              "AGENTS.md": (b"UNSELECTED_INSTRUCTION_SENTINEL\n", "instruction_file", "text/markdown")}
    if body_form == "file":
        values = {"SKILL.md": values["SKILL.md"]}
    entries = tuple(CataloguePackageFile(path, sha(body), len(body), media, role)
                    for path, (body, role, media) in values.items())
    package = CataloguePackage(entries, body_form)
    for path, (body, _role, _media) in values.items():
        destination = root / "payload" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(body)
    body = next(iter(values.values()))[0] if body_form == "file" else package.document()
    (root / "body").write_bytes(body)
    record = {"record_type": "baltor_library_fetch_receipt/v2", "client_version": "0.4.1",
              "identity": "synthetic_reference", "selected_digest": package.served_digest,
              "complete": True, "installed": False, "executed": False,
              "files": [row.to_dict() for row in package.files]}
    (root / "receipt.json").write_text(json.dumps(record))
    return values, record


class MaterialIntakeChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="native-material-check-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.stage = self.root / "selected"
        self.bodies, self.record = stage(self.stage)

    def rewrite(self, **changes):
        self.record.update(changes)
        (self.stage / "receipt.json").write_text(json.dumps(self.record))

    def services(self, material=None):
        material = material or load_material_package(str(self.stage))
        request = AdaptivePractitionerRequest("Read a selected local reference.",
            material_packages=(material,), allow_source_materialization_to_model=True,
            allow_network_reads=False, allow_workspace_writes=False, allow_sandbox_commands=False)
        return SimpleNamespace(request=request, source_inspections=[])

    def test_exact_native_members_enter_metadata_before_bodies(self):
        material = load_material_package(str(self.stage))
        service = self.services(material)
        result = source_inspection_operation({}, service)
        self.assertEqual(result["source_count"], 4)
        self.assertEqual(len(result["sandbox_input_files"]), 1)
        self.assertEqual(result["selected"], [])
        self.assertNotIn("UNSELECTED_INSTRUCTION_SENTINEL", json.dumps(result))
        name = material.namespace + "/SKILL.md"
        selected = source_inspection_operation({"paths": [name], "include_contents": True}, service)["selected"][0]
        self.assertEqual(selected["content"].encode(), self.bodies["SKILL.md"][0])
        self.assertEqual(selected["package_file_path"], "SKILL.md")
        self.assertEqual(selected["package_digest"], self.record["selected_digest"])
        self.assertFalse(selected["runtime_admission"])
        self.assertEqual(granted_permissions(service.request), ("source_read",))

    def test_single_file_native_package_is_supported(self):
        single = self.root / "single"
        stage(single, body_form="file")
        material = load_material_package(str(single))
        self.assertEqual(material.package.body_form, "file")
        self.assertEqual(material.selected_digest, sha((single / "payload/SKILL.md").read_bytes()))

    def test_wrong_payload_digest_refuses(self):
        (self.stage / "payload/SKILL.md").write_bytes(b"modified")
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))

    def test_wrong_selected_digest_refuses(self):
        self.rewrite(selected_digest="0" * 64)
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))

    def test_served_manifest_mutation_refuses(self):
        (self.stage / "body").write_bytes(b"{}")
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))

    def test_missing_member_refuses_complete_claim(self):
        (self.stage / "payload/AGENTS.md").unlink()
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))

    def test_unlisted_file_is_not_discovered(self):
        (self.stage / "payload/unlisted.md").write_text("not selected")
        result = source_inspection_operation({}, self.services())
        self.assertFalse(any(row["path"].endswith("unlisted.md") for row in result["source_manifest"]))

    def test_symlink_member_refuses(self):
        member = self.stage / "payload/AGENTS.md"
        member.unlink()
        target = self.root / "outside.md"
        target.write_bytes(self.bodies["AGENTS.md"][0])
        member.symlink_to(target)
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))

    def test_symlink_ancestor_refuses(self):
        link = self.root / "alias"
        link.symlink_to(self.stage, target_is_directory=True)
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(link))

    def test_symlink_swap_after_binding_cannot_reenter_source_reads(self):
        service = self.services()
        inventory = inventory_source_files(service)
        member = self.stage / "payload/SKILL.md"
        target = self.root / "same-bytes.md"
        target.write_bytes(member.read_bytes())
        member.unlink()
        member.symlink_to(target)
        name = service.request.material_packages[0].namespace + "/SKILL.md"
        with self.assertRaises(MaterialPackageError):
            read_inventory_source(inventory, name)

    def test_unavailable_descriptor_confinement_refuses_before_read(self):
        with patch("loop_engine.core.task_material_packages.os.supports_dir_fd", set()), \
                patch("loop_engine.core.adaptive_practitioner_source._read_source_bytes") as reader:
            with self.assertRaisesRegex(MaterialPackageError, "material_confined_read_unavailable"):
                load_material_package(str(self.stage))
            reader.assert_not_called()

    def test_deployed_wire_spelling_allowance_is_source_scoped(self):
        from loop_engine.nomenclature_conformance import retired_nomenclature_violations
        source_root = Path(__file__).resolve().parents[1] / "src/loop_engine"
        policy = json.loads((source_root / "forbidden_paths.json").read_text())["retired_source_nomenclature"]
        fragments = policy["allowed_fragments"]["core/task_material_packages.py"]
        self.assertEqual(fragments, ['_FETCH_RECORD = "baltor_library_fetch_receipt/v2"',
                                    'raw = _read(path / "receipt.json", MAXIMUM_FETCH_RECORD_BYTES)'])
        fixture = self.root / "nomenclature"
        (fixture / "core").mkdir(parents=True)
        owning = fixture / "core/task_material_packages.py"
        owning.write_text("\n".join(fragments) + "\n")
        self.assertEqual(retired_nomenclature_violations(str(fixture), policy), [])
        owning.write_text(owning.read_text() + 'description = "The receipt is complete."\n')
        wrong = fixture / "core/another_reader.py"
        wrong.write_text("\n".join(fragments) + "\n")
        findings = retired_nomenclature_violations(str(fixture), policy)
        self.assertEqual(len(findings), 3)
        self.assertEqual({row["file"] for row in findings},
                         {"core/task_material_packages.py", "core/another_reader.py"})

    def test_traversal_and_unsupported_version_refuse(self):
        for changes in ({"record_type": "baltor_library_fetch_receipt/v1"},
                        {"complete": False}, {"complete": 1}, {"executed": True}):
            with self.subTest(changes=changes):
                original = dict(self.record)
                self.rewrite(**changes)
                with self.assertRaises(MaterialPackageError):
                    load_material_package(str(self.stage))
                self.record = original
                self.rewrite()
        self.record["files"][0]["path"] = "../escape"
        self.rewrite()
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))

    def test_duplicate_json_and_bool_size_refuse(self):
        raw = (self.stage / "receipt.json").read_bytes()
        (self.stage / "receipt.json").write_bytes(raw[:-1] + b',"complete":true}')
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))
        self.record["files"][0]["size_bytes"] = True
        self.rewrite()
        with self.assertRaises(MaterialPackageError):
            load_material_package(str(self.stage))

    def test_no_source_authority_no_request_or_source_read(self):
        material = load_material_package(str(self.stage))
        for authority in (False, 0, 1, "true"):
            with self.assertRaises(ValueError):
                SolveRequest(TaskIntake("text", "goal"), material_packages=(material,),
                             allow_source_materialization_to_model=authority)
            with self.assertRaises(ValueError):
                AdaptivePractitionerRequest("goal", material_packages=(material,),
                                            allow_source_materialization_to_model=authority)
        service = self.services(material)
        service.request = SimpleNamespace(allow_source_materialization_to_model=False)
        with patch("loop_engine.core.adaptive_practitioner_source._open_source") as opened:
            with self.assertRaises(PermissionError):
                inventory_source_files(service)
            opened.assert_not_called()

    def test_cli_requires_solve_and_authority_before_package_read(self):
        from loop_engine.__main__ import main
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch("loop_engine.core.task_material_packages.load_material_packages") as loader:
            with self.assertRaises(SystemExit) as refused:
                main(["task", "compile", "--text", "goal", "--material-package", str(self.stage)])
            self.assertEqual(refused.exception.code, 2)
            self.assertNotEqual(main(["solve", "--text", "goal", "--material-package", str(self.stage)]), 0)
            loader.assert_not_called()

    def test_package_only_source_roles_do_not_sample_unselected_files(self):
        from loop_engine.core.source_role_orientation import orient_source_roles
        service = self.services()
        with patch("loop_engine.core.source_role_orientation._evidence_rows") as evidence:
            self.assertIsNone(orient_source_roles(service))
            evidence.assert_not_called()

    def test_combined_task_sources_do_not_auto_sample_package_bodies(self):
        from loop_engine.core.source_role_orientation import orient_source_roles
        service = self.services()
        data = self.root / "task.txt"
        data.write_text("ordinary task data")
        service.request = replace(service.request, source_kind="dataset", source_refs=(str(data),))
        seen = []
        def evidence(_service, admitted, _allowance):
            seen.extend(admitted)
            raise ValueError("test stops before any fixture model call")
        with patch("loop_engine.core.source_role_orientation._evidence_rows", evidence):
            self.assertIsNone(orient_source_roles(service))
        self.assertEqual(seen, ["task.txt"])

    def test_selected_optional_package_does_not_replace_required_task_data_selection(self):
        service = self.services()
        data = self.root / "task.txt"
        data.write_text("ordinary task data")
        service.request = replace(service.request, source_kind="dataset", source_refs=(str(data),))
        name = service.request.material_packages[0].namespace + "/SKILL.md"
        service.source_inspections.append(source_inspection_operation({"paths": [name]}, service))
        with self.assertRaisesRegex(ValueError, "local sources were supplied"):
            _local_project_inputs(service)
        service.source_inspections.append(source_inspection_operation({"paths": ["task.txt"]}, service))
        self.assertEqual(len(_local_project_inputs(service)), 2)

    def test_changed_after_intake_and_between_inventory_read_refuses(self):
        service = self.services()
        inventory = inventory_source_files(service)
        name = service.request.material_packages[0].namespace + "/SKILL.md"
        (self.stage / "payload/SKILL.md").write_bytes(b"changed")
        with self.assertRaises(MaterialPackageError):
            read_inventory_source(inventory, name)
        after = inventory_source_files(service)
        self.assertNotIn(name, dict(after.files))
        self.assertNotIn(name, dict(after.materializable))
        self.assertTrue(any(row.path == name and row.reason == "material_binding_changed" for row in after.records))

    def test_binary_selected_as_input_never_text_and_no_auto_use(self):
        service = self.services()
        self.assertEqual(_local_project_inputs(service), ())
        name = service.request.material_packages[0].namespace + "/assets/pattern.bin"
        result = source_inspection_operation({"paths": [name], "include_contents": True}, service)
        self.assertNotIn("content", result["selected"][0])
        self.assertFalse(result["selected"][0]["readable_by_model"])
        service.source_inspections.append(result)
        inputs = _local_project_inputs(service)
        self.assertEqual(inputs[0].content, self.bodies["assets/pattern.bin"][0])
        self.assertEqual(inputs[0].path, "inputs/" + name)
        (self.stage / "payload/assets/pattern.bin").write_bytes(b"\x00\xff\x03")
        with self.assertRaises(ValueError):
            _local_project_inputs(service)

    def test_profile_preserves_binding_and_duplicate_selection_refuses(self):
        service = self.services()
        name = service.request.material_packages[0].namespace + "/references/table.json"
        profile = source_profile_operation({"paths": [name]}, service)["profiles"][0]
        self.assertEqual(profile["fields"], ["unit_scale", "values"])
        self.assertEqual(profile["file_role"], "skill_reference")
        with self.assertRaises(MaterialPackageError):
            load_material_packages([str(self.stage), str(self.stage)])

    def test_declared_byte_ceiling_stops_before_payload(self):
        with patch("loop_engine.core.task_material_packages.read_material_file") as opened:
            with self.assertRaises(MaterialPackageError):
                load_material_package(str(self.stage), byte_allowance=0)
            opened.assert_not_called()

    def test_revision_changes_namespace_without_rewriting_old_binding(self):
        first = load_material_package(str(self.stage))
        second_root = self.root / "revision"
        stage(second_root, revision=2)
        second = load_material_package(str(second_root))
        self.assertNotEqual(first.namespace, second.namespace)
        self.assertNotEqual(first.selected_digest, second.selected_digest)
        self.assertEqual(first.selected_digest, self.record["selected_digest"])

    def test_spawned_scope_does_not_inherit_parent_materials(self):
        from loop_engine.core.adaptive_practitioner_records import AdaptiveRunServices, AdaptivePractitionerDependencies
        from loop_engine.core.adaptive_practitioner_scope import fork_services
        from loop_engine.core.context_artifacts import (ContextArtifactManager, ContextArtifactServices,
                                                       ContextArtifactStore, ContextArtifactStoreSpec)
        from loop_engine.core.practitioner_context import load_practitioner_context
        from loop_engine.loop.kernel import ProblemSpec
        service = AdaptiveRunServices(self.services().request, AdaptivePractitionerDependencies(), "scope-test",
            self.root / "workspace", ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(
                ContextArtifactStoreSpec(str(self.root / "artifacts"))))), load_practitioner_context())
        child = fork_services(service, ProblemSpec("Separate assignment."))
        self.assertTrue(service.request.material_packages)
        self.assertEqual(child.request.material_packages, ())
        self.assertNotIn("source_read", granted_permissions(child.request))


class PublicSolveUseChecks(unittest.TestCase):
    setUp = MaterialIntakeChecks.setUp

    def test_public_solve_reads_selected_native_files_and_uses_exact_data(self):
        self._exercise_solve(49)

    def test_revised_package_drives_a_different_real_output(self):
        self.stage = self.root / "revision"
        self.bodies, self.record = stage(self.stage, revision=2)
        self._exercise_solve(98)

    def _exercise_solve(self, expected):
        from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
        from loop_engine.core.adaptive_practitioner_acceptance_checks import (
            _orientation, _decision, _decision_id, _action_vector)
        from loop_engine.core.source_role_orientation import manifest_digest
        from loop_engine.core.generated_project import DockerWorkspace
        from loop_engine.core.workspace_contracts import BackendAvailability
        from loop_engine.core.independent_verification import IndependentVerificationPolicy
        import loop_engine.code_nodes.solve_runtime as runtime

        material = load_material_package(str(self.stage))
        data_path = material.namespace + "/references/table.json"
        skill_path = material.namespace + "/SKILL.md"
        inspect = _decision("RESEARCH_SOURCE", required_capabilities=["core.source.inspect"],
                            permissions=["source_read"], goal="Read selected reference files.")
        build = _decision("BUILD_CAPABILITY", goal="Compute the total using the selected data.")
        how = lambda decision, capability, arguments: {
            "action_id": _decision_id(decision), "how_mode": "research" if capability.endswith("inspect") else "generate",
            "act_mode": "run_dag", "capability_ref": capability, "arguments": arguments,
            "steps": ["perform bounded selected work"], "spawned_tasks": [], "rationale": decision["goal"]}
        verified = {"verdict": "accept", "best_index": 0, "scores": [1.0], "notes": "Synthetic output checked.",
                    "remaining_gaps": [], "advisory_findings": [], "new_requirement_proposals": [],
                    "action_vector": _action_vector()}
        continue_check = {**verified, "verdict": "research_more",
            "remaining_gaps": [{"criterion_ref": "criterion:0", "gap": "compute the requested output"}],
            "action_vector": _action_vector(unresolved_refs=("criterion:0",), continuation_status="continue",
                                             remaining_work=("Compute the output.",))}
        source_roles = {"manifest_digest": manifest_digest((data_path, skill_path)), "files": [
            {"path": skill_path, "role": "advisory procedure", "observed_fields": [],
             "evidence": "asks to read a reference table", "confidence": 0.9},
            {"path": data_path, "role": "synthetic table values", "observed_fields": ["unit_scale", "values"],
             "evidence": "contains a scale and two values", "confidence": 0.9}], "unresolved": []}
        candidate = {"record_type": "generated_project_candidate/v1", "project_id": "native_reference_use",
            "summary": "Compute the scaled sum from the selected native data.",
            "files": [{"path": "main.py", "purpose": "Use selected input.", "acceptance": [f"Output is {expected}."]}],
            "commands": [{"argv": ["python", "main.py"], "purpose": "Compute sum.", "timeout_seconds": 10}],
            "expected_artifacts": [{"path": "output.txt", "media_type": "text/plain", "minimum_bytes": 1}]}
        code = ("import json\nfrom pathlib import Path\n"
                f"value = json.loads(Path({'inputs/' + data_path!r}).read_text())\n"
                "Path('output.txt').write_text(str(sum(value['values']) * value['unit_scale']) + '\\n')\n")
        answers = (_orientation(candidate_capabilities=["core.source.inspect", "core.generated_project"]),
            {"actions": [inspect]}, how(inspect, "core.source.inspect", {"paths": [skill_path, data_path], "include_contents": True}),
            source_roles, continue_check, {"route": "continue", "reason": "Use the inspected data."},
            _orientation(), {"actions": [build]}, how(build, "core.generated_project", {}), candidate,
            {"path": "main.py", "content": code}, verified, {"route": "stop_success", "reason": "Output computed."})
        execution = fixture_model_execution(FixtureModelExecutionRequest(
            answers=tuple(json.dumps(item) for item in answers), max_model_calls=len(answers),
            forbidden_prompt_fragments=("UNSELECTED_SCRIPT_SENTINEL", "UNSELECTED_INSTRUCTION_SENTINEL")))
        observed = []
        original = runtime.run_adaptive_practitioner
        def capture(*args):
            result = original(*args)
            observed.append(result)
            return result
        unavailable = BackendAvailability(False, "docker", "dependency_unavailable", "Offline fixture selects explicit host authority.")
        with patch.object(DockerWorkspace, "availability", return_value=unavailable), patch.object(runtime, "run_adaptive_practitioner", capture):
            result = solve_task(SolveRequest(TaskIntake("text", "Compute the scaled sum using the selected reference data and write output.txt."),
                model_execution=execution, material_packages=(material,), max_passes=2,
                runs_dir=str(self.root / "runs"), workspace_root=str(self.root / "work"),
                allow_source_materialization_to_model=True, allow_workspace_writes=True,
                allow_sandbox_commands=True, allow_local_execution=True, allow_network_reads=False,
                independent_verification_policy=IndependentVerificationPolicy(required=False)))
        self.assertEqual(result.status, "COMPLETED_VERIFIED", {
            key: observed[0].get(key) for key in ("failure", "diagnostics", "model_calls", "passes", "project_attempts")})
        self.assertEqual((Path(result.workspace) / "output.txt").read_text(), f"{expected}\n")
        selected = observed[0]["source_inspections"][0]["selected"]
        self.assertEqual({row["package_file_path"] for row in selected}, {"SKILL.md", "references/table.json"})
        self.assertEqual((Path(result.workspace) / "inputs" / data_path).read_bytes(), self.bodies["references/table.json"][0])
        self.assertFalse(any(Path(result.workspace).rglob("never.py")))
        self.assertEqual(result.model_calls, len(answers))
        return {"record_type": "native_material_input_qualification/v1",
                "terminal_code": result.status, "package_digest": material.selected_digest,
                "transfer_record_digest": material.transfer_record_digest,
                "selected_files": [{key: row[key] for key in (
                    "path", "digest", "byte_count", "package_file_path", "file_role")}
                    for row in selected],
                "output_bytes": (Path(result.workspace) / "output.txt").read_text(),
                "output_digest": sha((Path(result.workspace) / "output.txt").read_bytes()),
                "input_digest": sha((Path(result.workspace) / "inputs" / data_path).read_bytes()),
                "offline_scripted_gateway_calls": result.model_calls,
                "external_provider_calls": 0, "downloaded_script_executed": False,
                "unselected_bodies_absent_from_prompts": True,
                "execution_backend": "restricted_local",
                "operating_system_sandbox": False,
                "qualification": "mechanism_only_not_model_quality_or_field_benefit"}


if __name__ == "__main__":
    unittest.main()
