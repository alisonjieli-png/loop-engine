"""Independent AgentFeeds presentation over the existing feed and account edges.

The caller selects the trusted public origin. This pure renderer never chooses
an account, changes a policy, collects sources or configures a schedule.
"""
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from importlib.resources import files

from . import feed_profiles, feed_source_collections
from .brand_profiles import ServiceBrandProfile
from .http_auth import is_loopback_url
from .web_pages import read_packaged_asset

ORIGIN = "https://agentfeeds.si"
ASSET_PREFIX = "/assets/agentfeeds/"
ASSETS = {"site.css": "text/css", "site.js": "text/javascript", "account.js": "text/javascript", "mark.svg": "image/svg+xml"}
ROUTES = ("/", "/collections", "/saved", "/feeds", "/build", "/connect", "/feeds/setup", "/pricing", "/help", "/docs",
          "/login", "/signup", "/get-started", "/account", "/auth/confirm", "/auth/callback", "/oauth/consent", "/privacy", "/terms", "/status", "/support")
ACCOUNT_ROUTES = frozenset(("/login", "/signup", "/get-started", "/account", "/auth/confirm", "/auth/callback", "/oauth/consent"))
SITE_FILES = ("/robots.txt", "/sitemap.xml", "/llms.txt")


def routes():
    return (*ROUTES, *("/collections/" + item.id for item in feed_profiles.current_directory().collections))


def _asset(name):
    return files(__package__).joinpath("web_assets", "agentfeeds", name).read_bytes()


def _versioned(path, body):
    return path + "?v=" + sha256(body).hexdigest()


def _link(path, label, kind=""):
    current = ' aria-current="page"' if kind == 'active' else ''
    return f'<a class="{kind}" href="{escape(path, quote=True)}"{current}>{escape(label)}</a>'


def _intro(kicker, title, text):
    return f'<div class="page-intro"><p class="eyebrow">{escape(kicker)}</p><h1>{escape(title)}</h1><p class="lede">{escape(text)}</p></div>'


def _search_text(item, data):
    """Words a visitor may type: the card's own text plus its purpose, question and source names."""
    names = {source.id: source.name for source in data.sources}
    return " ".join((item.title, item.group, item.id.replace("-", " "), item.purpose, item.decision_question,
                     *(names[key] for key in item.source_ids if key in names))).lower()


def _card(item, number, data):
    return (f'<article class="collection" data-collection data-search="{escape(_search_text(item, data), quote=True)}">'
            f'<p class="collection-meta"><span>{number:02}</span>{escape(item.group)}</p>'
            f'<h2>{_link("/collections/" + item.id, item.title)}</h2><p>{escape(item.decision_question)}</p>'
            f'<div class="collection-foot"><span>{len(item.source_ids)} sources</span>{_link("/collections/" + item.id, "Open collection →")}</div>'
            f'<button type="button" class="button secondary save-collection" data-save-collection="{escape(item.id, quote=True)}" aria-pressed="false">Save collection</button></article>')


def _saved(data):
    return (_intro("On this browser", "Your saved collections", "Keep useful collections together, then build a reading profile for your agent.")
            + '<p class="quiet">Selections stay in this browser on this website. They are not synced to an account, and saving creates no hosted feed or schedule.</p>'
            '<div class="actions"><a id="saved-build" class="button primary" href="/build">Build a reading profile</a>'
            '<button id="saved-clear" type="button" class="button secondary">Clear saved collections</button></div>'
            '<p id="saved-empty">No collections saved here yet. <a href="/collections">Browse collections</a> to choose some.</p>'
            '<div id="saved-collections" class="collection-grid">'
            + "".join(_card(item, index + 1, data) for index, item in enumerate(data.collections))
            + '</div><noscript><p>Saved selections need JavaScript. The collection links above still work.</p></noscript>')


