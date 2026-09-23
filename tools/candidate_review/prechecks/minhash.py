"""Duplicates pre-check engine ``datasketch_minhash_lsh``: MinHash with locality-sensitive hashing.

Adopted library: datasketch (MIT licence, ``ekzhu/datasketch``). An index of
MinHash signatures finds the bodies that are likely near duplicates without
comparing every pair, which the exact engine cannot do for tens of thousands
of bodies. MinHash only estimates similarity, so every candidate the index
returns is confirmed with the exact Jaccard similarity of its shingles before
it refuses anything. The library is optional: without it this engine is
unavailable and the exact engine decides the kind for populations it accepts.
"""
from __future__ import annotations

import hashlib
import importlib

from ..records import refuse
from . import result_of
from .duplicates import jaccard, settings_of, shingles, words

LIBRARY = "datasketch"


class DatasketchMinHash:
    kind = "duplicates"
    engine_id = "datasketch_minhash_lsh"

    def __init__(self, settings: dict, policy) -> None:
        part = settings_of(settings, self.engine_id, ("permutations",))
        permutations = part["permutations"]
        if type(permutations) is not int or not 16 <= permutations <= 1024:
            refuse("invalid_precheck_settings", "permutations is a whole number from 16 to 1024")
        self.size, self.threshold = part["shingle_words"], float(part["near_duplicate_threshold"])
        self.permutations = permutations
        self._index = None

    def _library(self):
        return importlib.import_module(LIBRARY)

    def availability(self):
        try:
            library = self._library()
        except ImportError:
            return False, f"the {LIBRARY} library (MIT licence) is not installed in this interpreter", ""
        return True, "", f"{LIBRARY} {getattr(library, '__version__', 'unknown version')}"

    def _signature(self, library, profile) -> object:
        signature = library.MinHash(num_perm=self.permutations)
        for shingle in profile:
            signature.update(" ".join(shingle).encode("utf-8"))
        return signature

    def _built(self, population):
        key = hashlib.sha256("\n".join(f"{identity}:{hashlib.sha256(body).hexdigest()}"
                                       for identity, body in sorted(population.items())).encode()).hexdigest()
        if self._index is None or self._index[0] != key:
            library = self._library()
            index = library.MinHashLSH(threshold=self.threshold, num_perm=self.permutations)
            profiles, digests = {}, {}
            for identity, body in population.items():
                text = body.decode("utf-8", "replace")
                profiles[identity] = (words(text), shingles(text, self.size))
                digests.setdefault(hashlib.sha256(body).hexdigest(), []).append(identity)
                index.insert(identity, self._signature(library, profiles[identity][1]))
            self._index = (key, index, profiles, digests)
        return self._index

    def check(self, request, context):
        library = self._library()
        _key, index, profiles, digests = self._built(context.population)
        version = self.availability()[2]
        text = request.body_text_lenient
        tokens, own = words(text), shingles(text, self.size)
        reported = {other for other in digests.get(hashlib.sha256(request.body).hexdigest(), ())
                    if other != request.identity}
        findings = [("exact_duplicate", f"the body repeats the body of {other}") for other in sorted(reported)]
        for other in sorted(index.query(self._signature(library, own))):
            if other == request.identity or other in reported:
                continue
            if profiles[other][0] == tokens:
                findings.append(("exact_duplicate", f"the body repeats the body of {other}"))
                continue
            similarity = jaccard(own, profiles[other][1])
            if similarity >= self.threshold:
                findings.append(("near_duplicate", f"the body is {similarity:.3f} similar to {other}"))
        return result_of(self.kind, self.engine_id, version, findings)
