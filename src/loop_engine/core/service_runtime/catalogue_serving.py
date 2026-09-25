"""The catalogue a running service serves, and how it changes without a redeploy.

The host chooses the catalogue source in the `catalogue` section of its host
file, record `service_catalogue_source/v1`:

```text
Catalogue source
├── image   the reviewed manifest packaged in the image; today's behaviour and the bootstrap
└── store   the active release in the service store, with bodies in the declared body folder
```

Whatever the source, the service serves one immutable view: the catalogue,
its qualification resolver, its body reader, and one search index built once
for that view. A request captures the view once and finishes on it. A
background refresher started by the web application checks the catalogue
state at a bounded interval, builds the next view off to the side, verifies
every body digest, and replaces the view with one assignment. A failed build
keeps the previous view and records the failure in the durable failure
journal. A durable withdrawal is honoured in both sources: the view leaves the
item out, and every manifest or body read checks the withdrawal record first.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
import threading
import time

from ..harness_intelligence import HarnessIntelligenceCatalogue
from ..provisioning_server import (QUALIFICATION_APPROVED, RUNNABLE_EFFECT, ProvisioningItemBinding,
                                   ProvisioningQualification, ProvisioningQualificationResolver)
from .catalogue_packages import FILE_BODY, CataloguePackage, VolumeBodyStore, require_body_store
from .catalogue_schema import EMPTY_SCHEMA
from .records import ServiceRuntimeError
from .storage import ServiceCatalogBinding

SOURCE_SETTINGS_VERSION = "service_catalogue_source/v1"
SOURCES = ("image", "store")
IMAGE_SOURCE, STORE_SOURCE = SOURCES
#: A view built directly in code, as local fixtures build one, rather than by a host source.
DIRECT_SOURCE = "direct"
MINIMUM_REFRESH_SECONDS, MAXIMUM_REFRESH_SECONDS, DEFAULT_REFRESH_SECONDS = 5, 3600, 60
STORE_RESOLVER_ID = "catalogue_release_review/v1"
VIEW_SUMMARY_VERSION = "service_catalogue_view/v1"


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


@dataclass(frozen=True)
class CatalogueSourceSettings:
    """Where the served catalogue comes from and how often the service looks for a new one."""

    source: str = IMAGE_SOURCE
    body_store_root: str = ""
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS
    new_accounts_follow_release: bool = False
    record_type: str = SOURCE_SETTINGS_VERSION

    def __post_init__(self):
        if self.record_type != SOURCE_SETTINGS_VERSION:
            _refuse("unsupported_catalogue_source", f"this release reads {SOURCE_SETTINGS_VERSION} only")
        if self.source not in SOURCES:
            _refuse("unsupported_catalogue_source", f"the catalogue source is one of {SOURCES}")
        if (type(self.refresh_seconds) is not int
                or not MINIMUM_REFRESH_SECONDS <= self.refresh_seconds <= MAXIMUM_REFRESH_SECONDS):
            _refuse("unsupported_catalogue_source",
                    f"the refresh interval is {MINIMUM_REFRESH_SECONDS} to {MAXIMUM_REFRESH_SECONDS} whole seconds")
        if type(self.new_accounts_follow_release) is not bool:
            _refuse("unsupported_catalogue_source", "new_accounts_follow_release is an explicit Boolean")
        if not isinstance(self.body_store_root, str) or (self.body_store_root and not self.body_store_root.startswith("/")):
            _refuse("unsupported_catalogue_source", "the body store root is an absolute folder")
        if self.source == STORE_SOURCE and not self.body_store_root:
            _refuse("unsupported_catalogue_source", "the store source names its body store root")


def catalogue_settings(configuration):
    """Return the catalogue section of a host file, or None when the host did not declare one."""
    if "catalogue" not in configuration:
        return None
    value = configuration["catalogue"]
    allowed = {"record_type", "source", "body_store_root", "refresh_seconds", "new_accounts_follow_release"}
    if not isinstance(value, dict) or "record_type" not in value or set(value) - allowed:
        _refuse("unsupported_catalogue_source", "the catalogue section names its record version and known fields only")
    return CatalogueSourceSettings(**value)


@dataclass(frozen=True)
class CatalogueView:
    """One immutable catalogue as the service serves it. Requests capture one and finish on it."""

    catalogue: HarnessIntelligenceCatalogue
    qualification_resolver: ProvisioningQualificationResolver
    body_reader: object = field(repr=False)
    source: str = DIRECT_SOURCE
    release_id: str = ""
    content_digest: str = ""
    schema: object = EMPTY_SCHEMA
    packages: dict = field(default_factory=dict, repr=False)
    attributes: dict = field(default_factory=dict, repr=False)
    bindings: dict = field(default_factory=dict, repr=False)
    withdrawn: frozenset = frozenset()
    withdrawal_check: object = field(default=None, repr=False)
    body_store: object = field(default=None, repr=False)
    index: object = field(default=None, repr=False)
    state_revision: int = 0
    built_at: float = 0.0
    #: The served release's own record of what it added, changed and withdrew, each with its note; the public library
    #: page lists it. A view built in code or from the image has none.
    changes: dict = field(default_factory=dict, repr=False, compare=False)
    _lazy: dict = field(default_factory=dict, repr=False, compare=False)

    def approved_bindings(self):
        """identity -> exact binding of every item this view approves."""
        if self.bindings or self.source != DIRECT_SOURCE:
            return self.bindings
        # A view built directly in code, as the local fixtures do, asks its own
        # resolver, so a grant can never reach further than the resolver does.
        approved = {}
        for identity, item in tuple(self.catalogue.items.items()):
            binding = ProvisioningItemBinding.from_item(item)
            try:
                decision = self.qualification_resolver.resolve(binding)
            except Exception:
                continue
            if isinstance(decision, ProvisioningQualification) and decision.status == QUALIFICATION_APPROVED:
                approved[identity] = binding
        return approved

    def search_index(self):
        """The view's one reusable index; a direct view rebuilds it only when its items change."""
        if self.index is not None:
            return self.index
        from .catalogue_search import index_for_items
        items = tuple(sorted(self.catalogue.items.values(), key=lambda item: item.identity))
        fingerprint = tuple((item.identity, item.digest, item.purpose) for item in items)
        with self._lazy.setdefault("lock", threading.Lock()):
            held = self._lazy.get("index")
            if held is None or held[0] != fingerprint:
                held = (fingerprint, index_for_items(items))
                self._lazy["index"] = held
            return held[1]

    def summary(self):
        return {"record_type": VIEW_SUMMARY_VERSION, "source": self.source, "release_id": self.release_id or None,
                "content_digest": self.content_digest or None, "items": len(self.catalogue.items),
                "withdrawn_left_out": len(self.withdrawn), "schema_digest": self.schema.digest,
                "catalogue_state_revision": self.state_revision, "built_at": int(self.built_at)}

    def shown_attributes(self, identity):
        return self.schema.shown_values(self.attributes.get(identity, {}))

    def package_summary(self, identity):
        package = self.packages.get(identity)
        if package is None:
            return None
        return {"body_form": package.body_form, "package_digest": package.package_digest,
                "files": [{"path": entry.path, "media_type": entry.media_type, "role": entry.role,
                           "size_bytes": entry.size_bytes, "digest": entry.digest} for entry in package.files]}

    def read_package_file(self, identity, path):
        """The verified bytes of one file of one package, after the item's own body read was authorized."""
        package = self.packages.get(identity)
        if package is None or self.body_store is None:
            _refuse("package_files_unavailable", "this catalogue serves no package files for that item")
        entry = package.file(path)
        if self.withdrawal_check is not None:
            self.withdrawal_check(identity, package.served_digest)
        return self.body_store.read(entry.digest, entry.size_bytes), entry

    def without(self, withdrawn, *, state_revision):
        """A new view with every durably withdrawn item left out; the index is shared, not rebuilt."""
        keep = {identity: item for identity, item in self.catalogue.items.items()
                if (identity, item.digest) not in withdrawn}
        return replace(self, catalogue=HarnessIntelligenceCatalogue(keep),
                       bindings={identity: value for identity, value in self.bindings.items() if identity in keep},
                       withdrawn=frozenset(withdrawn), state_revision=state_revision, built_at=time.time(),
                       index=self.search_index(), _lazy={})


