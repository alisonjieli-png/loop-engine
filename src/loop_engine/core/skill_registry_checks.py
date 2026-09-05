"""Offline contract and adversarial checks for Agent Skill discovery.

The checks use temporary local files and make no provider or model call.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from .runtime_observer import RuntimeObservationServices
from .skill_discovery_projection import projection_json as _projection_json
from .skill_registry import (
    _MINIMUM_SKILL_DISCOVERY_BYTES,
    AGENT_SKILLS_STRICT_POLICY,
    LOOP_ENGINE_LEGACY_FRONTMATTER_POLICY,
    SkillAdmissionRecord,
    SkillError,
    SkillLoadPurpose,
    SkillRegistry,
    _manifest,
)


def run_checks() -> dict:
    import tempfile

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="loop-engine-skills-") as root:
        from ..loop.recursive_loop import LoopLedger

        ledger = LoopLedger()
        runtime = RuntimeObservationServices(ledger=ledger)
        skill = Path(root) / "release-review"
        skill.mkdir()
        (skill / "references").mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: release-review\n"
            "description: Review release risk with typed checks.\n"
            "license: Apache-2.0\n"
            "compatibility: Requires git.\n"
            "metadata:\n"
            "  owner: test-team\n"
            "  loop-engine.version: '2.0.0'\n"
            "  loop-engine.title: Release review\n"
            "  loop-engine.tags: release,verification\n"
            "allowed-tools: Read Bash(git:*)\n"
            "---\n"
            "Read the release contract. Check every threshold.\n",
            encoding="utf-8",
        )
        (skill / "references" / "checks.md").write_text(
            "Threshold definitions.\n", encoding="utf-8"
        )
        registry = SkillRegistry()
        found = registry.discover((root,))
        check(
            "discovery_builds_a_small_candidate_manifest",
            len(found) == 1
            and found[0].lifecycle == "candidate"
            and len(found[0].files) == 2
            and found[0].license == "Apache-2.0"
            and found[0].compatibility == "Requires git."
            and dict(found[0].metadata)["owner"] == "test-team"
            and found[0].version == "2.0.0"
            and found[0].title == "Release review"
            and found[0].tags == ("release", "verification")
            and found[0].frontmatter_policy == AGENT_SKILLS_STRICT_POLICY
            and found[0].requested_tools == ("Read", "Bash(git:*)")
            and found[0].instruction_bytes > 0
            and found[0].instruction_lines == 1,
        )
        direct_registered_discovery_refused = False
        try:
            SkillRegistry().discover((root,), lifecycle="registered")
        except SkillError:
            direct_registered_discovery_refused = True
        check(
            "discovery_cannot_mark_a_skill_registered",
            direct_registered_discovery_refused,
        )
        direct_registered_manifest_refused = False
        try:
            SkillRegistry().register(replace(found[0], lifecycle="registered"))
        except SkillError:
            direct_registered_manifest_refused = True
        check(
            "registered_manifest_without_admission_is_refused",
            direct_registered_manifest_refused,
        )
        check(
            "candidate_skills_are_excluded_from_normal_search",
            not registry.search("release verification")
            and registry.search("release verification", include_candidates=True)[
                0
            ].skill_id
            == "release-review",
        )
        context = found[0].as_context_candidate()
        check(
            "an_imported_skill_is_candidate_context_not_executable_code",
            context.tier == "experimental"
            and context.body["context_type"] == "skill"
            and context.body["requested_tools_grant_authority"] is False,
        )
        projection = registry.discovery_projection(4096, include_candidates=True)
        projection_text = _projection_json(projection)
        check(
            "startup_projection_loads_cards_not_skill_bodies_or_tools",
            len(projection.cards) == 1
            and projection.omitted_candidates == 0
            and len(projection_text.encode("utf-8")) <= 4096
            and "Check every threshold" not in projection_text
            and "Bash(git:*)" not in projection_text
            and "references/checks.md" not in projection_text
            and projection.to_dict()["full_instructions_loaded"] is False,
        )
        bounded_projection = registry.discovery_projection(
            _MINIMUM_SKILL_DISCOVERY_BYTES, include_candidates=True
        )
        check(
            "startup_projection_omits_cards_that_do_not_fit",
            not bounded_projection.cards
            and bounded_projection.omitted_candidates == 1
            and len(_projection_json(bounded_projection).encode("utf-8"))
            <= _MINIMUM_SKILL_DISCOVERY_BYTES,
        )

        invalid_root = Path(root) / "invalid-skills"
        invalid_root.mkdir()
        mismatched = invalid_root / "wrong-directory"
        mismatched.mkdir()
        (mismatched / "SKILL.md").write_text(
            "---\nname: another-name\ndescription: Mismatched identity.\n---\nBody.\n",
            encoding="utf-8",
        )
        mismatch_refused = False
        try:
            _manifest(mismatched)
        except SkillError:
            mismatch_refused = True
        missing_frontmatter = invalid_root / "missing-frontmatter"
        missing_frontmatter.mkdir()
        (missing_frontmatter / "SKILL.md").write_text(
            "Instructions without metadata.\n", encoding="utf-8"
        )
        frontmatter_refused = False
        try:
            _manifest(missing_frontmatter)
        except SkillError:
            frontmatter_refused = True
        underscore = invalid_root / "bad_name"
        underscore.mkdir()
        (underscore / "SKILL.md").write_text(
            "---\nname: bad_name\ndescription: Invalid standard name.\n---\nBody.\n",
            encoding="utf-8",
        )
        underscore_refused = False
        try:
            _manifest(underscore)
        except SkillError:
            underscore_refused = True
        nonstring_description = invalid_root / "bad-description"
        nonstring_description.mkdir()
        (nonstring_description / "SKILL.md").write_text(
            "---\nname: bad-description\ndescription: [not, text]\n---\nBody.\n",
            encoding="utf-8",
        )
        description_refused = False
        try:
            _manifest(nonstring_description)
        except SkillError:
            description_refused = True
        check(
            "agent_skill_identity_and_frontmatter_fail_closed",
            mismatch_refused
            and frontmatter_refused
            and underscore_refused
            and description_refused,
        )
        unknown_field = invalid_root / "unknown-field"
        unknown_field.mkdir()
        (unknown_field / "SKILL.md").write_text(
            "---\nname: unknown-field\n"
            "description: Unknown authority-shaped field.\n"
            "disable-model-invocation: true\n---\nBody.\n",
            encoding="utf-8",
        )
        unknown_field_refused = False
        try:
            _manifest(unknown_field)
        except SkillError:
            unknown_field_refused = True
        lowercase = invalid_root / "lowercase-file"
        lowercase.mkdir()
        (lowercase / "skill.md").write_text(
            "---\nname: lowercase-file\n"
            "description: Case-insensitive manifest name.\n---\nBody.\n",
            encoding="utf-8",
        )
        lowercase_loaded = _manifest(lowercase)
        duplicate = invalid_root / "duplicate-file"
        duplicate.mkdir()
        for filename in ("SKILL.md", "skill.md"):
            (duplicate / filename).write_text(
                "---\nname: duplicate-file\n"
                "description: Duplicate manifest.\n---\nBody.\n",
                encoding="utf-8",
            )
        duplicate_refused = False
        try:
            _manifest(duplicate)
        except SkillError:
            duplicate_refused = True
        check(
            "strict_standard_fields_and_one_case_insensitive_manifest",
            unknown_field_refused
            and lowercase_loaded.skill_id == "lowercase-file"
            and duplicate_refused,
        )
        legacy_frontmatter = invalid_root / "legacy-frontmatter"
        legacy_frontmatter.mkdir()
        (legacy_frontmatter / "SKILL.md").write_text(
            "---\nname: legacy-frontmatter\n"
            "description: Read-only Loop Engine legacy metadata.\n"
            "version: 1.2.3\n"
            "title: Legacy title\n"
            "tags: [legacy, migration]\n---\nBody.\n",
            encoding="utf-8",
        )
        legacy_manifest = _manifest(legacy_frontmatter)
        check(
            "known_legacy_frontmatter_is_labeled_not_called_standard",
            legacy_manifest.frontmatter_policy == LOOP_ENGINE_LEGACY_FRONTMATTER_POLICY
            and legacy_manifest.version == "1.2.3"
            and legacy_manifest.title == "Legacy title"
            and legacy_manifest.tags == ("legacy", "migration"),
        )

        legacy_body = {
            "admission_id": "legacy-admission",
            "decision": "admit",
            "evidence_digest": "d" * 64,
            "evidence_refs": ["legacy:review"],
            "manifest_digest": "e" * 64,
            "reviewer_id": "independent-reviewer",
            "schema_version": "skill_admission/v1",
            "skill_id": "legacy_skill",
            "version": "1.0.0",
        }
        legacy_serialized = {
            **legacy_body,
            "record_digest": hashlib.sha256(
                json.dumps(legacy_body, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        legacy_loaded = SkillAdmissionRecord.from_dict(legacy_serialized)
        new_legacy_refused = False
        try:
            SkillAdmissionRecord(
                "new-legacy",
                "legacy_skill",
                "1.0.0",
                "e" * 64,
                "independent-reviewer",
                ("legacy:review",),
                "d" * 64,
            )
        except SkillError:
            new_legacy_refused = True
        check(
            "legacy_v1_underscore_ids_are_read_only_compatible",
            legacy_loaded.skill_id == "legacy_skill"
            and legacy_loaded.digest == legacy_serialized["record_digest"]
            and new_legacy_refused,
        )
        candidate_task_refused = False
        try:
            registry.load("release-review", "2.0.0", runtime=runtime)
        except SkillError:
            candidate_task_refused = True
        check(
            "candidate_skill_cannot_enter_an_active_task_context",
            candidate_task_refused,
        )
        loaded = registry.load(
            "release-review",
            "2.0.0",
            purpose=SkillLoadPurpose.CANDIDATE_REVIEW,
            runtime=runtime,
        )
        check(
            "candidate_instructions_load_only_in_a_review_loop",
            loaded.loop_id.startswith("loop")
            and "Check every threshold" in loaded.instructions
            and loaded.admission is None,
        )

        self_review_refused = False
        try:
            SkillAdmissionRecord(
                "admission-self",
                found[0].skill_id,
                found[0].version,
                found[0].manifest_digest,
                found[0].skill_id,
                ("review:release-review",),
                "a" * 64,
            )
        except SkillError:
            self_review_refused = True
        check("skill_cannot_issue_its_own_admission", self_review_refused)

        wrong_admission = SkillAdmissionRecord(
            "admission-wrong",
            found[0].skill_id,
            found[0].version,
            "b" * 64,
            "independent-reviewer",
            ("review:release-review",),
            "c" * 64,
        )
        wrong_manifest_refused = False
        try:
            registry.admit(wrong_admission, runtime=runtime)
        except SkillError:
            wrong_manifest_refused = True
        check(
            "admission_for_another_manifest_digest_is_refused", wrong_manifest_refused
        )

        review_evidence = b"independent release review passed"
        admission = SkillAdmissionRecord(
            "admission-release-review-v2",
            found[0].skill_id,
            found[0].version,
            found[0].manifest_digest,
            "independent-release-reviewer",
            ("review:release-review:2.0.0",),
            hashlib.sha256(review_evidence).hexdigest(),
        )
        serialized_admission = admission.to_dict()
        round_tripped_admission = SkillAdmissionRecord.from_dict(serialized_admission)
        changed_serialized = dict(serialized_admission)
        changed_serialized["reviewer_id"] = "different-reviewer"
        changed_record_refused = False
        try:
            SkillAdmissionRecord.from_dict(changed_serialized)
        except SkillError:
            changed_record_refused = True
        check(
            "admission_record_round_trips_and_detects_changed_fields",
            round_tripped_admission == admission and changed_record_refused,
        )
        admitted = registry.admit(admission, runtime=runtime)
        task_loaded = registry.load("release-review", "2.0.0", runtime=runtime)
        admission_inits = [
            event
            for event in ledger.events
            if event.get("event") == "init"
            and event.get("profile_id") == "practitioner.verifier"
        ]
        check(
            "task_use_requires_and_returns_the_exact_admission_record",
            admitted.lifecycle == "registered"
            and registry.admission("release-review", "2.0.0") == admission
            and task_loaded.admission == admission
            and len(admission.digest) == 64
            and task_loaded.loop_id.startswith("loop")
            and admission_inits
            and all(
                event.get("relationship_kind") == "starting"
                for event in admission_inits
            ),
        )
        changed_admission_refused = False
        try:
            registry.admit(
                replace(admission, admission_id="another-admission"), runtime=runtime
            )
        except SkillError:
            changed_admission_refused = True
        check(
            "registered_skill_cannot_replace_its_admission_authority",
            changed_admission_refused,
        )
        (skill / "references" / "checks.md").write_text(
            "Changed after discovery.\n", encoding="utf-8"
        )
        drift_refused = False
        try:
            registry.load("release-review", "2.0.0", runtime=runtime)
        except SkillError:
            drift_refused = True
        check("changed_skill_files_fail_closed", drift_refused)
        # Several harnesses read several standard skill roots, so the same
        # skill id commonly appears more than once. Discovery resolves that
        # instead of ending.
        import shutil

        mirror = Path(root) / "roots" / "mirror"
        mirror.mkdir(parents=True)
        shutil.copytree(skill, mirror / "release-review")
        conflicting = Path(root) / "roots" / "other"
        (conflicting / "release-review").mkdir(parents=True)
        (conflicting / "release-review" / "SKILL.md").write_text(
            "---\nname: release-review\n"
            "description: A different body under a taken identity.\n"
            "metadata: {loop-engine.version: '2.0.0'}\n---\n"
            "Different instructions.\n",
            encoding="utf-8",
        )
        multi = SkillRegistry()
        multi_found = multi.discover((root, str(mirror), str(conflicting)))
        conflicts = multi.discovery_conflicts
        check(
            "one_skill_under_several_standard_roots_resolves_not_fails",
            len(multi_found) == 1
            and len(conflicts) == 2
            and conflicts[0]["same_body"] is True
            and conflicts[1]["same_body"] is False
            and all(item["skill_id"] == "release-review" for item in conflicts),
            "duplicate bodies are skipped and a shadowed different body "
            "is recorded, so the remaining roots still load",
        )
        skill_events = [
            event
            for event in ledger.events
            if event.get("event") == "skill_load_terminal"
        ]
        check(
            "skill_load_identity_and_digest_enter_the_existing_loop_ledger",
            [event["status"] for event in skill_events]
            == ["completed", "completed", "failed"]
            and all(
                event["skill_id"] == "release-review"
                and event["manifest_digest"] == found[0].manifest_digest
                and "instructions" not in event
                and "root_path" not in event
                for event in skill_events
            ),
        )

    passed = sum(1 for test in tests if test["passed"])
    return {
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }
