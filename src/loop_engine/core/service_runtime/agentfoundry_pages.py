"""Independent AgentFoundry pages over the existing catalogue and account edges.

The renderer reads qualified public gallery metadata, not account bodies. A
preview or component reference never grants download or execution authority.
"""
from hashlib import sha256
from html import escape
from importlib.resources import files
import json

from . import agentfeeds_pages, gallery_records
from .http_auth import validate_public_origin
from .web_pages import read_packaged_asset

ORIGIN = "https://getagentfoundry.si"
ASSET_PREFIX = "/assets/agentfoundry/"
ASSETS = {"site.css": "text/css", "site.js": "text/javascript", "account.js": "text/javascript", "mark.svg": "image/svg+xml"}
ACCOUNT_ROUTES = agentfeeds_pages.ACCOUNT_ROUTES
ROUTES = ("/", "/library", "/examples", "/connect", "/help", "/docs", "/status", "/privacy", "/terms", *sorted(ACCOUNT_ROUTES))
SITE_FILES = ("/robots.txt", "/sitemap.xml", "/llms.txt", "/client.example.json")
CLIENT_FILES = ("SKILL.md", "LICENSE", "scripts/baltor.py", "references/client.md", "assets/client.example.json", "verification/test_client.py", "SHA256SUMS")
SHARED_ASSETS = frozenset(("/assets/supabase-client.js", "/assets/oauth-consent.js", "/assets/third-party-notices.txt",
                           *("/assets/baltor-library/" + name for name in CLIENT_FILES), *gallery_records.preview_assets()))


def public_items():
    return tuple(item for item in gallery_records.record()["items"] if item["tier"] in gallery_records.PUBLIC_TIERS)


def routes():
    return (*ROUTES, *("/examples/" + item["slug"] for item in public_items()))


def _asset(name):
    if name == "account.js":
        # The qualified identity flow is reused byte-for-byte except presentation
        # names and profile-specific copy. Its protocol and authority stay shared.
        return (agentfeeds_pages._asset(name).decode().replace("AgentFeeds", "AgentFoundry")
                .replace("agentfeeds.identity-session", "agentfoundry.identity-session")
                .replace("Your reading profiles remain in the files you save.", "Connect your agent to use the library.")
                .replace("Public feeds do not require sign-in.", "Public examples do not require sign-in.").encode())
    return files(__package__).joinpath("web_assets", "agentfoundry", name).read_bytes()


def _versioned(path, body):
    return path + "?v=" + sha256(body).hexdigest()


def _link(path, label, kind=""):
    return f'<a class="{kind}" href="{escape(path, quote=True)}">{escape(label)}</a>'


def _intro(label, title, description):
    return f'<div class="intro"><p class="eyebrow">{escape(label)}</p><h1>{escape(title)}</h1><p class="lede">{escape(description)}</p></div>'


def _copy(value, label):
    return f'<div class="copy-field"><label>{escape(label)}<input readonly value="{escape(value, quote=True)}"></label><button type="button" data-copy>Copy</button></div>'


def _tile(item):
    preview = item.get("preview")
    picture = (f'<img src="{gallery_records.ASSET_PREFIX}{preview["file"]}" width="{preview["width"]}" height="{preview["height"]}" '
               f'loading="lazy" alt="Recorded render of {escape(item["title"], quote=True)}">' if preview else '<span class="file-preview">Working files<br>+ recorded checks</span>')
    search = " ".join((item["title"], item["summary"], *item["tags"])).lower()
    return (f'<article class="component" data-component data-kind="{escape(item["kind"], quote=True)}" data-search="{escape(search, quote=True)}">'
            f'<a class="component-image" href="/examples/{item["slug"]}">{picture}</a><div class="component-copy"><p class="eyebrow">{escape(item["kind"].replace("-", " "))}</p>'
            f'<h3>{_link("/examples/" + item["slug"], item["title"])}</h3><p>{escape(item["summary"])}</p>'
            f'<div class="component-meta"><span>{len(item["files"])} files</span><span>{escape(item["licence"])}</span>{_link("/examples/" + item["slug"], "Inspect →")}</div></div></article>')


