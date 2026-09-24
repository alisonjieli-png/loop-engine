"use strict";
/* The pages of September 24, 2026: the service status, the demonstration of one task in five steps, and the facts on the
   protocol page. service.js chooses the view from the address; this file acts when its view opens.

   The status page shows only what the service's own records say, read by this browser when the page opens and again when the
   reader asks: the health record, service_health/v2 inside service_http_result/v1, and the capabilities record,
   service_capabilities/v1 inside the same envelope. A record of another version, an unreadable answer and a service that does not
   answer are said as such; no value is guessed, no history is kept and no uptime figure is shown. The health route answers 503 with
   the same record when the service is not ready, so that answer is read too, and it must agree with the record's own ready field.

   Each demonstration shows every step when this script does not run. When it runs, it shows one step at a time, moves between them
   by the list of steps, by Previous and Next or by Play, and shows each step's folder for the harness the reader picks. The folder
   roots below are the project skill locations of tools/install_selected_material.py; tools/test_showcase_pages.py compares them. */
(() => {
  const RESULT = "service_http_result/v1", HEALTH = "service_health/v2", CAPABILITIES = "service_capabilities/v1";
  const CATALOGUE = "service_catalogue_view/v1";
  const SKILL_ROOTS = {"claude-code": ".claude/skills/", "codex": ".agents/skills/", "opencode": ".opencode/skills/", "pi": ".pi/skills/"};
  /* Plain words for each check the health record names. A check this page has no words for is shown by its own name. */
  const CHECK_WORDS = {
    durable_store_answers: "Stored records answer",
    volume_has_write_headroom: "Storage has room to write",
    authentication_mode_installed: "Keys can be checked",
    catalogue_registered: "The library is loaded",
    catalogue_view_current: "The library view is current",
    interface_page_readable: "This website can be served",
    browser_identity_installed: "Email sign-in is set up",
    billing_sessions_installed: "Checkout is set up",
    billing_webhook_installed: "Payment notices can be received",
    billing_policy_current: "Payment settings are current",
    retention_sweep_current: "Old records are cleared on time",
    free_monthly_renewal_current: "Free monthly plans renew on time",
    readiness_within_deadline: "The health check finished in time"
  };
  const $ = id => document.getElementById(id);
  const element = (tag, text = "", className = "") => { const node = document.createElement(tag); if (text) node.textContent = text; if (className) node.className = className; return node; };
  const object = value => value !== null && typeof value === "object" && !Array.isArray(value);

  /* One public record: the answer's status and its body, or a refusal naming why it could not be read. */
  async function readRecord(path) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, {credentials: "omit", redirect: "error", cache: "no-store", signal: controller.signal, headers: {Accept: "application/json"}});
      let value = null;
      try { value = await response.json(); } catch (_) { value = null; }
      return {status: response.status, value};
    } finally { clearTimeout(timer); }
  }

  /* The health record, or null when the answer is not the version this page reads or disagrees with its own status. */
  const healthFrom = answer => {
    const value = answer?.value, result = object(value) ? value.result : null;
    if (!object(value) || value.record_type !== RESULT || !object(result) || result.record_type !== HEALTH) return null;
    if (typeof result.ready !== "boolean" || !Array.isArray(result.checks)) return null;
    if (!result.checks.every(check => object(check) && typeof check.name === "string" && typeof check.passed === "boolean" && typeof check.required === "boolean")) return null;
    if ((answer.status === 200) !== result.ready || ![200, 503].includes(answer.status)) return null;
    return result;
  };
  const capabilitiesFrom = answer => {
    const value = answer?.value, result = object(value) ? value.result : null;
    return answer?.status === 200 && object(value) && value.record_type === RESULT && object(result) && result.record_type === CAPABILITIES ? result : null;
  };

  /* The state the summary shows, from the health record alone. */
  const summaryOf = health => {
    if (!health) return {state: "unknown", word: "Could not be read", sentence: "The service did not answer, or answered with a record this page does not read. Try again in a minute."};
    const failedRequired = health.checks.filter(check => check.required && !check.passed).length;
    const failedOther = health.checks.filter(check => !check.required && !check.passed).length;
    if (!health.ready) return {state: "down", word: "Not working", sentence: failedRequired > 1
      ? failedRequired + " required checks have failed. Search and downloads may be refused until they pass."
      : failedRequired === 1 ? "One required check has failed. Search and downloads may be refused until it passes."
        : "The service says it is not ready. Search and downloads may be refused."};
    if (failedOther) return {state: "limited", word: "Working, with a limit", sentence: "Every required check passed. " + failedOther + " other check" + (failedOther === 1 ? " has" : "s have") + " failed; each is named below."};
    return {state: "working", word: "Working", sentence: "Every check passed when this page asked."};
  };

  const checkLabel = name => {
    const words = CHECK_WORDS[name];
    if (words) return document.createTextNode(words);
    const unknown = element("span"); unknown.append("Check ", element("code", name)); return unknown;
  };
  const drawChecks = (list, checks) => {
    list.replaceChildren(...checks.map(check => {
      const item = element("li", "", check.passed ? "is-passing" : "is-failing");
      item.append(element("span", check.passed ? "Passing" : "Failing", "status-state"), " ", element("span", "", "status-check-name"));
      item.lastChild.append(checkLabel(check.name));
      return item;
    }));
    if (!checks.length) list.replaceChildren(element("li", "None reported.", "is-empty"));
  };
  const drawFacts = (list, facts) => {
    list.replaceChildren(...facts.flatMap(([term, value]) => {
      const definition = element("dd");
      if (value instanceof Node) definition.append(value); else definition.textContent = value;
      return [element("dt", term), definition];
    }));
  };
  const code = text => element("code", text);
  /* Several short values, each kept whole on its line, for a list such as the protocol versions. */
  const values = list => { const holder = element("span", "", "fact-values"); list.forEach((value, place) => holder.append(...(place ? [" ", code(value)] : [code(value)]))); return holder; };
  const TRANSPORT_WORDS = {streamable_http: "Streamable HTTP"};
  const yesNo = (value, yes, no) => value === true ? yes : value === false ? no : "Not reported";

  let statusReading = 0;
  async function readStatus() {
    const ticket = ++statusReading, summary = $("status-summary");
    if (!summary) return;
    summary.dataset.statusState = "reading"; $("status-word").textContent = "Reading the service"; $("status-sentence").textContent = "This page asks the service now.";
    $("status-refresh").disabled = true;
    const [healthAnswer, capabilityAnswer] = await Promise.all([readRecord("/api/v1/health").catch(() => null), readRecord("/api/v1/capabilities").catch(() => null)]);
    if (ticket !== statusReading) return;
    const health = healthFrom(healthAnswer), capabilities = capabilitiesFrom(capabilityAnswer), shown = summaryOf(health);
    summary.dataset.statusState = shown.state; $("status-word").textContent = shown.word; $("status-sentence").textContent = shown.sentence;
    $("status-time").textContent = "Read at " + new Date().toLocaleTimeString() + ", your time";
    drawChecks($("status-required"), health ? health.checks.filter(check => check.required) : []);
    drawChecks($("status-other"), health ? health.checks.filter(check => !check.required) : []);
    const catalogue = health && object(health.catalogue_release) && health.catalogue_release.record_type === CATALOGUE ? health.catalogue_release : null;
    const viewCheck = health ? health.checks.find(check => check.name === "catalogue_view_current") : null;
    drawFacts($("status-library"), catalogue ? [
      ["Release", typeof catalogue.release_id === "string" && catalogue.release_id ? code(catalogue.release_id.slice(0, 8) + "…") : "Not reported"],
      ["Items", Number.isInteger(catalogue.items) ? String(catalogue.items) : "Not reported"],
      ["Library view", viewCheck ? (viewCheck.passed ? "Current" : "Not current") : "Not reported"],
      ["Built", Number.isFinite(catalogue.built_at) && catalogue.built_at > 0 ? new Date(catalogue.built_at * 1000).toLocaleString() : "Not reported"]
    ] : [["Library", health ? "Not reported by the service" : "Could not be read"]]);
    const website = object(capabilities?.website) ? capabilities.website : null, billing = object(capabilities?.billing) ? capabilities.billing : null;
    drawFacts($("status-accounts"), capabilities ? [
      ["New accounts", yesNo(website?.registration_available, "Open", "Closed")],
      ["Email sign-in", yesNo(website?.browser_identity_available, "Set up", "Not set up")],
      ["Subscriptions", yesNo(billing?.checkout, "Open", "Closed")]
    ] : [["Accounts", "Could not be read"]]);
    const protocol = object(capabilities?.protocol) ? capabilities.protocol : null;
    drawFacts($("status-connections"), capabilities ? [
      ["Protocol versions", Array.isArray(protocol?.versions) && protocol.versions.length ? values(protocol.versions.map(String)) : "Not reported"],
      ["Transport", typeof protocol?.transport === "string" ? TRANSPORT_WORDS[protocol.transport] || protocol.transport : "Not reported"],
      ["Service version", typeof health?.service_version === "string" && health.service_version ? health.service_version : "Not reported"]
    ] : [["Connections", "Could not be read"]]);
    $("status-refresh").disabled = false;
  }

  /* The protocol page names the versions the service reports and its own address, never a copy kept in this file. */
  async function readProtocol() {
    document.querySelectorAll("[data-protocol-endpoint]").forEach(node => { node.textContent = location.origin + "/mcp"; });
    const capabilities = capabilitiesFrom(await readRecord("/api/v1/capabilities").catch(() => null));
    const versions = capabilities && Array.isArray(capabilities.protocol?.versions) ? capabilities.protocol.versions.filter(value => typeof value === "string") : [];
    if (versions.length) document.querySelectorAll("[data-protocol-versions]").forEach(node => { node.textContent = versions.join(" and "); });
  }

  /* Each demonstration: one step at a time, moved by its list, by Previous and Next or by Play, which stops at the last step; the
     folder follows the harness the reader picks. The page holds several demonstrations, each set up on its own. */
  const players = [...document.querySelectorAll("[data-task-demo]")].map(demo => {
    const panels = [...demo.querySelectorAll("[data-task-step]")], links = [...demo.querySelectorAll("[data-task-go]")];
    const previous = demo.querySelector('[data-task-move="previous"]'), next = demo.querySelector('[data-task-move="next"]'), play = demo.querySelector("[data-task-play]");
    const harnesses = [...demo.querySelectorAll("[data-task-harness]")];
    let current = 0, timer = null;
    const select = (index, moveFocus) => {
      current = Math.max(0, Math.min(panels.length - 1, index));
      panels.forEach((panel, place) => { panel.hidden = place !== current; });
      links.forEach((link, place) => { if (place === current) link.setAttribute("aria-current", "step"); else link.removeAttribute("aria-current"); link.classList.toggle("is-done", place < current); });
      previous.disabled = current === 0; next.disabled = current === panels.length - 1;
      if (moveFocus) { const heading = panels[current].querySelector("h3"); heading.tabIndex = -1; heading.focus({preventScroll: true}); }
    };
    const stop = () => { if (timer) clearInterval(timer); timer = null; play.setAttribute("aria-pressed", "false"); play.textContent = "Play the steps"; };
    links.forEach((link, place) => link.addEventListener("click", event => { event.preventDefault(); stop(); select(place, true); }));
    previous.addEventListener("click", () => { stop(); select(current - 1, true); });
    next.addEventListener("click", () => { stop(); select(current + 1, true); });
    play.addEventListener("click", () => {
      if (timer) { stop(); return; }
      if (current === panels.length - 1) select(0, false);
      play.setAttribute("aria-pressed", "true"); play.textContent = "Pause";
      timer = setInterval(() => { if (current >= panels.length - 1) stop(); else select(current + 1, false); }, 3500);
    });
    harnesses.forEach(button => button.addEventListener("click", () => {
      const root = SKILL_ROOTS[button.dataset.taskHarness];
      if (!root) return;
      demo.querySelectorAll("[data-task-skill-root]").forEach(node => { node.textContent = root; });
      harnesses.forEach(other => other.setAttribute("aria-pressed", String(other === button)));
    }));
    demo.querySelector("[data-task-controls]").hidden = false;
    select(0, false);
    return stop;
  });
  const stopPlaying = () => players.forEach(stop => stop());

  /* Each view acts when it opens: service.js marks the open view on the body. */
  let opened = "";
  const onView = () => {
    const page = document.body.dataset.page || "";
    if (page === opened) return;
    stopPlaying();
    opened = page;
    if (page === "status") readStatus();
    if (page === "for-protocol-and-client") readProtocol();
  };
  $("status-refresh")?.addEventListener("click", readStatus);
  new MutationObserver(onView).observe(document.body, {attributes: true, attributeFilter: ["data-page"]});
  onView();
})();
