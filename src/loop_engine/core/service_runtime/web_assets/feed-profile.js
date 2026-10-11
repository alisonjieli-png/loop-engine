/* Customer-owned reading profiles. Values stay in this page until its bounded export request. */
const form = document.querySelector("#feed-profile-form");

if (form) {
  const status = document.querySelector("#feed-profile-status");
  const downloads = document.querySelector("#feed-profile-downloads");
  const submit = form.querySelector('[type="submit"]');
  const encoder = new TextEncoder();
  let revision = 0;
  let pending = null;
  let urls = [];

  function clearDownloads() {
    for (const url of urls) URL.revokeObjectURL(url);
    urls = [];
    downloads.replaceChildren();
    downloads.hidden = true;
  }

  function changed() {
    revision += 1;
    if (pending) pending.abort();
    pending = null;
    submit.disabled = false;
    clearDownloads();
    status.textContent = "Build a profile with these selections, then save both files in a folder for this agent.";
  }

  async function readBounded(response) {
    if (!response.ok || !response.body) throw new Error("response");
    const reader = response.body.getReader();
    const chunks = [];
    let size = 0;
    try {
      while (true) {
        const next = await reader.read();
        if (next.done) break;
        size += next.value.byteLength;
        if (size > 147456) throw new Error("response_size");
        chunks.push(next.value);
      }
    } catch (error) {
      await reader.cancel();
      throw error;
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
    return JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(body));
  }

  async function exactFiles(result, label) {
    if (result?.record_type !== "agent_feed_profile_export/v1" || result.hosted_settings_saved !== false ||
        result.scheduled !== false || result.profile?.record_type !== "agent_feed_reading_profile/v2" ||
        result.profile.request?.agent_label !== label || result.profile.source_directory?.sha256 !== form.dataset.directoryDigest ||
        !Array.isArray(result.files) || result.files.length !== 2) throw new Error("contract");
    const checked = [];
    for (const [index, path] of ["profile.json", "READING.md"].entries()) {
      const file = result.files[index];
      const media = index === 0 ? "application/json" : "text/markdown";
      if (file.path !== path || file.media_type !== media || typeof file.content !== "string") throw new Error("files");
      const body = encoder.encode(file.content);
      if (body.length !== file.size_bytes || body.length > 65536) throw new Error("size");
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", body)),
        value => value.toString(16).padStart(2, "0")).join("");
      if (digest !== file.sha256) throw new Error("digest");
      checked.push({path, body, media});
    }
    return checked;
  }

  form.addEventListener("input", changed);
  form.addEventListener("reset", changed);
  window.addEventListener("pagehide", () => { if (pending) pending.abort(); clearDownloads(); });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    changed();
    const thisRevision = revision;
    const values = new FormData(form);
    const label = String(values.get("agent_label") || "").trim();
    const request = {record_type: "agent_feed_profile_export_request/v1", directory_digest: form.dataset.directoryDigest,
      agent_label: label, collection_ids: values.getAll("collection_ids"), topics: [],
      source_ids: values.getAll("source_ids"), excluded_source_ids: values.getAll("excluded_source_ids"),
      report_format: values.get("report_format"), requested_poll_interval_minutes: Number(values.get("requested_poll_interval_minutes"))};
    if (!request.collection_ids.length && !request.source_ids.length) {
      status.textContent = "Choose at least one collection or individual source, then build the profile.";
      return;
    }
    const controller = new AbortController();
    pending = controller;
    const deadline = setTimeout(() => controller.abort(), 15000);
    submit.disabled = true;
    status.textContent = "Checking the sources and preparing your two files…";
    try {
      const response = await fetch("/api/v1/feeds/profile", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify(request), credentials: "omit", cache: "no-store", redirect: "error", signal: controller.signal});
      if (response.status === 400) throw new Error("selection");
      const envelope = await readBounded(response);
      const result = envelope.result;
      const files = await exactFiles(result, label);
      if (thisRevision !== revision) return;
      for (const file of files) {
        const url = URL.createObjectURL(new Blob([file.body], {type: file.media}));
        urls.push(url);
        const link = document.createElement("a");
        link.className = "button secondary";
        link.href = url;
        link.download = file.path;
        link.textContent = "Download " + file.path;
        downloads.append(link);
      }
      downloads.hidden = false;
      const stale = result.profile.freshness.source_documentation_status === "stale";
      const names = result.profile.sources.map(source => source.name).join(", ");
      const count = result.profile.coverage.active_source_count;
      status.textContent = `${label}: ${count} ${count === 1 ? "source" : "sources"}. ${names}. ` +
        "Save both files in this agent’s own folder. Your harness configures the requested reading interval. " +
        (stale ? "Source documentation needs a fresh review before current claims." : "Each file records the source documentation date.");
    } catch (error) {
      if (thisRevision !== revision) return;
      clearDownloads();
      status.textContent = error.message === "selection"
        ? "Check your label and source selections. If a source was both added and left out, choose one. Reload this page if the source directory changed."
        : "The profile could not be prepared. Your selections are still here. Try building it again.";
    } finally {
      clearTimeout(deadline);
      if (thisRevision === revision) { pending = null; submit.disabled = false; }
    }
  });
}
