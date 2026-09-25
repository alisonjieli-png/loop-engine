"""The public library page at /library: what the library holds, readable before anyone pays.

Kind: pure rendering over one catalogue view. The transport asks `rendered` for the page with the view it serves at
that moment, so a catalogue release published without a redeploy reaches this page within the refresher's minute.
Nothing here reads a request, a credential or an account's grants, and nothing here says how search works.

Roadmap step S-6.184, from the stakeholder review of September 24, 2026: "Browse the library" ended at a sign-in
prompt, so a visitor could not judge the library before paying. The page lists every Verified item with its purpose,
kind, licence, size, digest and review record; it stands counts by kind and tier in for the Community items, which it
does not list one by one; it prints one item in full; and it lists what the served release added, changed and
withdrew, with each withdrawal's note. Search beyond this page and every download still need an account.

```text
/library
├── the counts, from the served view
├── what the two labels mean, in the words the service publishes
├── Verified items, one row each, with the review record an approval names
├── Community items, as counts by kind only
├── one item in full, read through the view like any served body
└── the served release: what it added, changed and withdrew
```
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from html import escape

from ..provisioning_server import COMMUNITY_TIER, LIBRARY_TIERS, QUALIFICATION_APPROVED, TIER_LABELS, VERIFIED_TIER
from .catalogue_tiers import TIER_MEANINGS

ADDRESS = "/library"
VIEW = "library"
#: The item printed in full when the served library holds it as Verified; otherwise the shortest Verified item.
SAMPLE_PREFERENCE = ("check_for_existing_work_before_building",)
#: The distribution whose own metadata names the public repository, from the project URLs in pyproject.toml.
DISTRIBUTION = "loop-engine"
#: The project URL labels that name the repository, as the packaging metadata normalizes them.
REPOSITORY_LABELS = ("repository", "source")
#: The plain name of each item kind the catalogue knows; any other kind is shown as it is written.
KIND_NAMES = {"skill": "Skill", "instruction_file": "Instruction file", "tool": "Tool", "reusable_code": "Reusable code"}


def handles(address: str) -> bool:
    return address == ADDRESS


@dataclass(frozen=True)
class LibraryRow:
    """One approved item the view serves, with the facts the page may show and the review record it names."""

    identity: str
    purpose: str
    kind: str
    licence: str
    size_bytes: int
    digest: str
    tier: str
    approval_ref: str


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
        rows.append(LibraryRow(identity, item.purpose, item.kind, item.license_name or "", int(item.size_bytes),
                               item.digest, decision.library_tier, decision.approval_ref or ""))
    return rows


def sample(view, rows):
    """(row, body) of the one item printed in full, or (None, None) when the view serves no Verified item."""
    verified = [row for row in rows if row.tier == VERIFIED_TIER]
    chosen = next((row for name in SAMPLE_PREFERENCE for row in verified if row.identity == name), None)
    if chosen is None:
        chosen = min(verified, key=lambda row: (row.size_bytes, row.identity), default=None)
    if chosen is None:
        return None, None
    try:
        body = view.body_reader(view.catalogue.items[chosen.identity])
    except Exception:  # noqa: BLE001 - a body that cannot be read now is left out, never guessed
        return chosen, None
    return chosen, body if isinstance(body, str) else None


def release_changes(view) -> dict:
    """The served release's own record of what it added, changed and withdrew; empty for a view built in code."""
    value = getattr(view, "changes", None) or {}
    return {key: [row for row in value.get(key, []) if isinstance(row, dict) and row.get("identity")]
            for key in ("added", "changed", "withdrawn")}


def _kind(kind: str) -> str:
    return KIND_NAMES.get(kind, kind.replace("_", " ").capitalize())


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


def _counts_table(rows) -> str:
    kinds = sorted({row.kind for row in rows}, key=lambda kind: (_kind(kind), kind))
    counted = Counter((row.kind, row.tier) for row in rows)
    head = "".join(f'<th scope="col">{escape(TIER_LABELS[tier])}</th>' for tier in LIBRARY_TIERS)
    body = "".join(f'<tr><th scope="row">{escape(_kind(kind))}</th>'
                   + "".join(f"<td>{counted[(kind, tier)]}</td>" for tier in LIBRARY_TIERS) + "</tr>" for kind in kinds)
    totals = "".join(f"<td>{sum(1 for row in rows if row.tier == tier)}</td>" for tier in LIBRARY_TIERS)
    return ('<div class="md-table-wrap"><table class="md-table" data-library-counts><thead><tr><th scope="col">Kind</th>'
            f'{head}</tr></thead><tbody>{body}<tr><th scope="row">All kinds</th>{totals}</tr></tbody></table></div>')


