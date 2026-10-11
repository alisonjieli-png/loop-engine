"""The guide pages of two offerings: Use Agent Feeds at `/feeds/setup` and Harness Files at `/harness-files`.

Kind: pure rendering over packaged records and, for `/harness-files`, the counts of one catalogue view. The transport asks
`rendered` for a page after the pages it served before October 9, 2026. Nothing here reads a request, a credential or an
account, and nothing calls a model.

The owner, October 9, 2026: "we should also think about having dedicated hero pages, use cases, setup flow, for using
feeds, setting up custom feeds, harness + component files, and more we need to be super clear". Each page follows the
design brief's template: one promise and one action, use cases, numbered steps that say what the reader sees, the
questions people ask, and a closing action.

```text
/feeds/setup      Use Agent Feeds: collections, links per agent, formats, how often to read, troubleshooting
                  (every collection, source name, question and count read from feed_source_collections.json)
/harness-files    Harness Files: the kinds counted from the served view, how a harness gets a file (MCP, the REST
                  API, the folder it reads), the entry for each harness (from client-recipes.json and the same app
                  entries Get set up shows), use cases and questions
```

`/feeds/setup` is the same bytes on every request, so the edge serves it from the static export. `/harness-files` counts
the library the service serves now, like `/library`, so the edge passes it to the origin. The profile builder exports
per-agent settings to the customer's files. Hosting a private feed and scheduling collection remain separate capabilities.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape
import json

FEEDS_SETUP = "/feeds/setup"
HARNESS_FILES = "/harness-files"
ADDRESSES = (FEEDS_SETUP, HARNESS_FILES)
VIEWS = {FEEDS_SETUP: "feeds-setup", HARNESS_FILES: "harness-files"}
STYLESHEET = "/assets/offering-pages.css"
SCRIPT = "/assets/offering-pages.js"
#: The picture a shared link to each page shows (tools/render_share_cards.mjs) and the words that describe it.
CARDS = {FEEDS_SETUP: ("/assets/share-card-feeds.png", "Baltor Agent Feeds. Give your agent sources it can check."),
         HARNESS_FILES: ("/assets/share-card-harness-files.png", "Baltor Harness Files. Files your harness can pick up and use.")}


def share_card_head(address: str, alt: str) -> str:
    """The head tags of a page's own 1200 by 630 shared-link picture, which web_pages.with_page_head keeps."""
    return (f'<meta property="og:image" content="{escape(address, quote=True)}">\n<meta property="og:image:type" '
            'content="image/png">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" '
            f'content="630">\n<meta property="og:image:alt" content="{escape(alt, quote=True)}">\n')
#: The collections the use cases and examples name. A collection that leaves the directory fails the page's render.
USE_CASE_COLLECTIONS = ("coding-benchmarks", "model-cost", "mcp-services", "developer-releases", "hackathons",
                        "creative-engines")
EXAMPLE_COLLECTION = "coding-benchmarks"
AGENT_FEEDS = (("A coding agent", ("coding-benchmarks", "coding-agent-releases")),
               ("A research agent", ("research-papers", "retrieval-benchmarks")),
               ("A creative agent", ("creative-engines", "creative-mcp-servers")))
#: What each kind of harness file is, in a reader's words. A kind without a line here shows its label alone.
KIND_LINES = {
    "skill": ("Skills", "SKILL.md with its scripts, references and assets."),
    "instruction_file": ("Instruction files", "AGENTS.md, CLAUDE.md and other files a harness reads first."),
    "rules": ("Rules", "Project rules a harness applies to every step."),
    "subagent": ("Subagents", "Agent definitions a harness can hand a task to."),
    "command": ("Commands", "Slash commands and saved prompts."),
    "hook": ("Hooks", "Checks your harness runs itself, before or after a step."),
    "plugin_manifest": ("Plugin manifests", "Bundles of commands, agents and hooks."),
    "marketplace": ("Plugin marketplaces", "Lists a harness installs plugins from."),
    "protocol_server_configuration": ("MCP server settings", "Entries that connect a harness to an MCP server."),
    "harness_settings": ("Harness settings", "Settings files for a harness."),
    "contract_schema": ("Contract schemas", "What a step takes and returns, as a schema a check can read."),
    "code_module": ("Code modules", "Tested functions and modules a step can run."),
    "three_d_model": ("3D models", "Models with the script that builds them."),
    "template": ("Templates", "Starting files a step fills in."),
    "reference_image": ("Reference images", "Images a harness reads for guidance."),
    "mask": ("Masks", "Masks with their declared polarity."),
    "pose_layout": ("Pose layouts", "Keypoint layouts with their convention."),
    "cad_model": ("CAD models", "CAD files with their source."),
}
#: The kinds shown when the served view cannot be counted, so the page still says what the library holds.
DEFAULT_KINDS = ("skill", "instruction_file", "rules", "subagent", "command", "hook", "protocol_server_configuration",
                 "code_module", "contract_schema")
