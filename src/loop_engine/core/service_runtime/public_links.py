"""Counted links from the public lists: a redirect through the service that keeps one count per link per day.

Kind: service adapter with its passive link tables. Every outbound link of a public list (the directory of MCP
servers and agent APIs, the directory of models and endpoints) points to `/out/<list>/<link>/<row>` on this
service. `<link>` is `site`, the row's own documentation or home address, `code`, its code repository when that
is a second address, or `paid`, the reviewed paid link of a row whose commercial relationship is active. The answer is a redirect to the one address the packaged link table of that
list holds for that row and link; an unknown list, link or row is not found, so the path can never send a reader
anywhere the list does not name. Serving a list page adds one to that list's views for the day.

The owner approved aggregate link counting in the privacy notice changes of September 24, 2026. The counter
therefore reads only the path. It never reads or keeps a network address, a browser detail, a referring page,
a cookie or an account; the functions below receive nothing but the path and the day. Counts are kept per list,
row, link and day in Coordinated Universal Time, in memory, and written to the service database every five
minutes and when the service stops, as records the retention rule folds into monthly totals after 400 days. A
redirect answers with no caching and asks search engines not to index it, and robots.txt disallows `/out/`.

Link tables are packaged beside this module in `public_lists/<list>.json`, one per list, written by the list's
builder. A table names the list's pages and, for each row, the plain address without its scheme and, when a
paid link is active, that https address. Nothing here joins a programme or chooses a destination.
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
from datetime import datetime, timedelta, timezone

from .records import ServiceRuntimeError

LINK_TABLE_RECORD_TYPE = "public_list_links/v1"
COUNT_KIND = "public_list_count"
MONTHLY_KIND = "public_list_monthly_count"
COUNT_RECORD_TYPE = "public_list_count/v1"
MONTHLY_RECORD_TYPE = "public_list_monthly_count/v1"
OUT_PREFIX = "/out/"
SITE, CODE, PAID = "site", "code", "paid"
LINKS = (SITE, CODE, PAID)
FOLLOW, VIEW = "follow", "view"
FLUSH_SECONDS = 300
KEEP_DAYS = 400
TABLE_FOLDER = "public_lists"
REDIRECT_HEADERS = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow", "Referrer-Policy": "no-referrer"}
_SECURE_SCHEME = "https"
_LIST_NAME = re.compile(r"[a-z][a-z0-9-]{0,39}\Z")
#: A host of dotted labels, an optional port, then nothing or a path, query or fragment. Text after the host must
#: start with /, ? or #, so "example.com@elsewhere.org" is refused while "/package/@scope/name" is kept.
_ADDRESS = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})(?::[0-9]{1,5})?"
                      r"(?:[/?#][^\s\\]*)?\Z", re.IGNORECASE)


class PublicLinkError(ValueError):
    """A link table this service refuses to load, with the reason."""


def utc_day(now=None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def _address(value: str) -> str:
    """An https destination: a table address without its scheme becomes https; any other value is refused."""
    if not isinstance(value, str) or not value:
        raise PublicLinkError("a destination is a nonempty address")
    secure = _SECURE_SCHEME + "://"
    plain = value[len(secure):] if value.startswith(secure) else value
    if "://" in plain or not _ADDRESS.match(plain):
        raise PublicLinkError(f"a destination is a public https address: {value[:80]!r}")
    return secure + plain


def read_link_table(record) -> dict:
    """One list's table: its name, its pages and each row's destinations, checked before any use."""
    if not isinstance(record, dict) or record.get("record_type") != LINK_TABLE_RECORD_TYPE:
        raise PublicLinkError(f"a link table is {LINK_TABLE_RECORD_TYPE}")
    if set(record) != {"record_type", "list", "pages", "rows"}:
        raise PublicLinkError("a link table holds exactly record_type, list, pages and rows")
    name, pages, rows = record["list"], record["pages"], record["rows"]
    if not isinstance(name, str) or not _LIST_NAME.match(name):
        raise PublicLinkError("a list name is a short lowercase token")
    if not isinstance(pages, list) or not all(isinstance(page, str) and page.startswith("/") for page in pages):
        raise PublicLinkError("a list names the addresses of its pages")
    if not isinstance(rows, dict):
        raise PublicLinkError("a link table maps each row to its links")
    table = {}
    for row, links in rows.items():
        if not isinstance(row, str) or not row or not isinstance(links, dict) or not links or not set(links) <= set(LINKS):
            raise PublicLinkError(f"row {str(row)[:80]!r} names at least one of the links {LINKS} and no other")
        table[row] = {link: _address(address) for link, address in links.items()}
    return {"list": name, "pages": tuple(pages), "rows": table}


def packaged_link_tables() -> dict:
    """Every link table packaged beside this module, by list name."""
    from importlib.resources import files
    folder = files(__package__).joinpath(TABLE_FOLDER)
    tables = {}
    if not folder.is_dir():
        return tables
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if entry.name.endswith(".json"):
            table = read_link_table(json.loads(entry.read_text(encoding="utf-8")))
            if table["list"] in tables or entry.name != table["list"] + ".json":
                raise PublicLinkError(f"{entry.name} does not name its own list once")
            tables[table["list"]] = table
    return tables


class PublicListLinks:
    """The counted redirects of the public lists and their daily counts, kept in memory until written."""

    def __init__(self, runtime=None, tables=None, *, clock=None, flush_seconds: int = FLUSH_SECONDS):
        self.runtime = runtime
        self._tables = tables
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.flush_seconds = flush_seconds
        self._pending: dict = {}
        self._lock = threading.Lock()
        self._task = None
        self._folded_day = ""
        self.last_flush = {"outcome": "not_run", "written": 0}

    @property
    def tables(self) -> dict:
        if self._tables is None:
            self._tables = packaged_link_tables()
        return self._tables

    def list_of_page(self, path: str) -> str:
        """The list a page address belongs to, or empty for any other page."""
        return next((name for name, table in self.tables.items() if path in table["pages"]), "")

    def destination(self, path: str) -> "tuple[str, str, str, str] | None":
        """The list, link, row and https address a counted path names, or None when the lists hold no such link."""
        if not path.startswith(OUT_PREFIX):
            return None
        parts = path[len(OUT_PREFIX):].split("/", 2)
        if len(parts) != 3:
            return None
        name, link, row = parts
        address = self.tables.get(name, {}).get("rows", {}).get(row, {}).get(link)
        return (name, link, row, address) if address else None

    def _add(self, key) -> None:
        with self._lock:
            self._pending[key] = self._pending.get(key, 0) + 1

    def followed(self, path: str) -> "str | None":
        """Count one follow of a known link and return where it goes; an unknown path counts nothing."""
        found = self.destination(path)
        if found is None:
            return None
        name, link, row, address = found
        self._add((utc_day(self._clock()), name, FOLLOW, link, row))
        return address

    def viewed(self, path: str) -> bool:
        """Count one view of a list page; any other page counts nothing."""
        name = self.list_of_page(path)
        if name:
            self._add((utc_day(self._clock()), name, VIEW, "", ""))
        return bool(name)

    def pending(self) -> dict:
        with self._lock:
            return dict(self._pending)

    def flush(self) -> dict:
        """Write the pending counts to the service database in one batch, adding to what each day holds."""
        with self._lock:
            pending, self._pending = self._pending, {}
        if not pending:
            self.last_flush = {"outcome": "completed", "written": 0}
            return self.last_flush
        catalog = getattr(self.runtime, "_catalog", None)
        if catalog is None or self.runtime.config.writes_authorized is not True:
            self._restore(pending)
            self.last_flush = {"outcome": "not_written", "written": 0}
            return self.last_flush
        try:
            with catalog.store(write=True) as store:
                rows, guards = [], []
                for (day, name, event, link, row), count in sorted(pending.items()):
                    identity = "|".join((day, name, event, link, row))
                    held = catalog.read(store, COUNT_KIND, identity)
                    total = count + (int(held["payload"].get("count", 0)) if held else 0)
                    rows.append(catalog.record(COUNT_KIND, identity, {
                        "record_type": COUNT_RECORD_TYPE, "day": day, "list": name, "event": event, "link": link,
                        "row": row, "count": total}))
                    guards.append(catalog.guard(held, catalog.identity(COUNT_KIND, identity)))
                catalog.commit(store, rows, guards)
        except Exception as error:  # noqa: BLE001 - a failed write keeps its counts for the next flush
            self._restore(pending)
            self.last_flush = {"outcome": "failed", "written": 0, "code": getattr(error, "code", type(error).__name__)}
            return self.last_flush
        self.last_flush = {"outcome": "completed", "written": len(pending)}
        return self.last_flush

    def _restore(self, pending: dict) -> None:
        with self._lock:
            for key, count in pending.items():
                self._pending[key] = self._pending.get(key, 0) + count

    def start(self):
        """Start the periodic flush in the running event loop, once, when the host allows writes."""
        if self._task is None and self.runtime is not None and self.runtime.config.writes_authorized is True:
            self._task = asyncio.get_running_loop().create_task(self._run())
        return self._task

    def maintain(self) -> dict:
        """One scheduled pass: write the pending counts, and once a day fold the counts older than 400 days."""
        report = self.flush()
        today = utc_day(self._clock())
        if report["outcome"] == "completed" and today != self._folded_day:
            try:
                report = {**report, "fold": fold_old_days(self.runtime, today)}
                self._folded_day = today
            except Exception as error:  # noqa: BLE001 - a failed fold is tried again on the next pass
                report = {**report, "fold": {"outcome": "failed", "code": getattr(error, "code", type(error).__name__)}}
        return report

    async def _run(self):
        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(self.flush_seconds)
            await loop.run_in_executor(None, self.maintain)

    async def stop(self):
        """Cancel the periodic flush and write what is pending, never failing the shutdown."""
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        try:
            await asyncio.get_running_loop().run_in_executor(None, self.flush)
        except Exception:  # noqa: BLE001 - stopping never fails the shutdown it belongs to
            pass

    def redirect(self, path: str, method: str, response_class):
        """The answer to a counted path: a redirect to the list's own address, or None for an unknown link."""
        if method == "HEAD":
            found = self.destination(path)
            address = found[3] if found else None
        else:
            address = self.followed(path)
        if address is None:
            return None
        return response_class(status_code=302, headers={**REDIRECT_HEADERS, "Location": address})


