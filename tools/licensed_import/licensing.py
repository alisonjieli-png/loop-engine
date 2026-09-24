"""Licence decisions per file, the package decision, and the texts that travel with a copy.

The rule is the owner's of September 24, 2026, carried out through the
library ingestion component's licence gate (`decide_licence`), which reads
three signals for every file:

```text
One file of a package
├── its own metadata: a frontmatter licence field, a manifest's "license" field or an SPDX header
├── the nearest licence file above it, from its own folder up to the repository root
│   (every licence file of that folder must name the same licence)
└── the repository licence, which must also agree with GitHub's licence interface
```

The nearest licence file governs, the file's own metadata must agree with it,
and a repository licence counts only when GitHub reports the same licence.
A licence named only in metadata, with no licence text anywhere above the
file, leaves an idea record: the allowlisted licences all require their text
and the copyright notice to travel with a copy, and there is none to carry.

A package is copied only when every one of its files may be copied under a
licence on the owner's allowlist (MIT, Apache-2.0, BSD-2-Clause,
BSD-3-Clause, ISC, 0BSD, CC0-1.0, CC-BY-4.0, Unlicense). A package with one
file that may not be copied becomes an idea record whole; a licence that
forbids derivative works, or that binds a reader to outside terms, leaves a
refusal and nothing else. The copied files are never changed: each package
carries the governing licence texts, every notice file and one generated
attribution file. These are engineering rules that carry out the owner's
direction, not legal advice.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from loop_engine.core.library_ingestion.licences import (
    LicenceFile, LicencePolicy, decide_licence, is_licence_file, is_notice_file)
from loop_engine.core.library_ingestion.provenance import OUTLINE_ONLY, REFUSED, VERBATIM
from loop_engine.core.library_ingestion.record_rules import bytes_digest
from loop_engine.core.library_ingestion.source_github import frontmatter_licence

from .records import ALLOWED_LICENCES

POLICY = LicencePolicy(accepted=ALLOWED_LICENCES)
_SPDX_HEADER = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+(?: (?:AND|OR|WITH) [A-Za-z0-9.+-]+)*)")
_HEADER_LINES = 30
ATTRIBUTION_NAME = "ATTRIBUTION.md"
#: Manifests whose "license" field states the licence of the files they describe.
_MANIFEST_NAMES = frozenset({"plugin.json", "package.json", "gemini-extension.json", "marketplace.json"})
_DECISION_ORDER = {REFUSED: 0, OUTLINE_ONLY: 1, VERBATIM: 2}


@dataclass(frozen=True)
class PackageLicence:
    """What the licence evidence of every file of one package permits, and what travels with a copy."""

    decision: str
    spdx_expression: str
    reason: str
    per_file: dict
    carried: tuple
    primary_evidence: dict


def text_of(payload: bytes) -> "str | None":
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return None


def own_metadata_licence(path: str, payload: bytes) -> "str | None":
    """The licence a file names about itself: frontmatter, or a JSON manifest's licence field."""
    text = text_of(payload)
    if text is None:
        return None
    if text.startswith("---"):
        return frontmatter_licence(text)
    if PurePosixPath(path).name.lower() in _MANIFEST_NAMES:
        try:
            value = json.loads(text)
        except ValueError:
            return None
        found = value.get("license") if isinstance(value, dict) else None
        if isinstance(found, dict):
            found = found.get("type")
        return found.strip() if isinstance(found, str) and found.strip() else None
    return None


def spdx_headers(payload: bytes) -> tuple:
    text = text_of(payload)
    if text is None:
        return ()
    head = "\n".join(text.splitlines()[:_HEADER_LINES])
    return tuple(match.group(1) for match in _SPDX_HEADER.finditer(head))


def licence_file_set(licence_bytes: dict, root_path: "str | None", github_spdx: "str | None") -> dict:
    """LicenceFile records for the gate: every licence file read, the root one with GitHub's finding."""
    files = {}
    for path, payload in licence_bytes.items():
        if not is_licence_file(path):
            continue
        files[path] = LicenceFile(path, bytes_digest(payload), payload.decode("utf-8", "replace"),
                                  github_spdx if path == root_path else None)
    return files


