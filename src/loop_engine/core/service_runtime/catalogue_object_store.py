"""Catalogue bodies in an S3-compatible object store: the Cloudflare R2 engine of the body store edge.

Kind: engine adapter behind the fixed edge `catalogue_body_store/v1`, the same
edge `VolumeBodyStore` implements in `catalogue_packages.py`. Callers keep
asking the same four questions (capabilities, read, put, sync) and get the
same answers, records and typed refusals; only where the bytes live changes.
The slot's factory table, `service_engine_body_store.py`, is the one place a
host names this engine.

```text
Object store body engine (engine r2_object_storage, kind private_object_storage)
├── object key     sha256/<first two>/<digest>, the key the volume engine uses, in one private bucket
├── read           GET, read at most size_bytes + 1 bytes, then size and SHA-256 checked as on the volume
├── put            one PUT that can only create: If-None-Match: *, Content-MD5, and the payload's
│                  SHA-256 signed as x-amz-content-sha256 (it equals the digest the key names);
│                  412 means the key exists, so the stored bytes are read and must be the same bytes,
│                  otherwise body_digest_conflict; a created object is read back and verified
├── sync           nothing: the store acknowledges a PUT only once the object is durable
├── signing        AWS Signature Version 4 with hmac and hashlib from the standard library;
│                  region "auto" and service "s3", as R2 documents
├── credentials    env: references, resolved at each use; never held in capabilities, descriptors,
│                  refusals or logs
└── transport      http.client with TLS verification on, an explicit timeout, no redirect followed,
                   one reused connection per thread, closed whenever a response was not read to its end
```

Why these choices (October 5, 2026; R2's S3 compatibility page, last updated
July 31, 2026, and its limits page, June 8, 2026):

- R2 implements PutObject's If-None-Match and Content-MD5, so the volume
  engine's write-once rule (a name is created once and never replaced) holds
  in one request: no read before the write, and no window in which another
  writer's object could be replaced. Its PutObject feature list names no
  x-amz-checksum header, so the integrity checks are the signed payload hash,
  Content-MD5 and the read back, all of which R2 and every S3 implementation
  honour.
- Path-style addressing, `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<bucket>/<key>`,
  as R2's own presigned example uses; it also works with MinIO and the
  loopback fake used by the checks.
- R2 allows one write a second to the same key. Keys here are content
  addressed, so two writes to one key only happen when two writers store the
  same bytes, and the second one receives 412 and verifies.
- A read never trusts a length header: it reads at most one byte more than
  the recorded size and then checks size and digest, so an answer of any
  length costs bounded memory.
- No retry inside the engine. The interaction row of the edge names no retry
  owner but the request (`none_one_body_store`), and a write that times out has
  an unknown outcome that the next put resolves through 412 and the read back.

Two operator helpers live here and are not part of the edge: a presigned GET
link for a future delivery edge (a bearer link valid 1 second to 7 days, which
names the access key identifier, as every SigV4 link does, and never the
secret), and a listing of stored keys that the mirror tool uses to resume.
Constructing an engine reads no environment and opens no connection.
"""
from __future__ import annotations

import base64
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import hmac
import http.client
import ipaddress
import re
import ssl
import threading
import time
from urllib.parse import quote, urlsplit
import xml.etree.ElementTree as ElementTree

from .catalogue_packages import (BODY_STORE_CAPABILITIES_VERSION, BODY_STORE_EDGE_VERSION, MAXIMUM_FILE_BYTES,
                                 MAXIMUM_PACKAGE_BYTES, exact_digest, sha256_hex)
from .records import ServiceRuntimeError

