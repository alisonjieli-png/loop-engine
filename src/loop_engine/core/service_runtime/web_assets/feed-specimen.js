/* One anonymous, bounded read of the existing public catalogue feed. No account, storage or model access. */
export const MAXIMUM_FEED_BYTES = 32768;
export const READ_TIMEOUT_MS = 10000;
const FEED_PATH = "/feeds/catalogue.json";
const RECORD_TYPE = "catalogue_feed_snapshot/v1";
const FEED_VERSION = "https://jsonfeed.org/version/1.1";
const RECORD_FIELDS = ["record_type","notice_id","release_id","content_digest","catalogue_state_revision",
  "state_changed_at","packages","distinct_files","release_changes","coverage","release_changes_basis",
  "upstream_runtime_verification","limitation"];
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const exactFields = (value, fields) => object(value) && Object.keys(value).length === fields.length
  && fields.every(field => Object.hasOwn(value, field));
const count = value => Number.isSafeInteger(value) && value >= 0;
const words = value => typeof value === "string" && value.length > 0 && value.length <= 4096;
const digest = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const number = value => value.toLocaleString("en-US");

export function summaryText(record) {
  const changes = record.release_changes;
  return `${number(record.packages)} packages and ${number(record.distinct_files)} distinct files are in the served catalogue. `
    + `The release's original publication added ${number(changes.added)}, changed ${number(changes.changed)} and withdrew ${number(changes.withdrawn)} packages. `
    + "Later state changes can also reflect rollback or withdrawal. These are catalogue counts, not counts of independent capabilities or proven outcomes.";
}

export function validateFeed(feed, canonicalOrigin) {
  const origin = new URL(canonicalOrigin);
  if (origin.protocol !== "https:" || origin.origin !== canonicalOrigin) throw new Error("invalid_canonical_origin");
  if (!object(feed) || feed.version !== FEED_VERSION || feed.title !== "Baltor component updates"
      || !words(feed.description) || feed.home_page_url !== canonicalOrigin + "/feeds"
      || feed.feed_url !== canonicalOrigin + FEED_PATH || !Array.isArray(feed.items) || feed.items.length !== 1)
    throw new Error("invalid_feed_envelope");
  const item = feed.items[0], record = item?._baltor;
  if (!exactFields(record, RECORD_FIELDS) || record.record_type !== RECORD_TYPE || !digest(record.release_id)
      || !digest(record.content_digest) || !count(record.catalogue_state_revision) || !count(record.packages)
      || !count(record.distinct_files) || record.notice_id !== `${record.release_id}:${record.catalogue_state_revision}`
      || !exactFields(record.release_changes, ["added","changed","withdrawn"])
      || !Object.values(record.release_changes).every(count) || !words(record.limitation)
      || record.coverage !== "current_served_state_only"
      || record.release_changes_basis !== "original_release_publication_not_subsequent_state_transitions"
      || record.upstream_runtime_verification !== "not_assessed_by_this_feed"
      || typeof record.state_changed_at !== "string" || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(record.state_changed_at)
      || !Number.isFinite(Date.parse(record.state_changed_at))
      || new Date(record.state_changed_at).toISOString() !== record.state_changed_at.slice(0,-1) + ".000Z"
      || item.id !== record.notice_id || item.date_published !== record.state_changed_at
      || item.url !== canonicalOrigin + "/library" || item.title !== feed.title
      || item.content_text !== summaryText(record) + " " + record.limitation)
    throw new Error("invalid_catalogue_snapshot");
  return record;
}

export async function boundedText(response) {
  const refuse = async code => {
    if (response.body) await response.body.cancel().catch(() => {});
    throw new Error(code);
  };
  if (!response.ok || response.status !== 200 || response.redirected
      || response.headers.get("content-type")?.split(";",1)[0].trim() !== "application/feed+json")
    return refuse("feed_unavailable");
  const length = response.headers.get("content-length");
  if (length !== null && (!/^\d+$/.test(length) || Number(length) > MAXIMUM_FEED_BYTES))
    return refuse("feed_too_large");
  if (!response.body) throw new Error("feed_body_missing");
  const reader = response.body.getReader(), decoder = new TextDecoder("utf-8", {fatal:true, ignoreBOM:true});
  let size = 0, text = "";
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAXIMUM_FEED_BYTES) throw new Error("feed_too_large");
      text += decoder.decode(value, {stream:true});
    }
    return text + decoder.decode();
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  finally { reader.releaseLock(); }
}

