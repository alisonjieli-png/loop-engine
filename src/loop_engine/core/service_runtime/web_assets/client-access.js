"use strict";
/* Customer credentials use the existing authenticated request boundary. */
window.BaltorClientAccess = {
  create({request, element, message, current}) {
    const $ = id => document.getElementById(id);
    const path = "/api/v1/account/access", version = "service_client_access_request/v1";
    const scopeLabels = {"provisioning:metadata":"Search permitted material", "provisioning:read":"Download permitted material", "usage:read":"Read service usage"};
    let options = null, active = false, submission = null;
    const revocations = new Map();
    const eligible = () => { const state = current(); return state.connected && state.mode === "browser_identity" && state.available; };
    const clearSecret = () => { $("client-issued-token").value = ""; $("client-issued-token").type = "password"; $("client-issued").hidden = true; };
    function controls() {
      $("refresh-client-access").disabled = !eligible() || active;
      $("create-client-token").disabled = !eligible() || active || !options?.writes_authorized || options.active_tokens >= options.maximum_active_tokens || options.retained_token_records >= options.maximum_token_records;
    }
    function reset() {
      options = null; active = false; submission = null; revocations.clear(); clearSecret();
      $("client-access-controls").hidden = true; $("client-access-list").replaceChildren(); $("client-token-label").value = "";
      message("client-access-message", "Sign in with your verified account to manage client tokens. A service token cannot create more credentials."); controls();
    }
    function connectionChanged() {
      controls();
      if (eligible()) message("client-access-message", "Load your tokens to connect a development tool. These are not model-provider keys.");
      else if (!current().available) message("client-access-message", "Customer token management is not enabled on this service. Your operator issues and revokes your access.");
    }
    async function refresh() {
      if (!eligible() || active) return;
      const epoch = current().generation; active = true; controls();
      try {
        const value = await request(path);
        if (epoch !== current().generation) return;
        if (value.record_type !== "service_client_access_options/v1") throw new Error("Unsupported client-access response.");
        options = value; $("client-access-controls").hidden = false;
        $("client-token-quota").textContent = value.active_tokens + " / " + value.maximum_active_tokens + " active";
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
          const card = element("article", "", "result"); card.append(element("h3", row.label), element("span", row.state, "badge"));
          card.append(element("p", row.scopes.map(scope => scopeLabels[scope] || scope).join(" · ")), element("p", "Expires " + new Date(row.expires_at * 1000).toLocaleString()));
          if (row.state === "active" && value.writes_authorized) {
            const button = element("button", "Revoke " + row.label, "quiet"); button.type = "button";
            button.addEventListener("click", () => revoke(row)); card.append(button);
          }
          $("client-access-list").append(card);
        }
        $("client-history-note").textContent = "Showing " + value.tokens.length + " of " + value.total_records + " personal token records. Revocation cannot recall files already downloaded.";
      } catch (error) { if (epoch === current().generation) message("client-access-message", error.message, true); }
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
      } catch (error) { if (epoch === current().generation) message("client-access-message", error.message + " Refresh to inspect the result before retrying.", true); }
      finally { if (epoch === current().generation) { active = false; controls(); await refresh(); } }
    }
    $("refresh-client-access").addEventListener("click", refresh);
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
      } catch (error) { if (epoch === current().generation) message("client-access-message", error.message + " No automatic retry was made; an exact retry keeps this request identity.", true); }
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
