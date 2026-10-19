// Hidden UI checks for ADD-1. Each title starts with its id in ../checks.json.
// Selectors use roles, labels and the copy in ticket.md only.
import {
  test, expect, openModal, reopen, field, options, option, continueButton, submitButton,
  currentStep, search, choose, toConfirm, expectEmpty,
} from './fixtures.mjs';

const SEARCH_API = '**/api/places/search**';
const isCreate = (request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/businesses';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
// Hidden step panels may still hold the same text; look at visible matches only.
const seen = (dialog, text) => dialog.getByText(text).filter({ visible: true }).first();

test('UI-01 the modal opens in the empty state', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await expect(dialog).toHaveAttribute('aria-modal', 'true');
  await expect(field(dialog)).toBeVisible();
  await expectEmpty(dialog);
});

test('UI-02 search waits for 2 characters', async ({ page, server }) => {
  const queries = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/places/search')) queries.push(new URL(request.url()).searchParams.get('q') || '');
  });
  const dialog = await openModal(page, server);
  await search(dialog, 'S');
  await sleep(1_200);
  expect(queries, 'a 1-character query sends no request').toEqual([]);
  await expect(options(dialog)).toHaveCount(0);

  await search(dialog, 'Su');
  await expect(option(dialog, 'Sunrise Bakery')).toHaveCount(2);
  expect(queries.length).toBeGreaterThan(0);
  for (const q of queries) expect(q.trim().length, `query "${q}"`).toBeGreaterThanOrEqual(2);
});

test('UI-03 search by name, city and ZIP in the modal', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await search(dialog, 'sunrise oakland');
  await expect(options(dialog)).toHaveCount(1);
  await expect(options(dialog).first()).toContainText('Oakland');

  await search(dialog, 'sunrise 94122');
  await expect(options(dialog)).toHaveCount(1);
  await expect(options(dialog).first()).toContainText('1550 Irving St');

  await search(dialog, 'berkeley');
  await expect(options(dialog)).toHaveCount(1);
  await expect(options(dialog).first()).toContainText('Northside Veterinary Clinic');
});

test('UI-04 results header, rows and footer', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await search(dialog, 'bakery');
  await expect(dialog.getByRole('listbox', { name: 'Search results' })).toBeVisible();
  await expect(options(dialog)).toHaveCount(3);
  await expect(dialog.getByText('Best matches')).toBeVisible();
  await expect(dialog.getByText('3 found')).toBeVisible();
  await expect(dialog.getByText('Powered by places search')).toBeVisible();
  const row = option(dialog, 'Irving');
  for (const text of ['Sunrise Bakery', '1550 Irving St', '94122', 'San Francisco', 'Bakery']) {
    await expect(row).toContainText(text);
  }
  await expect(option(dialog, 'Bayview Bakery Cafe')).toContainText('4900 3rd St');
});

test('UI-05 the badge shows on existing places only', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  for (const [query, name] of [['bluefin', 'Bluefin Sushi Express'], ['mission', 'Mission St. Hardware & Supply'], ['cedar', 'Cedar Street Physical Therapy']]) {
    await search(dialog, query);
    await expect(option(dialog, name)).toContainText('Already in Acme Leads');
  }
  await search(dialog, 'tidewater');
  await expect(option(dialog, 'Tidewater Books')).toHaveCount(1);
  await expect(option(dialog, 'Tidewater Books')).not.toContainText('Already in Acme Leads');
});

test('UI-06 searching state while the search runs', async ({ page, server }) => {
  await page.route(SEARCH_API, async (route) => {
    await sleep(2_000);
    await route.continue().catch(() => {});
  });
  const dialog = await openModal(page, server);
  await search(dialog, 'tidewater');
  await expect(dialog.getByRole('status').filter({ hasText: /Searching(\.\.\.|…)/ })).toBeVisible();
  await expect(option(dialog, 'Tidewater Books')).toBeVisible({ timeout: 8_000 });
});

test('UI-07 no results state with suggestion chips', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await search(dialog, 'zzzz');
  await expect(dialog.getByText('No match yet')).toBeVisible();
  await expect(dialog.getByText('Try another name, or add a city or ZIP.')).toBeVisible();
  for (const chip of ['Add city', 'Add ZIP', 'Check spelling']) {
    await expect(dialog.getByRole('button', { name: chip })).toBeVisible();
  }
  await expect(options(dialog)).toHaveCount(0);
  await expect(continueButton(dialog)).toBeDisabled();
  await dialog.getByRole('button', { name: 'Add city' }).click();
  await expect(field(dialog)).toBeFocused();
});