#: The folder each harness reads a skill from, as tools/install_selected_material.py places one.
SKILL_FOLDERS = (("Claude Code", ".claude/skills/"), ("Codex", ".agents/skills/"), ("OpenCode", ".opencode/skills/"),
                 ("Pi", ".pi/skills/"))
#: The three app entries of Get set up, for apps without a recipe tab: the same objects service.js writes
#: (`appConfigurations`), each holding a reference to the key and never a key. tools/test_offering_guides.py runs the
#: page script's own objects under Node and compares them with these.
APP_STEP_EFFECTS = "reads_fs, writes_fs, spawns_process, network"


def app_configurations(endpoint: str) -> dict:
    return {
        "cursor": {"mcpServers": {"baltor": {"url": endpoint, "headers": {
            "Authorization": "Bearer ${env:BALTOR_SERVICE_TOKEN}", "Baltor-Step-Effects": APP_STEP_EFFECTS}}}},
        "vscode": {"inputs": [{"type": "promptString", "id": "baltor-token", "description": "Baltor key", "password": True}],
                   "servers": {"baltor": {"type": "http", "url": endpoint, "headers": {
                       "Authorization": "Bearer ${input:baltor-token}", "Baltor-Step-Effects": APP_STEP_EFFECTS}}}},
        "gemini-cli": {"mcpServers": {"baltor": {"httpUrl": endpoint, "headers": {
            "Authorization": "Bearer ${BALTOR_SERVICE_TOKEN}", "Baltor-Step-Effects": APP_STEP_EFFECTS}}}},
    }


def handles(address: str) -> bool:
    return address in ADDRESSES


# --- Shared parts ------------------------------------------------------------------------------------------------------

def _origin() -> str:
    from . import web_pages
    from .model_directory_pages import canonical
    return canonical(web_pages.packaged_site_map(), "")


def _code(text: str, label: str, copy: bool = True) -> str:
    """A code block with a copy button the page script shows; without the script the text stays selectable."""
    button = (f'<button class="quiet og-copy" type="button" data-copy-code hidden>Copy</button>'
              f'<span class="og-copy-status" role="status" aria-live="polite"></span>') if copy else ""
    return (f'<div class="og-code"><pre class="md-code" tabindex="0" aria-label="{escape(label, quote=True)}">'
            f'{escape(text)}</pre>{button}</div>')


def _details(summary: str, body: str, ident: str = "") -> str:
    ident = f' id="{escape(ident, quote=True)}"' if ident else ""
    return f'<details class="og-detail"{ident}><summary>{summary}</summary><div class="og-detail-body">{body}</div></details>'


def _band(ident: str, title: str, body: str, *, quiet: bool = False, eyebrow: str = "", lead: str = "") -> str:
    eyebrow = f'<p class="eyebrow">{escape(eyebrow)}</p>' if eyebrow else ""
    lead = f'<p class="md-reading">{lead}</p>' if lead else ""
    return (f'<section class="md-band{" md-quiet" if quiet else ""}" id="{ident}" aria-labelledby="{ident}-title">'
            f'{eyebrow}<h2 id="{ident}-title">{escape(title)}</h2>{lead}{body}</section>')


def _closing(title: str, line: str, action: str, href: str) -> str:
    return ('<section class="md-band og-closing" aria-labelledby="og-closing-title"><div class="og-closing-row"><div>'
            f'<h2 id="og-closing-title">{escape(title)}</h2><p class="md-reading">{line}</p></div>'
            f'<a class="button primary" href="{href}">{escape(action)}</a></div></section>')


def _intro(eyebrow: str, title: str, labelled_by: str, lede: str, extra: str, actions: str, contents) -> str:
    from .model_directory_pages import contents as contents_nav
    return (f'<div class="md-band md-intro og-hero"><p class="eyebrow">{escape(eyebrow)}</p>'
            f'<h1 id="{labelled_by}">{escape(title)}</h1><p class="lede">{lede}</p>{extra}'
            f'<div class="md-actions">{actions}</div>{contents_nav(contents)}</div>')


