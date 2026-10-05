"""A loopback S3-compatible object store for checks: SigV4 verified, write-once honoured, faults on request.

Kind: test fixture, like `http_test_fixtures.py`. It is not an engine and
serves nothing to customers. It binds 127.0.0.1 on a port the system picks,
answers path-style requests for one bucket, and keeps objects in memory.

```text
Object store fake
├── authentication   SigV4 Authorization headers and presigned query links, both recomputed from
│                    the request with the known secret; a mismatch answers 403 SignatureDoesNotMatch
│                    and an expired link 403 AccessDenied, as S3 and R2 do
├── integrity        x-amz-content-sha256 and Content-MD5 checked against the received bytes
├── write once       If-None-Match: * on a key that exists answers 412 and stores nothing
├── operations       PutObject, GetObject, HeadObject, ListObjectsV2 (prefix, continuation-token)
└── faults           plant other bytes under a key, fail with a status, redirect, delay, serve extra
                     bytes beyond the object, end a kept connection without saying so, switch
                     signature or expiry verification off
```

The signature check here is written separately from the engine's signer in
`catalogue_object_store.py`, so the two meet only through the protocol; the
engine's signer is also held to the published AWS test vectors by the kit.
"""
from __future__ import annotations

import base64
import calendar
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import threading
import time
from urllib.parse import parse_qsl, quote, unquote, urlsplit, urlunsplit
from xml.sax.saxutils import escape

ALGORITHM = "AWS4-HMAC-SHA256"
UNSIGNED = "UNSIGNED-PAYLOAD"
MAXIMUM_SKEW_SECONDS = 15 * 60
MAXIMUM_EXPIRES = 604_800
MAXIMUM_BODY_BYTES = 64 * 1024 * 1024
_AUTHORIZATION = re.compile(r"AWS4-HMAC-SHA256 Credential=([^,\s]+),\s*SignedHeaders=([^,\s]+),\s*Signature=([0-9a-f]{64})")


def _encode(text):
    return quote(text, safe="-_.~")


def _canonical(method, raw_path, pairs, header_lines, signed_names, payload_hash):
    path = "/".join(_encode(unquote(part)) for part in raw_path.split("/"))
    query = "&".join(f"{name}={value}" for name, value in sorted((_encode(n), _encode(v)) for n, v in pairs))
    return "\n".join((method, path, query, header_lines, signed_names, payload_hash))


def _sign(secret, amz_date, scope, canonical_text):
    date, region, service, terminator = scope.split("/")
    key = hmac.new(("AWS4" + secret).encode(), date.encode(), hashlib.sha256).digest()
    for part in (region, service, terminator):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    text = "\n".join((ALGORITHM, amz_date, scope, hashlib.sha256(canonical_text.encode()).hexdigest()))
    return hmac.new(key, text.encode(), hashlib.sha256).hexdigest()


def _amz_seconds(value):
    try:
        return calendar.timegm(time.strptime(value, "%Y%m%dT%H%M%SZ"))
    except (TypeError, ValueError):
        return None


