"""AgentStudios presentation over the shared qualified gallery and account edges.

Media lenses are discovery hints, never admission, access or execution authority.
Existing gallery records own every example, source identity and preview byte.
"""
from hashlib import sha256
from html import escape
from importlib.resources import files
import json

from . import agentfeeds_pages, agentfoundry_pages, gallery_media, gallery_records
from .http_auth import validate_public_origin
from .web_pages import read_packaged_asset

ORIGIN = "https://agentstudios.si"
ASSET_PREFIX = "/assets/agentstudios/"
ASSETS = {"site.css": "text/css", "site.js": "text/javascript", "account.js": "text/javascript", "mark.svg": "image/svg+xml"}
ACCOUNT_ROUTES = agentfeeds_pages.ACCOUNT_ROUTES
ROUTES = ("/", "/library", "/examples", "/connect", "/help", "/docs", "/status", "/privacy", "/terms", *sorted(ACCOUNT_ROUTES))
SITE_FILES = ("/robots.txt", "/sitemap.xml", "/llms.txt", "/client.example.json")
CLIENT_FILES = agentfoundry_pages.CLIENT_FILES
SHARED_ASSETS = agentfoundry_pages.SHARED_ASSETS | frozenset(gallery_media.media_assets())
LENSES = (("images", "Images & graphics"), ("audio", "Audio & music"), ("video", "Video & motion"),
          ("3d", "3D & materials"), ("games", "Games & interaction"), ("procedural", "Templates & processes"))


def public_items():
    return agentfoundry_pages.public_items()


def original_media():
    return tuple(item for item in gallery_media.public_previews() if item["source_kind"] == "website_example")


def routes():
    return (*ROUTES, *("/examples/" + item["slug"] for item in public_items()),
            *("/media/" + item["id"] for item in original_media()))


def media_lenses(item):
    """Non-exclusive presentation hints derived from existing public metadata."""
    kind, tags = item["kind"], set(item["tags"])
    result = []
    if kind in ("godot-shaders", "procedural-textures"):
        result.append("images")
    if tags & {"audio", "music", "sound", "synthesis"}:
        result.append("audio")
    if tags & {"animation", "motion", "video", "cinematic", "cinematics", "morph targets"}:
        result.append("video")
    if kind in ("blender-tools", "mesh-algorithms", "geometry-4d", "asset-contracts"):
        result.append("3d")
    if kind in ("godot-shaders", "godot-components") or "godot" in tags:
        result.append("games")
    if kind in ("procedural-textures", "blender-tools", "mesh-algorithms", "geometry-4d") or "procedural" in tags:
        result.append("procedural")
    return tuple(result)


def _asset(name):
    if name == "account.js":
        return (agentfoundry_pages._asset(name).decode().replace("AgentFoundry", "AgentStudios")
                .replace("agentfoundry.identity-session", "agentstudios.identity-session").encode())
    return files(__package__).joinpath("web_assets", "agentstudios", name).read_bytes()


def _versioned(name):
    return ASSET_PREFIX + name + "?v=" + sha256(_asset(name)).hexdigest()


def _link(path, title, cls=""):
    return f'<a class="{cls}" href="{escape(path, quote=True)}">{escape(title)}</a>'


def _intro(label, title, description):
    return f'<div class="intro"><p class="eyebrow">{escape(label)}</p><h1>{escape(title)}</h1><p class="lede">{escape(description)}</p></div>'


def _tile(item):
    return agentfoundry_pages._tile(item).replace('data-component ', 'data-component data-media="' + ' '.join(media_lenses(item)) + '" ')


