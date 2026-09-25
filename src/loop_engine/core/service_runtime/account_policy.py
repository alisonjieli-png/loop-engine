"""Staff roles fixed in code, and the account settings a host may choose.

Kind: internal service mechanics. This module holds passive typed records and
constants only. It adds no runtime type, no store and no graph vertex.

The owner decided on September 23, 2026 that internal staff hold one of three
roles, superadmin, developer and analytics, with permissions written in code
and nothing else. So the permissions of each role are the constant table
`ROLE_PERMISSIONS` below. The host configuration says only who holds a role,
by provider user identity or by email address, in the `staff` list of its
`accounts` block. A host file cannot name a permission, a fourth role or a
role for a service key, and no request can grant one.

```text
Staff roles
├── superadmin: every administration permission
├── developer: service diagnostics only; no account or billing change
└── analytics: account counts and usage counts only; no personal detail
```

The same block holds the number of founding accounts: the first accounts
that finish Baltor's sign-up receive Baltor Pro free each month. The default
is ten, the number the owner chose, and a host may set another number,
including zero.
"""
from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
import re
from types import MappingProxyType

from .records import ServiceRuntimeError

ACCOUNT_POLICY_VERSION = "service_account_policy/v1"
SUPERADMIN, DEVELOPER, ANALYTICS = "superadmin", "developer", "analytics"
STAFF_ROLES = (SUPERADMIN, DEVELOPER, ANALYTICS)
#: The administration permissions. Each one names exactly one thing a staff
#: member may read or change.
ACCOUNTS_LIST = "accounts.list"
ACCOUNT_COUNTS = "accounts.counts"
USAGE_COUNTS = "usage.counts"
SERVICE_DIAGNOSTICS = "service.diagnostics"
GRANT_FREE_MONTHLY = "accounts.grant_free_monthly"
REVOKE_FREE_MONTHLY = "accounts.revoke_free_monthly"
DISABLE_ACCOUNT = "accounts.disable"
ENABLE_ACCOUNT = "accounts.enable"
#: Start Baltor's own sign-up for a few addresses, owner request of September 24, 2026.
SEND_SIGN_UP_LINKS = "accounts.send_sign_up_links"
PERMISSIONS = (ACCOUNTS_LIST, ACCOUNT_COUNTS, USAGE_COUNTS, SERVICE_DIAGNOSTICS,
               GRANT_FREE_MONTHLY, REVOKE_FREE_MONTHLY, DISABLE_ACCOUNT, ENABLE_ACCOUNT, SEND_SIGN_UP_LINKS)
#: What each role may do. This table is the only source of a permission.
ROLE_PERMISSIONS = MappingProxyType({
    SUPERADMIN: frozenset(PERMISSIONS),
    DEVELOPER: frozenset({SERVICE_DIAGNOSTICS}),
    ANALYTICS: frozenset({ACCOUNT_COUNTS, USAGE_COUNTS}),
})
#: The operation a superadmin names on the wire, and the permission it needs.
ACTION_PERMISSIONS = MappingProxyType({
    "grant_free_monthly": GRANT_FREE_MONTHLY, "revoke_free_monthly": REVOKE_FREE_MONTHLY,
    "disable": DISABLE_ACCOUNT, "enable": ENABLE_ACCOUNT,
})
DEFAULT_FOUNDING_ACCOUNTS = 10
MOST_FOUNDING_ACCOUNTS = 10_000
MOST_STAFF_MEMBERS = 50
#: The provider's user identity is a lower-case UUID.
PROVIDER_USER_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_STAFF_FIELDS = frozenset({"role", "provider_user_id", "email", "name"})
#: The name a sign-up link message gives for the staff member who sent it.
LONGEST_STAFF_NAME = 64


