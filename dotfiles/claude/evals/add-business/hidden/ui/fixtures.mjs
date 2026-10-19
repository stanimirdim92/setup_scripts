// Each Playwright worker runs its own bin/serve and SQLite file. Each test starts
// from a fresh database (php bin/migrate).
import { test as base, expect } from '@playwright/test';
import { execFileSync, spawn } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';

const DEST = process.env.DEST;
const WORK = process.env.GRADE_WORK;
const FIXTURE = process.env.FIXTURE;
if (!DEST || !WORK || !FIXTURE) {
  throw new Error('Run through grade.sh: DEST, GRADE_WORK and FIXTURE must be set');
}

function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

async function waitForPort(port, ms = 15_000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const open = await new Promise((resolve) => {
      const socket = net.connect(port, '127.0.0.1');
      socket.once('connect', () => { socket.destroy(); resolve(true); });
      socket.once('error', () => resolve(false));
    });
    if (open) return;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`bin/serve did not listen on port ${port}`);
}

export const test = base.extend({
  server: [async ({}, use, workerInfo) => {
    const db = path.join(WORK, `ui-${workerInfo.workerIndex}.sqlite`);
    const port = await freePort();
    const env = {
      ...process.env, ACME_DB: db, ACME_PLACES: 'fixture', ACME_PLACES_FIXTURE: FIXTURE,
      PORT: String(port), HOST: '127.0.0.1',
    };
    const php = (args) => execFileSync('php', args, { cwd: DEST, env, encoding: 'utf8', stdio: 'pipe' });
    php(['bin/migrate']);
    // Own process group, so teardown also stops a server that bin/serve did not exec.
    const proc = spawn('bash', ['bin/serve'], { cwd: DEST, env, stdio: 'ignore', detached: true });
    try {
      await waitForPort(port);
      await use({
        url: `http://127.0.0.1:${port}`,
        migrate: () => php(['bin/migrate']),
        enrich: () => php(['bin/enrich']),
        outboxCount: () => Number(php(['-r', `echo (new PDO('sqlite:' . getenv('ACME_DB')))->query('SELECT COUNT(*) FROM outbox')->fetchColumn();`]).trim()),
      });
    } finally {
      try { process.kill(-proc.pid, 'SIGTERM'); } catch { proc.kill('SIGTERM'); }
    }
  }, { scope: 'worker' }],

  fresh: [async ({ server }, use) => {
    server.migrate();
    await use();
  }, { auto: true }],
});

export { expect };

/** Opens the modal from the Businesses page. Fails fast when no dialog appears. */
export async function openModal(page, server) {
  await page.goto(`${server.url}/businesses`);
  return reopen(page);
}

export async function reopen(page) {
  await page.getByRole('button', { name: 'Add business' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add business' });
  await expect(dialog, 'the "+ Add business" button opens a dialog named "Add business"').toBeVisible({ timeout: 3_000 });
  return dialog;
}

export const field = (dialog) => dialog.getByLabel('Search for a business');
export const options = (dialog) => dialog.getByRole('option');
export const option = (dialog, text) => dialog.getByRole('option').filter({ hasText: text });
export const continueButton = (dialog) => dialog.getByRole('button', { name: 'Continue', exact: true });
export const submitButton = (dialog) => dialog.getByRole('button', { name: 'Submit', exact: true });
export const currentStep = (dialog) => dialog.getByRole('list', { name: 'Progress' }).locator('[aria-current="step"]');
export const EMPTY_HINT = 'Search is powered by places search. Add a city or ZIP to narrow it down.';

export async function search(dialog, query) {
  await field(dialog).fill(query);
}

export async function choose(dialog, text) {
  const row = option(dialog, text);
  await expect(row).toHaveCount(1);
  await row.click();
  await expect(row).toHaveAttribute('aria-selected', 'true');
}

/** Search, select one result and continue to the Confirm step. */
export async function toConfirm(dialog, query, text) {
  await search(dialog, query);
  await choose(dialog, text);
  await continueButton(dialog).click();
  await expect(currentStep(dialog)).toContainText('Confirm');
}

/** The wizard is back in its empty state. */
export async function expectEmpty(dialog) {
  await expect(field(dialog)).toHaveValue('');
  await expect(dialog.getByText(EMPTY_HINT)).toBeVisible();
  await expect(currentStep(dialog)).toContainText('Search');
  await expect(continueButton(dialog)).toBeDisabled();
  await expect(dialog.getByText('Select a business to continue')).toBeVisible();
  await expect(options(dialog)).toHaveCount(0);
}