def _home(data):
    first = next(item for item in data.collections if item.id == "coding-benchmarks")
    source_by_id = {item.id: item for item in data.sources}
    sources = "".join(f'<li><span class="source-dot"></span>{escape(source_by_id[key].name)}<span>Source</span></li>' for key in first.source_ids)
    return ('<section class="hero"><div><p class="eyebrow"><span class="live-dot"></span> A reading plan for every agent</p>'
            '<h1>Good decisions<br>start <em>upstream.</em></h1><p class="hero-copy">Give your agents the sources, comparison questions and reading instructions they need before they choose.</p>'
            '<div class="actions">' + _link("/build", "Build a reading profile", "button primary") + _link("/collections", "Explore collections ↗", "text-link") + '</div>'
            '<p class="quiet">Public feeds. No account or model key needed.</p></div>'
            f'<aside class="specimen" aria-label="An actual source collection"><div class="specimen-bar"><span class="specimen-label">Inside a collection</span><span>01 / {len(data.collections)}</span></div>'
            f'<p class="eyebrow">{escape(first.group)}</p><h2>{escape(first.title)}</h2><p>{escape(first.decision_question)}</p>'
            '<ul class="specimen-sources">' + sources + '</ul><div class="specimen-question"><span>One thing to compare</span>'
            f'<strong>{escape(first.compare_fields[0].capitalize())}</strong></div><div class="specimen-bottom"><span>JSON Feed / RSS / Markdown</span>'
            + _link("/collections/" + first.id, "Read it ↗") + '</div></aside></section>'
            '<section class="facts-strip" aria-label="Available source directory">'
            f'<div><strong>{len(data.collections)}</strong><span>decision collections</span></div><div><strong>{len(data.sources)}</strong><span>registered sources</span></div>'
            f'<div><strong>{escape(data.source_docs_checked_on)}</strong><span>source documentation checked</span></div></section>'
            '<section class="section"><div class="section-heading"><div><p class="eyebrow">Start with a question</p><h2>What is your agent deciding?</h2></div>'
            + _link("/collections", "All collections →", "text-link") + '</div><div class="collection-grid">'
            + "".join(_card(item, index + 1, data) for index, item in enumerate(data.collections[:3])) + '</div></section>'
            '<section class="how section"><div><p class="eyebrow">From source to decision</p><h2>Your agent reads.<br>You keep control.</h2>'
            '<p>These are curated source references and research questions. Your agent checks the original sources and makes a comparison for your task.</p></div>'
            '<ol><li><span>01</span><div><h3>Choose its reading list</h3><p>Start with a collection. Add individual sources and leave out what does not apply.</p></div></li>'
            '<li><span>02</span><div><h3>Take the files with you</h3><p>Download the profile and its reading guide into your agent’s project.</p></div></li>'
            '<li><span>03</span><div><h3>Read before the next decision</h3><p>Use your own harness to read the sources. Its permissions and schedule stay yours.</p></div></li></ol></section>'
            '<section class="closing"><p class="eyebrow">A useful starting point</p><h2>Build your first reading profile.</h2>'
            + _link("/build", "Choose your sources →", "button primary") + '</section>')


def _collections(data):
    return (_intro("Source collections", "Begin with the decision.", "Find the questions and sources that fit your agent’s next task.")
            + '<div class="catalogue-tools"><label for="collection-search">Find a collection</label><input id="collection-search" type="search" placeholder="Try coding, finance or 3D" autocomplete="off">'
            f'<p class="quiet">{len(data.collections)} collections · {len(data.sources)} sources · Documentation checked {escape(data.source_docs_checked_on)}</p></div>'
            '<p class="quiet">Get the complete source directory: ' + _link('/feeds/sources.json', 'JSON Feed') + ', '
            + _link('/feeds/sources.rss', 'RSS') + ' or ' + _link('/feeds/sources.md', 'Markdown') + '.</p>'
            '<p id="collection-count" role="status" aria-live="polite"></p><div class="collection-grid">'
            + "".join(_card(item, index + 1, data) for index, item in enumerate(data.collections))
            + '</div><p id="collection-empty" hidden>No matching collections. Try a broader word or clear the search.</p>')


