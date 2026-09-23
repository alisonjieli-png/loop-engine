"""Duplicates pre-check engine ``exact_shingle_jaccard``.

Compares an item with every other body in the population: identical bytes or
an identical word sequence is an exact duplicate, and a word-shingle Jaccard
similarity at or above the declared threshold is a near duplicate. The item's
own identity is never compared with itself. The comparison is exact and runs
over every pair, so the engine declares the largest population it accepts;
above it the item is refused until the MinHash engine is installed, rather than
compared with a sample.
"""
from __future__ import annotations

import hashlib
import re

from ..records import read_part, refuse
from . import result_of

VERSION = "1"
TOKEN = re.compile(r"[a-z0-9]+")


def words(text: str) -> tuple:
    return tuple(TOKEN.findall(text.casefold()))


def shingles(text: str, size: int) -> frozenset:
    tokens = words(text)
    if len(tokens) < size:
        return frozenset({tokens}) if tokens else frozenset()
    return frozenset(tokens[index:index + size] for index in range(len(tokens) - size + 1))


def jaccard(first: frozenset, second: frozenset) -> float:
    if not first and not second:
        return 1.0
    return len(first & second) / len(first | second)


def settings_of(settings: dict, engine_id: str, extra: tuple) -> dict:
    part = read_part(settings, engine_id, ("shingle_words", "near_duplicate_threshold") + extra)
    size, threshold = part["shingle_words"], part["near_duplicate_threshold"]
    if type(size) is not int or not 1 <= size <= 20:
        refuse("invalid_precheck_settings", "shingle_words is a whole number from 1 to 20")
    if type(threshold) not in (int, float) or not 0 < threshold <= 1:
        refuse("invalid_precheck_settings", "near_duplicate_threshold is above 0 and at most 1")
    return part


class ExactShingleJaccard:
    kind = "duplicates"
    engine_id = "exact_shingle_jaccard"

    def __init__(self, settings: dict, policy) -> None:
        part = settings_of(settings, self.engine_id, ("maximum_population",))
        limit = part["maximum_population"]
        if type(limit) is not int or limit < 2:
            refuse("invalid_precheck_settings", "maximum_population is a whole number of two or more")
        self.size, self.threshold, self.limit = part["shingle_words"], float(part["near_duplicate_threshold"]), limit
        self._cache = {}

    def availability(self):
        return True, "", VERSION

    def _profile(self, identity: str, body: bytes) -> tuple:
        key = (identity, hashlib.sha256(body).hexdigest())
        if key not in self._cache:
            text = body.decode("utf-8", "replace")
            self._cache[key] = (key[1], words(text), shingles(text, self.size))
        return self._cache[key]

    def check(self, request, context):
        population = context.population
        if len(population) > self.limit:
            return result_of(self.kind, self.engine_id, VERSION, [(
                "population_too_large_for_exact_comparison",
                f"{len(population)} bodies is above the {self.limit} this engine compares exactly")])
        digest, tokens, own = self._profile(request.identity, request.body)
        findings = []
        for other, body in population.items():
            if other == request.identity:
                continue
            other_digest, other_tokens, other_shingles = self._profile(other, body)
            if other_digest == digest or other_tokens == tokens:
                findings.append(("exact_duplicate", f"the body repeats the body of {other}"))
                continue
            similarity = jaccard(own, other_shingles)
            if similarity >= self.threshold:
                findings.append(("near_duplicate", f"the body is {similarity:.3f} similar to {other}"))
        return result_of(self.kind, self.engine_id, VERSION, findings)

    def population_report(self, population) -> dict:
        """The largest similarity between two distinct bodies, and every exact duplicate, for the record."""
        profiles = {identity: self._profile(identity, body) for identity, body in population.items()}
        names = sorted(profiles)
        largest, pair, exact = 0.0, [], []
        for index, first in enumerate(names):
            for second in names[index + 1:]:
                if profiles[first][0] == profiles[second][0] or profiles[first][1] == profiles[second][1]:
                    exact.append([first, second])
                    continue
                similarity = jaccard(profiles[first][2], profiles[second][2])
                if similarity > largest:
                    largest, pair = similarity, [first, second]
        return {"bodies": len(names), "largest_similarity": round(largest, 6), "most_similar_pair": pair,
                "exact_duplicates": exact, "shingle_words": self.size, "near_duplicate_threshold": self.threshold}
