"""Candidate-only Agent Skill discovery and progressive loading.

Discovery reads only ``SKILL.md`` frontmatter and computes file references.
Loading the full instructions is a separate deterministic Loop. Imported skills
enter as candidate Context Intelligence and never become active intelligence,
executable Code Intelligence, or approved effects by being discovered.
Task use requires a digest-bound ``SkillAdmissionRecord`` from an independent
review. Discovery cannot create that authority.

Scripts, templates, references, and assets remain files behind bounded paths.
This module does not execute them.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence

from .runtime_observer import (
    RuntimeObservation, RuntimeObservationServices)


SKILL_STATES = ("candidate", "registered", "retired")
_SKILL_ID = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")


class SkillError(ValueError):
    """A skill path, manifest, or lifecycle request failed closed."""


class SkillLoadPurpose(str, Enum):
    """Why full skill instructions are entering a Loop context."""

    TASK_USE = "task_use"
    CANDIDATE_REVIEW = "candidate_review"


def _require_digest(value: str, name: str) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef"
                   for character in value)):
        raise SkillError(f"{name} must be a lowercase SHA-256 value")


@dataclass(frozen=True)
class SkillAdmissionRecord:
    """Independent review authority for one exact candidate manifest.

    The record does not perform the review. It binds the external review
    decision and its evidence to one skill id, version, and manifest digest so
    a different or changed skill cannot reuse that authority.
    """

    admission_id: str
    skill_id: str
    version: str
    manifest_digest: str
    reviewer_id: str
    evidence_refs: tuple[str, ...]
    evidence_digest: str
    decision: str = "admit"
    schema_version: str = "skill_admission/v1"

    def __post_init__(self) -> None:
        if (not isinstance(self.admission_id, str)
                or not self.admission_id.strip()):
            raise SkillError("skill admission needs admission_id")
        if (not isinstance(self.skill_id, str)
                or not _SKILL_ID.fullmatch(self.skill_id)):
            raise SkillError("skill admission has an invalid skill_id")
        if not isinstance(self.version, str) or not self.version.strip():
            raise SkillError("skill admission needs a version")
        _require_digest(self.manifest_digest, "manifest_digest")
        _require_digest(self.evidence_digest, "evidence_digest")
        if (not isinstance(self.reviewer_id, str)
                or not self.reviewer_id.strip()):
            raise SkillError("skill admission needs an independent reviewer_id")
        if self.reviewer_id.casefold() == self.skill_id.casefold():
            raise SkillError("a skill cannot review its own admission")
        try:
            refs = tuple(self.evidence_refs)
        except TypeError as exc:
            raise SkillError("skill admission evidence_refs must be iterable") \
                from exc
        if (not refs
                or any(not isinstance(ref, str) or not ref.strip()
                       for ref in refs)
                or len(refs) != len(set(refs))):
            raise SkillError(
                "skill admission needs unique non-empty evidence_refs")
        object.__setattr__(self, "evidence_refs", refs)
        if self.decision != "admit":
            raise SkillError("skill admission decision must be 'admit'")
        if self.schema_version != "skill_admission/v1":
            raise SkillError("unsupported skill admission schema_version")

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(
            self._body(), sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()

    def _body(self) -> dict:
        return {
            "admission_id": self.admission_id,
            "decision": self.decision,
            "evidence_digest": self.evidence_digest,
            "evidence_refs": list(self.evidence_refs),
            "manifest_digest": self.manifest_digest,
            "reviewer_id": self.reviewer_id,
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "version": self.version,
        }

    def to_dict(self) -> dict:
        return {**self._body(), "record_digest": self.digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]
                  ) -> "SkillAdmissionRecord":
        body = dict(value)
        expected = str(body.pop("record_digest", ""))
        try:
            body["evidence_refs"] = tuple(body["evidence_refs"])
            record = cls(**body)
        except (KeyError, TypeError, ValueError) as exc:
            raise SkillError("invalid serialized SkillAdmissionRecord") from exc
        if expected != record.digest:
            raise SkillError("SkillAdmissionRecord digest does not match")
        return record


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SkillError("SKILL.md frontmatter is not closed")
    import yaml
    try:
        values = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as exc:
        raise SkillError(f"invalid SKILL.md frontmatter: {exc}") from exc
    if not isinstance(values, Mapping):
        raise SkillError("SKILL.md frontmatter must be a mapping")
    return dict(values), text[end + 5:]


@dataclass(frozen=True)
class SkillFileRef:
    relative_path: str
    digest: str
    size_bytes: int
    kind: str


@dataclass(frozen=True)
class SkillManifest:
    """Small searchable skill card. It does not contain full instructions."""

    skill_id: str
    title: str
    description: str
    version: str
    root_path: str
    manifest_digest: str
    files: tuple[SkillFileRef, ...] = ()
    lifecycle: str = "candidate"
    source: str = "local_skill"
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _SKILL_ID.fullmatch(self.skill_id):
            raise SkillError(
                "skill_id must be a lowercase identifier with dashes or "
                "underscores")
        if not self.title.strip() or not self.description.strip():
            raise SkillError("a skill needs title and description")
        if self.lifecycle not in SKILL_STATES:
            raise SkillError(f"lifecycle must be one of {SKILL_STATES}")
        if not self.version:
            raise SkillError("a skill needs a version")

    def as_context_candidate(self):
        """Represent the skill as candidate Context Intelligence."""
        from .store_serve import StoreRecord
        return StoreRecord(
            record_id=f"skill.{self.skill_id}.{self.version}",
            kind="strategy", title=self.title,
            body={
                "description": self.description,
                "context_type": "skill",
                "source_kind": self.source,
                "root_path": self.root_path,
                "manifest_digest": self.manifest_digest,
                "files": [ref.relative_path for ref in self.files],
                "lifecycle": self.lifecycle,
            },
            tags=("context_intelligence", "agent_skill", *self.tags),
            tier="experimental")


@dataclass(frozen=True)
class LoadedSkill:
    manifest: SkillManifest
    instructions: str
    loaded_files: tuple[SkillFileRef, ...]
    loop_id: str = ""
    admission: "SkillAdmissionRecord | None" = None


def _file_kind(relative: str) -> str:
    first = relative.split("/", 1)[0]
    if first in ("scripts", "references", "templates", "assets"):
        return first[:-1] if first.endswith("s") else first
    return "instruction" if relative == "SKILL.md" else "supporting"


def _manifest(directory: Path, *, lifecycle: str = "candidate") -> SkillManifest:
    skill_file = directory / "SKILL.md"
    if not skill_file.is_file() or skill_file.is_symlink():
        raise SkillError(f"no regular SKILL.md in {directory}")
    raw = skill_file.read_text(encoding="utf-8")
    meta, _body = _frontmatter(raw)
    skill_id = str(meta.get("name") or directory.name).strip().lower()
    title = str(meta.get("title") or skill_id.replace("-", " ").title())
    description = str(meta.get("description") or "").strip()
    version = str(meta.get("version") or "1.0.0")
    raw_tags = meta.get("tags") or ()
    tags = tuple(str(value) for value in raw_tags) \
        if isinstance(raw_tags, (list, tuple)) else ()
    refs = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if not _inside(directory, path):
            raise SkillError(f"skill file escapes root: {path}")
        relative = path.relative_to(directory).as_posix()
        data = path.read_bytes()
        refs.append(SkillFileRef(
            relative, hashlib.sha256(data).hexdigest(), len(data),
            _file_kind(relative)))
    manifest_digest = hashlib.sha256("\n".join(
        f"{ref.relative_path}:{ref.digest}" for ref in refs).encode()).hexdigest()
    return SkillManifest(
        skill_id, title, description, version, str(directory.resolve()),
        manifest_digest, tuple(refs), lifecycle, tags=tags)


class SkillRegistry:
    """Explicit registry of small skill cards with lazy instruction loading."""

    def __init__(self, manifests: Sequence[SkillManifest] = ()):
        self._skills: dict[tuple[str, str], SkillManifest] = {}
        self._admissions: dict[
            tuple[str, str], SkillAdmissionRecord] = {}
        for manifest in manifests:
            self.register(manifest)

    def register(self, manifest: SkillManifest, *,
                 replace: bool = False) -> None:
        if not isinstance(manifest, SkillManifest):
            raise SkillError("register needs a SkillManifest")
        key = (manifest.skill_id, manifest.version)
        if key in self._skills and not replace:
            raise SkillError(f"skill {key} is already registered")
        if manifest.lifecycle == "registered":
            raise SkillError(
                "registered skill state can enter only through admit()")
        self._admissions.pop(key, None)
        self._skills[key] = manifest

    def discover(self, roots: Sequence[str], *,
                 lifecycle: str = "candidate") -> tuple[SkillManifest, ...]:
        if lifecycle != "candidate":
            raise SkillError(
                "skill discovery always produces candidates; use admit() "
                "with an independent SkillAdmissionRecord")
        found = []
        for root_text in roots:
            root = Path(root_text).expanduser()
            if not root.is_dir():
                raise SkillError(f"skill root is not a directory: {root}")
            candidates = ([root] if (root / "SKILL.md").is_file()
                          else sorted(path.parent
                                      for path in root.glob("*/SKILL.md")))
            for directory in candidates:
                manifest = _manifest(directory, lifecycle="candidate")
                self.register(manifest)
                found.append(manifest)
        return tuple(found)

    def admit(self, admission: SkillAdmissionRecord, *,
              runtime: "RuntimeObservationServices | None" = None
              ) -> SkillManifest:
        """Admit one unchanged candidate through a Verifier Practitioner Loop."""
        if not isinstance(admission, SkillAdmissionRecord):
            raise SkillError("admit needs a SkillAdmissionRecord")
        selected = runtime or RuntimeObservationServices()

        def apply_admission():
            key = (admission.skill_id, admission.version)
            manifest = self._skills.get(key)
            if manifest is None:
                raise SkillError(f"no candidate skill {key}")
            existing = self._admissions.get(key)
            if manifest.lifecycle == "registered":
                if existing == admission:
                    return manifest
                raise SkillError(
                    "a registered skill cannot change admission authority")
            if manifest.lifecycle != "candidate":
                raise SkillError("only a candidate skill can be admitted")
            self._validate_admission(manifest, admission)
            registered = replace(manifest, lifecycle="registered")
            self._skills[key] = registered
            self._admissions[key] = admission
            return registered

        from ..loop.encapsulate import as_loop
        from ..loop.loop_role import (
            LoopRelationship, LoopRole, LoopRoleIdentity)
        identity = LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.verifier")
        relationship = (LoopRelationship.spawned_by(
            selected.parent.loop_id) if selected.parent is not None
            else LoopRelationship.starting())
        wrapped = as_loop(
            f"review skill admission {admission.skill_id}@{admission.version}",
            apply_admission,
            parent=selected.parent,
            ledger=selected.ledger,
            identity=identity,
            relationship=relationship,
        )
        if wrapped.get("error") is not None:
            raise wrapped["error"]
        return wrapped["value"]

    @staticmethod
    def _validate_admission(
            manifest: SkillManifest,
            admission: SkillAdmissionRecord) -> None:
        if not isinstance(admission, SkillAdmissionRecord):
            raise SkillError("admission must be a SkillAdmissionRecord")
        if (admission.skill_id != manifest.skill_id
                or admission.version != manifest.version
                or admission.manifest_digest != manifest.manifest_digest):
            raise SkillError(
                "skill admission does not match id, version, and manifest digest")

    def admission(self, skill_id: str,
                  version: str = "1.0.0") -> SkillAdmissionRecord:
        key = (skill_id, version)
        if key not in self._admissions:
            raise SkillError(f"no admission record for {skill_id}@{version}")
        return self._admissions[key]

    def inventory(self, *, include_candidates: bool = False
                  ) -> tuple[SkillManifest, ...]:
        return tuple(manifest for _key, manifest in sorted(self._skills.items())
                     if include_candidates or manifest.lifecycle == "registered")

    def search(self, query: str, *, include_candidates: bool = False,
               top_n: "int | None" = None) -> tuple[SkillManifest, ...]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        ranked = []
        for manifest in self.inventory(include_candidates=include_candidates):
            text = " ".join((manifest.skill_id, manifest.title,
                             manifest.description, *manifest.tags)).lower()
            score = len(terms & set(re.findall(r"[a-z0-9]+", text)))
            if score:
                ranked.append((score, manifest.skill_id, manifest))
        ordered = sorted(ranked, key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in (
            ordered if top_n is None else ordered[:top_n]))

    def load(self, skill_id: str, version: str = "1.0.0", *,
             purpose: SkillLoadPurpose = SkillLoadPurpose.TASK_USE,
             runtime: "RuntimeObservationServices | None" = None
             ) -> LoadedSkill:
        selected = runtime or RuntimeObservationServices()
        key = (skill_id, version)
        if key not in self._skills:
            raise SkillError(f"no skill {skill_id}@{version}")
        manifest = self._skills[key]
        if not isinstance(purpose, SkillLoadPurpose):
            raise SkillError("skill load purpose is not recognized")
        if (purpose is SkillLoadPurpose.TASK_USE
                and manifest.lifecycle != "registered"):
            raise SkillError(
                "only a registered skill can enter an active task context; "
                "use candidate_review for independent review")
        admission = self._admissions.get(key)
        if (purpose is SkillLoadPurpose.TASK_USE
                and (admission is None
                     or admission.manifest_digest != manifest.manifest_digest)):
            raise SkillError(
                "registered task use needs its exact SkillAdmissionRecord")
        if manifest.lifecycle == "retired":
            raise SkillError("a retired skill cannot be loaded")
        root = Path(manifest.root_path)

        def read_and_verify():
            current = _manifest(root, lifecycle=manifest.lifecycle)
            if current.manifest_digest != manifest.manifest_digest:
                raise SkillError(
                    "skill files changed after discovery; rediscover explicitly")
            raw = (root / "SKILL.md").read_text(encoding="utf-8")
            _meta, body = _frontmatter(raw)
            return LoadedSkill(manifest, body.strip(), current.files)

        from ..loop.encapsulate import as_loop
        from ..loop.loop_role import (LoopRelationship, LoopRole,
                                     LoopRoleIdentity)
        identity = LoopRoleIdentity(
            LoopRole.INTELLIGENCE, "intelligence.context.serve")
        relationship = (LoopRelationship.retrieved_by(
            selected.parent.loop_id) if selected.parent is not None
            else LoopRelationship.starting())
        try:
            wrapped = as_loop(
                f"load skill {skill_id}@{version}", read_and_verify,
                parent=selected.parent, ledger=selected.ledger,
                identity=identity, relationship=relationship)
            if wrapped.get("error") is not None:
                raise wrapped["error"]
        except Exception as exc:
            selected.emit(_skill_observation(
                manifest, "failed", type(exc).__name__,
                loop_id=str(getattr(selected.parent, "loop_id", ""))))
            raise
        loaded = wrapped["value"]
        result = LoadedSkill(
            loaded.manifest, loaded.instructions, loaded.loaded_files,
            loop_id=wrapped["loop_id"], admission=admission)
        selected.emit(_skill_observation(
            manifest, "completed", "", loop_id=result.loop_id))
        return result


def _skill_observation(manifest: SkillManifest, status: str,
                       error_code: str, *, loop_id: str) -> RuntimeObservation:
    return RuntimeObservation(
        "skill_load_terminal",
        {"skill_id": manifest.skill_id,
         "version": manifest.version,
         "lifecycle": manifest.lifecycle,
         "manifest_digest": manifest.manifest_digest,
         "file_count": len(manifest.files),
         "status": status,
         "error_code": error_code},
        loop_id=loop_id)


def self_test() -> dict:
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
            "---\nname: release-review\nversion: 2.0.0\n"
            "description: Review release risk with typed checks.\n"
            "tags: [release, verification]\n---\n"
            "Read the release contract. Check every threshold.\n",
            encoding="utf-8")
        (skill / "references" / "checks.md").write_text(
            "Threshold definitions.\n", encoding="utf-8")
        registry = SkillRegistry()
        found = registry.discover((root,))
        check("discovery_builds_a_small_candidate_manifest",
              len(found) == 1 and found[0].lifecycle == "candidate"
              and len(found[0].files) == 2)
        direct_registered_discovery_refused = False
        try:
            SkillRegistry().discover((root,), lifecycle="registered")
        except SkillError:
            direct_registered_discovery_refused = True
        check("discovery_cannot_mark_a_skill_registered",
              direct_registered_discovery_refused)
        direct_registered_manifest_refused = False
        try:
            SkillRegistry().register(replace(
                found[0], lifecycle="registered"))
        except SkillError:
            direct_registered_manifest_refused = True
        check("registered_manifest_without_admission_is_refused",
              direct_registered_manifest_refused)
        check("candidate_skills_are_excluded_from_normal_search",
              not registry.search("release verification")
              and registry.search(
                  "release verification", include_candidates=True)[0].skill_id
              == "release-review")
        context = found[0].as_context_candidate()
        check("an_imported_skill_is_candidate_context_not_executable_code",
              context.tier == "experimental"
              and context.body["context_type"] == "skill")
        candidate_task_refused = False
        try:
            registry.load("release-review", "2.0.0", runtime=runtime)
        except SkillError:
            candidate_task_refused = True
        check("candidate_skill_cannot_enter_an_active_task_context",
              candidate_task_refused)
        loaded = registry.load(
            "release-review", "2.0.0",
            purpose=SkillLoadPurpose.CANDIDATE_REVIEW,
            runtime=runtime)
        check("candidate_instructions_load_only_in_a_review_loop",
              loaded.loop_id.startswith("loop")
              and "Check every threshold" in loaded.instructions
              and loaded.admission is None)

        self_review_refused = False
        try:
            SkillAdmissionRecord(
                "admission-self", found[0].skill_id, found[0].version,
                found[0].manifest_digest, found[0].skill_id,
                ("review:release-review",), "a" * 64)
        except SkillError:
            self_review_refused = True
        check("skill_cannot_issue_its_own_admission", self_review_refused)

        wrong_admission = SkillAdmissionRecord(
            "admission-wrong", found[0].skill_id, found[0].version,
            "b" * 64, "independent-reviewer",
            ("review:release-review",), "c" * 64)
        wrong_manifest_refused = False
        try:
            registry.admit(wrong_admission, runtime=runtime)
        except SkillError:
            wrong_manifest_refused = True
        check("admission_for_another_manifest_digest_is_refused",
              wrong_manifest_refused)

        review_evidence = b"independent release review passed"
        admission = SkillAdmissionRecord(
            "admission-release-review-v2", found[0].skill_id,
            found[0].version, found[0].manifest_digest,
            "independent-release-reviewer",
            ("review:release-review:2.0.0",),
            hashlib.sha256(review_evidence).hexdigest())
        serialized_admission = admission.to_dict()
        round_tripped_admission = SkillAdmissionRecord.from_dict(
            serialized_admission)
        changed_serialized = dict(serialized_admission)
        changed_serialized["reviewer_id"] = "different-reviewer"
        changed_record_refused = False
        try:
            SkillAdmissionRecord.from_dict(changed_serialized)
        except SkillError:
            changed_record_refused = True
        check("admission_record_round_trips_and_detects_changed_fields",
              round_tripped_admission == admission
              and changed_record_refused)
        admitted = registry.admit(admission, runtime=runtime)
        task_loaded = registry.load(
            "release-review", "2.0.0", runtime=runtime)
        admission_inits = [
            event for event in ledger.events
            if event.get("event") == "init"
            and event.get("profile_id") == "practitioner.verifier"]
        check("task_use_requires_and_returns_the_exact_admission_record",
              admitted.lifecycle == "registered"
              and registry.admission("release-review", "2.0.0") == admission
              and task_loaded.admission == admission
              and len(admission.digest) == 64
              and task_loaded.loop_id.startswith("loop")
              and admission_inits
              and all(event.get("relationship_kind") == "starting"
                      for event in admission_inits))
        changed_admission_refused = False
        try:
            registry.admit(replace(
                admission, admission_id="another-admission"),
                runtime=runtime)
        except SkillError:
            changed_admission_refused = True
        check("registered_skill_cannot_replace_its_admission_authority",
              changed_admission_refused)
        (skill / "references" / "checks.md").write_text(
            "Changed after discovery.\n", encoding="utf-8")
        drift_refused = False
        try:
            registry.load("release-review", "2.0.0", runtime=runtime)
        except Exception:
            drift_refused = True
        check("changed_skill_files_fail_closed", drift_refused)
        skill_events = [event for event in ledger.events
                        if event.get("event") == "skill_load_terminal"]
        check("skill_load_identity_and_digest_enter_the_existing_loop_ledger",
              [event["status"] for event in skill_events]
              == ["completed", "completed", "failed"]
              and all(event["skill_id"] == "release-review"
                      and event["manifest_digest"] == found[0].manifest_digest
                      and "instructions" not in event
                      and "root_path" not in event
                      for event in skill_events))

    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