def _media_tile(item):
    lens = "audio" if item["kind"] == "music" else "video"
    art = ('<span class="sound-bars" aria-hidden="true">' + '<i></i>' * 19 + '</span>' if lens == "audio"
           else '<span class="motion-lines" aria-hidden="true"><i></i><i></i><i></i></span>')
    search = escape((item["title"] + " " + item["summary"] + " " + lens).lower(), quote=True)
    return (f'<article class="component media-{lens}" data-component data-media="{lens} procedural" data-search="{search}">'
            f'<a class="component-image" href="/media/{item["id"]}" aria-label="Open {escape(item["title"], quote=True)}">{art}</a>'
            '<div class="component-copy"><p class="eyebrow">Original website demo</p><h3>'
            + _link('/media/' + item['id'], item['title']) + '</h3><p>' + escape(item['summary'])
            + '</p><div class="component-meta"><span>' + escape(item['format']) + '</span><span>' + escape(item['preview_licence'])
            + '</span>' + _link('/media/' + item['id'], 'Play & inspect ↗') + '</div></div></article>')


def _home(items):
    featured = [next(item for item in items if item['slug'] == slug) for slug in ('torus-knot', 'truchet-tiles-2d', 'material-soap-bubble')]
    hero = next(item for item in items if item['slug'] == 'plasma-sine-2d')
    previews = ''.join(_tile(item) for item in featured)
    return ('<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="live-dot"></span> A library for creative work</p>'
            '<h1>Working files for <br><em>creative projects.</em></h1><p class="lede">Explore visual components, editable source and tools for your next project. Bring the useful parts into the applications and agents you already use.</p>'
            '<div class="actions">' + _link('/library', 'Explore the library ↗', 'button primary') + _link('/connect', 'Connect your agent', 'text-link') + '</div>'
            '<p class="quiet">For designers, game makers, media creators and their agents.</p></div>'
            '<div class="studio-board"><div class="board-label"><span>ON THE WORKBENCH</span><span>EDITABLE / INSPECTABLE</span></div>'
            '<a class="board-main" href="/examples/' + hero['slug'] + '"><img src="' + gallery_records.ASSET_PREFIX + hero['preview']['file']
            + '" width="' + str(hero['preview']['width']) + '" height="' + str(hero['preview']['height']) + '" alt="Recorded render of the plasma sine shader">'
            '<span>Plasma sine shader <b>↗</b></span></a><div class="board-note"><span class="asterisk" aria-hidden="true">✳</span><p>Keep the source.<br>Change the result.</p><span class="tiny">RECORDED COMPONENT PREVIEW</span></div></div></section>'
            '<nav class="medium-strip" aria-label="Explore a creative medium">' + ''.join(_link('/library?media=' + key, label + ' ↗') for key, label in LENSES) + '</nav>'
            '<section class="section"><div class="section-heading"><div><p class="eyebrow">A few starting points</p><h2>Look inside the work.</h2></div>'
            + _link('/library', 'Browse all public examples →', 'text-link') + '</div><div class="component-grid">' + previews + '</div>'
            '<p class="quiet">These are recorded renders of real components. Each detail page includes files, requirements, licence and the checks performed.</p></section>'
            '<section class="sound-stage"><div><p class="eyebrow">Picture. Sound. Source.</p><h2>Play the preview.<br>Open the project.</h2>'
            '<p>Try the published motion and music demonstrations. Their source ZIP contains the editable score, procedural renderer and checks. These demo downloads are open to everyone.</p></div>'
            '<div class="demo-grid">' + ''.join(_media_tile(item) for item in original_media()) + '</div></section>'
            '<section class="workflow section"><div><p class="eyebrow">Your tools stay yours</p><h2>Use the material.<br>Keep creative control.</h2>'
            '<p>AgentStudios is a place to discover and retrieve working material. Editing, generation and rendering happen in the tools you choose.</p></div>'
            '<ol><li><span>01</span><div><h3>Find a useful starting point</h3><p>Filter examples by medium, or ask your connected agent to search for a specific task.</p></div></li>'
            '<li><span>02</span><div><h3>Check what comes with it</h3><p>Read the file list, licence, required application versions and known limits before downloading.</p></div></li>'
            '<li><span>03</span><div><h3>Bring it into your project</h3><p>Your agent retrieves the selected version with your account access. Test the result where you intend to use it.</p></div></li></ol></section>')


