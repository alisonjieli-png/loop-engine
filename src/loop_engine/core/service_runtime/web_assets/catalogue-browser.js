"use strict";
/* Browsing the library published for one account, as one searchable table. Search answers a question;
   browsing shows what is there. The service decides what this account may see and whether an item's body
   may be fetched. This file only arranges and displays the record the service returned. It holds no token,
   keeps no body and writes nothing into browser storage.

   The owner, September 26, 2026: "we should use a searchable table format not a random HTML table/rows,
   also size, and digest are useless pieces of information to waste space on showing and we need ALL types
   of harness working directory component files not just SKILLS". So the table names every file's purpose,
   the kind of file a harness picks up, the kinds of step it supports, its licence, its declared
   effects and the tools it is written for; it shows no size and no digest; and a search box, two filters
   and sortable columns narrow it without a second request (roadmap S-6.208). The same day: "tag/label our
   harness component files by job title, industry, level, language, geography, etc, and allow people to
   search in the dashboard (when they sign up not on the home pages)". So five more filters, one for each
   facet the service serves as an attribute, are filled from the loaded rows and applied here; the public
   pages show none of them (roadmap S-6.209).

   The list arrives in pages since September 26, 2026 (roadmap S-6.203): the whole list of 6,398 packages was
   about 6.75 MB, larger than the service sends in one answer, and the library keeps growing. The first page is
   drawn at once and the rest follow in order while the table stays usable. The table lists everything the
   account may use, with the effects each file declares: a list is descriptions only, so it asks with every step
   effect the service names. A file that declares more than reading files is checked and fetched only after the
   reader confirms those effects, and then with exactly those effects for that one file. */
/* What each declared effect means, in plain words. The service names effects with these exact names; a name it
   adds later is shown as it was sent. `pure` declares no effect at all, so it is never asked for. Search results
   on the workspace page use the same words. */
