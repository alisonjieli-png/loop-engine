"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let token = "", generation = 0, busy = false, capabilities = null, accessOptions = null, accessRequest = null, accessBusy = false;
  let connectionBusy = false, recipes = null, afterLogin = null, principalScopes = [];
  let identityClient = null, identityConfiguration = null, authenticationMode = "host_key";
  let clientAccess = null, catalogueBrowser = null;
  const pending = new Set(), downloads = new Map(), billingRequests = new Map();
  const message = (id, text, error = false) => { $(id).textContent = text; $(id).classList.toggle("error", error); };
  const element = (tag, text, className = "") => { const item = document.createElement(tag); item.textContent = text; if (className) item.className = className; return item; };
  const show = name => {
    document.body.dataset.page = name;
    document.querySelectorAll("[data-view]").forEach(item => { item.hidden = item.dataset.view !== name; });
    document.querySelectorAll("[data-page]").forEach(item => { if (item.dataset.page === name) item.setAttribute("aria-current", "page"); else item.removeAttribute("aria-current"); });
  };
  // "/get-started" and "/connect" open the same Get started page. The serving route table does not list
  // "/get-started" yet, so that address works through the navigation and a direct visit is not served.
  const routeNames = {"/":"home", "/app":"workspace", "/login":"login", "/signup":"signup", "/pricing":"pricing", "/account":"account", "/admin":"admin", "/docs":"docs", "/how-it-works":"about", "/connect":"setup", "/get-started":"setup", "/examples":"examples", "/security":"security", "/privacy":"privacy", "/waitlist":"waitlist", "/auth/callback":"login"};
  if (location.pathname === "/auth/callback") {
    // Confirmation tokens in a provider redirect never enter our logs, storage or links.
    history.replaceState({}, "", "/login");
    $("identity-message").textContent = "Your email link has returned to Baltor. Sign in to continue; the provider will check your confirmation status.";
  }
  const serviceName = document.title.split(" | ")[0];
  const route = () => { const name = routeNames[location.pathname] || "home"; show(name); document.title = serviceName + " | " + {home:"Material your coding tools can search", workspace:"Intelligence workspace", login:"Sign in", signup:"Account status", pricing:"Pricing", account:"Your account", admin:"Access administration", docs:"Setup guide", about:"How it works", setup:"Get started", examples:"Try your first retrieval", security:"Access and data boundaries", privacy:"Privacy notice", waitlist:"Ask for an invitation"}[name]; };
  const navigate = path => { history.pushState({}, "", path); route(); $("main").focus({preventScroll:true}); const target = location.hash ? document.getElementById(location.hash.slice(1)) : null; if (target) target.scrollIntoView(); else scrollTo(0,0); };
  document.querySelectorAll("[data-page]").forEach(link => link.addEventListener("click", event => { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return; event.preventDefault(); if (link.dataset.afterLogin && routeNames[link.dataset.afterLogin]) afterLogin = link.dataset.afterLogin; navigate(link.getAttribute("href")); }));
  addEventListener("popstate", route); route();
  /* The public access action, the pricing state and the personal-key wording come from the service capabilities record, never from wording kept in this file.
     They are read only from this exact record version, because another version may rename a field or give it a different meaning.
     Until the service answers, if it never answers, and for any other record version, the page keeps the careful state:
     the waiting list, payment not open, personal keys described as being prepared. */
  const CAPABILITIES_RECORD_TYPE = "service_capabilities/v1";
  const accessStates = {
    open:{label:"Create your account", href:"/signup", note:"Account creation is open. Search is free, and one downloaded item is the measured unit."},
    waiting:{label:"Join the waiting list", href:"/signup#waiting-list", note:"Accounts open in small groups. Join the waiting list and we will write to you when your turn comes."}};
  const paymentStates = {
    open:{badge:"Payment open", note:"Payment is open. Start or manage your subscription from your account page.", teaser:"Payment is open. Invited accounts stay free."},
    closed:{badge:"Payment not open", note:"Payment is not open yet. Nothing on this page charges you today, and invited accounts stay free.", teaser:"Payment is not open yet. Nothing on this page charges you today."}};
  const applyAccessState = open => {
    const state = open === true ? accessStates.open : accessStates.waiting;
    for (const id of ["hero-primary", "pricing-primary", "closing-primary"]) {
      $(id).setAttribute("href", state.href); $(id).dataset.accessState = open === true ? "open" : "waiting";
      $(id + "-label").textContent = state.label;
    }
    $("hero-access-note").textContent = state.note;
  };
  const applyPaymentState = open => {
    const state = open === true ? paymentStates.open : paymentStates.closed;
    $("pricing-state").textContent = state.badge; $("pricing-payment-state").textContent = state.note;
    $("pricing-teaser-note").textContent = state.teaser;
  };
  const clientAccessStates = {
    open:{offer:"You can also create and revoke a key for each device from your account page.",
          plan:"Create and revoke a key for every client you connect, from your account page."},
    closed:{offer:"Creating and revoking a key for each device from your account page is being prepared. Today the person who runs the service issues your key.",
            plan:"Creating and revoking a key for every client you connect, from your account page, is being prepared. Today the person who runs the service issues your key."}};
  const applyClientAccessState = open => {
    const state = open === true ? clientAccessStates.open : clientAccessStates.closed;
    $("offer-usage-keys").textContent = state.offer; $("plan-keys-detail").textContent = state.plan;
  };
  applyAccessState(false); applyPaymentState(false); applyClientAccessState(false);
  /* The benefit list on the homepage. Every detail is written in the page source, so a reader who never runs this
     file sees all six. Once this file runs, one benefit is open at a time. Pointing at a title, moving keyboard focus
     to it and pressing it each open that one and close the others, so a touch screen and a keyboard reach the same
     detail that a mouse reaches. Nothing moves or fades, so a reduced-motion setting changes nothing here. */
  const benefitTitles = [...document.querySelectorAll("[data-benefit-title]")];
  const benefitItem = title => title.closest("[data-benefit]");
  const benefitDetail = title => benefitItem(title).querySelector("[data-benefit-detail]");
  const openBenefit = name => {
    for (const title of benefitTitles) {
      const open = title.dataset.benefitTitle === name;
      title.setAttribute("aria-expanded", String(open));
      benefitItem(title).dataset.open = String(open);
      benefitDetail(title).hidden = !open;
    }
  };
  for (const title of benefitTitles) {
    const name = title.dataset.benefitTitle;
    title.addEventListener("click", () => openBenefit(name));
    title.addEventListener("focus", () => openBenefit(name));
    benefitItem(title).addEventListener("mouseenter", () => openBenefit(name));
  }
  if (benefitTitles.length) openBenefit(benefitTitles[0].dataset.benefitTitle);
  const themes = ["system", "light", "dark"];
  const createIdentityClient = settings => window.BaltorIdentitySdk.createClient(settings.project_url, settings.publishable_key,
    {auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});
  let theme = "light";
  $("theme").addEventListener("click", () => { theme = themes[(themes.indexOf(theme) + 1) % themes.length]; if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme; $("theme").textContent = "Appearance: " + theme; });
  function disconnect() {
    generation++; token = ""; principalScopes = []; authenticationMode = "host_key"; for (const controller of pending) controller.abort(); pending.clear(); downloads.clear(); billingRequests.clear();
    $("access-token").value = ""; $("identity").hidden = true; $("connect-form").hidden = false; $("connection-state").textContent = "Not connected";
    ["query", "search-button", "search-mode", "refresh-usage", "refresh-billing"].forEach(id => { $(id).disabled = true; });
    $("results").replaceChildren(element("p", "Connect to search permitted material.", "empty")); $("identity-facts").replaceChildren();
    $("usage").textContent = "Connect to inspect your permitted usage records."; $("billing").textContent = "Connect to check this service's billing configuration.";
    $("result-count").textContent = "Connect to search"; $("query").value = ""; message("search-message", ""); message("billing-message", "");
    $("account-facts").replaceChildren(); $("account-state").textContent = "Not connected";
    $("account-note").textContent = "Sign in to see your service identity, usage and available subscription settings.";
    $("workspace-access").textContent = "Sign in to search"; $("workspace-access-note").textContent = "Search and downloads are scoped to your service account.";
    $("workspace-access-link").textContent = "Sign in to this service"; $("account-access-link").textContent = "Sign in";
    accessOptions = null; accessRequest = null; $("admin-nav").hidden = true; $("admin-controls").hidden = true; $("admin-login").hidden = false; $("refresh-access").disabled = true;
    $("issued-token").value = ""; $("issued-access").hidden = true; $("access-list").replaceChildren(); $("token-label").value = "";
    message("admin-message", "Sign in with an administrator service token. Email is not required.");
    $("test-protocol").disabled = true; $("setup-identity").textContent = "Sign in with your service token to run the connection check.";
    $("protocol-tools").replaceChildren(); message("protocol-result", "Not tested. No model calls are made by this check.");
    clientAccess?.reset(); catalogueBrowser?.reset();
  }
  $("disconnect").addEventListener("click", async () => {
    const previousToken = token, previousMode = authenticationMode, previousClient = identityClient;
    disconnect(); const epoch = generation;
    message("connection-message", "Disconnected. Access and displayed data cleared.");
    if (previousMode !== "browser_identity" || !previousToken) return;
    // New sign-ins use a separate in-memory client. A delayed sign-out must
    // neither clear their session nor repopulate the page being disconnected.
    identityClient = identityConfiguration ? createIdentityClient(identityConfiguration) : null;
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
    let serviceRevoked = false, providerRevoked = false;
    try {
      const response = await fetch("/api/v1/account/logout", {method:"POST",credentials:"omit",redirect:"error",cache:"no-store",signal:controller.signal,
        headers:{Authorization:"Bearer " + previousToken,"Content-Type":"application/json"},body:JSON.stringify({record_type:"service_browser_logout_request/v1"})});
      if (response.ok) { const value = await response.json(); serviceRevoked = value.result?.committed === true && value.result?.revoked === true; }
    } catch (_) {} finally { clearTimeout(timer); }
    try { providerRevoked = !(await previousClient.auth.signOut({scope:"local"})).error; } catch (_) {}
    if (epoch === generation && (!serviceRevoked || !providerRevoked)) message("identity-message", "This page is cleared, but remote sign-out was not fully confirmed. A session may remain valid until expiry.", true);
  });
  async function protocolResponse(response, requestId) {
    const mediaType = response.headers.get("content-type")?.split(";")[0].trim();
    if (mediaType === "application/json") return response.json();
    if (mediaType !== "text/event-stream" || !response.body) throw new Error("Unsupported protocol response format.");
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = "", received = 0, events = 0;
    try {
      while (true) {
        const {done,value} = await reader.read();
        if (value) { received += value.byteLength; buffer += decoder.decode(value, {stream:true}); }
        if (received > 65536) throw new Error("Protocol response exceeded the browser check limit.");
        buffer = buffer.replaceAll("\r\n", "\n");
        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
          const data = frame.split("\n").filter(line => line.startsWith("data:")).map(line => line.slice(5).trimStart()).join("\n");
          if (!data) continue;
          if (++events > 32) throw new Error("Protocol response exceeded the browser event limit.");
          let packet; try { packet = JSON.parse(data); } catch (_) { throw new Error("Malformed protocol event. No success was recorded."); }
          if (packet?.method && packet.id === undefined) continue;
          if (packet?.id !== requestId) throw new Error("The protocol response did not match this request. No success was recorded.");
          return packet;
        }
        if (done) throw new Error("The protocol stream ended without a matching response.");
      }
    } finally { await reader.cancel().catch(() => {}); }
  }
  async function request(path, body, authenticated = true, binary = false, profile = {}) {
    if (authenticated && !token) throw new Error("Connect to this service first.");
    const epoch = generation, controller = new AbortController(); if (authenticated) pending.add(controller);
    const timer = setTimeout(() => controller.abort(), 35000);
    try {
      const response = await fetch(path, {method:body ? "POST" : "GET", credentials:"omit", redirect:"error", cache:"no-store", signal:controller.signal,
        headers:{...(authenticated ? {Authorization:"Bearer " + token} : {}), ...(body ? {"Content-Type":"application/json"} : {}), ...(profile.protocol ? {Accept:"application/json, text/event-stream", "MCP-Protocol-Version":profile.protocol} : {})}, ...(body ? {body:JSON.stringify(body)} : {})});
      if (authenticated && epoch !== generation) throw new Error("The connection changed. This response was discarded.");
      if (!response.ok) {
        let code = "request_failed"; try { code = (await response.json()).error?.code || code; } catch (_) {}
        if (response.status === 401 && authenticated) disconnect();
        throw new Error("Service refused the request: " + String(code).slice(0, 100) + ".");
      }
      if (binary) return {bytes:await response.arrayBuffer(), digest:response.headers.get("x-content-sha256"), epoch};
      if (profile.notification && response.status === 202) return null;
      const value = profile.protocol ? await protocolResponse(response, body.id) : await response.json();
      if (authenticated && epoch !== generation) throw new Error("The connection changed. This response was discarded.");
      if (profile.protocol && (value.jsonrpc !== "2.0" || value.id !== body.id || value.error || !value.result)) throw new Error("The protocol response did not match this request. No success was recorded.");
      if (profile.raw) return value;
      return value.result;
    } finally { clearTimeout(timer); pending.delete(controller); }
  }
  function facts(target, entries) { target.replaceChildren(); for (const [name, value] of entries) target.append(element("dt", name), element("dd", value ?? "Unknown")); }
  clientAccess = window.BaltorClientAccess.create({request, element, message,
    current:() => ({connected:!!token, mode:authenticationMode, generation,
      available:capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website.client_access_available === true})});
  // Browsing the permitted catalogue lives in its own file. It is given the same authenticated request
  // boundary and reads the connection state rather than keeping its own copy of the token.
  catalogueBrowser = window.BaltorCatalogueBrowser
    ? window.BaltorCatalogueBrowser.create({request, element, message,
        current:() => ({connected:!!token, generation, scopes:principalScopes})})
    : null;
  if (!catalogueBrowser) message("browse-message", "Browsing is not available on this page. Search above still works.", true);
  async function connectService(supplied, activate = false) {
    disconnect(); token = supplied; message("connection-message", "Checking access…");
    try {
      if (activate) await request("/api/v1/account/activate", {record_type:"service_account_activation_request/v1"});
      const value = await request("/api/v1/session");
      authenticationMode = value.authentication_mode;
      const entries = [["Tenant", value.principal.tenant_id], ["Namespace", value.principal.namespace], ["Scopes", value.principal.scopes.join(", ")], ["Access", value.principal.entitlement]];
      facts($("identity-facts"), entries); facts($("account-facts"), entries);
      $("account-state").textContent = "Connected"; $("account-note").textContent = "This connection is scoped to the identity below. Access and subscriptions are checked by the service.";
      $("workspace-access").textContent = value.principal.tenant_id; $("workspace-access-note").textContent = "Connected. Search returns only material permitted for this identity.";
      $("workspace-access-link").textContent = "Manage this connection"; $("account-access-link").textContent = "Disconnect or change account";
      $("identity").hidden = false; $("connect-form").hidden = true; $("connection-state").textContent = "Connected";
      ["query", "search-button", "search-mode", "refresh-usage", "refresh-billing"].forEach(id => { $(id).disabled = false; });
      $("result-count").textContent = "Ready"; message("connection-message", "Access confirmed for this tenant.");
      const administrator = value.principal.scopes.includes("access:manage");
      principalScopes = value.principal.scopes;
      $("test-protocol").disabled = authenticationMode === "browser_identity" || !value.principal.scopes.includes("provisioning:metadata") || !capabilities;
      $("setup-identity").textContent = "Connected as " + value.principal.tenant_id + ". Client setup uses a separate local copy of your service token.";
      $("admin-nav").hidden = !administrator; $("refresh-access").disabled = !administrator;
      const destination = afterLogin; afterLogin = null; navigate(destination || (administrator ? "/admin" : "/app"));
      if (administrator) await loadAccess();
      clientAccess.connectionChanged(); catalogueBrowser?.connectionChanged();
    } catch (error) { disconnect(); message("connection-message", error.name === "AbortError" ? "Connection timed out. No automatic retry was made." : error.message, true); }
  }
  $("connect-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy) return; busy = true; $("connect-button").disabled = true;
    try { await connectService($("access-token").value.trim()); }
    finally { busy = false; $("connect-button").disabled = false; }
  });
  $("email-login-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy || !identityClient) return;
    busy = true; const epoch = generation; $("email-login-button").disabled = true;
    const email = $("login-email").value.trim(), password = $("login-password").value; $("login-password").value = "";
    message("identity-message", "Checking your identity…");
    try {
      const result = await identityClient.auth.signInWithPassword({email,password});
      if (epoch !== generation) return;
      if (result.error || !result.data.session) throw new Error("Sign-in failed. Check your password and confirm your email. No account access was granted.");
      await connectService(result.data.session.access_token, identityConfiguration.registration_enabled);
      if (token) message("identity-message", "Signed in. Your account permissions come from the service.");
      else message("identity-message", "The identity provider accepted the login, but the service refused account access. Check the connection message below.", true);
    } catch (error) { message("identity-message", error.message, true); }
    finally { busy = false; $("email-login-button").disabled = false; }
  });
  // The waiting list is offered only where the service says it keeps one, and
  // the discount is named only where checkout says it takes a code. Until the
  // service answers, neither is offered: an unanswered page must not make an
  // offer that ends in a refusal.
  const waitlistOffer = value => {
    // Read only from the record version this page was written against, like
    // every other public statement: another version offers nothing.
    const open = value?.record_type === CAPABILITIES_RECORD_TYPE && value.website?.waitlist_available === true;
    for (const name of ["waitlist-link", "signup-waitlist-link", "waitlist-form"]) $(name).hidden = !open;
    $("waitlist-closed").hidden = open;
    // The sign-up page says the form is still being built only while no list is offered.
    $("waiting-list-pending").hidden = open;
    // So does the pricing page's list of unfinished work: it names the form only while no list is offered.
    $("in-progress-waitlist").hidden = open;
    $("waitlist-state").textContent = open ? "Open for requests" : "Not taking requests";
    $("waitlist-discount").hidden = !open || value?.billing?.discount_code !== true;
  };
  $("waitlist-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy) return; busy = true; $("waitlist-button").disabled = true;
    const email = $("waitlist-email").value.trim(), note = $("waitlist-note").value.trim();
    // Answers the service can give this form. Anything else is reported as it
    // arrived, without guessing that the request was recorded.
    const answers = {waitlist_address_invalid:"That does not look like an email address we can write to. Check it and try again.",
      waitlist_address_already_listed:"This address is already on the list. One request is enough, and a person will read it.",
      waitlist_address_has_account:"This address already has an account. Use sign-in instead.",
      waitlist_source_flooded:"Too many requests have come from this connection. Please try again later.",
      waitlist_unavailable:"This service is not taking requests right now. Nothing was recorded.",
      failed_attempt_limit_reached:"Too many refused attempts from this connection. Please try again later."};
    message("waitlist-message", "Sending your request…");
    try {
      const response = await fetch("/api/v1/waitlist", {method:"POST",credentials:"omit",redirect:"error",cache:"no-store",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({record_type:"service_waitlist_request/v1",email,note})});
      const value = await response.json();
      if (!response.ok) throw new Error(answers[value?.error?.code] || "Your request was not recorded. Please try again.");
      if (value.result?.state !== "waiting") throw new Error("Your request was not recorded. Please try again.");
      $("waitlist-form").hidden = true; $("waitlist-state").textContent = "Request received";
      message("waitlist-message", "Thank you. Your request is on the list and a person will read it. We do not promise a date, and we will only write to you about this.");
    } catch (error) { message("waitlist-message", error.message, true); }
    finally { busy = false; $("waitlist-button").disabled = false; }
  });
  $("email-signup-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy || !identityClient || !identityConfiguration.email_signup_enabled) return;
    busy = true; $("email-signup-button").disabled = true;
    const email = $("signup-email").value.trim(), password = $("signup-password").value; $("signup-password").value = "";
    message("signup-message", "Requesting account confirmation…");
    try {
      const result = await identityClient.auth.signUp({email,password,options:{emailRedirectTo:identityConfiguration.redirect_url}});
      if (result.error) throw new Error("Account confirmation could not be requested. Check the address and password requirements, or try again later.");
      message("signup-message", "Check your email for the confirmation link, then return here to sign in. If this address already has an account, use sign-in. This page has not granted access or started a subscription.");
    } catch (error) { message("signup-message", error.message, true); }
    finally { busy = false; $("email-signup-button").disabled = false; }
  });
  async function download(hit, button, status) {
    const identity = JSON.stringify(hit.reference), epoch = generation;
    if (!downloads.has(identity)) downloads.set(identity, crypto.randomUUID());
    button.disabled = true; status.textContent = "Fetching the selected revision…";
    try {
      const result = await request("/api/v1/download", {record_type:"service_provisioning_request/v1", operation:"read", identity:hit.reference.identity,
        expected_digest:hit.reference.body_digest, request_id:downloads.get(identity)}, true, true);
      const actual = [...new Uint8Array(await crypto.subtle.digest("SHA-256", result.bytes))].map(n => n.toString(16).padStart(2, "0")).join("");
      if (actual !== hit.reference.body_digest || actual !== result.digest) throw new Error("Downloaded bytes do not match the selected reference. Nothing was saved.");
      if (epoch !== generation || result.epoch !== generation) return;
      const objectUrl = URL.createObjectURL(new Blob([result.bytes], {type:"application/octet-stream"}));
      const link = element("a", "Download"); link.href = objectUrl; link.download = "intelligence-" + actual.slice(0, 12) + ".txt"; link.click(); setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      status.textContent = "Downloaded. Digest verified. Native loading and task acceptance are separate checks.";
    } catch (error) { status.textContent = error.name === "AbortError" ? "The wait ended. Usage may have been recorded. Retry this exact selection to reconcile." : error.message; }
    finally { button.disabled = false; }
  }
  function renderResults(hits) {
    $("results").replaceChildren(); $("result-count").textContent = hits.length + " references";
    if (!hits.length) { $("results").append(element("p", "No permitted matches. Try a different description or ask your operator about access.", "empty")); return; }
    for (const hit of hits) {
      const card = element("article", "", "result"); card.append(element("h3", hit.purpose), element("p", hit.reference.identity), element("span", hit.kind, "badge"));
      const detail = document.createElement("details"), list = document.createElement("dl");
      detail.append(element("summary", "Source, integrity and access"));
      facts(list, [["Source", hit.reference.source_ref], ["Digest", hit.reference.body_digest], ["License", hit.license || "Unknown"], ["Declared effects", (hit.declared_effects || []).join(", ") || "None declared"], ["Harness scope", (hit.harness_styles || []).join(", ") || "No specific harness declared"], ["Qualification basis", hit.qualification_basis], ["Bytes", hit.size_bytes], ["Body access", hit.body_allowed ? "Permitted, checked again on fetch" : "Not granted"]]); detail.append(list); card.append(detail);
      const button = element("button", "Fetch exact revision", "quiet"), status = element("p", "", "caption"); button.type = "button"; button.disabled = !hit.body_allowed; status.setAttribute("role", "status");
      button.addEventListener("click", () => download(hit, button, status)); card.append(button, status); $("results").append(card);
    }
  }
  $("search-form").addEventListener("submit", async event => {
    event.preventDefault(); $("search-button").disabled = true; message("search-message", "Searching authorized references…");
    try { const value = await request("/api/v1/retrieval", {record_type:"service_retrieval_request/v1", query:$("query").value, mode:$("search-mode").value, top_n:10}); renderResults(value.hits); message("search-message", "References only. No bodies loaded."); }
    catch (error) { message("search-message", error.name === "AbortError" ? "Search timed out. You can retry." : error.message, true); }
    finally { $("search-button").disabled = !token; }
  });
  $("refresh-usage").addEventListener("click", async () => {
    try { $("usage").textContent = JSON.stringify(await request("/api/v1/usage"), null, 2); }
    catch (error) { $("usage").textContent = error.message; }
  });
  async function createSession(operation, options, plan, button) {
    const key = JSON.stringify([operation, options.policy_digest, plan]), epoch = generation;
    if (!billingRequests.has(key)) billingRequests.set(key, crypto.randomUUID());
    button.disabled = true; message("billing-message", "Requesting a hosted session…");
    try {
      const result = await request("/api/v1/billing/" + operation, {record_type:"billing_session_request/v1", request_id:billingRequests.get(key), policy_digest:options.policy_digest, ...(plan ? {plan_ref:plan} : {})});
      if (epoch !== generation) return;
      const url = new URL(result.redirect_url); if (url.protocol !== "https:" || !["checkout.stripe.com", "billing.stripe.com"].includes(url.hostname) || url.username || url.password) throw new Error("The service returned an unsupported payment destination.");
      const link = element("a", "Open secure " + operation); link.href = url.href; link.rel = "noopener noreferrer"; link.target = "_blank"; $("billing-message").replaceChildren(link);
    } catch (error) { message("billing-message", error.name === "AbortError" ? "The outcome is uncertain. Check the provider before trying again. This page retains the same request identity." : error.message, true); }
    finally { button.disabled = !token; }
  }
  $("refresh-billing").addEventListener("click", async () => {
    try {
      const options = await request("/api/v1/billing/plans"); $("billing").replaceChildren();
      if (!options.checkout_available && !options.portal_available) { $("billing").textContent = "Billing is unavailable: " + (options.unavailable_reason || "not configured") + "."; return; }
      if (options.checkout_available) for (const plan of options.plans) { const button = element("button", "Choose " + plan.label, "quiet"); button.type = "button"; button.addEventListener("click", () => createSession("checkout", options, plan.plan_ref, button)); $("billing").append(button); }
      if (options.portal_available) { const button = element("button", "Manage subscription", "quiet"); button.type = "button"; button.addEventListener("click", () => createSession("portal", options, "", button)); $("billing").append(button); }
    } catch (error) { message("billing-message", error.message, true); }
  });
  async function loadAccess() {
    const options = await request("/api/v1/admin/access"); accessOptions = options;
    $("admin-controls").hidden = false; $("admin-login").hidden = true;
    $("token-quota").textContent = options.active_tokens + " / " + options.maximum_active_tokens + " active";
    const selected = $("token-tenant").value; $("token-tenant").replaceChildren();
    for (const tenant of options.target_tenants) { const choice = element("option", tenant); choice.value = tenant; $("token-tenant").append(choice); }
    if (options.target_tenants.includes(selected)) $("token-tenant").value = selected;
    const previous = new Set([...document.querySelectorAll("#token-scopes input:checked")].map(input => input.value));
    $("token-scopes").replaceChildren(element("legend", "Allowed operations"));
    for (const scope of options.allowed_scopes) { const label = element("label", "", "scope-choice"), input = document.createElement("input"); input.type = "checkbox"; input.value = scope; input.checked = previous.size ? previous.has(scope) : true; label.append(input, document.createTextNode(scope)); $("token-scopes").append(label); }
    $("token-hours").max = Math.floor(options.maximum_lifetime_seconds / 3600);
    if (!$("token-hours").value) $("token-hours").value = options.default_lifetime_seconds / 3600;
    $("issue-access-button").disabled = !options.writes_authorized || options.active_tokens >= options.maximum_active_tokens;
    $("access-list").replaceChildren();
    if (!options.tokens.length) $("access-list").append(element("p", "No test tokens have been created yet.", "empty"));
    for (const row of options.tokens) {
      const item = element("article", "", "result"); item.append(element("h3", row.label), element("span", row.state, "badge"));
      item.append(element("p", row.tenant_id + " · " + row.scopes.join(", ")), element("p", "Expires " + new Date(row.expires_at * 1000).toLocaleString()));
      item.append(element("p", "Token identity: " + row.key_id, "caption"));
      if (row.state === "active" && options.writes_authorized) { const button = element("button", "Revoke " + row.label, "quiet"); button.type = "button";
        button.addEventListener("click", async () => {
          if (accessBusy || !confirm("Revoke the token “" + row.label + "”? Its next service request will be refused.")) return;
          accessBusy = true; button.disabled = true;
          try { await request("/api/v1/admin/access", {record_type:"service_access_request/v1", operation:"revoke", request_id:crypto.randomUUID(), tenant_id:row.tenant_id, key_id:row.key_id}); await loadAccess(); message("admin-message", "Token revoked."); }
          catch (error) { message("admin-message", error.message + " Refresh to inspect the current state before retrying.", true); }
          finally { accessBusy = false; button.disabled = false; }
        }); item.append(button); }
      $("access-list").append(item);
    }
    message("admin-message", "Administrator access confirmed. Test tokens cannot delegate administration or billing management.");
  }
  $("refresh-access").addEventListener("click", () => loadAccess().catch(error => message("admin-message", error.message, true)));
  $("issue-access").addEventListener("submit", async event => {
    event.preventDefault(); if (accessBusy || !accessOptions) return;
    const fields = {record_type:"service_access_request/v1", operation:"issue", tenant_id:$("token-tenant").value, label:$("token-label").value.trim(),
      scopes:[...document.querySelectorAll("#token-scopes input:checked")].map(input => input.value), lifetime_seconds:Number($("token-hours").value)*3600};
    if (!fields.scopes.length) { message("admin-message", "Choose at least one allowed operation.", true); return; }
    const signature = JSON.stringify(fields);
    if (!accessRequest || accessRequest.signature !== signature) accessRequest = {signature, id:crypto.randomUUID()};
    accessBusy = true; $("issue-access-button").disabled = true; $("issued-token").value = ""; $("issued-access").hidden = true;
    try {
      const result = await request("/api/v1/admin/access", {...fields, request_id:accessRequest.id});
      await loadAccess();
      if (result.token) { $("issued-token").value = result.token; $("issued-access").hidden = false; message("admin-message", "Token created. Save it before closing or reloading this page."); }
      else message("admin-message", "This request already created a token. The secret cannot be shown again. Revoke that token before creating a replacement.");
      accessRequest = null;
    } catch (error) { message("admin-message", error.message + " No automatic retry was made. Refresh the list; an exact retry reuses this request identity.", true); }
    finally { accessBusy = false; $("issue-access-button").disabled = !token || !accessOptions?.writes_authorized || accessOptions.active_tokens >= accessOptions.maximum_active_tokens; }
  });
  $("copy-token").addEventListener("click", async () => { try { await navigator.clipboard.writeText($("issued-token").value); message("admin-message", "Token copied. Store it privately."); } catch (_) { $("issued-token").type = "text"; $("issued-token").select(); message("admin-message", "Copy the selected token, then clear it from this page."); } });
  $("clear-token").addEventListener("click", () => { $("issued-token").value = ""; $("issued-token").type = "password"; $("issued-access").hidden = true; });
  $("copy-endpoint").addEventListener("click", async () => { try { await navigator.clipboard.writeText($("protocol-url").value); $("copy-endpoint").textContent = "Endpoint copied"; } catch (_) { $("protocol-url").select(); $("copy-endpoint").textContent = "Select and copy the endpoint"; } });
  $("protocol-url").value = location.origin + "/mcp";
  $("setup-endpoint").textContent = location.origin + "/mcp";
  // A connection recipe is reviewed data that a person copies into a client. It may name the environment
  // variable that holds the service token. It may never carry a token, and the only address it may use is
  // the origin that served this page. A record that breaks a rule is refused as a whole and nothing from it is shown.
  // The rules list the few forms that a configuration text may take and refuse every other text. A new way to
  // write a key or an address is therefore refused without a rule of its own.
  // The limit of these rules is one plain word under an ordinary name. The page cannot tell a setting word from a short
  // secret, from a host name without dots or from the name of a program. The review of the record decides that.
  const recipeRecordType = "website_client_recipes/v2", endpointPlaceholder = "{{ENDPOINT}}";
  const recipeTextFields = ["id", "name", "configuration_location", "configuration_note", "verification_command", "verification_note", "version_note", "removal_note", "source_url"];
  const isTable = value => value !== null && typeof value === "object" && !Array.isArray(value);
  // Every field name and every single value in a record, each with the field names that lead to it.
  const recipeStrings = (value, path = [], found = []) => {
    if (value !== null && typeof value === "object") for (const [name, item] of Object.entries(value)) {
      if (!Array.isArray(value)) found.push({path:[...path, name], key:name, text:name, named:true, string:true});
      recipeStrings(item, Array.isArray(value) ? path : [...path, name], found);
    } else found.push({path, key:path[path.length - 1] ?? "", text:String(value), named:false, string:typeof value === "string"});
    return found;
  };
  // Key-shaped text. Keys are written in one of two alphabets. In the alphabet that is safe inside an address: a long unbroken run, or a shorter run
  // that mixes letters and digits. In the standard base64 alphabet: such a mixed run that also holds a plus sign or padding. A run that only slashes
  // join is not reported, because a record type such as name/v2 and the path of an address are not keys.
  const mixedRun = run => /[0-9]/.test(run) && /[A-Za-z]/.test(run);
  const tokenShaped = text => /[A-Za-z0-9_-]{32,}/.test(text) || (text.match(/[A-Za-z0-9_-]{20,}/g) || []).some(mixedRun)
    || (text.match(/[A-Za-z0-9+\/=]{20,}/g) || []).some(run => /[+=]/.test(run) && mixedRun(run));
  // A configuration holds tables and single settings only. A list is refused, because a list can carry the arguments of a command as plain words.
  const settingsOnly = value => isTable(value) ? Object.values(value).every(settingsOnly) : typeof value === "string" || typeof value === "boolean" || Number.isFinite(value);
  const plainHttps = text => { try { const url = new URL(text); return text.startsWith("https://") && !url.username && !url.password; } catch (_) { return false; } };
  // Two addresses sit on the same host. An address that cannot be read has no host, so it is never the same host as another one.
  const sameHost = (left, right) => { try { const host = new URL(left).host; return host !== "" && host === new URL(String(right)).host; } catch (_) { return false; } };
  const settingName = /^\$?[A-Za-z][A-Za-z0-9_-]*$/, settingWord = /^[A-Za-z][A-Za-z0-9_-]*$/, credentialTable = /^(?:.*headers|env|environment)$/i;
  // A name holds a credential when one of its words says so. A capital letter, a hyphen or an underscore divides the words of a name, so oauth and timeout are not such names.
  const credentialWords = ["authorization", "auth", "bearer", "token", "secret", "password", "passphrase", "credential", "credentials", "key", "apikey"];
  const namesCredential = name => name.replace(/([a-z0-9])([A-Z])/g, "$1 $2").toLowerCase().split(/[^a-z0-9]+/).some(word => credentialWords.includes(word));
  // The command that a person is told to run is plain words and options: no address, path, pipe, assignment or quotation.
  const plainCommand = /^[A-Za-z][A-Za-z0-9-]*(?: -{0,2}[A-Za-z][A-Za-z0-9-]*)*$/;
  // The table that holds the address. Every table above it holds exactly one table, so a configuration names exactly one server entry.
  const serverEntry = table => { while (!Object.keys(table).includes("url")) { const inner = Object.values(table).filter(isTable); if (inner.length !== 1) return null; table = inner[0]; } return table; };
  function recipeRefusal(record) {
    const variable = record?.credential_variable;
    if (record?.record_type !== recipeRecordType || typeof variable !== "string" || !/^[A-Z][A-Z0-9_]{2,63}$/.test(variable) || typeof record.revocation_note !== "string" || !record.revocation_note
      || !Array.isArray(record.recipes) || !record.recipes.length || new Set(record.recipes.map(recipe => recipe?.id)).size !== record.recipes.length) return "unsupported_record";
    // This file is public. No text anywhere in it is shaped like a key: not a value, not a field name and not the variable name, in a field that is displayed or in one that is not.
    if (tokenShaped(variable) || recipeStrings(record).some(item => tokenShaped(item.text.replaceAll(variable, "")))) return "credential_rule";
    const references = [variable, "Bearer {env:" + variable + "}", "Bearer ${" + variable + "}"];
    // A credential position holds a declared reference to the variable and nothing else. Such a position is every value inside a table of headers or of
    // environment values, every value under a name that holds a credential, and every text that mentions the variable or a bearer value.
    const credentialPosition = item => item.path.some(name => credentialTable.test(name)) || item.path.some(namesCredential) || item.text.includes(variable) || /\bbearer\b/i.test(item.text);
    for (const recipe of record.recipes) {
      if (!recipe || recipeTextFields.some(field => typeof recipe[field] !== "string" || !recipe[field]) || !["toml", "json"].includes(recipe.format) || !plainHttps(recipe.source_url)
        || !plainCommand.test(recipe.verification_command) || !isTable(recipe.configuration) || !settingsOnly(recipe.configuration)) return "unsupported_record";
      const found = recipeStrings(recipe.configuration), values = found.filter(item => !item.named);
      if (found.some(item => item.named && !settingName.test(item.text))) return "unsupported_record";
      const credentialProblem = !values.some(item => item.text.includes(variable))
        || values.some(item => credentialPosition(item) && !(item.string && references.includes(item.text)));
      if (credentialProblem) return "credential_rule";
      // The address is the placeholder. It is held once, under the url name of the single server entry, and the page fills it with its own origin.
      // Inside that entry the only tables are tables of headers or of environment values. Every other text is a plain setting word or the one
      // top-level https $schema value, so no other text can carry an address, a path, an option or a command line. That $schema value must sit on
      // the host of the source address this recipe cites, so the page cannot send a reader's editor to a host nobody reviewed. This is the rule the
      // release check applies to the reviewed record, so the page and the release check agree. A vendor that serves its schema from another host
      // needs a review decision, recorded by changing the record or this rule, not a silent exception.
      const entry = serverEntry(recipe.configuration);
      const addressProblem = !entry || entry.url !== endpointPlaceholder
        || Object.entries(entry).some(([name, item]) => isTable(item) && !credentialTable.test(name))
        || values.filter(item => item.key === "url" || item.text.includes("{{")).length !== 1
        || values.some(item => item.string && !credentialPosition(item) && item.text !== endpointPlaceholder && !settingWord.test(item.text) && !(item.path.length === 1 && item.key === "$schema" && plainHttps(item.text) && sameHost(item.text, recipe.source_url)));
      if (addressProblem) return "address_rule";
    }
    return "";
  }
  const tomlKey = key => /^[A-Za-z0-9_-]+$/.test(key) ? key : JSON.stringify(key);
  const tomlText = (table, path = []) => {
    const entries = Object.entries(table);
    const own = entries.filter(([, item]) => !isTable(item)).map(([key, item]) => tomlKey(key) + " = " + JSON.stringify(item));
    const blocks = own.length ? [(path.length ? "[" + path.map(tomlKey).join(".") + "]\n" : "") + own.join("\n")] : [];
    return blocks.concat(entries.filter(([, item]) => isTable(item)).map(([key, item]) => tomlText(item, [...path, key]))).join("\n\n");
  };
  function renderRecipe() {
    const selected = recipes?.recipes.find(item => item.id === $("client-choice").value);
    if (!selected) return;
    const endpoint = location.origin + "/mcp";
    const fill = value => value === endpointPlaceholder ? endpoint : Array.isArray(value) ? value.map(fill) : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).map(([key, item]) => [key, fill(item)])) : value;
    const configuration = fill(selected.configuration);
    $("client-configuration").textContent = selected.format === "toml" ? tomlText(configuration) : JSON.stringify(configuration, null, 2);
    $("configuration-location").textContent = selected.configuration_location; $("client-configuration-note").textContent = selected.configuration_note;
    $("client-verify-command").textContent = selected.verification_command; $("client-verify-note").textContent = selected.verification_note;
    $("client-version-note").textContent = selected.version_note;
    $("client-revoke-note").textContent = recipes.revocation_note; $("client-removal-note").textContent = selected.removal_note;
    $("client-source").href = selected.source_url; $("client-source").textContent = selected.source_url;
    $("copy-configuration").disabled = false; $("copy-configuration").textContent = "Copy configuration without secrets"; message("setup-message", "");
  }
  $("client-choice").addEventListener("change", renderRecipe);
  $("copy-configuration").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("client-configuration").textContent); $("copy-configuration").textContent = "Configuration copied"; }
    catch (_) { message("setup-message", "Clipboard unavailable. Select and copy the configuration text."); }
  });
  request("/assets/client-recipes.json", null, false, false, {raw:true}).then(value => {
    const refusal = recipeRefusal(value);
    if (refusal) throw Object.assign(new Error("Connection recipes refused"), {refusal});
    recipes = value; $("client-choice").replaceChildren();
    for (const recipe of value.recipes) { const option = element("option", recipe.name); option.value = recipe.id; $("client-choice").append(option); }
    $("client-choice").disabled = false; renderRecipe();
  }).catch(error => {
    recipes = null; $("setup-message").dataset.refusal = error.refusal || "unavailable";
    $("client-choice").replaceChildren(element("option", "Recipes unavailable")); $("client-choice").disabled = true; $("copy-configuration").disabled = true;
    $("client-configuration").textContent = "No configuration is shown."; $("client-version-note").textContent = "";
    message("setup-message", error.refusal ? "The connection recipes did not pass their safety check, so none is shown. Use the setup guide; do not guess a configuration." : "Client recipes could not be loaded. Use the setup guide; do not guess a configuration.", true);
  });
  $("test-protocol").addEventListener("click", async () => {
    if (connectionBusy || !token || !capabilities) return;
    connectionBusy = true; const epoch = generation, version = (capabilities.protocol.handshake_versions || [])[0];
    $("test-protocol").disabled = true; $("protocol-tools").replaceChildren(); message("protocol-result", "Checking the protocol handshake and available tools…");
    try {
      if (!version) throw new Error("This service offers no handshake protocol version, so this browser check cannot run.");
      const profile = {protocol:version};
      const initialized = await request("/mcp", {jsonrpc:"2.0", id:crypto.randomUUID(), method:"initialize", params:{protocolVersion:version, capabilities:{}, clientInfo:{name:"baltor-browser-check",version:"1.0.0"}}}, true, false, profile);
      if (initialized.protocolVersion !== version) throw new Error("The returned protocol version is not the selected service version.");
      await request("/mcp", {jsonrpc:"2.0",method:"notifications/initialized"}, true, false, {...profile,notification:true});
      const listed = await request("/mcp", {jsonrpc:"2.0",id:crypto.randomUUID(),method:"tools/list",params:{}}, true, false, profile);
      if (!Array.isArray(listed.tools) || !listed.tools.length || listed.tools.some(tool => typeof tool.name !== "string")) throw new Error("The service did not return a usable tool list.");
      if (epoch !== generation) return;
      for (const tool of listed.tools) $("protocol-tools").append(element("li", tool.name));
      message("protocol-result", "Service connection passed. Protocol " + version + "; " + listed.tools.length + " tools available. No file bodies fetched or models called. Native client loading is not tested here.");
    } catch (error) { if (epoch === generation) message("protocol-result", error.name === "AbortError" ? "The check timed out. No automatic retry was made." : error.message, true); }
    finally { connectionBusy = false; if (epoch === generation) $("test-protocol").disabled = !token || !principalScopes.includes("provisioning:metadata"); }
  });
  $("try-example").addEventListener("click", () => { navigate("/app"); $("query").value = "review inputs"; message("search-message", token ? "Example query prepared. Select Search to retrieve permitted references." : "Sign in first. This button does not submit a query or download a file."); });
  request("/api/v1/capabilities", null, false).then(value => {
    capabilities = value; $("service-status").textContent = "Service available";
    clientAccess.connectionChanged();
    waitlistOffer(value);
    $("protocol-note").textContent = "Supported protocol: " + value.protocol.versions.join(", ") + ". External identity flow qualified: " + (value.protocol.external_authorization_flow_qualified ? "yes" : "no") + ".";
    $("retrieval-note").textContent = "Installed vector method: " + value.retrieval.vector_backend + ". Semantic embedding model installed: " + (value.retrieval.semantic_embedding_model_installed ? "yes" : "no") + ". Bodies load only after selection.";
    $("setup-protocol").textContent = value.protocol.versions.join(", ");
    $("test-protocol").disabled = !token || authenticationMode === "browser_identity" || !principalScopes.includes("provisioning:metadata") || connectionBusy;
    /* Public statements are read last and only from the record version this page was written against. An unexpected version keeps the careful state. */
    if (value.record_type === CAPABILITIES_RECORD_TYPE) {
      applyAccessState(value.website.registration_available === true);
      applyPaymentState(value.billing.checkout === true);
      applyClientAccessState(value.website.client_access_available === true);
      if (value.website.browser_identity_available) openBrowserIdentity();
    }
    function openBrowserIdentity() {
      request("/api/v1/account/identity", null, false).then(settings => {
        if (settings.record_type !== "browser_identity_public_configuration/v1" || settings.provider_profile !== "supabase_user/v1" || !settings.publishable_key.startsWith("sb_publishable_") || !window.BaltorIdentitySdk) throw new Error("Identity configuration unavailable");
        identityConfiguration = settings;
        identityClient = createIdentityClient(settings);
        $("email-login").hidden = false; $("email-signup").hidden = !settings.email_signup_enabled;
        $("signup-closed").hidden = settings.email_signup_enabled;
        $("login-access-description").textContent = "Sign in with your verified email account, or use a service token issued by your operator.";
        $("email-access-note").textContent = "Email credentials are checked by the configured identity provider. Model keys are separate.";
        $("email-signin-limit").textContent = settings.email_signup_enabled ? "Email sign-in is available. Account creation and subscription access are separate." : "Email sign-in is available for prepared accounts. Public account creation remains closed; a service token does not create an account or subscription.";
      }).catch(() => message("identity-message", "Email sign-in configuration is unavailable. Operator service tokens remain separate.", true));
    }
  }).catch(() => { waitlistOffer(null); $("service-status").textContent = "Service unavailable. Check the host configuration."; $("protocol-note").textContent = "Could not confirm the installed protocol. Do not assume client compatibility."; });
})();
