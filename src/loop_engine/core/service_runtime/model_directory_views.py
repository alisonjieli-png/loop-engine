"""The detail pages of the model directory, the endpoint directory and the can-I-run page.

Kind: pure rendering functions, called by `model_directory_pages.render`. Every fact is written with
its source and the day it was read; a price older than the stale limit says so beside its date; an
estimate says it is one and shows its formula; a fact no source states is written "Unknown".
"""
from __future__ import annotations

from html import escape

from . import model_directory as records
from . import model_directory_fit as fit
from . import model_directory_format as fmt
from .model_directory_pages import (LISTING, SCHEMA_CONTEXT, breadcrumbs, canonical, commercial_link, contents, disclosure,
                                    frame, Page, today)
from .model_directory_setup import api_address, setups, variable

STYLE_NAMES = {records.API_OPENAI_CHAT: "OpenAI Chat Completions", records.API_OPENAI_RESPONSES: "OpenAI Responses",
               records.API_ANTHROPIC_MESSAGES: "Anthropic Messages", records.API_NATIVE: "Native API"}
FACT_NAMES = (("released", "Released"), ("licence", "Licence"), ("open_weights", "Open weights"), ("parameters", "Parameters"),
              ("active_parameters", "Active parameters"), ("knowledge_cutoff", "Knowledge cutoff"))
LIST_FACT_NAMES = (("context", "Context window"), ("max_output", "Longest output"), ("tool_calling", "Tool calling"),
                   ("structured_output", "Structured output"), ("reasoning", "Reasoning controls"))
FIT_CONTEXTS = (8192, 32768)


def _yes(value) -> str:
    return "Yes" if value is True else "No" if value is False else fmt.UNKNOWN


def _fact_text(name: str, value) -> str:
    if name in ("parameters", "active_parameters"):
        return fmt.parameters(value)
    if name in ("context", "max_output"):
        return fmt.tokens(value) + (" tokens" if isinstance(value, int) else "")
    if isinstance(value, bool):
        return _yes(value)
    return str(value) if value not in (None, "") else fmt.UNKNOWN


def _fact_rows(row: dict) -> str:
    items = []
    facts = row["facts"]
    for name, label in FACT_NAMES:
        fact = facts.get(name)
        if fact is None:
            items.append(f"<div><dt>{label}</dt><dd>{fmt.UNKNOWN}</dd></div>")
            continue
        extra = ' <span class="md-estimate">estimate</span>' if fact.get("estimate") else ""
        value = escape(_fact_text(name, fact.get("value")))
        if name == "licence" and fact.get("link"):
            value = fmt.link(fact["link"], _fact_text(name, fact.get("value")))
        items.append(f'<div><dt>{label}</dt><dd><span{LISTING if name == "licence" else ""}>{value}</span>{extra} '
                     f'<span class="md-basis">{escape(fact.get("basis", ""))}</span> {fmt.cite(row, fact["source"])}</dd></div>')
    for name, label in LIST_FACT_NAMES:
        values = facts.get(name)
        if not values:
            items.append(f"<div><dt>{label}</dt><dd>{fmt.UNKNOWN}</dd></div>")
            continue
        parts = "".join(f'<li>{escape(_fact_text(name, item.get("value")))} <span class="md-basis">{escape(item.get("basis", ""))}</span> '
                        f'{fmt.cite(row, item["source"])}</li>' for item in values)
        items.append(f'<div><dt>{label}</dt><dd><ul class="md-plain">{parts}</ul></dd></div>')
    modalities = facts.get("modalities")
    text = (f'{", ".join(modalities.get("input") or [])} in, {", ".join(modalities.get("output") or [])} out '
            f'{fmt.cite(row, modalities["source"])}') if modalities else fmt.UNKNOWN
    items.append(f"<div><dt>Inputs and outputs</dt><dd>{text}</dd></div>")
    uses = "".join(f'<li>{escape(item["value"].capitalize())}: <span class="md-basis">{escape(item.get("basis", ""))}</span> '
                   f'{fmt.cite(row, item["source"])}</li>' for item in row["use_cases"])
    items.append(f'<div><dt>Good for</dt><dd>{f"<ul class=md-plain>{uses}</ul>" if uses else "No source names a use."}</dd></div>')
    return '<dl class="md-dl">' + "".join(items) + "</dl>"