window.BaltorEffects = (() => {
  const words = {reads_fs:"reads files in your project", writes_fs:"writes files in your project",
    reads_secret:"reads secret values such as access keys", network:"uses the network",
    spawns_process:"runs commands or programs on your computer"};
  const requested = effects => (Array.isArray(effects) ? effects : []).filter(name => typeof name === "string" && name !== "pure");
  const beyondReading = effects => requested(effects).filter(name => name !== "reads_fs");
  const plainly = effects => {
    const named = requested(effects).map(name => words[name] || name);
    return named.length < 2 ? named.join("") : named.slice(0, -1).join(", ") + " and " + named[named.length - 1];
  };
  return Object.freeze({requested, beyondReading, plainly});
})();
window.BaltorCatalogueBrowser = {
  /* The five facets, each a served keyword list under its attribute name: the select that filters on it,
     the plain name of the facet and the wording of its empty choice. A value is shown exactly as the
     service sent it, because the vocabulary is the service's, not this page's. The three functions below
     hold the whole filtering rule, so a check can run them without a page. */
  facets: [["job_titles", "browse-job-title", "Job titles", "Every job title"],
    ["industries", "browse-industry", "Industries", "Every industry"], ["levels", "browse-level", "Levels", "Every level"],
    ["languages", "browse-language", "Languages", "Every language"], ["geographies", "browse-geography", "Geographies", "Every geography"]],
  /* The values of one facet a row carries; a row without the attribute, or with anything but a list, has none. */
  facetValues(row, name) {
    const values = row && row.attributes && typeof row.attributes === "object" ? row.attributes[name] : undefined;
    return Array.isArray(values) ? values.map(String) : [];
  },
  /* What a facet select offers: exactly the values the loaded rows carry, once each, in alphabetical order. */
  facetChoices(rows, name) {
    return [...new Set(rows.flatMap(row => this.facetValues(row, name)))].sort((left, right) => left.localeCompare(right));
  },
  /* Whether a row carries every chosen value, as [name, value] pairs; an empty choice keeps every row. */
  keepsFacets(row, chosen) {
    return chosen.every(([name, value]) => !value || this.facetValues(row, name).includes(value));
  },
  create({request, element, message, current}) {
    const facetRules = window.BaltorCatalogueBrowser;
    const $ = id => document.getElementById(id);
    const path = "/api/v1/provisioning", downloadPath = "/api/v1/download";
    /* Version 2, as search asks: the same default step effects and account library setting. Internal
       classification fields remain part of the wire contract; the customer sees one component library. */
    const requestVersion = "service_provisioning_request/v2";
    /* The exact record versions this file was written against. Another version may rename a field or
       give an existing field a different meaning, so a reply that carries one is refused as a whole and
       nothing from it is displayed. A newer service therefore needs a newer page, not a page that
       guesses. */
    const pageVersion = "provisioning_list_page/v1", manifestVersion = "provisioning_manifest/v3";
    /* One page asks for at most this many rows; the service may send fewer to stay under its answer size. The
       measured choice is recorded in artifacts/paged-listing-2026-09-26. At most drawLimit rows are drawn at once,
       so the page stays quick with tens of thousands of rows loaded. */
    const listPageSize = 500, drawLimit = 300;
    const effects = window.BaltorEffects;
    const itemVersion = "harness_intelligence_item/v1";
    /* The answer to a report. The service decides whether the report withdrew the item; this page repeats it. */
    const reportVersion = "service_catalogue_report_result/v1";
    /* Validate the service's internal classification fields without rendering them as customer classes. */
    const knownTiers = new Set(["verified", "community"]);
    const metadataScope = "provisioning:metadata";
    /* The kinds of file a harness picks up, in the order the filter lists them, with the plain name of each.
       An item names its own through the harness_kind attribute the service serves; an item served before the
       attribute existed is placed by its first style when that names a kind (the licensed import writes the
       package kind there), else by its served kind. */
    const harnessKinds = [["skill", "Skill"], ["instruction_file", "Instruction file"], ["rules", "Rules"],
      ["subagent", "Subagent"], ["command", "Command"], ["hook", "Hook"], ["plugin_manifest", "Plugin manifest"],
      ["marketplace", "Plugin marketplace"], ["protocol_server_configuration", "Protocol server configuration"],
      ["harness_settings", "Harness settings"], ["contract_schema", "Contract schema"], ["code_module", "Code module"]];
    const harnessKindNames = Object.fromEntries(harnessKinds), harnessKindOrder = harnessKinds.map(([name]) => name);
    const servedKindFallback = {skill:"skill", instruction_file:"instruction_file", tool:"code_module", reusable_code:"code_module"};
    const knownLayers = new Set(["harness_local", "context_intelligence", "code_intelligence",
      "runtime_history_solution_intelligence", "user_feedback_intelligence"]);
    const knownKinds = Object.keys(servedKindFallback);
    const columns = [["purpose", "What it is for"], ["harness_kind", "Kind of file"],
      ["step_functions", "Step functions"], ["license", "Licence"], ["effects", "Declared effects"], ["styles", "Written for"]];
    const facets = facetRules.facets, facetSelects = facets.map(([, id]) => id);
    let listed = null, shown = null, selected = "", active = false, sortKey = "harness_kind", sortAscending = true;
    let loading = 0;
    const downloads = new Map(), confirmed = new Set(), rowFacts = new WeakMap();
    const eligible = () => current().connected && current().scopes.includes(metadataScope);
    /* Every step effect the service names in its capabilities record. The page keeps no copy of that list. */
    const stepEffects = () => {
      const named = current().stepEffects;
      return Array.isArray(named) && named.length && named.every(name => typeof name === "string" && name) ? [...named] : null;
    };
    const number = value => value.toLocaleString("en-US");
    const count = value => number(value) + (value === 1 ? " item" : " items");
    const facts = (target, entries) => {
      target.replaceChildren();
      for (const [name, value] of entries) target.append(element("dt", name), element("dd", value));
    };
    /* Every field this view reads, checked before anything is displayed. A missing, wrongly typed or
       unknown value means the page and the service no longer agree about the record, which is a
       refusal, not a field to be guessed or quietly dropped from the list. */
    const stated = value => typeof value === "string" && value.trim() !== "";
    const itemProblem = row => {
      if (!row || typeof row !== "object" || row.record_type !== itemVersion) return "an unsupported item version";
      if (!stated(row.identity) || !stated(row.purpose) || !stated(row.source_ref)) return "a missing description";
      if (!/^[0-9a-f]{64}$/.test(String(row.digest))) return "a missing digest";
      if (!knownLayers.has(row.source_layer)) return "a group this page does not know";
      if (!knownKinds.includes(row.kind)) return "a kind this page does not know";
      if (!Array.isArray(row.declared_effects) || !Array.isArray(row.styles)) return "an unreadable list of declared values";
      if (typeof row.body_allowed !== "boolean") return "no plain answer about downloading";
      if (!knownTiers.has(row.library_tier) || !stated(row.library_tier_label)) return "missing review metadata";
      if (row.attributes !== undefined && (row.attributes === null || typeof row.attributes !== "object" || Array.isArray(row.attributes))) return "unreadable attributes";
      return "";
    };
    /* One item, asked for by name. It carries the same facts as a list entry under its own record
       version, so it is checked the same way before a single value of it is displayed. */
    const manifestProblem = (value, row) => {
      if (!value || typeof value !== "object" || value.record_type !== manifestVersion) return "an unsupported item version";
      if (value.identity !== row.identity) return "another item";
      if (!/^[0-9a-f]{64}$/.test(String(value.digest))) return "a missing digest";
      if (!stated(value.source_ref) || !stated(value.qualification_basis)) return "a missing description";
      if (!Array.isArray(value.declared_effects) || !Array.isArray(value.styles)) return "an unreadable list of declared values";
      if (typeof value.body_allowed !== "boolean") return "no plain answer about downloading";
      if (!knownTiers.has(value.library_tier) || !stated(value.library_tier_label)) return "missing review metadata";
      return "";
    };
    const refused = "This service answered with a catalogue record this page was not written for, so nothing is shown.";
    /* A page must agree with the first page of the same load: the same account and the same total. */
    const refusalText = (value, first) => {
      if (!value || value.record_type !== pageVersion || !Array.isArray(value.items)
          || !Array.isArray(value.withheld) || !stated(value.tenant_id)
          || !Number.isInteger(value.total_offered) || !Number.isInteger(value.withheld_count)
          || !(value.next_cursor === null || stated(value.next_cursor))
          || (first && (value.tenant_id !== first.tenant_id || value.total_offered !== first.total_offered))) return refused;
      const problems = [...new Set(value.items.map(itemProblem).filter(Boolean))];
      return problems.length ? refused + " The catalogue holds entries with " + problems.join(", ") + "." : "";
    };
    /* The service names a refusal with a short code. These are the refusals the operations on this view
       can cause, written out in plain words. A code this page does not know is shown exactly as the
       service sent it, because inventing a friendly sentence for an unknown refusal would tell the
       reader something that was never checked. */
    const refusals = {
      selected_body_digest_mismatch:"This item changed since the list was loaded. Load the library again before fetching it.",
      item_withheld:"This item is no longer offered to this account. Load the library again to see what is there now.",
      item_unavailable:"This item is no longer available to this account. Load the library again to see what is there now.",
      body_forbidden:"This account may read the details of this item, not the file.",
      body_reader_unavailable:"This service cannot hand out files at the moment. The details above are unchanged.",
      meter_unavailable:"This service cannot record usage at the moment, so it did not send the file.",
      scope_required:"This account may not do that. Ask the person who runs this service for permission.",
      item_withdrawn:"This item was withdrawn from the library. Load the library again to see what is there now.",
      report_reason_invalid:"Write what is wrong in plain words, up to 400 characters.",
      report_requires_download:"Fetch this item before you report it. A report counts only for a file your account received.",
      catalogue_reports_unavailable:"This service does not take reports at the moment. Nothing was recorded.",
      staff_role_required:"Only a staff member can flag an item. A report from your account still counts.",
      list_release_changed:"The library changed again while it was loading. Load the library again to see the current list.",
      list_cursor_invalid:"The library could not continue loading. Load the library again to see the current list."};
    const refusalCode = error => (/^Service refused the request: ([a-z_]+)\.$/.exec(error && error.message) || [])[1] || "";
    const plainly = text => {
      const named = /^Service refused the request: ([a-z_]+)\.$/.exec(text);
      return named && refusals[named[1]] ? refusals[named[1]] : text;
    };
    /* The facts of one row as the table shows them: the served attributes first, the item's own fields
       where no attribute exists. A tag is shown exactly as the service sent it. */
    const attributesOf = row => (row.attributes && typeof row.attributes === "object") ? row.attributes : {};
    const harnessKindOf = row => {
      const declared = attributesOf(row).harness_kind;
      if (typeof declared === "string" && harnessKindNames[declared]) return declared;
      const style = (row.styles || []).find(name => harnessKindNames[name]);
      return style || servedKindFallback[row.kind] || "code_module";
    };
    const functionsOf = row => Array.isArray(attributesOf(row).step_functions) ? attributesOf(row).step_functions.map(String) : [];
    const facetOf = (row, name) => facetRules.facetValues(row, name);
    const toolsOf = row => (row.styles || []).filter(name => stated(name) && !harnessKindNames[name] && !/^[a-z_]+_(format|skill|agent|command|rule|manifest|hooks|settings|config|marketplace|schema|module)$/.test(name));
    const cells = row => ({
      purpose: row.purpose, harness_kind: harnessKindNames[harnessKindOf(row)],
      step_functions: functionsOf(row).join(", ") || "Not tagged", license: stated(row.license) ? row.license : "Not stated",
      effects: row.declared_effects.length ? row.declared_effects.join(", ") : "None declared",
      styles: toolsOf(row).join(", ") || "Compatibility not recorded"});
    /* The words a row is searched by, worked out once per row, since a load can bring tens of thousands; the
       facet values are words a reader may search by too. */
    const searchable = row => {
      let text = rowFacts.get(row);
      if (text === undefined) {
        text = [row.purpose, row.identity, harnessKindOf(row), harnessKindNames[harnessKindOf(row)],
          ...functionsOf(row), row.license || "", ...(row.declared_effects || []), ...(row.styles || []),
          ...facets.flatMap(([name]) => facetOf(row, name))]
          .join(" ").toLowerCase();
        rowFacts.set(row, text);
      }
      return text;
    };
    const clearDetail = text => $("browse-detail").replaceChildren(element("p", text, "caption"));
    /* A reader reports the exact item version. Withdrawal follows the service's response; this view
       does not expose or reinterpret the service's internal review classifications. */
    const reportOutcome = value => {
      if (!value || value.record_type !== reportVersion) return "This service answered with a report record this page was not written for.";
      if (value.withdrawn) return "Thank you. This item is withdrawn from the library and queued for review.";
      return "Thank you. Your report is recorded and the item is queued for review.";
    };
    function reportControl(row) {
      const holder = element("div", "", "browse-report");
      const open = element("button", "Report a problem with this item", "quiet"); open.type = "button";
      const form = element("form", "", "browse-report-form"); form.hidden = true;
      const box = document.createElement("textarea"); box.maxLength = 400; box.rows = 3; box.required = true;
      box.placeholder = "What is wrong with it? Up to 400 characters."; box.setAttribute("aria-label", "What is wrong with this item");
      const send = element("button", "Send report", "quiet"); send.type = "submit";
      const outcome = element("p", "", "caption"); outcome.setAttribute("role", "status");
      form.append(box, send); holder.append(open, form, outcome);
      open.addEventListener("click", () => { form.hidden = !form.hidden; if (!form.hidden) box.focus(); });
      form.addEventListener("submit", async event => {
        event.preventDefault();
        const reason = box.value.trim(), epoch = current().generation;
        if (!reason) { outcome.textContent = "Write what is wrong before sending."; return; }
        send.disabled = true; outcome.textContent = "Sending your report…";
        try {
          const value = await request(path, {record_type:requestVersion, operation:"report", identity:row.identity,
            expected_digest:row.digest, reason});
          if (epoch !== current().generation) return;
          outcome.textContent = reportOutcome(value); form.hidden = true; box.value = "";
        } catch (error) {
          if (epoch !== current().generation) return;
          outcome.textContent = error.name === "AbortError"
            ? "The wait ended. Your report may not have been recorded. Send it again." : plainly(error.message);
        } finally { if (epoch === current().generation) send.disabled = false; }
      });
      return holder;
    }
    /* The search box and the filters work on the rows loaded so far, so they stay usable while pages arrive. */
    function controls() {
      $("refresh-browse").disabled = !eligible() || active;
      for (const id of ["browse-search", "browse-kind", "browse-style", ...facetSelects]) $(id).disabled = !eligible() || !listed;
    }
    function reset() {
      listed = null; shown = null; selected = ""; active = false; loading += 1; downloads.clear(); confirmed.clear();
      $("browse-table-body").replaceChildren(); $("browse-count").textContent = "Sign in to browse";
      $("browse-search").value = "";
      options($("browse-kind"), [], "Every kind of file"); options($("browse-style"), [], "Every tool");
      for (const [, id, , everything] of facets) options($(id), [], everything);
      clearDetail("Open an item to read its details.");
      message("browse-message", "Sign in to browse the library published for your account.");
      controls();
    }
    function connectionChanged() {
      controls();
      if (eligible()) message("browse-message", "Load the library to see every file your account may use.");
      else if (current().connected) message("browse-message",
        "This account may not list material. Ask the person who runs this service for permission to search and list.", true);
    }
    /* A filter's choices come from the whole loaded library, so a filter can always be undone. */
    function options(select, values, everything) {
      const chosen = select.value;
      select.replaceChildren(element("option", everything));
      select.options[0].value = "";
      for (const [value, name] of values) { const choice = element("option", name); choice.value = value; select.append(choice); }
      select.value = [...select.options].some(choice => choice.value === chosen) ? chosen : "";
    }
    const collate = new Intl.Collator().compare;
    function sorted(rows) {
      const key = sortKey, direction = sortAscending ? 1 : -1;
      const value = row => key === "harness_kind" ? String(harnessKindOrder.indexOf(harnessKindOf(row))).padStart(2, "0")
        : String(cells(row)[key]).toLowerCase();
      // Each row's sort value is worked out once, not once for every comparison.
      return rows.map(row => [value(row), row]).sort(([first, left], [second, right]) => {
        if (first === second) return collate(left.purpose, right.purpose) * direction;
        return collate(first, second) * direction;
      }).map(([_value, row]) => row);
    }
    /* Keep matching tool tags and entries whose compatibility is unrecorded. Absence of a tag does
       not establish support; the same inclusive matching rule is used by the service's tool filter. */
    function filtered() {
      const words = $("browse-search").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      const kind = $("browse-kind").value, style = $("browse-style").value;
      const wanted = facets.map(([name, id]) => [name, $(id).value]);
      return listed.filter(row => (!kind || harnessKindOf(row) === kind)
        && (!style || !toolsOf(row).length || (row.styles || []).includes(style))
        && facetRules.keepsFacets(row, wanted)
        && (!words.length || words.every(word => searchable(row).includes(word))));
    }
    function renderHead() {
      const head = $("browse-table-head");
      head.replaceChildren();
      const line = document.createElement("tr");
      for (const [key, name] of columns) {
        const cell = document.createElement("th"); cell.scope = "col";
        const button = element("button", name, "browse-sort"); button.type = "button"; button.dataset.sortKey = key;
        if (key === sortKey) { cell.setAttribute("aria-sort", sortAscending ? "ascending" : "descending"); button.dataset.active = "true"; }
        button.addEventListener("click", () => { if (sortKey === key) sortAscending = !sortAscending; else { sortKey = key; sortAscending = true; } apply(); });
        cell.append(button); line.append(cell);
      }
      head.append(line);
    }
    function render(rows) {
      const body = $("browse-table-body");
      body.replaceChildren();
      for (const row of rows.slice(0, drawLimit)) {
        const line = document.createElement("tr");
        line.dataset.identity = row.identity; line.dataset.harnessKind = harnessKindOf(row);
        line.setAttribute("aria-selected", row.identity === selected ? "true" : "false");
        const values = cells(row);
        for (const [key] of columns) {
          const cell = document.createElement("td");
          if (key === "purpose") {
            const button = element("button", values.purpose, "browse-open"); button.type = "button";
            button.addEventListener("click", () => choose(row));
            cell.append(button);
          } else cell.textContent = values[key];
          line.append(cell);
        }
        body.append(line);
      }
      if (!rows.length) {
        const line = document.createElement("tr"), cell = document.createElement("td");
        cell.colSpan = columns.length; cell.className = "browse-empty";
        cell.textContent = listed && listed.length ? "Nothing matches your search and filters." : active ? "Loading the library…" : "Nothing is published for this account yet.";
        line.append(cell); body.append(line);
      }
      if (rows.length > drawLimit) {
        const line = document.createElement("tr"), cell = document.createElement("td");
        cell.colSpan = columns.length; cell.className = "browse-more";
        cell.textContent = "Showing the first " + number(drawLimit) + " of " + count(rows.length)
          + ". Narrow the search or the filters to see the rest.";
        line.append(cell); body.append(line);
      }
      $("browse-count").textContent = listed && rows.length !== listed.length ? number(rows.length) + " of " + count(listed.length) : count(rows.length);
    }
    function apply() {
      if (!listed) return;
      shown = sorted(filtered());
      renderHead(); render(shown);
    }
    function showDetail(row, entries, status) {
      const panel = $("browse-detail");
      panel.replaceChildren();
      panel.append(element("h3", row.purpose), element("p", row.identity, "caption"));
      if (entries) { const list = document.createElement("dl"); facts(list, entries); panel.append(list); }
      const note = element("p", status, "caption"); note.setAttribute("role", "status"); panel.append(note);
      return note;
    }
    /* Selecting an item asks the service about that exact item again. The list may be minutes old, and
       permission or the published revision can change in between. The reply must name the same item and
       carry the same digest; a different one means the page must not offer a download of what it listed.
       The digest is compared here and never shown: it is a check, not a fact a reader acts on. */
    /* A file that declares more than reading files is not checked or fetched until the reader has seen its effects
       in plain words and confirmed them. Nothing is sent before that. The confirmation covers that exact version of
       that one file until the library is loaded again, and each of its requests names exactly its declared effects. */
    const effectsAsked = row => effects.beyondReading(row.declared_effects).length
      ? {authority_effects:effects.requested(row.declared_effects)} : {};
    function askToConfirm(row) {
      const note = showDetail(row, [["What it is for", row.purpose],
        ["Declared effects", effects.requested(row.declared_effects).join(", ")]], "");
      note.textContent = "This file declares that it " + effects.plainly(row.declared_effects) + ". Checking it and fetching it"
        + " ask the service for exactly these effects, for this file only. Nothing runs on this page; the tool you load it"
        + " into decides what it may do.";
      const button = element("button", "Confirm and check this file", "quiet");
      button.type = "button"; button.id = "browse-confirm-effects";
      button.addEventListener("click", () => { confirmed.add(row.identity + ":" + row.digest); choose(row); });
      $("browse-detail").insertBefore(button, note);
    }
    /* On a narrow screen the detail panel stands under the table, so opening a row brings the panel into view. Beside
       the table on a wide screen it is already in view, and nothing moves. */
    function revealDetail() {
      const panel = $("browse-detail"), box = panel.getBoundingClientRect();
      if (box.top >= window.innerHeight || box.bottom <= 0) panel.scrollIntoView({block:"start"});
    }
    async function choose(row) {
      selected = row.identity;
      for (const line of $("browse-table-body").querySelectorAll("tr[data-identity]")) {
        line.setAttribute("aria-selected", line.dataset.identity === selected ? "true" : "false");
      }
      revealDetail();
      if (effects.beyondReading(row.declared_effects).length && !confirmed.has(row.identity + ":" + row.digest)) {
        askToConfirm(row);
        return;
      }
      const epoch = current().generation;
      showDetail(row, null, "Checking this item with the service…");
      try {
        const value = await request(path, {record_type:requestVersion, operation:"manifest",
          identity:row.identity, expected_digest:row.digest, ...effectsAsked(row)});
        if (epoch !== current().generation || selected !== row.identity) return;
        const problem = manifestProblem(value, row);
        if (problem) {
          throw new Error("This service answered with an item record that holds " + problem + ". Nothing is shown for it.");
        }
        if (value.digest !== row.digest) {
          throw new Error("This item changed since the list was loaded. Load the library again before fetching it.");
        }
        const shownValues = cells(row);
        const note = showDetail(row, [
          ["What it is for", row.purpose],
          ["Kind of file", shownValues.harness_kind],
          ["Step functions", shownValues.step_functions],
          ...facets.map(([name, , label]) => [label, facetOf(row, name).join(", ") || "Not tagged"]),
          ["Exact reference", row.identity],
          ["Where it comes from", value.source_ref],
          ["Licence", stated(value.license) ? value.license : "Not stated"],
          ["Declared effects", value.declared_effects.length ? value.declared_effects.join(", ") : "None declared"],
          ["Written for", toolsOf(value).length ? toolsOf(value).join(", ") : "Compatibility not recorded"],
          ["Basis of its review", value.qualification_basis],
          ["The file itself", value.body_allowed ? "You may fetch it. Access is checked again on the way." : "Not granted to this account."]], "");
        $("browse-detail").append(reportControl(row));
        if (!value.body_allowed) { note.textContent = "This account may read the details above, not the file."; return; }
        const button = element("button", "Download this version", "quiet");
        button.type = "button"; button.id = "browse-download";
        button.addEventListener("click", () => fetchBody(row, button, note));
        note.textContent = "Fetching this file records usage. The bytes are checked against the exact version that was listed.";
        $("browse-detail").insertBefore(button, note);
      } catch (error) {
        if (epoch !== current().generation || selected !== row.identity) return;
        showDetail(row, null, error.name === "AbortError"
          ? "The wait for this item ended. Nothing was fetched. Select it again." : plainly(error.message));
      }
    }
    /* The download repeats the check the service already made: the bytes are measured here, and they
       must match both the digest that was listed and the digest the service reported for the answer it
       sent. A file that fails either comparison is never saved. */
    async function fetchBody(row, button, status) {
      const key = row.identity + ":" + row.digest, epoch = current().generation;
      if (!downloads.has(key)) downloads.set(key, crypto.randomUUID());
      button.disabled = true; status.textContent = "Fetching the selected revision…";
      try {
        const result = await request(downloadPath, {record_type:requestVersion, operation:"read",
          identity:row.identity, expected_digest:row.digest, request_id:downloads.get(key), ...effectsAsked(row)}, true, true);
        const measured = [...new Uint8Array(await crypto.subtle.digest("SHA-256", result.bytes))]
          .map(number => number.toString(16).padStart(2, "0")).join("");
        if (measured !== row.digest || measured !== result.digest) {
          throw new Error("The bytes that arrived do not match the selected item. Nothing was saved.");
        }
        /* The bytes arrived and they match, but the reader may have signed out while they were being
           measured. Nothing is written to disk after that, because the file belongs to a connection the
           reader has ended. */
        if (epoch !== current().generation || result.epoch !== current().generation) return;
        const objectUrl = URL.createObjectURL(new Blob([result.bytes], {type:"application/octet-stream"}));
        const link = element("a", "Download");
        link.href = objectUrl; link.download = "intelligence-" + measured.slice(0, 12) + ".txt"; link.click();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        status.textContent = "Downloaded and checked. Loading it into your own tool and accepting the result are separate steps.";
        ratingPair(row, status);
      } catch (error) {
        status.textContent = error.name === "AbortError"
          ? "The wait ended. Usage may have been recorded. Repeat this exact selection to reconcile it."
          : plainly(error.message);
      } finally { if (epoch === current().generation) button.disabled = false; }
    }
    /* After a download the status line offers one rating, useful or not useful, of the exact revision that was
       fetched. The service refuses a rating of an item this account never downloaded, and a second rating of
       the same item replaces the first, so the pair can be pressed again. The note field is not offered here;
       the workspace's search results carry it. */
    function ratingPair(row, status) {
      const pair = element("span", "", "rating-pair"); pair.setAttribute("role", "group"); pair.setAttribute("aria-label", "Rate this download");
      for (const [value, label] of [["useful", "Useful"], ["not_useful", "Not useful"]]) {
        const button = element("button", label, "quiet"); button.type = "button"; button.dataset.ratingValue = value;
        button.addEventListener("click", async () => {
          const epoch = current().generation;
          for (const other of pair.querySelectorAll("button")) other.disabled = true;
          try {
            const result = await request(path, {record_type:requestVersion, operation:"rate", identity:row.identity,
              expected_digest:row.digest, value});
            if (epoch !== current().generation) return;
            status.textContent = result.replaced ? "Your rating was changed to " + label.toLowerCase() + "." : "Thank you. Your rating, " + label.toLowerCase() + ", was recorded.";
          } catch (error) {
            if (epoch !== current().generation) return;
            status.textContent = error.name === "AbortError" ? "The wait ended. The rating may not have been recorded." : plainly(error.message);
          } finally { if (epoch === current().generation) for (const other of pair.querySelectorAll("button")) other.disabled = false; }
        });
        pair.append(button);
      }
      status.insertAdjacentElement("afterend", pair);
    }
    /* Filter choices come from the rows loaded so far, so a filter can always be undone. */
    function refreshOptions() {
      options($("browse-kind"), harnessKinds.filter(([name]) => listed.some(row => harnessKindOf(row) === name)), "Every kind of file");
      // A development tool names itself. The page shows that name as it was published, never one it invented.
      options($("browse-style"), [...new Set(listed.flatMap(toolsOf))].sort().map(name => [name, name]), "Every tool");
      // Each facet filter offers exactly the values the loaded rows carry, in alphabetical order.
      for (const [name, id, , everything] of facets) {
        options($(id), facetRules.facetChoices(listed, name).map(value => [value, value]), everything);
      }
    }
    function refuse(text) {
      listed = null; shown = null; selected = "";
      $("browse-table-body").replaceChildren(); $("browse-count").textContent = "Nothing shown";
      clearDetail("Nothing is shown for this reply.");
      message("browse-message", text, true);
    }
    /* The whole library this account may use arrives page by page, in the order the service lists it. The first
       page is drawn at once and every later page is added as it arrives, while the search box, the filters and the
       rows already drawn stay usable. A list asks with every step effect the service names, so every file the
       account may use is listed with the effects it declares; the service gives no file and grants nothing for a
       list. If the library changes while it loads, the load starts again once from the first page and says so. */
    async function load() {
      if (!eligible() || active) return;
      const epoch = current().generation, token = ++loading, named = stepEffects();
      const ask = {record_type:requestVersion, operation:"list", page_size:listPageSize, ...(named ? {authority_effects:named} : {})};
      const stillWanted = () => epoch === current().generation && token === loading;
      active = true; listed = null; shown = null; selected = ""; confirmed.clear(); controls();
      clearDetail("Open an item to read its details.");
      message("browse-message", "Loading the library…");
      let first = null, cursor = null, restarted = false;
      try {
        while (true) {
          let value;
          try {
            value = await request(path, cursor ? {...ask, cursor} : ask);
          } catch (error) {
            const code = refusalCode(error);
            if (stillWanted() && cursor && !restarted && (code === "list_release_changed" || code === "list_cursor_invalid")) {
              restarted = true; first = null; cursor = null; listed = []; apply();
              message("browse-message", "The library changed while it was loading, so it is loading again from the start.");
              continue;
            }
            throw error;
          }
          if (!stillWanted()) return;
          const refusal = refusalText(value, first);
          if (refusal) { refuse(refusal); return; }
          if (!first) { first = value; listed = []; selected = ""; }
          listed.push(...value.items);
          refreshOptions(); controls(); apply();
          cursor = value.next_cursor;
          if (!cursor) break;
          message("browse-message", (restarted ? "The library changed while it was loading, so it is loading again from the start. " : "")
            + "Loaded " + number(listed.length) + " of " + number(first.total_offered)
            + ". The search box and the filters work on the rows loaded so far.");
        }
        /* The service holds material back for more than one reason: material this account may not see, and material
           that declares an effect the list did not name. */
        const withheld = first.withheld_count;
        message("browse-message", (restarted ? "The library changed while it was loading, so it was loaded again from the start. " : "")
          + "Showing " + count(listed.length) + " for " + first.tenant_id + ". "
          + (withheld ? count(withheld) + (withheld === 1 ? " is" : " are")
            + " not offered here, because of this account's permissions or a declared effect this list did not name. " : "")
          + "This table holds descriptions only. No file was fetched.");
      } catch (error) {
        if (!stillWanted()) return;
        const text = error.name === "AbortError" ? "The wait for the library ended. Load the library again." : plainly(error.message);
        if (listed && listed.length) message("browse-message", "Showing the " + count(listed.length) + " loaded before the load stopped. " + text, true);
        else refuse(text);
      } finally { if (stillWanted()) { active = false; controls(); apply(); } }
    }
    $("refresh-browse").addEventListener("click", () => load());
    $("browse-search").addEventListener("input", () => apply());
    for (const id of ["browse-kind", "browse-style", ...facetSelects]) $(id).addEventListener("change", () => apply());
    reset();
    return {reset, connectionChanged, load};
  }
};
