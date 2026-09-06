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

    def __post_init__(self):
        if type(self.allow_fallback) is not bool:
            raise ValueError("capability fallback policy must be a boolean")
        digest = self.expected_handshake_digest
        if (not isinstance(digest, str) or (digest and (
                len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)))):
            raise ValueError("expected capability handshake digest must be empty or lowercase SHA-256")
        if self.expected_callable is not None and not callable(self.expected_callable):
            raise ValueError("expected capability implementation must be callable")

    def bind(self, handshake, function) -> bool:
        """Validate current identities and snapshot fallback before invocation."""
        self.__post_init__()
        if (self.expected_handshake_digest and self.expected_handshake_digest
                != capability_handshake_digest(handshake)):
            raise ValueError("capability handshake changed before invocation")
        if self.expected_callable is not None and function is not self.expected_callable:
            raise ValueError("capability callable changed before invocation")
        return self.allow_fallback
