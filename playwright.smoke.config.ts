import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke suite — the critical path only, fast enough to run on every push.
 * If this goes red, the published page is broken for a reviewer.
 */
process.env.SUITE = 'smoke';

export default defineConfig({
  globalSetup: './tests/global-setup.ts',
  testDir: './tests',
  testMatch: /smoke\.spec\.ts/,
  fullyParallel: true,
  retries: 0,                     // a flaky smoke test is a bug, not something to retry away
  reporter: [['line'], ['html', { outputFolder: 'artifacts/report-smoke', open: 'never' }]],
  outputDir: 'artifacts/output-smoke',
  use: {
    baseURL: 'http://127.0.0.1:4321',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'node scripts/serve.mjs 4321',
    url: 'http://127.0.0.1:4321',
    reuseExistingServer: false,   // never reuse a server someone left running
    timeout: 60_000,
  },
});
