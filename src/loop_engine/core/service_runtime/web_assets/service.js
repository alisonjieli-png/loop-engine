"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let token = "", generation = 0, busy = false, capabilities = null, accessOptions = null, accessRequest = null, accessBusy = false;
  let connectionBusy = false, recipes = null, afterLogin = null, principalScopes = [];
  let identityClient = null, identityConfiguration = null, authenticationMode = "host_key";
  let clientAccess = null, catalogueBrowser = null;
  // What the funnel reads: whether the service reports account creation open, where a signed-in account's paid access comes
  // from, and whether this page has asked for a sign-up link.
  let registrationOpen = false, accessSource = "", funnelSent = false;
  // A signed-in staff member's role, read from the session record. The service decides every permission again.
  let staffRole = "", staffBusy = false;
  const coveredSources = ["operator_grant", "free_monthly", "founding_free_monthly"];
  const pending = new Set(), downloads = new Map(), billingRequests = new Map();
  const message = (id, text, error = false) => { $(id).textContent = text; $(id).classList.toggle("error", error); };
  const element = (tag, text, className = "") => { const item = document.createElement(tag); item.textContent = text; if (className) item.className = className; return item; };
  const show = name => {
    document.body.dataset.page = name;
    document.querySelectorAll("[data-view]").forEach(item => { item.hidden = item.dataset.view !== name; });
    // A link to a part of a page, such as the library section of the homepage, is not the page itself.
    document.querySelectorAll("[data-page]").forEach(item => { if (item.dataset.page === name && !(item.getAttribute("href") || "").includes("#")) item.setAttribute("aria-current", "page"); else item.removeAttribute("aria-current"); });
  };
  // "/setup" opens the guide, Get set up, and "/connect" stays an alias for it, so older links and emails still work.
  // "/get-started" is the sign-up, registration and payment funnel.
  // "/waitlist" is the funnel's older address, so earlier links and emails open the same journey.
  const routeNames = {"/":"home", "/app":"workspace", "/login":"login", "/signup":"signup", "/pricing":"pricing", "/account":"account", "/admin":"admin", "/docs":"docs", "/docs/getting-set-up":"setup", "/how-it-works":"about", "/setup":"setup", "/connect":"setup", "/get-started":"start", "/use-cases":"use-cases", "/overnight":"overnight", "/efficiency":"efficiency", "/learning":"learning", "/examples":"examples", "/security":"security", "/privacy":"privacy", "/terms":"terms", "/waitlist":"start", "/auth/callback":"login"};
  if (location.pathname === "/auth/callback") {
    // Confirmation tokens in a provider redirect never enter our logs, storage or links.
    history.replaceState({}, "", "/login");
    $("identity-message").textContent = "Your email link has returned to Baltor. Sign in to continue; the provider will check your confirmation status.";
  }
  // Three addresses open views of their own: the Get started funnel, the page a message link opens, and the setup guide's
  // address. They are added here rather than in the table above, so that a change to either place merges on its own.
  routeNames["/get-started"] = "start"; routeNames["/auth/confirm"] = "confirm"; routeNames["/setup"] = "setup";
  /* A link from this service's own message opens /auth/confirm?token_hash=...&type=signup or recovery. The token is read once
     into page memory and removed from the address bar and the history at once, before anything else runs, as /auth/callback
     does. It is never stored or logged, and it leaves the page only for the identity provider, when the person submits the
     password they chose. A token or a type this page cannot read is dropped, and the page says the link cannot be used. */
  const confirmTypes = ["signup", "recovery"];
  let confirmation = null;
  if (location.pathname === "/auth/confirm") {
    const query = new URLSearchParams(location.search), tokenHash = query.get("token_hash") || "", type = query.get("type") || "";
    history.replaceState({}, "", "/auth/confirm");
    const readable = /^[A-Za-z0-9_-]{1,256}$/.test(tokenHash) && confirmTypes.includes(type);
    confirmation = {tokenHash:readable ? tokenHash : "", type:readable ? type : "signup", session:null, email:""};
  }
  const serviceName = document.title.split(" | ")[0];
  // Opening a page closes the phone menu, which the page script would otherwise leave open over the new page.
  const route = () => { const name = routeNames[location.pathname] || (location.pathname.startsWith("/docs/") ? "docs" : "home"); show(name); $("menu-toggle").checked = false; document.title = serviceName + " | " + {home:"The perfect harness setup for every task", "use-cases":"Use cases", overnight:"Solve complex problems overnight", efficiency:"More efficient operation", learning:"Learning and optimization, built in", workspace:"Intelligence workspace", login:"Sign in", signup:"Account status", pricing:"Pricing", account:"Your account", admin:"Access administration", docs:"Documentation", about:"How it works", setup:"Get set up", waitlist:"Get started", examples:"Try your first retrieval", security:"Access and data boundaries", privacy:"Privacy notice", terms:"Terms of service", start:"Get started", confirm:"Choose your password"}[name]; if (name === "docs") window.BaltorDocumentation?.show(location.pathname); };
  const navigate = path => { history.pushState({}, "", path); route(); $("main").focus({preventScroll:true}); const target = location.hash ? document.getElementById(location.hash.slice(1)) : null; if (target) target.scrollIntoView(); else scrollTo(0,0); };
  document.querySelectorAll("[data-page]").forEach(link => link.addEventListener("click", event => { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return; event.preventDefault(); if (link.dataset.afterLogin && routeNames[link.dataset.afterLogin]) afterLogin = link.dataset.afterLogin; navigate(link.getAttribute("href")); }));
  addEventListener("popstate", route); route();
  addEventListener("keydown", event => { const menu = $("menu-toggle"); if (event.key === "Escape" && menu.checked) { menu.checked = false; menu.focus(); } });
  /* The public access state, the pricing state and the personal-key wording come from the service capabilities record, never from wording kept in this file.
     They are read only from this exact record version, because another version may rename a field or give it a different meaning.
     Until the service answers, if it never answers, and for any other record version, the page keeps the careful state:
     registration closed, the operator's address leading the Get started page, payment not open, personal keys described as being prepared.
     Every public access action says "Get started" and opens /get-started, the sign-up, registration and payment funnel, in every
     state: the funnel adapts, so no label switches. The owner, September 22, 2026: "get started and join the waiting list are
     redundant"; September 23: "'get started' is the sign up and registration/pay funnel", and the guide is "Get set up". The
     state shows in the note under the hero action, in the plan's tag, in the closing note and in the panel that leads the guide. */
  const CAPABILITIES_RECORD_TYPE = "service_capabilities/v1";
  const accessStates = {
    open:{label:"Get started", href:"/get-started", note:"for the whole library", tag:"One plan",
          closing:"Create your account and connect your harness in a few minutes."},
    waiting:{label:"Get started", href:"/get-started", note:"for the whole library", tag:"One plan",
             closing:"Create your account and connect your harness in a few minutes."}};
  const paymentStates = {
    open:{badge:"Available now", note:"Subscribe from your account page, and cancel any time.", teaser:"Cancel any time from your account page."},
    invitation_only:{badge:"Available now", note:"Create your account, then subscribe from your account page. Cancel any time.", teaser:"Cancel any time from your account page."},
    closed:{badge:"Baltor Pro", note:"Subscribe from your account page once your account is ready.", teaser:"Cancel any time from your account page."}};
  /* One public payment state from two reported facts. While account creation is closed the page says invitation only, whatever checkout reports,
     so it never offers the waiting list beside "Payment open". Payment is open only when account creation and checkout are both open.
     The account page keeps its own checkout and portal buttons, which follow the session options of the signed-in account. */
  const publicPaymentState = (registration, checkout) => registration !== true ? "invitation_only" : checkout === true ? "open" : "closed";
  /* Every public access action carries the same attribute and a marked label, so an action added to another page later follows
     the reported state instead of a label written into it. */
  const applyAccessState = open => {
    const state = open === true ? accessStates.open : accessStates.waiting;
    for (const action of document.querySelectorAll("[data-access-state]")) {
      action.setAttribute("href", state.href); action.dataset.accessState = open === true ? "open" : "waiting";
      action.querySelector("[data-access-label]").textContent = state.label;
    }
    $("hero-access-note").textContent = state.note; $("home-plan-access").textContent = state.tag; $("closing-note").textContent = state.closing;
  };
  /* The Get started page leads with one panel, read from the same record: account creation when registration is open, the way to
     the invitation request page when the service keeps a waiting list, and otherwise the plain way to reach the operator. The
     operator's panel is also the careful state, so the served page shows it before the service answers. */
  const startState = website => website.registration_available === true ? "register" : website.waitlist_available === true ? "invite" : "operator";
  const applyStartState = state => {
    for (const panel of document.querySelectorAll("[data-start-state]")) panel.hidden = panel.dataset.startState !== state;
    $("start-access").dataset.startAccess = state;
  };
  /* Sentences that state whether this service takes new accounts, on Security and How it works, follow the same record. Each is
     served hidden, so a page that has not heard from the service states neither. The sentences beside them state only what is
     true in both states: people sign in with their email address and password, and client tokens come from the account page. */
  const applyRegistrationState = open => {
    for (const sentence of document.querySelectorAll("[data-registration-state]")) sentence.hidden = sentence.dataset.registrationState !== (open ? "open" : "closed");
  };
  const applyPaymentState = name => {
    const state = paymentStates[name] || paymentStates.closed;
    $("pricing-state").textContent = state.badge; $("pricing-payment-state").textContent = state.note;
    $("pricing-teaser-note").textContent = state.teaser;
  };
  const clientAccessStates = {
    open:{offer:"A personal key for each device, from your account page",
          plan:"Create and revoke a key for every client you connect, from your account page."},
    closed:{offer:"A key for each client you connect, issued to your account",
            plan:"Every client you connect gets its own key, issued to your account."}};
  const applyClientAccessState = open => {
    const state = open === true ? clientAccessStates.open : clientAccessStates.closed;
    $("offer-usage-keys").textContent = state.offer; $("plan-keys-detail").textContent = state.plan;
  };
  applyAccessState(false); applyPaymentState("closed"); applyClientAccessState(false);
  const themes = ["system", "light", "dark"];
  const createIdentityClient = settings => window.BaltorIdentitySdk.createClient(settings.project_url, settings.publishable_key,
    {auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});
  /* An email sign-in lasts as long as this browser tab. Once the service has opened the account, the page keeps the identity
     provider's access token and its expiry, and nothing else, in the tab's session storage, so a reload or an address typed in
     this tab opens the same account again. Closing the tab ends it; signing out, a refused session and any other sign-in remove
     it at once. The refresh token is never kept, so a kept sign-in ends when its access token expires. A service token or a
     client token is never kept, and the identity client itself keeps nothing. A confirmation link's session is kept only after
     its new password is set and the account opened, so a reload never opens an account whose password was not replaced. Fix 5
     of the persona journeys of September 24, 2026. */
  const keptSessionKey = "baltor.identity-session";
  const keptSession = {
    read() {
      try { const value = JSON.parse(sessionStorage.getItem(keptSessionKey) || "null");
        return value && typeof value.access_token === "string" && value.access_token && Number.isFinite(value.expires_at) ? value : null; } catch (_) { return null; }
    },
    write(accessToken) {
      let expiry = NaN;
      try { expiry = JSON.parse(atob(accessToken.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).exp; } catch (_) {}
      if (!Number.isFinite(expiry)) return;
      try { sessionStorage.setItem(keptSessionKey, JSON.stringify({access_token:accessToken, expires_at:expiry})); } catch (_) {}
    },
    clear() { try { sessionStorage.removeItem(keptSessionKey); } catch (_) {} }
  };
  let theme = "light";
  $("theme").addEventListener("click", () => { theme = themes[(themes.indexOf(theme) + 1) % themes.length]; if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme; $("theme").textContent = "Appearance: " + theme; });
  /* The header follows the sign-in this page holds. Signed in, it shows the account entry and Sign out, and hides Sign in and the
     invitation action, which are for a visitor who is not signed in. The phone menu is the same navigation folded, so it follows
     too. The served page is the signed-out state; a reload in a tab that keeps an email sign-in opens it again. */
  const showSignedIn = signedIn => {
    document.querySelectorAll("[data-signed-in]").forEach(item => { item.hidden = !signedIn; });
    document.querySelectorAll("[data-signed-out]").forEach(item => { item.hidden = signedIn; });
  };
  /* The usage panel says in words what it holds until a usage record is drawn, and keeps no raw record while it does. */
  const showUsageNote = (text, error = false) => {
    $("usage-view").replaceChildren(element("p", text, error ? "usage-note error" : "usage-note"));
    $("usage-raw").hidden = true; $("usage-raw").open = false; $("usage").textContent = "";
  };
  function disconnect() {
    // A pending confirmation belongs to the identity session that verified its link.
    // Connecting another account or signing out invalidates it before any retry.
    confirmation = null; $("confirm-password").value = ""; $("confirm-password-again").value = ""; showConfirmation();
    generation++; token = ""; keptSession.clear(); principalScopes = []; authenticationMode = "host_key"; for (const controller of pending) controller.abort(); pending.clear(); downloads.clear(); billingRequests.clear();
    $("access-token").value = ""; $("identity").hidden = true; $("connect-form").hidden = false; $("connection-state").textContent = "Not connected";
    ["query", "search-button", "search-mode", "refresh-usage", "refresh-billing"].forEach(id => { $(id).disabled = true; });
    $("results").replaceChildren(element("p", "Connect to search permitted material.", "empty")); $("identity-facts").replaceChildren();
    showUsageNote("Sign in to see the downloads recorded for your account."); $("billing").textContent = "Connect to check this service's billing configuration.";
    $("result-count").textContent = "Connect to search"; $("query").value = ""; message("search-message", ""); message("billing-message", "");
    $("account-facts").replaceChildren(); $("account-state").textContent = "Not connected";
    $("account-note").textContent = "Sign in to see your service identity, usage and available subscription settings.";
    $("workspace-access").textContent = "Sign in to search"; $("workspace-access-note").textContent = "Search and downloads are scoped to your service account.";
    $("workspace-access-link").textContent = "Sign in to this service"; $("account-access-link").textContent = "Sign in";
    showSignedIn(false);
    accessOptions = null; accessRequest = null; $("admin-nav").hidden = true; $("admin-controls").hidden = true; $("admin-login").hidden = false; $("refresh-access").disabled = true;
    staffRole = ""; $("staff-admin").hidden = true; $("staff-counts").replaceChildren(); $("staff-accounts").replaceChildren(); $("account-plan").hidden = true;
    $("issued-token").value = ""; $("issued-access").hidden = true; $("access-list").replaceChildren(); $("token-label").value = "";
    message("admin-message", "Sign in with an administrator service token. Email is not required.");
    $("test-protocol").disabled = true; $("setup-identity").textContent = "Sign in with a client token to run the connection check.";
    $("protocol-tools").replaceChildren(); message("protocol-result", "Not tested. No model calls are made by this check.");
    clientAccess?.reset(); catalogueBrowser?.reset();
    accessSource = ""; renderFunnel();
  }
  /* Signing out. The page forgets the access it holds at once, then asks the service and the identity provider to end the
     session. The sign-in page's Disconnect button and the header's Sign out do the same; Sign out also opens the sign-in page,
     where the result is reported. */
  async function signOut() {
    const previousToken = token, previousMode = authenticationMode, previousClient = identityClient;
    disconnect(); const epoch = generation;
    message("connection-message", "Signed out. Access and displayed data cleared.");
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
  }
  $("disconnect").addEventListener("click", signOut);
  $("header-sign-out").addEventListener("click", () => { navigate("/login"); signOut(); });
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
    current:() => ({connected:!!token, mode:authenticationMode, generation, known:capabilities !== null,
      available:capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website.client_access_available === true})});
  // Browsing the permitted catalogue lives in its own file. It is given the same authenticated request
  // boundary and reads the connection state rather than keeping its own copy of the token.
  catalogueBrowser = window.BaltorCatalogueBrowser
    ? window.BaltorCatalogueBrowser.create({request, element, message,
        current:() => ({connected:!!token, generation, scopes:principalScopes})})
    : null;
  if (!catalogueBrowser) message("browse-message", "Browsing is not available on this page. Search above still works.", true);
  async function connectService(supplied, activate = false, {stay = false} = {}) {
    disconnect(); token = supplied; message("connection-message", "Checking access…");
    try {
      if (activate) await request("/api/v1/account/activate", {record_type:"service_account_activation_request/v1"});
      const value = await request("/api/v1/session");
      authenticationMode = value.authentication_mode;
      if (authenticationMode === "browser_identity") keptSession.write(supplied);
      accessSource = typeof value.access_source === "string" ? value.access_source : "";
      staffRole = typeof value.staff_role === "string" ? value.staff_role : "";
      $("account-plan").hidden = !coveredSources.includes(accessSource); $("account-plan").textContent = "Your account includes Baltor Pro.";
      const entries = [["Tenant", value.principal.tenant_id], ["Namespace", value.principal.namespace], ["Scopes", value.principal.scopes.join(", ")], ["Access", value.principal.entitlement]];
      facts($("identity-facts"), entries); facts($("account-facts"), entries);
      $("account-state").textContent = "Connected"; $("account-note").textContent = "This connection is scoped to the identity below. Access and subscriptions are checked by the service.";
      $("workspace-access").textContent = value.principal.tenant_id; $("workspace-access-note").textContent = "Connected. Search returns only material permitted for this identity.";
      $("workspace-access-link").textContent = "Manage this connection"; $("account-access-link").textContent = "Disconnect or change account";
      $("identity").hidden = false; $("connect-form").hidden = true; $("connection-state").textContent = "Connected";
      showSignedIn(true); showUsageNote("Select Refresh to see the downloads recorded for this account.");
      ["query", "search-button", "search-mode", "refresh-usage", "refresh-billing"].forEach(id => { $(id).disabled = false; });
      $("result-count").textContent = "Ready"; message("connection-message", "Access confirmed for this tenant.");
      const administrator = value.principal.scopes.includes("access:manage");
      principalScopes = value.principal.scopes;
      $("test-protocol").disabled = authenticationMode === "browser_identity" || !value.principal.scopes.includes("provisioning:metadata") || !capabilities;
      // An email sign-in cannot run the protocol check, which takes a client token, so the guide says where one comes from.
      $("setup-identity").textContent = authenticationMode === "browser_identity"
        ? "This check runs with a client token, not with your email sign-in. Create one on your account page, set it in your harness, then run the check command above."
        : "Connected as " + value.principal.tenant_id + ". Client setup uses a separate local copy of your service token.";
      $("admin-nav").hidden = !administrator && !staffRole; $("refresh-access").disabled = !administrator;
      renderFunnel();
      // A kept sign-in opened again by a reload stays on the page the person asked for.
      if (!stay) { const destination = afterLogin; afterLogin = null; navigate(destination || (administrator ? "/admin" : "/app")); }
      if (administrator) await loadAccess();
      if (staffRole) await loadStaff().catch(error => message("staff-message", error.message, true));
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
  // offer that ends in a refusal. The form sits in the invitation panel of the
  // Get started page, which applyStartState shows or hides as a whole.
  const waitlistOffer = value => {
    // Read only from the record version this page was written against, like
    // every other public statement: another version offers nothing.
    const open = value?.record_type === CAPABILITIES_RECORD_TYPE && value.website?.waitlist_available === true;
    for (const name of ["signup-waitlist-link", "waitlist-form"]) $(name).hidden = !open;
    $("waitlist-closed").hidden = open;
    // The sign-up page says the form is still being built only while no list is offered.
    $("waiting-list-pending").hidden = open;
    // So does the pricing page's list of unfinished work: it names the form only while no list is offered.
    $("in-progress-waitlist").hidden = open;
    $("waitlist-state").textContent = open ? "Open" : "Not available";
    $("waitlist-discount").hidden = !open || value?.billing?.discount_code !== true;
  };
  $("waitlist-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy) return; busy = true; $("waitlist-button").disabled = true;
    const email = $("waitlist-email").value.trim(), note = $("waitlist-note").value.trim();
    // Answers the service can give this form. Anything else is reported as it
    // arrived, without guessing that the request was recorded.
    const answers = {waitlist_address_invalid:"That does not look like an email address we can write to. Check it and try again.",
      waitlist_address_already_listed:"This address is already registered. Check your email for your link.",
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
      $("waitlist-form").hidden = true; $("waitlist-state").textContent = "Received";
      message("waitlist-message", "Thank you. We will email you a link to finish creating your account, and we will only write to you about this.");
    } catch (error) { message("waitlist-message", error.message, true); }
    finally { busy = false; $("waitlist-button").disabled = false; }
  });
  /* Sign-up and recovery ask this service to send a link. The page sends the address alone: no password, and no request to the
     identity provider, which hears from this page only when the person opens the link and chooses a password. The service
     answers the same way whether or not the address has an account, so the page says what either message holds. */
  const accountRequests = {signup:{record_type:"service_account_signup_request/v2", result:"service_account_signup_result/v1", status:"confirmation_sent"},
    recovery:{record_type:"service_account_recovery_request/v1", result:"service_account_recovery_result/v1", status:"recovery_sent"}};
  const accountAnswers = {invalid_email_address:"That does not look like an email address we can write to. Check it and try again.",
    failed_attempt_limit_reached:"Too many requests for this address or from this connection. Please try again later.",
    account_signup_unavailable:"Account creation is not open right now. Nothing was sent.",
    account_recovery_unavailable:"A new password cannot be sent right now. Nothing was sent.",
    deadline_exceeded:"The service ran out of time. A message may still arrive, so wait before asking again."};
  async function requestAccountLink(action, email) {
    const expected = accountRequests[action], controller = new AbortController(), timer = setTimeout(() => controller.abort(), 35000);
    try {
      const response = await fetch("/api/v1/account/" + action, {method:"POST",credentials:"omit",redirect:"error",cache:"no-store",signal:controller.signal,
        headers:{"Content-Type":"application/json"},body:JSON.stringify({record_type:expected.record_type,email})});
      let value = null; try { value = await response.json(); } catch (_) {}
      if (response.status !== 202 || value?.result?.record_type !== expected.result || value.result.status !== expected.status)
        throw new Error(accountAnswers[value?.error?.code] || "The request was not sent. Please try again later.");
    } catch (error) {
      throw error.name === "AbortError" ? new Error("The service did not answer in time. A message may still arrive, so wait before asking again.") : error;
    } finally { clearTimeout(timer); }
  }
  const signupSent = "Check your email. The message holds a link to choose your password, or says how to sign in if this address already has an account. Nothing here starts a subscription.";
  const listenForSignUp = (form, field, button, status, sent) => $(form).addEventListener("submit", async event => {
    event.preventDefault(); if (busy || !registrationOpen) return;
    busy = true; $(button).disabled = true; message(status, "Sending your link…");
    try { await requestAccountLink("signup", $(field).value.trim()); message(status, signupSent); sent(); }
    catch (error) { message(status, error.message, true); }
    finally { busy = false; $(button).disabled = false; }
  });
  listenForSignUp("email-signup-form", "signup-email", "email-signup-button", "signup-message", () => {});
  listenForSignUp("funnel-signup-form", "funnel-email", "funnel-signup-button", "funnel-signup-message", () => { funnelSent = true; renderFunnel(); });
  /* While account creation is closed, the Get started form still takes the address: the service keeps it on its request list,
     and the link to finish creating the account follows by email. One form, one set of words, in every state. */
  $("funnel-signup-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy || registrationOpen) return;
    const listed = capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website?.waitlist_available === true;
    if (!listed) return;
    busy = true; $("funnel-signup-button").disabled = true; message("funnel-signup-message", "Sending…");
    const answers = {waitlist_address_invalid:"That does not look like an email address we can write to. Check it and try again.",
      waitlist_address_already_listed:"This address is already registered. Check your email for your link.",
      waitlist_address_has_account:"This address already has an account. Sign in instead.",
      waitlist_source_flooded:"Too many requests have come from this connection. Please try again later.",
      waitlist_unavailable:"Accounts cannot be created right now. Nothing was recorded.",
      failed_attempt_limit_reached:"Too many refused attempts from this connection. Please try again later."};
    try {
      const response = await fetch("/api/v1/waitlist", {method:"POST",credentials:"omit",redirect:"error",cache:"no-store",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({record_type:"service_waitlist_request/v1",email:$("funnel-email").value.trim(),note:""})});
      const value = await response.json();
      if (!response.ok) throw new Error(answers[value?.error?.code] || "Nothing was recorded. Please try again.");
      if (value.result?.state !== "waiting") throw new Error("Nothing was recorded. Please try again.");
      message("funnel-signup-message", "Thank you. We will email you a link to finish creating your account.");
      funnelSent = true; renderFunnel();
    } catch (error) { message("funnel-signup-message", error.message, true); }
    finally { busy = false; $("funnel-signup-button").disabled = false; }
  });
  $("recovery-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy || identityConfiguration?.recovery_available !== true) return;
    busy = true; $("recovery-button").disabled = true; message("recovery-message", "Sending your link…");
    try { await requestAccountLink("recovery", $("recovery-email").value.trim()); message("recovery-message", "Check your email. The message holds a link to choose a new password, or says that this address has no account."); }
    catch (error) { message("recovery-message", error.message, true); }
    finally { busy = false; $("recovery-button").disabled = false; }
  });
  /* The page a message link opens. The person chooses a password first. On submit the page exchanges the link for a sign-in at
     the identity provider and sets that password at once, and only then opens the account. The link is used only when the
     person submits, so a mail scanner that opens it does not use it up. The service never lets a caller choose the password
     of an account it creates, and this step replaces whatever password the account held before anything else opens it. */
  const minimumPassword = () => { const value = identityConfiguration?.minimum_password_length; return Number.isInteger(value) && value >= 8 && value <= 72 ? value : 12; };
  const passwordProblem = (password, again, email) => {
    const shortest = minimumPassword();
    if ([...password].length < shortest) return "Use at least " + shortest + " characters.";
    if (new TextEncoder().encode(password).length > 72) return "Use at most 72 bytes. A shorter password is enough.";
    if (/[\u0000-\u001f\u007f]/.test(password)) return "Use letters, digits, spaces and symbols only.";
    if (email && password.trim().toLowerCase() === email.trim().toLowerCase()) return "Choose a password that is not your email address.";
    if (password !== again) return "The two passwords are not the same. Type them again.";
    return "";
  };
  /* Once the identity provider has accepted the new password, the link has done its work, so the card never again says that it
     cannot be used or that nothing was changed. While the account opens, the password card stays with the status "Password set.
     Opening your account…", however long the activation takes. Afterwards the card says that the password is set; its signed-in
     and signed-out lines follow the header, so it offers Sign in only while this page is signed out. Finding 4 of the persona
     journeys of September 24, 2026. */
  let passwordSet = "";
  function showConfirmation() {
    $("confirm-set").hidden = passwordSet !== "set";
    if (passwordSet === "opening") { $("confirm-password-step").hidden = false; $("confirm-unusable").hidden = true; $("confirm-button").disabled = true; $("confirm-loading").hidden = true; return; }
    if (passwordSet === "set") { $("confirm-password-step").hidden = true; $("confirm-unusable").hidden = true; return; }
    if (!confirmation) { $("confirm-password-step").hidden = true; $("confirm-unusable").hidden = false; return; }
    const recovery = confirmation.type === "recovery", usable = Boolean(confirmation.tokenHash || confirmation.session);
    $("confirm-heading").textContent = recovery ? "Choose a new password." : "Choose your password.";
    $("confirm-lede").textContent = recovery ? "Your old password stops working when you set this one." : "Your email address is confirmed when you set it. Then you are signed in.";
    $("confirm-step").hidden = recovery;
    $("confirm-rule").textContent = "Use at least " + minimumPassword() + " characters and a password you use nowhere else.";
    for (const id of ["confirm-password", "confirm-password-again"]) $(id).minLength = minimumPassword();
    $("confirm-new-link").setAttribute("href", recovery ? "/login" : "/signup"); $("confirm-new-link").dataset.page = recovery ? "login" : "signup";
    $("confirm-password-step").hidden = !usable; $("confirm-unusable").hidden = usable;
    // Confirm stays disabled until the sign-in settings have loaded, so a quick click is never refused.
    $("confirm-button").disabled = !identityClient; $("confirm-loading").hidden = Boolean(identityClient);
  }
  $("confirm-form").addEventListener("submit", async event => {
    event.preventDefault(); if (busy || !confirmation) return;
    const password = $("confirm-password").value, again = $("confirm-password-again").value, problem = passwordProblem(password, again, confirmation.email);
    if (problem) { message("confirm-message", problem, true); return; }
    if (!identityClient) { message("confirm-message", "This page is still loading its sign-in settings. Wait a moment, then try again. Your link was not used.", true); return; }
    const flow = confirmation, client = identityClient, epoch = generation;
    const current = () => confirmation === flow && identityClient === client && generation === epoch;
    busy = true; $("confirm-button").disabled = true; message("confirm-message", "Setting your password…");
    try {
      if (!flow.session) {
        const tokenHash = flow.tokenHash; flow.tokenHash = "";
        const verified = await client.auth.verifyOtp({token_hash:tokenHash, type:flow.type});
        if (!current()) return;
        if (verified.error || !verified.data?.session) { showConfirmation(); message("confirm-message", ""); return; }
        flow.session = verified.data.session; flow.email = verified.data.user?.email || "";
        const late = passwordProblem(password, again, flow.email);
        if (late) { message("confirm-message", late, true); return; }
      }
      if (!current()) return;
      const updated = await client.auth.updateUser({password});
      if (!current()) return;
      if (updated.error) throw new Error("The password was not accepted. Choose a longer one that you use nowhere else, then try again.");
      $("confirm-password").value = ""; $("confirm-password-again").value = "";
      const accessToken = flow.session.access_token, recovery = flow.type === "recovery"; confirmation = null;
      passwordSet = "opening"; showConfirmation(); message("confirm-message", "Password set. Opening your account…");
      afterLogin = recovery ? "/account" : "/get-started";
      await connectService(accessToken, identityConfiguration.registration_enabled);
      passwordSet = "set"; showConfirmation();
      if (token) message("confirm-message", "");
      else message("confirm-message", "The service did not open your account.", true);
    } catch (error) { if (current()) message("confirm-message", error.message, true); }
    finally { busy = false; $("confirm-button").disabled = !identityClient; }
  });
  showConfirmation();
  /* The Get started funnel. One card shows the step a visitor is on, beside the five steps, with one primary action in every
     state: account creation while the service reports it open, the invitation request while it does not, and for a
     signed-in account the subscription, or the setup guide once an invitation, a code or a subscription covers Baltor Pro.
     Where paid access comes from is read from the session record. The page never guesses it, and it offers no payment
     control unless the service reports checkout open. */
  const funnelPlans = {
    operator_grant:{title:"Your account covers Baltor Pro", text:"There is nothing to pay on this account. Search and downloads are open.", covered:true},
    free_monthly:{title:"Your account includes Baltor Pro", text:"It is free for this account each month. Search and downloads are open to this account.", covered:true},
    founding_free_monthly:{title:"Your account includes Baltor Pro", text:"As one of the first accounts, it is free each month. Search and downloads are open to this account.", covered:true},
    promotion_code:{title:"A promotion code covers Baltor Pro", text:"There is nothing to pay while the code lasts. Search and downloads are open to this account.", covered:true},
    subscription:{title:"You subscribe to Baltor Pro", text:"Manage or cancel the subscription from your account page.", covered:true},
    checkout:{title:"Subscribe to Baltor Pro", text:"$29 a month. Cancel any time from your account page.", covered:false, subscribe:true},
    unpaid:{title:"Subscribe to Baltor Pro", text:"$29 a month. Subscribe from your account page.", covered:false}};
  const funnelOrder = ["account", "confirm", "password", "plan", "setup"];
  /* The price line under the heading, the fourth step and the pricing page's free plan answer follow the plan the account holds and
     the founding offer the service reports, so no line says "subscribe for $29 a month" to an account that Baltor Pro already
     covers, and no step is marked as a subscription that never happened. The founding offer is stated to a visitor who is not signed
     in, and only while the service reports a founding place free. The served words are the default and are kept here, so a signed-out
     page shows them again. Finding 10 of the persona journeys of September 24, 2026. */
  const servedFunnel = {price:$("funnel-price").textContent, title:$("funnel-step-plan-title").textContent, note:$("funnel-step-plan-note").textContent};
  const coveredSteps = {founding_free_monthly:["Baltor Pro included", "Free each month, as one of the first accounts"],
    free_monthly:["Baltor Pro included", "Free each month for this account"], operator_grant:["Baltor Pro included", "Covered for this account"],
    promotion_code:["Baltor Pro included", "Covered by a promotion code"], subscription:["Subscribed to Baltor Pro", "Manage or cancel it from your account page"]};
  function renderFunnel() {
    const signedIn = Boolean(token), checkout = capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.billing?.checkout === true;
    const waitingList = capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website?.waitlist_available === true;
    const foundingOpen = !signedIn && capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website?.founding_offer_open === true;
    const plan = signedIn ? funnelPlans[accessSource] || (checkout ? funnelPlans.checkout : funnelPlans.unpaid) : null;
    const coveredStep = plan?.covered ? coveredSteps[accessSource] : null;
    $("funnel-price").textContent = coveredStep ? plan.title + ". Connect your harness to start."
      : foundingOpen ? "Create your account and connect your harness. Baltor Pro is $29 a month, and while founding places last a new account gets it free each month." : servedFunnel.price;
    $("funnel-step-plan-title").textContent = coveredStep ? coveredStep[0] : servedFunnel.title;
    $("funnel-step-plan-note").textContent = coveredStep ? coveredStep[1] : foundingOpen ? "$29 a month, or free each month while founding places last" : servedFunnel.note;
    for (const sentence of document.querySelectorAll("[data-founding-offer]")) sentence.hidden = !foundingOpen;
    for (const sentence of document.querySelectorAll("[data-plan-note]")) sentence.hidden = !signedIn || sentence.dataset.planNote !== accessSource;
    const state = signedIn ? "plan" : (registrationOpen || waitingList) ? "register" : "invite", creating = signedIn || registrationOpen || waitingList;
    $("funnel").dataset.funnelState = state;
    for (const panel of document.querySelectorAll("[data-funnel-panel]")) panel.hidden = panel.dataset.funnelPanel !== state;
    $("funnel-signin").hidden = signedIn || (!registrationOpen && !waitingList);
    $("funnel-account-title").textContent = creating ? "Create your account" : "Sign in";
    $("funnel-account-note").textContent = creating ? "Your email address, nothing else" : "Use an existing account";
    $("funnel-invite-title").textContent = "Sign in to your account";
    $("funnel-invite-note").textContent = "Sign in with the account you already have.";
    $("funnel-invite").href = "/login";
    $("funnel-invite").dataset.page = "login";
    $("funnel-invite").textContent = "Sign in";
    if (plan) {
      $("funnel-plan-title").textContent = plan.title; $("funnel-plan-text").textContent = plan.text;
      $("funnel-plan-step").textContent = plan.covered ? "Step 5 of 5" : "Step 4 of 5";
      $("funnel-subscribe").hidden = !plan.subscribe; $("funnel-setup-action").className = plan.subscribe ? "button quiet" : "button primary";
    }
    const here = funnelOrder.indexOf(signedIn ? (plan.covered ? "setup" : "plan") : funnelSent ? "confirm" : "account");
    for (const item of document.querySelectorAll("[data-funnel-step]")) {
      const place = funnelOrder.indexOf(item.dataset.funnelStep);
      item.classList.toggle("is-done", place < here); item.classList.toggle("is-current", place === here);
      if (place === here) item.setAttribute("aria-current", "step"); else item.removeAttribute("aria-current");
    }
  }
  // Subscribing uses the checkout the account page uses, for the first plan the service offers; the host offers one plan.
  $("funnel-subscribe").addEventListener("click", async () => {
    if (!token) return;
    const button = $("funnel-subscribe"); message("funnel-plan-message", "Checking the plan…");
    try {
      const options = await request("/api/v1/billing/plans");
      if (!options.checkout_available || !Array.isArray(options.plans) || !options.plans.length) throw new Error("Checkout is not available for this account right now. Nothing was charged.");
      await createSession("checkout", options, options.plans[0].plan_ref, button, "funnel-plan-message");
    } catch (error) { message("funnel-plan-message", error.name === "AbortError" ? "The check timed out. Nothing was charged." : error.message, true); }
  });
  renderFunnel();
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
    if (!hits.length) { $("results").append(element("p", "No permitted matches. Try a different description.", "empty")); return; }
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
    try { const value = await request("/api/v1/retrieval", {record_type:"service_retrieval_request/v2", query:$("query").value, mode:$("search-mode").value, top_n:10}); renderResults(value.hits); message("search-message", "References only. No bodies loaded."); }
    catch (error) { message("search-message", error.name === "AbortError" ? "Search timed out. You can retry." : error.message, true); }
    finally { $("search-button").disabled = !token; }
  });
  /* Recorded usage, item by item: one row for each item, with its number of recorded downloads and the time of the latest, in
     the order the service gives. The table is drawn only from the record version this page was written against, with a list of
     items it can read; any other record is left to the raw view. The raw record always stays behind the disclosure below the
     table, for developers. Every value is written as text, never as markup. */
  const USAGE_RECORD_TYPE = "durable_tenant_usage/v1";
  const usageTime = new Intl.DateTimeFormat(undefined, {dateStyle:"medium", timeStyle:"short"});
  const usageItems = value => value?.record_type === USAGE_RECORD_TYPE && Array.isArray(value.items)
    && value.items.every(row => typeof row?.item_identity === "string" && row.item_identity !== "" && Number.isInteger(row.records) && row.records > 0 && Number.isFinite(row.last_used_at))
    ? value.items : null;
  function renderUsage(value) {
    const rows = usageItems(value), view = $("usage-view");
    $("usage").textContent = JSON.stringify(value, null, 2); $("usage-raw").hidden = false;
    if (!rows) { view.replaceChildren(element("p", "This service answered with a usage record this page was not written for, so no table is shown. The raw record is below.", "usage-note")); return; }
    if (!rows.length) { view.replaceChildren(element("p", "No downloads are recorded for this account yet. Each item your tools download appears here.", "usage-empty")); return; }
    const labels = ["Item", "Downloads", "Last used"], total = rows.reduce((sum, row) => sum + row.records, 0);
    const table = element("table", "", "usage-table"), head = document.createElement("thead"), heading = document.createElement("tr"), body = document.createElement("tbody");
    for (const label of labels) { const cell = element("th", label); cell.scope = "col"; heading.append(cell); }
    head.append(heading);
    for (const row of rows) {
      const line = document.createElement("tr"), when = new Date(row.last_used_at * 1000), time = element("time", usageTime.format(when));
      time.dateTime = when.toISOString();
      const cells = [element("td", "", "usage-item"), element("td", String(row.records), "usage-count"), element("td", "", "usage-when")];
      // A long item name may break after an underscore or a dot, where a reader expects it, and not inside a word.
      row.item_identity.split(/(?<=[_.])/).forEach((part, index) => { if (index) cells[0].append(document.createElement("wbr")); cells[0].append(part); });
      cells[2].append(time);
      cells.forEach((cell, index) => { cell.dataset.label = labels[index]; line.append(cell); });
      body.append(line);
    }
    table.append(element("caption", "Downloads recorded for this account, item by item", "sr-only"), head, body);
    view.replaceChildren(element("p", total + (total === 1 ? " download of " : " downloads of ") + rows.length + (rows.length === 1 ? " item." : " items."), "usage-summary"), table);
  }
  $("refresh-usage").addEventListener("click", async () => {
    const epoch = generation;
    try { renderUsage(await request("/api/v1/usage")); }
    catch (error) { if (epoch === generation) showUsageNote(error.name === "AbortError" ? "The usage request timed out. You can refresh again." : error.message, true); }
  });
  async function createSession(operation, options, plan, button, target = "billing-message") {
    const key = JSON.stringify([operation, options.policy_digest, plan]), epoch = generation;
    if (!billingRequests.has(key)) billingRequests.set(key, crypto.randomUUID());
    button.disabled = true; message(target, "Requesting a hosted session…");
    try {
      const result = await request("/api/v1/billing/" + operation, {record_type:"billing_session_request/v1", request_id:billingRequests.get(key), policy_digest:options.policy_digest, ...(plan ? {plan_ref:plan} : {})});
      if (epoch !== generation) return;
      const url = new URL(result.redirect_url); if (url.protocol !== "https:" || !["checkout.stripe.com", "billing.stripe.com"].includes(url.hostname) || url.username || url.password) throw new Error("The service returned an unsupported payment destination.");
      const link = element("a", "Open secure " + operation); link.href = url.href; link.rel = "noopener noreferrer"; link.target = "_blank"; $(target).replaceChildren(link);
    } catch (error) { message(target, error.name === "AbortError" ? "The outcome is uncertain. Check the provider before trying again. This page retains the same request identity." : error.message, true); }
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
  /* Staff administration. The overview shows what the role may read; a superadmin also sees every account and acts on one
     at a time, each action under a new request identity. The service checks the role, the session and the time again. */
  const planNames = {paid:"Paid", free_monthly:"Free monthly", founding_free_monthly:"Founding, free monthly", other_comped:"Other free access", none:"None"};
  const when = value => value ? new Date(typeof value === "number" ? value * 1000 : value).toLocaleDateString() : "Never";
  async function loadStaff() {
    const overview = await request("/api/v1/admin/overview");
    $("staff-admin").hidden = false; $("admin-login").hidden = true; $("staff-role").textContent = overview.role;
    const counts = overview.account_counts, usage = overview.usage_counts, health = overview.diagnostics?.health;
    facts($("staff-counts"), [...(counts ? [["Accounts", String(counts.accounts)], ["Paid", String(counts.plans.paid)],
      ["Free monthly", String(counts.plans.free_monthly + counts.plans.founding_free_monthly)], ["Founding places", counts.founding_holders + " of " + counts.founding_limit],
      ["Switched off", String(counts.switched_off)]] : []), ...(usage ? [["Downloads in 30 days", String(usage.downloads_in_the_last_30_days)]] : []),
      ...(health ? [["Service ready", health.ready ? "Yes" : "No"], ["Checks failing", health.checks.filter(row => !row.passed).map(row => row.name).join(", ") || "None"]] : [])]);
    $("staff-accounts").replaceChildren();
    $("staff-links-form").hidden = !overview.permissions.includes("accounts.send_sign_up_links");
    if (!overview.permissions.includes("accounts.list")) { message("staff-message", "Your role reads the figures above. Account changes need a superadmin."); return; }
    const listing = await request("/api/v1/admin/accounts");
    for (const row of listing.accounts) {
      const item = element("article", "", "result"); item.dataset.tenant = row.tenant_id;
      item.append(element("h3", row.email || row.provider_user_id), element("span", planNames[row.plan_state] || row.plan_state, "badge"));
      item.append(element("p", "Created " + when(row.created_at) + " · " + (row.email_confirmed ? "Confirmed" : "Not confirmed") + " · Last use " + when(row.last_item_at || row.last_sign_in_at)));
      if (row.founding) item.append(element("p", "Founding account", "caption"));
      if (row.sign_up_link?.state === "pending") item.append(element("p", "Sign-up link sent " + when(row.sign_up_link.sent_at) + ", waiting for this person to choose a password"
        + (row.sign_up_link.free_monthly ? ". Free monthly Baltor Pro starts when the account opens." : "."), "caption"));
      if (row.enabled === false) item.append(element("p", "Switched off", "caption"));
      const free = row.plan_state === "free_monthly" || row.plan_state === "founding_free_monthly";
      const actions = !row.tenant_id ? [] : [[free ? "revoke_free_monthly" : "grant_free_monthly", free ? "Revoke free monthly" : "Grant free monthly"],
        [row.enabled === false ? "enable" : "disable", row.enabled === false ? "Enable" : "Disable"]];
      for (const [operation, label] of actions) {
        if (operation === "grant_free_monthly" && row.plan_state === "paid") continue;
        const button = element("button", label + " for " + (row.email || row.tenant_id), "quiet"); button.type = "button";
        button.addEventListener("click", async () => {
          if (staffBusy || !confirm(label + " for " + (row.email || row.tenant_id) + "?")) return;
          staffBusy = true; button.disabled = true;
          try { await request("/api/v1/admin/accounts", {record_type:"service_account_administration_request/v1", operation, request_id:crypto.randomUUID(), tenant_id:row.tenant_id});
            await loadStaff(); message("staff-message", label + " is done."); }
          catch (error) { message("staff-message", error.message + " Refresh to see the current state before trying again.", true); }
          finally { staffBusy = false; button.disabled = false; }
        }); item.append(button);
      }
      $("staff-accounts").append(item);
    }
    message("staff-message", listing.total + " accounts. Founding places used: " + listing.founding_holders + " of " + listing.founding_limit + ".");
  }
  $("refresh-staff").addEventListener("click", () => loadStaff().catch(error => message("staff-message", error.message, true)));
  /* A superadmin starts Baltor's own sign-up for a few addresses. Each person gets one message from this service and chooses
     their own password on the confirmation page; an address that already has an account gets nothing. */
  let staffLinkRequest = null;
  const linkOutcomes = {sent:"Link sent to ", address_has_an_account:"No email sent, the account already exists: ",
    address_sent_recently:"No email sent, a link went out recently: ", failed:"The link could not be sent: "};
  $("staff-links-form").addEventListener("submit", async event => {
    event.preventDefault(); if (staffBusy) return;
    const addresses = $("staff-link-addresses").value.split(/[\s,;]+/).map(value => value.trim()).filter(Boolean);
    if (!addresses.length) { message("staff-message", "Enter at least one email address.", true); return; }
    if (addresses.length > 10) { message("staff-message", "Send at most 10 links at a time.", true); return; }
    const fields = {record_type:"service_staff_sign_up_link_request/v1", addresses, free_monthly:$("staff-link-free").checked};
    const signature = JSON.stringify(fields);
    if (!staffLinkRequest || staffLinkRequest.signature !== signature) staffLinkRequest = {signature, id:crypto.randomUUID()};
    staffBusy = true; $("staff-link-button").disabled = true;
    try {
      const result = await request("/api/v1/admin/sign-up-links", {...fields, request_id:staffLinkRequest.id});
      staffLinkRequest = null; $("staff-link-addresses").value = ""; $("staff-link-free").checked = false;
      await loadStaff();
      message("staff-message", result.links.map(row => (linkOutcomes[row.outcome] || row.outcome + ": ") + row.address + ".").join(" "));
    } catch (error) { message("staff-message", error.message + " Refresh to see the current state; an exact retry reuses this request identity.", true); }
    finally { staffBusy = false; $("staff-link-button").disabled = false; }
  });
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
  // The reviewed recipes are offered as tabs, one for each client, and only once the record has passed every rule above.
  let chosenRecipe = "";
  const recipeTabs = () => [...$("client-tabs").querySelectorAll('[role="tab"]')];
  // The configuration text of a reviewed recipe, with this service's own address in place of the placeholder.
  const configurationText = recipe => {
    const endpoint = location.origin + "/mcp";
    const fill = value => value === endpointPlaceholder ? endpoint : Array.isArray(value) ? value.map(fill) : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).map(([key, item]) => [key, fill(item)])) : value;
    const configuration = fill(recipe.configuration);
    return recipe.format === "toml" ? tomlText(configuration) : JSON.stringify(configuration, null, 2);
  };
  /* A recipe's note may name a file this website serves under /assets/, such as the Pi extension at /assets/pi/baltor.ts. That path
     becomes a link to the file on this website, so the reader can open and read it before saving it, and one button copies the
     file's full address. The note keeps its exact words; only the path turns into a link. Any other text stays text. Finding 6 of
     the persona journeys of September 24, 2026. */
  const servedFile = /\/assets\/[a-z0-9][a-z0-9-]*(?:\/[a-z0-9][a-z0-9._-]*)*\.[a-z0-9]+(?=[\s,.;:)]|$)/;
  function renderNote(note) {
    const target = $("client-configuration-note"), found = note.match(servedFile);
    target.replaceChildren();
    if (!found) { target.textContent = note; $("client-file").hidden = true; return; }
    const link = element("a", found[0]); link.href = found[0]; link.id = "client-file-link"; link.target = "_blank"; link.rel = "noopener";
    target.append(note.slice(0, found.index), link, note.slice(found.index + found[0].length));
    $("client-file").hidden = false; $("client-file-address").textContent = location.origin + found[0];
    $("copy-client-file").textContent = "Copy the file address";
  }
  function renderRecipe() {
    const selected = recipes?.recipes.find(item => item.id === chosenRecipe);
    if (!selected) return;
    $("client-configuration").textContent = configurationText(selected);
    $("configuration-location").textContent = selected.configuration_location; renderNote(selected.configuration_note);
    $("client-verify-command").textContent = selected.verification_command; $("client-verify-note").textContent = selected.verification_note;
    $("client-version-note").textContent = selected.version_note;
    $("client-revoke-note").textContent = recipes.revocation_note; $("client-removal-note").textContent = selected.removal_note;
    $("client-source").href = selected.source_url; $("client-source").textContent = selected.source_url;
    $("copy-configuration").disabled = false; $("copy-configuration").textContent = "Copy configuration without secrets"; message("setup-message", "");
  }
  function chooseRecipe(id, focus) {
    chosenRecipe = id;
    for (const tab of recipeTabs()) {
      const chosen = tab.dataset.recipe === id;
      tab.setAttribute("aria-selected", String(chosen)); tab.tabIndex = chosen ? 0 : -1;
      if (chosen) { $("client-recipe-panel").setAttribute("aria-labelledby", tab.id); if (focus) tab.focus(); }
    }
    renderRecipe();
  }
  $("client-tabs").addEventListener("click", event => { const tab = event.target.closest('[role="tab"]'); if (tab) chooseRecipe(tab.dataset.recipe, false); });
  $("client-tabs").addEventListener("keydown", event => {
    const tabs = recipeTabs(), index = tabs.findIndex(tab => tab.dataset.recipe === chosenRecipe);
    const next = {ArrowRight:index + 1, ArrowLeft:index - 1, Home:0, End:tabs.length - 1}[event.key];
    if (next === undefined || !tabs.length) return;
    event.preventDefault(); chooseRecipe(tabs[(next + tabs.length) % tabs.length].dataset.recipe, true);
  });
  $("copy-client-file").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("client-file-address").textContent); $("copy-client-file").textContent = "File address copied"; }
    catch (_) { message("setup-message", "Clipboard unavailable. Select and copy the file address."); }
  });
  $("copy-configuration").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("client-configuration").textContent); $("copy-configuration").textContent = "Configuration copied"; }
    catch (_) { message("setup-message", "Clipboard unavailable. Select and copy the configuration text."); }
  });
  request("/assets/client-recipes.json", null, false, false, {raw:true}).then(value => {
    const refusal = recipeRefusal(value);
    if (refusal) throw Object.assign(new Error("Connection recipes refused"), {refusal});
    recipes = value; $("client-tabs").replaceChildren();
    for (const recipe of value.recipes) {
      const tab = element("button", recipe.name); tab.type = "button"; tab.id = "client-tab-" + recipe.id; tab.dataset.recipe = recipe.id;
      tab.setAttribute("role", "tab"); tab.setAttribute("aria-controls", "client-recipe-panel"); $("client-tabs").append(tab);
    }
    chooseRecipe(value.recipes[0].id, false);
    // The homepage shows one reviewed entry. The page is served with the public address written in; once the record has passed
    // every rule above, the entry is written again from the record with this service's own address, as the Get started page shows it.
    const homeEntry = document.querySelector("[data-home-recipe]"), homeRecipe = value.recipes.find(recipe => recipe.id === homeEntry?.dataset.homeRecipe);
    if (homeEntry && homeRecipe) homeEntry.textContent = configurationText(homeRecipe);
  }).catch(error => {
    recipes = null; $("setup-message").dataset.refusal = error.refusal || "unavailable";
    chosenRecipe = ""; $("client-tabs").replaceChildren(); $("copy-configuration").disabled = true; $("client-file").hidden = true; $("configuration-location").textContent = "No connection settings are shown";
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
  /* Signed in, Get set up offers "Create a client token" where a visitor sees "Sign in to check access": the connection check
     and every harness run with a client token. The link opens the account page at its token panel and loads the panel, so the
     form that creates a token is ready. Fix 4 of the persona journeys of September 24, 2026. */
  $("setup-create-token").addEventListener("click", event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0 || !token) return;
    clientAccess.refresh().then(() => { if (!$("client-access-controls").hidden) $("client-token-label").focus({preventScroll:true}); });
  });
  $("try-example").addEventListener("click", () => { navigate("/app"); $("query").value = "review inputs"; message("search-message", token ? "Example query prepared. Select Search to retrieve permitted references." : "Sign in first. This button does not submit a query or download a file."); });
  /* A reload or a typed address in a tab that keeps an email sign-in opens the same account again, on the page asked for. A page
     opened by a message link starts from that link instead and forgets a kept sign-in, and an expired one is forgotten. */
  const kept = keptSession.read();
  if (kept && !confirmation && kept.expires_at > Date.now() / 1000 + 30) connectService(kept.access_token, false, {stay:true});
  else keptSession.clear();
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
      registrationOpen = value.website.registration_available === true;
      applyAccessState(value.website.registration_available === true);
      applyRegistrationState(registrationOpen);
      applyStartState(startState(value.website));
      applyPaymentState(publicPaymentState(value.website.registration_available === true, value.billing.checkout === true));
      applyClientAccessState(value.website.client_access_available === true);
      if (value.website.browser_identity_available) openBrowserIdentity();
    }
    renderFunnel();
    function openBrowserIdentity() {
      request("/api/v1/account/identity", null, false).then(settings => {
        if (settings.record_type !== "browser_identity_public_configuration/v1" || settings.provider_profile !== "supabase_user/v1" || !settings.publishable_key.startsWith("sb_publishable_") || !window.BaltorIdentitySdk) throw new Error("Identity configuration unavailable");
        identityConfiguration = settings;
        identityClient = createIdentityClient(settings);
        // The sign-up form is offered only where this service sends the link itself. The provider's own sign-up is never used.
        const signupOpen = settings.email_signup_enabled === true && settings.signup_available === true;
        $("email-login").hidden = false; $("email-signup").hidden = !signupOpen; $("signup-closed").hidden = signupOpen;
        $("email-recovery").hidden = settings.recovery_available !== true;
        $("login-access-description").textContent = "Sign in with your email address and password.";
        $("email-access-note").textContent = "Email credentials are checked by the configured identity provider. Model keys are separate.";
        $("email-signin-limit").textContent = signupOpen ? "Email sign-in is available. Account creation and subscription access are separate." : "Email sign-in is available for prepared accounts. Public account creation remains closed; a service token does not create an account or subscription.";
        showConfirmation();
      }).catch(() => {
        message("identity-message", "Email sign-in configuration is unavailable. Operator service tokens remain separate.", true);
        $("confirm-loading").hidden = true;
        if (confirmation) message("confirm-message", "Sign-in settings are unavailable, so this link cannot be finished now. Your link was not used; open it again later.", true);
      });
    }
  }).catch(() => { waitlistOffer(null); $("service-status").textContent = "Service unavailable. Check the host configuration."; $("protocol-note").textContent = "Could not confirm the installed protocol. Do not assume client compatibility."; });
})();
