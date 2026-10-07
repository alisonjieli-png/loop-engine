"""Engine (d) of the catalogue search index slot: one release's index in Cloudflare D1, answered by a Worker.

The catalogue search index slot (`catalogue_search_index`, edge `catalogue_search_index/v1`) keeps the search
request, the provisioning authorization, the fusion and the result fixed and lets the engine choose where one
release's index lives. This engine keeps it at Cloudflare's edge:

```text
d1_edge_index (kind edge_database_index; planned: measured on a workers.dev prototype, never selected by a host)
├── D1 database, one per published release index
│   ├── entries            position, identity, tier, effects and the public fields a search hit shows
│   ├── entries_text       a contentless FTS5 table over the service's own index text, rowid = position
│   ├── keyword_postings   filterable keyword, choice and list values, hashed into buckets of positions
│   ├── range_postings     filterable number and date values with their positions, sorted, in chunks
│   └── catalogue_index    the build record, written last
├── KV namespace           the 512 float32 hash-vector columns, one value per dimension, column-major
└── Worker                 edge/catalogue_search_worker.js
    ├── POST /v1/rank                catalogue_search_index_query/v1 -> catalogue_search_index_pools/v1
    ├── POST /api/v1/retrieval       service_retrieval_request/v2 -> service_retrieval_result/v1 under one
    │                                fixed account profile (below), for one published release
    ├── GET  /v1/index               the build record
    └── POST /v1/admin/vectors       writes the vector columns into KV; signed with an admin key
```

Exactness. The index text, positions, tiers and vectors come from the same functions the in-memory engine uses
(`entry_text`, the schema's `search_text`, `_TokenBuckets`), so for the same entries the Worker returns the same
pools: the same `MATCH` expression ordered by `bm25(), rowid` over a contentless single-column FTS5 table (bm25
reads only token counts, so it scores exactly as the in-memory table with an UNINDEXED column), and the hash-vector
products of the query's own dimensions added as doubles in increasing dimension order. The conformance kit
(`catalogue_d1_index_checks`) runs the Worker's own code under Node's SQLite against the in-memory engine.

What the measurement on October 5, 2026 found is in docs/architecture/CLOUDFLARE-HOSTING-2026-10-05.md: D1 bills
the rows a query scans, and an OR query's bm25 ranking scans every matching document, so the cost of this engine
grows with the library, not with the answer.

The account profile. A Worker cannot see accounts, grants or denials, which live in the service store, so its
retrieval route answers as the service answers one enabled account with default library settings: every item of
the release, community items included, `body_allowed` false (metadata only), the same effect rules, refusals and
result fields. A production edge route would either call the service to authorize candidates or receive a
replicated, versioned grant record; neither is built here. Requests are signed with Ed25519 keys whose public
halves the Worker holds, so no shared secret is ever copied into a host file, a prompt or a transcript.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from array import array
from dataclasses import dataclass, field

from .catalogue_schema import DATE, EMPTY_SCHEMA, KEYWORD_LIST, NUMBER, PUBLIC
from .records import ServiceRuntimeError

ENGINE_ID, ENGINE_KIND, ENGINE_VERSION = "d1_edge_index", "edge_database_index", "0.1.0"
INDEX_FORMAT = "catalogue_d1_index/v1"
BUILD_RECORD_TYPE = "catalogue_d1_index_build/v1"
PROFILE_RECORD_TYPE = "catalogue_edge_search_profile/v1"
#: The edge's one interaction row, core.interaction.catalogue.search_index_rank, names these two contracts.
QUERY_RECORD_TYPE, POOLS_RECORD_TYPE = "catalogue_search_index_query/v1", "catalogue_search_index_pools/v1"
VIEW_INDEX_RECORD_TYPE = "catalogue_view_index/v1"
#: Cloudflare's browser integrity check answers a library's default user agent with error 1010 (observed on
#: workers.dev, October 5, 2026), so every request names this client.
USER_AGENT = f"baltor-edge-client/{ENGINE_VERSION}"
SIGNATURE_SCHEME = "Baltor-Signature"
SIGNATURE_CONTEXT = "baltor-edge-search/v1"
#: D1's documented limit is 100,000 bytes for one SQL statement (limits page, April 21, 2026); an export keeps
#: every statement under this budget so the import never meets the limit.
MAXIMUM_STATEMENT_BYTES = 100_000
STATEMENT_BUDGET = 90_000
#: A keyword posting bucket or a range chunk is kept near this many bytes of JSON.
POSTING_BUCKET_BYTES = 60_000
VECTOR_DIMENSIONS = 512
#: How long a signed request stays acceptable, either side of the Worker's clock.
SIGNATURE_WINDOW_SECONDS = 300
_HEX = re.compile(r"[0-9a-f]{64}")
_KEY_ID = re.compile(r"[0-9a-f]{16}")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _sql_text(value):
    return "'" + value.replace("'", "''") + "'"


# --------------------------------------------------------------------------------------------------- export ----

@dataclass(frozen=True)
class D1IndexExport:
    """One release's index in the D1 format: SQL statements, vector columns and the build record."""

    build: dict
    statements: tuple
    columns: tuple = field(repr=False)

    @property
    def build_id(self):
        return self.build["build_id"]

    def sql(self):
        """The import file: one statement per line, the build record last."""
        return "\n".join(self.statements) + "\n"

    def column_key(self, dimension):
        return vector_key(self.build_id, dimension)


