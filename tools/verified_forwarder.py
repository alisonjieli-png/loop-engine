"""Loopback forwarder that holds one upstream HTTPS origin to a pinned TLS trust contract.

Kind: operator transport utility. Some HTTP clients cannot be told which
certificate name to expect or which single root to trust. OpenCode's client is
one: its runtime honours NODE_EXTRA_CA_CERTS, but that only adds a root to the
public store, and the hostname check still runs against the host the URL
connects to. A server whose certificate comes from a private authority and
names another host than the one it is reached by therefore cannot be verified
by such a client, and the old workaround was to switch verification off.

This forwarder is the verified alternative. The client talks plain HTTP to a
port on 127.0.0.1 in the same process tree. Each request it forwards opens a
new upstream connection through
``loop_engine.core.custom_endpoint._TrustedHTTPSConnection``, the product's own
trust contract connection: the TCP connection goes to the URL host, the
handshake names the expected server name, the context trusts exactly one
anchor file (``ssl.create_default_context(cafile=...)``, hostname checking on,
``CERT_REQUIRED``), and an optional pin compares the leaf certificate. A server
that cannot prove that identity is refused inside ``connect``, before the
request line is written, so no header, body or key leaves the process.

```text
VerifiedForwarder
├── binds 127.0.0.1 only, on a free port, with a random path token
├── forwards GET and POST under the upstream API base, nothing else
├── upstream: one verified connection per request, no redirect followed
├── authorization: passed through, or replaced by the one this process holds
└── refusals: 404 outside the token or base, 502 tls_trust_refused with nothing sent
```

The response is streamed back as it arrives (chunked), so server-sent events
keep flowing. A truncated upstream body ends the client's body without its
final chunk, so the client sees a broken stream instead of a short answer.
Error answers name a stable code and never the upstream host, its certificate
name, a header or a key.
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import http.server
import json
import secrets
import ssl
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

try:
    from loop_engine.core import custom_endpoint
except ImportError:  # run from a checkout without an installed package
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from loop_engine.core import custom_endpoint

RECORD_TYPE = "verified_forwarder/v1"
#: Headers that describe one connection and are never forwarded (RFC 9110 section 7.6.1), plus the
#: ones this forwarder writes itself and the 100-continue handshake, which it already answered.
HOP_BY_HOP = frozenset({"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
                        "trailer", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
                        "expect"})
RESPONSE_OWN = frozenset({"server", "date"})
MAX_REQUEST_BYTES = 64 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 1800.0


class ForwarderError(ValueError):
    """A forwarder declaration is invalid. Raised before any socket opens; the message names no private value."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def anchor_context(ca_file, ca_sha256: str | None = None) -> ssl.SSLContext:
    """A client context that trusts exactly the one anchor file and checks the server name.

    With a cafile, ``ssl.create_default_context`` loads that file alone and never the system store.
    When ``ca_sha256`` is given, the file's bytes must have that SHA-256, so a changed anchor is refused
    instead of trusted.
    """
    path = Path(ca_file)
    try:
        raw = path.read_bytes()
    except OSError:
        raise ForwarderError("trust_anchor_unreadable", "the declared trust anchor file cannot be read") from None
    if ca_sha256 is not None and not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), ca_sha256):
        raise ForwarderError("trust_anchor_digest_mismatch",
                             "the trust anchor file is not the one this forwarder was declared with")
    try:
        context = ssl.create_default_context(cafile=str(path))
    except (OSError, ValueError, ssl.SSLError):
        raise ForwarderError("trust_anchor_invalid", "the declared trust anchor is not a certificate") from None
    # The defaults already; stated so a reader and the repository's TLS guard see them.
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def _upstream(base_url: str) -> tuple[str, int, str]:
    """(host, port, API base path) of an https:// origin, refused when it carries anything else."""
    if type(base_url) is not str or any(character.isspace() for character in base_url):
        raise ForwarderError("upstream_invalid", "the upstream base URL must be one https:// URL")
    parts = urlsplit(base_url)
    try:
        port = parts.port or 443
    except ValueError:
        raise ForwarderError("upstream_invalid", "the upstream port is not a number") from None
    if (parts.scheme != "https" or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.query or parts.fragment):
        raise ForwarderError("upstream_invalid",
                             "the upstream must be https:// with a host and no credentials, query or fragment")
    return parts.hostname, port, parts.path.rstrip("/")


