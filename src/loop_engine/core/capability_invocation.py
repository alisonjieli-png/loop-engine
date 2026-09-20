"""Passive immutable policy for one existing capability-directory invocation.

The caller may forbid fallback and pin the selected handshake and callable.
This record does not register endpoints, execute work, or grant effect
authority. The directory validates it before crossing the callable boundary.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field

CAPABILITY_PROTOCOL_VERSION = "1.0.0"


def capability_handshake_digest(handshake) -> str:
    """Use the exact existing discovery serialization, including its defaults."""
    return hashlib.sha256(json.dumps(
        handshake.describe(), sort_keys=True, default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CapabilityInvocationPolicy:
    """Fallback choice and optional exact identities for one selected endpoint."""

    allow_fallback: bool = True
    expected_handshake_digest: str = ""
    expected_callable: Callable | None = field(default=None, repr=False, compare=False)
    supported_protocol_versions: tuple[str, ...] = (CAPABILITY_PROTOCOL_VERSION,)

    def __post_init__(self):
        if type(self.allow_fallback) is not bool:
            raise ValueError("capability fallback policy must be a boolean")
        digest = self.expected_handshake_digest
        if (not isinstance(digest, str) or (digest and (
                len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)))):
            raise ValueError("expected capability handshake digest must be empty or lowercase SHA-256")
        if self.expected_callable is not None and not callable(self.expected_callable):
            raise ValueError("expected capability implementation must be callable")
        versions = self.supported_protocol_versions
        if not isinstance(versions, (tuple, list)) or not versions or any(
                not isinstance(version, str) or not version.strip() for version in versions):
            raise ValueError("supported capability versions must be explicit non-empty identities")
        object.__setattr__(self, "supported_protocol_versions", tuple(versions))

    def bind(self, handshake, function) -> bool:
        """Validate current identities and snapshot fallback before invocation."""
        self.__post_init__()
        if handshake.protocol_version not in self.supported_protocol_versions:
            raise ValueError("unsupported capability protocol version")
        if (self.expected_handshake_digest and self.expected_handshake_digest
                != capability_handshake_digest(handshake)):
            raise ValueError("capability handshake changed before invocation")
        if self.expected_callable is not None and function is not self.expected_callable:
            raise ValueError("capability callable changed before invocation")
        return self.allow_fallback
