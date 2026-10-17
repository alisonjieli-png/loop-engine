"""/.well-known/security.txt (RFC 9116) and /favicon.ico, the two root files the launch audit found missing.

The launch audit of October 16, 2026 (docs/verification/LAUNCH-AUDIT-BALTOR-2026-10-16.md, finding O9) saw both answer
404. The security contact is the repository's private vulnerability report, as SECURITY.md asks, and the icon is the
packaged 32-pixel page icon, byte for byte. Served from real loopback HTTP; no provider or production request is made.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import struct
import tempfile
import unittest

import httpx

from loop_engine.core.service_runtime import static_site_export, support_page, web_pages
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
from loop_engine.core.service_runtime.web_site_map import load_site_map

FIELDS = {"acknowledgments", "canonical", "contact", "encryption", "expires", "hiring", "policy",
          "preferred-languages", "csaf"}


def security_problems(text, site_map, now, repository):
    """What keeps a security.txt from meeting RFC 9116 and this site's own facts."""
    problems, fields = [], {}
    for number, line in enumerate(text.split("\n"), 1):
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition(": ")
        if not separator or name.lower() not in FIELDS or not value.strip():
            problems.append(f"line {number} is not a known field: {line!r}")
            continue
        fields.setdefault(name.lower(), []).append(value.strip())
    contacts = fields.get("contact", [])
    if not contacts or any(not value.startswith(("https://", "mailto:")) for value in contacts):
        problems.append(f"contact {contacts}")
    if repository and contacts[:1] != [repository + "/security/advisories/new"]:
        problems.append(f"the first contact {contacts[:1]} is not the private vulnerability report")
    expires = fields.get("expires", [])
    if len(expires) != 1:
        problems.append(f"{len(expires)} expires fields")
    else:
        try:
            moment = datetime.fromisoformat(expires[0].replace("Z", "+00:00"))
        except ValueError:
            moment = None
        if moment is None or moment.tzinfo is None:
            problems.append(f"expires {expires[0]!r} is not an RFC 3339 time")
        elif moment <= now:
            problems.append(f"expired on {expires[0]}: renew SECURITY_TEXT_EXPIRES in support_page.py")
        elif moment > now + timedelta(days=366):
            problems.append(f"expires {expires[0]} is more than a year away")
    wanted = {f"https://{surface.hostname}/.well-known/security.txt" for surface in site_map.hostnames}
    wanted.add(site_map.canonical_origin + "/.well-known/security.txt")
    if set(fields.get("canonical", [])) != wanted:
        problems.append(f"canonical {sorted(fields.get('canonical', []))}")
    if fields.get("preferred-languages") != ["en"]:
        problems.append(f"preferred languages {fields.get('preferred-languages')}")
    return problems


def icon_problems(body, png):
    """What keeps an icon file from being the one packaged PNG in a one-image icon container."""
    if len(body) < 22:
        return ["shorter than its header"]
    reserved, kind, count = struct.unpack("<HHH", body[:6])
    width, height, colours, _zero, planes, depth, size, offset = struct.unpack("<BBBBHHII", body[6:22])
    problems = []
    if (reserved, kind, count) != (0, 1, 1):
        problems.append(f"header {(reserved, kind, count)}")
    if (width, height, colours, planes, depth) != (32, 32, 0, 1, 32):
        problems.append(f"entry {(width, height, colours, planes, depth)}")
    if size != len(png) or offset != 22 or body[offset:offset + size] != png or len(body) != 22 + len(png):
        problems.append("the image is not the packaged favicon-32.png byte for byte")
    return problems


class SiteRootFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site_map = load_site_map()
        cls.png = web_pages.read_packaged_asset("favicon-32.png")
        cls.repository = support_page.repository_address()

    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="site-root-files-")
        self.addCleanup(folder.cleanup)
        self.fixture = HttpDomainFixture(Path(folder.name))
        running = running_http(self.fixture)
        self.base, _service = running.__enter__()
        self.addCleanup(running.__exit__, None, None, None)
        self.client = httpx.Client(base_url=self.base, trust_env=False, follow_redirects=False, timeout=15)
        self.addCleanup(self.client.close)

    def test_security_text_meets_rfc_9116_and_names_the_private_report(self):
        self.assertTrue(self.repository, "the distribution metadata names no GitHub repository")
        answer = self.client.get("/.well-known/security.txt")
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.headers["content-type"], "text/plain; charset=utf-8")
        self.assertEqual(answer.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(security_problems(answer.text, self.site_map, datetime.now(timezone.utc), self.repository), [])
        self.assertIn(f"Policy: {self.repository}/security/policy\n", answer.text)

    def test_favicon_is_the_packaged_icon_in_an_icon_container(self):
        answer = self.client.get("/favicon.ico")
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.headers["content-type"], "image/vnd.microsoft.icon")
        self.assertEqual(answer.headers.get("cache-control"), web_pages.PUBLIC_ASSET_CACHE_CONTROL)
        self.assertEqual(icon_problems(answer.content, self.png), [])

    def test_head_answers_like_get_and_the_edge_export_serves_the_icon(self):
        for path in ("/.well-known/security.txt", "/favicon.ico"):
            with self.subTest(path=path):
                get, head = self.client.get(path), self.client.head(path)
                self.assertEqual((head.status_code, head.content), (200, b""))
                self.assertEqual(head.headers.get("content-length"), str(len(get.content)))
                self.assertEqual(head.headers.get("etag"), get.headers.get("etag"))
        addresses = static_site_export.static_addresses(include_model_details=False)
        self.assertIn("/favicon.ico", addresses)
        # The edge passes every /.well-known/ address to the origin, which answers it from this table.
        self.assertNotIn("/.well-known/security.txt", addresses)

    def test_known_wrong_controls(self):
        now = datetime.now(timezone.utc)
        good = support_page.security_text(self.site_map).decode("utf-8")
        self.assertEqual(security_problems(good, self.site_map, now, self.repository), [])
        expires = next(line for line in good.split("\n") if line.startswith("Expires: "))
        contact = next(line for line in good.split("\n") if line.startswith("Contact: "))
        canonical = next(line for line in good.split("\n") if line.startswith("Canonical: "))
        wrong = {"no contact": good.replace(contact + "\n", ""),
                 "a public issue as the first contact": good.replace(contact, "Contact: " + self.repository + "/issues"),
                 "two expiry fields": good.replace(expires, expires + "\n" + expires),
                 "an unknown field": good + "Encrypt: https://example.invalid/key\n",
                 "a missing hostname": good.replace(canonical + "\n", "")}
        for name, text in wrong.items():
            with self.subTest(name=name):
                self.assertTrue(security_problems(text, self.site_map, now, self.repository))
        moment = datetime.fromisoformat(support_page.SECURITY_TEXT_EXPIRES.replace("Z", "+00:00"))
        self.assertTrue(security_problems(good, self.site_map, moment + timedelta(seconds=1), self.repository))
        self.assertTrue(security_problems(good, self.site_map, moment - timedelta(days=400), self.repository))
        icon = web_pages.favicon_ico(self.site_map)
        self.assertEqual(icon_problems(icon, self.png), [])
        changed = icon[:-1] + bytes([icon[-1] ^ 1])
        for planted in (changed, icon[:21], icon + b"\0", self.png):
            self.assertTrue(icon_problems(planted, self.png))


if __name__ == "__main__":
    unittest.main()
