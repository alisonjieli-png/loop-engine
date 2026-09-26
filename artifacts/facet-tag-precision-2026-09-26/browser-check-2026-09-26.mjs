/* A one-off real-browser check of the facet filters in the signed-in library table, September 26, 2026.
   The page is the browse section of index.html with its own stylesheets and the exact catalogue-browser.js
   bytes of the worktree; only the service is a stub that answers list and manifest from fixture rows.
   A second run loads the module with the facet rule removed and must fail the filter comparison. */
import {chromium} from "/home/username/loop-engine/showcase/node_modules/playwright-core/index.mjs";
import {readFileSync, writeFileSync, copyFileSync} from "node:fs";

const assets = "/home/username/.le-agent-facet-tags/src/loop_engine/core/service_runtime/web_assets/";
const here = "/home/username/.le-ci-tmp/facet-tags/browser/";
const lines = readFileSync(assets + "index.html", "utf8").split("\n");
const start = lines.findIndex(line => line.includes('<section class="panel browse"'));
const end = lines.findIndex((line, index) => index > start && line.trim() === "</section>");
const section = lines.slice(start, end + 1).join("\n");
for (const name of ["service.css", "architecture.css", "public-pages.css"]) copyFileSync(assets + name, here + name);
const module = readFileSync(assets + "catalogue-browser.js", "utf8");
const rule = "facetRules.keepsFacets(row, wanted)";
if (module.split(rule).length !== 2) throw new Error("the facet rule is not in the module exactly once");
writeFileSync(here + "catalogue-browser.js", module);
writeFileSync(here + "catalogue-browser-mutant.js", module.replace(rule, "true"));

const item = (identity, kind, purpose, attributes, tier = "community") => ({
  record_type: "harness_intelligence_item/v1", identity, purpose, source_ref: "fixture:" + identity,
  digest: identity.length.toString(16).padStart(2, "0").repeat(32), source_layer: "harness_local", kind,
  declared_effects: [], styles: [], body_allowed: false, library_tier: tier,
  library_tier_label: tier === "verified" ? "Verified" : "Community", ...(attributes ? {attributes} : {})});
const rows = [
  item("skill.contract-review", "skill", "Review a supplier contract for a law firm",
    {harness_kind: "skill", step_functions: ["reviewing"], job_titles: ["Lawyers"], industries: ["legal"],
     levels: ["senior"], languages: ["english"], geographies: ["United States"]}, "verified"),
  item("skill.ward-rota", "skill", "Plan the rota of the doctors on a ward",
    {harness_kind: "skill", industries: ["healthcare", "legal"], languages: ["english"]}),
  item("instruction.notes", "instruction_file", "Notas de revision del codigo",
    {harness_kind: "instruction_file", languages: ["spanish"], geographies: ["Spain"]}),
  item("skill.changelog", "skill", "Format a changelog", {harness_kind: "skill", languages: ["english"]}),
  item("skill.rename", "skill", "Rename files in bulk", null),
];

const page = moduleFile => `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="service.css"><link rel="stylesheet" href="architecture.css">
<link rel="stylesheet" href="public-pages.css"></head><body><main id="main">
<section data-view="workspace">${section}</section></main>
<script src="${moduleFile}"></script>
<script>
const rows = ${JSON.stringify(rows)};
window.requests = [];
const element = (tag, text, className = "") => { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; return node; };
const message = (id, text) => { const node = document.getElementById(id); if (node) node.textContent = text; };
const state = {connected: true, generation: 1, scopes: ["provisioning:metadata"]};
const request = async (path, body) => {
  window.requests.push(body.operation);
  if (body.operation === "list") return {record_type: "provisioning_list/v3", items: rows, withheld: [], tenant_id: "tenant-fixture"};
  if (body.operation === "manifest") {
    const row = rows.find(entry => entry.identity === body.identity);
    return {record_type: "provisioning_manifest/v3", identity: row.identity, digest: row.digest, source_ref: row.source_ref,
            qualification_basis: "fixture", declared_effects: [], styles: [], body_allowed: false,
            library_tier: row.library_tier, library_tier_label: row.library_tier_label, license: "MIT"};
  }
  throw new Error("Service refused the request: scope_required.");
};
window.view = window.BaltorCatalogueBrowser.create({request, element, message, current: () => state});
</script></body></html>`;
writeFileSync(here + "harness.html", page("catalogue-browser.js"));
writeFileSync(here + "harness-mutant.html", page("catalogue-browser-mutant.js"));

const selects = {job_titles: "#browse-job-title", industries: "#browse-industry", levels: "#browse-level",
                 languages: "#browse-language", geographies: "#browse-geography"};
const shown = target => target.locator("#browse-table-body tr[data-identity]").evaluateAll(
  items => items.map(item => item.dataset.identity));
const settle = target => target.waitForFunction(() => !document.querySelector("#browse-message").textContent.startsWith("Loading"));