# --- /feeds/setup ------------------------------------------------------------------------------------------------------

def _collections():
    from .feed_source_collections import directory
    data = directory()
    by_id = {item.id: item for item in data.collections}
    named = {*USE_CASE_COLLECTIONS, EXAMPLE_COLLECTION, *(identity for _who, ids in AGENT_FEEDS for identity in ids)}
    missing = sorted(named - set(by_id))
    if missing:
        raise ValueError("the feed directory no longer holds the collections this page names: " + ", ".join(missing))
    return data, by_id, {item.id: item for item in data.sources}


def feeds_setup_body() -> str:
    from .feed_source_collections import COLLECTION_PREFIX, render as render_collection
    data, by_id, sources = _collections()
    origin = _origin()
    groups = tuple(dict.fromkeys(item.group for item in data.collections))
    example = by_id[EXAMPLE_COLLECTION]
    link = origin + COLLECTION_PREFIX + example.id + ".md"
    intro = _intro(
        "Agent Feeds", "Give your agent sources it can check.", "feeds-setup-title",
        "Pick a decision, copy one link, and your agent reads the sources before it chooses. Public feeds need no "
        "account and no key.",
        '<p class="md-reading og-price"><strong>$9 a month.</strong> Free through December 31, 2026 (Eastern). '
        'No automatic charge; a paid subscription requires your explicit opt-in.</p>',
        '<a class="button primary" href="/feeds#source-collections">Choose a collection</a>'
        '<a class="lib-text-link" href="#steps">See the five steps</a>',
        (("use-cases", "Use cases"), ("steps", "Set up"), ("formats", "Formats"), ("troubleshooting", "Troubleshooting"),
         ("questions", "Questions")))
    cards = ""
    for identity in USE_CASE_COLLECTIONS:
        item = by_id[identity]
        names = ", ".join(escape(sources[source_id].name) for source_id in item.source_ids[:3])
        more = len(item.source_ids) - 3
        names += f" and {more} more" if more > 0 else ""
        cards += (f'<li class="og-card"><h3>{escape(item.title)}</h3><p>{escape(item.decision_question)}</p>'
                  f'<p class="og-meta">Sources: {names}</p><p class="og-links">'
                  f'<a href="/feeds#collection-{item.id}">Open the collection</a>'
                  f'<a href="{COLLECTION_PREFIX}{item.id}.md" aria-label="{escape(item.title, quote=True)} as Markdown">'
                  'Markdown link</a></p></li>')
    use_cases = _band("use-cases", "What your agent can decide with a feed", f'<ul class="og-grid og-grid-three">{cards}</ul>',
                      lead=f"{len(data.collections)} collections in {len(groups)} groups: "
                           + ", ".join(escape(group) for group in groups) + ". Six of them, with the question each answers:")
    instruction = (f"Before choosing a coding model, read {link} and follow its decision checklist.")
    agents = "".join(f'<li><strong>{escape(who)}:</strong> '
                     + " and ".join(f'<a href="/feeds#collection-{identity}">{escape(by_id[identity].title)}</a>'
                                    for identity in ids) + "</li>" for who, ids in AGENT_FEEDS)
    etag = (f"ETAG=$(curl -sSI {link} | awk 'tolower($1)==\"etag:\"{{print $2}}' | tr -d '\\r')\n"
            f'curl -sS -o /dev/null -w "%{{http_code}}\\n" -H "If-None-Match: $ETAG" {link}')
    steps = (
        '<ol class="og-steps">'
        '<li><h3>Choose what each agent decides</h3><p>Open Feeds and pick one to three collections for each agent\'s job.</p>'
        f'<p class="og-see"><span>You see</span> {len(data.collections)} collections in {len(groups)} groups, each with its '
        'question, its sources and two links.</p></li>'
        '<li><h3>Copy the link in the format it reads</h3><p>Markdown suits instruction files and chat agents. JSON Feed '
        'suits scripts and tools.</p>'
        f'<p class="og-see"><span>You see</span> an address like <code>{escape(COLLECTION_PREFIX + example.id)}.md</code>.</p></li>'
        '<li><h3>Add the link to the agent\'s instructions</h3><p>One line in <code>AGENTS.md</code>, <code>CLAUDE.md</code> '
        'or your agent\'s own instructions file:</p>' + _code(instruction, "An instruction line that names a feed") + '</li>'
        '<li><h3>Give each agent only its feeds</h3><p>Each link stands alone, so different agents and different harnesses '
        'read different sources:</p><ul class="md-plain og-agents">' + agents + '</ul></li>'
        '<li><h3>Decide how often it reads</h3><p>Your harness owns scheduling; Baltor does not push. Once a day, or before '
        'each decision, is enough. Send the last <code>ETag</code> in <code>If-None-Match</code> and an unchanged feed '
        'answers 304 Not Modified:</p>' + _code(etag, "Read a feed only when it changed")
        + '<p class="og-see"><span>You see</span> <code>304</code> while the feed is unchanged. Each file names the date its '
        'sources were checked and a digest of the directory, so you can tell exactly what an agent read.</p></li></ol>'
        '<p class="md-reading"><a href="/feeds#feed-profile">Build a reading profile for each agent</a>: choose collections, '
        'include or exclude individual sources, and set a reading interval. Download the profile and instructions into '
        'that agent\'s project. Your harness owns the schedule and the saved files.</p>')
    steps = _band("steps", "Set it up in five steps", steps)
    served = render_collection(COLLECTION_PREFIX + example.id + ".md", origin)[0].decode("utf-8")
    excerpt = served[served.index("## " + example.title):served.index("\n\n[Browse Baltor Feeds]")].strip()
    rows = (("Markdown", f"{COLLECTION_PREFIX}{{collection}}.md", "Instruction files and chat agents: plain text an agent reads."),
            ("JSON Feed 1.1", f"{COLLECTION_PREFIX}{{collection}}.json",
             "Scripts and tools. The question, comparison fields and review trigger sit in its <code>_baltor</code> extension."),
            ("Every collection", "/feeds/sources.md and /feeds/sources.json", "One file with all of them."),
            ("Library updates", "/feeds/catalogue.json, .rss and .md",
             "The current state of the Harness Files library, for an agent that watches for changes. RSS suits a feed reader."))
    table = ('<div class="md-table-wrap"><table class="md-table og-table"><caption>Every feed address on this site</caption>'
             '<thead><tr><th scope="col">Format</th><th scope="col">Address</th><th scope="col">Best for</th></tr></thead><tbody>'
             + "".join(f'<tr><th scope="row">{name}</th><td>{escape(address)}</td><td>{use}</td></tr>'
                       for name, address, use in rows) + '</tbody></table></div>')
    formats = _band("formats", "Formats", table + _details(
        "What a collection looks like",
        f'<p class="md-reading">The section of <a href="{COLLECTION_PREFIX}{example.id}.md">{COLLECTION_PREFIX}{example.id}.md</a>'
        f' for one collection, as served:</p><pre class="md-code md-code-wrap" tabindex="0">{escape(excerpt)}</pre>'), quiet=True)
    problems = (
        ("The address answers 400", "Feed addresses take no query string. Remove everything after the question mark."),
        ("The address answers 503", "The library updates feed is refreshing, or a feed could not be read. Keep your last "
                                    "copy and try again in a minute. Collection files change only with Baltor releases."),
        ("Every read answers 304", "Nothing changed since the ETag your agent sent. Keep the copy it has."),
        ("My agent ignores the link", "Some harnesses ask before they read a web address, and some cannot read the web. "
                                      "Allow reads of baltor.ai, or save the file in the project and point the agent at it."),
        ("The sources look out of date", "Each file names the date its sources were checked. Updates follow Baltor releases, "
                                         "and no daily refresh is promised. Your agent can still open each source for its "
                                         "current state."))
    questions = (
        ("Is it free?", "Yes, through December 31, 2026 (Eastern). The standard price is $9 a month, and nothing is "
                        "charged automatically."),
        ("Do I need an account?", "No. Public feeds are open to anyone and need no key."),
        ("Can agents read different feeds?", "Yes. Each link stands alone, so each agent or harness gets its own."),
        ("How fresh is it?", "Sources are checked on the date each file shows. Updates follow Baltor releases; no daily "
                             "refresh is promised."),
        ("Does a feed run anything?", "No. A feed never installs or runs its contents, and reading a source does not grant "
                                      "permission to copy it."))
    help_band = ('<section class="md-band og-two" aria-label="Troubleshooting and questions">'
                 '<div id="troubleshooting"><h2 id="troubleshooting-title">Troubleshooting</h2>'
                 + "".join(_details(escape(name), f"<p>{escape(text)}</p>") for name, text in problems)
                 + '</div><div id="questions"><h2 id="questions-title">Questions</h2>'
                 + "".join(_details(escape(name), f"<p>{escape(text)}</p>") for name, text in questions)
                 + "</div></section>")
    closing = _closing("Pick the first decision for your agent",
                       f"{len(data.collections)} collections, free through December 31, 2026 (Eastern).",
                       "Choose a collection", "/feeds#source-collections")
    return intro + use_cases + steps + formats + help_band + closing