def _price_table(row: dict, day: str, directory) -> str:
    if not row["prices"]:
        return '<p class="md-reading">No source lists a price for this model. It may only run on your own hardware.</p>'
    lines = []
    for price in sorted(row["prices"], key=lambda item: (item["input"], item["output"], item["provider"], item["route"])):
        stale = records.price_is_stale(price, day)
        route = "direct" if price["route"] == records.ROUTE_DIRECT else "through OpenRouter"
        endpoint = price["provider_slug"] if price["route"] == records.ROUTE_DIRECT else "openrouter"
        provider = (f'<a href="/endpoints/{escape(endpoint)}"{LISTING}>{escape(price["provider"])}</a>' if directory.endpoint(endpoint)
                    else f'<span{LISTING}>{escape(price["provider"])}</span>')
        when = (f'<time datetime="{price["as_of"]}">{price["as_of"]}</time>'
                + (f' <span class="md-stale">older than {records.STALE_PRICE_DAYS} days; check the provider</span>' if stale else ""))
        lines.append(f'<tr><th scope="row">{provider} <span class="md-basis">{route}</span></th>'
                     f'<td>{escape(fmt.price(price["input"]))}</td><td>{escape(fmt.price(price["output"]))}</td>'
                     f'<td>{escape(fmt.tokens(price.get("context")))}</td><td>{when}</td><td>{fmt.cite(row, price["source"])}</td></tr>')
    return ('<div class="md-table-wrap"><table class="md-table"><caption>Prices in US dollars per million tokens, as each source lists them</caption>'
            '<thead><tr><th scope="col">Provider</th><th scope="col">Input</th><th scope="col">Output</th><th scope="col">Context</th>'
            '<th scope="col">As of</th><th scope="col">Source</th></tr></thead><tbody>' + "".join(lines) + "</tbody></table></div>")


def architecture_of(row: dict) -> fit.Architecture:
    fact = row["facts"].get("architecture") or {}
    context = fact.get("max_context") or fmt.largest(row, "context") or 0
    try:
        return fit.Architecture(fact.get("layers") or 0, fact.get("kv_heads") or 0, fact.get("head_dim") or 0,
                                fact.get("attention") or fit.ATTENTION_UNKNOWN, fact.get("latent_width") or 0, context)
    except fit.FitError:
        return fit.Architecture(max_context=context if isinstance(context, int) else 0)


def weights_of(row: dict) -> list:
    """(name, bytes, repository, estimated) for each quantization, or estimates from the parameter count."""
    listed = [(item["name"], item["bytes"], item["repository"], False) for item in row["quantizations"]]
    parameters = fmt.fact_value(row, "parameters")
    if listed or not isinstance(parameters, int) or parameters <= 0:
        return listed
    return [(name, fit.estimated_weight_bytes(parameters, bits), "", True) for name, bits in fit.ESTIMATE_BITS]