def root_licence_path(licence_paths) -> "str | None":
    """The repository's own licence file: the first licence file at the root, as the gate orders them."""
    roots = sorted(path for path in licence_paths if "/" not in path and is_licence_file(path))
    return roots[0] if roots else None


def decide_package(members: dict, primary: str, licence_bytes: dict, *, github_spdx: "str | None",
                   policy: LicencePolicy = POLICY) -> PackageLicence:
    """Decide every member, then the package: the weakest member decides for all."""
    root = root_licence_path(licence_bytes)
    files = licence_file_set(licence_bytes, root, github_spdx)
    per_file, carried = {}, set()
    for path, payload in sorted(members.items()):
        # A licence or notice text inside the package is carried, not decided; the primary file
        # is always decided, even when its name looks like one (a command named license-check.md).
        if path != primary and (is_licence_file(path) or is_notice_file(path)):
            continue
        folder_notices = tuple(
            (notice, bytes_digest(licence_bytes[notice])) for notice in sorted(licence_bytes)
            if is_notice_file(notice) and _governs(notice, path))
        evidence = decide_licence(path, files, root_path=root, frontmatter_licence=own_metadata_licence(path, payload),
                                  item_sha256=bytes_digest(payload), spdx_headers=spdx_headers(payload),
                                  notice_files=folder_notices, policy=policy)
        per_file[path] = evidence
        if evidence["decision"] == VERBATIM:
            carried.add(evidence["governing_file"]["path"])
            carried.update(notice for notice, _digest in folder_notices)
    if not per_file:
        raise ValueError("a package needs at least one file that is not a licence file")
    weakest = min(per_file.items(), key=lambda item: (_DECISION_ORDER[item[1]["decision"]], item[0] != primary))
    decision = weakest[1]["decision"]
    if decision == VERBATIM:
        expression = " AND ".join(sorted({evidence["spdx_expression"] for evidence in per_file.values()}))
        reason = per_file.get(primary, weakest[1])["reason"]
    else:
        expression, reason = weakest[1]["spdx_expression"], weakest[1]["reason"]
    return PackageLicence(decision, expression, reason, per_file,
                          tuple(sorted(carried)) if decision == VERBATIM else (),
                          per_file.get(primary, weakest[1]))


def _governs(notice: str, path: str) -> bool:
    """A notice file governs every file in its folder and below."""
    folder = str(PurePosixPath(notice).parent)
    return folder in (".", "") or path.startswith(folder + "/")


def carried_placements(carried, package_paths) -> dict:
    """Package paths for the licence and notice texts that travel with a copy, never over a member."""
    taken = {path.casefold() for path in package_paths}
    placed = {}
    for upstream in carried:
        name = PurePosixPath(upstream).name
        for candidate in (name, f"UPSTREAM-{name}", *(f"UPSTREAM-{index}-{name}" for index in range(2, 50))):
            if candidate.casefold() not in taken:
                placed[upstream] = candidate
                taken.add(candidate.casefold())
                break
    return placed


def attribution_text(*, repository: str, commit: str, spdx: str, rows, licence_names, imported_on: str) -> bytes:
    """The one generated file of a copied package: where every file came from, and under what licence."""
    lines = ["# Attribution", "",
             f"The files of this package were copied without change from github.com/{repository}",
             f"at commit {commit}.", "",
             f"Licence: {spdx}. The licence text travels with this package in "
             + ", ".join(sorted(licence_names)) + ".", "",
             "| File in this package | Upstream path | SHA-256 |", "| --- | --- | --- |"]
    for package_file, upstream, digest in sorted(rows):
        lines.append(f"| {package_file} | {upstream} | {digest} |")
    lines += ["", "Copyright notices stay in the licence text and in the files themselves.",
              f"Baltor's licensed import copied these files on {imported_on} as a candidate for",
              "independent review. Baltor did not change them, and they are not reviewed or approved.", ""]
    return "\n".join(lines).encode("utf-8")
