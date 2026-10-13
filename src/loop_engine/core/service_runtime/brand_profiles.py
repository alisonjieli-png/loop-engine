"""Passive, exact-origin website profiles owned by the existing HTTP boundary.

A profile selects presentation and OAuth audience, never another runtime,
catalogue, account namespace, entitlement policy or billing customer.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit

from .http_auth import validate_public_url

BRAND_PROFILE_VERSION = "service_brand_profile/v1"


@dataclass(frozen=True)
class ServiceBrandProfile:
    brand: str
    public_base_url: str
    display_name: str = "AgentFeeds"
    record_type: str = BRAND_PROFILE_VERSION

    def __post_init__(self):
        if self.record_type != BRAND_PROFILE_VERSION or self.brand != "agentfeeds":
            raise ValueError("unsupported service brand profile")
        if self.display_name != "AgentFeeds":
            raise ValueError("the qualified brand requires its exact display name")
        # Whether local HTTP is permitted is independently checked against
        # the containing host configuration before an application is built.
        origin = validate_public_url(self.public_base_url, permit_loopback=True)
        parsed = urlsplit(origin)
        if parsed.path or origin != self.public_base_url or "\\" in origin or any(c.isspace() for c in origin):
            raise ValueError("brand presentation requires one exact origin")
        parsed.port

    @property
    def host(self):
        return urlsplit(self.public_base_url).netloc

    @classmethod
    def from_host(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict) or value.get("record_type") != BRAND_PROFILE_VERSION:
            raise ValueError("typed service brand profile required")
        return cls(**value)
