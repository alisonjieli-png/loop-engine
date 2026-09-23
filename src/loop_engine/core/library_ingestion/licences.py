"""The licence gate for outside material: evidence first, then a decision.

A file may be copied verbatim only when the licence that governs it is on
the accepted list and the licence file itself proves it. The governing file
is the licence file nearest to the item (a folder's own LICENSE.txt
overrides the repository licence). Its text is compared with stored word
sets of the canonical licence texts (the Sorensen-Dice coefficient on
distinct words, the method licensee uses), and a repository licence must
also agree with what GitHub's licence interface reports. A notice on the
file itself (a frontmatter licence or an SPDX header) must agree too.

Everything else is decided conservatively. No licence file, an unrecognized
text, a recognized licence the policy does not list, disagreeing signals or
a disagreeing notice keep only an outline of the abstract purpose. A text
that forbids derivative works, or that makes reading or using the material an
agreement to a provider's own terms, refuses the outline as well. The stored word
sets come from github/choosealicense.com (MIT) at a pinned commit; the
texts themselves are not stored. This is an engineering rule that carries
out the owner's direction, not legal advice.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath

from .provenance import (
    LICENCE_EVIDENCE_RECORD_TYPE, NO_ASSERTION, NO_LICENCE, OUTLINE_ONLY, REFUSED, VERBATIM,
    spdx_expression)
from .record_rules import LibraryRecordError, bytes_digest, read_part, read_record

TEMPLATES_RECORD_TYPE = "library_licence_templates/v1"
POLICY_RECORD_TYPE = "library_licence_policy/v1"
TEMPLATES_FILE = Path(__file__).with_name("licence_templates.json")
DETECTOR = "licence_word_dice/v1 with the GitHub licence interface for repository licences"

#: The owner's list of clear permissive licences for verbatim import (September 22, 2026).
DEFAULT_ACCEPTED = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0",
                    "CC-BY-4.0")
#: The one match reason under which a text counts as the licence it resembles.
RECOGNIZED = "recognized"
#: licensee's own default confidence for its word-set matcher is 98 percent.
DEFAULT_MINIMUM_SIMILARITY = 0.98
#: The best template must beat the next one by this much, or the text is ambiguous.
DEFAULT_MINIMUM_MARGIN = 0.01

_LICENCE_NAME = re.compile(r"(?:licen[cs]e|copying|unlicense)(?:[-_.][a-z0-9-]+)?(?:\.(?:md|txt|rst))?\Z",
                           re.I)
_NOTICE_NAME = re.compile(r"notice(?:\.(?:md|txt))?\Z", re.I)
_OPTIONAL_SECTIONS = (
    r"creative commons legal code",
    r"creative commons corporation is not a law firm.*?provided hereunder\.",
    r"for more information,? please see",
    r"appendix: how to apply the apache license.*\Z",
    r"creative commons is not a party to its public licen[cs]es.*\Z",
    r"statement of purpose",
)
_SPELLINGS = (("licence", "license"), ("licenced", "licensed"), ("licencing", "licensing"))
_PROHIBITION = re.compile(
    r"(?:may not|must not|shall not|not permitted to|prohibited from|you are not allowed to)"
    r"[^.]{0,240}?(?:derivative works?|reproduce|modify|adapt|translate)", re.S)
_FILE_REFERENCE = re.compile(r"((?:licen[cs]e|copying)(?:\.(?:md|txt))?)\b", re.I)
#: A notice that ties whoever reads or uses the material to a provider's own terms. Accepting
#: outside terms is a legal commitment only the owner can make, so such material leaves nothing.
_OUTSIDE_TERMS = (
    re.compile(r"\bby\s+(?:accessing|downloading|using|installing|copying|viewing|reading)\b[^.]{0,300}?"
               r"\byou\s+(?:agree|accept|consent)\b", re.S),
    re.compile(r"\b(?:use|access|usage)\b[^.]{0,200}?\bis\s+governed\s+by\b[^.]{0,200}?"
               r"\b(?:terms|agreement|conditions)\b", re.S))


@dataclass(frozen=True)
class LicenceTemplate:
    """The distinct normalized words of one canonical licence text, and where they came from."""

    spdx: str
    words: frozenset
    source_path: str
    source_sha256: str
    forbidden_markers: tuple = ()


@dataclass(frozen=True)
class LicenceMatch:
    """What a text matched: an accepted identification, or the best guess and why it failed."""

    spdx: "str | None"
    best: "str | None"
    similarity: float
    runner_up: "str | None"
    runner_up_similarity: float
    reason: str


@dataclass(frozen=True)
class LicenceFile:
    """One licence file: its path, digest, text and, for the repository licence, GitHub's finding."""

    path: str
    sha256: str
    text: str
    github_spdx_id: "str | None" = None


