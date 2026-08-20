/**
 * Regression suite — the automatable remainder of TEST_PLAN.md.
 *
 * Runs serial, single-worker, no retries (see playwright.regression.config.ts):
 * a flaky result must surface as a flaky result rather than be masked.
 *
 * Cases NOT covered here are listed in STABILITY_MATRIX.md with the reason.
 */
import { test } from '@playwright/test';
import {
  expect, gotoApp, collectDialogs, collectPageErrors, uploadImage, pngBuffer, jpegBuffer,
  selectTool, dragOn, clickOn, setControl, annotations, snapshots, canvasSize,
  placeholderHidden, stubDisplayMedia, dropFile, pixelAt, isPng,
} from './helpers';
import { readFile } from 'node:fs/promises';

const FIXTURE = () => pngBuffer(400, 300, [40, 70, 120]);

async function withImage(page: any) {
  await gotoApp(page);
  await uploadImage(page, FIXTURE());
}

/* ─── 3.1 Image capture & upload ───────────────────────────────────────── */

test.describe('3.1 Image Capture & Upload', () => {
  test('IC-02 — declining the capture prompt leaves the page untouched', async ({ page }) => {
    await stubDisplayMedia(page, 'deny');
    const dialogs = collectDialogs(page);
    await gotoApp(page);

    await page.click('#btnCaptureTab');
    await page.waitForTimeout(500);

    expect(dialogs, 'declining should be silent, not an error').toEqual([]);
    expect(await placeholderHidden(page)).toBe(false);
  });

  test('IC-04 — a JPEG renders onto the canvas', async ({ page }) => {
    await gotoApp(page);
    await uploadImage(page, await jpegBuffer(page, 240, 180), 'shot.jpg', 'image/jpeg');
    expect(await canvasSize(page)).toEqual([240, 180]);
  });

  test('IC-05 — a PNG with transparency keeps its alpha channel', async ({ page }) => {
    await gotoApp(page);
    await uploadImage(page, pngBuffer(120, 90, [255, 0, 0], 0));   // fully transparent red
    const [, , , alpha] = await pixelAt(page, 'baseCanvas', 10, 10);
    expect(alpha, 'transparent pixels should not be composited opaque').toBe(0);
  });

  test('IC-06 — a very large image loads without crashing', async ({ page }) => {
    const errors = collectPageErrors(page);
    await gotoApp(page);
    await uploadImage(page, pngBuffer(4200, 600, [10, 120, 90]));
    expect(await canvasSize(page)).toEqual([4200, 600]);
    expect(errors).toEqual([]);
  });

  test('IC-07 — dropping an image onto the canvas loads it', async ({ page }) => {
    await gotoApp(page);
    await dropFile(page, 'dropped.png', 'image/png', pngBuffer(200, 150, [90, 40, 130]).toString('base64'));
    await page.waitForFunction(
      () => getComputedStyle(document.getElementById('placeholder')!).display === 'none',
    );
    expect(await canvasSize(page)).toEqual([200, 150]);
  });

  test('IC-08 — dropping a non-image file is ignored silently', async ({ page }) => {
    const errors = collectPageErrors(page);
    await gotoApp(page);
    await dropFile(page, 'notes.txt', 'text/plain', Buffer.from('not an image').toString('base64'));
    await page.waitForTimeout(300);
    expect(await placeholderHidden(page)).toBe(false);
    expect(errors).toEqual([]);
  });

  test('IC-09 — a browser without ImageCapture is told what to do instead', async ({ page }) => {
    // Not in TEST_PLAN v1.0; added because the README now makes a browser-support
    // claim (Firefox has no ImageCapture) that should not be able to drift.
    await stubDisplayMedia(page, 'no-imagecapture');
    const dialogs = collectDialogs(page);
    await gotoApp(page);
    await page.click('#btnCaptureTab');
    await page.waitForTimeout(300);
    expect(dialogs).toHaveLength(1);
    expect(dialogs[0]).toMatch(/Upload Image/i);
  });
});

/* ─── 3.2 Video recording ──────────────────────────────────────────────── */

