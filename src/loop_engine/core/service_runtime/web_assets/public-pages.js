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

  /* The homepage terminal, September 26, 2026: the folder of one step for the harness the reader picks. The skill folder is the
     placement tool's own, SKILL_ROOTS above; the instruction file is the one that harness reads, and the connection entry is the
     file its reviewed recipe in client-recipes.json names. The search and the download above the folder are the same for every
     harness, so they do not change. Without this script the folder stays the Claude Code one the page serves. */
  const HERO_FILES = {"claude-code": {instructions: "CLAUDE.md", tools: ".mcp.json"}, codex: {instructions: "AGENTS.md", tools: ".codex/config.toml"},
    opencode: {instructions: "AGENTS.md", tools: "opencode.json"}, pi: {instructions: "AGENTS.md", tools: ".pi/baltor.json"},
    "baltor-harness": {instructions: "task.md", tools: "loop-engine solve"}};
  /* The Baltor Harness has no skill folder, so it has no entry in SKILL_ROOTS: the placement tool's own profile
     declares no native location for it and refuses every kind with its reason. It is still a tab, because the owner
     asked for all five to be visible there. Picking it shows what is true: the task file it reads, no skill folder,
     and the refusal the placement tool returns. */
  const NO_SKILL_FOLDER = "no skill folder";
  const heroHarnesses = document.querySelector("[data-hero-harnesses]");
  const pickHeroHarness = harness => {
    const files = HERO_FILES[harness], root = SKILL_ROOTS[harness];
    if (!files) return;
    heroHarnesses.querySelectorAll("[data-hero-harness]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.heroHarness === harness)));
    const write = (name, text) => document.querySelectorAll('[data-hero-file="' + name + '"]').forEach(node => { node.textContent = text; });
    write("instructions", files.instructions);
    write("skills", root || "no skill folder");
    write("tools", files.tools);
    if (window.__baltorPaintTree) window.__baltorPaintTree();
  };
  heroHarnesses?.addEventListener("click", event => {
    const button = event.target.closest("[data-hero-harness]");
    if (button) pickHeroHarness(button.dataset.heroHarness);
  });

  /* Three worked steps, not one small one. Each names the chain of components a step actually needs, the folder it
     assembles, and what the step replaces. The first is the recorded run the service verified; the other two are
     worked examples over components the library serves today, labelled as examples so no reader mistakes a planned
     run for a measured one. Hovering or focusing a name swaps the whole terminal: the query, the search results, the
     download, the file tree and the saving. */
  const HERO_SCENARIOS = {
    "dedupe": {
      label: "Deduplicate a customer table",
      outcome: "17,000 rows in, 15,940 out: 1,060 duplicates found and merged without deleting a row",
      query: "find duplicate customer records",
      results: [
        {name: "find_duplicate_records_with_blocking_keys", kind: "skill", licence: "MIT", size: "2.7 KB", digest: "f3f1d0ab"},
        {name: "score_duplicate_pairs_by_weakest_signal", kind: "skill", licence: "MIT", size: "2.6 KB", digest: "55177178"}
      ],
      chosen: 0,
      step: "step-3-find-duplicates",
      tree: ["CLAUDE.md", ".claude/skills/", "find-duplicate-records-with-blocking-keys/", "SKILL.md", ".mcp.json", ".baltor/step.lock.json"],
      replaces: "reading the whole table by hand to decide which rows are the same customer"
    },
    "overnight": {
      label: "Fix a failing metric overnight",
      outcome: "a validation gap found and closed at 04:12, the run finished before anyone logged in",
      query: "choose metrics and read the validation gap",
      results: [
        {name: "orient_on_a_task_and_write_its_contracts", kind: "skill", licence: "MIT", size: "3.1 KB", digest: "9a2c41de"},
        {name: "read_the_train_validation_gap", kind: "skill", licence: "MIT", size: "2.4 KB", digest: "7d5e0b13"},
        {name: "decide_whether_a_step_needs_a_model", kind: "skill", licence: "MIT", size: "1.9 KB", digest: "c40a8f62"}
      ],
      chosen: 1,
      step: "step-2-close-the-validation-gap",
      tree: ["CLAUDE.md", ".claude/skills/", "read-the-train-validation-gap/", "SKILL.md", "contracts/", "task.schema.json", ".mcp.json", ".baltor/step.lock.json"],
      replaces: "a whole night of reading notebooks to find why the score stopped moving"
    },
    "handoff": {
      label: "Hand a finished result over",
      outcome: "one page naming what was observed, what was derived, and what is still unknown",
      query: "report what was observed and what is unknown",
      results: [
        {name: "report_observed_derived_assumed_and_unknown", kind: "skill", licence: "MIT", size: "2.2 KB", digest: "b1e75a30"},
        {name: "escalate_uncertain_values_with_candidates", kind: "skill", licence: "MIT", size: "2.0 KB", digest: "3e6c9d47"}
      ],
      chosen: 0,
      step: "step-5-report-the-result",
      tree: ["CLAUDE.md", ".claude/skills/", "report-observed-derived-assumed-and-unknown/", "SKILL.md", "report.md", "evidence/", ".mcp.json", ".baltor/step.lock.json"],
      replaces: "writing a confident answer that hides which part was never checked"
    }
  };
  const heroScenarioButtons = document.querySelectorAll("[data-hero-scenario]");
  const paintScenario = key => {
    const scenario = HERO_SCENARIOS[key];
    const terminal = document.querySelector(".hero-terminal");
    if (!scenario || !terminal) return;
    terminal.dataset.heroScenario = key;
    heroScenarioButtons.forEach(button => {
      const on = button.dataset.heroScenario === key;
      button.setAttribute("aria-pressed", String(on));
      button.classList.toggle("is-active", on);
    });
    const query = terminal.querySelector("[data-demo-query]");
    if (query) query.textContent = scenario.query;
    const results = terminal.querySelector(".hero-results");
    if (results) {
      results.textContent = "";
      scenario.results.forEach((item, index) => {
        const row = document.createElement("li");
        row.dataset.demoItem = item.name;
        row.className = index === scenario.chosen ? "is-chosen" : "";
        const name = document.createElement("span");
        name.className = "hero-result-name";
        name.textContent = item.name;
        const facts = document.createElement("span");
        facts.className = "hero-result-facts";
        ["kind", "licence", "size"].forEach((keyName, position) => {
          if (position) facts.append(" · ");
          const fact = document.createElement("span");
          fact.dataset.fact = keyName;
          fact.textContent = item[keyName];
          facts.append(fact);
        });
        facts.append(" · sha256 ");
        const digest = document.createElement("span");
        digest.dataset.fact = "digest";
        digest.textContent = item.digest;
        facts.append(digest, "…");
        row.append(name, facts);
        if (index === scenario.chosen) {
          const chosen = document.createElement("span");
          chosen.className = "hero-result-chosen";
          chosen.textContent = "chosen";
          row.append(chosen);
        }
        results.append(row);
      });
    }
    const stepName = terminal.querySelector("[data-hero-step]");
    if (stepName) stepName.textContent = scenario.step + "/";
    const replaces = terminal.querySelector("[data-hero-replaces]");
    if (replaces) replaces.textContent = scenario.replaces;
    const outcome = terminal.querySelector("[data-hero-outcome]");
    if (outcome) outcome.textContent = scenario.outcome;
    paintHeroTree(scenario);
  };
  /* The tree is rebuilt per scenario so a reader sees the folder that step needs, not the folder of the first one. */
  const paintHeroTree = scenario => {
    const tree = document.querySelector(".hero-tree");
    if (!tree) return;
    tree.textContent = "";
    const harness = document.querySelector("[data-hero-harness][aria-pressed='true']")?.dataset.heroHarness || "claude-code";
    const files = HERO_FILES[harness] || HERO_FILES["claude-code"];
    const root = SKILL_ROOTS[harness];
    tree.dataset.heroHasSkills = root ? "true" : "false";
    const rows = root ? scenario.tree : [scenario.step + "/", files.instructions, files.tools, ".baltor/", NO_SKILL_FOLDER + "/", "  ↳ refused:", "    engine_reads_library_material_only_from_the_task_file"];
    rows.forEach((row, index) => {
      const span = document.createElement("span");
      if (row === files.instructions) { span.dataset.heroPart = "instructions"; span.dataset.heroFile = "instructions"; }
      else if (row === root) { span.dataset.heroPart = "skills"; span.dataset.heroFile = "skills"; }
      else if (row === files.tools) { span.dataset.heroPart = "tools"; span.dataset.heroFile = "tools"; }
      else if (row === NO_SKILL_FOLDER + "/") { span.className = "hero-tree-refusal"; }
      else if (row.startsWith("engine_reads_")) { span.className = "hero-tree-reason"; }
      tree.append(document.createTextNode(index === 0 ? row : "│   ".repeat(Math.max(0, index - 1)) + "└── " + row), span);
    });
  };
  heroScenarioButtons.forEach(button => {
    const key = button.dataset.heroScenario;
    button.addEventListener("mouseenter", () => paintScenario(key));
    button.addEventListener("focus", () => paintScenario(key));
    button.addEventListener("click", () => paintScenario(key));
  });
  window.__baltorPaintTree = () => {
    const key = document.querySelector(".hero-terminal")?.dataset.heroScenario || "dedupe";
    paintHeroTree(HERO_SCENARIOS[key] || HERO_SCENARIOS.dedupe);
  };
  if (heroScenarioButtons.length) paintScenario("dedupe");

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
