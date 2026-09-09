# Test Assist — Outstanding Work Backlog

**Version:** 1.0
**Date:** 2026-09-02
**Status:** Multi-display fix complete and verified (216 tests), uncommitted

## Where things stand

`v1.3.0` is released and downloadable. On top of it, uncommitted in the working
tree: the issue #1 multi-display fix, the version stamped into `help.html`, and
the in-app About dialog with bug-report diagnostics. 216 tests pass with the
network hard-blocked; the geometry was spot-checked against a negative-x layout
and a spanning selection.

Everything below is what remains.

## Scope

### In scope
1. Commit and release the multi-display work as v1.4.0
2. Move app data out of `~/.test-assist` to discoverable, update-safe locations
3. Bring `help.html` back in line with what the app actually does
4. The manual passes that no automation here can perform

### Out of scope
- Three-or-more-monitor layouts (geometry should generalise; unproven)
- Live display hot-plug handling while the app runs
- macOS or Linux — this project targets Windows

---

## Backlog

### TA-201 — Commit and push the multi-display fix

- **Phase:** 1
- **Priority:** P0
- **Suggested labels:** `bug`, `capture`
- **Problem it solves:** The fix for issue #1 exists only in the working tree.
  Until it is committed, nothing else can build on it and a lost workspace loses
  a day's work.
- **Scope:**
  - Commit the six-site multi-display fix, `screen_geometry.py`, the help.html
    version stamping, and the About dialog.
  - Push to `origin/main`.
- **Deliverables:**
  - One commit on `main`, CI green.
- **Acceptance criteria:**
  - `git status` clean, in sync with origin.
  - Python Tests workflow passes on the pushed commit.
- **Dependencies:** None.

### TA-202 — Move app data out of `~/.test-assist`

- **Phase:** 1
- **Priority:** P0
- **Suggested labels:** `enhancement`, `data`, `technical-debt`
- **Problem it solves:** `~/.test-assist/recordings` is undiscoverable on
  Windows — a dot-prefixed folder is a Unix convention users do not look in.
  Worse, the documented update procedure ("replace the contents of the folder you
  run it from") means that if data ever moved into the install directory it would
  be destroyed on every update. Recordings must live somewhere visible and
  update-safe; history must live somewhere an auto-pruning routine can safely
  delete from.
- **Scope:**
  - New `paths.py` as the single resolution seam: `recordings_dir()`,
    `history_dir()`, `legacy_dir()`.
  - Recordings and exports → `DocumentsLocation` / `Test Assist`.
  - History → `AppLocalDataLocation` (auto-pruned; must never be under Documents).
  - Decide and state whether `setOrganizationName` is dropped — it currently
    produces `AppData\Local\TestAssist\Test Assist\`. Nothing else depends on it;
    `single_instance.py` uses its own hardcoded server name.
  - Resolve lazily inside the functions — `QStandardPaths` needs a live
    `QCoreApplication` for app-name-derived paths.
  - One-time best-effort migration from `~/.test-assist` on startup, wrapped so
    it can never block launch.
  - "Open containing folder" from the save-complete status message.
- **Deliverables:**
  - `paths.py`, migration routine, updated `capture.py` and `editor.py`.
  - Test isolation moved off `Path.home()` onto the new seam.
- **Acceptance criteria:**
  - A recording from source lands in `Documents\Test Assist\`; history in
    `AppData\Local\…`.
  - A populated `~/.test-assist` migrates once, then is not touched again.
  - Suite green with an assertion that a path produced by the app is under
    `tmp_path` — the isolation is verified, not assumed.
  - The real Documents and AppData folders are untouched by a full suite run.
- **Dependencies:** TA-201.
- **Reference:** `data-locations-brief.md`

### TA-203 — Bring `help.html` in line with the app

- **Phase:** 1
- **Priority:** P1
- **Suggested labels:** `documentation`
- **Problem it solves:** The help file has drifted behind three releases and
  contains a false statement shipped in v1.3.0: recordings are described as
  saved "to your home folder" when they are in a subfolder of it. MP4 is not
  mentioned at all despite being the headline v1.3.0 feature. A user who cannot
  find their recording concludes the tool lost their evidence.
- **Scope:**
  - Correct the recordings location — to the **new** path from TA-202.
  - Add: MP4 assembly and the frame-sequence fallback; the three-minute cap and
    1280px scaling; Check for Updates (manual, contacts nothing unless pressed,
    and how to install an update); About / Copy details for a bug report;
    multi-display behaviour.
  - Decide whether to pin the shortcuts table with a test comparing it to the
    shortcuts actually registered — report the judgement rather than assuming.
- **Deliverables:**
  - Updated `help.html`; `CHANGELOG.md` entry.
- **Acceptance criteria:**
  - No statement in `help.html` is false of the code as committed.
  - Every user-visible feature shipped since v1.1.0 appears.
- **Dependencies:** TA-202. *Sequencing matters: written before TA-202, the
  recordings path would be corrected to a value that TA-202 immediately
  invalidates.*

### TA-204 — Manual multi-display pass on real hardware

- **Phase:** 2
- **Priority:** P0
- **Suggested labels:** `bug`, `needs-hardware`
- **Problem it solves:** The multi-display geometry is covered by unit tests
  against synthetic layouts. Nothing proves a real `grabWindow` on a real
  secondary monitor returns the right pixels, and mixed-DPI compositing is
  recorded as Blocked. Issue #1 cannot honestly be closed on automated evidence.
- **Scope:**
  - Run all 18 cases in `MULTI_DISPLAY_MANUAL_PASS.md` against a **built
    executable**, not a source checkout.
  - Vary arrangement (right / left / above) and per-monitor scaling in Windows
    display settings between runs — one extra monitor covers every variant.
  - Record the outcome in `SMOKE_TEST.md` with the date and exact configurations.
- **Deliverables:**
  - Completed checklist; `SMOKE_TEST.md` entry.
- **Acceptance criteria:**
  - Every case has a real ✅ or ❌ — none left ⬜.
  - Any failure is filed as its own ticket rather than fixed silently.
- **Dependencies:** TA-201.

### TA-205 — Manual pass on the packaged build

- **Phase:** 2
- **Priority:** P0
- **Suggested labels:** `needs-hardware`, `packaging`
- **Problem it solves:** Six things have never been checked on a real packaged
  executable. Several are the kind that only fail once frozen, which is exactly
  the class of bug this project has been finding all week.
- **Scope:**
  - No console window flashes when a recording saves (`CREATE_NO_WINDOW`).
  - A real recording produces a playable MP4 from the packaged exe.
  - Tray survives closing the last window (INS-02).
  - Pinned taskbar icon matches the tray icon (PKG-03).
  - Windows file properties report the current version (PKG-05).
  - Check for Updates reaches GitHub and reports correctly.
- **Deliverables:**
  - Updated statuses in `DESKTOP_TEST_PLAN.md`; `SMOKE_TEST.md` entry.
- **Acceptance criteria:**
  - Each case marked from observation, not inference.
  - PKG-04 (first launch on a machine without Python) either run or explicitly
    deferred with the reason.
- **Dependencies:** TA-201. Best run in the same sitting as TA-204.

### TA-206 — Judge the editor's feel

- **Phase:** 2
- **Priority:** P2
- **Suggested labels:** `enhancement`, `ux`
- **Problem it solves:** The editor rebuild is verified in every respect except
  whether it is comfortable to drive. The 8px grab radius, the border-only
  selection and the cursor responsiveness are judgements no test can make, and
  the person best placed to make them is the target user.
- **Scope:**
  - Mark up several real captures at working speed on the packaged build.
  - Note anything that fights the hand: grab radius, handle size, click-through.
- **Deliverables:**
  - A short written verdict; tickets for anything worth changing.
- **Acceptance criteria:**
  - A stated judgement, even if it is "no change needed".
- **Dependencies:** TA-205.

### TA-207 — Release v1.4.0

- **Phase:** 3
- **Priority:** P0
- **Suggested labels:** `release`
- **Problem it solves:** The multi-display fix reaches nobody until it is
  released, and the bug reporter has no build to confirm against.
- **Scope:**
  - Bump `__version__` to 1.4.0, run `generate_version_info.py` so
    `version_info.txt` and `help.html` follow.
  - Convert `[Unreleased]` in `CHANGELOG.md` to a dated 1.4.0 heading.
  - Rehearse with `workflow_dispatch`, then tag and push `v1.4.0`.
- **Deliverables:**
  - Tagged release with an attached zip.
- **Acceptance criteria:**
  - Release page shows **Assets 3** — the zip attached, not just the two
    auto-generated source archives.
  - The release workflow's version-equals-tag assertion passes.
- **Dependencies:** TA-202, TA-203, TA-204, TA-205.

### TA-208 — Close out issue #1

- **Phase:** 3
- **Priority:** P1
- **Suggested labels:** `bug`, `communication`
- **Problem it solves:** The reporter wrote a well-specified bug and is owed the
  outcome. The thread is also portfolio surface — a reviewer reading it sees how
  defects get handled here.
- **Scope:**
  - Comment with the release link, what was fixed (including the recording
    defect they did not hit), and what was verified on hardware versus by test.
  - Mention the new About → Copy details button as the easier route next time.
  - Ask them to confirm on their setup before closing.
- **Deliverables:**
  - Issue comment; issue closed once confirmed.
- **Acceptance criteria:**
  - The comment states plainly which cases were verified on real hardware and
    which remain Blocked. No claim of "fixed" beyond what TA-204 established.
- **Dependencies:** TA-207.

### TA-209 — `plan_capture()` still leaves a gap for layouts separated on both axes

- **Phase:** 3
- **Priority:** P2
- **Suggested labels:** `bug`, `capture`
- **Problem it solves:** `plan_capture()` closes a gap along one axis - whichever
  one every intersecting screen's ranges agree is the separated one - and packs
  the other axis as-is. That is provably gap-free only when screens are
  separated on a single axis. A selection spanning screens separated on *both*
  axes still lands with an unpainted (black) region: a corner-touching diagonal
  pair, or three screens arranged in an L. Single-axis packing cannot close two
  independent gaps at once; a real fix needs row/column (shelf) packing, not a
  single left-to-right or top-to-bottom pass.
  - The two-screen diagonal case is not a surprise: it is already the
    documented, deliberately-chosen fallback in `plan_capture()`'s own
    docstring, and pinned by
    `test_plan_capture_diagonal_layout_is_pinned_not_incidental` precisely
    because it is a known incompleteness, not an oversight.
  - The three-screen L-shaped case follows from the exact same rule (it is
    "separated on both axes" for at least one pair) but is not yet mentioned
    anywhere - not in the docstring, not in `DESKTOP_TEST_PLAN.md`, not in this
    backlog until now.
- **Scope:**
  - Design a row/column packing scheme (or equivalent) that closes every gap
    for an arbitrary arrangement, not just the two single-axis cases.
  - Add synthetic-layout tests for the L-shaped three-screen case alongside the
    existing two-screen diagonal one.
  - Update the `plan_capture()` docstring and `DESKTOP_TEST_PLAN.md` once the
    L case is either fixed or explicitly documented as a known limitation.
- **Deliverables:**
  - Either a packing fix with new tests, or (if deferred) an explicit note in
    the docstring and test plan naming the L-shaped gap as a known limitation
    rather than leaving it undiscoverable.
- **Acceptance criteria:**
  - No layout separated on both axes is described as "fixed" without a test
    covering it.
- **Dependencies:** None.

### TA-210 — Register Test Assist as a Windows file association for images

- **Phase:** 3
- **Priority:** P3
- **Suggested labels:** `enhancement`, `packaging`
- **Problem it solves:** "Open with -> Test Assist" now works once a user picks
  it manually - the app validates the file argument and loads it into the
  editor. It is not, and does not need to be, the *default* handler for any
  image extension to work: that is a separate, more visible decision (it
  changes what double-clicking a `.png` does system-wide) than making "Open
  with" functional at all, and was explicitly out of scope for that fix.
- **Scope:**
  - Decide which extensions (`.png` at minimum; `.jpg`/`.jpeg` maybe) Test
    Assist should be allowed to register for, and whether it should ever set
    itself as *default* versus only appearing in the "Open with" list.
  - Registry writes (`HKCU\Software\Classes\...`) or an installer-time
    association, scoped to the current user - never a system-wide/admin
    write for an app that installs by unzipping.
  - An uninstall/cleanup story, since nothing currently uninstalls this app
    beyond deleting the folder - a stale association pointing at a deleted
    `TestAssist.exe` must not be left behind silently.
- **Deliverables:**
  - A decision on default-handler vs. "Open with"-list-only, recorded here or
    in a follow-up brief before any registry code is written.
  - If implemented: the registration code, plus a manual test case in
    `DESKTOP_TEST_PLAN.md` (this cannot be verified by the automated suite -
    it is real Windows shell state, not application behaviour).
- **Acceptance criteria:**
  - No registry write happens outside of this ticket's own implementation -
    the "Open with" fix it follows on from must keep working with zero
    registration, as it does today.
- **Dependencies:** None.

---

## Recommended Execution Order

1. **TA-201** — commit and push, so nothing else is built on sand
2. **TA-202** — data move, before the help text describes a path about to change
3. **TA-203** — help.html, now able to name the final paths
4. **TA-204** and **TA-205** — one sitting with the second monitor and a built exe
5. **TA-206** — while the packaged build is open anyway
6. **TA-207** — release
7. **TA-208** — close the loop with the reporter

TA-204 and TA-205 both depend only on TA-201, so they *could* run before the
data move. Doing them after is the deliberate choice: TA-202 changes where
recordings are written, and a packaged-build pass is worth spending on the code
that will actually ship.

## Suggested Milestone Gates

### TA-211 — Alt+P, Alt+Shift+P and Alt+V are advertised everywhere and bound to nothing

- **Phase:** 1
- **Priority:** P1
- **Suggested labels:** `bug`, `launcher`, `docs-integrity`
- **Problem it solves:** The launcher's photo button tooltip says
  "capture screenshot (Alt+P)", the video button says "(Alt+V)", the full-capture
  button says "(Alt+Shift+P)", the launcher shows an on-screen hint reading
  "Alt+P · capture   ·   Alt+V · record", and `help.html`'s Keyboard Shortcuts
  table lists all three. **None of them is bound to anything.** A repository-wide
  search finds `Alt+` only in those tooltip strings, that hint label, the help
  table, and three tests asserting the tooltip text. There is no `QShortcut`, no
  key handler and no hotkey registration for any of them. The only shortcuts that
  exist are `Ctrl+Z`, `Ctrl+Y`, `Ctrl+S`, `Delete` and the single-letter tool keys,
  all in `editor.py` and all editor-scoped.
  - Found by a user pressing Alt+P while working in a browser and nothing
    happening. It would not have worked with the app focused either.
  - `test_regressions.py` asserts the tooltips *contain* those strings, so the
    suite is actively protecting the advertisement of a feature that does not
    exist. Any fix must replace those assertions with ones that exercise the
    binding, not the label.
  - This violates the project's standing rule that every claim on the page or in
    the docs is true of the code as committed — here the false claim is on the
    app's own face.
- **Scope:**
  - Bind the three advertised shortcuts for real.
  - They must be **system-wide hotkeys**, not `QShortcut`. The entire point of an
    always-on-top capture widget is capturing whatever else has focus; a shortcut
    that only fires when Test Assist is focused is useless for the stated purpose.
    Qt has no cross-platform global hotkey API — on Windows this is `RegisterHotKey`
    via `ctypes` plus a `QAbstractNativeEventFilter` handling `WM_HOTKEY`. No new
    dependency.
  - Handle registration failure explicitly. `RegisterHotKey` fails when another
    application already owns the combination. A failed registration must be
    surfaced, and the corresponding tooltip and help entry must not claim a
    shortcut that did not register.
  - Release the hotkeys on exit.
- **Deliverables:**
  - Working global Alt+P / Alt+Shift+P / Alt+V, or — if global registration is
    deferred — every one of those five claim sites removed in the same commit.
    Shipping the claims unbound again is not an option.
- **Acceptance criteria:**
  - Pressing Alt+P with a browser focused captures, with Test Assist unfocused.
  - A combination that fails to register is reported and no longer advertised.
  - No test asserts a shortcut string in a tooltip without a corresponding test
    that the binding exists.
- **Dependencies:** None. Blocks the 1.4.0 release — the app currently makes three
  false claims about itself in its own UI.

### TA-212 — PrintScreen as an opt-in capture shortcut

- **Phase:** 2
- **Priority:** P2
- **Suggested labels:** `enhancement`, `launcher`
- **Problem it solves:** PrintScreen is what a tester's hand reaches for. Test
  Assist can own it via `RegisterHotKey` with `VK_SNAPSHOT` (0x2C).
- **Scope:**
  - Off by default and opt-in from a setting. Claiming PrintScreen globally takes
    it away from every other application on the machine, including the user's
    existing habits, and must never happen without the user asking.
  - Windows 11 can map PrintScreen to the Snipping Tool
    (Settings → Accessibility → Keyboard → "Use the Print screen key to open screen
    capture"). When that is on, registration fails. Detect it, say so plainly, and
    point at that setting rather than failing silently.
- **Deliverables:**
  - A setting, a registration path, and an honest failure message.
- **Acceptance criteria:**
  - Default install does not claim PrintScreen.
  - With the setting on and registration successful, PrintScreen captures.
  - With registration refused, the user is told why and where to change it.
- **Dependencies:** TA-211 — the hotkey mechanism it needs is built there.

### TA-213 — Rework help.html for the current UI, screenshots included

- **Phase:** 2
- **Priority:** P1
- **Suggested labels:** `docs`, `editor`
- **Problem it solves:** The editor's layout changed materially in `19bbf0c`
  (settings and export controls moved to a full-width second toolbar row, the
  right panel reduced to Edit and History), `734dfe7` (Show Launcher button),
  `a7a465f` (recording thumbnails with a play badge) and `6468591` (open a file
  from Explorer). Help's screenshots and diagrams show the previous layout, so a
  user following it is looking for controls where they no longer are.
- **Scope:**
  - Retake every screenshot and redraw the inline SVG diagrams against the built
    1.4.0 UI.
  - Cover what is new: the second toolbar row, the Show Launcher button, recording
    thumbnails, opening an image from Explorer, and the X-hides-to-tray behaviour.
  - Reconcile the Keyboard Shortcuts table with whatever TA-211 actually lands.
    The help table and the launcher tooltips currently disagree with each other as
    well as with the code.
- **Deliverables:**
  - Updated `help.html` with current imagery and an accurate shortcut table.
- **Acceptance criteria:**
  - Every control shown in help exists, in the position shown.
  - No shortcut appears in help that is not bound in the code.
- **Dependencies:** TA-211. Do this after the shortcut work, not before, or the
  table is rewritten twice.

### TA-214 — No way to open or paste an image into the editor once it's open

- **Phase:** 2
- **Priority:** P1
- **Suggested labels:** `bug`, `editor`, `ux`
- **Problem it solves:** Found during the rc3 manual pass. With the editor open
  and nothing loaded — first launch, or "Open Editor" with no capture taken —
  there is no way to bring an image in except History (past app-generated
  exports) or going back to the launcher for a fresh screen capture. Confirmed
  directly in the code, not just observed behaviour: every `QFileDialog` call in
  `editor.py` is `getSaveFileName` (Save PNG, Export JSON) — there is no
  `getOpenFileName` anywhere. The only clipboard code is `_copy_to_clipboard()`
  (write-only); nothing reads `QApplication.clipboard()`, and no `Ctrl+V`
  shortcut is registered (the bound set is `Ctrl+Z`, `Ctrl+Y`, `Ctrl+S`,
  `Delete`). Neither `canvas.py` nor `editor.py` implements `setAcceptDrops`,
  `dragEnterEvent` or `dropEvent`. `load_image_path()` (from `6468591`) is
  wired only to CLI argv at startup and the second-instance handoff socket —
  there is no UI control anywhere in the running editor that calls it. This
  isn't a regression: the README's "file picker or drag-and-drop" bullet is
  explicitly scoped to the browser build only. But it's a real gap in the
  desktop build's own stated purpose — "long test sessions" — if the tester
  can't get an existing image into it without a fresh capture.
- **Scope:**
  - Add an "Open Image…" action reachable from the editor toolbar, calling
    `QFileDialog.getOpenFileName()` and routing the result through the
    existing `load_image_path()` — reuse its bad-path/non-image handling
    rather than duplicating it.
  - Add `Ctrl+V` paste-from-clipboard: read the clipboard's pixmap/image data
    and load it the same way; a clipboard with no image should do nothing
    destructive (no crash, a plain status message), not silently fail.
  - Drag-and-drop onto the canvas, for parity with the browser build, is a
    reasonable stretch addition — flag it as optional rather than required.
  - Whether this should also be reachable from the floating launcher (a
    faster way to open an existing file without opening an empty editor
    first) is a product decision to make explicitly, not assume.
- **Deliverables:**
  - Open-file action wired to `load_image_path()`; `Ctrl+V` paste support;
    tests for a valid open, a cancelled dialog, an empty clipboard, and an
    image-bearing clipboard.
- **Acceptance criteria:**
  - With the editor open and nothing loaded, a discoverable control opens a
    file picker and loads the chosen image.
  - `Ctrl+V` loads a clipboard image into the canvas; an empty clipboard is a
    no-op with a status message, never a crash.
  - Both paths reuse `load_image_path()`'s existing validation rather than
    reimplementing it.
- **Dependencies:** None — builds on `load_image_path()` from `6468591`,
  already shipped.

### TA-215 — The docked launcher gives no feedback during a recording

- **Phase:** 2
- **Priority:** P1
- **Suggested labels:** `bug`, `launcher`, `ux`
- **Problem it solves:** Found during the rc3 manual pass (LCH-13 — the
  hotkeys themselves passed cleanly). Reported: *"there is no way to see that
  the recording is running, and no way to stop it besides the floating
  widget — even clicking the video capture icon does nothing. Only hitting
  Stop Recording stops it. The video capture icon should change into a red
  square which will stop the video capture."* Confirmed directly in
  `launcher.py`: the docked strip's single capture icon
  (`_btn_dock_capture`, wired to `_on_action_click` → `_toggle_recording()`)
  has its icon set once at construction and never updated — unlike the
  undocked `_btn_capture`, whose text/style *do* change between
  `"⏺ Start Recording"` and `"■ Stop Recording"`. Worse, `_rec_label` (the
  `"⏺ 00:00"` running-time readout) is added only to the undocked
  `float_layout`, never to `dock_layout` — so a user working from the
  compact docked strip, which is exactly the mode the docking feature exists
  for, gets **zero** visual confirmation a recording is running, and the one
  control available to stop it gives no visual cue that it will. The
  underlying toggle is correctly wired either way — clicking the docked icon
  a second time does call `_stop_recording()` — this is a state-feedback gap,
  not a broken stop mechanism, which is exactly why it read as "does
  nothing" under test.
  UPD-12 (*"unable to see test assist update request button"*) was
  originally suspected to be the same docked-visibility pattern. Screenshots
  of the *undocked* panel disproved that: `_btn_check_updates` is present
  and correctly wired exactly where documented (2nd icon in `header_row`,
  right after the editor icon). The real cause is unrelated to docking —
  moved to **TA-218**.
  Also flagged from the same pass, not yet reproduced with enough detail to
  diagnose: capturing the Windows Properties dialog (PKG-05) with Test
  Assist itself reportedly didn't work while docked, native PrintScreen was
  used instead. Needs a specific repro (did Quick Capture do nothing, fail
  to show the selection overlay, or capture the wrong window?) before it's
  scoped as part of this ticket or filed separately.
- **Scope:**
  - Give the docked capture icon its own visual state: swap its icon (e.g.
    to a red square/stop glyph) when `self._rec_timer.isActive()`, mirroring
    what `_btn_capture`'s text already does undocked.
  - Surface a minimal recording indicator while docked — a colored dot or
    the elapsed-time text is enough; it doesn't need the full `_rec_label`
    treatment, but *something* must be visible in the docked strip.
  - Get a precise repro on the PKG-05 docked-capture report before scoping a
    fix for it.
- **Deliverables:**
  - Docked-mode recording state (icon + indicator); a confirmed repro (or
    a "not reproducible" note) for the PKG-05 report.
- **Acceptance criteria:**
  - Starting a recording from the docked strip visibly changes the capture
    icon and shows some running-time indicator, without undocking.
  - Clicking the same icon again stops the recording, with the icon
    reverting.
- **Dependencies:** None.

### TA-216 — A capture isn't kept anywhere until you explicitly Save or Copy

- **Phase:** 2
- **Priority:** P1
- **Suggested labels:** `bug`, `editor`, `ux`
- **Problem it solves:** Found during the rc3 manual pass: *"taking multiple
  images do not store them in the history for me to be able to select them in
  the editor."* Confirmed in code: `_persist_history_snapshot()` — the only
  thing that adds a History entry — is called from exactly two places,
  `_save_png()` (after a completed Save-As dialog) and `_copy_to_clipboard()`.
  Simply taking a capture (Quick Capture, full-screen, or a recording) does
  not, by itself, add anything to History. A tester who takes a second
  capture without first running the Save-PNG file dialog for the first one
  has already lost access to it — nothing brings it back (this compounds
  `TA-214`: no open/paste path either). For a QA evidence tool meant for a
  session of several captures in a row, requiring a full Save-As dialog
  completion per capture just to keep it reachable is a real workflow cost,
  not a corner case.
- **Scope:**
  - Persist every completed capture (region, full-screen) to History
    automatically, the same way a save/copy currently does — without
    requiring the Save-As dialog first.
  - Decide explicitly whether recordings need equivalent treatment (they
    already appear in History per `a7a465f` — confirm captures get the same
    guarantee, not just video).
  - Keep the existing "skip if too small to be a real capture" guard
    (`pixmap.width() < 50...`) — that part of `_persist_history_snapshot()`
    is sound and should carry over unchanged.
- **Deliverables:** capture-time auto-persist to History; a test that two
  captures taken back to back, with no Save or Copy in between, both appear
  in the gallery.
- **Acceptance criteria:** taking N captures without saving or copying any
  of them leaves N entries in History, each selectable back into the canvas.
- **Dependencies:** None. Closely related to `TA-214` — both are "how do I
  get back to an image I'm not currently looking at" — worth sequencing
  together in the brief even though they're separate tickets.

### TA-217 — Quick Capture doesn't reliably start when another window has focus

- **Phase:** 2
- **Priority:** P1
- **Suggested labels:** `bug`, `capture`, `launcher`
- **Problem it solves:** Two related reports from the rc3 manual pass.
  1. **Confirmed mechanism:** *"opening the about screen and hitting alt+p...
     opens the capture on the screen below the about screen even though the
     about is in focus"* — and separately, Quick Capture reported as doing
     nothing while a dialog was open. `editor.py`'s `_open_about()` creates
     its `QDialog` with `setModal(True)`, which Qt treats as
     `Qt::ApplicationModal` — while that dialog's event loop is running, Qt
     blocks mouse/keyboard delivery to every other window belonging to the
     application, including a freshly-shown `ScreenshotOverlay`. Alt+P still
     fires `_start_capture()` (the global hotkey is a native OS message, not
     routed through Qt's own event queue), and the overlay's own
     `WindowStaysOnTopHint` + `raise_()` + `activateWindow()`
     (`capture.py::activate()`) still execute — but Qt's application-modal
     blocking means the overlay most likely never receives the mouse events
     needed to drag a selection, and the still-modal About dialog keeps real
     OS-level Z-order priority, consistent with the overlay appearing
     "below" it. This is a strong, code-grounded explanation, not yet
     confirmed live — needs a real repro with the About dialog open before
     it's called fixed.
  2. **Separate, less understood, intermittent:** capturing over the Windows
     Properties dialog (a different application's window, not one of Test
     Assist's own) reportedly did nothing on a first attempt, then worked on
     retry. Qt's own modality doesn't apply to a foreign process's window,
     so this is a different mechanism — most likely a focus/Z-order race
     against `_start_capture()`'s fixed 220ms `singleShot` delay before the
     overlay activates. Not enough repro detail yet to pin down; flagged
     separately rather than folded into the About-dialog fix.
- **Scope:**
  - For the confirmed case: either dismiss/close Test Assist's own modal
    dialogs (About, and any future one) automatically when a global hotkey
    fires a capture, or make overlay activation itself modality-proof so it
    can grab input regardless of an open dialog. Prefer the first — simpler,
    and matches user intent: pressing Alt+P clearly means "capture now."
  - For the intermittent case: get a repeatable repro (does it correlate
    with how quickly Quick Capture is clicked after the target window gains
    focus? does raising the delay in `_start_capture()` change the failure
    rate?) before scoping a fix.
- **Deliverables:** the About-dialog case fixed and covered by a test that
  opens the About dialog, fires the capture path, and asserts the overlay
  actually receives input; a documented repro (or a "not reproducible" note)
  for the Properties-dialog case.
- **Acceptance criteria:** triggering a capture (hotkey or button) while
  Test Assist's own About dialog is open results in a working, interactive
  capture overlay, not a silent no-op.
- **Dependencies:** None.

### TA-218 — Check for Updates is present but not recognizable, and only reachable from the launcher

- **Phase:** 2
- **Priority:** P2
- **Suggested labels:** `bug`, `launcher`, `editor`, `ux`
- **Problem it solves:** Reported as UPD-12, *"unable to see test assist
  update request button,"* then reconfirmed against the undocked launcher
  panel with *"still cant see the update button"* — and separately,
  *"the check for updates should be included on the editor screen as
  well."* Confirmed in `launcher.py`: `_btn_check_updates` exists, is
  correctly positioned in `header_row` (2nd icon, right after the editor
  icon) and correctly wired
  (`_btn_check_updates.clicked.connect(self._check_for_updates)`) — this is
  not a hidden or missing control. `_make_update_icon()` draws the glyph
  itself:
  ```python
  p.drawLine(7, 2, 7, 9)    # vertical stem
  p.drawLine(4, 6, 7, 9)    # arrowhead, left
  p.drawLine(10, 6, 7, 9)   # arrowhead, right
  p.drawLine(3, 12, 11, 12) # bar underneath
  ```
  That's a plain arrow into a tray — a generic "download" shape with no
  refresh/update visual convention (no circular arrows, no badge, no
  distinct color from its neighbors). The control isn't hidden; it isn't
  recognizable. Separately, it exists only on the launcher — the Editor
  window has no equivalent, so a user working from the Editor has no path
  to it at all without switching back to the launcher.
- **Scope:**
  - Redesign `_make_update_icon()` to something that reads as "check for
    updates" at 14×14 (a circular refresh arrow is the standard convention;
    a small tooltip already exists and stays as reinforcement, not a
    substitute).
  - Add a Check for Updates entry reachable from the Editor window (menu
    item or a header icon consistent with the Editor's own affordances) —
    it should not require returning to the launcher.
- **Deliverables:** a recognizable update-check icon on the launcher; a
  Check for Updates path from the Editor.
- **Acceptance criteria:** a user shown only the undocked launcher, without
  being told what it does, can identify the update-check control by sight;
  the same action is reachable from the Editor window.
- **Dependencies:** None.

### TA-219 — Save PNG / Export JSON default to the install folder instead of Documents\Test Assist

- **Phase:** 2
- **Priority:** P1
- **Suggested labels:** `bug`, `editor`, `data-integrity`
- **Problem it solves:** Reported: *"the images dont open to the documents
  test assist folder. when going to save an image in the new version it
  defaulted it to the location where the app was installed not to the
  documents folder."* Confirmed in `editor.py`: `_save_png()` and
  `_export_json()` both call `QFileDialog.getSaveFileName()` with a bare
  filename and no directory —
  ```python
  default = f"test-assist-{int(time.time())}.png"
  path, _ = QFileDialog.getSaveFileName(self, "Save PNG", default, "PNG (*.png)")
  ```
  Neither function references `paths` at all, despite `import paths` being
  present in the file and already used correctly elsewhere in the same
  module (`self._history_dir = paths.history_dir()`, and
  `directory = paths.recordings_dir()` for recordings). With no directory
  hint, Qt's save dialog falls back to the last-used folder or the current
  working directory — on Windows, launched via a shortcut, that's typically
  the app's own folder, matching exactly what was reported. This is the
  same `Documents\Test Assist` split `docs/data-locations-brief.md` already
  specifies and that video recordings (`capture.py::_recordings_dir()` →
  `paths.recordings_dir()`) already get right — the PNG/JSON save dialogs
  are the one place that split wasn't wired through.
- **Scope:**
  - Pass `paths.recordings_dir()` as the starting directory to both
    `QFileDialog.getSaveFileName()` calls in `_save_png()` and
    `_export_json()`, matching what `_recording_entries()` already does.
  - Confirm `paths.recordings_dir()` creates the folder if it doesn't exist
    yet, so the dialog doesn't open to a missing path on first save.
  - Out of scope for this ticket, explicitly not yet decided: letting the
    user choose a different default save folder — noted as a future option,
    not built here.
- **Deliverables:** both save dialogs default to `Documents\Test Assist`.
- **Acceptance criteria:** on a machine where that folder has never been
  opened manually, clicking Save PNG or Export JSON opens the dialog
  already inside `Documents\Test Assist`, not the app's install folder.
- **Dependencies:** None.

### TA-220 — Clicking the TA icon while the Editor is already open should toggle it, not just raise it

- **Phase:** 2
- **Priority:** P3
- **Suggested labels:** `enhancement`, `launcher`, `editor`, `ux`
- **Problem it solves:** Reported: *"if the editor has already been opened
  and the user clicks on the TA button on the floating widget it should
  maximise or minimise the editor page so that the user can have quick
  access to it instead of looking for the app in the toolbar."* Confirmed
  in `launcher.py`/`editor.py`: `_btn_open_editor` is already wired to
  `self._editor.bring_forward`, which does `show()` +
  `activateWindow()` + `raise_()` — so the "find it without hunting in the
  taskbar" half already works today. What's missing is the toggle half:
  clicking the TA icon again while the Editor is already open and focused
  currently does the same bring-forward no-op instead of minimizing it back
  out of the way.
- **Scope:** in `bring_forward()` (or the click handler that calls it),
  check whether the Editor window is currently the active window; if so,
  minimize it instead of re-raising it.
- **Deliverables:** the TA icon acts as a show/hide toggle for the Editor.
- **Acceptance criteria:** with the Editor open and focused, clicking the TA
  icon minimizes it; clicking it again restores and focuses it.
- **Dependencies:** None.

### Gate A — Code complete
- TA-201, TA-202, TA-203 merged
- Suite green, no skips, no test opens a socket
- No false statement remains in `help.html` or `README.md`

### Gate B — Verified on hardware
- TA-204 and TA-205 complete, every case marked from observation
- Any failure filed as its own ticket
- `SMOKE_TEST.md` records the date and the exact configurations used

### Gate C — Released
- v1.4.0 tagged, release page shows Assets 3
- Issue #1 answered with the release link and an honest verification statement