def _detail(item, data, origin):
    source_by_id = {source.id: source for source in data.sources}
    rows = "".join(f'<li><h3>{_link(source_by_id[key].url, source_by_id[key].name + " ↗")}</h3><p>{escape(source_by_id[key].description)}</p>'
                   f'<p class="quiet">{escape(source_by_id[key].access)} {escape(source_by_id[key].reuse)}</p></li>' for key in item.source_ids)
    path = feed_source_collections.COLLECTION_PREFIX + item.id
    return (_intro(item.group, item.title, item.decision_question)
            + '<div class="detail-layout"><article><section class="reading-block"><h2>What to compare</h2><ul class="check-list">'
            + "".join('<li>' + escape(field) + '</li>' for field in item.compare_fields) + '</ul></section>'
            '<section class="reading-block"><h2>Read the sources</h2><ul class="source-list">' + rows + '</ul></section>'
            '<section class="reading-block"><h2>When to look again</h2><p>' + escape(item.review_trigger) + '</p><h3>Give your agent this question</h3><p>'
            + escape(item.agent_task) + '</p></section></article><aside class="takeaway"><p class="eyebrow">Use this collection</p><h2>One link. Your agent.</h2>'
            '<p>Copy a feed link into your agent’s instructions.</p>' + _copy(origin + path + '.md', "Markdown feed")
            + _copy(origin + path + '.json', "JSON Feed") + _copy(origin + path + '.rss', "RSS feed")
            + '<div class="actions">' + _link(path + '.md', 'Read Markdown') + _link(path + '.json', 'Read JSON')
            + _link(path + '.rss', 'Read RSS') + '</div><hr><p>Need a different mix?</p>' + _link('/build?collection=' + item.id, 'Customize a profile →', 'button primary')
            + f'<p class="quiet">Source documentation checked {escape(data.source_docs_checked_on)}. This date does not mean every upstream item was refreshed.</p></aside></div>')


def _copy(value, label):
    return f'<div class="copy-field"><label>{escape(label)}<input readonly value="{escape(value, quote=True)}"></label><button type="button" data-copy aria-label="Copy {escape(label, quote=True)}">Copy</button></div>'


def _choices(items, name, title_key, note=None):
    return ''.join(f'<label class="choice"><input type="checkbox" name="{name}" value="{escape(item.id, quote=True)}"><span><strong>{escape(getattr(item, title_key))}</strong>'
                   + (f'<small>{escape(getattr(item, note))}</small>' if note else '') + '</span></label>' for item in items)


def _build(data):
    return (_intro("Build a reading profile", "A reading list with a job to do.", "Choose what this agent should read. Download its settings and guide when you are ready.")
            + f'<form id="feed-profile-form" data-directory-digest="{data.digest}" class="builder"><div class="builder-main">'
            '<section class="form-step"><p class="step-number">01 / Your agent</p><label>Agent label<input name="agent_label" required maxlength="64" pattern="[A-Za-z0-9][A-Za-z0-9 _.\\-]{0,63}" placeholder="Coding reviewer" autocomplete="off"></label>'
            '<p class="quiet">A short name for these files. Do not enter credentials or private project details.</p></section>'
            '<p class="builder-jump"><a href="#profile-output">Review and download ↓</a></p>'
            '<fieldset class="form-step"><legend><span class="step-number">02 / Collections</span> What will it decide?</legend>'
            '<label class="choice-filter">Find a collection<input type="search" data-choice-search placeholder="Search decisions"></label><p class="quiet">Filtering does not change your selections.</p>'
            + _choices(data.collections, "collection_ids", "title", "decision_question") + '</fieldset>'
            '<details class="form-step"><summary>Fine-tune individual sources</summary><p>Add a source, or exclude it from your selected collections. A source cannot be both added and excluded.</p>'
            '<div class="source-columns"><fieldset><legend>Add sources</legend><label class="choice-filter">Find a source<input type="search" data-choice-search></label>' + _choices(data.sources, "source_ids", "name")
            + '</fieldset><fieldset><legend>Leave sources out</legend><label class="choice-filter">Find a source to exclude<input type="search" data-choice-search></label>' + _choices(data.sources, "excluded_source_ids", "name") + '</fieldset></div></details></div>'
            '<aside class="builder-summary" id="profile-output"><p class="eyebrow">Your reading profile</p><h2>Ready for your harness.</h2>'
            '<label>Report format<select name="report_format"><option value="markdown">Markdown</option><option value="json">JSON</option></select></label>'
            '<label>Requested reading interval<select name="requested_poll_interval_minutes"><option value="1440">Every day</option><option value="60">Every hour</option><option value="360">Every 6 hours</option><option value="10080">Every week</option></select></label>'
            '<p class="quiet">This is a preference for your harness. Downloading a profile does not start a schedule.</p><button class="button primary" type="submit">Build reading profile</button>'
            '<button class="reset" type="reset">Start another agent</button><p id="feed-profile-status" role="status" aria-live="polite">Choose at least one collection or individual source.</p>'
            '<div id="feed-profile-downloads" class="download-list" hidden></div><div class="file-note"><strong>Two files, owned by you</strong><code>profile.json</code><code>READING.md</code>'
            '<p>Settings stay in the files you save. No hosted feed or schedule is created.</p></div></aside></form>'
            '<noscript><p>The profile builder needs JavaScript. You can still read and save the files on <a href="/collections">each collection page</a>.</p></noscript>')


