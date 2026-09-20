"""Versioned passive identity for trusted Solution operation implementations.

The compiler and execution boundary use this record to reject implementation
drift. It does not admit candidate code or establish independent task acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

BINDING_SCOPES = ("portable_code", "process_bound")
PORTABLE_CODE, PROCESS_BOUND = BINDING_SCOPES
RECORD_TYPE = "solution_operation_identity/v1"


@dataclass(frozen=True)
class SolutionOperationIdentity:
    """Versioned implementation binding for a supplied trusted operation.

    This identity does not admit untrusted code or establish task correctness.
    Process-bound callables cannot be replayed in another interpreter without
    an explicit recompilation against that interpreter's implementation.
    """

    operation_ref: str
    implementation_digest: str
    runtime_identity: str
    scope: str = PORTABLE_CODE

    def __post_init__(self):
        from .solution_graph import LoopGraphError

        if not isinstance(self.operation_ref, str) or not self.operation_ref.strip():
            raise LoopGraphError("operation identity requires an exact operation reference")
        if (not isinstance(self.implementation_digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", self.implementation_digest)):
            raise LoopGraphError("operation identity requires a SHA-256 implementation digest")
        if not isinstance(self.runtime_identity, str) or not self.runtime_identity:
            raise LoopGraphError("operation identity requires an interpreter identity")
        if self.scope not in BINDING_SCOPES:
            raise LoopGraphError("operation identity has an unsupported binding scope")

    def to_dict(self):
        return {"record_type": RECORD_TYPE,
                "operation_ref": self.operation_ref,
                "implementation_digest": self.implementation_digest,
                "runtime_identity": self.runtime_identity, "scope": self.scope}

    @classmethod
    def from_dict(cls, value):
        from .solution_graph import LoopGraphError

        required = {"record_type", "operation_ref", "implementation_digest",
                    "runtime_identity", "scope"}
        if (not isinstance(value, dict) or set(value) != required
                or value["record_type"] != RECORD_TYPE):
            raise LoopGraphError("operation identity has an invalid versioned encoding")
        return cls(**{key: item for key, item in value.items() if key != "record_type"})
