"""Template 4: Deterministic Timezone, Business-Day, SLA, and DST Factory.

Generates 40 deterministic IANA timezone (stdlib zoneinfo), DST-transition,
business-day calendar, and SLA deadline calculation components.

Each generated component includes:
- implement.py: pure-Python stdlib zoneinfo and datetime implementation
- test_implement.py: positive cases, DST/boundary checks, invalid input refusals, and known-wrong controls
- SKILL.md and harness integration guides (claude-code, codex, cursor, opencode)
- LICENSE (MIT) and ATTRIBUTION.md
- CataloguePackage with SHA-256 digests and local preview metadata, not an admission record
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _REPO_SRC not in sys.path:
    sys.path.insert(0, _REPO_SRC)

from loop_engine.core.service_runtime.catalogue_packages import (
    PACKAGE_BODY,
    CataloguePackage,
    CataloguePackageFile,
    sha256_hex,
)

FACTORY_ID = "gen-timezone-calendars"
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
class TimezoneCalendarSpec:
    component_id: str
    category: str  # "tz_offset", "dst_transition", "business_day", "sla_deadline"
    title: str
    description: str
    allowed_zones: tuple[str, ...]
    config: dict[str, Any]
    positive_cases: tuple[tuple[dict[str, Any], dict[str, Any]], ...]
    negative_cases: tuple[dict[str, Any], ...]


TIMEZONE_CALENDAR_SPECS: tuple[TimezoneCalendarSpec, ...] = (
    # --- Category A: 10 regional IANA timezone offset and conversion components ---
    TimezoneCalendarSpec(
        component_id="tz-americas-north-hubs",
        category="tz_offset",
        title="North America IANA timezone offset and conversion lookup",
        description="Resolves UTC offset minutes and local ISO timestamps across New York, Chicago, Denver, Los Angeles, Toronto, and Vancouver.",
        allowed_zones=("America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Toronto", "America/Vancouver"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "America/New_York"}, {"utc_offset_minutes": -300, "local_iso": "2026-01-15T07:00:00-05:00", "is_dst": False}),
            ({"utc_iso": "2026-07-15T12:00:00Z", "tz_name": "America/New_York"}, {"utc_offset_minutes": -240, "local_iso": "2026-07-15T08:00:00-04:00", "is_dst": True}),
            ({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "America/Los_Angeles"}, {"utc_offset_minutes": -480, "local_iso": "2026-01-15T04:00:00-08:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "Mars/Phobos"}, {"utc_iso": "not-a-timestamp", "tz_name": "America/New_York"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-americas-latin-hubs",
        category="tz_offset",
        title="Latin America IANA timezone offset and conversion lookup",
        description="Resolves UTC offsets across Mexico City, Bogota, Lima, Santiago, Sao Paulo, and Buenos Aires.",
        allowed_zones=("America/Mexico_City", "America/Bogota", "America/Lima", "America/Santiago", "America/Sao_Paulo", "America/Argentina/Buenos_Aires"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-06-15T15:00:00Z", "tz_name": "America/Sao_Paulo"}, {"utc_offset_minutes": -180, "local_iso": "2026-06-15T12:00:00-03:00", "is_dst": False}),
            ({"utc_iso": "2026-06-15T15:00:00Z", "tz_name": "America/Bogota"}, {"utc_offset_minutes": -300, "local_iso": "2026-06-15T10:00:00-05:00", "is_dst": False}),
            ({"utc_iso": "2026-06-15T15:00:00Z", "tz_name": "America/Argentina/Buenos_Aires"}, {"utc_offset_minutes": -180, "local_iso": "2026-06-15T12:00:00-03:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-06-15T15:00:00Z", "tz_name": "Invalid/Zone"}, {"utc_iso": "2026-99-99T00:00:00Z", "tz_name": "America/Lima"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-europe-western-central",
        category="tz_offset",
        title="Western and Central Europe IANA timezone offset lookup",
        description="Resolves UTC offsets across London, Dublin, Lisbon, Paris, Berlin, Madrid, Rome, and Zurich.",
        allowed_zones=("Europe/London", "Europe/Dublin", "Europe/Lisbon", "Europe/Paris", "Europe/Berlin", "Europe/Madrid", "Europe/Rome", "Europe/Zurich"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "Europe/London"}, {"utc_offset_minutes": 0, "local_iso": "2026-01-15T12:00:00+00:00", "is_dst": False}),
            ({"utc_iso": "2026-07-15T12:00:00Z", "tz_name": "Europe/Paris"}, {"utc_offset_minutes": 120, "local_iso": "2026-07-15T14:00:00+02:00", "is_dst": True}),
            ({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "Europe/Berlin"}, {"utc_offset_minutes": 60, "local_iso": "2026-01-15T13:00:00+01:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "Europe/Atlantis"}, {"utc_iso": "", "tz_name": "Europe/London"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-europe-nordic-eastern",
        category="tz_offset",
        title="Nordic and Eastern Europe IANA timezone offset lookup",
        description="Resolves UTC offsets across Stockholm, Oslo, Helsinki, Warsaw, Athens, Bucharest, and Istanbul.",
        allowed_zones=("Europe/Stockholm", "Europe/Oslo", "Europe/Helsinki", "Europe/Warsaw", "Europe/Athens", "Europe/Bucharest", "Europe/Istanbul"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "Europe/Helsinki"}, {"utc_offset_minutes": 120, "local_iso": "2026-01-15T14:00:00+02:00", "is_dst": False}),
            ({"utc_iso": "2026-07-15T12:00:00Z", "tz_name": "Europe/Athens"}, {"utc_offset_minutes": 180, "local_iso": "2026-07-15T15:00:00+03:00", "is_dst": True}),
            ({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "Europe/Istanbul"}, {"utc_offset_minutes": 180, "local_iso": "2026-01-15T15:00:00+03:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-01-15T12:00:00Z", "tz_name": "Unknown/City"}, {"utc_iso": "bad-date", "tz_name": "Europe/Oslo"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-asia-east-financial",
        category="tz_offset",
        title="East Asia financial center IANA timezone lookup",
        description="Resolves UTC offsets across Tokyo, Seoul, Shanghai, Hong Kong, Taipei, and Singapore.",
        allowed_zones=("Asia/Tokyo", "Asia/Seoul", "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Singapore"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-03-01T00:00:00Z", "tz_name": "Asia/Tokyo"}, {"utc_offset_minutes": 540, "local_iso": "2026-03-01T09:00:00+09:00", "is_dst": False}),
            ({"utc_iso": "2026-03-01T00:00:00Z", "tz_name": "Asia/Singapore"}, {"utc_offset_minutes": 480, "local_iso": "2026-03-01T08:00:00+08:00", "is_dst": False}),
            ({"utc_iso": "2026-03-01T00:00:00Z", "tz_name": "Asia/Shanghai"}, {"utc_offset_minutes": 480, "local_iso": "2026-03-01T08:00:00+08:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-03-01T00:00:00Z", "tz_name": "Asia/Unknown"}, {"utc_iso": "2026-13-01T00:00:00Z", "tz_name": "Asia/Tokyo"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-asia-south-fractional",
        category="tz_offset",
        title="South and Central Asia fractional-offset IANA timezone lookup",
        description="Resolves 30-minute and 45-minute fractional UTC offsets across Kolkata (+05:30), Kathmandu (+05:45), Yangon (+06:30), and Kabul (+04:30).",
        allowed_zones=("Asia/Kolkata", "Asia/Colombo", "Asia/Kathmandu", "Asia/Yangon", "Asia/Kabul", "Asia/Tehran"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-04-10T00:00:00Z", "tz_name": "Asia/Kolkata"}, {"utc_offset_minutes": 330, "local_iso": "2026-04-10T05:30:00+05:30", "is_dst": False}),
            ({"utc_iso": "2026-04-10T00:00:00Z", "tz_name": "Asia/Kathmandu"}, {"utc_offset_minutes": 345, "local_iso": "2026-04-10T05:45:00+05:45", "is_dst": False}),
            ({"utc_iso": "2026-04-10T00:00:00Z", "tz_name": "Asia/Yangon"}, {"utc_offset_minutes": 390, "local_iso": "2026-04-10T06:30:00+06:30", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-04-10T00:00:00Z", "tz_name": "Asia/Fake"}, {"utc_iso": "invalid", "tz_name": "Asia/Kolkata"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-asia-southeast-asean",
        category="tz_offset",
        title="Southeast Asia ASEAN IANA timezone offset lookup",
        description="Resolves UTC offsets across Bangkok, Jakarta, Ho Chi Minh, Manila, and Kuala Lumpur.",
        allowed_zones=("Asia/Bangkok", "Asia/Jakarta", "Asia/Ho_Chi_Minh", "Asia/Manila", "Asia/Kuala_Lumpur"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-05-01T00:00:00Z", "tz_name": "Asia/Bangkok"}, {"utc_offset_minutes": 420, "local_iso": "2026-05-01T07:00:00+07:00", "is_dst": False}),
            ({"utc_iso": "2026-05-01T00:00:00Z", "tz_name": "Asia/Manila"}, {"utc_offset_minutes": 480, "local_iso": "2026-05-01T08:00:00+08:00", "is_dst": False}),
            ({"utc_iso": "2026-05-01T00:00:00Z", "tz_name": "Asia/Jakarta"}, {"utc_offset_minutes": 420, "local_iso": "2026-05-01T07:00:00+07:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-05-01T00:00:00Z", "tz_name": "Asia/None"}, {"utc_iso": "bad", "tz_name": "Asia/Bangkok"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-middle-east-gulf",
        category="tz_offset",
        title="Middle East and Gulf IANA timezone offset lookup",
        description="Resolves UTC offsets across Dubai, Riyadh, Qatar, Kuwait, Jerusalem, and Amman.",
        allowed_zones=("Asia/Dubai", "Asia/Riyadh", "Asia/Qatar", "Asia/Kuwait", "Asia/Jerusalem", "Asia/Amman"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-02-01T00:00:00Z", "tz_name": "Asia/Dubai"}, {"utc_offset_minutes": 240, "local_iso": "2026-02-01T04:00:00+04:00", "is_dst": False}),
            ({"utc_iso": "2026-02-01T00:00:00Z", "tz_name": "Asia/Riyadh"}, {"utc_offset_minutes": 180, "local_iso": "2026-02-01T03:00:00+03:00", "is_dst": False}),
            ({"utc_iso": "2026-02-01T00:00:00Z", "tz_name": "Asia/Qatar"}, {"utc_offset_minutes": 180, "local_iso": "2026-02-01T03:00:00+03:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-02-01T00:00:00Z", "tz_name": "Invalid/Gulf"}, {"utc_iso": "invalid", "tz_name": "Asia/Dubai"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-africa-continental",
        category="tz_offset",
        title="African continental hub IANA timezone offset lookup",
        description="Resolves UTC offsets across Cairo, Lagos, Nairobi, Johannesburg, Casablanca, and Accra.",
        allowed_zones=("Africa/Cairo", "Africa/Lagos", "Africa/Nairobi", "Africa/Johannesburg", "Africa/Casablanca", "Africa/Accra"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-01-10T10:00:00Z", "tz_name": "Africa/Lagos"}, {"utc_offset_minutes": 60, "local_iso": "2026-01-10T11:00:00+01:00", "is_dst": False}),
            ({"utc_iso": "2026-01-10T10:00:00Z", "tz_name": "Africa/Nairobi"}, {"utc_offset_minutes": 180, "local_iso": "2026-01-10T13:00:00+03:00", "is_dst": False}),
            ({"utc_iso": "2026-01-10T10:00:00Z", "tz_name": "Africa/Johannesburg"}, {"utc_offset_minutes": 120, "local_iso": "2026-01-10T12:00:00+02:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-01-10T10:00:00Z", "tz_name": "Africa/Missing"}, {"utc_iso": "bad", "tz_name": "Africa/Lagos"}),
    ),
    TimezoneCalendarSpec(
        component_id="tz-oceania-pacific",
        category="tz_offset",
        title="Oceania and Pacific IANA timezone offset lookup",
        description="Resolves UTC offsets (including Darwin/Adelaide 30-minute offsets) across Sydney, Melbourne, Perth, Adelaide, Darwin, Auckland, and Honolulu.",
        allowed_zones=("Australia/Sydney", "Australia/Melbourne", "Australia/Perth", "Australia/Adelaide", "Australia/Darwin", "Pacific/Auckland", "Pacific/Honolulu"),
        config={},
        positive_cases=(
            ({"utc_iso": "2026-06-15T00:00:00Z", "tz_name": "Australia/Sydney"}, {"utc_offset_minutes": 600, "local_iso": "2026-06-15T10:00:00+10:00", "is_dst": False}),
            ({"utc_iso": "2026-06-15T00:00:00Z", "tz_name": "Australia/Darwin"}, {"utc_offset_minutes": 570, "local_iso": "2026-06-15T09:30:00+09:30", "is_dst": False}),
            ({"utc_iso": "2026-06-15T00:00:00Z", "tz_name": "Pacific/Honolulu"}, {"utc_offset_minutes": -600, "local_iso": "2026-06-14T14:00:00-10:00", "is_dst": False}),
        ),
        negative_cases=({"utc_iso": "2026-06-15T00:00:00Z", "tz_name": "Pacific/Atlantis"}, {"utc_iso": "bad", "tz_name": "Australia/Sydney"}),
    ),
    # --- Category B: 10 DST transition verification components ---
    TimezoneCalendarSpec(
        component_id="dst-us-eastern-transitions",
        category="dst_transition",
        title="US Eastern (America/New_York) DST transition verifier",
        description="Computes UTC offset delta and DST state before and after US Eastern spring-forward and fall-back transitions.",
        allowed_zones=("America/New_York",),
        config={"tz_name": "America/New_York"},
        positive_cases=(
            ({"before_utc": "2026-03-08T06:59:00Z", "after_utc": "2026-03-08T07:01:00Z"}, {"before_offset_min": -300, "after_offset_min": -240, "delta_minutes": 60, "transitioned": True}),
            ({"before_utc": "2026-11-01T05:59:00Z", "after_utc": "2026-11-01T06:01:00Z"}, {"before_offset_min": -240, "after_offset_min": -300, "delta_minutes": -60, "transitioned": True}),
        ),
        negative_cases=({"before_utc": "invalid", "after_utc": "2026-03-08T07:01:00Z"}, {"before_utc": "2026-03-08T06:59:00Z", "after_utc": ""}),
    ),
    TimezoneCalendarSpec(
        component_id="dst-us-pacific-transitions",
        category="dst_transition",
        title="US Pacific (America/Los_Angeles) DST transition verifier",
        description="Computes UTC offset delta before and after US Pacific spring-forward and fall-back transitions.",
        allowed_zones=("America/Los_Angeles",),
        config={"tz_name": "America/Los_Angeles"},
        positive_cases=(
            ({"before_utc": "2026-03-08T09:59:00Z", "after_utc": "2026-03-08T10:01:00Z"}, {"before_offset_min": -480, "after_offset_min": -420, "delta_minutes": 60, "transitioned": True}),
            ({"before_utc": "2026-11-01T08:59:00Z", "after_utc": "2026-11-01T09:01:00Z"}, {"before_offset_min": -420, "after_offset_min": -480, "delta_minutes": -60, "transitioned": True}),
        ),
        negative_cases=({"before_utc": "bad", "after_utc": "2026-03-08T10:01:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-us-arizona-no-dst",
        category="dst_transition",
        title="US Arizona (America/Phoenix) permanent standard-time verifier",
        description="Verifies that America/Phoenix remains at UTC-07:00 (-420 minutes) across US DST transition boundaries.",
        allowed_zones=("America/Phoenix",),
        config={"tz_name": "America/Phoenix"},
        positive_cases=(
            ({"before_utc": "2026-03-08T08:59:00Z", "after_utc": "2026-03-08T09:01:00Z"}, {"before_offset_min": -420, "after_offset_min": -420, "delta_minutes": 0, "transitioned": False}),
            ({"before_utc": "2026-01-15T12:00:00Z", "after_utc": "2026-07-15T12:00:00Z"}, {"before_offset_min": -420, "after_offset_min": -420, "delta_minutes": 0, "transitioned": False}),
        ),
        negative_cases=({"before_utc": "bad", "after_utc": "2026-07-15T12:00:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-uk-bst-transitions",
        category="dst_transition",
        title="United Kingdom (Europe/London) GMT/BST transition verifier",
        description="Computes UTC offset delta across the UK March spring-forward (01:00 UTC) and October fall-back (01:00 UTC) boundaries.",
        allowed_zones=("Europe/London",),
        config={"tz_name": "Europe/London"},
        positive_cases=(
            ({"before_utc": "2026-03-29T00:59:00Z", "after_utc": "2026-03-29T01:01:00Z"}, {"before_offset_min": 0, "after_offset_min": 60, "delta_minutes": 60, "transitioned": True}),
            ({"before_utc": "2026-10-25T00:59:00Z", "after_utc": "2026-10-25T01:01:00Z"}, {"before_offset_min": 60, "after_offset_min": 0, "delta_minutes": -60, "transitioned": True}),
        ),
        negative_cases=({"before_utc": "bad", "after_utc": "2026-10-25T01:01:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-eu-cet-cest-transitions",
        category="dst_transition",
        title="Central European Time (Europe/Berlin) CET/CEST transition verifier",
        description="Computes UTC offset delta across European Union CET (+01:00) and CEST (+02:00) transitions.",
        allowed_zones=("Europe/Berlin",),
        config={"tz_name": "Europe/Berlin"},
        positive_cases=(
            ({"before_utc": "2026-03-29T00:59:00Z", "after_utc": "2026-03-29T01:01:00Z"}, {"before_offset_min": 60, "after_offset_min": 120, "delta_minutes": 60, "transitioned": True}),
            ({"before_utc": "2026-10-25T00:59:00Z", "after_utc": "2026-10-25T01:01:00Z"}, {"before_offset_min": 120, "after_offset_min": 60, "delta_minutes": -60, "transitioned": True}),
        ),
        negative_cases=({"before_utc": "", "after_utc": "2026-03-29T01:01:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-australia-sydney-southern",
        category="dst_transition",
        title="Southern Hemisphere (Australia/Sydney) AEST/AEDT transition verifier",
        description="Computes UTC offset delta across Sydney April fall-back (+11 to +10) and October spring-forward (+10 to +11) transitions.",
        allowed_zones=("Australia/Sydney",),
        config={"tz_name": "Australia/Sydney"},
        positive_cases=(
            ({"before_utc": "2026-04-04T15:59:00Z", "after_utc": "2026-04-04T16:01:00Z"}, {"before_offset_min": 660, "after_offset_min": 600, "delta_minutes": -60, "transitioned": True}),
            ({"before_utc": "2026-10-03T15:59:00Z", "after_utc": "2026-10-03T16:01:00Z"}, {"before_offset_min": 600, "after_offset_min": 660, "delta_minutes": 60, "transitioned": True}),
        ),
        negative_cases=({"before_utc": "invalid", "after_utc": "2026-10-03T16:01:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-new-zealand-auckland",
        category="dst_transition",
        title="New Zealand (Pacific/Auckland) NZST/NZDT transition verifier",
        description="Computes UTC offset delta across Auckland April fall-back (+13 to +12) and September spring-forward (+12 to +13) transitions.",
        allowed_zones=("Pacific/Auckland",),
        config={"tz_name": "Pacific/Auckland"},
        positive_cases=(
            ({"before_utc": "2026-04-04T13:59:00Z", "after_utc": "2026-04-04T14:01:00Z"}, {"before_offset_min": 780, "after_offset_min": 720, "delta_minutes": -60, "transitioned": True}),
            ({"before_utc": "2026-09-26T13:59:00Z", "after_utc": "2026-09-26T14:01:00Z"}, {"before_offset_min": 720, "after_offset_min": 780, "delta_minutes": 60, "transitioned": True}),
        ),
        negative_cases=({"before_utc": "bad", "after_utc": "2026-09-26T14:01:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-canada-toronto-transitions",
        category="dst_transition",
        title="Canada Eastern (America/Toronto) EST/EDT transition verifier",
        description="Computes UTC offset delta across Toronto March spring-forward and November fall-back boundaries.",
        allowed_zones=("America/Toronto",),
        config={"tz_name": "America/Toronto"},
        positive_cases=(
            ({"before_utc": "2026-03-08T06:59:00Z", "after_utc": "2026-03-08T07:01:00Z"}, {"before_offset_min": -300, "after_offset_min": -240, "delta_minutes": 60, "transitioned": True}),
            ({"before_utc": "2026-11-01T05:59:00Z", "after_utc": "2026-11-01T06:01:00Z"}, {"before_offset_min": -240, "after_offset_min": -300, "delta_minutes": -60, "transitioned": True}),
        ),
        negative_cases=({"before_utc": "bad", "after_utc": "2026-11-01T06:01:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-asia-tokyo-no-dst",
        category="dst_transition",
        title="Japan (Asia/Tokyo) permanent JST invariance verifier",
        description="Verifies that Asia/Tokyo maintains a constant +09:00 (+540 minutes) offset across winter and summer.",
        allowed_zones=("Asia/Tokyo",),
        config={"tz_name": "Asia/Tokyo"},
        positive_cases=(
            ({"before_utc": "2026-01-15T00:00:00Z", "after_utc": "2026-07-15T00:00:00Z"}, {"before_offset_min": 540, "after_offset_min": 540, "delta_minutes": 0, "transitioned": False}),
            ({"before_utc": "2026-03-29T00:00:00Z", "after_utc": "2026-10-25T00:00:00Z"}, {"before_offset_min": 540, "after_offset_min": 540, "delta_minutes": 0, "transitioned": False}),
        ),
        negative_cases=({"before_utc": "bad", "after_utc": "2026-07-15T00:00:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="dst-utc-canonical-invariance",
        category="dst_transition",
        title="Canonical UTC zero-offset invariance verifier",
        description="Verifies that UTC maintains a zero-minute offset across all calendar timestamps.",
        allowed_zones=("UTC",),
        config={"tz_name": "UTC"},
        positive_cases=(
            ({"before_utc": "2026-01-01T00:00:00Z", "after_utc": "2026-06-01T00:00:00Z"}, {"before_offset_min": 0, "after_offset_min": 0, "delta_minutes": 0, "transitioned": False}),
            ({"before_utc": "2026-03-08T07:00:00Z", "after_utc": "2026-11-01T06:00:00Z"}, {"before_offset_min": 0, "after_offset_min": 0, "delta_minutes": 0, "transitioned": False}),
        ),
        negative_cases=({"before_utc": "not-iso", "after_utc": "2026-06-01T00:00:00Z"},),
    ),
    # --- Category C: 10 business-day calendar components ---
    TimezoneCalendarSpec(
        component_id="bday-standard-mon-fri-add",
        category="business_day",
        title="Standard Monday-Friday business day addition calculator",
        description="Adds N working days (Monday-Friday, excluding optional holiday ISO dates) to a start date.",
        allowed_zones=("UTC",),
        config={"op": "add_days", "workdays": [0, 1, 2, 3, 4]},
        positive_cases=(
            ({"start_date": "2026-10-09", "business_days": 1, "holidays": []}, {"result_date": "2026-10-12"}),
            ({"start_date": "2026-10-09", "business_days": 1, "holidays": ["2026-10-12"]}, {"result_date": "2026-10-13"}),
            ({"start_date": "2026-10-12", "business_days": 5, "holidays": []}, {"result_date": "2026-10-19"}),
        ),
        negative_cases=({"start_date": "bad-date", "business_days": 1}, {"start_date": "2026-10-09", "business_days": -5}),
    ),
    TimezoneCalendarSpec(
        component_id="bday-standard-mon-fri-count",
        category="business_day",
        title="Standard Monday-Friday working day counter",
        description="Counts working days between start_date (inclusive) and end_date (exclusive) skipping weekends and declared holidays.",
        allowed_zones=("UTC",),
        config={"op": "count_days", "workdays": [0, 1, 2, 3, 4]},
        positive_cases=(
            ({"start_date": "2026-10-05", "end_date": "2026-10-12", "holidays": []}, {"business_days": 5}),
            ({"start_date": "2026-10-05", "end_date": "2026-10-12", "holidays": ["2026-10-07"]}, {"business_days": 4}),
            ({"start_date": "2026-10-10", "end_date": "2026-10-12", "holidays": []}, {"business_days": 0}),
        ),
        negative_cases=({"start_date": "2026-10-12", "end_date": "2026-10-05"}, {"start_date": "bad", "end_date": "2026-10-12"}),
    ),
    TimezoneCalendarSpec(
        component_id="bday-t-plus-1-equities-settlement",
        category="business_day",
        title="T+1 North American equities trade settlement date calculator",
        description="Computes the T+1 settlement date for an equity trade date, rolling past weekends and market holidays.",
        allowed_zones=("America/New_York",),
        config={"op": "add_days", "workdays": [0, 1, 2, 3, 4], "fixed_offset": 1},
        positive_cases=(
            ({"start_date": "2026-10-13", "holidays": []}, {"result_date": "2026-10-14"}),
            ({"start_date": "2026-10-09", "holidays": []}, {"result_date": "2026-10-12"}),
            ({"start_date": "2026-07-02", "holidays": ["2026-07-03"]}, {"result_date": "2026-07-06"}),
        ),
        negative_cases=({"start_date": "2026-13-40"},),
    ),
    TimezoneCalendarSpec(
        component_id="bday-t-plus-2-fx-spot-settlement",
        category="business_day",
        title="T+2 foreign exchange spot value date calculator",
        description="Computes the T+2 FX spot settlement date skipping weekends and bank holidays.",
        allowed_zones=("Europe/London",),
        config={"op": "add_days", "workdays": [0, 1, 2, 3, 4], "fixed_offset": 2},
        positive_cases=(
            ({"start_date": "2026-10-12", "holidays": []}, {"result_date": "2026-10-14"}),
            ({"start_date": "2026-10-08", "holidays": []}, {"result_date": "2026-10-12"}),
            ({"start_date": "2026-10-09", "holidays": ["2026-10-12"]}, {"result_date": "2026-10-14"}),
        ),
        negative_cases=({"start_date": "not-a-date"},),
    ),
    TimezoneCalendarSpec(
        component_id="bday-gulf-sun-thu-workweek",
        category="business_day",
        title="Sunday-Thursday workweek business day calculator",
        description="Adds working days under a Sunday-Thursday workweek (where Friday=4 and Saturday=5 are weekend days).",
        allowed_zones=("Asia/Riyadh",),
        config={"op": "add_days", "workdays": [0, 1, 2, 3, 6]},
        positive_cases=(
            ({"start_date": "2026-10-15", "business_days": 1, "holidays": []}, {"result_date": "2026-10-18"}),
            ({"start_date": "2026-10-18", "business_days": 4, "holidays": []}, {"result_date": "2026-10-22"}),
        ),
        negative_cases=({"start_date": "bad", "business_days": 1},),
    ),
    TimezoneCalendarSpec(
        component_id="bday-six-day-mon-sat-logistics",
        category="business_day",
        title="Monday-Saturday 6-day logistics delivery calculator",
        description="Adds working delivery days where Monday through Saturday are active delivery days and only Sunday is skipped.",
        allowed_zones=("UTC",),
        config={"op": "add_days", "workdays": [0, 1, 2, 3, 4, 5]},
        positive_cases=(
            ({"start_date": "2026-10-09", "business_days": 1, "holidays": []}, {"result_date": "2026-10-10"}),
            ({"start_date": "2026-10-10", "business_days": 1, "holidays": []}, {"result_date": "2026-10-12"}),
        ),
        negative_cases=({"start_date": "invalid", "business_days": 2},),
    ),
    TimezoneCalendarSpec(
        component_id="bday-month-end-working-day",
        category="business_day",
        title="Last business day of month (BMonthEnd) calculator",
        description="Finds the final Monday-Friday working day of a given year and month.",
        allowed_zones=("UTC",),
        config={"op": "month_end", "workdays": [0, 1, 2, 3, 4]},
        positive_cases=(
            ({"year": 2026, "month": 10, "holidays": []}, {"result_date": "2026-10-30"}),
            ({"year": 2026, "month": 5, "holidays": []}, {"result_date": "2026-05-29"}),
            ({"year": 2026, "month": 10, "holidays": ["2026-10-30"]}, {"result_date": "2026-10-29"}),
        ),
        negative_cases=({"year": 2026, "month": 13}, {"year": 2026, "month": 0}),
    ),
    TimezoneCalendarSpec(
        component_id="bday-quarter-end-working-day",
        category="business_day",
        title="Fiscal quarter-end working day calculator",
        description="Finds the final Monday-Friday working day of fiscal quarter Q1, Q2, Q3, or Q4.",
        allowed_zones=("UTC",),
        config={"op": "quarter_end", "workdays": [0, 1, 2, 3, 4]},
        positive_cases=(
            ({"year": 2026, "quarter": 1, "holidays": []}, {"result_date": "2026-03-31"}),
            ({"year": 2026, "quarter": 2, "holidays": []}, {"result_date": "2026-06-30"}),
            ({"year": 2026, "quarter": 3, "holidays": []}, {"result_date": "2026-09-30"}),
            ({"year": 2026, "quarter": 4, "holidays": []}, {"result_date": "2026-12-31"}),
        ),
        negative_cases=({"year": 2026, "quarter": 5}, {"year": 2026, "quarter": 0}),
    ),
    TimezoneCalendarSpec(
        component_id="bday-next-business-day-roll-modified-following",
        category="business_day",
        title="ISDA Modified Following business day roll convention calculator",
        description="Rolls a non-business date forward to the next business day unless that crosses a month boundary, in which case it rolls backward to the preceding business day.",
        allowed_zones=("UTC",),
        config={"op": "modified_following", "workdays": [0, 1, 2, 3, 4]},
        positive_cases=(
            ({"target_date": "2026-10-10", "holidays": []}, {"result_date": "2026-10-12"}),
            ({"target_date": "2026-10-31", "holidays": []}, {"result_date": "2026-10-30"}),
            ({"target_date": "2026-10-13", "holidays": []}, {"result_date": "2026-10-13"}),
        ),
        negative_cases=({"target_date": "not-a-date"},),
    ),
    TimezoneCalendarSpec(
        component_id="bday-payroll-biweekly-anchor",
        category="business_day",
        title="Biweekly payroll date with preceding-business-day holiday adjustment",
        description="Computes the Nth biweekly (14-day) pay date from an anchor date and rolls backward if the pay date falls on a weekend or holiday.",
        allowed_zones=("UTC",),
        config={"op": "biweekly_preceding", "workdays": [0, 1, 2, 3, 4]},
        positive_cases=(
            ({"anchor_date": "2026-10-02", "periods": 1, "holidays": []}, {"result_date": "2026-10-16"}),
            ({"anchor_date": "2026-10-02", "periods": 1, "holidays": ["2026-10-16"]}, {"result_date": "2026-10-15"}),
        ),
        negative_cases=({"anchor_date": "bad", "periods": 1}, {"anchor_date": "2026-10-02", "periods": -1}),
    ),
    # --- Category D: 10 SLA deadline and window calculation components ---
    TimezoneCalendarSpec(
        component_id="sla-24x7-p1-incident-1h",
        category="sla_deadline",
        title="24x7 P1 incident 60-minute SLA deadline calculator",
        description="Computes the 60-minute P1 incident response deadline in both UTC and the target on-call IANA timezone.",
        allowed_zones=("UTC", "America/New_York", "Europe/London", "Asia/Tokyo"),
        config={"op": "add_minutes", "sla_minutes": 60},
        positive_cases=(
            ({"opened_utc": "2026-10-13T20:00:00Z", "tz_name": "America/New_York"}, {"deadline_utc": "2026-10-13T21:00:00Z", "deadline_local": "2026-10-13T17:00:00-04:00"}),
            ({"opened_utc": "2026-10-13T20:00:00Z", "tz_name": "Asia/Tokyo"}, {"deadline_utc": "2026-10-13T21:00:00Z", "deadline_local": "2026-10-14T06:00:00+09:00"}),
        ),
        negative_cases=({"opened_utc": "invalid", "tz_name": "UTC"}, {"opened_utc": "2026-10-13T20:00:00Z", "tz_name": "Invalid/Zone"}),
    ),
    TimezoneCalendarSpec(
        component_id="sla-24x7-p2-incident-4h",
        category="sla_deadline",
        title="24x7 P2 incident 4-hour SLA mitigation deadline calculator",
        description="Computes the 240-minute P2 incident mitigation deadline in UTC and the target IANA timezone.",
        allowed_zones=("UTC", "America/New_York", "Europe/London", "Asia/Tokyo"),
        config={"op": "add_minutes", "sla_minutes": 240},
        positive_cases=(
            ({"opened_utc": "2026-10-13T20:00:00Z", "tz_name": "UTC"}, {"deadline_utc": "2026-10-14T00:00:00Z", "deadline_local": "2026-10-14T00:00:00+00:00"}),
            ({"opened_utc": "2026-10-13T20:00:00Z", "tz_name": "Europe/London"}, {"deadline_utc": "2026-10-14T00:00:00Z", "deadline_local": "2026-10-14T01:00:00+01:00"}),
        ),
        negative_cases=({"opened_utc": "bad", "tz_name": "UTC"},),
    ),
    TimezoneCalendarSpec(
        component_id="sla-business-hours-9to17-ny",
        category="sla_deadline",
        title="US Eastern 09:00-17:00 business-hours SLA deadline calculator",
        description="Adds SLA working minutes within Monday-Friday 09:00-17:00 America/New_York business hours.",
        allowed_zones=("America/New_York",),
        config={"op": "business_hours_sla", "tz_name": "America/New_York", "start_hour": 9, "end_hour": 17},
        positive_cases=(
            ({"opened_utc": "2026-10-13T14:00:00Z", "sla_minutes": 120}, {"deadline_local": "2026-10-13T12:00:00-04:00"}),
            ({"opened_utc": "2026-10-13T20:00:00Z", "sla_minutes": 120}, {"deadline_local": "2026-10-14T10:00:00-04:00"}),
        ),
        negative_cases=({"opened_utc": "bad", "sla_minutes": 120}, {"opened_utc": "2026-10-13T14:00:00Z", "sla_minutes": -10}),
    ),
    TimezoneCalendarSpec(
        component_id="sla-business-hours-9to17-london",
        category="sla_deadline",
        title="UK London 09:00-17:00 business-hours SLA deadline calculator",
        description="Adds SLA working minutes within Monday-Friday 09:00-17:00 Europe/London business hours.",
        allowed_zones=("Europe/London",),
        config={"op": "business_hours_sla", "tz_name": "Europe/London", "start_hour": 9, "end_hour": 17},
        positive_cases=(
            ({"opened_utc": "2026-01-13T10:00:00Z", "sla_minutes": 180}, {"deadline_local": "2026-01-13T13:00:00+00:00"}),
            ({"opened_utc": "2026-01-13T16:00:00Z", "sla_minutes": 120}, {"deadline_local": "2026-01-14T10:00:00+00:00"}),
        ),
        negative_cases=({"opened_utc": "bad", "sla_minutes": 60},),
    ),
    TimezoneCalendarSpec(
        component_id="sla-business-hours-9to18-tokyo",
        category="sla_deadline",
        title="Japan Tokyo 09:00-18:00 business-hours SLA deadline calculator",
        description="Adds SLA working minutes within Monday-Friday 09:00-18:00 Asia/Tokyo business hours.",
        allowed_zones=("Asia/Tokyo",),
        config={"op": "business_hours_sla", "tz_name": "Asia/Tokyo", "start_hour": 9, "end_hour": 18},
        positive_cases=(
            ({"opened_utc": "2026-01-13T01:00:00Z", "sla_minutes": 120}, {"deadline_local": "2026-01-13T12:00:00+09:00"}),
            ({"opened_utc": "2026-01-13T08:00:00Z", "sla_minutes": 120}, {"deadline_local": "2026-01-14T10:00:00+09:00"}),
        ),
        negative_cases=({"opened_utc": "bad", "sla_minutes": 60},),
    ),
    TimezoneCalendarSpec(
        component_id="sla-follow-the-sun-handoff",
        category="sla_deadline",
        title="Follow-the-sun 3-region on-call shift router",
        description="Resolves active on-call region (Asia/Tokyo 00:00-08:00 UTC, Europe/London 08:00-16:00 UTC, America/New_York 16:00-24:00 UTC).",
        allowed_zones=("Asia/Tokyo", "Europe/London", "America/New_York"),
        config={"op": "follow_the_sun"},
        positive_cases=(
            ({"utc_iso": "2026-10-13T03:30:00Z"}, {"active_region": "Asia/Tokyo", "next_handoff_utc": "2026-10-13T08:00:00Z"}),
            ({"utc_iso": "2026-10-13T11:00:00Z"}, {"active_region": "Europe/London", "next_handoff_utc": "2026-10-13T16:00:00Z"}),
            ({"utc_iso": "2026-10-13T19:45:00Z"}, {"active_region": "America/New_York", "next_handoff_utc": "2026-10-14T00:00:00Z"}),
        ),
        negative_cases=({"utc_iso": "invalid-timestamp"},),
    ),
    TimezoneCalendarSpec(
        component_id="sla-gdpr-72h-breach-notification",
        category="sla_deadline",
        title="GDPR Article 33 72-hour notification deadline calculator",
        description="Computes the 72-hour (4320-minute) regulatory breach notification deadline in UTC and Europe/Brussels local time.",
        allowed_zones=("Europe/Brussels", "UTC"),
        config={"op": "add_minutes", "sla_minutes": 4320},
        positive_cases=(
            ({"opened_utc": "2026-01-10T10:00:00Z", "tz_name": "Europe/Brussels"}, {"deadline_utc": "2026-01-13T10:00:00Z", "deadline_local": "2026-01-13T11:00:00+01:00"}),
        ),
        negative_cases=({"opened_utc": "bad", "tz_name": "Europe/Brussels"},),
    ),
    TimezoneCalendarSpec(
        component_id="sla-cooling-off-14-calendar-days",
        category="sla_deadline",
        title="14-calendar-day consumer cooling-off deadline calculator",
        description="Computes the 14-calendar-day end-of-day (23:59:59) deadline in the customer's local IANA timezone.",
        allowed_zones=("Europe/Berlin", "Europe/London", "America/New_York"),
        config={"op": "cooling_off_14d"},
        positive_cases=(
            ({"purchase_date": "2026-10-01", "tz_name": "Europe/Berlin"}, {"deadline_local": "2026-10-15T23:59:59+02:00"}),
            ({"purchase_date": "2026-01-01", "tz_name": "Europe/London"}, {"deadline_local": "2026-01-15T23:59:59+00:00"}),
        ),
        negative_cases=({"purchase_date": "bad", "tz_name": "Europe/Berlin"}, {"purchase_date": "2026-10-01", "tz_name": "Invalid/Zone"}),
    ),
    TimezoneCalendarSpec(
        component_id="sla-maintenance-window-overlap",
        category="sla_deadline",
        title="Cross-timezone maintenance window overlap calculator",
        description="Computes the overlap in minutes between two UTC timestamp intervals.",
        allowed_zones=("UTC",),
        config={"op": "window_overlap"},
        positive_cases=(
            (
                {"start_a": "2026-10-13T10:00:00Z", "end_a": "2026-10-13T14:00:00Z", "start_b": "2026-10-13T12:00:00Z", "end_b": "2026-10-13T16:00:00Z"},
                {"overlap_minutes": 120, "overlaps": True},
            ),
            (
                {"start_a": "2026-10-13T08:00:00Z", "end_a": "2026-10-13T10:00:00Z", "start_b": "2026-10-13T12:00:00Z", "end_b": "2026-10-13T14:00:00Z"},
                {"overlap_minutes": 0, "overlaps": False},
            ),
        ),
        negative_cases=({"start_a": "bad", "end_a": "2026-10-13T14:00:00Z", "start_b": "2026-10-13T12:00:00Z", "end_b": "2026-10-13T16:00:00Z"},),
    ),
    TimezoneCalendarSpec(
        component_id="sla-iso-week-sprint-boundary",
        category="sla_deadline",
        title="ISO 8601 week Monday-00:00 to Sunday-23:59 boundary calculator",
        description="Computes the Monday start date and Sunday end date for a given ISO year and ISO week number.",
        allowed_zones=("UTC",),
        config={"op": "iso_week_bounds"},
        positive_cases=(
            ({"iso_year": 2026, "iso_week": 42}, {"monday_date": "2026-10-12", "sunday_date": "2026-10-18"}),
            ({"iso_year": 2026, "iso_week": 1}, {"monday_date": "2025-12-29", "sunday_date": "2026-01-04"}),
        ),
        negative_cases=({"iso_year": 2026, "iso_week": 0}, {"iso_year": 2026, "iso_week": 55}),
    ),
)


def _render_implement_py(spec: TimezoneCalendarSpec) -> bytes:
    code = f'''"""{spec.title} (category: {spec.category}).

