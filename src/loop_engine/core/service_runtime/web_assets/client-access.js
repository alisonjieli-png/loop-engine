"use strict";
/* Customer credentials use the existing authenticated request boundary. */
window.BaltorClientAccess = {
  /* said and failureState come from service.js: the service's own sentences for a refusal, and whether the status line shows a
     refusal or a failure. Without them a failure shows its short message, as before. */
  create({request, element, message, current, said = error => error.message, failureState = () => true}) {
    const $ = id => document.getElementById(id);
    const path = "/api/v1/account/access", version = "service_client_access_request/v1";
    const scopeLabels = {"provisioning:metadata":"Search material and send library feedback", "provisioning:read":"Download permitted material", "usage:read":"Read service usage"};
    let options = null, active = false, submission = null, loading = null, opened = false;
    const revocations = new Map();
    const eligible = () => { const state = current(); return state.connected && state.mode === "browser_identity" && state.available; };
    /* The overview tile for client tokens says how many are active, or why none can be listed on this connection. */
    const tile = (value, note) => { $("account-tile-keys").textContent = value; $("account-tile-keys-note").textContent = note; };
    const clearSecret = () => { $("client-issued-token").value = ""; $("client-issued-token").type = "password"; $("client-issued").hidden = true; };
    function controls() {
      $("refresh-client-access").disabled = !eligible() || active;
      $("create-client-token").disabled = !eligible() || active || !options?.writes_authorized || options.active_tokens >= options.maximum_active_tokens || options.retained_token_records >= options.maximum_token_records;
    }
    function reset() {
      options = null; active = false; submission = null; loading = null; opened = false; revocations.clear(); clearSecret();
      tile("Not loaded", "One for each device or tool.");
      $("client-access-controls").hidden = true; $("client-access-list").replaceChildren(); $("client-token-label").value = "";
      message("client-access-message", "Sign in with your verified account to manage client tokens. A service token cannot create more credentials."); controls();
    }
    function connectionChanged() {
      controls();
      if (eligible()) message("client-access-message", "Create one token for each device or tool. These are not model-provider keys.");
      // A sign-in kept by the tab can open before the service has said what it offers, so "not enabled" waits for the answer.
      else if (current().known && !current().available) message("client-access-message", "Client token management is not enabled on this service.");
      if (current().connected && !eligible() && current().mode !== "browser_identity") tile("Not listed here", "Client tokens are created from an email sign-in.");
      openView();
    }
    /* A second request for the list while one is on its way waits for that one, so a caller that focuses the form after the
       list arrives, such as the Create a client token link of Get set up, finds the form ready. */
    function refresh() {
      if (loading) return loading;
      if (!eligible() || active) return Promise.resolve();
      const pending = load().finally(() => { if (loading === pending) loading = null; });
      loading = pending;
      return pending;
    }
    async function load() {
      if (!eligible() || active) return;
      const epoch = current().generation; active = true; controls();
      try {
        const value = await request(path);
        if (epoch !== current().generation) return;
        if (value.record_type !== "service_client_access_options/v1") throw new Error("Unsupported client-access response.");
        options = value; $("client-access-controls").hidden = false;
        $("client-token-quota").textContent = value.active_tokens + " / " + value.maximum_active_tokens + " active";
        tile(value.active_tokens + " active", "Up to " + value.maximum_active_tokens + " at once. Each is shown once; the service keeps a digest.");
        const selected = new Set([...$("client-token-scopes").querySelectorAll("input:checked")].map(input => input.value));
        $("client-token-scopes").replaceChildren(element("legend", "Allowed operations"));
        for (const scope of value.allowed_scopes) {
          const label = element("label", "", "scope-choice"), input = document.createElement("input");
          input.type = "checkbox"; input.value = scope; input.checked = selected.size ? selected.has(scope) : true;
          label.append(input, document.createTextNode(scopeLabels[scope] || scope)); $("client-token-scopes").append(label);
        }
        $("client-token-minutes").max = Math.floor(value.maximum_lifetime_seconds / 60);
        if (!$("client-token-minutes").value) $("client-token-minutes").value = value.default_lifetime_seconds / 60;
        $("client-access-list").replaceChildren();
        if (!value.tokens.length) $("client-access-list").append(element("p", "You have not created a client token yet.", "empty"));
        for (const row of value.tokens) {
          const card = element("article", "", "result"); card.dataset.state = row.state; card.append(element("h3", row.label), element("span", row.state, "badge"));
          card.append(element("p", row.scopes.map(scope => scopeLabels[scope] || scope).join(" · ")), element("p", "Expires " + new Date(row.expires_at * 1000).toLocaleString()));
          if (row.state === "active" && value.writes_authorized) {
            const button = element("button", "Revoke " + row.label, "quiet"); button.type = "button";
            button.addEventListener("click", () => revoke(row)); card.append(button);
          }
          $("client-access-list").append(card);
        }
        $("client-history-note").textContent = "Showing " + value.tokens.length + " of " + value.total_records + " personal token records. Revocation cannot recall files already downloaded.";
      } catch (error) { if (epoch === current().generation) message("client-access-message", said(error), failureState(error)); }
      finally { if (epoch === current().generation) { active = false; controls(); } }
    }
    async function revoke(row) {
      if (!eligible() || active || !confirm("Revoke “" + row.label + "”? Its next service request will be refused.")) return;
      const epoch = current().generation; active = true; controls();
      if (!revocations.has(row.key_id)) revocations.set(row.key_id, crypto.randomUUID());
      try {
        await request(path, {record_type:version, operation:"revoke", request_id:revocations.get(row.key_id), key_id:row.key_id});
        if (epoch !== current().generation) return;
        clearSecret(); revocations.delete(row.key_id); message("client-access-message", "Client token revoked.");
      } catch (error) { if (epoch === current().generation) message("client-access-message", said(error) + " Refresh to inspect the result before retrying.", failureState(error)); }
      finally { if (epoch === current().generation) { active = false; controls(); await refresh(); } }
    }
    $("refresh-client-access").addEventListener("click", refresh);
    /* The account page opens with its figures loaded: the client tokens, the usage record and the plans, each read with the
       request its own button sends, once each time the page opens while signed in. Each button still reads them again. */
    const view = document.querySelector('[data-view="account"]');
    function openView() {
      if (!view || view.hidden || !current().connected) { opened = false; return; }
      if (!opened) {
        // A retained token can precede the session response. Wait until the session enables account reads.
        const readers = [$("refresh-usage"), $("refresh-billing")];
        if (readers.some(button => !button || button.disabled)) return;
        opened = true;
        for (const button of readers) button.click();
        if (eligible()) refresh();
      } else if (eligible() && !options) refresh();
    }
    if (view) new MutationObserver(openView).observe(view, {attributes:true, attributeFilter:["hidden"]});
    $("issue-client-access").addEventListener("submit", async event => {
      event.preventDefault(); if (!eligible() || active || !options?.writes_authorized) return;
      const epoch = current().generation;
      const fields = {record_type:version, operation:"issue", label:$("client-token-label").value.trim(), scopes:[...$("client-token-scopes").querySelectorAll("input:checked")].map(input => input.value), lifetime_seconds:Number($("client-token-minutes").value) * 60};
      if (!fields.scopes.length) { message("client-access-message", "Choose at least one operation.", true); return; }
      const signature = JSON.stringify(fields);
      if (!submission || submission.signature !== signature) submission = {signature, id:crypto.randomUUID()};
      active = true; clearSecret(); controls();
      try {
        const result = await request(path, {...fields, request_id:submission.id});
        if (epoch !== current().generation) return;
        if (result.record_type !== "service_client_access_result/v1" || result.committed !== true) throw new Error("Token creation was not confirmed. Refresh before retrying.");
        if (result.token) {
          $("client-issued-token").value = result.token; $("client-issued").hidden = false;
          message("client-access-message", "Save this token now. Use it only for Baltor, through your client's secret settings.");
        } else message("client-access-message", "This request already created a token. Its secret cannot be recovered. Revoke it before making a replacement.");
        submission = null;
      } catch (error) { if (epoch === current().generation) message("client-access-message", said(error) + " No automatic retry was made; an exact retry keeps this request identity.", failureState(error)); }
      finally { if (epoch === current().generation) { active = false; controls(); await refresh(); } }
    });
    $("copy-client-token").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText($("client-issued-token").value); message("client-access-message", "Copied. Keep the token in your secret manager, not a shared file."); }
      catch (_) { $("client-issued-token").type = "text"; $("client-issued-token").select(); message("client-access-message", "Copy the selected token, then clear it from this page."); }
    });
    $("clear-client-token").addEventListener("click", clearSecret);
    reset();
    return {reset, connectionChanged, refresh};
  }
};
