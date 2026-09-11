# Contributing to Test Assist (browser build)

This covers the **browser build** — the vanilla-JS app at the repo root
(`index.html`, `app.js`, `style.css`) that's live at
https://emil3663.github.io/test-assist/. If you're picking up front-end
work, this is almost certainly the codebase you want.

The **desktop build** (`python/`, PySide6/Qt, Windows-only) is a separate
codebase with its own test suite and its own `docs/DESKTOP_TEST_PLAN.md` —
not in scope here unless you're specifically asked to touch it.

## Prerequisites

- Node.js (any recent LTS) and npm
- A Chromium-based browser for day-to-day dev (Chrome/Edge); Safari 26+ and
  Firefox are also supported at runtime (Firefox via a video-frame fallback,
  since it has no `ImageCapture`)
- No Python, no build toolchain — this build has no compile/bundle step

## Getting set up

```bash
git clone https://github.com/emil3663/test-assist.git
cd test-assist
npm ci
```

## Running it locally

```bash
npm run serve      # serves the repo root at http://127.0.0.1:4321
```

Open that URL in a browser. **Don't just open `index.html` via `file://`**
— screen capture (`getDisplayMedia`) and recording (`MediaRecorder`) need a
secure context, and behave differently (or not at all) under `file://`.
`npm run serve` is a zero-dependency static server (`scripts/serve.mjs`)
built for exactly this reason.

There's no build/watch step: `app.js` is plain JavaScript, loaded directly
by `index.html`. Edit it and refresh.

## Running the tests

```bash
npx playwright install chromium   # once
npm run test:smoke                # 8 tests, ~10s — mirrors what CI runs on every push
npm run test:regression           # 47 tests, ~55s — the rest of TEST_PLAN.md, run on demand
npm run typecheck                 # tsc --noEmit over the *test* files only — app.js itself isn't typed
```

Both suites start their own static server on their own port (same reason as
above) rather than running against a shared dev server or `file://`.
`STABILITY_MATRIX.md` triages every case in `TEST_PLAN.md` and records what
each test actually proves — read it before assuming a passing test means
more than it does. One standing limitation worth knowing up front: the
native OS screen-share picker is browser chrome no automation can drive, so
capture/recording tests substitute a canvas-backed `MediaStream` — they
prove what the app does with a stream, not that the picker itself appears.

The regression suite runs single-worker with **no retries**, on purpose —
a flaky result is supposed to look flaky, not get masked by a rerun.

## How work here is scoped

Everything in this portfolio is specified before it's built: a ticket or
brief states the problem, the scope, and observable acceptance criteria
before implementation starts, and the result is checked against that
statement rather than accepted on trust (see the README's "How this was
built"). For anything beyond a small, obvious fix, write down what you're
about to do and how you'll know it's done before you start — a few sentences
is enough for most front-end tickets.

`TEST_PLAN.md` also carries the suggested GitHub label set and board columns
(`§6`) if you're filing or triaging issues.

## Deploying

There is no separate "build" artifact for this app — what's on `main` **is**
the deployed app. Pushing to `main` triggers `.github/workflows/pages.yml`,
which publishes the repo root straight to GitHub Pages (usually live within
a minute or two), and separately triggers the smoke suite
(`.github/workflows/playwright.yml`).

Because of that, **work on a branch and open a PR rather than committing
straight to `main`** — the smoke suite runs on PRs too, so a break gets
caught before it reaches the live URL, which is also the one linked from
Emil's CV and an already-sent cover letter. Merge only once it's green.

## Good starting points

Pulled straight from `TEST_PLAN.md`'s own status table and roadmap — nothing
invented for this doc:

**Known gaps (§2/§4 of TEST_PLAN.md), not yet started:**
- Annotation labels / numbered callouts (① ② ③)
- PDF export (PNG/JSON only today)
- Cloud save / share
- Frame-by-frame video annotation

**Roadmap (§5), in rough order:**
1. **Sprint 1** — persist snapshots in `localStorage`; numbered callout
   annotation type
2. **Sprint 2** — blur/pixelate tool (redacting sensitive info before
   export), measurement ruler, stamp/emoji overlay, an annotation list panel
3. **Sprint 3** — share via a unique URL (Supabase Storage or Cloudinary),
   per-annotation comment threads, PDF export
4. **Sprint 4** — frame-by-frame video scrubbing, overlay annotations on
   video frames, export annotated video as GIF/MP4

Sprint 1/2 items are reasonable first PRs — self-contained, no new backend.
Sprint 3 onward introduces a real backend dependency (Supabase/Cloudinary)
and is worth a short written scope (see "How work here is scoped" above)
before starting, since it's a bigger decision than the ticket text alone
covers.

## Getting access

Repo collaborator access is something Emil grants directly on GitHub
(Settings → Collaborators) — this doc doesn't cover that step since it isn't
something either of us can do from here.
