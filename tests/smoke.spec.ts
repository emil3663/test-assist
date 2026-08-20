/**
 * Smoke suite — the critical path a reviewer walks in their first ten seconds.
 *
 * Scope rule: if a failure here would mean the published page misrepresents
 * the tool, it belongs in this file. Everything else lives in the regression
 * suite. Test titles carry their TEST_PLAN.md case IDs.
 */
import { test } from '@playwright/test';
import {
  expect, gotoApp, collectPageErrors, collectDialogs, uploadImage, pngBuffer,
  selectTool, dragOn, annotations, canvasSize, placeholderHidden,
  stubDisplayMedia, isPng, snapshots,
} from './helpers';

const FIXTURE = () => pngBuffer(400, 300, [40, 70, 120]);

test('the page loads clean and describes itself honestly', async ({ page }) => {
  const errors = collectPageErrors(page);
  const consoleErrors: string[] = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });

  await gotoApp(page);

  // PRR-204 guard: the published page must never call itself a mock again.
  const body = (await page.innerText('body')).toLowerCase();
  for (const word of ['mock', 'prototype', 'concept', 'parked', 'recessed']) {
    expect(body, `page describes itself with "${word}"`).not.toContain(word);
  }
  await expect(page.locator('.subtitle')).toHaveText(/capture, annotate and export/i);
  await expect(page.locator('.desktop-pill')).toBeVisible();

  expect(errors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test('IC-03 — an uploaded image loads onto the canvas', async ({ page }) => {
  await gotoApp(page);
  await uploadImage(page, FIXTURE());

  expect(await canvasSize(page)).toEqual([400, 300]);
  expect(await placeholderHidden(page)).toBe(true);
});

test('AT-01/05/06/07/08 — every drag tool produces an annotation', async ({ page }) => {
  await gotoApp(page);
  await uploadImage(page, FIXTURE());

  for (const tool of ['highlight', 'circle', 'arrow', 'rect', 'pen']) {
    await selectTool(page, tool);
    await dragOn(page, 30, 30, 140, 110);
  }

  expect(await annotations(page)).toHaveLength(5);
  expect((await annotations(page)).map((a: any) => a.type))
    .toEqual(['highlight', 'circle', 'arrow', 'rect', 'pen']);
});

test('AT-02 — the text tool places a comment', async ({ page }) => {
  await gotoApp(page);
  await uploadImage(page, FIXTURE());

  await selectTool(page, 'text');
  const box = (await page.locator('#annoCanvas').boundingBox())!;
  await page.mouse.click(box.x + 80, box.y + 80);
  await expect(page.locator('#textPopup')).toBeVisible();
  await page.fill('#textInput', 'Login button misaligned');
  await page.click('#btnTextOk');

  const [anno] = await annotations(page);
  expect(anno.type).toBe('text');
  expect(anno.text).toBe('Login button misaligned');
});

test('EX-01/EX-03 — Save PNG downloads a real PNG and adds a snapshot', async ({ page }) => {
  await gotoApp(page);
  await uploadImage(page, FIXTURE());
  await selectTool(page, 'rect');
  await dragOn(page, 20, 20, 120, 90);

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('#btnExportPng'),
  ]);
  const buf = await require('node:fs/promises').readFile(await download.path());

  expect(isPng(buf)).toBe(true);
  expect(buf.length).toBeGreaterThan(1000);
  expect(download.suggestedFilename()).toMatch(/\.png$/);
  expect(await snapshots(page)).toHaveLength(1);
});

test('EX-04/EX-05 — Export JSON carries the full annotation record', async ({ page }) => {
  await gotoApp(page);
  await uploadImage(page, FIXTURE());
  await selectTool(page, 'rect');
  await dragOn(page, 20, 20, 120, 90);

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('#btnExportJson'),
  ]);
  const data = JSON.parse(
    await require('node:fs/promises').readFile(await download.path(), 'utf8'),
  );

  expect(Object.keys(data).sort()).toEqual(['annotations', 'timestamp']);
  expect(new Date(data.timestamp).toString()).not.toBe('Invalid Date');
  const [a] = data.annotations;
  // README documents these fields; if any goes missing the docs become false.
  for (const key of ['type', 'x', 'y', 'x2', 'y2', 'color', 'size']) {
    expect(a, `annotation is missing "${key}"`).toHaveProperty(key);
  }
  expect(a.type).toBe('rect');
});

test('IC-01 — screen capture loads the captured frame onto the canvas', async ({ page }) => {
  await stubDisplayMedia(page, 'grant', 800, 600);
  const dialogs = collectDialogs(page);
  await gotoApp(page);

  await page.click('#btnCaptureTab');
  await page.waitForFunction(() => (window as any).baseCanvas.width === 800, null, { timeout: 10_000 });

  expect(await canvasSize(page)).toEqual([800, 600]);
  expect(await placeholderHidden(page)).toBe(true);
  expect(dialogs).toEqual([]);
});

test('UR-01/UR-04 — undo and redo move through annotation history', async ({ page }) => {
  await gotoApp(page);
  await uploadImage(page, FIXTURE());
  await selectTool(page, 'rect');
  await dragOn(page, 20, 20, 120, 90);
  await dragOn(page, 150, 40, 240, 120);
  expect(await annotations(page)).toHaveLength(2);

  await page.click('#btnUndo');
  expect(await annotations(page)).toHaveLength(1);
  await page.click('#btnRedo');
  expect(await annotations(page)).toHaveLength(2);
});