def column_digests(columns):
    """The SHA-256 of each vector column's bytes, in dimension order."""
    return [_sha256(column) for column in columns]


def vectors_digest(digests):
    """One digest over every column digest: the Worker checks an uploaded column against it before writing."""
    if len(digests) != VECTOR_DIMENSIONS or not all(_HEX.fullmatch(digest or "") for digest in digests):
        _refuse("search_index_invalid", "every dimension has one column digest")
    return _sha256("\n".join(digests).encode("ascii"))


def vector_key(build_id, dimension):
    if not _HEX.fullmatch(build_id or "") or type(dimension) is not int or not 0 <= dimension < VECTOR_DIMENSIONS:
        _refuse("search_index_invalid", "a vector column is named by its build and one dimension")
    return f"{build_id}/{dimension:03d}"


def hit_fields(item, package, values, schema, tier):
    """The fields of one search hit that do not depend on the request, as the service builds them for a store view.

    `score`, `modes`, `body_allowed` and `effects_to_declare` are added per request by the Worker.
    """
    from dataclasses import asdict
    from ..provisioning_server import TIER_LABELS, ProvisioningItemBinding
    return {"reference": asdict(ProvisioningItemBinding.from_item(item)), "purpose": item.purpose,
            "kind": item.kind, "size_bytes": item.size_bytes, "license": item.license_name,
            "declared_effects": list(item.declared_effects), "harness_styles": list(item.styles),
            "qualification_basis": "host_attested", "library_tier": tier, "library_tier_label": TIER_LABELS[tier],
            "attributes": schema.shown_values(values),
            "package": {"body_form": package.body_form, "package_digest": package.package_digest,
                        "files": [{"path": entry.path, "media_type": entry.media_type, "role": entry.role,
                                   "size_bytes": entry.size_bytes, "digest": entry.digest}
                                  for entry in package.files]}}


def entries_from_bundle(bundle):
    """Index entries and hit fields of a validated bundle, built exactly as `store_view` builds them.

    Returns `(entries, hits)` in identity order, the order a release lists its items and a view numbers them.
    """
    from ..provisioning_server import RUNNABLE_EFFECT
    from .catalogue_search import IndexEntry, entry_text
    entries, hits = [], []
    for bundle_item in bundle.items:
        item, values = bundle_item.item, bundle_item.attributes
        entries.append(IndexEntry(item.identity, entry_text(item, bundle.schema.search_text(values)), values,
                                  bundle_item.tier, RUNNABLE_EFFECT in item.declared_effects))
        hits.append(hit_fields(item, bundle_item.package, values, bundle.schema, bundle_item.tier))
    return tuple(entries), tuple(hits)


def _vector_columns(entries):
    """The in-memory engine's float32 columns for these entries, as little-endian bytes per dimension."""
    from .catalogue_search import _TokenBuckets
    zero = bytes(4 * len(entries))
    columns = []
    for _dimension in range(VECTOR_DIMENSIONS):
        column = array("f")
        column.frombytes(zero)
        columns.append(column)
    buckets = _TokenBuckets()
    for position, entry in enumerate(entries):
        for dimension, weight in buckets.vector(entry.text):
            if weight:
                columns[dimension][position] = weight
    import sys
    if sys.byteorder != "little":
        for column in columns:
            column.byteswap()
    return tuple(column.tobytes() for column in columns)


