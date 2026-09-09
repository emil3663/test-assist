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
