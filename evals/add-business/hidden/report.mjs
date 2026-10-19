// Merges the baseline, API and UI results into one JSON object on stdout.
//   node report.mjs WORK_DIR DEST
// Exit 0 only when every check passes. A check with no result counts as failed.
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const [work, dest] = process.argv.slice(2);
const here = path.dirname(fileURLToPath(import.meta.url));
const catalogue = JSON.parse(readFileSync(path.join(here, 'checks.json'), 'utf8'));

const readJson = (file) => {
  try { return JSON.parse(readFileSync(path.join(work, file), 'utf8')); } catch { return null; }
};
const firstLine = (text) => String(text || '').replace(/\x1b\[[0-9;]*m/g, '').split('\n').map((l) => l.trim()).filter(Boolean).slice(0, 2).join(' ').slice(0, 300);

const results = {};

// BASE-1: php tests/run.php
const baseCode = existsSync(path.join(work, 'base1.status')) ? readFileSync(path.join(work, 'base1.status'), 'utf8').trim() : '';
const baseLog = existsSync(path.join(work, 'base1.log')) ? readFileSync(path.join(work, 'base1.log'), 'utf8') : '';
results['BASE-1'] = baseCode === '0'
  ? { pass: true, detail: '' }
  : { pass: false, detail: `exit ${baseCode || '?'}: ` + firstLine(baseLog.split('\n').filter((l) => l.startsWith('FAIL') || /error/i.test(l)).join('\n') || baseLog.split('\n').slice(-3).join('\n')) };

// API checks
const api = readJson('api.json') || {};
for (const [id, result] of Object.entries(api)) results[id] = result;

// UI checks: walk the Playwright JSON report
const ui = readJson('ui.json');
const walk = (suite) => {
  for (const spec of suite.specs || []) {
    const id = spec.title.split(' ')[0];
    const runs = spec.tests.flatMap((t) => t.results);
    const error = runs.flatMap((r) => r.errors || (r.error ? [r.error] : [])).map((e) => e.message)[0];
    results[id] = spec.ok && runs.length > 0 ? { pass: true, detail: '' } : { pass: false, detail: firstLine(error || 'did not run') };
  }
  for (const child of suite.suites || []) walk(child);
};
for (const suite of ui?.suites || []) walk(suite);
const uiSetupError = ui?.errors?.[0]?.message;

const checks = catalogue.checks.map((c) => {
  const r = results[c.id] || { pass: false, detail: c.id.startsWith('UI-') && uiSetupError ? firstLine(uiSetupError) : (api._setup?.detail && c.id.startsWith('API-') ? firstLine(api._setup.detail) : 'no result') };
  return { id: c.id, kind: c.kind, criterion: c.criterion, title: c.title, pass: r.pass === true, detail: r.pass ? '' : r.detail };
});

const criteria = {};
for (const [key, title] of Object.entries(catalogue.criteria)) {
  const mine = checks.filter((c) => c.criterion === key);
  criteria[key] = { title, pass: mine.every((c) => c.pass), passed: mine.filter((c) => c.pass).length, total: mine.length };
}
const count = (kind) => {
  const mine = checks.filter((c) => c.kind === kind);
  return { passed: mine.filter((c) => c.pass).length, total: mine.length };
};
const passed = checks.filter((c) => c.pass).length;
const report = {
  eval: 'add-business',
  dest,
  pass: passed === checks.length,
  passed,
  total: checks.length,
  baseline: count('baseline'),
  feature: count('feature'),
  criteria,
  checks,
};
process.stdout.write(JSON.stringify(report, null, 2) + '\n');
process.exit(report.pass ? 0 : 1);