test.describe('3.2 Video Recording', () => {
  test('VR-01 — starting a recording shows the badge', async ({ page }) => {
    await stubDisplayMedia(page, 'grant');
    await gotoApp(page);
    await page.click('#modeVideo');
    await page.click('#btnRecord');
    await expect(page.locator('#recordingBadge')).toBeVisible();
  });

  test('VR-02 — the timer advances while recording', async ({ page }) => {
    await stubDisplayMedia(page, 'grant');
    await gotoApp(page);
    await page.click('#modeVideo');
    await page.click('#btnRecord');
    await expect(page.locator('#recTime')).toHaveText('00:00');
    await expect(page.locator('#recTime')).not.toHaveText('00:00', { timeout: 5_000 });
  });

  test('VR-03/VR-06 — stopping downloads a clip and re-arms the button', async ({ page }) => {
    await stubDisplayMedia(page, 'grant');
    await gotoApp(page);
    await page.click('#modeVideo');
    await page.click('#btnRecord');
    await page.waitForTimeout(1200);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('#btnStopRecord'),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.(webm|mp4)$/);
    const buf = await readFile(await download.path());
    expect(buf.length, 'the recording should not be an empty file').toBeGreaterThan(0);

    await expect(page.locator('#recordingBadge')).toBeHidden();
    await expect(page.locator('#btnRecord')).toBeEnabled();
  });

  test('VR-05 — declining the recording prompt is silent', async ({ page }) => {
    await stubDisplayMedia(page, 'deny');
    const dialogs = collectDialogs(page);
    await gotoApp(page);
    await page.click('#modeVideo');
    await page.click('#btnRecord');
    await page.waitForTimeout(400);
    expect(dialogs).toEqual([]);
    await expect(page.locator('#recordingBadge')).toBeHidden();
    await expect(page.locator('#btnRecord')).toBeEnabled();
  });
});

/* ─── 3.3 Annotation tools ─────────────────────────────────────────────── */

test.describe('3.3 Annotation Tools', () => {
  test('AT-03 — multi-line text is stored with its line breaks', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'text');
    await clickOn(page, 60, 60);
    await page.fill('#textInput', 'Line one\nLine two');
    await page.click('#btnTextOk');
    expect((await annotations(page))[0].text).toBe('Line one\nLine two');
  });

  test('AT-04 — cancelling the text popup adds nothing', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'text');
    await clickOn(page, 60, 60);
    await page.fill('#textInput', 'discard me');
    await page.click('#btnTextCancel');
    await expect(page.locator('#textPopup')).toBeHidden();
    expect(await annotations(page)).toHaveLength(0);
  });

  test('AT-09 — the select tool moves an annotation without deforming it', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    await dragOn(page, 40, 40, 140, 120);
    const before = (await annotations(page))[0];

    await selectTool(page, 'select');
    await dragOn(page, 60, 60, 160, 140);            // grab inside the rect, drag +100/+80
    const after = (await annotations(page))[0];

    expect(after.x).toBeCloseTo(before.x + 100, 0);
    expect(after.y).toBeCloseTo(before.y + 80, 0);
    // a move must translate both corners, or the shape stretches instead of moving
    expect(after.x2).toBeCloseTo(before.x2 + 100, 0);
    expect(after.y2).toBeCloseTo(before.y2 + 80, 0);
  });

  test('AT-10 — a new colour applies to subsequent annotations only', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    await dragOn(page, 20, 20, 100, 80);
    await setControl(page, 'strokeColor', '#00ff00');
    await dragOn(page, 140, 20, 220, 80);

    const [first, second] = await annotations(page);
    expect(second.color).toBe('#00ff00');
    expect(first.color, 'existing annotations must not change colour').not.toBe('#00ff00');
  });

  test('AT-11 — a new stroke size applies to subsequent annotations', async ({ page }) => {
    await withImage(page);
    await setControl(page, 'strokeSize', '9');
    await expect(page.locator('#strokeSizeLabel')).toHaveText('9px');
    await selectTool(page, 'rect');
    await dragOn(page, 20, 20, 100, 80);
    expect((await annotations(page))[0].size).toBe(9);
  });

  test('AT-12 — highlight fill opacity is applied', async ({ page }) => {
    await withImage(page);
    await setControl(page, 'fillOpacity', '75');
    await expect(page.locator('#fillOpacityLabel')).toHaveText('75%');
    await selectTool(page, 'highlight');
    await dragOn(page, 20, 20, 120, 90);
    expect((await annotations(page))[0].fillOpacity).toBeCloseTo(0.75, 2);
  });

  test('AT-13 — a click smaller than 3px adds no annotation', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    await dragOn(page, 50, 50, 51, 51, 2);
    expect(await annotations(page)).toHaveLength(0);
  });

  test('AT-14 — touch drawing behaves like mouse drawing', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    await page.evaluate(() => {
      const c = document.getElementById('annoCanvas')!;
      const r = c.getBoundingClientRect();
      const at = (x: number, y: number) =>
        new Touch({ identifier: 1, target: c, clientX: r.left + x, clientY: r.top + y });
      const fire = (type: string, touches: Touch[], changed: Touch[]) =>
        c.dispatchEvent(new TouchEvent(type, { bubbles: true, cancelable: true, touches, changedTouches: changed }));
      const start = at(30, 30), mid = at(90, 80), end = at(150, 120);
      fire('touchstart', [start], [start]);
      fire('touchmove', [mid], [mid]);
      fire('touchmove', [end], [end]);
      fire('touchend', [], [end]);
    });
    const list = await annotations(page);
    expect(list).toHaveLength(1);
    expect(list[0].type).toBe('rect');
  });

  test('AT-15 — dragging a pen stroke moves it without corrupting its path', async ({ page }) => {
    // Not in TEST_PLAN v1.0. Pen annotations have no x/y, so the select-tool
    // drag used to write NaN into them and that NaN reached the JSON export.
    await withImage(page);
    await selectTool(page, 'pen');
    await dragOn(page, 40, 40, 140, 120);
    const before = (await annotations(page))[0];
    const firstPoint = { ...before.path[0] };

    await selectTool(page, 'select');
    await dragOn(page, 40, 40, 90, 70);

    const after = (await annotations(page))[0];
    expect(after.path[0].x).toBeCloseTo(firstPoint.x + 50, 0);
    expect(after.path[0].y).toBeCloseTo(firstPoint.y + 30, 0);
    expect(after.path.every((p: any) => Number.isFinite(p.x) && Number.isFinite(p.y))).toBe(true);
    expect(Number.isNaN(after.x ?? 0)).toBe(false);
  });
});

/* ─── 3.4 Undo / redo ──────────────────────────────────────────────────── */

test.describe('3.4 Undo / Redo', () => {
  test('UR-02 — each undo removes exactly one annotation', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    for (const x of [20, 120, 220]) await dragOn(page, x, 20, x + 70, 90);
    expect(await annotations(page)).toHaveLength(3);

    for (const expected of [2, 1, 0]) {
      await page.click('#btnUndo');
      expect(await annotations(page)).toHaveLength(expected);
    }
  });

  test('UR-03 — undo on an empty stack does nothing', async ({ page }) => {
    const errors = collectPageErrors(page);
    await withImage(page);
    await page.click('#btnUndo');
    await page.click('#btnUndo');
    expect(await annotations(page)).toHaveLength(0);
    expect(errors).toEqual([]);
  });

  test('UR-05 — drawing after an undo clears the redo stack', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    await dragOn(page, 20, 20, 100, 80);
    await page.click('#btnUndo');
    await dragOn(page, 140, 20, 220, 80);
    await page.click('#btnRedo');
    expect(await annotations(page), 'redo must not resurrect the discarded branch').toHaveLength(1);
  });

  test('UR-06/UR-07 — Ctrl+Z and Ctrl+Y mirror the buttons', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    await dragOn(page, 20, 20, 100, 80);

    await page.keyboard.press('Control+z');
    expect(await annotations(page)).toHaveLength(0);
    await page.keyboard.press('Control+y');
    expect(await annotations(page)).toHaveLength(1);
  });
});

/* ─── 3.5 Export ───────────────────────────────────────────────────────── */

