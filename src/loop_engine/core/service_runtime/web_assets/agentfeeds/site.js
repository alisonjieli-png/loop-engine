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
  // Browser preferences only. No account request, feed refresh or execution.
  const savedKey = 'agentfeeds.saved-collections.v1', maximumSaved = 64;
  const saveButtons = [...document.querySelectorAll('[data-save-collection]')];
  const savedStatus = document.querySelector('#saved-status');
  const savedPanel = document.querySelector('#saved-collections');
  const knownIds = new Set(saveButtons.map(button => button.dataset.saveCollection));
  let saved = [], storageReady = true;
  function readSaved() {
    try {
      const raw = localStorage.getItem(savedKey);
      if (raw && raw.length > 8192) throw Error('size');
      const value = raw ? JSON.parse(raw) : {version:1, collectionIds:[]};
      if (!value || value.version !== 1 || !Array.isArray(value.collectionIds)
          || value.collectionIds.length > maximumSaved
          || value.collectionIds.some(id => typeof id !== 'string' || !/^[a-z][a-z0-9-]{0,63}$/.test(id))) throw Error('shape');
      saved = [...new Set(value.collectionIds)];
      storageReady = true;
    } catch {
      saved = []; storageReady = false;
      if (savedStatus) savedStatus.textContent = 'Saved selections could not be read. Clear saved collections to reset them, or enable browser storage.';
    }
  }
  function renderSaved() {
    saveButtons.forEach(button => {
      const active = saved.includes(button.dataset.saveCollection);
      button.setAttribute('aria-pressed', String(active));
      button.textContent = active ? 'Remove saved collection' : 'Save collection';
    });
    if (!savedPanel) return;
    const valid = saved.filter(id => knownIds.has(id));
    savedPanel.querySelectorAll('[data-collection]').forEach(card => {
      card.hidden = !valid.includes(card.querySelector('[data-save-collection]').dataset.saveCollection);
    });
    document.querySelector('#saved-empty').hidden = valid.length > 0;
    document.querySelector('#saved-build').href = '/build' + (valid.length ? '?' + valid.map(id => 'collection=' + encodeURIComponent(id)).join('&') : '');
  }
  function writeSaved(next) {
    try {
      localStorage.setItem(savedKey, JSON.stringify({version:1, collectionIds:next}));
      saved = next; storageReady = true; renderSaved();
      if (savedStatus) savedStatus.textContent = saved.length + ' collections saved in this browser.';
      return true;
    } catch {
      if (savedStatus) savedStatus.textContent = 'Could not save this change. Browser storage may be blocked or full; your previous selection is unchanged.';
      return false;
    }
  }
  readSaved(); renderSaved();
  saveButtons.forEach(button => button.addEventListener('click', () => {
    readSaved();
    if (!storageReady) return;
    const id = button.dataset.saveCollection;
    const next = saved.includes(id) ? saved.filter(item => item !== id) : [...saved, id];
    if (next.length > maximumSaved) {
      if (savedStatus) savedStatus.textContent = 'Save up to 64 collections. Remove one before adding another.';
      return;
    }
    writeSaved(next);
  }));
  document.querySelector('#saved-clear')?.addEventListener('click', () => writeSaved([]));
  window.addEventListener('storage', event => { if (event.key === savedKey || event.key === null) { readSaved(); renderSaved(); } });
  document.querySelectorAll('[data-choice-search]').forEach(search => search.addEventListener('input', () => {
    const phrase = search.value.toLocaleLowerCase().trim();
    search.closest('fieldset').querySelectorAll('.choice').forEach(choice => { choice.hidden = !choice.textContent.toLocaleLowerCase().includes(phrase); });
  }));
  if (location.pathname === '/build' && selection.length > 0) {
    const wanted = new Set(selection);
    document.querySelectorAll('[name="collection_ids"]').forEach(field => { if (wanted.has(field.value)) field.checked = true; });
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
