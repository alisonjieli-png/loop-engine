"""Serving what goes into a harness instance, to tenants, behind a paid line.

A harness instance needs instructions, skills, tools, and code before it can
work. Loop Engine holds those as records with digests, licenses, and declared
effects. This module is the surface that hands them out: a caller asks what is
available, asks for one item's manifest, and asks for a body. Nothing else.

WHAT IS FREE AND WHAT IS PAID
Listing what exists is free, and so is a manifest: a caller can always see
identities, purposes, digests, sizes, and licenses, which is what is needed to
decide whether an item is worth having. Reading a body is the paid line,
because that is the part with the cost behind it. A refusal is never metered,
and neither is anything a tenant already owns.

INTEGRITY IS NOT OPTIONAL HERE
Every item is served with the digest of its body, and the body is checked
against that digest before it leaves. The formats these travel in carry no
digest of their own, so a caller that trusts a file name trusts nothing. A
caller that checks the digest it was given has something a changed file cannot
pass. This mirrors the one published provisioning format that makes
verification mandatory rather than advisory.

WHAT THIS IS NOT
It is not a transport. There is no socket here and no protocol framing: the
module speaks in typed request and result records, so an adapter can put it
behind whichever protocol a deployment wants without this module knowing.
It is also not an authorization system of its own; a tenant's entitlement and
the effects a caller holds both arrive with the request and are enforced, not
invented.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from .harness_intelligence import (HarnessIntelligenceCatalogue,
                                   HarnessIntelligenceError, offer)
from .service_api import ServiceError, key_digest

SERVER_RECORD_TYPE = "provisioning_server/v1"
DISCOVER_RECORD_TYPE = "provisioning_discover/v1"
LIST_RECORD_TYPE = "provisioning_list/v1"
MANIFEST_RECORD_TYPE = "provisioning_manifest/v1"
BODY_RECORD_TYPE = "provisioning_body/v1"
REFUSAL_RECORD_TYPE = "provisioning_refusal/v1"
#: What a caller may ask for.
OPERATIONS = ("discover", "list", "manifest", "read")
#: What a tenant is entitled to. Listing and manifests are free at both levels.
ENTITLEMENTS = ("metadata", "bodies")
#: The unit a read is metered in. Nothing else here is metered.
METERED_UNIT = "provisioned_item"
#: Stated to every caller, so what is never charged for is never a surprise.
NEVER_METERED = ("listing what exists", "a manifest with digests and sizes",
                 "a refusal of any kind", "reading the tenant's own usage")


class ProvisioningError(ServiceError):
    """The request names an unknown operation, an unknown item, or asks beyond its entitlement."""


@dataclass(frozen=True)
class ProvisioningTenant:
    """One paying caller: its identity, the digest of its key, and its entitlement."""

    tenant_id: str
    key_digest: str
    entitlement: str = ENTITLEMENTS[0]

    def __post_init__(self) -> None:
        if not self.tenant_id.strip():
            raise ProvisioningError("a tenant needs an identifier")
        if len(self.key_digest) != 64 or any(
                character not in "0123456789abcdef" for character in self.key_digest):
            raise ProvisioningError(
                "key_digest is the digest of the key, never the key")
        if self.entitlement not in ENTITLEMENTS:
            raise ProvisioningError(f"entitlement must be one of {ENTITLEMENTS}")


@dataclass(frozen=True)
class ProvisioningRequest:
    """One typed ask. The key arrives here and is never stored or recorded."""

    operation: str
    key: str
    identity: str = ""
    style: str = ""
    authority_effects: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.operation not in OPERATIONS:
            raise ProvisioningError(f"operation must be one of {OPERATIONS}")
        if not self.key.strip():
            raise ProvisioningError("a request carries the caller's key")


@dataclass
class ProvisioningServer:
    """Answers four questions over one catalogue, meters one of them."""

    catalogue: HarnessIntelligenceCatalogue
    tenants: tuple[ProvisioningTenant, ...] = ()
    body_reader: object = None
    meter: object = None
    server_id: str = "loop-engine-provisioning"

    def tenant_for(self, key: str) -> ProvisioningTenant:
        """The tenant this key belongs to, compared by digest in constant time."""
        import hmac
        supplied = key_digest(key)
        for tenant in self.tenants:
            if hmac.compare_digest(supplied, tenant.key_digest):
                return tenant
        raise ProvisioningError("no tenant matches this key")

    def handle(self, request: ProvisioningRequest) -> dict:
        """Authenticate, answer, and meter a body read and nothing else."""
        if not isinstance(request, ProvisioningRequest):
            raise ProvisioningError("a typed request is required")
        tenant = self.tenant_for(request.key)
        if request.operation == OPERATIONS[0]:
            return self._discover(tenant)
        if request.operation == OPERATIONS[1]:
            return self._list(tenant, request)
        if request.operation == OPERATIONS[2]:
            return self._manifest(tenant, request)
        return self._read(tenant, request)

    def _discover(self, tenant: ProvisioningTenant) -> dict:
        return {"record_type": DISCOVER_RECORD_TYPE, "server_id": self.server_id,
                "operations": list(OPERATIONS), "kinds": list(self.catalogue.kinds_held()),
                "tenant_id": tenant.tenant_id, "entitlement": tenant.entitlement,
                "items_held": len(self.catalogue.items),
                "metered_unit": METERED_UNIT,
                "metered": "reading a body",
                "never_metered": list(NEVER_METERED),
                "bodies_available": tenant.entitlement == ENTITLEMENTS[1]}

    def _offered(self, request: ProvisioningRequest) -> dict:
        try:
            return offer(self.catalogue, style=request.style,
                         authority_effects=request.authority_effects,
                         kinds=request.kinds)
        except HarnessIntelligenceError as exc:
            raise ProvisioningError(str(exc)) from None

    def _list(self, tenant: ProvisioningTenant, request: ProvisioningRequest) -> dict:
        offered = self._offered(request)
        return {"record_type": LIST_RECORD_TYPE, "tenant_id": tenant.tenant_id,
                "entitlement": tenant.entitlement,
                "items": offered["offered"], "withheld": offered["withheld"],
                "metered": False}

    def _item(self, request: ProvisioningRequest):
        if not request.identity.strip():
            raise ProvisioningError("name the item")
        offered = self._offered(request)
        for row in offered["offered"]:
            if row["identity"] == request.identity:
                return self.catalogue.items[request.identity]
        for row in offered["withheld"]:
            if row["identity"] == request.identity:
                raise ProvisioningError(
                    f"{request.identity!r} is withheld: {row['reason']}")
        raise ProvisioningError(f"no item named {request.identity!r}")

    def _manifest(self, tenant: ProvisioningTenant, request: ProvisioningRequest) -> dict:
        item = self._item(request)
        return {"record_type": MANIFEST_RECORD_TYPE, "tenant_id": tenant.tenant_id,
                "identity": item.identity, "kind": item.kind, "purpose": item.purpose,
                "digest": item.digest, "size_bytes": item.size_bytes,
                "license": item.license_name, "source_layer": item.source_layer,
                "source_ref": item.source_ref,
                "declared_effects": list(item.declared_effects),
                "verify_before_use": True, "metered": False}

    def _read(self, tenant: ProvisioningTenant, request: ProvisioningRequest) -> dict:
        item = self._item(request)
        if tenant.entitlement != ENTITLEMENTS[1]:
            raise ProvisioningError(
                f"tenant {tenant.tenant_id!r} holds the {tenant.entitlement!r} entitlement, so it "
                f"can see {request.identity!r} and its digest but cannot read its body")
        if not callable(self.body_reader):
            raise ProvisioningError(
                "this server holds no body reader, so it can serve manifests and not bodies")
        body = self.body_reader(item)
        if not isinstance(body, str):
            raise ProvisioningError("a body is text")
        measured = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if measured != item.digest:
            raise ProvisioningError(
                f"{item.identity!r} reads back with digest {measured[:12]} against the recorded "
                f"{item.digest[:12]}; the body changed since it was registered, so it is not served")
        if callable(self.meter):
            self.meter(tenant.tenant_id, METERED_UNIT, 1.0, item.identity)
        return {"record_type": BODY_RECORD_TYPE, "tenant_id": tenant.tenant_id,
                "identity": item.identity, "digest": item.digest,
                "size_bytes": item.size_bytes, "body": body,
                "metered": True, "metered_unit": METERED_UNIT}


@dataclass
class RecordedMeter:
    """A meter that keeps one row per charged read, for a usage answer."""

    rows: list = field(default_factory=list)

    def __call__(self, tenant_id: str, unit: str, quantity: float, reference: str) -> None:
        self.rows.append({"tenant_id": tenant_id, "unit": unit, "quantity": quantity,
                          "record_ref": reference, "at": time.time()})

    def total(self, tenant_id: str) -> float:
        return sum(row["quantity"] for row in self.rows if row["tenant_id"] == tenant_id)


def self_test() -> dict:
    """Listing is free, a body is paid, a changed body is refused, a refusal is never metered."""
    from .harness_intelligence import HarnessIntelligenceDraft, item_from_body
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ProvisioningError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    bodies = {
        "skill.clean_supplier_names": "# Clean supplier names\n\nUse the family.\n",
        "tool.database_copy": "{\"target\": \"new\"}",
    }
    catalogue = HarnessIntelligenceCatalogue()
    catalogue.register(item_from_body(HarnessIntelligenceDraft(
        "skill.clean_supplier_names", "skill", "Clean a supplier column",
        "context_intelligence", "ctx.skill.clean_supplier_names", "MIT"),
        bodies["skill.clean_supplier_names"]))
    catalogue.register(item_from_body(HarnessIntelligenceDraft(
        "tool.database_copy", "tool", "Copy a database with corrections",
        "code_intelligence", "code.capability.database_copy",
        declared_effects=("reads_fs", "writes_fs")),
        bodies["tool.database_copy"]))
    meter = RecordedMeter()
    free_tenant = ProvisioningTenant("reader", key_digest("free-key"), "metadata")
    paid_tenant = ProvisioningTenant("builder", key_digest("paid-key"), "bodies")
    server = ProvisioningServer(catalogue, (free_tenant, paid_tenant),
                                body_reader=lambda item: bodies[item.identity],
                                meter=meter)
    found = server.handle(ProvisioningRequest("discover", "free-key"))
    check("discovery_names_the_entitlement_the_metered_unit_and_what_is_never_metered",
          found["entitlement"] == "metadata" and found["bodies_available"] is False
          and found["metered_unit"] == METERED_UNIT
          and "a refusal of any kind" in found["never_metered"]
          and found["items_held"] == 2 and set(found["kinds"]) == {"skill", "tool"},
          str(found["kinds"]))
    listed = server.handle(ProvisioningRequest(
        "list", "free-key", authority_effects=("reads_fs", "writes_fs")))
    manifest = server.handle(ProvisioningRequest(
        "manifest", "free-key", identity="skill.clean_supplier_names"))
    check("listing_and_a_manifest_are_free_and_carry_digests_without_bodies",
          listed["metered"] is False and manifest["metered"] is False
          and len(listed["items"]) == 2
          and all("body" not in row for row in listed["items"])
          and manifest["digest"] == catalogue.items[
              "skill.clean_supplier_names"].digest
          and manifest["verify_before_use"] is True and meter.total("reader") == 0,
          manifest["digest"][:12])
    check("a_metadata_tenant_is_refused_a_body_by_name_and_is_not_metered",
          refuses(lambda: server.handle(ProvisioningRequest(
              "read", "free-key", identity="skill.clean_supplier_names")))
          and meter.total("reader") == 0)
    served = server.handle(ProvisioningRequest(
        "read", "paid-key", identity="skill.clean_supplier_names"))
    check("a_paid_tenant_reads_a_body_with_its_digest_and_is_metered_once",
          served["body"] == bodies["skill.clean_supplier_names"]
          and served["digest"] == hashlib.sha256(
              served["body"].encode("utf-8")).hexdigest()
          and served["metered"] is True and meter.total("builder") == 1.0
          and meter.rows[0]["record_ref"] == "skill.clean_supplier_names",
          str(meter.total("builder")))
    changed = ProvisioningServer(catalogue, (paid_tenant,),
                                 body_reader=lambda item: "something else entirely",
                                 meter=meter)
    check("a_body_that_no_longer_matches_its_recorded_digest_is_not_served",
          refuses(lambda: changed.handle(ProvisioningRequest(
              "read", "paid-key", identity="skill.clean_supplier_names")))
          and meter.total("builder") == 1.0)
    check("an_unknown_key_an_unknown_item_and_a_withheld_item_are_refused_and_never_metered",
          refuses(lambda: server.handle(ProvisioningRequest("discover", "wrong-key")))
          and refuses(lambda: server.handle(ProvisioningRequest(
              "manifest", "paid-key", identity="absent")))
          and refuses(lambda: server.handle(ProvisioningRequest(
              "read", "paid-key", identity="tool.database_copy")))
          and refuses(lambda: ProvisioningRequest("invent", "paid-key"))
          and refuses(lambda: ProvisioningTenant("x", "short", "bodies"))
          and refuses(lambda: ProvisioningTenant("x", key_digest("k"), "everything"))
          and meter.total("builder") == 1.0)
    bodiless = ProvisioningServer(catalogue, (paid_tenant,))
    check("a_server_with_no_body_reader_serves_manifests_and_says_so_rather_than_failing_oddly",
          bodiless.handle(ProvisioningRequest(
              "manifest", "paid-key", identity="skill.clean_supplier_names"))["digest"]
          and refuses(lambda: bodiless.handle(ProvisioningRequest(
              "read", "paid-key", identity="skill.clean_supplier_names"))))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "provisioning_server_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
