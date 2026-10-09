"""Public catalogue-state notices over the existing served view and release records.

This is a read-only website projection, not another catalogue, scheduler,
admission path or entitlement. It reveals aggregate facts already public on
the library page, never package bodies, individual item names, operator notes,
account data or private source locators. JSON Feed, RSS and Markdown are
representations of one notice, not three new components.

The notice identity binds the served release and catalogue-state revision.
Restarts keep that identity. A rollback or withdrawal changes the revision.
The timestamp comes from the state record, not the request clock. A pointer
ahead of the serving view is an unavailable/updating state, never a zero feed.
This initial feed contains only the current served state, not complete history.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import json
import re

from .catalogue_releases import load_release_header, read_pointer, read_state
from .catalogue_serving import STORE_SOURCE
from .library_page import release_change_counts
from .records import ServiceRuntimeError

PAGE = "/feeds"
FORMATS = {"/feeds/catalogue.json": "application/feed+json",
           "/feeds/catalogue.rss": "application/rss+xml",
           "/feeds/catalogue.md": "text/markdown"}
RECORD_TYPE = "catalogue_feed_snapshot/v1"
FEED_VERSION = "https://jsonfeed.org/version/1.1"
TITLE = "Baltor component updates"
DESCRIPTION = "The current served catalogue state. Public metadata only; complete history and personalized push are not included."
LIMITATION = ("Publication metadata does not prove upstream APIs were executed, every workflow was independently reviewed, "
              "or customer benefit was measured. This notice grants no package access and authorizes no installation or execution.")
MAXIMUM_FEED_BYTES = 32768
CACHE_CONTROL = "public, max-age=60"


def _require(condition, code="catalogue_feed_unavailable"):
    if not condition:
        raise ServiceRuntimeError(code)


def snapshot(runtime, view):
    """Capture one public aggregate notice, refusing a mismatched or changed serving state."""
    _require(view.source == STORE_SOURCE and bool(view.release_id))
    binding = runtime._catalog
    with binding.store() as store:
        state_row, state = read_state(binding, store)
        pointer_row, pointer = read_pointer(binding, store)
        _require(state is not None and pointer is not None)
        _require(pointer["release_id"] == view.release_id and state["revision"] == view.state_revision,
                 "catalogue_feed_updating")
        header = load_release_header(binding, store, view.release_id)
    summary = view.summary()
    _require(isinstance(summary, dict))
    population = summary.get("file_population")
    _require(isinstance(population, dict) and population.get("complete") is True)
    _require(header.content_digest == view.content_digest)
    counts = release_change_counts(view)
    values = [summary.get("items"), population.get("distinct_files"), state["revision"], state["updated_at"], *counts.values()]
    _require(all(type(value) is int and value >= 0 for value in values))
    try:
        changed_at = datetime.fromtimestamp(state["updated_at"], timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OSError, OverflowError):
        raise ServiceRuntimeError("catalogue_feed_unavailable") from None
    with binding.store() as store:
        latest_state, _state = read_state(binding, store)
        latest_pointer, _pointer = read_pointer(binding, store)
    _require(latest_state is not None and latest_pointer is not None
             and latest_state["record_version"] == state_row["record_version"]
             and latest_pointer["record_version"] == pointer_row["record_version"], "catalogue_feed_updating")
    return {"record_type": RECORD_TYPE, "notice_id": f"{view.release_id}:{state['revision']}",
            "release_id": view.release_id, "content_digest": view.content_digest,
            "catalogue_state_revision": state["revision"], "state_changed_at": changed_at,
            "packages": summary["items"], "distinct_files": population["distinct_files"],
            "release_changes": counts, "coverage": "current_served_state_only",
            "release_changes_basis": "original_release_publication_not_subsequent_state_transitions",
            "upstream_runtime_verification": "not_assessed_by_this_feed", "limitation": LIMITATION}


def _origin(value):
    # The canonical site-map origin is supplied by the host, never the request Host header.
    _require(isinstance(value, str) and bool(re.fullmatch(r"https://[a-z0-9.-]+(?::[0-9]{1,5})?", value)))
    return value


def summary_text(record):
    counts = record["release_changes"]
    return (f"{record['packages']:,} packages and {record['distinct_files']:,} distinct files are in the served catalogue. "
            f"The release's original publication added {counts['added']:,}, changed {counts['changed']:,} and withdrew {counts['withdrawn']:,} packages. "
            "Later state changes can also reflect rollback or withdrawal. "
            "These are catalogue counts, not counts of independent capabilities or proven outcomes.")


def json_feed(record, origin):
    """One JSON Feed 1.1 item with a namespaced structured extension and no executable content."""
    base = _origin(origin)
    return {"version": FEED_VERSION, "title": TITLE, "home_page_url": base + PAGE,
            "feed_url": base + "/feeds/catalogue.json", "description": DESCRIPTION, "language": "en",
            "authors": [{"name": "Baltor publication metadata"}],
            "items": [{"id": record["notice_id"], "url": base + "/library", "title": TITLE,
                       "date_published": record["state_changed_at"], "content_text": summary_text(record) + " " + LIMITATION,
                       "_baltor": record}]}


def rss(record, origin):
    """RSS 2.0 representation of the same single current-state notice."""
    base = _origin(origin)
    published = format_datetime(datetime.fromisoformat(record["state_changed_at"].replace("Z", "+00:00")), usegmt=True)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{TITLE}</title>'
            f'<link>{escape(base + PAGE)}</link><description>{escape(DESCRIPTION)}</description>'
            f'<item><guid isPermaLink="false">{escape(record["notice_id"])}</guid><title>{TITLE}</title>'
            f'<link>{escape(base + "/library")}</link><pubDate>{published}</pubDate>'
            f'<description>{escape(summary_text(record) + " " + LIMITATION)}</description></item></channel></rss>\n')


def markdown(record, origin):
    base = _origin(origin)
    return (f"# {TITLE}\n\nState changed: {record['state_changed_at']}\n\n"
            f"Served release: `{record['release_id']}`\n\n"
            f"Catalogue state revision: {record['catalogue_state_revision']}\n\n"
            f"{summary_text(record)}\n\n{DESCRIPTION}\n\n{LIMITATION}\n\n"
            f"[Inspect the library]({base}/library). File downloads retain their normal account, permission and licence checks.\n")


def render(record, path, origin):
    """Bounded deterministic bytes for one supported representation."""
    _require(path in FORMATS, "catalogue_feed_format_unknown")
    if path.endswith(".json"):
        body = json.dumps(json_feed(record, origin), ensure_ascii=False, separators=(",", ":")) + "\n"
    elif path.endswith(".rss"):
        body = rss(record, origin)
    else:
        body = markdown(record, origin)
    encoded = body.encode("utf-8")
    _require(len(encoded) <= MAXIMUM_FEED_BYTES)
    return encoded, FORMATS[path]


def live_specimen_body():
    """Static shell for one anonymous catalogue read; failures never render a made-up zero."""
    return ('<section class="md-band" id="live-catalogue"><p class="eyebrow">Library updates feed · live</p>'
            '<h2>Read an actual feed item.</h2><p class="md-reading">This notice comes from the library Baltor serves now. '
            'It reports what the library holds, not current model news or benchmark results.</p>'
            '<article class="feed-specimen" id="catalogue-specimen" data-state="loading" aria-labelledby="catalogue-specimen-heading">'
            '<h3 id="catalogue-specimen-heading">Baltor component updates</h3>'
            '<p id="catalogue-specimen-status" role="status" aria-live="polite">Reading the library updates feed…</p>'
            '<div id="catalogue-specimen-content" hidden>'
            '<p id="catalogue-specimen-summary"></p><dl class="md-dl">'
            '<div><dt>Harness components</dt><dd id="catalogue-specimen-packages"></dd></div>'
            '<div><dt>Distinct files</dt><dd id="catalogue-specimen-files"></dd></div>'
            '<div><dt>Library changed</dt><dd id="catalogue-specimen-changed"></dd></div>'
            '<div><dt>This browser read it at</dt><dd id="catalogue-specimen-read"></dd></div>'
            '<div><dt>Exact notice identity</dt><dd id="catalogue-specimen-notice"></dd></div></dl>'
            '<p id="catalogue-specimen-limit" class="md-reading"></p>'
            '<div class="md-actions"><a class="button secondary" id="catalogue-snapshot-json">Download this item as JSON</a>'
            '<a class="button secondary" id="catalogue-snapshot-markdown">Download this item as Markdown</a></div>'
            '<p class="md-reading">Both downloads use the same notice displayed here, even if the library changes afterwards.</p>'
            '</div><button class="button secondary" type="button" id="catalogue-specimen-refresh" disabled>Read the latest notice</button>'
            '<noscript><p>JavaScript is needed for the inline notice. The public feed links below work without it.</p></noscript>'
            '</article><p class="md-reading">For an agent that polls for changes, use these stable feed addresses:</p>'
            '<div class="md-actions"><a class="button secondary" href="/feeds/catalogue.json">JSON Feed</a>'
            '<a class="button secondary" href="/feeds/catalogue.rss">RSS</a>'
            '<a class="button secondary" href="/feeds/catalogue.md">Markdown</a></div>'
            '<p class="md-reading">This is one current-state notice in three formats, not a complete change history. '
            'A failed refresh does not mean the library is empty. Markdown here is plain text for agents, not a claim of '
            'Open Knowledge Format compatibility.</p></section>')


def decision_specimen_body():
    """A labeled research example with source statements kept apart from unmeasured performance."""
    from .feed_source_collections import directory
    collections = {item.id: item for item in directory().collections}
    chosen = ("founder-stack", "model-cost", "retrieval-benchmarks", "developer-releases")
    _require(all(identity in collections for identity in chosen), "feed_specimen_source_missing")
    links = "".join(f'<li><a href="#collection-{identity}">{escape(collections[identity].title)}</a>: '
                    f'{escape(collections[identity].purpose)}</li>' for identity in chosen)
    return ('<section class="md-band md-quiet" id="decision-specimen"><p class="eyebrow">Research-decision specimen · curated example</p>'
            '<h2>Where should a research-feed product run?</h2>'
            '<p class="md-reading">This example shows how an agent could use four of the source collections below. '
            'It is a decision brief, not an automated investigation or a measured Baltor cost comparison.</p>'
            '<article class="feed-specimen"><h3>The decision</h3>'
            '<p>Choose where to serve public feeds, store artifacts and run a custom search index.</p>'
            '<p><strong>Example assumptions:</strong> Public reads are frequent; source collection is periodic; '
            'the search index uses a custom Python process and persistent local files. These are scenario inputs, not measured traffic.</p>'
            '<div class="md-table-wrap"><table class="md-table feed-evidence-table"><caption>Source statements and missing measurements</caption>'
            '<thead><tr><th scope="col">Evidence</th><th scope="col">What the source says</th><th scope="col">What is not measured here</th></tr></thead><tbody>'
            '<tr><th scope="row">Publisher documentation</th><td><span class="feed-evidence-label">Source statement</span>'
            '<a href="https://developers.cloudflare.com/workers/platform/limits/" '
            'rel="noreferrer">Workers limits</a> define the runtime and resource constraints a collection job must fit.</td>'
            '<td><span class="feed-evidence-label">Not measured here</span>Whether this job fits those limits; '
            'its failure rate and end-to-end latency.</td></tr>'
            '<tr><th scope="row">Publisher documentation</th><td><span class="feed-evidence-label">Source statement</span>'
            '<a href="https://developers.cloudflare.com/r2/pricing/" '
            'rel="noreferrer">R2 pricing</a> separates storage and operation charges from egress.</td>'
            '<td><span class="feed-evidence-label">Not measured here</span>Actual requests, storage mix and monthly bill. '
            'No savings percentage is established.</td></tr>'
            '<tr><th scope="row">Publisher documentation</th><td><span class="feed-evidence-label">Source statement</span>'
            '<a href="https://docs.fly.io/machines/overview/" '
            'rel="noreferrer">Fly Machines</a> provide virtual machines for application processes.</td>'
            '<td><span class="feed-evidence-label">Not measured here</span>Search recall, index rebuild time, '
            'operating effort and cost for the same workload.</td></tr></tbody></table></div>'
            '<p><strong>Provisional choice:</strong> Test Cloudflare for anonymous feed delivery and artifact storage. '
            'Keep the custom search process on its existing host until an alternative passes the same workload and recovery checks. '
            'This is an inference from the scenario and documentation, not a deployment instruction.</p>'
            '<h3>Evidence that could change the choice</h3><ul class="md-plain">'
            '<li>A fixed workload with actual request counts, storage operations, observed latency and a complete cost estimate.</li>'
            '<li>The same search queries and relevance judgments on each engine, including failures and index rebuild time.</li>'
            '<li>A restore and rollback test, with identity and access checks unchanged.</li></ul>'
            '<p><strong>Review trigger:</strong> Revisit when traffic, provider pricing, runtime limits or the required search behavior changes. '
            'An agent must collect new evidence before changing the decision; this page does not schedule that work.</p>'
            '<p class="md-reading">Documentation checked 2026-10-08 (UTC). Workload measurements: not collected for this specimen.</p>'
            '<h3>Collections that support this decision</h3><ul class="md-plain">' + links + '</ul>'
            '<p class="md-reading">Agent Feeds supports the choice and its reasons. Harness Files supplies the parsers, '
            'comparison scripts, deployment files and checks used to carry it out.</p></article></section>')


def setup_section():
    """How a person gives each agent only the feeds it needs. The examples and the excerpt come from the packaged directory."""
    from . import web_pages
    from .feed_source_collections import COLLECTION_PREFIX, directory, render as render_collection
    from .model_directory_pages import canonical
    data = directory()
    by_id = {item.id: item for item in data.collections}
    sources = {item.id: item for item in data.sources}
    _require(all(identity in by_id for identity in ("coding-benchmarks", "coding-agent-releases", "research-papers",
                                                     "retrieval-benchmarks", "creative-engines")), "feed_specimen_source_missing")
    site = web_pages.packaged_site_map()
    example = by_id["coding-benchmarks"]
    link = canonical(site, COLLECTION_PREFIX + example.id + ".md")
    origin = canonical(site, "")

    def named(*identities):
        return " and ".join(f'<a href="#collection-{identity}">{escape(by_id[identity].title)}</a>' for identity in identities)
    # The excerpt is the collection's own section of the served Markdown, cut from the bytes the feed address answers.
    served = render_collection(COLLECTION_PREFIX + example.id + ".md", origin)[0].decode("utf-8")
    excerpt = served[served.index("## " + example.title):served.index("\n\n[Browse Baltor Feeds]")].strip()
    return ('<section class="md-band" id="feed-setup" aria-labelledby="feed-setup-title"><p class="eyebrow">Set up</p>'
            '<h2 id="feed-setup-title">Give each agent only the feeds it needs</h2>'
            '<p class="md-reading">Public feeds need no account and no key. Five steps, and your agent reads sources it can check '
            'before it decides.</p><ol class="feed-steps">'
            f'<li><strong>Choose what each agent decides.</strong> Pick one to three collections for each agent\'s job. Give a coding '
            f'agent {named("coding-benchmarks", "coding-agent-releases")}; give a research agent '
            f'{named("research-papers", "retrieval-benchmarks")}; give a creative agent {named("creative-engines")}.</li>'
            '<li><strong>Copy the link in the format it reads.</strong> Markdown suits instruction files and chat agents. '
            'JSON Feed suits scripts and tools, with the decision question and comparison fields in its <code>_baltor</code> '
            'extension. The library updates feed is also served as RSS for a feed reader.</li>'
            '<li><strong>Add the link to the agent\'s instructions.</strong> For example, one line in <code>AGENTS.md</code> or '
            f'<code>CLAUDE.md</code>:<pre class="md-code md-code-wrap" tabindex="0">Before choosing a coding model, read {escape(link)} '
            'and follow its decision checklist.</pre></li>'
            '<li><strong>Decide how often it reads.</strong> Your harness owns scheduling and source access. Baltor does not push. Collections '
            'change with Baltor releases and the library updates feed changes with the library, so once a day or before each '
            'decision is enough. Send the last <code>ETag</code> in <code>If-None-Match</code> and an unchanged feed answers '
            '304 Not Modified.</li>'
            '<li><strong>Check which version it read.</strong> Each file names the date its sources were checked and a digest of '
            'the directory, so you can tell exactly what an agent used.</li></ol>'
            f'<details class="feed-excerpt"><summary>What a collection looks like</summary><p class="md-reading">The '
            f'collection\'s section of <a href="{COLLECTION_PREFIX}{example.id}.md">{COLLECTION_PREFIX}{example.id}.md</a>, '
            f'as served:</p><pre class="md-code md-code-wrap" tabindex="0">{escape(excerpt)}</pre></details>'
            '<p class="md-reading">Saved feed settings for each agent, each with a token of its own, are not available yet. '
            'Today the links you give an agent are its settings.</p>'
            '<h3>Questions</h3><div class="feed-questions">'
            '<details><summary>Is it free?</summary><p>Yes, through December 31, 2026 (Eastern). The standard price is $4.99 a '
            'month, and nothing is charged automatically.</p></details>'
            '<details><summary>Do I need an account?</summary><p>No. Public feeds are open to anyone and need no key.</p></details>'
            '<details><summary>How fresh is it?</summary><p>Sources are checked on the date each file shows. Updates follow '
            'website releases; no daily refresh is promised.</p></details>'
            '<details><summary>Does a feed run anything?</summary><p>No. A feed never installs or runs its contents, and '
            'reading a source does not grant permission to copy it.</p></details></div></section>')


def page_body():
    from .feed_source_collections import page_section
    return ('<section class="md-band md-intro"><p class="eyebrow">Agent Feeds</p>'
            '<h1 id="feeds-title">Sources your agents can check.</h1>'
            '<p class="md-reading feed-offer-price"><strong>$4.99 a month.</strong> Free through December 31, 2026 (Eastern). '
            'No automatic charge; a paid subscription requires your explicit opt-in.</p>'
            '<p class="md-reading">Pick the decision in front of your agent, such as choosing a coding model, and give it one link. '
            'Your agent reads the sources, what to compare and when to look again. Agent Feeds helps your agents decide; '
            'Harness Files helps them build, and Overnight / AFK Work keeps a local queue moving while you are away.</p>'
            '<div class="md-actions"><a class="button primary" href="#source-collections">Choose a collection</a>'
            '<a class="button secondary" href="#feed-setup">Set up feeds for each agent</a>'
            '<a class="button secondary" href="/pricing">Compare the three offerings</a></div></section>'
            + page_section() + setup_section() + live_specimen_body() + decision_specimen_body()
            + '<section class="md-band"><h2>Harness Files</h2><p class="md-reading">'
            'Agent Feeds supplies public source collections and the library updates feed. '
            'Agent Feeds + Harness Files also gives you the whole library: skills, tools, code, hooks and settings your harness '
            'downloads at an exact version. The full-library plan is $29 a month.</p>'
            '<p class="md-reading">A feed notice never installs or runs its contents. Downloaded files still require their normal '
            'authorization, source and licence checks. The Public Good collection is free with an account.</p><div class="md-actions">'
            '<a class="button secondary" href="/library">Explore Harness Files</a>'
            '<a class="button secondary" href="/public-good">Public Good</a></div></section>'
            '<section class="md-band"><h2>Overnight / AFK Work · Preview</h2>'
            '<p class="md-reading">Run local task queues with call limits, task checkpoints and morning reports. '
            'Your worker and model access stay under your control.</p>'
            '<p class="md-reading">No extra charge with Harness Files. The local tools are free and open source.</p>'
            '<div class="md-actions"><a class="button secondary" href="/overnight">Set up overnight work</a>'
            '<a class="button secondary" href="/pricing">Compare the three offerings</a></div></section>')


def rendered_page(path, method, display_name, host=None):
    if path != PAGE or method not in ("GET", "HEAD"):
        return None
    from . import web_pages
    from .model_directory_pages import SCHEMA_CONTEXT, Page, breadcrumbs, canonical, frame
    site = web_pages.packaged_site_map()
    entry = site.page(PAGE)
    structured = {"@context": SCHEMA_CONTEXT, "@type": "WebPage", "name": entry.title,
                  "description": entry.description, "url": canonical(site, PAGE),
                  "breadcrumb": breadcrumbs(site, (("Home", "/"), ("Feeds", PAGE)))}
    body = frame(site, display_name, Page(PAGE, "feeds", entry.title, entry.description,
                                        page_body(), structured, "feeds-title")).encode()
    body = body.replace(b'</head>', b'<script type="module" src="/assets/feed-specimen.js"></script>\n</head>', 1)
    head = web_pages.page_head(site, path, host, display_name)
    if head is not None:
        body = web_pages.with_page_head(body, head)
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE
