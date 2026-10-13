"use strict";
(() => {
  const menu = document.querySelector('.menu-button'), nav = document.querySelector('#site-nav');
  function toggle(open) { menu?.setAttribute('aria-expanded', String(open)); nav?.classList.toggle('open', open); }
  menu?.addEventListener('click', () => toggle(menu.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') { toggle(false); menu.focus(); } });
  document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
    const field = button.closest('.copy-field').querySelector('input');
    try { await navigator.clipboard.writeText(field.value); button.textContent = 'Copied'; }
    catch { field.focus(); field.select(); button.textContent = 'Select & copy'; }
  }));
  const search = document.querySelector('#collection-search');
  search?.addEventListener('input', () => {
    const words = search.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    let count = 0;
    document.querySelectorAll('[data-collection]').forEach(card => { card.hidden = !words.every(word => card.dataset.search.includes(word)); if (!card.hidden) count++; });
    document.querySelector('#collection-count').textContent = count + (count === 1 ? ' collection' : ' collections');
    document.querySelector('#collection-empty').hidden = count !== 0;
  });
  const selection = new URLSearchParams(location.search).getAll('collection');
  document.querySelectorAll('[data-choice-search]').forEach(search => search.addEventListener('input', () => {
    const phrase = search.value.toLocaleLowerCase().trim();
    search.closest('fieldset').querySelectorAll('.choice').forEach(choice => { choice.hidden = !choice.textContent.toLocaleLowerCase().includes(phrase); });
  }));
  if (location.pathname === '/build' && selection.length === 1) {
    const field = [...document.querySelectorAll('[name="collection_ids"]')].find(item => item.value === selection[0]);
    if (field) field.checked = true;
  }
  const status = document.querySelector('[data-service-status]');
  if (status) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
    fetch('/api/v1/health', {credentials:'omit',cache:'no-store',redirect:'error',signal:controller.signal})
      .then(async response => { const value = await response.json(); status.textContent = response.ok && value.result?.ready === true ? 'Service available.' : 'The service is not ready right now. Please try again later.'; })
      .catch(() => { status.textContent = 'The service could not be reached. Check your connection and try again later.'; })
      .finally(() => clearTimeout(timer));
  }
})();