def _rows_statements(prefix, rows):
    """Multi-row INSERT statements under the statement budget in UTF-8 bytes; an oversized row is refused, never split."""
    statement, size = [], len(prefix.encode("utf-8"))
    for row in rows:
        width = len(row.encode("utf-8"))
        if len(prefix.encode("utf-8")) + width + 2 > STATEMENT_BUDGET:
            _refuse("search_index_invalid", "one row exceeds the D1 statement budget")
        if statement and size + width + 2 > STATEMENT_BUDGET:
            yield prefix + ",".join(statement) + ";"
            statement, size = [], len(prefix.encode("utf-8"))
        statement.append(row)
        size += width + 1
    if statement:
        yield prefix + ",".join(statement) + ";"


def _bucket_of(value, buckets):
    import zlib
    return zlib.crc32(value.encode("utf-8")) % buckets


def _keyword_postings(entries, attribute):
    """Rows of (bucket, part, {value: positions}) for one attribute, each row's JSON near the bucket size.

    A value names one bucket by the CRC-32 of its UTF-8 bytes, so a filter reads only that bucket's rows; a value
    with more positions than fit one row continues in the next part of the same bucket.
    """
    table = {}
    for position, entry in enumerate(entries):
        if attribute.name in entry.values:
            value = entry.values[attribute.name]
            for element in (value if attribute.type == KEYWORD_LIST else (value,)):
                table.setdefault(element, []).append(position)
    size = sum(len(canonical_json(key)) + len(canonical_json(value)) for key, value in table.items())
    buckets = 1
    while size / buckets > POSTING_BUCKET_BYTES:
        buckets *= 2
    held = [{} for _bucket in range(buckets)]
    for value, positions in table.items():
        held[_bucket_of(value, buckets)][value] = positions
    rows = []
    for bucket, values in enumerate(held):
        part, current, used = 0, {}, 2
        for value in sorted(values):
            positions = values[value]
            while positions:
                room = max(1, (POSTING_BUCKET_BYTES - used - len(canonical_json(value)) - 4) // 7)
                taken, positions = positions[:room], positions[room:]
                encoded = len(canonical_json(value)) + len(canonical_json(taken)) + 2
                if current and used + encoded > POSTING_BUCKET_BYTES:
                    rows.append((bucket, part, current))
                    part, current, used = part + 1, {}, 2
                current.setdefault(value, []).extend(taken)
                used += encoded
        if current:
            rows.append((bucket, part, current))
    return buckets, rows


def _range_postings(entries, attribute):
    pairs = sorted((entry.values[attribute.name], position) for position, entry in enumerate(entries)
                   if attribute.name in entry.values)
    chunks, chunk, size = [], [], 0
    for pair in pairs:
        encoded = len(canonical_json(list(pair))) + 1
        if chunk and size + encoded > POSTING_BUCKET_BYTES:
            chunks.append(chunk)
            chunk, size = [], 0
        chunk.append(list(pair))
        size += encoded
    if chunk:
        chunks.append(chunk)
    return chunks


SCHEMA_STATEMENTS = (
    "CREATE TABLE catalogue_index (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;",
    "CREATE TABLE entries (position INTEGER PRIMARY KEY, identity TEXT NOT NULL, tier TEXT NOT NULL, "
    "effects TEXT NOT NULL, hit TEXT NOT NULL);",
    "CREATE VIRTUAL TABLE entries_text USING fts5(body, content='');",
    "CREATE TABLE keyword_postings (attribute TEXT NOT NULL, bucket INTEGER NOT NULL, part INTEGER NOT NULL, "
    "data TEXT NOT NULL, PRIMARY KEY (attribute, bucket, part)) WITHOUT ROWID;",
    "CREATE TABLE range_postings (attribute TEXT NOT NULL, chunk INTEGER NOT NULL, low TEXT NOT NULL, "
    "data TEXT NOT NULL, PRIMARY KEY (attribute, chunk)) WITHOUT ROWID;",
)


def export_index(entries, schema=EMPTY_SCHEMA, *, release_id, content_digest, hits=None, policy=None,
                 profile=None, built_at=None):
    """Build one release's D1 index from the entries the service would index, in their served order.

    `hits` holds the public fields of each entry's search hit (`hit_fields`), or None for an index that only
    ranks. `profile` is the account profile record the Worker's retrieval route answers under
    (`edge_search_profile`), or None for an index without that route.
    """
    from .catalogue_search import CATALOGUE_RANKING_POLICY
    policy = policy if policy is not None else CATALOGUE_RANKING_POLICY
    entries = tuple(entries)
    identities = [entry.identity for entry in entries]
    if not entries or len(set(identities)) != len(identities):
        _refuse("search_index_invalid", "an index holds one or more entries, each identity once")
    if hits is not None and (len(hits) != len(entries) or any(
            hit["reference"]["identity"] != entry.identity for hit, entry in zip(hits, entries))):
        _refuse("search_index_invalid", "hit fields follow the entries one for one")
    filterable = [attribute for attribute in schema.attributes if attribute.filterable]
    if any(attribute.visibility != PUBLIC for attribute in schema.attributes
           if attribute.searchable or attribute.filterable):
        _refuse("search_index_invalid", "only public attributes are searched or filtered")
    columns = _vector_columns(entries)
    entry_rows, text_rows, digest = [], [], hashlib.sha256()
    for position, entry in enumerate(entries):
        hit = canonical_json(hits[position]) if hits is not None else "{}"
        effects = canonical_json(sorted(hits[position]["declared_effects"])) if hits is not None else "[]"
        entry_rows.append(f"({position},{_sql_text(entry.identity)},{_sql_text(entry.tier)},{_sql_text(effects)},"
                          f"{_sql_text(hit)})")
        text_rows.append(f"({position},{_sql_text(entry.text)})")
        digest.update(canonical_json([entry.identity, entry.tier, entry.runnable, entry.text, entry.values,
                                      hits[position] if hits is not None else None]).encode("utf-8") + b"\n")
    keyword_rows, range_rows, filters = [], [], {}
    for attribute in filterable:
        if attribute.type in (NUMBER, DATE):
            chunks = _range_postings(entries, attribute)
            filters[attribute.name] = {"type": attribute.type, "kind": "range", "chunks": len(chunks)}
            for number, chunk in enumerate(chunks):
                low = canonical_json(chunk[0][0])
                range_rows.append(f"({_sql_text(attribute.name)},{number},{_sql_text(low)},"
                                  f"{_sql_text(canonical_json(chunk))})")
        else:
            buckets, rows = _keyword_postings(entries, attribute)
            filters[attribute.name] = {"type": attribute.type, "kind": "keyword", "buckets": buckets}
            for bucket, part, table in rows:
                keyword_rows.append(f"({_sql_text(attribute.name)},{bucket},{part},"
                                    f"{_sql_text(canonical_json(table))})")
    from .catalogue_search import LEXICAL_TERMS
    body = {"format": INDEX_FORMAT, "release_id": release_id, "content_digest": content_digest,
            "entries": len(entries), "entries_digest": digest.hexdigest(),
            "vectors_digest": vectors_digest(column_digests(columns)),
            "schema": schema.to_dict(), "schema_digest": schema.digest, "filters": filters,
            "policy": {"reciprocal_rank_offset": policy.reciprocal_rank_offset,
                       "candidate_pool_multiplier": policy.candidate_pool_multiplier,
                       "hash_similarity_floor": policy.hash_similarity_floor},
            "lexical_terms": LEXICAL_TERMS, "vector_dimensions": VECTOR_DIMENSIONS,
            "vectors": {"store": "kv", "encoding": "float32_little_endian_column", "key": "<build_id>/<dimension>"},
            "hits": hits is not None, "profile": profile}
    build_id = _sha256(canonical_json(body).encode("utf-8"))
    build = {"record_type": BUILD_RECORD_TYPE, "build_id": build_id, **body,
             "built_at": int(time.time()) if built_at is None else built_at}
    statements = list(SCHEMA_STATEMENTS)
    statements += _rows_statements("INSERT INTO entries (position, identity, tier, effects, hit) VALUES ", entry_rows)
    statements += _rows_statements("INSERT INTO entries_text (rowid, body) VALUES ", text_rows)
    statements += _rows_statements("INSERT INTO keyword_postings (attribute, bucket, part, data) VALUES ",
                                   keyword_rows)
    statements += _rows_statements("INSERT INTO range_postings (attribute, chunk, low, data) VALUES ", range_rows)
    statements.append(f"INSERT INTO catalogue_index (key, value) VALUES ('build',{_sql_text(canonical_json(build))});")
    if any(len(statement.encode("utf-8")) > MAXIMUM_STATEMENT_BYTES for statement in statements):
        _refuse("search_index_invalid", "a statement exceeds the D1 statement limit")
    return D1IndexExport(build, tuple(statements), columns)


VECTOR_UPLOAD_MAGIC = b"BALTORV1"


def vector_upload_payload(export, dimensions):
    """One admin upload of vector columns: a magic word, a JSON header and the raw columns in header order.

    The header carries every column digest, so the Worker checks each uploaded column against the build's
    `vectors_digest` before it writes anything, and a column of another build is refused.
    """
    dimensions = list(dimensions)
    if not dimensions or len(set(dimensions)) != len(dimensions):
        _refuse("search_index_invalid", "an upload names distinct dimensions")
    header = canonical_json({"build_id": export.build_id, "dimensions": dimensions,
                             "column_bytes": len(export.columns[0]),
                             "column_digests": column_digests(export.columns)}).encode("utf-8")
    return (VECTOR_UPLOAD_MAGIC + len(header).to_bytes(4, "little") + header
            + b"".join(export.columns[dimension] for dimension in dimensions))


def load_export_into_sqlite(export, connection):
    """Run an export's statements on a local SQLite connection: the local stand-in for D1 in the checks."""
    for statement in export.statements:
        connection.execute(statement)
    connection.commit()


# -------------------------------------------------------------------------------------------- the profile ----

def edge_search_profile(*, release_id, maximum_search_results=50, community_default=None):
    """The account profile and the contract constants the Worker's retrieval route answers with.

    Every value is read from the service's own code, so the Worker holds no vocabulary of its own: the request
    and result record types, the fields a request may carry, the effect vocabulary and the step defaults, the
    tier labels and order, the limitation lines, the line for a search that finds nothing, and the wording of
    each refusal the route can give, with its status.
    """
    from ..facets import EFFECTS
    from ..provisioning_server import (COMMUNITY_EXCLUDED, COMMUNITY_INCLUDED, COMMUNITY_ITEM_CHOICES, COMMUNITY_TIER,
                                       COMMUNITY_WITHOUT_RUNNABLE, LIBRARY_TIERS, RUNNABLE_EFFECT, TIER_LABELS,
                                       TIER_ORDER, VERIFIED_TIER)
    from .catalogue_schema import MAXIMUM_FILTERS, MAXIMUM_KEYWORD_CHARACTERS, MAXIMUM_LIST_VALUES, MAXIMUM_NUMBER
    from .catalogue_tiers import DEFAULT_LIBRARY_SETTINGS
    from .feedback import ASK_FOR_MATERIAL_LINE
    from .http import (DEFAULT_STEP_EFFECTS, ERROR_VERSION, RESULT_VERSION, RETRIEVAL_REQUEST_VERSION, STEP_EFFECTS,
                       STEP_EFFECTS_HEADER_NAME)
    from .refusals import guidance
    codes = {"invalid_json": 400, "nesting_limit_exceeded": 400, "search_index_changed": 409,
             "object_required": 400, "unknown_request_field": 400, "unsupported_version": 400,
             "invalid_query": 400, "unsupported_retrieval_mode": 400, "invalid_search_limit": 400,
             "search_filter_invalid": 400, "search_filter_not_allowed": 400, "attribute_value_invalid": 400,
             "invalid_request": 400, "library_tiers_invalid": 400, "invalid_step_effects": 400,
             "unauthorized": 401, "route_unavailable": 404, "method_not_allowed": 405,
             "request_limit_exceeded": 413, "search_index_unavailable": 503}
    refusals = {code: {"status": status, "message": guidance(code, status)[0], "next_action": guidance(code, status)[1]}
                for code, status in codes.items()}
    return {"record_type": PROFILE_RECORD_TYPE, "release_id": release_id,
            "account": "one_enabled_account_with_default_library_settings",
            "request_record_type": RETRIEVAL_REQUEST_VERSION, "result_record_type": "service_retrieval_result/v1",
            "envelope_record_type": RESULT_VERSION, "error_record_type": ERROR_VERSION,
            "request_fields": ["query", "mode", "top_n", "filters", "authority_effects", "library_tiers"],
            "maximum_query_bytes": 4096, "maximum_search_results": maximum_search_results,
            "maximum_request_bytes": 65_536, "maximum_json_depth": 64,
            "modes": ["lexical", "hybrid"], "effects": list(EFFECTS), "step_effects": list(STEP_EFFECTS),
            "default_step_effects": list(DEFAULT_STEP_EFFECTS), "step_effects_header": STEP_EFFECTS_HEADER_NAME,
            "runnable_effect": RUNNABLE_EFFECT, "library_tiers": list(LIBRARY_TIERS),
            "verified_tier": VERIFIED_TIER, "community_tier": COMMUNITY_TIER, "community_included": COMMUNITY_INCLUDED,
            "tier_labels": dict(TIER_LABELS), "tier_order": dict(TIER_ORDER),
            "community_choices": list(COMMUNITY_ITEM_CHOICES),
            "community_default": community_default or DEFAULT_LIBRARY_SETTINGS.community_items,
            "community_excluded": COMMUNITY_EXCLUDED, "community_without_runnable": COMMUNITY_WITHOUT_RUNNABLE,
            "filters": {"maximum_filters": MAXIMUM_FILTERS, "maximum_list_values": MAXIMUM_LIST_VALUES,
                        "maximum_keyword_characters": MAXIMUM_KEYWORD_CHARACTERS, "maximum_number": MAXIMUM_NUMBER},
            "body_allowed": False,
            "backend": {"request_record_type": RETRIEVAL_REQUEST_VERSION,
                        "authority_effects": "metadata_eligibility_only", "modes": ["lexical", "hybrid"],
                        "lexical_backend": "cloudflare_d1_sqlite_fts5",
                        "vector_backend": "deterministic_character_hash",
                        "semantic_embedding_model_installed": False,
                        "scope": "authorized_catalogue_metadata", "returns_bodies": False,
                        "index": "one_d1_index_for_one_published_release",
                        "filters": "declared_filterable_public_attributes"},
            "limitations": ["Hash vectors measure character similarity, not learned semantic understanding.",
                            "Distribution references do not grant local code execution or independent Code admission.",
                            "Answered at the edge as one enabled account with default library settings; account "
                            "grants, denials and library settings are not applied."],
            "ask_for_material": ASK_FOR_MATERIAL_LINE, "refusals": refusals}


# ---------------------------------------------------------------------------------------------- signing ----

def signed_message(method, path, timestamp, body):
    """The bytes a request signature covers: the method, the path with its query, the time and the body digest."""
    return "\n".join((SIGNATURE_CONTEXT, method.upper(), path, str(int(timestamp)), _sha256(body or b""))).encode()


def key_id(public_key_raw):
    return _sha256(public_key_raw)[:16]


@dataclass(frozen=True)
class RequestSigner:
    """Signs requests with one Ed25519 private key, read from a file the operator keeps outside the repository."""

    private_key: object = field(repr=False)

    @classmethod
    def from_pem_file(cls, path):
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        with open(path, "rb") as handle:
            return cls(load_pem_private_key(handle.read(), password=None))

    @property
    def public_key_raw(self):
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        return self.private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    def header(self, method, path, body, *, now=None):
        timestamp = int(time.time() if now is None else now)
        signature = self.private_key.sign(signed_message(method, path, timestamp, body))
        encoded = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        return f"{SIGNATURE_SCHEME} v1 {key_id(self.public_key_raw)} {timestamp} {encoded}"


def public_key_entry(public_key_raw, scopes):
    """One entry of the Worker's allowed keys: its id, the raw public key in base64 and its scopes."""
    if set(scopes) - {"search", "admin"} or not scopes:
        _refuse("invalid_request", "a key holds the search scope, the admin scope or both")
    return {"id": key_id(public_key_raw), "public_key": base64.b64encode(public_key_raw).decode(),
            "scopes": sorted(scopes)}


# ---------------------------------------------------------------------------------------------- transport ----

class WorkerTransport:
    """Signed JSON requests to one Worker; https only, except a loopback host the checks start themselves."""

    def __init__(self, base_url, signer, *, timeout=10.0, allow_loopback_http=False, opener=None):
        parsed = urllib.parse.urlsplit(base_url or "")
        loopback = parsed.hostname in ("127.0.0.1", "::1") and allow_loopback_http and parsed.scheme == "http"
        if not (parsed.scheme == "https" or loopback) or not parsed.hostname or parsed.path not in ("", "/") \
                or parsed.query or parsed.fragment or parsed.username or parsed.password:
            _refuse("search_engine_unavailable", "the edge index is one https origin")
        if not isinstance(signer, RequestSigner):
            _refuse("search_engine_unavailable", "the edge index needs a request signer")
        if type(timeout) not in (int, float) or not 0 < timeout <= 30:
            _refuse("search_engine_unavailable", "the edge index deadline is bounded")
        self.origin, self.signer, self.timeout = f"{parsed.scheme}://{parsed.netloc}", signer, timeout
        self._opener = opener or urllib.request.build_opener(_NoRedirect)

    def request(self, method, path, payload=None, *, maximum_bytes=8_000_000):
        body = b"" if payload is None else canonical_json(payload).encode("utf-8")
        headers = {"Authorization": self.signer.header(method, path, body), "Accept": "application/json",
                   "User-Agent": USER_AGENT}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.origin + path, data=body if payload is not None else None,
                                         method=method, headers=headers)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read(maximum_bytes + 1)
                status, timing = response.status, response.headers.get("Server-Timing", "")
        except urllib.error.HTTPError as error:
            raw, status, timing = error.read(65_536), error.code, ""
        except (urllib.error.URLError, OSError, TimeoutError):
            _refuse("search_index_unavailable", "the edge index did not answer")
        if len(raw) > maximum_bytes:
            _refuse("search_index_unavailable", "the edge index answer is larger than allowed")
        try:
            decoded = json.loads(raw)
        except ValueError:
            _refuse("search_index_unavailable", "the edge index answer is not JSON")
        return status, decoded, timing


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: ANN002 - the standard handler's signature
        return None


