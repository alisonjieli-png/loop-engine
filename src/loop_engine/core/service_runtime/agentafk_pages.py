"""Independent AgentAFK presentation over the existing local overnight tools.

These pages prepare passive manifests. They neither dispatch a worker nor
introduce a scheduler, account store or execution contract.
"""
from hashlib import sha256
from html import escape
from importlib.resources import files

from .agentfeeds_pages import _legal
from .http_auth import is_loopback_url, validate_public_origin
from .web_pages import read_packaged_asset

ORIGIN = "https://agentafk.si"
ASSET_PREFIX = "/assets/agentafk/"
ASSETS = {"site.css": "text/css", "site.js": "text/javascript", "mark.svg": "image/svg+xml"}
SHARED_ASSETS = frozenset(("/assets/run-desk.js", "/assets/run-desk-core.js", "/assets/geist.woff2", "/assets/geist-mono.woff2", "/assets/third-party-notices.txt"))
ROUTES = ("/", "/plan", "/run-desk", "/setup", "/connect", "/help", "/docs", "/support", "/status", "/pricing", "/privacy", "/terms")
SITE_FILES = ("/robots.txt", "/sitemap.xml", "/llms.txt")
GUIDE = "https://github.com/alisonjieli-png/loop-engine/blob/main/tools/OVERNIGHT-QUEUE.md"


def routes():
    return ROUTES


def _asset(name):
    return files(__package__).joinpath("web_assets", "agentafk", name).read_bytes()


def _versioned(path, body):
    return path + "?v=" + sha256(body).hexdigest()


def _link(path, label, kind=""):
    return f'<a class="{kind}" href="{escape(path, quote=True)}">{escape(label)}</a>'


def _intro(label, title, description):
    return f'<div class="page-intro"><p class="eyebrow">{escape(label)}</p><h1>{escape(title)}</h1><p class="lede">{escape(description)}</p></div>'


def _home():
    return ('<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="signal"></span> Local overnight tools · Public preview</p>'
            '<h1>Leave a task.<br><em>Keep the limits.</em></h1><p class="lede">Prepare a night of agent work with your own model access. Set the call budget, keep checkpoints, and review what happened when you return.</p>'
            '<div class="actions">' + _link('/plan', 'Prepare a run ↗', 'button primary') + _link('/setup', 'How to run it', 'text-link') + '</div>'
            '<p class="quiet">Free local preview. No account or payment required.</p></div>'
            '<figure class="night-board"><div class="board-top"><span class="mono">NIGHT SHIFT / 01</span><span class="preview-tag">Illustrative plan</span></div>'
            '<div class="board-heading"><h2>Clean the dataset</h2><span class="moon" aria-hidden="true">◒</span></div>'
            '<p>One small assignment at a time.</p><ol class="task-flow"><li><span class="task-number">01</span><div><strong>Inspect the source</strong><small>List columns and missing values</small></div><span class="state">First</span></li>'
            '<li><span class="task-number">02</span><div><strong>Propose a revision</strong><small>Use the inspection report</small></div><span class="state">Then</span></li>'
            '<li><span class="task-number">03</span><div><strong>Check the result</strong><small>Compare against acceptance checks</small></div><span class="state review">Review</span></li></ol>'
            '<div class="board-limits"><div><span>Call allocation</span><strong>24 maximum</strong></div><div><span>Queue deadline</span><strong>1 hour</strong></div></div>'
            '<figcaption>Example plan, not a running job or recorded result. Dependent tasks require your review before dispatch.</figcaption></figure></section>'
            '<section class="scope-strip" aria-label="Execution boundaries"><span>Your worker</span><span>Your model access</span><span>Your explicit limits</span></section>'
            '<section class="section split"><div><p class="eyebrow">Before you step away</p><h2>Make the next step<br>small enough to check.</h2><p>A long assignment needs more than an open chat window. Prepare task files, state the permitted work, and decide what counts as done.</p>'
            + _link('/setup', 'Read the worker setup →', 'text-link') + '</div><ol class="steps"><li><span>01</span><div><h3>Choose ready tasks</h3><p>Put task files in the order you want. Leave work with unresolved prerequisites out of the executable queue.</p></div></li>'
            '<li><span>02</span><div><h3>Reserve a bounded allowance</h3><p>Choose a call allocation for each task and a deadline for the queue. Review your provider’s spending controls separately.</p></div></li>'
            '<li><span>03</span><div><h3>Keep the attempt record</h3><p>The worker retains reservations and checkpoints. An uncertain outcome pauses further dispatch for reconciliation.</p></div></li></ol></section>'
            '<section class="section report-band"><div><p class="eyebrow">When you return</p><h2>A process exit is not<br>the finish line.</h2></div><div><p>Bring the worker’s status file into the run desk. See recorded attempts, reserved calls and process exits, then check the output files before accepting the work.</p>'
            + _link('/plan#report', 'Inspect a status report →', 'text-link') + '<p class="quiet">Report inspection stays in your browser. We do not upload the file.</p></div></section>'
            '<section class="closing"><div><p class="eyebrow">Start with one short task</p><h2>Prepare tonight’s run.</h2></div>' + _link('/plan', 'Open the run desk ↗', 'button primary') + '</section>')


def _plan():
    return (_intro('Your run desk · Public preview', 'A bounded queue, ready to review.', 'Prepare the manifest and commands for a worker you control. Nothing starts from this page.')
            + '<div class="notice"><strong>Your files stay here.</strong> Preparation and report inspection happen in this browser. Do not enter credentials. The worker uses your own model access and hosting.</div>'
            '<div class="desk-layout"><section class="desk-panel" aria-labelledby="prepare-title"><p class="eyebrow">01 / Prepare</p><h2 id="prepare-title">Choose the work and its limits</h2>'
            '<p>Use existing absolute task-file paths on your Linux, macOS or WSL worker. List only ready tasks in the intended order. A cloud machine you control can run the same command.</p>'
            '<form id="run-desk-form" class="run-desk-grid"><label class="wide">Task files, one absolute path per line<textarea name="tasks" rows="4" required placeholder="/home/you/project/tasks/inspect.txt"></textarea></label>'
            '<label>Baltor checkout on the worker<input name="checkout" value="/home/you/loop-engine" required></label>'
            '<label>New private run folder<input name="runs" value="/home/you/baltor-runs/project-01" required></label>'
            '<label class="wide">Private workspace folder<input name="workspace" value="/home/you/baltor-work/project-01" required></label>'
            '<label>Maximum calls per task<input name="calls" type="number" min="1" step="1" value="12" required></label>'
            '<label>Total queue call budget<input name="budget" type="number" min="1" step="1" value="24" required></label>'
            '<label>Task time limit, seconds<input name="timeout" type="number" min="1" step="1" value="600" required></label>'
            '<label>Queue time limit, seconds<input name="deadline" type="number" min="1" step="1" value="3600" required></label>'
            '<div class="actions wide"><button type="submit" class="button primary">Prepare the queue</button><button type="button" class="button secondary" id="run-desk-download" disabled>Download task list</button></div></form>'
            '<p id="run-desk-message" class="form-status" role="status" aria-live="polite">Choose task files and limits for the worker you control.</p>'
            '<details open><summary>Review the command to run on your worker</summary><pre id="run-desk-command" tabindex="0"></pre><p>Save <code>baltor-tasks.txt</code> in your checkout. Follow the <a href="/setup">worker setup</a> before starting. Use Ctrl+C in the worker terminal to interrupt its owned process group.</p></details>'
            '<details><summary>Read the worker’s status without dispatch</summary><pre id="run-desk-status-command" tabindex="0"></pre><p>Save the command’s JSON output as a status file. Reuse exactly the same task paths, bytes and limits.</p></details></section>'
            '<aside class="desk-aside"><p class="eyebrow">Before dispatch</p><h2>Check the handoff.</h2><ul class="check-list"><li>The task says which inputs and changes are permitted.</li><li>You have checked its prerequisites.</li><li>The output has an explicit acceptance check.</li><li>Your provider has appropriate spending controls.</li><li>You have tried one short task first.</li></ul>'
            '<hr><h3>What this queue does</h3><p>Runs a fixed-order task list. Preserves call reservations, the original deadline and uncertain outcomes.</p><h3>What it does not do</h3><p>Automatically resolve dependencies, learn priorities or provide a hosted worker. Do not queue a dependent task before its prerequisite output is checked.</p>'
            + _link('/help#dependencies', 'Understand task dependencies →', 'text-link') + '</aside></div>'
            '<section id="report" class="report-panel"><p class="eyebrow">02 / Review</p><h2>Bring back the attempt record.</h2><p>Import the JSON output of the worker’s <code>--status</code> command. No sample results are mixed with your record.</p>'
            '<label class="report-upload">Inspect a status report<input id="run-desk-report" type="file" accept="application/json,.json"></label>'
            '<p id="run-desk-summary" role="status" aria-live="polite">Choose a queue status report to inspect its attempts.</p>'
            '<div class="table-scroll"><table><caption>Recorded task attempts. A finished process still needs its output checked.</caption><thead><tr><th scope="col">Task</th><th scope="col">State</th><th scope="col">Calls reserved</th><th scope="col">Process exit</th></tr></thead><tbody id="run-desk-attempts"></tbody></table></div></section>'
            '<noscript><p class="notice">The run desk needs JavaScript. Follow the <a href="/setup">command-line setup guide</a> to prepare a manifest and inspect the worker directly.</p></noscript>')


def _setup():
    return (_intro('Worker setup', 'Run it where you have control.', 'Use a reviewed checkout and your own model access. The browser prepares files; the worker executes the tasks you authorize.')
            + '<div class="guide-layout"><ol class="setup-steps"><li><h2>Install the local tools</h2><p>Use a Linux, macOS or WSL worker with Python and Git. Keep the checkout because the queue is a repository tool.</p>'
            '<pre tabindex="0"><code>git clone https://github.com/alisonjieli-png/loop-engine.git\ncd loop-engine\npython3 -m venv .venv\n.venv/bin/python -m pip install -e .</code></pre></li>'
            '<li><h2>Configure your model access</h2><p>Choose an endpoint you can reach, including your own machine, network service or Ollama Cloud. A local worker does not require a local model download.</p>'
            '<pre tabindex="0"><code>.venv/bin/python -m loop_engine configure\n.venv/bin/python tools/overnight_queue.py --help</code></pre><p>Use the <a href="https://github.com/alisonjieli-png/loop-engine/blob/main/docs/guides/providers-and-keys.md">provider and credential guide</a>. Keep keys on the worker, not in task files or this website.</p></li>'
            '<li><h2>Write one short task</h2><p>State the objective, permitted inputs and changes, destination files, and checks for success. Do not include work whose prerequisite result still needs approval.</p><div class="task-spec"><span class="mono">A useful task file includes</span><ul><li>Objective and expected output</li><li>Allowed files and effects</li><li>Time and provider limits</li><li>Checks that determine acceptance</li></ul></div></li>'
            '<li><h2>Prepare and inspect the queue</h2><p>Enter the absolute task-file path in the run desk. Download the manifest, save it in your checkout, and inspect the generated command before running it.</p>'
            + _link('/plan', 'Open the run desk →', 'button primary') + '</li><li><h2>Review the result before leaving more work</h2><p>Check the worker’s status and output files. A finished process is not proof that the task succeeded. Preserve the original run folder for interrupted or uncertain work.</p></li></ol>'
            '<aside class="desk-aside"><h2>Before a longer run</h2><p>Use a new private run folder for newly authorized work. Keep the task files and manifest unchanged during a queue.</p><p>Call limits count reserved invocations, not tokens or dollars. They do not replace provider spending controls.</p><h3>Need to stop?</h3><p>Use Ctrl+C in the worker terminal. Inspect the recorded outcome before resuming. Do not repeat an uncertain external action.</p>'
            + _link(GUIDE, 'Full prerequisites and recovery guide ↗', 'text-link') + '</aside></div>')


def _help():
    return (_intro('Help and scope', 'Know what the queue will do.', 'The public preview exposes existing local tools. Its limits are part of the handoff.')
            + '<div class="help-list"><section id="dependencies"><h2>How do priorities and dependencies work?</h2><p>The current worker uses the order of the task manifest. It does not schedule a dependency graph or learn priorities from outcomes. Put only independently ready tasks in that list. Check a prerequisite result before creating or authorizing dependent work.</p><p>Customized task graphs and outcome-based ranking are product work, not active features of this preview. A task’s priority never grants permission to run it.</p></section>'
            '<section><h2>Does AgentAFK run a cloud worker for me?</h2><p>No. You run the queue on your own computer or cloud machine. Hosted execution and cloud supervision are not available from this site. Downloading a manifest does not start a worker or a schedule.</p></section>'
            '<section><h2>Can I use an inexpensive model?</h2><p>Use a supported configured provider that fits the task. Start with a short assignment and check its output. The queue does not guarantee task completion, lower spending or measured token savings.</p></section>'
            '<section><h2>What happens after an interruption?</h2><p>The worker retains its call reservation and original deadline. Failed or uncertain outcomes hold further dispatch. Inspect artifacts, provider records and external effects before following the explicit reconciliation steps in the worker guide.</p>'
            + _link(GUIDE + '#interrupted-and-unknown-work', 'Read recovery instructions ↗', 'text-link') + '</section>'
            '<section><h2>Why is the report file refused?</h2><p>Use the JSON output of the queue’s <code>--status</code> command, up to 4 MiB. The viewer accepts <code>overnight_queue_status/v2</code>. It refuses malformed records and reservations that exceed the recorded budget.</p></section>'
            '<section><h2>Where is my data saved?</h2><p>The site does not upload task paths or imported status files. Save your downloaded manifest yourself. Reloading the page clears the form. The worker’s output and state remain wherever you configured them on your machine.</p></section>'
            '<section><h2>Where can I get help?</h2><p>Check the <a href="/setup">setup steps</a> and <a href="/status">service connection</a>. Report a reproducible software problem in the <a href="https://github.com/alisonjieli-png/loop-engine/issues">public repository</a>. Do not post credentials, private task files or customer data.</p><p>Operated by Baltor.AI. Postal contact: 1428 Bryn Mawr St, Saxton, PA 16678, United States.</p></section></div>')


def _pricing():
    return (_intro('Public preview', 'Try the local tools for free.', 'The run desk, task manifest preparation and status report viewer require no account or subscription.')
            + '<section class="price-panel"><div><p class="eyebrow">Local overnight tools</p><p class="price">Free<span> Public preview</span></p>'
            + _link('/plan', 'Prepare a run ↗', 'button primary') + '</div><div><h2>You bring the worker and model access.</h2><p>Your provider and hosting costs remain yours. Queue call limits do not cap your provider bill.</p><p>Max subscriptions are not sold during this public preview. This site does not start a subscription or offer paid hosted execution.</p></div></section>')


def render(path, *, origin=ORIGIN, allow_loopback=False):
    """Render an admitted route without executing a task or reading user state."""
    validate_public_origin(origin, permit_loopback=allow_loopback)
    if not (allow_loopback and is_loopback_url(origin)) and (not origin.startswith('https://') or ':' in origin.split('://', 1)[1]):
        raise ValueError('AgentAFK requires an exact HTTPS public origin')
    if path.startswith(ASSET_PREFIX):
        name = path[len(ASSET_PREFIX):]
        return (_asset(name), ASSETS[name]) if name in ASSETS else None
    if path == '/robots.txt':
        return ('User-agent: *\nDisallow: /api/\nDisallow: /auth/\nDisallow: /oauth/\nSitemap: ' + origin + '/sitemap.xml\n').encode(), 'text/plain'
    if path == '/sitemap.xml':
        addresses = ('/', '/plan', '/setup', '/help', '/pricing', '/privacy', '/terms')
        return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + ''.join('<url><loc>' + escape(origin + address) + '</loc></url>' for address in addresses) + '</urlset>').encode(), 'application/xml'
    if path == '/llms.txt':
        return (f'# AgentAFK\n\nFree local overnight tools.\n\n- Prepare a manifest: {origin}/plan\n'
                f'- Worker setup: {origin}/setup\n- Scope and recovery: {origin}/help\n\n'
                'Browser preparation is passive. It does not start a worker or authorize effects. '
                'The current queue is fixed-order, not an adaptive dependency scheduler. '
                'Task paths and imported status files stay in the browser. '
                'Hosted execution and cloud supervision are unavailable.\n').encode(), 'text/plain'
    if path not in ROUTES:
        return None
    if path == '/':
        title, body = 'Local overnight tools', _home()
    elif path in ('/plan', '/run-desk'):
        title, body = 'Your run desk', _plan()
    elif path in ('/setup', '/connect'):
        title, body = 'Worker setup', _setup()
    elif path == '/pricing':
        title, body = 'Free public preview', _pricing()
    elif path in ('/privacy', '/terms'):
        title, body = ('Privacy' if path == '/privacy' else 'Terms'), _legal(path[1:])
    elif path == '/status':
        title, body = 'Service status', (_intro('Service status', 'Check this site’s connection.', 'This checks the shared service, not the state of your worker or tasks.')
                                      + '<section class="status-panel"><p data-service-status role="status" aria-live="polite">Checking service availability…</p><p>Local queues run on your own machine. Inspect them with the worker’s status command.</p>'
                                      + _link('/plan#report', 'Inspect a local report →', 'text-link') + '</section>')
    else:
        title, body = 'Help and scope', _help()
    css = _versioned(ASSET_PREFIX + 'site.css', _asset('site.css'))
    js = _versioned(ASSET_PREFIX + 'site.js', _asset('site.js'))
    mark = _versioned(ASSET_PREFIX + 'mark.svg', _asset('mark.svg'))
    scripts = f'<script defer src="{js}"></script>'
    if path in ('/plan', '/run-desk'):
        scripts += '<script type="module" src="' + _versioned('/assets/run-desk.js', read_packaged_asset('run-desk.js')) + '"></script>'
    nav = ''.join('<a href="' + href + '"' + (' aria-current="page"' if path == href else '') + '>' + label + '</a>'
                  for href, label in (('/plan', 'Run desk'), ('/setup', 'Setup'), ('/help', 'Help'), ('/pricing', 'Preview')))
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)} | AgentAFK</title><meta name="description" content="Prepare bounded local agent work with your own models. Keep call limits, task checkpoints and an attempt record.">'
            f'<link rel="canonical" href="{escape(origin + path, quote=True)}"><meta property="og:title" content="{escape(title, quote=True)} | AgentAFK">'
            f'<meta property="og:url" content="{escape(origin + path, quote=True)}"><meta name="theme-color" content="#171b2a"><link rel="icon" href="{mark}"><link rel="stylesheet" href="{css}">{scripts}</head>'
            '<body><a class="skip-link" href="#main">Skip to content</a><header class="site-header"><a class="brand" href="/" aria-label="AgentAFK home">'
            f'<img src="{mark}" width="32" height="32" alt=""><span>Agent<span class="brand-accent">AFK</span></span></a>'
            '<button class="menu-button" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button><nav id="site-nav" aria-label="Main navigation">'
            + nav + '</nav><a class="header-action" href="/plan">Prepare a run ↗</a></header><main id="main" tabindex="-1">' + body + '</main>'
            '<footer class="site-footer"><div><a class="brand" href="/">Agent<span class="brand-accent">AFK</span></a><p>Local work. Explicit limits.</p></div>'
            '<nav aria-label="Footer"><a href="/setup">Setup</a><a href="/help">Help</a><a href="/status">Status</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/assets/third-party-notices.txt">Open-source notices</a></nav>'
            '<p class="operator">Operated by Baltor.AI · 1428 Bryn Mawr St, Saxton, PA 16678</p></footer></body></html>')
    return html.encode('utf-8'), 'text/html'
