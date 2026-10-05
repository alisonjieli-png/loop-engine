"""Engine `sqlite_disk_index` of the catalogue search index slot: the same ranking, held on disk.

The in-memory engine (`catalogue_search.ReleaseSearchIndex`) keeps a SQLite
full-text table, 512 float32 hash-vector columns and the filter tables of a
whole view in process memory: about 3.2 kilobytes for each item, measured on
October 5, 2026. This engine keeps the same three things in files on the
volume and reads them per query, so its memory does not grow with the library.

```text
One disk index, written once into its own folder and never changed afterwards
├── index.sqlite   entries(position, identity, item version, stored item record), a
│                  contentless FTS5 table over the same text, the distinct files with
│                  their reference counts, and the build record (meta)
├── vectors.f32    512 float32 columns of the same character-hash vectors,
│                  column-major, memory-mapped; a query reads its own dimensions
├── filter files   one inverted list per filterable keyword attribute and one
│                  sorted value list per number or date attribute
└── BUILT.json     written last: engine, format, counts and the digest of every file
```

Equivalence with the in-memory engine, for the same entries in the same order:

- lexical: the same `MATCH` expression, `bm25()` and `ORDER BY bm25, position`. FTS5 bm25 reads only token
  counts, so a contentless single-column table scores exactly as the two-column table with an UNINDEXED column.
- hybrid: the same hash vectors, scored by adding float64 products in the same dimension order, so every score is
  bit-identical; the floor and the `(-score, position)` order are the same.
- filters: the same conditions, answered from the inverted and sorted lists instead of Python sets.

A filter is applied while ranking instead of fetching every match first, so a filtered query reads the matches
until the pool is full rather than the whole match list.

An overlay serves a later release from an earlier full index without rebuilding it: the base index with the
positions of removed and changed items masked, plus a small delta index of the added and changed items. Vector
scores do not depend on the corpus, so they stay exact. Lexical scores of delta items are computed with the base
index's own statistics by the same bm25 formula FTS5 uses, so base and delta scores are comparable; they equal a
full rebuild's scores only up to the change in corpus statistics that the delta brings, and a full rebuild
replaces the overlay when the delta grows past `OVERLAY_REBUILD_FRACTION` of the base.

This engine needs numpy (BSD-3-Clause) and SQLite with FTS5. `availability()` says whether they are present; a
host that selects this engine without them is refused at start, before any request, and never falls back.
"""
from __future__ import annotations

import datetime
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import threading

from ..retrieval import hash_vector
from .catalogue_schema import DATE, EMPTY_SCHEMA, KEYWORD_LIST, NUMBER
from .records import ServiceRuntimeError

ENGINE_ID = "sqlite_disk_index"
ENGINE_VERSION = "1.0.0"
INDEX_FORMAT = "catalogue_disk_index/v1"
OVERLAY_FORMAT = "catalogue_disk_index_overlay/v1"
DATABASE_FILE, VECTOR_FILE, MARKER_FILE = "index.sqlite", "vectors.f32", "BUILT.json"
#: The two kinds of filter file: an inverted list per keyword, choice or list attribute, and a sorted value list
#: per number or date attribute. Each names its files `<kind>-<attribute>-*.npy` and its build record entry.
FILTER_FILE_KINDS = ("keyword", "range")
KEYWORD_FILTER, RANGE_FILTER = FILTER_FILE_KINDS
#: Positions scored together in one vector chunk; bounds the float64 work arrays to a few megabytes.
VECTOR_CHUNK = 262_144
#: Rows inserted into the full-text table in one statement batch while building.
BUILD_BATCH = 20_000
#: Up to this many entries a build checks identities for duplicates with a set; a larger build takes its entries
#: in identity order and checks each against the one before, so it holds no set.
SMALL_BUILD_ENTRIES = 200_000
#: The same limits and token rule as the in-memory engine.
LEXICAL_TERMS = 12
VECTOR_DIMENSIONS = 512
#: bm25 constants of FTS5 (fts5_aux.c), used to score delta items with the base index's statistics.
BM25_K1, BM25_B = 1.2, 0.75
#: An overlay whose delta passes this share of the base is replaced by a full rebuild.
OVERLAY_REBUILD_FRACTION = 0.10
#: Below this many base entries a full rebuild takes about a minute or less and keeps every score exact, so no
#: overlay is built; above it the statistics a delta shifts are a small share of the corpus.
OVERLAY_MINIMUM_BASE = 50_000
#: SQLite pages a reader keeps in memory: about 32 megabytes at 4 kilobyte pages.
READER_CACHE_PAGES = 8_000
_TOKEN = re.compile(r"[a-z0-9]+")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def _numpy():
    try:
        import numpy
    except ImportError:
        _refuse("search_engine_unavailable", f"{ENGINE_ID} needs numpy, which is not installed")
    return numpy


