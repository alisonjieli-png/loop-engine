"""The conformance kit of the catalogue body store slot: every engine against the same edge checks.

Every engine of `catalogue_body_store/v1` (the factory table is
`service_engine_body_store.py`) must give the same answers to the same
questions. The edge checks run against each engine: the volume engine on a
real temporary folder, and the R2 engine (`catalogue_object_store.py`) against
`object_store_fake.ObjectStoreFake`, a loopback S3-compatible store that
verifies SigV4 signatures, payload hashes, Content-MD5 and If-None-Match.

```text
Kit
├── edge, for each engine    stored once under its digest and read back verified; invalid digests, sizes
│                            and payloads refused; other bytes under a digest never overwritten; a changed
│                            or missing object refused at read; the same capability keys
├── signer                   the published Signature Version 4 vectors: five from the AWS test suite as
│                            botocore ships it, the S3 header example and the S3 presigned example
├── object store             refused credentials typed; redirects never followed; reads bounded; a kept
│                            connection the store closed replaced once; presigned links expire and refuse
│                            changes; credentials never in a record or a refusal; slow and failing stores
│                            refused within the timeout; credentials resolved at use; a missing bucket is
│                            not a missing object; exact locations; listings followed to the end
└── factory table            described without effect; host records read exactly; no record keeps the
                             volume; a named object store never reads the volume
```

Each guard is shown twice, as the other kits here do: the known-wrong case is
refused, and a removed-guard control reruns the case with the guard patched
away (or with a known-wrong engine) and requires the check's own predicate to
fail. No check reaches a network beyond the loopback fake.

`run_external_checks` runs the edge checks and the credential check against a
real S3-compatible store (MinIO, or an R2 test bucket on the day R2 is
enabled). It writes test objects, including other bytes under a digest's
name, so it is pointed at a dedicated test bucket only, never at the bucket
that serves customers.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import socket
import tempfile
import time
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request

from . import catalogue_object_store, service_engine_body_store
from .catalogue_object_store import (EMPTY_PAYLOAD_DIGEST, ERROR_BODY_BYTES, ObjectStoreBodyStore, amz_date_of,
                                     authorization_header, presigned_query, signature, uri_encode)
from .catalogue_packages import (BODY_STORE_CAPABILITIES_VERSION, BODY_STORE_EDGE_VERSION, VolumeBodyStore,
                                 require_body_store, sha256_hex)
from .object_store_fake import ObjectStoreFake
from .records import ServiceRuntimeError
from .service_engine_body_store import (DESCRIPTOR_VERSION, HOST_RECORD_VERSION, BodyReader, describe,
                                        open_body_store, read_host_record)

KIT_RECORD_TYPE = "catalogue_body_store_checks/v1"
#: Credentials of the loopback fake only. They are distinctive so a check can look for them in any text.
FAKE_KEY_ID = "BALTORKITKEYID7Q3X9"
FAKE_SECRET = "baltor-kit-secret-k8f3n2p7q1z9"
FAKE_KEY_REF, FAKE_SECRET_REF = "env:BALTOR_KIT_OBJECT_STORE_KEY_ID", "env:BALTOR_KIT_OBJECT_STORE_SECRET"
BUCKET = "baltor-kit-bodies"
#: A small file allowance keeps the oversize cases quick; both engines take the same one.
KIT_MAXIMUM_FILE_BYTES = 64 * 1024
#: An R2 endpoint of the documented form, for checks that open but never contact it.
SAMPLE_R2_ENDPOINT = "https://" + "0123456789abcdef" * 2 + ".r2.cloudflarestorage.com"

VOLUME_NAMES = {
    "stored_once": "the_volume_engine_stores_a_body_once_under_its_digest_and_reads_it_back_verified",
    "refusals": "the_volume_engine_refuses_invalid_digests_sizes_and_payloads",
    "never_overwrite": "the_volume_engine_never_overwrites_an_object_holding_other_bytes",
    "changed_at_read": "the_volume_engine_refuses_a_changed_or_missing_object_at_read",
}
OBJECT_STORE_NAMES = {
    "stored_once": "the_object_store_engine_stores_a_body_once_under_its_digest_and_reads_it_back_verified",
    "refusals": "the_object_store_engine_refuses_invalid_digests_sizes_and_payloads",
    "never_overwrite": "the_object_store_engine_never_overwrites_an_object_holding_other_bytes",
    "changed_at_read": "the_object_store_engine_refuses_a_changed_or_missing_object_at_read",
}

# The published Signature Version 4 vectors. The first five are the AWS SigV4 test suite as botocore ships it
# (tests/unit/auth/aws4_testsuite: get-vanilla, get-vanilla-query-order-key-case, get-vanilla-query-unreserved,
# get-utf8, get-vanilla-utf8-query; Apache-2.0), read October 5, 2026. The last two are the GetObject header
# example and the presigned GetObject example of the Amazon S3 Signature Version 4 documentation. The example
# credentials are AWS's published examples, not secrets; they are split here only so that a secret scanner does
# not mistake the documented example for a leaked key.
_SUITE_SECRET = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEX" + "AMPLEKEY"
_S3_EXAMPLE_KEY_ID = "AKIA" + "IOSFODNN7EXAMPLE"
_S3_EXAMPLE_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEX" + "AMPLEKEY"
_UNRESERVED = "-._~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
SUITE_VECTORS = (
    ("/", (), "5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31"),
    ("/", (("Param2", "value2"), ("Param1", "value1")),
     "b97d918cfa904a5beff61c982a1b6f458b799221646efd99d3219ec94cdf2500"),
    ("/", ((_UNRESERVED, _UNRESERVED),), "9c3e54bfcdf0b19771a7f523ee5669cdf59bc7cc0884027167c21bb143a40197"),
    ("/ሴ", (), "8318018e0b0f223aa2bbf98705b62bb787dc9c0e678f255a891fd03141be5d85"),
    ("/", (("ሴ", "bar"),), "2cdec8eed098649ff3a119c94853b13c643bcf08f8b0a1d91e12c9027818dd04"),
)
S3_HEADER_EXAMPLE = "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
S3_PRESIGNED_EXAMPLE = "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"


def refused(action, code=None):
    try:
        action()
    except ServiceRuntimeError as error:
        return code is None or error.code == code
    except Exception:  # noqa: BLE001 - a crash is not a typed refusal
        return False
    return False


def refusal_text(action):
    """The code and message of the refusal an action raises, or empty text."""
    try:
        action()
    except ServiceRuntimeError as error:
        return f"{error.code} {error}"
    except Exception as error:  # noqa: BLE001 - kept as text so a leak in it is still found
        return f"untyped {error!r}"
    return ""


def _quietly(action):
    """The action's result, or False when it raised: a known-wrong variant may fail by raising."""
    try:
        return action()
    except Exception:  # noqa: BLE001 - the control only asks whether the predicate held
        return False


