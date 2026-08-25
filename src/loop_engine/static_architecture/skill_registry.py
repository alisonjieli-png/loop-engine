"""Candidate-only Agent Skill discovery and progressive loading.

Discovery reads only ``SKILL.md`` frontmatter and computes file references.
Loading the full instructions is a separate deterministic Loop. Imported skills
enter as candidate Context Intelligence and never become active intelligence,
executable Code Intelligence, or approved effects by being discovered.

Scripts, templates, references, and assets remain files behind bounded paths.
This module does not execute them.
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
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
        for manifest in manifests:
            self.register(manifest)

    def register(self, manifest: SkillManifest, *, replace: bool = False) -> None:
        key = (manifest.skill_id, manifest.version)
        if key in self._skills and not replace:
            raise SkillError(f"skill {key} is already registered")
        self._skills[key] = manifest

    def discover(self, roots: Sequence[str], *,
                 lifecycle: str = "candidate") -> tuple[SkillManifest, ...]:
        found = []
        for root_text in roots:
            root = Path(root_text).expanduser()
            if not root.is_dir():
                raise SkillError(f"skill root is not a directory: {root}")
            candidates = ([root] if (root / "SKILL.md").is_file()
                          else sorted(path.parent
                                      for path in root.glob("*/SKILL.md")))
            for directory in candidates:
                manifest = _manifest(directory, lifecycle=lifecycle)
                self.register(manifest)
                found.append(manifest)
        return tuple(found)

    def inventory(self, *, include_candidates: bool = False
                  ) -> tuple[SkillManifest, ...]:
        return tuple(manifest for _key, manifest in sorted(self._skills.items())
                     if include_candidates or manifest.lifecycle == "registered")

    def search(self, query: str, *, include_candidates: bool = False,
               top_n: int = 8) -> tuple[SkillManifest, ...]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        ranked = []
        for manifest in self.inventory(include_candidates=include_candidates):
            text = " ".join((manifest.skill_id, manifest.title,
                             manifest.description, *manifest.tags)).lower()
            score = len(terms & set(re.findall(r"[a-z0-9]+", text)))
            if score:
                ranked.append((score, manifest.skill_id, manifest))
        return tuple(item[2] for item in sorted(
            ranked, key=lambda item: (-item[0], item[1]))[:top_n])

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
            loop_id=wrapped["loop_id"])
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
              and "Check every threshold" in loaded.instructions)
        (skill / "references" / "checks.md").write_text(
            "Changed after discovery.\n", encoding="utf-8")
        drift_refused = False
        try:
            registry.load(
                "release-review", "2.0.0",
                purpose=SkillLoadPurpose.CANDIDATE_REVIEW,
                runtime=runtime)
        except Exception:
            drift_refused = True
        check("changed_skill_files_fail_closed", drift_refused)
        skill_events = [event for event in ledger.events
                        if event.get("event") == "skill_load_terminal"]
        check("skill_load_identity_and_digest_enter_the_existing_loop_ledger",
              [event["status"] for event in skill_events]
              == ["completed", "failed"]
              and all(event["skill_id"] == "release-review"
                      and event["manifest_digest"] == found[0].manifest_digest
                      and "instructions" not in event
                      and "root_path" not in event
                      for event in skill_events))

    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