def availability():
    """Whether this engine can run here, with the reason when it cannot. Imports nothing it does not need."""
    try:
        import numpy  # noqa: F401
    except ImportError:
        return {"available": False, "reason": "numpy_not_installed"}
    try:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE VIRTUAL TABLE probe USING fts5(body, content='')")
        connection.close()
    except sqlite3.Error:
        return {"available": False, "reason": "sqlite_without_fts5"}
    return {"available": True, "reason": "", "sqlite_version": sqlite3.sqlite_version}


def _file_digest(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _date_number(value):
    return float(datetime.date.fromisoformat(value).toordinal())


def _range_number(kind, value):
    return _date_number(value) if kind == DATE else float(value)


#: Distinct words whose hash buckets a build keeps worked out; past this the memo starts again, so a library of
#: unique identities cannot grow it without bound.
TOKEN_MEMO_LIMIT = 250_000
_WORKER_BUCKETS = None


def vector_block(texts):
    """The float32 vector columns of one block of texts, `(VECTOR_DIMENSIONS, len(texts))`.

    The weights are the in-memory engine's doubles (`_TokenBuckets.vector`, equal to `hash_vector` bit for bit),
    rounded to float32 as `array("f")` rounds them, gathered in flat lists and placed with one array assignment.
    """
    global _WORKER_BUCKETS
    numpy = _numpy()
    from .catalogue_search import _TokenBuckets
    if _WORKER_BUCKETS is None or len(_WORKER_BUCKETS._held) > TOKEN_MEMO_LIMIT:
        _WORKER_BUCKETS = _TokenBuckets()
    dimensions, offsets, weights = [], [], []
    for offset, text in enumerate(texts):
        for dimension, weight in _WORKER_BUCKETS.vector(text):
            if weight:
                dimensions.append(dimension)
                offsets.append(offset)
                weights.append(weight)
    block = numpy.zeros((VECTOR_DIMENSIONS, len(texts)), dtype=numpy.float32)
    block[numpy.asarray(dimensions, dtype=numpy.int64), numpy.asarray(offsets, dtype=numpy.int64)] = (
        numpy.asarray(weights, dtype=numpy.float64).astype(numpy.float32))
    return block


class _VectorWriter:
    """Hash vectors of the same features as the in-memory engine, written one block of positions at a time.

    With `workers` above one, blocks are computed in that many processes, at most two blocks ahead of each, and
    written in position order; the result is the same bytes.
    """

    def __init__(self, path, count, workers=1):
        numpy = _numpy()
        self.numpy = numpy
        self.columns = numpy.lib.format.open_memmap(path, mode="w+", dtype=numpy.float32,
                                                    shape=(VECTOR_DIMENSIONS, max(1, count)))
        self.pool, self.pending = None, []
        if workers > 1:
            from concurrent.futures import ProcessPoolExecutor
            self.pool, self.window = ProcessPoolExecutor(max_workers=workers), 2 * workers

    def write(self, start, texts):
        if self.pool is None:
            self.columns[:, start:start + len(texts)] = vector_block(texts)
            return
        self.pending.append((start, len(texts), self.pool.submit(vector_block, list(texts))))
        while len(self.pending) > self.window:
            self._drain_one()

    def _drain_one(self):
        start, size, future = self.pending.pop(0)
        self.columns[:, start:start + size] = future.result()

    def close(self):
        while self.pending:
            self._drain_one()
        if self.pool is not None:
            self.pool.shutdown()
        self.columns.flush()
        del self.columns


def build_disk_index(folder, entries, schema=EMPTY_SCHEMA, *, count=None, release_id="", content_digest="",
                     note="", policy_fingerprint="", workers=1):
    """Write one immutable disk index of `entries` into the new folder `folder`.

    Each entry is an `IndexEntry`, for a search-only index, or a triple `(IndexEntry, item version, item record)`,
    whose record is stored so a disk view reads item descriptors from the index instead of holding them. Entries
    come in position order. `entries` may be any iterable; `count` must then name how many it yields, so the
    vector file can be sized before the first entry is read and the build never holds the entries. The folder
    appears only when the build is complete: everything is written to a sibling partial folder that is renamed
    at the end. `workers` above one computes the vectors in that many processes; the files are the same.
    """
    numpy = _numpy()
    target = Path(folder)
    if not target.is_absolute() or target.exists():
        _refuse("search_index_folder_invalid", "a disk index is written into a new absolute folder")
    if count is None:
        entries = tuple(entries)
        count = len(entries)
    if type(count) is not int or count < 0:
        _refuse("search_index_folder_invalid", "an index names how many entries it holds")
    partial = target.with_name(f".{target.name}.partial-{secrets.token_hex(6)}")
    partial.mkdir(parents=True)
    try:
        connection = sqlite3.connect(str(partial / DATABASE_FILE))
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA cache_size=-65536")
        connection.executescript("""
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE entries(position INTEGER PRIMARY KEY, identity TEXT NOT NULL, item_version TEXT NOT NULL,
                                 record TEXT NOT NULL);
            CREATE TABLE files(digest TEXT PRIMARY KEY, size INTEGER NOT NULL, refs INTEGER NOT NULL) WITHOUT ROWID;
            CREATE VIRTUAL TABLE fts USING fts5(body, content='');
        """)
        vectors = _VectorWriter(partial / VECTOR_FILE, count, workers)
        from array import array
        filterable = [attribute for attribute in schema.attributes if attribute.filterable]
        kinds = {attribute.name: attribute.type for attribute in filterable}
        # Filter values accumulate in flat machine arrays, eight bytes a value, never in Python tuples.
        keyword_codes = {name: {} for name, kind in kinds.items() if kind not in (NUMBER, DATE)}
        keyword_postings = {name: (array("q"), array("q")) for name in keyword_codes}
        range_values = {name: (array("d"), array("q")) for name, kind in kinds.items() if kind in (NUMBER, DATE)}
        position, batch, texts, identities, files = 0, [], [], [], []
        placements, packages, missing = 0, 0, 0
        seen = set() if count <= SMALL_BUILD_ENTRIES else None

        def flush():
            nonlocal batch, texts, identities, files
            if not batch:
                return
            connection.executemany("INSERT INTO entries(position, identity, item_version, record) VALUES (?, ?, ?, ?)",
                                   identities)
            connection.executemany("INSERT INTO fts(rowid, body) VALUES (?, ?)", batch)
            # A digest named with two byte counts keeps size -1, which the build refuses below.
            connection.executemany("INSERT INTO files(digest, size, refs) VALUES (?, ?, 1) "
                                   "ON CONFLICT(digest) DO UPDATE SET refs = refs + 1, "
                                   "size = CASE WHEN size = excluded.size THEN size ELSE -1 END", files)
            vectors.write(batch[0][0], texts)
            batch, texts, identities, files = [], [], [], []

        previous = None
        for row in entries:
            entry, version, record = row if isinstance(row, tuple) else (row, "", None)
            if position >= count:
                _refuse("search_index_invalid", "the entries outnumber the count the build was given")
            if seen is not None:
                if entry.identity in seen:
                    _refuse("catalogue_index_invalid", "an index holds each identity once")
                seen.add(entry.identity)
            elif previous is not None and entry.identity <= previous:
                # A large build holds no identity set; its entries come in identity order instead.
                _refuse("catalogue_index_invalid", "a large index is built from entries in identity order")
            previous = entry.identity
            text = record if isinstance(record, str) else (
                json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                if record is not None else "")
            if isinstance(record, str):
                record = json.loads(record)
            identities.append((position, entry.identity, version, text))
            if record is not None:
                packages += 1
                listed = record.get("package", {}).get("files") if isinstance(record.get("package"), dict) else None
                if listed is None:
                    missing += 1
                else:
                    for file in listed:
                        placements += 1
                        files.append((file["digest"], file["size_bytes"]))
            batch.append((position, entry.text))
            texts.append(entry.text)
            for name, kind in kinds.items():
                if name not in entry.values:
                    continue
                value = entry.values[name]
                if name in range_values:
                    values, positions = range_values[name]
                    values.append(_range_number(kind, value))
                    positions.append(position)
                    continue
                codes = keyword_codes[name]
                held_codes, held_positions = keyword_postings[name]
                for element in (value if kind == KEYWORD_LIST else (value,)):
                    held_codes.append(codes.setdefault(element, len(codes)))
                    held_positions.append(position)
            position += 1
            if len(batch) >= BUILD_BATCH:
                flush()
        flush()
        if position != count:
            _refuse("search_index_invalid", "the entries are fewer than the count the build was given")
        vectors.close()
        filter_files = {}
        for name, (held_codes, held_positions) in keyword_postings.items():
            codes_array = numpy.frombuffer(held_codes, dtype=numpy.int64) if held_codes else numpy.zeros(0, numpy.int64)
            positions = (numpy.frombuffer(held_positions, dtype=numpy.int64) if held_positions
                         else numpy.zeros(0, numpy.int64))
            # Positions were appended in increasing order, so a stable sort by code keeps each list in position order.
            order = numpy.argsort(codes_array, kind="stable")
            codes_array, positions = codes_array[order], positions[order]
            offsets = numpy.searchsorted(codes_array, numpy.arange(len(keyword_codes[name]) + 1), side="left")
            numpy.save(partial / f"{KEYWORD_FILTER}-{name}-offsets.npy", offsets.astype(numpy.int64))
            numpy.save(partial / f"{KEYWORD_FILTER}-{name}-positions.npy", positions.astype(numpy.int64))
            del codes_array, positions, order
            filter_files[f"{KEYWORD_FILTER}-{name}"] = {"values": {str(value): code
                                                          for value, code in keyword_codes[name].items()},
                                               "type": kinds[name]}
        for name, (held_values, held_positions) in range_values.items():
            values = numpy.frombuffer(held_values, dtype=numpy.float64) if held_values else numpy.zeros(0)
            positions = (numpy.frombuffer(held_positions, dtype=numpy.int64) if held_positions
                         else numpy.zeros(0, numpy.int64))
            # The same order as sorting (value, position) pairs: by value, ties in position order.
            order = numpy.argsort(values, kind="stable")
            numpy.save(partial / f"{RANGE_FILTER}-{name}-values.npy", values[order])
            numpy.save(partial / f"{RANGE_FILTER}-{name}-positions.npy", positions[order])
            filter_files[f"{RANGE_FILTER}-{name}"] = {"type": kinds[name]}
        total_tokens = _total_tokens(connection)
        connection.execute("CREATE UNIQUE INDEX entries_identity ON entries(identity)")
        distinct, distinct_bytes = connection.execute("SELECT count(*), coalesce(sum(size), 0) FROM files").fetchone()
        conflicting = connection.execute("SELECT count(*) FROM files WHERE size < 0").fetchone()[0]
        if conflicting:
            _refuse("package_file_size_conflict", "one file digest names different byte counts")
        population = {"packages": packages, "file_placements": placements, "distinct_files": distinct,
                      "distinct_file_bytes": distinct_bytes, "packages_without_file_manifest": missing}
        meta = {"record_type": INDEX_FORMAT, "engine": ENGINE_ID, "engine_version": ENGINE_VERSION,
                "entries": count, "release_id": release_id, "content_digest": content_digest,
                "schema_digest": schema.digest, "filters": filter_files, "total_tokens": total_tokens,
                "vector_dimensions": VECTOR_DIMENSIONS, "note": note, "population": population,
                "policy_fingerprint": policy_fingerprint}
        connection.executemany("INSERT INTO meta(key, value) VALUES (?, ?)",
                               [(key, json.dumps(value, sort_keys=True)) for key, value in meta.items()])
        connection.commit()
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.close()
        digests = {path.name: _file_digest(path) for path in sorted(partial.iterdir()) if path.is_file()}
        (partial / MARKER_FILE).write_text(json.dumps({**meta, "files": digests}, sort_keys=True, indent=1))
        os.sync()
        os.rename(partial, target)
    except BaseException:
        if "vectors" in locals() and getattr(vectors, "pool", None) is not None:
            vectors.pool.shutdown(cancel_futures=True)
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return target


def _total_tokens(connection):
    """The total token count of the full-text table, the denominator FTS5 uses for its average row size."""
    connection.execute("CREATE VIRTUAL TABLE temp.size_vocabulary USING fts5vocab(main, fts, 'row')")
    try:
        value = connection.execute("SELECT coalesce(sum(cnt), 0) FROM temp.size_vocabulary").fetchone()[0]
    finally:
        connection.execute("DROP TABLE temp.size_vocabulary")
    return int(value)


class DiskIndex:
    """One built disk index, opened read-only. Thread-safe: one SQLite connection per thread."""

    def __init__(self, folder, *, verify_files=False):
        numpy = _numpy()
        self.numpy = numpy
        self.folder = Path(folder)
        try:
            marker = json.loads((self.folder / MARKER_FILE).read_text())
        except (OSError, ValueError):
            _refuse("search_index_unavailable", "the disk index is incomplete or unreadable")
        if (marker.get("record_type") != INDEX_FORMAT or marker.get("engine") != ENGINE_ID
                or marker.get("engine_version") != ENGINE_VERSION):
            _refuse("search_index_unavailable", f"this engine reads {INDEX_FORMAT} written by {ENGINE_ID} "
                                                f"{ENGINE_VERSION} only")
        if verify_files:
            for name, digest in marker["files"].items():
                if _file_digest(self.folder / name) != digest:
                    _refuse("search_index_unavailable", "a disk index file differs from its build record")
        self.marker = marker
        self.size = marker["entries"]
        self.total_tokens = marker["total_tokens"]
        self.release_id = marker["release_id"]
        self._local = threading.local()
        self.columns = numpy.load(self.folder / VECTOR_FILE, mmap_mode="r") if self.size else None
        self._keyword, self._range = {}, {}
        for key, value in marker["filters"].items():
            kind, name = key.split("-", 1)
            if kind == KEYWORD_FILTER:
                self._keyword[name] = (value["values"],
                                       numpy.load(self.folder / f"{KEYWORD_FILTER}-{name}-offsets.npy", mmap_mode="r"),
                                       numpy.load(self.folder / f"{KEYWORD_FILTER}-{name}-positions.npy", mmap_mode="r"),
                                       value["type"])
            elif kind == RANGE_FILTER:
                self._range[name] = (numpy.load(self.folder / f"{RANGE_FILTER}-{name}-values.npy", mmap_mode="r"),
                                     numpy.load(self.folder / f"{RANGE_FILTER}-{name}-positions.npy", mmap_mode="r"),
                                     value["type"])
            else:
                _refuse("search_index_unavailable", f"the disk index names an unknown filter kind {kind!r}")

    def connection(self):
        held = getattr(self._local, "connection", None)
        if held is None:
            uri = (self.folder / DATABASE_FILE).resolve().as_uri() + "?mode=ro&immutable=1"
            held = sqlite3.connect(uri, uri=True, check_same_thread=False)
            held.execute(f"PRAGMA cache_size={READER_CACHE_PAGES}")
            self._local.connection = held
        return held

    def identity_at(self, positions):
        """Identities of positions, in the order given."""
        if not positions:
            return []
        wanted = list(dict.fromkeys(int(position) for position in positions))
        found = {}
        connection = self.connection()
        for start in range(0, len(wanted), 900):
            part = wanted[start:start + 900]
            rows = connection.execute(
                f"SELECT position, identity FROM entries WHERE position IN ({','.join('?' * len(part))})", part)
            found.update(rows)
        return [found[int(position)] for position in positions]

    def records(self, identities):
        """identity -> (position, item version, stored item record text) for the identities this index holds."""
        wanted = list(dict.fromkeys(identities))
        found, connection = {}, self.connection()
        for start in range(0, len(wanted), 900):
            part = wanted[start:start + 900]
            for identity, position, version, record in connection.execute(
                    "SELECT identity, position, item_version, record FROM entries "
                    f"WHERE identity IN ({','.join('?' * len(part))})", part):
                found[identity] = (position, version, record)
        return found

    def iter_identities(self):
        """Every identity in position order, read in pages."""
        connection, last = self.connection(), -1
        while True:
            rows = connection.execute("SELECT position, identity FROM entries WHERE position > ? "
                                      "ORDER BY position LIMIT 10000", (last,)).fetchall()
            if not rows:
                return
            for position, identity in rows:
                yield identity
            last = rows[-1][0]

    def iter_records(self, page=512):
        """`(identity, (position, item version, stored item record text))` of every entry in position order, read
        `page` rows at a time, for a walk over the whole index without one query per identity."""
        connection, last = self.connection(), -1
        while True:
            rows = connection.execute("SELECT position, identity, item_version, record FROM entries "
                                      "WHERE position > ? ORDER BY position LIMIT ?", (last, page)).fetchall()
            if not rows:
                return
            for position, identity, version, record in rows:
                yield identity, (position, version, record)
            last = rows[-1][0]

    def file_refs(self, digests):
        """digest -> (size, references) for the digests this index's items name."""
        wanted = list(dict.fromkeys(digests))
        found, connection = {}, self.connection()
        for start in range(0, len(wanted), 900):
            part = wanted[start:start + 900]
            for digest, size, refs in connection.execute(
                    f"SELECT digest, size, refs FROM files WHERE digest IN ({','.join('?' * len(part))})", part):
                found[digest] = (size, refs)
        return found

    def positions_of(self, identities):
        """Positions of identities this index holds; identities it does not hold are left out."""
        wanted = list(dict.fromkeys(identities))
        found, connection = {}, self.connection()
        for start in range(0, len(wanted), 900):
            part = wanted[start:start + 900]
            rows = connection.execute(
                f"SELECT identity, position FROM entries WHERE identity IN ({','.join('?' * len(part))})", part)
            found.update(rows)
        return found

    def mask(self, conditions):
        """The positions every typed condition accepts, as one boolean array, or None for no condition."""
        numpy = self.numpy
        chosen = None
        for name, operator, operand in conditions:
            accepted = numpy.zeros(self.size, dtype=bool)
            if operator == "any_of":
                held = self._keyword.get(name)
                if held is not None:
                    codes, offsets, positions, _kind = held
                    for value in operand:
                        code = codes.get(str(value))
                        if code is not None:
                            accepted[positions[offsets[code]:offsets[code + 1]]] = True
            else:
                held = self._range.get(name)
                if held is not None:
                    values, positions, kind = held
                    low, high = operand
                    start = 0 if low is None else int(numpy.searchsorted(values, _range_number(kind, low), "left"))
                    end = (len(values) if high is None
                           else int(numpy.searchsorted(values, _range_number(kind, high), "right")))
                    accepted[positions[start:end]] = True
            chosen = accepted if chosen is None else chosen & accepted
        return chosen

    def lexical(self, match, keep, pool):
        """Up to `pool + 1` best `(position, bm25)` rows that `keep(position)` accepts, best first.

        SQLite keeps only the best `limit` matches while it sorts, so the query asks for a bounded number and asks
        again with a wider bound only when the filter left fewer than `pool + 1` of them.
        """
        connection, limit = self.connection(), pool + 1 if keep is None else 4 * (pool + 1)
        try:
            while True:
                fetched = connection.execute(
                    "SELECT rowid, bm25(fts) FROM fts WHERE fts MATCH ? ORDER BY bm25(fts), rowid LIMIT ?",
                    (match, limit)).fetchall()
                rows = [row for row in fetched if keep is None or keep(row[0])]
                if len(rows) > pool or len(fetched) < limit or limit >= self.size:
                    return rows[:pool + 1]
                limit = min(self.size, limit * 8)
        except sqlite3.Error:
            raise ServiceRuntimeError("search_index_unavailable", "the disk search index did not answer") from None

    def document_frequency(self, terms):
        """How many rows hold each term, from the index's own vocabulary."""
        connection = self.connection()
        try:
            connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.row_vocabulary USING fts5vocab(main, fts, 'row')")
        except sqlite3.OperationalError:
            # A read-only immutable database still allows a temporary virtual table; any other failure is unavailable.
            raise ServiceRuntimeError("search_index_unavailable", "the disk index vocabulary did not open") from None
        held = {}
        for term in set(terms):
            row = connection.execute("SELECT doc FROM temp.row_vocabulary WHERE term = ?", (term,)).fetchone()
            held[term] = int(row[0]) if row else 0
        return held

    def vector_top(self, weights, pool, keep_mask, floor):
        """The best `pool + 1` `(score, position)` pairs by `(-score, position)`, with every score bit-identical to
        the in-memory engine's: float64 products added in increasing dimension order."""
        numpy = self.numpy
        best = []
        for start in range(0, self.size, VECTOR_CHUNK):
            stop = min(self.size, start + VECTOR_CHUNK)
            scores = numpy.zeros(stop - start, dtype=numpy.float64)
            product = numpy.empty(stop - start, dtype=numpy.float64)
            for dimension, weight in weights:
                numpy.multiply(self.columns[dimension, start:stop], weight, out=product, dtype=numpy.float64)
                numpy.add(scores, product, out=scores)
            accepted = scores > floor
            if keep_mask is not None:
                accepted &= keep_mask[start:stop]
            candidates = numpy.flatnonzero(accepted)
            if candidates.size > pool + 1:
                values = scores[candidates]
                # Keep every candidate tied with the (pool + 1)th best, so ties resolve by position as they do in
                # the in-memory engine.
                threshold = numpy.partition(values, values.size - (pool + 1))[values.size - (pool + 1)]
                candidates = candidates[values >= threshold]
            best.extend((float(scores[offset]), start + int(offset)) for offset in candidates)
            if len(best) > 4 * (pool + 1):
                best = heapq.nsmallest(pool + 1, best, key=lambda row: (-row[0], row[1]))
        return heapq.nsmallest(pool + 1, best, key=lambda row: (-row[0], row[1]))

    def stats(self):
        return {"record_type": "catalogue_view_index/v1", "engine": ENGINE_ID, "entries": self.size,
                "vector_bytes": VECTOR_DIMENSIONS * 4 * self.size, "stored_on_disk": True,
                "filterable_attributes": sorted(set(self._keyword) | set(self._range)),
                "files_bytes": sum(path.stat().st_size for path in self.folder.iterdir() if path.is_file())}


def _match_expression(query):
    terms = _TOKEN.findall(query.lower())[:LEXICAL_TERMS]
    return terms, " OR ".join(f'"{term}"' for term in terms)


class DiskSearchIndex:
    """The search index edge over one disk index, with an optional overlay of a later release.

    `base` is a `DiskIndex`. `removed` holds the base positions the served release no longer lists as they are
    (removed or changed items). `delta` is a `DiskIndex` of the items added or changed since the base, or None.
    """

    engine = ENGINE_ID

    def __init__(self, base, schema=EMPTY_SCHEMA, policy=None, *, removed=frozenset(), delta=None):
        from ..retrieval_backends import RetrievalRankingPolicy
        self.policy = policy if policy is not None else RetrievalRankingPolicy()
        self.schema = schema
        self.base, self.delta = base, delta
        numpy = base.numpy
        self.removed_mask = None
        if removed:
            self.removed_mask = numpy.ones(base.size, dtype=bool)
            self.removed_mask[numpy.fromiter(sorted(removed), dtype=numpy.int64, count=len(removed))] = False
        self.size = base.size - len(removed) + (delta.size if delta is not None else 0)
        self._base_tokens = base.total_tokens

    @property
    def identities(self):
        """A sized view for callers that only count; the identities themselves stay on disk."""
        return _SizedIdentities(self.size)

    def stats(self):
        value = self.base.stats()
        value.update({"entries": self.size, "overlay": self.delta is not None or self.removed_mask is not None,
                      "delta_entries": self.delta.size if self.delta is not None else 0})
        return value

    def eligible(self, conditions):
        if not conditions:
            return None
        return (self.base.mask(conditions), self.delta.mask(conditions) if self.delta is not None else None)

    def rank(self, query, *, mode, pool, eligible=None):
        from .catalogue_search import HYBRID_MODE
        lexical, exhausted = self._lexical(query, pool, eligible)
        pools = {"lexical": lexical}
        if mode == HYBRID_MODE:
            pools["vector"], vector_exhausted = self._vector(query, pool, eligible)
            exhausted = exhausted and vector_exhausted
        return pools, exhausted

    def _keep(self, part_mask, removed_mask):
        if part_mask is None and removed_mask is None:
            return None
        if part_mask is None:
            return lambda position: bool(removed_mask[position])
        if removed_mask is None:
            return lambda position: bool(part_mask[position])
        return lambda position: bool(part_mask[position] and removed_mask[position])

    def _lexical(self, query, pool, eligible):
        terms, match = _match_expression(query)
        if not terms or not self.size:
            return [], True
        base_mask, delta_mask = eligible if eligible is not None else (None, None)
        filtered = eligible is not None
        base_rows = self.base.lexical(match, self._keep(base_mask, self.removed_mask), pool) if self.base.size else []
        ranked = [(score, identity) for (_position, score), identity
                  in zip(base_rows, self.base.identity_at([position for position, _score in base_rows]))]
        if self.delta is not None and self.delta.size:
            ranked.extend(self._delta_lexical(terms, match, pool, delta_mask))
            ranked.sort()
        kept = [(identity, -score) for score, identity in ranked[:pool + 1]]
        if not filtered:
            # The in-memory engine asks for `pool` rows and calls the pool exhausted when fewer came back.
            return kept[:pool], len(kept) < pool
        return kept[:pool], len(kept) <= pool

    def _delta_lexical(self, terms, match, pool, delta_mask):
        """Delta rows scored by FTS5's bm25 formula with the base index's statistics, so they rank with base rows."""
        rows = self.delta.lexical(match, self._keep(delta_mask, None), self.delta.size)
        if not rows:
            return []
        positions = [position for position, _score in rows]
        frequencies, lengths = _term_frequencies(self.delta, positions, set(terms))
        base_rows = max(1, self.base.size)
        average = self._base_tokens / base_rows
        hits = self.base.document_frequency(terms)
        weights = []
        for term in terms:
            idf = math.log((base_rows - hits[term] + 0.5) / (hits[term] + 0.5))
            weights.append(idf if idf > 0.0 else 1e-6)
        scored = []
        for position, identity in zip(positions, self.delta.identity_at(positions)):
            score, length = 0.0, float(lengths[position])
            for term, idf in zip(terms, weights):
                frequency = float(frequencies.get((position, term), 0))
                score += idf * ((frequency * (BM25_K1 + 1.0))
                                / (frequency + BM25_K1 * (1 - BM25_B + BM25_B * length / average)))
            scored.append((-1.0 * score, identity))
        return scored

    def _vector(self, query, pool, eligible):
        weights = [(dimension, weight) for dimension, weight in enumerate(hash_vector(query)) if weight]
        if not weights or not self.size:
            return [], True
        floor = self.policy.hash_similarity_floor
        base_mask, delta_mask = eligible if eligible is not None else (None, None)
        keep = base_mask
        if self.removed_mask is not None:
            keep = self.removed_mask if keep is None else keep & self.removed_mask
        best = self.base.vector_top(weights, pool, keep, floor) if self.base.size else []
        rows = [(score, identity) for (score, _position), identity
                in zip(best, self.base.identity_at([position for _score, position in best]))]
        if self.delta is not None and self.delta.size:
            delta_best = self.delta.vector_top(weights, pool, delta_mask, floor)
            rows.extend((score, identity) for (score, _position), identity
                        in zip(delta_best, self.delta.identity_at([position for _score, position in delta_best])))
        rows.sort(key=lambda row: (-row[0], row[1]))
        rows = rows[:pool + 1]
        return [(identity, score) for score, identity in rows[:pool]], len(rows) <= pool


class _SizedIdentities:
    """Answers `len()` without holding identities."""

    def __init__(self, size):
        self._size = size

    def __len__(self):
        return self._size


def _term_frequencies(index, positions, terms):
    """Exact token counts of the query terms in some rows of a small index, and those rows' lengths, read from
    FTS5's own instance vocabulary so the tokenizer is FTS5's."""
    connection = index.connection()
    connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.instance_vocabulary "
                       "USING fts5vocab(main, fts, 'instance')")
    wanted = set(positions)
    frequencies, lengths = {}, {position: 0 for position in positions}
    for term in terms:
        for doc, count in connection.execute(
                "SELECT doc, count(*) FROM temp.instance_vocabulary WHERE term = ? GROUP BY doc", (term,)):
            if doc in wanted:
                frequencies[(doc, term)] = count
    # Row lengths: every instance of the wanted rows. The delta is small by construction (OVERLAY_REBUILD_FRACTION).
    for doc, count in connection.execute("SELECT doc, count(*) FROM temp.instance_vocabulary GROUP BY doc"):
        if doc in wanted:
            lengths[doc] = count
    return frequencies, lengths


def bm25_with_statistics(index, position, terms, *, rows, total_tokens, hits):
    """FTS5's bm25 of one row of `index` for the phrases `terms`, computed with the given corpus statistics.

    With an index's own statistics this equals FTS5's `bm25()` exactly; the checks use that as the known-good
    control for the delta scores.
    """
    frequencies, lengths = _term_frequencies(index, [position], set(terms))
    average = total_tokens / max(1, rows)
    score, length = 0.0, float(lengths[position])
    for term in terms:
        idf = math.log((rows - hits[term] + 0.5) / (hits[term] + 0.5))
        idf = idf if idf > 0.0 else 1e-6
        frequency = float(frequencies.get((position, term), 0))
        score += idf * ((frequency * (BM25_K1 + 1.0)) / (frequency + BM25_K1 * (1 - BM25_B + BM25_B * length / average)))
    return -1.0 * score