# --- /harness-files ----------------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _recipes() -> dict:
    from importlib.resources import files
    path = files("loop_engine").joinpath("core", "service_runtime", "web_assets", "client-recipes.json")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("record_type") != "website_client_recipes/v2":
        raise ValueError("this page reads website_client_recipes/v2")
    return {recipe["id"]: recipe for recipe in record["recipes"]}


def _filled(value, endpoint):
    if value == "{{ENDPOINT}}":
        return endpoint
    if isinstance(value, list):
        return [_filled(item, endpoint) for item in value]
    if isinstance(value, dict):
        return {key: _filled(item, endpoint) for key, item in value.items()}
    return value


def _toml_key(key: str) -> str:
    import re
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else json.dumps(key)


def _toml(table: dict, path=()) -> str:
    """The TOML text Get set up writes for a recipe (service.js `tomlText`), for the tables a recipe holds."""
    own = [_toml_key(key) + " = " + json.dumps(item, ensure_ascii=False) for key, item in table.items()
           if not isinstance(item, dict)]
    blocks = [("[" + ".".join(_toml_key(part) for part in path) + "]\n" if path else "") + "\n".join(own)] if own else []
    blocks += [_toml(item, (*path, key)) for key, item in table.items() if isinstance(item, dict)]
    return "\n\n".join(blocks)


def recipe_text(recipe: dict, endpoint: str) -> str:
    """A recipe's configuration with this service's address, as Get set up shows it (service.js `configurationText`)."""
    configuration = _filled(recipe["configuration"], endpoint)
    return _toml(configuration) if recipe["format"] == "toml" else json.dumps(configuration, indent=2, ensure_ascii=False)


def _kinds(counts, total_items, files_text) -> str:
    from .catalogue_attributes import harness_kind_label
    rows = counts or [(kind, None) for kind in DEFAULT_KINDS]
    cards = ""
    for kind, count in rows:
        name, line = KIND_LINES.get(kind, (harness_kind_label(kind), ""))
        shown = f"{count:,} item{'' if count == 1 else 's'}" if isinstance(count, int) else "Not measured"
        cards += (f'<li class="og-kind" data-harness-kind="{escape(kind, quote=True)}"><h3>{escape(name)}</h3>'
                  f'<p>{escape(line)}</p><p class="og-count">{shown}</p></li>')
    total = (f"In all, {total_items:,} items holding {files_text} distinct files. One item can hold several files, and "
             "identical files count once." if isinstance(total_items, int) and counts else
             "The counts are not measured on this page right now. The library page shows the current total.")
    return (f'<ul class="og-grid og-grid-four og-kinds">{cards}</ul><p class="md-reading og-total" data-kind-total>{total}</p>'
            '<p class="og-links"><a href="/library">See the library</a><a href="/gallery">See creative files with previews</a></p>')


def _harness_entries(origin: str) -> str:
    endpoint = origin + "/mcp"
    recipes, apps = _recipes(), app_configurations(endpoint)

    def key_note(variable_note):
        return (f'<p class="md-reading">{variable_note} The entry names the variable <code>BALTOR_SERVICE_TOKEN</code>, '
                'never your key.</p>')
    entries = [
        ("claude-code", "Claude Code", ".mcp.json or OAuth",
         '<p class="md-reading">Sign in with OAuth: run these two commands in your project folder. The second one opens '
         'the Baltor sign-in page in your browser.</p>'
         + _code(f"claude mcp add --transport http baltor {endpoint}\nclaude mcp login baltor", "Claude Code OAuth commands")
         + '<p class="md-reading">Or use a Baltor key: create <code>.mcp.json</code> in your project folder.</p>'
         + _code(recipe_text(recipes["claude-code"], endpoint), "Claude Code configuration")
         + f'<p class="og-check">Check it: <code>{escape(recipes["claude-code"]["verification_command"])}</code>. '
           '<a href="/docs/quickstart-claude-code">Read the Claude Code quickstart</a></p>'),
        ("claude", "Claude on the web and Claude Desktop", "a custom connector",
         f'<p class="md-reading">In Claude, add a custom connector with the address <code>{escape(endpoint)}</code>. '
         'When Claude asks, sign in to Baltor, check the permissions and allow the connection. There is no key to copy.</p>'
         '<p class="og-check"><a href="/docs/serving-and-connections#oauth-connections">How OAuth connections work</a></p>'),
        ("cursor", "Cursor", ".cursor/mcp.json",
         '<p class="md-reading">Add this entry to <code>.cursor/mcp.json</code> in your project, or to '
         '<code>~/.cursor/mcp.json</code> for every project. Start Cursor from a terminal where '
         '<code>BALTOR_SERVICE_TOKEN</code> is set.</p>'
         + _code(json.dumps(apps["cursor"], indent=2), "Cursor configuration")
         + '<p class="og-check">Check it in Cursor Settings under MCP, or run <code>agent mcp list</code> with the Cursor '
           'CLI. Baltor also accepts OAuth sign-in from Cursor.</p>'),
        ("vscode", "VS Code", ".vscode/mcp.json",
         '<p class="md-reading">Add this to <code>.vscode/mcp.json</code> in your workspace. VS Code asks for your Baltor '
         'key once and keeps it in its own secret storage.</p>'
         + _code(json.dumps(apps["vscode"], indent=2), "VS Code configuration")
         + '<p class="og-check">Check it with MCP: List Servers in the Command Palette. Baltor also accepts OAuth sign-in '
           'from VS Code.</p>'),
        ("codex", "Codex", "config.toml or OAuth",
         '<p class="md-reading">Merge this table into your existing <code>config.toml</code>.</p>'
         + _code(recipe_text(recipes["codex"], endpoint), "Codex configuration")
         + f'<p class="og-check">Check it: <code>{escape(recipes["codex"]["verification_command"])}</code>. To sign in with '
           f'OAuth instead, run <code>codex mcp add baltor --url {escape(endpoint)}</code> and then '
           '<code>codex mcp login baltor</code>. <a href="/docs/quickstart-codex">Read the Codex quickstart</a></p>'),
        ("opencode", "OpenCode", "opencode.json or OAuth",
         '<p class="md-reading">Merge the <code>baltor</code> entry into the <code>mcp</code> section of your existing '
         '<code>opencode.json</code>.</p>'
         + _code(recipe_text(recipes["opencode"], endpoint), "OpenCode configuration")
         + f'<p class="og-check">Check it: <code>{escape(recipes["opencode"]["verification_command"])}</code>. To sign in with '
           'OAuth instead, leave out the Authorization header and the <code>oauth</code> setting, then run '
           '<code>opencode mcp auth baltor</code>. <a href="/docs/quickstart-opencode">Read the OpenCode quickstart</a></p>'),
        ("gemini-cli", "Gemini CLI", ".gemini/settings.json",
         '<p class="md-reading">Add this entry to <code>.gemini/settings.json</code> in your project, or to '
         '<code>~/.gemini/settings.json</code>. Start Gemini CLI from a terminal where <code>BALTOR_SERVICE_TOKEN</code> '
         'is set.</p>' + _code(json.dumps(apps["gemini-cli"], indent=2), "Gemini CLI configuration")
         + '<p class="og-check">Check it: <code>gemini mcp list</code>.</p>'),
        ("pi", "Pi", "a Pi extension or native MCP",
         '<p class="md-reading">Pi 0.99.2 connects through its own MCP support and signs in with '
         '<code>pi mcp login baltor</code>. Pi 0.73.1 uses the Baltor extension.</p>'
         '<p class="og-check"><a href="/docs/quickstart-pi">Read the Pi quickstart</a></p>'),
    ]
    items = "".join(_details(f'<strong>{escape(name)}</strong><span>{escape(where)}</span>', body, "harness-" + ident)
                    for ident, name, where, body in entries)
    return (f'<p class="md-reading">One entry in your harness, with a Baltor key from your '
            f'<a href="/account#account-keys">account page</a> or an OAuth sign-in where the app offers one. The address '
            f'is <code>{escape(endpoint)}</code>. None of these settings holds your key or your model key.</p>'
            f'<div class="og-harnesses">{items}</div>'
            '<p class="md-reading">Any other app that speaks MCP over Streamable HTTP connects the same way. '
            '<a href="/setup">Get set up</a> has every entry with a copy button and a connection check.</p>')


