"""Template 1: Deterministic Regex Recipe Factory (gen-regex-library).

Generates 50 local regular-expression matching and extraction previews.
The names refer to format specifications (RFC 5322, RFC 4122,
RFC 9562, SemVer 2.0.0, ISO 8601, RFC 3986, IEEE 802, ITU-T E.164, ISO 6166,
ISO 17442, RFC 6901, RFC 7519, BCP 47, and spatial/package standards).
These are original lexical approximations, not complete standards validators.

Each generated component includes:
- pattern.py: compiled stdlib re pattern with validate() and extract() functions
- test_pattern.py: positive corpus, negative corpus, boundary cases, ReDoS check, and known-wrong control
- SKILL.md and harness integration guides (claude-code, codex, cursor, opencode)
- LICENSE (MIT) and ATTRIBUTION.md
- CataloguePackage with SHA-256 digests and local preview metadata, not an admission record
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import time
from typing import Any

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _REPO_SRC not in sys.path:
    sys.path.insert(0, _REPO_SRC)

from loop_engine.core.service_runtime.catalogue_packages import (
    PACKAGE_BODY,
    CataloguePackage,
    CataloguePackageFile,
    sha256_hex,
)

FACTORY_ID = "gen-regex-library"
FACTORY_VERSION = "1.0.0"
GENERATED_ON = "2026-10-13"

MIT_LICENSE_TEXT = (
    "MIT License\n\n"
    "Copyright (c) 2026 Alie Jie Li\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy "
    "of this software and associated documentation files (the \"Software\"), to deal "
    "in the Software without restriction, including without limitation the rights "
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
    "copies of the Software, and to permit persons to whom the Software is "
    "furnished to do so, subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all "
    "copies or substantial portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR "
    "COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN "
    "ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE "
    "SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
)


@dataclass(frozen=True)
class RegexRecipeSpec:
    recipe_id: str
    title: str
    standard: str
    description: str
    pattern: str
    max_length: int
    positive_cases: tuple[str, ...]
    negative_cases: tuple[str, ...]
    extraction_text: str
    expected_extractions: tuple[str, ...]


REGEX_RECIPES: tuple[RegexRecipeSpec, ...] = (
    RegexRecipeSpec(
        recipe_id="rfc5322-email-subset",
        title="RFC 5322 practical email address validator",
        standard="RFC 5322 Section 3.4.1",
        description="Validates practical ASCII email addresses with bounded local part and DNS domain labels.",
        pattern=r"[A-Za-z0-9._%+-]{1,64}@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,24}",
        max_length=254,
        positive_cases=("ada@example.com", "grace.hopper+navy@cs.yale.edu", "user_123@sub.domain.co.uk", "a@b.io", "billing-team@company.org"),
        negative_cases=("plainaddress", "@example.com", "ada@", "ada..b@example", "ada@-example.com", "ada@example.c"),
        extraction_text="Contact ada@example.com or billing-team@company.org for details.",
        expected_extractions=("ada@example.com", "billing-team@company.org"),
    ),
    RegexRecipeSpec(
        recipe_id="rfc4122-uuid-any",
        title="RFC 4122 canonical 36-character UUID validator",
        standard="RFC 4122 Section 3",
        description="Matches canonical 8-4-4-4-12 hexadecimal UUID strings in lowercase or uppercase.",
        pattern=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        max_length=36,
        positive_cases=(
            "123e4567-e89b-12d3-a456-426614174000",
            "00000000-0000-0000-0000-000000000000",
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "F81D4FAE-7DEC-11D0-A765-00A0C91E6BF6",
        ),
        negative_cases=("123e4567e89b12d3a456426614174000", "123e4567-e89b-12d3-a456-42661417400g", "123-456-789", "", "123e4567-e89b-12d3-a456-42661417400"),
        extraction_text="Task 550e8400-e29b-41d4-a716-446655440000 spawned 6ba7b810-9dad-11d1-80b4-00c04fd430c8.",
        expected_extractions=("550e8400-e29b-41d4-a716-446655440000", "6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
    ),
    RegexRecipeSpec(
        recipe_id="rfc4122-uuid-v4",
        title="RFC 4122 strict version 4 random UUID validator",
        standard="RFC 4122 Section 4.4",
        description="Matches version 4 RFC 4122 UUIDs with version nibble 4 and variant nibble 8, 9, a, or b.",
        pattern=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
        max_length=36,
        positive_cases=(
            "550e8400-e29b-41d4-a716-446655440000",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
            "110ec58a-a0f2-4ac4-8393-c866d813b8d1",
            "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
        ),
        negative_cases=(
            "123e4567-e89b-12d3-a456-426614174000",
            "550e8400-e29b-41d4-0716-446655440000",
            "00000000-0000-0000-0000-000000000000",
            "not-a-uuid-v4",
            "550e8400-e29b-51d4-a716-446655440000",
        ),
        extraction_text="IDs: 550e8400-e29b-41d4-a716-446655440000 and f47ac10b-58cc-4372-a567-0e02b2c3d479.",
        expected_extractions=("550e8400-e29b-41d4-a716-446655440000", "f47ac10b-58cc-4372-a567-0e02b2c3d479"),
    ),
    RegexRecipeSpec(
        recipe_id="rfc9562-uuid-v7",
        title="RFC 9562 time-ordered UUIDv7 validator",
        standard="RFC 9562 Section 5.7",
        description="Matches time-ordered version 7 UUIDs with version nibble 7 and RFC variant nibble 8, 9, a, or b.",
        pattern=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-7[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
        max_length=36,
        positive_cases=(
            "017f22e2-79b0-7cc3-98c4-dc0c0c07398f",
            "018e65c0-1234-7000-8000-000000000001",
            "018f1a2b-3c4d-7e5f-9a0b-1c2d3e4f5a6b",
            "01900000-0000-7abc-a123-456789abcdef",
            "019284f0-8811-7fff-b000-112233445566",
        ),
        negative_cases=(
            "550e8400-e29b-41d4-a716-446655440000",
            "017f22e2-79b0-4cc3-98c4-dc0c0c07398f",
            "017f22e2-79b0-7cc3-18c4-dc0c0c07398f",
            "invalid-uuid-v7",
            "017f22e2-79b0-7cc3-98c4",
        ),
        extraction_text="Events 017f22e2-79b0-7cc3-98c4-dc0c0c07398f and 018e65c0-1234-7000-8000-000000000001 logged.",
        expected_extractions=("017f22e2-79b0-7cc3-98c4-dc0c0c07398f", "018e65c0-1234-7000-8000-000000000001"),
    ),
    RegexRecipeSpec(
        recipe_id="semver-2-0-0",
        title="Semantic Versioning 2.0.0 validator",
        standard="SemVer 2.0.0",
        description="Matches Semantic Versioning 2.0.0 strings with optional pre-release and build metadata.",
        pattern=r"(?:0|[1-9][0-9]{0,9})\.(?:0|[1-9][0-9]{0,9})\.(?:0|[1-9][0-9]{0,9})(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
        max_length=128,
        positive_cases=("1.0.0", "0.1.0", "2.10.6", "1.0.0-alpha.1", "1.0.0-rc.1+build.123"),
        negative_cases=("01.1.1", "1.0", "v1.0.0", "1.2.3.4", "1.0.0-"),
        extraction_text="Upgraded from 1.0.0-alpha.1 to 2.10.6",
        expected_extractions=("1.0.0-alpha.1", "2.10.6"),
    ),
    RegexRecipeSpec(
        recipe_id="iso8601-date",
        title="ISO 8601 calendar date YYYY-MM-DD validator",
        standard="ISO 8601-1:2019",
        description="Matches 4-digit year, 2-digit month (01-12), and 2-digit day (01-31).",
        pattern=r"[12][0-9]{3}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])",
        max_length=10,
        positive_cases=("2026-10-13", "2026-01-01", "1999-12-31", "2024-02-29", "2030-06-15"),
        negative_cases=("2026-13-01", "2026-00-10", "2026-10-32", "26-10-13", "2026/10/13"),
        extraction_text="Window runs from 2026-01-01 through 2026-10-13.",
        expected_extractions=("2026-01-01", "2026-10-13"),
    ),
    RegexRecipeSpec(
        recipe_id="iso8601-utc-timestamp",
        title="ISO 8601 / RFC 3339 UTC timestamp validator",
        standard="RFC 3339 Section 5.6",
        description="Matches UTC timestamps formatted as YYYY-MM-DDTHH:MM:SS with optional fractional seconds and Z suffix.",
        pattern=r"[12][0-9]{3}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?Z",
        max_length=30,
        positive_cases=(
            "2026-10-13T20:07:14Z",
            "2026-01-01T00:00:00Z",
            "2026-10-13T12:30:45.123Z",
            "2026-10-13T23:59:59.999999Z",
            "2025-07-04T08:15:00Z",
        ),
        negative_cases=(
            "2026-10-13 20:07:14Z",
            "2026-10-13T24:00:00Z",
            "2026-10-13T20:60:00Z",
            "2026-10-13T20:07:14",
            "2026-10-13T20:07:14+02:00",
        ),
        extraction_text="Started at 2026-01-01T00:00:00Z and finished at 2026-10-13T20:07:14Z.",
        expected_extractions=("2026-01-01T00:00:00Z", "2026-10-13T20:07:14Z"),
    ),
    RegexRecipeSpec(
        recipe_id="iso8601-duration",
        title="ISO 8601 duration validator",
        standard="ISO 8601 Duration",
        description="Matches ISO 8601 day/time durations starting with P and containing at least one unit.",
        pattern=r"P(?=[0-9T])(?:[0-9]{1,4}Y)?(?:[0-9]{1,4}M)?(?:[0-9]{1,4}W)?(?:[0-9]{1,4}D)?(?:T(?=[0-9])(?:[0-9]{1,4}H)?(?:[0-9]{1,4}M)?(?:[0-9]{1,4}S)?)?",
        max_length=40,
        positive_cases=("P1D", "PT15M", "P3Y6M4DT12H30M5S", "P2W", "PT1H30M"),
        negative_cases=("P", "PT", "1D", "P-1D", "T15M"),
        extraction_text="Intervals P1D and PT15M are supported.",
        expected_extractions=("P1D", "PT15M"),
    ),
    RegexRecipeSpec(
        recipe_id="iso8601-week-date",
        title="ISO 8601 week date validator",
        standard="ISO 8601 Week Date",
        description="Matches ISO week dates formatted as YYYY-Www or YYYY-Www-D.",
        pattern=r"[12][0-9]{3}-W(?:0[1-9]|[1-4][0-9]|5[0-3])(?:-[1-7])?",
        max_length=10,
        positive_cases=("2026-W42-2", "2026-W01-1", "2026-W52-7", "2025-W10", "2024-W53-4"),
        negative_cases=("2026-W00-1", "2026-W54-1", "2026-W42-8", "2026-42-2", "W42-2"),
        extraction_text="Scheduled for 2026-W01-1 and 2026-W42-2.",
        expected_extractions=("2026-W01-1", "2026-W42-2"),
    ),
    RegexRecipeSpec(
        recipe_id="rfc3986-https-url",
        title="RFC 3986 HTTPS URL validator",
        standard="RFC 3986",
        description="Matches strict https:// URLs with a valid hostname, optional port, and safe path characters.",
        pattern=r"https://[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?::[0-9]{1,5})?(?:/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*[A-Za-z0-9_~/#=-])?",
        max_length=512,
        positive_cases=(
            "https://baltor.ai",
            "https://baltor.ai/feeds/sources.json",
            "https://api.osv.dev/v1/querybatch",
            "https://registry.modelcontextprotocol.io/v0/servers",
            "https://example.com:8443/path/to/item?version=1",
        ),
        negative_cases=("http://baltor.ai", "ftp://baltor.ai", "https://localhost", "https://", "://baltor.ai"),
        extraction_text="Fetch https://baltor.ai/feeds/sources.json or https://api.osv.dev/v1/querybatch",
        expected_extractions=("https://baltor.ai/feeds/sources.json", "https://api.osv.dev/v1/querybatch"),
    ),
    RegexRecipeSpec(
        recipe_id="ipv4-dotted-quad",
        title="IPv4 dotted-quad address validator",
        standard="RFC 791",
        description="Matches IPv4 addresses where each of the four octets is between 0 and 255.",
        pattern=r"(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])",
        max_length=15,
        positive_cases=("127.0.0.1", "192.168.1.1", "10.0.0.255", "0.0.0.0", "255.255.255.255"),
        negative_cases=("256.0.0.1", "192.168.1", "192.168.1.1.1", "192.168.1.999", "abc.def.ghi.jkl"),
        extraction_text="Loopback is 127.0.0.1 and gateway is 192.168.1.1",
        expected_extractions=("127.0.0.1", "192.168.1.1"),
    ),
    RegexRecipeSpec(
        recipe_id="ipv4-cidr-block",
        title="IPv4 CIDR block validator",
        standard="RFC 4632",
        description="Matches IPv4 addresses with a /0 to /32 prefix length.",
        pattern=r"(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])/(?:3[0-2]|[12]?[0-9])",
        max_length=18,
        positive_cases=("10.0.0.0/8", "172.16.0.0/12", "192.168.1.0/24", "0.0.0.0/0", "203.0.113.5/32"),
        negative_cases=("10.0.0.0/33", "10.0.0.0", "256.0.0.0/24", "10.0.0.0/-1", "10.0.0/24"),
        extraction_text="Subnets 10.0.0.0/8 and 192.168.1.0/24 are private.",
        expected_extractions=("10.0.0.0/8", "192.168.1.0/24"),
    ),
    RegexRecipeSpec(
        recipe_id="ipv6-full-hex",
        title="IPv6 full 8-group hexadecimal address validator",
        standard="RFC 4291",
        description="Matches uncompressed 8-hextet IPv6 addresses.",
        pattern=r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}",
        max_length=39,
        positive_cases=(
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "fe80:0000:0000:0000:0202:b3ff:fe1e:8329",
            "0000:0000:0000:0000:0000:0000:0000:0001",
            "2001:4860:4860:0000:0000:0000:0000:8888",
            "fd00:1234:5678:9abc:def0:1234:5678:9abc",
        ),
        negative_cases=("2001:db8::1", "2001:0db8:85a3:0000:0000:8a2e:0370", "2001:0db8:85a3:0000:0000:8a2e:0370:7334:1111", "gggg:0000:0000:0000:0000:0000:0000:0001", "127.0.0.1"),
        extraction_text="Primary 2001:0db8:85a3:0000:0000:8a2e:0370:7334 and DNS 2001:4860:4860:0000:0000:0000:0000:8888.",
        expected_extractions=("2001:0db8:85a3:0000:0000:8a2e:0370:7334", "2001:4860:4860:0000:0000:0000:0000:8888"),
    ),
    RegexRecipeSpec(
        recipe_id="ieee802-mac-colon",
        title="IEEE 802 colon-separated MAC-48 address validator",
        standard="IEEE 802",
        description="Matches 6-octet colon-separated hexadecimal MAC addresses.",
        pattern=r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}",
        max_length=17,
        positive_cases=("00:1A:2B:3C:4D:5E", "aa:bb:cc:dd:ee:ff", "01:23:45:67:89:ab", "FF:FF:FF:FF:FF:FF", "10:20:30:40:50:60"),
        negative_cases=("00-1A-2B-3C-4D-5E", "00:1A:2B:3C:4D", "00:1A:2B:3C:4D:5E:6F", "00:1A:2B:3C:4D:GG", "0:1A:2B:3C:4D:5E"),
        extraction_text="NICs 00:1A:2B:3C:4D:5E and aa:bb:cc:dd:ee:ff online.",
        expected_extractions=("00:1A:2B:3C:4D:5E", "aa:bb:cc:dd:ee:ff"),
    ),
    RegexRecipeSpec(
        recipe_id="ieee802-mac-hyphen",
        title="IEEE 802 hyphen-separated MAC-48 address validator",
        standard="IEEE 802",
        description="Matches 6-octet hyphen-separated hexadecimal MAC addresses.",
        pattern=r"(?:[0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2}",
        max_length=17,
        positive_cases=("00-1A-2B-3C-4D-5E", "aa-bb-cc-dd-ee-ff", "01-23-45-67-89-ab", "FF-FF-FF-FF-FF-FF", "10-20-30-40-50-60"),
        negative_cases=("00:1A:2B:3C:4D:5E", "00-1A-2B-3C-4D", "00-1A-2B-3C-4D-5E-6F", "00-1A-2B-3C-4D-GG", "001A2B3C4D5E"),
        extraction_text="Found 00-1A-2B-3C-4D-5E and 01-23-45-67-89-ab.",
        expected_extractions=("00-1A-2B-3C-4D-5E", "01-23-45-67-89-ab"),
    ),
    RegexRecipeSpec(
        recipe_id="e164-phone-number",
        title="ITU-T E.164 international phone number validator",
        standard="ITU-T E.164",
        description="Matches international phone numbers starting with + followed by 8 to 15 digits.",
        pattern=r"\+[1-9][0-9]{7,14}",
        max_length=16,
        positive_cases=("+14155552671", "+442071838750", "+81312345678", "+4930123456", "+61298765432"),
        negative_cases=("14155552671", "+0123456789", "+12345", "+1234567890123456", "+1-415-555-2671"),
        extraction_text="Call +14155552671 or +442071838750.",
        expected_extractions=("+14155552671", "+442071838750"),
    ),
    RegexRecipeSpec(
        recipe_id="nanp-us-phone",
        title="North American Numbering Plan phone validator",
        standard="NANP",
        description="Matches standard 10-digit US/Canada phone numbers formatted as NXX-NXX-XXXX.",
        pattern=r"[2-9][0-9]{2}-[2-9][0-9]{2}-[0-9]{4}",
        max_length=12,
        positive_cases=("415-555-2671", "212-456-7890", "310-234-5678", "650-888-1234", "800-555-0199"),
        negative_cases=("115-555-2671", "415-155-2671", "415-555-267", "4155552671", "000-000-0000"),
        extraction_text="Numbers: 415-555-2671 and 212-456-7890.",
        expected_extractions=("415-555-2671", "212-456-7890"),
    ),
    RegexRecipeSpec(
        recipe_id="us-zip-code",
        title="United States 5-digit and ZIP+4 postal code validator",
        standard="USPS Publication 28",
        description="Matches 5-digit US ZIP codes and 9-digit ZIP+4 codes.",
        pattern=r"[0-9]{5}(?:-[0-9]{4})?",
        max_length=10,
        positive_cases=("94107", "16678", "10001-1234", "02139", "90210-0001"),
        negative_cases=("9410", "941071", "94107-123", "94107-12345", "ABCDE"),
        extraction_text="Locations 16678 and 10001-1234 verified.",
        expected_extractions=("16678", "10001-1234"),
    ),
    RegexRecipeSpec(
        recipe_id="ca-postal-code",
        title="Canada Post alphanumeric postal code validator",
        standard="Canada Post Addressing Guidelines",
        description="Matches Canadian A1A 1A1 postal codes excluding unused letters D, F, I, O, Q, U.",
        pattern=r"[ABCEGHJKLMNPRSTVXY][0-9][ABCEGHJKLMNPRSTVWXYZ] [0-9][ABCEGHJKLMNPRSTVWXYZ][0-9]",
        max_length=7,
        positive_cases=("K1A 0B1", "M5V 3L9", "H3Z 2Y7", "V6B 1A1", "T2P 1J9"),
        negative_cases=("D1A 0B1", "K1A0B1", "123 456", "Z1A 0B1", "K1O 0B1"),
        extraction_text="Ship to K1A 0B1 or M5V 3L9.",
        expected_extractions=("K1A 0B1", "M5V 3L9"),
    ),
    RegexRecipeSpec(
        recipe_id="uk-postcode",
        title="United Kingdom Royal Mail postcode validator",
        standard="BS 7666",
        description="Matches standard UK outward and inward postcode formats with a single space.",
        pattern=r"[A-Z]{1,2}[0-9][0-9A-Z]? [0-9][ABD-HJLNP-UW-Z]{2}",
        max_length=8,
        positive_cases=("SW1A 1AA", "EC1A 1BB", "W1A 0AX", "M1 1AE", "B33 8TH"),
        negative_cases=("SW1A1AA", "123 456", "SW1A 1CI", "ABCD 1AA", "SW1A  1AA"),
        extraction_text="Offices at SW1A 1AA and EC1A 1BB.",
        expected_extractions=("SW1A 1AA", "EC1A 1BB"),
    ),
    RegexRecipeSpec(
        recipe_id="de-postal-code",
        title="German 5-digit Postleitzahl validator",
        standard="Deutsche Post PLZ",
        description="Matches German 5-digit postal codes (01000 to 99999).",
        pattern=r"(?:0[1-9]|[1-9][0-9])[0-9]{3}",
        max_length=5,
        positive_cases=("10115", "80331", "01067", "50667", "20095"),
        negative_cases=("00123", "1011", "101150", "ABCDE", "00000"),
        extraction_text="Berlin 10115 and Munich 80331.",
        expected_extractions=("10115", "80331"),
    ),
    RegexRecipeSpec(
        recipe_id="jp-postal-code",
        title="Japan Post NNN-NNNN postal code validator",
        standard="Japan Post",
        description="Matches Japanese 7-digit postal codes formatted as 3 digits, a hyphen, and 4 digits.",
        pattern=r"[0-9]{3}-[0-9]{4}",
        max_length=8,
        positive_cases=("100-0001", "150-0043", "060-0000", "530-0001", "900-0015"),
        negative_cases=("1000001", "10-0001", "100-001", "100-00012", "ABC-DEFG"),
        extraction_text="Chiyoda 100-0001 and Shibuya 150-0043.",
        expected_extractions=("100-0001", "150-0043"),
    ),
    RegexRecipeSpec(
        recipe_id="css-hex-color",
        title="CSS Color Module Level 4 hex color validator",
        standard="W3C CSS Color 4",
        description="Matches 8-digit or 6-digit hexadecimal CSS color literals prefixed with #.",
        pattern=r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6})",
        max_length=9,
        positive_cases=("#1a2b3c", "#FFFFFF", "#000000", "#ff5733cc", "#0F172A"),
        negative_cases=("1a2b3c", "#12", "#12345", "#1234567", "#gggggg"),
        extraction_text="Palette uses #1a2b3c and #ff5733cc.",
        expected_extractions=("#1a2b3c", "#ff5733cc"),
    ),
    RegexRecipeSpec(
        recipe_id="github-repo-slug",
        title="GitHub owner/repository slug validator",
        standard="GitHub Repository Naming",
        description="Matches GitHub owner/repository identifiers with valid owner and repository characters.",
        pattern=r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/[A-Za-z0-9_-]{1,100}",
        max_length=140,
        positive_cases=("alisonjieli-png/loop-engine", "torvalds/linux", "python/cpython", "godotengine/godot", "modelcontextprotocol/servers"),
        negative_cases=("-badowner/repo", "owner-/repo", "owner/", "/repo", "owner/repo/extra"),
        extraction_text="Mirrors alisonjieli-png/loop-engine and godotengine/godot",
        expected_extractions=("alisonjieli-png/loop-engine", "godotengine/godot"),
    ),
    RegexRecipeSpec(
        recipe_id="git-commit-sha1",
        title="Git 40-character lowercase SHA-1 commit object ID validator",
        standard="Git Object Format",
        description="Matches exact 40-character lowercase hexadecimal Git commit hashes.",
        pattern=r"[0-9a-f]{40}",
        max_length=40,
        positive_cases=(
            "a3bd0f1000000000000000000000000000000001",
            "0123456789abcdef0123456789abcdef01234567",
            "ffffffffffffffffffffffffffffffffffffffff",
            "1111111122222222333333334444444455555555",
            "9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d",
        ),
        negative_cases=("a3bd0f1", "0123456789ABCDEF0123456789ABCDEF01234567", "g123456789abcdef0123456789abcdef01234567", "", "0123456789abcdef0123456789abcdef012345678"),
        extraction_text="Pinned at a3bd0f1000000000000000000000000000000001 and 0123456789abcdef0123456789abcdef01234567.",
        expected_extractions=("a3bd0f1000000000000000000000000000000001", "0123456789abcdef0123456789abcdef01234567"),
    ),
    RegexRecipeSpec(
        recipe_id="sha256-hex-digest",
        title="FIPS 180-4 64-character lowercase SHA-256 digest validator",
        standard="FIPS 180-4",
        description="Matches exact 64-character lowercase hexadecimal SHA-256 digests.",
        pattern=r"[0-9a-f]{64}",
        max_length=64,
        positive_cases=(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
            "0" * 64,
            "f" * 64,
        ),
        negative_cases=("e3b0c44298fc1c149afbf4c8996fb924", "E" * 64, "g" * 64, "0" * 63, "0" * 65),
        extraction_text="Digests e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 and ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad.",
        expected_extractions=(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        ),
    ),
    RegexRecipeSpec(
        recipe_id="docker-image-digest-ref",
        title="OCI / Docker digest-pinned image reference validator",
        standard="OCI Distribution Spec",
        description="Matches container image references pinned by an immutable @sha256:<64-hex> digest.",
        pattern=r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*@sha256:[0-9a-f]{64}",
        max_length=255,
        positive_cases=(
            "python@sha256:" + "a" * 64,
            "library/postgres@sha256:" + "b" * 64,
            "ghcr.io/owner/app@sha256:" + "c" * 64,
            "debian@sha256:" + "0" * 64,
            "redis@sha256:" + "9" * 64,
        ),
        negative_cases=("python:latest", "python:3.12", "python@sha256:1234", "PYTHON@sha256:" + "a" * 64, "@sha256:" + "a" * 64),
        extraction_text="Use python@sha256:" + "a" * 64 + " and redis@sha256:" + "9" * 64 + ".",
        expected_extractions=("python@sha256:" + "a" * 64, "redis@sha256:" + "9" * 64),
    ),
    RegexRecipeSpec(
        recipe_id="k8s-dns1123-label",
        title="Kubernetes RFC 1123 DNS label validator",
        standard="RFC 1123",
        description="Matches lowercase alphanumeric Kubernetes labels containing a hyphen.",
        pattern=r"[a-z0-9]+-[a-z0-9-]+",
        max_length=63,
        positive_cases=("web-frontend", "db-01", "worker-pool-2", "metrics-collector", "cache-node"),
        negative_cases=("-web", "web-", "Web-Frontend", "web_frontend", "singleword"),
        extraction_text="Pods web-frontend and worker-pool-2 ready.",
        expected_extractions=("web-frontend", "worker-pool-2"),
    ),
    RegexRecipeSpec(
        recipe_id="k8s-dns1123-subdomain",
        title="Kubernetes RFC 1123 DNS subdomain validator",
        standard="RFC 1123",
        description="Matches dot-separated lowercase DNS subdomains with at least two labels.",
        pattern=r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
        max_length=253,
        positive_cases=("api.baltor.ai", "svc.cluster.local", "db-01.prod.internal", "a.b", "cache.us-east-1.example.org"),
        negative_cases=("singlelabel", "-api.baltor.ai", "api.baltor.ai.", "API.baltor.ai", "api..baltor.ai"),
        extraction_text="Endpoints api.baltor.ai and svc.cluster.local active.",
        expected_extractions=("api.baltor.ai", "svc.cluster.local"),
    ),
    RegexRecipeSpec(
        recipe_id="cron-5-field",
        title="POSIX 5-field cron schedule expression validator",
        standard="POSIX crontab",
        description="Matches 5-field cron expressions (minute, hour, day-of-month, month, day-of-week).",
        pattern=r"(?:\*(?:/[1-9][0-9]*)?|[0-5]?[0-9](?:-[0-5]?[0-9])?(?:,[0-5]?[0-9])*) (?:\*(?:/[1-9][0-9]*)?|(?:[01]?[0-9]|2[0-3])(?:-(?:[01]?[0-9]|2[0-3]))?) (?:\*(?:/[1-9][0-9]*)?|(?:[1-9]|[12][0-9]|3[01])) (?:\*(?:/[1-9][0-9]*)?|(?:[1-9]|1[0-2])) (?:\*|[0-7](?:-[0-7])?)",
        max_length=64,
        positive_cases=("*/5 * * * *", "0 9 * * 1-5", "30 2 1 * *", "0 */6 * * *", "15,45 14 * * 0"),
        negative_cases=("* * * *", "* * * * * *", "60 * * * *", "* 24 * * *", "invalid cron"),
        extraction_text="Schedules: */5 * * * * and 0 9 * * 1-5",
        expected_extractions=("*/5 * * * *", "0 9 * * 1-5"),
    ),
    RegexRecipeSpec(
        recipe_id="iana-media-type",
        title="RFC 6838 IANA media type validator",
        standard="RFC 6838",
        description="Matches lowercase type/subtype MIME media type identifiers.",
        pattern=r"(?:application|audio|font|image|message|model|multipart|text|video)/[a-z0-9][a-z0-9!#$&^_+-]{0,80}",
        max_length=100,
        positive_cases=("application/json", "text/markdown", "application/feed+json", "image/png", "model/gltf-binary"),
        negative_cases=("application", "text/", "APPLICATION/JSON", "custom/type", "application/json; charset=utf-8"),
        extraction_text="Accepts application/json and text/markdown.",
        expected_extractions=("application/json", "text/markdown"),
    ),
    RegexRecipeSpec(
        recipe_id="bcp47-language-tag",
        title="IETF BCP 47 language-region tag validator",
        standard="RFC 5646 / BCP 47",
        description="Matches primary language subtags with optional script and required region subtag.",
        pattern=r"[a-z]{2,3}(?:-[A-Z][a-z]{3})?-(?:[A-Z]{2}|[0-9]{3})",
        max_length=35,
        positive_cases=("en-US", "en-GB", "zh-Hans-CN", "es-419", "pt-BR"),
        negative_cases=("EN-us", "english", "en_US", "e", "en-USA"),
        extraction_text="Locales en-US and zh-Hans-CN enabled.",
        expected_extractions=("en-US", "zh-Hans-CN"),
    ),
    RegexRecipeSpec(
        recipe_id="iana-timezone-name",
        title="IANA tzdb Area/Location timezone identifier validator",
        standard="IANA Time Zone Database",
        description="Matches Area/Location (or Area/Region/City) IANA timezone names and UTC.",
        pattern=r"(?:UTC|Etc/UTC|(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)/[A-Z][A-Za-z0-9_+-]{1,30}(?:/[A-Z][A-Za-z0-9_+-]{1,30})?)",
        max_length=64,
        positive_cases=("UTC", "America/New_York", "Europe/London", "Asia/Tokyo", "America/Indiana/Indianapolis"),
        negative_cases=("EST", "GMT+5", "america/new_york", "Mars/Olympus", "America/"),
        extraction_text="Convert from America/New_York to Asia/Tokyo.",
        expected_extractions=("America/New_York", "Asia/Tokyo"),
    ),
    RegexRecipeSpec(
        recipe_id="isbn-13-hyphenated",
        title="ISO 2108 ISBN-13 identifier validator",
        standard="ISO 2108",
        description="Matches 13-digit ISBN identifiers starting with 978 or 979.",
        pattern=r"97[89]-[0-9]{1,5}-[0-9]{1,7}-[0-9]{1,6}-[0-9]",
        max_length=17,
        positive_cases=("978-0-306-40615-7", "978-1-492-05136-7", "979-10-90636-07-1", "978-3-16-148410-0", "978-0-13-110362-7"),
        negative_cases=("977-0-306-40615-7", "9780306406157", "0-306-40615-2", "978-0-306-40615-X", "978-0-306"),
        extraction_text="Books 978-0-306-40615-7 and 978-3-16-148410-0.",
        expected_extractions=("978-0-306-40615-7", "978-3-16-148410-0"),
    ),
    RegexRecipeSpec(
        recipe_id="issn-identifier",
        title="ISO 3297 ISSN serial identifier validator",
        standard="ISO 3297",
        description="Matches 8-character ISSN strings formatted as NNNN-NNNC where C is a digit or X.",
        pattern=r"[0-9]{4}-[0-9]{3}[0-9X]",
        max_length=9,
        positive_cases=("0378-5955", "2434-561X", "0028-0836", "1548-7660", "2049-3630"),
        negative_cases=("03785955", "0378-595x", "0378-595A", "037-5955", "0378-59555"),
        extraction_text="Journals 0378-5955 and 2434-561X.",
        expected_extractions=("0378-5955", "2434-561X"),
    ),
    RegexRecipeSpec(
        recipe_id="doi-identifier",
        title="ISO 26324 Digital Object Identifier (DOI) validator",
        standard="ISO 26324",
        description="Matches DOI strings starting with 10.<registrant>/<suffix>.",
        pattern=r"10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]*[A-Za-z0-9]",
        max_length=128,
        positive_cases=("10.1000/182", "10.1038/nphys1170", "10.1145/3292500.3330701", "10.48550/arXiv.2301.00001", "10.1109/5.771073"),
        negative_cases=("11.1000/182", "10.12/182", "doi:10.1000/182", "10.1000/", "10.1000/bad space"),
        extraction_text="Cite 10.1038/nphys1170 and 10.1145/3292500.3330701.",
        expected_extractions=("10.1038/nphys1170", "10.1145/3292500.3330701"),
    ),
    RegexRecipeSpec(
        recipe_id="orcid-identifier",
        title="ISO 27729 ORCID researcher identifier validator",
        standard="ISO 27729",
        description="Matches 16-character hyphenated ORCID identifiers (0000-000X-XXXX-XXXC).",
        pattern=r"0000-000[1-9]-[0-9]{4}-[0-9]{3}[0-9X]",
        max_length=19,
        positive_cases=(
            "0000-0002-1825-0097",
            "0000-0001-5109-3700",
            "0000-0002-1694-233X",
            "0000-0003-1415-9265",
            "0000-0009-0001-2345",
        ),
        negative_cases=("0000-0000-1825-0097", "0000000218250097", "0000-0002-1825-009A", "1234-5678-1234-5678", "0000-0002-1825"),
        extraction_text="Authors 0000-0002-1825-0097 and 0000-0002-1694-233X.",
        expected_extractions=("0000-0002-1825-0097", "0000-0002-1694-233X"),
    ),
    RegexRecipeSpec(
        recipe_id="swift-bic-code",
        title="ISO 9362 SWIFT / BIC code validator",
        standard="ISO 9362",
        description="Matches 8-character or 11-character uppercase SWIFT Business Identifier Codes.",
        pattern=r"[A-Z]{6}[A-Z2-9][A-NP-Z0-9](?:[A-Z0-9]{3})?",
        max_length=11,
        positive_cases=("DEUTDEFF", "DEUTDEFF500", "CHASUS33", "BOFAUS3NXXX", "BNPAFRPP"),
        negative_cases=("deutdeff", "DEUTDE", "DEUTDEFF12", "12345678", "DEUTDE00"),
        extraction_text="Route via DEUTDEFF500 or CHASUS33.",
        expected_extractions=("DEUTDEFF500", "CHASUS33"),
    ),
    RegexRecipeSpec(
        recipe_id="iso6166-isin",
        title="ISO 6166 International Securities Identification Number (ISIN) validator",
        standard="ISO 6166",
        description="Matches 12-character ISIN codes (2-letter country code, 9 alphanumeric NSIN, 1 check digit).",
        pattern=r"[A-Z]{2}[A-Z0-9]{9}[0-9]",
        max_length=12,
        positive_cases=("US0378331005", "US5949181045", "GB0002634946", "DE0007164600", "JP3633400001"),
        negative_cases=("us0378331005", "US037833100A", "120378331005", "US037833100", "US03783310059"),
        extraction_text="Tickers US0378331005 and GB0002634946.",
        expected_extractions=("US0378331005", "GB0002634946"),
    ),
    RegexRecipeSpec(
        recipe_id="iso17442-lei",
        title="ISO 17442 Legal Entity Identifier (LEI) validator",
        standard="ISO 17442",
        description="Matches 20-character alphanumeric Legal Entity Identifiers ending in two check digits.",
        pattern=r"[0-9A-Z]{18}[0-9]{2}",
        max_length=20,
        positive_cases=(
            "5493001KJTIIGC8Y1R12",
            "7ZW8QJWVPR4P1J1KQY45",
            "HWUPKR0MPOU8FGXBT394",
            "213800D1EI4B9WTWWD28",
            "529900T8BM49AURSDO55",
        ),
        negative_cases=("5493001KJTIIGC8Y1R1A", "5493001KJTIIGC8Y1R1", "5493001kjtiigc8y1r12", "5493001KJTIIGC8Y1R123", "SHORTLEI12"),
        extraction_text="Entities 5493001KJTIIGC8Y1R12 and HWUPKR0MPOU8FGXBT394.",
        expected_extractions=("5493001KJTIIGC8Y1R12", "HWUPKR0MPOU8FGXBT394"),
    ),
    RegexRecipeSpec(
        recipe_id="rfc6901-json-pointer",
        title="RFC 6901 JSON Pointer validator",
        standard="RFC 6901",
        description="Matches non-empty RFC 6901 JSON Pointers starting with / and using ~0 / ~1 escapes.",
        pattern=r"(?:/(?:[A-Za-z0-9_.-]|~[01])+)+",
        max_length=128,
        positive_cases=("/foo", "/foo/0", "/a~1b", "/m~0n", "/paths/~1users/get"),
        negative_cases=("foo/bar", "/a~2b", "/a~", "http://example.com", "relative"),
        extraction_text="Patch /foo/0 and /paths/~1users/get",
        expected_extractions=("/foo/0", "/paths/~1users/get"),
    ),
    RegexRecipeSpec(
        recipe_id="rfc7519-jwt-compact",
        title="RFC 7519 compact JSON Web Token structure validator",
        standard="RFC 7519",
        description="Matches 3-segment base64url-encoded JWT strings (header.payload.signature).",
        pattern=r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{10,}",
        max_length=512,
        positive_cases=(
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJiYWx0b3IifQ.abcdef1234567890_-ABCDEF",
            "eyJhbGciOiJFZERTQSJ9.eyJhdWQiOiJhcGkifQ.0123456789abcdef0123456789abcdef",
            "eyJhbGciOiJFUzI1NiJ9.eyJleHAiOjE3MDAwMDAwMDB9.signature_segment_12345",
            "eyJraWQiOiJrMSIsImFsZyI6IkhTMjU2In0.eyJ1c2VyIjoiYWRhIn0.valid_base64url_sig_99",
        ),
        negative_cases=("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ", "not.a.jwt", "eyJ.eyJ.short", "eyJhbGciOiJIUzI1NiJ9.notbase64!.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV", "a.b.c.d"),
        extraction_text="Tokens eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c and eyJhbGciOiJFZERTQSJ9.eyJhdWQiOiJhcGkifQ.0123456789abcdef0123456789abcdef.",
        expected_extractions=(
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "eyJhbGciOiJFZERTQSJ9.eyJhdWQiOiJhcGkifQ.0123456789abcdef0123456789abcdef",
        ),
    ),
    RegexRecipeSpec(
        recipe_id="ulid-identifier",
        title="Crockford Base32 26-character ULID validator",
        standard="ULID Specification",
        description="Matches 26-character Crockford Base32 Universally Unique Lexicographically Sortable Identifiers.",
        pattern=r"[0-7][0-9A-HJKMNP-TV-Z]{25}",
        max_length=26,
        positive_cases=(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "01H5Z8PK000000000000000000",
            "01J9Z2M4N6P8Q0R2S4T6V8W0X2",
            "01BX5ZZKBKACTAV9WEVGEMMVRY",
            "7ZZZZZZZZZZZZZZZZZZZZZZZZZ",
        ),
        negative_cases=(
            "81ARZ3NDEKTSV4RRFFQ69G5FAV",
            "01ARZ3NDEKTSV4RRFFQ69G5FA",
            "01ARZ3NDEKTSV4RRFFQ69G5FIL",
            "01arz3ndektsv4rrffq69g5fav",
            "01ARZ3NDEKTSV4RRFFQ69G5FAV1",
        ),
        extraction_text="Records 01ARZ3NDEKTSV4RRFFQ69G5FAV and 01BX5ZZKBKACTAV9WEVGEMMVRY.",
        expected_extractions=("01ARZ3NDEKTSV4RRFFQ69G5FAV", "01BX5ZZKBKACTAV9WEVGEMMVRY"),
    ),
    RegexRecipeSpec(
        recipe_id="mongodb-objectid",
        title="BSON 24-character hexadecimal ObjectId validator",
        standard="BSON ObjectId Spec",
        description="Matches 24-character hexadecimal BSON/MongoDB ObjectIds.",
        pattern=r"[0-9a-f]{24}",
        max_length=24,
        positive_cases=(
            "507f1f77bcf86cd799439011",
            "507f191e810c19729de860ea",
            "000000000000000000000000",
            "6529a1b2c3d4e5f60718293a",
            "ffffffffffffffffffffffff",
        ),
        negative_cases=("507f1f77bcf86cd79943901", "507f1f77bcf86cd7994390111", "507f1f77bcf86cd79943901g", "507F1F77BCF86CD799439011", "short"),
        extraction_text="Keys 507f1f77bcf86cd799439011 and 507f191e810c19729de860ea.",
        expected_extractions=("507f1f77bcf86cd799439011", "507f191e810c19729de860ea"),
    ),
    RegexRecipeSpec(
        recipe_id="geohash-base32",
        title="Geohash Base32 spatial string validator",
        standard="Geohash Public Domain Spec",
        description="Matches 4-to-12 character geohash strings using the geohash Base32 alphabet (excluding a, i, l, o).",
        pattern=r"[0-9bcdefghjkmnpqrstuvwxyz]{4,12}",
        max_length=12,
        positive_cases=("9q8yyk8yuv", "u4pruydqqvj", "dr5regw", "gcpvj0du6", "ezs42"),
        negative_cases=("abcde", "9q8yyi", "9q8yyo", "9Q8YYK", "9q8yyk8yuv1234"),
        extraction_text="Cells: 9q8yyk8yuv, u4pruydqqvj",
        expected_extractions=("9q8yyk8yuv", "u4pruydqqvj"),
    ),
    RegexRecipeSpec(
        recipe_id="h3-cell-index",
        title="H3 15-character hexadecimal spatial cell index validator",
        standard="H3 Spatial Index",
        description="Matches 15-character lowercase hex H3 cell indexes starting with 8.",
        pattern=r"8[0-9a-f]{14}",
        max_length=15,
        positive_cases=(
            "8928308280fffff",
            "8a2a1072b59ffff",
            "85283473fffffff",
            "872830828ffffff",
            "8c2830828056dff",
        ),
        negative_cases=("7928308280fffff", "8928308280ffff", "8928308280ffffff", "8928308280FFFFF", "8928308280ggggg"),
        extraction_text="Hexagons 8928308280fffff and 8a2a1072b59ffff.",
        expected_extractions=("8928308280fffff", "8a2a1072b59ffff"),
    ),
    RegexRecipeSpec(
        recipe_id="plus-code-olc",
        title="Open Location Code (Plus Code) full validator",
        standard="Open Location Code",
        description="Matches full 8+2 or 8+3 character Open Location Codes using the 20-character OLC alphabet.",
        pattern=r"[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,3}",
        max_length=12,
        positive_cases=("849VCWC8+R9", "8FVC9G8F+6W", "9C3XGV4P+22", "87G8Q2JM+HV", "8Q7XMP2J+34X"),
        negative_cases=("849VCWC8R9", "849VCWC+R9", "149VCWC8+R9", "849VCWC8+R", "849vcwc8+r9"),
        extraction_text="Coordinates 849VCWC8+R9 and 8FVC9G8F+6W.",
        expected_extractions=("849VCWC8+R9", "8FVC9G8F+6W"),
    ),
    RegexRecipeSpec(
        recipe_id="maidenhead-locator",
        title="Maidenhead Locator System grid square validator",
        standard="IARU Maidenhead Locator",
        description="Matches 4-character or 6-character Maidenhead grid locators (e.g. FN31pr).",
        pattern=r"[A-R]{2}[0-9]{2}(?:[a-x]{2})?",
        max_length=6,
        positive_cases=("FN31pr", "IO91wm", "CM87ts", "JN58td", "QF56"),
        negative_cases=("SZ31pr", "FN31yz", "fn31pr", "FN3", "FN31p"),
        extraction_text="Stations at FN31pr and IO91wm.",
        expected_extractions=("FN31pr", "IO91wm"),
    ),
    RegexRecipeSpec(
        recipe_id="spiffe-id-uri",
        title="SPIFFE workload identity URI validator",
        standard="SPIFFE Identity and Verifiable Identity Document",
        description="Matches spiffe://<trust-domain>/<workload-path> URIs.",
        pattern=r"spiffe://[a-z0-9._-]+(?:/[A-Za-z0-9_-]+)+",
        max_length=255,
        positive_cases=(
            "spiffe://example.org/ns/prod/sa/web",
            "spiffe://baltor.internal/worker/dag-runner",
            "spiffe://cluster.local/service/api",
            "spiffe://trust.domain/app/v1",
            "spiffe://corp.net/region/us-east/node-1",
        ),
        negative_cases=("https://example.org/ns/prod", "spiffe://example.org", "spiffe://Example.Org/app", "spiffe:///app", "spiffe://example.org/app/"),
        extraction_text="Identities spiffe://example.org/ns/prod/sa/web and spiffe://baltor.internal/worker/dag-runner.",
        expected_extractions=("spiffe://example.org/ns/prod/sa/web", "spiffe://baltor.internal/worker/dag-runner"),
    ),
    RegexRecipeSpec(
        recipe_id="python-pep508-package-name",
        title="Python PEP 508 hyphenated distribution name validator",
        standard="PEP 508 / PEP 503",
        description="Matches normalized lowercase hyphenated Python distribution names.",
        pattern=r"[a-z0-9]+(?:-[a-z0-9]+)+",
        max_length=100,
        positive_cases=("loop-engine", "pydantic-core", "google-genai", "pytest-asyncio", "uvicorn-worker"),
        negative_cases=("Loop-Engine", "loop_engine", "loop--engine", "-loop", "loop-"),
        extraction_text="Install loop-engine and google-genai.",
        expected_extractions=("loop-engine", "google-genai"),
    ),
)


def check_redos_safety(pattern_str: str, max_length: int = 256, timeout_seconds: float = 1.0) -> dict[str, Any]:
    """Measure fixed examples of registered patterns, not a linear-time proof or a timeout sandbox."""
    if pattern_str not in {spec.pattern for spec in REGEX_RECIPES}:
        raise ValueError("unregistered_pattern_requires_sandbox_qualification")
    compiled = re.compile(pattern_str)
    adversarial_inputs = [
        "a" * 10240 + "!",
        "0" * 10240 + "!",
        "a1-" * 3400 + "!",
        "https://" + "a." * 5000 + "!",
    ]
    max_elapsed = 0.0
    for sample in adversarial_inputs:
        t0 = time.perf_counter()
        _ = compiled.fullmatch(sample)
        elapsed = time.perf_counter() - t0
        if elapsed > max_elapsed:
            max_elapsed = elapsed
    return {
        "safe": max_elapsed < timeout_seconds,
        "max_elapsed_seconds": round(max_elapsed, 6),
        "timeout_seconds": timeout_seconds,
        "adversarial_bytes_tested": 10240,
    }


def execute_regex_recipe(recipe_id: str, text: str, *, mode: str = "validate") -> dict[str, Any]:
    """Execute a regex recipe in-memory for either fullmatch validation or substring extraction."""
    spec_map = {item.recipe_id: item for item in REGEX_RECIPES}
    if recipe_id not in spec_map:
        raise KeyError(f"unknown_regex_recipe: {recipe_id!r}")
    spec = spec_map[recipe_id]
    if not isinstance(text, str):
        raise ValueError("input_must_be_string")
    compiled = re.compile(spec.pattern)
    if mode == "validate":
        if not (1 <= len(text) <= spec.max_length):
            return {"recipe_id": recipe_id, "valid": False, "reason": "length_out_of_bounds"}
        matched = compiled.fullmatch(text) is not None
        return {"recipe_id": recipe_id, "valid": matched, "reason": "matched" if matched else "pattern_mismatch"}
    if mode == "extract":
        if len(text) > 65536:
            raise ValueError("extract_text_too_large")
        matches = [m.group(0) for m in compiled.finditer(text) if 1 <= len(m.group(0)) <= spec.max_length]
        return {"recipe_id": recipe_id, "matches": matches, "count": len(matches)}
    raise ValueError(f"unsupported_mode: {mode!r}")


def _render_pattern_py(spec: RegexRecipeSpec) -> bytes:
    code = f'''"""{spec.title} ({spec.standard}).