@dataclass(frozen=True)
class LicencePolicy:
    """The exact licences this host accepts for verbatim import. A list replaces the default."""

    accepted: tuple = DEFAULT_ACCEPTED
    minimum_similarity: float = DEFAULT_MINIMUM_SIMILARITY
    minimum_margin: float = DEFAULT_MINIMUM_MARGIN
    record_type: str = POLICY_RECORD_TYPE

    def __post_init__(self) -> None:
        if self.record_type != POLICY_RECORD_TYPE:
            raise LibraryRecordError("unsupported_record_version", f"this release reads {POLICY_RECORD_TYPE}")
        names = self.accepted
        known = set(load_templates())
        if (type(names) not in (tuple, list) or not names or len(set(names)) != len(names)
                or any(type(name) is not str or name not in known for name in names)):
            raise LibraryRecordError("invalid_licence_policy",
                                     "accepted licences are distinct identifiers of stored licence "
                                     "templates; no licence, an unknown name or an expression is not one")
        if not 0.9 <= self.minimum_similarity <= 1 or not 0 <= self.minimum_margin <= 0.2:
            raise LibraryRecordError("invalid_licence_policy", "the similarity bounds are out of range")
        object.__setattr__(self, "accepted", tuple(names))

    def to_record(self) -> dict:
        return {"record_type": self.record_type, "accepted": list(self.accepted),
                "minimum_similarity": self.minimum_similarity,
                "minimum_margin": self.minimum_margin}


def licence_words(text: str) -> frozenset:
    """Distinct normalized words: copyright lines, addresses and placeholders removed."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            text = text[end + 5:]
    lowered = re.sub(r"https?://\S+", " ", text.lower())
    kept = [line for line in lowered.splitlines()
            if not re.match(r"\s*(?:copyright|\(c\)|\u00a9)", line) and "all rights reserved" not in line]
    joined = "\n".join(kept)
    for section in _OPTIONAL_SECTIONS:
        joined = re.sub(section.replace(" ", r"\s+"), " ", joined, flags=re.S)
    joined = re.sub(r"\[[^\]]{0,40}\]|<[^>]{0,40}>|\{[^}]{0,40}\}", " ", joined)
    for british, american in _SPELLINGS:
        joined = joined.replace(british, american)
    return frozenset(re.sub(r"[^a-z0-9]+", " ", joined).split())


@lru_cache(maxsize=4)
def _templates_at(path: str) -> dict:
    record = read_record(json.loads(Path(path).read_text(encoding="utf-8")), TEMPLATES_RECORD_TYPE,
                         ("source", "normalizer", "templates"))
    read_part(record["source"], "source", ("repository", "commit", "fetched_at"))
    templates = {}
    for row in record["templates"]:
        read_part(row, "template", ("spdx", "path", "sha256", "words", "forbidden_markers"))
        spdx_expression(row["spdx"], "template.spdx")
        templates[row["spdx"]] = LicenceTemplate(row["spdx"], frozenset(row["words"]), row["path"],
                                                 row["sha256"], tuple(row["forbidden_markers"]))
    return templates


def load_templates(path: "Path | None" = None) -> dict:
    return _templates_at(str(path or TEMPLATES_FILE))


def _dice(left: frozenset, right: frozenset) -> float:
    return 2 * len(left & right) / (len(left) + len(right)) if left or right else 0.0


def match_words(words: frozenset, templates: "dict | None" = None,
                policy: "LicencePolicy | None" = None) -> LicenceMatch:
    """Identify a word set only when the best template is close, unique and unmarked."""
    templates = templates or load_templates()
    minimum = policy.minimum_similarity if policy else DEFAULT_MINIMUM_SIMILARITY
    margin = policy.minimum_margin if policy else DEFAULT_MINIMUM_MARGIN
    ranked = sorted(((_dice(words, template.words), spdx) for spdx, template in templates.items()),
                    reverse=True)
    (best_score, best), (next_score, runner) = ranked[0], ranked[1]
    marked = [marker for marker in templates[best].forbidden_markers if marker in words]
    if best_score < minimum:
        reason = "below_minimum_similarity"
    elif best_score - next_score < margin:
        reason = "ambiguous_between_templates"
    elif marked:
        reason = "carries_a_word_the_template_forbids"
    else:
        reason = RECOGNIZED
    return LicenceMatch(best if reason == RECOGNIZED else None, best, round(best_score, 4), runner,
                        round(next_score, 4), reason)


def match_licence(text: str, templates: "dict | None" = None,
                  policy: "LicencePolicy | None" = None) -> LicenceMatch:
    return match_words(licence_words(text), templates, policy)


def prohibits_recreation(text: str) -> bool:
    """True when a licence text forbids derivative works, copies or adaptations."""
    return bool(_PROHIBITION.search(re.sub(r"\s+", " ", text.lower())))


def binds_to_outside_terms(text: str) -> bool:
    """True when a licence text makes reading or using the material an agreement to other terms."""
    folded = re.sub(r"\s+", " ", text.lower())
    return any(pattern.search(folded) for pattern in _OUTSIDE_TERMS)


def is_licence_file(path: str) -> bool:
    return bool(_LICENCE_NAME.match(PurePosixPath(path).name))


def is_notice_file(path: str) -> bool:
    return bool(_NOTICE_NAME.match(PurePosixPath(path).name))


def governing_licence_path(item_path: str, licence_paths) -> "str | None":
    """The licence file in the nearest folder that holds one, from the item's folder up to the root."""
    by_folder: dict = {}
    for path in sorted(licence_paths):
        by_folder.setdefault(str(PurePosixPath(path).parent), path)
    folder = PurePosixPath(item_path).parent
    while True:
        found = by_folder.get(str(folder))
        if found is not None:
            return found
        if str(folder) in (".", ""):
            return None
        folder = folder.parent


