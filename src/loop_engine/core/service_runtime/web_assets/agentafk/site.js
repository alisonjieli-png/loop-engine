/* Presentation only. The shared run desk owns passive local-file preparation. */
(() => {
  const menu = document.querySelector('.menu-button');
  const nav = document.getElementById('site-nav');
  menu?.addEventListener('click', () => {
    const expanded = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(expanded));
    nav.classList.toggle('is-open', expanded);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') {
      menu.setAttribute('aria-expanded', 'false');
      nav.classList.remove('is-open');
      menu.focus();
    }
  });
  const status = document.querySelector('[data-service-status]');
  if (status) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    fetch('/api/v1/health', {cache: 'no-store', credentials: 'omit', signal: controller.signal})
      .then(async response => {
        const body = await response.json();
        if (!response.ok || body.result?.ready !== true) throw Error('not ready');
        status.textContent = 'The shared service is reachable and ready. This does not report the state of your worker.';
      })
      .catch(() => { status.textContent = 'Service readiness could not be confirmed. Reload to check again. Your local worker is separate.'; })
      .finally(() => clearTimeout(timeout));
  }
})();
