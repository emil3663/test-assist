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
  PKG-05 (docked capture over the Windows Properties dialog): retried on
  rc4 and **not reproducible** — closing this sub-item, no longer part of
  this ticket's scope.

  **Re-tested on rc4, 2026-09-09 — the icon/indicator fix works, but two
  new gaps found:**
  1. *Video recordings don't appear in History without reopening the
     editor.* Confirmed in code: `record_capture()` (still captures) ends
     with `self._persist_history_snapshot(pixmap)`, which itself calls
     `self._refresh_history()` — the gallery updates live. But
     `_on_record_finished()` (launcher.py, called when a recording
     finishes) only updates the status label and reveals "Open Folder" —
     it never tells the editor's History panel to refresh. The recording
     is saved correctly to `recordings_dir()` on disk, and would show up
     the next time History is rebuilt (e.g. on editor restart), but not
     live, unlike still captures.
  2. *No visual distinction for "video mode selected" before recording
     starts.* Reported: *"the image for capture should be changed to video
     icon if that is selected."* The recording-in-progress feedback this
     ticket originally fixed does work now — this is a separate, smaller
     ask: the docked icon doesn't reflect that Video mode (vs. Photo) is
     the active mode until a recording is actually running.
- **Scope:**
  - Give the docked capture icon its own visual state: swap its icon (e.g.
    to a red square/stop glyph) when `self._rec_timer.isActive()`, mirroring
    what `_btn_capture`'s text already does undocked. **Done in rc4.**
  - Surface a minimal recording indicator while docked. **Done in rc4.**
  - New: have `_on_record_finished()` trigger the same History refresh
    `_persist_history_snapshot()` already does, so a finished recording
    appears in the open editor's gallery without a restart.
  - New, smaller: give the docked (and undocked) capture icon a distinct
    "video mode selected" appearance when Video mode is active but not yet
    recording — decide the exact glyph (e.g. a video-camera icon) rather
    than guessing.
- **Deliverables:**
  - Docked-mode recording state (icon + indicator) — done.
  - Finished recordings appear in History live, no restart needed.
  - Video-mode-selected visual state on the capture icon.
- **Acceptance criteria:**
  - Starting a recording from the docked strip visibly changes the capture
    icon and shows some running-time indicator, without undocking. ✅
  - Clicking the same icon again stops the recording, with the icon
    reverting. ✅
  - A finished recording appears in History without closing/reopening the
    editor.
  - Selecting Video mode (before recording) is visually distinguishable
    from Photo mode on the capture icon.
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
- **Verified:** ✅ 2026-09-09, rc4 — PASS. Manual re-test confirms multiple
  captures now persist to History without a Save/Copy step
  (`multiple_images_saved.png`).

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
     Assist's own). Retried on rc4 and **not reproducible** — closing this
     sub-item, no longer part of this ticket's scope.

  **Re-tested on rc4, 2026-09-09 — FAIL, two distinct gaps found in the
  "fix":**
  1. *The fix only covers the hotkey path.* Reported: *"clicking the quick
     capture on the widgets does not work"* (while About is open).
     Confirmed in `launcher.py`: `_dismiss_active_modal_dialog()` is called
     **only** from `_on_global_hotkey()`. The launcher's own Quick Capture
     *button* click handler never calls it — so clicking the button while
     About's `Qt::ApplicationModal` block is up is still silently
     swallowed by Qt, exactly as before this ticket's fix. The rc4 fix
     solved the hotkey path and left the button path exactly as broken as
     it always was.
  2. *The hotkey path itself no longer captures.* Reported: *"pressing
     alt+P closes the about popup. it doesnt take a snap shot."* So
     `_dismiss_active_modal_dialog()` is doing its job (About visibly
     closes), but the capture that's supposed to follow doesn't happen.
     Read through `_on_global_hotkey()` → `_start_capture()` and didn't
     find a definitive mechanism from the code alone — this needs a live
     repro with logging (does `_overlay.activate()`'s 220ms `singleShot`
     even fire? does the overlay show but not receive input, or never show
     at all?) rather than another guess. Flagging honestly as unconfirmed
     instead of asserting a cause I haven't verified.
- **Scope:**
  - Wire `_dismiss_active_modal_dialog()` into the Quick Capture *button's*
    click handler too, not just the hotkey path — both routes into
    `_start_capture()` need the same guard.
  - Instrument or step through the hotkey path on real hardware to find why
    dismissing About no longer results in a working capture — this regressed
    from what rc4's own test claimed to cover, so the rc4 test itself needs
    re-examination (was it asserting the right thing, or just that
    `_dismiss_active_modal_dialog` was *called*, not that a capture actually
    resulted?).
- **Deliverables:** both the button and hotkey paths dismiss a blocking
  modal *and* produce a working, interactive capture overlay afterward,
  covered by a test that checks the end state (an overlay that can actually
  receive a drag), not just that the dismiss function ran.
- **Acceptance criteria:** triggering a capture (hotkey **or** button)
  while Test Assist's own About dialog is open results in a working,
  interactive capture overlay, not a silent no-op — neither leaves the
  dialog open blocking input, nor closes it without capturing.
- **Dependencies:** None.

  **Re-verified on hardware, Launcher Evaluation Pass T5, 2026-09-16 —
  sub-item 1 still fails exactly as rc4 left it; sub-item 2 is not what
  rc4's report described.**

  1. *Button path (both floating and docked widgets):* tester's report:
     "both docked and floating widgets are not able to capture the about
     or anything else" while the About dialog is open. Matches rc4's
     finding exactly — `_dismiss_active_modal_dialog()` is still only
     wired into `_on_global_hotkey()`, not into either Quick Capture
     button's click handler (`launcher.py`, `_btn_capture` /
     `_btn_dock_capture`). Still an unqualified no-op by design, not a
     new regression.

  2. *Hotkey path:* re-tested with `TESTASSIST_DEBUG=1` enabled (the
     opt-in logging this ticket's own Scope asked for), rather than
     relying on another unaided manual report. `history/debug.log`:

     ```
     [2026-09-16 03:08:29] _dismiss_active_modal_dialog: activeModalWidget=<PySide6.QtWidgets.QDialog(0x1a0ddfbe7a0) at 0x000001A0C4512A40>
     [2026-09-16 03:08:29] _start_capture: singleShot fired, calling _overlay.activate()
     [2026-09-16 03:08:33] TA-223 drag move: globalPosition=(431, 109) ...
     [2026-09-16 03:08:34] TA-225 grab: dragged_rect=(430, 107, 855, 641) ...
     ```

     This is the first time `activeModalWidget` has ever logged as
     non-`None` in this file's history — a real modal was up, Alt+P (the
     tester said "ctrl+p"; the bound hotkey is actually Alt+P per
     `_register_hotkeys()` — likely just a naming slip, the behavior
     matches Alt+P's code path either way) dismissed it, the overlay
     activated, and a full drag-to-grab cycle completed successfully.
     **rc4's "hotkey path itself no longer captures" is not reproduced
     here — the capture mechanism works end-to-end via the hotkey.**

     But the resulting file
     (`history/snapshot-20260916-030834-537324.png`, viewed directly)
     shows the Editor window from an *earlier*, unrelated capture — not
     the About dialog. Mechanism: dismiss happens, then only *after*
     that does `_start_capture()`'s 220ms `singleShot` fire and the
     overlay appear — so by the time a selection can be dragged, About is
     already gone. The hotkey path was never going to be able to
     capture About's own content, regardless of whether the capture
     itself succeeds afterward. So "you can't get a screenshot of the
     About dialog via Quick Capture" is confirmed true for both paths —
     just for two different reasons (button: no-ops entirely; hotkey:
     works, but only on whatever is left after About closes).
  - This ticket's Scope/Acceptance criteria stand as written; item 1
    above is what they still need to fix, and the acceptance criteria's
    "produce a working, interactive capture overlay afterward" is now
    confirmed met for the hotkey path specifically — it's the capturing
    *of the dialog itself* that was never in scope or possible here, and
    is worth an explicit "not in this ticket" note if that's ever
    expected to work.

  **Correction, 2026-09-16 (later) — the "button path never calls
  dismiss" claim above is wrong, checked against every relevant commit,
  not just current `main`.** Attempting to implement this ticket's own
  Scope item 1 found `_dismiss_active_modal_dialog()` already wired into
  both `_btn_capture` and `_btn_dock_capture`'s shared click handler
  (`_on_action_click` pre-merge, renamed `_on_capture_click` on
  `ui-polish` and current `main`) — confirmed by direct `git show`/`git
  blame` against `v1.4.0` (line 446), pre-merge `main` (`03726da`),
  unrebased `ui-polish` (`ca71881`), and current `main`. The dismiss call
  traces back to `5783f8dc` (the rc4 fix itself, 2026-09-09) and survived
  intact through every rebuild since. `test_TA217_quick_capture_button_closes_an_open_about_dialog_before_capturing`
  (`test_regressions.py`) already exercises this ticket's own stated
  acceptance bar — real `.click()`, unstubbed `_start_capture`, asserts
  `_overlay.isVisible()` and a real non-null grabbed pixmap — and passes.
  A throwaway repro using `QTest.mouseClick` (a real synthesized Qt mouse
  event, not a direct `.click()` call) against `_btn_capture` while
  `editor._open_about()` was genuinely blocked in `dlg.exec()` also
  dismissed the dialog correctly.

  **So the code-level explanation this ticket has given for the button
  path's no-op, in every pass from rc4 through tonight, does not match
  the code and has not for several days.** Both rc4's and tonight's
  hardware testers independently report the same real symptom (button
  produces nothing while a modal is open) against builds whose code
  provably has the dismiss call wired in — which means either (a) the
  testers were holding a stale build without this fix (a stale `v1.4.0`
  exe from this exact scenario was found sitting in `python/dist/` this
  session), or (b) the real mechanism is something in-process/offscreen
  Qt testing cannot observe at all, e.g. Windows disabling sibling HWNDs
  at the OS level under a real modal dialog — the same class of gap
  `TA-228`'s black-box lane exists for. **Not yet determined which.**
  Scope item 1 as written ("wire dismiss into the button handler") is
  not actionable — it asks for something that already exists. Before any
  further code change is scoped here, this needs a fresh hardware repro
  against current `main` specifically (not the stale build, not
  `ui-polish` pre-merge), ideally with `TESTASSIST_DEBUG=1` so
  `_dismiss_active_modal_dialog`'s own log line confirms whether it's
  even reached on the real click, the same standard this ticket's own
  hotkey-path finding already met. No code changed here.

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
- **Verified:** ✅ 2026-09-09, rc4 — PASS. "check for updates clear in both
  edit and floating widget."

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
- **Verified:** ✅ 2026-09-09, rc4 — PASS, after a full restart. App now
  defaults to `C:\Users\MSI workstation\Documents\Test Assist`; both a PNG
  and a JSON export landed there correctly.

### TA-220 — TA icon does not restore the Editor when it's minimized

- **Phase:** 2
- **Priority:** P1
- **Suggested labels:** `bug`, `launcher`, `editor`, `ux`
- **Problem it solves:** Reported: *"if the editor has already been opened
  and the user clicks on the TA button on the floating widget it should
  maximise or minimise the editor page so that the user can have quick
  access to it instead of looking for the app in the toolbar."* Then
  reproduced more precisely: *"during my manual testing it was discovered
  if the edit app was minimised it is not brought forward maximised. the
  focus might change to the edit screen but it is not displayed."*
  `_btn_open_editor` is wired to `self._editor.bring_forward`:
  ```python
  def bring_forward(self) -> None:
      self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
      self.show()
      self.activateWindow()
      self.raise_()
  ```
  This is a genuine bug, not just a missing toggle. Once a Qt window has
  already been shown once, calling `.show()` again does not clear a
  minimized state — Qt treats "shown" and "not minimized" as separate
  flags, and neither `show()` nor `raise_()` clears
  `Qt::WindowMinimized`. `activateWindow()` can still hand the window OS-
  level activation while it stays iconified in the taskbar, which is
  exactly the reported symptom: focus moves, nothing becomes visible.
  Confirmed by absence — `windowState`, `isMinimized`, and `showNormal`
  do not appear anywhere in `editor.py`; the minimized case was never
  handled.
  **Fixed in the rc4 batch** (see `docs/BUILD_LOG.md`'s rc4 entry):
  `bring_forward()` now checks `isActiveWindow()`/`isMinimized()` and
  calls `showNormal()` before re-showing.

  **Re-tested on rc4, 2026-09-09 — FAIL, restore now works but two gaps
  remain.** Current code:
  ```python
  def bring_forward(self) -> None:
      if self.isActiveWindow() and not self.isMinimized():
          self.showMinimized()
          return
      if self.isMinimized():
          self.showNormal()
      self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
      self.show()
  ```
  1. *Confirmed:* Reported: *"it does restore now but there seems to be an
     issue if the edit app was full view(maximised) then it should return
     in full view not the minimum size view. it should keep the sizing
     parameters."* `showNormal()` always restores to the **normal**
     (windowed) state — it clears both the minimized *and* maximized
     flags unconditionally, so a window that was maximized before being
     minimized comes back windowed-size instead. Qt actually keeps both
     flags set at once on a minimized-while-maximized window (its
     `windowState()` carries `WindowMinimized | WindowMaximized`
     together), so the maximized flag is available to check — the code
     just never checks it before deciding how to restore.
  2. *Reported, not yet confirmed by code:* *"minimise doesn't work at
     present"* and *"if view is maximised the ta icon in the docked or
     floating widgets do not minimise it."* One plausible mechanism: the
     `isActiveWindow()` check at the top runs the instant the TA icon is
     clicked — but the click itself happens on a *different* top-level
     window (the launcher), so at the moment this code runs, Windows may
     not yet have reported the Editor as active even if it visually is,
     making `isActiveWindow()` read `False` more often than intended and
     skipping the minimize branch regardless of maximize state. This is a
     hypothesis from reading the code, not a measurement — needs a live
     check (e.g. log `isActiveWindow()`'s value at the top of the
     function on a real click) before treating it as the cause.
- **Scope:**
  - In the `isMinimized()` branch, check whether `Qt.WindowState.WindowMaximized`
    is also set in `self.windowState()` before restoring; call
    `self.showMaximized()` in that case instead of `self.showNormal()`, so
    the Editor comes back in whatever state (normal or maximized) it was
    minimized from.
  - Investigate the minimize-toggle not firing — confirm or rule out the
    `isActiveWindow()` timing hypothesis above with a real measurement
    before changing that logic.
- **Deliverables:** `bring_forward()` restores to the correct prior window
  state (not always "normal"); the minimize toggle reliably fires
  regardless of whether the Editor is maximized.
- **Acceptance criteria:**
  - A maximized Editor, minimized, then restored via the TA icon, comes
    back maximized — not windowed-size.
  - With the Editor open and focused (maximized or not), clicking the TA
    icon minimizes it; clicking it again restores and focuses it.
- **Dependencies:** None.

### TA-221 — Copy/Export button text is clipped, reads as "Copv"/"Exoort"

- **Phase:** 2
- **Priority:** P2
- **Suggested labels:** `bug`, `editor`, `ux`
- **Problem it solves:** Reported with a screenshot: the Copy and Export
  buttons on the editor's settings bar render as "Copv" and "Exoort," not
  "Copy" and "Export." Confirmed in code, and the exact letters match a
  precise mechanism, not a random rendering glitch:
  ```python
  self._btn_copy = QPushButton("Copy")
  self._btn_copy.setFixedHeight(26)
  ...
  self._btn_export_json = QPushButton("Export")
  self._btn_export_json.setFixedHeight(26)
  ```
  The global `QPushButton` rule in `theme.py` sets
  `padding: 7px 14px; font-size: 12px;` — 14px of vertical padding alone.
  Inside a `setFixedHeight(26)` button, that leaves only 12px of vertical
  room for the text, tighter than a 12px font's natural line height, so
  Qt clips whatever falls below the baseline. "Copy" loses the descender
  tail off its **y**, leaving what reads as "Copv"; "Export" loses the
  descender stem off its **p**, leaving only the round bowl, which reads
  as "Exoort." `_btn_save_png` — same base rule, but
  `setFixedHeight(28)`, 2px taller — is not reported as clipped, which is
  exactly consistent with 26px being the specific height that's too
  tight.
  Not related to the rc4 batch — this button and its fixed height predate
  every ticket fixed in that round.
- **Scope:** don't hand-tune another fixed pixel height that can drift out
  of sync with the stylesheet's own padding/font-size again. Either:
  - remove the redundant `setFixedHeight(26)` on `_btn_copy` and
    `_btn_export_json` and let them size naturally from the QSS padding,
    the way most other buttons in this file already do, or
  - raise both to `setFixedHeight(28)`, matching `_btn_save_png`'s
    proven-working height.

  Whichever is chosen, verify against an actual rendered screenshot
  showing the full, unclipped text — font metrics can shift slightly with
  Windows' own scaling/ClearType settings, so a matched pixel count isn't
  proof by itself.
- **Deliverables:** Copy and Export render their full text with no clipped
  descenders, confirmed visually on the real Windows build.
- **Acceptance criteria:** a screenshot of both buttons shows "Copy" and
  "Export" in full — not "Copv"/"Exoort" or any other clipped variant.
- **Dependencies:** None.

### TA-222 — Settings bar is right-aligned instead of centered under the tool row

- **Phase:** 2
- **Priority:** P3
- **Suggested labels:** `bug`, `editor`, `ux`
- **Problem it solves:** Reported: *"the second row of icons needs to be
  centered below the editing icons not right aligned."* Confirmed in
  `editor.py`: `_build_tools_bar()` (the row of tool icons — Highlight,
  Circle, Arrow, Rectangle, Pen, etc.) wraps its tool-icon group in
  `layout.addStretch()` on **both** sides, centering it as a group in the
  available width. `_build_settings_bar()`, the row directly below it, does
  not follow the same pattern: there's no leading stretch at all — the
  zoom/stroke/arrow-style/opacity controls are packed flush against the
  left edge, then a single `layout.addStretch(1)` pushes Copy, Export and
  Save PNG all the way to the right edge. The two rows use different
  alignment strategies stacked directly on top of each other, which is
  exactly what reads as inconsistent in the screenshot.
- **Scope:** add a matching leading `layout.addStretch()` at the start of
  `_build_settings_bar()`'s layout, before the zoom controls, so the row's
  full content — zoom through Save PNG — centers as one group the same way
  the tool row above it does. Confirm this is the intended scope (the
  whole row centered as a group, not just the Copy/Export/Save PNG cluster
  centered on its own) before building — it's a visual call the code alone
  doesn't settle.
- **Deliverables:** settings bar content centered as a group, matching the
  tools bar's centering pattern one row above it.
- **Acceptance criteria:** at a typical window width, the settings bar's
  content sits visually centered beneath the tool-icon row, not flush
  against the right edge.
- **Dependencies:** None.

### TA-223 — Drag-selection rectangle resizes unexpectedly crossing a screen boundary

- **Phase:** 3
- **Priority:** P1
- **Suggested labels:** `bug`, `capture`, `multi-display`
- **Problem it solves:** From the first real second-monitor pass, reported
  independently for three cases in the current layout (laptop LEFT @125%,
  external main @100% — negative coordinates *and* mixed DPI):
  - **DSP-03** (capture on the laptop): *"capture point and where icon is
    differ. unable to do selection properly. box being highlighted changes
    when you get close to the right of the screen when laptop is set as
    left screen. size of highlighted section auto changes when going from
    one screen to the next. this is not what i would want to see."*
  - **DSP-07** (capture on the external): *"image does say external however
    size of highlighted section auto changes when going from one screen to
    the next."*
  - **DSP-08** (selection spanning both screens): *"when going over the
    sides then there is an incorrect sizing of the dragged size for the
    image"* (`auto area change.png` saved as evidence).
  - Possibly the same mechanism as **DSP-01** (Block C, secondary on the
    right): *"unable to span the entire screen to the right."*

  Read through `capture.py`'s drag handling
  (`mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent`): it already
  tracks the selection in `event.globalPosition()` throughout (not
  window-local coordinates), which is the fix the earlier
  `overlay-geometry-fix-brief.md` recommended and which is meant to make
  the rectangle independent of window geometry.

  **Resolved, 2026-09-15 — measured on real hardware, not a coordinate bug.**
  `docs/TA-233.md`'s HW-6 pass recorded and frame-measured a real
  boundary-crossing drag: each screen's own on-screen highlight piece is a
  single widget (`_OverlayWindow`, `capture.py`) sized in that screen's
  logical coordinates, which Qt renders at that screen's own
  `devicePixelRatio()` — so the laptop's (@1.25 DPR) piece and the
  external's (@1.0 DPR) piece are, correctly, different physical sizes for
  the identical logical rectangle. Measured ratio (308px/246px = 1.2520)
  matched the screens' own DPR ratio (1.25) within rounding across 22
  consecutive frames of a continuous drag, not a one-frame fluke. This is
  the "size... auto changes when going from one screen to the next"
  symptom in DSP-03/DSP-07/DSP-08 above, fully explained as expected
  DPI-aware rendering — not a `globalPosition()` rounding discontinuity,
  which was a plausible but unconfirmed mechanism and did not hold up.
  Guarded by `test_TA233_HW6_per_screen_highlight_extent_scales_by_its_own_dpr`
  in `python/tests/test_screen_geometry.py`.
- **Scope:**
  - ~~Log the raw values `mouseMoveEvent` receives...~~ — done; see
    "Resolved" above. No code change needed for the resize-at-boundary
    symptom.
  - Still open, not covered by the above: whether DSP-01 ("unable to
    span... to the right") is the same mechanism under a different screen
    arrangement, or a separate issue — not measured either way.
- **Deliverables:** ~~a confirmed measurement...~~ — done, see "Resolved."
- **Acceptance criteria:** dragging a selection across the laptop/external
  boundary in the reporter's exact layout produces a rectangle that tracks
  the cursor smoothly, with no visible *jump* at the crossing (confirmed —
  see `docs/TA-233.md` HW-6's reticle-tracking measurement, 24 sampled
  frames, smooth x motion, no jumps). A *resize* at the crossing is
  expected, correct DPI-aware rendering, not a defect to eliminate.
- **Dependencies:** None.

### TA-224 — Recording has no region-selection, only full-screen

- **Phase:** 3
- **Priority:** P2
- **Suggested labels:** `enhancement`, `capture`
- **Problem it solves:** Reported (DSP-11): *"as it is full screen this
  always plays back correctly. unable to do area selection first for
  recording."* Confirmed in code — this isn't a regression, it's a
  capability that has never existed: `launcher.py::_start_recording()`
  calls `self._recorder.start(self._current_screen())`, and
  `FrameRecorder.start()` takes a screen, not a rectangle. Every recording
  captures a whole screen; there is no drag-a-region step before recording
  the way there is for a still capture.
- **Scope:** decide explicitly whether region-selection recording is in
  scope for 1.4.0 or a deferred enhancement — it's a real feature gap, not
  a small fix, and needs its own scoping pass (reusing the same drag-select
  overlay `ScreenshotOverlay` already provides, then recording only that
  sub-rectangle) rather than being folded into this ticket unscoped.
- **Deliverables:** an explicit decision recorded here (build it for 1.4.0,
  or defer it with the reason), not a silent gap.
- **Acceptance criteria:** N/A until the scope decision above is made.
- **Dependencies:** Reuses `ScreenshotOverlay`'s existing drag-select
  mechanism if built.
- **Decision, 2026-09-09 (`docs/ta215-225-fix-brief.md`): deferred past
  1.4.0.** This is a net-new capability (region-select before recording),
  not a bug, and 1.4.0's scope has already grown from seven tickets to
  sixteen since the manual pass started. No code change made. Reusing
  `ScreenshotOverlay`'s drag-select overlay for a sub-rectangle recording
  is still the intended approach whenever this is picked up — noted here
  so the scoping pass above doesn't need to be redone from scratch.

### TA-225 — Capture on the laptop (Block D, secondary above) produces no visible content

- **Phase:** 3
- **Priority:** P1
- **Suggested labels:** `bug`, `capture`, `multi-display`
- **Problem it solves:** Reported (DSP-04, laptop above/negative-Y layout):
  *"information not displayed even though the wording of laptop and
  external where highlighted."* Read literally: the drag selection
  correctly highlighted the region containing the on-screen `LAPTOP LAPTOP
  LAPTOP` test text, but the resulting capture didn't show it. Block D is
  separated on a single axis (vertical only, no horizontal offset), which
  is exactly the case `TA-209` says `plan_capture()` should already handle
  without gaps — so either this is a new edge case in the single-axis
  path, or it shares the same root cause as `TA-223` (a wrong/degenerate
  selection rectangle produced *during the drag*, before `plan_capture()`
  ever runs on it). Not enough information yet to tell which — needs a
  repro with the actual captured image and the coordinates
  `plan_capture()` received, not a guess.
- **Scope:** reproduce with logging on real hardware (the selected rect
  as dragged, and what `plan_capture()` did with it); compare against
  `TA-209`'s and `TA-223`'s findings once those have their own answers —
  this may turn out to be the same bug reported three ways rather than a
  third independent one.
- **Deliverables:** a confirmed repro and either a fix or a merge into
  `TA-209`/`TA-223` if the mechanism turns out to be shared.
- **Acceptance criteria:** capturing on the laptop in the secondary-above
  layout produces an image showing the actual on-screen content.
- **Dependencies:** Likely related to `TA-209`, `TA-223` — confirm before
  fixing independently.

### TA-226 — No CI path can verify real font rendering or on-screen layout

- **Phase:** 2
- **Priority:** P2
- **Suggested labels:** `testing`, `infra`, `ci`
- **Problem it solves:** TA-221's own acceptance criterion asked for a
  screenshot confirming the Copy/Export buttons render unclipped. It
  couldn't be produced: `conftest.py` sets `QT_QPA_PLATFORM=offscreen` by
  default, and `.github/workflows/python-tests.yml` pins the same value at
  the job level, and Qt's offscreen platform plugin does not rasterize real
  glyphs — a screenshot taken under it is tofu boxes, not text. rc5's fix
  was verified by a measurement-based proxy (natural height now matches
  `_btn_save_png`'s already-unclipped 28px) instead of the real thing the
  ticket asked for. This isn't specific to TA-221 — any future clipping,
  alignment, or icon-rendering regression hits the identical wall, and would
  keep needing a manual screenshot pass to actually confirm.
  Not a platform limitation: CI already runs on `windows-latest` — a real
  Windows machine, not Linux-under-Xvfb — so real font rendering is
  available today. `offscreen` is a constraint the suite chose for itself
  (almost certainly for speed and to avoid a visible window during the main
  run), applied blanket to every test, not something Windows requires.
- **Scope:**
  - Add a second, separate test lane — a marker (e.g.
    `@pytest.mark.visual`) or its own test module — that runs without the
    `offscreen` override, against the real `windows` Qt platform plugin, and
    asserts against an actual `QWidget.grab()` screenshot.
  - Pick one concrete assertion mechanism and say why: a pixel-diff against
    a checked-in golden image is the obvious first idea, but is brittle to
    font-hinting/DPI drift whenever the CI image's Windows or font-package
    version changes underneath it. A bounding-box check — render the
    widget, measure the actual ink extent of its text/icon, assert it stays
    inside the widget's client rect — doesn't drift the same way and is
    closer to what "not clipped" literally means. Decide this explicitly in
    the PR rather than defaulting to whichever is easiest to write first.
  - Retrofit TA-221's own acceptance criterion as the first real test in
    this lane — closes the "one honest gap" flagged in rc5's `BUILD_LOG.md`
    entry instead of leaving it as a permanent manual step.
  - Wire it into `.github/workflows/python-tests.yml` as its own job or
    step, separate from the main `offscreen` suite, so a slower or flakier
    visual check never blocks the fast suite everything else depends on.
  - Note in whichever test-plan doc this project uses for its testing
    conventions: which class of future ticket belongs in this lane
    (rendering/layout) versus the main suite (everything else).
- **Deliverables:** a working visual test lane on real Windows font
  rendering; TA-221's clipping check as its first real test, verified to
  fail against the pre-rc5 code and pass against current code; CI wiring
  that keeps it independent of the main suite's pass/fail.
- **Acceptance criteria:** the new lane runs on `windows-latest` without the
  `offscreen` override; the retrofitted TA-221 test fails when pointed at
  the old `setFixedHeight(26)` code and passes against current code; a
  failure in this lane does not fail the main suite's job.
- **Dependencies:** None. Not a release gate by itself — it's what would
  have caught TA-221 automatically instead of a manual screenshot pass, and
  is meant to catch the same class of bug going forward.
- **Verified:** ✅ 2026-09-09, per `docs/ta215-225-fix-brief.md`'s follow-up
  brief `docs/ta226-visual-test-lane-brief.md`. `tests/test_visual.py`
  added (`@pytest.mark.visual`, excluded from the default run by
  `pytest.ini`'s `-m "not visual"`, run as its own `visual` job in
  `python-tests.yml` against the real `windows` Qt platform plugin,
  `continue-on-error: true` so it cannot block anything gating on the
  workflow's overall conclusion). Assertion mechanism: bounding-box/ink-
  extent against a real `QWidget.grab()` screenshot, not a pixel-diff
  golden image — chosen specifically to not become the kind of
  font-hinting/DPI-brittle fixture this ticket exists to move away from.
  Main suite unaffected: `320 passed, 0 skipped` (2 deselected), identical
  to rc5.
  **One acceptance-criterion gap found while verifying, reported rather
  than hidden:** reverting `_btn_copy`/`_btn_export_json` to the pre-fix
  `setFixedHeight(26)` does **not** reproduce visible clipping on this
  machine's real font rendering — measured at 12 ink rows out of a 14-row
  unclipped maximum, identical to `_btn_save_png`'s own untouched
  `setFixedHeight(28)` (already treated as fine). This is font-metric
  drift across machines/ClearType settings exactly as this ticket's own
  "Problem it solves" section warned about, not a flaw in the test — the
  retrofitted test still checks the real, literal acceptance criterion
  against the code as shipped (passes, for real, against real rendering),
  and a second test in the same file
  (`test_ink_extent_detection_actually_catches_a_clipped_button`) proves
  the detection mechanism itself does catch a real, deliberately
  undersized button on this same hardware, independent of whether the
  specific historical height reproduces it. Full measurement in
  `docs/BUILD_LOG.md`'s TA-226 entry.

### TA-227 — Capture-dispatch tests stub the very thing they're supposed to prove works

- **Phase:** 2
- **Priority:** P2
- **Suggested labels:** `testing`, `quality`
- **Problem it solves:** Both TA-217 tests —
  `test_TA217_global_hotkey_closes_an_open_about_dialog_before_capturing` and
  `test_TA217_quick_capture_button_closes_an_open_about_dialog_before_capturing`
  (`python/tests/test_regressions.py`) — replace `launcher._start_capture`
  with `lambda: calls.append("start_capture")` before triggering the path
  under test, then assert `calls == ["start_capture"]`. That proves the
  function was *called*. It does not, and structurally cannot, prove a real
  capture overlay ever became visible or interactive — the actual
  `_start_capture()` → `QTimer.singleShot(220, self._overlay.activate)`
  chain never runs in either test, because the stub replaces it entirely.
  This is exactly the shape of gap TA-217's own ticket already called out
  by name: *"was it asserting the right thing, or just that
  `_dismiss_active_modal_dialog` was called, not that a capture actually
  resulted?"* — confirmed here by direct code read, not inference. It means
  TA-217's still-open "hotkey path dismisses the dialog but doesn't
  capture" gap could regress *again* in either direction and both of these
  tests would stay green throughout.
  The button-path test has a second, smaller version of the same shape: it
  calls `launcher._on_action_click` directly via `QTimer.singleShot` rather
  than clicking the real `_btn_capture` widget, skipping the signal/slot
  wiring Qt itself provides between the button and the handler.
- **Scope:**
  - Retrofit both named tests so the real `_start_capture()` runs — no stub
    — and the assertion is on the real end state: the overlay
    (`launcher._overlay`) is visible, active, and able to receive input,
    not just that a function was invoked. Use whatever mechanism this file
    already uses elsewhere for letting an async Qt chain actually complete
    before asserting (`QTest.qWait()` appears in `test_functional.py` for
    exactly this reason) rather than inventing a new pattern.
  - In the button-path test, trigger the real click
    (`launcher._btn_capture.click()`) instead of calling
    `_on_action_click` directly, so the signal/slot wiring itself is
    exercised too, not just the handler body.
  - Grep the rest of `test_regressions.py` and `test_functional.py` for the
    same shape — a dispatched action replaced with a
    call-recording lambda, then only the call recorded is asserted on —
    and retrofit any other case found where the stubbed thing is the
    actual behavior the ticket exists to prove. Report what was found, even
    if the answer is "no other instance of this shape."
  - Note the convention going forward (a line in whichever doc already
    carries this project's testing conventions): a dispatch/wiring test
    stubs the *side effects downstream of* the action under test (file
    I/O, network, the OS hotkey API), never the action's own immediate,
    in-process effect — that's the one thing the test exists to check.
- **Deliverables:** both retrofitted tests, verified to still pass against
  current code and to fail if `_start_capture()`'s call is removed from
  either dispatch path (the actual regression this ticket exists to catch);
  a report on whether the same shape exists elsewhere; the convention note.
- **Acceptance criteria:** reverting either the hotkey-path or button-path
  call to `_start_capture()` (a deliberate, temporary regression) makes the
  corresponding retrofitted test fail — not just a function-call assertion,
  a real observed absence of the overlay.
- **Dependencies:** None.
- **Verified:** ✅ 2026-09-09, per `docs/ta227-228-e2e-testing-brief.md`.
  Both named tests retrofitted: `_start_capture` no longer stubbed, real
  end state asserted (`launcher._overlay.isVisible()`, then a real
  press/move/release drag through the real overlay confirmed via a real
  `capture_ready` emission with a non-null pixmap) instead of a
  function-call assertion; button-path test now triggers
  `launcher._btn_capture.click()` instead of calling `_on_action_click`
  directly. Verified to fail two ways, each restored after: (1) removing
  the `_dismiss_active_modal_dialog()` call reintroduces the original
  rc4 regression and fails on the pre-existing dismiss assertion; (2)
  keeping that call but removing `_start_capture()` itself fails
  specifically on the *new* `isVisible()` assertion, confirming the
  retrofit adds real, independent detection power, not just riding on
  the older check. Full suite: `320 passed, 0 skipped` (2 deselected),
  unaffected.
  **Grep for the same shape, repo-wide:** every other
  `lambda: ...append(...)` stub in both test files checked against the
  ticket's own rule (stub only what's downstream of the action under
  test, or a method with its own independently-verified real-effect
  test elsewhere, or a real signal-spy — never the action's own
  immediate effect). Found no other instance of the flawed shape:
  TA-211's hotkey-routing test stubs `_start_capture` etc. but its own
  claim is narrowly "routes to the right handler," not "capture
  works," and that broader claim is now covered by TA-217's retrofit
  above; the DSP-15 restore-repositioning tests stub
  `_position_top_right`/`_dock_right` but each has its own real,
  unstubbed correctness test elsewhere
  (`test_launcher_position_top_right_uses_the_screen_the_widget_is_on`,
  `test_launcher_dock_right_moves_to_expected_x_position`); the TA-218
  Editor-button test stubs `_check_for_updates` but its own claim is
  narrowly "reaches the launcher's checker," with the checker's own
  logic covered by UPD-01 through UPD-11; `QApplication.quit`/
  `primaryScreen` stubs are system-API-boundary substitutions, not
  app-logic shortcuts; every `signal.connect(lambda: ...)` found is a
  spy on a real signal, not a stand-in for a mechanism. Convention note
  added to `DESKTOP_STABILITY_MATRIX.md`. Full findings in
  `docs/BUILD_LOG.md`'s TA-227 entry.

### TA-228 — No test drives the actual packaged app from outside the process

- **Phase:** 3
- **Priority:** P2
- **Suggested labels:** `testing`, `infra`, `e2e`
- **Problem it solves:** Every test in this suite, including TA-227's
  retrofit above, imports `python/`'s modules directly into the test
  process and drives them in-process — real Qt signal/slot wiring, but
  still one process, one Qt event loop, Qt's *own* idea of window state.
  That's exactly why TA-220's minimize-toggle gap and TA-217's
  hotkey-capture gap are still "instrumented, not fixed" rather than
  actually fixed: nothing in this suite can observe what the real Windows
  window manager does with a real separate top-level window under real
  focus/Z-order rules, which is precisely where both unconfirmed hypotheses
  live (`isActiveWindow()` timing against a *different* top-level window;
  whether the overlay actually receives real OS-level input after a
  hotkey). Debug logging plus a manual pass was the best available option
  in-process; a black-box layer driving the actual built `.exe` is what
  could close that gap for good instead of needing a human on real hardware
  every time.
- **Scope:**
  - Add `pywinauto` as a Windows-only, dev/test-only dependency — it drives
    a real running application from outside via Windows UI Automation, the
    native-desktop equivalent of what a browser-automation tool does for a
    web page. Not bundled into the shipped app.
  - New, clearly separate test lane — its own module or directory (e.g.
    `tests_e2e/`), not mixed into `test_regressions.py`/`test_functional.py`
    — that launches the actual built `python/dist/TestAssist/TestAssist.exe`
    as a subprocess and drives it via `pywinauto`, not by importing the
    Python modules.
  - Start deliberately small — three checks, not broad coverage:
    1. The app launches and its main window/tray icon appears within a
       timeout.
    2. Clicking the real Quick Capture button produces a real, visible
       overlay window (owned by the OS, not asserted from inside the
       process).
    3. Minimize/restore via the TA icon changes the *real* OS window state
       (`pywinauto`'s own maximized/minimized checks, not Qt's internal
       flags) — the direct, actual test of TA-220's still-unconfirmed
       hypothesis.
  - Decide explicitly, and record the decision here rather than defaulting
    silently: does this lane run in CI (needs a build step before the
    tests, adding real CI time for three checks) or stay a documented
    local/manual smoke pass for now, promoted to CI once it's proven its
    worth? Recommendation, not a mandate: start local/manual — a
    `scripts/` helper run against an already-built exe — since building
    just to run three checks is a heavier lift than today's payoff; revisit
    once this lane has caught something real.
  - Document how to run it (README or a new doc) — this can't run from a
    source checkout the way everything else in the suite can; it needs a
    build first.
- **Deliverables:** `pywinauto` added; the three smoke checks; the
  CI-vs-manual decision recorded with its reasoning; a way to run it
  documented.
- **Acceptance criteria:** each of the three checks fails against a
  deliberately broken build (e.g. TA-220's fix temporarily reverted, built,
  and tested) and passes against the current one — same
  verified-to-fail-first discipline as everything else in this project.
- **Dependencies:** Needs a built exe to run against
  (`python/dist/TestAssist/TestAssist.exe`) — cannot run from source alone.
  Complements rather than replaces TA-220's and TA-217's still-open
  investigate-first gaps; a passing check here is what would let those
  finally close without waiting on a manual pass.
- **Verified:** ⚠️ 2026-09-09, per `docs/ta227-228-e2e-testing-brief.md` —
  partially, honestly. `pywinauto` added (`python/tests_e2e/requirements.txt`,
  kept out of `python/requirements.txt`); new `python/tests_e2e/` lane with
  the three checks, kept out of the default `pytest`/`pytest -q` run via
  `pytest.ini`'s new `testpaths = tests`. **Decision recorded (not
  defaulted into):** stays local/manual, not CI-wired — see
  `python/tests_e2e/README.md` for the full reasoning, including a harder
  finding than the ticket's own cost argument (below).
  Check 1 (launch, window appears) is genuinely verified both ways: passes
  against the real build, and errors against a deliberately corrupted exe
  (`CreateProcess` / "not a valid Win32 application") — a real, meaningful
  failure, not a skip (a *missing* exe correctly skips instead, a
  different and correct case).
  **Checks 2 and 3 could not be verified end-to-end in this environment.**
  While building this lane, no synthetic input mechanism tried — UI
  Automation's Invoke pattern, `pywinauto`'s `click_input()` (real OS
  `SendInput`), and the `win32` backend's direct `PostMessage`-based click
  — had any observable effect on the real, correctly-identified running
  app, each checked via an independent real signal (a
  `TESTASSIST_DEBUG=1` log line that never appeared; a UI-Automation
  checkbox toggle-state read-back that never changed). Ruled out, not
  assumed: process DPI awareness (set explicitly), click coordinates
  (confirmed landing on the right window via `WindowFromPoint`), desktop/
  session attachment (`OpenInputDesktop` succeeded, session id matched the
  active console session), and a UIPI mismatch (`whoami /groups` confirmed
  Medium integrity, the normal, unelevated level, for the calling
  process). Both tests are written correctly — verified to fail cleanly
  within their own timeouts (not hang) when input has no effect — but
  "passes against the current build" could not be shown here. This is the
  same class of hardware/environment gap as TA-220/TA-217/TA-223/TA-225,
  not a flaw in the tests, and is exactly why the CI-vs-manual decision
  above went further than the ticket's own cost argument: GitHub Actions'
  hosted Windows runners are a similarly non-interactive automated
  context, so wiring this into CI before confirming synthetic input
  actually works there would risk building on the same false assumption
  that just failed here. Needs running once on a real, interactively-used
  Windows machine to confirm checks 2 and 3 for real. Full account in
  `docs/BUILD_LOG.md`'s TA-228 entry.
  One small production change made in service of this lane, not a UX
  change: `launcher.py`'s `_btn_open_editor` (icon-only, previously
  indistinguishable from its unlabeled siblings to UI Automation) now has
  `setAccessibleName("Open Editor")`, needed for check 3 to reliably find
  it from outside the process — also a real accessibility improvement
  (screen readers now announce it), not solely a test hook. Required a
  rebuild to include; not a new numbered `rc`, since nothing else
  app-facing changed.

  **Re-run on real hardware, 2026-09-09 — the "needs a real interactive
  machine" theory above is disproven, not confirmed.** Run twice on
  Emil's own desktop, both times freshly (no stale instance in the tray
  either run): check 1 passes, checks 2 and 3 fail identically both
  times, same failure shape as the cloud/CI environment.
  Disambiguated directly rather than assumed: with the automated run
  finished, Emil opened Test Assist and clicked Quick Capture and Open
  Editor **with his own mouse** — both work exactly as expected (floating
  widget hides, capture-area targeting icon appears; Editor opens from
  both the floating and docked widget). The app is not regressed. What's
  actually failing is narrower and more specific than "no synthetic
  input reaches the app in this class of environment": `pywinauto`'s
  `click_input()` (real OS `SendInput`) does not register with this
  specific Qt application even from a real, logged-in, interactive
  desktop session — every cause the original investigation ruled out
  (DPI awareness, click coordinates, session/desktop attachment, UIPI
  integrity level) was already eliminated there, and none of those
  explanations depended on the session being non-interactive, so their
  being ruled out again here isn't new information — what's new is that
  the "will just work on real hardware" part of the theory is now
  falsified by a direct test.
  Not yet investigated: whether this is specific to `pywinauto`'s default
  UI Automation backend against a `PySide6`/Qt window (Qt's own input
  handling may not treat OS-level synthetic `SendInput` the same as a
  physically-generated one for reasons unrelated to focus/DPI/session),
  whether `pywinauto`'s `win32` backend (direct `PostMessage`, already
  tried once during the original investigation but not re-tried on an
  interactive session where the message pump behaves differently) fares
  any better, or whether third-party security software on this specific
  machine is intercepting synthetic input to this one process. Checks 2
  and 3 remain correctly designed and this ticket's acceptance criteria
  are still not met — the next step is investigating *why Qt specifically
  ignores this* on a session that accepts real mouse input from Windows
  itself, not another "try it somewhere more interactive" attempt.

  **Root cause found and confirmed, 2026-09-09, per
  `docs/ta228-synthetic-input-investigation-brief.md`.** Not Qt-specific,
  not this project's code, not the environment: a raw `SendInput` mouse
  *move* was confirmed reaching the OS (`GetCursorPos` moved to the exact
  target), but a raw `SendInput` button click at the same point had zero
  effect against a from-scratch, non-Qt Tkinter test window — pinning the
  block to button-press delivery specifically, system-wide, independent of
  Qt entirely. Traced to `XMouseButtonControl.exe` (X-Mouse Button Control
  2.20.5), a third-party mouse-button remapper whose entire mechanism is a
  system-wide low-level mouse hook on button press/release events, not
  movement — exactly the split measured. Confirmed directly, with the
  user's go-ahead: stopping it made the identical `SendInput` click, and
  `pywinauto`'s own `click_input()`, work immediately; restarted afterward.
  Re-ran the real `pytest tests_e2e` suite with it stopped: **check 1
  passes, check 2 now genuinely passes for the first time (Quick Capture
  produces a real overlay, no caveat), check 3 fails — consistently,
  re-run twice — for a new and different reason.** Input delivery is no
  longer the blocker (check 2 proves that), so check 3's failure now looks
  like a real reproduction of this ticket's own still-unconfirmed
  minimize-toggle hypothesis, or a test-timing artifact — not chased
  further here per the investigation brief's explicit scope boundary; see
  `docs/BUILD_LOG.md`'s TA-228 follow-up entry for the full account and
  flag a new ticket before investigating check 3 further. Acceptance
  criteria: checks 1 and 2 now met for real; check 3 still open, but for
  an app-behavior reason rather than an infrastructure one. CI-vs-manual
  decision unchanged.

  **Re-run 2026-09-16, after TA-241 shipped — a genuinely new mechanism,
  not a re-reproduction of the old one.** Fresh 1.5.0 build
  (`build.ps1`, "Built and verified: Test Assist 1.5.0"), no stale
  `TestAssist.exe` in the tray, `XMouseButtonControl.exe` confirmed not
  running (checked via `tasklist`, so it needed no stopping this pass —
  asked first rather than assuming last session's go-ahead carried
  forward). `pytest tests_e2e`:

  - **Check 1 — pass.** Same as every prior run.
  - **Check 2 — fail.** `TimeoutError` waiting for a button titled
    "Quick Capture" to appear. Confirmed by dumping the real launcher's
    UI Automation control tree directly: that button is now named
    **"Capture Region"** — the `ui-polish` launcher rebuild (merged into
    `main` this session, well after `test_smoke.py` was last touched)
    replaced the old single "Quick Capture" button with three separate
    actions, and the test's selector was never updated to match.
  - **Check 3 — fail.** `pywinauto.findwindows.ElementAmbiguousError:
    There are 2 elements that match the criteria {'title': 'Editor', ...}`
    — confirmed via the same control-tree dump: **two** buttons are now
    named "Editor" in the floating panel simultaneously (the header
    icon-only button and a separate wide button below RECENT, at
    different screen rectangles) — both always present together when
    undocked, which is the launcher's default state. The test's
    `child_window(title="Editor", ...)` selector, written against the
    pre-rebuild single-button launcher, is no longer unique.

  **This is not the previous blocker recurring.** The `SendInput`/
  `XMouseButtonControl.exe` block that defeated checks 2 and 3 before
  would have produced silent no-effect timeouts with no other symptom;
  what happened instead is `TimeoutError` (target genuinely doesn't
  exist under that name) and `ElementAmbiguousError` (pywinauto's own
  UI Automation query mechanics working correctly, enumerating and
  disambiguating real controls) — both are pywinauto successfully
  talking to the real app and failing only on a stale selector, the
  opposite signature from an input-delivery block. **So the theory this
  re-run was meant to test — does TA-241's `WindowDoesNotAcceptFocus`
  fix make check 3 pass — is still unconfirmed, not disproven**: check 3
  never got far enough to click anything, let alone test a minimize
  toggle. Filed as this fresh finding rather than folded into the
  already-closed input-delivery investigation, per that investigation's
  own scope boundary.

  **CI-vs-manual decision: not revisited, stays local/manual for now** —
  a stated opinion, not left silent. The original blocker this decision
  was partly built on (non-interactive contexts not delivering synthetic
  input) is confirmed gone this run, which does weaken that specific
  argument. But the lane is not close to reliably green either way right
  now — 2 of 3 checks fail today, for a reason (selector staleness
  against `ui-polish`'s launcher rebuild) that has nothing to do with
  environment interactivity and everything to do with `tests_e2e` not
  being kept in sync with app changes, which not being CI-wired makes
  more likely, not less. Promoting an unreliable lane to CI now would
  just start reporting red for reasons unrelated to real regressions.
  Worth revisiting once `test_smoke.py`'s selectors are updated to match
  the current UI and the lane passes cleanly again.

### TA-229 — `to_device_rect()` can seam a three-or-more-piece capture at a fractional device pixel ratio

- **Phase:** 3
- **Priority:** P3
- **Suggested labels:** `bug`, `capture`
- **Problem it solves:** `to_device_rect()` rounds each piece's x, y, width
  and height independently. For two pieces this is safe by construction —
  piece 2's `dest.x` equals piece 1's width, so both the per-piece rounding
  and `device_result_size()`'s whole-rect rounding round the same
  expression, `round(w1*ratio)`. For three or more pieces that guarantee
  does not hold: `round(w1*r) + round(w2*r) + round(w3*r)` is not
  guaranteed to equal `round((w1+w2+w3)*r)`. Confirmed, not merely
  reasoned: three synthetic screens 297/297/298px wide produce a 1px
  unpainted gap at ratio 1.25 (1114 covered vs. 1115 wanted) and a 1px
  overlap at ratio 1.5 (1339 vs. 1338) — see
  `test_three_piece_layout_can_seam_at_a_fractional_ratio` in
  `python/tests/test_screen_geometry.py`, added and confirmed failing
  (`xfail(strict=True)`) while completing PR #8. The two-piece case (every
  real layout this project has hardware to test) is unaffected — see
  `test_device_pieces_tile_the_result_without_gap_or_overlap`, now covering
  1.25 and 1.5 alongside the integer ratios and staying green throughout.
  1.25 and 1.5 are the ratios that matter (Windows' 125%/150% presets),
  not the integers the original test used.
- **Scope:**
  - A packing/rounding scheme where a piece's placement is derived from
    the *previous* piece's already-rounded edge (cumulative rounding)
    rather than each piece rounding its own offset from zero independently
    — the same class of fix as carry-propagated rounding elsewhere.
  - Extend `test_three_piece_layout_can_seam_at_a_fractional_ratio` (or
    replace it) to a real regression guard once fixed, removing the
    `xfail`.
- **Deliverables:** Either a fix with the `xfail` removed and turned into a
  passing regression test, or this entry staying open with the limitation
  documented — not both left silently inconsistent.
- **Acceptance criteria:** Three-or-more-piece layouts tile without gap or
  overlap at 1.25 and 1.5, not just at integer ratios.
- **Dependencies:** Related to but distinct from TA-209 (which is about
  `plan_capture()` leaving an axis-packing gap for layouts separated on
  both axes) — this is a rounding defect within a single axis's packing,
  reachable even when TA-209 is fixed. Real-hardware verification needs
  three screens at fractional scaling, which is not available; not
  blocking this release, which does not claim three-screen spans.

### TA-230 — The `register_global_hotkeys` path is structurally untested, and has cost time three times in two days

- **Phase:** 3
- **Priority:** P2
- **Suggested labels:** `testing`, `quality`, `technical-debt`
- **Problem it solves:** `FloatingLauncher`'s `register_global_hotkeys`
  parameter defaults to `False`, because the `True` path claims real,
  process-wide OS state via `RegisterHotKey` that concurrent tests would
  fight over. That is a sound precaution, and it leaves an entire code path
  exercised only by five Windows-only `skipif` tests. The cost is no longer
  hypothetical — it has surfaced three times in two days, each time in a
  different way:

  1. **2026-09-11, fixed in `5c5e0a1`.** `_apply_hotkey_labels()` still
     addressed `_btn_photo` and `_btn_video` after the launcher rebuild
     removed them. **The app died on startup with an `AttributeError` while
     350 tests stayed green**, because that method runs only when
     `register_global_hotkeys=True` and every test avoids it.
  2. **2026-09-11, fixed in `aca5463`.** Three TA-211 tests referenced the
     same removed attributes. They are `skipif`-guarded to Windows, so every
     run on a Mac reported green **by construction** — the only tests that
     would have failed were the ones that never ran. It surfaced on someone
     else's Windows machine, which is the worst place to find it.
  3. **2026-09-12, during PR #8's release gate.** A `TestAssist.exe` left
     running from the manual capture check still held the real Win32
     hotkeys, so the TA-211 tests' own `RegisterHotKey` calls failed. Three
     phantom failures that read as a code regression *during a release*.
     Correctly diagnosed as leftover process state rather than written off
     as flaky — but only after investigation, mid-release.

  The shape was already named in `docs/SESSION_HANDOVER_2026-09-11.md` §7.2
  ("paths the suite deliberately avoids"). This ticket is the evidence that
  the shape costs real time, and the record that stops a fourth occurrence
  being re-derived from scratch.

  **Three distinct sub-problems wear this one label**, and they have
  different remedies:

  - **(A) Coverage.** The parts of the `True` path that need no OS call —
    principally that `_apply_hotkey_labels()` addresses widgets that exist —
    can be tested without one. Partly addressed already: `5c5e0a1`'s test
    sets `_hotkey_registered` directly rather than registering for real.
  - **(B) Cross-platform blindness.** A `skipif`-guarded test rots silently
    between the runs that actually execute it. Partly addressed already:
    `test_LAUNCH_09_every_launcher_attribute_this_suite_names_exists` scans
    the suite for `launcher.<attr>` references and asserts a real launcher
    has each one — and it runs everywhere, including where the guarded tests
    are skipped.
  - **(C) A foreign hotkey holder.** A genuinely running instance makes the
    suite fail opaquely. Not a code defect — `RegisterHotKey` is behaving
    correctly and the test is asserting the right thing — but the diagnosis
    is invisible from the failure message.

  **Both (A) and (B)'s mitigations currently exist only on `ui-polish`
  (PR #19)**, deferred to 1.5.0. Their real-world instances were caused by
  the launcher rebuild on that same branch, so 1.4.0 is not exposed to
  those two — but the mechanism they guard is general, not rebuild-specific.

- **Scope:**
  - **(C), the concrete fix:** a precondition in the TA-211 tests that
    detects a foreign `RegisterHotKey` holder and reports it as a named skip
    or an explicit failure — "Alt+P is held by another process; close any
    running Test Assist (check the tray)" — rather than a bare assertion
    failure that reads as a code regression.
  - **(A) and (B), the decision:** state explicitly whether those two
    mitigations should be cherry-picked to `main` independently of the
    launcher rebuild, or wait and arrive with PR #19 in 1.5.0. Decide it;
    do not let it default by inaction.
  - A note in whichever document carries this project's testing conventions:
    a default-off flag guarding real OS state is a recognised coverage
    hazard, with this ticket as the worked example.
- **Deliverables:**
  - (C)'s precondition check, with a test proving it reports the right thing
    when a hotkey is deliberately held.
  - The (A)/(B) decision, written down whichever way it goes.
  - The convention note.
- **Acceptance criteria:**
  - Running the suite with a Test Assist instance deliberately left running
    produces a message naming the cause, not three unexplained assertion
    failures.
  - The (A)/(B) decision is recorded, with its reasoning.
- **Dependencies:** None, and **not release-blocking for 1.4.0** — no
  user-facing behaviour is involved. (C) is developer experience; (A) and
  (B)'s instances were both caused by PR #19's rebuild, which is deferred.

**2026-09-16 (later) — (C) closed.** `hotkeys_available`, a fixture in
`test_regressions.py`, probes the same three combinations
`_register_hotkeys()` registers (claim-and-release with a throwaway id,
`MOD_NOREPEAT` included to match `GlobalHotkeyManager.register()`
exactly) and is applied to the four tests that construct a real launcher
with `register_global_hotkeys=True` for reasons other than deliberately
testing a conflict — `test_TA211_global_hotkeys_register_and_are_advertised`,
`test_TA211_global_hotkey_dispatch_routes_to_the_right_action`,
`test_TA211_an_unrelated_native_message_is_ignored`,
`test_TA211_hotkeys_are_released_on_close`.
`test_TA211_a_failed_registration_is_surfaced_and_not_advertised` is
deliberately left without it, per this ticket's own Scope — it exists to
create exactly the condition the precondition detects, on purpose.
Verified end to end, not just read from the code: with Alt+P claimed
from an external process, the four guarded tests now skip with `Alt+P is
held by another process; close any running Test Assist (check the
tray)` instead of failing; the excluded test fails at its own setup
assertion in that same run, which is expected and correct — it has no
precondition by design, and a real external conflict coinciding with its
own simulated one is exactly the contrived case it isn't equipped for.
`test_TA230C_precondition_names_a_deliberately_held_hotkey` covers the
ticket's own acceptance bar (claims Alt+P from the test itself, same
pattern as the excluded test, asserts the precondition names it
specifically). (A) and (B) were already confirmed closed earlier this
session (see the 1.5.0 status section above) — all three sub-problems
are now closed. The convention note is in `docs/WORKING_AGREEMENTS.md`'s
"Two things already learned here" section, a third entry alongside the
two this ticket's own text already referenced.

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

---

## 1.5.0 status (2026-09-16)

`fix/ta-232-overlay-hidpi-coverage` and `ui-polish` both landed on `main`
for this release. Full sequencing and the `python/launcher.py` collision
resolution are in `docs/RELEASE_1.5.0_PLAN.md`.

**Deviation from that plan, found during the rebase:** `ff0f276` (the
indigo/light-follows-OS palette commit the plan called for dropping) could
not be cleanly excised — commits as little as 16 minutes later
(`951e24a`, "follow the OS light/dark setting") depend on the theme-token
plumbing `ff0f276` introduces, so dropping it broke 20+ conflicting hunks
across `launcher.py`/`theme.py` in the very next commit. Kept `ff0f276`
and the rest of the chain intact instead. Since `_DARK`'s own `ACCENT` had
by then become indigo (to match the editor, with amber demoted to a
light-mode-only accent), restoring amber meant pinning the launcher's
whole palette independent of the OS light/dark toggle, not swapping one
token — `69e692c` adds `theme.LAUNCHER`, a fixed dark/amber snapshot
`launcher.py`'s ~40 styling call sites read instead of the shared
`theme.*` globals `editor.py` reads, so an OS light-mode session changes
the editor but not the launcher.

- **TA-241 — closed.** The floating toolbar no longer steals OS focus from
  an already-open editor (`d8b67b1`, `python/launcher.py`'s
  `WindowDoesNotAcceptFocus` flag). Full account: `docs/ISSUE-TA-241.md`.
  `test_TA241_launcher_does_not_accept_focus` confirmed passing against the
  rebuilt `FloatingLauncher` on `ui-polish-rebased`, not just carried
  through without conflict markers. **Also confirmed on real hardware**
  post-merge (2026-09-16): opening the editor, then clicking the TA icon
  again while it's frontmost, minimizes it correctly against the merged
  `main` build — the plan's one remaining unchecked item.
- **TA-231 — closed.** The black band an unequal-height spanning selection
  produced is real transparency correctly composited, not an opaque-black
  compositing bug (`1df02f9`, gives the composite canvas a real alpha
  channel). Full account: `docs/TA-231.md`.
- **TA-232 — closed for this release.** The per-screen overlay fix (one
  `ScreenshotOverlay` per `QScreen`, each inheriting its own DPR) ships on
  this branch. Re-confirmed on a pre-fix build the same evening
  (`docs/TA-232-HARDWARE-VERIFICATION.md`'s 2026-09-16 entry) with explicit
  user sign-off that this branch's overlay behaviour takes precedence over
  `main`/`v1.4.0`'s at merge time.
- **TA-217 — left open, reopened.** See the entry above: the button path
  (`_btn_capture` / `_btn_dock_capture`) is still an unqualified no-op
  against a modal dialog; the hotkey path completes a real capture but
  can't reach the dialog itself before it closes. Not fixed in 1.5.0.
- **TA-239 — carried forward, not a 1.5.0 blocker.** Debug instrumentation
  (`capture.py::_grab()`, gated by `TESTASSIST_DEBUG=1`) is in place but
  not yet exercised — needs a real cross-screen drag on hardware once a
  build with this code is deployed. `docs/ISSUE-TA-239.md`.
- **HW-5 — carried forward, not a 1.5.0 blocker.** Not code: closing the
  384px gap between the two screens in Windows Display Settings, then
  retesting, is an action item for whoever is at the physical rig.

The Launcher Evaluation Pass also filed six new tickets from live testing
of the `ui-polish` rebuild — `TA-242` through `TA-247`
(`docs/ISSUE-TA-242.md`–`TA-247.md`) — none release-blocking; `TA-247` is
explicitly filed as backlog, not a blocker, per the pass's own decision
record.

- **TA-248 — carried forward, cosmetic, not a 1.5.0 blocker.** Found
  during the TA-241 hardware repro above: the editor control's label
  ("Open Editor," all three call sites) still only describes the "open"
  half of what `bring_forward()` now correctly does on a second click.
  `docs/ISSUE-TA-248.md`.

---

## Backlog audit & bundles (2026-09-16)

Every ticket TA-201 through TA-248 checked against the current `main`
(post-1.5.0-merge) code, not against what its own text last claimed —
each verdict below cites what was actually grepped/read, not the
ticket's own prior "Verified" note taken on faith where one existed.

### Closed, confirmed against current code

TA-201 (committed/pushed, superseded by every release since), TA-202
(`paths.py` exists with exactly the scoped functions), TA-207 (`1.4.0`
tagged and shipped, confirmed in `main`'s own log), TA-211 (global
hotkeys live — `main.py` passes `register_global_hotkeys=True`, and every
later ticket's hardware evidence depends on Alt+P actually firing), TA-214
(`Ctrl+V` shortcut and `getOpenFileName()` both present, comment cites
TA-214 directly), TA-216, TA-218, TA-219, TA-221 (`setFixedHeight(26)`
removed from `_btn_copy`/`_btn_export_json` entirely — sizes naturally
now), TA-222 (`_build_settings_bar()` now has a leading `addStretch()`
that didn't exist before, matching the centering pattern), TA-223
(explained and guarded by a passing regression test, not a defect),
TA-226, TA-227, TA-230 (A)/(B) (`test_LAUNCH_09_...` confirmed present on
`main` — these mitigations were `ui-polish`-only until tonight's merge,
now landed), TA-231, TA-232, TA-241.

**TA-220 — closed, but via two different mechanisms worth knowing apart:**
sub-item 1 (restore to maximized, not windowed) is fixed directly in
`bring_forward()` (`editor.py`) — checks `WindowState.WindowMaximized`
before choosing `showMaximized()`/`showNormal()`. Sub-item 2 (the
minimize-toggle not firing reliably) is fixed by TA-241 — the fix
isn't in `editor.py` at all, it's `launcher.py`'s
`WindowDoesNotAcceptFocus` flag stopping the launcher from stealing
activation in the first place, confirmed on real hardware tonight.
**Housekeeping gap, not a functional one:** `bring_forward()`'s own
comment still describes the minimize-toggle cause as "unconfirmed" and
says it's only logging values rather than fixing it — stale now that
TA-241 has actually fixed the underlying mechanism elsewhere. Worth a
one-line comment update so a future reader doesn't re-investigate a
solved problem.

### Open, real work remaining

**Bundle A — Capture correctness & multi-display geometry** (needs
hardware; same class of gap, worth one hardware session covering all of
these together with `TESTASSIST_DEBUG=1`):
- **TA-246** (P1 — already root-caused precisely: `devicePixelRatio()`
  misread as 1.0; highest-value fix in this bundle since the mechanism is
  already known, not just suspected)
- **TA-239** (instrumentation in place, needs one real cross-screen drag)
- **TA-242** (launcher visible in its own captures — a real behavioral
  gap, not just measurement)
- **TA-225** (blank capture on laptop/secondary-above — still only
  "instrumented, not fixed" per `docs/BUILD_LOG.md`; worth checking in
  the same session for any connection to TA-246's DPR bug before assuming
  it's independent — not yet confirmed either way)
- **TA-209** (diagonal/L-shaped multi-screen gap — correctly documented as
  a known limitation, not silently broken; lowest urgency here, no
  hardware to test 3-screen L layouts anyway)
- **TA-229** (3+ piece rounding — `xfail(strict=True)`, explicitly not
  blocking, no 3-screen hardware available)

**Bundle B — TA-217, standalone** (P1, the one still-reopened item from
1.5.0): wire `_dismiss_active_modal_dialog()` into both Quick Capture
button handlers, not just the hotkey path. Kept separate from Bundle A —
it's launcher-dialog interaction, not capture geometry.

**Bundle C — Recording UX polish** (all filed tonight, none blocking):
TA-243 (undocked double-click-to-stop, stray snapshot), TA-244 (recording
badge too subtle), TA-245 (dropped frames, no warning). TA-224 (region-
select recording) sits here too but has an explicit prior decision to
stay deferred — no action needed, just grouped for visibility.

**Bundle D — Launcher discoverability & labeling** (small, low-risk,
mostly text/behavior-labeling, good candidate for a quick single-PR
bundle): TA-247 (tray-hide has no confirmation), TA-248 (Open/Close
Editor label doesn't cover what the control now does).

**Bundle E — New feature: launcher accent picker.** TA-249, filed
tonight per this session's decision (picker, amber default). Standalone —
genuinely new work, not a bug fix, don't mix it into a bug-fix bundle.

**Bundle F — Testing/infra hygiene:**
- TA-228 check 3 — re-run 2026-09-16, still open, blocked on a new
  mechanism. `test_smoke.py`'s selectors are stale against the
  `ui-polish` launcher rebuild ("Quick Capture" is now "Capture
  Region"; "Editor" now matches two controls at once) - checks 2 and 3
  fail on that, not on input delivery, so TA-241's fix is still
  unconfirmed by this lane, not disproven. See TA-228's own entry above
  for the full account. Updating `test_smoke.py`'s selectors to match
  the current UI is the next step, not yet done.
- TA-230 (C) — closed 2026-09-16. See TA-230's own entry above for the
  full account.

**Bundle G — Documentation & bookkeeping catch-up** (no code risk, but
real accuracy debt):
- `MULTI_DISPLAY_MANUAL_PASS.md` still shows 27 cases as `⬜`, including
  several (DSP-03, DSP-07, DSP-08, LCH-13, UPD-12) whose actual outcomes
  are already documented, case-by-case, elsewhere in this file and in
  `docs/BUILD_LOG.md`/`docs/SESSION_HANDOVER_*.md`. This is TA-204's own
  stated acceptance criterion ("no case left ⬜") not actually met by the
  tracking file itself, even though the underlying testing happened — a
  backfill pass transcribing the already-known outcomes into that file's
  checkboxes, not new testing.
- TA-206 (judge the editor's feel) — no written verdict found anywhere.
  Either do the pass or record an explicit "no change needed" — currently
  neither has happened.
- TA-208 (close out issue #1 on GitHub) — can't be confirmed from the
  repository alone; needs a manual check that the issue comment was
  actually posted.
- TA-203/TA-213 (help.html accuracy) — `ui-polish` did rework `help.html`
  (light/dark following, redrawn diagrams), but its shortcut table and
  screenshots haven't been re-checked against the post-merge UI (mode
  removal, the three separate capture buttons) — worth a fresh pass now
  that 1.5.0 is the shipped baseline, not assumed done because commits
  with the right names exist.

### Deferred, no action needed right now

TA-210 (Windows file association, P3, no registry code exists — correctly
untouched), TA-212 (PrintScreen opt-in, P2, `VK_SNAPSHOT` not referenced
anywhere — correctly untouched, no urgency signal).