def _home(items):
    featured = [next(item for item in items if item["kind"] == kind and item.get("preview"))
                for kind in ("godot-shaders", "procedural-textures", "mesh-algorithms")]
    return ('<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="square"></span> The component library for your agent</p>'
            '<h1>Start with<br>something<br><em>that works.</em></h1><p class="lede">Give your agent the skills, code, instructions and working files it needs. Spend less time assembling its starting point.</p>'
            '<div class="actions">' + _link('/examples', 'Explore the components ↗', 'button primary') + _link('/connect', 'Connect your agent', 'text-link') + '</div>'
            '<p class="quiet">For your existing harness. Your models and permissions stay yours.</p></div>'
            '<aside class="assembly" aria-label="The kinds of material available to an agent"><div class="assembly-top"><span>YOUR NEXT PROJECT</span><span>PARTS / 01</span></div>'
            '<p class="assembly-title">The useful work<br>starts here.</p><div class="parts"><div><span>01</span><strong>Instructions & skills</strong><code>AGENTS.md · SKILL.md</code></div>'
            '<div><span>02</span><strong>Code & tool setup</strong><code>modules · configs · contracts</code></div><div><span>03</span><strong>Editable material</strong><code>scenes · shaders · templates</code></div>'
            '<div><span>04</span><strong>Checks & provenance</strong><code>tests · licences · exact versions</code></div></div>'
            '<p class="assembly-caption">Select what the task needs. Keep the files you use.</p></aside></section>'
            '<section class="band"><p>Works with the agent tools you already use</p><div><span>Claude Code</span><span>Codex</span><span>OpenCode</span><span>Pi</span><span>MCP clients</span></div></section>'
            '<section class="section"><div class="section-heading"><div><p class="eyebrow">Open the actual material</p><h2>See what a component makes.</h2></div>'
            + _link('/examples', f'All {len(items)} public examples →', 'text-link') + '</div><div class="component-grid">' + ''.join(_tile(item) for item in featured) + '</div>'
            '<p class="quiet">Previews come from recorded component checks. Review each component’s limits before using it in your project.</p></section>'
            '<section class="workflow section"><div><p class="eyebrow">A shorter path to building</p><h2>Find the part.<br>Keep your workflow.</h2><p>AgentFoundry connects to the shared component service. It does not replace your agent or run your model.</p></div>'
            '<ol><li><span>01</span><div><h3>Ask for what the task needs</h3><p>Your connected agent searches short descriptions. It does not load the whole library into context.</p></div></li>'
            '<li><span>02</span><div><h3>Inspect before downloading</h3><p>Check the files, licence, requirements, declared effects and recorded tests.</p></div></li>'
            '<li><span>03</span><div><h3>Use it in your own project</h3><p>Retrieve the exact version. Run its checks in the environment where the result needs to work.</p></div></li></ol></section>'
            '<section class="closing"><div><p class="eyebrow">Keep your agent. Improve its starting point.</p><h2>What are you building?</h2></div>' + _link('/connect', 'Connect an agent →', 'button primary') + '</section>')


def _examples(items):
    kinds = [kind for kind in gallery_records.record()["kinds"] if any(item["kind"] == kind["id"] for item in items)]
    return (_intro('Component examples', 'Working material, open for inspection.', 'Browse actual creative components, their file lists and the checks recorded for each version. Download through your connected agent with the required account access.')
            + '<form class="filters" data-example-filters role="search"><label>Find a component<input name="query" type="search" placeholder="Try texture, geometry or shader"></label>'
            '<label>Component type<select name="kind"><option value="">Every type</option>'
            + ''.join(f'<option value="{kind["id"]}">{escape(kind["label"])}</option>' for kind in kinds)
            + f'</select></label><button class="button secondary" type="reset">Clear filters</button></form><p role="status" data-example-status>{len(items)} public examples</p>'
            '<div class="component-grid">' + ''.join(_tile(item) for item in items) + '</div><noscript><p>All examples are visible. JavaScript adds filtering.</p></noscript>')


