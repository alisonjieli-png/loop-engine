"""Engine builtin_minhash_lsh of the library_near_duplicate engine slot, in plain Python.

MinHash over word shingles with locality-sensitive hashing: each document
is reduced to 128 minimum hash values, the values are cut into 16 bands of
8, documents that share a whole band become candidate pairs, and a pair is
kept only when the share of equal values (the estimated Jaccard similarity
of the shingle sets) reaches the declared threshold. It needs no library,
so it is always available; datasketch (MIT) is the adopted engine and this
one is the declared fallback that the gates can run without installing it.
The hash of a shingle is the first eight bytes of its BLAKE2b digest, and
the permutations are fixed by a seed, so a result is the same on every run.
"""
from __future__ import annotations

import hashlib
from itertools import combinations

_PRIME = (1 << 61) - 1
_MASK = (1 << 32) - 1


class BuiltinMinHashLsh:
    """Candidate pairs by banded MinHash, verified by the estimated similarity."""

    engine_id = "builtin_minhash_lsh"
    engine_version = "1.0.0"
    engine_kind = "near_duplicate_detector"
    effects = ("pure",)
    third_party = "none; the method follows Broder's MinHash as datasketch implements it"

    def __init__(self, permutations: int = 128, bands: int = 16, seed: int = 1) -> None:
        if permutations % bands:
            raise ValueError("the permutations must divide into whole bands")
        self.permutations, self.bands, self.rows = permutations, bands, permutations // bands
        self._pairs = [self._pair(seed, index) for index in range(permutations)]

    @staticmethod
    def _pair(seed: int, index: int) -> tuple:
        digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
        return (int.from_bytes(digest[:8], "little") % (_PRIME - 1)) + 1, int.from_bytes(digest[8:16], "little") % _PRIME

    @classmethod
    def availability(cls, settings: dict):
        return True, "always_available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "permutations": self.permutations, "bands": self.bands, "rows": self.rows}

    def signature(self, shingles) -> tuple:
        values = [int.from_bytes(hashlib.blake2b(item.encode("utf-8"), digest_size=8).digest(), "little") & _MASK
                  for item in shingles]
        if not values:
            return (_MASK,) * self.permutations
        return tuple(min(((a * value + b) % _PRIME) & _MASK for value in values) for a, b in self._pairs)

    def pairs(self, documents: dict, threshold: float) -> list:
        """Every pair of keys whose estimated similarity reaches the threshold, sorted."""
        signatures = {key: self.signature(shingles) for key, shingles in documents.items()}
        buckets: dict = {}
        for key, values in signatures.items():
            for band in range(self.bands):
                chunk = values[band * self.rows:(band + 1) * self.rows]
                buckets.setdefault((band, chunk), []).append(key)
        candidates = set()
        for keys in buckets.values():
            if 1 < len(keys) <= 200:
                candidates.update(combinations(sorted(keys), 2))
        found = []
        for left, right in sorted(candidates):
            same = sum(1 for one, two in zip(signatures[left], signatures[right]) if one == two)
            estimate = same / self.permutations
            if estimate >= threshold:
                found.append((left, right, round(estimate, 4)))
        return found
