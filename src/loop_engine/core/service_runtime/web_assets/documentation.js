"use strict";
/* The Documentation view. One versioned index, /assets/documentation-index.json, names every page, its section, title,
   one-line summary and address. This file draws that index as a grid of cards and, at a page address, fetches the page's
   built body and places it inside the site's one header and footer. It takes every address from the index and never builds
   one from a title, an identity or a file name.

   A body is rebuilt element by element from a short list of allowed elements and attributes. A body that holds anything
   else is refused whole and nothing from it is shown, so a changed build or a changed file cannot put markup on this page
   that the list does not name. The index is read only in the exact record version this file was written for; another
   version may rename a field or give one a different meaning, so it is refused and the page says so.

   The page script, service.js, chooses the view from the address. It calls show() whenever the Documentation view opens
   or its address changes, and this file calls show() once when it loads. A link inside this view moves through the site's
   own history, so a signed-in page keeps its sign-in, which lives only in the memory of the page. */
window.BaltorDocumentation = (() => {
  const INDEX_ADDRESS = "/assets/documentation-index.json", INDEX_VERSION = "website_documentation_index/v1";
  const HOME = "/docs", PAGE_PREFIX = "/docs/";
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
  const entries = () => index.sections.flatMap(section => section.pages.map(page => ({...page, section:section.title})));

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
    toc.open = matchMedia("(min-width: 1200px)").matches;
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
      $("docs-nav").replaceChildren(); $("docs-pager").replaceChildren(); $("docs-toc").hidden = true;
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
    if (page && path === drawnPage) { document.title = serviceName + " | " + $("docs-page-title").textContent; return; }
    try {
      await loadIndex();
    } catch (error) {
      if (ticket !== generation) return;
      $("docs-status").textContent = refusal(error);
      if (page) { $("docs-page-title").textContent = "Documentation"; $("docs-article").replaceChildren(element("p", refusal(error), "docs-note")); drawnPage = ""; }
      return;
    }
    if (ticket !== generation) return;
    if (!page) { if (!drawnIndex) drawIndex(); return; }
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

  return {show};
})();
if (document.body.dataset.page === "docs") window.BaltorDocumentation.show(location.pathname);
