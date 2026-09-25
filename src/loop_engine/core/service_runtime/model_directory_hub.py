"""The endpoint directory page, the can-I-run page and the fit calculation they share with the browser.

Kind: pure rendering and calculation. `fit_results` answers the question the can-I-run page asks:
for one device, which models fit, with which quantization, at which context length, and how fast
they may run. The page's script repeats the same steps on the same numbers; a browser check holds
the two to the same answer for every hardware preset.

The calculation reads only the model's size, architecture and context facts. It never reads a
commercial relationship, and its order is by parameter count, then name.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape

from . import model_directory as records
from . import model_directory_fit as fit
from . import model_directory_format as fmt
from .model_directory_pages import (DEFAULT_CONTEXT, DEFAULT_PRESET, LISTING, RESULT_LENGTH, SCHEMA_CONTEXT, ads_band, breadcrumbs,
                                    canonical, commercial_link, contents, disclosure, frame, Page, paid_link_notice, sources_band)
from .model_directory_views import STYLE_NAMES, architecture_of


#: How the results of the hardware check are ordered, stated where they are shown.
FIT_ORDER_SENTENCE = ("Models that fit on the device come first, then models that also need computer memory; within each, the largest "
                      "models come first, by parameter count, then by name. For each model the check picks the largest quantization "
                      "that fits. Payment never changes the results.")
ENDPOINT_ORDER_SENTENCE = ("Services a person reviewed come first, in the order of the review, then the other services by name, then the local "
                           "runtimes. Payment never changes the order or which services are listed.")


@dataclass(frozen=True)
class FitResult:
    """The best quantization of one model that fits a device, and at which context."""

    slug: str
    name: str
    maker: str
    parameters: "int | None"
    quantization: str
    weights: float
    estimated: bool
    fit: fit.Fit
    speed: "tuple | None"


def device_from_preset(preset: dict, system: "dict | None" = None) -> fit.Device:
    system = system or {}
    return fit.Device(preset["kind"], float(preset["memory_gib"]), float(preset["usable_fraction"]),
                      float(preset.get("bandwidth_gbps") or 0), float(system.get("memory_gib") or 0),
                      float(system.get("bandwidth_gbps") or 0))


def fit_results(rows, device: fit.Device, minimum_context: int = DEFAULT_CONTEXT, use: str = "",
                kv_type: str = fit.DEFAULT_KV_TYPE) -> tuple:
    """(results that fit, count of models whose KV cache numbers are unknown)."""
    results, unknown = [], 0
    for row in rows:
        if use and use not in fmt.uses(row):
            continue
        outputs = (row["facts"].get("modalities") or {}).get("output") or []
        if outputs and "text" not in outputs:
            continue
        architecture = architecture_of(row)
        listed = {item["name"]: item["bytes"] for item in row["quantizations"]}
        weights = sorted(((name, size, "", estimated) for name, size, estimated in fit.compared_weights(listed, fmt.fact_value(row, "parameters"))),
                         key=lambda item: -item[1])
        if not weights:
            continue
        if not architecture.kv_known:
            unknown += 1
            continue
        chosen = None
        for wanted in (fit.FIT_DEVICE, fit.FIT_SPLIT):
            for name, size, _repository, estimated in weights:
                found = fit.best_fit(size, architecture, device, kv_type)
                if found.kind == wanted and found.context >= min(minimum_context, architecture.max_context or minimum_context):
                    chosen = (name, size, estimated, found)
                    break
            if chosen:
                break
        if chosen is None:
            continue
        name, size, estimated, found = chosen
        parameters = fmt.fact_value(row, "parameters")
        active = fmt.fact_value(row, "active_parameters")
        share = active / parameters if isinstance(active, int) and isinstance(parameters, int) and parameters > 0 else 1.0
        results.append(FitResult(row["slug"], row["name"], row["maker"], parameters if isinstance(parameters, int) else None,
                                 name, size, estimated, found, fit.speed_range(found, device, share)))
    results.sort(key=lambda item: (item.fit.kind != fit.FIT_DEVICE, -(item.parameters or 0), item.name.lower(), item.slug))
    return tuple(results), unknown


def _speed(result: FitResult) -> str:
    if result.speed is None:
        return "Unknown: enter the memory bandwidth"
    low, high = result.speed
    return f"{low:,.0f} to {high:,.0f} tokens a second (estimate)"


def result_rows(results) -> str:
    lines = []
    for result in results:
        where = "On the device" if result.fit.kind == fit.FIT_DEVICE else "Split with computer memory, slower"
        weights = fmt.gib(result.weights) + (" (estimate)" if result.estimated else "")
        lines.append(f'<tr><th scope="row"><a href="/models/{result.slug}"{LISTING}>{escape(result.name)}</a></th>'
                     f'<td>{escape(result.quantization)}</td><td>{escape(weights)}</td><td>{result.fit.context:,}</td>'
                     f'<td>{escape(fmt.gib(result.fit.estimate.total))}</td><td>{where}</td><td>{escape(_speed(result))}</td></tr>')
    return "".join(lines)


def _preset_options(hardware: dict, selected: str) -> str:
    groups: dict = {}
    for preset in hardware["presets"]:
        groups.setdefault(preset["group"], []).append(preset)
    return "".join(f'<optgroup label="{escape(group)}">' + "".join(
        f'<option value="{escape(item["id"])}"{" selected" if item["id"] == selected else ""}>{escape(item["name"])}</option>'
        for item in items) + "</optgroup>" for group, items in groups.items())


def can_i_run_page(directory, site_map, name: str) -> str:
    hardware = directory.hardware
    preset = next(item for item in hardware["presets"] if item["id"] == DEFAULT_PRESET)
    system = hardware["system_memory_default"]
    device = device_from_preset(preset, system)
    results, unknown = fit_results(directory.models, device)
    shown = results[:RESULT_LENGTH]
    context_options = "".join(f'<option value="{value}"{" selected" if value == DEFAULT_CONTEXT else ""}>{value:,} tokens</option>'
                              for value in fit.CONTEXT_STEPS[:8])
    use_options = "".join(f'<option value="{value}">{value.capitalize()}</option>' for value in records.USE_CASES)
    kv_options = "".join(f'<option value="{value}">{label}</option>' for value, label in
                         (("f16", "16-bit, the usual default"), ("q8_0", "8-bit (q8_0)"), ("q4_0", "4-bit (q4_0)")))
    formula = ("memory = weights + KV cache + overhead\n"
               "weights  = the size of the quantized files, or parameters x bits per weight / 8\n"
               "KV cache = 2 x layers x KV heads x head size x context x bytes per value\n"
               "overhead = 512 MiB + 5% of the weights (an estimate of runtime buffers)\n"
               "speed    = 50% to 80% of bandwidth / (active weights + KV cache), an estimate")
    sources = "".join(f'<li>{fmt.link(item["address"], item["id"].replace("_", " "))}, read {escape(item["read"])}</li>'
                      for item in hardware["sources"])
    browser = {key: hardware[key] for key in ("presets", "system_memory_default", "formula")}
    data = '<script type="application/json" id="md-hardware">' + json.dumps(browser, separators=(",", ":")).replace("<", "\\u003c") + "</script>"
    body = (data + '<div class="md-band md-intro"><p class="eyebrow">Hardware</p><h1 id="run-title">Can I run it?</h1>'
            '<p class="lede">Choose your GPU, your Apple or other unified memory, or your computer\'s memory alone, and see which models '
            'and quantizations fit, at which context length. The calculation runs in this page: nothing you enter leaves it.</p>'
            + contents((("check", "Check your hardware"), ("formula", "How the estimate works"), ("presets", "Where the numbers come from")))
            + "</div>"
            '<div class="md-band" id="check" aria-labelledby="check-title"><h2 id="check-title">Check your hardware</h2>'
            '<form class="md-fit-form" data-fit-form><fieldset class="md-kinds"><legend>What runs the model</legend>'
            '<label><input type="radio" name="kind" value="gpu" checked> A graphics card</label>'
            '<label><input type="radio" name="kind" value="unified"> Apple or other unified memory</label>'
            '<label><input type="radio" name="kind" value="cpu"> Computer memory only</label></fieldset>'
            f'<label class="md-field md-wide"><span>Hardware</span><select name="preset"><option value="">Enter my own numbers</option>{_preset_options(hardware, DEFAULT_PRESET)}</select></label>'
            f'<label class="md-field"><span>Memory, GiB</span><input type="number" name="memory" min="1" max="4096" step="1" value="{preset["memory_gib"]}"></label>'
            f'<label class="md-field"><span>Bandwidth, GB/s, for speed</span><input type="number" name="bandwidth" min="0" max="20000" step="0.1" value="{preset.get("bandwidth_gbps") or ""}"></label>'
            f'<label class="md-field"><span>Computer memory, GiB</span><input type="number" name="system" min="0" max="4096" step="1" value="{system["memory_gib"]}"></label>'
            f'<label class="md-field"><span>Shortest context you need</span><select name="context">{context_options}</select></label>'
            f'<label class="md-field"><span>KV cache</span><select name="kv">{kv_options}</select></label>'
            f'<label class="md-field"><span>Good for</span><select name="use"><option value="">Any use</option>{use_options}</select></label>'
            '<p class="md-field md-submit"><button class="primary" type="submit">Check</button></p></form>'
            f'<p class="md-order">{FIT_ORDER_SENTENCE}</p>'
            f'<p class="md-count" data-fit-summary aria-live="polite">On {escape(preset["name"])}, {len(results):,} models fit at {DEFAULT_CONTEXT:,} tokens or more. '
            f'{unknown:,} more have no KV cache numbers in any source, so they are left out.</p>'
            '<div class="md-table-wrap"><table class="md-table md-results"><thead><tr><th scope="col">Model</th><th scope="col">Quantization</th>'
            '<th scope="col">Weights</th><th scope="col">Longest context that fits</th><th scope="col">Memory then</th><th scope="col">Where</th>'
            f'<th scope="col">Speed</th></tr></thead><tbody data-fit-results>{result_rows(shown)}</tbody></table></div>'
            '<p class="md-more"><button class="quiet" type="button" data-fit-more hidden>Show more</button></p></div>'
            '<div class="md-band" id="formula" aria-labelledby="formula-title"><h2 id="formula-title">How the estimate works</h2>'
            '<p class="md-reading">The page picks, for each model, the largest quantization that fits, and the longest context that fits with it. '
            'Numbers marked estimate are not measurements. Real memory and speed depend on the runtime, its settings and the other work on the machine.</p>'
            f'<pre class="md-code"><code>{escape(formula)}</code></pre>'
            '<p class="md-reading">A graphics card may use all its memory; unified memory keeps about a quarter to a third for the system; computer '
            'memory alone keeps a fifth. These shares are estimates you can change by entering your own memory. A model that does not fit on the '
            'graphics card can still run with some layers in computer memory, much more slowly.</p></div>'
            f'<div class="md-band" id="presets" aria-labelledby="presets-title"><h2 id="presets-title">Where the numbers come from</h2>'
            '<p class="md-reading">Memory and bandwidth of each preset come from the vendor page below, read on the day shown. A preset without a '
            'bandwidth gives no speed until you enter one. Model sizes and architecture numbers come from the model pages. '
            '<a href="/models">Browse the models</a> or <a href="/endpoints">compare endpoints and runtimes</a>.</p>'
            f'<ul class="md-plain">{sources}</ul></div>' + disclosure(directory.models))
    structured = {"@context": SCHEMA_CONTEXT, "@type": "WebApplication", "name": "Can I run it?", "applicationCategory": "UtilitiesApplication",
                  "operatingSystem": "Any", "url": canonical(site_map, "/can-i-run"), "isAccessibleForFree": True,
                  "description": "Checks which open models and quantizations fit a GPU, unified memory or computer memory, at which context length.",
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Can I run it?", "/can-i-run")))}
    return frame(site_map, name, Page("/can-i-run", "can-i-run", site_map.page("/can-i-run").title,
                 "Enter a GPU and its memory, unified memory or computer memory, and see which open models and quantizations fit, at which context length, with a speed estimate.",
                 body, structured, "run-title"))


def _hosted_card(endpoint: dict) -> str:
    styles = ", ".join(STYLE_NAMES[api["style"]] for api in endpoint["apis"])
    facts = endpoint["facts"]
    parts = [f'<p class="md-styles">{escape(styles)}</p>']
    for key, label in (("structured_output", "Structured output"), ("tool_calling", "Tool calling")):
        value = (facts.get(key) or {}).get("value")
        parts.append(f"<span>{label}: {'Yes' if value is True else 'No' if value is False else escape(str(value)) if value else fmt.UNKNOWN}</span>")
    links = " ".join(fmt.link(facts[key]["address"], label) for key, label in (("rate_limits", "Rate limits"), ("pricing", "Prices"),
                                                                          ("data_policy", "Data retention")) if (facts.get(key) or {}).get("address"))
    return (f'<li class="md-card"><a class="md-row-link" href="/endpoints/{endpoint["slug"]}"><span class="md-name"{LISTING}>{escape(endpoint["name"])}</span>'
            f'<span class="md-maker">{len(endpoint["models"]):,} models listed</span></a>{"".join(parts)}<p class="md-links">{links}</p>'
            f'{commercial_link(endpoint)}</li>')


def endpoints_page(directory, site_map, name: str) -> str:
    ordered = fmt.order_endpoints(directory.endpoints)
    reviewed = [row for row in ordered if row["kind"] == records.ENDPOINT_HOSTED and any(item["id"] == "provider_documentation" for item in row["sources"])]
    listed = [row for row in ordered if row["kind"] == records.ENDPOINT_HOSTED and row not in reviewed]
    local = [row for row in ordered if row["kind"] == records.ENDPOINT_LOCAL]
    listed_rows = "".join(f'<tr><th scope="row"><a href="/endpoints/{row["slug"]}"{LISTING}>{escape(row["name"])}</a></th>'
                          f'<td><code{LISTING}>{escape(row["apis"][0]["base"])}</code></td><td>{len(row["models"]):,}</td></tr>' for row in listed)
    local_cards = "".join(f'<li class="md-card"><a class="md-row-link" href="/endpoints/{row["slug"]}"><span class="md-name">{escape(row["name"])}</span>'
                          f'<span class="md-maker">{escape(", ".join(row["setup"].get("formats") or []))} files</span></a>'
                          f'<p class="md-styles">{escape(", ".join(STYLE_NAMES[api["style"]] for api in row["apis"]))}</p>'
                          f'<pre class="md-code"><code>{escape((row["setup"].get("run") or {}).get("command", ""))}</code></pre></li>' for row in local)
    harness_rows = "".join(
        f'<tr><th scope="row">{escape(item["name"])}</th>' + "".join(f'<td>{"Reads it" if style in item["styles"] else "No"}</td>' for style in records.API_STYLES[:3])
        + f'<td>{fmt.link(item["source_address"], "Documentation")}, read {escape(item["source_read"])}</td></tr>' for item in directory.harnesses)
    body = ('<div class="md-band md-intro"><p class="eyebrow">Directory</p><h1 id="endpoints-title">Endpoints and local runtimes</h1>'
            f'<p class="lede">{len(reviewed) + len(listed):,} hosted model services and {len(local)} local runtimes: which API each speaks, how it takes a key, '
            'where its rate limits, prices and data rules are written, and how to set up OpenCode, Pi, Codex and Claude Code for it.</p>'
            + contents((("hosted", "Hosted services"), ("local", "Local runtimes"), ("harnesses", "What each harness reads"), ("sources", "Sources and dates")))
            + '<div class="md-actions"><a class="button secondary" href="/models">Browse the models</a>'
            '<a class="button secondary" href="/can-i-run">Check what your hardware runs</a><a class="button secondary" href="/setup">Get set up</a></div></div>'
            f'<div class="md-band" id="hosted" aria-labelledby="hosted-title"><h2 id="hosted-title">Hosted services</h2>'
            f'<p class="md-order">{ENDPOINT_ORDER_SENTENCE}</p>{paid_link_notice(ordered)}'
            '<p class="md-reading">A person read each of these services\' documentation on the date its page shows.</p>'
            f'<ul class="md-cards">{"".join(_hosted_card(row) for row in reviewed)}</ul>{ads_band(ordered)}'
            f'<details class="md-setup md-more-services"><summary>{len(listed):,} more services that models.dev lists</summary>'
            '<p class="md-reading">These publish an OpenAI-compatible address. Their pages show only what models.dev records.</p>'
            f'<div class="md-table-wrap"><table class="md-table"><thead><tr><th scope="col">Service</th><th scope="col">Address</th><th scope="col">Models</th></tr></thead>'
            f'<tbody>{listed_rows}</tbody></table></div></details></div>'
            f'<div class="md-band" id="local" aria-labelledby="local-title"><h2 id="local-title">Local runtimes</h2>'
            '<p class="md-reading">Each runs models on your own hardware and answers on your own computer. The start command takes a model from its page.</p>'
            f'<ul class="md-cards">{local_cards}</ul></div>'
            '<div class="md-band" id="harnesses" aria-labelledby="harnesses-title"><h2 id="harnesses-title">What each harness reads</h2>'
            '<div class="md-table-wrap"><table class="md-table"><thead><tr><th scope="col">Harness</th>'
            + "".join(f'<th scope="col">{escape(STYLE_NAMES[style])}</th>' for style in records.API_STYLES[:3])
            + f'<th scope="col">Source</th></tr></thead><tbody>{harness_rows}</tbody></table></div></div>'
            + sources_band(directory) + disclosure(directory.endpoints))
    structured = {"@context": SCHEMA_CONTEXT, "@type": "CollectionPage", "name": "Endpoints and local runtimes",
                  "url": canonical(site_map, "/endpoints"), "mainEntity": {"@type": "ItemList", "numberOfItems": len(ordered), "itemListElement": [
                      {"@type": "ListItem", "position": index + 1, "url": canonical(site_map, "/endpoints/" + row["slug"]), "name": row["name"]}
                      for index, row in enumerate(reviewed + local)]},
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Endpoints", "/endpoints")))}
    return frame(site_map, name, Page("/endpoints", "endpoints", site_map.page("/endpoints").title,
                 "Hosted model services and local runtimes: API style, OpenAI compatibility, authentication, structured output, tool calling, rate limits, dated prices and data retention.",
                 body, structured, "endpoints-title"))
