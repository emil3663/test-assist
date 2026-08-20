import { defineConfig, devices } from '@playwright/test';

/**
 * Regression suite — broader coverage, run on demand.
 *
 * Deliberately serial and non-retrying. Speed is not the goal; a flaky result
 * has to surface AS a flaky result rather than being masked by a retry or by
 * cross-worker interference. Its server runs on a different port from the
 * smoke suite so the two can never collide.
 */
process.env.SUITE = 'regression';

export default defineConfig({
  globalSetup: './tests/global-setup.ts',
  testDir: './tests',
  testMatch: /regression\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['line'], ['html', { outputFolder: 'artifacts/report-regression', open: 'never' }]],
  outputDir: 'artifacts/output-regression',
  use: {
    baseURL: 'http://127.0.0.1:4322',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'node scripts/serve.mjs 4322',
    url: 'http://127.0.0.1:4322',
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
