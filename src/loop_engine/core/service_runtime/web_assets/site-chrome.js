"use strict";
/* The shared footer's behaviour, on every page that carries the shared header and footer: the one-page app, the pages the
   service renders on its own, the directory and the deck. September 26, 2026, from the owner's orange design.

   Each footer group is a disclosure (details and summary). The served markup holds every group open, so a page without this
   script shows every link. On a wide screen a group stays open and its heading reads as a plain label. At 860 pixels and below
   the groups start closed, so the footer on a phone is five headings a person opens one at a time. In the signed-in views the
   footer is compact (architecture.css): every group is held open there, because its few links must show.

   It changes no link, no address and no text, and it reads nothing from the service. */
(() => {
  const groups = [...document.querySelectorAll(".site-footer details.footer-group")];
  if (!groups.length) return;
  const narrow = matchMedia("(max-width: 860px)");
  const compact = () => document.body.matches(":has(main > :is([data-view=workspace],[data-view=account],[data-view=admin]):not([hidden]))");
  let applying = false;
  const apply = () => {
    applying = true;
    const hold = !narrow.matches || compact();
    for (const group of groups) {
      group.open = hold;
      const summary = group.querySelector("summary");
      /* A wide screen's heading is a label, not a control, so it leaves the keyboard order. */
      if (summary) { if (hold) summary.setAttribute("tabindex", "-1"); else summary.removeAttribute("tabindex"); }
    }
    applying = false;
  };
  for (const group of groups) group.addEventListener("toggle", () => {
    if (applying) return;
    if (!narrow.matches || compact()) group.open = true;
  });
  narrow.addEventListener("change", apply);
  /* The one-page app shows another view without loading a page; the view it shows decides the compact footer. */
  new MutationObserver(apply).observe(document.body, {attributes: true, attributeFilter: ["data-page"]});
  apply();
})();

/* A dedicated hostname can open a standalone page at its root, as redteam.baltor.ai does. Its Home and library-section
   links lead to the canonical homepage, using the same service-written metadata as service.js and deck.js. */
(() => {
  const rootAddress = document.querySelector('meta[name="baltor-root-address"]')?.getAttribute("content") || "/";
  if (rootAddress === "/") return;
  const canonical = document.querySelector('link[rel="canonical"]')?.getAttribute("href");
  if (!canonical) return;
  const origin = new URL(canonical, location.href).origin;
  if (origin === location.origin) return;
  document.querySelectorAll('a[href="/"], a[href^="/#"]').forEach(link => {
    link.setAttribute("href", origin + link.getAttribute("href"));
    delete link.dataset.page;
  });
})();

/* Where the visitor is, on a page the service renders on its own: the library, the model directory, the MCP directory, the
   deck and the others that carry this header and footer. The one-page app marks its own links (the ones with data-page), and
   no script marked these, so on the library page the header's Library link looked like any other. A header or footer link
   without data-page whose address is this very page, with no fragment, is marked as the current page, which the header and
   the footer show in ink and bold. It adds an attribute and changes no link, address or text. */
(() => {
  const trimmed = path => path.replace(/\/+$/, "") || "/";
  const here = trimmed(location.pathname);
  for (const link of document.querySelectorAll(".header nav a[href]:not([data-page]), .site-footer a[href]:not([data-page])")) {
    const address = new URL(link.getAttribute("href"), location.href);
    if (address.origin === location.origin && !address.hash && trimmed(address.pathname) === here) link.setAttribute("aria-current", "page");
  }
})();
