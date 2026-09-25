/* The model directory pages: search and order the model list, and check models against hardware in the page.
   The pages work without this script: the service renders every list. The script only reads the two same-origin indexes
   the page names, and it sends nothing anywhere. The hardware check repeats the formula of model_directory_fit.py with the
   constants the page carries, and a browser check holds the two to the same answer for every preset. */
(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const view = $("[data-view]");
  const GIB = 1024 ** 3;
  const USES = ["coding", "reasoning", "classification", "embeddings", "rerank", "vision"];

  /* The appearance switch and the service line of the shared footer, as the site's own page script drives them. */
  const themes = ["system", "light", "dark"];
  let theme = "light";
  const themeButton = $("#theme");
  if (themeButton) themeButton.addEventListener("click", () => {
    theme = themes[(themes.indexOf(theme) + 1) % themes.length];
    if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
    themeButton.textContent = "Appearance: " + theme;
  });
  /* The phone menu of the shared header: one button that shows and hides the navigation it controls and says which with
     aria-expanded; Escape closes it and returns focus to the button, as the site's other pages do. */
  const menuButton = $("#menu-button");
  const setMenu = open => { if (!menuButton) return; menuButton.setAttribute("aria-expanded", String(open)); menuButton.closest(".header")?.classList.toggle("menu-open", open); };
  menuButton?.addEventListener("click", () => setMenu(menuButton.getAttribute("aria-expanded") !== "true"));
  addEventListener("keydown", event => { if (event.key === "Escape" && menuButton?.getAttribute("aria-expanded") === "true") { setMenu(false); menuButton.focus(); } });
  const status = $("#service-status");
  if (status) fetch("/api/v1/capabilities", {credentials: "omit", redirect: "error", cache: "no-store"})
    .then(answer => answer.json().then(() => answer.ok))
    .then(ok => { status.textContent = ok ? "Service available" : "Service unavailable. Check the host configuration."; })
    .catch(() => { status.textContent = "Service unavailable. Check the host configuration."; });

  const loadIndex = address => fetch(address, {credentials: "omit", redirect: "error"}).then(answer => {
    if (!answer.ok) throw new Error("index " + answer.status);
    return answer.json();
  }).then(record => record.rows.map(values => Object.fromEntries(record.fields.map((name, index) => [name, values[index]]))));
  const text = value => document.createTextNode(String(value));
  const element = (tag, attributes = {}, children = []) => {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (value === true) node.setAttribute(name, ""); else if (value !== false && value !== null && value !== undefined) node.setAttribute(name, value);
    }
    for (const child of children) node.append(child instanceof Node ? child : text(child));
    return node;
  };
  const compare = (left, right) => (left < right ? -1 : left > right ? 1 : 0);
  const unknown = "Unknown";

  /* Formatting that matches model_directory_format.py. */
  const shortParameters = value => !Number.isInteger(value) || value <= 0 ? unknown
    : value >= 1e12 ? (value / 1e12).toFixed(1) + "T" : value >= 1e9 ? (value / 1e9).toFixed(1) + "B" : (value / 1e6).toFixed(0) + "M";
  const tokens = value => Number.isInteger(value) && value > 0 ? value.toLocaleString("en-US") : unknown;
  const price = value => {
    if (typeof value !== "number" || value < 0) return unknown;
    if (value === 0) return "0 USD";
    const digits = value >= 1 ? 2 : value >= 0.01 ? 3 : 4;
    return value.toLocaleString("en-US", {minimumFractionDigits: digits, maximumFractionDigits: digits}) + " USD";
  };
  const gib = value => {
    if (typeof value !== "number" || value <= 0) return unknown;
    const amount = value / GIB;
    return amount < 100 ? amount.toFixed(1) + " GiB" : Math.round(amount).toLocaleString("en-US") + " GiB";
  };
  const usesOf = bits => USES.filter((_, index) => bits & (1 << index));

  /* The model list: search by name or maker, one sourced use, open or hosted, and one of three orders. */
  if (view && view.dataset.view === "models") {
    const form = $("[data-models-filter]"), list = $("[data-models-list]"), count = $("[data-models-count]"), more = $("[data-models-more]");
    let rows = null, shown = 0, current = [];
    const descending = day => day.replace(/[0-9]/g, digit => String(9 - Number(digit)));
    const orders = {
      providers: (a, b) => compare(a.providers === 0, b.providers === 0) || compare(-a.providers, -b.providers)
        || compare(a.providers === 0 ? "" : descending(a.released || "0000-00-00"), b.providers === 0 ? "" : descending(b.released || "0000-00-00"))
        || compare(-(a.downloads || 0), -(b.downloads || 0)) || compare(a.name.toLowerCase(), b.name.toLowerCase()) || compare(a.slug, b.slug),
      newest: (a, b) => compare(a.released === "", b.released === "") || compare(a.released ? descending(a.released) : "", b.released ? descending(b.released) : "")
        || compare(a.name.toLowerCase(), b.name.toLowerCase()) || compare(a.slug, b.slug),
      downloads: (a, b) => compare(-(a.downloads || 0), -(b.downloads || 0)) || compare(a.name.toLowerCase(), b.name.toLowerCase()) || compare(a.slug, b.slug),
      name: (a, b) => compare(a.name.toLowerCase(), b.name.toLowerCase()) || compare(a.slug, b.slug)};
    const item = row => element("li", {class: "md-row"}, [
      element("a", {class: "md-row-link", href: "/models/" + row.slug}, [element("span", {class: "md-name", "data-listing-text": true}, [row.name]),
        element("span", {class: "md-maker", "data-listing-text": true}, [row.maker])]),
      element("dl", {class: "md-facts"}, [
        element("div", {}, [element("dt", {}, ["Parameters"]), element("dd", {}, [shortParameters(row.parameters)])]),
        element("div", {}, [element("dt", {}, ["Context"]), element("dd", {}, [tokens(row.context)])]),
        element("div", {}, [element("dt", {}, ["Licence"]), element("dd", {"data-listing-text": true}, [row.licence || unknown])]),
        element("div", {}, [element("dt", {}, ["Input, per million tokens"]), element("dd", {}, [row.input_price === null ? unknown : price(row.input_price)])])]),
      ...(row.uses ? [element("p", {class: "md-tags"}, [usesOf(row.uses).join(", ")])] : [])]);
    const draw = () => {
      const next = current.slice(shown, shown + 40);
      list.append(...next.map(item));
      shown += next.length;
      more.hidden = shown >= current.length;
      count.textContent = "Showing " + shown.toLocaleString("en-US") + " of " + current.length.toLocaleString("en-US") + " models"
        + (current.length === rows.length ? "." : " that match, of " + rows.length.toLocaleString("en-US") + ".");
    };
    const apply = () => {
      const data = new FormData(form), query = String(data.get("q") || "").trim().toLowerCase(), use = String(data.get("use") || "");
      const weights = String(data.get("weights") || "all"), order = orders[String(data.get("order"))] || orders.providers;
      const bit = use ? 1 << USES.indexOf(use) : 0;
      current = rows.filter(row => (!query || (row.name + " " + row.maker + " " + row.slug).toLowerCase().includes(query))
        && (!bit || (row.uses & bit)) && (weights === "all" || (weights === "open" ? row.kind !== "h" : row.input_price !== null))).sort(order);
      list.replaceChildren();
      shown = 0;
      draw();
    };
    const ready = () => rows ? Promise.resolve() : loadIndex(view.dataset.searchIndex).then(loaded => { rows = loaded; });
    const run = () => ready().then(apply).catch(() => { count.textContent = "The list could not be searched here. Every model above still links to its page."; });
    form.addEventListener("input", run);
    form.addEventListener("change", run);
    form.addEventListener("submit", event => { event.preventDefault(); run(); });
    /* The index is read only when a person searches or asks for more, so opening the page reads nothing extra. */
    more.addEventListener("click", () => ready().then(() => {
      if (!current.length) { current = rows.slice().sort(orders.providers); shown = list.children.length; }
      draw();
    }).catch(() => { count.textContent = "More models could not be loaded here. Every model above still links to its page."; }));
    form.addEventListener("focusin", () => { ready().catch(() => {}); }, {once: true});
    const given = new URLSearchParams(location.search);
    for (const name of ["q", "use", "weights", "order"]) if (given.get(name) && form.elements[name]) form.elements[name].value = given.get(name);
    if (["q", "use", "weights", "order"].some(name => given.get(name))) run();
  }

  /* The hardware check: the formula of model_directory_fit.py, with the constants the page carries. */
  if (view && view.dataset.view === "can-i-run") {
    const hardware = JSON.parse($("#md-hardware").textContent);
    const formula = hardware.formula;
    const form = $("[data-fit-form]"), body = $("[data-fit-results]"), summary = $("[data-fit-summary]"), more = $("[data-fit-more]");
    const presets = Object.fromEntries(hardware.presets.map(preset => [preset.id, preset]));
    let rows = null, results = [], shown = 0;
    const kvBytes = (model, context, kind) => {
      const perValue = formula.kv_bytes_per_value[kind];
      if (model.attention === "l") return model.layers > 0 && model.latent_width > 0 ? model.layers * model.latent_width * context * perValue : null;
      if (model.attention === "f") return model.layers > 0 && model.kv_heads > 0 && model.head_dim > 0 ? 2 * model.layers * model.kv_heads * model.head_dim * context * perValue : null;
      return null;
    };
    const overhead = weights => formula.overhead_fixed_bytes + formula.overhead_weight_fraction * weights;
    const contextsFor = model => {
      const limit = model.max_context || formula.context_steps[2];
      const steps = formula.context_steps.filter(step => step <= limit);
      return steps.length ? steps : [limit];
    };
    const fitKind = (total, device) => total <= device.usable ? "device" : device.kind === "gpu" && total <= device.usable + device.spill ? "split" : "none";
    const bestFit = (weights, model, device, kind) => {
      const found = {device: null, split: null};
      for (const context of contextsFor(model)) {
        const kv = kvBytes(model, context, kind);
        if (kv === null) return {kind: "unknown", context: 0, total: null};
        const total = weights + kv + overhead(weights), where = fitKind(total, device);
        if (where in found) found[where] = {kind: where, context, total, weights, kv};
      }
      if (found.device) return found.device;
      if (found.split) return found.split;
      return {kind: "none", context: contextsFor(model)[0], total: null};
    };
    const speed = (fit, device, share) => {
      if (fit.kind !== "device" && fit.kind !== "split") return null;
      const read = fit.weights * share + fit.kv;
      let seconds;
      if (fit.kind === "device") {
        if (!(device.bandwidth > 0)) return null;
        seconds = read / (device.bandwidth * 1e9);
      } else {
        if (!(device.bandwidth > 0) || !(device.systemBandwidth > 0)) return null;
        const onDevice = Math.min(1, device.usable / fit.total);
        seconds = read * onDevice / (device.bandwidth * 1e9) + read * (1 - onDevice) / (device.systemBandwidth * 1e9);
      }
      return [formula.speed_low_fraction / seconds, formula.speed_high_fraction / seconds];
    };
    const defaultFraction = (kind, memory) => kind === "gpu" ? 1 : kind === "unified" ? (memory > 36 ? 0.75 : 0.67) : formula.cpu_usable_fraction;
    const device = () => {
      const data = new FormData(form), preset = presets[String(data.get("preset"))];
      const kind = preset ? preset.kind : String(data.get("kind"));
      const memory = Number(data.get("memory")) || (preset ? preset.memory_gib : 0), system = Number(data.get("system")) || 0;
      const fraction = preset && memory === preset.memory_gib ? preset.usable_fraction : defaultFraction(kind, memory);
      return {kind, memory, bandwidth: Number(data.get("bandwidth")) || 0, usable: memory * GIB * fraction,
        spill: kind === "gpu" ? system * GIB * formula.cpu_usable_fraction : 0, systemBandwidth: hardware.system_memory_default.bandwidth_gbps,
        name: preset && memory === preset.memory_gib ? preset.name : memory + " GiB"};
    };
    const compute = () => {
      const data = new FormData(form), hardwareNow = device(), minimum = Number(data.get("context")) || 8192;
      const kind = String(data.get("kv") || "f16"), use = String(data.get("use") || ""), bit = use ? 1 << USES.indexOf(use) : 0;
      const found = [];
      let unknownCount = 0;
      for (const model of rows) {
        if (bit && !(model.uses & bit)) continue;
        const quantizations = model.quantizations.slice().sort((a, b) => b[1] - a[1]);
        if (!quantizations.length) continue;
        if (!((model.attention === "f" && model.layers > 0 && model.kv_heads > 0 && model.head_dim > 0) || (model.attention === "l" && model.layers > 0 && model.latent_width > 0))) { unknownCount += 1; continue; }
        let chosen = null;
        for (const wanted of ["device", "split"]) {
          for (const [name, size] of quantizations) {
            const fit = bestFit(size, model, hardwareNow, kind);
            if (fit.kind === wanted && fit.context >= Math.min(minimum, model.max_context || minimum)) { chosen = {name, size, fit}; break; }
          }
          if (chosen) break;
        }
        if (!chosen) continue;
        const share = Number.isInteger(model.active_parameters) && Number.isInteger(model.parameters) && model.parameters > 0 ? model.active_parameters / model.parameters : 1;
        found.push({model, ...chosen, speed: speed(chosen.fit, hardwareNow, share)});
      }
      found.sort((a, b) => compare(a.fit.kind !== "device", b.fit.kind !== "device") || compare(-(a.model.parameters || 0), -(b.model.parameters || 0))
        || compare(a.model.name.toLowerCase(), b.model.name.toLowerCase()) || compare(a.model.slug, b.model.slug));
      return {found, unknownCount, hardwareNow, minimum};
    };
    const row = result => element("tr", {}, [
      element("th", {scope: "row"}, [element("a", {href: "/models/" + result.model.slug, "data-listing-text": true}, [result.model.name])]),
      element("td", {}, [result.name]), element("td", {}, [gib(result.size) + (result.model.estimated ? " (estimate)" : "")]),
      element("td", {}, [result.fit.context.toLocaleString("en-US")]), element("td", {}, [gib(result.fit.total)]),
      element("td", {}, [result.fit.kind === "device" ? "On the device" : "Split with computer memory, slower"]),
      element("td", {}, [result.speed ? Math.round(result.speed[0]).toLocaleString("en-US") + " to " + Math.round(result.speed[1]).toLocaleString("en-US") + " tokens a second (estimate)" : "Unknown: enter the memory bandwidth"])]);
    const draw = () => {
      const next = results.slice(shown, shown + 25);
      body.append(...next.map(row));
      shown += next.length;
      more.hidden = shown >= results.length;
    };
    const run = () => (rows ? Promise.resolve() : loadIndex(view.dataset.fitIndex).then(loaded => { rows = loaded; })).then(() => {
      const outcome = compute();
      results = outcome.found;
      body.replaceChildren();
      shown = 0;
      draw();
      summary.textContent = "On " + outcome.hardwareNow.name + ", " + results.length.toLocaleString("en-US") + " models fit at "
        + outcome.minimum.toLocaleString("en-US") + " tokens or more. " + outcome.unknownCount.toLocaleString("en-US")
        + " more have no KV cache numbers in any source, so they are left out.";
      view.dataset.fitReady = "true";
    }).catch(() => { summary.textContent = "The check could not load its model list. The table above shows the result for the first preset."; });
    form.elements.preset.addEventListener("change", () => {
      const preset = presets[form.elements.preset.value];
      if (preset) {
        form.elements.memory.value = preset.memory_gib;
        form.elements.bandwidth.value = preset.bandwidth_gbps || "";
        for (const input of form.elements.kind) input.checked = input.value === preset.kind;
      }
    });
    for (const input of form.elements.kind) input.addEventListener("change", () => { form.elements.preset.value = ""; });
    form.elements.memory.addEventListener("input", () => { const preset = presets[form.elements.preset.value]; if (preset && Number(form.elements.memory.value) !== preset.memory_gib) form.elements.preset.value = ""; });
    form.addEventListener("submit", event => { event.preventDefault(); run(); });
    form.addEventListener("change", () => run());
    more.addEventListener("click", () => draw());
    window.baltorFit = {compute: () => rows ? compute() : null, ready: () => view.dataset.fitReady === "true"};
    run();
  }
})();