def _local_band(row: dict, directory) -> str:
    architecture = architecture_of(row)
    weights = weights_of(row)
    if not weights:
        return ('<div class="md-band" id="local" aria-labelledby="local-title"><h2 id="local-title">Run it on your own hardware</h2>'
                '<p class="md-reading">No source lists weight files or a parameter count for this model, so its memory needs are Unknown.</p></div>')
    header = "".join(f'<th scope="col">Memory at {context:,} tokens</th>' for context in FIT_CONTEXTS)
    lines = []
    for name, size, repository, estimated in weights:
        cells = []
        for context in FIT_CONTEXTS:
            if architecture.max_context and context > architecture.max_context:
                cells.append("<td>Beyond its context</td>")
                continue
            estimate = fit.memory_estimate(size, architecture, context)
            cells.append(f"<td>{escape(fmt.gib(estimate.total)) if estimate.total else 'Unknown: no KV cache numbers'}</td>")
        label = f'{escape(name)}{" <span class=md-estimate>estimate</span>" if estimated else ""}'
        lines.append(f"<tr><th scope=\"row\">{label}</th><td>{escape(fmt.gib(size))}</td>{''.join(cells)}</tr>")
    commands = _run_commands(row, directory)
    note = ("Weights are the sizes of the files a source lists, or an estimate from the parameter count where none does. "
            "Memory is an estimate: weights plus KV cache plus 512 MiB and 5 percent of the weights for runtime buffers.")
    return ('<div class="md-band" id="local" aria-labelledby="local-title"><h2 id="local-title">Run it on your own hardware</h2>'
            f'<p class="md-reading">{note} <a href="/can-i-run?model={escape(row["slug"])}">Check it against your hardware</a>.</p>'
            f'<div class="md-table-wrap"><table class="md-table"><thead><tr><th scope="col">Quantization</th><th scope="col">Weights</th>{header}</tr></thead>'
            f'<tbody>{"".join(lines)}</tbody></table></div>{commands}</div>')


def _run_commands(row: dict, directory) -> str:
    items = []
    gguf = next((item for item in row["quantizations"] if item["format"] == "gguf"), None)
    medium = next((item for item in row["quantizations"] if item["name"] in ("Q4_K_M", "Q4_K_S", "Q4_0")), gguf)
    identifier = row["ids"].get("huggingface")
    for endpoint in directory.endpoints:
        if endpoint["kind"] != records.ENDPOINT_LOCAL:
            continue
        run = endpoint["setup"].get("run") or {}
        command = run.get("command", "")
        if run.get("format") == "gguf" and medium:
            text = command.replace("{repository}", medium["repository"]).replace("{quantization}", medium["name"])
        elif run.get("format") == "safetensors" and identifier and fmt.fact_value(row, "parameters"):
            text = command.replace("{huggingface_id}", identifier)
        else:
            continue
        items.append(f'<li><a href="/endpoints/{endpoint["slug"]}">{escape(endpoint["name"])}</a><pre class="md-code"><code>{escape(text)}</code></pre></li>')
    if not items:
        return '<p class="md-reading">No local runtime in this directory has a published file for this model.</p>'
    return '<h3>Start it with a local runtime</h3><ul class="md-plain md-commands">' + "".join(items) + "</ul>"


def _routes(row: dict, directory) -> list:
    """(endpoint row, model identifier) for each way to reach the model, in a fixed order: the maker's own API, OpenRouter, local."""
    routes, seen = [], set()
    for price in sorted(row["prices"], key=lambda item: (item["route"] != records.ROUTE_DIRECT, item["provider_slug"])):
        slug = price["provider_slug"] if price["route"] == records.ROUTE_DIRECT else "openrouter"
        endpoint = directory.endpoint(slug)
        if endpoint is not None and slug not in seen:
            seen.add(slug)
            model_id = price["model_id"] if price["route"] == records.ROUTE_DIRECT else row["ids"].get("openrouter", price["model_id"])
            routes.append((endpoint, model_id))
    gguf = next((item for item in row["quantizations"] if item["name"] in ("Q4_K_M", "Q4_K_S", "Q4_0")), None)
    ollama = directory.endpoint("ollama")
    if gguf and ollama is not None:
        routes.append((ollama, "hf.co/" + gguf["repository"] + ":" + gguf["name"]))
    return routes


