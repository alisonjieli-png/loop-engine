"""Host-only selected policy validation through the existing catalogue readers.

This maintenance path checks full immutable header/schema/membership, then only
the requested versions and all their files. It does not build search, create a
store, admit content, install a partial serving view or introduce a runtime.
Application remains owned by PublicGoodAccess.configure and its atomic guards.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..harness_intelligence import HarnessIntelligenceCatalogue
from ..provisioning_server import ProvisioningItemBinding, ProvisioningQualification
from . import catalogue_releases as releases
from .catalogue_bundle import BUNDLE_ITEM_RECORD_TYPE, item_version_tier, validate_item
from .catalogue_grants import require_served_state
from .catalogue_packages import VolumeBodyStore, require_body_store
from .catalogue_serving import STORE_SOURCE, _approved_resolver
from .public_good import PublicGoodGrant
from .records import ServiceRuntimeError

MAXIMUM_SELECTION = 2048
SELECTION_RECORD_TYPE = "public_good_policy_selection/v1"


def _require(value, code):
    if not value:
        raise ServiceRuntimeError(code)


@dataclass(frozen=True)
class SelectedBodyVerification:
    """Explicit selected-package coverage, never a fully qualified LoadedRelease."""

    versions: tuple
    coverage: str = "all_files_of_selected_versions_only"


@dataclass(frozen=True)
class PublicGoodPolicySelection:
    """Passive operator facts, not a CatalogueView or an installable serving API."""

    catalogue: object = field(repr=False)
    qualification_resolver: object = field(repr=False)
    packages: dict = field(repr=False)
    item_versions: dict = field(repr=False)
    release_id: str
    content_digest: str
    state_revision: int
    state_record_version: str = field(repr=False)
    pointer_record_version: str = field(repr=False)
    full_release_membership_count: int
    schema: object = field(repr=False)
    withdrawn: frozenset = frozenset()
    record_type: str = SELECTION_RECORD_TYPE

    def __post_init__(self):
        _require(self.record_type == SELECTION_RECORD_TYPE, "public_good_selection_invalid")

    def summary(self):
        """Public-safe coverage facts, without store locators or private reviews."""
        return {"record_type": self.record_type, "catalogue_release": self.release_id,
            "full_content_digest": self.content_digest, "full_release_membership_count": self.full_release_membership_count,
            "selected_versions_verified": len(self.item_versions),
            "selected_file_placements_verified": sum(len(package.files) for package in self.packages.values()),
            "selected_file_placement_bytes_verified": sum(entry.size_bytes for package in self.packages.values() for entry in package.files),
            "validation_scope": "selected_versions_only", "full_catalogue_bodies_verified": False,
            "search_prepared": False, "serving_view_installed": False}


def assert_current(binding, selection):
    """Check state/pointer unconditionally, including an empty previous policy."""
    _require(isinstance(selection, PublicGoodPolicySelection), "public_good_selection_invalid")
    with binding.store() as store:
        state_row, state = releases.read_state(binding, store)
        pointer_row, pointer = releases.read_pointer(binding, store)
        require_served_state(state, selection)
        _require(pointer is not None and pointer["release_id"] == selection.release_id, "public_good_release_changed")
        _require(state_row is not None and state_row["record_version"] == selection.state_record_version
                 and pointer_row["record_version"] == selection.pointer_record_version, "catalogue_state_changed")


def load_selection(binding, settings, grants, *, expected_release, license_policy, family_policy):
    """Read at most 2,048 exact selections, preserving full header membership.

    The full service loader remains responsible for qualifying/installing every
    served item. Missing unrelated rows or bytes are outside this operation's
    explicitly selected coverage, not silently declared valid.
    """
    _require(settings.source == STORE_SOURCE, "public_good_store_source_required")
    _require(isinstance(grants, (tuple, list)) and len(grants) <= MAXIMUM_SELECTION, "public_good_selection_limit")
    _require(all(isinstance(grant, PublicGoodGrant) for grant in grants), "public_good_selection_invalid")
    _require(len({grant.binding.identity for grant in grants}) == len(grants), "public_good_grant_not_current")
    body_store = require_body_store(VolumeBodyStore(settings.body_store_root))
    with binding.store() as store:
        state_row, state = releases.read_state(binding, store)
        pointer_row, pointer = releases.read_pointer(binding, store)
        _require(state_row is not None and pointer is not None and pointer["release_id"] == expected_release,
                 "public_good_release_changed")
        header = releases.load_release_header(binding, store, expected_release)
        read_segment = releases.segment_reader(binding, store)
        catalogue, packages, versions, approvals, selected = HarnessIntelligenceCatalogue(), {}, {}, {}, []
        for grant in grants:
            identity, version = grant.binding.identity, grant.item_version
            _require(header.version_of(identity, read_segment) == version, "public_good_grant_not_current")
            payload = releases.load_item_version(binding, store, identity, version)
            try:
                tier = item_version_tier(payload)
                # The immutable, active item version binds this admission ref
                # and these bytes; reuse publication's complete typed rules.
                entry = validate_item({"record_type": BUNDLE_ITEM_RECORD_TYPE, "reference": payload["reference"],
                    "package": payload["package"], "attributes": payload["attributes"], "approval": {
                        "tier": tier, "approval_ref": payload["approval_ref"], "approved_digest": payload["reference"]["digest"]}},
                    header.schema, license_policy=license_policy, family_policy=family_policy)
            except ServiceRuntimeError:
                raise
            except (ValueError, TypeError, KeyError, AttributeError):
                raise ServiceRuntimeError("catalogue_record_unsupported") from None
            item, package = entry.item, entry.package
            exact = ProvisioningItemBinding.from_item(item)
            _require(exact == grant.binding and payload["approval_ref"] == grant.approval_ref
                     and set(grant.useful_paths) <= {entry.path for entry in package.files}, "public_good_grant_not_current")
            _require(not releases.is_withdrawn(binding, store, identity, item.digest), "public_good_grant_not_current")
            catalogue.register(item)
            packages[identity], versions[identity] = package, version
            approvals[identity] = ProvisioningQualification(exact, "approved", "host_attested", payload["approval_ref"], tier)
            selected.append((version, payload))
    releases.verify_release_bodies(SelectedBodyVerification(tuple(selected)), body_store)
    selection = PublicGoodPolicySelection(catalogue, _approved_resolver("public_good_policy_selection/v1", approvals),
        packages, versions, expected_release, header.content_digest, state["revision"], state_row["record_version"],
        pointer_row["record_version"], header.item_count, header.schema)
    assert_current(binding, selection)
    return selection


def host_selection(path, grants, *, expected_release):
    """Return the existing runtime plus selected facts; never call served_view."""
    from .catalogue_commands import _host
    from .http_entrypoint import host_family_policy, host_license_policy
    from .runtime import ServiceRuntime

    configuration, settings, config = _host(path, needs_bodies=True)
    runtime = ServiceRuntime(config)
    selected = load_selection(runtime._catalog, settings, grants, expected_release=expected_release,
        license_policy=host_license_policy(configuration), family_policy=host_family_policy(configuration))
    return runtime, selected
