/* The library site pages' one bottom bar, October 16, 2026: links to the library's update feed, shown once the reader has
   scrolled past most of the first screen and hidden for good when they dismiss it. Without this script the bar stays
   hidden and every page reads the same; the dismissal is kept in this browser's local storage only, like the
   appearance setting, and nothing here sends a request. */
(() => {
  "use strict";
  const bar = document.querySelector("[data-library-site-bar]");
  if (!bar) return;
  const key = "baltor.library-site-bar.dismissed";
  let dismissed = false;
  try { dismissed = localStorage.getItem(key) === "1"; } catch (_) { dismissed = false; }
  if (dismissed) return;
  const show = () => {
    if (window.scrollY > window.innerHeight * 0.6) {
      bar.hidden = false;
      window.removeEventListener("scroll", show);
    }
  };
  window.addEventListener("scroll", show, {passive: true});
  bar.querySelector("[data-library-site-bar-close]")?.addEventListener("click", () => {
    bar.hidden = true;
    try { localStorage.setItem(key, "1"); } catch (_) { /* the bar stays closed for this page view only */ }
  });
})();
