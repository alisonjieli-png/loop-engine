"""Staff tools for catalogue releases: status, publish, rollback and item withdrawal, without a redeploy.

Kind: internal service mechanics. The tools reach the same functions the
operator commands in `catalogue_commands.py` run, with the same guards, so a
release published here is the release `loop-engine service publish-catalogue`
would publish. It adds no second path, no runtime type, no store and no graph
vertex.

```text
How new files reach the live library without a redeploy
├── build a bundle away from the service: tools/build_catalogue_release_bundle.py
│   prints its bundle_digest
├── upload the bundle into the host's incoming folder
├── catalogue_publish, step plan: reads the bundle there, refuses a bundle whose
│   digest is not the expected_bundle_digest, and lists what it adds, changes
│   and withdraws against the active release
├── catalogue_publish, step apply: the same publish the operator command runs,
│   guarded by the active release the plan named
└── the running service's refresher serves the new release within its
    refresh_seconds; nothing restarts
```

A rollback moves the pointer to an earlier, fully verified release, and every
withdrawal stays honoured. A withdrawal is refused at once on every view.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .account_policy import CATALOGUE_PUBLISH, CATALOGUE_READ, CATALOGUE_ROLLBACK, CATALOGUE_WITHDRAW
from .http import ServiceHttpError
from .records import ServiceRuntimeError
from .staff_tools import FAILED, Plan, StaffTool

STATUS_VERSION = "service_staff_catalogue_status/v1"
BUNDLE_NAME = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$"}
DIGEST = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
MOST_LISTED_BUNDLES = 100


@dataclass(frozen=True)
class StaffCatalogue:
    """What the catalogue tools may touch: the operator context, the incoming folder and the host policies."""

    context: object
    incoming_root: str
    license_policy: object
    family_policy: object

    @classmethod
    def from_host(cls, configuration, settings, *, license_policy=None, family_policy=None):
        from .catalogue_releases import CatalogueOperatorContext
        from .catalogue_serving import catalogue_settings
        from .records import ServiceRuntimeConfig
        from .storage import ServiceCatalogBinding
        section = catalogue_settings(configuration)
        context = None
        if section is not None:
            context = CatalogueOperatorContext(ServiceCatalogBinding(ServiceRuntimeConfig(**configuration["runtime"])),
                                               section.body_store_root)
        return cls(context, settings.catalogue_incoming_root, license_policy, family_policy)

    @property
    def publishing(self):
        return self.context is not None and bool(self.context.body_store_root) and bool(self.incoming_root)

    def require(self, *, bodies=False, incoming=False):
        if self.context is None:
            raise ServiceHttpError("catalogue_section_required", 503)
        if bodies and not self.context.body_store_root:
            raise ServiceHttpError("catalogue_section_required", 503)
        if incoming and not self.incoming_root:
            raise ServiceHttpError("catalogue_incoming_folder_not_configured", 503)
        return self.context

    def bundle_folder(self, name):
        """One bundle folder directly inside the incoming folder, never a path that leaves it."""
        root = Path(self.incoming_root)
        folder = root / name
        if (not root.is_dir() or folder.is_symlink() or folder.resolve() != folder or folder.parent != root
                or not folder.is_dir()):
            raise ServiceHttpError("catalogue_bundle_not_found", 404)
        return folder

    def incoming_bundles(self):
        from .catalogue_bundle import HEADER_FILE
        root = Path(self.incoming_root) if self.incoming_root else None
        if root is None or not root.is_dir():
            return []
        names = sorted(entry.name for entry in root.iterdir()
                       if entry.is_dir() and not entry.is_symlink() and (entry / HEADER_FILE).is_file())
        return names[:MOST_LISTED_BUNDLES]


def _catalogue(tools):
    if tools.catalogue is None:
        raise ServiceHttpError("catalogue_section_required", 503)
    return tools.catalogue


def catalogue_status(tools, actor, fields):
    """What the service serves now, what the store holds, and the bundles waiting in the incoming folder."""
    from .catalogue_releases import status
    view = tools.application.provisioning.current_view()
    staff_catalogue = tools.catalogue
    stored = status(staff_catalogue.context) if staff_catalogue is not None and staff_catalogue.context else None
    return {"record_type": STATUS_VERSION,
            "served": {"source": view.source, "release_id": view.release_id or None,
                       "items": len(view.catalogue.items), "state_revision": view.state_revision,
                       "withdrawn": len(view.withdrawn)},
            "store": stored,
            "publishing_available": staff_catalogue is not None and staff_catalogue.publishing,
            "incoming_bundles": (staff_catalogue.incoming_bundles()
                                 if staff_catalogue is not None and actor.may(CATALOGUE_PUBLISH) else [])}


def _pointer(context):
    from .catalogue_releases import read_pointer, read_state
    binding = context.binding
    with binding.store() as store:
        state_row, _state = read_state(binding, store)
        pointer_row, pointer = read_pointer(binding, store)
    from .catalogue_releases import POINTER_KIND, POINTER_LOGICAL, STATE_KIND, STATE_LOGICAL
    guards = (binding.guard(state_row, binding.identity(STATE_KIND, STATE_LOGICAL)),
              binding.guard(pointer_row, binding.identity(POINTER_KIND, POINTER_LOGICAL)))
    return (pointer["release_id"] if pointer is not None else ""), guards


def publish_plan(tools, actor, fields):
    from .catalogue_bundle import read_bundle
    from .catalogue_releases import _changes, load_release, withdrawal_keys
    staff_catalogue = _catalogue(tools)
    context = staff_catalogue.require(bodies=True, incoming=True)
    bundle = read_bundle(staff_catalogue.bundle_folder(fields["bundle"]), license_policy=staff_catalogue.license_policy,
                         family_policy=staff_catalogue.family_policy, verify_blobs=False)
    if bundle.digest != fields["expected_bundle_digest"]:
        raise ServiceHttpError("bundle_digest_mismatch", 409)
    active_id, guards = _pointer(context)
    binding = context.binding
    with binding.store() as store:
        active = load_release(binding, store, active_id) if active_id else None
        withdrawn = withdrawal_keys(binding, store)
    listed = [entry.identity for entry in bundle.items if (entry.identity, entry.package.served_digest) in withdrawn]
    if listed:
        raise ServiceHttpError("catalogue_release_lists_withdrawn_item", 409)
    changes = _changes(active, bundle, {row["identity"] for row in bundle.withdrawals})
    return Plan({"bundle": fields["bundle"], "bundle_digest": bundle.digest, "items": len(bundle.items),
                 "active_release_id": active_id or None, "added": len(changes["added"]),
                 "changed": len(changes["changed"]), "withdrawn": len(changes["withdrawn"]),
                 "durable_withdrawals": len(bundle.withdrawals), "notes": bundle.notes,
                 "served_after": "the running service serves the new release at its next refresh; nothing restarts"},
                guards, "", bundle.digest, context=(bundle, active_id))


def _outside(context, work):
    """Run one catalogue operation that writes in several batches, keeping its request identity honest."""
    context.reserve()
    try:
        result = work()
    except (ServiceRuntimeError, ServiceHttpError) as error:
        context.finish({"code": getattr(error, "code", "operation_failed")}, FAILED)
        raise
    return context.finish(result)


def publish_apply(tools, actor, fields, context):
    from .catalogue_releases import publish
    bundle, active_id = context.plan.context
    operator = tools.catalogue.require(bodies=True, incoming=True)
    return _outside(context, lambda: publish(operator, bundle, expected_release=active_id))


def rollback_plan(tools, actor, fields):
    from .catalogue_releases import load_release, withdrawal_keys
    from .catalogue_packages import CataloguePackage
    context = _catalogue(tools).require(bodies=True)
    active_id, guards = _pointer(context)
    if not active_id:
        raise ServiceHttpError("catalogue_release_not_found", 404)
    binding = context.binding
    with binding.store() as store:
        target = load_release(binding, store, fields["to_release"])
        withdrawn = withdrawal_keys(binding, store)
    held_back = sorted(payload["reference"]["identity"] for _version, payload in target.versions
                       if (payload["reference"]["identity"],
                           CataloguePackage.from_dict(payload["package"]).served_digest) in withdrawn)
    return Plan({"active_release_id": active_id, "to_release": fields["to_release"], "items": len(target.versions),
                 "withdrawn_items_kept_withheld": held_back}, guards, "", fields["to_release"], context=active_id)


def rollback_apply(tools, actor, fields, context):
    from .catalogue_releases import rollback
    operator = tools.catalogue.require(bodies=True)
    return _outside(context, lambda: rollback(operator, to_release=fields["to_release"],
                                              expected_release=context.plan.context))


def _withdrawal_choice(context, fields):
    """The item versions a withdrawal would record, read without writing, as `withdraw` chooses them."""
    from .catalogue_bundle import ITEM_VERSION_RECORD_TYPE, canonical_bytes
    from .catalogue_packages import CataloguePackage, sha256_hex
    from .catalogue_releases import ITEM_KIND, WITHDRAWAL_KIND, _payload, load_release, read_pointer
    binding = context.binding
    chosen = {}
    with binding.store() as store:
        _row, pointer = read_pointer(binding, store)
        if fields.get("all_versions"):
            for row in binding.rows_all(store, ITEM_KIND):
                if row["payload"].get("reference", {}).get("identity") == fields["identity"]:
                    chosen[sha256_hex(canonical_bytes(row["payload"]))] = row["payload"]
        else:
            version = fields.get("item_version")
            if version is None and pointer is not None:
                version = dict(load_release(binding, store, pointer["release_id"]).items).get(fields["identity"])
            _item, payload = _payload(binding, store, ITEM_KIND, version, ITEM_VERSION_RECORD_TYPE) if version else (None,
                                                                                                                  None)
            if payload is not None and payload["reference"]["identity"] == fields["identity"]:
                chosen[version] = payload
        pending = {version: CataloguePackage.from_dict(payload["package"]).served_digest
                   for version, payload in chosen.items()}
        fresh = sorted(version for version, served in pending.items()
                       if binding.read(store, WITHDRAWAL_KIND, (fields["identity"], served)) is None)
    return sorted(chosen), fresh


def withdraw_plan(tools, actor, fields):
    from .catalogue_bundle import note
    from .catalogue_releases import STATE_KIND, STATE_LOGICAL, read_state
    context = _catalogue(tools).require()
    note(fields["note"])
    versions, fresh = _withdrawal_choice(context, fields)
    if not versions:
        raise ServiceHttpError("catalogue_item_not_found", 404)
    binding = context.binding
    with binding.store() as store:
        state_row, _state = read_state(binding, store)
    return Plan({"identity": fields["identity"], "item_versions": versions, "newly_withdrawn": fresh,
                 "already_withdrawn": len(versions) - len(fresh), "effect": "every read of these versions is "
                 "refused at once, and no later release or rollback serves them"},
                (binding.guard(state_row, binding.identity(STATE_KIND, STATE_LOGICAL)),), "", fields["identity"])


def withdraw_apply(tools, actor, fields, context):
    from .catalogue_releases import withdraw
    operator = tools.catalogue.require()
    return _outside(context, lambda: withdraw(operator, identity=fields["identity"], note_text=fields["note"],
                                              item_version=fields.get("item_version"),
                                              all_versions=fields.get("all_versions", False)))


TOOLS = (
    StaffTool("catalogue_status", "What the service serves now, the releases the store holds, and the bundles "
              "waiting in the incoming folder.", {}, (CATALOGUE_READ,), catalogue_status),
    StaffTool("catalogue_publish", "Publish a release bundle already uploaded to the incoming folder, with no "
              "redeploy. The bundle digest its builder printed is required. Plan first, then apply.",
              {"bundle": BUNDLE_NAME, "expected_bundle_digest": DIGEST}, (CATALOGUE_PUBLISH,), publish_plan,
              publish_apply, required=("bundle", "expected_bundle_digest")),
    StaffTool("catalogue_rollback", "Serve an earlier release again; every withdrawal stays honoured. Plan first, "
              "then apply.", {"to_release": DIGEST}, (CATALOGUE_ROLLBACK,), rollback_plan, rollback_apply,
              required=("to_release",)),
    StaffTool("item_withdraw", "Withdraw one catalogue item version, or every stored version, at once and for good. "
              "Plan first, then apply.",
              {"identity": {"type": "string", "minLength": 1, "maxLength": 200},
               "note": {"type": "string", "minLength": 3, "maxLength": 400}, "item_version": DIGEST,
               "all_versions": {"type": "boolean"}}, (CATALOGUE_WITHDRAW,), withdraw_plan, withdraw_apply,
              required=("identity", "note")),
)
