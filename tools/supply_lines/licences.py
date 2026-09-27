"""The licence of an upstream GitHub repository at a pinned commit, decided the way the licensed import decides it.

GitHub's licence interface and the licence text must name the same licence,
and that licence must be on the owner's allowlist. A repository whose two
signals disagree, whose licence nobody could name or whose licence is not on
the allowlist is refused by name; nothing is assumed from a README, a badge or
a package manifest. The decision records the file, its SHA-256 and the
similarity of the text to the licence template, so a reviewer can check it.
"""
from __future__ import annotations

from dataclasses import dataclass

from loop_engine.core.library_ingestion.licences import match_licence
from loop_engine.core.library_ingestion.record_rules import bytes_digest

from .records import ALLOWED_LICENCES

#: The decisions, in one closed vocabulary: the refusal reasons are the supply lines' own reason names.
AGREED, LICENCE_UNKNOWN, LICENCE_SIGNALS_DISAGREE, LICENCE_NOT_ON_ALLOWLIST = DECISIONS = (
    "agreed", "licence_unknown", "licence_signals_disagree", "licence_not_on_allowlist")
#: The refusals a licence that exists but cannot be copied gives, as opposed to one nobody could read.
KNOWN_LICENCE_REFUSALS = (LICENCE_SIGNALS_DISAGREE, LICENCE_NOT_ON_ALLOWLIST)
#: GitHub's own words for a licence it could not name.
_UNNAMED = (None, "NOASSERTION", "NONE")


@dataclass(frozen=True)
class RepositoryLicence:
    repository: str
    commit: str
    spdx: "str | None"  # the agreed licence, or None
    reason: str  # AGREED or the refusal reason
    path: "str | None" = None
    text: bytes = b""
    github_spdx: "str | None" = None
    matched_spdx: "str | None" = None
    similarity: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.reason == AGREED

    def refusal_reason(self, vocabulary) -> str:
        """The line's own reason for this decision: the decision itself when the line names it, else the
        allowlist refusal, which every line names."""
        return self.reason if self.reason in vocabulary else LICENCE_NOT_ON_ALLOWLIST

    @property
    def sha256(self) -> "str | None":
        return bytes_digest(self.text) if self.text else None

    def evidence(self) -> dict:
        return {"repository": self.repository, "commit": self.commit, "path": self.path, "sha256": self.sha256,
                "github_spdx_id": self.github_spdx, "matched_spdx": self.matched_spdx,
                "similarity": round(self.similarity, 4), "decision": self.reason}


def decide(repository: str, commit: str, found) -> RepositoryLicence:
    """Decide from what the reader found: (path, bytes, GitHub's SPDX identifier) or None."""
    if found is None:
        return RepositoryLicence(repository, commit, None, LICENCE_UNKNOWN)
    path, text, github = found
    try:
        matched = match_licence(text.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 - an unreadable text is an unknown licence, never a pass
        return RepositoryLicence(repository, commit, None, LICENCE_UNKNOWN, path, text, github)
    base = dict(path=path, text=text, github_spdx=github, matched_spdx=matched.spdx, similarity=matched.similarity)
    if github in _UNNAMED or matched.spdx is None:
        return RepositoryLicence(repository, commit, None, LICENCE_UNKNOWN, **base)
    if github != matched.spdx:
        return RepositoryLicence(repository, commit, None, LICENCE_SIGNALS_DISAGREE, **base)
    if github not in ALLOWED_LICENCES:
        return RepositoryLicence(repository, commit, github, LICENCE_NOT_ON_ALLOWLIST, **base)
    return RepositoryLicence(repository, commit, github, AGREED, **base)


def repository_licence(reader, repository: str, commit: str) -> RepositoryLicence:
    """Read and decide one repository's licence at an exact commit."""
    return decide(repository, commit, reader.licence_text(repository, commit))
