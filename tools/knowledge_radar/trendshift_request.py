"""Typed read selection for Trendshift's documented API or public daily page.

No credential, network call or storage effect belongs to this record. The
public-page engine has a deliberately smaller capability set than the API.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import re

from .records import day

REQUEST = "trendshift_source_request/v1"
PUBLIC, SIGNAL = "trendshift_public", "trendshift_signal"
TRENDING, GITHUB, SPIKES = "trending", "github", "spikes"
KINDS = (TRENDING, GITHUB, SPIKES)
TERMS = "https://trendshift.io/tos"
API_SCHEMA = "https://api.trendshift.io/openapi.yaml"
API_SCHEMA_SHA256 = "f8946f14e06e80e94636f606ffa155a30263bab8a58fd9a9a12875b843465bdc"
MAXIMUM_BYTES = 1024 * 1024
MAXIMUM_RESULTS = 60  # The existing radar question contract's bounded output.
MINIMUM_INTERVAL_SECONDS = 10
RIGHTS = {"terms_url": TERMS, "terms_effective_on": "2026-07-19", "checked_on": "2026-10-08",
          "use": "private_research", "raw_redistribution_allowed": False,
          "substantial_reproduction_allowed": False, "derived_analysis_requires_review": True}
GITHUB_LANGUAGES = ("javascript", "python", "go", "java", "php", "c++", "c", "typescript", "ruby",
                    "c#", "rust", "dart", "swift", "kotlin", "zig")
METRICS = ("stars", "forks", "merged_prs", "issues", "closed_issues")


class TrendshiftError(ValueError):
    """A source contract failed. The stable code contains no supplied source text."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def valid_cursor(value):
    return (type(value) is str and bool(re.fullmatch(r"[A-Za-z0-9+/=_-]{1,512}", value))
            and "ts_live_" not in value)


@dataclass(frozen=True)
class TrendshiftRequest:
    engine: str = SIGNAL
    kind: str = TRENDING
    window: str = "daily"
    period: "str | None" = None
    language: "str | None" = None
    limit: int = 25
    cursor: "str | None" = None
    metric: "str | None" = None
    start: "str | None" = None
    end: "str | None" = None
    min_gain: int = 100
    max_gain: "int | None" = None

    def __post_init__(self):
        if self.engine not in (PUBLIC, SIGNAL) or self.kind not in KINDS:
            raise TrendshiftError("trendshift_selection_invalid")
        if self.window not in ("daily", "weekly", "monthly", "yearly"):
            raise TrendshiftError("trendshift_window_invalid")
        if type(self.limit) is not int or not 1 <= self.limit <= MAXIMUM_RESULTS:
            raise TrendshiftError("trendshift_result_bound")
        if self.language is not None and (type(self.language) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9 +#.-]{0,79}", self.language)):
            raise TrendshiftError("trendshift_language_invalid")
        if self.cursor is not None and not valid_cursor(self.cursor):
            raise TrendshiftError("trendshift_cursor_invalid")
        for value in (self.min_gain, self.max_gain):
            if value is not None and (type(value) is not int or not 0 <= value < 2**63):
                raise TrendshiftError("trendshift_gain_invalid")
        if type(self.min_gain) is not int:raise TrendshiftError("trendshift_gain_invalid")
        if self.max_gain is not None and self.max_gain < self.min_gain:
            raise TrendshiftError("trendshift_gain_invalid")
        if self.kind == SPIKES:
            if self.metric not in METRICS or self.start is None or self.end is None:
                raise TrendshiftError("trendshift_spike_window_required")
            day(self.start, "start");day(self.end, "end")
            if self.start > self.end or self.period is not None or self.language is not None or self.window != "daily":
                raise TrendshiftError("trendshift_spike_selection_invalid")
        elif any(value is not None for value in (self.metric, self.start, self.end, self.max_gain)) or self.min_gain != 100:
            raise TrendshiftError("trendshift_spike_fields_not_applicable")
        if self.kind == GITHUB and (self.window != "daily" or self.cursor is not None
                or (self.language is not None and self.language.lower() not in (*GITHUB_LANGUAGES, "all"))):
            raise TrendshiftError("trendshift_github_selection_invalid")
        if self.period is not None:
            self.period_parts()
        if self.engine == PUBLIC and (self.kind != TRENDING or self.window != "daily"
                or any(value is not None for value in (self.period, self.language, self.cursor))):
            raise TrendshiftError("trendshift_public_only_current_daily")

    def period_parts(self):
        if type(self.period) is not str:
            raise TrendshiftError("trendshift_period_invalid")
        try:
            if self.window == "daily":
                return (day(self.period, "period"),)
            if self.window == "weekly" and re.fullmatch(r"\d{4}-W\d{2}", self.period):
                year, week = int(self.period[:4]), int(self.period[-2:])
                date.fromisocalendar(year, week, 1)
                return str(year), str(week)
            if self.window == "monthly" and re.fullmatch(r"\d{4}-\d{2}", self.period):
                value = date.fromisoformat(self.period + "-01")
                return str(value.year), str(value.month)
            if self.window == "yearly" and re.fullmatch(r"[1-9]\d{0,3}", self.period):
                return (str(int(self.period)),)
        except ValueError:
            pass
        raise TrendshiftError("trendshift_period_invalid")

    def target(self, today: str):
        """Fixed provider host and a documented read-only path. No caller-supplied URL."""
        today = day(today, "today")
        if self.engine == PUBLIC:
            return "trendshift.io", "/", {}, "text/html"
        if self.kind == SPIKES:
            if self.start < f"{int(today[:4])-1:04d}-01-01" or self.end > today:
                raise TrendshiftError("trendshift_spike_dates_outside_contract")
            path = "/v1/engagement-spikes/" + self.metric
            query = {"limit": self.limit, "min_gain": self.min_gain, "start_date": self.start, "end_date": self.end}
            if self.max_gain is not None:query["max_gain"] = self.max_gain
        else:
            path = "/v1/github-trending" if self.kind == GITHUB else "/v1/trending/" + self.window
            if self.period is not None:
                parts = self.period_parts()
                first = (date.fromisoformat(parts[0]) if self.window == "daily" else
                         date.fromisocalendar(int(parts[0]), int(parts[1]), 1) if self.window == "weekly" else
                         date(int(parts[0]), int(parts[1]), 1) if self.window == "monthly" else date(int(parts[0]), 1, 1))
                if first > date.fromisoformat(today):raise TrendshiftError("trendshift_future_period_refused")
                path += "/" + "/".join(parts)
            query = {} if self.kind == GITHUB else {"limit": self.limit}
            if self.language is not None:query["language"] = self.language
        if self.cursor is not None:query["cursor"] = self.cursor
        return "api.trendshift.io", path, query, "application/json"

    def to_record(self):
        return {"record_type": REQUEST, **asdict(self)}

    def parameters(self):
        return {key: value for key, value in self.to_record().items() if value is not None}


def read_request(value):
    if type(value) is not dict or value.get("record_type") != REQUEST:
        raise TrendshiftError("trendshift_request_version")
    fields = set(TrendshiftRequest.__dataclass_fields__)
    if set(value) - fields - {"record_type"}:
        raise TrendshiftError("trendshift_request_fields")
    return TrendshiftRequest(**{key: value for key, value in value.items() if key != "record_type"})
