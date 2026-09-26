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
