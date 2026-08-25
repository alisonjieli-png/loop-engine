"""Separate role identity from semantic relationships between Loops.

Role and profile describe what a Loop is configured to do. A relationship
describes how its work relates to another Loop. Runtime ownership, recursion
depth, and ledger sharing remain separate internal mechanics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


LOOP_RELATIONSHIP_KINDS = (
    "starting", "spawned_by", "queried_by", "retrieved_by",
    "connected_from")
LOOP_ROLES = ("practitioner", "intelligence", "solution")


class LoopRelationshipKind(str, Enum):
    STARTING = "starting"
    SPAWNED_BY = "spawned_by"
    QUERIED_BY = "queried_by"
    RETRIEVED_BY = "retrieved_by"
    CONNECTED_FROM = "connected_from"


class LoopRole(str, Enum):
    PRACTITIONER = "practitioner"
    INTELLIGENCE = "intelligence"
    SOLUTION = "solution"


@dataclass(frozen=True)
class LoopRoleIdentity:
    """One role and exact versioned role profile, independent of relationship."""

    role: LoopRole
    profile_id: str
    profile_version: str = "1.0.0"

    def __post_init__(self) -> None:
        try:
            role = LoopRole(self.role)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"role must use {LOOP_ROLES}") from exc
        object.__setattr__(self, "role", role)
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ValueError("profile_id must be a non-empty string")
        if not (self.profile_id == role.value
                or self.profile_id.startswith(role.value + ".")):
            raise ValueError(
                f"profile {self.profile_id!r} does not belong to role "
                f"{role.value!r}")
        if not re.fullmatch(
                r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)",
                self.profile_version):
            raise ValueError("profile_version must use MAJOR.MINOR.PATCH")

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "profile_id": self.profile_id,
                "profile_version": self.profile_version}

    @classmethod
    def from_dict(cls, value: dict) -> "LoopRoleIdentity":
        if not isinstance(value, dict):
            raise ValueError("role identity record must be a dictionary")
        required = {"role", "profile_id", "profile_version"}
        allowed = required | {"relationship_kind", "spawned_by_loop_id",
                              "queried_by_loop_id", "retrieved_by_loop_id",
                              "connected_from_loop_ids"}
        if not required <= set(value) or set(value) - allowed:
            raise ValueError("role identity record has an invalid shape")
        return cls(value["role"], value["profile_id"], value["profile_version"])


@dataclass(frozen=True)
class LoopRelationship:
    """One closed semantic relationship between this Loop and related Loops."""

    kind: LoopRelationshipKind
    spawned_by_loop_id: str = ""
    queried_by_loop_id: str = ""
    retrieved_by_loop_id: str = ""
    connected_from_loop_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            kind = LoopRelationshipKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"relationship kind must use {LOOP_RELATIONSHIP_KINDS}") from exc
        object.__setattr__(self, "kind", kind)
        for name in ("spawned_by_loop_id", "queried_by_loop_id",
                     "retrieved_by_loop_id"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be a string")
        connected = tuple(self.connected_from_loop_ids)
        if (any(not isinstance(value, str) or not value.strip()
                for value in connected)
                or len(connected) != len(set(connected))):
            raise ValueError(
                "connected_from_loop_ids must contain unique non-empty IDs")
        object.__setattr__(self, "connected_from_loop_ids", connected)
        populated = {
            LoopRelationshipKind.SPAWNED_BY: bool(self.spawned_by_loop_id),
            LoopRelationshipKind.QUERIED_BY: bool(self.queried_by_loop_id),
            LoopRelationshipKind.RETRIEVED_BY: bool(self.retrieved_by_loop_id),
            LoopRelationshipKind.CONNECTED_FROM: bool(connected),
        }
        if kind == LoopRelationshipKind.STARTING:
            if any(populated.values()):
                raise ValueError("starting relationship cannot name another Loop")
        elif not populated[kind] or sum(populated.values()) != 1:
            raise ValueError(
                f"{kind.value} must populate only its matching relationship field")

    @classmethod
    def starting(cls) -> "LoopRelationship":
        return cls(LoopRelationshipKind.STARTING)

    @classmethod
    def spawned_by(cls, loop_id: str) -> "LoopRelationship":
        return cls(LoopRelationshipKind.SPAWNED_BY,
                   spawned_by_loop_id=loop_id)

    @classmethod
    def queried_by(cls, loop_id: str) -> "LoopRelationship":
        return cls(LoopRelationshipKind.QUERIED_BY,
                   queried_by_loop_id=loop_id)

    @classmethod
    def retrieved_by(cls, loop_id: str) -> "LoopRelationship":
        return cls(LoopRelationshipKind.RETRIEVED_BY,
                   retrieved_by_loop_id=loop_id)

    @classmethod
    def connected_from(cls, loop_ids) -> "LoopRelationship":
        return cls(LoopRelationshipKind.CONNECTED_FROM,
                   connected_from_loop_ids=tuple(loop_ids))

    def to_dict(self) -> dict:
        value = {"relationship_kind": self.kind.value}
        field = {
            LoopRelationshipKind.SPAWNED_BY: "spawned_by_loop_id",
            LoopRelationshipKind.QUERIED_BY: "queried_by_loop_id",
            LoopRelationshipKind.RETRIEVED_BY: "retrieved_by_loop_id",
            LoopRelationshipKind.CONNECTED_FROM: "connected_from_loop_ids",
        }.get(self.kind)
        if field:
            item = getattr(self, field)
            value[field] = list(item) if isinstance(item, tuple) else item
        return value

    @classmethod
    def from_dict(cls, value: dict) -> "LoopRelationship":
        if not isinstance(value, dict):
            raise ValueError("relationship record must be a dictionary")
        kind = LoopRelationshipKind(value.get("relationship_kind", ""))
        expected = {"relationship_kind"}
        fields = {
            LoopRelationshipKind.SPAWNED_BY: "spawned_by_loop_id",
            LoopRelationshipKind.QUERIED_BY: "queried_by_loop_id",
            LoopRelationshipKind.RETRIEVED_BY: "retrieved_by_loop_id",
            LoopRelationshipKind.CONNECTED_FROM: "connected_from_loop_ids",
        }
        if kind in fields:
            expected.add(fields[kind])
        if set(value) != expected:
            raise ValueError("relationship record has an invalid current shape")
        if kind == LoopRelationshipKind.STARTING:
            return cls.starting()
        item = value[fields[kind]]
        return {
            LoopRelationshipKind.SPAWNED_BY: cls.spawned_by,
            LoopRelationshipKind.QUERIED_BY: cls.queried_by,
            LoopRelationshipKind.RETRIEVED_BY: cls.retrieved_by,
            LoopRelationshipKind.CONNECTED_FROM: cls.connected_from,
        }[kind](item)