def permissions_for(role):
    """The permissions of one role, or none for anything that is not a staff role."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def staff_address(value):
    """The address a staff entry names, in lower case, or a refusal.

    Only printable ASCII with one `@` is accepted, so an address written with
    letters of another script cannot stand in for a staff address.
    """
    if (not isinstance(value, str) or not 3 <= len(value) <= 254 or value.count("@") != 1
            or not value.isascii() or not value.isprintable() or any(ch.isspace() for ch in value)
            or value.startswith("@") or value.endswith("@")):
        raise ServiceRuntimeError("invalid_staff_member", "a staff address is one printable ASCII address")
    return value.lower()


@dataclass(frozen=True)
class StaffMember:
    """One person and the one role they hold. Exactly one identity field is named."""

    role: str
    provider_user_id: str = ""
    email: str = ""
    #: How a message this person sends names them, such as "Sam at Baltor".
    #: Optional; without it the message names the person's address.
    name: str = ""

    def __post_init__(self):
        if (not isinstance(self.name, str) or len(self.name) > LONGEST_STAFF_NAME or self.name != self.name.strip()
                or any(not (ch.isalnum() or ch in " .-'") for ch in self.name)):
            raise ServiceRuntimeError("invalid_staff_member",
                                      "a staff name is up to 64 letters, digits, spaces, points, hyphens or apostrophes")
        if self.role not in STAFF_ROLES:
            raise ServiceRuntimeError("unknown_staff_role", "a staff role is superadmin, developer or analytics")
        if not isinstance(self.provider_user_id, str) or not isinstance(self.email, str):
            raise ServiceRuntimeError("invalid_staff_member")
        if bool(self.provider_user_id) == bool(self.email):
            raise ServiceRuntimeError("invalid_staff_member",
                                      "a staff entry names a provider user identity or an email address, not both")
        if self.provider_user_id and not PROVIDER_USER_ID.fullmatch(self.provider_user_id):
            raise ServiceRuntimeError("invalid_staff_member", "a provider user identity is a lower-case UUID")
        if self.email:
            object.__setattr__(self, "email", staff_address(self.email))

    def __repr__(self):
        return "StaffMember(role=%r, named_by=%r)" % (self.role, "provider_user_id" if self.provider_user_id else "email")

    @classmethod
    def from_host(cls, value):
        if not isinstance(value, dict) or set(value) - _STAFF_FIELDS or "role" not in value:
            raise ServiceRuntimeError("invalid_staff_member",
                                      "a staff entry has a role and one identity field, and nothing else")
        return cls(**value)


@dataclass(frozen=True)
class ServiceAccountPolicy:
    """The founding account count and the staff list, from the host file only."""

    founding_free_monthly_accounts: int = DEFAULT_FOUNDING_ACCOUNTS
    staff: tuple = ()
    record_type: str = ACCOUNT_POLICY_VERSION

    def __post_init__(self):
        if self.record_type != ACCOUNT_POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_account_policy",
                                      f"this release reads {ACCOUNT_POLICY_VERSION} only")
        count = self.founding_free_monthly_accounts
        if type(count) is not int or not 0 <= count <= MOST_FOUNDING_ACCOUNTS:
            raise ServiceRuntimeError("invalid_account_policy",
                                      "the founding account count is a whole number from 0 to 10000")
        members = tuple(member if isinstance(member, StaffMember) else StaffMember.from_host(member)
                        for member in (self.staff if isinstance(self.staff, (list, tuple)) else ()))
        if not isinstance(self.staff, (list, tuple)) or len(members) > MOST_STAFF_MEMBERS:
            raise ServiceRuntimeError("invalid_account_policy", "the staff list holds at most fifty entries")
        named = [member.provider_user_id or member.email for member in members]
        if len(set(named)) != len(named):
            raise ServiceRuntimeError("invalid_account_policy", "one person holds one staff role")
        object.__setattr__(self, "staff", members)

    @classmethod
    def from_host(cls, value):
        """Accept the exact versioned block from a host file, and nothing else."""
        names = {item.name for item in dataclass_fields(cls)}
        if (not isinstance(value, dict) or set(value) - names
                or value.get("record_type") != ACCOUNT_POLICY_VERSION):
            raise ServiceRuntimeError("unsupported_account_policy",
                "an accounts block names its record version, the founding count and the staff list, and nothing else")
        return cls(**value)

    def member_for(self, provider_user_id, email):
        """The staff entry of one verified identity, or None for everyone else."""
        address = email.lower() if isinstance(email, str) else ""
        for member in self.staff:
            if ((member.provider_user_id and member.provider_user_id == provider_user_id)
                    or (member.email and address and member.email == address)):
                return member
        return None

    def role_for(self, provider_user_id, email):
        """The staff role of one verified identity, or empty text for everyone else."""
        member = self.member_for(provider_user_id, email)
        return member.role if member is not None else ""
