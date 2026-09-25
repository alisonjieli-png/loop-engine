"""Bounded checks for imported licensed packages; a package with code is held until its own tests run in a sandbox.

The safety, effect, secret and duplicate checks are the original-package checks, applied to the imported request.
The licence and format checks are this profile's own: an imported package keeps its upstream layout, so the original
profile's placement rules do not apply, and its licence is the panel's accepted list with the licence text and the
attribution inside the package. Nothing here approves anything; a finding only refuses before any reviewer is asked.
"""
from __future__ import annotations

import json
from pathlib import PurePosixPath

import yaml

from loop_engine.core.service_runtime.catalogue_packages import EXECUTABLE_ROLES, FILE_ROLES

from .imported import IMPORTED_PROFILE, ImportedPackageReviewRequest
from .native import json_document
from .native_prechecks import (
    NativeCheck,
    NativeDuplicateRules,
    NativeEffectsRules,
    NativeMinHashRules,
    NativeSafetyRules,
    NativeSecretRules,
)
from .prechecks import result_of
from .records import CandidateReviewError

#: The file role of a skill's entry file, from the package vocabulary; a package holding an executable role waits
#: for the Community tier's rule that code passes its own tests.
SKILL_DEFINITION_ROLE = FILE_ROLES[FILE_ROLES.index("skill_definition")]
JSON_MEDIA = frozenset({"application/json", "application/schema+json"})
YAML_MEDIA = frozenset({"application/yaml", "text/yaml"})


class ImportedCheck(NativeCheck):
    def check(self, request, context):
        if not isinstance(request, ImportedPackageReviewRequest) or request.review_profile != IMPORTED_PROFILE:
            findings = [("imported_review_profile_mismatch", "an imported check requires the versioned imported request")]
        else:
            findings = self.findings(request, context)
        return result_of(self.kind, self.engine_id, self.version, findings)


def _licence(request):
    return json.loads(request.specification_json)["provenance"]["license"]


class ImportedLicenceRules(ImportedCheck):
    kind, engine_id = "licence", "imported_licence_rules"

    def findings(self, request, context):
        licence = request.item["reference"]["license"]
        if licence not in self.policy.accepted_licences:
            return [("imported_licence_not_accepted", "the package licence is not on the panel's accepted list")]
        declared = _licence(request)
        texts = {file.entry.path: file.text for file in request.files}
        if any(not (texts.get(path) or "").strip() for path in (*declared["texts"], declared["attribution"])):
            return [("imported_licence_text_missing", "a licence text or the attribution is empty or not text")]
        return []


def _skill_header(file):
    """A skill entry file opens with a YAML mapping that names the skill and describes it."""
    parts = (file.text or "").split("---", 2)
    if len(parts) != 3 or parts[0].strip() or not parts[2].strip():
        return [("imported_skill_header_invalid", "a skill entry needs YAML metadata and a body")]
    try:
        header = yaml.safe_load(parts[1])
    except (yaml.YAMLError, RecursionError):
        return [("imported_skill_header_invalid", "skill metadata must parse as YAML")]
    if (type(header) is not dict or type(header.get("name")) is not str or not header["name"].strip()
            or type(header.get("description")) is not str or not header["description"].strip()):
        return [("imported_skill_header_invalid", "skill metadata names the skill and describes it")]
    return []


class ImportedFormatRules(ImportedCheck):
    kind, engine_id = "format", "imported_format_rules"

    def findings(self, request, context):
        findings = []
        declared = _licence(request)
        licence_files = {*declared["texts"], declared["attribution"]}
        content = 0
        for file in request.files:
            role, media, text = file.entry.role, file.entry.media_type, file.text
            if role in EXECUTABLE_ROLES:
                findings.append(("imported_code_tests_missing", "a package with code waits for its own tests in a sandbox"))
                continue
            if text is None:
                findings.append(("imported_binary_verification_missing",
                                 "binary material needs an independent asset verification profile"))
                continue
            if not text.strip():
                findings.append(("imported_file_empty", f"{file.entry.path}: a delivered file is empty"))
                continue
            if file.entry.path not in licence_files:
                content += 1
            if media in JSON_MEDIA:
                try:
                    json_document(file.payload)
                except CandidateReviewError:
                    findings.append(("imported_json_invalid", f"{file.entry.path}: a JSON file must be strict JSON"))
            elif media in YAML_MEDIA:
                try:
                    yaml.safe_load(text)
                except (yaml.YAMLError, RecursionError):
                    findings.append(("imported_yaml_invalid", f"{file.entry.path}: a YAML file must parse"))
            if role == SKILL_DEFINITION_ROLE:
                if PurePosixPath(file.entry.path).name != "SKILL.md":
                    findings.append(("imported_skill_header_invalid", "a skill definition uses its entry filename"))
                findings.extend(_skill_header(file))
        if not content:
            findings.append(("imported_content_missing", "the package holds nothing beyond its licence and attribution"))
        return findings


class ImportedSafetyRules(ImportedCheck, NativeSafetyRules):
    kind, engine_id = "safety", "imported_safety_rules"


class ImportedEffectsRules(ImportedCheck, NativeEffectsRules):
    kind, engine_id = "effects", "imported_effects_rules"


class ImportedSecretRules(ImportedCheck, NativeSecretRules):
    kind, engine_id = "secrets", "imported_secret_rules"


class ImportedDuplicateRules(ImportedCheck, NativeDuplicateRules):
    kind, engine_id = "duplicates", "imported_duplicate_rules"


class ImportedMinHashRules(ImportedCheck, NativeMinHashRules):
    engine_id = "imported_minhash_rules"
