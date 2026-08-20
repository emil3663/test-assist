/**
 * Records what actually produced a run, so a flaky-looking result can be
 * correlated with the environment rather than guessed at. Written next to the
 * HTML report for whichever suite is running.
 *
 * (The skill this follows suggests Allure's environmentInfo; this repo uses
 * Playwright's built-in HTML reporter instead to avoid a second reporting
 * dependency, so the same metadata is written here by hand.)
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import os from 'node:os';
import type { FullConfig } from '@playwright/test';

export default async function globalSetup(config: FullConfig) {
  const suite = process.env.SUITE ?? 'unknown';
  const dir = join(process.cwd(), 'artifacts');
  await mkdir(dir, { recursive: true });
  await writeFile(
    join(dir, `environment-${suite}.json`),
    JSON.stringify({
      suite,
      os_platform: os.platform(),
      os_release: os.release(),
      arch: os.arch(),
      node_version: process.version,
      workers: config.workers,
      retries: config.projects[0]?.retries ?? 0,
      ci: Boolean(process.env.CI),
    }, null, 2),
  );
}