def _setup_band(row: dict, directory) -> str:
    routes = _routes(row, directory)
    if not routes:
        return ('<div class="md-band" id="harness" aria-labelledby="harness-title"><h2 id="harness-title">Use it from your harness</h2>'
                '<p class="md-reading">No endpoint in this directory serves this model yet.</p></div>')
    endpoint, model_id = routes[0]
    limits = {"context": fmt.largest(row, "context"), "output": fmt.largest(row, "max_output")}
    blocks = setup_blocks(endpoint, model_id, row["name"], directory, limits)
    others = "".join(f'<li><a href="/endpoints/{item["slug"]}">{escape(item["name"])}</a>, model <code{LISTING}>{escape(identifier)}</code></li>'
                     for item, identifier in routes[1:12])
    return ('<div class="md-band" id="harness" aria-labelledby="harness-title"><h2 id="harness-title">Use it from your harness</h2>'
            f'<p class="md-reading">Set up for <a href="/endpoints/{endpoint["slug"]}">{escape(endpoint["name"])}</a> with the model '
            f'<code{LISTING}>{escape(model_id)}</code>. Each endpoint page has the same setup for its own address.</p>{blocks}'
            + (f'<h3>Other ways to reach it</h3><ul class="md-plain">{others}</ul>' if others else "") + "</div>")


def setup_blocks(endpoint: dict, model_id: str, model_name: str, directory, limits: "dict | None" = None) -> str:
    harnesses = directory_harnesses(directory)
    blocks = []
    for item in setups(endpoint, model_id, model_name, harnesses, limits):
        notes = "".join(f"<li>{escape(note)}</li>" for note in item.notes if note)
        source = (f'<p class="md-basis">From {fmt.link(item.source_address, item.harness_name + " documentation")}, read '
                  f'<time datetime="{item.source_read}">{item.source_read}</time>.</p>') if item.source_address else ""
        if item.text:
            body = (f'<p>Put this in {escape(item.location)}:</p><pre class="md-code"><code>{escape(item.text)}</code></pre>')
        else:
            body = f'<p>{escape(item.reason)}</p>'
        blocks.append(f'<details class="md-setup"{" open" if not blocks else ""}><summary>{escape(item.harness_name)}</summary>'
                      f'{body}{f"<ul class=md-plain>{notes}</ul>" if notes else ""}{source}</details>')
    return "".join(blocks)


def directory_harnesses(directory) -> list:
    return list(directory.harnesses)


def _benchmarks(row: dict) -> str:
    if not row["benchmarks"]:
        return ""
    items = "".join(f'<li>{fmt.link(item["address"], item["name"])}' + (f": {escape(str(item['value']))}" if "value" in item else "")
                    + f' <span class="md-basis">published by <span{LISTING}>{escape(item["publisher"])}</span></span> {fmt.cite(row, item["source"])}</li>'
                    for item in row["benchmarks"])
    return ('<div class="md-band" id="results" aria-labelledby="results-title"><h2 id="results-title">Published results</h2>'
            '<p class="md-reading">These are results other people published. Baltor did not run them and does not rank models by them.</p>'
            f'<ul class="md-plain">{items}</ul></div>')


def _row_sources(row: dict) -> str:
    items = "".join(f'<li><span{LISTING}>{fmt.link(item["address"], item["address"])}</span>, read <time datetime="{item["read"]}">{item["read"]}</time></li>'
                    for item in row["sources"])
    return ('<div class="md-band md-quiet" id="sources" aria-labelledby="sources-title"><h2 id="sources-title">Sources of this page</h2>'
            f'<ul class="md-plain md-sources">{items}</ul></div>')