def _verified_item(row: LibraryRow) -> str:
    """One row, in the layout of a directory row on every screen size. A directory row links to a page of its own; a
    library row does not, so its name is set in the text colour and never looks like a link."""
    return (f'<li class="md-row" data-library-item="{escape(row.identity)}" data-library-tier="{escape(row.tier)}">'
            f'<div class="md-row-head"><span class="md-name">{escape(row.purpose)}</span>'
            f'<span class="md-maker"><code>{escape(row.identity)}</code></span></div><dl class="md-facts">'
            f'<div><dt>Kind</dt><dd>{escape(_kind(row.kind))}</dd></div>'
            f'<div><dt>Licence</dt><dd>{escape(row.licence or "Not stated")}</dd></div>'
            f'<div><dt>Size</dt><dd>{row.size_bytes:,} bytes</dd></div>'
            f'<div><dt>Digest</dt><dd><code>{escape(row.digest[:12])}</code></dd></div></dl>'
            f'<p class="md-tags">{escape(TIER_LABELS[row.tier])} · {_review_link(row)}</p></li>')


def _release_band(view, rows) -> str:
    changes = release_changes(view)
    summary = view.summary() if hasattr(view, "summary") else {}
    release = str(summary.get("release_id") or "")
    built = summary.get("built_at")
    served_since = (datetime.fromtimestamp(built, tz=timezone.utc).strftime("%B %d, %Y at %H:%M UTC").replace(" 0", " ")
                    if isinstance(built, (int, float)) and built > 0 else "")
    lines = []
    if release:
        lines.append(f'<p class="md-reading">This page shows catalogue release <code>{escape(release[:12])}</code>'
                     + (f", served since {escape(served_since)}" if served_since else "") + ". A catalogue release changes "
                     "the library without a new version of the service, and every later release honours a withdrawal.</p>")
    else:
        lines.append('<p class="md-reading">A catalogue release changes the library without a new version of the service, '
                     "and every later release honours a withdrawal.</p>")
    if any(changes.values()):
        lines.append(f'<p class="md-reading">This release added {_items(len(changes["added"]))} and changed '
                     f'{_items(len(changes["changed"]))}.</p>')
    if changes["withdrawn"]:
        withdrawn = "".join(f'<li data-library-withdrawn="{escape(row["identity"])}"><code>{escape(row["identity"])}</code>'
                            + (f": {escape(str(row.get('note') or ''))}" if row.get("note") else "") + "</li>"
                            for row in changes["withdrawn"])
        lines.append(f'<h3>Withdrawn in this release</h3><ul class="md-plain">{withdrawn}</ul>')
    else:
        lines.append('<p class="md-reading">This release withdrew no item.</p>')
    return ('<div class="md-band" id="releases" aria-labelledby="releases-title"><h2 id="releases-title">Releases and '
            "withdrawals</h2>" + "".join(lines) + "</div>")


def library_body(view, rows=None) -> str:
    """The page's own markup inside the site frame, written from one view."""
    rows = library_rows(view) if rows is None else rows
    verified = [row for row in rows if row.tier == VERIFIED_TIER]
    community = [row for row in rows if row.tier == COMMUNITY_TIER]
    chosen, body = sample(view, rows)
    meanings = "".join(f"<div><dt>{escape(TIER_LABELS[tier])}</dt><dd>{escape(TIER_MEANINGS[tier])}</dd></div>"
                       for tier in LIBRARY_TIERS)
    intro = ('<div class="md-band md-intro"><h1 id="library-title">The library</h1>'
             f'<p class="lede">{len(rows)} items a coding agent can fetch today: {len(verified)} Verified and '
             f'{len(community)} Community. Each one names its licence, its size and the digest of its exact bytes. '
             "Read them here; search and downloads come with an account.</p>"
             '<div class="md-actions"><a class="button primary" href="/get-started">Get started</a>'
             '<a class="button secondary" href="/setup">Get set up</a></div></div>')
    labels = ('<div class="md-band" id="labels" aria-labelledby="labels-title"><h2 id="labels-title">What the labels mean'
              f'</h2><dl class="md-dl">{meanings}</dl></div>')
    counts = ('<div class="md-band" id="counts" aria-labelledby="counts-title"><h2 id="counts-title">What is in it</h2>'
              + _counts_table(rows) + "</div>")
    listed = ('<div class="md-band" id="verified" aria-labelledby="verified-title"><h2 id="verified-title">Verified items'
              '</h2>' + (f'<ol class="md-list" data-library-verified>{"".join(_verified_item(row) for row in verified)}</ol>'
                         if verified else "<p>No item carries the Verified label today.</p>") + "</div>")
    others = ('<div class="md-band" id="community" aria-labelledby="community-title"><h2 id="community-title">Community '
              f'items</h2><p class="md-reading">{len(community)} Community items, counted by kind in the table above. Each '
              "one is shown with "
              "its label wherever an account searches, and an account can leave Community items out.</p></div>")
    if chosen is not None and body is not None:
        shown = ('<div class="md-band" id="sample" aria-labelledby="sample-title"><h2 id="sample-title">One item in full'
                 f'</h2><p class="md-reading"><code>{escape(chosen.identity)}</code>, {escape(TIER_LABELS[chosen.tier])}, '
                 f'digest <code>{escape(chosen.digest[:12])}</code>. Every other body comes through an account and is '
                 'checked against its digest.</p>'
                 f'<pre class="md-code md-code-wrap" data-library-sample="{escape(chosen.identity)}">'
                 f"<code>{escape(body)}</code></pre></div>")
    else:
        shown = ""
    return intro + labels + counts + listed + others + shown + _release_band(view, rows)


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
