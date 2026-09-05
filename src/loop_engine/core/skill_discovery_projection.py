"""Passive byte-bounded discovery records for Agent Skills.

The records expose only small identity and description cards. They do not load
instructions, select task semantics, execute a skill, or grant authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .skill_registry import SkillManifest


def _skill_error(message: str) -> Exception:
    from .skill_registry import SkillError

    return SkillError(message)


def _require_digest(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _skill_error(f"{name} must be a lowercase SHA-256 value")


@dataclass(frozen=True)
class SkillDiscoveryCard:
    """Small startup card. Full instructions and file paths stay unloaded."""

    skill_id: str
    version: str
    description: str
    manifest_digest: str
    lifecycle: str
    source: str
    frontmatter_policy: str

    def __post_init__(self) -> None:
        from .skill_registry import (
            _MAXIMUM_SKILL_NAME_CHARACTERS,
            _SKILL_ID,
            AGENT_SKILLS_STRICT_POLICY,
            LOOP_ENGINE_LEGACY_FRONTMATTER_POLICY,
            SKILL_STATES,
        )

        if (
            len(self.skill_id) > _MAXIMUM_SKILL_NAME_CHARACTERS
            or not _SKILL_ID.fullmatch(self.skill_id)
            or not self.version.strip()
            or not self.description.strip()
            or self.lifecycle not in SKILL_STATES
            or not self.source.strip()
            or self.frontmatter_policy
            not in (AGENT_SKILLS_STRICT_POLICY, LOOP_ENGINE_LEGACY_FRONTMATTER_POLICY)
        ):
            raise _skill_error("skill discovery card identity is invalid")
        _require_digest(self.manifest_digest, "manifest_digest")

    @classmethod
    def from_manifest(cls, manifest: SkillManifest) -> SkillDiscoveryCard:
        from .skill_registry import SkillManifest

        if not isinstance(manifest, SkillManifest):
            raise _skill_error("a discovery card needs a SkillManifest")
        return cls(
            manifest.skill_id,
            manifest.version,
            manifest.description,
            manifest.manifest_digest,
            manifest.lifecycle,
            manifest.source,
            manifest.frontmatter_policy,
        )

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "description": self.description,
            "manifest_digest": self.manifest_digest,
            "lifecycle": self.lifecycle,
            "source": self.source,
            "frontmatter_policy": self.frontmatter_policy,
        }


@dataclass(frozen=True)
class SkillDiscoveryProjection:
    """Byte-bounded skill cards for progressive context disclosure."""

    maximum_bytes: int
    total_candidates: int
    cards: tuple[SkillDiscoveryCard, ...]
    omitted_candidates: int
    record_type: str = "skill_discovery_projection/v1"

    def __post_init__(self) -> None:
        from .skill_registry import _MINIMUM_SKILL_DISCOVERY_BYTES

        if (
            not isinstance(self.maximum_bytes, int)
            or isinstance(self.maximum_bytes, bool)
            or self.maximum_bytes < _MINIMUM_SKILL_DISCOVERY_BYTES
        ):
            raise _skill_error(
                "skill discovery maximum_bytes is below the envelope minimum"
            )
        cards = tuple(self.cards)
        if any(not isinstance(card, SkillDiscoveryCard) for card in cards):
            raise _skill_error("skill discovery cards have the wrong type")
        if self.total_candidates < len(
            cards
        ) or self.omitted_candidates != self.total_candidates - len(cards):
            raise _skill_error("skill discovery candidate accounting is invalid")
        if len({(card.skill_id, card.version) for card in cards}) != len(cards):
            raise _skill_error("skill discovery cards cannot repeat an identity")
        object.__setattr__(self, "cards", cards)
        if len(projection_json(self).encode("utf-8")) > self.maximum_bytes:
            raise _skill_error("skill discovery projection exceeds maximum_bytes")

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "maximum_bytes": self.maximum_bytes,
            "total_candidates": self.total_candidates,
            "cards": [card.to_dict() for card in self.cards],
            "omitted_candidates": self.omitted_candidates,
            "full_instructions_loaded": False,
            "supporting_files_loaded": False,
        }


def projection_json(projection: SkillDiscoveryProjection) -> str:
    """Serialize one projection for exact byte-budget checks."""
    return json.dumps(
        projection.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


__all__ = (
    "SkillDiscoveryCard",
    "SkillDiscoveryProjection",
    "projection_json",
)