def _library(items):
    return (_intro('The creative library', 'Find your next starting point.', 'Browse components and original media demonstrations. The medium filters group the public examples, and editing happens in the tools you choose.')
            + '<form class="filters" data-example-filters role="search"><label>Search public examples<input name="query" type="search" maxlength="200" placeholder="Try a texture, shader, camera or music cue"></label>'
            '<label>Creative medium<select name="media"><option value="">Every medium</option>'
            + ''.join(f'<option value="{key}">{label}</option>' for key, label in LENSES) + '</select></label><button class="button secondary" type="reset">Clear</button></form>'
            '<p data-example-status role="status" aria-live="polite"></p><div class="component-grid">'
            + ''.join(_media_tile(item) for item in original_media()) + ''.join(_tile(item) for item in items) + '</div>'
            '<p class="quiet">Component previews show recorded renders, and reuse of each preview follows its licence. Check the source licence and access notes. Original media demos have their own MIT licence.</p>'
            '<noscript><p>All public examples are shown. JavaScript adds search and medium filters.</p></noscript>'
            '<section class="section public-section"><div class="section-heading"><div><p class="eyebrow">Search beyond these examples</p><h2>The Public Good collection.</h2></div></div>'
            '<p>Search current shared component metadata. Selected Public Good files are free with an enabled account, subject to the collection limits. Your connected agent can also search the wider account-authorized library.</p>'
            '<form class="filters" data-public-search role="search"><label>Search the shared collection<input name="query" type="search" maxlength="200" placeholder="Describe the task or tool you need"></label><button class="button primary">Search</button></form>'
            '<p role="status" aria-live="polite" data-public-status>Loading the current collection…</p><div class="public-results" data-public-results></div>'
            '<div class="pagination"><button class="button secondary" type="button" data-public-previous disabled>Previous</button><button class="button secondary" type="button" data-public-next disabled>Next</button></div>'
            '<p class="quiet" data-public-limits></p><noscript><a href="/api/v1/public-good">Read collection metadata as JSON</a></noscript></section>')


def _media_detail(item):
    tag = 'audio' if item['kind'] == 'music' else 'video'
    return (_link('/library', '← Back to the library', 'back') + _intro('Original website demonstration', item['title'], item['summary'])
            + '<div class="detail-layout"><article><div class="media-player ' + tag + '"><' + tag + ' controls preload="none" aria-label="' + escape(item['title'], quote=True) + '">'
            '<source src="' + item['url'] + '" type="' + item['media_type'] + '">Use the preview download if your browser cannot play this format.</' + tag + '></div>'
            '<section class="reading"><h2>Editable source, included.</h2><p>This is an original website demo, separate from the account-authorized library. Its MIT licence covers the preview and the editable source. The ZIP includes the source, instructions and checks.</p>'
            + _link(item['source_page'], 'Download the source ZIP ↗', 'button primary') + '</section><section class="reading"><h2>Provenance</h2><p>' + escape(item['provenance']) + '</p>'
            '<p>Treat it as a starting point and run your project’s own checks before production use.</p></section></article><aside class="panel"><p class="eyebrow">File details</p><h2>Inspect the version.</h2>'
            '<dl class="facts"><dt>Format</dt><dd>' + escape(item['format']) + '</dd><dt>Duration</dt><dd>' + str(item['duration_seconds']) + ' seconds</dd>'
            '<dt>Preview and source licence</dt><dd>' + escape(item['preview_licence']) + '</dd><dt>Preview SHA-256</dt><dd><code>' + item['sha256'] + '</code></dd>'
            '<dt>Source ZIP SHA-256</dt><dd><code>' + item['source_version'] + '</code></dd></dl>'
            + _link(item['url'], 'Download the preview', 'button secondary') + '<p class="quiet">These two downloads are open to everyone.</p></aside></div>')


