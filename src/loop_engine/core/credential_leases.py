"""One authentication, many instances, and no instance holding the secret.

When every node of the solutioning space is its own harness instance, the
naive path authenticates once per instance. That is wrong twice over: it asks
a person to approve the same access again and again, and it spreads copies of
a credential across folders that the engine then has to chase down.

WHAT THIS DOES INSTEAD
The host authenticates once and holds the credential. Each instance is issued
a lease: a reference with a scope, an expiry, and a use ceiling. The lease
record carries no value and never has, so a lease can be written into a
folder, recorded in run history, and read by a person without exposing
anything. At the point of use the host resolves the lease through its own
resolver; the value goes to the call, not to the instance.

WHY A LEASE RATHER THAN A COPY
A copy cannot be withdrawn. Revoking one credential revokes every lease on it
at once, which is what a person means when they say stop. A ceiling on live
leases means a runaway spawn cannot quietly multiply access, and a use ceiling
means a lease meant for one call cannot serve a thousand.

WHAT IS COUNTED
Authentications, leases, and resolutions are three different numbers, and the
whole point is that the first stays at one while the others grow. They are
reported separately so nobody can claim sharing works by counting the wrong
one.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

RECORD_TYPE = "credential_lease/v1"
HOLDER_RECORD_TYPE = "held_credential/v1"
USAGE_RECORD_TYPE = "credential_usage/v1"
#: What a lease permits. A scope is not a permission by itself; the effect
#: authority of the step still applies.
SCOPES = ("read", "write", "act")
#: Why a lease stopped resolving.
LEASE_STATES = ("live", "expired", "revoked", "spent")
#: Live leases one credential may back at once unless a holder declares its own.
DEFAULT_LEASE_CEILING = 64


class CredentialLeaseError(ValueError):
    """The lease names an unknown credential or scope, or has stopped being valid."""


@dataclass(frozen=True)
class HeldCredential:
    """A credential the host holds, named and never carried."""

    credential_ref: str
    kind: str
    owner: str
    lease_ceiling: int = DEFAULT_LEASE_CEILING
    scopes: tuple[str, ...] = SCOPES

    def __post_init__(self) -> None:
        if not self.credential_ref.strip() or not self.kind.strip() or not self.owner.strip():
            raise CredentialLeaseError(
                "a held credential needs a reference, a kind, and an owner")
        unknown = [scope for scope in self.scopes if scope not in SCOPES]
        if unknown:
            raise CredentialLeaseError(f"{unknown} is not drawn from {SCOPES}")
        if not isinstance(self.lease_ceiling, int) or self.lease_ceiling < 1:
            raise CredentialLeaseError("a lease ceiling is a positive count")

    def to_dict(self) -> dict:
        return {"record_type": HOLDER_RECORD_TYPE, "credential_ref": self.credential_ref,
                "kind": self.kind, "owner": self.owner,
                "lease_ceiling": self.lease_ceiling, "scopes": list(self.scopes),
                "value_held_here": False}


@dataclass
class Lease:
    """One instance's right to have the host use a credential on its behalf."""

    lease_id: str
    credential_ref: str
    instance_id: str
    scope: str
    issued_at: float
    expires_at: float
    use_ceiling: int
    uses: int = 0
    revoked: bool = False

    def state(self, now: float) -> str:
        if self.revoked:
            return LEASE_STATES[2]
        if now >= self.expires_at:
            return LEASE_STATES[1]
        if self.uses >= self.use_ceiling:
            return LEASE_STATES[3]
        return LEASE_STATES[0]

    def to_dict(self, now: "float | None" = None) -> dict:
        """The record a folder or a run history may carry. It holds no value."""
        return {"record_type": RECORD_TYPE, "lease_id": self.lease_id,
                "credential_ref": self.credential_ref, "instance_id": self.instance_id,
                "scope": self.scope, "issued_at": self.issued_at,
                "expires_at": self.expires_at, "use_ceiling": self.use_ceiling,
                "uses": self.uses,
                "state": self.state(time.time() if now is None else now),
                "value_included": False}


