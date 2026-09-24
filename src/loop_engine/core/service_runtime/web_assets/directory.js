/* The directory page: search, category chips, filters and one scrollable list of every listing.

   The served page already holds the first rows, so a reader without this script and a search engine see real
   listings. This script loads the manifest and the eight row files named in it, checks their record versions and
   their row counts, and then draws only the rows inside the visible part of the list, so tens of thousands of rows
   scroll without drawing them all.

   Ordering, filtering, search and inclusion read only the listing facts on the page. A row's commercial relationship
   is read by drawRow, drawSponsored and drawNotice alone, with the labels the manifest names: an active affiliate or
   referral link is labelled Paid link, names its destination, shows the product's plain address beside it and carries
   rel="sponsored noopener", and never replaces the row's own links; Baltor's own service is labelled as such; an
   active ad is drawn in its own band headed Ads, at most three, never in the list; and one sentence sits above the
   list exactly while a paid link is active. Third-party text is written with textContent and marked data-listing-text. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const MANIFEST = "/assets/directory/manifest.json", MANIFEST_VERSION = "mcp_directory_manifest/v1", ROWS_VERSION = "mcp_directory_rows/v1";
  const COMMERCIAL_SCHEMA = "directory_commercial_relationship/v1", SECURE = "https://";
  const OVERSCAN = 6, ORIGIN_RANK = {maker: 0, unknown: 1, other: 2};
  /* Every outbound link of a row goes through the service's counted redirect, /out/directory/<link>/<row>, which
     answers with the address the list's link table holds and keeps one count per link per day, from the path alone. */
  const out = (link, identity) => "/out/directory/" + link + "/" + identity.split("/").map(encodeURIComponent).join("/");
  const state = {manifest: null, relationships: [], commercial: null, rows: [], shown: [], byId: new Map(), category: "", query: "",
    filters: {offering: "", origin: "", transport: "", auth: ""}, order: "sources", rowHeight: 120, target: "", frame: 0};
  const list = $("directory-list"), pane = $("directory-scroll"), count = $("directory-count");

  /* The shared header and footer, as the one-page app drives them: the appearance button, the phone menu and the status line. */
  const themes = ["system", "light", "dark"];
  let theme = "light";
  $("theme")?.addEventListener("click", () => { theme = themes[(themes.indexOf(theme) + 1) % themes.length];
    if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
    $("theme").textContent = "Appearance: " + theme; });
  addEventListener("keydown", event => { const menu = $("menu-toggle"); if (event.key === "Escape" && menu?.checked) { menu.checked = false; menu.focus(); } });
  fetch("/api/v1/capabilities", {headers: {Accept: "application/json"}}).then(response => {
    if (!response.ok) throw new Error("unavailable");
    $("service-status").textContent = "Service available";
  }).catch(() => { if ($("service-status")) $("service-status").textContent = "Service unavailable. Check the host configuration."; });

  const bits = (value, table) => Object.entries(table).filter(([, bit]) => value & bit).map(([name]) => name);
  const element = (tag, attributes = {}, text = "") => { const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) if (value !== false && value !== undefined) node.setAttribute(name, value === true ? "" : value);
    if (text) node.textContent = text; return node; };
  const plural = (number, word) => number.toLocaleString("en-US") + " " + word + (number === 1 ? "" : "s");

  async function fetchJson(address, cache = "default") {
    const response = await fetch(address, {headers: {Accept: "application/json"}, cache});
    if (!response.ok) throw new Error("The directory data answered " + response.status + ".");
    return response.json();
  }

  /* A commercial relationship record of the one version this page was written for, or a refusal. */
  function readRelationship(record) {
    const fields = ["kind", "program_name", "program_terms_address", "disclosure_label", "outbound_link", "canonical_address", "status", "reviewed_at"];
    if (!record || typeof record !== "object" || Object.keys(record).length !== fields.length || fields.some(name => typeof record[name] !== "string")
      || !state.commercial.kinds.includes(record.kind) || (record.kind !== "none" && record.disclosure_label !== state.commercial.labels[record.kind]))
      throw new Error("A commercial relationship in the manifest is not the version this page reads.");
    return record;
  }
  const active = relation => Boolean(relation) && relation.status === "active" && relation.outbound_link.startsWith(SECURE) && relation.canonical_address.startsWith(SECURE);
  const showsCommercialLink = relation => active(relation) && (relation.kind === "affiliate" || relation.kind === "referral");
  const isSponsoredPlacement = relation => active(relation) && relation.kind === "sponsored";
  const isOwnedService = relation => active(relation) && relation.kind === "owned";
  const label = (text, extra = {}) => element("span", {class: "paid-label", "data-disclosure-label": true, ...extra}, text);

  function decode(manifest, positions, values) {
    const column = name => values[positions[name]];
    const row = {id: column("id"), name: column("name"), publisher: column("publisher"), publisherKind: manifest.publisher_kinds[column("publisher_kind")],
      description: column("description"), category: manifest.categories[column("category")].id, offering: column("offering"),
      origin: manifest.origins[column("origin")], locations: column("locations").map(([kind, value]) => ({kind: manifest.location_kinds[kind], value})),
      transports: column("transports"), auth: column("auth"), licence: manifest.licences[column("licence")], licenceBasis: manifest.licence_bases[column("licence_basis")],
      website: column("website"), repository: column("repository"), repositoryState: manifest.repository_states[column("repository_state")],
      sources: column("sources"), aliases: column("aliases"), updated: column("updated"),
      commercial: column("commercial")};
    row.sourceCount = bits(row.sources, Object.fromEntries(manifest.sources.map(source => [source.id, source.bit]))).length;
    row.haystack = [row.id, row.name, row.publisher, row.description, row.website, row.repository, ...row.aliases,
      ...row.locations.map(location => location.value), manifest.categories[column("category")].label].join(" ").toLowerCase();
    row.sortName = row.name.toLowerCase();
    return row;
  }

  /* The orders a reader can choose. Each compares listing facts only. */
  function compareDefault(a, b) {
    return b.sourceCount - a.sourceCount || ORIGIN_RANK[a.origin] - ORIGIN_RANK[b.origin] || (a.description ? 0 : 1) - (b.description ? 0 : 1)
      || (a.sortName < b.sortName ? -1 : a.sortName > b.sortName ? 1 : 0) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  }
  const compareName = (a, b) => (a.sortName < b.sortName ? -1 : a.sortName > b.sortName ? 1 : 0) || (a.id < b.id ? -1 : 1);
  const compareUpdated = (a, b) => b.updated - a.updated || compareDefault(a, b);
  const orders = {sources: compareDefault, name: compareName, updated: compareUpdated};

  function matches(row, tokens) {
    const {offering, origin, transport, auth} = state.filters, manifest = state.manifest;
    if (state.category && row.category !== state.category) return false;
    if (offering && !(row.offering & manifest.offering_bits[offering])) return false;
    if (origin && row.origin !== origin) return false;
    if (transport && !(row.transports & manifest.transport_bits[transport])) return false;
    if (auth && !(row.auth & manifest.auth_bits[auth])) return false;
    return tokens.every(token => row.haystack.includes(token));
  }

  function apply() {
    const tokens = state.query.toLowerCase().split(/\s+/).filter(Boolean);
    state.shown = state.rows.filter(row => matches(row, tokens)).sort(orders[state.order] || compareDefault);
    list.style.height = (state.shown.length * state.rowHeight) + "px";
    pane.scrollTop = 0;
    const total = state.rows.length;
    count.textContent = state.shown.length === total ? "Showing all " + plural(total, "listing") + "."
      : state.shown.length ? "Showing " + state.shown.length.toLocaleString("en-US") + " of " + plural(total, "listing") + "."
      : "No listing matches. Clear the search or choose All.";
    $("directory-order-note").textContent = orderNotes[state.order] || orderNotes.sources;
    writeAddress();
    draw();
  }

  function drawLocation(row) {
    const labels = state.manifest.labels, where = element("p", {class: "row-where"});
    const first = row.locations[0];
    where.append(element("span", {class: "row-where-kind"}, first ? labels.location_kinds[first.kind] : "Code repository"), " ",
      element("code", {class: "row-where-value", "data-listing-text": true}, first ? first.value : row.repository));
    if (row.locations.length > 1) where.append(" ", element("span", {class: "row-more"}, "and " + (row.locations.length - 1) + " more"));
    return where;
  }

  /* One row, the same markup as the rows the served page holds. */
  function drawRow(row, index) {
    const labels = state.manifest.labels, manifest = state.manifest;
    const item = element("div", {class: "directory-row" + (row.id === state.target ? " is-target" : ""), id: row.id, role: "listitem", "data-row": true,
      "aria-setsize": String(state.shown.length), "aria-posinset": String(index + 1)});
    item.style.transform = "translateY(" + (index * state.rowHeight) + "px)";
    const main = element("div", {class: "row-main"}), name = element("h3", {class: "row-name"}), link = element("a", {class: "row-link", href: "#" + row.id});
    link.append(element("span", {"data-listing-text": true}, row.name));
    name.append(link);
    const publisher = element("p", {class: "row-publisher"});
    publisher.append(element("span", {"data-listing-text": true}, row.publisher || "Publisher not named"));
    const note = labels.publisher_kinds[row.publisherKind];
    if (note && row.publisher) publisher.append(" ", element("span", {class: "row-note"}, note));
    main.append(name, publisher, element("p", {class: "row-description", "data-listing-text": true}, row.description || ""));
    const get = element("div", {class: "row-get"});
    get.append(element("p", {class: "row-offering"}, bits(row.offering, manifest.offering_bits).map(name => labels.offering[name]).join(", ")), drawLocation(row));
    const connect = element("div", {class: "row-connect"});
    connect.append(element("p", {class: "row-transport"}, bits(row.transports, manifest.transport_bits).map(name => labels.transports[name]).join(", ") || "Connection not declared"),
      element("p", {class: "row-auth"}, bits(row.auth, manifest.auth_bits).map(name => labels.auth[name]).join(", ")));
    const facts = element("div", {class: "row-facts"});
    facts.append(element("p", {class: "row-origin", "data-origin": row.origin}, labels.origins[row.origin]),
      element("p", {class: "row-licence"}, row.licence || "Licence not known"),
      element("p", {class: "row-sources"}, manifest.sources.filter(source => row.sources & source.bit).map(source => labels.sources[source.id]).join(", ")));
    const docs = row.website || row.repository;
    if (docs) {
      const line = element("p", {class: "row-link-line"});
      line.append(element("a", {class: "row-docs", href: out("site", row.id), rel: "noopener", "data-row-docs": true}, "Documentation"), " ",
        element("span", {class: "row-host", "data-listing-text": true}, docs.split("/")[0]));
      facts.append(line);
    }
    const relation = state.relationships[row.commercial];
    if (showsCommercialLink(relation)) {
      const paid = element("p", {class: "row-paid"});
      paid.append(element("a", {href: out("paid", row.id), rel: state.commercial.paid_link_rel, "data-commercial-link": true}, "Sign up at " + row.name), " ",
        label(relation.disclosure_label), " ", element("span", {class: "paid-address", "data-listing-text": true}, relation.canonical_address.slice(SECURE.length)));
      facts.append(paid);
    } else if (isOwnedService(relation)) {
      facts.append(label(relation.disclosure_label, {"data-owned-service": true}));
    }
    item.append(main, get, connect, facts);
    return item;
  }

  function draw() {
    state.frame = 0;
    const total = state.shown.length, height = state.rowHeight;
    const first = Math.max(0, Math.floor(pane.scrollTop / height) - OVERSCAN);
    const last = Math.min(total, Math.ceil((pane.scrollTop + pane.clientHeight) / height) + OVERSCAN);
    const nodes = [];
    for (let index = first; index < last; index++) nodes.push(drawRow(state.shown[index], index));
    list.replaceChildren(...nodes);
  }
  const schedule = () => { if (!state.frame) state.frame = requestAnimationFrame(draw); };

  /* Ads, if any are active, in their own band headed Ads above the list, at most the manifest's maximum. None is active today. */
  function drawSponsored() {
    const band = $("directory-sponsored"), holder = $("directory-sponsored-list"), placed = [];
    for (const row of state.rows) {
      const relation = state.relationships[row.commercial];
      if (!isSponsoredPlacement(relation) || placed.length >= state.commercial.maximum_ads) continue;
      const item = element("li", {class: "sponsored-item"});
      item.append(element("a", {href: out("paid", row.id), rel: state.commercial.paid_link_rel, "data-commercial-link": true, "data-listing-text": true}, row.name), " ",
        label(relation.disclosure_label));
      placed.push(item);
    }
    $("directory-sponsored-title").textContent = state.commercial.ad_band_heading;
    holder.replaceChildren(...placed);
    band.hidden = placed.length === 0;
  }

  /* The sentence above the list, shown exactly while at least one row carries an active paid link. */
  function drawNotice() {
    const notice = $("directory-paid-notice");
    const paid = state.rows.some(row => showsCommercialLink(state.relationships[row.commercial]));
    notice.textContent = paid ? state.commercial.paid_link_notice : "";
    notice.hidden = !paid;
  }

  /* The sentence that says how the list is ordered, for the order the reader chose. */
  const orderNotes = {sources: "The list puts listings found in more sources first, then publisher listings before unmatched and community ones, then listings with a description, then names from A to Z.",
    name: "The list is in order of name, from A to Z.", updated: "The list puts the listings most recently updated in the registry first."};

  function measure() {
    const value = parseFloat(getComputedStyle(list).getPropertyValue("--row-height"));
    const changed = value > 0 && value !== state.rowHeight;
    if (value > 0) state.rowHeight = value;
    return changed;
  }

  /* The address holds the search and the filters, so a filtered list can be shared; the fragment names one listing. */
  function writeAddress() {
    const query = new URLSearchParams();
    if (state.query) query.set("q", state.query);
    if (state.category) query.set("category", state.category);
    for (const [name, value] of Object.entries(state.filters)) if (value) query.set(name, value);
    if (state.order !== "sources") query.set("order", state.order);
    const search = query.toString();
    history.replaceState(null, "", location.pathname + (search ? "?" + search : "") + location.hash);
  }

  function readAddress() {
    const query = new URLSearchParams(location.search), manifest = state.manifest;
    state.query = (query.get("q") || "").slice(0, 200);
    const category = query.get("category") || "";
    state.category = manifest.categories.some(entry => entry.id === category) ? category : "";
    const allowed = {offering: manifest.offering_bits, origin: Object.fromEntries(manifest.origins.map(name => [name, 1])),
      transport: manifest.transport_bits, auth: manifest.auth_bits};
    for (const name of Object.keys(state.filters)) { const value = query.get(name) || ""; state.filters[name] = value in allowed[name] ? value : ""; }
    state.order = orders[query.get("order")] ? query.get("order") : "sources";
  }

  function fillSelect(select, entries) {
    for (const [value, label] of entries) select.append(element("option", {value}, label));
  }

  function showTarget(identity, openDetail) {
    const row = state.byId.get(identity);
    if (!row) return;
    state.target = identity;
    let index = state.shown.indexOf(row);
    if (index < 0) { state.query = ""; state.category = ""; for (const name of Object.keys(state.filters)) state.filters[name] = ""; syncControls(); apply(); index = state.shown.indexOf(row); }
    pane.scrollTop = Math.max(0, index * state.rowHeight - state.rowHeight);
    draw();
    if (openDetail) detail(row);
  }

  function syncControls() {
    $("directory-query").value = state.query;
    for (const chip of document.querySelectorAll(".directory-chip")) chip.setAttribute("aria-pressed", String(chip.dataset.category === state.category));
    $("filter-offering").value = state.filters.offering; $("filter-origin").value = state.filters.origin;
    $("filter-transport").value = state.filters.transport; $("filter-auth").value = state.filters.auth; $("filter-order").value = state.order;
  }

  function detailRow(list, term, value) {
    if (value === "" || value === null || value === undefined) return;
    list.append(element("dt", {}, term));
    const cell = element("dd");
    if (value instanceof Node) cell.append(value); else cell.textContent = value;
    list.append(cell);
  }

  function detail(row) {
    const manifest = state.manifest, labels = manifest.labels, body = $("detail-body");
    $("detail-title").textContent = row.name;
    $("detail-title").setAttribute("data-listing-text", "");
    $("detail-message").textContent = "";
    const facts = element("dl", {class: "detail-facts"});
    detailRow(facts, "Publisher", (row.publisher || "Not named") + (labels.publisher_kinds[row.publisherKind] ? ", " + labels.publisher_kinds[row.publisherKind] : ""));
    detailRow(facts, "What it does", row.description || "No description in the listing");
    detailRow(facts, "Category", manifest.categories.find(entry => entry.id === row.category).label);
    detailRow(facts, "What it is", bits(row.offering, manifest.offering_bits).map(name => labels.offering[name]).join(", "));
    const places = element("ul", {class: "detail-places"});
    for (const location of row.locations) {
      const item = element("li");
      item.append(element("span", {}, labels.location_kinds[location.kind] + ": "), element("code", {"data-listing-text": true}, location.value));
      places.append(item);
    }
    if (row.locations.length) detailRow(facts, "Where to get it", places);
    const docs = row.website || row.repository;
    if (docs) detailRow(facts, "Documentation", element("a", {href: out("site", row.id), rel: "noopener", "data-listing-text": true}, docs));
    if (row.repository) {
      const code = element("span");
      code.append(element("a", {href: out(row.repository === docs ? "site" : "code", row.id), rel: "noopener", "data-listing-text": true}, row.repository));
      if (labels.repository_states[row.repositoryState]) code.append(", " + labels.repository_states[row.repositoryState]);
      detailRow(facts, "Code repository", code);
    }
    detailRow(facts, "Connects over", bits(row.transports, manifest.transport_bits).map(name => labels.transports[name]).join(", ") || "Not declared");
    detailRow(facts, "Signs in with", bits(row.auth, manifest.auth_bits).map(name => labels.auth[name]).join(", "));
    detailRow(facts, "Listed by", labels.origins[row.origin]);
    detailRow(facts, "Licence", row.licence ? row.licence + (labels.licence_bases[row.licenceBasis] ? ", " + labels.licence_bases[row.licenceBasis] : "") : "Not known");
    const sources = manifest.sources.filter(source => row.sources & source.bit);
    detailRow(facts, "Sources", sources.map(source => labels.sources[source.id] + (source.checked ? ", checked " + source.checked : "")).join("; "));
    if (row.aliases.length) detailRow(facts, "Also listed as", row.aliases.join(", "));
    if (row.updated) detailRow(facts, "Updated in the registry", new Date(Date.parse(manifest.day_zero) + row.updated * 86400000).toISOString().slice(0, 10));
    const relation = state.relationships[row.commercial];
    if (showsCommercialLink(relation)) {
      const paid = element("span");
      paid.append(element("a", {href: out("paid", row.id), rel: state.commercial.paid_link_rel, "data-commercial-link": true}, "Sign up at " + row.name), " ",
        label(relation.disclosure_label), " ", element("span", {class: "paid-address", "data-listing-text": true}, relation.canonical_address.slice(SECURE.length)));
      detailRow(facts, "Paid link", paid);
    } else if (isOwnedService(relation)) {
      detailRow(facts, "Listed by Baltor", label(relation.disclosure_label, {"data-owned-service": true}));
    }
    body.replaceChildren(facts);
    const dialog = $("directory-detail");
    if (typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
  }

  async function start() {
    const manifest = await fetchJson(MANIFEST, "no-cache");
    if (manifest.record_type !== MANIFEST_VERSION || manifest.commercial_relationship_schema !== COMMERCIAL_SCHEMA || !Array.isArray(manifest.columns))
      throw new Error("The directory data is not the version this page reads.");
    state.manifest = manifest;
    state.commercial = manifest.commercial_labels;
    state.relationships = manifest.commercial_relationships.map(readRelationship);
    /* Each row file is asked for by its own digest, so a browser never pairs a new manifest with an old cached file. */
    const parts = await Promise.all(manifest.parts.map(part => fetchJson(part.address + "?v=" + encodeURIComponent(part.sha256 || ""))));
    const rows = [], positions = Object.fromEntries(manifest.columns.map((name, position) => [name, position]));
    parts.forEach((part, index) => {
      if (part.record_type !== ROWS_VERSION || part.part !== index || part.rows.length !== manifest.parts[index].rows)
        throw new Error("A directory row file is not the one the manifest names.");
      for (const values of part.rows) rows.push(decode(manifest, positions, values));
    });
    if (rows.length !== manifest.row_count) throw new Error("The directory data holds a different number of rows than its manifest.");
    state.rows = rows;
    for (const row of rows) state.byId.set(row.id, row);
    fillSelect($("filter-offering"), Object.keys(manifest.offering_bits).map(name => [name, manifest.labels.offering[name]]));
    fillSelect($("filter-origin"), manifest.origins.map(name => [name, manifest.labels.origins[name]]));
    fillSelect($("filter-transport"), Object.keys(manifest.transport_bits).map(name => [name, manifest.labels.transports[name]]));
    fillSelect($("filter-auth"), Object.keys(manifest.auth_bits).map(name => [name, manifest.labels.auth[name]]));
    readAddress();
    measure();
    list.classList.add("is-virtual");
    syncControls();
    for (const control of [$("directory-query"), $("filter-offering"), $("filter-origin"), $("filter-transport"), $("filter-auth"), $("filter-order")]) control.disabled = false;
    drawSponsored();
    drawNotice();
    apply();
    const identity = decodeURIComponent(location.hash.slice(1));
    if (identity) showTarget(identity, false);
    document.documentElement.dataset.directory = "ready";
  }

  /* A read-only view of what the list shows, for the browser checks and for anyone reading the page with a script. */
  window.BaltorDirectory = Object.freeze({shown: () => state.shown.map(row => row.id), total: () => state.rows.length});

  let typing = 0;
  $("directory-query").addEventListener("input", event => { clearTimeout(typing); typing = setTimeout(() => { state.query = event.target.value.slice(0, 200); apply(); }, 120); });
  $("directory-search").addEventListener("submit", event => { event.preventDefault(); state.query = $("directory-query").value.slice(0, 200); apply(); });
  $("directory-categories").addEventListener("click", event => {
    const chip = event.target.closest(".directory-chip");
    if (!chip || !state.manifest) return;
    state.category = chip.dataset.category || "";
    syncControls(); apply();
  });
  for (const [control, name] of [[$("filter-offering"), "offering"], [$("filter-origin"), "origin"], [$("filter-transport"), "transport"], [$("filter-auth"), "auth"]])
    control.addEventListener("change", () => { state.filters[name] = control.value; apply(); });
  $("filter-order").addEventListener("change", () => { state.order = orders[$("filter-order").value] ? $("filter-order").value : "sources"; apply(); });
  pane.addEventListener("scroll", schedule, {passive: true});
  addEventListener("resize", () => { if (state.manifest && measure()) { list.style.height = (state.shown.length * state.rowHeight) + "px"; } if (state.manifest) schedule(); });
  list.addEventListener("click", event => {
    const link = event.target.closest(".row-link");
    if (!link || !state.manifest) return;
    event.preventDefault();
    const identity = link.getAttribute("href").slice(1);
    history.replaceState(null, "", location.pathname + location.search + "#" + encodeURIComponent(identity));
    showTarget(identity, true);
  });
  addEventListener("hashchange", () => { const identity = decodeURIComponent(location.hash.slice(1)); if (state.byId.has(identity)) showTarget(identity, false); });
  $("detail-close").addEventListener("click", () => $("directory-detail").close());
  $("detail-copy").addEventListener("click", async () => {
    const address = location.origin + location.pathname + "#" + encodeURIComponent(state.target);
    try { await navigator.clipboard.writeText(address); $("detail-message").textContent = "Link copied."; }
    catch (_) { $("detail-message").textContent = address; }
  });
  start().catch(error => { count.textContent = error.message + " The first listings above are from the served page."; document.documentElement.dataset.directory = "failed"; });
})();
