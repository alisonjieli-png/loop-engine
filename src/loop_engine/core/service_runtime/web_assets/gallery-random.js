// Local selection from the gallery's checked public previews. No account or provider calls.
export function choosePreview(items, currentId, entropy) {
  if (!Number.isSafeInteger(entropy) || entropy < 0) throw new TypeError("Selection needs unsigned integer entropy.");
  if (!items.length) return null;
  const others = items.filter(item => item.id !== currentId);
  const pool = others.length ? others : items;
  return pool[entropy % pool.length];
}

export function exactPreview(items, id) {
  return items.find(item => item.id === id) || null;
}

export function requestedPreview(search) {
  const values = new URLSearchParams(search).getAll("asset");
  if (!values.length) return undefined;
  return values.length === 1 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(values[0]) && values[0].length <= 180
    ? values[0] : null;
}

function start() {
  const root = document.querySelector("[data-random-discovery]");
  const data = document.getElementById("random-preview-data");
  if (!root || !data) return;
  const payload = JSON.parse(data.textContent);
  if (payload.record_type !== "gallery_random_projection/v1") return;
  const items = payload.items;
  const card = root.querySelector("[data-asset-card]");
  const unavailable = root.querySelector("[data-asset-unavailable]");
  const status = document.querySelector("[data-selection-status]");
  const another = document.querySelector("[data-show-another]");
  let selected = null;
  const entropy = () => globalThis.crypto.getRandomValues(new Uint32Array(1))[0];
  const set = (name, value) => { root.querySelector(`[data-asset-${name}]`).textContent = value; };
  const stopMedia = () => {
    const previous = root.querySelector("audio, video");
    if (previous) { previous.pause(); previous.removeAttribute("src"); previous.load(); }
  };
  const show = (item, historyMode = null) => {
    if (!item || !card) {
      stopMedia();
      if (card) card.hidden = true;
      unavailable.hidden = false;
      status.textContent = items.length ? "The requested preview is unavailable. Choose another to continue."
        : "No public previews in this category.";
      selected = null;
      another.disabled = false;
      another.textContent = "Show another";
      return;
    }
    selected = item;
    another.disabled = items.length < 2;
    another.textContent = items.length < 2 ? "Only one preview available" : "Show another";
    unavailable.hidden = true;
    card.hidden = false;
    const media = document.createElement(item.kind === "image" ? "img" : item.kind === "video" ? "video" : "audio");
    if (item.kind === "image") {
      media.alt = item.title;
      media.width = item.width;
      media.height = item.height;
    } else {
      media.controls = true;
      media.preload = "none";
      media.setAttribute("aria-label", item.title);
    }
    media.src = item.url;
    const picture = root.querySelector("[data-asset-media]");
    media.addEventListener("error", () => {
      if (selected?.id !== item.id || media.parentElement !== picture) return;
      picture.replaceChildren(Object.assign(document.createElement("p"), {
        textContent: "This preview could not be loaded. Its details are below; you can choose another."
      }));
      status.textContent = "Preview unavailable. Choose another or review its source.";
      const download = root.querySelector("[data-asset-download]");
      download.hidden = true;
    });
    stopMedia();
    picture.replaceChildren(media);
    set("kind", `${item.kind === "music" ? "Music" : item.kind === "video" ? "Video" : "Image"} / public preview`);
    set("title", item.title);
    set("summary", item.summary);
    let shape = item.width ? `${item.width} × ${item.height} pixels` : "Audio";
    if (item.duration_seconds !== null) shape += ` · ${item.duration_seconds} seconds`;
    set("format", `${item.format} · ${(item.bytes / 1024).toFixed(1)} KB · ${shape}`);
    set("licence", item.preview_licence || "Not separately recorded");
    set("source-licence", item.source_licence);
    set("provenance", item.provenance);
    set("identity", item.source_identity);
    set("version", item.source_version);
    set("digest", item.sha256);
    const download = root.querySelector("[data-asset-download]");
    download.hidden = false;
    download.href = item.url;
    download.download = item.url.split("/").pop();
    root.querySelector("[data-asset-source]").href = item.source_page;
    root.querySelector("[data-asset-permalink]").href = `/random/${item.kind}?asset=${encodeURIComponent(item.id)}`;
    status.textContent = `${item.title}. ${items.length} public ${items.length === 1 ? "preview" : "previews"} in this selection.`;
    if (historyMode) {
      const url = new URL(location.href);
      url.search = new URLSearchParams({asset: item.id}).toString();
      history[historyMode](null, "", url.pathname + url.search);
    }
  };
  const loadAddress = () => {
    const requested = requestedPreview(location.search);
    show(requested === undefined ? choosePreview(items, null, entropy()) : exactPreview(items, requested),
      requested === undefined && items.length ? "replaceState" : null);
  };
  if (items.length) {
    another.hidden = false;
    another.addEventListener("click", () => show(choosePreview(items, selected?.id, entropy()), "pushState"));
  }
  addEventListener("popstate", loadAddress);
  loadAddress();
}

if (typeof document !== "undefined") start();
