/* The guide pages and the gallery, October 9, 2026: copy buttons for code, and the gallery's kind filters.

   Without this script every page still works: code stays selectable text, each filter is a link to its kind's section,
   and "Show all" is a disclosure. With it, a copy button appears beside each code block and announces the copy, and a
   filter shows one kind in place and keeps the choice in the address as ?kind=, which the canonical address leaves out.
   Nothing here sends a request. */
(() => {
  "use strict";
  for (const button of document.querySelectorAll("[data-copy-code]")) {
    const block = button.parentElement.querySelector("pre"), status = button.parentElement.querySelector(".og-copy-status");
    if (!block) continue;
    button.hidden = false;
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(block.textContent);
        if (status) status.textContent = "Copied. No key included.";
      } catch (_) {
        const range = document.createRange(); range.selectNodeContents(block);
        const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
        if (status) status.textContent = "Copying is not available here. The text is selected; copy it with your keyboard.";
      }
    });
  }

  const filters = document.querySelector(".gl-filters");
  if (!filters) return;
  const chips = [...filters.querySelectorAll("[data-kind-filter]")];
  const sections = [...document.querySelectorAll(".gl-kind[data-kind]")];
  const count = document.getElementById("gallery-count");
  const kinds = new Set(sections.map(section => section.dataset.kind));
  const tiles = section => section.querySelectorAll(".gl-tile").length;
  function show(kind, remember) {
    const chosen = kinds.has(kind) ? kind : "";
    for (const chip of chips) chip.setAttribute("aria-current", String(chip.dataset.kindFilter === chosen));
    for (const section of sections) {
      section.hidden = Boolean(chosen) && section.dataset.kind !== chosen;
      const more = section.querySelector("details.gl-more");
      if (more) more.open = Boolean(chosen) && section.dataset.kind === chosen;
    }
    const shown = sections.filter(section => !section.hidden).reduce((total, section) => total + tiles(section), 0);
    const label = chosen ? chips.find(chip => chip.dataset.kindFilter === chosen).firstChild.textContent.trim() : "";
    if (count) count.textContent = chosen ? "Showing all " + shown + " " + label + "." : "Showing every kind. Choose one to see all of its files.";
    if (remember) {
      const address = new URL(location.href);
      if (chosen) address.searchParams.set("kind", chosen); else address.searchParams.delete("kind");
      address.hash = "";
      history.replaceState(null, "", address.pathname + address.search);
    }
  }
  for (const chip of chips) chip.addEventListener("click", event => { event.preventDefault(); show(chip.dataset.kindFilter, true); });
  show(new URLSearchParams(location.search).get("kind") || "", false);
})();