# ------------------------------------------------------------------------------------------ the engine ----

def availability():
    """The engine stays planned; dependency presence never authorizes host selection."""
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return {"available": False, "reason": "cryptography_not_installed"}
    return {"available": False, "reason": "planned"}


class _SizedIdentities:
    """The edge asks only how many entries an index holds; the identities themselves stay in D1."""

    def __init__(self, size):
        self._size = size

    def __len__(self):
        return self._size


@dataclass(frozen=True)
class _RemoteConditions:
    """What `eligible` returns: the typed conditions, evaluated by the Worker inside the same ranking request."""

    conditions: tuple


def _read_build(value):
    if not isinstance(value, dict) or value.get("record_type") != BUILD_RECORD_TYPE \
            or value.get("format") != INDEX_FORMAT or not _HEX.fullmatch(str(value.get("build_id", ""))) \
            or type(value.get("entries")) is not int or value["entries"] < 1:
        _refuse("search_engine_unavailable", f"the edge index does not hold a {INDEX_FORMAT} build")
    return value


class D1EdgeSearchIndex:
    """The catalogue_search_index/v1 edge over one Worker: `eligible`, `rank`, `stats`, `policy` and `schema`.

    The build the Worker serves is read once and pinned: an answer for another build is refused with
    `search_index_changed`, and a Worker whose ranking policy differs from this service's is refused before the
    first request, never used in its place.
    """

    def __init__(self, transport, schema=EMPTY_SCHEMA, policy=None, *, expected_build_id=None):
        from .catalogue_search import CATALOGUE_RANKING_POLICY
        self.transport, self.schema = transport, schema
        self.policy = policy if policy is not None else CATALOGUE_RANKING_POLICY
        status, answer, _timing = transport.request("GET", "/v1/index")
        if status != 200:
            _refuse("search_engine_unavailable", "the edge index did not describe its build")
        self.build = _read_build(answer)
        if expected_build_id is not None and self.build["build_id"] != expected_build_id:
            _refuse("search_index_changed", "the edge index serves another build than the one selected")
        stated = self.build["policy"]
        if (stated.get("reciprocal_rank_offset") != self.policy.reciprocal_rank_offset
                or stated.get("hash_similarity_floor") != self.policy.hash_similarity_floor):
            _refuse("search_engine_unavailable", "the edge index ranks with another policy than this service")
        if self.build["schema_digest"] != schema.digest:
            _refuse("search_engine_unavailable", "the edge index was built with another attribute schema")
        self.size = self.build["entries"]
        self.identities = _SizedIdentities(self.size)

    def stats(self):
        return {"record_type": VIEW_INDEX_RECORD_TYPE, "entries": self.size,
                "vector_bytes": VECTOR_DIMENSIONS * 4 * self.size,
                "filterable_attributes": sorted(self.build["filters"])}

    def eligible(self, conditions):
        if not conditions:
            return None
        checked = []
        for condition in conditions:
            name, operator, operand = condition
            declared = self.build["filters"].get(name)
            if declared is None or operator not in ("any_of", "range") \
                    or (operator == "range") != (declared["kind"] == "range"):
                _refuse("search_filter_not_allowed", "the edge index does not filter on that attribute that way")
            checked.append([name, operator, list(operand)])
        return _RemoteConditions(tuple(map(tuple, checked)))

    def rank(self, query, *, mode, pool, eligible=None):
        from .catalogue_search import HYBRID_MODE, SEARCH_MODES
        if mode not in SEARCH_MODES or type(pool) is not int or pool < 1:
            _refuse("search_index_unavailable", "a ranking request names a mode and a positive pool")
        if eligible is not None and not isinstance(eligible, _RemoteConditions):
            _refuse("search_index_unavailable", "conditions come from this engine's own eligible()")
        request = {"record_type": QUERY_RECORD_TYPE, "build_id": self.build["build_id"], "query": query,
                   "mode": mode, "pool": pool,
                   "conditions": [list(row) for row in eligible.conditions] if eligible is not None else None}
        status, answer, _timing = self.transport.request("POST", "/v1/rank", request)
        if status != 200:
            code = (answer.get("error") or {}).get("code") if isinstance(answer, dict) else None
            _refuse("search_index_changed" if code == "search_index_changed" else "search_index_unavailable",
                    "the edge index refused the ranking request")
        return read_pools(answer, self.build["build_id"], mode=mode, pool=pool, hybrid=mode == HYBRID_MODE)