def _withdrawal_check(config):
    from . import catalogue_releases
    binding = ServiceCatalogBinding(config)

    def check(identity, body_digest):
        with binding.store() as store:
            if catalogue_releases.is_withdrawn(binding, store, identity, body_digest):
                _refuse("item_withdrawn", "this item version was withdrawn from the library")
    return check


def _approved_resolver(resolver_id, approvals):
    def resolve(binding):
        decision = approvals.get(binding.identity)
        return decision if decision is not None and decision.binding == binding else ProvisioningQualification(
            binding, "unknown", "host_attested")
    return ProvisioningQualificationResolver(resolver_id, resolve)


def image_view(catalogue, resolver, reader, *, config=None, withdrawn=frozenset(), state_revision=0):
    """The view of the packaged manifest, with one index built now and durable withdrawals applied."""
    from .catalogue_search import index_for_items
    check = _withdrawal_check(config) if config is not None else None
    keep = {identity: item for identity, item in catalogue.items.items() if (identity, item.digest) not in withdrawn}

    def guarded_reader(item):
        if check is not None:
            check(item.identity, item.digest)
        return reader(item)
    bindings = {identity: ProvisioningItemBinding.from_item(item) for identity, item in keep.items()}
    return CatalogueView(HarnessIntelligenceCatalogue(dict(keep)), resolver, guarded_reader, source="image",
                         bindings=bindings, withdrawn=frozenset(withdrawn), withdrawal_check=check,
                         index=index_for_items(tuple(sorted(keep.values(), key=lambda item: item.identity))),
                         state_revision=state_revision, built_at=time.time())


