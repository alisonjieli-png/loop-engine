"""The public library page at /library: what the library holds, counted by every kind of harness file, before sign-up.

Kind: pure rendering over one catalogue view. The transport asks `rendered` for the page with the view it serves at
that moment, so a catalogue release published without a redeploy reaches this page within the refresher's minute.
Nothing here reads a request, a credential or an account's grants, and nothing here says how search works.

Roadmap step S-6.184 (September 24, 2026) made the page list every Verified item with its size and digest. The owner,
September 26, 2026: "we should make people sign up before showing them, and we should use a searchable table format
not a random HTML table/rows, also size, and digest are useless pieces of information to waste space on showing and we
need ALL types of harness working directory component files not just SKILLS". So this page lists no item one by one:
it counts the library by harness kind, shows one item's metadata, and
sends the visitor to sign up; the searchable table of every item is the signed-in library in the app.

```text
/library
├── the total in large type, the sentence that counts it by kind, and the one primary action
├── the combined counts by harness kind, from the served view, with each kind drawn to scale
├── one item's metadata, with no anonymous body read
├── the searchable table: after sign-up, in the app, at the plan's price from the layout standard record
└── the served release: what it added, changed and withdrew
```

The owner's orange design of September 26, 2026 (the Claude Design archive, view Library) sets the layout: the
large total, the kinds as bars, the item on a dark panel beside its explanation, one call to
sign up and the release as three numbers above its withdrawals. Its sample numbers and its release cadence are not
copied; every number here is read from the served view. The owner later removed the two review-class cards. The page's styles are the `design: library` block of
service.css, scoped to this view.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from html import escape
import re

from ..provisioning_server import LIBRARY_TIERS, QUALIFICATION_APPROVED, VERIFIED_TIER
from .catalogue_attributes import HARNESS_KINDS, harness_kind_label, harness_kind_of

ADDRESS = "/library"
VIEW = "library"
#: Where a signed-in account browses and searches the whole library as a table.
APP_LIBRARY_ADDRESS = "/app#browse-heading"
SIGN_UP_ADDRESS = "/get-started"
#: The metadata example when the served library holds it as Verified; otherwise the shortest Verified item.
SAMPLE_PREFERENCE = ("check_for_existing_work_before_building",)
#: The distribution whose own metadata names the public repository, from the project URLs in pyproject.toml.
DISTRIBUTION = "loop-engine"
#: The project URL labels that name the repository, as the packaging metadata normalizes them.
REPOSITORY_LABELS = ("repository", "source")


def handles(address: str) -> bool:
    return address == ADDRESS


@dataclass(frozen=True)
class LibraryRow:
    """One approved item the view serves, with the facts the page may count and the review record it names."""

    identity: str
    purpose: str
    kind: str
    harness_kind: str
    licence: str
    size_bytes: int
    tier: str
    approval_ref: str


def _shown(view, identity: str) -> dict:
    reader = getattr(view, "shown_attributes", None)
    if not callable(reader):
        return {}
    try:
        values = reader(identity)
    except Exception:  # noqa: BLE001 - an attribute that cannot be read is not shown
        return {}
    return values if isinstance(values, dict) else {}


def library_rows(view) -> "list[LibraryRow]":
    """Every approved item the view serves, in identity order, with its tier from the approval itself."""
    rows = []
    withdrawn = set(getattr(view, "withdrawn", ()) or ())
    for identity, binding in sorted(view.approved_bindings().items()):
        item = view.catalogue.items.get(identity)
        if item is None or (identity, item.digest) in withdrawn:
            continue
        try:
            decision = view.qualification_resolver.resolve(binding)
        except Exception:  # noqa: BLE001 - an item the resolver cannot decide is not shown
            continue
        if getattr(decision, "status", None) != QUALIFICATION_APPROVED or decision.library_tier not in LIBRARY_TIERS:
            continue
        declared = str(_shown(view, identity).get("harness_kind") or "")
        kind = harness_kind_of(item.kind, tuple(getattr(item, "styles", ()) or ()), (), declared)
        rows.append(LibraryRow(identity, item.purpose, item.kind, kind, item.license_name or "", int(item.size_bytes),
                               decision.library_tier, decision.approval_ref or ""))
    return rows


def sample(view, rows):
    """A metadata example only. The September 30 account rule excludes anonymous body reads."""
    verified = [row for row in rows if row.tier == VERIFIED_TIER]
    chosen = next((row for name in SAMPLE_PREFERENCE for row in verified if row.identity == name), None)
    if chosen is None:
        chosen = min(verified, key=lambda row: (row.size_bytes, row.identity), default=None)
    return chosen, None



def _sample_display_parts(body: str) -> tuple[str, str, str]:
    """Read a display title and an optional terminal source appendix without changing any body byte.

    Only unfenced ATX headings are considered. A later H1/H2 keeps the whole
    document visible, so a Source heading in the middle cannot hide a later
    instruction section. Possible raw HTML blocks also keep the document whole.
    This changes presentation only, never served material.
    """
    title, final_section, offset, fence, raw_html = "", None, 0, "", False
    for line in body.splitlines(keepends=True):
        text = line.rstrip("\r\n")
        marker = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", text)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip(" \t"):
                fence = ""
        elif marker:
            fence = marker[1]
        elif re.match(r" {0,3}<(?=[!/?A-Za-z])", text):
            raw_html = True
        elif not raw_html:
            heading = re.fullmatch(r" {0,3}(#{1,6})[ \t]+(.*)", text)
            if heading:
                label = re.sub(r"[ \t]+#+[ \t]*$", "", heading[2]).strip()
                level = len(heading[1])
                if level == 1 and not title:
                    title = label
                if level <= 2:
                    final_section = (level, label.casefold(), offset)
        offset += len(line)
    if not raw_html and final_section and final_section[0] == 2 and final_section[1] in {"source", "sources"}:
        split = final_section[2]
        return title or "Sample component", body[:split], body[split:]
    return title or "Sample component", body, ""


def release_changes(view) -> dict:
    """The served release's own record of what it added, changed and withdrew; empty for a view built in code."""
    value = getattr(view, "changes", None) or {}
    return {key: [row for row in value.get(key, []) if isinstance(row, dict) and row.get("identity")]
            for key in ("added", "changed", "withdrawn")}