def _detail(item):
    preview = item.get("preview")
    picture = (f'<img class="detail-preview" src="{gallery_records.ASSET_PREFIX}{preview["file"]}" width="{preview["width"]}" height="{preview["height"]}" alt="Recorded render of {escape(item["title"], quote=True)}">' if preview else '')
    checks = item.get("checks") or {}
    return (_link('/examples', '← All examples', 'back') + _intro(item['kind'].replace('-', ' '), item['title'], item['summary'])
            + '<div class="detail-layout"><article>' + picture + '<section class="reading"><h2>What this component contains</h2><ul class="file-list">'
            + ''.join('<li><code>' + escape(entry['path']) + '</code></li>' for entry in item['files']) + '</ul></section>'
            '<section class="reading"><h2>How it works</h2><dl class="facts">'
            + ''.join('<dt>' + escape(key) + '</dt><dd>' + escape(value) + '</dd>' for key, value in item['contract']) + '</dl></section>'
            '<section class="reading"><h2>Recorded checks</h2><p>' + escape(checks.get('engine', 'See the package verification files.')) + '</p><ul>'
            + ''.join('<li><code>' + escape(name) + '</code></li>' for name in checks.get('names', [])) + '</ul><h3>Limits to consider</h3><p>' + escape(item['limits']) + '</p></section></article>'
            '<aside class="panel"><p class="eyebrow">Retrieve with your agent</p><h2>Inspect, then bring it in.</h2><p>These are public descriptions and previews. The service checks current access before delivering files.</p>'
            + _copy(item['identity'], 'Component identity') + _copy(item['version'], 'Exact version')
            + '<dl class="facts"><dt>Licence</dt><dd>' + escape(item['licence']) + '</dd><dt>Declared effects</dt><dd>' + escape(', '.join(item['declared_effects']) or 'None') + '</dd></dl>'
            '<p>Ask your connected agent to inspect this identity and version, explain its requirements, then request your approval for use.</p>'
            + _link('/connect', 'Connect your agent →', 'button primary') + '<p class="quiet">A file download does not install or run the component.</p></aside></div>')


def _library():
    return (_intro('The component library', 'Useful files for the next step.', 'Skills and instructions, code modules, tool configurations and native working material. Your connected agent searches the account-authorized library and retrieves only the selected files.')
            + '<div class="split"><section class="reading"><h2>Search from your harness</h2><p>The full library uses authenticated search. Results carry a purpose, exact version, source, licence and declared effects. Your account determines which file bodies can be downloaded.</p>'
            + _link('/connect', 'Connect and search →', 'button primary') + '</section><section class="panel"><p class="eyebrow">Before you use a component</p><h2>Read the requirements.</h2><p>Check its recorded tests and target tools. A catalogue entry or successful download is not proof that it works in your environment.</p></section></div>'
            '<section class="section"><div class="section-heading"><div><p class="eyebrow">Public discovery</p><h2>Find Public Good components.</h2></div>' + _link('/examples', 'Browse creative examples →', 'text-link') + '</div>'
            '<p>Search the current shared Public Good collection. Its selected files are available with an enabled account and no paid plan, subject to the published limits.</p>'
            '<form class="filters" data-public-search role="search"><label>Search component descriptions<input name="query" type="search" maxlength="200" placeholder="Try water, education or accessibility"></label><button class="button primary">Search</button></form>'
            '<p role="status" aria-live="polite" data-public-status>Loading the current collection…</p><div class="public-results" data-public-results></div>'
            '<div class="pagination"><button class="button secondary" type="button" data-public-previous disabled>Previous</button><button class="button secondary" type="button" data-public-next disabled>Next</button></div>'
            '<p class="quiet" data-public-limits></p><noscript><p>Search requires JavaScript. <a href="/api/v1/public-good">Read the public collection as JSON</a>, or connect your agent.</p></noscript></section>')


