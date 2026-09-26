"""Bounded checks for imported licensed packages, with two routes for a package that holds code.

The safety, effect, secret and duplicate checks are the original-package checks, applied to the imported request.
The licence and format checks are this profile's own: an imported package keeps its upstream layout, so the original
profile's placement rules do not apply, and its licence is the panel's accepted list with the licence text and the
attribution inside the package. Nothing here approves anything; a finding only refuses before any reviewer is asked.

```text
A package with code (a skill script, a hook or an executable tool)
├── reviewer_reads_code (imported_format_rules_code_read, the Community route since September 26, 2026)
│   ├── every executable file is text the reviewer reads line by line, within the review bounds
│   ├── a Python file parses; a JSON hook file is strict JSON
│   ├── the effects rules still refuse an undeclared network, file or process effect
│   └── the reviewer answers the executable-code criterion of the written criteria
└── sandbox_tests (imported_format_rules, the rule until then and the route to Verified for code)
    └── the package waits until its own tests have run in a sandbox
```

The owner, September 26, 2026, asked for python scripts and "a large mix of everything that can be placed into a
harness working directory"; the sandbox route kept every package with a script out of the library, so the Community
tier reads the code instead and the sandbox stays the Verified route (roadmap S-6.205).
"""
from __future__ import annotations

import ast
import json
from pathlib import PurePosixPath

import yaml

from loop_engine.core.service_runtime.catalogue_packages import EXECUTABLE_ROLES, FILE_ROLES

#: The routes a package with code may take; each format engine names its own.
CODE_ROUTES = ("reviewer_reads_code", "sandbox_tests")
REVIEWER_READS_CODE, SANDBOX_TESTS = CODE_ROUTES
PYTHON_MEDIA = frozenset({"text/x-python", "application/x-python"})

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
    """The format rules with the sandbox route: a package with code waits for its own tests."""

    kind, engine_id = "format", "imported_format_rules"
    code_route = SANDBOX_TESTS

    def findings(self, request, context):
        findings = []
        declared = _licence(request)
        licence_files = {*declared["texts"], declared["attribution"]}
        content = 0
        for file in request.files:
            role, media, text = file.entry.role, file.entry.media_type, file.text
            if role in EXECUTABLE_ROLES and self.code_route == SANDBOX_TESTS:
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
            if media in PYTHON_MEDIA:
                try:
                    ast.parse(text)
                except (SyntaxError, ValueError, RecursionError):
                    findings.append(("imported_code_syntax_invalid", f"{file.entry.path}: a Python file must parse"))
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


class ImportedFormatRulesCodeRead(ImportedFormatRules):
    """The format rules with the reviewer route: code is text the reviewer reads, parsed where a parser exists."""

    engine_id = "imported_format_rules_code_read"
    code_route = REVIEWER_READS_CODE


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
