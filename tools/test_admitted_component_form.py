"""A qualified component keeps its declared form even when its native format is Python."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]
from tools.candidate_review.native import NativeReviewFile
from tools.component_qualification import controls
from tools.component_qualification import decisions, qualified_admission
from tools.component_qualification.admission import reference_for
from tools.write_reviewed_catalogue import item_attributes
from loop_engine.core.service_runtime.catalogue_attributes import ComponentFormError


class AdmittedFormTests(unittest.TestCase):
    def setUp(self):
        self.component = controls.code_fixture("c" * 40)
        self.reference = reference_for(self.component)
        self.reference["styles"] = ["code_module", "python"]
        self.files = tuple(NativeReviewFile(file, self.component.payloads[file.path]) for file in self.component.package.files)

    def attributes(self, form=None):
        spec = {"title": "Synthetic callable", "provenance": {"harness_kind": "code_module"}}
        if form is not None:
            spec["component_form"] = form
        return item_attributes(self.reference, spec, self.component.package, self.files, is_import=True)[0]

    def test_declared_form_wins_over_language_format(self):
        for form in ("function", "api_operation", "program", "library_module"):
            self.assertEqual(self.attributes(form)["component_form"], form)
        self.assertEqual(self.attributes()["component_form"], "library_module")
        self.assertNotEqual(self.attributes()["component_form"], "api_operation")

    def test_unknown_and_kind_conflicting_forms_refuse(self):
        for form in ("invented", "skill_with_code", {"form": "api_operation"}):
            with self.assertRaises(ComponentFormError):
                self.attributes(form)

    def test_qualified_admission_carries_the_form_into_the_served_attributes(self):
        component = controls.api_fixture("c" * 40)
        component = component.replaced(candidate={**component.candidate, "native_format":"python"})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            qualification = root / "qualification"
            qualification.mkdir()
            record = {"identity":component.identity,"outcome":"qualified", "line":component.line,
                      "record_version":component.record_version,"batch":component.batch,
                      "package_digest":component.package.package_digest,"vetting":{"implementation_tested":"fixture"},
                      "qualifier":{"tool":"tools/component_qualification","version":"1.0.0",
                                   "code_revision":"c"*40,"uncommitted_changes":False},
                      "self_test_sha256":"0"*64,"checks":[]}
            (qualification / "qualification.jsonl").write_text(json.dumps(record) + "\n")
            ledger = root / "decisions.jsonl"
            decisions.create(ledger, created_at="2026-10-06T00:00:00Z", created_by="fixture")
            held = root / "held.json"
            held.write_text(json.dumps({"record_type":qualified_admission.HELD_RECORD,"held":[]}))
            target = root / "admitted"
            qualified_admission.admit_qualified(qualification,None,ledger,held,target,"2026-10-06",ROOT,
                                                components={component.identity:component})
            item = json.loads((target/"items.json").read_text())["items"][0]
            self.assertEqual(item["attributes"]["component_form"], "api_operation")
            self.assertEqual(item["provenance"]["component_form"], "api_operation")
            self.assertEqual(item["reference"]["digest"], component.package.served_digest)


if __name__ == "__main__":
    unittest.main()
