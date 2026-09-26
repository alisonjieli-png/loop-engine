"""The changelog, the feature list and the open work: three pages nothing links to, rendered from one packaged record.

Kind: pure rendering over one packaged record and the typed site map. The transport asks `rendered` for a page after
the decision red team page finds nothing; the surface checks and the site map checks ask the same way. Nothing here
reads a request, a credential, an account, the roadmap or an artifacts folder, and nothing here calls a model.

The owner, September 26, 2026: "Do we have a public changelog, feature list, and todo pages? We could add these, public
links, but they can be undiscoverable (no page linking to them) but if you have those it would be really helpful". So
the site map lists /changelog, /features and /todo with no place that links to them and that sentence as the reason.
Like every page the site map does not list for search engines, they carry noindex and stay out of sitemap.xml.

The record, `web_assets/status-pages/status-pages.json`, is written by `tools/build_public_status_pages.py` from the
authoritative records: the Fly release records and the Community release records under `artifacts/`, CHANGELOG.md, the
site map, the capabilities builder in `http.py` (read as code), the served attribute declarations, the client recipes,
the layout standard's price and the roadmap. The continuation status generator and the records index builder run the
same command, and their `--check` refuses a stale record, so the pages follow the records. Every fact a page prints is
a field of that record; this module writes only the sentences that frame them.

```text
/changelog   every service release and every library release, newest first, then the earlier changelog
/features    the plan, the pages, the library's kinds, labels and attributes, the harnesses Get set up connects,
             and what the capabilities record reports
/todo        the open roadmap steps by delivery package in launch order, each with its status in plain words
```

The pages use plain public words. The names of the runtime stay in the records and in the repository.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from html import escape
import json

#: The three addresses and the view that shows each, as the site map lists them.
ADDRESSES = {"/changelog": "changelog", "/features": "features", "/todo": "todo"}
RECORD_TYPE = "public_status_pages/v1"
#: The packaged record, under the served files' folder; it is not served itself.
RECORD_FOLDER = "status-pages"
RECORD_FILE = "status-pages.json"
RECORD_FIELDS = ("record_type", "generated_by", "changelog", "features", "todo")
RELEASE_KINDS = ("service", "library")
RELEASE_FIELDS = ("kind", "number", "at", "lines", "seen_after_release", "not_shown")
EARLIER_FIELDS = ("heading", "lines", "not_shown")
FEATURE_FIELDS = ("plan", "page_groups", "harness_kinds", "tiers", "attributes", "harnesses", "capabilities")
CAPABILITY_FIELDS = ("section", "feature", "value", "fixed")
TODO_FIELDS = ("steps", "live", "checked", "open", "listed", "groups")
#: What a capability that the code does not fix says in place of a value: each deployment sets it, or the running
#: service computes it, and the capabilities record reports it.
REPORTED_LIVE = "Reported by the running service"


class StatusPageError(ValueError):
    """A page record this reader refuses, with the reason."""


@dataclass(frozen=True)
class PageRecord:
    """The checked record, as plain values."""

    value: dict

    @property
    def changelog(self) -> dict:
        return self.value["changelog"]

    @property
    def features(self) -> dict:
        return self.value["features"]

    @property
    def todo(self) -> dict:
        return self.value["todo"]


def handles(address: str) -> bool:
    return address in ADDRESSES


def _fields(value, where: str, names) -> dict:
    if not isinstance(value, dict):
        raise StatusPageError(f"{where} must be an object")
    missing, unknown = sorted(set(names) - set(value)), sorted(set(value) - set(names))
    if missing or unknown:
        raise StatusPageError(f"{where} has missing fields {missing} and unknown fields {unknown}")
    return value


def _text(value, where: str, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise StatusPageError(f"{where} must be a{'' if empty else ' nonempty'} string")
    return value


def _texts(value, where: str) -> list:
    if not isinstance(value, list):
        raise StatusPageError(f"{where} must be a list")
    return [_text(item, where) for item in value]


def _count(value, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise StatusPageError(f"{where} must be a whole number of at least 0")
    return value


def _moment(value, where: str) -> str:
    try:
        datetime.fromisoformat(_text(value, where).replace("Z", "+00:00"))
    except ValueError as error:
        raise StatusPageError(f"{where} is not a date and time: {value!r}") from error
    return value


def _check_changelog(value) -> None:
    row = _fields(value, "changelog", ("releases", "earlier"))
    if not isinstance(row["releases"], list) or not row["releases"]:
        raise StatusPageError("changelog.releases must be a nonempty list")
    moments = []
    for index, item in enumerate(row["releases"]):
        where = f"changelog.releases[{index}]"
        release = _fields(item, where, RELEASE_FIELDS)
        if release["kind"] not in RELEASE_KINDS:
            raise StatusPageError(f"{where}.kind must be one of {RELEASE_KINDS}")
        _count(release["number"], where + ".number")
        moments.append(datetime.fromisoformat(_moment(release["at"], where + ".at").replace("Z", "+00:00")))
        _texts(release["lines"], where + ".lines")
        _text(release["seen_after_release"], where + ".seen_after_release", empty=True)
        _count(release["not_shown"], where + ".not_shown")
    if moments != sorted(moments, reverse=True):
        raise StatusPageError("changelog.releases are listed newest first")
    if not isinstance(row["earlier"], list):
        raise StatusPageError("changelog.earlier must be a list")
    for index, item in enumerate(row["earlier"]):
        section = _fields(item, f"changelog.earlier[{index}]", EARLIER_FIELDS)
        _text(section["heading"], f"changelog.earlier[{index}].heading")
        _texts(section["lines"], f"changelog.earlier[{index}].lines")
        _count(section["not_shown"], f"changelog.earlier[{index}].not_shown")


def _check_features(value) -> None:
    row = _fields(value, "features", FEATURE_FIELDS)
    _text(row["plan"], "features.plan")
    for index, group in enumerate(row["page_groups"]):
        _fields(group, f"features.page_groups[{index}]", ("group", "pages"))
        for number, page in enumerate(group["pages"]):
            where = f"features.page_groups[{index}].pages[{number}]"
            _fields(page, where, ("address", "title", "description"))
            if page["address"] in ADDRESSES or not _text(page["address"], where).startswith("/"):
                raise StatusPageError(f"{where}.address is a listed page other than these three")
            _text(page["title"], where + ".title")
            _text(page["description"], where + ".description")
    _texts(row["harness_kinds"], "features.harness_kinds")
    for index, tier in enumerate(row["tiers"]):
        _fields(tier, f"features.tiers[{index}]", ("label", "meaning"))
    for index, attribute in enumerate(row["attributes"]):
        where = f"features.attributes[{index}]"
        _fields(attribute, where, ("name", "description", "searchable", "filterable", "choices"))
        if not isinstance(attribute["searchable"], bool) or not isinstance(attribute["filterable"], bool):
            raise StatusPageError(f"{where} says whether search reads and filters it")
        _texts(attribute["choices"], where + ".choices")
    _texts(row["harnesses"], "features.harnesses")
    for index, capability in enumerate(row["capabilities"]):
        where = f"features.capabilities[{index}]"
        _fields(capability, where, CAPABILITY_FIELDS)
        if not isinstance(capability["fixed"], bool) or (capability["fixed"] and not capability["value"]):
            raise StatusPageError(f"{where} is fixed with a value, or set by each deployment")


def _check_todo(value) -> None:
    row = _fields(value, "todo", TODO_FIELDS)
    for name in ("steps", "live", "checked", "open", "listed"):
        _count(row[name], "todo." + name)
    listed = 0
    for index, group in enumerate(row["groups"]):
        _fields(group, f"todo.groups[{index}]", ("title", "steps"))
        _text(group["title"], f"todo.groups[{index}].title")
        for number, step in enumerate(group["steps"]):
            _fields(step, f"todo.groups[{index}].steps[{number}]", ("step", "title", "status"))
            listed += 1
    if listed != row["listed"] or row["listed"] > row["open"] or row["live"] + row["checked"] + row["open"] != row["steps"]:
        raise StatusPageError("todo counts disagree with the listed steps")


def page_record_from_value(value) -> PageRecord:
    """Read a page record, or refuse it with the reason."""
    row = _fields(value, "page record", RECORD_FIELDS)
    if row["record_type"] != RECORD_TYPE:
        raise StatusPageError(f"this reader reads {RECORD_TYPE}, not {row['record_type']!r}")
    _text(row["generated_by"], "generated_by")
    _check_changelog(row["changelog"])
    _check_features(row["features"])
    _check_todo(row["todo"])
    return PageRecord(row)


def _packaged_value():
    from importlib.resources import files
    path = files("loop_engine").joinpath("core", "service_runtime", "web_assets", RECORD_FOLDER, RECORD_FILE)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_page_record() -> PageRecord:
    """The packaged record, read and checked once; a new release starts a new process."""
    return page_record_from_value(_packaged_value())


# Rendering.

def _when(value: str) -> str:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment.strftime("%B %d, %Y at %H:%M UTC").replace(" 0", " ")


def _items(lines) -> str:
    return '<ul class="md-plain">' + "".join(f"<li>{escape(line)}</li>" for line in lines) + "</ul>" if lines else ""


def _not_shown(count: int, shown: int) -> str:
    """The sentence for the changes of a record that a page does not repeat: lines written in internal terms, and lines
    the reviewed exclusion list leaves out. It says how many, never which or why, so it points at nothing."""
    if not count:
        return ""
    if shown:
        words = "One more change in the record is" if count == 1 else f"{count:,} more changes in the record are"
    else:
        words = "The one change in the record is" if count == 1 else f"The {count:,} changes in the record are"
    return f'<p class="md-reading">{words} not repeated here.</p>'


def _release(release: dict) -> str:
    name = ("Service release" if release["kind"] == "service" else "Library release") + f" {release['number']}"
    anchor = f"{release['kind']}-release-{release['number']}"
    seen = (f'<p class="md-reading">After the release: {escape(release["seen_after_release"])}</p>'
            if release["seen_after_release"] else "")
    shown = len(release["lines"]) + bool(release["seen_after_release"])
    empty = ('<p class="md-reading">The record of this release lists no changes.</p>'
             if not shown and not release["not_shown"] else "")
    # The time sits in the facts list the model directory pages use, so it is set like their facts.
    return (f'<article class="md-release" id="{anchor}" data-release="{escape(anchor)}"><h3>{escape(name)}</h3>'
            f'<dl class="md-facts"><div><dt>Released</dt><dd><time datetime="{escape(release["at"])}">'
            f'{escape(_when(release["at"]))}</time></dd></div></dl>'
            f"{_items(release['lines'])}{seen}{empty}{_not_shown(release['not_shown'], shown)}</article>")


def changelog_body(record: PageRecord) -> str:
    value = record.changelog
    links = [("releases", "Releases")] + ([("earlier", "Before the live service")] if value["earlier"] else [])
    from .model_directory_pages import contents
    intro = ('<div class="md-band md-intro"><p class="eyebrow">Changelog</p><h1 id="changelog-title">Changelog</h1>'
             '<p class="lede">Every release of the service and of its library, newest first. Each line is taken from the '
             "release's own record.</p>" + contents(links) + "</div>")
    releases = ('<div class="md-band" id="releases" aria-labelledby="releases-title"><h2 id="releases-title">Releases</h2>'
                '<p class="md-reading">A service release changes the website and the service; a library release changes '
                "the files the library serves, without a new service release.</p>"
                + "".join(_release(release) for release in value["releases"]) + "</div>")
    earlier = ""
    if value["earlier"]:
        sections = "".join(f'<h3>{escape(section["heading"])}</h3>{_items(section["lines"])}'
                           f'{_not_shown(section["not_shown"], len(section["lines"]))}' for section in value["earlier"])
        earlier = ('<div class="md-band" id="earlier" aria-labelledby="earlier-title"><h2 id="earlier-title">Before the '
                   'live service</h2><p class="md-reading">The changelog of the code before the first release of the live '
                   f"service, one line for each change.</p>{sections}</div>")
    return intro + releases + earlier


def _definitions(rows) -> str:
    return '<dl class="md-dl">' + "".join(f"<div><dt>{term}</dt><dd>{escape(text)}</dd></div>" for term, text in rows) + "</dl>"


def features_body(record: PageRecord) -> str:
    from .model_directory_pages import contents
    value = record.features
    links = [("plan", "The plan"), ("pages", "Pages"), ("library", "The library"), ("harnesses", "Harnesses"),
             ("service", "What the service reports")]
    intro = ('<div class="md-band md-intro"><p class="eyebrow">Features</p><h1 id="features-title">What Baltor does today'
             '</h1><p class="lede">The pages, the library, the harnesses it connects and the plan, each read from the '
             "service's own records.</p>" + contents(links) + "</div>")
    plan = ('<div class="md-band" id="plan" aria-labelledby="plan-title"><h2 id="plan-title">The plan</h2>'
            f'<p class="md-reading">The price is {escape(value["plan"])}.</p></div>')
    groups = "".join(f'<h3>{escape(group["group"])}</h3>' + _definitions(
        (f'<a href="{escape(page["address"])}">{escape(page["title"])}</a>', page["description"]) for page in group["pages"])
        for group in value["page_groups"])
    pages = ('<div class="md-band" id="pages" aria-labelledby="pages-title"><h2 id="pages-title">Pages</h2>'
             f'<p class="md-reading">Every page search engines may list, with the description each page gives.</p>{groups}</div>')
    kinds = ", ".join(value["harness_kinds"])
    tiers = _definitions((escape(tier["label"]), tier["meaning"]) for tier in value["tiers"])
    head = ('<thead><tr><th scope="col">Attribute</th><th scope="col">What it holds</th><th scope="col">Search reads it</th>'
            '<th scope="col">Search filters by it</th></tr></thead>')
    rows = "".join(f'<tr><th scope="row">{escape(item["name"])}</th><td>{escape(item["description"])}</td>'
                   f'<td>{"Yes" if item["searchable"] else "No"}</td><td>{"Yes" if item["filterable"] else "No"}</td></tr>'
                   for item in value["attributes"])
    library = ('<div class="md-band" id="library" aria-labelledby="library-title"><h2 id="library-title">The library</h2>'
               f'<p class="md-reading">The kinds of file the library serves: {escape(kinds)}.</p>'
               f'<h3>The two labels</h3>{tiers}<h3>What every file carries</h3><div class="md-table-wrap">'
               f'<table class="md-table">{head}<tbody>{rows}</tbody></table></div></div>')
    harnesses = ('<div class="md-band" id="harnesses" aria-labelledby="harnesses-title"><h2 id="harnesses-title">Harnesses'
                 '</h2><p class="md-reading">Get set up gives a written setup for each of these harnesses.</p>'
                 + _items(value["harnesses"]) + "</div>")
    head = ('<thead><tr><th scope="col">Part</th><th scope="col">Feature</th><th scope="col">In this release</th></tr>'
            "</thead>")
    rows = "".join(f'<tr><th scope="row">{escape(item["section"])}</th><td>{escape(item["feature"])}</td>'
                   f'<td>{escape(item["value"] if item["fixed"] else REPORTED_LIVE)}</td></tr>'
                   for item in value["capabilities"])
    service = ('<div class="md-band" id="service" aria-labelledby="service-title"><h2 id="service-title">What the service '
               'reports</h2><p class="md-reading">The service publishes a capabilities record that any client can read. '
               "These are its parts as the service code builds them: a value fixed in the code of this release, or one "
               "that each deployment sets and the running service reports.</p>"
               f'<div class="md-table-wrap"><table class="md-table">{head}<tbody>{rows}</tbody></table></div></div>')
    return intro + plan + pages + library + harnesses + service


def todo_body(record: PageRecord) -> str:
    from .model_directory_pages import contents
    value = record.todo
    intro = ('<div class="md-band md-intro"><p class="eyebrow">Open work</p><h1 id="todo-title">Open work</h1>'
             f'<p class="lede">The open steps of the development plan, grouped by delivery package in launch order. Of '
             f'{value["steps"]:,} steps, {value["live"]:,} are live and checked on the live service, {value["checked"]:,} '
             f'more are finished and checked by automated tests, and {value["open"]:,} are open.</p>'
             + contents([("steps", "The open steps"), ("left-out", "What this page leaves out")]) + "</div>")
    head = '<thead><tr><th scope="col">Step</th><th scope="col">Status</th></tr></thead>'
    groups = "".join(f'<h3>{escape(group["title"])}</h3><div class="md-table-wrap"><table class="md-table">{head}<tbody>'
                     + "".join(f'<tr><th scope="row">{escape(step["title"])}</th><td>{escape(step["status"])}</td></tr>'
                               for step in group["steps"])
                     + "</tbody></table></div>" for group in value["groups"])
    steps = ('<div class="md-band" id="steps" aria-labelledby="steps-title"><h2 id="steps-title">The open steps</h2>'
             f'<p class="md-reading">{value["listed"]:,} open steps, each with its title and its status.</p>{groups}</div>')
    left = value["open"] - value["listed"]
    left_out = ('<div class="md-band md-quiet" id="left-out" aria-labelledby="left-out-title"><h2 id="left-out-title">What '
                f'this page leaves out</h2><p class="md-reading">{left:,} open step{"" if left == 1 else "s"} '
                f'{"is" if left == 1 else "are"} not listed here. The plan keeps each step\'s evidence and next work; this '
                "page shows only titles and status.</p></div>")
    return intro + steps + left_out


BODIES = {"/changelog": changelog_body, "/features": features_body, "/todo": todo_body}
LABELLED_BY = {"/changelog": "changelog-title", "/features": "features-title", "/todo": "todo-title"}


def status_page(record: PageRecord, address: str, site_map, display_name: str) -> str:
    """The whole page at one of the three addresses, framed like the other pages the service renders on its own."""
    from .model_directory_pages import SCHEMA_CONTEXT, Page, breadcrumbs, canonical, frame
    entry = site_map.page(address)
    if entry is None or address not in ADDRESSES:
        raise StatusPageError(f"the site map does not list {address}")
    structured = {"@context": SCHEMA_CONTEXT, "@type": "WebPage", "name": entry.title, "url": canonical(site_map, address),
                  "description": entry.description,
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), (entry.title, address)))}
    return frame(site_map, display_name, Page(address, ADDRESSES[address], entry.title, entry.description,
                                              BODIES[address](record), structured, LABELLED_BY[address]))


@lru_cache(maxsize=12)
def _framed(address: str, display_name: str) -> bytes:
    from .web_site_map import load_site_map
    return status_page(load_page_record(), address, load_site_map(), display_name).encode("utf-8")


def rendered(path: str, method: str, display_name: str, host: "str | None" = None):
    """`(body, media_type)` for one of the three pages at its address on any hostname, or None.

    The page is rendered once for each deployment name, then given the head the site map writes for its address,
    which carries noindex because the site map does not list it, and the release versions of its assets."""
    from . import web_pages
    if method not in ("GET", "HEAD") or not handles(path):
        return None
    body = _framed(path, display_name)
    head = web_pages.page_head(web_pages.packaged_site_map(), path, host, display_name)
    if head is not None:
        body = web_pages.with_page_head(body, head)
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE
