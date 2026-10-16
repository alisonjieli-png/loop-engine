"""Passive AgentFeeds campaign pages using the existing source directory.

This presentation does not collect visitor data, configure agents or activate
schedules. Its links hand the visitor to AgentFeeds explicitly.
"""
from hashlib import sha256
from html import escape
from importlib.resources import files

from . import feed_profiles
from .agentfeeds_pages import _legal
from .http_auth import is_loopback_url, validate_public_origin

ORIGIN = "https://dontbeameatproxy.si"
FEEDS_ORIGIN = "https://agentfeeds.si"
ASSET_PREFIX = "/assets/meatproxy/"
ASSETS = {"site.css": "text/css", "site.js": "text/javascript", "mark.svg": "image/svg+xml"}
SHARED_ASSETS = frozenset()
ROUTES = ("/", "/how-it-works", "/questions", "/privacy", "/terms")
SITE_FILES = ("/robots.txt", "/sitemap.xml", "/llms.txt")
COLLECTION_IDS = ("coding-benchmarks", "model-cost", "developer-releases", "creative-engines")


def routes():
    return ROUTES


def _asset(name):
    return files(__package__).joinpath("web_assets", "meatproxy", name).read_bytes()


def _versioned(name):
    return ASSET_PREFIX + name + "?v=" + sha256(_asset(name)).hexdigest()


def _link(href, label, kind=""):
    return f'<a class="{kind}" href="{escape(href, quote=True)}">{escape(label)}</a>'


def _instruction(collection_id):
    return (f"Read {FEEDS_ORIGIN}/feeds/collections/{collection_id}.md before making this decision. "
            "Check the original sources, compare evidence relevant to my task, and cite what you used. "
            "State the dates and anything you could not verify. Ask before taking actions.")


def _try_it():
    by_id = {item.id: item for item in feed_profiles.current_directory().collections}
    options = ''.join(f'<option value="{key}">{escape(by_id[key].title)}</option>' for key in COLLECTION_IDS)
    first = COLLECTION_IDS[0]
    return ('<section class="try-section" id="try-it" aria-labelledby="try-title"><div class="section-label"><span>02 / Try a direct route</span><span>Uses real source collections</span></div>'
            '<div class="try-grid"><div><h2 id="try-title">Give your agent<br>a place to start.</h2>'
            '<p>Choose a decision. Take this instruction to the agent you already use.</p>'
            '<label for="decision">What is it working on?</label><select id="decision">' + options + '</select>'
            '<p class="small">Your agent needs permission to read the web. Its tools, model access and schedule stay under your control.</p></div>'
            '<div class="instruction-card"><div class="instruction-top"><span>Agent instruction</span><span class="file-kind">Plain text</span></div>'
            '<label class="visually-hidden" for="reading-instruction">Instruction to give your agent</label>'
            '<textarea id="reading-instruction" readonly rows="8">' + escape(_instruction(first)) + '</textarea>'
            '<div class="instruction-actions"><button type="button" id="copy-instruction">Copy instruction <span aria-hidden="true">↗</span></button>'
            + _link(FEEDS_ORIGIN + '/collections/' + first, 'Inspect the sources ↗', 'source-link') + '</div>'
            '<p id="copy-status" role="status" aria-live="polite">Read the sources yourself whenever you want.</p></div></div>'
            '<p class="customize">Different agents need different reading lists. '
            + _link(FEEDS_ORIGIN + '/build?collection=' + first, 'Customize this reading profile on AgentFeeds →', 'profile-link') + '</p>'
            '<noscript><p>The example above works without JavaScript. Browse the other decisions in <a href="https://agentfeeds.si/collections">AgentFeeds collections</a>.</p></noscript></section>')


