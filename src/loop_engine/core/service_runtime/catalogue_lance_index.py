"""Engine `lance_object_store_index` of the catalogue search index slot, as a measured prototype.

A Lance dataset ([lancedb](https://github.com/lancedb/lancedb), Apache-2.0) holds one row for each item: its
position, identity and search text, the same 512-dimension character-hash vector the other engines use, and every
filterable attribute as a typed column with a scalar index (bitmap, label list or B-tree). A full-text index over
the text and the vector column answer `rank`; a SQL filter answers `eligible`. Every commit of a Lance dataset
is an immutable version, so one dataset can hold every release as a version and open the one a release names.

```text
Lance dataset <uri>/entries.lance
├── position, identity, text      the same entries as the other engines, in the same order
├── vector                        fixed-size list of 512 float32, the same hash vectors
├── <attribute> columns           keyword and choice as text, keyword lists as lists, numbers and dates as
│                                 float64 (dates as day ordinals), each with a scalar index
├── FTS index on text             simple tokenizer, lower case, ASCII folding, no stemming or stop words,
│                                 the nearest Lance offers to FTS5's unicode61 tokenizer
└── versions                      one per commit; BUILT.json names the version a build wrote
```

It is not exact against the in-memory engine and does not claim to be: Lance's BM25 is another implementation
with other statistics, and its vector scores are float32 dot products (1 minus Lance's dot distance) rather than
float64 sums. The kit therefore holds it to the edge, to filters that select exactly the baseline's items, and
to the judged queries within a stated tolerance, and the slot keeps it unselectable by a host (`planned`) until
a recorded comparison says otherwise. This prototype reads a local folder; an `s3://` URI with storage options
is the same call against R2, and an item-descriptor view over the dataset is not built.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
import re
import shutil

from ..retrieval import hash_vector
from .catalogue_schema import DATE, EMPTY_SCHEMA, KEYWORD_LIST, NUMBER
from .records import ServiceRuntimeError

ENGINE_ID = "lance_object_store_index"
ENGINE_VERSION = "0.1.0"
INDEX_FORMAT = "catalogue_lance_index/v1"
TABLE, MARKER_FILE = "entries", "BUILT.json"
VECTOR_DIMENSIONS = 512
LEXICAL_TERMS = 12
BUILD_BATCH = 50_000
_TOKEN = re.compile(r"[a-z0-9]+")
_COLUMN = re.compile(r"[a-z][a-z0-9_]{0,62}")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def availability():
    """Whether the prototype can run here: lancedb, pyarrow and numpy importable."""
    try:
        import lancedb  # noqa: F401
        import numpy  # noqa: F401
        import pyarrow  # noqa: F401
    except ImportError:
        return {"available": False, "reason": "lancedb_not_installed"}
    return {"available": True, "reason": ""}


def _sql_text(value):
    return "'" + str(value).replace("'", "''") + "'"


def _number(kind, value):
    return float(datetime.date.fromisoformat(value).toordinal()) if kind == DATE else float(value)


def _column(name):
    if not _COLUMN.fullmatch(name) or name in ("position", "identity", "text", "vector"):
        _refuse("search_index_invalid", "an attribute column name is a plain lower-case name")
    return f"attr_{name}"


def _batch_table(rows, kinds, pyarrow, numpy):
    from .catalogue_disk_index import vector_block
    texts = [entry.text for _position, entry in rows]
    vectors = vector_block(texts).T.astype(numpy.float32)
    columns = {"position": pyarrow.array([position for position, _entry in rows], pyarrow.int64()),
               "identity": pyarrow.array([entry.identity for _position, entry in rows], pyarrow.string()),
               "text": pyarrow.array(texts, pyarrow.string()),
               "vector": pyarrow.FixedSizeListArray.from_arrays(pyarrow.array(vectors.reshape(-1)),
                                                                VECTOR_DIMENSIONS)}
    for name, kind in kinds.items():
        values = [entry.values.get(name) for _position, entry in rows]
        if kind == KEYWORD_LIST:
            columns[_column(name)] = pyarrow.array([value if value is not None else [] for value in values],
                                                   pyarrow.list_(pyarrow.string()))
        elif kind in (NUMBER, DATE):
            columns[_column(name)] = pyarrow.array([_number(kind, value) if value is not None else None
                                                    for value in values], pyarrow.float64())
        else:
            columns[_column(name)] = pyarrow.array([value for value in values], pyarrow.string())
    return pyarrow.table(columns)


def build_lance_index(folder, entries, schema=EMPTY_SCHEMA, *, release_id=""):
    """Write one Lance dataset of `entries` (IndexEntry, in position order) into the new folder `folder`."""
    import lancedb
    import numpy
    import pyarrow
    from lancedb.index import FTS, BTree, Bitmap, LabelList
    target = Path(folder)
    if not target.is_absolute() or target.exists():
        _refuse("search_index_folder_invalid", "a Lance index is written into a new absolute folder")
    kinds = {attribute.name: attribute.type for attribute in schema.attributes if attribute.filterable}
    partial = target.with_name(f".{target.name}.partial")
    shutil.rmtree(partial, ignore_errors=True)
    database, table, batch, count = lancedb.connect(str(partial)), None, [], 0
    try:
        for position, entry in enumerate(entries):
            batch.append((position, entry))
            if len(batch) >= BUILD_BATCH:
                data = _batch_table(batch, kinds, pyarrow, numpy)
                table = database.create_table(TABLE, data=data) if table is None else table
                if table is not None and count:
                    table.add(data)
                count, batch = count + len(batch), []
        if batch or table is None:
            data = _batch_table(batch, kinds, pyarrow, numpy) if batch else None
            if table is None:
                table = database.create_table(TABLE, data=data)
            elif data is not None:
                table.add(data)
            count += len(batch)
        table.create_index("text", config=FTS(base_tokenizer="simple", lower_case=True, stem=False,
                                              remove_stop_words=False, ascii_folding=True, with_position=False))
        for name, kind in kinds.items():
            config = LabelList() if kind == KEYWORD_LIST else BTree() if kind in (NUMBER, DATE) else Bitmap()
            table.create_index(_column(name), config=config)
        marker = {"record_type": INDEX_FORMAT, "engine": ENGINE_ID, "engine_version": ENGINE_VERSION,
                  "entries": count, "release_id": release_id, "schema_digest": schema.digest,
                  "version": table.version, "filters": kinds}
        (partial / MARKER_FILE).write_text(json.dumps(marker, sort_keys=True, indent=1))
        partial.rename(target)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return target


class LanceSearchIndex:
    """The search index edge over one Lance dataset version."""

    engine = ENGINE_ID

    def __init__(self, folder, schema=EMPTY_SCHEMA, policy=None, *, version=None):
        import lancedb
        from ..retrieval_backends import RetrievalRankingPolicy
        self.policy = policy if policy is not None else RetrievalRankingPolicy()
        self.schema = schema
        try:
            self.marker = json.loads((Path(folder) / MARKER_FILE).read_text())
        except (OSError, ValueError):
            _refuse("search_index_unavailable", "the Lance index is incomplete or unreadable")
        if self.marker.get("record_type") != INDEX_FORMAT or self.marker.get("engine") != ENGINE_ID:
            _refuse("search_index_unavailable", f"this engine reads {INDEX_FORMAT} only")
        self.table = lancedb.connect(str(folder)).open_table(TABLE)
        self.table.checkout(version if version is not None else self.marker["version"])
        self.kinds = dict(self.marker["filters"])
        self.size = self.marker["entries"]

    @property
    def identities(self):
        from .catalogue_disk_index import _SizedIdentities
        return _SizedIdentities(self.size)

    def stats(self):
        return {"record_type": "catalogue_view_index/v1", "engine": ENGINE_ID, "entries": self.size,
                "version": self.table.version, "stored_on_disk": True,
                "filterable_attributes": sorted(self.kinds)}

    def eligible(self, conditions):
        """One SQL predicate for every typed condition, or None for no condition."""
        if not conditions:
            return None
        parts = []
        for name, operator, operand in conditions:
            kind, column = self.kinds.get(name), _column(name)
            if kind is None:
                parts.append("false")
            elif operator == "any_of":
                values = ", ".join(_sql_text(value) for value in operand)
                parts.append(f"array_has_any({column}, [{values}])" if kind == KEYWORD_LIST
                             else f"{column} IN ({values})")
            else:
                low, high = operand
                bounds = ([f"{column} >= {_number(kind, low)!r}"] if low is not None else []) + (
                    [f"{column} <= {_number(kind, high)!r}"] if high is not None else [])
                parts.append("(" + " AND ".join(bounds or [f"{column} IS NOT NULL"]) + ")")
        return " AND ".join(parts)

    def rank(self, query, *, mode, pool, eligible=None):
        from .catalogue_search import HYBRID_MODE
        lexical, exhausted = self._lexical(query, pool, eligible)
        pools = {"lexical": lexical}
        if mode == HYBRID_MODE:
            pools["vector"], vector_exhausted = self._vector(query, pool, eligible)
            exhausted = exhausted and vector_exhausted
        return pools, exhausted

    def _search(self, builder, eligible, pool):
        if eligible is not None:
            builder = builder.where(eligible, prefilter=True)
        return builder.limit(pool + 1).select(["identity"]).to_list()

    def _lexical(self, query, pool, eligible):
        terms = _TOKEN.findall(query.lower())[:LEXICAL_TERMS]
        if not terms or not self.size:
            return [], True
        rows = self._search(self.table.search(" ".join(terms), query_type="fts"), eligible, pool)
        ranked = sorted(((-row["_score"], row["identity"]) for row in rows))
        return [(identity, -score) for score, identity in ranked[:pool]], len(ranked) <= pool

    def _vector(self, query, pool, eligible):
        import numpy
        vector = numpy.asarray(hash_vector(query), dtype=numpy.float32)
        if not vector.any() or not self.size:
            return [], True
        builder = self.table.search(vector, vector_column_name="vector").distance_type("dot")
        rows = self._search(builder, eligible, pool)
        floor = self.policy.hash_similarity_floor
        ranked = sorted((-(1.0 - row["_distance"]), row["identity"]) for row in rows if 1.0 - row["_distance"] > floor)
        return [(identity, -score) for score, identity in ranked[:pool]], len(rows) <= pool