def harness_files_body(summary=None) -> str:
    """The page from one view's counts. `summary` is `library_page.kind_summary(view)`, or None when nothing is counted."""
    origin = _origin()
    counts = list(summary["kinds"]) if summary else []
    total_items = summary["items"] if summary else None
    files = summary.get("distinct_files") if summary else None
    files_text = f"{files:,}" if isinstance(files, int) else "Not measured"
    from .web_site_map import load_layout_standard
    price = str(load_layout_standard().price.get("phrase") or "")
    intro = _intro(
        "Harness Files", "Files your harness can pick up and use.", "harness-files-title",
        f'Skills, instruction files, tools, hooks and settings, from a library of <span data-library-file-count>{files_text}'
        '</span> files. Your harness downloads the exact version a step needs, with its checksum.',
        f'<p class="md-reading og-price"><strong>Pro, {escape(price)}.</strong> Bring your own '
        'harness and model access. Cancel any time from your account page.</p>' if price else "",
        '<a class="button primary" href="/get-started">Get started</a><a class="lib-text-link" href="/setup">Get set up</a>',
        (("kinds", "What they are"), ("how", "How a harness gets them"), ("harnesses", "Set up your harness"),
         ("use-cases", "Use cases"), ("questions", "Questions")))
    kinds = _band("kinds", "Every kind of file a harness reads", _kinds(counts, total_items, files_text),
                  lead="Counted by kind from the library Baltor serves now.")
    tree = ("project/\n├── CLAUDE.md\n├── .claude/skills/find-duplicates/SKILL.md\n├── .mcp.json\n"
            "└── .baltor/step.lock.json")
    folders = "".join(f"<tr><th scope=\"row\">{escape(name)}</th><td>{escape(folder)}</td></tr>" for name, folder in SKILL_FOLDERS)
    how = ('<ul class="og-grid og-grid-three og-ways">'
           '<li class="og-card"><p class="eyebrow">MCP</p><h3>Search and download in your harness</h3><p>Your agent '
           'searches with <code>intelligence_search</code>, reads an item\'s file list with <code>provisioning_manifest</code> '
           'and downloads the exact files with <code>provisioning_read</code>. Every file names its SHA-256 checksum.</p>'
           f'<p class="og-meta"><code>{escape(origin)}/mcp</code></p></li>'
           '<li class="og-card"><p class="eyebrow">REST API</p><h3>Call it from a script</h3><p><code>POST /api/v1/retrieval'
           '</code> searches and <code>POST /api/v1/download</code> returns the exact bytes. Send your Baltor key in the '
           'Authorization header.</p><p class="og-links"><a href="/docs/searching-and-retrieving">Read the search and '
           'download guide</a></p></li>'
           '<li class="og-card"><p class="eyebrow">Placement</p><h3>In the folder your harness reads</h3><p>The Baltor '
           'library skill writes the exact bytes and checks each checksum, so no model retypes a file.</p>'
           '<div class="md-table-wrap"><table class="md-table og-table og-folders"><caption>Where each harness reads a skill'
           '</caption><tbody>' + folders + '</tbody></table></div></li></ul>'
           '<div class="og-tree"><p class="og-meta">Example layout: one step\'s folder</p>'
           f'<pre class="md-code" tabindex="0" aria-label="An example folder for one step">{escape(tree)}</pre></div>')
    how = _band("how", "How a harness gets them", how, quiet=True)
    harnesses = _band("harnesses", "Set up your harness", _harness_entries(origin))
    uses = (("Clean a customer file in five steps", "Each step searches, chooses one item and downloads it.", "/demo",
             "See the five steps"),
            ("From the metric to the submission", "A Kaggle competition in six steps, with the files each one used.",
             "/demo/kaggle", "See the Kaggle steps"),
            ("Run a small model with the files it needs", "Pi and Gemma 4 on Ollama Cloud, from search to use.",
             "/case-studies/pi-and-gemma-4", "Read the case study"),
            ("Free files for public-benefit work", "Public Good files are free with an account, no paid plan.",
             "/public-good", "Explore Public Good"),
            ("Creative files you can see first", "Godot shaders, textures, meshes and Blender tools, each with a recorded "
                                                 "render.", "/gallery", "Open the gallery"))
    cards = "".join(f'<li class="og-card"><h3>{escape(title)}</h3><p>{escape(text)}</p><p class="og-links">'
                    f'<a href="{href}">{escape(label)}</a></p></li>' for title, text, href, label in uses)
    use_cases = _band("use-cases", "Use cases", f'<ul class="og-grid og-grid-three">{cards}</ul>', quiet=True)
    questions = (
        ("What counts as a download?", "One item at the version you chose counts once a month. A search, a second look at "
                                       "the same result and a refused download are not downloads."),
        ("Do I need a model key?", "No. Baltor never asks for a model key. Your harness keeps using your own model access."),
        ("Can files run commands?", "Only if your harness lets them. An item that declares effects, such as running "
                                    "commands, says so in its results, and your harness's Baltor-Step-Effects setting "
                                    "decides whether its download is allowed."),
        ("What if a file is withdrawn?", "A withdrawn item is not served again, and the library page lists it with its "
                                         "note. Files you already downloaded stay with you."),
        ("Can I cancel?", "Any time, from your account page."))
    questions = _band("questions", "Questions", "".join(_details(escape(name), f"<p>{escape(text)}</p>")
                                                       for name, text in questions))
    closing = _closing("Give your harness the whole library", f"Pro, {escape(price)}.",
                       "Get started", "/get-started")
    return intro + kinds + how + harnesses + use_cases + questions + closing


