"""Whether a registry entry's package exists at its exact version, read from its public registry.

For an npm package it reads the version document from the npm registry, and
for a PyPI package the version's JSON document from PyPI, both through the
run's bounded HTTPS transport. A 200 answer means the package resolves, a
404 means it does not and the entry is refused, and any other outcome
(another status, an exhausted request budget) is unknown and only marked
for the reviewer, never read as a pass. Container images are not checked.
"""
from __future__ import annotations

from .https_transport import quote_part
from .request_log import PauseExceedsBound, RequestCeilingReached

NPM_HOST, PYPI_HOST = "registry.npmjs.org", "pypi.org"


class PackageResolver:
    """Exact-version existence checks for npm and PyPI packages; None when unknown."""

    def __init__(self, transport) -> None:
        self.transport = transport
        self.checked: dict = {}

    def resolves(self, package: dict) -> "bool | None":
        key = (package["registry"], package["identifier"], package["version"])
        if key in self.checked:
            return self.checked[key]
        registry, identifier, version = key
        if registry == "npm":
            host, path = NPM_HOST, f"/{quote_part(identifier, safe='@')}/{quote_part(version)}"
        elif registry == "pypi":
            host, path = PYPI_HOST, f"/pypi/{quote_part(identifier)}/{quote_part(version)}/json"
        else:
            return None
        try:
            status = self.transport.get(host, path).status
        except (RequestCeilingReached, PauseExceedsBound):
            return None
        verdict = True if status == 200 else False if status == 404 else None
        self.checked[key] = verdict
        return verdict