ENGINE_ID = "r2_object_storage"
ENGINE_VERSION = "1.0.0"
ENGINE_KIND = "private_object_storage"
OBJECT_KEY_FORM = "sha256/<first two>/<digest>"
SIGNING_ALGORITHM = "AWS4-HMAC-SHA256"
SIGNING_TERMINATOR = "aws4_request"
SERVICE = "s3"
#: R2's region: "an empty value and us-east-1 will alias to the auto region".
DEFAULT_REGION = "auto"
UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"
EMPTY_PAYLOAD_DIGEST = hashlib.sha256(b"").hexdigest()
#: R2 presigned links: "Timeout from 1 second to 7 days (604,800 seconds)".
MAXIMUM_PRESIGN_SECONDS = 604_800
DEFAULT_TIMEOUT_SECONDS = 10
MAXIMUM_TIMEOUT_SECONDS = 120
#: How much of an answer that is not the object is read: enough for an S3 error document.
ERROR_BODY_BYTES = 8192
#: A ListObjectsV2 page of at most 1,000 keys is a few hundred kilobytes; more is refused.
MAXIMUM_LISTING_BYTES = 2 * 1024 * 1024
LISTING_PAGE_KEYS = 1000
#: The write-once guard. A PUT carrying it can only create an object; one that finds the key answers 412.
WRITE_ONCE_HEADERS = (("If-None-Match", "*"),)
#: What a reference to a secret looks like; the name is read from the process environment at use only.
SECRET_REFERENCE = re.compile(r"env:[A-Z_][A-Z0-9_]*")
#: R2 bucket names: lowercase letters, digits and hyphens, 3 to 63, not starting or ending with a hyphen.
BUCKET_NAME = re.compile(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]")
REGION_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
#: The characters SigV4 leaves unencoded (RFC 3986 unreserved).
_UNRESERVED = "-_.~"
_LOOPBACK_HOSTS = ("127.0.0.1", "::1")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


# --- AWS Signature Version 4 -------------------------------------------------------------------------------


def uri_encode(text, *, keep_slash=False):
    """Percent-encode every byte except the unreserved characters, as SigV4 canonicalization requires."""
    return quote(text, safe=_UNRESERVED + ("/" if keep_slash else ""))


def canonical_query(pairs):
    """The canonical query string: each name and value encoded, then sorted by encoded name and value."""
    encoded = sorted((uri_encode(str(name)), uri_encode(str(value))) for name, value in pairs)
    return "&".join(f"{name}={value}" for name, value in encoded)


def _header_value(value):
    """SigV4 'trimall': surrounding white space removed and inner runs of spaces collapsed to one."""
    return " ".join(str(value).split())


def canonical_request(method, path, query, headers, payload_hash):
    """The canonical request and the signed header list for one request.

    `headers` maps every header name to sign to its value. Names are compared
    in lower case. The path is encoded once, the S3 rule (other AWS services
    encode twice).
    """
    lowered = {}
    for name, value in headers.items():
        key = name.strip().lower()
        lowered[key] = (lowered[key] + "," + _header_value(value)) if key in lowered else _header_value(value)
    names = sorted(lowered)
    request = "\n".join((method, uri_encode(path, keep_slash=True), canonical_query(query),
                         "".join(f"{name}:{lowered[name]}\n" for name in names), ";".join(names), payload_hash))
    return request, ";".join(names)


def signing_key(secret_access_key, date, region, service):
    key = hmac.new(("AWS4" + secret_access_key).encode("utf-8"), date.encode("utf-8"), hashlib.sha256).digest()
    for part in (region, service, SIGNING_TERMINATOR):
        key = hmac.new(key, part.encode("utf-8"), hashlib.sha256).digest()
    return key


def signature(*, method, path, query, headers, payload_hash, secret_access_key, region, service, amz_date):
    """The hexadecimal signature and the signed header list of one canonical request."""
    request, signed = canonical_request(method, path, query, headers, payload_hash)
    scope = f"{amz_date[:8]}/{region}/{service}/{SIGNING_TERMINATOR}"
    string_to_sign = "\n".join((SIGNING_ALGORITHM, amz_date, scope,
                                hashlib.sha256(request.encode("utf-8")).hexdigest()))
    key = signing_key(secret_access_key, amz_date[:8], region, service)
    return hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest(), signed


@dataclass(frozen=True)
class SigningKey:
    """One access key with the scope it signs for; the secret is never represented."""

    access_key_id: str
    secret_access_key: str = field(repr=False)
    region: str = DEFAULT_REGION
    service: str = SERVICE


