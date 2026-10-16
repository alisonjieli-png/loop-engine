"use strict";
/* The staff Systems view at /admin/systems (roadmap S-6.35.11). It draws what GET /api/v1/admin/systems returns: what the
   running service measures now, labelled as live with its read time, and the facts recorded in the repository's release,
   catalogue and edge records, each with its source revision, environment, attempt, time and record. The five result
   states are drawn in five separate lists and never merged. The service decides who may read it; this file only draws the
   answer and holds no data of its own. */
window.BaltorSystemsView = (() => {
  const STATES = ["failed", "pending", "skipped", "unknown", "passed"];
  const STATE_NAMES = {failed:"Failed", pending:"Pending", skipped:"Skipped", unknown:"Unknown", passed:"Passed"};
  const RESULT = "service_staff_systems/v1", LIVE = "service_staff_systems_live/v1", ENDPOINT = "/api/v1/admin/systems";
  const COMPARISONS = {agrees:"agrees with the newest release record", differs:"differs from the newest release record",
    not_stated:"not stated in the section", not_recorded:"not in the newest release record"};
  function create({request, element, message, said, failureState, current, signIn}) {
    const $ = id => document.getElementById(id);
    let epoch = 0, open = false;
    const pages = {};
    const text = value => value === null || value === undefined || value === "" ? "not recorded" : String(value);
    const moment = value => typeof value === "number" ? new Date(value * 1000).toISOString().replace(".000Z", "Z") : text(value);
    const short = value => typeof value === "string" && /^[0-9a-f]{40}$/.test(value) ? value.slice(0, 12) : text(value);
    function row(item) {
      const article = element("article", "", "result"); article.dataset.state = item.state;
      article.append(element("h3", item.check), element("span", STATE_NAMES[item.state] || item.state, "badge"),
        element("p", item.observed));
      const revision = item.source_revision ? short(item.source_revision) + (item.revision_basis === "row" ? " (this row's record)" : " (the release record)") : "not recorded";
      article.append(element("p", [item.entry_title ? "Entry: " + item.entry_title : "", "Revision: " + revision,
        "Environment: " + item.environment_or_host, "Attempt: " + text(item.attempt), "Time: " + moment(item.at)].filter(Boolean).join(" · "), "caption"),
        element("p", "Record: " + item.evidence + (item.pointer ? "#" + item.pointer : ""), "caption"));
      return article;
    }
    function rows(target, items, empty) {
      target.replaceChildren(...items.map(row));
      if (!items.length) target.append(element("p", empty, "empty"));
    }
    function facts(target, entries) {
      target.replaceChildren();
      for (const [name, value] of entries) { const group = document.createElement("div"); group.append(element("dt", name), element("dd", text(value))); target.append(group); }
    }
    function clear() {
      epoch++;
      for (const state of STATES) { pages[state] = 0; $("systems-state-" + state).replaceChildren(); $("systems-more-" + state).hidden = true; }
      ["systems-live-facts", "systems-live-checks", "systems-current-facts", "systems-newest-rows", "systems-entries", "systems-entry-detail"].forEach(id => $(id).replaceChildren());
      ["systems-live-note", "systems-current-note", "systems-newest-note"].forEach(id => { $(id).textContent = ""; });
      $("systems-view").hidden = true; $("refresh-systems").disabled = true;
    }
    function signedOut() {
      clear(); $("systems-login").hidden = false;
      message("systems-message", "Sign in with a staff account to read this view. The service checks the role on every request.");
    }
    function live(value) {
      if (!value || value.record_type !== LIVE || !value.health) { $("systems-live-note").textContent = "The live reading is not available in this answer."; return; }
      const health = value.health;
      $("systems-live-note").textContent = "Live: " + value.source + ", read at " + value.read_at + ". It is not a recorded fact and changes on every read.";
      facts($("systems-live-facts"), [["Alive", health.alive ? "yes" : "no"], ["Ready", health.ready ? "yes" : "no"],
        ["Service version", health.service_version], ["Release reference", health.release_reference || "not stated by the host"],
        ...(health.catalogue_release && typeof health.catalogue_release === "object"
          ? Object.entries(health.catalogue_release).filter(([, item]) => item === null || typeof item !== "object").map(([name, item]) => ["Catalogue " + name.replaceAll("_", " "), item]) : [])]);
      rows($("systems-live-checks"), (health.checks || []).map(check => ({check:check.name.replaceAll("_", " "), state:check.passed ? "passed" : "failed",
        observed:(check.required ? "Required" : "Reported, not required") + (check.code ? "; code " + check.code : ""),
        source_revision:null, environment_or_host:"this service process", attempt:"this request", at:value.read_at, evidence:"live reading", pointer:""})), "No check was measured.");
    }
    function deployment(value, newest) {
      const stated = value.stated || {}, comparison = value.comparison || {};
      $("systems-current-note").textContent = "As stated in " + value.statement + " (" + value.section + "), compared field by field with " + value.newest_release_evidence + ".";
      $("systems-current-facts").replaceChildren(...Object.keys(stated).map(name => {
        const article = element("article", "", "result"); article.dataset.state = comparison[name] === "agrees" ? "passed" : comparison[name] === "differs" ? "failed" : "unknown";
        article.append(element("h3", name.replaceAll("_", " ")), element("span", comparison[name] === "agrees" ? "Agrees" : comparison[name] === "differs" ? "Differs" : "Not compared", "badge"),
          element("p", text(stated[name]) + ": " + (COMPARISONS[comparison[name]] || "not compared")));
        return article;
      }));
      if (newest) {
        const entry = newest.entry;
        $("systems-newest-note").textContent = [entry.title, "Time: " + moment(entry.at), "Revision: " + text(entry.source_revision),
          "Environment: " + entry.environment_or_host, "Image: " + text(entry.image), "Rollback: " + (entry.rollback ? "release " + text(entry.rollback.release) : "not recorded"),
          "Record: " + entry.evidence].join(" · ");
        rows($("systems-newest-rows"), newest.rows, "This release record holds no check this view can read.");
      }
    }
    function entries(list) {
      $("systems-entries").replaceChildren(...list.map(entry => {
        const article = element("article", "", "result"), button = element("button", "Open every row", "quiet");
        button.type = "button"; button.addEventListener("click", () => detail(entry.id).catch(failed("systems-message")));
        article.append(element("h3", entry.title), element("span", entry.kind.replaceAll("_", " "), "badge"),
          element("p", ["Time: " + moment(entry.at), "Revision: " + short(entry.source_revision), "Environment: " + entry.environment_or_host, "Record: " + entry.evidence].join(" · ")), button);
        return article;
      }));
    }
    async function detail(id) {
      const mine = epoch, value = await request(ENDPOINT + "?" + new URLSearchParams({entry:id}));
      if (mine !== epoch || value.record_type !== RESULT || value.view !== "entry") return;
      const target = $("systems-entry-detail"), heading = element("h3", value.entry.title + ": every recorded row");
      const list = document.createElement("div"); list.className = "admin-rows"; rows(list, value.rows, "This record holds no check this view can read.");
      target.replaceChildren(heading, element("p", "Earlier attempts stay listed beside later ones. Record: " + value.entry.evidence, "caption"), list);
      heading.tabIndex = -1; heading.focus({preventScroll:false});
    }
    async function more(state) {
      const mine = epoch, page = (pages[state] || 0) + 1;
      const value = await request(ENDPOINT + "?" + new URLSearchParams({state, page:String(page)}));
      if (mine !== epoch || value.record_type !== RESULT || value.view !== "state" || value.state !== state) return;
      pages[state] = page;
      const target = $("systems-state-" + state);
      if (page === 1) target.replaceChildren();
      for (const item of value.rows) target.append(row(item));
      if (page === 1 && !value.rows.length) target.append(element("p", "None recorded in this state.", "empty"));
      $("systems-more-" + state).hidden = value.has_next !== true;
    }
    const failed = id => error => {
      if (error && error.status === 401) { signedOut(); signIn?.(); return; }
      message(id, said(error), failureState(error));
    };
    async function load() {
      const state = current();
      if (!state.connected) { signedOut(); return; }
      $("systems-login").hidden = true;
      if (!state.staff) { clear(); message("systems-message", "This view is for Baltor staff. Your account is signed in, and the service refuses it here.", "refused"); return; }
      if (!state.permitted) { clear(); message("systems-message", "Your staff role does not include the Systems view. It needs the service diagnostics permission.", "refused"); return; }
      const mine = ++epoch; message("systems-message", "Reading the recorded facts and the live health…", "loading");
      const value = await request(ENDPOINT);
      if (mine !== epoch) return;
      if (value.record_type !== RESULT || value.view !== "overview") throw Error("The Systems answer could not be read.");
      $("systems-view").hidden = false; $("refresh-systems").disabled = false;
      live(value.live); deployment(value.current_deployment, value.newest); entries(value.entries);
      for (const state of STATES) { pages[state] = 0; await more(state); if (mine !== epoch) return; }
      message("systems-message", "Recorded facts from " + value.record.generated_by + ", record digest " + value.record.sha256.slice(0, 12) + ". Each state is listed separately below.");
    }
    function show() { open = true; load().catch(failed("systems-message")); }
    function connectionChanged() { if (open) show(); }
    for (const state of STATES) $("systems-more-" + state).addEventListener("click", () => more(state).catch(failed("systems-message")));
    $("refresh-systems").addEventListener("click", () => load().catch(failed("systems-message")));
    /* Signing out clears every drawn fact at once; on this view the page then offers sign-in again. */
    function reset() { clear(); if (open) signedOut(); }
    return {show, reset, connectionChanged, hide:() => { open = false; }};
  }
  return {create, STATES};
})();
