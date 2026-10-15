"""Passive, exact-origin website profiles owned by the existing HTTP boundary.

A profile selects presentation and OAuth audience, never another runtime,
catalogue, account namespace, entitlement policy or billing customer.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit

from .http_auth import validate_public_origin

BRAND_PROFILE_VERSION = "service_brand_profile/v1"
BRAND_NAMES = {"agentfeeds": "AgentFeeds", "agentfoundry": "AgentFoundry",
               "agentafk": "AgentAFK", "meatproxy": "Don't be a meat proxy",
               "agentstudios": "AgentStudios"}
# Five qualified presentations can each declare an apex and www origin.
# This bound grants no domain access: every entry still needs explicit Host
# and Origin admission in the containing transport configuration.
MAXIMUM_BRAND_PROFILES = 10

# These addresses carry an origin-bound protocol or browser-local state. A
# website's canonical address does not migrate its accounts, tokens or data.
ORIGIN_LOCAL_WEB_PATHS = frozenset((
    "/authorize", "/token", "/register", "/revoke", "/app", "/account", "/admin",
    "/login", "/signup", "/get-started", "/saved", "/build", "/plan", "/run-desk",
))
ORIGIN_LOCAL_WEB_PREFIXES = ("/api", "/mcp", "/oauth", "/auth", "/.well-known", "/out", "/assets", "/__edge")
ORIGIN_LOCAL_REQUEST_HEADERS = frozenset(("authorization", "cookie", "proxy-authorization", "origin"))


def website_redirect_origins(public_base_url, allowed_hosts, allowed_origins, brand_profiles=()):
    """Only explicitly admitted www/apex pairs within the same presentation.

    The base presentation has one canonical origin. A standalone pair must
    additionally have both profiles for the same brand; an admitted hostname
    alone never authorizes forwarding a request to another brand.
    """
    groups = {"": {public_base_url}}
    for profile in brand_profiles:
        groups.setdefault(profile.brand, set()).add(profile.public_base_url)
    redirects = {}
    for brand, origins in groups.items():
        for target in origins:
            parsed = urlsplit(target)
            if parsed.netloc.startswith("www."):
                continue
            alias = "www." + parsed.netloc
            alias_origin = parsed.scheme + "://" + alias
            if (parsed.netloc in allowed_hosts and alias in allowed_hosts
                    and target in allowed_origins and alias_origin in allowed_origins
                    and (not brand or alias_origin in origins)):
                redirects[alias] = target
    return redirects


def public_website_read(method, path, header_names):
    """Navigation only, before any credential, callback or protocol migration."""
    return (method in ("GET", "HEAD")
            and not ORIGIN_LOCAL_REQUEST_HEADERS.intersection(name.lower() for name in header_names)
            and path.rstrip("/") not in ORIGIN_LOCAL_WEB_PATHS
            and not any(path == prefix or path.startswith(prefix + "/") for prefix in ORIGIN_LOCAL_WEB_PREFIXES))


def website_redirect_location(origin, raw_path, raw_query):
    """Keep the original encoded target; never resolve it as a relative URL."""
    try:
        target = (raw_path + (b"?" + raw_query if raw_query else b"")).decode("ascii")
    except UnicodeDecodeError:
        return None
    if not target.startswith("/") or any(ord(char) < 33 or ord(char) == 127 for char in target):
        return None
    return origin + target


@dataclass(frozen=True)
class ServiceBrandProfile:
    brand: str
    public_base_url: str
    display_name: str = "AgentFeeds"
    record_type: str = BRAND_PROFILE_VERSION

    def __post_init__(self):
        if self.record_type != BRAND_PROFILE_VERSION or self.brand not in BRAND_NAMES:
            raise ValueError("unsupported service brand profile")
        if self.display_name != BRAND_NAMES[self.brand]:
            raise ValueError("the qualified brand requires its exact display name")
        # Whether local HTTP is permitted is independently checked against
        # the containing host configuration before an application is built.
        validate_public_origin(self.public_base_url, permit_loopback=True)

    @property
    def host(self):
        return self.public_base_url.split("://", 1)[1]

    @property
    def public_only(self):
        """These presentations have no account UI or provider-effect surface."""
        return self.brand in ("agentafk", "meatproxy")

    @classmethod
    def from_host(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict) or value.get("record_type") != BRAND_PROFILE_VERSION:
            raise ValueError("typed service brand profile required")
        return cls(**value)