test('UI-08 search error with Retry', async ({ page, server }) => {
  let calls = 0;
  await page.route(SEARCH_API, async (route) => {
    calls += 1;
    if (calls === 1) {
      await route.fulfill({ status: 502, contentType: 'application/json', body: '{"error":"places_unavailable"}' });
    } else {
      await route.continue();
    }
  });
  const dialog = await openModal(page, server);
  await search(dialog, 'tidewater');
  const alert = dialog.getByRole('alert').filter({ hasText: 'Search is unavailable right now.' });
  await expect(alert).toBeVisible();
  await dialog.getByRole('button', { name: 'Retry' }).click();
  await expect(option(dialog, 'Tidewater Books')).toBeVisible();
  await expect(alert).toHaveCount(0);
  expect(calls).toBeGreaterThanOrEqual(2);
});

test('UI-09 selected state; a query change clears the selection', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await search(dialog, 'sunrise');
  await expect(continueButton(dialog)).toBeDisabled();
  await choose(dialog, 'Oakland');
  await expect(dialog.getByText('Selected: Sunrise Bakery')).toBeVisible();
  await expect(dialog.getByText('Ready when you are')).toBeVisible();
  await expect(continueButton(dialog)).toBeEnabled();

  await search(dialog, 'sunrise bakery');
  await expect(options(dialog)).toHaveCount(2);
  await expect(dialog.locator('[role="option"][aria-selected="true"]')).toHaveCount(0);
  await expect(dialog.getByText('Select a business to continue')).toBeVisible();
  await expect(dialog.getByText('Selected: Sunrise Bakery')).toHaveCount(0);
  await expect(continueButton(dialog)).toBeDisabled();
});

test('UI-10 continue shows the prefilled Confirm step', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await toConfirm(dialog, 'tidewater', 'Tidewater Books');
  const progress = dialog.getByRole('list', { name: 'Progress' });
  await expect(progress.getByRole('img', { name: 'Completed' }).first()).toBeVisible();
  for (const text of ['Tidewater Books', 'plc_F203', 'Book store', '77 Main St', '94105 San Francisco', 'tidewaterbooks.com', '+1 415-555-0303']) {
    await expect(seen(dialog, text), text).toBeVisible();
  }
  await expect(dialog.getByRole('link', { name: 'Open in Maps' })).toHaveAttribute('href', 'https://www.google.com/maps?cid=7770203');
  await expect(dialog.getByLabel('Notes (optional)')).toHaveValue('');
  await expect(dialog.getByText('We enrich the data and check for duplicates in the background.')).toBeVisible();
  await expect(submitButton(dialog)).toBeEnabled();
});

test('UI-11 submit shows Submitting, then Success', async ({ page, server }) => {
  await page.route('**/api/businesses', async (route) => {
    if (isCreate(route.request())) await sleep(1_500);
    await route.continue().catch(() => {});
  });
  const dialog = await openModal(page, server);
  await toConfirm(dialog, 'tidewater', 'Tidewater Books');
  await dialog.getByLabel('Notes (optional)').fill('Prefers email');
  const requestSeen = page.waitForRequest(isCreate);
  const responseSeen = page.waitForResponse((response) => isCreate(response.request()));
  await submitButton(dialog).click();

  const busy = dialog.getByRole('button', { name: 'Submitting' });
  await expect(busy).toBeVisible();
  await expect(busy).toBeDisabled();

  const request = await requestSeen;
  expect(request.postDataJSON()).toMatchObject({ place_id: 'plc_F203', notes: 'Prefers email' });
  const response = await responseSeen;
  expect(response.status()).toBe(201);
  const { request_id: requestId } = await response.json();

  await expect(dialog.getByText('Request received')).toBeVisible();
  await expect(dialog.getByText('We are enriching the data. The business appears in your list when it is ready.')).toBeVisible();
  await expect(dialog.getByText(requestId)).toBeVisible();
  await expect(seen(dialog, 'Tidewater Books')).toBeVisible();
  await expect(seen(dialog, 'San Francisco')).toBeVisible();
  await expect(dialog.getByText('Live in about an hour')).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Done' })).toBeVisible();
  await expect(submitButton(dialog)).toHaveCount(0);
});

test('UI-12 submit failure keeps the notes and allows a retry', async ({ page, server }) => {
  let creates = 0;
  await page.route('**/api/businesses', async (route) => {
    if (isCreate(route.request()) && ++creates === 1) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"server_error"}' });
      return;
    }
    await route.continue();
  });
  const dialog = await openModal(page, server);
  await toConfirm(dialog, 'tidewater', 'Tidewater Books');
  await dialog.getByLabel('Notes (optional)').fill('Call after 5pm');
  await submitButton(dialog).click();
  await expect(dialog.getByRole('alert').filter({ hasText: 'We could not submit this business. Please try again.' })).toBeVisible();
  await expect(dialog.getByLabel('Notes (optional)')).toHaveValue('Call after 5pm');
  await expect(submitButton(dialog)).toBeEnabled();
  await submitButton(dialog).click();
  await expect(dialog.getByText('Request received')).toBeVisible();
  expect(creates).toBe(2);
});