def authorization_header(*, method, path, query, headers, payload_hash, key, amz_date):
    """The Authorization header value for a request whose `headers` already hold every signed header."""
    value, signed = signature(method=method, path=path, query=query, headers=headers, payload_hash=payload_hash,
                              secret_access_key=key.secret_access_key, region=key.region, service=key.service,
                              amz_date=amz_date)
    scope = f"{amz_date[:8]}/{key.region}/{key.service}/{SIGNING_TERMINATOR}"
    return f"{SIGNING_ALGORITHM} Credential={key.access_key_id}/{scope}, SignedHeaders={signed}, Signature={value}"


def presigned_query(*, method, host, path, expires_seconds, access_key_id, secret_access_key, region, service,
                    amz_date):
    """The query pairs of a presigned request that signs only the host, with an unsigned payload."""
    if type(expires_seconds) is not int or not 1 <= expires_seconds <= MAXIMUM_PRESIGN_SECONDS:
        _refuse("presigned_expiry_invalid", f"a presigned link lasts from 1 to {MAXIMUM_PRESIGN_SECONDS} seconds")
    scope = f"{amz_date[:8]}/{region}/{service}/{SIGNING_TERMINATOR}"
    pairs = [("X-Amz-Algorithm", SIGNING_ALGORITHM), ("X-Amz-Credential", f"{access_key_id}/{scope}"),
             ("X-Amz-Date", amz_date), ("X-Amz-Expires", str(expires_seconds)), ("X-Amz-SignedHeaders", "host")]
    value, _signed = signature(method=method, path=path, query=pairs, headers={"host": host},
                               payload_hash=UNSIGNED_PAYLOAD, secret_access_key=secret_access_key,
                               region=region, service=service, amz_date=amz_date)
    return pairs + [("X-Amz-Signature", value)]


def amz_date_of(seconds):
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(seconds))


# --- secrets -----------------------------------------------------------------------------------------------


def environment_reference(reference):
    """Resolve one `env:NAME` reference at use, the rule of the host loader's `environment_secret`."""
    import os
    if not isinstance(reference, str) or not SECRET_REFERENCE.fullmatch(reference):
        _refuse("unsupported_secret_resolver", "a secret is named by an env: reference")
    value = os.environ.get(reference[len("env:"):])
    if not value:
        _refuse("configured_secret_unavailable", "a configured secret reference holds no value in this process")
    return value


def secret_reference(value):
    """Check the form of a reference without reading anything."""
    if not isinstance(value, str) or not SECRET_REFERENCE.fullmatch(value):
        _refuse("unsupported_secret_resolver", "an object store credential is named by an env: reference")
    return value


# --- location ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ObjectStoreLocation:
    """Where the bucket is: an https origin (or a loopback http origin for checks), a bucket and a region."""

    scheme: str
    host: str
    port: "int | None"
    bucket: str
    region: str

    @property
    def host_header(self):
        host = f"[{self.host}]" if ":" in self.host else self.host
        return host if self.port is None else f"{host}:{self.port}"

    @property
    def origin(self):
        return f"{self.scheme}://{self.host_header}"


def parse_location(endpoint, bucket, region=DEFAULT_REGION):
    """Read an endpoint, bucket and region strictly. A plain http origin is allowed for a loopback address only."""
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 255 or endpoint != endpoint.strip():
        _refuse("body_store_root_invalid", "the object store endpoint is one origin")
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError:
        _refuse("body_store_root_invalid", "the object store endpoint is one origin")
    host = (parts.hostname or "").lower()
    if (parts.scheme not in ("https", "http") or not host or parts.username is not None
            or parts.password is not None or parts.path not in ("", "/") or parts.query or parts.fragment
            or "@" in parts.netloc):
        _refuse("body_store_root_invalid", "the object store endpoint is a scheme and a host, nothing more")
    if parts.scheme == "http":
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if not loopback or host not in _LOOPBACK_HOSTS:
            _refuse("body_store_root_invalid", "a plain http object store is allowed on a loopback address only")
    if not isinstance(bucket, str) or not BUCKET_NAME.fullmatch(bucket) or "--" in bucket:
        _refuse("body_store_root_invalid", "the bucket name is 3 to 63 lowercase letters, digits and hyphens")
    if not isinstance(region, str) or not REGION_NAME.fullmatch(region):
        _refuse("body_store_root_invalid", "the region is a short lowercase name such as auto")
    return ObjectStoreLocation(parts.scheme, host, port, bucket, region)


