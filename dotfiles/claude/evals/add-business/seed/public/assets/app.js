// Acme Leads front end. Vanilla JS, no build step.
'use strict';

/** fetch() wrapper: JSON in and out. Rejects with {status, body} on a non-2xx answer. */
async function api(path, options = {}) {
  const init = { ...options, headers: { Accept: 'application/json', ...(options.headers || {}) } };
  if (init.body !== undefined && typeof init.body !== 'string') {
    init.body = JSON.stringify(init.body);
    init.headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(path, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw { status: response.status, body };
  }
  return body;
}

/** Creates an element: el('p', { class: 'hint' }, 'text', childNode). */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === false || value === null || value === undefined) continue;
    if (name.startsWith('on')) node.addEventListener(name.slice(2), value);
    else node.setAttribute(name, value === true ? '' : value);
  }
  node.append(...children.flat().filter((c) => c !== null && c !== undefined && c !== false));
  return node;
}

// Businesses page: filter rows by name or city.
function initBusinessFilter() {
  const input = document.getElementById('business-filter');
  const table = document.getElementById('business-table');
  if (!input || !table) return;
  input.addEventListener('input', () => {
    const needle = input.value.trim().toLowerCase();
    for (const row of table.tBodies[0].rows) {
      row.hidden = needle !== '' && !row.dataset.search.includes(needle);
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initBusinessFilter();
});
