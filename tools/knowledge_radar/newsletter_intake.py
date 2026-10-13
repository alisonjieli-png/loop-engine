"""Private newsletter bytes and receipts, never public feed observations.

This deterministic intake adapter uses the existing managed-record owner and
content-addressed artifacts. Delivery authentication binds the ingress, not
the sender's claims. Every accepted message remains quarantined. This module
has no network, model, publication, subscription or command-execution adapter.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat

from loop_engine.core.context_artifacts import ContextArtifactStore, ContextArtifactStoreSpec
from .community_intake import public_url
from .community_store import CommunityStore

VERSION = "newsletter_email/v1"
RECIPIENT = "newsletters@agentfeeds.si"
MAXIMUM_RAW = 2 * 1024 * 1024
MAXIMUM_WIRE = 4 * ((MAXIMUM_RAW + 2) // 3) + 4096
MAXIMUM_HEADERS = 64 * 1024
MAXIMUM_PARTS = 32
MAXIMUM_DEPTH = 8
MAXIMUM_PREVIEW = 4096
INGRESS_PATH = "/internal/newsletter-email"
_ADDRESS = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?")
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


class NewsletterRefusal(ValueError):
    """A stable refusal code with no raw message or credential in its text."""


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _time(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise NewsletterRefusal("newsletter_time_invalid")
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        raise NewsletterRefusal("newsletter_time_invalid") from None


@dataclass(frozen=True)
class NewsletterEmail:
    """A passive immutable private-source envelope, not an instruction."""
    delivery_id: str
    recipient: str
    envelope_sender: str
    received_at: str
    raw: bytes
    ingress: str = "local_operator_import/v1"
    record_type: str = VERSION

    def __post_init__(self):
        if self.record_type != VERSION:
            raise NewsletterRefusal("newsletter_version_refused")
        if (not isinstance(self.delivery_id, str) or not _ID.fullmatch(self.delivery_id)
                or not isinstance(self.envelope_sender, str) or not _ADDRESS.fullmatch(self.envelope_sender)
                or self.recipient != RECIPIENT):
            raise NewsletterRefusal("newsletter_envelope_refused")
        if type(self.raw) is not bytes or not 1 <= len(self.raw) <= MAXIMUM_RAW:
            raise NewsletterRefusal("newsletter_raw_size_refused")
        if self.ingress not in ("local_operator_import/v1", "cloudflare_email_worker/v1"):
            raise NewsletterRefusal("newsletter_ingress_refused")
        _time(self.received_at)

    @property
    def raw_sha256(self):
        return _sha(self.raw)

    @property
    def identity(self):
        return "community.email.delivery." + _sha((self.ingress + ":" + self.delivery_id).encode())

    def wire(self):
        return {"record_type": VERSION, "delivery_id": self.delivery_id, "recipient": self.recipient,
                "envelope_sender": self.envelope_sender, "received_at": self.received_at, "ingress": self.ingress,
                "raw_sha256": self.raw_sha256, "raw_base64": base64.b64encode(self.raw).decode("ascii")}


def _pairs(values):
    result = {}
    for name, value in values:
        if name in result:
            raise NewsletterRefusal("newsletter_duplicate_json_field")
        result[name] = value
    return result


def decode_delivery(body: bytes) -> NewsletterEmail:
    if type(body) is not bytes or not 1 <= len(body) <= MAXIMUM_WIRE:
        raise NewsletterRefusal("newsletter_wire_size_refused")
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_pairs)
        if not isinstance(value, dict) or set(value) != {"record_type", "delivery_id", "recipient", "envelope_sender",
                                                       "received_at", "ingress", "raw_sha256", "raw_base64"}:
            raise NewsletterRefusal("newsletter_wire_fields_refused")
        encoded = value.pop("raw_base64")
        if not isinstance(encoded, str) or len(encoded) > 4 * ((MAXIMUM_RAW + 2) // 3):
            raise NewsletterRefusal("newsletter_raw_size_refused")
        raw = base64.b64decode(encoded, validate=True)
        digest = value.pop("raw_sha256")
        if digest != _sha(raw):
            raise NewsletterRefusal("newsletter_raw_digest_mismatch")
        return NewsletterEmail(raw=raw, **value)
    except NewsletterRefusal:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise NewsletterRefusal("newsletter_wire_invalid") from None


def verify_ingress(body: bytes, headers: dict, key: bytes, *, now: int) -> NewsletterEmail:
    """Verify exact signed bytes before interpreting provider metadata.

    The host supplies the trusted key and clock; neither comes from MIME.
    The signature proves which ingress submitted bytes, not DKIM or DMARC.
    Replayed valid envelopes are reconciled by the managed delivery identity.
    """
    if type(key) is not bytes or len(key) < 32 or type(now) is not int:
        raise NewsletterRefusal("newsletter_ingress_binding_required")
    if type(body) is not bytes or len(body) > MAXIMUM_WIRE:
        raise NewsletterRefusal("newsletter_wire_size_refused")
    if not isinstance(headers, dict) or set(headers) != {"x-baltor-intake-timestamp", "x-baltor-intake-signature"}:
        raise NewsletterRefusal("newsletter_signature_headers_refused")
    stamp, signature = headers["x-baltor-intake-timestamp"], headers["x-baltor-intake-signature"]
    if (not isinstance(stamp, str) or not re.fullmatch(r"[0-9]{1,12}", stamp)
            or not isinstance(signature, str) or not re.fullmatch(r"[a-f0-9]{64}", signature)
            or abs(now - int(stamp)) > 300):
        raise NewsletterRefusal("newsletter_signature_time_refused")
    expected = hmac.new(key, stamp.encode() + b"\n" + INGRESS_PATH.encode() + b"\n" + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise NewsletterRefusal("newsletter_signature_refused")
    message = decode_delivery(body)
    if message.ingress != "cloudflare_email_worker/v1" or abs(_time(message.received_at) - int(stamp)) > 300:
        raise NewsletterRefusal("newsletter_provider_binding_refused")
    return message


def inspect_mime(raw: bytes) -> dict:
    """Extract bounded passive text; HTML and attachments remain raw only."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAXIMUM_RAW or b"\x00" in raw:
        raise NewsletterRefusal("newsletter_mime_size_or_encoding_refused")
    split = re.search(br"\r?\n\r?\n", raw)
    if split is None or split.start() > MAXIMUM_HEADERS:
        raise NewsletterRefusal("newsletter_header_size_refused")
    try:
        allocated = 0
        def bounded_message(*args, **kwargs):
            nonlocal allocated
            allocated += 1
            if allocated > MAXIMUM_PARTS:
                raise NewsletterRefusal("newsletter_mime_structure_refused")
            return EmailMessage(*args, **kwargs)
        message = BytesParser(_class=bounded_message, policy=policy.default).parsebytes(raw)
        pending, parts, decoded_size, text, attachments = [(message, 0, True)], 0, 0, [], 0
        reasons = []
        while pending:
            part, depth, read_text = pending.pop()
            parts += 1
            if parts > MAXIMUM_PARTS or depth > MAXIMUM_DEPTH:
                raise NewsletterRefusal("newsletter_mime_structure_refused")
            if part.defects:
                reasons.append("mime_parser_defect")
            children = part.get_payload()
            if isinstance(children, list):
                if len(children) + len(pending) + parts > MAXIMUM_PARTS:
                    raise NewsletterRefusal("newsletter_mime_structure_refused")
                if (part.get_content_maintype() != "multipart"
                        or part.get_content_disposition() == "attachment" or part.get_filename()):
                    read_text = False
                    attachments += 1
                pending.extend((child, depth + 1, read_text) for child in children)
                continue
            if part.get_content_maintype() == "multipart":
                raise NewsletterRefusal("newsletter_mime_structure_refused")
            if not read_text or part.get_content_type() != "text/plain" or part.get_content_disposition() == "attachment" or part.get_filename():
                attachments += 1
                continue
            content = part.get_payload(decode=True)
            if not isinstance(content, bytes):
                raise NewsletterRefusal("newsletter_text_payload_refused")
            decoded_size += len(content)
            if decoded_size > MAXIMUM_RAW:
                raise NewsletterRefusal("newsletter_decoded_size_refused")
            try:
                value = content.decode(part.get_content_charset() or "utf-8", errors="strict")
            except (LookupError, UnicodeError):
                reasons.append("text_encoding_unreadable")
                continue
            text.append(value)
            if part.defects:
                reasons.append("mime_parser_defect")
        preview = "\n".join(text)[:MAXIMUM_PREVIEW]
        links = set()
        for match in re.finditer(r"https://[^\s<>\"']{1,2048}", preview):
            try:
                url = public_url(match.group().rstrip(".,);]"))
                # Email links routinely contain recipient tracking or action
                # tokens. Keep only query-free research references in previews.
                if "?" not in url and len(url) <= 1024:
                    links.add(url)
            except ValueError:
                pass
        return {"record_type": "newsletter_mime_inspection/v1", "mime_parts": parts,
                "nonplain_parts_not_extracted": attachments, "plain_text_preview": preview,
                "preview_truncated": sum(len(value) for value in text) > MAXIMUM_PREVIEW,
                "candidate_public_links": sorted(links)[:10], "findings": sorted(set(reasons)),
                "claimed_from": str(message.get("From", ""))[:512],
                "claimed_subject": str(message.get("Subject", ""))[:512],
                "authentication_headers_present": bool(message.get_all("Authentication-Results", [])),
                "sender_authentication": "not_verified", "content_trust": "untrusted_private_source",
                "remote_fetches": 0, "actions_executed": 0, "publication_approved": False}
    except NewsletterRefusal:
        raise
    except (ValueError, TypeError, RecursionError, IndexError):
        raise NewsletterRefusal("newsletter_mime_invalid") from None