class _TransportFailure(Exception):
    """The store gave no usable answer: a connection, TLS, timeout or protocol failure. Never shown as is."""


# --- the engine --------------------------------------------------------------------------------------------


class ObjectStoreBodyStore:
    """Bodies in one private bucket of an S3-compatible store, behind the body store edge.

    The answers match `VolumeBodyStore` record for record: the same capability
    keys, the same put result, the same refusal codes for the same faults. Two
    failures the volume cannot have are mapped onto existing codes: a read the
    store did not answer (credentials refused, server error, redirect, timeout,
    missing bucket) is `body_unreadable`, and a write it did not accept is
    `body_store_write_failed`. Their messages name the kind of failure and the
    HTTP status class, never a header, a credential or a response body.
    """

    def __init__(self, endpoint, bucket, *, access_key_id_ref, secret_access_key_ref, region=DEFAULT_REGION,
                 writes_authorized=False, maximum_file_bytes=MAXIMUM_FILE_BYTES,
                 timeout_seconds=DEFAULT_TIMEOUT_SECONDS, secret_resolver=None, clock=time.time):
        if type(writes_authorized) is not bool:
            _refuse("body_store_root_invalid", "body store write authority is an explicit Boolean")
        if type(maximum_file_bytes) is not int or not 1 <= maximum_file_bytes <= MAXIMUM_PACKAGE_BYTES:
            _refuse("body_store_root_invalid", "the file allowance is a positive bounded byte count")
        if (type(timeout_seconds) not in (int, float) or timeout_seconds != timeout_seconds
                or not 0 < timeout_seconds <= MAXIMUM_TIMEOUT_SECONDS):
            _refuse("body_store_root_invalid", f"the timeout is above 0 and at most {MAXIMUM_TIMEOUT_SECONDS} s")
        if secret_resolver is not None and not callable(secret_resolver):
            _refuse("unsupported_secret_resolver", "the secret resolver is a function of one reference")
        if not callable(clock):
            _refuse("body_store_root_invalid", "the clock is a function")
        self.location = parse_location(endpoint, bucket, region)
        self._key_reference = secret_reference(access_key_id_ref)
        self._secret_reference = secret_reference(secret_access_key_ref)
        self._resolve = secret_resolver or environment_reference
        self.writes_authorized = writes_authorized
        self.maximum_file_bytes = maximum_file_bytes
        self.timeout_seconds = float(timeout_seconds)
        self.clock = clock
        self._local = threading.local()
        self._open = set()
        self._operations = Counter()
        self._lock = threading.Lock()
        self._tls = ssl.create_default_context() if self.location.scheme == "https" else None

    def __repr__(self):
        return (f"ObjectStoreBodyStore(origin={self.location.origin!r}, bucket={self.location.bucket!r}, "
                f"writes={self.writes_authorized})")

    def capabilities(self):
        return {"record_type": BODY_STORE_CAPABILITIES_VERSION, "edge": BODY_STORE_EDGE_VERSION,
                "engine": ENGINE_ID, "engine_version": ENGINE_VERSION, "content_addressed": True,
                "digest": "sha256", "writes": self.writes_authorized, "object_key": OBJECT_KEY_FORM,
                "maximum_file_bytes": self.maximum_file_bytes}

    @staticmethod
    def object_key(digest):
        exact_digest(digest)
        return f"sha256/{digest[:2]}/{digest}"

    def _path(self, digest):
        return f"/{self.location.bucket}/{self.object_key(digest)}"

    # --- the edge ------------------------------------------------------------------------------------------

    def read(self, digest, size_bytes):
        exact_digest(digest)
        if type(size_bytes) is not int or size_bytes < 0:
            _refuse("body_size_mismatch", "a read names the exact size it expects")
        if size_bytes > self.maximum_file_bytes:
            _refuse("body_too_large", "the object is larger than this store's file allowance")
        status, payload = self._request("GET", self._path(digest), read_limit=self._read_bound(size_bytes),
                                        failure="body_unreadable")
        if status == 404:
            if _error_code(payload) in ("NoSuchKey", ""):
                _refuse("body_missing", "the body store holds no object with that digest")
            _refuse("body_unreadable", "the object store has no such bucket or refused the address")
        if status != 200:
            _refuse("body_unreadable", f"the object store answered a read with status class {status // 100}xx")
        return self._verified(payload, digest, size_bytes)

    def put(self, payload, *, expected_digest=None, durable=True):
        """Create the object once under its digest; an existing different object is never replaced.

        `durable` is accepted for the edge and changes nothing: the store answers
        a PUT only after the object is stored.
        """
        if not self.writes_authorized:
            _refuse("body_store_writes_not_authorized", "this body store was opened for reading")
        if not isinstance(payload, bytes):
            _refuse("body_payload_invalid", "a body is bytes")
        if len(payload) > self.maximum_file_bytes:
            _refuse("body_too_large", "the body is larger than this store's file allowance")
        digest = sha256_hex(payload)
        if expected_digest is not None and exact_digest(expected_digest) != digest:
            _refuse("body_digest_mismatch", "the bytes differ from the digest they were declared under")
        headers = {"Content-Type": "application/octet-stream",
                   "Content-MD5": base64.b64encode(hashlib.md5(payload, usedforsecurity=False).digest()).decode(),
                   **dict(WRITE_ONCE_HEADERS)}
        status, _answer = self._request("PUT", self._path(digest), body=payload, headers=headers,
                                        payload_hash=digest, read_limit=0, failure="body_store_write_failed")
        if status == 412:
            if not self._existing_matches(digest, len(payload)):
                _refuse("body_digest_conflict",
                        "an object already stored under this digest holds other bytes; it is never overwritten")
            return {"digest": digest, "size_bytes": len(payload), "written": False}
        if status != 200:
            _refuse("body_store_write_failed", f"the object store answered a write with status class {status // 100}xx")
        try:
            self.read(digest, len(payload))
        except ServiceRuntimeError:
            _refuse("body_store_write_failed", "the stored object could not be read back")
        return {"digest": digest, "size_bytes": len(payload), "written": True}

    def sync(self):
        """Nothing to flush: every acknowledged PUT is already durable in the store."""

    # --- guards, kept as methods so a check can remove one and see it fail ---------------------------------

    def _read_bound(self, size_bytes):
        """At most one byte more than the recorded size is read, so a longer answer is seen and costs nothing."""
        return size_bytes + 1

    def _verified(self, payload, digest, size_bytes):
        if len(payload) != size_bytes:
            _refuse("body_size_mismatch", "the object size differs from the recorded size")
        if sha256_hex(payload) != digest:
            _refuse("body_digest_mismatch", "the object bytes differ from their digest")
        return payload

    def _existing_matches(self, digest, size_bytes):
        """After a 412: whether the stored object holds exactly these bytes."""
        try:
            self.read(digest, size_bytes)
            return True
        except ServiceRuntimeError as error:
            if error.code in ("body_size_mismatch", "body_digest_mismatch"):
                return False
            if error.code == "body_missing":
                _refuse("body_store_write_failed", "the store refused the write and then held no such object")
            raise

    # --- operator helpers, outside the edge ----------------------------------------------------------------

    def presigned_read_url(self, digest, expires_seconds):
        """A GET link for one object, valid `expires_seconds` (1 to 604,800). It is a bearer link."""
        exact_digest(digest)
        access_key_id, secret = self._credentials()
        path = self._path(digest)
        pairs = presigned_query(method="GET", host=self.location.host_header, path=path,
                                expires_seconds=expires_seconds, access_key_id=access_key_id,
                                secret_access_key=secret, region=self.location.region, service=SERVICE,
                                amz_date=amz_date_of(self.clock()))
        return f"{self.location.origin}{uri_encode(path, keep_slash=True)}?{canonical_query(pairs)}"

    def stored_objects(self, prefix="sha256/"):
        """Every (key, size) the bucket holds under `prefix`, one ListObjectsV2 page at a time."""
        if not isinstance(prefix, str) or len(prefix) > 64:
            _refuse("body_store_root_invalid", "a listing prefix is short text")
        token, seen = None, set()
        while True:
            query = [("list-type", "2"), ("prefix", prefix), ("max-keys", str(LISTING_PAGE_KEYS))]
            if token:
                query.append(("continuation-token", token))
            status, payload = self._request("GET", f"/{self.location.bucket}", query=query,
                                            read_limit=MAXIMUM_LISTING_BYTES + 1, failure="body_unreadable",
                                            operation="LIST")
            if status != 200 or len(payload) > MAXIMUM_LISTING_BYTES:
                _refuse("body_unreadable", f"the object store answered a listing with status class {status // 100}xx")
            rows, token = _listing(payload)
            if token is not None:
                if token in seen:
                    _refuse("body_unreadable", "the object store repeated its listing cursor")
                seen.add(token)
            yield from rows
            if not token:
                return

    def close(self):
        """End every connection this engine opened; a later request opens a new one."""
        with self._lock:
            held, self._open = list(self._open), set()
        self._local = threading.local()
        for connection in held:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a broken connection has nothing left to report
                pass

    def __enter__(self):
        return self

    def __exit__(self, *_exception):
        self.close()

    def operation_counts(self):
        """Requests sent so far by kind: PUT and LIST are R2 Class A operations, GET is Class B."""
        with self._lock:
            return dict(self._operations)

    # --- transport -----------------------------------------------------------------------------------------

    def _credentials(self):
        try:
            access_key_id = self._resolve(self._key_reference)
            secret = self._resolve(self._secret_reference)
        except ServiceRuntimeError as error:
            raise ServiceRuntimeError(error.code, "an object store credential reference could not be resolved") from None
        except Exception:  # noqa: BLE001 - a resolver's own failure text could carry what it resolved
            _refuse("configured_secret_unavailable", "an object store credential reference could not be resolved")
        if not isinstance(access_key_id, str) or not access_key_id or not isinstance(secret, str) or not secret:
            _refuse("configured_secret_unavailable", "an object store credential reference resolved to nothing")
        return access_key_id, secret

    def _connection(self):
        """This thread's connection and whether it already carried a request."""
        held = getattr(self._local, "connection", None)
        if held is not None:
            return held, True
        location = self.location
        if location.scheme == "https":
            held = http.client.HTTPSConnection(location.host, location.port, timeout=self.timeout_seconds,
                                               context=self._tls)
        else:
            held = http.client.HTTPConnection(location.host, location.port, timeout=self.timeout_seconds)
        self._local.connection = held
        with self._lock:
            self._open.add(held)
        return held, False

    def _drop_connection(self):
        held = getattr(self._local, "connection", None)
        self._local.connection = None
        if held is not None:
            with self._lock:
                self._open.discard(held)
            try:
                held.close()
            except Exception:  # noqa: BLE001 - closing a broken connection has nothing left to report
                pass

    def _request(self, method, path, *, query=(), body=None, headers=None, payload_hash=EMPTY_PAYLOAD_DIGEST,
                 read_limit, failure, operation=None):
        """(status, at most `read_limit` bytes of the answer for 200, else a bounded error document)."""
        try:
            return self._exchange(method, path, query=query, body=body, headers=headers or {},
                                  payload_hash=payload_hash, read_limit=read_limit, operation=operation or method)
        except _TransportFailure as failed:
            _refuse(failure, f"the object store did not answer: {failed}")

    def _exchange(self, method, path, *, query, body, headers, payload_hash, read_limit, operation):
        """One signed request. A connection kept from an earlier request that turns out to be closed by the store
        before any answer is replaced and the request sent once more; this is the transport's stale connection,
        not a retry of an answer, and it is safe for a read and for the write-once PUT, whose repeat answers 412."""
        access_key_id, secret = self._credentials()
        amz_date = amz_date_of(self.clock())
        signed = {**headers, "host": self.location.host_header, "x-amz-date": amz_date,
                  "x-amz-content-sha256": payload_hash}
        signed["Authorization"] = authorization_header(
            method=method, path=path, query=query, headers=signed, payload_hash=payload_hash,
            key=SigningKey(access_key_id, secret, self.location.region, SERVICE), amz_date=amz_date)
        target = uri_encode(path, keep_slash=True) + (f"?{canonical_query(query)}" if query else "")
        for attempt in (1, 2):
            connection, reused = self._connection()
            with self._lock:
                self._operations[operation] += 1
            try:
                connection.request(method, target, body=body, headers=signed)
                response = connection.getresponse()
            except _STALE_CONNECTION as error:
                self._drop_connection()
                if reused and attempt == 1:
                    continue
                raise _TransportFailure(type(error).__name__) from None
            except (OSError, http.client.HTTPException) as error:
                self._drop_connection()
                raise _TransportFailure(_failure_name(error)) from None
            reusable = False
            try:
                status = response.status
                # A write's answer and an error document are read up to a small bound; that also lets an empty
                # answer finish, so the connection can carry the next request.
                limit = read_limit if status == 200 and read_limit else ERROR_BODY_BYTES
                payload = response.read(limit)
                reusable = response.isclosed() and not response.will_close
                return status, payload
            except (OSError, http.client.HTTPException) as error:
                raise _TransportFailure(_failure_name(error)) from None
            finally:
                if not reusable:
                    self._drop_connection()
        raise _TransportFailure("connection closed")