def release_change_counts(view) -> dict:
    """How many items the served release added, changed and withdrew. A version 2 release states its counts and
    keeps a bounded number of rows; a version 1 release lists every row."""
    value = getattr(view, "changes", None) or {}
    counts = value.get("counts") if isinstance(value, dict) else None
    rows = release_changes(view)
    if isinstance(counts, dict):
        return {key: counts[key] if type(counts.get(key)) is int else len(rows[key]) for key in rows}
    return {key: len(value) for key, value in rows.items()}


def _items(count: int) -> str:
    return "no items" if count == 0 else "1 item" if count == 1 else f"{count:,} items"


def _project_urls():
    """The installed distribution's project URLs, as `Label, address` entries; none when it is not installed."""
    from importlib.metadata import PackageNotFoundError, metadata
    try:
        return tuple(metadata(DISTRIBUTION).get_all("Project-URL") or ())
    except PackageNotFoundError:
        return ()


def source_prefix() -> str:
    """Where a review record cited by a repository path can be read: the main line of the repository that the
    distribution's own metadata names. The address has one owner, pyproject.toml, and is never written here. Empty
    when the metadata names no https repository; the page then says the record is kept with the release. The address
    is split as text: this module renders a page and imports no network module, not even for parsing."""
    for entry in _project_urls():
        label, _, address = entry.partition(",")
        address = address.strip().rstrip("/")
        scheme, separator, rest = address.partition("://")
        if (label.strip().lower() in REPOSITORY_LABELS and scheme == "https" and separator and rest.split("/", 1)[0]
                and not any(character.isspace() for character in address)):
            return address + "/blob/main/"
    return ""


def _review_link(row: LibraryRow) -> str:
    path = row.approval_ref.split("#", 1)[0]
    prefix = source_prefix()
    if prefix and path.startswith(("examples/", "artifacts/", "docs/")) and ".." not in path.split("/"):
        return f'<a href="{escape(prefix + path)}">Review record</a>'
    return "Review record kept with the release"