def _private_root(store, digest):
    if not isinstance(store, CommunityStore) or store.writes_allowed is not True:
        raise NewsletterRefusal("newsletter_private_write_grant_required")
    store._safe()
    store.root.mkdir(parents=True, mode=0o700, exist_ok=True)
    held = store.root.stat()
    if held.st_uid != os.getuid() or held.st_mode & 0o077:
        raise NewsletterRefusal("newsletter_private_root_required")
    # This is a trusted, owner-only host directory. Reject pre-existing aliases
    # before delegating immutable byte storage to the existing artifact owner.
    folder = store.root / "newsletter-quarantine"
    paths = (folder, folder / "objects", folder / "objects" / digest[:2], folder / "objects" / digest[:2] / digest)
    if any(path.is_symlink() for path in paths):
        raise NewsletterRefusal("newsletter_artifact_alias_refused")
    return ContextArtifactStore(ContextArtifactStoreSpec(str(store.root), "newsletter-quarantine"))


def quarantine(store: CommunityStore, message: NewsletterEmail, *, ingress_provenance="local_operator_import") -> dict:
    """Commit a bounded private receipt; never queue or approve its contents.

    Cloudflare envelopes require host-verified transport provenance. Local
    imports cannot assert sender authentication. Distinct delivery identities
    share exact raw bytes but retain separate managed receipt records.
    """
    allowed = ("local_operator_import", "signature_verified_ingress", "host_authenticated_private_object_read")
    if (not isinstance(message, NewsletterEmail) or ingress_provenance not in allowed
            or (message.ingress == "cloudflare_email_worker/v1") == (ingress_provenance == "local_operator_import")):
        raise NewsletterRefusal("newsletter_verified_ingress_required")
    inspection = inspect_mime(message.raw)
    # Validate before making directories or storing any bytes.
    artifacts = _private_root(store, message.raw_sha256)
    existing = store.get(message.identity)
    metadata = {key: value for key, value in message.wire().items() if key != "raw_base64"}
    if existing:
        if existing["document"]["kind"] != "email_receipt" or existing["document"]["data"].get("delivery") != metadata:
            raise NewsletterRefusal("newsletter_delivery_identity_conflict")
        from loop_engine.core.context_artifacts import ContextArtifactRef
        artifacts.get(ContextArtifactRef.from_dict(existing["document"]["data"]["raw_artifact"]))
        return {"record_type": "newsletter_quarantine_ack/v1", "record_id": message.identity,
                "record_version": existing["version"], "raw_sha256": message.raw_sha256,
                "delivery_id": message.delivery_id, "disposition": "quarantined", "duplicate": True}
    reference = artifacts.put(message.raw, media_type="message/rfc822", encoding="binary", artifact_kind="private_newsletter_email")
    data = {"record_type": VERSION, "delivery": metadata, "raw_artifact": reference.to_dict(),
            "inspection": inspection, "disposition": "quarantined", "source_semantics": "private_email_not_public_feed",
            "ingress_authentication": ingress_provenance,
            "sender_authentication": "not_verified", "research_admitted": False, "publication_approved": False}
    version = store.put(message.identity, "email_receipt", "newsletter_inbox", "recorded", data)
    return {"record_type": "newsletter_quarantine_ack/v1", "record_id": message.identity,
            "record_version": version, "raw_sha256": message.raw_sha256, "delivery_id": message.delivery_id,
            "disposition": "quarantined", "duplicate": False}