def _connect(data, origin):
    item = data.collections[0]
    url = origin + feed_source_collections.COLLECTION_PREFIX + item.id + '.md'
    return (_intro("Connect an agent", "Bring a feed to the tools you use.", "Public source collections work with any harness that can read an HTTPS URL. No service key is needed.")
            + '<div class="guide-layout"><ol class="guide-steps"><li><h2>Pick the decision</h2><p>Open a collection, or build a custom reading profile. Check the sources and the question before assigning it.</p>'
            + _link('/collections', 'Browse collections →') + '</li><li><h2>Add the reading instruction</h2><p>Put this in the agent’s task or its own project instructions. Replace the example with your chosen collection.</p>'
            + _copy('Read ' + url + ' before choosing. Check the original sources, compare like-for-like evidence, and state what you could not verify.', 'Agent instruction')
            + '</li><li><h2>Check an actual read</h2><p>Ask the agent to name the directory date, source IDs and the decision question. A copied link alone is not a successful read.</p>'
            '<pre><code>curl --fail --show-error ' + escape(url) + '</code></pre></li><li><h2>Choose when it reads</h2><p>Use your harness’s own task scheduler, or ask it to read before each decision. AgentFeeds does not activate a hosted schedule.</p>'
            '<p>Keep the response <code>ETag</code>. Send it as <code>If-None-Match</code> next time; an unchanged collection answers <code>304 Not Modified</code>.</p>'
            '<p>If your reader uses RSS, copy the RSS link from the collection. JSON Feed and Markdown carry the same sources and research questions.</p></li></ol>'
            '<aside class="takeaway"><p class="eyebrow">Working with profile files</p><h2>Keep each agent’s files together.</h2><p>Save <code>profile.json</code> and <code>READING.md</code> in that agent’s project. Follow the reading guide before configuring its cadence.</p>'
            '<p>Use your existing harness and model access. A source link does not grant permission to copy material or run code.</p>' + _link('/build', 'Build a profile →', 'button primary') + '</aside></div>')


def _pricing():
    return (_intro("Pricing", "Start reading. Keep the choice yours.", "Public source collections and reading-profile downloads are free through December 31, 2026, Eastern time.")
            + '<section class="price-panel"><div><p class="eyebrow">AgentFeeds</p><p class="price">$9<span> a month</span></p><p class="free-label">Free through 2026</p>'
            '<p>No automatic charge. A paid subscription requires your explicit opt-in.</p></div><div><h2>For the agents you already run</h2><ul class="check-list">'
            '<li>Curated source collections and research questions</li><li>JSON Feed, RSS and Markdown links</li><li>Custom reading profiles for individual agents</li><li>Exact files and source-documentation dates</li></ul>'
            + _link('/build', 'Build a profile for free →', 'button primary') + '<p class="quiet">Your harness, model access and any upstream provider costs remain yours. This page does not start a subscription.</p></div></section>')


