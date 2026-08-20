# 🔍 Test Assist — Browser build stability matrix

**Version:** 1.1
**Last updated:** 2026-08-20
**Applies to:** the browser build only. The desktop build is covered by 29
pytest regression tests under `python/tests/`.

---

## Why this document exists

Converting all 54 `TEST_PLAN.md` cases straight into Playwright tests would
produce a suite where some tests are trustworthy and some fail at random, with
no way to tell which is which without running it repeatedly. Every case is
triaged here first, with the reason for its classification, so the suite's
coverage claim can be checked rather than taken on trust.

| Stability | Meaning |
|---|---|
| **Stable** | Deterministic. Stable selectors, no external services, no timing dependency. |
| **Moderate** | Deterministic in behaviour but depends on timing or on a substituted browser API. |
| **Flaky** | Would fail intermittently without further harnessing. |
| **Blocked** | Cannot be automated in this environment; needs capability the test runner does not have. |

---

## The honest caveat about screen capture

`getDisplayMedia` always raises a **native picker that no automation can
drive** — it is browser chrome, not page content. Every capture and recording
test substitutes a canvas-backed `MediaStream` in its place.

That means these tests cover everything the app does *once a stream exists, or
once the user declines* — the `ImageCapture` path, canvas sizing, the
`MediaRecorder` lifecycle, the download, error handling. They do **not** prove
the picker appears, and they do not prove real screen pixels arrive. Those two
things remain manual checks. Cases relying on the substitution are marked
**Moderate** rather than Stable for exactly this reason.

The substituted stream is animated, because `ImageCapture.grabFrame()` rejects
on a track that has not yet produced a frame — a real source of false failures
if the stub paints only once.

---

## App-side changes needed to reach this coverage

Far fewer than expected:

- **`window.__APP_READY__`** — one line at the end of `app.js`. Tests wait on
  it instead of guessing a timeout after load, which is the single biggest
  source of "sometimes it works" flakiness.
- **Stable element IDs** — *no work required*. Every control the test plan
  references already had an `id`, and all 29 `getElementById` calls in `app.js`
  resolve against `index.html`.
- **A state-seeding hook** — *not needed*. `app.js` is a classic script, so its
  top-level bindings (`annotations`, `snapshots`, `currentTool`) are reachable
  from `page.evaluate`. No test-only seeding code was added to the app.

---

## Coverage summary

| | Count |
|---|---|
| Cases in `TEST_PLAN.md` v1.2 | 61 |
| Automated and passing | 60 |
| Blocked | 1 (VR-04) |
| Cases added during triage | 7 (from an original 54) |
| Automated tests | 49 (8 smoke, 41 regression) |

Four defects were found by writing these tests; all are fixed and all now have
a regression test — see **Defects found** below.

---

## 3.1 Image Capture & Upload

| ID | Stability | Suite | Notes |
|----|-----------|-------|-------|
| IC-01 | Moderate | smoke | Substituted stream; picker itself not asserted |
| IC-02 | Moderate | regression | Stub rejects with `NotAllowedError`; asserts the decline is silent |
| IC-03 | Stable | smoke | `setInputFiles` with a generated PNG |
| IC-04 | Stable | regression | JPEG encoded in-browser, so no image library is needed |
| IC-05 | Stable | regression | Asserts the alpha channel survives, by sampling a canvas pixel |
| IC-06 | Stable | regression | 4200×600; asserts canvas dimensions and no page error |
| IC-07 | Stable | regression | Real `dragover`/`drop` events with a `DataTransfer` |
| IC-08 | Stable | regression | Non-image drop must be ignored silently |
| IC-09 | Moderate | regression | **Added.** With `ImageCapture` removed (as in Firefox), capture must still succeed through the video-frame fallback |
| IC-10 | Stable | regression | **Added.** With no `getDisplayMedia` at all, the user must be pointed at Upload Image |

## 3.2 Video Recording

| ID | Stability | Suite | Notes |
|----|-----------|-------|-------|
| VR-01 | Moderate | regression | Substituted stream |
| VR-02 | Moderate | regression | Timing-dependent; waits for the counter to leave `00:00` rather than asserting a specific value |
| VR-03 | Moderate | regression | Asserts a non-empty `.webm` actually downloads |
| VR-04 | **Blocked** | — | Requires clicking the browser's own "Stop sharing" bar, which is browser chrome and unreachable from the page. Would need a real screen-share session driven at the OS level. |
| VR-05 | Stable | regression | Stub rejects; asserts silence and that the button re-arms |
| VR-06 | Moderate | regression | Covered alongside VR-03 |

## 3.3 Annotation Tools