test.describe('3.5 Export', () => {
  test('EX-02 — the exported PNG contains the annotation pixels', async ({ page }) => {
    await withImage(page);
    await setControl(page, 'strokeColor', '#ff0000');
    await selectTool(page, 'rect');
    await dragOn(page, 40, 40, 240, 200);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('#btnExportPng'),
    ]);
    const b64 = (await readFile(await download.path())).toString('base64');

    // Re-open the exported file and sample the pixel where the border was drawn.
    const sampled = await page.evaluate(async (b64) => {
      const img = new Image();
      img.src = 'data:image/png;base64,' + b64;
      await img.decode();
      const c = document.createElement('canvas');
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      const ctx = c.getContext('2d')!;
      ctx.drawImage(img, 0, 0);
      // scan the top border line of the rectangle for a red pixel
      const strip = ctx.getImageData(40, 38, 200, 5).data;
      let red = 0;
      for (let i = 0; i < strip.length; i += 4) {
        if (strip[i] > 180 && strip[i + 1] < 80 && strip[i + 2] < 80) red++;
      }
      return { red, w: img.naturalWidth, h: img.naturalHeight };
    }, b64);

    expect(sampled.w).toBe(400);
    expect(sampled.h).toBe(300);
    expect(sampled.red, 'the annotation should be burned into the exported PNG').toBeGreaterThan(20);
  });

  test('EX-06 — Ctrl+S exports a PNG', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'rect');
    await dragOn(page, 20, 20, 120, 90);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.keyboard.press('Control+s'),
    ]);
    expect(isPng(await readFile(await download.path()))).toBe(true);
  });
});

/* ─── 3.6 Snapshot gallery ─────────────────────────────────────────────── */

test.describe('3.6 Snapshot Gallery', () => {
  async function exportOnce(page: any, x: number) {
    await selectTool(page, 'rect');
    await dragOn(page, x, 20, x + 70, 90);
    await Promise.all([page.waitForEvent('download'), page.click('#btnExportPng')]);
  }

  test('SG-01 — clicking a thumbnail reloads that snapshot', async ({ page }) => {
    await withImage(page);
    await exportOnce(page, 20);
    await page.click('.snapshot-thumb');
    await page.waitForTimeout(400);
    expect(await placeholderHidden(page)).toBe(true);
    expect(await canvasSize(page)).toEqual([400, 300]);
  });

  test('SG-02 — deleting a snapshot removes it from the gallery', async ({ page }) => {
    await withImage(page);
    await exportOnce(page, 20);
    expect(await snapshots(page)).toHaveLength(1);
    await page.click('.snap-del');
    expect(await snapshots(page)).toHaveLength(0);
    await expect(page.locator('.snapshot-thumb')).toHaveCount(0);
  });

  test('SG-03 — the newest snapshot is listed first', async ({ page }) => {
    await withImage(page);
    await exportOnce(page, 20);
    await page.waitForTimeout(1100);          // labels are time-based
    await exportOnce(page, 150);

    const list = await snapshots(page);
    expect(list).toHaveLength(2);
    const firstThumbId = await page.getAttribute('.snapshot-thumb', 'onclick');
    expect(firstThumbId).toContain(String(list[0].id));
  });
});

/* ─── 3.7 Keyboard shortcuts ───────────────────────────────────────────── */

test.describe('3.7 Keyboard Shortcuts', () => {
  const KEYS: [string, string, string][] = [
    ['KS-01', 'h', 'highlight'],
    ['KS-02', 't', 'text'],
    ['KS-03', 'c', 'circle'],
    ['KS-04', 'a', 'arrow'],
    ['KS-05', 'r', 'rect'],
    ['KS-06', 'p', 'pen'],
    ['KS-07', 's', 'select'],
  ];

  for (const [id, key, tool] of KEYS) {
    test(`${id} — "${key}" selects the ${tool} tool`, async ({ page }) => {
      await withImage(page);
      await page.keyboard.press(key);
      await expect(page.locator(`.tool-btn[data-tool="${tool}"]`)).toHaveClass(/active/);
      expect(await page.evaluate<string>('currentTool')).toBe(tool);
    });
  }

  test('KS — shortcuts stay inert while typing in the text popup', async ({ page }) => {
    await withImage(page);
    await selectTool(page, 'text');
    await clickOn(page, 60, 60);
    await page.fill('#textInput', 'press p and r here');
    expect(await page.evaluate<string>('currentTool')).toBe('text');
  });
});