def read_pools(answer, build_id, *, mode, pool, hybrid):
    """Read a pools record strictly: its build, its pools, bounded rows of identity and finite score."""
    if not isinstance(answer, dict) or set(answer) != {"record_type", "build_id", "mode", "pools", "exhausted"} \
            or answer["record_type"] != POOLS_RECORD_TYPE or answer["mode"] != mode \
            or type(answer["exhausted"]) is not bool:
        _refuse("search_index_unavailable", f"the edge index did not answer with {POOLS_RECORD_TYPE}")
    if answer["build_id"] != build_id:
        _refuse("search_index_changed", "the edge index answered from another build")
    pools = answer["pools"]
    expected = {"lexical", "vector"} if hybrid else {"lexical"}
    if not isinstance(pools, dict) or set(pools) != expected:
        _refuse("search_index_unavailable", "the pools are the lexical pool and, for hybrid search, the vector pool")
    read = {}
    for name in ("lexical", "vector"):
        if name not in pools:
            continue
        rows = pools[name]
        if not isinstance(rows, list) or len(rows) > pool:
            _refuse("search_index_unavailable", "a pool holds at most the rows asked for")
        held, seen = [], set()
        for row in rows:
            if (not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str) or not row[0]
                    or row[0] in seen or type(row[1]) not in (int, float) or not math.isfinite(row[1])):
                _refuse("search_index_unavailable", "a pool row is one identity, once, with a finite score")
            seen.add(row[0])
            held.append((row[0], float(row[1])))
        read[name] = held
    return read, answer["exhausted"]