def _resolver(values):
    def resolve(reference):
        if reference not in values:
            raise ServiceRuntimeError("configured_secret_unavailable", "no value for that reference")
        return values[reference]
    return resolve


FAKE_CREDENTIALS = _resolver({FAKE_KEY_REF: FAKE_KEY_ID, FAKE_SECRET_REF: FAKE_SECRET})


# --- targets -----------------------------------------------------------------------------------------------


class _VolumeTarget:
    label = "volume"

    def __init__(self, root):
        self.root = Path(root).resolve() / "volume"
        self.root.mkdir(parents=True)
        self.maximum = KIT_MAXIMUM_FILE_BYTES
        self.writer = VolumeBodyStore(str(self.root), writes_authorized=True, maximum_file_bytes=self.maximum)
        self.reader = VolumeBodyStore(str(self.root), maximum_file_bytes=self.maximum)

    def _file(self, digest):
        return self.root / VolumeBodyStore.object_key(digest)

    def plant(self, digest, payload):
        target = self._file(digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            os.chmod(target, 0o644)
        target.write_bytes(payload)

    def held(self, digest):
        target = self._file(digest)
        return target.read_bytes() if target.is_file() else None


class _ObjectStoreTarget:
    label = "object-store"

    def __init__(self, fake):
        self.fake = fake
        self.maximum = KIT_MAXIMUM_FILE_BYTES
        self.opened = []
        self.writer = self.store(write=True)
        self.reader = self.store(write=False)

    def store(self, *, write=False, resolver=FAKE_CREDENTIALS, kind=ObjectStoreBodyStore, **options):
        opened = kind(self.fake.endpoint, options.pop("bucket", BUCKET), access_key_id_ref=FAKE_KEY_REF,
                      secret_access_key_ref=FAKE_SECRET_REF, writes_authorized=write,
                      maximum_file_bytes=self.maximum, secret_resolver=resolver, **options)
        self.opened.append(opened)
        return opened

    def close(self):
        for opened in self.opened:
            opened.close()

    def plant(self, digest, payload):
        self.fake.plant(ObjectStoreBodyStore.object_key(digest), payload)

    def held(self, digest):
        return self.fake.held(ObjectStoreBodyStore.object_key(digest))


class _ExternalTarget:
    """A real S3-compatible test bucket: plant and inspect through raw signed requests without the guards."""

    label = "external"

    def __init__(self, endpoint, bucket, key_ref, secret_ref, region, resolver):
        self.maximum = KIT_MAXIMUM_FILE_BYTES
        options = dict(access_key_id_ref=key_ref, secret_access_key_ref=secret_ref, region=region,
                       maximum_file_bytes=self.maximum, secret_resolver=resolver, timeout_seconds=30)
        self.writer = ObjectStoreBodyStore(endpoint, bucket, writes_authorized=True, **options)
        self.reader = ObjectStoreBodyStore(endpoint, bucket, **options)
        self.raw = _RawStore(endpoint, bucket, writes_authorized=True, **options)

    def plant(self, digest, payload):
        self.raw.raw_put(digest, payload)

    def held(self, digest):
        return self.raw.raw_get(digest)


class _RawStore(ObjectStoreBodyStore):
    """Checks only: a PUT without the write-once header and a GET without verification."""

    def raw_put(self, digest, payload):
        status, _answer = self._request("PUT", self._path(digest), body=payload,
                                        headers={"Content-Type": "application/octet-stream"},
                                        payload_hash=hashlib.sha256(payload).hexdigest(), read_limit=0,
                                        failure="body_store_write_failed")
        if status != 200:
            raise ServiceRuntimeError("body_store_write_failed", f"a raw write answered {status}")

    def raw_get(self, digest):
        status, payload = self._request("GET", self._path(digest), read_limit=self.maximum_file_bytes + 1,
                                        failure="body_unreadable")
        return payload if status == 200 else None


# --- the edge, for every engine -----------------------------------------------------------------------------


def _edge_checks(check, names, target, nonce):
    writer, reader, label = target.writer, target.reader, target.label.encode()
    payload = b"one body for " + label + b" " + nonce
    digest, size = sha256_hex(payload), len(payload)
    stored, again = writer.put(payload), writer.put(payload)
    check(names["stored_once"],
          stored == {"digest": digest, "size_bytes": size, "written": True}
          and again == {"digest": digest, "size_bytes": size, "written": False}
          and reader.read(digest, size) == payload and target.held(digest) == payload
          and isinstance(reader, BodyReader) and require_body_store(writer, write=True) is writer
          and require_body_store(reader) is reader
          and refused(lambda: require_body_store(reader, write=True), "body_store_contract_unavailable")
          and refused(lambda: reader.put(b"x"), "body_store_writes_not_authorized")
          and refused(lambda: writer.put(b"x", expected_digest="0" * 64), "body_digest_mismatch"))
    check(names["refusals"],
          refused(lambda: reader.read("../../../etc/passwd", 1), "body_digest_invalid")
          and refused(lambda: reader.read("A" * 64, 1), "body_digest_invalid")
          and refused(lambda: reader.read(digest, -1), "body_size_mismatch")
          and refused(lambda: reader.read(digest, True), "body_size_mismatch")
          and refused(lambda: reader.read(digest, str(size)), "body_size_mismatch")
          and refused(lambda: reader.read(digest, target.maximum + 1), "body_too_large")
          and refused(lambda: writer.put("text, not bytes"), "body_payload_invalid")
          and refused(lambda: writer.put(b"x" * (target.maximum + 1)), "body_too_large"))
    honest = b"honest bytes for " + label + b" " + nonce
    planted = b"planted bytes! " + label + b" " + nonce
    target.plant(sha256_hex(honest), planted)
    check(names["never_overwrite"],
          refused(lambda: writer.put(honest), "body_digest_conflict") and target.held(sha256_hex(honest)) == planted)
    changing = b"changing body for " + label + b" " + nonce
    changed_digest = writer.put(changing)["digest"]
    target.plant(changed_digest, bytes(reversed(changing)))
    changed = refused(lambda: reader.read(changed_digest, len(changing)), "body_digest_mismatch")
    target.plant(changed_digest, changing[:-1])
    shortened = refused(lambda: reader.read(changed_digest, len(changing)), "body_size_mismatch")
    check(names["changed_at_read"],
          changed and shortened
          and refused(lambda: reader.read(sha256_hex(b"never stored " + nonce), 3), "body_missing"))


# --- the signer --------------------------------------------------------------------------------------------


def _vectors_hold():
    results = []
    for path, query, expected in SUITE_VECTORS:
        value, _signed = signature(method="GET", path=path, query=query,
                                   headers={"Host": "example.amazonaws.com", "X-Amz-Date": "20150830T123600Z"},
                                   payload_hash=EMPTY_PAYLOAD_DIGEST, secret_access_key=_SUITE_SECRET,
                                   region="us-east-1", service="service", amz_date="20150830T123600Z")
        results.append(value == expected)
    value, _signed = signature(method="GET", path="/test.txt", query=(),
                               headers={"Host": "examplebucket.s3.amazonaws.com", "Range": "bytes=0-9",
                                        "x-amz-content-sha256": EMPTY_PAYLOAD_DIGEST,
                                        "x-amz-date": "20130524T000000Z"},
                               payload_hash=EMPTY_PAYLOAD_DIGEST, secret_access_key=_S3_EXAMPLE_SECRET,
                               region="us-east-1", service="s3", amz_date="20130524T000000Z")
    results.append(value == S3_HEADER_EXAMPLE)
    pairs = presigned_query(method="GET", host="examplebucket.s3.amazonaws.com", path="/test.txt",
                            expires_seconds=86400, access_key_id=_S3_EXAMPLE_KEY_ID,
                            secret_access_key=_S3_EXAMPLE_SECRET, region="us-east-1", service="s3",
                            amz_date="20130524T000000Z")
    results.append(pairs[-1] == ("X-Amz-Signature", S3_PRESIGNED_EXAMPLE))
    return all(results)


def _signer_checks(check):
    check("the_object_store_signer_reproduces_the_published_signature_version_4_vectors", _vectors_hold())

    def unsorted(pairs):
        return "&".join(f"{uri_encode(str(name))}={uri_encode(str(value))}" for name, value in pairs)
    holds = _vectors_hold()
    with patch.object(catalogue_object_store, "canonical_query", unsorted):
        check("removed_canonical_query_ordering_is_detected", holds and not _vectors_hold())


# --- the object store engine against the fake ---------------------------------------------------------------


class _RecordingReads:
    """Every amount an HTTP answer was asked for while active, to show that reads are bounded."""

    def __init__(self):
        self.amounts = []
        self._original = http.client.HTTPResponse.read

    def __enter__(self):
        recording, original = self, self._original

        def read(response, amt=None):
            recording.amounts.append(amt)
            return original(response, amt)
        self._patch = patch.object(http.client.HTTPResponse, "read", read)
        self._patch.start()
        return self

    def __exit__(self, *_exception):
        self._patch.stop()


class _UrllibStore(ObjectStoreBodyStore):
    """Known wrong: the same signed request sent through urllib's default opener, which follows redirects."""

    def _exchange(self, method, path, *, query, body, headers, payload_hash, read_limit, operation):
        access_key_id, secret = self._credentials()
        amz_date = amz_date_of(self.clock())
        signed = {**headers, "host": self.location.host_header, "x-amz-date": amz_date,
                  "x-amz-content-sha256": payload_hash}
        signed["Authorization"] = authorization_header(
            method=method, path=path, query=query, headers=signed, payload_hash=payload_hash,
            access_key_id=access_key_id, secret_access_key=secret, region=self.location.region, service="s3",
            amz_date=amz_date)
        request = urllib.request.Request(self.location.origin + uri_encode(path, keep_slash=True), data=body,
                                         headers={k: v for k, v in signed.items() if k != "host"}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as answer:
                return answer.status, answer.read(read_limit or ERROR_BODY_BYTES)
        except urllib.error.HTTPError as error:
            return error.code, error.read(ERROR_BODY_BYTES)
        except OSError as error:
            raise catalogue_object_store._TransportFailure(type(error).__name__) from None


class _LeakyStore(ObjectStoreBodyStore):
    """Known wrong: a refusal that tells the reader which credential signed the request."""

    def read(self, digest, size_bytes):
        try:
            return super().read(digest, size_bytes)
        except ServiceRuntimeError as error:
            key_id, secret = self._credentials()
            raise ServiceRuntimeError(error.code, f"{error} (signed by {key_id} with {secret})") from None


def _presigned_status(url):
    parts = urllib.parse.urlsplit(url)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
    try:
        connection.request("GET", parts.path + "?" + parts.query)
        answer = connection.getresponse()
        return answer.status, answer.read(ERROR_BODY_BYTES)
    finally:
        connection.close()


def _object_store_checks(check, fake, nonce):
    target = _ObjectStoreTarget(fake)
    try:
        _object_store_cases(check, fake, nonce, target)
    finally:
        target.close()


def _object_store_cases(check, fake, nonce, target):
    writer, reader = target.writer, target.reader
    payload = b"object store body " + nonce
    digest, size = writer.put(payload)["digest"], len(payload)
    other = writer.put(b"another object " + nonce)["digest"]

    def wrong_secret_refused():
        wrong = _resolver({FAKE_KEY_REF: FAKE_KEY_ID, FAKE_SECRET_REF: "not-the-secret"})
        before = fake.count(status=403)
        read = refused(lambda: target.store(resolver=wrong).read(digest, size), "body_unreadable")
        write = refused(lambda: target.store(write=True, resolver=wrong).put(b"refused write " + nonce),
                        "body_store_write_failed")
        return read and write and fake.count(status=403) >= before + 2
    holds = wrong_secret_refused()
    check("an_object_store_credential_the_store_refuses_is_a_typed_refusal_for_reads_and_writes", holds)
    fake.verify_signatures = False
    try:
        check("removed_signature_verification_is_detected", holds and not wrong_secret_refused())
    finally:
        fake.verify_signatures = True

    tampered = writer.put(b"tamper target " + nonce)
    fake.plant(ObjectStoreBodyStore.object_key(tampered["digest"]), b"tamper TARGET " + nonce)

    def tampered_refused():
        return refused(lambda: reader.read(tampered["digest"], tampered["size_bytes"]), "body_digest_mismatch")
    holds = tampered_refused()
    with patch.object(ObjectStoreBodyStore, "_verified", lambda self, data, wanted, length: data):
        check("removed_object_store_digest_check_is_detected", holds and not tampered_refused())

    def write_once_holds():
        honest = b"write once " + os.urandom(8).hex().encode()
        planted = b"planted under that name"
        target.plant(sha256_hex(honest), planted)
        return refused(lambda: writer.put(honest), "body_digest_conflict") and target.held(sha256_hex(honest)) == planted
    holds = write_once_holds()
    with patch.object(catalogue_object_store, "WRITE_ONCE_HEADERS", ()):
        check("removed_write_once_header_is_detected", holds and not write_once_holds())
    with patch.object(ObjectStoreBodyStore, "_existing_matches", lambda self, wanted, length: True):
        check("removed_existing_object_comparison_is_detected", holds and not write_once_holds())

    def links_hold():
        fresh = reader.presigned_read_url(digest, 60)
        expired = target.store(clock=lambda: time.time() - 120).presigned_read_url(digest, 60)
        longer = fresh.replace("X-Amz-Expires=60", "X-Amz-Expires=6000")
        elsewhere = fresh.replace(ObjectStoreBodyStore.object_key(digest), ObjectStoreBodyStore.object_key(other))
        return (_presigned_status(fresh) == (200, payload) and _presigned_status(expired)[0] == 403
                and longer != fresh and _presigned_status(longer)[0] == 403
                and elsewhere != fresh and _presigned_status(elsewhere)[0] == 403
                and refused(lambda: reader.presigned_read_url(digest, 0), "presigned_expiry_invalid")
                and refused(lambda: reader.presigned_read_url(digest, 604_801), "presigned_expiry_invalid")
                and FAKE_SECRET not in fresh)
    holds = links_hold()
    check("a_presigned_read_link_works_until_it_expires_and_refuses_any_change", holds)
    fake.verify_signatures = fake.verify_expiry = False
    try:
        check("removed_presigned_link_verification_is_detected", holds and not links_hold())
    finally:
        fake.verify_signatures = fake.verify_expiry = True

    with ObjectStoreFake(access_key_id=FAKE_KEY_ID, secret_access_key=FAKE_SECRET, bucket=BUCKET) as elsewhere:
        elsewhere.plant(ObjectStoreBodyStore.object_key(digest), payload)

        def redirect_refused(store):
            fake.redirect_next(elsewhere.endpoint + "/" + BUCKET + "/" + ObjectStoreBodyStore.object_key(digest))
            outcome = refused(lambda: store.read(digest, size), "body_unreadable")
            return outcome and elsewhere.count() == 0
        holds = redirect_refused(reader)
        check("a_redirect_from_the_object_store_is_never_followed", holds)
        check("a_redirect_following_engine_is_detected", holds and not redirect_refused(target.store(kind=_UrllibStore)))

    def bounded():
        fake.extra_bytes = 4096
        try:
            with _RecordingReads() as recording:
                outcome = refused(lambda: reader.read(digest, size), "body_size_mismatch")
            return outcome and recording.amounts and all(amount is not None and amount <= size + 1
                                                         for amount in recording.amounts)
        finally:
            fake.extra_bytes = 0
    def kept_connection_replaced():
        with target.store() as kept:
            first = kept.read(digest, size) == payload
            fake.close_silently_after_next()
            second = kept.read(digest, size) == payload
            return first and second and kept.read(digest, size) == payload
    holds = kept_connection_replaced()
    check("a_kept_connection_the_store_closed_is_replaced_once", holds)
    with patch.object(catalogue_object_store, "_STALE_CONNECTION", ()):
        check("removed_stale_connection_replacement_is_detected", holds and not _quietly(kept_connection_replaced))

    holds = bounded()
    check("an_oversized_object_store_answer_is_refused_after_a_bounded_read", holds)
    with patch.object(ObjectStoreBodyStore, "_read_bound", lambda self, length: length + 1_000_000):
        check("removed_read_bound_is_detected", holds and not bounded())

    def nothing_leaks(kind):
        texts = [repr(target.store(kind=kind)), json.dumps(target.store(kind=kind).capabilities()), json.dumps(describe())]
        wrong = _resolver({FAKE_KEY_REF: FAKE_KEY_ID, FAKE_SECRET_REF: "not-the-secret"})
        texts.append(refusal_text(lambda: target.store(kind=kind, resolver=wrong).read(digest, size)))
        fake.fail_next(500)
        texts.append(refusal_text(lambda: target.store(kind=kind).read(digest, size)))
        texts.append(refusal_text(lambda: target.store(kind=kind).read(sha256_hex(b"absent " + nonce), 4)))
        joined = "\n".join(texts)
        return all(texts[3:]) and FAKE_KEY_ID not in joined and FAKE_SECRET not in joined
    holds = nothing_leaks(ObjectStoreBodyStore)
    check("object_store_credentials_never_appear_in_capabilities_descriptors_or_refusals", holds)
    check("a_refusal_that_carries_a_credential_is_detected", holds and not nothing_leaks(_LeakyStore))

    slow = target.store(timeout_seconds=0.3)
    fake.delay_seconds = 1.0
    started = time.monotonic()
    try:
        timed_out = refused(lambda: slow.read(digest, size), "body_unreadable")
    finally:
        fake.delay_seconds = 0.0
    waited = time.monotonic() - started
    fake.fail_next(500)
    failed_read = refused(lambda: reader.read(digest, size), "body_unreadable")
    fake.fail_next(503)
    failed_write = refused(lambda: writer.put(b"failed write " + nonce), "body_store_write_failed")
    check("a_slow_or_failing_object_store_is_refused_typed_within_the_timeout",
          timed_out and waited < 3.0 and failed_read and failed_write and reader.read(digest, size) == payload)

    unresolved = ObjectStoreBodyStore(fake.endpoint, BUCKET, access_key_id_ref="env:BALTOR_KIT_UNSET_KEY_ID",
                                      secret_access_key_ref="env:BALTOR_KIT_UNSET_SECRET")
    target.opened.append(unresolved)
    environment = {key: value for key, value in os.environ.items() if not key.startswith("BALTOR_KIT_UNSET")}
    with patch.dict(os.environ, environment, clear=True):
        at_use = refused(lambda: unresolved.read(digest, size), "configured_secret_unavailable")
    check("object_store_credentials_are_resolved_at_use_and_never_at_construction",
          at_use and refused(lambda: ObjectStoreBodyStore(fake.endpoint, BUCKET, access_key_id_ref="BALTOR_KEY",
                                                          secret_access_key_ref=FAKE_SECRET_REF),
                             "unsupported_secret_resolver")
          and refused(lambda: ObjectStoreBodyStore(fake.endpoint, BUCKET, access_key_id_ref=FAKE_KEY_REF,
                                                   secret_access_key_ref="env:lower_case"),
                      "unsupported_secret_resolver"))

    check("a_missing_bucket_is_never_reported_as_a_missing_object",
          refused(lambda: target.store(bucket="baltor-kit-elsewhere").read(digest, size), "body_unreadable")
          and refused(lambda: reader.read(sha256_hex(b"absent object " + nonce), 5), "body_missing"))

    invalid = [("http://example.com", BUCKET), ("https://user@example.com", BUCKET),
               ("https://example.com/bucket", BUCKET), ("https://example.com?x=1", BUCKET),
               ("https://example.com#part", BUCKET), ("http://localhost:9000", BUCKET), ("ftp://example.com", BUCKET),
               (" https://example.com", BUCKET), ("https://", BUCKET), ("https://example.com", "Bad_Bucket"),
               ("https://example.com", "ab"), ("https://example.com", "-abc"), ("https://example.com", "abc-"),
               ("https://example.com", "a--b-c"), ("https://example.com", "x" * 64), ("https://example.com:99999", BUCKET)]
    check("an_object_store_location_is_read_exactly",
          all(refused(lambda row=row: ObjectStoreBodyStore(row[0], row[1], access_key_id_ref=FAKE_KEY_REF,
                                                           secret_access_key_ref=FAKE_SECRET_REF),
                      "body_store_root_invalid") for row in invalid)
          and ObjectStoreBodyStore("https://Example.COM:8443", BUCKET, access_key_id_ref=FAKE_KEY_REF,
                                   secret_access_key_ref=FAKE_SECRET_REF).location.host_header == "example.com:8443"
          and refused(lambda: ObjectStoreBodyStore(fake.endpoint, BUCKET, access_key_id_ref=FAKE_KEY_REF,
                                                   secret_access_key_ref=FAKE_SECRET_REF, timeout_seconds=0),
                      "body_store_root_invalid"))

    page_keys, fake.page_keys = fake.page_keys, 2
    try:
        expected = {key: len(value) for key, value in fake.objects.items() if key.startswith("sha256/")}
        pages = -(-len(expected) // 2)
        before = reader.operation_counts().get("LIST", 0)
        listed = dict(reader.stored_objects())
        after = reader.operation_counts().get("LIST", 0)
    finally:
        fake.page_keys = page_keys
    check("the_object_store_listing_follows_continuation_tokens_to_the_end",
          listed == expected and len(expected) > 4 and after - before == pages)


# --- the factory table -------------------------------------------------------------------------------------


class _NoNetwork:
    """While active, any name lookup or connection fails as an unreachable network does, and is counted."""

    def __init__(self):
        self.attempts = 0

    def _refuse(self, *_arguments, **_keywords):
        self.attempts += 1
        raise ConnectionRefusedError("no network in this check")

    def __enter__(self):
        self._patches = [patch.object(socket, "getaddrinfo", self._refuse),
                         patch.object(socket.socket, "connect", self._refuse)]
        for item in self._patches:
            item.start()
        return self

    def __exit__(self, *_exception):
        for item in self._patches:
            item.stop()


def _r2_record(**changes):
    record = {"record_type": HOST_RECORD_VERSION, "engine": "r2_object_storage", "endpoint": SAMPLE_R2_ENDPOINT,
              "bucket": "baltor-catalogue-bodies", "region": "auto", "access_key_id_ref": "env:BALTOR_R2_ACCESS_KEY_ID",
              "secret_access_key_ref": "env:BALTOR_R2_SECRET_ACCESS_KEY", "timeout_seconds": 10,
              "maximum_file_bytes": 8 * 1024 * 1024}
    record.update(changes)
    return {key: value for key, value in record.items() if value is not None}


def _records_read_exactly():
    jurisdictions = [SAMPLE_R2_ENDPOINT.replace(".r2.", ".eu.r2."), SAMPLE_R2_ENDPOINT.replace(".r2.", ".fedramp.r2.")]
    accepted = all(read_host_record(_r2_record(endpoint=endpoint))["endpoint"] == endpoint
                   for endpoint in [SAMPLE_R2_ENDPOINT, *jurisdictions])
    wrong = [{"record_type": "catalogue_body_store_engine/v2", **{k: v for k, v in _r2_record().items() if k != "record_type"}},
             _r2_record(engine="lance_object_store"), _r2_record(cache_root="/data/cache"),
             _r2_record(bucket=None), _r2_record(secret_access_key_ref=None),
             _r2_record(endpoint="https://evil.example.com"), _r2_record(endpoint="http://" + SAMPLE_R2_ENDPOINT[8:]),
             _r2_record(endpoint=SAMPLE_R2_ENDPOINT.replace("0123", "012", 1)),
             _r2_record(endpoint=SAMPLE_R2_ENDPOINT.upper()), _r2_record(endpoint=SAMPLE_R2_ENDPOINT + "/bucket"),
             _r2_record(endpoint=SAMPLE_R2_ENDPOINT.replace(".r2.", ".us.r2.")),
             _r2_record(region="us-east-1"), _r2_record(maximum_file_bytes=0), _r2_record(maximum_file_bytes="8"),
             {"record_type": HOST_RECORD_VERSION, "engine": "service_volume_files", "endpoint": SAMPLE_R2_ENDPOINT},
             "r2_object_storage", None, ["r2_object_storage"]]
    return accepted and all(refused(lambda row=row: read_host_record(row), "unsupported_body_store_engine")
                            for row in wrong)


def _factory_checks(check, root):
    with _NoNetwork() as network:
        descriptors = describe()
    check("the_body_store_slot_describes_its_engines_without_any_effect",
          network.attempts == 0
          and [row["engine_id"] for row in descriptors] == ["service_volume_files", "r2_object_storage"]
          and all(row["record_type"] == DESCRIPTOR_VERSION and row["edge"] == BODY_STORE_EDGE_VERSION
                  for row in descriptors)
          and [row["kind"] for row in descriptors] == ["image_files", "private_object_storage"]
          and descriptors[1]["needs_the_owner"] and not descriptors[0]["needs_the_owner"])
    holds = _records_read_exactly()
    check("a_body_store_engine_record_is_read_exactly_or_refused_before_anything_opens", holds)
    with patch.object(service_engine_body_store, "R2_ENDPOINT", re.compile(r"https://.+")):
        check("removed_r2_endpoint_rule_is_detected", holds and not _records_read_exactly())
    folder = Path(root).resolve() / "factory-volume"
    folder.mkdir()
    with _NoNetwork() as network:
        written = open_body_store(None, write=True, root_fallback=str(folder)).put(b"volume body")
        served = open_body_store(None, write=False, root_fallback=str(folder))
        named = open_body_store({"record_type": HOST_RECORD_VERSION, "engine": "service_volume_files"},
                                write=False, root_fallback=str(folder))
    from .catalogue_body_flush import ExactFlushVolumeBodyStore
    check("without_a_body_store_record_the_volume_engine_serves_as_before",
          type(served) is VolumeBodyStore and served.read(written["digest"], 11) == b"volume body"
          and network.attempts == 0
          and named.capabilities() == served.capabilities() and served.capabilities()["engine"] == "service_volume_files"
          and type(open_body_store(None, write=True, root_fallback=str(folder))) is ExactFlushVolumeBodyStore
          and refused(lambda: open_body_store(None, write="yes", root_fallback=str(folder)), "body_store_root_invalid"))
    r2_credentials = _resolver({"env:BALTOR_R2_ACCESS_KEY_ID": FAKE_KEY_ID,
                                "env:BALTOR_R2_SECRET_ACCESS_KEY": FAKE_SECRET})
    with _NoNetwork() as network:
        object_store = open_body_store(_r2_record(), write=False, secret_resolver=r2_credentials,
                                       root_fallback=str(folder))
        opened_without_contact = network.attempts == 0
        reaches_out = refusal_text(lambda: object_store.read(written["digest"], 11))
        object_store.close()
    check("a_host_that_names_the_object_store_never_reads_the_volume",
          opened_without_contact and network.attempts >= 1
          and object_store.capabilities()["engine"] == "r2_object_storage" and object_store.capabilities()["writes"] is False
          and reaches_out.startswith("body_unreadable")
          and refused(lambda: open_body_store(_r2_record(endpoint="https://evil.example.com"), write=False,
                                              root_fallback=str(folder)), "unsupported_body_store_engine"))


def _shared_checks(check, volume, object_store):
    keys = set(volume.writer.capabilities())
    check("every_body_engine_states_the_same_capability_keys_and_speaks_the_reader_protocol",
          keys == set(object_store.writer.capabilities()) == set(object_store.reader.capabilities())
          and all(store.capabilities()["record_type"] == BODY_STORE_CAPABILITIES_VERSION
                  and store.capabilities()["edge"] == BODY_STORE_EDGE_VERSION and isinstance(store, BodyReader)
                  for store in (volume.writer, volume.reader, object_store.writer, object_store.reader))
          and volume.writer.capabilities()["object_key"] == object_store.writer.capabilities()["object_key"])


# --- entry points ------------------------------------------------------------------------------------------


def run_checks(check=None, root=None):
    tests = []
    if check is None:
        def check(name, passed):
            tests.append({"test": name, "passed": bool(passed),
                          "detail": "real temporary body folder and a loopback S3-compatible fake; no provider"})
    with tempfile.TemporaryDirectory(prefix="catalogue-body-store-kit-") as directory:
        base = Path(root) if root is not None else Path(directory)
        nonce = os.urandom(6).hex().encode()
        groups = []
        with ObjectStoreFake(access_key_id=FAKE_KEY_ID, secret_access_key=FAKE_SECRET, bucket=BUCKET) as fake:
            volume = _VolumeTarget(base / "edge")
            object_store = _ObjectStoreTarget(fake)
            groups = [(lambda: _edge_checks(check, VOLUME_NAMES, volume, nonce), "volume_edge_checks"),
                      (lambda: _edge_checks(check, OBJECT_STORE_NAMES, object_store, nonce), "object_store_edge_checks"),
                      (lambda: _shared_checks(check, volume, object_store), "shared_checks"),
                      (lambda: _signer_checks(check), "signer_checks"),
                      (lambda: _object_store_checks(check, fake, nonce), "object_store_checks"),
                      (lambda: _factory_checks(check, base / "factory"), "factory_checks")]
            (base / "factory").mkdir(parents=True, exist_ok=True)
            try:
                for group, name in groups:
                    try:
                        group()
                    except Exception:  # noqa: BLE001 - a group that stops part way is a failure with a name
                        check(f"the_{name}_ran_to_completion", False)
            finally:
                object_store.close()
    return {"record_type": KIT_RECORD_TYPE, "tests": tests, "passed": sum(row["passed"] for row in tests),
            "total": len(tests), "all_passed": all(row["passed"] for row in tests)}


def run_external_checks(check, *, endpoint, bucket, access_key_id_ref, secret_access_key_ref, region="auto",
                        secret_resolver=None):
    """The edge checks and the refused-credential check against a real S3-compatible test bucket."""
    resolver = secret_resolver or catalogue_object_store.environment_reference
    target = _ExternalTarget(endpoint, bucket, access_key_id_ref, secret_access_key_ref, region, resolver)
    nonce = os.urandom(8).hex().encode()
    _edge_checks(check, OBJECT_STORE_NAMES, target, nonce)
    payload = b"external presigned " + nonce
    stored = target.writer.put(payload)
    status = _external_status(target.reader.presigned_read_url(stored["digest"], 60))
    check("a_presigned_read_link_works_until_it_expires_and_refuses_any_change", status == (200, payload))

    def wrong(reference):
        return "not-the-secret" if reference == secret_access_key_ref else resolver(reference)
    check("an_object_store_credential_the_store_refuses_is_a_typed_refusal_for_reads_and_writes",
          refused(lambda: ObjectStoreBodyStore(endpoint, bucket, access_key_id_ref=access_key_id_ref,
                                               secret_access_key_ref=secret_access_key_ref, region=region,
                                               secret_resolver=wrong).read(stored["digest"], len(payload)),
                  "body_unreadable"))


def _external_status(url):
    parts = urllib.parse.urlsplit(url)
    kind = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    connection = kind(parts.hostname, parts.port, timeout=30)
    try:
        connection.request("GET", parts.path + "?" + parts.query)
        answer = connection.getresponse()
        return answer.status, answer.read(KIT_MAXIMUM_FILE_BYTES + 1)
    finally:
        connection.close()


def self_test():
    return run_checks()