#: Failures that mean a kept connection was already closed by the store when the request went out.
_STALE_CONNECTION = (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError)


def _failure_name(error):
    return "timed out" if isinstance(error, TimeoutError) or "timed out" in str(error) else type(error).__name__


def _error_code(document):
    """The Code of an S3 error document, or empty text when there is none to read."""
    if not document:
        return ""
    match = re.search(rb"<Code>([A-Za-z0-9]{1,64})</Code>", document[:ERROR_BODY_BYTES])
    return match.group(1).decode("ascii") if match else ""


def _listing(document):
    """The (key, size) rows and the next continuation token of one ListObjectsV2 page."""
    if b"<!DOCTYPE" in document.upper() or b"<!ENTITY" in document.upper():
        _refuse("body_unreadable", "the object store listing cannot declare XML entities")
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError:
        _refuse("body_unreadable", "the object store answered a listing that is not a listing")

    def local(tag):
        return tag.rsplit("}", 1)[-1]
    if local(root.tag) != "ListBucketResult":
        _refuse("body_unreadable", "the object store answered another XML document")
    rows, token, truncated, seen_keys = [], None, None, set()
    for element in root:
        name = local(element.tag)
        if name == "Contents":
            fields = {local(node.tag): (node.text or "") for node in element}
            try:
                key, size = fields["Key"], int(fields["Size"])
                if not key or size < 0 or key in seen_keys:
                    raise ValueError()
                seen_keys.add(key)
                rows.append((key, size))
            except (KeyError, ValueError):
                _refuse("body_unreadable", "the object store answered a listing row without a key or size")
        elif name == "IsTruncated":
            flag = (element.text or "").strip()
            if flag not in ("true", "false") or truncated is not None:
                _refuse("body_unreadable", "the object store answered an invalid truncation flag")
            truncated = flag == "true"
        elif name == "NextContinuationToken":
            token = (element.text or "").strip() or None
    if truncated is None or truncated and not token:
        _refuse("body_unreadable", "the object store answered a truncated listing without a continuation token")
    return rows, (token if truncated else None)