| ID | Stability | Suite | Notes |
|----|-----------|-------|-------|
| AT-01 | Stable | smoke | |
| AT-02 | Stable | smoke | |
| AT-03 | Stable | regression | Multi-line text preserved through the popup |
| AT-04 | Stable | regression | Cancel adds nothing |
| AT-05 – AT-08 | Stable | smoke | Covered as one drag-tool sweep |
| AT-09 | Stable | regression | **Found a defect** — see below |
| AT-10 | Stable | regression | Also asserts existing annotations do *not* change colour |
| AT-11 | Stable | regression | |
| AT-12 | Stable | regression | |
| AT-13 | Stable | regression | Sub-3px drag must add nothing |
| AT-14 | Moderate | regression | Synthetic `TouchEvent`s; real hardware touch is still a manual check |
| AT-15 | Stable | regression | **Added.** Dragging a pen stroke — see the second defect below |
| AT-16 | Stable | regression | **Added.** Drawing with the page zoomed. Added to disprove a documented limitation, not to cover one |

## 3.4 Undo / Redo

| ID | Stability | Suite | Notes |
|----|-----------|-------|-------|
| UR-01 | Stable | smoke | |
| UR-02 | Stable | regression | |
| UR-03 | Stable | regression | Undo on an empty stack must not throw |
| UR-04 | Stable | smoke | |
| UR-05 | Stable | regression | Redo stack cleared by a new annotation |
| UR-06 | Stable | regression | Also satisfies KS-08 |
| UR-07 | Stable | regression | Also satisfies KS-09 |
| UR-08 | Stable | regression | **Added.** Moves are undoable, and a bare click adds no undo step |

## 3.5 Export

| ID | Stability | Suite | Notes |
|----|-----------|-------|-------|
| EX-01 | Stable | smoke | Asserts the PNG signature, not just that a file arrived |
| EX-02 | Moderate | regression | Re-opens the exported PNG and samples pixels along the drawn border |
| EX-03 | Stable | smoke | |
| EX-04 | Stable | smoke | |
| EX-05 | Stable | smoke | Asserts every field the README documents, so the docs cannot drift |
| EX-06 | Stable | regression | Also satisfies KS-10 |

## 3.6 Snapshot Gallery

| ID | Stability | Suite | Notes |
|----|-----------|-------|-------|
| SG-01 | Stable | regression | |
| SG-02 | Stable | regression | |
| SG-03 | Stable | regression | Was Moderate: it needed a one-second wait between exports until snapshot ids stopped colliding |
| SG-04 | Stable | regression | **Added.** Two exports in the same millisecond — see the fourth defect below |

## 3.7 Keyboard Shortcuts

| ID | Stability | Suite | Notes |
|----|-----------|-------|-------|
| KS-01 – KS-07 | Stable | regression | One parameterised test per key |
| KS-08 | Stable | regression | Covered by UR-06 |
| KS-09 | Stable | regression | Covered by UR-07 |
| KS-10 | Stable | regression | Covered by EX-06 |
| KS-11 | Stable | regression | **Added.** Shortcuts must stay inert while typing in the text popup |

---

## Defects found by writing these tests

All four are fixed, and each has a regression test that would catch it coming
back.

**1. Dragging a shape deformed it instead of moving it.** `onMouseMove` moved
`x`/`y` but left `x2`/`y2` where they were, so a rectangle dragged 100px to the
right became 100px wider rather than moving. Caught by AT-09.

**2. Dragging a pen stroke wrote `NaN` into the annotation.** Pen annotations
store a `path` and have no `x`/`y`, but the drag handler computed its offset
from `selectedAnnotation.x` — `undefined`. The stroke did not move, and the
`NaN` coordinates then reached the exported JSON. Caught by AT-15.

Both are now handled by a single `moveAnnotation(a, dx, dy)` that translates
every geometry an annotation can carry.

**3. Snapshot ids collided.** Ids were `Date.now()` alone, so two exports in the
same millisecond shared one id — deleting either removed both, and clicking a
thumbnail could load the wrong one. Caught by SG-04. This one is worth noting
as a process point: the first version of SG-03 papered over it with a
one-second `waitForTimeout` between exports. A sleep that exists to avoid a
collision is a defect in disguise, and removing it is what exposed this.

**4. The page 404'd on `/favicon.ico`** on every visit, which the smoke suite's
"no console errors" assertion caught immediately. Fixed with an inline SVG
icon.

---

## Suite design

Two configs rather than one config with tags:

| | Smoke | Regression |
|---|---|---|
| Config | `playwright.smoke.config.ts` | `playwright.regression.config.ts` |
| Runs | Every push, via CI | On demand |
| Tests | 8 | 41 |
| Wall clock | ~10s | ~50s |
| Parallel | yes | **no** — `workers: 1` |
| Retries | **0** | **0** |
| Port | 4321 | 4322 |

`retries: 0` on both is deliberate. A retry converts a flaky test into a
passing one and hides the flakiness; the point of this exercise is the
opposite. The regression suite additionally runs single-worker so a failure
cannot be blamed on cross-worker interference.

Both suites start their own instance of `scripts/serve.mjs` on their own port,
rather than running against `file://` or a dev server someone left running.
`file://` in particular is not a secure context, so `getDisplayMedia` and
`MediaRecorder` behave differently there than they do on the published site.

## Running them

```bash
npm ci
npx playwright install chromium
npm run test:smoke        # ~10s
npm run test:regression   # ~50s
```
