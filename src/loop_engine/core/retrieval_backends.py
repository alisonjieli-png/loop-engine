"""Host-bound retrieval adapters using the existing capability handshake.

Bindings are explicit dependencies, not another discovery registry. A factory
receives the caller's admitted corpus and returns the same ranked-reference
interface. No engine name imports code, resolves credentials or grants effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Protocol
from .capability_directory import CapabilityHandshake
from .capability_invocation import CapabilityInvocationPolicy, capability_handshake_digest
from .facets import EFFECTS

INPUT_SCHEMA = "retrieval_query/v1"
OUTPUT_SCHEMA = "retrieval_candidates/v1"
STAGES = ("lexical", "vector")
LEXICAL_STAGE, VECTOR_STAGE = STAGES
BUILTIN_IDENTITIES = ("fts5", "store", "lancedb", "hash", "model2vec")


class RetrievalSearchBackend(Protocol):
    """Structural interface; external packages need not inherit a base class."""
    def search(self, query: str, top_n: int) -> list[tuple[str, float]]: ...


@dataclass(frozen=True)
class RetrievalRankingPolicy:
    """Tunable ranking values, separate from embedding identity and permission."""
    reciprocal_rank_offset: float = 10.0
    facet_preference_weight: float = 0.01
    candidate_pool_multiplier: int = 2
    hash_similarity_floor: float = 0.05

    def __post_init__(self):
        for name in ("reciprocal_rank_offset", "facet_preference_weight", "hash_similarity_floor"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("ranking values must be finite nonnegative numbers")
        if (self.reciprocal_rank_offset == 0 or self.hash_similarity_floor > 1
                or type(self.candidate_pool_multiplier) is not int or self.candidate_pool_multiplier < 1):
            raise ValueError("rank offset and pool multiplier must be positive; similarity floor is at most one")


@dataclass(frozen=True)
class RetrievalBackendBinding:
    handshake: CapabilityHandshake
    stage: str
    factory: object = field(repr=False, compare=False)
    capability_note: str
    embedding_space: object = None
    handshake_digest: str = field(init=False)

    def __post_init__(self):
        if (not isinstance(self.handshake, CapabilityHandshake) or self.stage not in STAGES
                or not callable(self.factory) or not isinstance(self.capability_note, str)
                or not self.capability_note.strip()):
            raise ValueError("typed retrieval binding and explicit capability limits are required")
        if (self.handshake.surface in BUILTIN_IDENTITIES or not self.handshake.supports("search")
                or self.handshake.input_schema != INPUT_SCHEMA or self.handshake.output_schema != OUTPUT_SCHEMA):
            raise ValueError("retrieval binding must name its own exact compatible search contract")
        if self.stage == VECTOR_STAGE:
            from .retrieval import EmbeddingSpace
            if not isinstance(self.embedding_space, EmbeddingSpace):
                raise ValueError("a vector backend must identify its embedding space")
        elif self.embedding_space is not None:
            raise ValueError("a lexical backend does not declare a vector space")
        object.__setattr__(self, "handshake_digest", capability_handshake_digest(self.handshake))

    @property
    def identity(self):
        return self.handshake.surface

    def instantiate(self, records, *, authority_effects=()):
        if type(authority_effects) not in (tuple, list) or any(value not in EFFECTS for value in authority_effects):
            raise ValueError("retrieval authority must name declared effects")
        if any(effect != "pure" and effect not in authority_effects for effect in self.handshake.effects):
            raise ValueError("retrieval backend exceeds caller effect authority")
        CapabilityInvocationPolicy(expected_handshake_digest=self.handshake_digest,
                                   expected_callable=self.factory).bind(self.handshake, self.factory)
        backend = self.factory(tuple(records))
        if not callable(getattr(backend, "search", None)):
            raise ValueError("retrieval backend does not implement search(query, top_n)")
        return backend


def self_test():
    from .retrieval_backend_checks import run_self_test_checks
    return run_self_test_checks()
