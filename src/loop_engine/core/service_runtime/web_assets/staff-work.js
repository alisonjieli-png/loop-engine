"use strict";
window.BaltorStaffWork = (() => {
  function create({request, element, current}) {
    const $ = id => document.getElementById(id), endpoint = "/api/v1/admin/work";
    let epoch = 0, sequence = 0, tasks = [], pending = null, saving = false, shown = null;
    const status = text => { $("dot-work-status").textContent = text; };
    const permitted = () => current().connected && current().allowed;
    function reset() {
      epoch++; sequence++; tasks = []; pending = null; saving = false; shown = null;
      $("dot-work").hidden = true; $("dot-work-form").reset();
      $("dot-work-task").replaceChildren(); $("dot-work-list").replaceChildren();
      $("dot-work-detail").replaceChildren(); $("dot-work-list-note").textContent = "";
      $("dot-work-newer").hidden = true; $("dot-work-older").hidden = true;
      $("dot-work-submit").disabled = true; status("");
    }
    async function briefs(mine) {
      const values = [];
      for (const name of ["context", "feedback"]) {
        const response = await fetch("/dot-" + name + ".json", {cache:"no-store", credentials:"omit", redirect:"error", signal:AbortSignal.timeout(15000)});
        if (!response.ok) throw Error("The task brief could not be read.");
        const record = await response.json(), revision = (response.headers.get("etag") || "").replace(/^"|"$/g, "");
        if (record.record_type !== "baltor_dot_brief/v1" || !/^[a-f0-9]{64}$/.test(revision)) throw Error("The task brief has no valid revision.");
        for (const task of record.tasks) values.push({brief:name, revision, id:task.id, title:task.title});
      }
      if (mine !== epoch || !permitted()) return;
      tasks = values; $("dot-work-task").replaceChildren();
      for (const [index, task] of tasks.entries()) {
        const option = element("option", task.title); option.value = String(index); $("dot-work-task").append(option);
      }
      $("dot-work-submit").disabled = false;
    }
    // Refresh lists page 1 of the day and filter typed; Older and Newer page
    // the listing on screen, never a day or filter typed after it.
    async function list(page = 1, of = null) {
      const mine = epoch, call = ++sequence;
      if (!permitted()) return;
      $("dot-work-list").replaceChildren(); $("dot-work-list-note").textContent = "";
      $("dot-work-newer").hidden = true; $("dot-work-older").hidden = true;
      const filter = of || {day:$("dot-work-day").value, task_id:$("dot-work-filter").value.trim()};
      const query = new URLSearchParams({day:filter.day, page:String(page)});
      if (filter.task_id) query.set("task_id", filter.task_id);
      const result = await request(endpoint + "?" + query);
      if (mine !== epoch || call !== sequence || !permitted()) return;
      if (result.record_type !== "service_staff_work_result/v1" || !Array.isArray(result.items) || result.page !== page
          || !Number.isInteger(result.matches) || !Number.isInteger(result.limit)) throw Error("The saved reports could not be read.");
      shown = {...filter, page};
      for (const row of result.items) {
        const item = element("article", "", "admin-row"), button = element("button", row.title, "quiet");
        button.type = "button"; button.addEventListener("click", () => detail(row.id).catch(showError));
        item.append(button, element("p", row.kind.replaceAll("_", " ") + " · " + row.task_id + " · " + row.file_count + " files", "caption"));
        $("dot-work-list").append(item);
      }
      if (!result.items.length) $("dot-work-list").append(element("p", result.matches ? "No reports on this page." : "No report for this day and task.", "caption"));
      const first = (page - 1) * result.limit, unreadable = Array.isArray(result.unreadable) ? result.unreadable.length : 0;
      $("dot-work-list-note").textContent = ((result.items.length ? "Reports " + (first + 1) + " to " + (first + result.items.length) + " of " + result.matches + ", newest first." : "")
        + (unreadable ? " " + unreadable + " saved report(s) could not be read and are left out." : "")
        + (!result.complete && !unreadable ? " Some matching reports may not be listed. Narrow the task filter to see a smaller set." : "")).trim();
      $("dot-work-newer").hidden = page <= 1; $("dot-work-older").hidden = result.has_next !== true;
    }
    async function detail(id) {
      const mine = epoch, call = ++sequence;
      if (!permitted()) return;
      $("dot-work-detail").replaceChildren();
      const result = await request(endpoint + "?" + new URLSearchParams({id}));
      if (mine !== epoch || call !== sequence || !permitted()) return;
      if (result.record_type !== "service_staff_work_result/v1" || result.id !== id) throw Error("The report identity did not match.");
      const doc = result.document, box = $("dot-work-detail");
      box.append(element("h3", doc.title), element("p", result.id, "caption"), element("pre", doc.message, "dot-work-text"));
      for (const link of doc.links) box.append(element("p", link, "dot-work-text"));
      for (const file of doc.files) {
        const details = element("details", ""), summary = element("summary", file.name + " · " + file.bytes + " bytes");
        details.append(summary, element("p", "SHA-256 " + file.sha256, "caption"), element("pre", file.content, "dot-work-text"));
        const download = element("button", "Save file", "quiet"); download.type = "button";
        download.addEventListener("click", () => {
          if (!permitted() || mine !== epoch) return;
          const url = URL.createObjectURL(new Blob([file.content], {type:"text/plain;charset=utf-8"}));
          const anchor = document.createElement("a"); anchor.href = url; anchor.download = file.name.split("/").pop();
          anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        details.append(download); box.append(details);
      }
      const reply = element("button", "Reply to this report", "quiet"); reply.type = "button";
      reply.addEventListener("click", () => {
        if (pending) { status("Reconcile the pending submission or choose New report first."); return; }
        if ($("dot-work-message").value || $("dot-work-files").files.length) {
          status("A draft is still in the form. Save it or choose New report before replying."); return;
        }
        const index = tasks.findIndex(task => task.id === doc.task_id && task.brief === doc.brief);
        if (index < 0) { status("This task is no longer in the current brief. Record the follow-up under a current task."); return; }
        $("dot-work-task").value = String(index); $("dot-work-reply").value = result.id;
        $("dot-work-kind").value = "review"; $("dot-work-title").value = ("Re: " + doc.title).slice(0, 160);
        $("dot-work-message").focus();
      });
      box.append(reply);
    }
    const showError = error => {
      if ([401,403].includes(error.status || error.refusal?.status)) {
        reset(); $("admin-message").textContent = "Work-log access changed. Reconnect to check your current permissions."; return;
      }
      if (permitted()) status(error.message || "The operation did not finish. Refresh before retrying.");
    };
    async function connectionChanged() {
      reset(); if (!permitted()) return;
      $("dot-work").hidden = false; $("dot-work-day").value = new Date().toISOString().slice(0, 10);
      const mine = epoch;
      try { await briefs(mine); if (mine === epoch && permitted()) await list(); }
      catch (error) { if (mine === epoch) showError(error); }
    }
    $("dot-work-refresh").addEventListener("click", () => list().catch(showError));
    $("dot-work-older").addEventListener("click", () => shown && list(shown.page + 1, shown).catch(showError));
    $("dot-work-newer").addEventListener("click", () => shown && list(Math.max(1, shown.page - 1), shown).catch(showError));
    $("dot-work-new").addEventListener("click", () => {
      if (saving) return;
      pending = null; $("dot-work-reply").value = ""; $("dot-work-message").value = "";
      $("dot-work-files").value = ""; status("A new submission will use a new request identity.");
    });
    $("dot-work-form").addEventListener("submit", async event => {
      event.preventDefault(); if (saving || !permitted()) return;
      const mine = epoch; let confirmedId = ""; saving = true; $("dot-work-submit").disabled = true;
      try {
        const task = tasks[Number($("dot-work-task").value)];
        if (!task) throw Error("Choose a current task.");
        const files = [...$("dot-work-files").files];
        if (files.length > 16 || files.some(file => file.size > 65536) || files.reduce((sum,file) => sum+file.size,0) > 262144)
          throw Error("Use at most 16 files, 64 KiB per file and 256 KiB total.");
        const attachments = [];
        for (const file of files) {
          const bytes = await file.arrayBuffer();
          if (mine !== epoch || !permitted()) return;
          attachments.push({name:file.name,content:new TextDecoder("utf-8", {fatal:true,ignoreBOM:true}).decode(bytes)});
        }
        if (mine !== epoch || !permitted()) return;
        const fields = {brief:task.brief, brief_revision:task.revision, task_id:task.id,
          kind:$("dot-work-kind").value, title:$("dot-work-title").value, message:$("dot-work-message").value,
          links:$("dot-work-links").value.split(/\r?\n/).map(value => value.trim()).filter(Boolean), files:attachments,
          reply_to:$("dot-work-reply").value};
        const fingerprint = JSON.stringify(fields);
        if (pending && pending.fingerprint !== fingerprint) throw Error("The earlier submission may have saved. Inspect the reports, then choose New report before submitting changed content.");
        if (!pending) pending = {fingerprint, request_id:crypto.randomUUID()};
        const payload = {record_type:"service_staff_work_request/v1",request_id:pending.request_id,...fields};
        if (new TextEncoder().encode(JSON.stringify(payload)).byteLength > current().requestBytes) {
          pending = null;
          throw Error("The encoded report exceeds this host's request limit. Use smaller files or split the report.");
        }
        status("Saving report…");
        const result = await request(endpoint, payload);
        if (mine !== epoch || !permitted()) return;
        if (result.record_type !== "service_staff_work_result/v1" || result.committed !== true || result.promotes_intelligence !== false)
          throw Error("No confirmation was returned. Keep this request identity and inspect saved reports.");
        confirmedId = result.id;
        pending = null; status((result.repeated ? "Existing report confirmed: " : "Report saved: ") + result.id + ". Files remain private and unreviewed.");
        for (const id of ["dot-work-title","dot-work-message","dot-work-links","dot-work-files","dot-work-reply"]) $(id).value = "";
        $("dot-work-day").value = new Date().toISOString().slice(0, 10);
        await list(); await detail(result.id);
      } catch (error) {
        if (mine === epoch) {
          if (confirmedId && ![401,403].includes(error.status || error.refusal?.status)) status("Report saved: " + confirmedId + ". The view could not refresh. Use Refresh reports; do not resubmit.");
          else showError(error);
        }
      }
      finally { if (mine === epoch) { saving = false; $("dot-work-submit").disabled = !permitted() || !tasks.length; } }
    });
    return {reset, connectionChanged};
  }
  return {create};
})();
