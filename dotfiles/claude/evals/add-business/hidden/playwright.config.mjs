// Hidden UI checks. grade.sh sets DEST, GRADE_WORK, FIXTURE and UI_REPORT.
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './ui',
  fullyParallel: true,
  workers: Number(process.env.UI_WORKERS || 4),
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [['list'], ['json', { outputFile: process.env.UI_REPORT || 'ui-report.json' }]],
  use: {
    browserName: 'chromium',
    headless: true,
    viewport: { width: 1280, height: 800 },
    actionTimeout: 5_000,
  },
});
