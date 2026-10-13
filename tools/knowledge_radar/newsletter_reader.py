"""Host-only private mailbox reads; no public URL, send, click or provider write.

The documented R2 REST object interface sits behind NewsletterObjectRead.
Credentials are supplied by the host's existing resolver. Mail is untrusted
data and never controls the origin, account, bucket, command or credential.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
import ipaddress
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import ssl
import sys
from urllib.parse import urlencode, urlsplit, urlunsplit

from .newsletter_intake import (MAXIMUM_RAW, NewsletterObjectRead, NewsletterRefusal,
                               _pairs, inspect_mime)

PREFIX = "newsletter-email/v1/receipts/"
RECEIPT_KEY = re.compile(re.escape(PREFIX) + r"[A-Za-z0-9_-]{1,128}\.json")
RAW_KEY = re.compile(r"newsletter-email/v1/raw/[0-9a-f]{64}")
ORIGIN = "https://api.cloudflare.com/client/v4"
MAXIMUM_LIST = 64 * 1024
MAXIMUM_PRIVATE_TEXT = 16384
MAXIMUM_MANUAL_LINKS = 32
KEY_REFERENCE = "cloudflare-r2-management"


@dataclass(frozen=True)
class NewsletterReaderBinding:
    """Host-selected private bucket and a bounded read session, not authority."""
    account_id: str
    bucket: str
    record_type: str = "newsletter_reader_binding/v1"

    def __post_init__(self):
        if (self.record_type != "newsletter_reader_binding/v1"
                or not isinstance(self.account_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.account_id)
                or not isinstance(self.bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", self.bucket)):
            raise NewsletterRefusal("newsletter_reader_binding_refused")

    @property
    def path(self):
        return "/accounts/" + self.account_id + "/r2/buckets/" + self.bucket + "/objects"


def load_binding(path):
    """Read an owner-only, explicit host file; never a receipt-supplied path."""
    import stat
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        held = os.fstat(fd)
        if (not stat.S_ISREG(held.st_mode) or held.st_nlink != 1 or held.st_uid != os.getuid()
                or held.st_mode & 0o077 or held.st_size > 4096):
            raise NewsletterRefusal("newsletter_reader_private_binding_required")
        body = os.read(fd, 4097)
        if len(body) > 4096:
            raise NewsletterRefusal("newsletter_reader_binding_refused")
        value = json.loads(body, object_pairs_hook=_pairs)
        if not isinstance(value, dict) or set(value) != {"record_type", "account_id", "bucket"}:
            raise NewsletterRefusal("newsletter_reader_binding_refused")
        return NewsletterReaderBinding(**value)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise NewsletterRefusal("newsletter_reader_binding_refused") from None
    finally:
        os.close(fd)


def _request(binding, operation, selection, maximum_bytes):
    """Construct only fixed-origin GETs, with literal validated object keys."""
    if not isinstance(binding, NewsletterReaderBinding) or type(maximum_bytes) is not int:
        raise NewsletterRefusal("newsletter_reader_request_refused")
    if operation == "get":
        if not isinstance(selection, str):
            raise NewsletterRefusal("newsletter_reader_key_refused")
        maximum = 4096 if RECEIPT_KEY.fullmatch(selection) else MAXIMUM_RAW if RAW_KEY.fullmatch(selection) else 0
        if not 1 <= maximum_bytes <= maximum:
            raise NewsletterRefusal("newsletter_reader_key_or_size_refused")
        return ORIGIN + binding.path + "/" + selection
    if operation == "list":
        if (not isinstance(selection, dict) or set(selection) != {"after", "limit"}
                or type(selection["limit"]) is not int or not 1 <= selection["limit"] <= 20
                or not isinstance(selection["after"], str)
                or (selection["after"] and not RECEIPT_KEY.fullmatch(selection["after"]))
                or maximum_bytes != MAXIMUM_LIST):
            raise NewsletterRefusal("newsletter_reader_listing_refused")
        query = {"prefix": PREFIX, "per_page": selection["limit"]}
        if selection["after"]:
            query["start_after"] = selection["after"]
        return ORIGIN + binding.path + "?" + urlencode(query)
    raise NewsletterRefusal("newsletter_reader_operation_refused")


def bounded_get(url, token, maximum_bytes, *, connection_factory=http.client.HTTPSConnection):
    """One bounded request; parent process supplies the hard wall deadline."""
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "api.cloudflare.com"
            or not parsed.path.startswith("/client/v4/accounts/") or parsed.fragment):
        raise NewsletterRefusal("newsletter_reader_origin_refused")
    connection = None
    try:
        # http.client does not consult HTTP_PROXY/HTTPS_PROXY and does not
        # follow redirects. The default context verifies certificate and host.
        connection = connection_factory("api.cloudflare.com", port=443, timeout=10, context=ssl.create_default_context())
        target = parsed.path + ("?" + parsed.query if parsed.query else "")
        connection.request("GET", target, headers={"Authorization": "Bearer " + token,
                           "Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("content-encoding", "identity") != "identity":
            raise NewsletterRefusal("newsletter_reader_provider_refused")
        length = response.getheader("content-length")
        if length is not None and (not length.isdecimal() or int(length) > maximum_bytes):
            raise NewsletterRefusal("newsletter_reader_response_size_refused")
        body = bytearray()
        while True:
            chunk = response.read(min(16384, maximum_bytes + 1 - len(body)))
            if not chunk:
                break
            if len(body) + len(chunk) > maximum_bytes:
                raise NewsletterRefusal("newsletter_reader_response_size_refused")
            body.extend(chunk)
        if length is not None and len(body) != int(length):
            raise NewsletterRefusal("newsletter_reader_response_size_refused")
        return bytes(body)
    except NewsletterRefusal:
        raise
    except Exception:
        # Provider error documents, request objects and token-bearing exception
        # text never cross the transport boundary.
        raise NewsletterRefusal("newsletter_reader_transport_unknown") from None
    finally:
        if connection is not None:
            connection.close()


def network_read(binding, operation, selection, maximum_bytes, token):
    """Secret over stdin only; no ambient proxies or credential environment.

    The known child writes at most the selected byte cap in base64. The
    parent's timeout includes DNS, TLS and slow response streams. No retry.
    """
    _request(binding, operation, selection, maximum_bytes)
    if not isinstance(token, str) or not 1 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise NewsletterRefusal("newsletter_reader_credential_refused")
    payload = {"binding": asdict(binding), "operation": operation, "selection": selection,
               "maximum_bytes": maximum_bytes, "token": token}
    launcher = Path(__file__).resolve().parents[1] / "read_newsletter_email.py"
    try:
        result = subprocess.run([sys.executable, "-I", str(launcher), "--transport"],
                                input=json.dumps(payload).encode(), capture_output=True,
                                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        raise NewsletterRefusal("newsletter_reader_transport_unknown") from None
    if result.returncode or result.stderr or len(result.stdout) > 4 * ((maximum_bytes + 2) // 3) + 256:
        raise NewsletterRefusal("newsletter_reader_transport_unknown")
    try:
        held = json.loads(result.stdout, object_pairs_hook=_pairs)
        if not isinstance(held, dict) or set(held) != {"body_base64"}:
            raise ValueError()
        body = base64.b64decode(held["body_base64"], validate=True)
        if len(body) > maximum_bytes:
            raise ValueError()
        return body
    except (ValueError, TypeError, UnicodeError):
        raise NewsletterRefusal("newsletter_reader_transport_refused") from None


def transport_main():
    """Known subprocess entry, deliberately not a general HTTP proxy."""
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    try:
        payload = json.loads(sys.stdin.buffer.read(16385), object_pairs_hook=_pairs)
        if not isinstance(payload, dict) or set(payload) != {"binding", "operation", "selection", "maximum_bytes", "token"}:
            raise ValueError()
        binding = NewsletterReaderBinding(**payload["binding"])
        url = _request(binding, payload["operation"], payload["selection"], payload["maximum_bytes"])
        token = payload["token"]
        if not isinstance(token, str) or not 1 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError()
        raw = bounded_get(url, token, payload["maximum_bytes"])
        print(json.dumps({"body_base64": base64.b64encode(raw).decode("ascii")}))
        return 0
    except Exception:
        # Do not echo payloads, credentials, provider bodies or exception text.
        return 1


class NewsletterR2Reader:
    """One host-authenticated session: at most three reads and three MiB."""
    def __init__(self, binding, resolve_credential, *, transport=network_read):
        if not isinstance(binding, NewsletterReaderBinding) or not callable(resolve_credential) or not callable(transport):
            raise NewsletterRefusal("newsletter_reader_binding_refused")
        self.binding, self.resolve_credential, self.transport = binding, resolve_credential, transport
        self.reads, self.reserved_bytes, self.held = 0, 0, False

    def _read(self, operation, selection, maximum_bytes):
        _request(self.binding, operation, selection, maximum_bytes)
        if self.held or self.reads >= 3 or self.reserved_bytes + maximum_bytes > 3 * 1024 * 1024:
            raise NewsletterRefusal("newsletter_reader_session_held_or_exhausted")
        self.reads += 1
        self.reserved_bytes += maximum_bytes
        self.held = True
        token = self.resolve_credential(KEY_REFERENCE)
        body = self.transport(self.binding, operation, selection, maximum_bytes, token)
        del token
        if type(body) is not bytes or len(body) > maximum_bytes:
            raise NewsletterRefusal("newsletter_reader_response_size_refused")
        self.held = False
        return body

    def __call__(self, request):
        if not isinstance(request, NewsletterObjectRead) or request.bucket != self.binding.bucket:
            raise NewsletterRefusal("newsletter_reader_bucket_refused")
        return self._read("get", request.key, request.maximum_bytes)

    def list_receipts(self, *, limit=20, after=""):
        body = self._read("list", {"limit": limit, "after": after}, MAXIMUM_LIST)
        try:
            value = json.loads(body, object_pairs_hook=_pairs)
            if not isinstance(value, dict) or value.get("success") is not True or value.get("errors") != []:
                raise ValueError()
            rows, info = value["result"], value.get("result_info", {})
            if not isinstance(rows, list) or len(rows) > limit or not isinstance(info, dict):
                raise ValueError()
            result = []
            for row in rows:
                if (not isinstance(row, dict) or not isinstance(row.get("key"), str)
                        or not RECEIPT_KEY.fullmatch(row["key"]) or type(row.get("size")) is not int
                        or not 1 <= row["size"] <= 4096 or (after and row["key"] <= after)):
                    raise ValueError()
                result.append({"receipt_key": row["key"], "receipt_bytes": row["size"]})
            keys = [row["receipt_key"] for row in result]
            if keys != sorted(set(keys)):
                raise ValueError()
            truncated = info.get("is_truncated")
            if truncated is not None and type(truncated) is not bool:
                raise ValueError()
            return {"record_type": "newsletter_receipt_listing/v1", "receipts": result,
                    "is_truncated": truncated, "next_after": keys[-1] if keys and truncated is not False else None,
                    "content_included": False, "automatic_pagination": False}
        except (KeyError, ValueError, TypeError, UnicodeError, RecursionError):
            self.held = True
            raise NewsletterRefusal("newsletter_reader_listing_refused") from None


def _manual_url(value):
    """Keep private action tokens for human review, never automatic fetching."""
    if not isinstance(value, str) or not 1 <= len(value) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value):
        return None
    try:
        item = urlsplit(value)
        host = item.hostname or ""
        if (item.scheme != "https" or item.username or item.password or item.port not in (None, 443)
                or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host)
                or "." not in host or host.lower().endswith((".local", ".localhost", ".internal"))):
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass
        return urlunsplit(("https", item.netloc, item.path, item.query, item.fragment))
    except ValueError:
        return None


class _PassiveHtml(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a" and len(self.links) < MAXIMUM_MANUAL_LINKS:
            for name, value in attrs:
                if name.lower() == "href":
                    safe = _manual_url(value)
                    if safe:
                        self.links.append(safe)


def private_mail_view(message):
    """Inert, bounded private reading view. HTML is parsed, never rendered.

    This view may contain newsletter confirmation tokens. Do not publish it,
    put it in an agent prompt or treat a link as a verified publisher action.
    """
    inspection = inspect_mime(message.raw)  # shared MIME allocation/depth gate
    parsed = BytesParser(policy=policy.default).parsebytes(message.raw)
    pending, links, texts = [(parsed, True)], [], []
    while pending:
        part, include = pending.pop()
        if part.get_content_disposition() == "attachment" or part.get_filename():
            include = False
        children = part.get_payload()
        if isinstance(children, list):
            if part.get_content_maintype() != "multipart":
                include = False
            pending.extend((child, include) for child in children)
            continue
        if not include or part.get_content_type() not in ("text/plain", "text/html"):
            continue
        raw = part.get_payload(decode=True)
        if not isinstance(raw, bytes):
            continue
        try:
            text = raw.decode(part.get_content_charset() or "utf-8", errors="strict")
        except (LookupError, UnicodeError):
            continue
        if part.get_content_type() == "text/html":
            parser = _PassiveHtml()
            parser.feed(text)
            links.extend(parser.links)
        else:
            texts.append(text)
            for match in re.finditer(r"https://[^\s<>\"']{1,4096}", text):
                candidate = _manual_url(match.group().rstrip(".,);]"))
                if candidate:
                    links.append(candidate)
    return {"record_type": "newsletter_private_mail_view/v1", "delivery_id": message.delivery_id,
            "received_at": message.received_at, "recipient": message.recipient,
            "envelope_sender": message.envelope_sender, "raw_sha256": message.raw_sha256,
            "claimed_subject": inspection["claimed_subject"], "claimed_from": inspection["claimed_from"],
            "plain_text": "\n".join(texts)[:MAXIMUM_PRIVATE_TEXT],
            "manual_links": list(dict.fromkeys(links))[:MAXIMUM_MANUAL_LINKS],
            "warning": "Private source; sender unverified. Links may confirm subscriptions or perform other actions. Review the host and action before opening manually.",
            "sender_authentication": "not_verified", "remote_fetches": 0,
            "html_rendered": False, "automatic_actions": False, "publication_approved": False}