def _connect(origin):
    return (_intro('Connect your agent', 'Bring the library to your tools.', 'Use the existing shared account and component service from your own harness. Your model access and project permissions stay with you.')
            + '<div class="detail-layout"><article><section class="reading"><span class="step">01</span><h2>Connect through MCP</h2><p>In a client that supports remote Streamable HTTP and OAuth, add this server address. Follow its sign-in flow and review the requested access.</p>'
            + _copy(origin + '/mcp', 'Remote MCP server') + '<p>Account registration is email-first. A confirmation link lets you set a password. Creating an account does not start a subscription.</p>'
            + _link('/get-started', 'Create an account →', 'text-link') + '</section><section class="reading"><span class="step">02</span><h2>Make a small first request</h2><p>Ask your agent:</p>'
            '<blockquote>Search the component library for my task. Show the purpose, licence, required tools and declared effects of the best matches. Do not download or run anything yet.</blockquote>'
            '<p>The service exposes <code>intelligence_search</code>, <code>provisioning_manifest</code> and <code>provisioning_read</code>. Read the manifest before authorizing a download.</p></section>'
            '<section class="reading"><span class="step">03</span><h2>Use the existing file client when needed</h2><p>The shared library skill supports Claude Code, Codex, OpenCode and Pi. Its Python client requires Python 3.10 or newer and POSIX file operations. It does not sign in or create a key for you.</p>'
            '<ul class="file-list">' + ''.join('<li>' + _link('/assets/baltor-library/' + name, name) + '</li>' for name in CLIENT_FILES) + '</ul>'
            '<p>Keep the published files and checksums together. Read the client guide before installation. The upstream example names the shared service; this same-origin configuration uses AgentFoundry:</p>'
            '<a class="button secondary" href="/client.example.json" download="agentfoundry-client.example.json">Download AgentFoundry configuration</a>'
            '<p>Supply an existing scoped service key through the named environment variable. Never paste credentials into a prompt or a configuration file.</p></section></article>'
            '<aside class="panel"><p class="eyebrow">Availability</p><h2>Files and access are separate.</h2><p>Public examples show metadata and previews. Downloads use your existing account entitlements. Public Good files require an enabled account but no paid plan.</p>'
            '<p>Paid checkout is not offered on this standalone site. Existing subscriptions and grants remain unchanged. This launch does not include hosted model calls or a general cloud-tool allowance.</p>'
            + _link('/account', 'View your account →', 'text-link') + '</aside></div>')


def _help():
    answers = (("What can I use now?", "Public component previews, file manifests and the Public Good discovery view are available here. Connect a supported harness to search and retrieve files using your existing account access."),
               ("Does AgentFoundry build an entire agent for me?", "The current service supplies reusable parts. Your harness still selects, places and checks them. Automatic whole-agent setup and qualified hosted tools remain separate work."),
               ("Where do my models run?", "In the environment and provider you choose. This website does not ask for a model key or call a model for you."),
               ("Why do some files require access?", "Public metadata and delivery rights are different. The service checks the account, item version, declared effects and entitlement before delivering a body."),
               ("Is this a separate account system?", "No. AgentFoundry is an independent interface operated by Baltor.AI over the same backend and account service. Browser sessions remain local to this origin."))
    return (_intro('Questions and limits', 'Know what you are connecting.', 'Start with a public example or a small metadata search. Inspect the result before giving your agent permission to use it.')
            + '<div class="faq">' + ''.join('<details><summary>' + escape(question) + '</summary><p>' + escape(answer) + '</p></details>' for question, answer in answers) + '</div>'
            '<p>For account trouble, use password recovery on the <a href="/login">sign-in page</a>. You can also <a href="/status">check service availability</a>. Do not include passwords or provider keys in a support request.</p>')


def _account(path):
    return (agentfeeds_pages._account(path).replace('AgentFeeds', 'AgentFoundry')
            .replace('Public source feeds and reading-profile downloads do not require an account.', 'Public examples do not require an account. Connect your agent to retrieve authorized files.')
            .replace('Reading profiles remain in the files you save.', 'Your existing component access remains unchanged.')
            .replace('Public feeds work without signing in.', 'Public examples work without signing in.')
            .replace('href="/collections">Browse collections', 'href="/examples">Browse examples'))


