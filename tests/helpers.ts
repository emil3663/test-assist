import { Page, expect } from '@playwright/test';
import { deflateSync } from 'node:zlib';

/* ─── App lifecycle ─────────────────────────────────────────────────────── */

/**
 * Load the app and wait on its ready signal rather than a fixed timeout.
 * `window.__APP_READY__` is set at the end of app.js, so waiting on it means
 * every listener is bound before a test touches anything.
 */
export async function gotoApp(page: Page) {
  await page.goto('/');
  await page.waitForFunction(() => (window as any).__APP_READY__ === true);
}

/** Collect alert()/confirm() text. The app uses alert() for capture failures. */
export function collectDialogs(page: Page): string[] {
  const seen: string[] = [];
  page.on('dialog', d => { seen.push(d.message()); d.dismiss().catch(() => {}); });
  return seen;
}

/** Collect uncaught page errors so every test can assert the page stayed clean. */
export function collectPageErrors(page: Page): string[] {
  const seen: string[] = [];
  page.on('pageerror', e => seen.push(String(e)));
  return seen;
}

/* ─── App state ─────────────────────────────────────────────────────────── */
/*
 * app.js is a classic script, so its top-level `let` bindings (annotations,
 * snapshots, undoStack…) are global lexical bindings rather than properties of
 * window. They are reachable from page.evaluate via the string form, which
 * means no test-only state-seeding hook had to be added to the app.
 */

export const annotations = (page: Page) => page.evaluate<any[]>('annotations');
export const snapshots   = (page: Page) => page.evaluate<any[]>('snapshots');
export const canvasSize  = (page: Page) =>
  page.evaluate<[number, number]>('[baseCanvas.width, baseCanvas.height]');

export const placeholderHidden = (page: Page) =>
  page.evaluate(() => getComputedStyle(document.getElementById('placeholder')!).display === 'none');

/** Seed annotations directly, for cases that need a populated canvas as a precondition. */
export async function seedAnnotations(page: Page, items: any[]) {
  await page.evaluate((list) => {
    (globalThis as any).eval('annotations').length = 0;
    (globalThis as any).eval('annotations').push(...list);
    (globalThis as any).eval('redrawAnnotations')();
  }, items);
}

/* ─── Interaction ───────────────────────────────────────────────────────── */

export const selectTool = (page: Page, tool: string) =>
  page.click(`.tool-btn[data-tool="${tool}"]`);

/** Drag on the annotation canvas in canvas-local coordinates. */
export async function dragOn(page: Page, x1: number, y1: number, x2: number, y2: number, steps = 10) {
  const box = (await page.locator('#annoCanvas').boundingBox())!;
  await page.mouse.move(box.x + x1, box.y + y1);
  await page.mouse.down();
  await page.mouse.move(box.x + x2, box.y + y2, { steps });
  await page.mouse.up();
}

export async function clickOn(page: Page, x: number, y: number) {
  const box = (await page.locator('#annoCanvas').boundingBox())!;
  await page.mouse.click(box.x + x, box.y + y);
}

/** Move a range/colour input and fire the `input` event the app listens for. */
export async function setControl(page: Page, id: string, value: string) {
  await page.evaluate(([id, value]) => {
    const el = document.getElementById(id) as HTMLInputElement;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }, [id, value]);
}

export async function uploadImage(
  page: Page, buffer: Buffer, name = 'fixture.png', mimeType = 'image/png',
) {
  await page.setInputFiles('#uploadImage', { name, mimeType, buffer });
  await page.waitForFunction(
    () => getComputedStyle(document.getElementById('placeholder')!).display === 'none',
  );
}

