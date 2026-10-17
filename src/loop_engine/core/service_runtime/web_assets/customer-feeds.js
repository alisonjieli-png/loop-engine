"use strict";
/* Saved feeds for agents on the account page. The service checks every permission and owns every record; this file
   draws its answers with textContent only, so no feed text, name or label is ever read as markup. The section stays
   hidden unless the service's capabilities record says saved feeds are available on this host. */
window.BaltorCustomerFeeds = {
  create({request, element, message, current, said = error => error.message, failureState = () => true}) {
    const $ = id => document.getElementById(id);
    const path = "/api/v1/account/feeds", version = "customer_feed_request/v1";
    let overview = null, active = false;
    /* One request identity for each logical action, kept until it succeeds, so a retry repeats the same request. */
    const identities = new Map();
    const eligible = () => { const state = current(); return state.connected && state.mode === "browser_identity" && state.available; };
    const button = (text, action, className = "quiet") => { const node = element("button", text, className); node.type = "button"; node.addEventListener("click", action); return node; };
    function controls() {
      $("refresh-feeds").disabled = !eligible() || active;
      for (const id of ["preview-feed", "save-feed", "export-feeds"]) $(id).disabled = !eligible() || active || !overview;
    }
    function reset() {
      overview = null; active = false; identities.clear();
      $("account-feeds").hidden = !current().available; $("feeds-controls").hidden = true;
      $("feed-list").replaceChildren(); $("feed-preview").replaceChildren(); $("feed-preview").hidden = true;
      message("feeds-message", "Sign in with your email to save feeds and choose which key reads each one."); controls();
    }
    function connectionChanged() {
      $("account-feeds").hidden = !current().available; controls();
      if (eligible() && !overview) refresh();
    }
    async function send(signature, fields) {
      if (!identities.has(signature)) identities.set(signature, crypto.randomUUID());
      const result = await request(path, {record_type:version, request_id:identities.get(signature), ...fields});
      identities.delete(signature);
      return result;
    }
    async function act(work, done) {
      if (!eligible() || active) return;
      const epoch = current().generation; active = true; controls();
      try { const result = await work(); if (epoch === current().generation && done) message("feeds-message", done(result)); }
      catch (error) { if (epoch === current().generation) message("feeds-message", said(error), failureState(error)); }
      finally { if (epoch === current().generation) { active = false; controls(); await refresh(); } }
    }
    function draft() {
      const template = overview.templates.find(row => row.template === $("feed-template").value) || overview.templates[0];
      return {...template.settings, name:$("feed-name").value.trim(), format:$("feed-format").value,
        max_items:Number($("feed-max-items").value), max_age_days:Number($("feed-max-age").value)};
    }
    function showPreview(value) {
      const box = $("feed-preview"); box.replaceChildren(); box.hidden = false;
      box.append(element("h4", "Preview: " + value.delivery_state),
        element("p", value.counts.delivered + " items would be sent, " + value.counts.excluded + " left out by your settings, "
          + value.counts.withheld_for_access + " held back by access, about " + value.estimated_usage.bytes + " bytes."));
      const list = element("ul", "");
      for (const row of value.items.slice(0, 8)) list.append(element("li", row.title + " (" + row.matched_by.join(", ") + ")"));
      box.append(list);
      const reasons = {};
      for (const row of value.excluded) for (const reason of row.reasons) reasons[reason] = (reasons[reason] || 0) + 1;
      if (Object.keys(reasons).length) box.append(element("p", "Left out: " + Object.entries(reasons).map(([name, count]) => name + " " + count).join(", ") + "."));
      if (value.stale_sources.length) box.append(element("p", value.stale_sources.length + " sources are older than this feed allows."));
      for (const read of value.streams) if (read.status !== "searched") box.append(element("p", "Not read: " + read.stream + " (" + (read.reason || read.status) + ")."));
      box.append(element("p", "A preview saves nothing and starts nothing.", "caption"));
    }
    function draw() {
      const list = $("feed-list"); list.replaceChildren();
      $("feeds-quota").textContent = overview.definitions.length + " / " + overview.limits.maximum_definitions + " feeds";
      const keys = overview.agent_keys.filter(key => key.state === "active" && key.reads_feeds);
      if (!overview.definitions.length) list.append(element("p", "You have not saved a feed yet.", "empty"));
      for (const feed of overview.definitions) {
        const card = element("article", "", "result"); card.dataset.state = feed.state;
        card.append(element("h4", feed.name), element("span", feed.state, "badge"), element("p", "Version " + feed.definition_version + ", " + feed.settings.format));
        const row = element("div", "", "actions");
        row.append(button("Preview", () => act(async () => showPreview(await request(path, {record_type:version, operation:"preview_definition", feed_id:feed.feed_id})))),
          button("Copy", () => act(() => send("clone:" + feed.feed_id, {operation:"clone_definition", feed_id:feed.feed_id, name:(feed.name + " copy").slice(0, 64)}), () => "Feed copied.")),
          button(feed.state === "active" ? "Pause" : "Resume", () => act(() => send(feed.state + ":" + feed.revision, {operation:feed.state === "active" ? "pause_definition" : "resume_definition", feed_id:feed.feed_id, expected_revision:feed.revision}), () => "Feed " + (feed.state === "active" ? "paused." : "resumed."))),
          button("Delete", () => { if (confirm("Delete “" + feed.name + "”? Its assignments and delivery history are removed too.")) act(() => send("delete:" + feed.revision, {operation:"delete_definition", feed_id:feed.feed_id, expected_revision:feed.revision}), () => "Feed deleted."); }));
        card.append(row);
        for (const assignment of overview.assignments.filter(item => item.feed_id === feed.feed_id)) {
          const last = assignment.deliveries[0];
          const line = element("p", (assignment.key_label || "A removed key") + ": " + assignment.state + (assignment.key_state !== "active" ? " (key " + assignment.key_state + ")" : "")
            + (last ? ", last read " + new Date(last.last_delivered_at * 1000).toLocaleString() + ", " + last.items_served + " items" : ", not read yet"));
          line.append(button(assignment.state === "active" ? "Pause" : "Resume", () => act(() => send(assignment.state + ":" + assignment.revision, {operation:assignment.state === "active" ? "pause_assignment" : "resume_assignment", assignment_id:assignment.assignment_id, expected_revision:assignment.revision}))),
            button("Remove", () => act(() => send("unassign:" + assignment.revision, {operation:"delete_assignment", assignment_id:assignment.assignment_id, expected_revision:assignment.revision}), () => "Key removed from this feed.")));
          card.append(line);
        }
        if (keys.length) {
          const choice = document.createElement("select"); choice.setAttribute("aria-label", "Key for " + feed.name);
          for (const key of keys) { const option = element("option", key.label); option.value = key.key_id; choice.append(option); }
          card.append(choice, button("Assign key", () => act(() => send("assign:" + feed.feed_id + ":" + choice.value, {operation:"create_assignment", feed_id:feed.feed_id, key_id:choice.value}), () => "Key assigned. It can read this feed now.")));
        }
        list.append(card);
      }
      if (!keys.length) list.append(element("p", "Create a Baltor key with search access above, then assign it to a feed.", "caption"));
    }
    async function refresh() {
      if (!eligible() || active) return;
      const epoch = current().generation; active = true; controls();
      try {
        const value = await request(path);
        if (epoch !== current().generation) return;
        if (value.record_type !== "customer_feed_overview/v1") throw new Error("Unsupported feed settings response.");
        overview = value; $("feeds-controls").hidden = false;
        const chosen = $("feed-template").value;
        $("feed-template").replaceChildren(...value.templates.map(row => { const option = element("option", row.title); option.value = row.template; return option; }));
        if (chosen) $("feed-template").value = chosen;
        draw(); message("feeds-message", "Each key reads only the feeds you assign to it.");
      } catch (error) { if (epoch === current().generation) message("feeds-message", said(error), failureState(error)); }
      finally { if (epoch === current().generation) { active = false; controls(); } }
    }
    $("refresh-feeds").addEventListener("click", refresh);
    $("preview-feed").addEventListener("click", () => act(async () => showPreview(await request(path, {record_type:version, operation:"preview_definition", definition:draft()}))));
    $("feed-definition-form").addEventListener("submit", event => {
      event.preventDefault();
      const fields = draft();
      act(() => send("create:" + JSON.stringify(fields), {operation:"create_definition", definition:fields}), () => "Feed saved. Assign a key so an agent can read it.");
    });
    $("export-feeds").addEventListener("click", () => act(async () => {
      const value = await request(path, {record_type:version, operation:"export_settings"});
      const link = document.createElement("a"), url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + "\n"], {type:"application/json"}));
      link.href = url; link.download = "baltor-feed-settings.json"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, () => "Settings downloaded."));
    reset();
    return {reset, connectionChanged, refresh};
  }
};
