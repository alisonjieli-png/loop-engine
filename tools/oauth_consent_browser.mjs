/* One person's OAuth consent on the deployed site, in a real browser, for a native client's connection check.

   node tools/oauth_consent_browser.mjs AUTHORIZATION_URL CALLBACK_PREFIX CREDENTIALS_JSON EVIDENCE_DIR \
     [approve|deny] [answer|deliver]

   AUTHORIZATION_URL is the address a client such as Claude Code built and printed. The browser opens it, follows
   the service to its consent page, signs in through that page's own sign-in route with the checking account in
   CREDENTIALS_JSON, records what the page shows and takes the decision. With `answer`, the default, it stops at the
   client's loopback callback and answers it inside the browser, so nothing needs to listen on a port. With
   `deliver` the browser goes on to the callback address as a person's browser does, so a client listening there,
   such as Claude Code, receives it itself. It prints one JSON line: the callback address (code, state and issuer)
   and what the page showed. That line holds the one-time code, which only the calling process reads; no password
   or token is printed or saved. Screenshots of the consent page at desktop and phone widths go to EVIDENCE_DIR.

   CREDENTIALS_JSON must be a fresh_account_journey/v1 state file whose journey completed: an account made through
   Baltor's own public sign-up by tools/check_live_account_journeys.mjs --fresh-only, mode 0600, outside the
   repository. Any other account, staff included, is refused before the browser starts. Administration and
   payment addresses are refused inside the browser.

   The arguments and the output fields are those of tools/chatgpt_app_consent.mjs, written the same day for the
   ChatGPT app check, so the two can become one. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {lstatSync, readFileSync} from "node:fs";
import {resolve} from "node:path";

const [authorizationUrl, callbackPrefix, credentialsPath, evidenceDir, decision = "approve", callbackMode = "answer"] =
  process.argv.slice(2);
if (!authorizationUrl || !callbackPrefix || !credentialsPath || !evidenceDir || !["approve", "deny"].includes(decision)
    || !["answer", "deliver"].includes(callbackMode))
  throw new Error("Use AUTHORIZATION_URL CALLBACK_PREFIX CREDENTIALS_JSON EVIDENCE_DIR [approve|deny] [answer|deliver].");
const authorization = new URL(authorizationUrl), callback = new URL(callbackPrefix);
if (authorization.protocol !== "https:" || authorization.username || authorization.password)
  throw new Error("The authorization address must be HTTPS without credentials.");
if (callback.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(callback.hostname))
  throw new Error("The callback must be a loopback address.");
const held = lstatSync(credentialsPath);
if (!held.isFile() || held.isSymbolicLink() || (held.mode & 0o077) !== 0 || held.uid !== process.getuid())
  throw new Error("The credentials file must be a regular file readable by this user only.");
const state = JSON.parse(readFileSync(credentialsPath, "utf8"));
const email = state?.fresh?.address, password = state?.fresh?.password;
if (state?.record_type !== "fresh_account_journey/v1" || state?.stage !== "complete"
    || typeof email !== "string" || !email.startsWith("baltor-check-") || typeof password !== "string" || !password)
  throw new Error("The credentials file must hold a checking account that Baltor's public sign-up completed.");

const origin = authorization.origin;
// What a person on this page never needs: administration, payment sessions and the provider's own sign-up.
const refusedPath = path => /^\/api\/v1\/(admin|billing\/(checkout|portal))(?:\/|$)/.test(path) || path === "/auth/v1/signup";
const browser = await chromium.launch({executablePath: "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox"]});
const shown = {}, refused = [];
try {
  const context = await browser.newContext({viewport: {width: 1440, height: 900}});
  let callbackUrl = null;
  await context.route("**/*", async route => {
    const url = new URL(route.request().url());
    if (url.origin === callback.origin && url.pathname === callback.pathname) {
      callbackUrl = url.href;
      if (callbackMode === "deliver") return route.continue();
      return route.fulfill({status: 200, contentType: "text/html", body: "<!doctype html><title>Connected</title><p>Connected.</p>"});
    }
    if (refusedPath(url.pathname)) { refused.push(url.pathname); return route.abort(); }
    return route.continue();
  });
  const page = await context.newPage();
  await page.goto(authorization.href, {waitUntil: "domcontentloaded", timeout: 60000});
  await page.waitForFunction(() => location.pathname === "/oauth/consent", null, {timeout: 30000});
  await page.waitForFunction(() => !document.getElementById("oauth-sign-in")?.hidden
    || !document.getElementById("oauth-consent-details")?.hidden, null, {timeout: 30000});
  if (await page.locator("#oauth-sign-in").isVisible()) {
    shown.sign_in_first = true;
    await page.click("#oauth-sign-in");
    await page.waitForSelector("#login-email", {state: "visible", timeout: 30000});
    await page.waitForFunction(() => !document.getElementById("email-login-button")?.disabled, null, {timeout: 30000});
    await page.fill("#login-email", email);
    await page.fill("#login-password", password);
    await page.click("#email-login-button");
    await page.waitForFunction(() => location.pathname === "/oauth/consent", null, {timeout: 60000});
  }
  await page.waitForSelector("#oauth-consent-details", {state: "visible", timeout: 60000});
  await page.waitForFunction(() => !document.getElementById("oauth-approve")?.disabled, null, {timeout: 30000});
  shown.heading = ((await page.locator("#oauth-consent-heading").textContent()) || "").trim();
  shown.client_name = ((await page.locator("#oauth-client-name").textContent()) || "").trim();
  shown.destination = ((await page.locator("#oauth-client-destination").textContent()) || "").trim();
  shown.scopes = (await page.locator("#oauth-consent-scopes li").allTextContents()).map(text => text.trim());
  shown.status = ((await page.locator("#oauth-consent-status").textContent()) || "").trim();
  await page.screenshot({path: resolve(evidenceDir, "consent-1440.png"), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  await page.waitForTimeout(300);
  shown.phone_no_horizontal_overflow = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  await page.screenshot({path: resolve(evidenceDir, "consent-390.png"), fullPage: true});
  await page.click(decision === "approve" ? "#oauth-approve" : "#oauth-deny");
  const until = Date.now() + 60000;
  while (!callbackUrl && Date.now() < until) await page.waitForTimeout(250);
  if (!callbackUrl) throw new Error("The consent page did not return to the client.");
  if (callbackMode === "deliver") {
    // What the client's own callback page answered, read once it has loaded; a client that is not listening leaves
    // an error page, and the caller can still hand it the address.
    await page.waitForLoadState("domcontentloaded", {timeout: 15000}).catch(() => {});
    shown.callback_page = ((await page.locator("body").textContent().catch(() => "")) || "").trim().slice(0, 200);
  }
  process.stdout.write(JSON.stringify({record_type: "oauth_browser_consent/v1", origin, decision, callback_mode: callbackMode,
    callback_url: callbackUrl, shown, refused_requests: refused}) + "\n");
} finally {
  await browser.close();
}
