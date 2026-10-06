/* Complete one Stripe-hosted page in a real browser with a Stripe test card, for the test-mode journey check.

   Kind: operator check helper. It is driven by tools/check_stripe_test_journey.py and never by a customer.
   It opens one page that the service under test created, in Stripe test mode only:

   - checkout: fills the hosted Checkout form with a test card and submits it, then waits for Stripe to send
     the browser back to the return address the service configured;
   - portal: opens the customer portal, reads whether the invoice history lists a paid invoice, and cancels the
     subscription through the portal's own buttons when asked to.

   The page address arrives on standard input as JSON, never as an argument, because a hosted page address
   carries a session secret. The answer on standard output names what the page showed and where the browser
   ended; it never repeats the page address. A page that is not a Stripe test-mode page is refused before it
   is opened: the address must be HTTPS on checkout.stripe.com or billing.stripe.com, and a checkout session
   identity must start with cs_test_. Test card numbers are Stripe's published test numbers, listed on the testing
   page of Stripe's documentation, which no live account accepts. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";

const read = async () => { let text = ""; for await (const chunk of process.stdin) text += chunk; return JSON.parse(text); };
const settings = await read();
const answer = value => { process.stdout.write(JSON.stringify(value) + "\n"); };
const address = new URL(settings.url);
const host = settings.operation === "checkout" ? "checkout.stripe.com" : "billing.stripe.com";
if (address.protocol !== "https:" || address.hostname !== host || address.username || address.password
    || (settings.operation === "checkout" && !address.pathname.includes("/cs_test_"))) {
  answer({record_type: "stripe_test_page_result/v1", operation: settings.operation, refused: "not_a_stripe_test_page"});
  process.exit(2);
}
const returnPrefix = String(settings.return_prefix || "");
const browser = await chromium.launch({headless: true});
const context = await browser.newContext({locale: "en-US", viewport: {width: 1280, height: 1000}});
const page = await context.newPage();
const steps = [];
const note = (name, detail = {}) => steps.push({step: name, at: new Date().toISOString(), ...detail});
const screenshot = async name => {
  if (!settings.evidence_prefix) return null;
  const path = settings.evidence_prefix + "-" + name + ".png";
  await page.screenshot({path, fullPage: true}).catch(() => null);
  return path;
};
const visible = async locator => { try { return await locator.first().isVisible(); } catch (_) { return false; } };
async function fillIfVisible(selector, value) {
  const field = page.locator(selector);
  if (await visible(field)) { await field.first().fill(value); return true; }
  return false;
}
let outcome = {record_type: "stripe_test_page_result/v1", operation: settings.operation};
try {
  await page.goto(address.href, {waitUntil: "domcontentloaded", timeout: 60000});
  if (settings.operation === "checkout") {
    await page.locator("#email, #cardNumber, [data-testid='card-accordion-item']").first().waitFor({timeout: 45000});
    note("checkout_page_open", {title: await page.title()});
    outcome.amount_text = (await page.locator("[data-testid='product-summary-total-amount']").first().textContent({timeout: 5000}).catch(() => ""))
      .replace(/\s+/g, " ").trim();
    outcome.page_terms = (await page.locator("body").innerText().catch(() => "")).split("\n")
      .filter(line => /sold through|authorize|provided by|merchant/i.test(line)).slice(0, 3);
    outcome.email_field_shown = await fillIfVisible("#email", settings.email);
    /* Link, Stripe's saved-details option, starts ticked and then asks for a phone number. The check pays with a card
       only, so it is unticked before the card form is filled. */
    const remember = page.locator("#enableStripePass");
    if (await visible(remember) && await remember.first().isChecked().catch(() => false)) { await remember.first().uncheck({force: true}); note("link_unticked"); }
    const cardChoice = page.locator("[data-testid='card-accordion-item']");
    if (await visible(cardChoice) && !(await visible(page.locator("#cardNumber")))) { await cardChoice.first().click(); note("card_method_selected"); }
    await page.locator("#cardNumber").waitFor({timeout: 20000});
    await page.locator("#cardNumber").fill(settings.card);
    await page.locator("#cardExpiry").fill(settings.expiry || "12 / 34");
    await page.locator("#cardCvc").fill(settings.cvc || "123");
    await fillIfVisible("#billingName", settings.name || "Baltor Test Customer");
    const country = page.locator("#billingCountry");
    if (await visible(country)) await country.first().selectOption(settings.country || "US").catch(() => null);
    /* An account that computes tax at checkout asks for the whole billing address; a test address is used. */
    if (await fillIfVisible("#billingAddressLine1", settings.address_line || "1 Test Way")) await page.keyboard.press("Escape");
    await fillIfVisible("#billingLocality", settings.city || "Altoona");
    await fillIfVisible("#billingPostalCode", settings.postal_code || "16601");
    const area = page.locator("#billingAdministrativeArea");
    if (await visible(area)) await area.first().selectOption(settings.state || "PA").catch(() => null);
    if (await visible(remember) && await remember.first().isChecked().catch(() => false)) await remember.first().uncheck({force: true}).catch(() => null);
    note("form_filled", {email_field_shown: outcome.email_field_shown});
    /* The page recalculates tax once the address is complete; the total it then shows is what the card is charged. */
    await page.waitForLoadState("networkidle", {timeout: 15000}).catch(() => null);
    await page.waitForTimeout(1500);
    outcome.total_due_text = (await page.locator("[data-testid='product-summary-total-amount']").first().textContent().catch(() => ""))
      .replace(/\s+/g, " ").trim();
    outcome.tax_lines = (await page.locator("[data-testid='order-details']").first().innerText().catch(() => "")).split("\n")
      .filter(line => /tax/i.test(line)).slice(0, 2);
    const submit = page.locator("[data-testid='hosted-payment-submit-button']");
    await submit.first().click();
    note("submitted");
    /* A click that lands while the page is still recalculating is ignored by the page; one more click is sent
       only when the page still shows the form, is not processing and shows no error. */
    if (settings.authenticate) {
      /* A card that asks for authentication opens Stripe's test challenge in a frame; its Complete button stands
         in for the cardholder's bank. */
      const deadline = Date.now() + 60000;
      let completed = false;
      while (!completed && Date.now() < deadline) {
        for (const frame of page.frames()) {
          const button = frame.locator("#test-source-authorize-3ds");
          if (await button.count().catch(() => 0) && await button.first().isVisible().catch(() => false)) {
            await button.first().click({timeout: 10000}).then(() => { completed = true; }).catch(() => null);
            if (completed) { note("authentication_completed"); break; }
          }
        }
        if (!completed) await page.waitForTimeout(1000);
      }
      outcome.authentication_completed = completed;
    }
    if (!settings.expect_decline) {
      const left = await page.waitForURL(url => url.href.startsWith(returnPrefix), {timeout: 30000, waitUntil: "commit"})
        .then(() => true).catch(() => false);
      const failed = left ? false : await visible(page.locator(".FieldError, [role='alert']"));
      if (failed) outcome.form_errors = (await page.locator(".FieldError, [role='alert']").allInnerTexts()).slice(0, 4);
      else if (!left && await visible(submit) && await submit.first().isEnabled().catch(() => false)) {
        await submit.first().click(); note("submitted_again");
      }
    }
    if (settings.expect_decline) {
      const error = page.locator("#cardNumber-fieldset .FieldError, .FieldError, [role='alert']");
      await error.first().waitFor({timeout: 45000});
      outcome.decline_message = (await error.first().textContent()).trim();
      outcome.returned = false;
    } else {
      await page.waitForURL(url => url.href.startsWith(returnPrefix), {timeout: 90000, waitUntil: "commit"});
      outcome.returned = true;
      const returned = new URL(page.url());
      outcome.returned_path = returned.pathname;
      note("returned_to_service", {path: returned.pathname});
    }
  } else {
    await page.waitForFunction(() => /current subscription|invoice history/i.test(document.body.innerText), null, {timeout: 45000});
    note("portal_open", {title: await page.title()});
    const text = await page.locator("body").innerText();
    outcome.shows_invoice_history = /invoice history/i.test(text);
    outcome.shows_paid_invoice = /\bPaid\b/.test(text);
    outcome.shows_plan = /Baltor Pro/.test(text);
    outcome.price_lines = text.split("\n").filter(line => /\$\d+\.\d\d/.test(line)).slice(0, 4);
    outcome.next_billing_line = text.split("\n").find(line => /next billing date|renews|cancels on/i.test(line)) || "";
    outcome.shows_cancel = await visible(page.getByRole("button", {name: /cancel (subscription|plan)/i}))
      || await visible(page.getByRole("link", {name: /cancel (subscription|plan)/i}));
    await screenshot("portal");
    if (settings.cancel) {
      const control = (await visible(page.getByRole("link", {name: /cancel (subscription|plan)/i})))
        ? page.getByRole("link", {name: /cancel (subscription|plan)/i}) : page.getByRole("button", {name: /cancel (subscription|plan)/i});
      await control.first().click();
      note("cancel_opened");
      const confirm = page.getByRole("button", {name: /cancel (subscription|plan)/i});
      await confirm.first().waitFor({timeout: 30000});
      await confirm.first().click();
      note("cancel_confirmed");
      await page.waitForFunction(() => /cancels on|will be canceled|subscription has been canceled|renew subscription|don.t cancel/i
        .test(document.body.innerText), null, {timeout: 45000});
      outcome.cancelled_in_portal = true;
      outcome.after_cancel_text = (await page.locator("body").innerText()).split("\n").filter(line => /cancel|renew/i.test(line)).slice(0, 4);
      await screenshot("portal-cancelled");
    }
  }
  outcome.ok = true;
} catch (error) {
  outcome.ok = false;
  outcome.error = String(error && error.message || error).split("\n")[0].slice(0, 300);
  /* Where the browser stood, without the query or fragment, which can carry a session secret. */
  try { const at = new URL(page.url()); outcome.final_location = at.protocol + "//" + at.host + at.pathname; } catch (_) {}
  outcome.page_text = (await page.locator("body").innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 1200);
  outcome.screenshot = await screenshot("failure");
}
outcome.steps = steps;
await browser.close();
answer(outcome);
process.exit(outcome.ok ? 0 : 1);
