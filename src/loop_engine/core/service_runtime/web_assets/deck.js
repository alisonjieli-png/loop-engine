/* The deck at /deck: one slide at a time, moved by the arrow keys, Page Up and Page Down, Home and End, a swipe, the
   controls or a link to a slide's address such as /deck#live. O opens the overview of every slide and F presents in
   full screen. Without this script the page shows every slide one after another, so nothing depends on it.
   It writes nothing inside a slide: the position and the overview sit outside the slides. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const deck = document.querySelector("[data-view=deck]"), stage = $("deck-stage");
  if (!deck || !stage) return;
  const slides = [...stage.querySelectorAll("[data-slide]")];
  if (!slides.length) return;
  const root = document.documentElement, header = document.querySelector("header"), controls = $("deck-controls");
  const position = $("deck-position"), status = $("deck-status"), progress = $("deck-progress-bar"), previous = $("deck-previous"), next = $("deck-next");
  const overview = $("deck-overview"), overviewList = $("deck-overview-list"), overviewButton = $("deck-overview-button");
  const present = $("deck-present");
  const titleOf = slide => (slide.querySelector("h1, h2")?.textContent || "").trim();
  const eyebrowOf = slide => (slide.querySelector(".deck-eyebrow")?.textContent || "").trim();
  let current = 0;

  /* On a hostname whose root address shows this page, such as deck.baltor.ai, the service names that address in the
     page. Links to the homepage then go to the canonical hostname, as the rest of the website does. */
  const rootAddress = document.querySelector('meta[name="baltor-root-address"]')?.getAttribute("content") || "/";
  if (rootAddress !== "/") {
    const canonical = document.querySelector('link[rel="canonical"]')?.getAttribute("href");
    const origin = canonical ? new URL(canonical, location.href).origin : "";
    if (origin && origin !== location.origin)
      document.querySelectorAll('a[href="/"], a[href^="/#"]').forEach(link => link.setAttribute("href", origin + link.getAttribute("href")));
  }

  root.classList.add("deck-on");
  controls.hidden = false;
  const measureHeader = () => root.style.setProperty("--deck-header", (header ? Math.round(header.getBoundingClientRect().height) : 0) + "px");
  measureHeader();
  addEventListener("resize", measureHeader);

  const slideFromHash = () => {
    const id = decodeURIComponent(location.hash.slice(1));
    return id ? slides.findIndex(slide => slide.id === id) : -1;
  };
  const writeAddress = () => {
    const address = current === 0 ? location.pathname + location.search : "#" + slides[current].id;
    if ((current === 0 ? "" : "#" + slides[current].id) !== location.hash) history.replaceState(history.state, "", address);
  };
  const show = (index, {direction = 0} = {}) => {
    const target = Math.max(0, Math.min(slides.length - 1, index));
    const moved = target !== current;
    current = target;
    slides.forEach((slide, place) => {
      slide.hidden = place !== current;
      slide.classList.toggle("is-current", place === current);
    });
    const slide = slides[current];
    if (moved && direction) {
      slide.style.setProperty("--deck-shift", (direction > 0 ? 24 : -24) + "px");
      slide.classList.remove("is-entering"); void slide.offsetWidth; slide.classList.add("is-entering");
    }
    position.textContent = (current + 1) + " / " + slides.length;
    status.textContent = "Slide " + (current + 1) + " of " + slides.length + ": " + titleOf(slide);
    progress.style.width = ((current + 1) / slides.length * 100) + "%";
    previous.disabled = current === 0;
    next.disabled = current === slides.length - 1;
    overviewList.querySelectorAll("a").forEach((link, place) => link.setAttribute("aria-current", String(place === current)));
    writeAddress();
    /* A long slide on a small screen scrolls with the page; the next slide starts at its own top. */
    if (moved && slide.getBoundingClientRect().top < (header ? header.getBoundingClientRect().bottom : 0)) slide.scrollIntoView({block: "start"});
  };
  const go = step => show(current + step, {direction: step});

  /* The overview: one card for each slide, written from the slide's own heading. */
  slides.forEach((slide, place) => {
    const item = document.createElement("li"), link = document.createElement("a");
    link.href = "#" + slide.id;
    const number = document.createElement("span"), eyebrow = document.createElement("span"), title = document.createElement("span");
    number.className = "deck-overview-number"; number.textContent = String(place + 1).padStart(2, "0");
    eyebrow.className = "deck-overview-eyebrow"; eyebrow.textContent = eyebrowOf(slide) || "Baltor";
    title.className = "deck-overview-title"; title.textContent = titleOf(slide);
    link.append(number, eyebrow, title);
    link.addEventListener("click", event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault(); closeOverview(false); show(place, {direction: place > current ? 1 : -1}); stage.focus({preventScroll: true});
    });
    item.append(link); overviewList.append(item);
  });
  stage.tabIndex = -1;
  const openOverview = () => {
    overview.hidden = false; overviewButton.setAttribute("aria-expanded", "true");
    (overviewList.querySelector('a[aria-current="true"]') || overviewList.querySelector("a"))?.focus();
  };
  function closeOverview(returnFocus = true) {
    if (overview.hidden) return;
    overview.hidden = true; overviewButton.setAttribute("aria-expanded", "false");
    if (returnFocus) overviewButton.focus();
  }
  const toggleOverview = () => (overview.hidden ? openOverview() : closeOverview());
  overviewButton.addEventListener("click", toggleOverview);
  $("deck-overview-close").addEventListener("click", () => closeOverview());

  /* Full screen, where the browser allows it. A phone browser that cannot put a page in full screen hides the control. */
  const canPresent = Boolean(document.fullscreenEnabled && deck.requestFullscreen);
  present.hidden = !canPresent;
  const togglePresent = () => {
    if (!canPresent) return;
    if (document.fullscreenElement) document.exitFullscreen?.(); else deck.requestFullscreen().catch(() => {});
  };
  present.addEventListener("click", togglePresent);
  document.addEventListener("fullscreenchange", () => {
    const on = document.fullscreenElement === deck;
    present.querySelector("span").textContent = on ? "Leave full screen" : "Present";
    present.setAttribute("aria-label", on ? "Leave full screen" : "Present in full screen");
    measureHeader();
  });
  present.setAttribute("aria-label", "Present in full screen");
  overviewButton.setAttribute("aria-label", "All slides");

  previous.addEventListener("click", () => go(-1));
  next.addEventListener("click", () => go(1));
  addEventListener("hashchange", () => { const index = slideFromHash(); if (index >= 0) { closeOverview(false); show(index); } });

  /* The keys. A key typed into a field, or pressed with a modifier, is left to the browser; Space on a link or a
     button presses it rather than moving the deck. */
  document.addEventListener("keydown", event => {
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    const target = event.target instanceof Element ? event.target : null;
    if (target?.closest("input, textarea, select, [contenteditable]")) return;
    if (!overview.hidden) { if (event.key === "Escape") { event.preventDefault(); closeOverview(); } return; }
    const pressable = target?.closest("a[href], button, summary");
    switch (event.key) {
      case "ArrowRight": case "PageDown": go(1); break;
      case "ArrowLeft": case "PageUp": go(-1); break;
      case " ": if (pressable) return; go(event.shiftKey ? -1 : 1); break;
      case "Home": show(0, {direction: -1}); break;
      case "End": show(slides.length - 1, {direction: 1}); break;
      case "o": case "O": openOverview(); break;
      case "f": case "F": if (!canPresent) return; togglePresent(); break;
      default: return;
    }
    event.preventDefault();
  });

  /* A swipe: a mostly sideways touch or pen movement of at least 56 pixels. An upward or downward movement stays a
     scroll, which the browser keeps because the slides allow only vertical panning. */
  let start = null;
  stage.addEventListener("pointerdown", event => {
    if (event.pointerType === "mouse" || !event.isPrimary) return;
    start = {x: event.clientX, y: event.clientY, id: event.pointerId};
  });
  stage.addEventListener("pointerup", event => {
    if (!start || event.pointerId !== start.id) return;
    const dx = event.clientX - start.x, dy = event.clientY - start.y;
    start = null;
    if (Math.abs(dx) >= 56 && Math.abs(dx) > Math.abs(dy) * 1.5) go(dx < 0 ? 1 : -1);
  });
  stage.addEventListener("pointercancel", () => { start = null; });

  /* The appearance control in the shared footer: the system's choice, light or dark, as on every other page. */
  const themes = ["system", "light", "dark"], themeButton = $("theme");
  let theme = root.dataset.theme || "system";
  themeButton?.addEventListener("click", () => {
    theme = themes[(themes.indexOf(theme) + 1) % themes.length];
    if (theme === "system") delete root.dataset.theme; else root.dataset.theme = theme;
    themeButton.textContent = "Appearance: " + theme;
  });

  const opened = slideFromHash();
  show(opened >= 0 ? opened : 0);
  if (opened > 0) deck.scrollIntoView({block: "start"});
})();
