/* One person's OAuth consent on the deployed site, in a real browser, for the ChatGPT app check.

   node tools/chatgpt_app_consent.mjs AUTHORIZATION_URL CALLBACK_PREFIX CREDENTIALS_JSON EVIDENCE_DIR [approve|deny]

   The browser opens the authorization address an MCP client built, signs in on the consent page's own
   sign-in route with the account in CREDENTIALS_JSON (a fresh_account_journey/v1 state file, mode 0600,
   outside the repository), records what the consent page shows, takes the decision and stops at the
   client's loopback callback, which is answered inside the browser so nothing listens on a port. It
   prints one JSON line: the callback address (code, state and iss) and what the page showed. The line
   holds the one-time code, which only the calling process reads; no password or token is printed or saved.
   Screenshots of the consent page at desktop and phone widths go to EVIDENCE_DIR. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {lstatSync, readFileSync} from "node:fs";
import {resolve} from "node:path";

const [authorizationUrl, callbackPrefix, credentialsPath, evidenceDir, decision = "approve"] = process.argv.slice(2);
if (!authorizationUrl || !callbackPrefix || !credentialsPath || !evidenceDir || !["approve", "deny"].includes(decision))
  throw new Error("Use AUTHORIZATION_URL CALLBACK_PREFIX CREDENTIALS_JSON EVIDENCE_DIR [approve|deny].");
const authorization = new URL(authorizationUrl), callback = new URL(callbackPrefix);
if (authorization.protocol !== "https:" || authorization.username || authorization.password)
  throw new Error("The authorization address must be HTTPS without credentials.");
if (callback.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(callback.hostname))
  throw new Error("The callback must be a loopback address.");
const held = lstatSync(credentialsPath);
if (!held.isFile() || held.isSymbolicLink() || (held.mode & 0o077) !== 0 || held.uid !== process.getuid())
  throw new Error("The credentials file must be a regular file readable by this user only.");
const state = JSON.parse(readFileSync(credentialsPath, "utf8"));
const email = state?.fresh?.address, password = state?.fresh?.password;
if (typeof email !== "string" || typeof password !== "string" || !email || !password)
  throw new Error("The credentials file holds no account.");

const origin = authorization.origin;
const browser = await chromium.launch({executablePath: "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox"]});
const shown = {};
try {
  const context = await browser.newContext({viewport: {width: 1440, height: 900}});
  let callbackUrl = null;
  await context.route(url => url.href.startsWith(callback.origin + callback.pathname), async route => {
    callbackUrl = route.request().url();
    await route.fulfill({status: 200, contentType: "text/html", body: "<!doctype html><title>Connected</title><p>Connected.</p>"});
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
    await page.fill("#login-email", email);
    await page.fill("#login-password", password);
    await page.click("#email-login-button");
    await page.waitForFunction(() => location.pathname === "/oauth/consent", null, {timeout: 60000});
  }
  await page.waitForSelector("#oauth-consent-details", {state: "visible", timeout: 60000});
  shown.heading = (await page.locator("#oauth-consent-heading").textContent() || "").trim();
  shown.client_name = (await page.locator("#oauth-client-name").textContent() || "").trim();
  shown.destination = (await page.locator("#oauth-client-destination").textContent() || "").trim();
  shown.scopes = await page.locator("#oauth-consent-scopes li").allTextContents();
  shown.status = (await page.locator("#oauth-consent-status").textContent() || "").trim();
  await page.screenshot({path: resolve(evidenceDir, "consent-1440.png"), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  await page.waitForTimeout(300);
  shown.phone_no_horizontal_overflow = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  await page.screenshot({path: resolve(evidenceDir, "consent-390.png"), fullPage: true});
  await page.click(decision === "approve" ? "#oauth-approve" : "#oauth-deny");
  const until = Date.now() + 60000;
  while (!callbackUrl && Date.now() < until) await page.waitForTimeout(250);
  if (!callbackUrl) throw new Error("The consent page did not return to the client.");
  process.stdout.write(JSON.stringify({record_type: "chatgpt_app_consent/v1", origin, decision, callback_url: callbackUrl, shown}) + "\n");
} finally {
  await browser.close();
}
