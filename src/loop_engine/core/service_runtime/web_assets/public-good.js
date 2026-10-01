"use strict";
(() => {
  const root = document.querySelector('[data-public-good-browser]');
  if (!root) return;
  const form = document.getElementById('public-good-filters');
  const query = document.getElementById('public-good-query');
  const goal = document.getElementById('public-good-goal');
  const status = document.getElementById('public-good-status');
  const items = document.getElementById('public-good-items');
  const previous = document.getElementById('public-good-previous');
  const next = document.getElementById('public-good-next');
  let page = 1, requestNumber = 0, controller;
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const integer = value => Number.isSafeInteger(value) && value >= 0;
  const validate = record => {
    if (!record || record.record_type !== 'public_good_collection/v1'
      || record.authentication_required !== true || record.subscription_required !== false
      || !integer(record.packages) || !integer(record.distinct_useful_files)
      || !integer(record.matches) || !integer(record.page) || record.page < 1
      || typeof record.has_next !== 'boolean' || !Array.isArray(record.items) || record.items.length > 50
      || !Array.isArray(record.goals) || record.goals.length !== 17
      || !record.items.every(row => typeof row.identity === 'string' && /^[a-zA-Z0-9_.:-]+$/.test(row.identity)
        && typeof row.title === 'string' && typeof row.summary === 'string' && typeof row.public_benefit === 'string'
        && typeof row.component_form === 'string' && typeof row.licence === 'string'
        && Array.isArray(row.sdg_goals) && row.sdg_goals.every(id => Number.isInteger(id) && id >= 1 && id <= 17))
      || !record.goals.every(row => Number.isInteger(row.id) && row.id >= 1 && row.id <= 17
        && typeof row.label === 'string' && integer(row.packages))
      || new Set(record.goals.map(row => row.id)).size !== 17) throw new Error('invalid collection');
    return record;
  };
  const card = row => {
    const node = element('li', undefined, 'pg-item');
    node.append(element('h2', row.title), element('p', row.summary));
    node.append(element('p', row.public_benefit));
    node.append(element('p', row.component_form + ' · ' + row.licence, 'pg-meta'));
    node.append(element('p', row.sdg_goals.length ? row.sdg_goals.map(id => 'SDG ' + id).join(' · ') : 'Related public-benefit initiative', 'pg-meta'));
    const link = element('a', 'Sign in and open component');
    link.href = '/app?component=' + encodeURIComponent(row.identity) + '#browse-heading';
    node.append(link);
    return node;
  };
  async function load() {
    const thisRequest = ++requestNumber;
    controller?.abort(); controller = new AbortController();
    previous.disabled = true; next.disabled = true;
    root.setAttribute('aria-busy', 'true'); status.textContent = 'Loading the current collection…';
    const params = new URLSearchParams({page:String(page)});
    if (query.value.trim()) params.set('query', query.value.trim());
    if (goal.value) params.set('goal', goal.value);
    try {
      const answer = await fetch('/api/v1/public-good?' + params, {credentials:'omit',cache:'no-store',redirect:'error',signal:controller.signal});
      if (!answer.ok) throw new Error('collection unavailable');
      const packet = await answer.json();
      const record = validate(packet.result);
      if (thisRequest !== requestNumber) return;
      items.replaceChildren(...record.items.map(card));
      document.getElementById('public-good-population').textContent = record.packages.toLocaleString('en-US') + (record.packages===1?' package · ':' packages · ')
        + record.distinct_useful_files.toLocaleString('en-US') + ' distinct useful files';
      status.textContent = record.matches ? record.matches.toLocaleString('en-US') + (record.matches===1?' matching package. ':' matching packages. ') + 'Account required for every download.'
        : 'No published components match these filters. Try another goal or search.';
      document.getElementById('public-good-page').textContent = 'Page ' + record.page;
      previous.disabled = record.page <= 1; next.disabled = !record.has_next;
      document.getElementById('public-good-coverage').replaceChildren(...record.goals.map(row => element('li',
        'SDG ' + row.id + ' · ' + row.label + ': ' + row.packages.toLocaleString('en-US') + ' packages')));
      if (typeof record.limits_description === 'string') document.getElementById('public-good-limits').textContent = record.limits_description;
    } catch (error) {
      if (thisRequest !== requestNumber || error.name === 'AbortError') return;
      items.replaceChildren();
      document.getElementById('public-good-population').textContent = '';
      status.textContent = 'The collection could not be loaded. Please try again.';
    } finally {
      if (thisRequest === requestNumber) root.removeAttribute('aria-busy');
    }
  }
  form.addEventListener('submit', event => {event.preventDefault();page=1;load();});
  goal.addEventListener('change', () => {page=1;load();});
  previous.addEventListener('click', () => {if(page>1){page--;load();}});
  next.addEventListener('click', () => {page++;load();});
  load();
})();