def counts_by_harness_kind(rows) -> "list[tuple[str, int]]":
    """One combined count per kind, independent of the item's internal review path."""
    counted = Counter(row.harness_kind for row in rows)
    present = [kind for kind in HARNESS_KINDS if counted[kind]]
    present += sorted({row.harness_kind for row in rows} - set(HARNESS_KINDS))
    return [(kind, counted[kind]) for kind in present]


def _plural(label: str) -> str:
    """The plural of a kind's label in running text: "rules" and "harness settings" are plural already."""
    word = label.lower()
    return word if word.endswith("s") else word + "s"


def _share(count: int, largest: int) -> str:
    """How long a kind's bar is drawn, as a percentage of the largest kind; a kind that holds anything shows a sliver."""
    if count <= 0 or largest <= 0:
        return "0%"
    return f"{max(2, round(count * 100 / largest))}%"


def _bar(count: int, largest: int) -> str:
    """A bar drawn to scale. It is an SVG shape, because the page's content security policy refuses style attributes;
    the counts beside it carry the same fact for a reader who cannot see it."""
    return (f'<svg class="lib-bar" aria-hidden="true" focusable="false"><rect class="lib-bar-fill" width="{_share(count, largest)}"'
            ' height="100%" rx="4"/></svg>')


def _counts_table(rows) -> str:
    kinds = counts_by_harness_kind(rows)
    largest = max((count for _kind, count in kinds), default=0)
    body = "".join(f'<tr data-harness-kind="{escape(kind)}"><th scope="row">{escape(harness_kind_label(kind))}</th>'
                   f'<td class="lib-bar-cell">{_bar(count, largest)}</td>'
                   f'<td class="lib-num lib-all">{count:,}</td></tr>' for kind, count in kinds)
    return ('<div class="md-table-wrap lib-kinds"><table class="md-table lib-kind-table" data-library-counts><thead><tr>'
            '<th scope="col">Kind of file</th><th scope="col" class="lib-bar-cell"><span class="sr-only">Share of the '
            f'largest kind</span></th><th scope="col" class="lib-num">Packages</th></tr></thead><tbody>{body}'
            '<tr class="lib-total-row"><th scope="row">All kinds</th><td class="lib-bar-cell"></td>'
            f'<td class="lib-num lib-all">{len(rows):,}</td></tr></tbody></table></div>')


def _withdrawn_list(heading: str, rows) -> str:
    items = "".join(f'<li data-library-withdrawn="{escape(row["identity"])}"><code>{escape(row["identity"])}</code>'
                    + (f'<span>{escape(str(row.get("note") or ""))}</span>' if row.get("note") else "") + "</li>"
                    for row in rows)
    return f'<div class="lib-withdrawn"><h3>{escape(heading)}</h3><ul class="md-plain">{items}</ul></div>'


def _release_band(view, rows) -> str:
    changes, counts = release_changes(view), release_change_counts(view)
    summary = view.summary() if hasattr(view, "summary") else {}
    release = str(summary.get("release_id") or "")
    built = summary.get("built_at")
    served_since = (datetime.fromtimestamp(built, tz=timezone.utc).strftime("%B %d, %Y at %H:%M UTC").replace(" 0", " ")
                    if isinstance(built, (int, float)) and built > 0 else "")
    head = ['<h2 id="releases-title">Releases and withdrawals</h2>']
    if release:
        head.append(f'<p class="md-reading">This page shows catalogue release <code>{escape(release[:12])}</code>'
                    + (f", served since {escape(served_since)}" if served_since else "") + ". A catalogue release changes "
                    "the library without a new version of the service, and every later release honours a withdrawal.</p>")
    else:
        head.append('<p class="md-reading">A catalogue release changes the library without a new version of the service, '
                    "and every later release honours a withdrawal.</p>")
    lines = []
    if any(counts.values()):
        stats = "".join(f'<div><dt>{name}</dt><dd>{counts[key]:,}</dd></div>'
                        for key, name in (("added", "Added"), ("changed", "Changed"), ("withdrawn", "Withdrawn")))
        lines.append(f'<dl class="lib-stats">{stats}</dl>')
        lines.append(f'<p class="md-reading">This release added {_items(counts["added"])} and changed '
                     f'{_items(counts["changed"])}.</p>')
    if changes["withdrawn"]:
        lines.append(_withdrawn_list("Withdrawn in this release", changes["withdrawn"]))
    else:
        lines.append('<p class="md-reading">This release withdrew no item.</p>')
    # An item withdrawn after the release was published, on a customer report, a staff flag, a rescan or an
    # operator's command, keeps its record and its note here until a new review serves new bytes (roadmap S-6.199).
    listed = {row["identity"] for row in changes["withdrawn"]}
    later = sorted((row for row in (getattr(view, "withdrawal_notes", None) or {}).values()
                    if isinstance(row, dict) and row.get("identity") and row["identity"] not in listed),
                   key=lambda row: (row.get("withdrawn_at") or 0, row["identity"]))
    if later:
        lines.append(_withdrawn_list("Withdrawn since this release was published", later))
    return ('<div class="md-band lib-band" id="releases" aria-labelledby="releases-title"><div class="lib-split">'
            f'<div class="lib-split-head">{"".join(head)}</div><div class="lib-split-body">{"".join(lines)}</div></div></div>')