def _relay():
    return ('<div class="relay-board" aria-label="An illustration of the human relay and the direct source-reading workflow">'
            '<div class="board-top"><span>The familiar routine</span><span class="board-number">01</span></div>'
            '<div class="relay-stack"><div class="source-stack"><span>Newsletter</span><span>Social post</span><span>Release notes</span></div>'
            '<span class="relay-arrow" aria-hidden="true">↓</span><div class="person-card"><span class="person-icon" aria-hidden="true">●</span>'
            '<strong>You</strong><span>Read. Filter. Copy. Paste.</span></div><span class="relay-arrow" aria-hidden="true">↓</span>'
            '<div class="agent-card"><span class="agent-icon" aria-hidden="true">[ : ]</span><strong>Your agent</strong><span>Waiting for context</span></div></div>'
            '<div class="board-new"><span>A more direct route</span><p>Sources <span aria-hidden="true">→</span> Your agent</p>'
            '<span>You set the question and check the result.</span></div></div>')


def _home():
    return ('<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="signal" aria-hidden="true"></span>An AgentFeeds campaign</p>'
            '<h1>Don\'t be a<br><span class="meat">meat proxy.</span></h1>'
            '<p class="hero-lede">You have better things to do than read the internet to your agent.</p>'
            '<p class="hero-explanation">Reading newsletters. Scrolling LinkedIn. Pasting somebody’s take into a chat. Give your agent the sources and a question it can investigate instead.</p>'
            '<div class="actions">' + _link(FEEDS_ORIGIN + '/build', 'Build a reading profile ↗', 'button primary')
            + _link('#try-it', 'Try an instruction ↓', 'text-link') + '</div><p class="small">Opens AgentFeeds. Public collections and profile downloads are open to everyone.</p></div>'
            + _relay() + '</section>'
            '<section class="problem-section" id="the-problem"><div class="section-label"><span>01 / The human relay problem</span><span>Keep the judgment. Lose the copying.</span></div>'
            '<div class="problem-grid"><h2>Your attention<br>is not an API.</h2><div><p class="large-copy">A post says a model is better. Your task needs to know: better at what, compared with which version, and under which conditions?</p>'
            '<p>AgentFeeds gives your agent a curated source list and specific comparison questions. It can check the original evidence for the decision in front of it. You decide what matters and review the answer.</p>'
            + _link('/how-it-works', 'See how the handoff works →', 'text-link') + '</div></div></section>'
            + _try_it()
            + '<section class="scope-section"><div><p class="eyebrow">What you can use today</p><h2>A reading list.<br>With a job to do.</h2></div>'
            '<div class="scope-copy"><p>Browse curated collections. Read them as Markdown, RSS or JSON Feed. Build a custom profile and download its settings and reading guide for each agent.</p>'
            '<p>These are source references and research questions for your agent to investigate. Your agent reads the originals, on the schedule your harness sets.</p>'
            + _link(FEEDS_ORIGIN + '/collections', 'Explore AgentFeeds collections ↗', 'text-link') + '</div></section>'
            '<section class="closing"><p class="eyebrow">For the agent you already run</p><h2>Point it at the source.</h2><p>Choose the decisions your agent needs to stay informed about.</p>'
            + _link(FEEDS_ORIGIN + '/build', 'Build your AgentFeeds profile ↗', 'button light')
            + '<p class="small">Browsing and downloading a reading profile take only a browser.</p></section>')


def _how_it_works():
    return ('<header class="page-intro"><p class="eyebrow">The handoff</p><h1>Set the question.<br>Let your agent read.</h1><p>You keep the decisions and permissions. AgentFeeds supplies a starting point for research.</p></header>'
            '<ol class="steps"><li><span class="step-number">01</span><div><h2>Choose an actual decision</h2><p>Start with a collection such as choosing a coding model or planning a platform upgrade. Read its source references and comparison questions.</p>'
            + _link(FEEDS_ORIGIN + '/collections', 'Browse the collections ↗') + '</div></li>'
            '<li><span class="step-number">02</span><div><h2>Give the reading job to your agent</h2><p>Use the instruction below, or build a custom reading profile. Save the downloaded <code>profile.json</code> and <code>READING.md</code> in that agent’s project. Do not put secrets in its label or feed links.</p>'
            + _link(FEEDS_ORIGIN + '/build', 'Build a custom reading profile ↗') + '</div></li>'
            '<li><span class="step-number">03</span><div><h2>Check what it actually found</h2><p>Ask for original source links, dates, relevant comparisons and uncertainties: those links show what your agent actually read. Treat a release notice as a reason to investigate before you change your tools.</p></div></li>'
            '<li><span class="step-number">04</span><div><h2>Choose when it looks again</h2><p>Ask it to read before a decision, or configure your own harness’s scheduler. A requested reading interval in a profile is a preference that your harness’s scheduler applies.</p>'
            + _link(FEEDS_ORIGIN + '/connect', 'Read the AgentFeeds setup guide ↗') + '</div></li></ol>' + _try_it())


