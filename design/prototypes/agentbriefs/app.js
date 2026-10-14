'use strict';
(() => {
  const initial = {company: 'Northstar Components', goal: 'Reduce order delays without changing the core ordering system.', systems: 'Order management service, warehouse planning and invoice review.', constraints: 'Use synthetic data for any experiment. No production writes, purchases or vendor contact.', version: 3};
  const context = {...initial}, decisions = [];
  let dismissed = false;
  const fixtures = [
    {id: 'AB-001', title: 'A second fulfillment region merits review.', kind: 'development', label: 'Source-backed development', score: 80, age: 2, ready: true, detail: 'Compare a fictional supplier announcement with the example delivery goal. Performance and commercial fit remain unknown.'},
    {id: 'AB-002', title: 'Test an invoice extraction alternative.', kind: 'experiment', label: 'Experimental fit', score: 75, age: 3, ready: false, detail: 'A proposed test using synthetic invoices. No experiment has run and no improvement has been measured.'},
    {id: 'AB-003', title: 'Revisit an older planning-system note.', kind: 'development', label: 'Source-backed development', score: 40, age: 18, ready: false, detail: 'An older fictional method note. Its relevance and current applicability need another review.'}
  ];
  const $ = id => document.getElementById(id);
  function text(tag, value, className) { const node = document.createElement(tag); node.textContent = value; if (className) node.className = className; return node; }
  function number(id, minimum, maximum) { const input = $(id), parsed = Number(input.value); const value = Number.isFinite(parsed) ? Math.min(maximum, Math.max(minimum, Math.trunc(parsed))) : minimum; input.value = String(value); return value; }
  function renderCandidates() {
    const category = $('category').value, floor = $('floor').value, priority = number('priority', 0, 100), freshness = number('freshness', 1, 30), attention = number('attention', 0, 3);
    $('priority-value').textContent = priority + ' / 100';
    let surfaced = 0;
    $('candidates').replaceChildren();
    for (const item of fixtures) {
      const reasons = [];
      if (item.id === 'AB-001' && dismissed) reasons.push('Dismissed in this preview');
      if (category !== 'all' && category !== item.kind) reasons.push('Outside the selected category');
      if (item.score < priority) reasons.push('Below the scenario importance floor');
      if (item.age > freshness) reasons.push('Older than the freshness limit');
      if (floor === 'ready' && !item.ready) reasons.push(item.kind === 'experiment' ? 'No approved experiment, baseline or result' : 'Evidence is not decision-ready');
      if (!reasons.length && surfaced >= attention) reasons.push('Outside the attention budget');
      const eligible = reasons.length === 0;
      if (eligible) surfaced++;
      const card = text('article', '', 'candidate');card.dataset.candidate = item.id;
      const top = text('div', '', 'candidate-top');top.append(text('span', item.id + ' · SCENARIO', 'record-id'), text('span', eligible ? 'Would surface' : 'Held in preview', 'tag ' + (eligible ? 'synthetic' : 'held')));
      card.append(top, text('h3', item.title), text('p', item.detail));
      const meta = text('div', '', 'candidate-meta');meta.append(text('span', item.label), text('span', 'Importance ' + item.score), text('span', item.age + ' scenario days old'));card.append(meta);
      card.append(text('p', eligible ? 'Meets these local review rules. No alert is sent and no work is authorized.' : reasons.join('. ') + '.', 'reason'));
      const link = text('a', item.id === 'AB-001' ? 'Read the example brief ↗' : 'Inspect its evidence →');link.href = item.id === 'AB-001' ? '#brief' : '#evidence';card.append(link);$('candidates').append(card);
    }
    $('surface-count').textContent = String(surfaced);$('held-count').textContent = String(fixtures.length - surfaced);
    $('rule-status').textContent = surfaced + (surfaced === 1 ? ' example would surface.' : ' examples would surface.') + ' No notification is sent.';
  }
  function renderContext() {
    document.querySelectorAll('[data-company]').forEach(node => {node.textContent = context.company;});
    document.querySelectorAll('[data-version]').forEach(node => {node.textContent = 'context v' + context.version;});
    $('context-name').textContent = context.company;
    for (const key of ['goal', 'systems', 'constraints']) $('context-' + key).textContent = context[key];
  }
  function addDecision(kind) {
    if (decisions.some(row => row.kind === kind && row.version === context.version)) { $('decision-status').textContent = 'That demonstration action is already listed for this context version.'; return; }
    const row = {kind, company: context.company, version: context.version};decisions.push(row);
    const li = document.createElement('li');li.append(text('strong', kind + ': AB-001'), text('p', row.company + ' · review context v' + row.version + ' · brief based on original context v3, example revision 1'), text('p', 'Local demonstration entry. No adoption, experiment, notification or realized benefit recorded.'));
    $('decision-list').append(li);$('decision-empty').hidden = true;$('decision-count').textContent = decisions.length + (decisions.length === 1 ? ' entry' : ' entries');
    $('decision-status').textContent = kind + ' in this preview only. Review it in Decision Memory. Reload clears the entry.';
    if (kind === 'Dismissed') {dismissed = true;renderCandidates();}
  }
  function showView() {
    const name = location.hash.slice(1), valid = ['overview', 'company', 'brief', 'evidence', 'decisions'].includes(name) ? name : 'overview';
    document.querySelectorAll('[data-view]').forEach(node => {node.hidden = node.dataset.view !== valid;});
    document.querySelectorAll('[data-nav]').forEach(node => {if (node.dataset.nav === valid) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current');});
    document.title = 'AgentBriefs | ' + {overview: 'Local decision workspace', company: 'CompanyDNA preview', brief: 'Synthetic decision brief', evidence: 'Synthetic evidence ledger', decisions: 'Local Decision Memory'}[valid];
  }
  for (const key of ['goal', 'systems', 'constraints']) $(key).value = initial[key];
  $('company-name').value = initial.company;
  $('category').value = 'all';$('floor').value = 'ready';$('priority').value = '60';$('freshness').value = '7';$('attention').value = '1';
  for (const id of ['category', 'floor', 'priority', 'freshness', 'attention']) $(id).addEventListener('input', renderCandidates);
  $('company-form').addEventListener('submit', event => event.preventDefault());
  $('apply-context').addEventListener('click', () => {
    const name = $('company-name').value.trim();
    if (!name) { $('context-status').textContent = 'Enter an invented company name before applying the preview.'; $('company-name').focus(); return; }
    context.company = name.slice(0, 80);for (const key of ['goal', 'systems', 'constraints']) context[key] = $(key).value.trim().slice(0, 600);context.version++;renderContext();
    $('context-status').textContent = 'Applied to this preview only. Nothing was uploaded or stored; reload resets the context.';
  });
  $('discuss').addEventListener('click', () => addDecision('For discussion'));
  $('dismiss').addEventListener('click', () => addDecision('Dismissed'));
  $('reset').addEventListener('click', () => location.reload());
  window.addEventListener('hashchange', () => {showView();$('main').focus();});
  renderContext();renderCandidates();showView();
})();
