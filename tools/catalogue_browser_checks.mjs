/* The signed-in library table, src/loop_engine/core/service_runtime/web_assets/catalogue-browser.js, in a real
   browser against real loopback services. tools/check_service_workspace.mjs starts the services and calls
   runCatalogueBrowserChecks.

   Two services are used. The small one holds seven items: two Community items, one granted without its body, one
   without a licence, two written for a named development tool and one that declares running a process. The large
   one holds 1,200 items, so the table loads the library in several pages (roadmap S-6.203).

   Checks
   ├── the rows match the service's list: count, identities and the label of every row
   ├── every list request names every step effect the capabilities record names, and a file that declares an
   │   effect is listed with it
   ├── the kind, label and tool filters and the search box narrow the loaded rows without asking the service again
   ├── a row opens its detail panel, by pointer and by keyboard, and the empty state says so plainly
   ├── a file that declares more than reading files is checked and fetched only after the reader confirms its
   │   effects, and then with exactly those effects; a file that only reads files is checked without asking
   ├── the first page is drawn while later pages load, with a progress line, and the search box works meanwhile
   ├── a large library loads every page, draws a bounded number of rows and says how to see the rest
   ├── a change of the library while loading restarts the load once and says so
   └── refusals, changed bytes, changed items, record versions and sign-out behave as before the table

   Each check names at least one removed-guard control: the served module is changed in memory for one run, and
   the control is detected when every check it names fails. */
import {createHash} from "node:crypto";

const REQUEST_VERSION = "service_provisioning_request/v2";