def _help():
    answers = (("Are these live research results?", "The current collections contain source references and research questions. The date records a source-documentation review, not a refresh of every upstream article or score."),
               ("Where are my reading profiles saved?", "In the files you download. The builder does not save account settings or configure hosted schedules. Keep a separate pair of files for each agent."),
               ("A source changed while I was building.", "Reload the collection directory, review your choices and build again. An old selection is not silently expanded to include new sources."),
               ("The download did not finish.", "Your selections stay on the page after a failed request. Build again when the service is available. Do not use a file whose integrity check failed."),
               ("Can I use sources that need a key?", "A collection can describe such a source. Access comes from your own provider account and permissions; never put provider keys into an agent label or feed URL."))
    return (_intro("Help", "A clear next step.", "Understand the files, freshness and account controls before you depend on them.")
            + '<div class="help-grid"><article>' + ''.join('<details class="faq"><summary>' + escape(q) + '</summary><p>' + escape(a) + '</p></details>' for q, a in answers)
            + '</article><aside class="takeaway"><h2>Get connected</h2><p>Our setup guide walks through an actual feed read and the files your harness needs.</p>'
            + _link('/connect', 'Read the setup guide →') + '<hr><h2>Account help</h2><p>Use the recovery form on the sign-in page to request a new password link.</p>'
            + _link('/login', 'Sign in or recover access →') + '<p class="quiet">Operated by Baltor.AI. Postal contact: 1428 Bryn Mawr St, Saxton, PA 16678, United States.</p></aside></div>')


class _LegalSection(HTMLParser):
    """Preserve the approved served article bytes rather than reauthoring legal text."""
    def __init__(self, view):
        super().__init__(convert_charrefs=False)
        self.view, self.depth, self.parts = view, 0, []

    def handle_starttag(self, tag, attrs):
        if not self.depth and tag == "section" and dict(attrs).get("data-view") == self.view:
            self.depth = 1
            return
        if self.depth:
            if tag == "section":
                self.depth += 1
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.depth:
            if tag == "section":
                self.depth -= 1
            if self.depth:
                self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)

    def handle_entityref(self, name):
        self.handle_data('&' + name + ';')

    def handle_charref(self, name):
        self.handle_data('&#' + name + ';')


def _legal(view):
    parser = _LegalSection(view)
    parser.feed(read_packaged_asset("index.html").decode())
    if not parser.parts or parser.depth:
        raise ValueError("approved legal section unavailable")
    return '<div class="legal reading-block">' + ''.join(parser.parts) + '</div>'


def _account(path):
    if path == '/oauth/consent':
        return (_intro('Connect your app', 'Review this connection.', 'Only allow an app you intended to connect.')
                + '<section id="oauth-consent-panel" class="account-panel"><p id="oauth-consent-status" role="status" aria-live="polite">Checking your sign-in…</p>'
                '<button id="oauth-sign-in" class="button primary" hidden>Sign in to review</button><div id="oauth-consent-details" hidden><h2 id="oauth-client-name"></h2>'
                '<p>Return destination</p><p id="oauth-client-destination"></p><h3>Requested access</h3><ul id="oauth-consent-scopes"></ul>'
                '<div class="actions"><button id="oauth-approve" class="button primary" disabled>Allow access</button><button id="oauth-deny" class="button secondary" disabled>Deny access</button></div></div>'
                '<p data-account-status role="status" aria-live="polite"></p></section>')
    if path in ("/signup", "/get-started"):
        content = '<form data-account-form="signup"><label>Email address<input name="email" type="email" required autocomplete="email" maxlength="254"></label><p class="quiet">By creating an account you agree to the <a href="/terms">terms</a> and <a href="/privacy">privacy notice</a>. This does not start a subscription.</p><button class="button primary" disabled>Send confirmation link</button></form>'
        title, text = 'An account, when you need one.', 'Enter your email first. Choose your password on the page your confirmation link opens.'
    elif path == '/auth/confirm':
        content = '<form data-account-form="confirm"><label>New password<input name="password" type="password" required autocomplete="new-password"></label><label>Repeat password<input name="again" type="password" required autocomplete="new-password"></label><p data-password-rule class="quiet"></p><button class="button primary" disabled>Set password and continue</button></form>'
        title, text = 'Choose your password.', 'Your link is used only when you submit this form.'
    elif path == '/account':
        content = '<div data-account-details hidden><dl data-account-facts></dl><button type="button" data-signout class="button secondary">Sign out</button></div><p data-account-login>Sign in to view your account. Public source feeds and reading-profile downloads do not require an account.</p>' + _link('/login', 'Sign in →', 'text-link')
        title, text = 'Your AgentFeeds account.', 'Access is checked by the shared account service. Reading profiles remain in the files you save.'
    else:
        content = '<form data-account-form="login"><label>Email address<input name="email" type="email" required autocomplete="email" maxlength="254"></label><label>Password<input name="password" type="password" required autocomplete="current-password"></label><button class="button primary" disabled>Sign in</button></form><p>New here? <a href="/get-started">Create an account</a>.</p><details class="recovery"><summary>Forgot your password?</summary><form data-account-form="recovery"><label>Email address<input name="email" type="email" required autocomplete="email" maxlength="254"></label><button class="button secondary" disabled>Send recovery link</button></form></details>'
        title, text = 'Welcome back.', 'Sign in with your email and password. Your model keys are separate.'
    return '<div class="account-layout">' + _intro('Your account', title, text) + '<section class="account-panel">' + content + '<p data-account-status role="status" aria-live="polite">Checking account availability…</p><p class="quiet">Public feeds work without signing in. <a href="/collections">Browse collections</a>.</p></section></div>'


