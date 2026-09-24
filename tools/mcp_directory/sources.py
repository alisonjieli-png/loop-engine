"""Source engines of the directory build: each reads one outside source into Listing records.

Kind: pure normalizers plus bounded readers. A normalizer turns one source entry into a Listing, or
into an Exclusion that names the rule that refused it: a status other than active, an entry that is
not the latest version, or an entry with no place to get it from. Readers fetch through the
repository's bounded read-only transport (`loop_engine.core.library_ingestion.https_transport`),
which sends only GET requests to declared hosts, follows no redirect and records every request.

Nothing here copies a README, an image or a star count. A description is kept only from the
official registry, whose terms dedicate listing metadata to the public domain, from GitHub's
directory, which carries the same publisher-written server description, and from the Docker
catalog, whose repository is under the MIT licence.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
from urllib.parse import urlsplit

from .records import (
    API, AUTH_BITS, CARGO, MCPB, NPM, NUGET, OCI, ORIGIN_MAKER, ORIGIN_OTHER, ORIGIN_UNKNOWN, PACKAGE_KINDS, PYPI,
    REMOTE_HTTP, REMOTE_SSE, SSE, STDIO, STREAMABLE_HTTP, Exclusion, Listing, Location, host_of, names_agree,
    namespace_account, namespace_domain, repository_address, repository_owner, starts_with_address, text_line,
    under_domain, without_scheme)

OFFICIAL_META = "io.modelcontextprotocol.registry/official"
ACTIVE = "active"
REGISTRY_HOST = "registry.modelcontextprotocol.io"
REGISTRY_LIST_PATH = "/v0.1/servers"
GITHUB_DIRECTORY_HOST = "api.mcp.github.com"
GITHUB_DIRECTORY_PATH = "/v0.1/servers"
DOCKER_ARCHIVE_HOST = "codeload.github.com"
DOCKER_REPOSITORY = "docker/mcp-registry"
PAGE_SIZE = 100

#: Registry package types and the transport names the registry uses.
PACKAGE_TYPES = PACKAGE_KINDS
TRANSPORTS = frozenset({STDIO, STREAMABLE_HTTP, SSE})
REMOTE_TRANSPORT_KIND = {STREAMABLE_HTTP: REMOTE_HTTP, SSE: REMOTE_SSE}
#: A server part of a registry name that says nothing about the offering, so the name leads with
#: the publisher label instead.
PLAIN_SERVER_PARTS = frozenset({"mcp", "server", "mcp-server", "remote", "api", "mcp-remote", "remote-mcp"})

_IDENTIFIERS = {
    NPM: re.compile(r"^(?:@[A-Za-z0-9][A-Za-z0-9._~-]*/)?[A-Za-z0-9][A-Za-z0-9._~-]*$"),
    PYPI: re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$"),
    OCI: re.compile(r"^[a-z0-9][a-z0-9._/-]*(?::[A-Za-z0-9._-]{1,128})?(?:@sha256:[0-9a-f]{64})?$"),
    NUGET: re.compile(r"^[A-Za-z0-9_.-]+$"),
    CARGO: re.compile(r"^[A-Za-z0-9_-]+$"),
}
_CREDENTIAL_NAME = re.compile(r"(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASSWD|ACCESS[_-]?KEY|PRIVATE[_-]?KEY|CREDENTIAL|"
                              r"AUTHORIZATION|AUTHENTICATION|\bAUTH\b|BEARER)", re.IGNORECASE)
_PAYMENT_NAME = re.compile(r"(?:PAYMENT|X-?402|WALLET)", re.IGNORECASE)
_PLACEHOLDER = re.compile(r"\{[^{}/]{1,64}\}")


def _remote_location(kind: str, url: str) -> "tuple[Location, str] | None":
    """A remote endpoint without scheme, query or fragment, and the identity that keeps its query."""
    if not isinstance(url, str):
        return None
    placeholders = _PLACEHOLDER.sub("x", url)
    try:
        parts = urlsplit(url.strip())
        checked = urlsplit(placeholders.strip())
    except ValueError:
        return None
    if not without_scheme(checked._replace(query="", fragment="").geturl()):
        return None
    host = (parts.hostname or "").lower()
    port = f":{parts.port}" if parts.port not in (None, 443) else ""
    path = parts.path.rstrip("/") if parts.path not in ("", "/") else ""
    address = host + port + path
    identity = address.lower() + ("?" + parts.query if parts.query else "")
    return Location(kind, address, SSE if kind == REMOTE_SSE else STREAMABLE_HTTP), identity


def _package_location(package: dict) -> "Location | None":
    kind = package.get("registryType")
    identifier = package.get("identifier")
    transport = ((package.get("transport") or {}).get("type") or STDIO)
    if kind not in PACKAGE_TYPES or not isinstance(identifier, str) or transport not in TRANSPORTS:
        return None
    identifier = identifier.strip()
    if kind == MCPB:
        address = without_scheme(identifier)
        return Location(kind, address, transport) if address else None
    pattern = _IDENTIFIERS[kind]
    return Location(kind, identifier, transport) if pattern.match(identifier) else None


def _arguments_digest(package: dict) -> str:
    """A short digest of a package's declared arguments, so one package that starts several servers stays several."""
    arguments = [package.get("packageArguments") or [], package.get("runtimeArguments") or []]
    if not any(arguments):
        return ""
    return "#" + hashlib.sha256(json.dumps(arguments, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def package_identity(location: Location) -> str:
    """The identity of an installable package, without its version tag."""
    value = location.value
    if location.kind == PYPI:
        value = re.sub(r"[-_.]+", "-", value).lower()
    elif location.kind == OCI:
        value = value.split("@", 1)[0]
        head, _, tail = value.rpartition(":")
        if head and "/" not in tail:
            value = head
        if value.startswith("docker.io/"):
            value = value[len("docker.io/"):]
        if value.startswith("library/"):
            value = value[len("library/"):]
        value = value.lower()
    else:
        value = value.lower()
    return f"{location.kind}:{value}"


def declared_auth(remotes, packages) -> int:
    """The sign-in bits a listing declares: a credential header or variable, a payment header, or none."""
    bits = 0
    for remote in remotes or ():
        for header in (remote.get("headers") or ()) if isinstance(remote, dict) else ():
            name = str((header or {}).get("name") or "")
            if _PAYMENT_NAME.search(name):
                bits |= AUTH_BITS["payment"]
            elif (header or {}).get("isSecret") is True or _CREDENTIAL_NAME.search(name):
                bits |= AUTH_BITS["key"]
        for variable in ((remote.get("variables") or {}).values() if isinstance(remote, dict)
                         and isinstance(remote.get("variables"), dict) else ()):
            if isinstance(variable, dict) and variable.get("isSecret") is True:
                bits |= AUTH_BITS["key"]
    for package in packages or ():
        if not isinstance(package, dict):
            continue
        for variable in package.get("environmentVariables") or ():
            name = str((variable or {}).get("name") or "")
            if (variable or {}).get("isSecret") is True or _CREDENTIAL_NAME.search(name):
                bits |= AUTH_BITS["key"]
    return bits or AUTH_BITS["none"]


def listing_origin(namespace: str, repository: str, hosts) -> str:
    """Whether the verified lister is the owner of the code or of the endpoint, by the written rules.

    A domain namespace is the maker when its code owner agrees with the domain, or, with no code
    address, when an endpoint or the website is on that domain. An io.github namespace is the maker
    when it owns the code repository. A lister whose name differs from the code owner is someone
    else. Anything else is not known.
    """
    owner = repository_owner(repository)
    domain = namespace_domain(namespace)
    account = namespace_account(namespace)
    if domain:
        if owner:
            return ORIGIN_MAKER if names_agree(owner, domain) else ORIGIN_OTHER
        return ORIGIN_MAKER if any(under_domain(host, domain) for host in hosts) else ORIGIN_UNKNOWN
    if account and owner and repository.startswith("github.com/"):
        return ORIGIN_MAKER if owner.lower() == account.lower() else ORIGIN_OTHER
    return ORIGIN_UNKNOWN


def _display_name(name: str, title: str, namespace: str) -> str:
    if title and not starts_with_address(title):
        return title
    server = name.split("/", 1)[1] if "/" in name else name
    if server.lower() in PLAIN_SERVER_PARTS:
        domain = namespace_domain(namespace)
        label = domain.split(".")[-2] if domain.count(".") >= 1 else namespace_account(namespace)
        return f"{label} {server}".strip()
    return server


def server_listing(source: str, server: dict, meta: dict, reference: str = "") -> "Listing | Exclusion":
    """One server.json entry, as the official registry and GitHub's directory publish it."""
    name = str(server.get("name") or "").strip()
    if not name or "/" not in name:
        return Exclusion(source, name or "(unnamed)", "unreadable", "an entry without a namespaced name")
    status = str(meta.get("status") or ACTIVE)
    if status != ACTIVE:
        return Exclusion(source, name, "not_active", status)
    if meta.get("isLatest") is False:
        return Exclusion(source, name, "not_latest", str(server.get("version") or ""))
    namespace = name.split("/", 1)[0]
    repository = server.get("repository") if isinstance(server.get("repository"), dict) else {}
    repo = repository_address(str(repository.get("url") or ""))
    subfolder = text_line(repository.get("subfolder"), 200) if repo else ""
    website = without_scheme(str(server.get("websiteUrl") or ""))
    if website and website.rstrip("/").lower() == repo.lower():
        website = ""
    locations, identities = [], []
    for remote in server.get("remotes") or ():
        if not isinstance(remote, dict):
            continue
        kind = REMOTE_TRANSPORT_KIND.get(str(remote.get("type") or ""))
        found = _remote_location(kind, remote.get("url")) if kind else None
        if found:
            locations.append(found[0])
            identities.append("remote:" + found[1])
    for package in server.get("packages") or ():
        location = _package_location(package) if isinstance(package, dict) else None
        if location:
            locations.append(location)
            identities.append(package_identity(location) + _arguments_digest(package))
    if not locations and not repo:
        return Exclusion(source, name, "no_location", "no package, remote endpoint or code repository")
    description = text_line(server.get("description"), 300)
    if starts_with_address(description):
        description = ""
    title = text_line(server.get("title"), 120)
    domain, account = namespace_domain(namespace), namespace_account(namespace)
    hosts = [host_of(location.value) for location in locations if location.kind.startswith("remote")]
    hosts += [host_of(website)] if website else []
    return Listing(
        source=source, key=name, name=_display_name(name, title, namespace), description=description,
        namespace=namespace, publisher=domain or account, publisher_kind="domain" if domain else "github" if account else "unknown",
        repository=repo, subfolder=subfolder, website=website, locations=tuple(dict.fromkeys(locations)),
        auth=declared_auth(server.get("remotes"), server.get("packages")),
        latest=meta.get("isLatest") is not False, updated_at=str(meta.get("updatedAt") or ""),
        published_at=str(meta.get("publishedAt") or ""),
        origin=listing_origin(namespace, repo, hosts), reference=reference or name,
        identities=tuple(sorted(set(identities))))


def registry_listing(entry: dict) -> "Listing | Exclusion":
    """One entry of the official registry's list interface."""
    server = entry.get("server") if isinstance(entry, dict) else None
    meta = ((entry.get("_meta") or {}).get(OFFICIAL_META) or {}) if isinstance(entry, dict) else {}
    if not isinstance(server, dict) or not isinstance(meta, dict):
        return Exclusion("registry", "(unreadable)", "unreadable", "an entry without server or official metadata")
    return server_listing("registry", server, meta)


def github_listing(entry: dict) -> "Listing | Exclusion":
    """One entry of GitHub's MCP directory. The licence is the one GitHub reports for the repository."""
    server = entry.get("server") if isinstance(entry, dict) else None
    meta = ((entry.get("_meta") or {}).get(OFFICIAL_META) or {}) if isinstance(entry, dict) else {}
    if not isinstance(server, dict):
        return Exclusion("github", "(unreadable)", "unreadable", "an entry without server metadata")
    listing = server_listing("github", server, meta if isinstance(meta, dict) else {})
    if isinstance(listing, Exclusion):
        return listing
    provided = ((server.get("_meta") or {}).get("io.modelcontextprotocol.registry/publisher-provided") or {})
    github = provided.get("github") if isinstance(provided, dict) else None
    licence = spdx_from_github_name(str((github or {}).get("license") or "")) if isinstance(github, dict) else ""
    origin = listing.origin if namespace_domain(listing.namespace) or namespace_account(listing.namespace) else ORIGIN_UNKNOWN
    owner = repository_owner(listing.repository)
    return Listing(**{**listing.__dict__, "licence": licence, "licence_basis": "repository" if licence else "",
                      "origin": origin, "publisher": listing.publisher or owner,
                      "publisher_kind": listing.publisher_kind if listing.publisher else ("repository" if owner else "unknown")})


#: GitHub reports a licence by its display name in the directory; the page shows the SPDX identifier.
GITHUB_LICENCE_NAMES = {
    "MIT License": "MIT", "Apache License 2.0": "Apache-2.0", "GNU Affero General Public License v3.0": "AGPL-3.0",
    "GNU General Public License v3.0": "GPL-3.0", "GNU General Public License v2.0": "GPL-2.0",
    "GNU Lesser General Public License v3.0": "LGPL-3.0", "GNU Lesser General Public License v2.1": "LGPL-2.1",
    "Mozilla Public License 2.0": "MPL-2.0", "BSD 3-Clause \"New\" or \"Revised\" License": "BSD-3-Clause",
    "BSD 2-Clause \"Simplified\" License": "BSD-2-Clause", "The Unlicense": "Unlicense", "ISC License": "ISC",
    "Creative Commons Attribution 4.0 International": "CC-BY-4.0", "Creative Commons Zero v1.0 Universal": "CC0-1.0",
    "PostgreSQL License": "PostgreSQL", "Eclipse Public License 2.0": "EPL-2.0", "Boost Software License 1.0": "BSL-1.0",
    "Other": "Other",
}


def spdx_from_github_name(name: str) -> str:
    """The SPDX identifier of a licence GitHub names, or empty when the name is not one it reports."""
    return GITHUB_LICENCE_NAMES.get(name.strip(), "")


def docker_listing(server: dict, commit: str) -> "Listing | Exclusion":
    """One server.yaml of the Docker MCP Catalog at a pinned commit."""
    name = str((server or {}).get("name") or "").strip()
    if not name:
        return Exclusion("docker", "(unnamed)", "unreadable", "a catalog entry without a name")
    about = server.get("about") if isinstance(server.get("about"), dict) else {}
    source = server.get("source") if isinstance(server.get("source"), dict) else {}
    repo = repository_address(str(source.get("project") or ""))
    subfolder = text_line(source.get("directory"), 200) if repo else ""
    locations, identities = [], []
    image = str(server.get("image") or "").strip()
    if image and _IDENTIFIERS[OCI].match(image):
        location = Location(OCI, image, STDIO)
        locations.append(location)
        identities.append(package_identity(location))
    remote = server.get("remote") if isinstance(server.get("remote"), dict) else {}
    if remote:
        kind = REMOTE_SSE if str(remote.get("transport_type") or "").lower() == SSE else REMOTE_HTTP
        found = _remote_location(kind, remote.get("url"))
        if found:
            locations.append(found[0])
            identities.append("remote:" + found[1])
    if not locations and not repo:
        return Exclusion("docker", name, "no_location", "no image, remote endpoint or code repository")
    auth = 0
    if server.get("oauth"):
        auth |= AUTH_BITS["oauth"]
    if ((server.get("config") or {}).get("secrets") if isinstance(server.get("config"), dict) else None):
        auth |= AUTH_BITS["key"]
    if remote and remote.get("headers"):
        auth |= AUTH_BITS["key"]
    description = text_line(about.get("description"), 300)
    if starts_with_address(description):
        description = ""
    title = text_line(about.get("title"), 120)
    owner = repository_owner(repo)
    meta = server.get("meta") if isinstance(server.get("meta"), dict) else {}
    return Listing(
        source="docker", key=name, name=title if title and not starts_with_address(title) else name,
        description=description, publisher=owner, publisher_kind="repository" if owner else "unknown",
        repository=repo, subfolder=subfolder, locations=tuple(locations), auth=auth or AUTH_BITS["none"],
        category_hint=str(meta.get("category") or "").lower(), origin=ORIGIN_UNKNOWN,
        reference=f"{commit}:servers/{name}/server.yaml", identities=tuple(sorted(set(identities))))


def docker_archive_listings(archive: bytes, commit: str, yaml_loader) -> "tuple[list, list]":
    """Every server.yaml in the catalog's source archive, read without extracting a file to disk."""
    listings, exclusions = [], []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        for member in bundle.getmembers():
            parts = member.name.split("/")
            if not member.isfile() or len(parts) != 4 or parts[1] != "servers" or parts[3] != "server.yaml":
                continue
            handle = bundle.extractfile(member)
            try:
                value = yaml_loader(handle.read(1_000_000).decode("utf-8")) if handle else None
            except (ValueError, UnicodeDecodeError, AttributeError) as error:
                exclusions.append(Exclusion("docker", parts[2], "unreadable", type(error).__name__))
                continue
            except Exception as error:  # noqa: BLE001 - a YAML error of one entry refuses that entry only
                exclusions.append(Exclusion("docker", parts[2], "unreadable", type(error).__name__))
                continue
            if not isinstance(value, dict):
                exclusions.append(Exclusion("docker", parts[2], "unreadable", "not a mapping"))
                continue
            found = docker_listing(value, commit)
            (exclusions if isinstance(found, Exclusion) else listings).append(found)
    return listings, exclusions


def publisher_listing(record: dict) -> "Listing | Exclusion":
    """One offering a publisher documents on its own site, from the reviewed publisher file."""
    key = str(record.get("id") or "").strip()
    docs = without_scheme(str(record.get("documentation") or ""))
    if not key or not docs:
        return Exclusion("docs", key or "(unnamed)", "unreadable", "a publisher record needs an id and its documentation")
    locations, identities = [], []
    for item in record.get("locations") or ():
        kind = str((item or {}).get("kind") or "")
        if kind in REMOTE_TRANSPORT_KIND.values():
            found = _remote_location(kind, (item or {}).get("url"))
            if found:
                locations.append(found[0])
                identities.append("remote:" + found[1])
        elif kind == API:
            address = without_scheme(str((item or {}).get("url") or ""))
            if address:
                locations.append(Location(API, address, ""))
                identities.append("api:" + address.lower())
        elif kind in PACKAGE_TYPES:
            location = _package_location({"registryType": kind, "identifier": (item or {}).get("identifier"),
                                          "transport": {"type": (item or {}).get("transport") or STDIO}})
            if location:
                locations.append(location)
                identities.append(package_identity(location))
    repo = repository_address(str(record.get("repository") or ""))
    if not locations and not repo:
        return Exclusion("docs", key, "no_location", "no endpoint, package, interface or code repository")
    auth = 0
    for name in record.get("auth") or ():
        auth |= AUTH_BITS.get(str(name), 0)
    domain = host_of(docs)
    return Listing(
        source="docs", key=key, name=text_line(record.get("name"), 120), description=text_line(record.get("description"), 300),
        publisher=text_line(record.get("publisher"), 80) or domain, publisher_kind="domain",
        repository=repo, website=docs, locations=tuple(locations), auth=auth,
        category_hint=str(record.get("category") or ""), origin=ORIGIN_MAKER, reference=docs,
        identities=tuple(sorted(set(identities))))


def read_json_page(body: bytes) -> "tuple[list, str | None]":
    """The entries and next cursor of one list page, or a ValueError for another shape."""
    value = json.loads(body)
    if not isinstance(value, dict) or not isinstance(value.get("servers"), list):
        raise ValueError("a list page is not the documented shape")
    return value["servers"], (value.get("metadata") or {}).get("nextCursor")


def repository_hosts_of(listings) -> "set[str]":
    return {listing.repository.lower() for listing in listings if listing.repository}


def unknown_origin(listing: Listing) -> Listing:
    """The same listing with its origin cleared, for a source that does not verify who listed it."""
    return Listing(**{**listing.__dict__, "origin": ORIGIN_UNKNOWN})


__all__ = [
    "ACTIVE", "DOCKER_ARCHIVE_HOST", "DOCKER_REPOSITORY", "GITHUB_DIRECTORY_HOST", "GITHUB_DIRECTORY_PATH",
    "OFFICIAL_META", "ORIGIN_OTHER", "PAGE_SIZE", "REGISTRY_HOST", "REGISTRY_LIST_PATH", "declared_auth",
    "docker_archive_listings", "docker_listing", "github_listing", "listing_origin", "package_identity",
    "publisher_listing", "read_json_page", "registry_listing", "server_listing", "spdx_from_github_name",
    "unknown_origin"]
