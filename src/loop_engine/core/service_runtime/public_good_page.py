"""Public Good policy and metadata browser; never reads or renders catalogue bodies.

The service supplies the independently authorized metadata projection. Public
browsing is not download authority; downloads stay in the authenticated app.
This is a renderer within the existing website boundary, not a new runtime.
"""
from __future__ import annotations

from html import escape
import re

ADDRESS = "/public-good"
VIEW = "public-good"
COLLECTION_PATH = "/api/v1/public-good"
# Short navigation descriptions, not claims of affiliation or UN-approved material.
# Official goal definitions: https://sdgs.un.org/goals (checked September 30, 2026).
GOALS = (
    (1, "No poverty"), (2, "Zero hunger"), (3, "Good health and well-being"),
    (4, "Quality education"), (5, "Gender equality"), (6, "Clean water and sanitation"),
    (7, "Affordable and clean energy"), (8, "Decent work and economic growth"),
    (9, "Industry, innovation and infrastructure"), (10, "Reduced inequalities"),
    (11, "Sustainable cities and communities"), (12, "Responsible consumption and production"),
    (13, "Climate action"), (14, "Life below water"), (15, "Life on land"),
    (16, "Peace, justice and strong institutions"), (17, "Partnerships for the goals"),
)


def collection(view, snapshot, *, query="", goal="", page=1, page_size=20):
    """A bounded public whitelist from exact eligible grants; no body/source locator is read."""
    from .records import ServiceRuntimeError
    from .catalogue_attributes import harness_kind_label, harness_kind_of
    if (not isinstance(query, str) or len(query) > 200 or any(ord(char) < 32 for char in query)
            or goal not in ("", "related", *(str(number) for number, _ in GOALS))
            or type(page) is not int or not 1 <= page <= 10000
            or type(page_size) is not int or not 1 <= page_size <= 50):
        raise ServiceRuntimeError("invalid_public_good_query")
    rows, all_files, useful_files, goal_counts = [], set(), set(), {number:0 for number, _ in GOALS}
    for grant in snapshot.grants:
        item = view.catalogue.items.get(grant.binding.identity)
        if item is None:
            continue
        package = view.packages.get(item.identity)
        entries = package.files if package is not None else ()
        all_files.update(entry.digest for entry in entries)
        useful_files.update(entry.digest for entry in entries if entry.path in grant.useful_paths)
        for number in grant.sdg_goals:
            goal_counts[number] += 1
        title = grant.display_name or re.sub(r"[_-]+", " ", item.identity).strip()
        shown = view.shown_attributes(item.identity) if callable(getattr(view, "shown_attributes", None)) else {}
        kind = harness_kind_of(item.kind, tuple(getattr(item, "styles", ()) or ()), (), str(shown.get("harness_kind") or ""))
        rows.append({"identity":item.identity, "title":title[:120], "summary":item.purpose[:400],
            "public_benefit":grant.public_benefit_reason[:600], "sdg_goals":list(grant.sdg_goals),
            "initiatives":list(grant.initiatives), "component_form":harness_kind_label(kind),
            "licence":item.license_name or "See package licence", "files":len(entries)})
    rows.sort(key=lambda row:(row["title"].casefold(),row["identity"]))
    words = query.casefold().split()
    matched = [row for row in rows if (not goal or goal == "related" and not row["sdg_goals"]
               or goal != "related" and int(goal) in row["sdg_goals"])
               and all(word in " ".join((row["title"],row["summary"],row["public_benefit"],*row["initiatives"])).casefold() for word in words)]
    start = (page-1)*page_size
    limits = snapshot.limits
    return {"record_type":"public_good_collection/v1", "authentication_required":True, "subscription_required":False,
        "policy_version":snapshot.version, "packages":len(rows), "distinct_files":len(all_files),
        "distinct_useful_files":len(useful_files), "useful_file_count_basis":"explicit_reviewed_paths_only",
        "matches":len(matched), "page":page, "has_next":start+page_size<len(matched), "items":matched[start:start+page_size],
        "goals":[{"id":number,"label":label,"packages":goal_counts[number]} for number,label in GOALS],
        "limits_description":f"Per account: up to {limits.requests_per_window} requests and {limits.bytes_per_window:,} reserved response bytes per {limits.window_seconds:,} seconds. Shared service limits also apply. Failed attempts can consume delivery allowance; paid usage is not increased."}


