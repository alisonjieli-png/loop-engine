/* AgentFoundry presentation only. Public metadata is never download authority. */
"use strict";
(() => {
  document.querySelector('.menu-button')?.addEventListener('click', event => {
    const button = event.currentTarget, open = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', String(open)); document.querySelector('#site-nav').classList.toggle('open', open);
  });
  document.addEventListener('keydown', event => {
    const button = document.querySelector('.menu-button');
    if (event.key !== 'Escape' || button?.getAttribute('aria-expanded') !== 'true') return;
    button.setAttribute('aria-expanded', 'false'); document.querySelector('#site-nav').classList.remove('open'); button.focus();
  });
  document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
    const input = button.parentElement.querySelector('input');
    try { await navigator.clipboard.writeText(input.value); button.textContent = 'Copied'; }
    catch (_) { input.focus(); input.select(); button.textContent = 'Select & copy'; }
    setTimeout(() => { button.textContent = 'Copy'; }, 2500);
  }));
  const filters = document.querySelector('[data-example-filters]');
  if (filters) {
    const items = [...document.querySelectorAll('[data-component]')], status = document.querySelector('[data-example-status]');
    function filter() {
      const query = filters.elements.query.value.trim().toLowerCase().split(/\s+/).filter(Boolean), kind = filters.elements.kind.value;
      let count = 0; for (const item of items) { item.hidden = Boolean(kind && item.dataset.kind !== kind) || !query.every(word => item.dataset.search.includes(word)); if (!item.hidden) count++; }
      status.textContent = count ? count + ' matching public example' + (count === 1 ? '' : 's') : 'No matching examples. Clear the filters or try a broader word.';
    }
    filters.addEventListener('input', filter); filters.addEventListener('submit', event => { event.preventDefault(); filter(); });
    filters.addEventListener('reset', () => setTimeout(filter, 0));
  }
  async function read(path) {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, {credentials:'omit',redirect:'error',cache:'no-store',signal:controller.signal});
      if (!response.ok) throw Error('The shared service is unavailable right now.');
      const reader = response.body?.getReader(); if (!reader) throw Error('The service returned an empty response.');
      const chunks = []; let length = 0;
      try { for (;;) { const part = await reader.read(); if (part.done) break; length += part.value.length; if (length > 1048576) throw Error('The service response was too large.'); chunks.push(part.value); } }
      catch (error) { await reader.cancel(); throw error; }
      const body = new Uint8Array(length); let offset = 0; for (const chunk of chunks) { body.set(chunk,offset); offset += chunk.length; }
      return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(body));
    } finally { clearTimeout(timeout); }
  }
  const form = document.querySelector('[data-public-search]');
  if (form) {
    const status = document.querySelector('[data-public-status]'), rows = document.querySelector('[data-public-results]');
    const previous = document.querySelector('[data-public-previous]'), next = document.querySelector('[data-public-next]');
    let page = 1, query = '', generation = 0;
    const node = (tag, text, className = '') => { const result = document.createElement(tag); result.textContent = text; if (className) result.className = className; return result; };
    async function load() {
      const attempt = ++generation; previous.disabled = true; next.disabled = true; status.textContent = 'Reading the current public collection…'; rows.replaceChildren();
      try {
        const envelope = await read('/api/v1/public-good?' + new URLSearchParams({query,page:String(page)}));
        if (attempt !== generation) return;
        const result = envelope.result;
        if (!result || result.record_type !== 'public_good_collection/v1' || result.page !== page || !Array.isArray(result.items)
            || !Number.isInteger(result.matches) || typeof result.has_next !== 'boolean' || typeof result.limits_description !== 'string'
            || result.items.some(item => !item || ['identity','title','summary','component_form','licence'].some(key => typeof item[key] !== 'string') || !Number.isInteger(item.files)))
          throw Error('This collection response is not a supported version. No items were shown.');
        const fragment = document.createDocumentFragment();
        for (const item of result.items) {
          const card = node('article','','public-result'); card.append(node('p',item.component_form,'eyebrow'), node('h3',item.title),node('p',item.summary),node('p',item.files+' files · '+item.licence),node('code',item.identity));
          const link = node('a','Connect your agent to retrieve →','text-link'); link.href = '/connect'; card.append(link); fragment.append(card);
        }
        rows.replaceChildren(fragment); status.textContent = result.matches ? result.matches + ' matching components · Page ' + page : 'No matching components. Try a broader search.';
        document.querySelector('[data-public-limits]').textContent = result.limits_description;
        previous.disabled = page <= 1; next.disabled = !result.has_next;
      } catch (error) { if (attempt === generation) status.textContent = error.name === 'AbortError' ? 'The collection did not answer in time. Submit the search to try again.' : error.message; }
    }
    form.addEventListener('submit', event => { event.preventDefault(); query = form.elements.query.value.trim(); page = 1; load(); });
    previous.addEventListener('click', () => { if (page > 1) { page--; load(); } }); next.addEventListener('click', () => { page++; load(); }); load();
  }
  const service = document.querySelector('[data-service-status]');
  if (service) read('/api/v1/health').then(value => {
    const result = value.result;
    if (!result || result.record_type !== 'service_health/v2' || typeof result.alive !== 'boolean' || typeof result.ready !== 'boolean') throw Error('The health response was not recognized.');
    service.textContent = result.alive && result.ready ? 'The shared service is reachable and its readiness checks passed. Account and download operations report their own status when you use them.' : 'The service answered, but is not reporting ready. Try again later.';
  }).catch(error => { service.textContent = error.name === 'AbortError' ? 'The service did not answer in time.' : error.message; });
})();
