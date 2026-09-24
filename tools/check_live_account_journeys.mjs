/* Live account journeys on the deployed site, with disposable inboxes. It creates real accounts.

   Run only when public registration is open, with a new report path:
     node tools/check_live_account_journeys.mjs https://baltor.ai REPORT.json [--fresh-only | --staff-step | --sign-up-link-step]

   Journey "fresh": a new address signs up on Get started, reads the message, chooses a password on the
   page the link opens and lands signed in; the founding offer is read from the page.
   Journey "provider_first": an address is first registered through the identity provider's own public
   sign-up with a password this script chooses, then signs up through Baltor. Baltor's sign-up must
   replace that account, so the provider's first password must be refused afterwards and the password
   chosen on Baltor's page must work.
   With --staff-step, the fresh account (named as a superadmin in the host file by the operator before
   this step) opens Administration, revokes and grants free monthly for the other account, switches it
   off and on, and finally revokes free monthly for both, so the two checking accounts hold no founding
   place.
   With --sign-up-link-step, the same superadmin sends one sign-up link with free monthly Baltor Pro to a new
   disposable inbox from Administration. The person shows as pending, the message names the sender and links to
   the confirmation page, choosing a password opens the account with the staff grant (not a founding place), the
   account leaves the pending list, and a second link to the same address is refused with no second message.
   The new checking account then gives its grant back and is switched off.
   The report holds no password, token or message body. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {existsSync, writeFileSync, readFileSync} from "node:fs";
import {resolve} from "node:path";
import {randomUUID, randomBytes} from "node:crypto";

const origin = process.argv[2], output = resolve(process.argv[3] || ""), staffStep = process.argv.includes("--staff-step");
const linkStep = process.argv.includes("--sign-up-link-step");
// The checking accounts' passwords stay on this workstation, outside the repository, readable by this user only.
const statePath = process.env.BALTOR_JOURNEY_STATE || resolve(process.env.HOME, ".le-safety", "live-account-journeys-state.json");
if (statePath.startsWith(resolve(new URL("..", import.meta.url).pathname))) throw new Error("The journey state must live outside the repository.");
if (!origin || new URL(origin).origin !== origin || !origin.startsWith("https://") || !process.argv[3] || existsSync(output))
  throw new Error("Use an exact HTTPS origin and a new report path.");
const MAIL = "https://api.mail.tm";
const steps = [];
const step = (journey, name, passed, detail = {}) => steps.push({journey, name, passed: passed === true, ...detail});
const sleep = ms => new Promise(done => setTimeout(done, ms));
const password = () => "Qa-" + randomBytes(18).toString("base64url");

async function inbox() {
  const domain = (await (await fetch(MAIL + "/domains")).json())["hydra:member"][0].domain;
  const address = `baltor-check-${randomUUID().slice(0, 8)}@${domain}`, secret = randomUUID();
  const made = await fetch(MAIL + "/accounts", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({address, password: secret})});
  if (!made.ok) throw new Error("inbox_not_created_" + made.status);
  const token = (await (await fetch(MAIL + "/token", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({address, password: secret})})).json()).token;
  return {address, token, seen: new Set()};
}
async function nextMessage(box, predicate, timeoutMs = 240000) {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    const list = await (await fetch(MAIL + "/messages", {headers: {Authorization: "Bearer " + box.token}})).json();
    for (const row of list["hydra:member"] || []) {
      if (box.seen.has(row.id)) continue;
      const full = await (await fetch(MAIL + "/messages/" + row.id, {headers: {Authorization: "Bearer " + box.token}})).json();
      const text = [full.text || "", ...(Array.isArray(full.html) ? full.html : [full.html || ""])].join("\n");
      const from = full.from?.address || "";
      if (predicate(from, text)) { box.seen.add(row.id); return {from, subject: full.subject || "", text}; }
    }
    await sleep(5000);
  }
  return null;
}
// The message links to the host file's public base address, which may be another hostname of this deployment.
const confirmLink = text => (text.match(/https:\/\/[a-z0-9.-]+\/auth\/confirm\?[^\s"'<>]+/) || [null])[0]?.replace(/&amp;/g, "&");

const identity = (await (await fetch(origin + "/api/v1/account/identity")).json()).result;
const capabilities = (await (await fetch(origin + "/api/v1/capabilities")).json()).result;
step("setup", "registration_is_open", capabilities.website?.registration_available === true && identity.signup_available === true,
  {registration_available: capabilities.website?.registration_available, signup_available: identity.signup_available});
const providerPassword = async (email, secret) => (await fetch(identity.project_url + "/auth/v1/token?grant_type=password", {method: "POST",
  headers: {"Content-Type": "application/json", apikey: identity.publishable_key}, body: JSON.stringify({email, password: secret})})).status;

const browser = await chromium.launch({executablePath: "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox"]});
const newPage = async () => { const context = await browser.newContext({viewport: {width: 1440, height: 1000}}); const page = await context.newPage(); page.on("dialog", dialog => dialog.accept()); return page; };

async function signUpOnGetStarted(page, email) {
  await page.goto(origin + "/get-started");
  await page.waitForSelector("#funnel-email", {state: "visible", timeout: 20000});
  await page.fill("#funnel-email", email); await page.click("#funnel-signup-button");
  await page.waitForFunction(() => /check your email/i.test(document.getElementById("funnel-signup-message")?.textContent || ""), null, {timeout: 60000});
}
async function choosePassword(page, link, secret) {
  // The three calls the page makes after Confirm, by status only: the provider's verify and password update, and activation.
  const calls = [];
  page.on("response", response => { const path = new URL(response.url()).pathname;
    if (/\/auth\/v1\/(verify|user)$|\/api\/v1\/(account\/activate|session)$/.test(path)) calls.push(response.request().method() + " " + path + " " + response.status()); });
  await page.goto(link);
  await page.waitForSelector("#confirm-password", {state: "visible", timeout: 30000});
  await page.fill("#confirm-password", secret); await page.fill("#confirm-password-again", secret);
  // The page refuses a click before its sign-in settings have loaded, and says the link was not used; try again then.
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.click("#confirm-button"); await page.waitForTimeout(2000);
    if (!/still loading its sign-in settings/.test((await page.locator("#confirm-message").textContent().catch(() => "")) || "")) break;
  }
  await page.waitForFunction(() => location.pathname !== "/auth/confirm" || !document.getElementById("confirm-unusable")?.hidden
    || !/^(|Setting your password…)$/.test((document.getElementById("confirm-message")?.textContent || "").trim()), null, {timeout: 60000}).catch(() => {});
  await page.waitForTimeout(3000);
  return {path: new URL(page.url()).pathname, calls,
          unusable_shown: await page.locator("#confirm-unusable").isVisible().catch(() => null),
          confirm_message: ((await page.locator("#confirm-message").textContent().catch(() => "")) || "").trim().slice(0, 200),
          planTitle: (await page.locator("#funnel-plan-title").textContent().catch(() => "")) || "",
          planText: (await page.locator("#funnel-plan-text").textContent().catch(() => "")) || ""};
}
async function signIn(page, email, secret) {
  await page.goto(origin + "/login", {waitUntil: "domcontentloaded", timeout: 90000});
  await page.waitForSelector("#login-email", {state: "visible", timeout: 60000});
  await page.fill("#login-email", email); await page.fill("#login-password", secret); await page.click("#email-login-button");
  await page.waitForFunction(() => location.pathname !== "/login" || /refused|not|wrong|invalid/i.test(document.getElementById("identity-message")?.textContent || ""), null, {timeout: 60000}).catch(() => {});
  await page.waitForTimeout(2000);
  return {path: new URL(page.url()).pathname, message: (await page.locator("#identity-message").textContent().catch(() => "")) || ""};
}

// Administration keeps its sign-in in memory only, so it is opened inside the page, not by loading its address.
async function openAdministration(page) {
  await page.evaluate(() => { history.pushState({}, "", "/admin"); dispatchEvent(new PopStateEvent("popstate")); });
  await page.waitForSelector("#staff-admin", {state: "visible", timeout: 30000});
}
async function staffAction(page, label, email) {
  await page.waitForFunction(() => document.querySelectorAll("#staff-accounts article").length > 0, null, {timeout: 30000});
  const button = page.getByRole("button", {name: label + " for " + email});
  if (await button.count() !== 1) return {done: false, reason: "button not found"};
  await button.click();
  await page.waitForFunction(text => (document.getElementById("staff-message")?.textContent || "").includes(text), label + " is done.", {timeout: 60000}).catch(() => {});
  return {done: ((await page.locator("#staff-message").textContent()) || "").includes(label + " is done.")};
}
const foundingPlaces = async page => { const text = (await page.locator("#staff-counts").textContent().catch(() => "")) || "";
  const match = text.match(/Founding places\s*(\d+) of (\d+)/); return match ? Number(match[1]) : null; };
const accountCard = (page, email) => page.evaluate(address => {
  const node = [...document.querySelectorAll("#staff-accounts article")].find(card => card.querySelector("h3")?.textContent.trim() === address);
  return node ? {pending: /waiting for this person to choose a password/.test(node.textContent),
                 free_monthly_on_opening: /Free monthly Baltor Pro starts when the account opens/.test(node.textContent)} : null; }, email);

let state = existsSync(statePath) ? JSON.parse(readFileSync(statePath, "utf8")) : null;
try {
  if (linkStep) {
    if (!state) throw new Error("run the journeys first");
    const page = await newPage(), signedIn = await signIn(page, state.fresh.address, state.fresh.password);
    step("links", "the_superadmin_signs_in", signedIn.path !== "/login", signedIn);
    await openAdministration(page);
    await page.waitForSelector("#staff-links-form", {state: "visible", timeout: 30000}).catch(() => {});
    step("links", "the_sign_up_link_form_shows_for_a_superadmin", await page.locator("#staff-links-form").isVisible());
    await page.waitForFunction(() => document.querySelectorAll("#staff-accounts article").length > 0, null, {timeout: 30000}).catch(() => {});
    const foundingBefore = await foundingPlaces(page);
    const person = await inbox(), personPassword = password();
    const send = async address => {
      await page.fill("#staff-link-addresses", address); await page.check("#staff-link-free"); await page.click("#staff-link-button");
      await page.waitForFunction(text => (document.getElementById("staff-message")?.textContent || "").includes(text), address, {timeout: 60000}).catch(() => {});
      return ((await page.locator("#staff-message").textContent()) || "").trim();
    };
    const sent = await send(person.address);
    step("links", "a_link_with_free_monthly_is_sent", sent.includes("Link sent to " + person.address), {message: sent.slice(0, 200)});
    const pendingCard = await accountCard(page, person.address);
    step("links", "the_person_shows_as_pending_with_free_monthly_on_opening",
      pendingCard?.pending === true && pendingCard?.free_monthly_on_opening === true, {card: pendingCard});
    const message = await nextMessage(person, (from, text) => /baltor\.ai$/.test(from) && Boolean(confirmLink(text)));
    step("links", "the_message_names_the_sender_and_links_to_auth_confirm",
      Boolean(message) && message.subject.includes(state.fresh.address) && /invited you to Baltor/.test(message.subject),
      {from: message?.from, subject: message?.subject, link_host: message ? new URL(confirmLink(message.text)).host : null});
    const landed = message ? await choosePassword(await newPage(), confirmLink(message.text), personPassword) : {};
    step("links", "choosing_a_password_opens_the_account", Boolean(message) && landed.path !== "/auth/confirm", landed);
    step("links", "the_account_opens_with_the_staff_grant_of_baltor_pro",
      /includes Baltor Pro/i.test(landed.planTitle || "") && /free for this account each month/i.test(landed.planText || ""),
      {title: landed.planTitle, text: (landed.planText || "").slice(0, 120)});
    state = {...state, linked: [...(state.linked || []), {address: person.address, password: personPassword}]};
    writeFileSync(statePath, JSON.stringify(state), {mode: 0o600});
    await page.click("#refresh-staff"); await page.waitForTimeout(4000);
    const openedCard = await accountCard(page, person.address), foundingAfter = await foundingPlaces(page);
    step("links", "the_opened_account_leaves_the_pending_list", openedCard !== null && openedCard.pending === false, {card: openedCard});
    step("links", "the_staff_grant_takes_no_founding_place", foundingBefore !== null && foundingAfter === foundingBefore,
      {founding_before: foundingBefore, founding_after: foundingAfter});
    const again = await send(person.address);
    step("links", "a_second_link_to_the_same_address_is_refused",
      again.includes("No email sent, the account already exists: " + person.address), {message: again.slice(0, 200)});
    const extra = await nextMessage(person, from => /baltor\.ai$/.test(from), 60000);
    step("links", "no_second_message_arrives", extra === null, {subject: extra?.subject});
    step("links", "cleanup_the_checking_account_gives_back_its_grant", (await staffAction(page, "Revoke free monthly", person.address)).done);
    step("links", "cleanup_the_checking_account_is_switched_off", (await staffAction(page, "Disable", person.address)).done);
  } else if (!staffStep) {
    const freshOnly = process.argv.includes("--fresh-only");
    // Journey "fresh"
    const fresh = await inbox(), freshPassword = password(), page = await newPage();
    await signUpOnGetStarted(page, fresh.address);
    step("fresh", "get_started_takes_the_address", true);
    const message = await nextMessage(fresh, (from, text) => /baltor\.ai$/.test(from) && Boolean(confirmLink(text)));
    step("fresh", "the_message_comes_from_baltor_and_links_to_auth_confirm", Boolean(message), {from: message?.from, subject: message?.subject,
      link_host: message ? new URL(confirmLink(message.text)).host : null});
    const landed = message ? await choosePassword(page, confirmLink(message.text), freshPassword) : {};
    step("fresh", "choosing_a_password_signs_the_account_in", Boolean(message) && landed.path !== "/auth/confirm", landed);
    step("fresh", "the_founding_offer_covers_baltor_pro", /includes Baltor Pro/i.test((landed.planTitle || "") + " " + (landed.planText || "")), {title: landed.planTitle});
    if (freshOnly) throw new Error("stopped after the fresh journey, as asked");
    // Journey "provider_first"
    const first = await inbox(), firstPassword = password(), finalPassword = password();
    const providerSignup = await fetch(identity.project_url + "/auth/v1/signup", {method: "POST",
      headers: {"Content-Type": "application/json", apikey: identity.publishable_key}, body: JSON.stringify({email: first.address, password: firstPassword})});
    step("provider_first", "the_provider_public_sign_up_answered", true, {status: providerSignup.status});
    const page2 = await newPage();
    await signUpOnGetStarted(page2, first.address);
    const message2 = await nextMessage(first, (from, text) => /baltor\.ai$/.test(from) && Boolean(confirmLink(text)));
    step("provider_first", "baltor_sign_up_sends_its_own_link", Boolean(message2), {from: message2?.from, subject: message2?.subject});
    const landed2 = message2 ? await choosePassword(page2, confirmLink(message2.text), finalPassword) : {};
    step("provider_first", "choosing_a_password_signs_the_account_in", Boolean(message2) && landed2.path !== "/auth/confirm", landed2);
    const oldStatus = await providerPassword(first.address, firstPassword), newStatus = await providerPassword(first.address, finalPassword);
    step("provider_first", "the_provider_first_password_is_refused", oldStatus >= 400, {status: oldStatus});
    step("provider_first", "the_password_chosen_on_baltor_works_at_the_provider", newStatus === 200, {status: newStatus});
    const signedIn = await signIn(await newPage(), first.address, finalPassword);
    step("provider_first", "baltor_sign_in_accepts_the_new_password", signedIn.path !== "/login", signedIn);
    state = {fresh: {address: fresh.address, password: freshPassword}, first: {address: first.address, password: finalPassword}};
    writeFileSync(statePath, JSON.stringify(state), {mode: 0o600});
  } else {
    if (!state) throw new Error("run the journeys first");
    const page = await newPage(), signedIn = await signIn(page, state.fresh.address, state.fresh.password);
    step("staff", "the_superadmin_signs_in", signedIn.path !== "/login", signedIn);
    // The page keeps its sign-in in memory only, so Administration is opened inside the page, not by loading its address.
    await page.evaluate(() => { history.pushState({}, "", "/admin"); dispatchEvent(new PopStateEvent("popstate")); });
    await page.waitForSelector("#staff-admin", {state: "visible", timeout: 30000});
    const role = (await page.locator("#staff-role").textContent()) || "";
    step("staff", "administration_shows_the_superadmin_role", role.trim() === "superadmin", {role});
    const act = async (label, email) => {
      await page.waitForFunction(() => document.querySelectorAll("#staff-accounts article").length > 0, null, {timeout: 30000});
      const button = page.getByRole("button", {name: label + " for " + email});
      if (await button.count() !== 1) return {done: false, reason: "button not found"};
      await button.click();
      await page.waitForFunction(text => (document.getElementById("staff-message")?.textContent || "").includes(text), label + " is done.", {timeout: 60000}).catch(() => {});
      return {done: ((await page.locator("#staff-message").textContent()) || "").includes(label + " is done.")};
    };
    const other = state.first.address, self = state.fresh.address;
    // A run stopped part way can leave the other checking account switched off; switch it on before the checks.
    await page.waitForFunction(() => document.querySelectorAll("#staff-accounts article").length > 0, null, {timeout: 30000});
    if (await page.getByRole("button", {name: "Enable for " + other}).count() === 1) step("staff", "restore_a_state_left_by_an_earlier_run", (await act("Enable", other)).done);
    if (await page.getByRole("button", {name: "Grant free monthly for " + other}).count() === 1) step("staff", "restore_free_monthly_left_by_an_earlier_run", (await act("Grant free monthly", other)).done);
    step("staff", "revoke_free_monthly_for_another_account", (await act("Revoke free monthly", other)).done);
    step("staff", "grant_free_monthly_for_another_account", (await act("Grant free monthly", other)).done);
    step("staff", "switch_another_account_off", (await act("Disable", other)).done);
    const refused = await signIn(await newPage(), other, state.first.password);
    step("staff", "a_switched_off_account_cannot_sign_in", refused.path === "/login", refused);
    step("staff", "switch_it_on_again", (await act("Enable", other)).done);
    // Every checking account, including those of earlier diagnostic runs, gives its founding place back, and every
    // one except the signed-in superadmin is switched off. Checking accounts are recognised by their address prefix.
    const checking = await page.evaluate(() => [...document.querySelectorAll("#staff-accounts article h3")]
      .map(node => node.textContent.trim()).filter(text => text.startsWith("baltor-check-")));
    const released = [], switchedOff = [];
    for (const email of checking) {
      const free = await page.getByRole("button", {name: "Revoke free monthly for " + email}).count();
      if (free === 1 && (await act("Revoke free monthly", email)).done) released.push(email);
      if (email !== self && await page.getByRole("button", {name: "Disable for " + email}).count() === 1
          && (await act("Disable", email)).done) switchedOff.push(email);
    }
    // Read the state afterwards rather than counting this run's clicks: an account switched off by an earlier run, or
    // one that never confirmed and so has no Baltor account, has no Disable button and is already not active.
    await page.click("#refresh-staff"); await page.waitForTimeout(4000);
    const stillFree = [], stillActive = [];
    for (const email of checking) {
      if (await page.getByRole("button", {name: "Revoke free monthly for " + email}).count()) stillFree.push(email);
      if (email !== self && await page.getByRole("button", {name: "Disable for " + email}).count()) stillActive.push(email);
    }
    step("staff", "checking_accounts_give_back_their_founding_places", checking.length >= 2 && stillFree.length === 0,
      {checking: checking.length, released: released.length, still_free: stillFree.length});
    step("staff", "checking_accounts_other_than_the_superadmin_are_switched_off", stillActive.length === 0,
      {switched_off_now: switchedOff.length, still_active: stillActive.length});
    // Each action's message replaces the list summary, so the founding count is read from the counts panel.
    const founding = await foundingPlaces(page);
    step("staff", "the_account_list_reports_its_founding_places", founding !== null, {founding_places_used: founding});
  }
} catch (error) {
  step("run", "journey_completed", false, {error: String(error).slice(0, 300)});
} finally {
  await browser.close();
}
const report = {record_type: "live_account_journeys/v1", origin, observed_at: new Date().toISOString(), staff_step: staffStep, sign_up_link_step: linkStep,
  passed: steps.filter(row => row.passed).length, total: steps.length, all_passed: steps.every(row => row.passed), steps,
  limits: "Disposable inboxes at a public service; real accounts are created. No password, token or message body is recorded."};
writeFileSync(output, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({passed: report.passed, total: report.total, all_passed: report.all_passed,
  failures: steps.filter(row => !row.passed).map(row => row.journey + ":" + row.name)}));
process.exit(report.all_passed ? 0 : 1);