@dataclass
class LeaseBroker:
    """Issues, renews, revokes, and resolves leases over credentials the host holds."""

    credentials: dict = field(default_factory=dict)
    leases: dict = field(default_factory=dict)
    authentications: dict = field(default_factory=dict)
    resolutions: int = 0

    def hold(self, credential: HeldCredential) -> dict:
        """Record that the host authenticated once for this credential."""
        if not isinstance(credential, HeldCredential):
            raise CredentialLeaseError("only a typed held credential can be recorded")
        self.credentials[credential.credential_ref] = credential
        self.authentications[credential.credential_ref] = (
            self.authentications.get(credential.credential_ref, 0) + 1)
        return credential.to_dict()

    def _credential(self, credential_ref: str) -> HeldCredential:
        held = self.credentials.get(credential_ref)
        if held is None:
            raise CredentialLeaseError(
                f"the host holds no credential named {credential_ref!r}; an instance is "
                "never asked to authenticate on its own")
        return held

    def live_leases(self, credential_ref: str, now: float) -> tuple:
        return tuple(lease for lease in self.leases.values()
                     if lease.credential_ref == credential_ref
                     and lease.state(now) == LEASE_STATES[0])

    def issue(self, credential_ref: str, instance_id: str, *, scope: str = SCOPES[0],
              seconds: float = 900.0, use_ceiling: int = 1, now: "float | None" = None) -> Lease:
        """Lease one credential to one instance. The instance never authenticates."""
        moment = time.time() if now is None else now
        held = self._credential(credential_ref)
        if not instance_id.strip():
            raise CredentialLeaseError("a lease names the instance it is for")
        if scope not in held.scopes:
            raise CredentialLeaseError(
                f"{credential_ref!r} is held for {list(held.scopes)}, so it cannot be "
                f"leased for {scope!r}")
        if not isinstance(use_ceiling, int) or use_ceiling < 1 or seconds <= 0:
            raise CredentialLeaseError("a lease needs a positive life and use ceiling")
        for lease in self.leases.values():
            if (lease.credential_ref == credential_ref
                    and lease.instance_id == instance_id
                    and lease.state(moment) == LEASE_STATES[0]):
                raise CredentialLeaseError(
                    f"instance {instance_id!r} already holds a live lease on "
                    f"{credential_ref!r}; renew it rather than taking a second")
        if len(self.live_leases(credential_ref, moment)) >= held.lease_ceiling:
            raise CredentialLeaseError(
                f"{credential_ref!r} already backs {held.lease_ceiling} live leases, which is "
                "its declared ceiling; a runaway spawn does not quietly multiply access")
        lease = Lease("lease-" + secrets.token_hex(8), credential_ref, instance_id, scope,
                      moment, moment + seconds, use_ceiling)
        self.leases[lease.lease_id] = lease
        return lease

    def renew(self, lease_id: str, *, seconds: float = 900.0,
              now: "float | None" = None) -> Lease:
        moment = time.time() if now is None else now
        lease = self.leases.get(lease_id)
        if lease is None:
            raise CredentialLeaseError(f"no lease named {lease_id!r}")
        if lease.revoked:
            raise CredentialLeaseError(
                f"{lease_id!r} was revoked; a revoked lease is not renewed, it is reissued")
        lease.expires_at = moment + seconds
        return lease

    def revoke(self, lease_id: str) -> dict:
        lease = self.leases.get(lease_id)
        if lease is None:
            raise CredentialLeaseError(f"no lease named {lease_id!r}")
        lease.revoked = True
        return lease.to_dict()

    def revoke_credential(self, credential_ref: str) -> dict:
        """Stop every lease on one credential at once, which is what stop means."""
        self._credential(credential_ref)
        stopped = 0
        for lease in self.leases.values():
            if lease.credential_ref == credential_ref and not lease.revoked:
                lease.revoked = True
                stopped += 1
        return {"record_type": "credential_revocation/v1", "credential_ref": credential_ref,
                "leases_revoked": stopped}

    def resolve(self, lease_id: str, resolver, *, now: "float | None" = None):
        """Use the credential on behalf of the lease, without handing it over.

        ``resolver`` belongs to the host: it receives the credential reference
        and returns whatever the call needs. The value is never stored here and
        never enters the lease record.
        """
        moment = time.time() if now is None else now
        lease = self.leases.get(lease_id)
        if lease is None:
            raise CredentialLeaseError(f"no lease named {lease_id!r}")
        state = lease.state(moment)
        if state != LEASE_STATES[0]:
            raise CredentialLeaseError(
                f"lease {lease_id!r} is {state}, so it resolves nothing")
        if not callable(resolver):
            raise CredentialLeaseError(
                "resolving needs the host's own resolver; this broker holds no value")
        self._credential(lease.credential_ref)
        lease.uses += 1
        self.resolutions += 1
        return resolver(lease.credential_ref)

    def usage(self, now: "float | None" = None) -> dict:
        """Three counts kept apart, so sharing is shown rather than claimed."""
        moment = time.time() if now is None else now
        return {"record_type": USAGE_RECORD_TYPE,
                "authentications": sum(self.authentications.values()),
                "credentials_held": len(self.credentials),
                "leases_issued": len(self.leases),
                "leases_live": sum(1 for lease in self.leases.values()
                                   if lease.state(moment) == LEASE_STATES[0]),
                "resolutions": self.resolutions,
                "instances_served": len({lease.instance_id for lease in self.leases.values()})}