def _rebrand(body):
    return body.replace('AgentFoundry', 'AgentStudios').replace('agentfoundry-', 'agentstudios-')


def _help():
    answers = (("What can I use here?", "Browse public component details and recorded previews, play the original media demonstrations and download their editable source ZIP. Connect your agent for library search and authorized file delivery."),
               ("Where do editing and rendering happen?", "In your chosen applications and agents, which do the editing, generation and rendering. This site supplies discoverable material, requirements and source files."),
               ("Which creative media are covered best?", "Current examples are strongest in shaders, procedural textures, 3D geometry and Godot components. Music and video have a small set of original demonstrations. The filters show only real, available examples."),
               ("Can I reuse a preview image?", "Reuse rights come from each licence, so read the source and preview licences separately. The original music and video demonstrations explicitly include MIT-licensed previews and source."),
               ("Is this a new account or subscription?", "AgentStudios has a separate creative-facing website over the same backend and account service. Existing entitlements remain unchanged. Sign-in sessions stay on this website's origin, so you sign in on each website separately."))
    return (_intro('Help & access', 'A clear starting point.', 'Check the material and its requirements before bringing it into a project.')
            + '<div class="faq">' + ''.join('<details><summary>' + escape(question) + '</summary><p>' + escape(answer) + '</p></details>' for question, answer in answers) + '</div>'
            '<p>Recover your password from <a href="/login">sign in</a>, or <a href="/status">check service availability</a>. Never include a password or provider key in a support request.</p>')


def error_page(status, *, message='', next_action='', reference=''):
    """An escaped standalone error with no request address or foreign assets."""
    title = 'Page not found' if status == 404 else 'This request could not be completed'
    body = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + title + ' | AgentStudios</title><meta name="robots" content="noindex"><link rel="icon" href="' + _versioned('mark.svg')
            + '"><link rel="stylesheet" href="' + _versioned('site.css') + '"></head><body><header class="site-header"><a class="brand" href="/">Agent<span>Studios</span></a></header>'
            '<main id="main">' + _intro(str(status), title, message or 'Use the library or return to the home page.')
            + ('<p>' + escape(next_action) + '</p>' if next_action else '')
            + ('<p>Reference: <code>' + escape(reference) + '</code></p>' if reference else '')
            + '<div class="actions"><a class="button primary" href="/library">Explore the library</a><a href="/status">Service status</a></div></main></body></html>')
    return body.encode()