def _canonical_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


_ALIASES = {"mitlicense": "MIT", "apache20": "Apache-2.0", "apachelicense20": "Apache-2.0",
            "apachelicenseversion20": "Apache-2.0", "apache2": "Apache-2.0", "cc0": "CC0-1.0",
            "ccby40": "CC-BY-4.0", "bsd3clause": "BSD-3-Clause", "bsd2clause": "BSD-2-Clause",
            "isclicense": "ISC"}


def notice_identifier(value: str, templates: "dict | None" = None) -> "str | None":
    """The licence a short notice names, or None when it names none this gate knows."""
    templates = templates or load_templates()
    wanted = _canonical_id(value)
    for spdx in templates:
        if _canonical_id(spdx) == wanted:
            return spdx
    return _ALIASES.get(wanted)


def _governing_part(governing: "LicenceFile | None", match: "LicenceMatch | None"):
    if governing is None:
        return None
    return {"path": governing.path, "sha256": governing.sha256,
            "matched_spdx": match.spdx if match else None,
            "similarity": match.similarity if match else None}


def _evidence(spdx: str, decision: str, reason: str, *, repository, governing, notices) -> dict:
    return {"record_type": LICENCE_EVIDENCE_RECORD_TYPE, "spdx_expression": spdx,
            "decision": decision, "reason": reason, "detector": DETECTOR,
            "repository_licence": repository, "governing_file": governing,
            "file_level_notices": list(notices)}


@dataclass(frozen=True)
class _Notice:
    kind: str
    path: str
    sha256: str
    value: str
    names: "str | None" = None
    file_reference: "str | None" = None
    extra: dict = field(default_factory=dict)


def _read_notice(kind: str, path: str, sha256: str, value: str, templates) -> _Notice:
    reference = _FILE_REFERENCE.search(value)
    return _Notice(kind, path, sha256, value.strip()[:512] or "(empty)", notice_identifier(value, templates),
                   reference.group(1) if reference and notice_identifier(value, templates) is None else None)


#: Why a verbatim decision was lowered to an outline: the curated source list reads this source for outlines.
CURATED_FOR_OUTLINES = "source_curated_for_outlines"


def cap_to_outline(evidence: dict, reason: str = CURATED_FOR_OUTLINES) -> dict:
    """The same evidence with a verbatim decision lowered to an outline; any other decision is kept.

    A source curated for outlines never yields a verbatim copy, whatever its
    files say at run time: curation is a ceiling on what a source may give.
    """
    if evidence["decision"] != VERBATIM:
        return evidence
    return {**evidence, "decision": OUTLINE_ONLY, "reason": reason}