def fold_old_days(runtime, today: str, *, keep_days: int = KEEP_DAYS) -> dict:
    """Fold daily counts older than keep_days into monthly totals and remove the daily records."""
    catalog = runtime._catalog
    limit = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    with catalog.store(write=True) as store:
        old = [row for row in catalog.rows_all(store, COUNT_KIND) if row["payload"].get("day", "9999") < limit]
        if not old:
            return {"folded": 0}
        totals, removed_guards = {}, []
        for row in old:
            payload = row["payload"]
            key = "|".join((payload["day"][:7], payload["list"], payload["event"], payload["link"], payload["row"]))
            totals[key] = totals.get(key, 0) + int(payload.get("count", 0))
            removed_guards.append(catalog.guard(row))
        rows, guards = [], list(removed_guards)
        for key, count in sorted(totals.items()):
            held = catalog.read(store, MONTHLY_KIND, key)
            month, name, event, link, row = key.split("|", 4)
            rows.append(catalog.record(MONTHLY_KIND, key, {
                "record_type": MONTHLY_RECORD_TYPE, "month": month, "list": name, "event": event, "link": link,
                "row": row, "count": count + (int(held["payload"].get("count", 0)) if held else 0)}))
            guards.append(catalog.guard(held, catalog.identity(MONTHLY_KIND, key)))
        catalog.commit(store, rows, guards, removals=[row["record_id"] for row in old])
    return {"folded": len(old), "months": len(totals)}


def require_list_name(name: str) -> str:
    if not isinstance(name, str) or not _LIST_NAME.match(name):
        raise ServiceRuntimeError("invalid_list_name")
    return name
