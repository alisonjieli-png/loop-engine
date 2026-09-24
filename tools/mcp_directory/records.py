"""Typed records of the directory build and the address rules every source shares.

Kind: passive typed records and pure helpers. A Listing is what one source says about one
offering; an Offering is the merged row the page shows. Addresses are kept without their scheme,
because every address the directory publishes is an https address and the scheme adds bytes to
every row. An address that is not https, names no public host or carries user information is
refused here, before any row is built from it.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from loop_engine.core.service_runtime.commercial_relationship import NONE as NO_COMMERCIAL_RELATIONSHIP

LISTING_RECORD_TYPE = "mcp_directory_listing/v1"
MANIFEST_RECORD_TYPE = "mcp_directory_manifest/v1"
ROWS_RECORD_TYPE = "mcp_directory_rows/v1"
REPORT_RECORD_TYPE = "mcp_directory_build_report/v1"

#: Sources in declared order of trust. The order decides which listing speaks for a merged row.
SOURCE_ORDER = ("registry", "codex", "docs", "github", "docker")
SOURCE_BITS = {name: 1 << index for index, name in enumerate(SOURCE_ORDER)}

#: The kinds of place an offering can be taken from, in the order the page shows them.
REMOTE_HTTP, REMOTE_SSE = "remote-http", "remote-sse"
NPM, PYPI, OCI, NUGET, CARGO, MCPB = "npm", "pypi", "oci", "nuget", "cargo", "mcpb"
API = "api"
LOCATION_KINDS = (REMOTE_HTTP, REMOTE_SSE, NPM, PYPI, OCI, NUGET, CARGO, MCPB, API)
REMOTE_KINDS = frozenset({REMOTE_HTTP, REMOTE_SSE})
PACKAGE_KINDS = frozenset({NPM, PYPI, OCI, NUGET, CARGO, MCPB})
#: The transports the registry names.
STDIO, STREAMABLE_HTTP, SSE = "stdio", "streamable-http", "sse"

#: What an offering is. A row can be more than one of these.
OFFERING_BITS = {"remote": 1, "package": 2, "source": 4, "api": 8}
#: How an offering connects.
TRANSPORT_BITS = {STDIO: 1, STREAMABLE_HTTP: 2, SSE: 4}
#: How an offering signs in, as its listings declare it. None declared is not the same as none.
AUTH_BITS = {"none": 1, "key": 2, "oauth": 4, "payment": 8}
#: Who listed the offering, compared with who owns its code or its endpoint.
ORIGINS = ("unknown", "maker", "other")
ORIGIN_UNKNOWN, ORIGIN_MAKER, ORIGIN_OTHER = ORIGINS
#: What a publisher name is: a domain the registry verified, a GitHub account it verified, or an owner
#: read from a code address that nobody verified.
PUBLISHER_KINDS = ("unknown", "domain", "github", "repository")
#: Where a licence fact came from.
LICENCE_BASES = ("", "repository", "package")
#: What the code host said about a GitHub repository when the build last asked: not asked, found, not found, archived.
REPOSITORY_STATES = ("unknown", "found", "missing", "archived")

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_HOST_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
SECURE_SCHEME = "https"
LOOPBACK_NAMES = frozenset({"localhost", "localhost.localdomain"})
PRIVATE_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home", ".corp", ".test", ".invalid", ".example")


@dataclass(frozen=True)
class Location:
    """One place an offering can be taken from: an identifier or an address without its scheme."""

    kind: str
    value: str
    transport: str = ""


@dataclass(frozen=True)
class Listing:
    """What one source says about one offering, before any merge."""

    source: str
    key: str
    name: str
    description: str = ""
    namespace: str = ""
    publisher: str = ""
    publisher_kind: str = "unknown"
    repository: str = ""
    subfolder: str = ""
    website: str = ""
    locations: tuple = ()
    auth: int = 0
    licence: str = ""
    licence_basis: str = ""
    category_hint: str = ""
    active: bool = True
    status: str = "active"
    latest: bool = True
    updated_at: str = ""
    published_at: str = ""
    origin: str = ORIGIN_UNKNOWN
    reference: str = ""
    identities: tuple = ()


@dataclass(frozen=True)
class Exclusion:
    """A listing the directory does not show, with the rule that refused it."""

    source: str
    key: str
    rule: str
    detail: str = ""


@dataclass
class Offering:
    """One merged row: every listing that describes the same offering, and the facts the row shows."""

    listings: list
    identity: str = ""
    name: str = ""
    description: str = ""
    publisher: str = ""
    publisher_kind: str = "unknown"
    category: str = ""
    offering_bits: int = 0
    origin: str = ORIGIN_UNKNOWN
    locations: tuple = ()
    transport_bits: int = 0
    auth_bits: int = 0
    licence: str = ""
    licence_basis: str = ""
    docs: str = ""
    repository: str = ""
    repository_state: str = "unknown"
    source_bits: int = 0
    aliases: tuple = ()
    references: dict = field(default_factory=dict)
    updated_at: str = ""
    #: Whether a link to this offering earns anything. Kept apart from every editorial field above: ranking,
    #: ordering, filtering, search and inclusion never read it.
    commercial_relationship: object = NO_COMMERCIAL_RELATIONSHIP


def without_scheme(address: str) -> str:
    """An https address as host and path, or an empty string when the address is refused."""
    if not isinstance(address, str) or not address.strip():
        return ""
    value = address.strip()
    try:
        parts = urlsplit(value)
    except ValueError:
        return ""
    if parts.scheme.lower() != SECURE_SCHEME or parts.username or parts.password or not parts.hostname:
        return ""
    host = parts.hostname.lower().rstrip(".")
    if not public_host(host):
        return ""
    port = f":{parts.port}" if parts.port not in (None, 443) else ""
    path = re.sub(r"/{2,}", "/", parts.path or "")
    if path == "/":
        path = ""
    return host + port + path


def public_host(host: str) -> bool:
    """True for a dotted host name or address that a stranger on the internet can reach."""
    if not host or host in LOOPBACK_NAMES or any(host.endswith(suffix) for suffix in PRIVATE_SUFFIXES):
        return False
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        labels = host.split(".")
        return len(labels) >= 2 and all(_HOST_LABEL.match(label) for label in labels) and not labels[-1].isdigit()
    return address.is_global


def starts_with_address(text: str) -> bool:
    """True when a piece of text opens with a scheme, so it is an address and not a name."""
    return bool(_SCHEME.match(text or ""))


def host_of(address: str) -> str:
    """The host of an address kept without its scheme."""
    return (address or "").split("/", 1)[0].split(":", 1)[0].lower()


def under_domain(host: str, domain: str) -> bool:
    """True when a host is the domain itself or a name inside it."""
    host, domain = (host or "").lower(), (domain or "").lower()
    return bool(domain) and (host == domain or host.endswith("." + domain))


def repository_address(url: str) -> str:
    """A code repository address without scheme, trailing slash or .git ending, or empty."""
    value = without_scheme(url)
    if not value:
        return ""
    value = value.rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    host = host_of(value)
    if host in ("github.com", "gitlab.com", "codeberg.org", "bitbucket.org"):
        segments = value.split("/")
        if len(segments) < 3 or not segments[1] or not segments[2]:
            return ""
        value = "/".join(segments[:3])
    return value


def repository_key(address: str, subfolder: str = "") -> str:
    """The case-folded identity of a repository and an optional folder inside it."""
    base = (address or "").lower()
    folder = (subfolder or "").strip("/").lower()
    return base + ("#" + folder if folder and base else "")


def repository_owner(address: str) -> str:
    """The account that owns a repository on a known code host, or an empty string."""
    segments = (address or "").split("/")
    if len(segments) >= 3 and segments[0] in ("github.com", "gitlab.com", "codeberg.org", "bitbucket.org"):
        return segments[1]
    return ""


def namespace_domain(namespace: str) -> str:
    """The domain a reverse-DNS registry namespace names, or empty for a GitHub account namespace."""
    if not namespace or namespace.lower().startswith("io.github."):
        return ""
    labels = [label for label in namespace.lower().split(".") if label]
    return ".".join(reversed(labels)) if len(labels) >= 2 else ""


def namespace_account(namespace: str) -> str:
    """The GitHub account an io.github registry namespace names, or empty."""
    prefix = "io.github."
    return namespace[len(prefix):] if namespace.lower().startswith(prefix) else ""


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def names_agree(owner: str, domain: str) -> bool:
    """True when an account name and a domain name the same party, by one written rule.

    The account agrees with the domain when, after dropping everything but letters and digits, it
    equals one label of the domain (the last label excepted), or one contains the other and the
    shorter has at least four characters. `makenotion` agrees with `notion.com`; `222wcnm` does not
    agree with `smithery.ai`.
    """
    account = _squash(owner)
    labels = [_squash(label) for label in (domain or "").split(".")[:-1]]
    for label in labels:
        if not account or not label:
            continue
        if account == label:
            return True
        shorter, longer = sorted((account, label), key=len)
        if len(shorter) >= 4 and shorter in longer:
            return True
    return False


def text_line(value, limit: int = 240) -> str:
    """One line of plain text: control characters and runs of space folded, cut at the limit."""
    if not isinstance(value, str):
        return ""
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text