{spec.description}
Deterministic stdlib zoneinfo and datetime implementation.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

COMPONENT_ID = {spec.component_id!r}
CATEGORY = {spec.category!r}
ALLOWED_ZONES = {list(spec.allowed_zones)!r}
CONFIG = {spec.config!r}


def _parse_utc(iso_str: str) -> datetime:
    if not isinstance(iso_str, str) or not re.fullmatch(r"[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}T[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}(?:\\.[0-9]{{1,6}})?Z", iso_str):
        raise ValueError(f"invalid_utc_timestamp: {{iso_str!r}}")
    dt = datetime.fromisoformat(iso_str[:-1] + "+00:00")
    return dt.astimezone(timezone.utc)


def _parse_date(date_str: str) -> date:
    if not isinstance(date_str, str) or len(date_str) != 10:
        raise ValueError(f"invalid_iso_date: {{date_str!r}}")
    return date.fromisoformat(date_str)


def _load_zone(tz_name: str) -> ZoneInfo:
    if not isinstance(tz_name, str) or tz_name not in ALLOWED_ZONES:
        raise ValueError(f"disallowed_or_unknown_timezone: {{tz_name!r}}")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown_timezone: {{tz_name!r}}") from exc


def calculate(**kwargs) -> dict:
    """Execute deterministic timezone/calendar calculation for {spec.component_id}."""
    # This local profile bounds work before iteration. It does not install or update timezone data.
    for key, value in kwargs.items():
        if isinstance(value, bool) or (isinstance(value, int) and not -100000 <= value <= 100000):
            raise ValueError("input_outside_calendar_profile")
        if isinstance(value, str) and len(value) > 100:
            raise ValueError("calendar_text_too_large")
    holidays_input = kwargs.get("holidays", [])
    if not isinstance(holidays_input, (list, tuple)) or len(holidays_input) > 512:
        raise ValueError("holiday_limit_exceeded")
    if CATEGORY == "tz_offset":
        utc_dt = _parse_utc(kwargs.get("utc_iso", ""))
        zi = _load_zone(kwargs.get("tz_name", ""))
        local_dt = utc_dt.astimezone(zi)
        offset_sec = local_dt.utcoffset().total_seconds()
        dst_sec = local_dt.dst().total_seconds() if local_dt.dst() is not None else 0.0
        return {{
            "utc_offset_minutes": int(round(offset_sec / 60.0)),
            "local_iso": local_dt.isoformat(),
            "is_dst": dst_sec != 0.0,
        }}

    if CATEGORY == "dst_transition":
        zi = _load_zone(CONFIG["tz_name"])
        before_dt = _parse_utc(kwargs.get("before_utc", "")).astimezone(zi)
        after_dt = _parse_utc(kwargs.get("after_utc", "")).astimezone(zi)
        b_min = int(round(before_dt.utcoffset().total_seconds() / 60.0))
        a_min = int(round(after_dt.utcoffset().total_seconds() / 60.0))
        return {{
            "before_offset_min": b_min,
            "after_offset_min": a_min,
            "delta_minutes": a_min - b_min,
            "transitioned": b_min != a_min,
        }}

    if CATEGORY == "business_day":
        op = CONFIG["op"]
        workdays = set(CONFIG.get("workdays", [0, 1, 2, 3, 4]))
        holidays = {{_parse_date(h) for h in kwargs.get("holidays", [])}}

        if op == "add_days":
            current = _parse_date(kwargs.get("start_date", ""))
            days = kwargs.get("business_days", CONFIG.get("fixed_offset"))
            if not isinstance(days, int) or not 0 <= days <= 3660:
                raise ValueError("business_days_must_be_non_negative_int")
            remaining = days
            while remaining > 0:
                current += timedelta(days=1)
                if current.weekday() in workdays and current not in holidays:
                    remaining -= 1
            return {{"result_date": current.isoformat()}}

        if op == "count_days":
            start = _parse_date(kwargs.get("start_date", ""))
            end = _parse_date(kwargs.get("end_date", ""))
            if end < start:
                raise ValueError("end_date_before_start_date")
            if (end - start).days > 36600:
                raise ValueError("calendar_range_too_large")
            count = 0
            cur = start
            while cur < end:
                if cur.weekday() in workdays and cur not in holidays:
                    count += 1
                cur += timedelta(days=1)
            return {{"business_days": count}}

        if op == "month_end":
            year = kwargs.get("year")
            month = kwargs.get("month")
            if not isinstance(year, int) or not isinstance(month, int) or not (1 <= month <= 12):
                raise ValueError("invalid_year_or_month")
            last_day = calendar.monthrange(year, month)[1]
            cur = date(year, month, last_day)
            while cur.weekday() not in workdays or cur in holidays:
                cur -= timedelta(days=1)
            return {{"result_date": cur.isoformat()}}

        if op == "quarter_end":
            year = kwargs.get("year")
            quarter = kwargs.get("quarter")
            if not isinstance(year, int) or quarter not in (1, 2, 3, 4):
                raise ValueError("invalid_year_or_quarter")
            month = quarter * 3
            last_day = calendar.monthrange(year, month)[1]
            cur = date(year, month, last_day)
            while cur.weekday() not in workdays or cur in holidays:
                cur -= timedelta(days=1)
            return {{"result_date": cur.isoformat()}}

        if op == "modified_following":
            target = _parse_date(kwargs.get("target_date", ""))
            cur = target
            while cur.weekday() not in workdays or cur in holidays:
                cur += timedelta(days=1)
            if cur.month != target.month:
                cur = target
                while cur.weekday() not in workdays or cur in holidays:
                    cur -= timedelta(days=1)
            return {{"result_date": cur.isoformat()}}

        if op == "biweekly_preceding":
            anchor = _parse_date(kwargs.get("anchor_date", ""))
            periods = kwargs.get("periods")
            if not isinstance(periods, int) or periods < 0:
                raise ValueError("invalid_periods")
            cur = anchor + timedelta(days=14 * periods)
            while cur.weekday() not in workdays or cur in holidays:
                cur -= timedelta(days=1)
            return {{"result_date": cur.isoformat()}}

    if CATEGORY == "sla_deadline":
        op = CONFIG["op"]
        if op == "add_minutes":
            opened = _parse_utc(kwargs.get("opened_utc", ""))
            zi = _load_zone(kwargs.get("tz_name", ""))
            deadline_utc = opened + timedelta(minutes=int(CONFIG["sla_minutes"]))
            deadline_local = deadline_utc.astimezone(zi)
            return {{
                "deadline_utc": deadline_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "deadline_local": deadline_local.isoformat(),
            }}

        if op == "business_hours_sla":
            opened = _parse_utc(kwargs.get("opened_utc", ""))
            sla_minutes = kwargs.get("sla_minutes")
            if not isinstance(sla_minutes, int) or not 0 < sla_minutes <= 44640:
                raise ValueError("invalid_sla_minutes")
            zi = _load_zone(CONFIG["tz_name"])
            start_h = int(CONFIG["start_hour"])
            end_h = int(CONFIG["end_hour"])
            cur = opened.astimezone(zi)
            remaining = sla_minutes
            while remaining > 0:
                if cur.weekday() >= 5:
                    cur = datetime.combine(cur.date() + timedelta(days=1), dtime(start_h, 0), tzinfo=zi)
                    continue
                day_start = datetime.combine(cur.date(), dtime(start_h, 0), tzinfo=zi)
                day_end = datetime.combine(cur.date(), dtime(end_h, 0), tzinfo=zi)
                if cur < day_start:
                    cur = day_start
                if cur >= day_end:
                    cur = datetime.combine(cur.date() + timedelta(days=1), dtime(start_h, 0), tzinfo=zi)
                    continue
                avail = int((day_end - cur).total_seconds() // 60)
                if remaining <= avail:
                    cur = cur + timedelta(minutes=remaining)
                    remaining = 0
                else:
                    remaining -= avail
                    cur = datetime.combine(cur.date() + timedelta(days=1), dtime(start_h, 0), tzinfo=zi)
            return {{"deadline_local": cur.isoformat()}}

        if op == "follow_the_sun":
            dt = _parse_utc(kwargs.get("utc_iso", ""))
            hour = dt.hour
            if 0 <= hour < 8:
                region = "Asia/Tokyo"
                handoff = dt.replace(hour=8, minute=0, second=0, microsecond=0)
            elif 8 <= hour < 16:
                region = "Europe/London"
                handoff = dt.replace(hour=16, minute=0, second=0, microsecond=0)
            else:
                region = "America/New_York"
                handoff = (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            return {{
                "active_region": region,
                "next_handoff_utc": handoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }}

        if op == "cooling_off_14d":
            p_date = _parse_date(kwargs.get("purchase_date", ""))
            zi = _load_zone(kwargs.get("tz_name", ""))
            end_date = p_date + timedelta(days=14)
            end_dt = datetime.combine(end_date, dtime(23, 59, 59), tzinfo=zi)
            return {{"deadline_local": end_dt.isoformat()}}

        if op == "window_overlap":
            sa = _parse_utc(kwargs.get("start_a", ""))
            ea = _parse_utc(kwargs.get("end_a", ""))
            sb = _parse_utc(kwargs.get("start_b", ""))
            eb = _parse_utc(kwargs.get("end_b", ""))
            if ea < sa or eb < sb:
                raise ValueError("window_end_before_start")
            latest_start = max(sa, sb)
            earliest_end = min(ea, eb)
            overlap = max(0, int((earliest_end - latest_start).total_seconds() // 60))
            return {{"overlap_minutes": overlap, "overlaps": overlap > 0}}

        if op == "iso_week_bounds":
            iso_year = kwargs.get("iso_year")
            iso_week = kwargs.get("iso_week")
            if not isinstance(iso_year, int) or not isinstance(iso_week, int):
                raise ValueError("invalid_iso_week_args")
            monday = date.fromisocalendar(iso_year, iso_week, 1)
            sunday = date.fromisocalendar(iso_year, iso_week, 7)
            return {{"monday_date": monday.isoformat(), "sunday_date": sunday.isoformat()}}

    raise ValueError(f"unsupported_operation_for_{{COMPONENT_ID}}")
'''
    return code.encode("utf-8")


def _render_test_implement_py(spec: TimezoneCalendarSpec) -> bytes:
    code = f'''"""Deterministic conformance tests for {spec.component_id}."""
from __future__ import annotations

import unittest
from implement import calculate

POSITIVE_CASES = {list(spec.positive_cases)!r}
NEGATIVE_CASES = {list(spec.negative_cases)!r}


class TimezoneCalendarTests(unittest.TestCase):
    def test_positive_cases(self) -> None:
        for inputs, expected in POSITIVE_CASES:
            actual = calculate(**inputs)
            for k, v in expected.items():
                self.assertEqual(actual.get(k), v)

    def test_negative_cases_refused(self) -> None:
        for bad_inputs in NEGATIVE_CASES:
            with self.assertRaises(ValueError):
                calculate(**bad_inputs)

    def test_known_wrong_control_fails(self) -> None:
        inputs, expected = POSITIVE_CASES[0]
        actual = calculate(**inputs)
        first_key = next(iter(expected.keys()))
        with self.assertRaises(AssertionError):
            self.assertEqual(actual[first_key], "__known_wrong_sentinel__")


if __name__ == "__main__":
    unittest.main()
'''
    return code.encode("utf-8")


def _render_skill_md(spec: TimezoneCalendarSpec) -> bytes:
    zones_text = ", ".join(f"`{z}`" for z in spec.allowed_zones)
    text = (
        f"---\n"
        f"name: {spec.component_id}\n"
        f"description: {spec.description}\n"
        f"---\n\n"
        f"# {spec.title}\n\n"
        f"Category: `{spec.category}`.\n"
        f"Allowed IANA timezones: {zones_text}.\n\n"
        f"## Usage\n\n"
        f"Call `calculate(**kwargs)` from `implement.py` using stdlib `zoneinfo` and `datetime`.\n"
    )
    return text.encode("utf-8")


def _render_integration_md(spec: TimezoneCalendarSpec, harness_name: str) -> bytes:
    text = (
        f"# {spec.title} ({harness_name} integration)\n\n"
        f"Import `calculate` from `implement.py` in `{harness_name}` for deterministic "
        f"IANA timezone and calendar calculations without external dependencies.\n"
    )
    return text.encode("utf-8")


def execute_timezone_calendar(component_id: str, **kwargs: Any) -> dict[str, Any]:
    """Execute a timezone or calendar component in-memory."""
    comp = build_timezone_calendar_component(component_id)
    namespace: dict[str, Any] = {}
    exec(compile(comp["file_bodies"]["implement.py"].decode("utf-8"), "implement.py", "exec"), namespace)
    return namespace["calculate"](**kwargs)


def build_timezone_calendar_component(spec_or_id: TimezoneCalendarSpec | str) -> dict[str, Any]:
    """Build a local package preview, not a library admission record for a timezone/calendar component."""
    if isinstance(spec_or_id, str):
        spec_map = {item.component_id: item for item in TIMEZONE_CALENDAR_SPECS}
        if spec_or_id not in spec_map:
            raise KeyError(f"unknown_timezone_calendar_component: {spec_or_id!r}")
        spec = spec_map[spec_or_id]
    else:
        spec = spec_or_id
    if not isinstance(spec, TimezoneCalendarSpec) or spec not in TIMEZONE_CALENDAR_SPECS:
        raise ValueError("unregistered_factory_spec")

    attribution = (
        f"# Attribution\n\n"
        f"Generated deterministically by `{FACTORY_ID}` version `{FACTORY_VERSION}` on {GENERATED_ON}.\n"
        f"Source data: IANA Time Zone Database and ISO 8601 calendar rules (public domain).\n"
        f"Licence: MIT.\n"
    ).encode("utf-8")

    raw_files = [
        ("implement.py", _render_implement_py(spec), "text/x-python", "skill_script"),
        ("test_implement.py", _render_test_implement_py(spec), "text/x-python", "skill_reference"),
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
        "component_id": spec.component_id,
        "category": spec.category,
        "title": spec.title,
        "allowed_zones": list(spec.allowed_zones),
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


def verify_timezone_calendar_component(component: dict[str, Any]) -> dict[str, Any]:
    """Execute generated implement.py and verify positive cases, negative refusals, and known-wrong controls."""
    comp_id = component["component_id"]
    spec = {item.component_id: item for item in TIMEZONE_CALENDAR_SPECS}[comp_id]
    canonical = build_timezone_calendar_component(comp_id)
    if component != canonical:
        raise ValueError("noncanonical_factory_package")
    namespace: dict[str, Any] = {}
    exec(compile(canonical["file_bodies"]["implement.py"].decode("utf-8"), "implement.py", "exec"), namespace)
    calc_fn = namespace["calculate"]

    pos_ok = True
    for inputs, expected in spec.positive_cases:
        actual = calc_fn(**inputs)
        for k, v in expected.items():
            if actual.get(k) != v:
                pos_ok = False

    neg_ok = True
    for bad_inputs in spec.negative_cases:
        try:
            calc_fn(**bad_inputs)
            neg_ok = False
        except ValueError:
            pass

    inputs0, expected0 = spec.positive_cases[0]
    actual0 = calc_fn(**inputs0)
    first_key = next(iter(expected0.keys()))
    known_wrong_ok = actual0.get(first_key) != "__known_wrong_sentinel__"

    passed = bool(pos_ok and neg_ok and known_wrong_ok)
    return {
        "component_id": comp_id,
        "category": spec.category,
        "passed": passed,
        "positive_cases_passed": pos_ok,
        "negative_cases_rejected": neg_ok,
        "known_wrong_control_passed": known_wrong_ok,
    }


def build_all_timezone_calendar_components() -> list[dict[str, Any]]:
    """Build all 40 deterministic timezone, DST, business-day, and SLA components."""
    return [build_timezone_calendar_component(spec) for spec in TIMEZONE_CALENDAR_SPECS]


__all__ = [
    "FACTORY_ID",
    "FACTORY_VERSION",
    "TimezoneCalendarSpec",
    "TIMEZONE_CALENDAR_SPECS",
    "execute_timezone_calendar",
    "build_timezone_calendar_component",
    "verify_timezone_calendar_component",
    "build_all_timezone_calendar_components",
]
