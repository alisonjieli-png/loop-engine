"use strict";
/* Browsing the material published for one account. Search answers a question; browsing shows what is
   there. The service decides what this account may see, which group an item belongs to and whether its
   body may be fetched. This file only arranges and displays the record the service returned. It holds
   no token, keeps no body and writes nothing into browser storage. */
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
    /* The four groups, with the plain name each one carries in this view, and before them the files a
       development tool reads as they are: skills, agent instructions and similar drop-in files. Those
       are the harness family, whose bodies live in their own source layer, so they are not one of the
       four groups. A service serves only that family unless its host declares another, so the group
       comes first. It is shown only when the service offers such an item, and it says that it sits
       beside the four groups. Until September 22, 2026 it was named for material already on the
       reader's machine, which was not true of a file the service delivers. */
    const groups = [
      {layer:"harness_local", name:"Files for your development tools", outside:true,
       note:"Skills, agent instructions and other files your development tool reads as they are. They sit beside the four groups below."},
      {layer:"context_intelligence", name:"Guidance and methods",
       note:"Written help, procedures and checklists for a step of your task."},
      {layer:"code_intelligence", name:"Reusable code and tools",
       note:"Code and tools that were reviewed before they were published here."},
      {layer:"runtime_history_solution_intelligence", name:"What worked before",
       note:"Records of earlier work that can be read again."},
      {layer:"user_feedback_intelligence", name:"Your own instructions",
       note:"Instructions your account added for its own work."}];
    const kindNames = {reusable_code:"Reusable code", skill:"Skill", tool:"Tool", instruction_file:"Instructions"};
    const knownLayers = new Set(groups.map(group => group.layer)), knownKinds = Object.keys(kindNames);
    let listed = null, shown = null, selected = "", active = false;
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
      if (!Number.isInteger(row.size_bytes) || row.size_bytes < 0) return "an unreadable size";
      if (!Array.isArray(row.declared_effects) || !Array.isArray(row.styles)) return "an unreadable list of declared values";
      if (typeof row.body_allowed !== "boolean") return "no plain answer about downloading";
      if (!knownTiers.has(row.library_tier) || !stated(row.library_tier_label)) return "no library tier";
      return "";
    };
    /* One item, asked for by name. It carries the same facts as a list entry under its own record
       version, so it is checked the same way before a single value of it is displayed. */
    const manifestProblem = (value, row) => {
      if (!value || typeof value !== "object" || value.record_type !== manifestVersion) return "an unsupported item version";
      if (value.identity !== row.identity) return "another item";
      if (!/^[0-9a-f]{64}$/.test(String(value.digest))) return "a missing digest";
      if (!stated(value.source_ref) || !stated(value.qualification_basis)) return "a missing description";
      if (!Number.isInteger(value.size_bytes) || value.size_bytes < 0) return "an unreadable size";
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
      selected_body_digest_mismatch:"This item changed since the list was loaded. Load the catalogue again before fetching it.",
      item_withheld:"This item is no longer offered to this account. Load the catalogue again to see what is there now.",
      item_unavailable:"This item is no longer available to this account. Load the catalogue again to see what is there now.",
      body_forbidden:"This account may read the details of this item, not the file.",
      body_reader_unavailable:"This service cannot hand out files at the moment. The details above are unchanged.",
      meter_unavailable:"This service cannot record usage at the moment, so it did not send the file.",
      scope_required:"This account may not do that. Ask the person who runs this service for permission."};
    const plainly = text => {
      const named = /^Service refused the request: ([a-z_]+)\.$/.exec(text);
      return named && refusals[named[1]] ? refusals[named[1]] : text;
    };
    const clearDetail = text => $("browse-detail").replaceChildren(element("p", text, "caption"));
    function controls() {
      const ready = eligible() && !active;
      $("refresh-browse").disabled = !ready;
      $("browse-kind").disabled = !ready || !listed || $("browse-kind").options.length < 2;
      $("browse-style").disabled = !ready || !listed || $("browse-style").options.length < 2;
    }
    function reset() {
      listed = null; shown = null; selected = ""; active = false; downloads.clear();
      $("browse-groups").replaceChildren(); $("browse-count").textContent = "Sign in to browse";
      for (const id of ["browse-kind", "browse-style"]) {
        $(id).replaceChildren(element("option", id === "browse-kind" ? "Every kind" : "Every tool"));
        $(id).options[0].value = "";
      }
      clearDetail("Open an item to read its details.");
      message("browse-message", "Sign in to browse the material published for your account.");
      controls();
    }
    function connectionChanged() {
      controls();
      if (eligible()) message("browse-message", "Load the catalogue to see every item your account may use.");
      else if (current().connected) message("browse-message",
        "This account may not list material. Ask the person who runs this service for permission to search and list.", true);
    }
    /* A control shows the request that was sent, never a request the reader only started to make. The
       choices come from the unfiltered catalogue, so a filter can always be undone, and the selected
       value is the one this reply was asked for. */
    function options(select, values, plainName, chosen) {
      select.replaceChildren(element("option", select.id === "browse-kind" ? "Every kind" : "Every tool"));
      select.options[0].value = "";
      for (const value of values) { const choice = element("option", plainName(value)); choice.value = value; select.append(choice); }
      select.value = [...select.options].some(choice => choice.value === chosen) ? chosen : "";
    }
    function render(rows, total, filtered) {
      const groupsElement = $("browse-groups");
      groupsElement.replaceChildren();
      for (const group of groups) {
        const held = rows.filter(row => row.source_layer === group.layer);
        if (group.outside && !held.length) continue;
        const section = element("section", "", "browse-group");
        section.dataset.layer = group.layer;
        const heading = element("div", "", "browse-group-heading");
        heading.append(element("h3", group.name), element("span", count(held.length), "badge"));
        section.append(heading, element("p", group.note, "caption"));
        if (!held.length) section.append(element("p", filtered
          ? "Nothing in this group matches your filters." : "Nothing is published in this group yet.", "browse-empty"));
        else {
          const list = element("ul", "", "browse-list");
          for (const row of held) {
            const line = document.createElement("li");
            const button = element("button", "", "browse-item");
            button.type = "button"; button.dataset.identity = row.identity;
            button.setAttribute("aria-current", row.identity === selected ? "true" : "false");
            button.append(element("span", row.purpose, "browse-item-name"),
              element("span", row.library_tier_label + " · " + (kindNames[row.kind] || row.kind) + " · " + row.size_bytes + " bytes · "
                + (row.body_allowed ? "download permitted" : "details only"), "browse-item-facts"));
            button.addEventListener("click", () => choose(row));
            line.append(button); list.append(line);
          }
          section.append(list);
        }
        groupsElement.append(section);
      }
      $("browse-count").textContent = rows.length === total ? count(rows.length) : rows.length + " of " + count(total);
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
       carry the same digest; a different one means the page must not offer a download of what it listed. */
    async function choose(row) {
      selected = row.identity;
      for (const button of $("browse-groups").querySelectorAll(".browse-item")) {
        button.setAttribute("aria-current", button.dataset.identity === selected ? "true" : "false");
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
          throw new Error("This item changed since the list was loaded. Load the catalogue again before fetching it.");
        }
        const note = showDetail(row, [
          ["What it is for", row.purpose],
          ["Library tier", value.library_tier_label],
          ["Exact reference", row.identity],
          ["Where it comes from", value.source_ref],
          ["Licence", stated(value.license) ? value.license : "Not stated"],
          ["Size", value.size_bytes + " bytes"],
          ["Digest", value.digest],
          ["Declared effects", value.declared_effects.length ? value.declared_effects.join(", ") : "None declared"],
          ["Written for", value.styles.length ? value.styles.join(", ") : "No tool named, so it suits every tool"],
          ["Basis of its review", value.qualification_basis],
          ["The file itself", value.body_allowed ? "You may fetch it. Access is checked again on the way." : "Not granted to this account."]], "");
        if (!value.body_allowed) { note.textContent = "This account may read the details above, not the file."; return; }
        const button = element("button", "Fetch exact revision", "quiet");
        button.type = "button"; button.id = "browse-download";
        button.addEventListener("click", () => fetchBody(row, button, note));
        note.textContent = "Fetching this file records usage. The digest is checked against the bytes that arrive.";
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
        status.textContent = "Downloaded. Digest verified. Loading it into your own tool and accepting the result are separate steps.";
      } catch (error) {
        status.textContent = error.name === "AbortError"
          ? "The wait ended. Usage may have been recorded. Repeat this exact selection to reconcile it."
          : plainly(error.message);
      } finally { if (epoch === current().generation) button.disabled = false; }
    }
    /* The service applies the filters, because it owns the rule about which material a request may see.
       The page sends no authority over effects, so the service applies its default step effect, reading
       files, and material that declares any other effect is not offered here. The choices themselves come
       from an unfiltered load, so a filter can always be undone. */
    async function load(fresh) {
      if (!eligible() || active) return;
      const epoch = current().generation, kind = fresh ? "" : $("browse-kind").value, style = fresh ? "" : $("browse-style").value;
      active = true; controls();
      message("browse-message", fresh ? "Loading the catalogue…" : "Applying your filters…");
      try {
        const value = await request(path, {record_type:requestVersion, operation:"list",
          ...(kind ? {kinds:[kind]} : {}), ...(style ? {style} : {})});
        if (epoch !== current().generation) return;
        const refusal = refusalText(value);
        if (refusal) {
          listed = null; shown = null; selected = "";
          $("browse-groups").replaceChildren(); $("browse-count").textContent = "Nothing shown";
          clearDetail("Nothing is shown for this reply.");
          message("browse-message", refusal, true);
          return;
        }
        if (fresh) { listed = value.items; selected = ""; clearDetail("Open an item to read its details."); }
        options($("browse-kind"), knownKinds.filter(name => listed.some(row => row.kind === name)), value => kindNames[value], kind);
        // A development tool names itself. The page shows that name as it was published, never one it invented.
        options($("browse-style"), [...new Set(listed.flatMap(row => row.styles))].filter(stated).sort(), value => value, style);
        shown = value.items;
        if (selected && !shown.some(row => row.identity === selected)) { selected = ""; clearDetail("Open an item to read its details."); }
        render(shown, listed.length, Boolean(kind || style));
        /* The service holds material back for more than one reason, and only some of them are the
           filters. It also holds back material this account may not see, and material that declares an
           effect such as running a command, for which this page carries no authority at all. The
           sentence names the reasons that can apply to the request that was actually sent. */
        const withheld = value.withheld.length;
        message("browse-message", "Showing " + count(shown.length) + " for " + value.tenant_id + ". "
          + (withheld ? count(withheld) + (kind || style
              ? " did not match the filters, this account's permissions, or a declared effect this page holds no authority for. "
              : (withheld === 1 ? " is" : " are")
                + " not offered here, because of this account's permissions or a declared effect this page holds no authority for. ") : "")
          + "This list holds descriptions only. No file was fetched.");
      } catch (error) {
        if (epoch !== current().generation) return;
        message("browse-message", error.name === "AbortError"
          ? "The wait for the catalogue ended. Nothing was loaded. Try again." : plainly(error.message), true);
      } finally { if (epoch === current().generation) { active = false; controls(); } }
    }
    $("refresh-browse").addEventListener("click", () => load(true));
    for (const id of ["browse-kind", "browse-style"]) $(id).addEventListener("change", () => load(false));
    reset();
    return {reset, connectionChanged, load};
  }
};