def render(path, *, origin=ORIGIN, allow_loopback=False):
    """Render only declared pages and exact assets for the selected safe origin."""
    validate_public_origin(origin, permit_loopback=allow_loopback)
    if path.startswith(ASSET_PREFIX):
        name = path[len(ASSET_PREFIX):]
        return (_asset(name), ASSETS[name]) if name in ASSETS else None
    if path == '/client.example.json':
        return (json.dumps({'record_type': 'baltor_library_client_configuration/v2', 'origin': origin,
                            'credential_environment': 'BALTOR_SERVICE_TOKEN', 'authority_effects': ['reads_fs']}, indent=2) + '\n').encode(), 'application/json'
    if path == '/robots.txt':
        return ('User-agent: *\nDisallow: /api/\nDisallow: /auth/\nDisallow: /account\nDisallow: /oauth/\nSitemap: ' + origin + '/sitemap.xml\n').encode(), 'text/plain'
    if path == '/sitemap.xml':
        addresses = [value for value in routes() if value not in ACCOUNT_ROUTES and value not in ('/docs', '/status')]
        return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + ''.join('<url><loc>' + escape(origin + address) + '</loc></url>' for address in addresses) + '</urlset>').encode(), 'application/xml'
    if path == '/llms.txt':
        return (f'# AgentStudios\n\nCreative components, media demonstrations and editable source for your existing tools.\n\n- Library: {origin}/library\n- Connect: {origin}/connect\n- MCP: {origin}/mcp\n\n'
                'Check source and preview licences separately. Public component metadata grants no download or execution authority. '
                'Library delivery uses existing account entitlements. Original website demos include public MIT-licensed source ZIPs. '
                'Editing, model calls and rendering run in your chosen tools, not on this website.\n').encode(), 'text/plain'
    item = next((entry for entry in public_items() if path == '/examples/' + entry['slug']), None)
    media = next((entry for entry in original_media() if path == '/media/' + entry['id']), None)
    if path not in ROUTES and item is None and media is None:
        return None
    if path == '/':
        body, title = _home(public_items()), 'Working files for creative projects'
    elif path in ('/library', '/examples'):
        body, title = _library(public_items()), 'Creative library'
    elif item:
        body, title = agentfoundry_pages._detail(item), item['title']
    elif media:
        body, title = _media_detail(media), media['title']
    elif path == '/connect':
        body, title = _rebrand(agentfoundry_pages._connect(origin)), 'Connect your agent'
    elif path in ACCOUNT_ROUTES:
        body, title = _rebrand(agentfoundry_pages._account(path)), 'Your account'
    elif path in ('/privacy', '/terms'):
        body, title = agentfeeds_pages._legal(path[1:]), path[1:].title()
    elif path == '/status':
        body, title = _intro('Service status', 'Check the connection.', 'Read current reachability from the shared service.') + '<p role="status" data-service-status>Checking service availability…</p>', 'Service status'
    else:
        body, title = _help(), 'Help'
    scripts = '<script defer src="' + _versioned('site.js') + '"></script>'
    if path in ACCOUNT_ROUTES:
        scripts += ''.join('<script defer src="/assets/' + name + '?v=' + sha256(read_packaged_asset(name)).hexdigest() + '"></script>' for name in ('supabase-client.js', 'oauth-consent.js'))
        scripts += '<script defer src="' + _versioned('account.js') + '"></script><meta name="robots" content="noindex">'
    nav = ''.join('<a href="' + href + '"' + (' aria-current="page"' if href == path else '') + '>' + label + '</a>' for href, label in (('/library', 'Library'), ('/connect', 'For your agent'), ('/help', 'About & help')))
    mark = _versioned('mark.svg')
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + escape(title) + ' | AgentStudios</title><meta name="description" content="Creative components, editable source and media demonstrations for the tools and agents you already use.">'
            '<link rel="canonical" href="' + escape(origin + path, quote=True) + '"><meta property="og:title" content="' + escape(title, quote=True) + ' | AgentStudios">'
            '<meta property="og:url" content="' + escape(origin + path, quote=True) + '">'
            + agentfeeds_pages._preview('AgentStudios', 'Creative components, editable source and media demonstrations for the tools and agents you already use.')
            + '<meta name="theme-color" content="#f7f5ef"><link rel="icon" href="' + mark + '">'
            '<link rel="stylesheet" href="' + _versioned('site.css') + '">' + scripts + '</head><body><a class="skip-link" href="#main">Skip to content</a>'
            '<header class="site-header"><a class="brand" href="/" aria-label="AgentStudios home"><img src="' + mark + '" width="34" height="34" alt="">Agent<span>Studios</span></a>'
            '<button class="menu-button" type="button" aria-controls="site-nav" aria-expanded="false">Menu</button><nav id="site-nav" aria-label="Main navigation">' + nav + '</nav>'
            '<a class="header-account" href="/login">Sign in ↗</a></header><main id="main" tabindex="-1">' + body + '</main>'
            '<footer class="site-footer"><div><a class="brand" href="/">Agent<span>Studios</span></a><p>Working material for creative projects.</p></div>'
            '<nav aria-label="Footer"><a href="/connect">Connect</a><a href="/help">Help</a><a href="/status">Status</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/assets/third-party-notices.txt">Open-source notices</a></nav>'
            '<p class="operator">Operated by Baltor.AI · 1428 Bryn Mawr St, Saxton, PA 16678</p></footer></body></html>')
    return html.encode(), 'text/html'