def model_page(row: dict, directory, site_map, name: str) -> str:
    day = today()
    parameters, context = fmt.fact_value(row, "parameters"), fmt.largest(row, "context")
    licence = fmt.fact_value(row, "licence")
    summary = (f'{fmt.parameters(parameters)} parameters, a context window of {fmt.tokens(context)} tokens'
               f'{" and the licence " + str(licence) if licence else ", licence Unknown"}.')
    body = (f'<div class="md-band md-intro"><p class="eyebrow"><a href="/models">Models</a></p><h1 id="model-title"{LISTING}>{escape(row["name"])}</h1>'
            f'<p class="lede">By <span{LISTING}>{escape(row["maker"])}</span>. {escape(summary)}</p>'
            + contents((("facts", "Facts"), ("prices", "Prices"), ("local", "Run it yourself"), ("harness", "Use it from a harness"),
                        ("sources", "Sources")))
            + commercial_link(row) + "</div>"
            f'<div class="md-band" id="facts" aria-labelledby="facts-title"><h2 id="facts-title">Facts</h2>{_fact_rows(row)}</div>'
            f'<div class="md-band" id="prices" aria-labelledby="prices-title"><h2 id="prices-title">Prices</h2>{_price_table(row, day, directory)}</div>'
            + _local_band(row, directory) + _setup_band(row, directory) + _benchmarks(row) + _row_sources(row) + disclosure([row]))
    structured = {"@context": SCHEMA_CONTEXT, "@type": "SoftwareApplication", "name": row["name"], "applicationCategory": "Machine learning model",
                  "url": canonical(site_map, "/models/" + row["slug"]), "author": {"@type": "Organization", "name": row["maker"]},
                  "description": f'{row["name"]} by {row["maker"]}: {summary}',
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Models", "/models"), (row["name"], "/models/" + row["slug"])))}
    if licence:
        structured["license"] = str(licence)
    released = fmt.released(row)
    if released:
        structured["datePublished"] = released
    return frame(site_map, name, Page("/models/" + row["slug"], "model", row["name"],
                 f'{row["name"]} by {row["maker"]}: context window, prices with dates, licence, quantizations, hardware needs and harness setup.',
                 body, structured, "model-title"))


def _api_list(endpoint: dict) -> str:
    items = []
    for api in endpoint["apis"]:
        note = f' <span class="md-basis">{escape(api["note"])}</span>' if api.get("note") else ""
        items.append(f'<li>{escape(STYLE_NAMES[api["style"]])}: <code>{escape(api_address(api))}</code>{note} {fmt.cite(endpoint, api["source"])}</li>')
    return '<ul class="md-plain">' + "".join(items) + "</ul>"


def _endpoint_facts(endpoint: dict) -> str:
    facts = endpoint["facts"]
    lines = []
    auth = endpoint.get("auth")
    if auth:
        lines.append(f'<div><dt>Authentication</dt><dd>{escape(auth["header"])}, with the key in <code>{escape(variable(auth["variable"]))}</code> '
                     f'{fmt.cite(endpoint, auth["source"])}</dd></div>')
    for name, label in (("structured_output", "Structured output"), ("tool_calling", "Tool calling"), ("rate_limits", "Rate limits"),
                        ("pricing", "Prices"), ("data_policy", "Data retention"), ("documentation", "Documentation"),
                        ("observed_output_limits", "Output limits Baltor recorded")):
        fact = facts.get(name)
        if fact is None:
            lines.append(f"<div><dt>{label}</dt><dd>{fmt.UNKNOWN}</dd></div>")
            continue
        parts = []
        if "value" in fact and not isinstance(fact["value"], int):
            parts.append(escape(_yes(fact["value"]) if isinstance(fact["value"], bool) else str(fact["value"])))
        if fact.get("note"):
            parts.append(escape(fact["note"]))
        if fact.get("address"):
            parts.append(fmt.link(fact["address"], "Read the page"))
        lines.append(f'<div><dt>{label}</dt><dd>{" ".join(parts)} {fmt.cite(endpoint, fact["source"])}</dd></div>')
    return '<dl class="md-dl">' + "".join(lines) + "</dl>"


def _endpoint_models(endpoint: dict, day: str) -> str:
    if not endpoint["models"]:
        return ""
    lines = []
    for item in endpoint["models"][:400]:
        name = (f'<a href="/models/{escape(item["model_slug"])}"{LISTING}>{escape(item["name"])}</a>' if item.get("model_slug")
                else f'<span{LISTING}>{escape(item["name"])}</span>')
        stale = records.price_is_stale(item, day) if "input" in item else False
        lines.append(f'<tr><th scope="row">{name} <code{LISTING}>{escape(item["id"])}</code></th><td>{escape(fmt.price(item.get("input")))}</td>'
                     f'<td>{escape(fmt.price(item.get("output")))}</td><td>{escape(fmt.tokens(item.get("context")))}</td>'
                     f'<td><time datetime="{item["as_of"]}">{item["as_of"]}</time>{" <span class=md-stale>older than " + str(records.STALE_PRICE_DAYS) + " days</span>" if stale else ""}</td></tr>')
    first = endpoint["models"][0]["source"]
    return ('<div class="md-band" id="listed" aria-labelledby="listed-title"><h2 id="listed-title">Models it lists</h2>'
            f'<p class="md-reading">Prices in US dollars per million tokens, input and output, as {fmt.cite(endpoint, first)} records them.</p>'
            '<div class="md-table-wrap"><table class="md-table"><thead><tr><th scope="col">Model</th><th scope="col">Input</th>'
            '<th scope="col">Output</th><th scope="col">Context</th><th scope="col">As of</th></tr></thead><tbody>'
            + "".join(lines) + "</tbody></table></div></div>")


def endpoint_page(endpoint: dict, directory, site_map, name: str) -> str:
    local = endpoint["kind"] == records.ENDPOINT_LOCAL
    example = "<model>" if local or not endpoint["models"] else endpoint["models"][0]["id"]
    run = endpoint["setup"].get("run") or {}
    run_text = (f'<h3>Start it</h3><pre class="md-code"><code>{escape(run["command"])}</code></pre>'
                + (f'<p class="md-basis">{escape(run["note"])}</p>' if run.get("note") else "")) if run.get("command") else ""
    kind = "A local runtime you install and run on your own hardware." if local else "A hosted service with its own key and prices."
    body = (f'<div class="md-band md-intro"><p class="eyebrow"><a href="/endpoints">Endpoints</a></p><h1 id="endpoint-title"{LISTING}>{escape(endpoint["name"])}</h1>'
            f'<p class="lede">{kind} This page lists the addresses it answers, the facts its documentation states, and the setup of each harness.</p>'
            + contents((("api", "Addresses"), ("setup", "Harness setup"), ("sources", "Sources"))) + commercial_link(endpoint) + "</div>"
            f'<div class="md-band" id="api" aria-labelledby="api-title"><h2 id="api-title">Addresses and facts</h2>{_api_list(endpoint)}'
            f'{"" if local else _endpoint_facts(endpoint)}{run_text}</div>'
            f'<div class="md-band" id="setup" aria-labelledby="setup-title"><h2 id="setup-title">Harness setup</h2>'
            f'<p class="md-reading">Replace <code{LISTING}>{escape(example)}</code> with the model you want.</p>'
            f'{setup_blocks(endpoint, example, example, directory)}</div>'
            + _endpoint_models(endpoint, today()) + _row_sources(endpoint) + disclosure([endpoint]))
    structured = {"@context": SCHEMA_CONTEXT, "@type": "SoftwareApplication" if local else "WebAPI", "name": endpoint["name"],
                  "url": canonical(site_map, "/endpoints/" + endpoint["slug"]),
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Endpoints", "/endpoints"), (endpoint["name"], "/endpoints/" + endpoint["slug"])))}
    return frame(site_map, name, Page("/endpoints/" + endpoint["slug"], "endpoint", endpoint["name"],
                 f'{endpoint["name"]}: API addresses, authentication, structured output, tool calling, rate limits, data retention and setup for OpenCode, Pi, Codex and Claude Code.',
                 body, structured, "endpoint-title"))
