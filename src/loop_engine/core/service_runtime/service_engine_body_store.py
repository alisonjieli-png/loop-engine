"""The catalogue body store slot: its read protocol, its engines and the one place a host chooses one.

Kind: factory table of the `catalogue_body_store` engine slot
(`src/loop_engine/data/engine_slots.yaml`). The edge is `catalogue_body_store/v1`
(`catalogue_packages.CatalogueBodyStore`: capabilities, read, put, sync); the
serving path needs only its read side, `BodyReader`, whose protocol version is
`catalogue_body_reader/v1`. Every engine answers with the same records and the
same typed refusals and passes the same kit, `catalogue_body_store_checks`.

```text
catalogue_body_store slot (one engine per host, chosen when the host starts)
├── service_volume_files   immutable files under the host's body_store_root on the service volume;
│                          the default, and what a host without a body store record keeps
└── r2_object_storage      one private bucket of Cloudflare R2 through its S3-compatible API
                           (catalogue_object_store.ObjectStoreBodyStore); needs R2 enabled on the account
```

A host names its engine in a `catalogue_body_store_engine/v1` record:

```json
{"record_type": "catalogue_body_store_engine/v1", "engine": "r2_object_storage",
 "endpoint": "https://<account id>.r2.cloudflarestorage.com", "bucket": "baltor-catalogue-bodies",
 "region": "auto", "access_key_id_ref": "env:BALTOR_R2_ACCESS_KEY_ID",
 "secret_access_key_ref": "env:BALTOR_R2_SECRET_ACCESS_KEY", "timeout_seconds": 10,
 "maximum_file_bytes": 8388608}
```

The record is read exactly: an unknown key, version or engine is refused, an R2
endpoint must be the account's S3 endpoint (or its documented `eu`, `us` or `fedramp`
jurisdiction endpoint), and the named engine is never replaced by another one;
an engine that cannot be opened is a refusal at start, not a quiet fall back to
the volume. Opening an engine reads no environment and opens no connection;
credentials are resolved at each request. Describing the slot reads nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol, runtime_checkable

from .catalogue_packages import MAXIMUM_FILE_BYTES, MAXIMUM_PACKAGE_BYTES, VOLUME_ENGINE, require_body_store
from .records import ServiceRuntimeError

SLOT_ID = "catalogue_body_store"
EDGE_VERSION = "catalogue_body_store/v1"
#: The read side of the edge, which serving needs; the slot record names it as the engine protocol.
BODY_READER_PROTOCOL_VERSION = "catalogue_body_reader/v1"
DESCRIPTOR_VERSION = "catalogue_body_store_engine_descriptor/v1"
HOST_RECORD_VERSION = "catalogue_body_store_engine/v1"
ENGINE_KINDS = ("image_files", "private_object_storage")
VOLUME_KIND, OBJECT_STORAGE_KIND = ENGINE_KINDS
OBJECT_STORAGE_ENGINE = "r2_object_storage"
DEFAULT_ENGINE = VOLUME_ENGINE
#: Account endpoints and jurisdictions documented at developers.cloudflare.com/r2/api/tokens/ on October 6, 2026.
R2_ENDPOINT = re.compile(r"https://[0-9a-f]{32}(?:\.(?:eu|us|fedramp))?\.r2\.cloudflarestorage\.com")
_RECORD_FIELDS = {"record_type", "engine", "endpoint", "bucket", "region", "access_key_id_ref",
                  "secret_access_key_ref", "timeout_seconds", "maximum_file_bytes"}
#: The fields each engine reads; a field another engine reads is refused, so a record says one thing.
_ENGINE_FIELDS = {
    VOLUME_ENGINE: {"record_type", "engine", "maximum_file_bytes"},
    OBJECT_STORAGE_ENGINE: _RECORD_FIELDS,
}
_REQUIRED_FIELDS = {
    VOLUME_ENGINE: {"record_type", "engine"},
    OBJECT_STORAGE_ENGINE: {"record_type", "engine", "endpoint", "bucket", "access_key_id_ref",
                            "secret_access_key_ref"},
}


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


@runtime_checkable
class BodyReader(Protocol):
    """The read side of the edge: what serving asks of any body engine."""

    def capabilities(self) -> dict: ...

    def read(self, digest: str, size_bytes: int) -> bytes: ...


@dataclass(frozen=True)
class BodyStoreEngine:
    """One engine of the slot: identity, kind, what it needs, and whether a host may select it."""

    engine_id: str
    engine_version: str
    kind: str
    title: str
    requires: tuple = ()
    state: str = "candidate"
    needs_the_owner: str = ""

    def descriptor(self):
        return {"record_type": DESCRIPTOR_VERSION, "slot_id": SLOT_ID, "edge": EDGE_VERSION,
                "engine_protocol": BODY_READER_PROTOCOL_VERSION, "engine_id": self.engine_id,
                "engine_version": self.engine_version, "kind": self.kind, "title": self.title,
                "requires": list(self.requires), "state": self.state,
                "needs_the_owner": self.needs_the_owner or None}


#: The factory table, in declared order. The first engine is the default.
ENGINES = {
    VOLUME_ENGINE: BodyStoreEngine(
        VOLUME_ENGINE, "1.0.0", VOLUME_KIND, "Immutable files under the body store root on the service volume"),
    OBJECT_STORAGE_ENGINE: BodyStoreEngine(
        OBJECT_STORAGE_ENGINE, "1.0.0", OBJECT_STORAGE_KIND,
        "One private Cloudflare R2 bucket through its S3-compatible API, keys sha256/<first two>/<digest>",
        requires=("r2_enabled_on_the_account", "bucket_scoped_object_credentials"),
        needs_the_owner="A configured bucket-scoped credential needs read access for serving and write access for publication"),
}


def describe():
    """Every engine as a descriptor, in declared order. Reads no file, no environment and no network."""
    return [engine.descriptor() for engine in ENGINES.values()]


def read_host_record(record):
    """The exact `catalogue_body_store_engine/v1` record, or a typed refusal before anything is opened."""
    if not isinstance(record, dict) or record.get("record_type") != HOST_RECORD_VERSION:
        _refuse("unsupported_body_store_engine", f"the body store record is {HOST_RECORD_VERSION} and nothing else")
    engine = record.get("engine")
    if not isinstance(engine, str) or engine not in ENGINES:
        _refuse("unsupported_body_store_engine", f"the body store engine is one of {tuple(ENGINES)}")
    unknown = set(record) - _ENGINE_FIELDS[engine]
    missing = _REQUIRED_FIELDS[engine] - set(record)
    if unknown or missing:
        _refuse("unsupported_body_store_engine",
                f"the {engine} record names exactly its own fields: unknown {sorted(unknown)}, missing {sorted(missing)}")
    maximum = record.get("maximum_file_bytes", MAXIMUM_FILE_BYTES)
    if type(maximum) is not int or not 1 <= maximum <= MAXIMUM_PACKAGE_BYTES:
        _refuse("unsupported_body_store_engine", "the file allowance is a positive bounded byte count")
    if engine == OBJECT_STORAGE_ENGINE:
        endpoint = record["endpoint"]
        if not isinstance(endpoint, str) or not R2_ENDPOINT.fullmatch(endpoint):
            _refuse("unsupported_body_store_engine",
                    "the R2 endpoint is https://<32 hex account id>.r2.cloudflarestorage.com, or its eu, us or fedramp form")
        if record.get("region", "auto") != "auto":
            _refuse("unsupported_body_store_engine", "the R2 region is auto")
    return dict(record)


def open_body_store(record, *, write, secret_resolver=None, root_fallback=""):
    """Open the engine a host named, negotiated on the edge; with no record, the volume engine at `root_fallback`.

    `write` is the operator's write authority for this process: a publish
    passes True, serving passes False. `root_fallback` is the catalogue
    section's `body_store_root`, which the volume engine keeps using. Nothing
    is read from the environment and nothing is contacted here.
    """
    if type(write) is not bool:
        _refuse("body_store_root_invalid", "body store write authority is an explicit Boolean")
    settings = {"record_type": HOST_RECORD_VERSION, "engine": DEFAULT_ENGINE} if record is None else read_host_record(record)
    engine = settings["engine"]
    maximum = settings.get("maximum_file_bytes", MAXIMUM_FILE_BYTES)
    if engine == VOLUME_ENGINE:
        from .catalogue_body_flush import ExactFlushVolumeBodyStore
        from .catalogue_packages import VolumeBodyStore
        kind = ExactFlushVolumeBodyStore if write else VolumeBodyStore
        return require_body_store(kind(root_fallback, writes_authorized=write, maximum_file_bytes=maximum), write=write)
    from .catalogue_object_store import ObjectStoreBodyStore
    store = ObjectStoreBodyStore(settings["endpoint"], settings["bucket"],
                                 access_key_id_ref=settings["access_key_id_ref"],
                                 secret_access_key_ref=settings["secret_access_key_ref"],
                                 region=settings.get("region", "auto"), writes_authorized=write,
                                 maximum_file_bytes=maximum,
                                 timeout_seconds=settings.get("timeout_seconds", 10),
                                 secret_resolver=secret_resolver)
    return require_body_store(store, write=write)