test('UI-13 duplicate state on Confirm', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await toConfirm(dialog, 'bluefin', 'Bluefin Sushi Express');
  const notice = dialog.getByRole('alert').filter({ hasText: 'This business is already in Acme Leads.' });
  await expect(notice).toBeVisible();
  await expect(dialog.getByText('Existing record #101')).toBeVisible();
  await expect(dialog.getByRole('link', { name: 'Open business' })).toHaveAttribute('href', /\/businesses\/101$/);
  await expect(dialog.getByText('plc_F101')).toBeVisible();
  await expect(submitButton(dialog)).toBeHidden();
  await expect(dialog.getByLabel('Notes (optional)')).toBeHidden();
});

test('UI-14 a duplicate found at submit shows the duplicate state', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await toConfirm(dialog, 'tidewater', 'Tidewater Books');
  // Someone else adds the same place while this user is on Confirm.
  const other = await page.request.post(`${server.url}/api/businesses`, { data: { place_id: 'plc_F203' } });
  expect(other.status()).toBe(201);
  const { business } = await other.json();
  await submitButton(dialog).click();
  await expect(dialog.getByRole('alert').filter({ hasText: 'This business is already in Acme Leads.' })).toBeVisible();
  await expect(dialog.getByText(`Existing record #${business.id}`)).toBeVisible();
  await expect(dialog.getByRole('link', { name: 'Open business' })).toHaveAttribute('href', new RegExp(`/businesses/${business.id}$`));
  await expect(dialog.getByText('Request received')).toHaveCount(0);
});

for (const [id, how] of [['UI-15', 'Close'], ['UI-16', 'Cancel']]) {
  test(`${id} ${how} resets the wizard`, async ({ page, server }) => {
    const dialog = await openModal(page, server);
    await search(dialog, 'sunrise');
    await choose(dialog, 'Oakland');
    await dialog.getByRole('button', { name: how, exact: true }).click();
    await expect(dialog).toBeHidden();
    await expectEmpty(await reopen(page));
  });
}

test('UI-17 Done resets the wizard', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await toConfirm(dialog, 'tidewater', 'Tidewater Books');
  await submitButton(dialog).click();
  await expect(dialog.getByText('Request received')).toBeVisible();
  await dialog.getByRole('button', { name: 'Done' }).click();
  await expect(dialog).toBeHidden();
  await expectEmpty(await reopen(page));
});

test.describe('phone width', () => {
  test.use({ viewport: { width: 375, height: 740 } });

  test('UI-18 the modal fits a 375 px viewport', async ({ page, server }) => {
    const fits = async (dialog, label) => {
      const box = await dialog.boundingBox();
      expect(box, `${label}: dialog has a box`).not.toBeNull();
      expect(box.x, `${label}: left edge`).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width, `${label}: right edge`).toBeLessThanOrEqual(375.5);
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(scrollWidth, `${label}: page scroll width`).toBeLessThanOrEqual(375);
    };
    const dialog = await openModal(page, server);
    await fits(dialog, 'empty');
    await search(dialog, 'bakery');
    await expect(options(dialog)).toHaveCount(3);
    await fits(dialog, 'results');
    await choose(dialog, 'Bayview');
    await continueButton(dialog).click();
    await expect(submitButton(dialog)).toBeVisible();
    await fits(dialog, 'confirm');
    await submitButton(dialog).click();
    await expect(dialog.getByText('Request received')).toBeVisible();
    await fits(dialog, 'success');
  });
});

test('UI-19 the business shows in the list only after enrichment', async ({ page, server }) => {
  const dialog = await openModal(page, server);
  await toConfirm(dialog, 'tidewater', 'Tidewater Books');
  await submitButton(dialog).click();
  await expect(dialog.getByText('Request received')).toBeVisible();
  await dialog.getByRole('button', { name: 'Done' }).click();

  await page.reload();
  await expect(page.getByRole('table')).toContainText('Bluefin Sushi Bar');
  await expect(page.getByRole('table')).not.toContainText('Tidewater Books');
  server.enrich();
  await page.reload();
  await expect(page.getByRole('table')).toContainText('Tidewater Books');
  expect(server.outboxCount(), 'emails in the outbox').toBe(0);
});