def _questions():
    items = (("What is a meat proxy?", "Here it means the person in the middle: reading posts, filtering newsletters and copying information into an agent. You still choose the task and judge the result. Your agent can do the copying."),
             ("What is this campaign?", "A campaign for AgentFeeds. The links take you to its source collections and reading-profile builder. You keep using your own agent and model access."),
             ("Does AgentFeeds read every source for me?", "The current public collections provide curated source references and research questions. Your agent reads the original sources with its own tools and permissions. A directory review date shows when the source list was checked; each upstream article keeps its own date."),
             ("Can I give different agents different feeds?", "Yes. Build a reading profile for each agent, choosing collections and individual sources. Download its profile.json and READING.md files. These settings stay in your files, where your harness reads them."),
             ("What happens when I download a profile?", "You get two files to keep. Your own harness runs any reading schedule, model call or action, each with your approval."),
             ("What does it cost?", "AgentFeeds public source collections and reading-profile downloads are free through December 31, 2026, Eastern time. Its published standard price is $9 a month. There is no automatic charge; paid activation requires explicit opt-in. Your model access and upstream provider costs remain yours."),
             ("Who operates this website?", "Baltor.AI operates this campaign and AgentFeeds. They use the same backend. This campaign adds no account form or advertising tracker. The privacy notice and terms below are the existing operator notices."))
    return ('<header class="page-intro"><p class="eyebrow">Before you hand it off</p><h1>Good questions.</h1><p>What the campaign means, what you can use, and what stays under your control.</p></header>'
            '<section class="questions" aria-label="Frequently asked questions">'
            + ''.join('<details><summary>' + escape(question) + '</summary><p>' + escape(answer) + '</p></details>' for question, answer in items)
            + '</section><div class="question-links">' + _link(FEEDS_ORIGIN + '/help', 'Get AgentFeeds help ↗', 'button primary')
            + _link(FEEDS_ORIGIN + '/pricing', 'Read the pricing details ↗', 'text-link') + '</div>')


def error_page(status, *, message='', next_action='', reference=''):
    """An escaped standalone campaign error. It links only to campaign pages and names no account or key."""
    title = 'Page not found' if status == 404 else 'This request could not be completed'
    css, mark = _versioned('site.css'), _versioned('mark.svg')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title} | Don\'t be a meat proxy</title><meta name="robots" content="noindex"><link rel="icon" href="{mark}"><link rel="stylesheet" href="{css}"></head>'
            '<body><header class="site-header"><a class="brand" href="/" aria-label="Don\'t be a meat proxy home">'
            f'<img src="{mark}" width="36" height="36" alt=""><span>don\'t be a<br>meat proxy.</span></a></header>'
            '<main id="main"><header class="page-intro"><p class="eyebrow">' + str(status) + '</p><h1>' + title + '</h1><p>'
            + escape(message or 'Return to the campaign home page or read how the handoff works.') + '</p>'
            + ('<p>' + escape(next_action) + '</p>' if next_action else '')
            + ('<p>Reference: <code>' + escape(reference) + '</code></p>' if reference else '')
            + '<div class="actions">' + _link('/', 'Go to the campaign home', 'button primary') + _link('/how-it-works', 'How it works', 'text-link')
            + '</div></header></main></body></html>').encode()