async function scenario(browser, file, screenshots) {
  const target = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const errors = [];
  target.on("pageerror", error => errors.push(String(error)));
  await target.goto("file://" + here + file);
  const before = {};
  for (const [name, id] of Object.entries(selects)) {
    before[name] = {disabled: await target.locator(id).isDisabled(), options: await target.locator(id + " option").allInnerTexts()};
  }
  await target.evaluate(() => window.view.load());
  await settle(target);
  const result = {before, errors, choices: {}, filters: {}};
  for (const [name, id] of Object.entries(selects)) {
    result.choices[name] = {disabled: await target.locator(id).isDisabled(),
                            values: await target.locator(id + " option").evaluateAll(items => items.map(item => item.value))};
  }
  result.filters.none = await shown(target);
  await target.selectOption(selects.industries, "legal");
  result.filters.industry_legal = await shown(target);
  await target.selectOption(selects.job_titles, "Lawyers");
  result.filters.industry_legal_and_lawyers = await shown(target);
  result.filters.count_text = await target.locator("#browse-count").innerText();
  await target.selectOption(selects.industries, "");
  await target.selectOption(selects.job_titles, "");
  result.filters.cleared = await shown(target);
  await target.selectOption(selects.languages, "spanish");
  result.filters.language_spanish = await shown(target);
  await target.selectOption(selects.languages, "");
  await target.fill("#browse-search", "healthcare");
  result.filters.search_healthcare = await shown(target);
  await target.fill("#browse-search", "");
  const detail = async identity => {
    await target.locator(`tr[data-identity="${identity}"] .browse-open`).click();
    await target.waitForSelector("#browse-detail dl");
    const pairs = await target.locator("#browse-detail dl").evaluate(list => {
      const found = {}, terms = [...list.querySelectorAll("dt")];
      for (const term of terms) found[term.textContent] = term.nextElementSibling ? term.nextElementSibling.textContent : "";
      return found;
    });
    const buttons = await target.locator("#browse-detail button").allInnerTexts();
    return {facts: Object.fromEntries(["Job titles", "Industries", "Levels", "Languages", "Geographies"].map(key => [key, pairs[key]])), buttons};
  };
  result.detail_tagged = await detail("skill.contract-review");
  result.detail_untagged = await detail("skill.rename");
  const fits = [];
  for (const width of [1440, 820, 390, 320]) {
    await target.setViewportSize({width, height: 1000});
    for (const size of ["", "200%"]) {
      await target.evaluate(value => document.documentElement.style.fontSize = value, size);
      fits.push({width, size: size || "100%", ...await target.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        items: [...document.querySelectorAll(".browse *")].filter(node => { const box = node.getBoundingClientRect(); return box.width && box.right > innerWidth + 1; })
          .slice(0, 6).map(node => node.id || node.tagName)}))});
    }
    await target.evaluate(() => document.documentElement.style.fontSize = "");
    if (screenshots && (width === 1440 || width === 390)) {
      await target.screenshot({path: here + `facet-table-${width}.png`, fullPage: true});
    }
  }
  result.fits = fits;
  result.requests = await target.evaluate(() => window.requests);
  await target.close();
  return result;
}

const browser = await chromium.launch({executablePath: "/home/username/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome"});
const real = await scenario(browser, "harness.html", true);
const mutant = await scenario(browser, "harness-mutant.html", false);
await browser.close();

const expected = {
  none: ["skill.changelog", "skill.contract-review", "skill.rename", "skill.ward-rota", "instruction.notes"],
};
const same = (left, right) => JSON.stringify([...left].sort()) === JSON.stringify([...right].sort());
const checks = {
  selects_start_disabled_with_only_the_empty_choice: Object.values(real.before).every(entry => entry.disabled && entry.options.length === 1),
  selects_offer_the_values_the_rows_carry: JSON.stringify(real.choices.industries.values) === JSON.stringify(["", "healthcare", "legal"])
    && JSON.stringify(real.choices.job_titles.values) === JSON.stringify(["", "Lawyers"])
    && JSON.stringify(real.choices.languages.values) === JSON.stringify(["", "english", "spanish"])
    && JSON.stringify(real.choices.geographies.values) === JSON.stringify(["", "Spain", "United States"])
    && JSON.stringify(real.choices.levels.values) === JSON.stringify(["", "senior"])
    && Object.values(real.choices).every(entry => !entry.disabled),
  no_filter_shows_every_row: same(real.filters.none, expected.none),
  an_industry_keeps_only_rows_that_carry_it: same(real.filters.industry_legal, ["skill.contract-review", "skill.ward-rota"]),
  two_facets_keep_rows_that_carry_both: same(real.filters.industry_legal_and_lawyers, ["skill.contract-review"])
    && real.filters.count_text === "1 of 5 items",
  clearing_the_choices_shows_every_row: same(real.filters.cleared, expected.none),
  a_language_keeps_its_rows: same(real.filters.language_spanish, ["instruction.notes"]),
  the_search_box_finds_a_facet_value: same(real.filters.search_healthcare, ["skill.ward-rota"]),
  the_detail_lists_each_facet: JSON.stringify(real.detail_tagged.facts) === JSON.stringify({"Job titles": "Lawyers",
    "Industries": "legal", "Levels": "senior", "Languages": "english", "Geographies": "United States"}),
  an_untagged_item_says_not_tagged: Object.values(real.detail_untagged.facts).every(value => value === "Not tagged"),
  the_table_fits_small_screens_and_enlarged_text: real.fits.length === 8 && real.fits.every(entry => !entry.overflow),
  no_page_errors: real.errors.length === 0,
  removed_facet_rule_keeps_every_row_and_fails_the_filter_comparison: same(mutant.filters.industry_legal, expected.none)
    && !same(mutant.filters.industry_legal, ["skill.contract-review", "skill.ward-rota"]),
};
const report = {record_type: "facet_table_browser_check/v1", date: "2026-09-26", checks,
                passed: Object.values(checks).filter(Boolean).length, total: Object.keys(checks).length, real, mutant};
writeFileSync(here + "facet-table-browser-check.json", JSON.stringify(report, null, 1) + "\n");
console.log(JSON.stringify({passed: report.passed, total: report.total, failed: Object.keys(checks).filter(name => !checks[name])}));