def render(path, *, origin=ORIGIN, allow_loopback=False):
    """Render a known route using a validated origin chosen by the HTTP owner."""
    validate_public_origin(origin, permit_loopback=allow_loopback)
    if path.startswith(ASSET_PREFIX):
        name = path[len(ASSET_PREFIX):]
        return (_asset(name), ASSETS[name]) if name in ASSETS else None
    items = public_items()
    if path == '/client.example.json':
        return (json.dumps({'record_type': 'baltor_library_client_configuration/v2', 'origin': origin,
                            'credential_environment': 'BALTOR_SERVICE_TOKEN', 'authority_effects': ['reads_fs']}, indent=2) + '\n').encode(), 'application/json'
    if path == '/robots.txt':
        return ('User-agent: *\nDisallow: /api/\nDisallow: /auth/\nDisallow: /account\nDisallow: /oauth/\nSitemap: ' + origin + '/sitemap.xml\n').encode(), 'text/plain'
    if path == '/sitemap.xml':
        addresses = ('/', '/library', '/examples', '/connect', '/help', '/privacy', '/terms', *('/examples/' + item['slug'] for item in items))
        return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + ''.join('<url><loc>' + escape(origin + address) + '</loc></url>' for address in addresses) + '</urlset>').encode(), 'application/xml'
    if path == '/llms.txt':
        return (f'# AgentFoundry\n\nReusable files and components for your existing agent.\n\n- Public examples: {origin}/examples\n- Library: {origin}/library\n- Connect: {origin}/connect\n- MCP: {origin}/mcp\n\n'
                'Public previews do not grant body access. Inspect the licence, requirements, effects and recorded checks. '
                'Downloads need account authorization and do not install or execute files. Model calls and hosted execution are not included.\n').encode(), 'text/plain'
    item = next((item for item in items if path == '/examples/' + item['slug']), None)
    if path not in ROUTES and item is None:
        return None
    if path == '/':
        body, title = _home(items), 'A better starting point for your agent'
    elif path == '/examples':
        body, title = _examples(items), 'Component examples'
    elif item:
        body, title = _detail(item), item['title']
    elif path == '/library':
        body, title = _library(), 'Component library'
    elif path == '/connect':
        body, title = _connect(origin), 'Connect your agent'
    elif path in ACCOUNT_ROUTES:
        body, title = _account(path), 'Your account'
    elif path in ('/privacy', '/terms'):
        body, title = agentfeeds_pages._legal(path[1:]), path[1:].title()
    elif path == '/status':
        body, title = _intro('Service status', 'Check the shared connection.', 'Current reachability is read from the service.') + '<p role="status" data-service-status>Checking service availability…</p>', 'Service status'
    else:
        body, title = _help(), 'Help'
    css, js, mark = (_versioned(ASSET_PREFIX + name, _asset(name)) for name in ('site.css', 'site.js', 'mark.svg'))
    scripts = f'<script defer src="{js}"></script>'
    if path in ACCOUNT_ROUTES:
        scripts += ''.join('<script defer src="' + _versioned('/assets/' + name, read_packaged_asset(name)) + '"></script>' for name in ('supabase-client.js', 'oauth-consent.js'))
        scripts += '<script defer src="' + _versioned(ASSET_PREFIX + 'account.js', _asset('account.js')) + '"></script><meta name="robots" content="noindex">'
    nav = ''.join(f'<a href="{href}"' + (' aria-current="page"' if href == path else '') + f'>{label}</a>' for href, label in (('/examples', 'Examples'), ('/library', 'Library'), ('/connect', 'Connect'), ('/help', 'Help')))
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)} | AgentFoundry</title><meta name="description" content="Skills, code, instructions and working files for the agent tools you already use.">'
            f'<link rel="canonical" href="{escape(origin + path, quote=True)}"><meta property="og:title" content="{escape(title, quote=True)} | AgentFoundry">'
            f'<meta property="og:url" content="{escape(origin + path, quote=True)}"><meta name="theme-color" content="#f4f1e9"><link rel="icon" href="{mark}">'
            f'<link rel="stylesheet" href="{css}">{scripts}</head><body><a class="skip-link" href="#main">Skip to content</a><header class="site-header">'
            f'<a class="brand" href="/" aria-label="AgentFoundry home"><img src="{mark}" width="30" height="30" alt="">Agent<span>Foundry</span></a>'
            '<button class="menu-button" type="button" aria-controls="site-nav" aria-expanded="false">Menu</button><nav id="site-nav" aria-label="Main navigation">' + nav + '</nav>'
            '<a class="header-account" href="/login">Sign in ↗</a></header><main id="main" tabindex="-1">' + body + '</main>'
            '<footer class="site-footer"><div><a class="brand" href="/">Agent<span>Foundry</span></a><p>Working material for your next project.</p></div>'
            '<nav aria-label="Footer"><a href="/connect">Setup</a><a href="/help">Help</a><a href="/status">Status</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/assets/third-party-notices.txt">Open-source notices</a></nav>'
            '<p class="operator">Operated by Baltor.AI · 1428 Bryn Mawr St, Saxton, PA 16678</p></footer></body></html>')
    return html.encode(), 'text/html'