def _plan_price() -> str:
    """The plan's price as the layout standard record writes it, the one record every page's price is checked against."""
    from .web_site_map import load_layout_standard
    return str(load_layout_standard().price.get("phrase") or "")


def library_body(view, rows=None) -> str:
    """The page's own markup inside the site frame, written from one view."""
    rows = library_rows(view) if rows is None else rows
    kinds = counts_by_harness_kind(rows)
    population = view.file_population()
    files = population.get("distinct_files")
    measured = (population.get("record_type") == "catalogue_file_population/v1" and population.get("complete") is True
                and population.get("packages") == len(rows) and type(files) is int and files >= 0)
    package_word = "package" if len(rows) == 1 else "packages"
    total, unit = (files, "distinct component files") if measured else (len(rows), "reviewed packages")
    population_note = (f"{files:,} distinct files delivered in {len(rows):,} {package_word}. Identical shared files are counted once."
                       if measured else "The distinct file total is not measured for this catalogue. Packages and files are different units.")
    chosen, body = sample(view, rows)
    kind_names = ", ".join(_plural(harness_kind_label(kind)) for kind, _counts in kinds[:6])
    contents = [("counts", "What is in it")]
    if chosen is not None:
        contents.append(("sample", "One component's details"))
    contents += [("browse", "Search it as a table"), ("releases", "Releases")]
    intro = ('<div class="md-band md-intro lib-hero"><div class="lib-hero-grid"><h1 id="library-title">'
             f'<span class="lib-total">{total:,}</span> <span class="lib-title-words">{unit}, ready for '
             'your harness</span></h1><div class="lib-hero-copy">'
             f'<p class="lede">{len(rows):,} {package_word} a coding agent can fetch today, of {len(kinds)} kinds'
             + (f" ({escape(kind_names)}" + (", and more" if len(kinds) > 6 else "") + ")" if kinds else "")
             + ". Every package names its source, its "
             "licence and its review. Create an account to search the whole library as a table and download the "
             "exact version your agent chose.</p>"
             f'<p class="description" data-library-population>{population_note}</p>'
             f'<div class="md-actions"><a class="button primary" href="{SIGN_UP_ADDRESS}">Get started</a>'
             f'<a class="lib-text-link" href="{APP_LIBRARY_ADDRESS}">Sign in and browse</a></div></div></div>'
             '<nav class="md-contents lib-contents" aria-label="On this page">'
             + "".join(f'<a href="#{anchor}">{escape(text)}</a>' for anchor, text in contents) + "</nav></div>")
    counts = ('<div class="md-band lib-band" id="counts" aria-labelledby="counts-title"><div class="lib-section-head">'
              '<h2 id="counts-title">What is in it</h2><p class="md-reading">Every kind of file a harness picks up from its '
              'working directory, together in one library.</p></div><div class="lib-counts">'
              + _counts_table(rows) + "</div></div>")
    price = _plan_price()
    table = ('<div class="md-band lib-band lib-cta-band" id="browse" aria-labelledby="browse-title"><div class="lib-cta">'
             '<div class="lib-cta-copy"><h2 id="browse-title">Search it as a table</h2><p class="md-reading">A signed-in '
             "account sees every file in one searchable table: its purpose, the kind of file, the kinds of "
             "step it supports, its licence and the effects it declares, with a search box and sortable columns. Each "
             "row opens to the file's details. Public Good files need an account but no paid plan; other files need the stated access.</p>"
             + (f'<p class="lib-cta-price">Baltor Pro, {escape(price)}. <a href="{APP_LIBRARY_ADDRESS}">Sign in and '
                'browse</a></p>' if price else "")
             + f'</div><div class="md-actions"><a class="button primary" href="{SIGN_UP_ADDRESS}">Get started</a></div>'
             "</div></div>")
    if chosen is not None:
        shown = ('<div class="md-band lib-band" id="sample" aria-labelledby="sample-title"><div class="lib-split">'
                 '<div class="lib-split-head"><p class="lib-sample-label">One component’s details</p>'
                 '<h2 id="sample-title">See what a component is for.</h2>'
                 f'<p class="md-reading">{escape(harness_kind_label(chosen.harness_kind))} · '
                 f'{escape(chosen.licence or "Licence not stated")} · {_review_link(chosen)}</p>'
                 '<p class="md-reading">Every component download requires an account and is checked against its exact version.</p></div>'
                 f'<div><p class="md-reading">{escape(chosen.purpose[:400])}</p>'
                 f'<a href="{APP_LIBRARY_ADDRESS}">Sign in to inspect and download</a>'
                 '<p><a href="/public-good">Browse the free Public Good collection</a></p></div></div></div>')
    else:
        shown = ""
    return intro + counts + shown + table + _release_band(view, rows)