def self_test() -> dict:
    """One authentication backs many instances, a lease carries no value, revoking cuts all."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except CredentialLeaseError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    start = 1_000_000.0
    broker = LeaseBroker()
    held = broker.hold(HeldCredential("host.credential.postal", "api_key", "tenant.acme",
                                      lease_ceiling=3, scopes=("read",)))
    leases = [broker.issue("host.credential.postal", f"node-{index}", scope="read",
                           seconds=60, use_ceiling=2, now=start)
              for index in range(3)]
    usage = broker.usage(now=start)
    second = LeaseBroker()
    second.hold(HeldCredential("host.credential.postal", "api_key", "tenant.acme"))
    for index in range(3):
        second.issue("host.credential.postal", f"node-{index}", seconds=60, now=start)
    second.hold(HeldCredential("host.credential.postal", "api_key", "tenant.acme"))
    check("one_authentication_backs_every_instance_and_the_counts_stay_apart",
          held["value_held_here"] is False
          and usage["authentications"] == 1 and usage["credentials_held"] == 1
          and usage["leases_issued"] == 3 and usage["leases_live"] == 3
          and usage["instances_served"] == 3 and usage["resolutions"] == 0
          # Authenticating again is visible rather than hidden, and it does not
          # count the leases that already exist.
          and second.usage(now=start)["authentications"] == 2
          and second.usage(now=start)["leases_issued"] == 3,
          str(usage))
    record = leases[0].to_dict(now=start)
    check("a_lease_record_carries_no_value_and_says_so",
          record["value_included"] is False and "value" not in record
          and "secret" not in str(record).lower()
          and record["state"] == "live" and record["credential_ref"].startswith("host."),
          str(record["state"]))
    resolved = []

    def host_resolver(credential_ref):
        resolved.append(credential_ref)
        return "the value the host holds"

    first = broker.resolve(leases[0].lease_id, host_resolver, now=start)
    broker.resolve(leases[1].lease_id, host_resolver, now=start)
    check("resolving_uses_the_host_resolver_and_counts_the_use_without_storing_the_value",
          first == "the value the host holds" and resolved == ["host.credential.postal"] * 2
          and broker.usage(now=start)["resolutions"] == 2
          and broker.leases[leases[0].lease_id].uses == 1
          and broker.authentications["host.credential.postal"] == 1
          and refuses(lambda: broker.resolve(leases[0].lease_id, None, now=start)),
          str(broker.usage(now=start)["resolutions"]))
    # A second credential with room to spare, so the duplicate refusal is shown
    # where the ceiling is not the reason.
    broker.hold(HeldCredential("host.credential.roomy", "api_key", "tenant.acme",
                               lease_ceiling=9, scopes=("read",)))
    broker.issue("host.credential.roomy", "node-0", seconds=60, now=start)
    broker.issue("host.credential.roomy", "node-1", seconds=60, now=start)
    check("a_ceiling_a_second_lease_for_one_instance_and_an_unheld_credential_are_refused",
          refuses(lambda: broker.issue("host.credential.postal", "node-3", now=start))
          and refuses(lambda: broker.issue("host.credential.roomy", "node-0", now=start))
          and len(broker.live_leases("host.credential.roomy", start)) == 2
          and refuses(lambda: broker.issue("host.credential.postal", "node-0", now=start))
          and refuses(lambda: broker.issue("host.credential.absent", "node-9", now=start))
          and refuses(lambda: broker.issue("host.credential.postal", "node-9",
                                           scope="write", now=start))
          and refuses(lambda: broker.issue("host.credential.postal", "", now=start))
          and refuses(lambda: broker.hold({"credential_ref": "x"}))
          and refuses(lambda: HeldCredential("x", "api_key", "owner", scopes=("fly",)))
          and refuses(lambda: HeldCredential("x", "api_key", "owner", lease_ceiling=0)))
    later = start + 61
    check("an_expired_lease_a_spent_lease_and_a_revoked_lease_all_stop_resolving",
          refuses(lambda: broker.resolve(leases[0].lease_id, host_resolver, now=later))
          and leases[0].state(later) == "expired"
          and broker.renew(leases[0].lease_id, seconds=60, now=later).state(later) == "live"
          and broker.resolve(leases[0].lease_id, host_resolver, now=later)
          and leases[0].state(later) == "spent"
          and refuses(lambda: broker.resolve(leases[0].lease_id, host_resolver, now=later)),
          leases[0].state(later))
    stopped = broker.revoke_credential("host.credential.postal")
    check("revoking_the_credential_stops_every_lease_at_once_and_a_revoked_lease_is_not_renewed",
          stopped["leases_revoked"] == 3
          and all(lease.state(later) == "revoked" for lease in leases)
          and broker.usage(now=later)["leases_live"] == 0
          and refuses(lambda: broker.renew(leases[1].lease_id, now=later))
          and refuses(lambda: broker.revoke("lease-absent"))
          and refuses(lambda: broker.revoke_credential("host.credential.absent")),
          str(stopped["leases_revoked"]))
    reissued = broker.issue("host.credential.postal", "node-0", scope="read",
                            seconds=60, use_ceiling=1, now=later)
    check("after_a_revocation_a_fresh_lease_still_needs_no_second_authentication",
          reissued.state(later) == "live"
          and broker.authentications["host.credential.postal"] == 1
          and broker.usage(now=later)["leases_issued"] > 4,
          str(broker.authentications["host.credential.postal"]))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "credential_leases_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
