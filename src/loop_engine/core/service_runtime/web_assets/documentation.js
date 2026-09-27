"use strict";
/* The Documentation view. One versioned index, /assets/documentation-index.json, names every page, its section, title,
   one-line summary and address. This file draws that index as a grid of cards and, at a page address, fetches the page's
   built body and places it inside the site's one header and footer. It takes every address from the index and never builds
   one from a title, an identity or a file name.

   A body is rebuilt element by element from a short list of allowed elements and attributes. A body that holds anything
   else is refused whole and nothing from it is shown, so a changed build or a changed file cannot put markup on this page
   that the list does not name. The index is read only in the exact record version this file was written for; another
   version may rename a field or give one a different meaning, so it is refused and the page says so.

   The documentation bar above the view names the sections of the index as tabs, each opening the first page of its section,
   and holds the search control. Search reads the same index and the same rebuilt bodies, so it finds only what a page would
   show; a body the rebuild refuses is found by its title and summary alone. Nothing typed into search leaves the page.

   The page script, service.js, chooses the view from the address. It calls show() whenever the Documentation view opens
   or its address changes, and this file calls show() once when it loads. A link inside this view moves through the site's
   own history, so a signed-in page keeps its sign-in without loading the page again. */
window.BaltorDocumentation = (() => {
  const INDEX_ADDRESS = "/assets/documentation-index.json", INDEX_VERSION = "website_documentation_index/v1";
  const HOME = "/docs", PAGE_PREFIX = "/docs/";
  /* The repository that holds each page's source, for the page's edit link. The path comes from the index and is checked
     against docs/guides/ by the index rule below before it is used. */
  const SOURCE_EDIT = "https://github.com/alisonjieli-png/loop-engine/edit/main/";
  const WIDE = "(min-width: 1240px)";
  /* The elements a built body may hold, each with the attributes it may carry, and the rule every attribute value must meet. */
  const ALLOWED = {H2:["id"], H3:["id"], H4:["id"], P:[], PRE:[], CODE:["class"], TABLE:[], THEAD:[], TBODY:[], TR:[], TH:[], TD:[],
    UL:[], OL:["start"], LI:[], STRONG:[], A:["href", "rel", "target"]};
  const VALUES = {id:/^[a-z0-9_-]+$/, class:/^language-[A-Za-z0-9+-]+$/, start:/^[1-9][0-9]{0,3}$/,
    href:/^(?:\/(?!\/)[^\s"'<>\\]*|#[a-z0-9_-]+|https:\/\/[^\s"'<>\\]+)$/, rel:/^noopener noreferrer$/, target:/^_blank$/};
  const $ = id => document.getElementById(id);
  const serviceName = document.title.split(" | ")[0];
  let index = null, loading = null, drawnIndex = false, drawnPage = "", generation = 0;

  class Refused extends Error {}
  const element = (tag, text = "", className = "") => { const item = document.createElement(tag); if (text) item.textContent = text; if (className) item.className = className; return item; };
  const link = (href, text, className = "") => { const item = element("a", text, className); item.href = href; return item; };
  const entries = () => index.sections.flatMap(section => section.pages.map(page => ({...page, section:section.title, sectionId:section.id})));

  const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const text = value => typeof value === "string" && value.length > 0 && value.length <= 200 && value.trim() === value && !/[\r\n\t]/.test(value);
  const identity = value => text(value) && /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/.test(value);
  const fields = (value, allowed, required) => object(value) && Object.keys(value).every(key => allowed.includes(key)) && required.every(key => Object.hasOwn(value, key));
  const validIndex = record => {
    if (!fields(record, ["record_type", "reviewed_at", "sections"], ["record_type", "reviewed_at", "sections"]) || record.record_type !== INDEX_VERSION) return false;
    if (!text(record.reviewed_at) || !/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(record.reviewed_at)) return false;
    const date = new Date(record.reviewed_at + "T00:00:00Z");
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== record.reviewed_at) return false;
    if (!Array.isArray(record.sections) || !record.sections.length || record.sections.length > 32) return false;
    const sections = new Set(), pages = new Set(), addresses = new Set(), paths = new Set();
    for (const section of record.sections) {
      if (!fields(section, ["id", "title", "pages"], ["id", "title", "pages"]) || !identity(section.id) || sections.has(section.id) || !text(section.title)) return false;
      sections.add(section.id);
      if (!Array.isArray(section.pages) || !section.pages.length || section.pages.length > 100) return false;
      for (const page of section.pages) {
        if (!fields(page, ["id", "title", "summary", "address", "body", "repository_path", "aliases"], ["id", "title", "summary", "address"]) || !identity(page.id) || pages.has(page.id) || !text(page.title) || !text(page.summary) || page.summary.length > 100) return false;
        pages.add(page.id);
        if (Object.hasOwn(page, "body")) {
          if (page.address !== "/docs/" + page.id || page.body !== "/assets/docs/" + page.id + ".html" || !page.repository_path) return false;
        } else if (page.address !== "/setup") return false;
        if (Object.hasOwn(page, "repository_path")) {
          if (!text(page.repository_path) || !/^docs\/guides\/[a-z0-9-]+\.md$/.test(page.repository_path) || paths.has(page.repository_path)) return false;
          paths.add(page.repository_path);
        }
        const aliases = Object.hasOwn(page, "aliases") ? page.aliases : [];
        if (!Array.isArray(aliases) || aliases.length > 10 || !aliases.every(alias => text(alias) && /^\/docs\/[a-z][a-z0-9-]*$/.test(alias))) return false;
        for (const address of [page.address, ...aliases]) { if (addresses.has(address)) return false; addresses.add(address); }
      }
    }
    return true;
  };

  const loadIndex = () => loading || (loading = fetch(INDEX_ADDRESS, {cache:"no-store", headers:{Accept:"application/json"}}).then(async response => {
    if (!response.ok) throw new Error("the documentation list answered " + response.status);
    const record = await response.json();
    if (!validIndex(record)) throw new Refused("index contract");
    index = record;
    return record;
  }).catch(error => { loading = null; throw error; }));

  const refusal = error => error instanceof Refused
    ? "This service answered with a documentation list this page was not written for, so nothing from it is shown. Reload the page after the next release."
    : "The documentation list could not be loaded. Check your connection and reload the page.";

  /* The tabs of the documentation bar: the overview, then one tab for each section of the index, opening the first page of the
     section that this view shows. The tab of the section being read is marked, and the scroll region brings it into view. */
  const drawTabs = current => {
    const tabs = $("docs-tabs"), overview = link(HOME, "Overview");
    overview.dataset.docsTab = "overview";
    const items = [overview, ...(index ? index.sections : []).map(section => {
      const first = section.pages.find(page => page.body) || section.pages[0], tab = link(first.address, section.title);
      tab.dataset.docsTab = section.id;
      return tab;
    })];
    for (const tab of items) if (tab.dataset.docsTab === current) tab.setAttribute("aria-current", current === "overview" ? "page" : "true");
    tabs.replaceChildren(...items);
    const active = tabs.querySelector("[aria-current]");
    if (active) tabs.scrollLeft = Math.max(0, active.offsetLeft - (tabs.clientWidth - active.offsetWidth) / 2);
  };

  /* The index: one card for each page, in the order the index gives, the section named on the card. */
  const drawIndex = () => {
    const cards = $("docs-cards");
    cards.replaceChildren(...entries().map((entry, position) => {
      const card = element("li", "", "docs-card" + (position === 0 ? " is-first" : ""));
      card.dataset.docsPage = entry.id;
      const title = element("h3", "", "docs-card-title");
      title.append(link(entry.address, entry.title));
      card.append(element("p", entry.section, "docs-card-section"), title, element("p", entry.summary, "docs-card-summary"));
      return card;
    }));
    $("docs-status").textContent = "";
    drawnIndex = true;
  };

  /* A body is copied node by node. Text is copied as text; an element is copied only when the list names it, with only the
     attributes the list names, each checked against its rule. Anything else refuses the whole body. */
  const rebuild = (source, target) => {
    for (const node of source.childNodes) {
      if (node.nodeType === Node.TEXT_NODE) { target.append(document.createTextNode(node.data)); continue; }
      if (node.nodeType !== Node.ELEMENT_NODE || !Object.hasOwn(ALLOWED, node.tagName)) throw new Refused("element " + node.nodeName);
      const copy = document.createElement(node.tagName.toLowerCase());
      for (const attribute of node.attributes) {
        if (!ALLOWED[node.tagName].includes(attribute.name) || !VALUES[attribute.name].test(attribute.value)) throw new Refused("attribute " + attribute.name);
        copy.setAttribute(attribute.name, attribute.value);
      }
      const address = copy.getAttribute("href") || "";
      if (copy.tagName === "A" && address.startsWith("https://") !== (copy.getAttribute("target") === "_blank" && copy.getAttribute("rel") === "noopener noreferrer")) throw new Refused("link target");
      rebuild(node, copy);
      if (copy.tagName === "TABLE") {
        const frame = element("div", "", "docs-table"); frame.tabIndex = 0; frame.setAttribute("role", "region"); frame.setAttribute("aria-label", "Table");
        frame.append(copy); target.append(frame);
      } else {
        if (copy.tagName === "PRE") { copy.tabIndex = 0; copy.setAttribute("aria-label", "Example"); }
        target.append(copy);
      }
    }
  };

  const drawNavigation = current => {
    const nav = $("docs-nav");
    nav.replaceChildren(...index.sections.map(section => {
      const group = element("div", "", "docs-nav-group");
      const list = element("ul");
      for (const entry of section.pages) {
        const item = element("li"), anchor = link(entry.address, entry.title);
        if (entry.address === current.address) anchor.setAttribute("aria-current", "page");
        item.append(anchor); list.append(item);
      }
      group.append(element("p", section.title, "docs-nav-section"), list);
      return group;
    }));
    const all = entries(), position = all.findIndex(entry => entry.address === current.address);
    const pager = $("docs-pager");
    pager.replaceChildren(...[[all[position - 1], "Previous", "docs-pager-previous"], [all[position + 1], "Next", "docs-pager-next"]]
      .filter(([entry]) => entry).map(([entry, word, className]) => {
        const anchor = link(entry.address, "", className);
        anchor.append(element("span", word, "docs-pager-word"), element("span", entry.title, "docs-pager-title"));
        return anchor;
      }));
  };

  const drawContents = article => {
    const headings = [...article.querySelectorAll("h2[id]")], toc = $("docs-toc");
    toc.hidden = headings.length < 2;
    const list = element("ul");
    for (const heading of headings) { const item = element("li"); item.append(link("#" + heading.id, heading.textContent)); list.append(item); }
    $("docs-toc-list").replaceChildren(list);
    toc.open = matchMedia(WIDE).matches;
  };

  /* Each example gets a bar with its language, when the body names one, and a control that copies the example's text. The
     example itself is the rebuilt element, unchanged. */
  const frameExamples = article => {
    for (const pre of article.querySelectorAll("pre")) {
      const language = (pre.querySelector("code[class^='language-']")?.className || "").slice("language-".length);
      const frame = element("div", "", "docs-code-frame"), bar = element("div", "", "docs-code-bar");
      const copy = element("button", "Copy", "docs-code-copy");
      copy.type = "button";
      copy.setAttribute("aria-label", "Copy this example");
      copy.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(pre.textContent); copy.textContent = "Copied"; }
        catch (_) { copy.textContent = "Select the text to copy"; }
        setTimeout(() => { copy.textContent = "Copy"; }, 1600);
      });
      bar.append(element("span", language || "Example", "docs-code-label"), copy);
      pre.replaceWith(frame);
      frame.append(bar, pre);
    }
  };

  const settleOnTarget = () => {
    const target = location.hash ? document.getElementById(decodeURIComponent(location.hash.slice(1))) : null;
    if (target) target.scrollIntoView();
  };

  const drawPage = async (path, ticket) => {
    const entry = entries().find(item => item.body && (item.address === path || item.aliases?.includes(path)));
    const article = $("docs-article");
    if (!entry) {
      $("docs-page-section").textContent = ""; $("docs-page-title").textContent = "This page is not in the documentation";
      $("docs-page-summary").textContent = "The address may be mistyped or older than the current list.";
      $("docs-nav").replaceChildren(); $("docs-pager").replaceChildren(); $("docs-toc").hidden = true; $("docs-page-meta").hidden = true;
      drawTabs("");
      const note = element("p", "", "docs-note"); note.append("Open the ", link(HOME, "documentation list"), " to find the page you need.");
      article.replaceChildren(note);
      drawnPage = path;
      return;
    }
    document.title = serviceName + " | " + entry.title;
    $("docs-page-section").textContent = entry.section;
    $("docs-page-title").textContent = entry.title;
    $("docs-page-summary").textContent = entry.summary;
    drawNavigation(entry);
    drawTabs(entry.sectionId);
    $("docs-page-reviewed").textContent = "Documentation reviewed " + new Date(index.reviewed_at + "T00:00:00Z")
      .toLocaleDateString("en-US", {year:"numeric", month:"long", day:"numeric", timeZone:"UTC"});
    $("docs-page-source").href = SOURCE_EDIT + entry.repository_path;
    $("docs-page-meta").hidden = false;
    article.setAttribute("aria-busy", "true");
    article.replaceChildren(element("p", "Loading this page.", "docs-note"));
    $("docs-toc").hidden = true;
    try {
      const response = await fetch(entry.body, {cache:"no-store", headers:{Accept:"text/html"}});
      if (!response.ok || !(response.headers.get("content-type") || "").startsWith("text/html")) throw new Error("the page answered " + response.status);
      const parsed = new DOMParser().parseFromString(await response.text(), "text/html");
      if (parsed.head.childNodes.length) throw new Refused("unexpected document head");
      const body = document.createDocumentFragment();
      rebuild(parsed.body, body);
      if (ticket !== generation) return;
      article.replaceChildren(body);
      frameExamples(article);
      drawContents(article);
      drawnPage = path;
      settleOnTarget();
    } catch (error) {
      if (ticket !== generation) return;
      const note = element("p", error instanceof Refused
        ? "This page holds content this site does not show, so it was not shown. "
        : "This page could not be loaded. ", "docs-note");
      note.dataset.docsRefused = error instanceof Refused ? "body" : "load";
      note.append("Open the ", link(HOME, "documentation list"), " or reload the page.");
      article.replaceChildren(note);
    } finally {
      if (ticket === generation) article.removeAttribute("aria-busy");
    }
  };

  const show = async path => {
    const ticket = ++generation, page = path.startsWith(PAGE_PREFIX);
    $("docs-index").hidden = page; $("docs-page").hidden = !page;
    if (page && path === drawnPage) {
      drawTabs(entries().find(entry => entry.body && (entry.address === path || entry.aliases?.includes(path)))?.sectionId || "");
      document.title = serviceName + " | " + $("docs-page-title").textContent;
      return;
    }
    try {
      await loadIndex();
    } catch (error) {
      if (ticket !== generation) return;
      $("docs-status").textContent = refusal(error);
      if (page) { $("docs-page-title").textContent = "Documentation"; $("docs-article").replaceChildren(element("p", refusal(error), "docs-note")); drawnPage = ""; }
      return;
    }
    if (ticket !== generation) return;
    if (!page) { drawTabs("overview"); if (!drawnIndex) drawIndex(); return; }
    await drawPage(path, ticket);
  };

  /* A link inside this view to another address of this site moves through the history that service.js keeps, which opens the
     right view and calls show() for a documentation address. A link to another site, and a link to a part of this page,
     behave as links do. */
  document.querySelector('[data-view="docs"]').addEventListener("click", event => {
    const anchor = event.target.closest("a[href]");
    if (!anchor || anchor.dataset.page || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const address = anchor.getAttribute("href");
    if (!address.startsWith("/") || address.startsWith("//")) return;
    event.preventDefault();
    history.pushState({}, "", address);
    dispatchEvent(new PopStateEvent("popstate"));
    $("main").focus({preventScroll:true});
    if (location.hash) settleOnTarget(); else scrollTo(0, 0);
  });

  /* Search. The dialog lists every page until something is typed. A page matches when each word typed is in its title, summary,
     section or text; the title counts most, then the summary, a heading and the text. The text of a page is read once, the first
     time search opens, through the same rebuild as a page that is shown. Enter opens the first match, the arrow keys move
     between matches, and Escape closes the dialog and returns to the control that opened it. */
  const dialog = $("docs-search"), input = $("docs-search-input"), results = $("docs-search-results"), status = $("docs-search-status");
  const texts = new Map();
  let reading = null, opener = null, leaving = false;
  const readTexts = () => reading || (reading = Promise.all(entries().filter(entry => entry.body).map(async entry => {
    try {
      const response = await fetch(entry.body, {cache:"no-store", headers:{Accept:"text/html"}});
      if (!response.ok || !(response.headers.get("content-type") || "").startsWith("text/html")) return;
      const parsed = new DOMParser().parseFromString(await response.text(), "text/html");
      if (parsed.head.childNodes.length) return;
      const body = document.createDocumentFragment();
      rebuild(parsed.body, body);
      texts.set(entry.id, {text:body.textContent.replace(/\s+/g, " ").trim(),
        headings:[...body.querySelectorAll("h2[id], h3[id]")].map(heading => ({id:heading.id, text:heading.textContent.trim()}))});
    } catch (_) { /* A page that does not load, or that the rebuild refuses, is found by its title and summary alone. */ }
  })).then(() => { if (dialog.open) search(); }));
  const snippet = (text, word) => {
    const at = text.toLowerCase().indexOf(word);
    if (at < 0) return "";
    const start = Math.max(0, text.lastIndexOf(" ", Math.max(0, at - 60)) + 1), end = text.indexOf(" ", Math.min(text.length, at + 110));
    return (start > 0 ? "…" : "") + text.slice(start, end < 0 ? text.length : end) + (end < 0 ? "" : "…");
  };
  const match = (entry, words) => {
    const known = texts.get(entry.id), body = known ? known.text.toLowerCase() : "";
    let total = 0, heading = null;
    for (const word of words) {
      let found = (entry.title.toLowerCase().includes(word) ? 8 : 0) + (entry.summary.toLowerCase().includes(word) ? 4 : 0)
        + (entry.section.toLowerCase().includes(word) ? 2 : 0);
      for (const item of known ? known.headings : []) if (item.text.toLowerCase().includes(word)) { found += 3; heading = heading || item; }
      if (known) found += Math.min(body.split(word).length - 1, 6);
      if (!found) return null;
      total += found;
    }
    return {entry, total, heading, text:known ? snippet(known.text, words[0]) : ""};
  };
  const result = ({entry, heading, text}) => {
    const item = element("li"), anchor = link(entry.address + (heading ? "#" + heading.id : ""), "");
    anchor.append(element("span", entry.section + (heading ? " / " + heading.text : ""), "docs-search-crumb"),
      element("span", entry.title, "docs-search-title"), element("span", text || entry.summary, "docs-search-snippet"));
    item.append(anchor);
    return item;
  };
  const search = () => {
    if (!index) return;
    const words = input.value.toLowerCase().split(/\s+/).filter(Boolean), pages = entries();
    const found = words.length ? pages.map(entry => match(entry, words)).filter(Boolean).sort((one, two) => two.total - one.total).slice(0, 8)
      : pages.map(entry => ({entry, heading:null, text:""}));
    results.replaceChildren(...found.map(result));
    const partial = texts.size === 0 && reading !== null;
    status.textContent = !words.length ? "Every page. Type to search the text of each page."
      : !found.length ? (partial ? "No title or summary matches yet. The text of each page is still loading." : "No pages match. Try fewer words.")
      : (found.length === 1 ? "One page matches." : found.length + " pages match.") + (partial ? " Titles only while the pages load." : "");
  };
  const openSearch = async () => {
    if (dialog.open) { input.focus(); return; }
    opener = document.activeElement; leaving = false;
    input.value = "";
    results.replaceChildren();
    status.textContent = "Loading the documentation list.";
    dialog.showModal();
    input.focus();
    try { await loadIndex(); } catch (error) { status.textContent = refusal(error); return; }
    search();
    readTexts();
  };
  const move = (from, step) => {
    const anchors = [...results.querySelectorAll("a")], at = anchors.indexOf(from) + step;
    if (at < 0) input.focus(); else if (anchors[at]) anchors[at].focus();
  };
  $("docs-search-open").addEventListener("click", openSearch);
  $("docs-search-close").addEventListener("click", () => dialog.close());
  input.addEventListener("input", search);
  input.addEventListener("keydown", event => {
    if (event.key === "ArrowDown") { event.preventDefault(); move(null, 1); }
    else if (event.key === "Enter") { event.preventDefault(); results.querySelector("a")?.click(); }
  });
  results.addEventListener("keydown", event => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); move(event.target.closest("a"), event.key === "ArrowDown" ? 1 : -1); }
  });
  /* A chosen match closes the dialog; the view's own link handler below then opens the page, so focus goes to the page. */
  results.addEventListener("click", event => { if (event.target.closest("a")) { leaving = true; dialog.close(); } });
  dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener("close", () => { if (!leaving && opener && opener.isConnected) opener.focus(); opener = null; });
  addEventListener("keydown", event => {
    if (document.body.dataset.page !== "docs" || dialog.open || event.defaultPrevented || event.altKey) return;
    const typing = event.target.closest?.("input, textarea, select, [contenteditable]");
    if (((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") || (event.key === "/" && !typing && !event.ctrlKey && !event.metaKey)) {
      event.preventDefault();
      openSearch();
    }
  });

  return {show};
})();
if (document.body.dataset.page === "docs") window.BaltorDocumentation.show(location.pathname);
