"""The licence a specification declares in its own info.license, read the same way by every mode of the API line.

```text
info.license of one specification
├── identifier (OpenAPI 3.1): one SPDX identifier, taken as written
├── name: only the exact names mapped below; a name not listed is refused, never guessed from its words
├── url
│   ├── the licence file of a GitHub repository: that repository's licence decides (the caller reads it)
│   ├── words of a licence off the allowlist (gpl, by-nc, ...) or of another listed licence: the
│   │   declaration contradicts itself and names no licence
│   └── otherwise neutral beside a repository's own licence (curated mode), and required to confirm the
│       name where it is the only second signal (directory mode)
└── the text of a declared licence: github/choosealicense.com at the commit the licence matcher pins,
    its SHA-256 checked against licence_templates.json
```

The OpenAPI specification describes info.license as the licence of the exposed
API. The API line reads it as the specification's own declaration beside the
licence of the repository that publishes the file: a declaration off the
allowlist refuses the specification, and a second allowlisted licence travels
with the package beside the repository's.
"""
from __future__ import annotations

import json
import re

from loop_engine.core.library_ingestion.licences import TEMPLATES_FILE

from .licences import AGREED, RepositoryLicence
from .records import SupplyRecordError

LICENCE_TEXT_REPOSITORY = "github/choosealicense.com"
#: The licence names specifications declare, mapped to SPDX identifiers. Only exact names are mapped.
DECLARED_LICENCE_NAMES = {
    "MIT": "MIT", "MIT License": "MIT", "The MIT License (MIT)": "MIT", "Distributed under the MIT license": "MIT",
    "Apache 2.0": "Apache-2.0", "Apache 2.0 License": "Apache-2.0", "Apache-2.0": "Apache-2.0",
    "Apache v2 License": "Apache-2.0", "Apache License 2.0": "Apache-2.0", "Apache License, Version 2.0": "Apache-2.0",
    "BSD-3-Clause": "BSD-3-Clause", "BSD-2-Clause": "BSD-2-Clause", "ISC": "ISC", "CC0 1.0": "CC0-1.0",
    "CC0-1.0": "CC0-1.0", "Unlicense": "Unlicense", "CC-BY-4.0": "CC-BY-4.0", "Creative Commons": "CC-BY-4.0",
    "CC-BY 4.0": "CC-BY-4.0", "Creative Commons Attribution 4.0 International": "CC-BY-4.0",
    "Creative Commons Attribution 4.0 International Public License": "CC-BY-4.0", "BSD3": "BSD-3-Clause",
    "CC BY 4.0": "CC-BY-4.0", "Apache2": "Apache-2.0", "MIT license": "MIT"}
#: Names that say which licence only together with an address: "Creative Commons" is CC-BY-4.0 only when its
#: address is that licence's.
NAMES_NEEDING_AN_ADDRESS = frozenset({"Creative Commons"})
#: The address patterns that name each listed licence (word bounded, so "commit" never reads as MIT).
LICENCE_ADDRESS_PATTERNS = {
    "MIT": re.compile(r"\bmit\b"),
    "Apache-2.0": re.compile(r"apache\.org/licenses|\bapache-2\.0\b|\bapache2\b"),
    "BSD-3-Clause": re.compile(r"\bbsd-3"), "BSD-2-Clause": re.compile(r"\bbsd-2"), "ISC": re.compile(r"\bisc\b"),
    "CC0-1.0": re.compile(r"\bcc0\b|publicdomain/zero"), "Unlicense": re.compile(r"\bunlicense\b"),
    "CC-BY-4.0": re.compile(r"/by/4\.0|\bcc-by-4\.0\b")}
#: Address patterns of licences off the allowlist.
OTHER_LICENCE_ADDRESS = re.compile(r"\b[al]?gpl|gnu\.org/licenses|\bmpl\b|mozilla\.org/mpl|/by-nc|/by-sa|/by-nd|"
                                   r"/by/[123]\.|\beupl\b|\bcddl\b|\bepl\b|\bsspl\b|\bbusl\b|elastic-license|"
                                   r"commons-clause")
_SPDX_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}\Z")
#: A declared licence address that is the licence file of a GitHub repository (a blob page or its raw file).
_LICENCE_FILE = re.compile(r"https://(?:github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100})/blob|"
                           r"raw\.githubusercontent\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100}))"
                           r"/[^/?#]+/(?:LICEN[CS]E|COPYING)(?:\.[A-Za-z]{1,8})?\Z")


