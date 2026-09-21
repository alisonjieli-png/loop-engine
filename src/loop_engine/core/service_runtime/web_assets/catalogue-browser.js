"use strict";
/* Browsing the material published for one account. Search answers a question; browsing shows what is
   there. The service decides what this account may see, which group an item belongs to and whether its
   body may be fetched. This file only arranges and displays the record the service returned. It holds
   no token, keeps no body and writes nothing into browser storage. */
window.BaltorCatalogueBrowser = {
  create({request, element, message, current}) {
    const $ = id => document.getElementById(id);
    const path = "/api/v1/provisioning", downloadPath = "/api/v1/download";
    const requestVersion = "service_provisioning_request/v1";
    /* The exact record versions this file was written against. Another version may rename a field or
       give an existing field a different meaning, so a reply that carries one is refused as a whole and
       nothing from it is displayed. A newer service therefore needs a newer page, not a page that
       guesses. */
    const listVersion = "provisioning_list/v2", manifestVersion = "provisioning_manifest/v2";
    const itemVersion = "harness_intelligence_item/v1";
    const metadataScope = "provisioning:metadata";
    /* The four groups, with the plain name each one carries in this view. A fifth place holds material
       whose body already sits on the reader's own machine. It is shown only when the service offers
       such an item, and it says that it is outside the four groups. */
    const groups = [
      {layer:"context_intelligence", name:"Guidance and methods",
       note:"Written help, procedures and checklists for a step of your task."},
      {layer:"code_intelligence", name:"Reusable code and tools",
       note:"Code and tools that were reviewed before they were published here."},
      {layer:"runtime_history_solution_intelligence", name:"What worked before",
       note:"Records of earlier work that can be read again."},
      {layer:"user_feedback_intelligence", name:"Your own instructions",
       note:"Instructions your account added for its own work."},
      {layer:"harness_local", name:"Already on your own machine", outside:true,
       note:"These point at files your own setup holds. They are not part of the four groups above."}];
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
      return "";
    };
    const refused = "This service answered with a catalogue record this page was not written for, so nothing is shown.";
    const refusalText = value => {
      if (!value || value.record_type !== listVersion || !Array.isArray(value.items) || !stated(value.tenant_id)) return refused;
      const problems = [...new Set(value.items.map(itemProblem).filter(Boolean))];
      return problems.length ? refused + " The catalogue holds entries with " + problems.join(", ") + "." : "";
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
    function options(select, values, names) {
      const previous = select.value;
      select.replaceChildren(element("option", select.id === "browse-kind" ? "Every kind" : "Every tool"));
      select.options[0].value = "";
      for (const value of values) { const choice = element("option", names[value] || value); choice.value = value; select.append(choice); }
      select.value = [...select.options].some(choice => choice.value === previous) ? previous : "";
    }
    function render(rows, total) {
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
        if (!held.length) section.append(element("p", "Nothing is published in this group yet.", "browse-empty"));
        else {
          const list = element("ul", "", "browse-list");
          for (const row of held) {
            const line = document.createElement("li");
            const button = element("button", "", "browse-item");
            button.type = "button"; button.dataset.identity = row.identity;
            button.setAttribute("aria-current", row.identity === selected ? "true" : "false");
            button.append(element("span", row.purpose, "browse-item-name"),
              element("span", (kindNames[row.kind] || row.kind) + " · " + row.size_bytes + " bytes · "
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
        if (!value || value.record_type !== manifestVersion || value.identity !== row.identity) {
          throw new Error("This service answered with an item record this page was not written for. Nothing is shown for it.");
        }
        if (value.digest !== row.digest) {
          throw new Error("This item changed since the list was loaded. Load the catalogue again before fetching it.");
        }
        const note = showDetail(row, [
          ["What it is for", row.purpose],
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
        note.textContent = "Fetching records usage. The digest is checked against the bytes that arrive.";
        $("browse-detail").insertBefore(button, note);
      } catch (error) {
        if (epoch !== current().generation || selected !== row.identity) return;
        showDetail(row, null, error.name === "AbortError"
          ? "The wait for this item ended. Nothing was fetched. Select it again." : error.message);
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
        if (epoch !== current().generation || result.epoch !== current().generation) return;
        const objectUrl = URL.createObjectURL(new Blob([result.bytes], {type:"application/octet-stream"}));
        const link = element("a", "Download");
        link.href = objectUrl; link.download = "intelligence-" + measured.slice(0, 12) + ".txt"; link.click();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        status.textContent = "Downloaded. Digest verified. Loading it into your own tool and accepting the result are separate steps.";
      } catch (error) {
        status.textContent = error.name === "AbortError"
          ? "The wait ended. Usage may have been recorded. Repeat this exact selection to reconcile it."
          : error.message;
      } finally { if (epoch === current().generation) button.disabled = false; }
    }
    /* The service applies the filters, because it owns the rule about which material a request may see.
       The page sends no authority over effects, so material that declares an effect is never offered
       here. The choices themselves come from an unfiltered load, so a filter can always be undone. */
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
        if (fresh) {
          listed = value.items;
          options($("browse-kind"), knownKinds.filter(name => listed.some(row => row.kind === name)), kindNames);
          options($("browse-style"), [...new Set(listed.flatMap(row => row.styles))].sort(), {});
          selected = ""; clearDetail("Open an item to read its details.");
        }
        shown = value.items;
        if (!shown.some(row => row.identity === selected)) { selected = ""; clearDetail("Open an item to read its details."); }
        render(shown, listed.length);
        const withheld = Array.isArray(value.withheld) ? value.withheld.length : 0;
        message("browse-message", "Showing " + count(shown.length) + " for " + value.tenant_id + ". "
          + (withheld ? count(withheld) + " were held back by the filters or by this account's permissions. " : "")
          + "This list holds descriptions only. No file was fetched.");
      } catch (error) {
        if (epoch !== current().generation) return;
        message("browse-message", error.name === "AbortError"
          ? "The wait for the catalogue ended. Nothing was loaded. Try again." : error.message, true);
      } finally { if (epoch === current().generation) { active = false; controls(); } }
    }
    $("refresh-browse").addEventListener("click", () => load(true));
    for (const id of ["browse-kind", "browse-style"]) $(id).addEventListener("change", () => load(false));
    reset();
    return {reset, connectionChanged, load};
  }
};