def error_page(status, *, message='', next_action='', reference=''):
    """An escaped standalone error on AgentFeeds assets, with no request address or foreign asset."""
    title = 'Page not found' if status == 404 else 'This request could not be completed'
    css = _versioned(ASSET_PREFIX + 'site.css', _asset('site.css'))
    mark = _versioned(ASSET_PREFIX + 'mark.svg', _asset('mark.svg'))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title} | AgentFeeds</title><meta name="robots" content="noindex"><link rel="icon" href="{mark}"><link rel="stylesheet" href="{css}"></head>'
            '<body><header class="site-header"><a class="brand" href="/" aria-label="AgentFeeds home">'
            f'<img src="{mark}" width="32" height="32" alt=""><span>Agent<span class="brand-light">Feeds</span></span></a></header>'
            '<main id="main">' + _intro(str(status), title, message or 'Browse the source collections or return to the home page.')
            + ('<p>' + escape(next_action) + '</p>' if next_action else '')
            + ('<p>Reference: <code>' + escape(reference) + '</code></p>' if reference else '')
            + '<div class="actions">' + _link('/collections', 'Browse collections', 'button primary') + _link('/status', 'Service status', 'text-link')
            + '</div></main></body></html>').encode()


def render(path, *, origin=ORIGIN, directory=None, allow_loopback=False):
    """Render an exact known route; the HTTP owner controls method and host admission."""
    profile = ServiceBrandProfile(brand='agentfeeds', public_base_url=origin)
    if not (allow_loopback and is_loopback_url(origin)) and (not origin.startswith('https://') or ':' in profile.host):
        raise ValueError('AgentFeeds requires an exact HTTPS public origin')
    if path.startswith(ASSET_PREFIX):
        name = path[len(ASSET_PREFIX):]
        return (_asset(name), ASSETS[name]) if name in ASSETS else None
    data = directory if directory is not None else feed_profiles.current_directory()
    if path == '/robots.txt':
        return ('User-agent: *\nDisallow: /api/\nDisallow: /auth/\nDisallow: /account\nDisallow: /oauth/\nSitemap: ' + origin + '/sitemap.xml\n').encode(), 'text/plain'
    if path == '/sitemap.xml':
        addresses = ('/', '/collections', '/build', '/connect', '/pricing', '/help', '/privacy', '/terms', *('/collections/' + item.id for item in data.collections))
        return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + ''.join('<url><loc>' + escape(origin + address) + '</loc></url>' for address in addresses) + '</urlset>').encode(), 'application/xml'
    if path == '/llms.txt':
        return (f'# AgentFeeds\n\nCurated source collections and customer-owned reading profiles.\n\n'
                f'- Collections: {origin}/collections\n- Source directory: {origin}/feeds/sources.json\n'
                f'- Build a profile: {origin}/build\n- Setup: {origin}/connect\n\n'
                'Source documentation is release-curated. Upstream freshness is not established by the directory date. '
                'Profile export does not save hosted settings or start a schedule. External sources are reference material, not effect authority.\n').encode(), 'text/plain'
    item = next((item for item in data.collections if path == '/collections/' + item.id), None)
    if path not in ROUTES and item is None:
        return None
    title = 'Source collections for your agents'
    if path == '/':
        body = _home(data)
    elif path in ('/collections', '/feeds'):
        body, title = _collections(data), 'Collections'
    elif path == '/saved':
        body, title = _saved(data), 'Saved collections'
    elif item:
        body, title = _detail(item, data, origin), item.title
    elif path == '/build':
        body, title = _build(data), 'Build a reading profile'
    elif path in ('/connect', '/feeds/setup'):
        body, title = _connect(data, origin), 'Connect an agent'
    elif path == '/pricing':
        body, title = _pricing(), 'Pricing'
    elif path in ACCOUNT_ROUTES:
        body, title = _account(path), 'Your account'
    elif path in ('/privacy', '/terms'):
        body, title = _legal(path[1:]), 'Privacy' if path == '/privacy' else 'Terms'
    elif path == '/status':
        body, title = _intro('Service status', 'Check the connection.', 'Current reachability is read from the shared service.') + '<p data-service-status role="status">Checking service availability…</p>', 'Status'
    else:
        body, title = _help(), 'Help'
    nav = ''.join(_link(href, label, 'active' if path == href else '') for href, label in (('/collections', 'Collections'), ('/saved', 'Saved'), ('/build', 'Build a feed'), ('/connect', 'Connect'), ('/pricing', 'Pricing'), ('/help', 'Help')))
    css = _versioned(ASSET_PREFIX + 'site.css', _asset('site.css'))
    js = _versioned(ASSET_PREFIX + 'site.js', _asset('site.js'))
    mark = _versioned(ASSET_PREFIX + 'mark.svg', _asset('mark.svg'))
    feed_path = (feed_source_collections.COLLECTION_PREFIX + item.id if item
                 else '/feeds/sources' if path in ('/', '/collections', '/feeds') else None)
    feed_links = (''.join(f'<link rel="alternate" type="{media}" title="AgentFeeds source collection" '
                         f'href="{escape(origin + feed_path + suffix, quote=True)}">'
                         for suffix, media in (('.rss', 'application/rss+xml'), ('.json', 'application/feed+json')))
                  if feed_path else '')
    scripts = f'<script defer src="{js}"></script>'
    if path == '/build':
        scripts += '<script type="module" src="' + _versioned('/assets/feed-profile.js', read_packaged_asset('feed-profile.js')) + '"></script>'
    if path in ACCOUNT_ROUTES:
        scripts += '<script defer src="' + _versioned('/assets/supabase-client.js', read_packaged_asset('supabase-client.js')) + '"></script><script defer src="' + _versioned('/assets/oauth-consent.js', read_packaged_asset('oauth-consent.js')) + '"></script><script defer src="' + _versioned(ASSET_PREFIX + 'account.js', _asset('account.js')) + '"></script>'
        scripts += '<meta name="robots" content="noindex">'
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)} | AgentFeeds</title><meta name="description" content="Source collections and reading profiles for the agents you already run.">'
            f'<link rel="canonical" href="{escape(origin + path, quote=True)}">{feed_links}<meta property="og:title" content="{escape(title, quote=True)} | AgentFeeds">'
            f'<meta property="og:url" content="{escape(origin + path, quote=True)}"><meta name="theme-color" content="#102A43"><link rel="icon" href="{mark}"><link rel="stylesheet" href="{css}">{scripts}</head>'
            '<body><a class="skip-link" href="#main">Skip to content</a><header class="site-header"><a class="brand" href="/" aria-label="AgentFeeds home">'
            f'<img src="{mark}" width="32" height="32" alt=""><span>Agent<span class="brand-light">Feeds</span></span></a>'
            '<button class="menu-button" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button><nav id="site-nav" aria-label="Main navigation">'
            + nav + '</nav><a class="header-account" href="/login">Sign in <span aria-hidden="true">↗</span></a></header>'
            '<main id="main" tabindex="-1">' + body + '<p id="saved-status" role="status" aria-live="polite"></p></main><footer class="site-footer"><div><a class="brand" href="/">Agent<span class="brand-light">Feeds</span></a>'
            '<p>A reading plan for the decisions ahead.</p></div><nav aria-label="Footer"><a href="/connect">Setup</a><a href="/help">Help</a><a href="/status">Status</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/assets/third-party-notices.txt">Open-source notices</a></nav>'
            '<p class="operator">Operated by Baltor.AI · 1428 Bryn Mawr St, Saxton, PA 16678</p></footer></body></html>')
    return html.encode('utf-8'), 'text/html'
