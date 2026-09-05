"""Candidate-only Agent Skill discovery and progressive loading.

Discovery parses only ``SKILL.md`` frontmatter as semantic metadata. It reads
skill-file bytes to compute exact references and digests but does not return
their bodies. Loading the full instructions is a separate deterministic Loop.
Imported skills enter as candidate Context Intelligence and never become
active intelligence, executable Code Intelligence, or approved effects by
being discovered.
Task use requires a digest-bound ``SkillAdmissionRecord`` that names an
external reviewer and evidence. The registry validates the record but does not
perform or prove that review. Discovery cannot create the admission.

Scripts, templates, references, and assets remain files behind bounded paths.
This module does not execute them.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from .runtime_observer import RuntimeObservation, RuntimeObservationServices
from .skill_discovery_projection import SkillDiscoveryCard, SkillDiscoveryProjection

SKILL_STATES = ("candidate", "registered", "retired")
AGENT_SKILLS_STRICT_POLICY = "agent_skills_standard_strict/v1"
AGENT_SKILLS_ALLOWED_FRONTMATTER = frozenset(
    {
        "name",
        "description",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
    }
)
LOOP_ENGINE_LEGACY_FRONTMATTER_POLICY = "loop_engine_skill_frontmatter_legacy/v1"
_LEGACY_FRONTMATTER_FIELDS = frozenset({"version", "title", "tags"})
_SKILL_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LEGACY_V1_SKILL_ID = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_MAXIMUM_SKILL_NAME_CHARACTERS = 64
_MAXIMUM_SKILL_DESCRIPTION_CHARACTERS = 1024
_MAXIMUM_SKILL_COMPATIBILITY_CHARACTERS = 500
_MINIMUM_SKILL_DISCOVERY_BYTES = 256
_VERSION_METADATA_KEY = "loop-engine.version"
_TITLE_METADATA_KEY = "loop-engine.title"
_TAGS_METADATA_KEY = "loop-engine.tags"


class SkillError(ValueError):
    """A skill path, manifest, or lifecycle request failed closed."""


class SkillLoadPurpose(str, Enum):
    """Why full skill instructions are entering a Loop context."""

    TASK_USE = "task_use"
    CANDIDATE_REVIEW = "candidate_review"


def _require_digest(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
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
        if not isinstance(self.admission_id, str) or not self.admission_id.strip():
            raise SkillError("skill admission needs admission_id")
        if not isinstance(self.skill_id, str) or not _SKILL_ID.fullmatch(self.skill_id):
            raise SkillError("skill admission has an invalid skill_id")
        if not isinstance(self.version, str) or not self.version.strip():
            raise SkillError("skill admission needs a version")
        _require_digest(self.manifest_digest, "manifest_digest")
        _require_digest(self.evidence_digest, "evidence_digest")
        if not isinstance(self.reviewer_id, str) or not self.reviewer_id.strip():
            raise SkillError("skill admission needs an independent reviewer_id")
        if self.reviewer_id.casefold() == self.skill_id.casefold():
            raise SkillError("a skill cannot review its own admission")
        try:
            refs = tuple(self.evidence_refs)
        except TypeError as exc:
            raise SkillError("skill admission evidence_refs must be iterable") from exc
        if (
            not refs
            or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
            or len(refs) != len(set(refs))
        ):
            raise SkillError("skill admission needs unique non-empty evidence_refs")
        object.__setattr__(self, "evidence_refs", refs)
        if self.decision != "admit":
            raise SkillError("skill admission decision must be 'admit'")
        if self.schema_version != "skill_admission/v1":
            raise SkillError("unsupported skill admission schema_version")

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self._body(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

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
    def from_dict(cls, value: Mapping[str, object]) -> SkillAdmissionRecord:
        body = dict(value)
        expected = str(body.pop("record_digest", ""))
        try:
            body["evidence_refs"] = tuple(body["evidence_refs"])
            skill_id = str(body.get("skill_id", ""))
            if _LEGACY_V1_SKILL_ID.fullmatch(skill_id) and not _SKILL_ID.fullmatch(
                skill_id
            ):
                if body.get("schema_version") != "skill_admission/v1":
                    raise SkillError("legacy skill ids are readable only in v1 records")
                if str(body.get("reviewer_id", "")).casefold() == skill_id.casefold():
                    raise SkillError("a skill cannot review its own admission")
                strict_body = {**body, "skill_id": "legacy-record"}
                validated = cls(**strict_body)
                record = object.__new__(cls)
                for name in cls.__dataclass_fields__:
                    object.__setattr__(
                        record,
                        name,
                        skill_id if name == "skill_id" else getattr(validated, name),
                    )
            else:
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
        raise SkillError("SKILL.md needs YAML frontmatter")
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
    return dict(values), text[end + 5 :]


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
    license: str = ""
    compatibility: str = ""
    metadata: tuple[tuple[str, str], ...] = ()
    requested_tools: tuple[str, ...] = ()
    instruction_bytes: int = 0
    instruction_lines: int = 0
    frontmatter_policy: str = AGENT_SKILLS_STRICT_POLICY

    def __post_init__(self) -> None:
        if len(
            self.skill_id
        ) > _MAXIMUM_SKILL_NAME_CHARACTERS or not _SKILL_ID.fullmatch(self.skill_id):
            raise SkillError(
                "skill_id must use 1 to 64 lowercase letters, numbers, and "
                "single hyphens"
            )
        if (
            not self.title.strip()
            or not self.description.strip()
            or len(self.description) > _MAXIMUM_SKILL_DESCRIPTION_CHARACTERS
        ):
            raise SkillError("a skill needs title and description")
        if self.lifecycle not in SKILL_STATES:
            raise SkillError(f"lifecycle must be one of {SKILL_STATES}")
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(self.version):
            raise SkillError("Loop Engine skill metadata needs a semantic version")
        if self.frontmatter_policy not in (
            AGENT_SKILLS_STRICT_POLICY,
            LOOP_ENGINE_LEGACY_FRONTMATTER_POLICY,
        ):
            raise SkillError("unknown Agent Skills frontmatter policy")
        if len(self.compatibility) > _MAXIMUM_SKILL_COMPATIBILITY_CHARACTERS:
            raise SkillError("skill compatibility exceeds 500 characters")
        for name, values in (
            ("tags", self.tags),
            ("requested_tools", self.requested_tools),
        ):
            if any(
                not isinstance(value, str) or not value.strip() for value in values
            ) or len(values) != len(set(values)):
                raise SkillError(f"{name} must contain unique non-empty text")
        if any(
            not isinstance(key, str) or not key.strip() or not isinstance(value, str)
            for key, value in self.metadata
        ) or len(self.metadata) != len({key for key, _ in self.metadata}):
            raise SkillError("skill metadata must contain unique string pairs")
        if (
            not isinstance(self.instruction_bytes, int)
            or self.instruction_bytes < 0
            or not isinstance(self.instruction_lines, int)
            or self.instruction_lines < 0
        ):
            raise SkillError("skill instruction size must be non-negative")

    def as_context_candidate(self):
        """Represent the skill as candidate Context Intelligence."""
        from .store_serve import StoreRecord

        return StoreRecord(
            record_id=f"skill.{self.skill_id}.{self.version}",
            kind="strategy",
            title=self.title,
            body={
                "description": self.description,
                "context_type": "skill",
                "source_kind": self.source,
                "root_path": self.root_path,
                "manifest_digest": self.manifest_digest,
                "files": [ref.relative_path for ref in self.files],
                "lifecycle": self.lifecycle,
                "license": self.license,
                "compatibility": self.compatibility,
                "metadata": dict(self.metadata),
                # A skill can state what it expects. Only Loop authority can
                # make a tool or effect available at execution time.
                "requested_tools": list(self.requested_tools),
                "requested_tools_grant_authority": False,
                "instruction_bytes": self.instruction_bytes,
                "instruction_lines": self.instruction_lines,
                "frontmatter_policy": self.frontmatter_policy,
            },
            tags=("context_intelligence", "agent_skill", *self.tags),
            tier="experimental",
        )


@dataclass(frozen=True)
class LoadedSkill:
    manifest: SkillManifest
    instructions: str
    loaded_files: tuple[SkillFileRef, ...]
    loop_id: str = ""
    admission: SkillAdmissionRecord | None = None


def _file_kind(relative: str) -> str:
    first = relative.split("/", 1)[0]
    if first in ("scripts", "references", "templates", "assets"):
        return first.removesuffix("s")
    return "instruction" if relative.casefold() == "skill.md" else "supporting"


def _skill_files(directory: Path) -> tuple[Path, ...]:
    try:
        return tuple(
            sorted(
                path
                for path in directory.iterdir()
                if path.name.casefold() == "skill.md"
            )
        )
    except OSError as exc:
        raise SkillError(f"cannot inspect skill directory: {directory}") from exc


def _skill_file(directory: Path) -> Path:
    matches = _skill_files(directory)
    if len(matches) != 1:
        raise SkillError(
            "a skill directory needs exactly one case-insensitive SKILL.md"
        )
    skill_file = matches[0]
    if not skill_file.is_file() or skill_file.is_symlink():
        raise SkillError(f"SKILL.md must be one regular file in {directory}")
    return skill_file


def _manifest(directory: Path, *, lifecycle: str = "candidate") -> SkillManifest:
    skill_file = _skill_file(directory)
    raw = skill_file.read_text(encoding="utf-8")
    meta, body = _frontmatter(raw)
    unexpected = set(meta) - AGENT_SKILLS_ALLOWED_FRONTMATTER
    unsupported = unexpected - _LEGACY_FRONTMATTER_FIELDS
    if unsupported:
        raise SkillError(
            "strict Agent Skills frontmatter has unknown fields: "
            + ", ".join(sorted(str(value) for value in unsupported))
        )
    frontmatter_policy = (
        LOOP_ENGINE_LEGACY_FRONTMATTER_POLICY
        if unexpected
        else AGENT_SKILLS_STRICT_POLICY
    )
    if "name" not in meta or "description" not in meta:
        raise SkillError("SKILL.md frontmatter needs name and description")
    for name in ("name", "description"):
        if not isinstance(meta[name], str):
            raise SkillError(f"SKILL.md {name} must be a string")
    for name in ("license", "compatibility", *unexpected):
        if (
            name in meta
            and not isinstance(meta[name], str)
            and (name != "tags" or not isinstance(meta[name], (list, tuple)))
        ):
            raise SkillError(f"SKILL.md {name} has the wrong type")
    skill_id = meta["name"].strip()
    if skill_id != directory.name:
        raise SkillError("SKILL.md name must match its parent directory")
    description = str(meta["description"]).strip()
    license_name = str(meta.get("license") or "").strip()
    compatibility = str(meta.get("compatibility") or "").strip()
    raw_metadata = meta.get("metadata") or {}
    if not isinstance(raw_metadata, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in raw_metadata.items()
    ):
        raise SkillError("SKILL.md metadata must map strings to strings")
    version = str(
        meta.get("version") or raw_metadata.get(_VERSION_METADATA_KEY, "1.0.0")
    ).strip()
    if not _SEMVER.fullmatch(version):
        raise SkillError(
            f"metadata.{_VERSION_METADATA_KEY} must use semantic versioning"
        )
    title = str(
        meta.get("title")
        or raw_metadata.get(_TITLE_METADATA_KEY, skill_id.replace("-", " ").title())
    ).strip()
    if not title:
        raise SkillError(f"metadata.{_TITLE_METADATA_KEY} cannot be empty")
    legacy_tags = meta.get("tags") or ()
    if legacy_tags and (
        not isinstance(legacy_tags, (list, tuple))
        or any(not isinstance(value, str) for value in legacy_tags)
    ):
        raise SkillError("legacy SKILL.md tags must be a list of strings")
    raw_tags = raw_metadata.get(_TAGS_METADATA_KEY, "")
    tags = (
        tuple(legacy_tags)
        if legacy_tags
        else tuple(value.strip() for value in raw_tags.split(",") if value.strip())
    )
    allowed_tools = meta.get("allowed-tools") or ""
    if not isinstance(allowed_tools, str):
        raise SkillError("SKILL.md allowed-tools must be a string")
    requested_tools = tuple(allowed_tools.split())
    refs = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if not _inside(directory, path):
            raise SkillError(f"skill file escapes root: {path}")
        relative = path.relative_to(directory).as_posix()
        data = path.read_bytes()
        refs.append(
            SkillFileRef(
                relative,
                hashlib.sha256(data).hexdigest(),
                len(data),
                _file_kind(relative),
            )
        )
    manifest_digest = hashlib.sha256(
        "\n".join(f"{ref.relative_path}:{ref.digest}" for ref in refs).encode()
    ).hexdigest()
    return SkillManifest(
        skill_id,
        title,
        description,
        version,
        str(directory.resolve()),
        manifest_digest,
        tuple(refs),
        lifecycle,
        tags=tags,
        license=license_name,
        compatibility=compatibility,
        metadata=tuple(sorted(raw_metadata.items())),
        requested_tools=requested_tools,
        instruction_bytes=len(body.encode("utf-8")),
        instruction_lines=len(body.splitlines()),
        frontmatter_policy=frontmatter_policy,
    )


class SkillRegistry:
    """Explicit registry of small skill cards with lazy instruction loading."""

    def __init__(self, manifests: Sequence[SkillManifest] = ()):
        self._skills: dict[tuple[str, str], SkillManifest] = {}
        self._admissions: dict[tuple[str, str], SkillAdmissionRecord] = {}
        self.discovery_conflicts: list[dict] = []
        for manifest in manifests:
            self.register(manifest)

    def register(self, manifest: SkillManifest, *, replace: bool = False) -> None:
        if not isinstance(manifest, SkillManifest):
            raise SkillError("register needs a SkillManifest")
        key = (manifest.skill_id, manifest.version)
        if key in self._skills and not replace:
            raise SkillError(f"skill {key} is already registered")
        if manifest.lifecycle == "registered":
            raise SkillError("registered skill state can enter only through admit()")
        self._admissions.pop(key, None)
        self._skills[key] = manifest

    def discover(
        self, roots: Sequence[str], *, lifecycle: str = "candidate"
    ) -> tuple[SkillManifest, ...]:
        if lifecycle != "candidate":
            raise SkillError(
                "skill discovery always produces candidates; use admit() "
                "with an independent SkillAdmissionRecord"
            )
        found = []
        # The same skill commonly appears under several standard roots
        # because different harnesses read different directories. An
        # identical manifest digest is one skill seen twice and is skipped;
        # a different body under a taken identity is a real conflict and is
        # recorded, so one shadowed skill never ends discovery of the rest.
        self.discovery_conflicts: list[dict] = []
        for root_text in roots:
            root = Path(root_text).expanduser()
            if not root.is_dir():
                raise SkillError(f"skill root is not a directory: {root}")
            root_matches = _skill_files(root)
            candidates = (
                [root]
                if root_matches
                else sorted(
                    path
                    for path in root.iterdir()
                    if path.is_dir() and _skill_files(path)
                )
            )
            for directory in candidates:
                manifest = _manifest(directory, lifecycle="candidate")
                key = (manifest.skill_id, manifest.version)
                existing = self._skills.get(key)
                if existing is not None:
                    self.discovery_conflicts.append(
                        {
                            "record_type": "skill_discovery_conflict/v1",
                            "skill_id": manifest.skill_id,
                            "version": manifest.version,
                            "kept_root": str(existing.root_path),
                            "shadowed_root": str(manifest.root_path),
                            "same_body": (
                                existing.manifest_digest == manifest.manifest_digest
                            ),
                        }
                    )
                    continue
                self.register(manifest)
                found.append(manifest)
        return tuple(found)

    def admit(
        self,
        admission: SkillAdmissionRecord,
        *,
        runtime: RuntimeObservationServices | None = None,
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
                raise SkillError("a registered skill cannot change admission authority")
            if manifest.lifecycle != "candidate":
                raise SkillError("only a candidate skill can be admitted")
            self._validate_admission(manifest, admission)
            registered = replace(manifest, lifecycle="registered")
            self._skills[key] = registered
            self._admissions[key] = admission
            return registered

        from ..loop.encapsulate import as_loop
        from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity

        identity = LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.verifier")
        relationship = (
            LoopRelationship.spawned_by(selected.parent.loop_id)
            if selected.parent is not None
            else LoopRelationship.starting()
        )
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
        manifest: SkillManifest, admission: SkillAdmissionRecord
    ) -> None:
        if not isinstance(admission, SkillAdmissionRecord):
            raise SkillError("admission must be a SkillAdmissionRecord")
        if (
            admission.skill_id != manifest.skill_id
            or admission.version != manifest.version
            or admission.manifest_digest != manifest.manifest_digest
        ):
            raise SkillError(
                "skill admission does not match id, version, and manifest digest"
            )

    def admission(self, skill_id: str, version: str = "1.0.0") -> SkillAdmissionRecord:
        key = (skill_id, version)
        if key not in self._admissions:
            raise SkillError(f"no admission record for {skill_id}@{version}")
        return self._admissions[key]

    def inventory(
        self, *, include_candidates: bool = False
    ) -> tuple[SkillManifest, ...]:
        return tuple(
            manifest
            for _key, manifest in sorted(self._skills.items())
            if include_candidates or manifest.lifecycle == "registered"
        )

    def search(
        self, query: str, *, include_candidates: bool = False, top_n: int | None = None
    ) -> tuple[SkillManifest, ...]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        ranked = []
        for manifest in self.inventory(include_candidates=include_candidates):
            text = " ".join(
                (
                    manifest.skill_id,
                    manifest.title,
                    manifest.description,
                    *manifest.tags,
                )
            ).lower()
            score = len(terms & set(re.findall(r"[a-z0-9]+", text)))
            if score:
                ranked.append((score, manifest.skill_id, manifest))
        ordered = sorted(ranked, key=lambda item: (-item[0], item[1]))
        return tuple(
            item[2] for item in (ordered if top_n is None else ordered[:top_n])
        )

    def discovery_projection(
        self, maximum_bytes: int, *, include_candidates: bool = False, query: str = ""
    ) -> SkillDiscoveryProjection:
        """Return bounded cards before any full SKILL.md body is loaded."""
        if (
            not isinstance(maximum_bytes, int)
            or isinstance(maximum_bytes, bool)
            or maximum_bytes < _MINIMUM_SKILL_DISCOVERY_BYTES
        ):
            raise SkillError(
                "maximum_bytes is below the skill discovery envelope minimum"
            )
        manifests = (
            self.search(query, include_candidates=include_candidates)
            if query.strip()
            else self.inventory(include_candidates=include_candidates)
        )
        cards: list[SkillDiscoveryCard] = []
        total = len(manifests)
        for manifest in manifests:
            candidate = [*cards, SkillDiscoveryCard.from_manifest(manifest)]
            try:
                SkillDiscoveryProjection(
                    maximum_bytes, total, tuple(candidate), total - len(candidate)
                )
            except SkillError:
                continue
            cards = candidate
        return SkillDiscoveryProjection(
            maximum_bytes, total, tuple(cards), total - len(cards)
        )

    def load(
        self,
        skill_id: str,
        version: str = "1.0.0",
        *,
        purpose: SkillLoadPurpose = SkillLoadPurpose.TASK_USE,
        runtime: RuntimeObservationServices | None = None,
    ) -> LoadedSkill:
        selected = runtime or RuntimeObservationServices()
        key = (skill_id, version)
        if key not in self._skills:
            raise SkillError(f"no skill {skill_id}@{version}")
        manifest = self._skills[key]
        if not isinstance(purpose, SkillLoadPurpose):
            raise SkillError("skill load purpose is not recognized")
        if purpose is SkillLoadPurpose.TASK_USE and manifest.lifecycle != "registered":
            raise SkillError(
                "only a registered skill can enter an active task context; "
                "use candidate_review for independent review"
            )
        admission = self._admissions.get(key)
        if purpose is SkillLoadPurpose.TASK_USE and (
            admission is None or admission.manifest_digest != manifest.manifest_digest
        ):
            raise SkillError("registered task use needs its exact SkillAdmissionRecord")
        if manifest.lifecycle == "retired":
            raise SkillError("a retired skill cannot be loaded")
        root = Path(manifest.root_path)

        def read_and_verify():
            current = _manifest(root, lifecycle=manifest.lifecycle)
            if current.manifest_digest != manifest.manifest_digest:
                raise SkillError(
                    "skill files changed after discovery; rediscover explicitly"
                )
            raw = _skill_file(root).read_text(encoding="utf-8")
            _meta, body = _frontmatter(raw)
            return LoadedSkill(manifest, body.strip(), current.files)

        from ..loop.encapsulate import as_loop
        from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity

        identity = LoopRoleIdentity(LoopRole.INTELLIGENCE, "intelligence.context.serve")
        relationship = (
            LoopRelationship.retrieved_by(selected.parent.loop_id)
            if selected.parent is not None
            else LoopRelationship.starting()
        )
        try:
            wrapped = as_loop(
                f"load skill {skill_id}@{version}",
                read_and_verify,
                parent=selected.parent,
                ledger=selected.ledger,
                identity=identity,
                relationship=relationship,
            )
            if wrapped.get("error") is not None:
                raise wrapped["error"]
        except Exception as exc:
            selected.emit(
                _skill_observation(
                    manifest,
                    "failed",
                    type(exc).__name__,
                    loop_id=str(getattr(selected.parent, "loop_id", "")),
                )
            )
            raise
        loaded = wrapped["value"]
        result = LoadedSkill(
            loaded.manifest,
            loaded.instructions,
            loaded.loaded_files,
            loop_id=wrapped["loop_id"],
            admission=admission,
        )
        selected.emit(
            _skill_observation(manifest, "completed", "", loop_id=result.loop_id)
        )
        return result


def _skill_observation(
    manifest: SkillManifest, status: str, error_code: str, *, loop_id: str
) -> RuntimeObservation:
    return RuntimeObservation(
        "skill_load_terminal",
        {
            "skill_id": manifest.skill_id,
            "version": manifest.version,
            "lifecycle": manifest.lifecycle,
            "manifest_digest": manifest.manifest_digest,
            "file_count": len(manifest.files),
            "status": status,
            "error_code": error_code,
        },
        loop_id=loop_id,
    )


def self_test() -> dict:
    """Run the separately housed offline registry checks."""
    from .skill_registry_checks import run_checks

    return run_checks()
