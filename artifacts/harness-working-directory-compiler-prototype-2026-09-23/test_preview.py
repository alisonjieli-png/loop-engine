"""Known-wrong checks first; all bytes and workspace observations are synthetic."""
import builtins
from dataclasses import replace
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from tools.install_selected_material import OPENCODE_PROFILE, native_name
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile
from preview import (Authority, BaltorPreviewEngine, DraftPackageProfile, ExistingState,
                     PackageInput, PreviewRefusal, PreviewRequest, UnavailableAgentHarnessEngine, revalidate)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def package(identity="sample", files=None, effects=()):
    files = files or [("SKILL.md", b"---\nname: sample\ndescription: fixture\n---\n", "text/markdown", "skill_definition"),
                      ("assets/data.bin", b"\x00\xff\x80\r\n", "application/octet-stream", "skill_asset")]
    body = CataloguePackage(tuple(CataloguePackageFile(p, sha(b), len(b), media, role) for p,b,media,role in files))
    return PackageInput(identity, "skill", body, tuple((p,b) for p,b,_m,_r in files), tuple(effects))


def request(*packages, supported=("skill_definition", "skill_asset")):
    packages = packages or (package(),)
    profile = DraftPackageProfile(OPENCODE_PROFILE, tuple(supported))
    state = tuple(ExistingState(".opencode/skills/"+native_name(p.identity)+"/"+f.path,"absent")
                  for p in packages for f in p.package.files)
    # Deduplicate identical observations; collision in desired output remains a compiler check.
    states = {entry.path:entry for entry in state}
    for entry in state:
        parts=entry.path.split("/")
        for count in range(1,len(parts)):
            parent="/".join(parts[:count]); states.setdefault(parent,ExistingState(parent,"directory"))
    state = tuple(states.values())
    return PreviewRequest(profile, tuple(packages), Authority(("writes_fs",), ()), state, state)


class PreviewTests(unittest.TestCase):
    def check_refusal(self, selected, code):
        result = BaltorPreviewEngine().compile(selected)
        self.assertEqual(result.status, "refused")
        self.assertEqual(result.refusal, code)
        self.assertEqual(result.files, ())

    def test_opaque_bytes_and_complete_tree_preserved(self):
        selected=request(); result=BaltorPreviewEngine().compile(selected)
        self.assertEqual(result.status,"compiled")
        self.assertFalse(result.native_qualified)
        self.assertFalse(result.writes_performed)
        self.assertEqual(len(result.files),len(selected.packages[0].package.files))
        for file in result.files:
            original=dict(selected.packages[0].payloads)[file.source_path]
            self.assertEqual(file.payload,original)
            self.assertEqual(file.digest,sha(original))
            self.assertEqual(file.role,selected.packages[0].package.file(file.source_path).role)

    def test_unsupported_mandatory_role_refuses(self):
        self.check_refusal(request(supported=("skill_definition",)),"unsupported_mandatory_role")

    def test_two_packages_claim_same_target_refuses(self):
        a=package("sample_one"); b=package("sample.one",files=[("SKILL.md",b"different", "text/markdown","skill_definition")])
        self.check_refusal(request(a,b),"target_collision")

    def test_parent_file_collision_refuses(self):
        selected=package(files=[("SKILL.md",b"fixture","text/markdown","skill_definition"),
            ("assets",b"file","text/plain","skill_asset"),("assets/data.bin",b"child","application/octet-stream","skill_asset")])
        self.check_refusal(request(selected),"parent_file_collision")

    def test_same_size_payload_change_refuses(self):
        selected=request(); item=selected.packages[0]
        modified=tuple((p,(b"\x00\x00\x80\r\n" if p.endswith(".bin") else b)) for p,b in item.payloads)
        self.check_refusal(replace(selected,packages=(replace(item,payloads=modified),)),"package_bytes_mismatch")

    def test_missing_or_extra_file_refuses(self):
        selected=request(); item=selected.packages[0]
        for payloads in (item.payloads[:-1],item.payloads+(("unlisted.txt",b"extra"),)):
            with self.subTest(payloads=len(payloads)):
                self.check_refusal(replace(selected,packages=(replace(item,payloads=payloads),)),"package_inventory_mismatch")

    def test_stale_expected_current_refuses(self):
        selected=request(); changed=(ExistingState(selected.expected[0].path,"file",sha(b"new"),True),)+selected.observed[1:]
        self.check_refusal(replace(selected,observed=changed),"stale_workspace_state")

    def test_unowned_file_and_symlink_parent_refuse(self):
        selected=request(); path=selected.expected[0].path
        state=(ExistingState(path,"file",sha(b"old"),False),)+selected.expected[1:]
        self.check_refusal(replace(selected,expected=state,observed=state),"foreign_file_collision")
        state=tuple(ExistingState(e.path,"symlink") if e.path==".opencode" else e for e in selected.expected)
        self.check_refusal(replace(selected,expected=state,observed=state),"unsafe_parent_state")

    def test_worker_effects_cannot_expand(self):
        selected=request(package(effects=("network",)))
        self.check_refusal(selected,"worker_authority_exceeded")

    def test_preview_can_be_inspected_without_installation_write_authority(self):
        result=BaltorPreviewEngine().compile(replace(request(),authority=Authority((),("writes_fs",))))
        self.assertEqual(result.status,"compiled")
        self.assertEqual(result.required_installation_effects,("writes_fs",))
        self.assertFalse(result.installation_authorized)
        self.assertFalse(result.writes_performed)

    def test_external_engine_is_unavailable(self):
        result=UnavailableAgentHarnessEngine().compile(request())
        self.assertEqual(result.refusal,"engine_unavailable")
        self.assertEqual(result.files,())

    def test_executable_package_cannot_omit_process_declaration(self):
        with self.assertRaises(PreviewRefusal) as caught:
            package(files=[("SKILL.md",b"fixture","text/markdown","skill_definition"),
                           ("scripts/tool.py",b"print(1)\n","text/x-python","executable_tool")])
        self.assertEqual(caught.exception.code,"package_executable_effect_missing")

    def test_projected_path_over_package_bound_is_typed_refusal(self):
        item=package(files=[("SKILL.md",b"fixture","text/markdown","skill_definition"),
            ("a/b/c/d/e/f/g/blob",b"asset","application/octet-stream","skill_asset")])
        selected=PreviewRequest(DraftPackageProfile(OPENCODE_PROFILE,("skill_definition","skill_asset")),
            (item,),Authority(("writes_fs",),()),(),())
        self.check_refusal(selected,"projected_path_invalid")

    def test_unknown_parent_observation_refuses(self):
        selected=request(); state=tuple(s for s in selected.expected if s.path!=".opencode")
        self.check_refusal(replace(selected,expected=state,observed=state),"workspace_observation_missing")

    def test_compilation_uses_no_filesystem_or_process(self):
        selected=request()
        with patch.object(builtins,"open",side_effect=AssertionError("unexpected filesystem")), \
                patch("os.open",side_effect=AssertionError("unexpected filesystem")), \
                patch("subprocess.run",side_effect=AssertionError("unexpected process")):
            self.assertEqual(BaltorPreviewEngine().compile(selected).status,"compiled")

    def test_revalidation_refuses_changes_after_preview(self):
        selected=request(); plan=BaltorPreviewEngine().compile(selected)
        self.assertEqual(revalidate(plan,selected.observed),"")
        changed=(ExistingState(selected.observed[0].path,"file",sha(b"different"),True),)+selected.observed[1:]
        self.assertEqual(revalidate(plan,changed),"stale_workspace_state")


if __name__ == "__main__":
    unittest.main()