def store_view(config, settings, *, license_policy, family_policy):
    """Build the view of the active release: verify every record and body, then index it once."""
    from ..practitioner_runtime.provisioning import _item
    from .catalogue_bundle import item_version_tier
    from .catalogue_releases import load_release, read_pointer, read_state, verify_release_bodies, withdrawal_keys
    from .catalogue_search import IndexEntry, ReleaseSearchIndex, entry_text
    binding = ServiceCatalogBinding(config)
    body_store = require_body_store(VolumeBodyStore(settings.body_store_root))
    with binding.store() as store:
        _state_row, state = read_state(binding, store)
        _pointer_row, pointer = read_pointer(binding, store)
        if pointer is None:
            _refuse("catalogue_release_not_published", "the store source needs a published release")
        release = load_release(binding, store, pointer["release_id"])
        withdrawn = withdrawal_keys(binding, store)
    # Every body of every served item is read and checked before this view
    # can be installed; a changed byte keeps the previous view serving.
    verify_release_bodies(release, body_store, withdrawn=withdrawn)
    catalogue, approvals, packages, attributes, bindings, entries = HarnessIntelligenceCatalogue(), {}, {}, {}, {}, []
    for _version, payload in release.versions:
        item = _item(payload["reference"])
        package = CataloguePackage.from_dict(payload["package"])
        refused = family_policy.refusal(item.family) or license_policy.refusal(item.license_name)
        if refused:
            _refuse(refused, "the host family or licence policy refuses an item of the active release")
        if item.digest != package.served_digest or item.size_bytes != package.served_size:
            _refuse("catalogue_release_digest_mismatch", "an item reference names other bytes than its package")
        if (item.identity, package.served_digest) in withdrawn:
            continue
        tier = item_version_tier(payload)
        values = release.schema.validate_values(payload["attributes"])
        catalogue.register(item)
        exact = ProvisioningItemBinding.from_item(item)
        approvals[item.identity] = ProvisioningQualification(exact, "approved", "host_attested", payload["approval_ref"],
                                                             tier)
        packages[item.identity], attributes[item.identity], bindings[item.identity] = package, values, exact
        entries.append(IndexEntry(item.identity, entry_text(item, release.schema.search_text(values)), values,
                                  tier, RUNNABLE_EFFECT in item.declared_effects))
    check = _withdrawal_check(config)

    def reader(item):
        package = packages[item.identity]
        check(item.identity, package.served_digest)
        if package.body_form == FILE_BODY:
            entry = package.files[0]
            return body_store.read(entry.digest, entry.size_bytes).decode("utf-8")
        return package.document().decode("utf-8")
    from .catalogue_releases import content_digest
    return CatalogueView(catalogue, _approved_resolver(STORE_RESOLVER_ID, approvals), reader, source=STORE_SOURCE,
                         release_id=release.release_id, content_digest=content_digest(release.schema.digest, release.items),
                         schema=release.schema, packages=packages, attributes=attributes, bindings=bindings,
                         withdrawn=frozenset(key for key in withdrawn if key[0] in dict(release.items)),
                         withdrawal_check=check, body_store=body_store,
                         index=ReleaseSearchIndex(tuple(entries), release.schema),
                         state_revision=state["revision"] if state else 0, built_at=time.time(),
                         changes=dict(release.document.get("changes") or {}))


def catalogue_state_gate(config, settings):
    """Refuse to start against catalogue state this image does not understand, or that the host file hides.

    The gate reads the marker and writes nothing. A store that cannot be opened
    is left to the readiness check, as before this gate existed.
    """
    from .catalogue_releases import read_state
    binding = ServiceCatalogBinding(config)
    try:
        with binding.store() as store:
            _row, state = read_state(binding, store)
    except ServiceRuntimeError as error:
        if error.code == "store_unavailable":
            return None
        raise
    if state is not None and settings is None:
        _refuse("catalogue_section_required",
                "the service store holds catalogue state, so the host file must declare its catalogue section")
    return state