def handle_signed(store, body, headers, key, *, now):
    """Host adapter for the fixed private ingress path, not a public route."""
    message = verify_ingress(body, headers, key, now=now)
    return quarantine(store, message, ingress_provenance="signature_verified_ingress")


@dataclass(frozen=True)
class NewsletterObjectRead:
    """One bounded private object read for a separately authenticated host."""
    bucket: str
    key: str
    maximum_bytes: int


def read_private_receipt(receipt_key, read_object, *, bucket):
    """Validate and read one named Worker receipt without local mutations.

    ``read_object(NewsletterObjectRead)`` must bind its authenticated account
    and bucket, refuse redirects, and enforce the byte bound while streaming.
    It cannot enumerate, write or delete through this interface. The host
    qualifies private bucket access; a bucket name alone proves no permission.
    """
    prefix = "newsletter-email/v1/"
    if (not isinstance(bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket)
            or not callable(read_object) or not isinstance(receipt_key, str)
            or not re.fullmatch(re.escape(prefix) + r"receipts/[A-Za-z0-9_-]{1,128}\.json", receipt_key)):
        raise NewsletterRefusal("newsletter_named_object_binding_refused")
    body = read_object(NewsletterObjectRead(bucket, receipt_key, 4096))
    if type(body) is not bytes or not 1 <= len(body) <= 4096:
        raise NewsletterRefusal("newsletter_receipt_size_refused")
    try:
        value = json.loads(body, object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError):
        raise NewsletterRefusal("newsletter_receipt_invalid") from None
    fields = {"record_type", "delivery_id", "recipient", "envelope_sender", "received_at", "ingress", "raw_sha256",
              "raw_bytes", "raw_key", "source_semantics", "disposition", "sender_authentication", "publication_approved"}
    if (not isinstance(value, dict) or set(value) != fields or value["record_type"] != VERSION
            or value["ingress"] != "cloudflare_email_worker/v1" or value["recipient"] != RECIPIENT
            or not isinstance(value["raw_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["raw_sha256"])
            or value["raw_key"] != prefix + "raw/" + value["raw_sha256"]
            or type(value["raw_bytes"]) is not int or not 1 <= value["raw_bytes"] <= MAXIMUM_RAW
            or not isinstance(value["delivery_id"], str) or not _ID.fullmatch(value["delivery_id"])
            or receipt_key != prefix + "receipts/" + value["delivery_id"] + ".json"
            or value["source_semantics"] != "private_email_not_public_feed" or value["disposition"] != "quarantined"
            or value["sender_authentication"] != "not_verified" or value["publication_approved"] is not False):
        raise NewsletterRefusal("newsletter_receipt_binding_refused")
    # Validate the envelope before a second provider request.
    NewsletterEmail(value["delivery_id"], value["recipient"], value["envelope_sender"], value["received_at"], b"x", value["ingress"])
    raw = read_object(NewsletterObjectRead(bucket, value["raw_key"], value["raw_bytes"]))
    if type(raw) is not bytes or len(raw) != value["raw_bytes"] or _sha(raw) != value["raw_sha256"]:
        raise NewsletterRefusal("newsletter_raw_digest_mismatch")
    return NewsletterEmail(value["delivery_id"], value["recipient"], value["envelope_sender"], value["received_at"], raw, value["ingress"])


def import_private_receipt(store, receipt_key, read_object, *, bucket):
    """Import one exact validated receipt into the existing private store."""
    message = read_private_receipt(receipt_key, read_object, bucket=bucket)
    return quarantine(store, message, ingress_provenance="host_authenticated_private_object_read")


def read_local_mime(path):
    """Read one explicit regular file without following a final symlink/FIFO."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        held = os.fstat(descriptor)
        if not stat.S_ISREG(held.st_mode) or held.st_nlink != 1 or held.st_size > MAXIMUM_RAW:
            raise NewsletterRefusal("newsletter_local_file_refused")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            body = stream.read(MAXIMUM_RAW + 1)
        if len(body) > MAXIMUM_RAW:
            raise NewsletterRefusal("newsletter_raw_size_refused")
        return body
    finally:
        os.close(descriptor)