const markdownText = value => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replace(/[\\`*_[\]]/g, character => "\\" + character);

export function snapshotMarkdown(feed, canonicalOrigin) {
  const record = validateFeed(feed, canonicalOrigin);
  return `# ${feed.title}\n\nState changed: ${record.state_changed_at}\n\n`
    + `Served release: \`${record.release_id}\`\n\nCatalogue state revision: ${record.catalogue_state_revision}\n\n`
    + `${summaryText(record)}\n\n${markdownText(feed.description)}\n\n${markdownText(record.limitation)}\n\n`
    + `[Inspect the library](${canonicalOrigin}/library). File downloads retain their normal account, permission and licence checks.\n`;
}

export function mountSpecimen(document, fetcher = globalThis.fetch) {
  const panel = document.getElementById("catalogue-specimen");
  if (!panel) return;
  const status = document.getElementById("catalogue-specimen-status");
  const content = document.getElementById("catalogue-specimen-content");
  const refresh = document.getElementById("catalogue-specimen-refresh");
  const jsonLink = document.getElementById("catalogue-snapshot-json");
  const markdownLink = document.getElementById("catalogue-snapshot-markdown");
  const canonicalOrigin = new URL(document.querySelector('link[rel="canonical"]').href).origin;
  let urls = [], reading = false, accepted = null;
  const clear = () => {
    content.hidden = true;
    for (const id of ["catalogue-specimen-summary","catalogue-specimen-packages","catalogue-specimen-files",
      "catalogue-specimen-changed","catalogue-specimen-read","catalogue-specimen-notice","catalogue-specimen-limit"])
      document.getElementById(id).textContent = "";
    for (const url of urls) URL.revokeObjectURL(url);
    urls = [];
    for (const link of [jsonLink, markdownLink]) { link.removeAttribute("href"); link.removeAttribute("download"); }
    delete panel.dataset.noticeId;
  };
  const put = (id, value) => { document.getElementById(id).textContent = String(value); };
  const read = async () => {
    if (reading) return;
    reading = true; refresh.disabled = true; clear(); panel.dataset.state = "loading";
    status.textContent = "Reading the public catalogue notice…";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), READ_TIMEOUT_MS);
    try {
      const response = await fetcher(FEED_PATH, {credentials:"omit", redirect:"error", cache:"no-store", signal:controller.signal});
      if (response.url !== new URL(FEED_PATH, document.location.origin).href) throw new Error("feed_path_changed");
      const raw = await boundedText(response), feed = JSON.parse(raw), record = validateFeed(feed, canonicalOrigin);
      const signature = JSON.stringify(RECORD_FIELDS.map(name => [name, name === "release_changes"
        ? [record.release_changes.added,record.release_changes.changed,record.release_changes.withdrawn] : record[name]]));
      if (accepted && (record.catalogue_state_revision < accepted.revision
          || (record.catalogue_state_revision === accepted.revision && signature !== accepted.signature)))
        throw new Error("feed_state_moved_backwards");
      const bodies = [[jsonLink, raw, "application/feed+json", "json"],
        [markdownLink, snapshotMarkdown(feed, canonicalOrigin), "text/markdown", "md"]];
      for (const [link, body, media, extension] of bodies) {
        const url = URL.createObjectURL(new Blob([body], {type:media+";charset=utf-8"}));
        urls.push(url); link.href = url;
        link.download = `baltor-catalogue-${record.release_id.slice(0,12)}-${record.catalogue_state_revision}.${extension}`;
      }
      put("catalogue-specimen-summary", summaryText(record));
      put("catalogue-specimen-packages", number(record.packages));
      put("catalogue-specimen-files", number(record.distinct_files));
      put("catalogue-specimen-changed", record.state_changed_at);
      put("catalogue-specimen-read", new Date().toISOString());
      put("catalogue-specimen-notice", record.notice_id);
      put("catalogue-specimen-limit", record.limitation);
      panel.dataset.noticeId = record.notice_id; panel.dataset.state = "ready";
      accepted = {revision:record.catalogue_state_revision, signature};
      content.hidden = false; status.textContent = "Current catalogue notice read successfully.";
    } catch (_) {
      clear(); panel.dataset.state = "unavailable";
      status.textContent = "Current catalogue notice unavailable. This is not an empty catalogue. Try again or open a feed link below.";
    } finally { clearTimeout(timeout); controller.abort(); reading = false; refresh.disabled = false; }
  };
  refresh.addEventListener("click", read);
  read();
}

if (typeof document !== "undefined") mountSpecimen(document);
