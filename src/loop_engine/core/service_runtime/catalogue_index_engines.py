"""The catalogue search index slot: interchangeable index engines behind one fixed edge.

The served search request and result (`service_retrieval_request/v2` and
`service_retrieval_result/v1`) and the authorization, fusion and tier order of
`catalogue_search.authorized_hits` stay fixed. What varies is the engine that
holds one release's index and answers `eligible` and `rank` for it:

```text
catalogue_search_index slot (edge catalogue_search_index/v1, one engine per host, chosen at host start)
├── in_memory_view_index   engine (a), the baseline and the default: ReleaseSearchIndex, built into
│                          process memory for each served view
├── sqlite_disk_index      engine (b): the same FTS5 table and hash vectors in files on the volume,
│                          with item descriptors read from the index on demand (catalogue_disk_index,
│                          catalogue_disk_view); needs numpy
└── lance_object_store_index  engine (c), planned: columnar fragments in object storage whose versions
                           map to releases (docs/architecture/CATALOGUE-AT-SCALE-2026-10-05.md)
```

Every engine answers the same edge and passes the same conformance kit
(`catalogue_index_checks`): the existing search checks and the judged queries,
run against each engine, and exact pool equality with the baseline on a fresh
build. The host names its engine in the catalogue section of its host file
(`service_catalogue_source/v2`, field `search_engine`); a section of version 1
names none and keeps the baseline. An engine that cannot run on the host is
refused when the service starts, with `search_engine_unavailable`, and never
replaced by another engine without the host saying so. An engine is an adapter
the service uses, not a runtime type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .records import ServiceRuntimeError

SLOT_ID = "catalogue_search_index"
EDGE_VERSION = "catalogue_search_index/v1"
#: The request and result of the edge's one interaction row (core.interaction.catalogue.search_index_rank): a
#: query, a mode, a pool size and typed filter conditions in; best-first candidate pools and whether a larger
#: pool could add anything out.
QUERY_CONTRACT, POOLS_CONTRACT = "catalogue_search_index_query/v1", "catalogue_search_index_pools/v1"
DESCRIPTOR_VERSION = "catalogue_search_index_engine/v1"
ENGINE_KINDS = ("in_memory_index", "disk_index", "object_store_index")
IN_MEMORY_KIND, DISK_KIND, OBJECT_STORE_KIND = ENGINE_KINDS
IN_MEMORY_ENGINE, DISK_ENGINE, OBJECT_STORE_ENGINE = (
    "in_memory_view_index", "sqlite_disk_index", "lance_object_store_index")
DEFAULT_ENGINE = IN_MEMORY_ENGINE


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


@runtime_checkable
class CatalogueSearchIndexEngine(Protocol):
    """The fixed edge: what `authorized_hits` asks of a release's index, whichever engine holds it."""

    policy: object
    schema: object

    def eligible(self, conditions): ...

    def rank(self, query, *, mode, pool, eligible=None): ...

    def stats(self) -> dict: ...


@dataclass(frozen=True)
class CatalogueIndexEngine:
    """One engine of the slot: its identity, kind, what it needs and whether it can run here."""

    engine_id: str
    engine_version: str
    kind: str
    title: str
    holds_items_on_disk: bool
    exact_with: str = ""
    requires: tuple = ()
    state: str = "candidate"
    availability: object = field(default=None, repr=False, compare=False)

    def available(self):
        if self.availability is None:
            return {"available": self.state != "planned", "reason": "" if self.state != "planned" else "planned"}
        return self.availability()

    def descriptor(self):
        state = self.available()
        return {"record_type": DESCRIPTOR_VERSION, "slot_id": SLOT_ID, "edge": EDGE_VERSION,
                "engine_id": self.engine_id, "engine_version": self.engine_version, "kind": self.kind,
                "title": self.title, "holds_items_on_disk": self.holds_items_on_disk,
                "exact_with": self.exact_with or None, "requires": list(self.requires), "state": self.state,
                "available": bool(state.get("available")), "unavailable_reason": state.get("reason") or None}


def _disk_availability():
    from .catalogue_disk_index import availability
    return availability()


#: The factory table of the slot, in declared order. The planned engine is described, never selectable.
ENGINES = {
    IN_MEMORY_ENGINE: CatalogueIndexEngine(
        IN_MEMORY_ENGINE, "1.0.0", IN_MEMORY_KIND, "SQLite FTS5 and float32 hash vectors in process memory",
        holds_items_on_disk=False, state="candidate"),
    DISK_ENGINE: CatalogueIndexEngine(
        DISK_ENGINE, "1.0.0", DISK_KIND, "SQLite FTS5 and float32 hash vectors in files on the volume",
        holds_items_on_disk=True, exact_with=IN_MEMORY_ENGINE, requires=("numpy", "sqlite_fts5"),
        state="candidate", availability=_disk_availability),
    OBJECT_STORE_ENGINE: CatalogueIndexEngine(
        OBJECT_STORE_ENGINE, "0.0.0", OBJECT_STORE_KIND,
        "Columnar fragments in object storage, one dataset version for each release",
        holds_items_on_disk=True, requires=("lancedb",), state="planned"),
}


def describe():
    """Every engine of the slot as a descriptor, in declared order. Reads nothing and starts nothing."""
    return [engine.descriptor() for engine in ENGINES.values()]


def select_engine(engine_id):
    """The engine a host named, or a typed refusal before any request; never another engine in its place."""
    engine = ENGINES.get(engine_id)
    if engine is None or engine.state == "planned":
        _refuse("search_engine_unavailable", f"the host names a search engine this image does not offer: "
                                             f"{engine_id!r}; it offers {sorted(k for k, v in ENGINES.items() if v.state != 'planned')}")
    state = engine.available()
    if not state.get("available"):
        _refuse("search_engine_unavailable", f"{engine_id} cannot run on this host: {state.get('reason')}")
    return engine


def require_index(index):
    """Refuse an object that does not speak the edge, before a request reaches it."""
    if not isinstance(index, CatalogueSearchIndexEngine):
        _refuse("search_index_unavailable", f"a catalogue index must speak {EDGE_VERSION}")
    return index


def index_size(index):
    """How many entries an index holds, from its size when it states one, otherwise from its identities."""
    size = getattr(index, "size", None)
    return size if type(size) is int else len(index.identities)