/** Drop a file onto the canvas area, exercising the real dragover/drop handlers. */
export async function dropFile(page: Page, name: string, type: string, base64: string) {
  await page.evaluate(async ({ name, type, base64 }) => {
    const bin = atob(base64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const file = new File([bytes], name, { type });
    const dt = new DataTransfer();
    dt.items.add(file);
    const wrap = document.querySelector('.canvas-wrap')!;
    wrap.dispatchEvent(new DragEvent('dragover', { dataTransfer: dt, bubbles: true, cancelable: true }));
    wrap.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
  }, { name, type, base64 });
}

/* ─── Screen-capture stubbing ───────────────────────────────────────────── */
/*
 * getDisplayMedia always shows a native picker that no automation can drive,
 * so these tests substitute a canvas-backed MediaStream. That means the
 * PROMPT itself is never asserted — what is covered is everything the app does
 * once a stream exists (or once the user declines). The stream is animated
 * because ImageCapture.grabFrame() rejects on a track that has not yet
 * produced a frame.
 */
export type CaptureMode =
  | 'grant'                  // stream available, ImageCapture present (Chrome/Edge/Safari)
  | 'grant-no-imagecapture'  // stream available, ImageCapture absent (Firefox)
  | 'deny'                   // user dismisses the picker
  | 'error'                  // the device fails
  | 'unsupported';           // no getDisplayMedia at all (older Safari, iOS)

export async function stubDisplayMedia(page: Page, mode: CaptureMode = 'grant', w = 640, h = 480) {
  await page.addInitScript(({ mode, w, h }) => {
    if (mode === 'grant-no-imagecapture') delete (window as any).ImageCapture;

    if (mode === 'unsupported') {
      // getDisplayMedia lives on MediaDevices.prototype, so `delete` on the
      // instance is a no-op — shadow it with undefined instead
      Object.defineProperty(navigator.mediaDevices, 'getDisplayMedia', {
        value: undefined, configurable: true, writable: true,
      });
      return;
    }

    (navigator.mediaDevices as any).getDisplayMedia = async () => {
      if (mode === 'deny') {
        const e: any = new Error('Permission denied'); e.name = 'NotAllowedError'; throw e;
      }
      if (mode === 'error') {
        const e: any = new Error('Device unreadable'); e.name = 'NotReadableError'; throw e;
      }
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      const ctx = c.getContext('2d')!;
      let i = 0;
      const paint = () => {
        ctx.fillStyle = (i++ % 2) ? '#204080' : '#2a5090';
        ctx.fillRect(0, 0, w, h);
      };
      paint();
      (window as any).__stubPaint = setInterval(paint, 40);
      const stream = c.captureStream(30);
      (window as any).__stubStream = stream;
      return stream;
    };
  }, { mode, w, h });
}

/** Apply a browser-style page zoom. */
export const setZoom = (page: Page, factor: number) =>
  page.evaluate((z) => { document.body.style.zoom = String(z); }, factor);

/* ─── Image fixtures ────────────────────────────────────────────────────── */
/*
 * Generated rather than committed, so the repo stays free of binary fixtures
 * and each test states the exact dimensions its assertion depends on.
 */

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(buf: Buffer): number {
  let c = 0xffffffff;
  for (const b of buf) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type: string, data: Buffer): Buffer {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
}

/** Build a solid-colour PNG. Pass alpha to get a 32-bit PNG with transparency. */
export function pngBuffer(w: number, h: number, rgb: [number, number, number], alpha?: number): Buffer {
  const hasAlpha = alpha !== undefined;
  const px = hasAlpha ? [...rgb, alpha!] : rgb;
  const row = Buffer.concat([Buffer.from([0]), Buffer.from(Array(w).fill(px).flat())]);
  const raw = Buffer.concat(Array(h).fill(row));
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = hasAlpha ? 6 : 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

/** Encode a JPEG using the browser, so no image library is needed. */
export async function jpegBuffer(page: Page, w = 240, h = 180): Promise<Buffer> {
  const dataUrl = await page.evaluate(({ w, h }) => {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const x = c.getContext('2d')!;
    x.fillStyle = '#3366aa'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#ffcc00'; x.fillRect(w / 4, h / 4, w / 2, h / 2);
    return c.toDataURL('image/jpeg', 0.9);
  }, { w, h });
  return Buffer.from(dataUrl.split(',')[1], 'base64');
}

export const isPng = (buf: Buffer) =>
  buf.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));

/** Read one pixel out of a canvas as [r,g,b,a]. */
export const pixelAt = (page: Page, canvas: 'baseCanvas' | 'annoCanvas', x: number, y: number) =>
  page.evaluate<number[]>(
    `Array.from(${canvas}.getContext('2d').getImageData(${x}, ${y}, 1, 1).data)`,
  );

export { expect };
