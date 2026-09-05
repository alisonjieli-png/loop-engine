"""Parse ISO-8601 duration strings into total seconds.

Only the integer year/month/day/hour/minute/second unit form is supported:
a year is treated as 365 days and a month as 30 days.  Weeks, fractional
values, and other ISO-8601 duration features are not supported.  Only the
Python standard library is used.
"""

import re

_DURATION_RE = re.compile(
    r"^P"
    r"(?:(?P<years>\d+)Y)?"
    r"(?:(?P<months>\d+)M)?"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)

_DAY_SECONDS = 86400
_HOUR_SECONDS = 3600
_MINUTE_SECONDS = 60


def parse_duration(s: str) -> int:
    """Return the total number of seconds in an ISO-8601 duration string.

    Raises ValueError if the string is malformed or if the input is not a
    string.
    """
    if not isinstance(s, str):
        raise ValueError(f"malformed ISO-8601 duration: {s!r}")

    match = _DURATION_RE.fullmatch(s)
    if match is None:
        raise ValueError(f"malformed ISO-8601 duration: {s!r}")

    groups = match.groupdict()
    components = {
        name: int(value) for name, value in groups.items() if value is not None
    }

    if not components:
        raise ValueError(f"duration has no components: {s!r}")

    # A 'T' with no time component is malformed (e.g. 'P1DT').
    if "T" in s and not any(
        name in components for name in ("hours", "minutes", "seconds")
    ):
        raise ValueError(f"duration has 'T' but no time component: {s!r}")

    years = components.get("years", 0)
    months = components.get("months", 0)
    days = components.get("days", 0)
    hours = components.get("hours", 0)
    minutes = components.get("minutes", 0)
    seconds = components.get("seconds", 0)

    return (
        (years * 365 + months * 30 + days) * _DAY_SECONDS
        + hours * _HOUR_SECONDS
        + minutes * _MINUTE_SECONDS
        + seconds
    )