def body() -> str:
    options = ''.join(f'<option value="{number}">SDG {number} · {escape(label)}</option>' for number, label in GOALS)
    tiles = ''.join(
        f'<a class="pg-goal-tile" data-goal="{number}" href="/public-good?goal={number}#public-good-library">'
        f'<span class="pg-goal-number">SDG {number}</span><h3>{escape(label)}</h3>'
        f'<span class="pg-goal-count" data-goal-count="{number}">View components</span>'
        '<span class="pg-goal-arrow" aria-hidden="true">↗</span></a>' for number, label in GOALS)
    return (
        '<section class="pg-hero" aria-labelledby="public-good-title"><div class="pg-intro">'
        '<div><p class="pg-eyebrow">Baltor Public Good</p>'
        '<h1 id="public-good-title">Free harness components.<br>For work that helps people.</h1>'
        '<p class="lede">Practical tools, code, skills and reference material for sustainable development '
        'and public-benefit initiatives. Start with a goal, find useful components and bring them into your own AI tools.</p>'
        '<p class="pg-commitment">A free Baltor account gives you access to the selected files, '
        'with fair-use limits. Everyone can take part, including individuals, nonprofits and public-interest teams.</p>'
        '<div class="actions"><a class="button primary" href="#public-good-goals">Explore the goals</a>'
        '<a class="text-link" href="#public-good-policy">Our Public Good Policy</a></div></div>'
        '<aside class="pg-promise" aria-label="The free collection"><span class="pg-free">Free with an account</span>'
        '<p class="pg-counts" id="public-good-population">Explore the current collection</p>'
        '<p>Choose a goal below. Each published component includes its purpose, licence and exact files.</p>'
        '<a href="/get-started">Create your free account →</a></aside></div></section>'
        '<section class="pg-goals" id="public-good-goals" aria-labelledby="public-good-goals-title">'
        '<div class="pg-section-heading"><div><p class="pg-eyebrow">17 goals. Shared purpose.</p>'
        '<h2 id="public-good-goals-title">Choose the work you care about.</h2></div>'
        '<a class="text-link" data-goal="" href="/public-good#public-good-library">Browse all components →</a></div>'
        '<div class="pg-goal-grid">' + tiles + '</div>'
        '<a class="pg-initiative-tile" data-goal="related" href="/public-good?goal=related#public-good-library">'
        '<div><h3>Other public-benefit initiatives</h3><p>Explore accessibility, open research, '
        'public data, nonprofit operations and other work that serves the public.</p></div>'
        '<span>Explore initiatives →</span></a></section>'
        '<section id="public-good-library" class="pg-workspace" data-public-good-browser aria-labelledby="public-good-library-title">'
        '<div class="pg-section-heading"><h2 id="public-good-library-title">All Public Good components</h2>'
        '<a href="#public-good-goals">Choose another goal ↑</a></div>'
        '<details class="pg-advanced"><summary>More filters</summary>'
        '<div class="pg-options"><label for="public-good-view">Browse<select id="public-good-view">'
        '<option value="files">Files</option><option value="packages">Packages</option></select></label>'
        '<label for="public-good-media">File type<select id="public-good-media"><option value="">Every file type</option></select></label>'
        '<label for="public-good-initiative">Related initiative<select id="public-good-initiative"><option value="">Every initiative</option></select></label></div></details>'
        '<form id="public-good-filters" class="pg-filters" role="search">'
        '<label for="public-good-query">Find a component<input id="public-good-query" name="query" '
        'type="search" maxlength="200" placeholder="For example, water quality or accessible learning"></label>'
        '<label for="public-good-goal">Goal<select id="public-good-goal" name="goal">'
        '<option value="">All goals and initiatives</option>' + options +
        '<option value="related">Other public-benefit initiatives</option></select></label>'
        '<button class="button primary" type="submit">Search</button></form>'
        '<p id="public-good-status" role="status" aria-live="polite">Loading the current collection…</p>'
        '<ul id="public-good-items" class="pg-items" aria-label="Public Good files and packages"></ul>'
        '<div class="pg-pagination"><button class="button secondary" type="button" id="public-good-previous" disabled>Previous</button>'
        '<span id="public-good-page"></span><button class="button secondary" type="button" id="public-good-next" disabled>Next</button></div>'
        '<details class="pg-coverage"><summary>Coverage across the 17 goals</summary>'
        '<p>One file can support several goals, so counts overlap. Each count reflects the currently published collection. Related initiatives are counted separately.</p>'
        '<ul id="public-good-coverage"></ul></details>'
        '<noscript><p>The collection filters need JavaScript. You can read the policy below and '
        '<a href="/login">sign in</a> to use the library.</p></noscript></section>'
        '<section id="public-good-policy" class="pg-policy" aria-labelledby="public-good-policy-title">'
        '<h2 id="public-good-policy-title">The Public Good Policy</h2>'
        '<div class="pg-policy-grid"><div><h3>Free files, with an account</h3>'
        '<p>Everyone with an enabled Baltor account can download the listed component versions without a paid plan. '
        'You do not need to prove nonprofit status or disclose who you are helping. Anonymous browsing shows descriptions, not file bodies.</p>'
        '<p>Use your normal sign-in, an OAuth connection or a scoped harness key. Access to paid and private material remains separate.</p></div>'
        '<div><h3>A clear public benefit</h3><p>The collection supports the '
        '<a href="https://sdgs.un.org/goals" rel="noreferrer">17 Sustainable Development Goals</a> '
        'and related work such as worker protection, accessibility, education and responsible use of public data. '
        'Each listed version has a specific public-benefit reason. A topic tag alone does not make a file eligible.</p>'
        '<p>This is an independent Baltor initiative, organized around practical public-benefit work.</p></div>'
        '<div><h3>Licences and checks still apply</h3><p>Every file keeps its own licence and conditions. '
        'Free access does not mean public domain, permission to reuse unrelated media, or proof of effectiveness in the field. '
        'Check current sources before using time-sensitive guidance, especially law, health or safety information.</p>'
        '<p>Withdrawn or changed versions must pass the normal checks before they can be served again.</p></div>'
        '<div><h3>Bounded delivery</h3><p>Request and byte limits keep free delivery sustainable. '
        'A refused request tells your harness when it can retry. Free-file delivery is accounted for separately from paid usage.</p>'
        '<p id="public-good-limits">Current limits are shown with the collection when it loads.</p>'
        '<p>Model calls, rendering and other external services are not included. Bring your own model access and follow '
        'the <a href="/terms">terms</a> and <a href="/privacy">privacy notice</a>.</p></div></div>'
        '<div class="actions"><a class="button secondary" href="/get-started">Create a free account</a>'
        '<a class="button secondary" href="/app#browse-heading">Sign in and use the library</a>'
        '<a class="button secondary" href="/docs/searching-and-retrieving">Use these files in your harness</a></div></section>'
    )


def rendered(path: str, method: str, display_name: str, host: str | None = None):
    if path != ADDRESS or method not in ("GET", "HEAD"):
        return None
    from . import web_pages
    from .model_directory_pages import SCHEMA_CONTEXT, Page, breadcrumbs, canonical, frame
    site_map = web_pages.packaged_site_map()
    entry = site_map.page(ADDRESS)
    structured = {"@context": SCHEMA_CONTEXT, "@type": "CollectionPage", "name": entry.title,
                  "description": entry.description, "url": canonical(site_map, ADDRESS),
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Public Good", ADDRESS)))}
    page = frame(site_map, display_name, Page(ADDRESS, VIEW, entry.title, entry.description,
                                             body(), structured, "public-good-title"))
    page = page.replace('</head>', '<link rel="stylesheet" href="/assets/public-good.css">\n'
                        '<script defer src="/assets/public-good.js"></script>\n</head>')
    encoded = page.encode('utf-8')
    head = web_pages.page_head(site_map, path, host, display_name)
    if head is not None:
        encoded = web_pages.with_page_head(encoded, head)
    return web_pages.version_asset_references(encoded), web_pages.HTML_MEDIA_TYPE
