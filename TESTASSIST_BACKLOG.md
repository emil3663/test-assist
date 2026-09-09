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
  the rectangle independent of window geometry. That doesn't rule out the
  live symptom being reported here, though — a plausible mechanism **not
  yet confirmed by measurement**: Windows' per-monitor DPI awareness can
  report `globalPosition()` with a rounding discontinuity right at a
  monitor boundary on a mixed-DPI setup (125% laptop next to 100%
  external), which would make a rectangle that's being actively dragged
  appear to jump or resize exactly when the cursor crosses from one
  screen's scale to the other's — matching "changes when you get close to
  the right of the screen" precisely. This needs on-hardware coordinate
  logging during a real boundary-crossing drag to confirm or rule out,
  not another round of reading the code.
- **Scope:**
  - Log the raw values `mouseMoveEvent` receives from
    `event.globalPosition()` on the real dual-monitor hardware while
    dragging across the laptop/external boundary, and compare against
    `QScreen.geometry()` for both screens at that moment — this is the
    measurement the hypothesis above needs before any fix is attempted.
  - If confirmed, either work in a single physical-pixel space that
    doesn't inherit Qt's per-screen logical-pixel rounding, or clamp/adjust
    the tracked origin at each `mouseMoveEvent` rather than trusting
    `globalPosition()` to stay linear across the boundary.
  - Check whether DSP-01 ("unable to span... to the right") is the same
    mechanism under a different screen arrangement, or a separate issue.
- **Deliverables:** a confirmed measurement of what actually happens to
  tracked coordinates at the boundary crossing; a fix or a documented
  reason none is needed; a regression test if the mechanism can be
  reproduced synthetically (a fake mixed-DPI two-screen layout, if Qt's
  own DPI reporting can be faked in a test the way `screen_geometry.py`'s
  existing synthetic-layout tests already do).
- **Acceptance criteria:** dragging a selection across the laptop/external
  boundary in the reporter's exact layout produces a rectangle that tracks
  the cursor smoothly, with no visible jump or resize at the crossing.
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
