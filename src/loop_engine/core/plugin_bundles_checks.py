"""Executable checks for governed plugin bundle resolution.

Owns exact-admission, conflict, drift, JSON, ASCII, and Loop-envelope proof.
It never installs or activates a plugin.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .plugin_bundles import (
    PluginBundleError, PluginResolutionRequest, resolve_plugin_snapshot_as_loop)
from .skill_registry import SkillAdmissionRecord, SkillRegistry


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        skill_root = root / "skills" / "review-code"
        skill_root.mkdir(parents=True)
        skill_file = skill_root / "SKILL.md"
        skill_file.write_text(
            "---\nname: review-code\ndescription: Review changed code.\n"
            "version: 1.0.0\n---\nReview exact changed files.\n",
            encoding="utf-8")
        registry = SkillRegistry()
        candidate = registry.discover((str(skill_root),))[0]
        admission = SkillAdmissionRecord(
            "admission.review-code.1", candidate.skill_id, candidate.version,
            candidate.manifest_digest, "independent-verifier",
            ("evidence:test",), "a" * 64)
        registry.admit(admission)

        def write_bundle(directory: Path, description: str) -> None:
            directory.mkdir(parents=True, exist_ok=True)
            value = {
                "schema_version": "plugin_bundle/v1",
                "plugin_id": "review-suite", "version": "1.0.0",
                "description": description, "engine_api_version": "1",
                "skills": [{"skill_id": candidate.skill_id,
                            "version": candidate.version,
                            "manifest_digest": candidate.manifest_digest}],
                "profile_refs": ["practitioner.verifier@1.0.0"],
                "capability_refs": [],
                "event_subscriptions": ["evaluation.completed"]}
            (directory / "loop-engine-plugin.json").write_text(
                json.dumps(value, indent=2) + "\n", encoding="utf-8")

        installed = root / "installed"
        project = root / "project"
        write_bundle(installed, "Review admitted code changes.")
        write_bundle(project, "Review admitted code changes.")
        snapshot = resolve_plugin_snapshot_as_loop(PluginResolutionRequest(
            (str(installed),), (str(project),), registry))
        check("exact_installed_and_project_bundles_deduplicate",
              len(snapshot.plugins) == 1
              and any("deduplicated" in reason
                      for reason in snapshot.resolution_reasons))
        check("resolution_runs_as_intelligence_loop",
              bool(snapshot.loop_id) and snapshot.content_digest)
        tree = snapshot.ascii_tree()
        check("ascii_tree_and_json_share_the_same_snapshot",
              "review-suite@1.0.0" in tree and "review-code@1.0.0" in tree
              and snapshot.to_dict()["content_digest"]
              == snapshot.content_digest)

        write_bundle(project, "Changed project override.")
        conflict = False
        try:
            resolve_plugin_snapshot_as_loop(PluginResolutionRequest(
                (str(installed),), (str(project),), registry))
        except PluginBundleError:
            conflict = True
        check("changed_project_bundle_cannot_silently_override", conflict)

        write_bundle(project, "Review admitted code changes.")
        skill_file.write_text(skill_file.read_text() + "Changed.\n")
        drift = False
        try:
            resolve_plugin_snapshot_as_loop(PluginResolutionRequest(
                (str(installed),), (), registry))
        except PluginBundleError:
            drift = True
        check("changed_skill_body_invalidates_plugin_resolution", drift)

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "plugin_bundle_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}