def decide_licence(item_path: str, licence_files: dict, *, root_path: "str | None" = None,
                   frontmatter_licence: "str | None" = None, item_sha256: str = "",
                   spdx_headers=(), notice_files=(), policy: "LicencePolicy | None" = None) -> dict:
    """Return outside_licence_evidence/v1 for one item from the licence files that could govern it."""
    policy = policy or LicencePolicy()
    templates = load_templates()
    notices = []
    root_file = licence_files.get(root_path) if root_path else None
    root_match = match_licence(root_file.text, templates, policy) if root_file else None
    repository = None if root_file is None else {
        "path": root_file.path, "sha256": root_file.sha256, "github_spdx_id": root_file.github_spdx_id,
        "matched_spdx": root_match.spdx, "similarity": root_match.similarity}
    governing_path = governing_licence_path(item_path, set(licence_files))
    governing = licence_files.get(governing_path) if governing_path else None
    match = None
    if governing is not None:
        match = root_match if governing is root_file else match_licence(governing.text, templates, policy)
        notices.append({"kind": "licence_file", "path": governing.path, "sha256": governing.sha256,
                        "value": match.spdx or f"unrecognized, closest {match.best}"})
    for path, sha256 in notice_files:
        notices.append({"kind": "notice_file", "path": path, "sha256": sha256, "value": "notice file"})
    file_notices = []
    if frontmatter_licence is not None:
        file_notices.append(_read_notice("frontmatter_licence", item_path, item_sha256 or bytes_digest(b""),
                                         str(frontmatter_licence), templates))
    for header in spdx_headers:
        file_notices.append(_read_notice("spdx_header", item_path, item_sha256 or bytes_digest(b""),
                                         str(header), templates))
    for notice in file_notices:
        notices.append({"kind": notice.kind, "path": notice.path, "sha256": notice.sha256,
                        "value": notice.value})

    def outcome(spdx, decision, reason):
        return _evidence(spdx, decision, reason, repository=repository,
                         governing=_governing_part(governing, match), notices=notices)

    notice_texts = " ".join(notice.value for notice in file_notices)
    if notice_texts and prohibits_recreation(notice_texts):
        return outcome(NO_ASSERTION, REFUSED, "file_level_notice_prohibits_derivatives")
    if notice_texts and binds_to_outside_terms(notice_texts):
        return outcome(NO_ASSERTION, REFUSED, "file_level_notice_binds_to_outside_terms")
    if governing is None:
        return outcome(NO_LICENCE, OUTLINE_ONLY, "no_licence_file")
    if match.spdx is None:
        # The prohibition rule reads only a text no template recognizes. A known
        # licence's own terms are known, and several of them use the same words
        # ("shall not", "derivative works") without forbidding an adaptation.
        if prohibits_recreation(governing.text):
            return outcome(NO_ASSERTION, REFUSED, "licence_prohibits_derivatives")
        if binds_to_outside_terms(governing.text):
            return outcome(NO_ASSERTION, REFUSED, "licence_binds_to_outside_terms")
        return outcome(NO_ASSERTION, OUTLINE_ONLY, f"licence_text_{match.reason}")
    if governing is root_file:
        github = root_file.github_spdx_id
        if github in (None, NO_ASSERTION, "other"):
            return outcome(NO_ASSERTION, OUTLINE_ONLY, "repository_licence_not_asserted")
        if github != match.spdx:
            return outcome(NO_ASSERTION, OUTLINE_ONLY, "repository_licence_signals_disagree")
    if match.spdx not in policy.accepted:
        return outcome(match.spdx, OUTLINE_ONLY, "licence_not_on_accepted_list")
    for notice in file_notices:
        if notice.names is not None:
            if notice.names != match.spdx:
                return outcome(match.spdx, OUTLINE_ONLY, "licence_notices_disagree")
        elif notice.file_reference is not None:
            if notice.file_reference.lower() != PurePosixPath(governing.path).name.lower():
                return outcome(match.spdx, OUTLINE_ONLY, "licence_notices_disagree")
        else:
            return outcome(match.spdx, OUTLINE_ONLY, "file_level_notice_not_recognized")
    reason = "repository_licence_accepted" if governing is root_file else "nested_licence_file_accepted"
    return outcome(match.spdx, VERBATIM, reason)