{spec.description}
Deterministic stdlib re implementation with anchored fullmatch validation and
bounded extraction. No network, file, or model calls.
"""
from __future__ import annotations

import re

RECIPE_ID = {spec.recipe_id!r}
STANDARD = {spec.standard!r}
PATTERN_TEXT = {spec.pattern!r}
MAX_LENGTH = {spec.max_length!r}
COMPILED_PATTERN = re.compile(PATTERN_TEXT)


def validate(value: str) -> dict:
    """Return {{"valid": bool, "recipe_id": str, "reason": str}} using fullmatch."""
    if not isinstance(value, str):
        raise ValueError("invalid_input_type: expected str")
    if not (1 <= len(value) <= MAX_LENGTH):
        return {{"recipe_id": RECIPE_ID, "valid": False, "reason": "length_out_of_bounds"}}
    matched = COMPILED_PATTERN.fullmatch(value) is not None
    return {{"recipe_id": RECIPE_ID, "valid": matched, "reason": "matched" if matched else "pattern_mismatch"}}


def extract(text: str) -> dict:
    """Extract all bounded matches of the pattern from text."""
    if not isinstance(text, str):
        raise ValueError("invalid_input_type: expected str")
    if len(text) > 65536:
        raise ValueError("input_text_exceeds_65536_bytes")
    matches = [m.group(0) for m in COMPILED_PATTERN.finditer(text) if 1 <= len(m.group(0)) <= MAX_LENGTH]
    return {{"recipe_id": RECIPE_ID, "matches": matches, "count": len(matches)}}
'''
    return code.encode("utf-8")


def _render_test_pattern_py(spec: RegexRecipeSpec) -> bytes:
    code = f'''"""Deterministic conformance tests for regex recipe {spec.recipe_id}."""
from __future__ import annotations

import time
import unittest
from pattern import COMPILED_PATTERN, MAX_LENGTH, extract, validate

POSITIVE_CASES = {list(spec.positive_cases)!r}
NEGATIVE_CASES = {list(spec.negative_cases)!r}
EXTRACTION_TEXT = {spec.extraction_text!r}
EXPECTED_EXTRACTIONS = {list(spec.expected_extractions)!r}


class RegexRecipeTests(unittest.TestCase):
    def test_positive_cases_match(self) -> None:
        for sample in POSITIVE_CASES:
            with self.subTest(sample=sample):
                res = validate(sample)
                self.assertTrue(res["valid"], f"Expected positive case to match: {{sample!r}}")

    def test_negative_cases_rejected(self) -> None:
        for sample in NEGATIVE_CASES:
            with self.subTest(sample=sample):
                res = validate(sample)
                self.assertFalse(res["valid"], f"Expected negative case to fail: {{sample!r}}")

    def test_boundary_and_fixed_adversarial_examples(self) -> None:
        self.assertFalse(validate("")["valid"])
        self.assertFalse(validate("a" * (MAX_LENGTH + 5))["valid"])
        t0 = time.perf_counter()
        _ = COMPILED_PATTERN.fullmatch("a" * 10240 + "!")
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 1.0)

    def test_extraction_matches_expected(self) -> None:
        extracted = extract(EXTRACTION_TEXT)
        self.assertEqual(extracted["matches"], EXPECTED_EXTRACTIONS)

    def test_known_wrong_control_fails(self) -> None:
        wrong_result = validate(NEGATIVE_CASES[0])
        with self.assertRaises(AssertionError):
            self.assertTrue(wrong_result["valid"])


if __name__ == "__main__":
    unittest.main()
'''
    return code.encode("utf-8")


def _render_skill_md(spec: RegexRecipeSpec) -> bytes:
    text = (
        f"---\n"
        f"name: regex-{spec.recipe_id}\n"
        f"description: {spec.description}\n"
        f"---\n\n"
        f"# {spec.title}\n\n"
        f"Standard: {spec.standard}.\n\n"
        f"## When to use\n\n"
        f"Use this recipe to validate or extract `{spec.recipe_id}` strings deterministically "
        f"with Python's standard `re` library and a maximum input bound of {spec.max_length} characters.\n\n"
        f"## Pattern\n\n"
        f"```python\n{spec.pattern}\n```\n"
        f"\nLexical matching only: checksums, calendar validity, assigned identifiers and complete standards compliance are not checked. "
        f"Extraction can match substrings inside larger tokens. Test your boundary requirements before reuse.\n"
    )
    return text.encode("utf-8")


def _render_integration_md(spec: RegexRecipeSpec, harness_name: str) -> bytes:
    text = (
        f"# {spec.title} ({harness_name} integration)\n\n"
        f"Import `validate` and `extract` from `pattern.py` to validate or extract `{spec.recipe_id}` "
        f"values in `{harness_name}` without external dependencies or model calls.\n"
    )
    return text.encode("utf-8")


def build_regex_component(spec_or_id: RegexRecipeSpec | str) -> dict[str, Any]:
    """Build a local package preview, not a library admission record for a regex recipe."""
    if isinstance(spec_or_id, str):
        spec_map = {item.recipe_id: item for item in REGEX_RECIPES}
        if spec_or_id not in spec_map:
            raise KeyError(f"unknown_regex_recipe: {spec_or_id!r}")
        spec = spec_map[spec_or_id]
    else:
        spec = spec_or_id
    if not isinstance(spec, RegexRecipeSpec) or spec not in REGEX_RECIPES:
        raise ValueError("unregistered_factory_spec")

    attribution = (
        f"# Attribution\n\n"
        f"Generated deterministically by `{FACTORY_ID}` version `{FACTORY_VERSION}` on {GENERATED_ON}.\n"
        f"Format reference: {spec.standard}; original lexical approximation, not copied specification text.\n"
        f"Licence: MIT.\n"
    ).encode("utf-8")

    raw_files = [
        ("pattern.py", _render_pattern_py(spec), "text/x-python", "skill_script"),
        ("test_pattern.py", _render_test_pattern_py(spec), "text/x-python", "skill_reference"),
        ("SKILL.md", _render_skill_md(spec), "text/markdown", "skill_definition"),
        ("integrate/claude-code.md", _render_integration_md(spec, "claude_code"), "text/markdown", "skill_reference"),
        ("integrate/codex.md", _render_integration_md(spec, "codex"), "text/markdown", "skill_reference"),
        ("integrate/cursor.md", _render_integration_md(spec, "cursor"), "text/markdown", "skill_reference"),
        ("integrate/opencode.md", _render_integration_md(spec, "opencode"), "text/markdown", "skill_reference"),
        ("LICENSE", MIT_LICENSE_TEXT.encode("utf-8"), "text/plain", "other"),
        ("ATTRIBUTION.md", attribution, "text/markdown", "other"),
    ]

    entries: list[CataloguePackageFile] = []
    file_bodies: dict[str, bytes] = {}
    for path, data, mtype, role in raw_files:
        file_bodies[path] = data
        entries.append(CataloguePackageFile(path, sha256_hex(data), len(data), mtype, role))

    package = CataloguePackage(tuple(entries), PACKAGE_BODY)
    return {
        "build_state": "local_package_preview",
        "admission_ready": False,
        "factory_id": FACTORY_ID,
        "component_id": f"regex-{spec.recipe_id}",
        "recipe_id": spec.recipe_id,
        "title": spec.title,
        "standard": spec.standard,
        "description": spec.description,
        "licence": "MIT",
        "catalogue_package": package.to_dict(),
        "package_digest": package.package_digest,
        "file_bodies": file_bodies,
        "approved": False,
        "published": False,
        "effects_granted": [],
        "lifecycle": "candidate",
        "qualification": "not_independently_reviewed",
    }


def verify_regex_component(component: dict[str, Any]) -> dict[str, Any]:
    """Execute the generated pattern.py and verify positive, negative, extraction, ReDoS, and known-wrong controls."""
    recipe_id = component["recipe_id"]
    spec = {item.recipe_id: item for item in REGEX_RECIPES}[recipe_id]
    canonical = build_regex_component(recipe_id)
    if component != canonical:
        raise ValueError("noncanonical_factory_package")
    namespace: dict[str, Any] = {}
    exec(compile(canonical["file_bodies"]["pattern.py"].decode("utf-8"), "pattern.py", "exec"), namespace)
    validate_fn = namespace["validate"]
    extract_fn = namespace["extract"]

    pos_ok = all(validate_fn(case)["valid"] is True for case in spec.positive_cases)
    neg_ok = all(validate_fn(case)["valid"] is False for case in spec.negative_cases)
    ext_res = extract_fn(spec.extraction_text)
    ext_ok = tuple(ext_res["matches"]) == spec.expected_extractions
    redos = check_redos_safety(spec.pattern, spec.max_length)
    known_wrong_caught = validate_fn(spec.negative_cases[0])["valid"] is False

    passed = bool(pos_ok and neg_ok and ext_ok and redos["safe"] and known_wrong_caught)
    return {
        "component_id": component["component_id"],
        "passed": passed,
        "positive_cases_passed": pos_ok,
        "negative_cases_rejected": neg_ok,
        "extraction_matched": ext_ok,
        "redos_safe": redos["safe"],
        "max_redos_seconds": redos["max_elapsed_seconds"],
        "known_wrong_control_passed": known_wrong_caught,
    }


def build_all_regex_components() -> list[dict[str, Any]]:
    """Build all 50 deterministic regex recipe components."""
    return [build_regex_component(spec) for spec in REGEX_RECIPES]


__all__ = [
    "FACTORY_ID",
    "FACTORY_VERSION",
    "RegexRecipeSpec",
    "REGEX_RECIPES",
    "check_redos_safety",
    "execute_regex_recipe",
    "build_regex_component",
    "verify_regex_component",
    "build_all_regex_components",
]
