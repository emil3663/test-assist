# Session handover — 11 September 2026

Martin spent a day on the repo from a Mac. This is what changed, why, where it
deviated from your direction, what needs your decision, and how to get an agent
to review it usefully.

**Nothing here is merged.** Five PRs are open and every one can be rejected
without losing the others.

---

## 1. Read the commit messages first

This is the single most useful instruction in this document, for you and for
any agent you point at the repo.

**23 commits carry 6,397 words of rationale — a median of 256 words each.**
They are not "fixed the thing". They state the problem, the measurement that
justified the fix, the approach chosen, **the approaches rejected and why**,
and what the change deliberately does not do.

```bash
git log origin/main..ui-polish        # the UI work, 15 commits
git log origin/main..macos-support    # macOS, 4
git log origin/main..hidpi-capture    # the capture fix, 1
```

Almost every "why is it like this?" you or a reviewer will have is answered
there rather than in the diff. An agent reviewing the diff alone will
re-derive conclusions already written down, and will occasionally "fix"
something that is deliberate.

**If you take one habit from this: the commit body is where the reasoning
goes.** The code says what; the message says why, and it is the only record
that survives a refactor.

---

## 2. Commit format

`docs/CONVENTIONAL_COMMITS.md` (PR #10) proposes Conventional Commits:

```
<type>(<scope>): <subject>

<body — the why, the alternatives rejected, what this does not do>

Closes #N
```

Types: `feat` `fix` `docs` `test` `refactor` `build` `chore` `revert`.
Scopes drawn from the actual modules: `capture` `canvas` `editor` `launcher`
`hotkeys` `geometry` `theme` `build` `tests` `docs` `browser`.

Three arguments for it, all specific to this repo:

- `CHANGELOG.md` is maintained by hand, so every user-visible change is
  written twice and can drift.
- `v1.0.0`, `v1.1.0`, `v1.3.0` were tagged with nothing mechanical connecting
  a set of commits to the number that follows.
- `git log v1.1.0..v1.3.0` cannot be filtered to "what would a user notice".

**No tooling is added on purpose.** A commit linter that rejects messages
before anyone has internalised why is a good way to make people resent a
convention. `commitlint` and `release-please` are worth their own issue once
the habit exists — and the automated changelog is the actual payoff.

**Applies from the next commit. History is not rewritten** — which is why
three of the 23 commits here are not in the format. They were written before
the convention existed, and rewriting them would contradict it.

The worked examples in that document are rewrites of **your own history**,
including two real commits that turn out to be four commits each. That is the
point of the convention, not a criticism of the messages.

---

## 3. Design decisions, and the reasoning

These are the choices a reviewer is most likely to question. Each was
deliberate.

**Chrome follows the OS theme. The canvas never does.**
Light/dark is a strict binary read once at startup, with no in-app toggle and
nothing persisted. It styles the app's own surfaces only and never reaches
`canvas.py`. Annotations are painted on the user's screenshot, so the same
defect marked up on a light machine and a dark one must export identical
evidence — a tester's appearance setting should not be visible in a bug
report. A test asserts `canvas.py` imports no palette token, so the
separation cannot erode by accident.

**Icons are a font, not SVG assets.**
Both are crisp. Only a font takes its colour from the text it is, so icons
follow the palette for free and will keep doing so for any palette added
later. SVG would need two icon sets or runtime tinting for the same result.

**In `help.html`, the same glyphs are outlines, not a webfont.**
That page opens as a `file://` URI and browsers refuse font loads across that
origin — an `@font-face` would render tofu on exactly the path the app
actually uses.

**Captures are stored at device resolution and left untagged at ratio 1.0.**
The obvious fix — `setDevicePixelRatio()` on the result — is wrong here and
quietly so: `canvas.py` measures annotation coordinates *and* its own widget
size from `_pixmap.width()`, which is device pixels. A tagged pixmap would
render into a quarter of the widget and halve every annotation's position.

**The menu bar is parentless.**
A `QMenuBar` owned by a window is only the macOS menu bar while that window is
active, and Test Assist normally starts with the editor constructed but not
shown. About and Quit carry `MenuRole`s so macOS moves them into the
application menu while Windows keeps them under Help and File — one action,
both conventions.

**The text plate is stored per annotation, not read at paint time.**
So an exported JSON layer re-renders the way it looked when it was made.
Changing the default later must not silently restyle evidence already taken.

**One PyInstaller spec for both platforms**, guarded by `sys.platform`, so the
`datas`/`excludes` lists cannot drift. Those are the parts that decide whether
a build works and they are identical either way. The Windows path is untouched.

**The depth layer is additive only** — `background-image` gradients with alpha
stops, never `background-color`. Every fill still comes from the tokens, no
contrast ratio moves, and it can be removed by deleting three rules.

---

## 4. Where this deviated from your direction

The honest section. Four places.

### The launcher rebuild — the big one (PR #19, issue #11)

Your current floating panel had **nine controls, two of them labelled**. The
original design in `help.html` had six and labelled all of them. The redesign
had been optimised for footprint while controls kept accruing, and the two
goals collided.

What was wrong, concretely: the Photo/Video toggle sat beside the capture
button, so what "Quick Capture" did depended on an unlabelled control next to
it — and that toggle shared a row with Full Screen, so a radio pair and an
action looked identical.

**This reverses a deliberate decision of yours, and the footprint gain was
real.** The rebuilt panel is roughly three times the height. It is only
defensible because the docked strip exists to be the compact mode — so the
panel does not need to be compact, and can go back to being the descriptive
one.

If you disagree, `ca71881` is the commit to drop. Everything else in that PR
stands without it.

### The mode concept is gone entirely

Not softened — removed. `_mode`, `_set_mode`, `_on_action_click`. Each action
is its own button. If you wanted a mode for a reason not visible in the code,
this is the change to push back on.

### Windows-only scoping

`CONTRIBUTING.md` described the desktop build as Windows-only. PR #9 changes
that to one sentence, and leaves your scoping prose alone.

Worth being clear about why that line was there: it was not a limitation of
the code — Qt was already doing the cross-platform work, which is why **315 of
320 tests passed unmodified on a Mac before anything was changed**. It was a
limitation of what you could verify, which is the same instinct behind your
stability matrices. What changed is the hardware available, not the judgement.

### One place we deliberately did *not* deviate

You added `CONTRIBUTING.md` for the incoming front-end developer while this
work was in flight. PR #10 originally added one of its own, which collided.
**Yours was kept as-is** and the process content moved to
`docs/WORKING_AGREEMENTS.md`, with a four-line pointer added to your file and
nothing else touched. Yours is scoped to the browser build for a real person
arriving, and carries setup detail the other did not.

Its label set was also dropped rather than merged: `TEST_PLAN.md` §6 already
has one, and a second list in a second file is how two records start
disagreeing.

---

## 5. What needs your decision

| # | Question | Notes |
|---|---|---|
| — | **Review order** | #12 and #8 first (one line, four files), then #9, then #19. #19 is based on #9 and retargets to `main` when that merges. #10 any time. |
| #11 | **Accept or reject the launcher rebuild** | The one real judgement call. Footprint vs descriptiveness. |
| — | **Is macOS supported, or "runs from source"?** | Changes what you promise and what you have to keep working. |
| #15 | **The JSON export** | It cannot do what the README claims — no image reference, no dimensions, no importer anywhere. Add the fields (~1 hour) or soften the README. They only need to stop disagreeing. |
| #13 | **Code signing** | The one thing between "works" and "a stranger can install it". Free routes exist — see below. |
| #14 | **Recording length cap** | No cap, no warning today. A product decision, not a bug. |
| #2 | **Whether TA-225 is the same bug** | The HiDPI fix makes captures *softer*, never blank; TA-225 reports blank. Probably unrelated — re-run its repro on a build with the fix before closing it. |

### On signing, since it looks like a wall

Hosting does not matter. SmartScreen and Gatekeeper are client-side OS checks
— SourceForge, GitHub Releases and your own site produce identical warnings.

Routes worth investigating (verify current terms — these change):

- **Microsoft Store** — individual accounts are free and **Microsoft signs
  Store apps for you**, so no certificate is needed. Cost is MSIX packaging
  and review, not money.
- **SignPath Foundation** — free code signing for open-source projects. MIT
  with a public repo likely qualifies.
- **Azure Trusted Signing** — roughly $10/month rather than £200–400/year;
  individuals need several years of verifiable identity history.
- **Apple** — $99/year, no free tier, no open-source exemption.

**The browser build sidesteps all of it** and is already live. If the goal is
reach rather than depth, that is the shorter road.

---

## 6. What was found that you could not have found

All four are hardware-dependent and invisible on a 1.0-ratio Windows machine.

1. **HiDPI capture discarded three quarters of every pixel** (#2). A 400×300
   selection on a 2.0-ratio display grabbed 800×600 real pixels and exported
   400×300. Hits Windows at 125%/150% scaling too — the common laptop setup.
2. **Text annotations lost their background on commit.** The plate existed
   only while typing, so text was readable as you authored it and gone in the
   exported PNG. A red note over a red error banner exported as an empty box.
3. **Hardcoded `Segoe UI` changed exported annotation layout.** Five of the
   seven call sites are in `canvas.py`, where font metrics drive text wrapping
   — so on any machine without that font it was the *evidence* that laid out
   differently, not just the chrome.
4. **Global hotkeys took the app down at startup** on any non-Windows
   platform.

**Your tests caught three mistakes of ours**, which is worth more than the
above: the contrast test caught a regression that put white labels at 2.65:1;
the version test caught `help.html` being edited without bumping `main.py`;
and running the suite on Windows caught three `skipif`-guarded tests that a
Mac reports green on by construction.

---

## 7. Briefing an agent to review the code

### Read first, and do not re-report

`STABILITY_MATRIX.md`, `DESKTOP_STABILITY_MATRIX.md`, `TESTASSIST_BACKLOG.md`
(TA-201–TA-228), the 13 open issues, and **the commit messages in §1**. This
repo documents its own weaknesses better than most commercial codebases. A
review whose findings are all already written down has cost more than it
returned.

### The four places the tests structurally cannot see

This is where the value is. "Find bugs" will mostly rediscover the backlog.

1. **`skipif`-guarded platform paths.** 14 tests run on one OS only. Every
   other platform runs a suite that *cannot fail* for those paths. This caused
   two live breakages in one week.
   `test_LAUNCH_09_every_launcher_attribute_this_suite_names_exists` guards one
   shape of it — look for the shapes it does not cover.
2. **Paths the suite deliberately avoids.** `register_global_hotkeys=True`
   claims real OS state, so nearly every test omits it — which left
   `_apply_hotkey_labels()` uncovered until it crashed the app on startup. Look
   for other default-off flags, and for `monkeypatch` replacing the thing under
   test.
3. **Offscreen rendering proves logic, not appearance.** It cannot show that
   Qt dispatches events in a real window, that a layout is usable, that
   anything is legible, or that a capture on mixed-DPI hardware is the right
   size. Hunt for other logical-vs-device-pixel confusion in `capture.py`,
   `canvas.py`, and anything touching `grabWindow`, `QPixmap` or
   `devicePixelRatio`.
4. **The browser capture picker cannot be automated.** Tests substitute a
   canvas-backed `MediaStream` — they prove what the app does *with* a stream,
   not that acquiring one works.

### Specific targets

- `canvas.py` (1,587 lines) — annotation geometry, hit-testing, text wrapping.
  The largest module and the one whose output *is* the product.
- `capture.py` — `plan_capture()` multi-monitor packing. TA-209 documents a
  known gap for layouts separated on both axes.
- **Coordinate spaces generally.** Annotations live in the captured image's
  pixel space; selections are dragged in logical pixels; screens have
  independent ratios. Every bug found so far has lived at that boundary.
- `_prune_unreadable_history()` deletes from a real user directory on every
  launch. Check the `conftest.py` isolation assertion is actually sufficient.
- Qt object lifetime — timers, threads, ctypes callbacks, the parentless menu
  bar, the tray icon. Losing the last Python reference is a crash, not a leak.

### What good output looks like

- **Measured evidence, not impressions.** "Adds 195 ms to launch, measured"
  beats "feels slow".
- **A named failure scenario per finding** — concrete inputs, concrete wrong
  outcome. If you cannot write one, it is an observation.
- **Say what you could not check.** A reviewer who has not run it on Windows
  should say so. That is the house style — see the stability matrices.
- **Say which build** a finding applies to.
- **Rank by consequence to the evidence.** This tool's output is attached to
  defect reports. A bug that silently degrades an exported PNG matters more
  than an awkward UI.

### What not to do

- Do not rewrite history, reformat files, or modernise working code.
- Do not add dependencies casually — the desktop build has three, on purpose,
  and the browser build has none at runtime.
- Do not weaken a test to make a change pass. If a test is wrong, say why in
  the same breath as changing it.

---

## 8. Running it

```bash
# desktop
cd python && pip install -r requirements.txt
pytest -q                 # 351 tests, ~12s
python main.py            # or ./run.ps1 (Windows) / ./run.sh (macOS, Linux)
./build.sh --zip          # macOS .app  (build.ps1 -Zip on Windows)

# browser
npm ci && npx playwright install chromium
npm run serve             # http://127.0.0.1:4321 — not file://
npm run test:smoke        # 8 tests
npm run test:regression   # 47, single-worker, no retries on purpose
```

The macOS artefact is `python/dist/Test Assist.app`. Ignore `python/build/` —
the `TestAssist.pkg` in there is PyInstaller's own archive, not an installer,
and double-clicking it gives `com.apple.installer.pagecontroller error -1`.