def _written(info: dict) -> "tuple | None":
    """(identifier, name, address) as the specification wrote them, or None when it declares nothing."""
    licence = info.get("license") if isinstance(info, dict) else None
    if not isinstance(licence, dict):
        return None
    identifier = str(licence.get("identifier") or "").strip()
    name = str(licence.get("name") or "").strip()
    if not identifier and not name:
        return None
    return identifier, name, str(licence.get("url") or "").strip()


def names_another_licence(address: str, spdx: str) -> bool:
    """Whether an address names a licence other than spdx: one off the allowlist, or another listed licence."""
    text = address.lower()
    if OTHER_LICENCE_ADDRESS.search(text):
        return True
    return any(pattern.search(text) for other, pattern in LICENCE_ADDRESS_PATTERNS.items() if other != spdx)


def declared_licence(info: dict) -> "tuple | None":
    """(SPDX identifier or None, what was declared, address) where the declaration is the only second signal
    (directory mode): an identifier as written, or an exact name whose address, when given, confirms it."""
    written = _written(info)
    if written is None:
        return None
    identifier, name, address = written
    if identifier:
        return (identifier if _SPDX_IDENTIFIER.match(identifier) else None), identifier, address
    spdx = DECLARED_LICENCE_NAMES.get(name)
    if spdx and name in NAMES_NEEDING_AN_ADDRESS and not address:
        spdx = None  # the name alone does not say which licence
    if spdx and address and (not LICENCE_ADDRESS_PATTERNS[spdx].search(address.lower())
                             or names_another_licence(address, spdx)):
        spdx = None  # the address does not confirm the name, or names another licence
    return spdx, name, address


def repository_declaration(info: dict) -> "tuple | None":
    """(SPDX identifier or None, what was declared, address) for a specification a licensed repository publishes,
    whose own licence is the first signal: an identifier as written, or an exact name whose address does not name
    another licence (an address that says nothing either way, such as a private LICENSE page, is neutral)."""
    written = _written(info)
    if written is None:
        return None
    identifier, name, address = written
    if identifier:
        return (identifier if _SPDX_IDENTIFIER.match(identifier) else None), identifier, address
    spdx = DECLARED_LICENCE_NAMES.get(name)
    if spdx and name in NAMES_NEEDING_AN_ADDRESS and not LICENCE_ADDRESS_PATTERNS[spdx].search(address.lower()):
        spdx = None
    if spdx and address and names_another_licence(address, spdx):
        spdx = None
    return spdx, name, address


def licence_file_repository(address: str) -> "str | None":
    """owner/name of the GitHub repository whose licence file a declared licence address is, or None."""
    match = _LICENCE_FILE.match(str(address or ""))
    if match is None:
        return None
    owner, name = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
    return f"{owner}/{name}"


def licence_text_paths() -> tuple:
    """(SPDX identifier to (path, SHA-256) of its text, commit) in github/choosealicense.com, as the licence matcher
    of library ingestion pins them (licence_templates.json)."""
    record = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    return {row["spdx"]: (row["path"], row["sha256"]) for row in record["templates"]}, record["source"]["commit"]


class LicenceTexts:
    """Licence texts from github/choosealicense.com at the commit the licence matcher pins, each checked by SHA-256."""

    def __init__(self, reader) -> None:
        self.reader = reader
        self.paths, self.commit = licence_text_paths()
        self.found = {}

    def text(self, spdx: str) -> RepositoryLicence:
        if spdx not in self.found:
            if spdx not in self.paths:
                raise SupplyRecordError("licence_text_unknown", spdx)
            path, digest = self.paths[spdx]
            pinned = self.reader.pinned_file(LICENCE_TEXT_REPOSITORY, self.commit, path)
            if pinned["sha256"] != digest:
                raise SupplyRecordError("licence_text_changed", f"{path} is not the pinned text")
            self.found[spdx] = RepositoryLicence(LICENCE_TEXT_REPOSITORY, pinned["commit"], spdx, AGREED, path,
                                                 pinned["bytes"], spdx, spdx, 1.0)
        return self.found[spdx]


__all__ = ["DECLARED_LICENCE_NAMES", "LICENCE_TEXT_REPOSITORY", "LicenceTexts", "declared_licence",
           "licence_file_repository", "licence_text_paths", "names_another_licence", "repository_declaration"]