export async function runCatalogueBrowserChecks({browser, fixture, check, mutants, errors, safeError, localOnly, output,
  routeBrowseAsset, holdDigestScript, signOutFromHeader, internalTerms}) {
  const small = {base:fixture.browse_base, token:fixture.browse_token};
  const large = {base:fixture.browse_large_base, token:fixture.browse_large_token};
  const stepEffects = async (target, service) =>
    (await (await target.request.get(service.base + "/api/v1/capabilities")).json()).result.library.step_effects;
  const browseList = async (target, service, fields = {}) => (await (await target.request.post(service.base + "/api/v1/provisioning",
    {headers:{Authorization:"Bearer " + service.token, "Content-Type":"application/json"},
     data:{record_type:REQUEST_VERSION, operation:"list", ...fields}})).json()).result;
  const tableRows = target => target.locator("#browse-table-body tr[data-identity]").evaluateAll(lines => lines.map(line => ({
    identity:line.dataset.identity, kind:line.dataset.harnessKind, tier:line.dataset.libraryTier,
    label:line.querySelector(".badge")?.textContent || "", cells:[...line.children].map(cell => cell.textContent)})));
  const shownIdentities = async target => (await tableRows(target)).map(row => row.identity).sort();
  const browseDetail = target => target.locator("#browse-detail dl").evaluate(node => {
    const pairs = [];
    for (const item of node.children) { if (item.tagName === "DT") pairs.push([item.textContent, ""]); else pairs[pairs.length - 1][1] = item.textContent; }
    return Object.fromEntries(pairs);});
  const browseStatus = page => page.locator('#browse-detail > p[role="status"]').evaluate(node => node.textContent);
  const settleBrowse = page => page.waitForFunction(() => !document.querySelector("#refresh-browse").disabled, null, {timeout:20000});
  const loadBrowse = async page => { await page.click("#refresh-browse"); await settleBrowse(page); };
  const openItem = async (page, identity) => {
    await page.locator('#browse-table-body tr[data-identity="' + identity + '"] button.browse-open').click();
    await page.waitForFunction(id => { const panel = document.querySelector("#browse-detail");
      return panel.querySelector("p.caption")?.textContent === id && !panel.textContent.includes("Checking this item"); }, identity);};
  const saveDownload = async (page, trigger) => {
    const saving = page.waitForEvent("download");
    await trigger();
    const chunks = [];
    for await (const chunk of await (await saving).createReadStream()) chunks.push(chunk);
    return Buffer.concat(chunks).toString();
  };
  const sentOf = (sent, operation) => sent.filter(entry => entry.body?.operation === operation);
  const refusedBrowse = async (page, note, name, planted) => {
    const rows = await tableRows(page), message = await page.locator("#browse-message").innerText();
    note(name, rows.length === 0 && await page.locator("#browse-count").innerText() === "Nothing shown"
      && message.startsWith("This service answered with a catalogue record this page was not written for")
      && !(await page.locator(".browse").innerText()).includes(planted), {rows:rows.length, message});};
  /* A signed-in page on one of the two services. Every request the page sends to the provisioning and download
     addresses is recorded with its body, so a check can say what was sent and what was not. */
  async function openBrowseWorkspace(service, mutation, holdDigest = false) {
    const context = await browser.newContext({viewport:{width:1440, height:1000}, acceptDownloads:true, reducedMotion:"reduce"});
    await context.route("**/*", localOnly);
    if (holdDigest) await context.addInitScript(holdDigestScript);
    const state = routeBrowseAsset(context, mutation);
    const opened = await context.newPage(), sent = [];
    opened.on("pageerror", error => (mutation ? state.errors : errors).push(safeError(error.message)));
    opened.on("request", request => {
      const path = new URL(request.url()).pathname;
      if (request.method() === "POST" && (path === "/api/v1/provisioning" || path === "/api/v1/download")) {
        let body = null; try { body = request.postDataJSON(); } catch (_) {}
        sent.push({path, body});
      }
    });
    await opened.goto(service.base + "/login");
    await opened.fill("#access-token", service.token);
    await opened.click("#connect-button");
    await opened.waitForFunction(() => document.querySelector("#connection-state").textContent === "Connected");
    await opened.waitForFunction(() => !document.querySelector("#refresh-browse").disabled);
    return {context, page:opened, state, sent};
  }
  const browseScenarios = {
    catalogue:async (opened, note, sent) => {
      await loadBrowse(opened);
      const named = await stepEffects(opened, small), reply = await browseList(opened, small, {authority_effects:named});
      const rows = await tableRows(opened), identities = rows.map(row => row.identity).sort();
      note("browse_table_rows_match_the_service_list", reply.items.length === 7
        && JSON.stringify(identities) === JSON.stringify(reply.items.map(row => row.identity).sort())
        && await opened.locator("#browse-count").innerText() === "7 items", {identities});
      note("browse_shows_each_item_s_library_tier", rows.length === reply.items.length && rows.every(row => {
        const item = reply.items.find(value => value.identity === row.identity);
        return Boolean(item?.library_tier_label) && row.label === item.library_tier_label && row.tier === item.library_tier;}),
        {rows:rows.map(row => [row.identity, row.label])});
      const lists = sentOf(sent, "list");
      note("browse_every_list_request_carries_every_step_effect", Array.isArray(named) && named.length === 5 && lists.length >= 1
        && lists.every(entry => JSON.stringify(entry.body.authority_effects) === JSON.stringify(named)), {named, sent:lists.map(entry => entry.body)});
      const deploy = rows.find(row => row.identity === "code.deploy");
      note("browse_lists_a_file_that_declares_an_effect_with_that_effect", deploy !== undefined && deploy.cells[5] === "spawns_process", {deploy});
      const message = await opened.locator("#browse-message").innerText();
      note("browse_says_what_it_shows_and_that_no_file_was_fetched", message.startsWith("Showing 7 items for alpha.")
        && message.includes("No file was fetched.") && !message.includes("not offered here"), {message});
      await openItem(opened, "context.review");
      const detail = await browseDetail(opened), listed = reply.items.find(row => row.identity === "context.review");
      note("browse_detail_states_purpose_source_licence_and_effects",
        detail["What it is for"] === listed.purpose && detail["Exact reference"] === listed.identity
        && detail["Where it comes from"] === listed.source_ref && detail.Licence === listed.license
        && detail["Declared effects"] === "None declared" && detail["Written for"] === "claude-code"
        && detail["The file itself"].startsWith("You may fetch it"), {detail});
      note("browse_detail_states_the_library_tier", Boolean(listed.library_tier_label) && detail.Label === listed.library_tier_label,
        {detail, tier:listed.library_tier_label});
      const body = await saveDownload(opened, () => opened.click("#browse-download"));
      note("browse_download_matches_the_selected_digest", body === "CONTEXT_REVIEW_BODY"
        && createHash("sha256").update("CONTEXT_REVIEW_BODY").digest("hex") === listed.digest
        && (await browseStatus(opened)).startsWith("Downloaded and checked."), {status:await browseStatus(opened)});
      await openItem(opened, "code.verify");
      note("browse_detail_says_when_the_file_is_not_granted", (await browseDetail(opened))["The file itself"] === "Not granted to this account."
        && await opened.locator("#browse-download").count() === 0
        && (await browseStatus(opened)) === "This account may read the details above, not the file.");
      await openItem(opened, "local.notes");
      note("browse_detail_states_an_unstated_licence_honestly", (await browseDetail(opened)).Licence === "Not stated"
        && (await browseDetail(opened))["Written for"] === "No tool named, so it suits every tool");
      const view = await opened.locator('[data-view="workspace"] .browse').innerText();
      note("browse_view_uses_plain_words", !internalTerms.test(view) && !/\bPractitioner\b/i.test(view), {});
      note("browse_shows_descriptions_and_no_file_body", view.includes("No file was fetched.")
        && !["CONTEXT_REVIEW_BODY", "CODE_NORMALISE_BODY", "LOCAL_NOTES_BODY", "HISTORY_RETRY_BODY", "CODE_DEPLOY_BODY"].some(text => view.includes(text)));
      note("browse_stores_nothing_in_the_browser", await opened.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0 && document.cookie === "")
        && !view.includes(small.token));
      const first = opened.locator("#browse-table-body tr[data-identity] button.browse-open").first();
      await first.focus();
      const focused = await opened.evaluate(() => document.activeElement.closest("tr")?.dataset.identity || "");
      await opened.keyboard.press("Enter");
      await opened.waitForFunction(id => document.querySelector("#browse-detail p.caption")?.textContent === id, focused).catch(() => {});
      note("browse_opens_an_item_with_the_keyboard", Boolean(focused)
        && await opened.locator("#browse-detail p.caption").first().innerText() === focused
        && await opened.locator('#browse-table-body tr[data-identity="' + focused + '"]').getAttribute("aria-selected") === "true", {focused});
      // A removed-guard control runs this same scenario against a changed module. The saved pictures must show the
      // page as it is, so only the unchanged run writes them.
      const unchangedRun = note === check;
      if (unchangedRun) await opened.screenshot({path:output.replace(/\.json$/, "-browse-desktop.png"), fullPage:true});
      const browseFits = [];
      for (const width of [1440, 820, 390, 320]) {
        await opened.setViewportSize({width, height:1000});
        for (const size of ["", "200%"]) {
          await opened.evaluate(value => document.documentElement.style.fontSize = value, size);
          browseFits.push({width, size:size || "100%", overflow:await opened.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)});
        }
        await opened.evaluate(() => document.documentElement.style.fontSize = "");
      }
      await opened.setViewportSize({width:390, height:1000});
      if (unchangedRun) await opened.screenshot({path:output.replace(/\.json$/, "-browse-mobile.png"), fullPage:true});
      await opened.setViewportSize({width:1440, height:1000});
      note("browse_fits_small_screens_and_enlarged_text", browseFits.length === 8 && browseFits.every(item => !item.overflow),
        {problems:browseFits.filter(item => item.overflow)});
    },
    /* A file that declares running a process. Opening it sends nothing until the reader confirms the effects named
       in plain words; then the check and the fetch each ask for exactly that file's declared effects. */
    confirm_effects:async (opened, note, sent) => {
      await loadBrowse(opened);
      const before = sent.length;
      await openItem(opened, "code.deploy");
      await opened.waitForTimeout(300);
      const early = sent.slice(before).filter(entry => entry.body?.identity === "code.deploy");
      const status = await browseStatus(opened);
      note("browse_asks_to_confirm_declared_effects_before_checking_a_file", early.length === 0
        && await opened.locator("#browse-confirm-effects").count() === 1 && status.includes("runs commands or programs on your computer")
        && await opened.locator("#browse-download").count() === 0, {status, sent:early.map(entry => entry.body)});
      let body = "";
      if (await opened.locator("#browse-confirm-effects").count() === 1) {
        await opened.click("#browse-confirm-effects");
        await opened.waitForFunction(() => document.querySelector("#browse-download") !== null
          || /Service refused|could not|no longer/.test(document.querySelector('#browse-detail > p[role="status"]')?.textContent || ""), null, {timeout:5000}).catch(() => {});
        if (await opened.locator("#browse-download").count() === 1) body = await saveDownload(opened, () => opened.click("#browse-download"));
      }
      const asked = sent.slice(before).filter(entry => entry.body?.identity === "code.deploy");
      note("browse_sends_exactly_the_confirmed_effects_for_that_file", asked.length === 2
        && asked.map(entry => entry.body.operation).join() === "manifest,read"
        && asked.every(entry => JSON.stringify(entry.body.authority_effects) === JSON.stringify(["spawns_process"]))
        && body === "CODE_DEPLOY_BODY", {asked:asked.map(entry => entry.body)});
      const beforePlain = sent.length;
      await openItem(opened, "context.review");
      const plain = sent.slice(beforePlain).filter(entry => entry.body?.identity === "context.review");
      note("browse_checks_a_file_that_only_reads_files_without_asking", plain.length === 1 && !("authority_effects" in plain[0].body)
        && await opened.locator("#browse-confirm-effects").count() === 0, {plain:plain.map(entry => entry.body)});
    },
    kind_filter:async (opened, note, sent) => {
      await loadBrowse(opened);
      const lists = sentOf(sent, "list").length;
      await opened.selectOption("#browse-kind", "code_module");
      const shown = await shownIdentities(opened);
      note("browse_filters_by_kind_of_file_on_the_loaded_rows", JSON.stringify(shown) === JSON.stringify(["code.deploy", "code.normalise", "code.verify"])
        && await opened.locator("#browse-count").innerText() === "3 of 7 items" && sentOf(sent, "list").length === lists, {shown});
    },
    label_filter:async (opened, note) => {
      await loadBrowse(opened);
      await opened.selectOption("#browse-tier", "community");
      const shown = await shownIdentities(opened);
      note("browse_filters_by_label_on_the_loaded_rows", JSON.stringify(shown) === JSON.stringify(["code.normalise", "history.retry"])
        && await opened.locator("#browse-count").innerText() === "2 of 7 items", {shown});
    },
    /* A file that names no development tool suits every tool, as the page says, so a tool filter keeps it. */
    tool_filter:async (opened, note) => {
      await loadBrowse(opened);
      await opened.selectOption("#browse-style", "codex");
      const shown = await shownIdentities(opened);
      note("browse_filters_by_development_tool_and_keeps_files_for_every_tool",
        JSON.stringify(shown) === JSON.stringify(["code.deploy", "code.normalise", "code.verify", "context.brief", "history.retry", "local.notes"])
        && await opened.locator("#browse-count").innerText() === "6 of 7 items", {shown});
    },
    search_box:async (opened, note) => {
      await loadBrowse(opened);
      await opened.fill("#browse-search", "normalise");
      const shown = await shownIdentities(opened);
      note("browse_search_box_narrows_the_loaded_rows", JSON.stringify(shown) === JSON.stringify(["code.normalise"])
        && await opened.locator("#browse-count").innerText() === "1 of 7 items", {shown});
    },
    empty_state:async (opened, note) => {
      await loadBrowse(opened);
      await opened.fill("#browse-search", "nothing-in-this-library");
      const empty = await opened.locator("#browse-table-body td.browse-empty").allInnerTexts();
      note("browse_says_plainly_when_nothing_matches", JSON.stringify(empty) === JSON.stringify(["Nothing matches your search and filters."])
        && await opened.locator("#browse-count").innerText() === "0 of 7 items", {empty});
    },
    /* Loading the library again keeps the filters the reader chose, and the rows still follow them. */
    refresh_after_filter:async (opened, note) => {
      await loadBrowse(opened);
      await opened.selectOption("#browse-kind", "code_module");
      await opened.fill("#browse-search", "normalise");
      await loadBrowse(opened);
      const shown = await shownIdentities(opened);
      note("browse_reload_keeps_the_filters_it_shows", await opened.inputValue("#browse-kind") === "code_module"
        && await opened.inputValue("#browse-search") === "normalise" && JSON.stringify(shown) === JSON.stringify(["code.normalise"])
        && await opened.locator("#browse-count").innerText() === "1 of 7 items", {shown, kind:await opened.inputValue("#browse-kind")});
    },
    /* The service decides. The request that leaves this page names a revision that is not the published one, so the
       real service refuses it with its own short code, and the reader must be told what to do about it in words. */
    stale_selection:async (opened, note) => {
      await loadBrowse(opened);
      const staleDigest = "0".repeat(64);
      const direct = await opened.request.post(small.base + "/api/v1/provisioning",
        {headers:{Authorization:"Bearer " + small.token, "Content-Type":"application/json"},
         data:{record_type:REQUEST_VERSION, operation:"manifest", identity:"context.review", expected_digest:staleDigest}});
      const code = (await direct.json())?.error?.code || "";
      await opened.route("**/api/v1/provisioning", async route => {
        const sentBody = route.request().postDataJSON();
        if (sentBody?.operation !== "manifest") return route.continue();
        await route.continue({postData:JSON.stringify({...sentBody, expected_digest:staleDigest})});});
      await openItem(opened, "context.review");
      const status = await browseStatus(opened);
      note("browse_states_a_service_refusal_in_plain_words", direct.status() >= 400 && code === "item_unavailable"
        && status === "This item is no longer available to this account. Load the library again to see what is there now."
        && !status.includes(code) && !/[a-z]_[a-z]/.test(status)
        && await opened.locator("#browse-detail dl").count() === 0
        && await opened.locator("#browse-download").count() === 0, {status, code, refused:direct.status()});
      await opened.unroute("**/api/v1/provisioning");
    },
    changed_download:async (opened, note) => {
      await loadBrowse(opened); await openItem(opened, "context.review");
      /* Bytes that are not the revision the reader selected, with a service report that agrees with those bytes.
         Only the comparison against the listed digest can tell this answer from a correct one. */
      const wrongBody = "CORRUPTED_LOCAL_FIXTURE", wrongDigest = createHash("sha256").update(wrongBody).digest("hex");
      await opened.route("**/api/v1/download", async route => { const response = await route.fetch();
        await route.fulfill({response, headers:{...response.headers(), "x-content-sha256":wrongDigest}, body:wrongBody});});
      const saving = opened.waitForEvent("download", {timeout:1500}).then(() => false, () => true);
      await opened.click("#browse-download");
      await opened.waitForFunction(() => document.querySelector('#browse-detail > p[role="status"]').textContent !== "Fetching the selected revision…");
      const nothingSaved = await saving;
      note("browse_refuses_changed_download_bytes_and_saves_nothing", nothingSaved
        && (await browseStatus(opened)).includes("do not match the selected item")
        && (await browseStatus(opened)).includes("Nothing was saved."), {status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/download");
    },
    reported_digest:async (opened, note) => {
      await loadBrowse(opened); await openItem(opened, "context.review");
      /* The bytes are the real ones; only the digest the service reports for them is changed. */
      await opened.route("**/api/v1/download", async route => { const response = await route.fetch();
        await route.fulfill({response, headers:{...response.headers(), "x-content-sha256":"0".repeat(64)}});});
      const saving = opened.waitForEvent("download", {timeout:1500}).then(() => false, () => true);
      await opened.click("#browse-download");
      await opened.waitForFunction(() => document.querySelector('#browse-detail > p[role="status"]').textContent !== "Fetching the selected revision…");
      const nothingSaved = await saving;
      note("browse_refuses_a_download_whose_reported_digest_disagrees", nothingSaved
        && (await browseStatus(opened)).includes("Nothing was saved."), {status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/download");
    },
    changed_item:async (opened, note) => {
      await loadBrowse(opened);
      await opened.route("**/api/v1/provisioning", async route => {
        const sentBody = route.request().postDataJSON();
        if (sentBody?.operation !== "manifest") return route.continue();
        const response = await route.fetch(), value = await response.json();
        value.result.digest = "0".repeat(64);
        await route.fulfill({response, json:value});});
      await openItem(opened, "context.review");
      note("browse_refuses_an_item_that_changed_since_the_list",
        (await browseStatus(opened)) === "This item changed since the list was loaded. Load the library again before fetching it."
        && await opened.locator("#browse-download").count() === 0
        && await opened.locator("#browse-detail dl").count() === 0, {status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/provisioning");
    },
    wrong_item_version:async (opened, note) => {
      await loadBrowse(opened);
      await opened.route("**/api/v1/provisioning", async route => {
        const sentBody = route.request().postDataJSON();
        if (sentBody?.operation !== "manifest") return route.continue();
        const response = await route.fetch(), value = await response.json();
        value.result.record_type = "provisioning_manifest/v4";
        await route.fulfill({response, json:value});});
      await openItem(opened, "context.review");
      note("browse_refuses_an_item_record_version_it_was_not_written_for",
        (await browseStatus(opened)).includes("an unsupported item version")
        && await opened.locator("#browse-detail dl").count() === 0
        && await opened.locator("#browse-download").count() === 0, {status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/provisioning");
    },
    wrong_version:async (opened, note) => {
      await changedList(opened, value => { value.result.record_type = "provisioning_list_page/v2"; });
      await refusedBrowse(opened, note, "browse_refuses_a_catalogue_record_version_it_was_not_written_for", "context.review");
    },
    unknown_group:async (opened, note) => {
      await changedList(opened, value => { value.result.items[0].source_layer = "mystery_intelligence"; });
      await refusedBrowse(opened, note, "browse_refuses_a_catalogue_that_names_a_group_it_does_not_know", "context.review");
      note("browse_names_the_reason_it_refused_a_catalogue", (await opened.locator("#browse-message").innerText()).includes("a group this page does not know"));
    },
    /* Every item names its library tier. A reply whose item has no label is a record this page was not written for. */
    missing_tier:async (opened, note) => {
      await changedList(opened, value => { delete value.result.items[0].library_tier_label; });
      await refusedBrowse(opened, note, "browse_refuses_a_catalogue_item_without_its_library_tier", "context.review");
    },
    /* The held-back material is read out of the reply, so its shape is checked like every other field the page reads. */
    withheld_shape:async (opened, note) => {
      await changedList(opened, value => { value.result.withheld = value.result.withheld.length; });
      await refusedBrowse(opened, note, "browse_refuses_a_catalogue_that_counts_held_back_material_the_wrong_way", "context.review");
    },
    /* A download whose bytes are measured after the reader signs out. No file may reach the disk. */
    held_download:async (opened, note) => {
      await loadBrowse(opened); await openItem(opened, "context.review");
      await opened.evaluate(() => window.__armDigestHold());
      const saving = opened.waitForEvent("download", {timeout:2500}).then(() => false, () => true);
      await opened.click("#browse-download");
      await opened.waitForFunction(() => window.__digestHeld === true, null, {timeout:8000});
      await signOutFromHeader(opened);
      await opened.waitForFunction(() => document.querySelector("#connection-state").textContent === "Not connected");
      await opened.evaluate(() => window.__releaseDigest());
      const nothingSaved = await saving;
      note("browse_sign_out_stops_a_download_that_finishes_afterwards", nothingSaved
        && await opened.locator("#browse-table-body tr[data-identity]").count() === 0
        && await opened.locator("#browse-count").innerText() === "Sign in to browse"
        && await opened.locator("#browse-detail dl").count() === 0,
        {nothingSaved, message:await opened.locator("#browse-message").innerText()});
    },
    delayed_reply:async (opened, note) => {
      await loadBrowse(opened); await openItem(opened, "context.review");
      let release; const gate = new Promise(resolve => { release = resolve; }); let held = false;
      await opened.route("**/api/v1/provisioning", async route => {
        if (route.request().postDataJSON()?.operation === "list") { held = true; await gate; }
        await route.continue().catch(() => {});});
      await opened.click("#refresh-browse");
      await new Promise((resolve, reject) => { const deadline = setTimeout(() => { clearInterval(poll); reject(new Error("No held catalogue request")); }, 5000);
        const poll = setInterval(() => { if (held) { clearInterval(poll); clearTimeout(deadline); resolve(); } }, 10); });
      await signOutFromHeader(opened);
      await opened.waitForFunction(() => document.querySelector("#connection-state").textContent === "Not connected");
      release();
      const signedOut = "Sign in to browse the library published for your account.";
      await opened.waitForFunction(text => document.querySelector("#browse-message").textContent !== text, signedOut, {timeout:1200}).catch(() => {});
      note("browse_sign_out_clears_a_delayed_catalogue_reply",
        await opened.locator("#browse-table-body tr[data-identity]").count() === 0
        && await opened.locator("#browse-count").innerText() === "Sign in to browse"
        && await opened.locator("#browse-message").innerText() === signedOut
        && await opened.locator("#browse-detail dl").count() === 0
        && await opened.locator("#browse-kind").isDisabled() && await opened.locator("#refresh-browse").isDisabled(),
        {message:await opened.locator("#browse-message").innerText()});
      await opened.unroute("**/api/v1/provisioning");
    },
    /* 1,200 items arrive in several pages. The second page is held until the first page is drawn, so the checks see
       the table while the load is still running. */
    paged_load:async (opened, note, sent) => {
      let release = () => {}, held = false; const gate = new Promise(resolve => { release = resolve; });
      await opened.route("**/api/v1/provisioning", async route => {
        const body = route.request().postDataJSON();
        if (body?.operation === "list" && body.cursor && !held) { held = true; await gate; }
        await route.continue().catch(() => {});});
      let progress = "", drawnWhileLoading = 0, searchUsable = false, narrowed = [];
      try {
        await opened.click("#refresh-browse");
        await opened.waitForFunction(() => /^Loaded [\d,]+ of [\d,]+\./.test(document.querySelector("#browse-message").textContent), null, {timeout:15000}).catch(() => {});
        progress = await opened.locator("#browse-message").innerText();
        drawnWhileLoading = await opened.locator("#browse-table-body tr[data-identity]").count();
        searchUsable = !(await opened.locator("#browse-search").isDisabled());
        if (searchUsable) { await opened.fill("#browse-search", "large.item.0042"); narrowed = await shownIdentities(opened); await opened.fill("#browse-search", ""); }
      } finally { release(); }
      await settleBrowse(opened).catch(() => {});
      await opened.unroute("**/api/v1/provisioning");
      const named = await stepEffects(opened, large), lists = sentOf(sent, "list");
      note("browse_shows_a_progress_line_while_pages_load", held && /^Loaded [\d,]+ of 1,200\./.test(progress), {progress});
      note("browse_draws_the_first_page_while_later_pages_load", held && drawnWhileLoading > 0 && drawnWhileLoading <= 300, {drawnWhileLoading});
      note("browse_search_works_on_the_rows_loaded_so_far", searchUsable && JSON.stringify(narrowed) === JSON.stringify(["large.item.0042"]), {narrowed});
      note("browse_loads_every_page_of_a_large_library", await opened.locator("#browse-count").innerText() === "1,200 items"
        && lists.length >= 3 && !lists[0].body.cursor && lists.slice(1).every(entry => typeof entry.body.cursor === "string")
        && (await opened.locator("#browse-message").innerText()).startsWith("Showing 1,200 items for alpha."), {pages:lists.length});
      note("browse_every_page_request_carries_every_step_effect", lists.length >= 3
        && lists.every(entry => JSON.stringify(entry.body.authority_effects) === JSON.stringify(named) && entry.body.page_size === 500), {named});
      const more = await opened.locator("#browse-table-body td.browse-more").allInnerTexts();
      note("browse_draws_a_bounded_number_of_rows_and_says_how_to_see_the_rest",
        await opened.locator("#browse-table-body tr[data-identity]").count() === 300
        && JSON.stringify(more) === JSON.stringify(["Showing the first 300 of 1,200 items. Narrow the search or the filters to see the rest."]), {more});
    },
    /* The service answers the second page once with the refusal a changed library produces. The page starts the
       load again from the first page, once, and says so. */
    release_change:async (opened, note, sent) => {
      let refused = false;
      await opened.route("**/api/v1/provisioning", async route => {
        const body = route.request().postDataJSON();
        if (body?.operation === "list" && body.cursor && !refused) {
          refused = true;
          await route.fulfill({status:409, contentType:"application/json", body:JSON.stringify({record_type:"service_http_error/v1",
            error:{code:"list_release_changed", message:"The library served to this account changed after the first page was read.",
              next_action:"Load the list again from the first page, without a cursor, and use only the new pages."},
            effect_commitment:"not_asserted", automatic_retry:false})});
          return;
        }
        await route.continue().catch(() => {});});
      await loadBrowse(opened).catch(() => {});
      await opened.unroute("**/api/v1/provisioning");
      const firsts = sentOf(sent, "list").filter(entry => !entry.body.cursor), message = await opened.locator("#browse-message").innerText();
      note("browse_restarts_once_when_the_library_changes_while_loading", refused && firsts.length === 2
        && message.startsWith("The library changed while it was loading, so it was loaded again from the start.")
        && await opened.locator("#browse-count").innerText() === "1,200 items", {message, first_pages:firsts.length});
    }};
  async function changedList(opened, change) {
    await opened.route("**/api/v1/provisioning", async route => {
      const sentBody = route.request().postDataJSON();
      if (sentBody?.operation !== "list") return route.continue();
      const response = await route.fetch(), value = await response.json();
      change(value);
      await route.fulfill({response, json:value});});
    await loadBrowse(opened);
    await opened.unroute("**/api/v1/provisioning");
  }
  // The held measurement is installed only where a check names it, so every other browse check runs in an
  // unchanged page served entirely by the service.
  const browseHoldsDigest = new Set(["held_download"]), onLarge = new Set(["paged_load", "release_change"]);
  for (const name of Object.keys(browseScenarios)) {
    const {context, page, sent} = await openBrowseWorkspace(onLarge.has(name) ? large : small, null, browseHoldsDigest.has(name));
    await browseScenarios[name](page, check, sent);
    await context.close();
  }
  /* Removed-guard controls for browsing. The served module is changed in memory only. A control is detected when
     every check it names fails with the guard removed. */
  const browseControls = [
    {name:"accept_any_catalogue_record_version", scenario:"wrong_version", find:"value.record_type !== pageVersion", replacement:"false",
     expected:["browse_refuses_a_catalogue_record_version_it_was_not_written_for"]},
    {name:"accept_a_group_the_page_does_not_know", scenario:"unknown_group",
     find:'if (!knownLayers.has(row.source_layer)) return "a group this page does not know";', replacement:"",
     expected:["browse_refuses_a_catalogue_that_names_a_group_it_does_not_know", "browse_names_the_reason_it_refused_a_catalogue"]},
    {name:"trust_the_downloaded_bytes", scenario:"changed_download", find:"measured !== row.digest || ", replacement:"",
     expected:["browse_refuses_changed_download_bytes_and_saves_nothing"]},
    {name:"trust_the_reported_download_digest", scenario:"reported_digest", find:" || measured !== result.digest", replacement:"",
     expected:["browse_refuses_a_download_whose_reported_digest_disagrees"]},
    {name:"ignore_an_item_that_changed_since_the_list", scenario:"changed_item", find:"if (value.digest !== row.digest) {", replacement:"if (false) {",
     expected:["browse_refuses_an_item_that_changed_since_the_list"]},
    {name:"accept_any_item_record_version", scenario:"wrong_item_version", find:"value.record_type !== manifestVersion", replacement:"false",
     expected:["browse_refuses_an_item_record_version_it_was_not_written_for"]},
    /* Signing out cancels the list request in flight, so the reply arrives as a cancellation and the guard in the
       failure path decides whether the signed-out page is written to. */
    {name:"keep_a_delayed_catalogue_reply_after_sign_out", scenario:"delayed_reply",
     find:'if (!stillWanted()) return;\n        const text = error.name === "AbortError"',
     replacement:'const text = error.name === "AbortError"',
     expected:["browse_sign_out_clears_a_delayed_catalogue_reply"]},
    {name:"save_a_download_that_finished_after_sign_out", scenario:"held_download",
     find:"if (epoch !== current().generation || result.epoch !== current().generation) return;", replacement:"",
     expected:["browse_sign_out_stops_a_download_that_finishes_afterwards"]},
    {name:"forget_a_chosen_filter_on_reload", scenario:"refresh_after_filter",
     find:'select.value = [...select.options].some(choice => choice.value === chosen) ? chosen : "";', replacement:'select.value = "";',
     expected:["browse_reload_keeps_the_filters_it_shows"]},
    {name:"show_a_service_refusal_as_its_code", scenario:"stale_selection",
     find:"return named && refusals[named[1]] ? refusals[named[1]] : text;", replacement:"return text;",
     expected:["browse_states_a_service_refusal_in_plain_words"]},
    {name:"count_held_back_material_from_a_shape_the_page_was_not_written_for", scenario:"withheld_shape",
     find:"|| !Array.isArray(value.withheld) ", replacement:"",
     expected:["browse_refuses_a_catalogue_that_counts_held_back_material_the_wrong_way"]},
    {name:"accept_an_item_without_a_library_tier", scenario:"missing_tier",
     find:'if (!knownTiers.has(row.library_tier) || !stated(row.library_tier_label)) return "no library tier";', replacement:"",
     expected:["browse_refuses_a_catalogue_item_without_its_library_tier"]},
    {name:"leave_the_library_tier_off_the_rows", scenario:"catalogue",
     find:'const badge = element("span", values.tier, "badge");', replacement:'const badge = element("span", "", "badge");',
     expected:["browse_shows_each_item_s_library_tier"]},
    {name:"leave_the_library_tier_out_of_the_detail", scenario:"catalogue",
     find:'["Label", value.library_tier_label],', replacement:"",
     expected:["browse_detail_states_the_library_tier"]},
    {name:"list_without_every_step_effect", scenario:"catalogue",
     find:"...(named ? {authority_effects:named} : {})", replacement:"...{}",
     expected:["browse_every_list_request_carries_every_step_effect", "browse_lists_a_file_that_declares_an_effect_with_that_effect",
       "browse_table_rows_match_the_service_list"]},
    {name:"ignore_the_kind_filter", scenario:"kind_filter", find:"(!kind || harnessKindOf(row) === kind)", replacement:"true",
     expected:["browse_filters_by_kind_of_file_on_the_loaded_rows"]},
    {name:"ignore_the_label_filter", scenario:"label_filter", find:"(!tier || row.library_tier === tier)", replacement:"true",
     expected:["browse_filters_by_label_on_the_loaded_rows"]},
    {name:"ignore_the_development_tool_filter", scenario:"tool_filter",
     find:"(!style || !toolsOf(row).length || (row.styles || []).includes(style))", replacement:"true",
     expected:["browse_filters_by_development_tool_and_keeps_files_for_every_tool"]},
    {name:"ignore_the_search_box", scenario:"search_box",
     find:"(!words.length || words.every(word => searchable(row).includes(word)))", replacement:"true",
     expected:["browse_search_box_narrows_the_loaded_rows"]},
    {name:"hide_the_empty_state", scenario:"empty_state", find:'"Nothing matches your search and filters."', replacement:'""',
     expected:["browse_says_plainly_when_nothing_matches"]},
    {name:"check_a_file_before_its_effects_are_confirmed", scenario:"confirm_effects",
     find:'if (effects.beyondReading(row.declared_effects).length && !confirmed.has(row.identity + ":" + row.digest)) {', replacement:"if (false) {",
     expected:["browse_asks_to_confirm_declared_effects_before_checking_a_file"]},
    {name:"ask_for_more_effects_than_the_file_declares", scenario:"confirm_effects",
     find:"? {authority_effects:effects.requested(row.declared_effects)} : {};",
     replacement:'? {authority_effects:["reads_fs", "writes_fs", "reads_secret", "network", "spawns_process"]} : {};',
     expected:["browse_sends_exactly_the_confirmed_effects_for_that_file"]},
    {name:"stop_after_the_first_page", scenario:"paged_load", find:"cursor = value.next_cursor;", replacement:"cursor = null;",
     expected:["browse_loads_every_page_of_a_large_library"]},
    {name:"draw_every_loaded_row", scenario:"paged_load", find:"for (const row of rows.slice(0, drawLimit)) {", replacement:"for (const row of rows) {",
     expected:["browse_draws_a_bounded_number_of_rows_and_says_how_to_see_the_rest"]},
    {name:"hide_the_progress_line", scenario:"paged_load",
     find:'+ "Loaded " + number(listed.length) + " of " + number(first.total_offered)', replacement:'+ ""',
     expected:["browse_shows_a_progress_line_while_pages_load"]},
    {name:"disable_the_search_box_while_loading", scenario:"paged_load",
     find:"$(id).disabled = !eligible() || !listed;", replacement:"$(id).disabled = !eligible() || !listed || active;",
     expected:["browse_search_works_on_the_rows_loaded_so_far"]},
    {name:"never_restart_a_changed_load", scenario:"release_change",
     find:'if (stillWanted() && cursor && !restarted && (code === "list_release_changed" || code === "list_cursor_invalid")) {', replacement:"if (false) {",
     expected:["browse_restarts_once_when_the_library_changes_while_loading"]}];
  for (const control of browseControls) {
    const failed = new Set(), note = (name, passed) => { if (passed !== true) failed.add(name); };
    let applied = false, problem = "";
    try {
      const {context:changedContext, page:changedPage, state, sent} = await openBrowseWorkspace(
        onLarge.has(control.scenario) ? large : small, {find:control.find, replacement:control.replacement}, browseHoldsDigest.has(control.scenario));
      applied = state.applied;
      await browseScenarios[control.scenario](changedPage, note, sent);
      await changedContext.close();
    } catch (error) { problem = safeError(error); }
    const missed = control.expected.filter(name => !failed.has(name)), detected = applied && !problem && missed.length === 0;
    mutants.push({name:control.name, applied, detected, required_checks:control.expected, missed_checks:missed, failed_checks:[...failed].sort(), ...(problem ? {problem} : {})});
    check("removed_guard_is_detected_" + control.name, detected, {applied, missed_checks:missed, ...(problem ? {problem} : {})});
  }
}