def render(path, *, origin=ORIGIN, allow_loopback=False):
    """Render an exact public route without network calls or customer effects."""
    validate_public_origin(origin, permit_loopback=allow_loopback)
    if not (allow_loopback and is_loopback_url(origin)) and ':' in origin.split('://', 1)[1]:
        raise ValueError("campaign pages require an exact HTTPS public origin without a port")
    if path.startswith(ASSET_PREFIX):
        name = path[len(ASSET_PREFIX):]
        return (_asset(name), ASSETS[name]) if name in ASSETS else None
    if path == '/robots.txt':
        return (f'User-agent: *\nDisallow: /api/\nDisallow: /auth/\nSitemap: {origin}/sitemap.xml\n').encode(), 'text/plain'
    if path == '/sitemap.xml':
        return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + ''.join('<url><loc>' + escape(origin + item) + '</loc></url>' for item in ROUTES) + '</urlset>').encode(), 'application/xml'
    if path == '/llms.txt':
        return ("# Don't be a meat proxy\n\nAn AgentFeeds acquisition campaign operated by Baltor.AI.\n\n"
                f'- How it works: {origin}/how-it-works\n- Questions: {origin}/questions\n'
                f'- AgentFeeds collections: {FEEDS_ORIGIN}/collections\n- Build a reading profile: {FEEDS_ORIGIN}/build\n\n'
                'Current collections contain curated source references and research questions. The agent reads original sources with its own permissions. '
                'Profile downloads do not create hosted schedules or personalized news streams.\n').encode(), 'text/plain'
    if path not in ROUTES:
        return None
    title = "Don't be a meat proxy"
    if path == '/':
        body = _home()
    elif path == '/how-it-works':
        body, title = _how_it_works(), "How the handoff works"
    elif path == '/questions':
        body, title = _questions(), "Questions"
    else:
        body, title = '<div class="legal-page">' + _legal(path[1:]) + '</div>', 'Privacy' if path == '/privacy' else 'Terms'
    css, js, mark = (_versioned(name) for name in ('site.css', 'site.js', 'mark.svg'))
    canonical = escape(origin + path, quote=True)
    nav = ''.join('<a href="' + href + '"' + (' aria-current="page"' if href == path else '') + '>' + label + '</a>'
                  for href, label in (('/how-it-works', 'How it works'), ('/questions', 'Questions')))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)} | An AgentFeeds campaign</title><meta name="description" content="Stop relaying newsletters and social posts to your agent. Give it curated sources and a question with AgentFeeds.">'
            f'<link rel="canonical" href="{canonical}"><meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:url" content="{canonical}">'
            '<meta property="og:description" content="You have better things to do than read the internet to your agent."><meta property="og:type" content="website">'
            '<meta property="og:site_name" content="Don&#x27;t be a meat proxy"><meta name="twitter:card" content="summary">'
            f'<meta name="theme-color" content="#f5f0e8"><link rel="icon" href="{mark}"><link rel="stylesheet" href="{css}"><script defer src="{js}"></script></head>'
            '<body><a class="skip-link" href="#main">Skip to content</a><header class="site-header"><a class="brand" href="/" aria-label="Don\'t be a meat proxy home">'
            f'<img src="{mark}" width="36" height="36" alt=""><span>don\'t be a<br>meat proxy.</span></a>'
            '<button class="menu-button" type="button" aria-controls="site-nav" aria-expanded="false">Menu</button>'
            '<nav id="site-nav" aria-label="Main navigation">' + nav + _link(FEEDS_ORIGIN + '/build', 'Open AgentFeeds ↗', 'nav-cta') + '</nav></header>'
            '<main id="main" tabindex="-1">' + body + '</main><footer class="site-footer"><div><strong>Don\'t be a meat proxy.</strong>'
            '<p>An AgentFeeds campaign. Sources for the agent you already run.</p></div><nav aria-label="Footer">'
            + _link('/privacy', 'Privacy') + _link('/terms', 'Terms') + _link(FEEDS_ORIGIN + '/help', 'AgentFeeds help ↗')
            + '</nav><p class="operator">Operated by Baltor.AI · 1428 Bryn Mawr St, Saxton, PA 16678</p></footer></body></html>').encode(), 'text/html'