class ObjectStoreFake:
    """One bucket of an S3-compatible store on a loopback port, for the body store kit and the mirror tool."""

    def __init__(self, *, access_key_id, secret_access_key, bucket, region="auto", clock=time.time,
                 page_keys=1000):
        self.access_key_id, self.secret_access_key = access_key_id, secret_access_key
        self.bucket, self.region, self.clock, self.page_keys = bucket, region, clock, page_keys
        self.objects = {}
        self.requests = []
        self.verify_signatures = True
        self.verify_expiry = True
        self.delay_seconds = 0.0
        self.extra_bytes = 0
        self._failures = []
        self._redirects = []
        self._silent_closes = 0
        self._lock = threading.Lock()
        self._server = None
        self._thread = None
        self.endpoint = ""

    # --- life cycle ----------------------------------------------------------------------------------------

    def start(self):
        fake = self

        class Handler(_Handler):
            store = fake
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05},
                                        name="object-store-fake", daemon=True)
        self._thread.start()
        host, port = self._server.server_address[:2]
        self.endpoint = urlunsplit(("http", f"{host}:{port}", "", "", ""))
        return self

    def close(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(10)
            self._server = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *_exception):
        self.close()

    # --- fault hooks ---------------------------------------------------------------------------------------

    def plant(self, key, payload):
        """Store bytes under a key directly, with no check: other bytes under a digest's name."""
        with self._lock:
            self.objects[key] = bytes(payload)

    def drop(self, key):
        with self._lock:
            self.objects.pop(key, None)

    def fail_next(self, status=500, count=1):
        with self._lock:
            self._failures.extend([status] * count)

    def redirect_next(self, location, count=1):
        with self._lock:
            self._redirects.extend([location] * count)

    def close_silently_after_next(self, count=1):
        """After the next answer, end its connection without saying so, as a store ends an idle kept connection."""
        with self._lock:
            self._silent_closes += count

    def held(self, key):
        with self._lock:
            return self.objects.get(key)

    def count(self, method=None, status=None):
        with self._lock:
            return sum(1 for row in self.requests
                       if (method is None or row[0] == method) and (status is None or row[2] == status))

    def _take(self, queue):
        with self._lock:
            return queue.pop(0) if queue else None

    def _record(self, method, path, status):
        with self._lock:
            self.requests.append((method, path, status))


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    store: ObjectStoreFake

    def log_message(self, *_arguments):  # the checks read the request record, not a log
        pass

    def do_GET(self):
        self._serve("GET")

    def do_HEAD(self):
        self._serve("HEAD")

    def do_PUT(self):
        self._serve("PUT")

    def do_DELETE(self):
        self._serve("DELETE")

    # --- answers -------------------------------------------------------------------------------------------

    def _answer(self, method, status, body=b"", headers=(), *, length=None):
        # Recorded before the answer is sent, so a client that has its answer always finds the request recorded.
        self.store._record(method, self.path.split("?", 1)[0], status)
        self.send_response(status)
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body) if length is None else length))
        self.end_headers()
        if method != "HEAD" and body:
            try:
                self.wfile.write(body)
            except OSError:  # the client stopped reading, as a bounded reader does
                pass
        with self.store._lock:
            if self.store._silent_closes:
                self.store._silent_closes -= 1
                self.close_connection = True

    def _error(self, method, status, code, message):
        document = (f'<?xml version="1.0" encoding="UTF-8"?><Error><Code>{code}</Code>'
                    f"<Message>{escape(message)}</Message></Error>").encode()
        self._answer(method, status, document, (("Content-Type", "application/xml"),))

    # --- one request ---------------------------------------------------------------------------------------

    def _serve(self, method):
        store = self.store
        body = b""
        length = self.headers.get("Content-Length")
        if length is not None:
            if not length.isdigit() or int(length) > MAXIMUM_BODY_BYTES:
                self.close_connection = True
                return self._error(method, 400, "EntityTooLarge", "the body is larger than this store accepts")
            body = self.rfile.read(int(length))
        if store.delay_seconds:
            time.sleep(store.delay_seconds)
        failure = store._take(store._failures)
        if failure is not None:
            return self._error(method, failure, "InternalError", "an injected failure")
        location = store._take(store._redirects)
        if location is not None:
            return self._answer(method, 307, b"", (("Location", location),))
        parts = urlsplit(self.path)
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        segments = parts.path.split("/", 2)
        if len(segments) < 2 or unquote(segments[1]) != store.bucket:
            return self._error(method, 404, "NoSuchBucket", "the specified bucket does not exist")
        refusal = self._authenticate(method, parts.path, pairs, body)
        if refusal is not None:
            return self._error(method, *refusal)
        key = unquote(segments[2]) if len(segments) == 3 else ""
        if not key:
            if method == "GET" and dict(pairs).get("list-type") == "2":
                return self._list(dict(pairs))
            return self._error(method, 501, "NotImplemented", "only object operations and ListObjectsV2")
        if method == "PUT":
            return self._put(key, body)
        if method in ("GET", "HEAD"):
            held = store.held(key)
            if held is None:
                return self._error(method, 404, "NoSuchKey", "the specified key does not exist")
            served = held + b"x" * store.extra_bytes
            return self._answer(method, 200, served, (("Content-Type", "application/octet-stream"),
                                                      ("ETag", '"' + hashlib.md5(held).hexdigest() + '"')))
        if method == "DELETE":
            store.drop(key)
            return self._answer(method, 204)
        return self._error(method, 405, "MethodNotAllowed", "method not allowed")

    def _put(self, key, body):
        store = self.store
        declared = self.headers.get("x-amz-content-sha256", "")
        if declared != UNSIGNED and declared != hashlib.sha256(body).hexdigest():
            return self._error("PUT", 400, "XAmzContentSHA256Mismatch", "the payload hash does not match")
        md5 = self.headers.get("Content-MD5")
        if md5 is not None and md5 != base64.b64encode(hashlib.md5(body).digest()).decode():
            return self._error("PUT", 400, "BadDigest", "the Content-MD5 does not match the body")
        with store._lock:
            if self.headers.get("If-None-Match", "").strip() == "*" and key in store.objects:
                exists = True
            else:
                exists = False
                store.objects[key] = body
        if exists:
            return self._error("PUT", 412, "PreconditionFailed", "an object already exists under this key")
        return self._answer("PUT", 200, b"", (("ETag", '"' + hashlib.md5(body).hexdigest() + '"'),))

    def _list(self, fields):
        store = self.store
        prefix = fields.get("prefix", "")
        start = ""
        token = fields.get("continuation-token")
        if token:
            try:
                start = base64.urlsafe_b64decode(token.encode()).decode()
            except (ValueError, UnicodeDecodeError):
                return self._error("GET", 400, "InvalidArgument", "the continuation token is not valid")
        try:
            limit = min(int(fields.get("max-keys", "1000")), store.page_keys)
        except ValueError:
            return self._error("GET", 400, "InvalidArgument", "max-keys is a number")
        with store._lock:
            keys = sorted(key for key in store.objects if key.startswith(prefix) and key > start)
            page = [(key, len(store.objects[key])) for key in keys[:limit]]
        truncated = len(keys) > limit
        rows = "".join(f"<Contents><Key>{escape(key)}</Key><Size>{size}</Size></Contents>" for key, size in page)
        following = (f"<NextContinuationToken>{base64.urlsafe_b64encode(page[-1][0].encode()).decode()}"
                     f"</NextContinuationToken>") if truncated and page else ""
        document = ('<?xml version="1.0" encoding="UTF-8"?>'
                    '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                    f"<Name>{escape(store.bucket)}</Name><Prefix>{escape(prefix)}</Prefix>"
                    f"<KeyCount>{len(page)}</KeyCount><MaxKeys>{limit}</MaxKeys>"
                    f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>{following}{rows}"
                    "</ListBucketResult>").encode()
        return self._answer("GET", 200, document, (("Content-Type", "application/xml"),))

    # --- authentication ------------------------------------------------------------------------------------

    def _authenticate(self, method, raw_path, pairs, body):
        """None when the request is signed with the known secret, else (status, code, message)."""
        store = self.store
        fields = dict(pairs)
        if "X-Amz-Algorithm" in fields:
            return self._presigned(method, raw_path, pairs, fields)
        header = self.headers.get("Authorization", "")
        match = _AUTHORIZATION.fullmatch(header.strip())
        if match is None:
            return 403, "AccessDenied", "the request is not signed"
        credential, signed_names, offered = match.groups()
        key_id, _, scope = credential.partition("/")
        amz_date = self.headers.get("x-amz-date", "")
        names = signed_names.split(";")
        if key_id != store.access_key_id:
            return 403, "InvalidAccessKeyId", "the access key does not exist"
        moment = _amz_seconds(amz_date)
        if moment is None or abs(moment - store.clock()) > MAXIMUM_SKEW_SECONDS:
            return 403, "RequestTimeTooSkewed", "the request time is too far from the store's time"
        if (scope != f"{amz_date[:8]}/{store.region}/s3/aws4_request"
                or not {"host", "x-amz-date", "x-amz-content-sha256"} <= set(names) or names != sorted(names)):
            return 403, "SignatureDoesNotMatch", "the signed scope or headers are incomplete"
        lines = ""
        for name in names:
            values = self.headers.get_all(name) or []
            if not values:
                return 403, "SignatureDoesNotMatch", "a signed header is missing"
            lines += f"{name}:{','.join(' '.join(value.split()) for value in values)}\n"
        payload_hash = self.headers.get("x-amz-content-sha256", "")
        expected = _sign(store.secret_access_key, amz_date, scope,
                         _canonical(method, raw_path, pairs, lines, signed_names, payload_hash))
        if store.verify_signatures and not hmac.compare_digest(expected, offered):
            return 403, "SignatureDoesNotMatch", "the signature does not match"
        return None

    def _presigned(self, method, raw_path, pairs, fields):
        store = self.store
        try:
            expires = int(fields.get("X-Amz-Expires", ""))
        except ValueError:
            return 400, "AuthorizationQueryParametersError", "X-Amz-Expires is a number"
        if not 1 <= expires <= MAXIMUM_EXPIRES:
            return 400, "AuthorizationQueryParametersError", "X-Amz-Expires is 1 to 604800"
        credential = fields.get("X-Amz-Credential", "")
        key_id, _, scope = credential.partition("/")
        amz_date = fields.get("X-Amz-Date", "")
        moment = _amz_seconds(amz_date)
        if fields.get("X-Amz-Algorithm") != ALGORITHM or moment is None:
            return 400, "AuthorizationQueryParametersError", "the presigned parameters are incomplete"
        if key_id != store.access_key_id:
            return 403, "InvalidAccessKeyId", "the access key does not exist"
        if store.verify_expiry and store.clock() > moment + expires:
            return 403, "AccessDenied", "Request has expired"
        names = fields.get("X-Amz-SignedHeaders", "")
        if scope != f"{amz_date[:8]}/{store.region}/s3/aws4_request" or names != "host":
            return 403, "SignatureDoesNotMatch", "the signed scope or headers are not the expected ones"
        lines = f"host:{' '.join((self.headers.get('Host') or '').split())}\n"
        unsigned = [(name, value) for name, value in pairs if name != "X-Amz-Signature"]
        expected = _sign(store.secret_access_key, amz_date, scope,
                         _canonical(method, raw_path, unsigned, lines, names, UNSIGNED))
        if store.verify_signatures and not hmac.compare_digest(expected, fields.get("X-Amz-Signature", "")):
            return 403, "SignatureDoesNotMatch", "the signature does not match"
        return None
