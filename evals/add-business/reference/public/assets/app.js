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

/** An inline SVG icon. role="img" + label when it carries meaning, hidden otherwise. */
function icon(path, label) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', 'icon');
  if (label) {
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', label);
  } else {
    svg.setAttribute('aria-hidden', 'true');
  }
  const p = document.createElementNS(ns, 'path');
  p.setAttribute('d', path);
  svg.append(p);
  return svg;
}

const ICON_CHECK = 'M20 6 9 17l-5-5';
const ICON_SEARCH = 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16-4.3-4.3';

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

// Add-business modal: step 1 Search, step 2 Confirm, then Success.
function initAddBusiness() {
  const opener = document.getElementById('add-business');
  if (!opener) return;

  const MIN_QUERY = 2;
  const DEBOUNCE_MS = 250;
  let state;
  let timer = null;
  let searchSeq = 0;

  const input = el('input', {
    type: 'search', id: 'add-business-query', autocomplete: 'off',
    placeholder: 'Company name, city or ZIP',
  });
  const steps = el('ol', { class: 'steps', 'aria-label': 'Progress' });
  const searchArea = el('div', { class: 'search-area' });
  const searchStep = el('div', { class: 'step-panel' },
    el('label', { for: 'add-business-query', class: 'form-label' }, 'Search for a business'),
    el('div', { class: 'search-field' }, icon(ICON_SEARCH), input),
    searchArea,
  );
  const confirmStep = el('div', { class: 'step-panel' });
  const successStep = el('div', { class: 'step-panel' });
  const footer = el('footer', { class: 'modal-foot' });
  const dialog = el('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'add-business-title' },
    el('header', { class: 'modal-head' },
      el('h2', { id: 'add-business-title' }, 'Add business'),
      el('button', { type: 'button', class: 'icon-btn', 'aria-label': 'Close', onclick: close }, '×'),
    ),
    steps,
    el('div', { class: 'modal-body' }, searchStep, confirmStep, successStep),
    footer,
  );
  const backdrop = el('div', { class: 'modal-backdrop', hidden: true }, dialog);
  document.body.append(backdrop);

  function reset() {
    clearTimeout(timer);
    searchSeq++;
    state = {
      step: 'search', query: '', search: 'idle', results: [], selected: null,
      notes: '', submit: 'idle', duplicate: null, success: null,
    };
    input.value = '';
  }

  function open() {
    reset();
    render();
    backdrop.hidden = false;
    input.focus();
  }

  function close() {
    backdrop.hidden = true;
    reset();
    opener.focus();
  }

  input.addEventListener('input', () => {
    state.query = input.value;
    state.selected = null; // a new query clears the selection
    clearTimeout(timer);
    if (state.query.trim().length < MIN_QUERY) {
      searchSeq++;
      state.search = 'idle';
      state.results = [];
      render();
      return;
    }
    render();
    timer = setTimeout(() => runSearch(state.query.trim()), DEBOUNCE_MS);
  });

  async function runSearch(query) {
    const seq = ++searchSeq;
    state.search = 'loading';
    render();
    try {
      const data = await api('/api/places/search?q=' + encodeURIComponent(query));
      if (seq !== searchSeq) return;
      state.results = data.results;
      state.search = data.results.length ? 'results' : 'empty';
    } catch {
      if (seq !== searchSeq) return;
      state.results = [];
      state.search = 'error';
    }
    render();
  }

  function select(result) {
    state.selected = result;
    render();
  }

  function goToConfirm() {
    if (!state.selected) return;
    state.step = 'confirm';
    state.duplicate = state.selected.existing;
    state.submit = 'idle';
    render();
  }

  function back() {
    state.step = 'search';
    state.duplicate = null;
    state.submit = 'idle';
    render();
    input.focus();
  }

  async function submit() {
    state.submit = 'submitting';
    render();
    try {
      const data = await api('/api/businesses', {
        method: 'POST',
        body: { place_id: state.selected.place_id, notes: state.notes },
      });
      state.success = data;
      state.step = 'success';
    } catch (error) {
      if (error && error.status === 409 && error.body && error.body.existing) {
        state.duplicate = error.body.existing;
        state.submit = 'idle';
      } else {
        state.submit = 'error';
      }
    }
    render();
  }

  function render() {
    renderSteps();
    searchStep.hidden = state.step !== 'search';
    confirmStep.hidden = state.step !== 'confirm';
    successStep.hidden = state.step !== 'success';
    if (state.step === 'search') renderSearch();
    if (state.step === 'confirm') renderConfirm();
    if (state.step === 'success') renderSuccess();
    renderFooter();
  }

  function renderSteps() {
    const current = state.step === 'search' ? 0 : state.step === 'confirm' ? 1 : 2;
    steps.replaceChildren(...['Search', 'Confirm'].map((name, index) => {
      const done = index < current;
      return el('li', {
        class: 'step' + (done ? ' is-done' : '') + (index === current ? ' is-current' : ''),
        'aria-current': index === current ? 'step' : null,
      },
      el('span', { class: 'step-dot' }, done ? icon(ICON_CHECK, 'Completed') : String(index + 1)),
      el('span', { class: 'step-name' }, name),
      index === 0 ? el('span', { class: 'connector' + (current > 0 ? ' is-done' : ''), 'aria-hidden': 'true' }) : null);
    }));
  }

  function renderSearch() {
    const parts = [];
    if (state.selected) {
      parts.push(el('div', { class: 'selected-strip' }, icon(ICON_CHECK), `Selected: ${state.selected.name}`));
    }
    if (state.search === 'idle') {
      parts.push(el('p', { class: 'hint' }, 'Search is powered by places search. Add a city or ZIP to narrow it down.'));
    } else if (state.search === 'loading') {
      parts.push(el('div', { class: 'loading', role: 'status' },
        el('span', { class: 'skeleton' }), el('span', { class: 'skeleton' }), el('span', { class: 'skeleton short' }),
        el('span', { class: 'muted' }, 'Searching...')));
    } else if (state.search === 'error') {
      parts.push(el('div', { class: 'notice notice-danger', role: 'alert' },
        el('span', {}, 'Search is unavailable right now.'),
        el('button', { type: 'button', class: 'btn', onclick: () => runSearch(state.query.trim()) }, 'Retry')));
    } else if (state.search === 'empty') {
      const focusInput = () => input.focus();
      parts.push(el('div', { class: 'no-results' },
        icon(ICON_SEARCH),
        el('strong', {}, 'No match yet'),
        el('p', { class: 'muted' }, 'Try another name, or add a city or ZIP.'),
        el('div', { class: 'chips' }, ['Add city', 'Add ZIP', 'Check spelling'].map((label) =>
          el('button', { type: 'button', class: 'chip', onclick: focusInput }, label)))));
    } else {
      parts.push(renderResults());
    }
    searchArea.replaceChildren(...parts);
  }

  function renderResults() {
    const options = state.results.map((result) => {
      const selected = state.selected !== null && state.selected.place_id === result.place_id;
      const choose = () => select(result);
      return el('li', {
        role: 'option', class: 'result' + (selected ? ' is-selected' : ''), tabindex: '0',
        'aria-selected': selected ? 'true' : 'false',
        onclick: choose,
        onkeydown: (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(); } },
      },
      el('span', { class: 'result-check' }, selected ? icon(ICON_CHECK) : null),
      el('span', { class: 'result-main' },
        el('span', { class: 'result-name' }, result.name,
          result.existing ? el('span', { class: 'badge-warning' }, 'Already in Acme Leads') : null),
        el('span', { class: 'muted' }, [result.street, `${result.zip} ${result.city}`].filter(Boolean).join(', '))),
      el('span', { class: 'pill' }, result.category));
    });
    return el('div', { class: 'results' },
      el('div', { class: 'results-head' }, el('span', {}, 'Best matches'), el('span', { class: 'muted' }, `${state.results.length} found`)),
      el('ul', { role: 'listbox', 'aria-label': 'Search results', class: 'result-list' }, options),
      el('div', { class: 'results-foot muted' }, 'Powered by places search'));
  }

  function renderConfirm() {
    const place = state.selected;
    const card = el('div', { class: 'card' },
      el('div', { class: 'card-head' }, el('strong', {}, place.name), el('span', { class: 'pill' }, place.category)),
      el('dl', { class: 'facts' },
        el('dt', {}, 'Place ID'), el('dd', {}, place.place_id),
        el('dt', {}, 'Address'), el('dd', {}, el('div', {}, place.street || '—'), el('div', {}, `${place.zip} ${place.city}`)),
        el('dt', {}, 'Website'), el('dd', {}, place.website ? el('a', { href: place.website, target: '_blank', rel: 'noopener' }, place.website) : '—'),
        el('dt', {}, 'Phone'), el('dd', {}, place.phone || '—')),
      place.maps_url ? el('a', { href: place.maps_url, target: '_blank', rel: 'noopener', class: 'maps-link' }, 'Open in Maps') : null);

    const parts = [card];
    if (state.duplicate) {
      parts.push(el('div', { class: 'notice notice-warning', role: 'alert' },
        el('strong', {}, 'This business is already in Acme Leads.'),
        el('span', {}, `Existing record #${state.duplicate.id}`),
        el('a', { class: 'btn', href: `/businesses/${state.duplicate.id}` }, 'Open business')));
    } else {
      const notes = el('textarea', {
        id: 'add-business-notes', rows: '3', maxlength: '1000',
        disabled: state.submit === 'submitting',
        oninput: (event) => { state.notes = event.target.value; },
      });
      notes.value = state.notes;
      parts.push(
        el('label', { for: 'add-business-notes', class: 'form-label' }, 'Notes (optional)'),
        notes,
        el('p', { class: 'hint' }, 'We enrich the data and check for duplicates in the background.'));
      if (state.submit === 'error') {
        parts.push(el('div', { class: 'notice notice-danger', role: 'alert' }, 'We could not submit this business. Please try again.'));
      }
    }
    confirmStep.replaceChildren(...parts);
  }

  function renderSuccess() {
    const { request_id: requestId, business } = state.success;
    successStep.replaceChildren(el('div', { class: 'success' },
      el('span', { class: 'success-icon' }, icon(ICON_CHECK, 'Success')),
      el('h3', {}, 'Request received'),
      el('p', { class: 'muted' }, 'We are enriching the data. The business appears in your list when it is ready.'),
      el('div', { class: 'request-pill' }, el('strong', {}, requestId), el('span', {}, business.name), el('span', { class: 'muted' }, business.city)),
      el('div', { class: 'info-card' }, 'Live in about an hour')));
  }

  function renderFooter() {
    if (state.step === 'search') {
      footer.replaceChildren(
        el('span', { class: 'muted foot-hint' }, state.selected ? 'Ready when you are' : 'Select a business to continue'),
        el('div', { class: 'foot-actions' },
          el('button', { type: 'button', class: 'btn', onclick: close }, 'Cancel'),
          el('button', { type: 'button', class: 'btn btn-primary', disabled: !state.selected, onclick: goToConfirm }, 'Continue')));
    } else if (state.step === 'confirm') {
      const submitting = state.submit === 'submitting';
      footer.replaceChildren(
        el('button', { type: 'button', class: 'btn', onclick: back, disabled: submitting }, 'Back'),
        el('div', { class: 'foot-actions' },
          el('button', { type: 'button', class: 'btn', onclick: close }, 'Cancel'),
          state.duplicate ? null : el('button', { type: 'button', class: 'btn btn-primary', disabled: submitting, onclick: submit },
            submitting ? [el('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Submitting'] : 'Submit')));
    } else {
      footer.replaceChildren(el('span'), el('button', { type: 'button', class: 'btn btn-primary', onclick: close }, 'Done'));
    }
  }

  opener.addEventListener('click', open);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !backdrop.hidden) close();
  });
  reset();
}

document.addEventListener('DOMContentLoaded', () => {
  initBusinessFilter();
  initAddBusiness();
});