def state_token(config):
    """What the refresher compares: the marker revision and the active release. This only reads."""
    from .catalogue_releases import read_pointer, read_state
    binding = ServiceCatalogBinding(config)
    with binding.store() as store:
        _row, state = read_state(binding, store)
        _pointer_row, pointer = read_pointer(binding, store)
    return (state["revision"] if state else 0, pointer["release_id"] if pointer else "")


def next_view(current, token, config, settings, *, license_policy, family_policy):
    """The view for a changed catalogue state: a full build for a new release, a cheaper one for withdrawals."""
    from .catalogue_releases import withdrawal_keys
    revision, release_id = token
    if settings.source == STORE_SOURCE and release_id != current.release_id:
        return store_view(config, settings, license_policy=license_policy, family_policy=family_policy)
    binding = ServiceCatalogBinding(config)
    with binding.store() as store:
        withdrawn = withdrawal_keys(binding, store)
    return current.without(withdrawn | current.withdrawn, state_revision=revision)


class CatalogueRefresher:
    """Checks the catalogue state on an interval and swaps in a fully verified view.

    It runs on the event loop's default executor, never on the bounded customer
    pool, so a slow build cannot take a worker a customer needs.
    """

    def __init__(self, provisioning, *, build, probe, journal=None, interval_seconds=DEFAULT_REFRESH_SECONDS,
                 clock=time.time):
        self.provisioning, self.build, self.probe, self.journal = provisioning, build, probe, journal
        self.interval_seconds, self.clock = interval_seconds, clock
        view = provisioning.current_view()
        self._token = (view.state_revision, view.release_id)
        # The health record reads the refresher through the binding it refreshes.
        provisioning.catalogue_refresher = self
        self.last_failure_code, self.last_checked_at, self.swaps, self.last_swap_seconds = "", 0, 0, None
        self._lock = threading.Lock()

    def check_once(self):
        with self._lock:
            self.last_checked_at = int(self.clock())
            try:
                token = self.probe()
                if token == self._token:
                    return {"changed": False}
                started = time.perf_counter()
                view = self.build(self.provisioning.current_view(), token)
            except Exception as error:
                code = getattr(error, "code", "") or "catalogue_refresh_failed"
                self.last_failure_code = code
                self._record(code)
                return {"changed": False, "failure": code}
            self.provisioning.install_view(view)
            self._token = token
            self.swaps += 1
            self.last_swap_seconds = round(time.perf_counter() - started, 3)
            self.last_failure_code = ""
            return {"changed": True, "release_id": view.release_id, "seconds": self.last_swap_seconds}

    def _record(self, code):
        if self.journal is None:
            return
        from .observability import OTHER_METHOD, UNMATCHED_ROUTE, new_request_reference
        self.journal.record(new_request_reference(), route=UNMATCHED_ROUTE, method=OTHER_METHOD,
                            refusal_code=("catalogue_refresh:" + code)[:128], status=503, tenant_id="")

    async def run(self):
        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(self.interval_seconds)
            await loop.run_in_executor(None, self.check_once)

    def status(self):
        return {"interval_seconds": self.interval_seconds, "last_checked_at": self.last_checked_at,
                "last_failure_code": self.last_failure_code or None, "swaps": self.swaps,
                "last_swap_seconds": self.last_swap_seconds}


def load_catalogue_view(configuration, config, *, license_policy, family_policy):
    """The view a host file selects at start, after the catalogue state gate, and its source settings."""
    from .catalogue_releases import withdrawal_keys
    from .http_entrypoint import load_host_manifest
    settings = catalogue_settings(configuration)
    state = catalogue_state_gate(config, settings)
    if settings is not None and settings.source == STORE_SOURCE:
        return store_view(config, settings, license_policy=license_policy, family_policy=family_policy), settings
    catalogue, resolver, reader, _grants = load_host_manifest(
        configuration["manifest_path"], license_policy=license_policy, family_policy=family_policy)
    if settings is None:
        return image_view(catalogue, resolver, reader), None
    binding = ServiceCatalogBinding(config)
    with binding.store() as store:
        withdrawn = withdrawal_keys(binding, store)
    return image_view(catalogue, resolver, reader, config=config, withdrawn=withdrawn,
                      state_revision=state["revision"] if state else 0), settings


def refresher_for(application, settings, *, license_policy, family_policy):
    """The refresher of one application, reading the same store and writing failures to its journal."""
    config = application.runtime.config
    refresher = CatalogueRefresher(
        application.provisioning,
        build=lambda current, token: next_view(current, token, config, settings,
                                               license_policy=license_policy, family_policy=family_policy),
        probe=lambda: state_token(config), journal=application.failure_journal,
        interval_seconds=settings.refresh_seconds)
    return refresher
