"""Engine datasketch_minhash_lsh of the library_near_duplicate engine slot.

The adopted library: datasketch (MIT licence, version 1.6.5 in the tools
environment) builds each document's MinHash over the same word shingles
and indexes them with MinHashLSH at the declared threshold; every candidate
pair is then verified by the estimated Jaccard similarity, so the edge
returns the same shape as the built-in engine. The library is imported only
when the engine is used, and a missing library makes the engine ineligible
with the reason dependency_missing rather than breaking the component.
"""
from __future__ import annotations


def _library():
    try:
        import datasketch  # optional engine dependency, MIT licence
    except ImportError:
        return None
    return datasketch


class DatasketchMinHashLsh:
    """datasketch MinHash and MinHashLSH behind the near-duplicate edge."""

    engine_id = "datasketch_minhash_lsh"
    engine_version = "1.0.0"
    engine_kind = "near_duplicate_detector"
    effects = ("pure",)
    third_party = "datasketch (MIT), MinHash and MinHashLSH"
    dependency = "datasketch"

    def __init__(self, permutations: int = 128, seed: int = 1) -> None:
        self.permutations, self.seed = permutations, seed

    @classmethod
    def availability(cls, settings: dict):
        return (True, "available") if _library() is not None else (False, "dependency_missing")

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        library = _library()
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "library_version": getattr(library, "__version__", "unknown") if library else None,
                "permutations": self.permutations, "seed": self.seed}

    def pairs(self, documents: dict, threshold: float) -> list:
        library = _library()
        if library is None:
            raise RuntimeError("datasketch is not installed")
        hashes = {}
        for key, shingles in documents.items():
            minhash = library.MinHash(num_perm=self.permutations, seed=self.seed)
            # One vectorized update per document; the signature is the same as updating
            # shingle by shingle, about three times faster on a real round.
            minhash.update_batch([shingle.encode("utf-8") for shingle in sorted(shingles)])
            hashes[key] = minhash
        index = library.MinHashLSH(threshold=threshold, num_perm=self.permutations)
        for key in sorted(hashes):
            index.insert(key, hashes[key])
        found = set()
        for key in sorted(hashes):
            for other in index.query(hashes[key]):
                if other == key:
                    continue
                left, right = sorted((key, other))
                estimate = hashes[left].jaccard(hashes[right])
                if estimate >= threshold:
                    found.add((left, right, round(float(estimate), 4)))
        return sorted(found)
