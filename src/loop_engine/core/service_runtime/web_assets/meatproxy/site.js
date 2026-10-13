"use strict";
(() => {
  const menu = document.querySelector('.menu-button');
  const nav = document.querySelector('#site-nav');
  if (menu && nav) {
    document.documentElement.classList.add('has-js');
    menu.addEventListener('click', () => {
      const open = menu.getAttribute('aria-expanded') !== 'true';
      menu.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
        menu.setAttribute('aria-expanded', 'false');
        nav.classList.remove('is-open');
        menu.focus();
      }
    });
  }
  const choice = document.querySelector('#decision');
  const instruction = document.querySelector('#reading-instruction');
  const status = document.querySelector('#copy-status');
  if (choice && instruction && status) {
    choice.addEventListener('change', () => {
      const selected = choice.selectedOptions[0];
      if (!selected || !/^[a-z0-9-]+$/.test(selected.value)) return;
      const id = selected.value;
      instruction.value = `Read https://agentfeeds.si/feeds/collections/${id}.md before making this decision. Check the original sources, compare evidence relevant to my task, and cite what you used. State the dates and anything you could not verify. Ask before taking actions.`;
      document.querySelector('.source-link').href = `https://agentfeeds.si/collections/${id}`;
      document.querySelector('.profile-link').href = `https://agentfeeds.si/build?collection=${id}`;
      status.textContent = `Ready: ${selected.textContent}. Review the instruction before using it.`;
    });
    document.querySelector('#copy-instruction').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(instruction.value);
        status.textContent = 'Copied. Paste this into your agent’s task or project instructions.';
      } catch {
        instruction.focus();
        instruction.select();
        status.textContent = 'Clipboard access is unavailable. The instruction is selected so you can copy it manually.';
      }
    });
  }
})();