def library_page(view, site_map, display_name: str) -> str:
    """The whole page, framed like the other pages the service renders on its own."""
    from .model_directory_pages import SCHEMA_CONTEXT, Page, breadcrumbs, canonical, frame
    rows = library_rows(view)
    entry = site_map.page(ADDRESS)
    structured = {"@context": SCHEMA_CONTEXT, "@type": "CollectionPage", "name": entry.title,
                  "url": canonical(site_map, ADDRESS), "description": entry.description,
                  "mainEntity": {"@type": "ItemList", "numberOfItems": len(rows)},
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Library", ADDRESS)))}
    return frame(site_map, display_name, Page(ADDRESS, VIEW, entry.title, entry.description, library_body(view, rows),
                                              structured, "library-title"))


@lru_cache(maxsize=8)
def _framed(key, view_holder, display_name):
    from .web_site_map import load_site_map
    return library_page(view_holder.view, load_site_map(), display_name).encode("utf-8")


class _ViewHolder:
    """Carries a view into the cache without making the view part of the cache key."""

    def __init__(self, view):
        self.view = view

    def __hash__(self):
        return 0

    def __eq__(self, other):
        return isinstance(other, _ViewHolder)


def rendered(view, path: str, method: str, display_name: str, host: "str | None" = None):
    """`(body, media_type)` for /library, or None for any other address or method.

    The page is rendered once for each served catalogue (its release, content digest, state revision and build time),
    then given the head the site map writes for its hostname and the release versions of its assets."""
    from . import web_pages
    if method not in ("GET", "HEAD") or not handles(path):
        return None
    summary = view.summary() if hasattr(view, "summary") else {}
    key = (summary.get("release_id"), summary.get("content_digest"), summary.get("catalogue_state_revision"),
           summary.get("built_at"), summary.get("items"))
    body = _framed(key, _ViewHolder(view), display_name)
    head = web_pages.page_head(web_pages.packaged_site_map(), path, host, display_name)
    if head is not None:
        body = web_pages.with_page_head(body, head)
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE


def empty_view():
    """A view that serves nothing, for checks that render every page of the site map without a running service."""
    from ..harness_intelligence import HarnessIntelligenceCatalogue
    from ..provisioning_server import ProvisioningQualificationResolver
    from .catalogue_serving import CatalogueView

    def refuse(_binding):
        raise LookupError("this view approves nothing")
    return CatalogueView(HarnessIntelligenceCatalogue({}), ProvisioningQualificationResolver("library-empty-view", refuse),
                         lambda item: "")
