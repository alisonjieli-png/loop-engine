"use strict";
/* Browsing the library published for one account, as one searchable table. Search answers a question;
   browsing shows what is there. The service decides what this account may see and whether an item's body
   may be fetched. This file only arranges and displays the record the service returned. It holds no token,
   keeps no body and writes nothing into browser storage.

   The owner, September 26, 2026: "we should use a searchable table format not a random HTML table/rows,
   also size, and digest are useless pieces of information to waste space on showing and we need ALL types
   of harness working directory component files not just SKILLS". So the table names every file's purpose,
   the kind of file a harness picks up, its label, the kinds of step it supports, its licence, its declared
   effects and the tools it is written for; it shows no size and no digest; and a search box, three filters
   and sortable columns narrow it without a second request (roadmap S-6.208). */
window.BaltorCatalogueBrowser = {
  create({request, element, message, current}) {
    const $ = id => document.getElementById(id);
    const path = "/api/v1/provisioning", downloadPath = "/api/v1/download";
    /* Version 2, as search asks: the same default step effects and the account's library setting, so this
       view lists what search can find and every answer names each item's library tier. Version 1 predates
       the tiers and lists Verified items only (September 25, 2026). */
    const requestVersion = "service_provisioning_request/v2";
    /* The exact record versions this file was written against. Another version may rename a field or
       give an existing field a different meaning, so a reply that carries one is refused as a whole and
       nothing from it is displayed. A newer service therefore needs a newer page, not a page that
       guesses. */
    const listVersion = "provisioning_list/v3", manifestVersion = "provisioning_manifest/v3";
    const itemVersion = "harness_intelligence_item/v1";
    /* Every item names its library tier and the exact label to show for it. An item without one is a record
       this page was not written for, never an item shown without its label. */
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
    const columns = [["purpose", "What it is for"], ["harness_kind", "Kind of file"], ["tier", "Label"],
      ["step_functions", "Step functions"], ["license", "Licence"], ["effects", "Declared effects"], ["styles", "Written for"]];
    let listed = null, shown = null, selected = "", active = false, sortKey = "harness_kind", sortAscending = true;
    const downloads = new Map();
    const eligible = () => current().connected && current().scopes.includes(metadataScope);
    const count = number => number + (number === 1 ? " item" : " items");
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
      if (!knownTiers.has(row.library_tier) || !stated(row.library_tier_label)) return "no library tier";
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
      if (!knownTiers.has(value.library_tier) || !stated(value.library_tier_label)) return "no library tier";
      return "";
    };
    const refused = "This service answered with a catalogue record this page was not written for, so nothing is shown.";
    const refusalText = value => {
      if (!value || value.record_type !== listVersion || !Array.isArray(value.items)
          || !Array.isArray(value.withheld) || !stated(value.tenant_id)) return refused;
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
      scope_required:"This account may not do that. Ask the person who runs this service for permission."};
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
    const toolsOf = row => (row.styles || []).filter(name => stated(name) && !harnessKindNames[name] && !/^[a-z_]+_(format|skill|agent|command|rule|manifest|hooks|settings|config|marketplace|schema|module)$/.test(name));
    const cells = row => ({
      purpose: row.purpose, harness_kind: harnessKindNames[harnessKindOf(row)], tier: row.library_tier_label,
      step_functions: functionsOf(row).join(", ") || "Not tagged", license: stated(row.license) ? row.license : "Not stated",
      effects: row.declared_effects.length ? row.declared_effects.join(", ") : "None declared",
      styles: toolsOf(row).join(", ") || "Every tool"});
    const searchable = row => [row.purpose, row.identity, harnessKindOf(row), harnessKindNames[harnessKindOf(row)],
      row.library_tier_label, ...functionsOf(row), row.license || "", ...(row.declared_effects || []), ...(row.styles || [])]
      .join(" ").toLowerCase();
    const clearDetail = text => $("browse-detail").replaceChildren(element("p", text, "caption"));
    function controls() {
      const ready = eligible() && !active;
      $("refresh-browse").disabled = !ready;
      for (const id of ["browse-search", "browse-kind", "browse-tier", "browse-style"]) $(id).disabled = !ready || !listed;
    }
    function reset() {
      listed = null; shown = null; selected = ""; active = false; downloads.clear();
      $("browse-table-body").replaceChildren(); $("browse-count").textContent = "Sign in to browse";
      $("browse-search").value = "";
      options($("browse-kind"), [], "Every kind of file"); options($("browse-tier"), [], "Every label"); options($("browse-style"), [], "Every tool");
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
    function sorted(rows) {
      const key = sortKey, direction = sortAscending ? 1 : -1;
      const value = row => key === "harness_kind" ? String(harnessKindOrder.indexOf(harnessKindOf(row))).padStart(2, "0")
        : key === "tier" ? (row.library_tier === "verified" ? "0" : "1") + row.purpose.toLowerCase()
        : String(cells(row)[key]).toLowerCase();
      return [...rows].sort((left, right) => {
        const first = value(left), second = value(right);
        if (first === second) return left.purpose.localeCompare(right.purpose) * direction;
        return first.localeCompare(second) * direction;
      });
    }
    function filtered() {
      const words = $("browse-search").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      const kind = $("browse-kind").value, tier = $("browse-tier").value, style = $("browse-style").value;
      return listed.filter(row => (!kind || harnessKindOf(row) === kind) && (!tier || row.library_tier === tier)
        && (!style || (row.styles || []).includes(style))
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
      for (const row of rows) {
        const line = document.createElement("tr");
        line.dataset.identity = row.identity; line.dataset.harnessKind = harnessKindOf(row); line.dataset.libraryTier = row.library_tier;
        line.setAttribute("aria-selected", row.identity === selected ? "true" : "false");
        const values = cells(row);
        for (const [key] of columns) {
          const cell = document.createElement("td");
          if (key === "purpose") {
            const button = element("button", values.purpose, "browse-open"); button.type = "button";
            button.addEventListener("click", () => choose(row));
            cell.append(button);
          } else if (key === "tier") {
            const badge = element("span", values.tier, "badge"); badge.dataset.libraryTier = row.library_tier; cell.append(badge);
          } else cell.textContent = values[key];
          line.append(cell);
        }
        body.append(line);
      }
      if (!rows.length) {
        const line = document.createElement("tr"), cell = document.createElement("td");
        cell.colSpan = columns.length; cell.className = "browse-empty";
        cell.textContent = listed && listed.length ? "Nothing matches your search and filters." : "Nothing is published for this account yet.";
        line.append(cell); body.append(line);
      }
      $("browse-count").textContent = listed && rows.length !== listed.length ? rows.length + " of " + count(listed.length) : count(rows.length);
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
    async function choose(row) {
      selected = row.identity;
      for (const line of $("browse-table-body").querySelectorAll("tr[data-identity]")) {
        line.setAttribute("aria-selected", line.dataset.identity === selected ? "true" : "false");
      }
      const epoch = current().generation;
      showDetail(row, null, "Checking this item with the service…");
      try {
        const value = await request(path, {record_type:requestVersion, operation:"manifest",
          identity:row.identity, expected_digest:row.digest});
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
          ["Label", value.library_tier_label],
          ["Step functions", shownValues.step_functions],
          ["Exact reference", row.identity],
          ["Where it comes from", value.source_ref],
          ["Licence", stated(value.license) ? value.license : "Not stated"],
          ["Declared effects", value.declared_effects.length ? value.declared_effects.join(", ") : "None declared"],
          ["Written for", toolsOf(value).length ? toolsOf(value).join(", ") : "No tool named, so it suits every tool"],
          ["Basis of its review", value.qualification_basis],
          ["The file itself", value.body_allowed ? "You may fetch it. Access is checked again on the way." : "Not granted to this account."]], "");
        if (!value.body_allowed) { note.textContent = "This account may read the details above, not the file."; return; }
        const button = element("button", "Fetch exact revision", "quiet");
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
          identity:row.identity, expected_digest:row.digest, request_id:downloads.get(key)}, true, true);
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
      } catch (error) {
        status.textContent = error.name === "AbortError"
          ? "The wait ended. Usage may have been recorded. Repeat this exact selection to reconcile it."
          : plainly(error.message);
      } finally { if (epoch === current().generation) button.disabled = false; }
    }
    /* One load brings the whole library this account may see; the search box and the filters narrow it
       here, so the service answers once. The page sends no authority over effects, so the service applies
       its default step effect, reading files, and material that declares any other effect is not offered. */
    async function load() {
      if (!eligible() || active) return;
      const epoch = current().generation;
      active = true; controls();
      message("browse-message", "Loading the library…");
      try {
        const value = await request(path, {record_type:requestVersion, operation:"list"});
        if (epoch !== current().generation) return;
        const refusal = refusalText(value);
        if (refusal) {
          listed = null; shown = null; selected = "";
          $("browse-table-body").replaceChildren(); $("browse-count").textContent = "Nothing shown";
          clearDetail("Nothing is shown for this reply.");
          message("browse-message", refusal, true);
          return;
        }
        listed = value.items; selected = ""; clearDetail("Open an item to read its details.");
        options($("browse-kind"), harnessKinds.filter(([name]) => listed.some(row => harnessKindOf(row) === name)), "Every kind of file");
        options($("browse-tier"), [["verified", "Verified"], ["community", "Community"]].filter(([name]) => listed.some(row => row.library_tier === name)), "Every label");
        // A development tool names itself. The page shows that name as it was published, never one it invented.
        options($("browse-style"), [...new Set(listed.flatMap(toolsOf))].sort().map(name => [name, name]), "Every tool");
        apply();
        /* The service holds material back for more than one reason: material this account may not see,
           and material that declares an effect such as running a command, for which this page carries no
           authority at all. */
        const withheld = value.withheld.length;
        message("browse-message", "Showing " + count(listed.length) + " for " + value.tenant_id + ". "
          + (withheld ? count(withheld) + (withheld === 1 ? " is" : " are")
            + " not offered here, because of this account's permissions or a declared effect this page holds no authority for. " : "")
          + "This table holds descriptions only. No file was fetched.");
      } catch (error) {
        if (epoch !== current().generation) return;
        message("browse-message", error.name === "AbortError"
          ? "The wait for the library ended. Nothing was loaded. Try again." : plainly(error.message), true);
      } finally { if (epoch === current().generation) { active = false; controls(); } }
    }
    $("refresh-browse").addEventListener("click", () => load());
    $("browse-search").addEventListener("input", () => apply());
    for (const id of ["browse-kind", "browse-tier", "browse-style"]) $(id).addEventListener("change", () => apply());
    reset();
    return {reset, connectionChanged, load};
  }
};