class VerifiedForwarder:
    """Plain HTTP on 127.0.0.1 in, one verified HTTPS origin out."""

    def __init__(self, upstream_base_url: str, *, ca_file, ca_sha256: str | None = None,
                 tls_server_name: str = "", tls_pinned_sha256: str = "", authorization: str | None = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.host, self.port, self.base_path = _upstream(upstream_base_url)
        if tls_server_name and not custom_endpoint._TLS_SERVER_NAME.fullmatch(tls_server_name):
            raise ForwarderError("tls_server_name_invalid", "the expected name must be a lower-case DNS name")
        pin = tls_pinned_sha256.replace(":", "").lower()
        if pin and not custom_endpoint._SHA256_HEX.fullmatch(pin):
            raise ForwarderError("tls_pin_invalid", "the pin must be the SHA-256 of the leaf certificate")
        if authorization is not None and (not authorization.strip() or "\n" in authorization
                                          or "\r" in authorization):
            raise ForwarderError("authorization_invalid", "the authorization header value is empty or multi-line")
        self.context = anchor_context(ca_file, ca_sha256)
        self.tls_server_name, self.tls_pinned_sha256 = tls_server_name, pin
        self.authorization = authorization
        self.timeout_seconds = float(timeout_seconds)
        self.token = secrets.token_urlsafe(24)
        self.counts = {"forwarded": 0, "tls_trust_refused": 0, "transport_failed": 0, "refused_path": 0}
        self._lock = threading.Lock()
        self._server: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> str:
        """Bind a free port on 127.0.0.1, serve in a daemon thread, return the local API base URL."""
        if self._server is not None:
            return self.base_url
        server = _Server(self)
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="verified-forwarder", daemon=True)
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()

    @property
    def serving(self) -> bool:
        return self._server is not None and self._thread is not None and self._thread.is_alive()

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise ForwarderError("forwarder_not_started")
        return f"http://127.0.0.1:{self._server.server_port}/{self.token}{self.base_path}"

    # -- upstream ------------------------------------------------------------
    def connection(self, timeout: float | None = None) -> http.client.HTTPSConnection:
        """One upstream connection held to the trust contract; it verifies when it connects."""
        return custom_endpoint._TrustedHTTPSConnection(
            self.host, port=self.port, timeout=self.timeout_seconds if timeout is None else timeout,
            context=self.context, tls_server_name=self.tls_server_name,
            tls_pinned_sha256=self.tls_pinned_sha256)

    def handshake(self, timeout: float = 20.0) -> dict:
        """Open and close one verified TLS connection without sending any HTTP; report the leaf digest."""
        connection = self.connection(timeout)
        try:
            connection.connect()
            leaf = connection.sock.getpeercert(binary_form=True) or b""
            return {"verified": True, "tls_version": connection.sock.version(),
                    "leaf_sha256": hashlib.sha256(leaf).hexdigest()}
        finally:
            connection.close()

    def upstream_path(self, path: str) -> str | None:
        """The upstream path for a local request path, or None when it is outside the token or the API base."""
        prefix, _, rest = path.lstrip("/").partition("/")
        if not hmac.compare_digest(prefix.encode(), self.token.encode()):
            return None
        rest = "/" + rest
        route = rest.split("?", 1)[0]
        if self.base_path and route != self.base_path and not route.startswith(self.base_path + "/"):
            return None
        return rest

    def summary(self) -> dict:
        """What a record may hold: the trust contract's shape and the counts, never the host, name or key."""
        with self._lock:
            counts = dict(self.counts)
        return {"record_type": RECORD_TYPE, "transport": "loopback_http_to_verified_https",
                "trust_anchor": "pinned_file", "hostname_check": True,
                "expected_name_declared": bool(self.tls_server_name),
                "leaf_pin_declared": bool(self.tls_pinned_sha256),
                "authorization": "replaced" if self.authorization is not None else "passed_through",
                "counts": counts}

    def count(self, name: str) -> None:
        with self._lock:
            self.counts[name] += 1


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, forwarder: VerifiedForwarder) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.forwarder = forwarder

    def handle_error(self, request, client_address) -> None:
        # A client that hangs up mid-stream is not an error of the forwarder; nothing private is printed.
        return None


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "verified-forwarder"
    sys_version = ""

    def log_message(self, *args) -> None:
        return None

    def do_GET(self) -> None:
        self._forward()

    def do_POST(self) -> None:
        self._forward()

    def _refuse_method(self) -> None:
        self._answer(405, "method_not_forwarded", "only GET and POST are forwarded")

    do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _refuse_method

    def _answer(self, status: int, code: str, message: str) -> None:
        body = json.dumps({"error": {"type": code, "code": code, "message": message}}).encode()
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _forward(self) -> None:
        forwarder: VerifiedForwarder = self.server.forwarder
        path = forwarder.upstream_path(self.path)
        if path is None:
            forwarder.count("refused_path")
            self._answer(404, "not_forwarded", "this path is not forwarded")
            return
        if self.headers.get("Transfer-Encoding"):
            self._answer(411, "length_required", "send the request body with a Content-Length")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_REQUEST_BYTES:
            self._answer(413, "request_too_large", "the request body is too large or its length is invalid")
            return
        body = self.rfile.read(length) if length else b""
        headers = {}
        for name, value in self.headers.items():
            lowered = name.lower()
            if lowered in HOP_BY_HOP or (forwarder.authorization is not None and lowered == "authorization"):
                continue
            headers[name] = value
        if forwarder.authorization is not None:
            headers["Authorization"] = forwarder.authorization
        if body or self.command == "POST":
            headers["Content-Length"] = str(len(body))
        connection = forwarder.connection()
        try:
            try:
                connection.request(self.command, path, body=body or None, headers=headers)
                response = connection.getresponse()
            except custom_endpoint.TLSTrustRefused:
                forwarder.count("tls_trust_refused")
                self._answer(502, "tls_trust_refused",
                             "the upstream did not prove the expected identity under the pinned anchor; "
                             "nothing was sent")
                return
            except (OSError, http.client.HTTPException) as error:
                forwarder.count("transport_failed")
                self._answer(502, "upstream_transport_failed", "the upstream connection failed: "
                             + type(error).__name__)
                return
            forwarder.count("forwarded")
            self._relay(response)
        finally:
            connection.close()

    def _relay(self, response: http.client.HTTPResponse) -> None:
        self.close_connection = True
        self.send_response(response.status, response.reason)
        for name, value in response.getheaders():
            if name.lower() not in HOP_BY_HOP and name.lower() not in RESPONSE_OWN:
                self.send_header(name, value)
        bodiless = response.status in (204, 304) or 100 <= response.status < 200
        if not bodiless:
            self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        if bodiless:
            return
        try:
            while True:
                chunk = response.read1(CHUNK_BYTES)
                if not chunk:
                    break
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
        except (OSError, ValueError, http.client.HTTPException):
            # The upstream or the client broke off: end without the final chunk, so the client sees an
            # incomplete body rather than a complete short one.
            return
        if response.length:
            # The upstream declared more bytes than it sent before closing.
            return
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()