# --- Pages -------------------------------------------------------------------------------------------------------------

def _page(site_map, display_name: str, address: str, body: str) -> str:
    from .model_directory_pages import SCHEMA_CONTEXT, Page, breadcrumbs, canonical, frame
    entry = site_map.page(address)
    if entry is None:
        raise ValueError(f"the site map does not list {address}")
    trail = (("Home", "/"), ("Feeds", "/feeds"), (entry.title, address)) if address == FEEDS_SETUP \
        else (("Home", "/"), (entry.title, address))
    structured = {"@context": SCHEMA_CONTEXT, "@type": "WebPage", "name": entry.title, "url": canonical(site_map, address),
                  "description": entry.description, "breadcrumb": breadcrumbs(site_map, trail)}
    labelled = "feeds-setup-title" if address == FEEDS_SETUP else "harness-files-title"
    page = frame(site_map, display_name, Page(address, VIEWS[address], entry.title, entry.description, body, structured,
                                              labelled))
    card, alt = CARDS[address]
    return page.replace("</head>", f'<link rel="stylesheet" href="{STYLESHEET}">\n<script defer src="{SCRIPT}"></script>\n'
                                   + share_card_head(canonical(site_map, card), alt) + "</head>", 1)


@lru_cache(maxsize=4)
def _feeds_setup(display_name: str) -> bytes:
    from .web_site_map import load_site_map
    return _page(load_site_map(), display_name, FEEDS_SETUP, feeds_setup_body()).encode("utf-8")


@lru_cache(maxsize=8)
def _harness_files(display_name: str, kinds: tuple, items, distinct_files) -> bytes:
    from .web_site_map import load_site_map
    summary = None if items is None else {"kinds": kinds, "items": items, "distinct_files": distinct_files}
    return _page(load_site_map(), display_name, HARNESS_FILES, harness_files_body(summary)).encode("utf-8")


def harness_files_page(display_name: str, summary=None) -> bytes:
    """The page for one view's counts, rendered once for each served catalogue."""
    if not summary:
        return _harness_files(display_name, (), None, None)
    return _harness_files(display_name, tuple(summary["kinds"]), summary["items"], summary.get("distinct_files"))


def rendered(path: str, method: str, display_name: str, host: "str | None" = None, view=None):
    """`(body, media_type)` for a guide page, or None for any other address or method.

    `/harness-files` counts `view`, the catalogue the service serves now; without one (a check, the static export) it
    says the counts are not measured rather than guessing them."""
    from . import web_pages
    if method not in ("GET", "HEAD") or not handles(path):
        return None
    if path == FEEDS_SETUP:
        body = _feeds_setup(display_name)
    else:
        from .library_page import kind_summary
        body = harness_files_page(display_name, kind_summary(view) if view is not None else None)
    head = web_pages.page_head(web_pages.packaged_site_map(), path, host, display_name)
    if head is not None:
        body = web_pages.with_page_head(body, head)
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE
