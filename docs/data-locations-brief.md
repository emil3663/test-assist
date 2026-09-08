# Move the app's data out of `~/.test-assist`

## Why

`~/.test-assist/recordings` is undiscoverable on Windows. A dot-prefixed folder
is a Unix convention Windows users do not look in, and `help.html` compounds it
by claiming recordings are saved "to your home folder" — they are not, they are
in a subfolder of it. A tester who records a repro and then cannot find the file
has, from their point of view, lost their evidence.

**The install folder is not the answer**, tempting as it looks:

- The documented update procedure is "close the app, download the zip, replace
  the contents of the folder you run it from." Recordings in that folder are
  **deleted by every update**. For a tool whose job is preserving defect
  evidence that is the worst available failure, and we created it ourselves when
  we wrote those instructions.
- `C:\TestAssist` happens to be writable. Someone unzipping to `Program Files`
  gets an app that cannot write at all.
- Two users on one machine would share a folder and see each other's screen
  recordings.
- A folder outside the user profile falls outside most corporate backup policy.

## Where things should go

Split by what the files *are*, which is the part that matters:

| Data | Destination | Via | Why |
|---|---|---|---|
| Recordings, saved exports | `Documents\Test Assist\` | `QStandardPaths.DocumentsLocation` | User evidence. Discoverable, backed up, per-user, survives updates. |
| Capture history | `AppData\Local\…\history` | `QStandardPaths.AppLocalDataLocation` | App-managed cache, **auto-pruned on startup**. |

That second row is not a detail. `_load_history` deletes unreadable files every
launch. **An auto-deleting folder must never live in the user's Documents** —
that is the difference between the history-pruning bug being annoying and being
alarming. Keep the pruning where users do not keep things they would miss.

## Current state

Two places build a path, both by hand:

- `capture.py:22` — `_recordings_dir()`: `Path.home() / ".test-assist" / "recordings"`
- `editor.py:611` — `_load_history()`: `Path.home() / ".test-assist" / "history"`

## What to change

**1. One module for path resolution.** A new `paths.py` with
`recordings_dir()`, `history_dir()`, and `legacy_dir()`. Every caller goes
through it. Do not scatter `QStandardPaths` calls the way `Path.home()` is
scattered now — the single seam is what makes the test isolation tractable.

**2. Mind the app/organization name.** `main.py` sets both
`setApplicationName("Test Assist")` and `setOrganizationName("TestAssist")`, and
`AppLocalDataLocation` incorporates both — giving
`AppData\Local\TestAssist\Test Assist\history`, which is silly. Either drop the
organization name (nothing else uses it — `single_instance.py` uses its own
hardcoded `"test-assist-single-instance"`, so dropping it is safe) or build the
path explicitly rather than relying on the derived one. Your call; say which you
chose.

**3. `QStandardPaths` needs a `QCoreApplication` to exist** for the app-name
paths. Resolve lazily inside the functions, never at import time, or a path
resolved during module import will be wrong.

**4. Migrate on first run — and this is not for me.** My own history is
disposable, but v1.0.0, v1.1.0 and v1.3.0 are public downloads and at least one
person outside this repo has used them. On startup, if `~/.test-assist` exists
and the new locations do not, move the contents across. Best-effort: wrapped in
try/except, never fatal, never blocking startup. Leave the empty old folder
rather than risking a delete.

**5. Fix the discoverability properly.** After a recording saves, make the
status message open the containing folder — `QDesktopServices.openUrl` on the
parent directory. Whatever the path is, "where did it go" then has a one-click
answer. This is the actual fix for the original complaint; the path move just
stops the answer being embarrassing.

**6. The test isolation moves with it.** `conftest.py` currently patches
`Path.home` in three places. That seam disappears. Patch the new `paths` module's
functions instead, and **assert the redirect took effect** — a path produced by
the app must live under `tmp_path`. Isolation you have asserted is not isolation
you have verified, and a suite that silently starts writing to the real
`Documents` folder is worse than the bug being fixed here.

## Tests

- `recordings_dir()` and `history_dir()` return distinct paths, and neither is
  under the other.
- The history directory is **not** under `DocumentsLocation` — pin the reasoning,
  not just the current value.
- Migration: a populated legacy folder is moved; an already-migrated install is
  left alone; a missing legacy folder is a no-op; an unreadable legacy folder
  does not prevent startup.
- Isolation: with the fixture active, a path returned by `paths.py` is under the
  temp directory. Run the suite with something recognisable in the real
  locations and confirm it is untouched afterwards.

## Docs

- `help.html` — name the real recording location, and mention the open-folder
  behaviour. The current "your home folder" line is false today.
- `README.md`, `DESKTOP_TEST_PLAN.md`, `DESKTOP_STABILITY_MATRIX.md` wherever
  `~/.test-assist` appears.
- `CHANGELOG.md` — flag the move and the migration, since it changes where
  existing users' files live.

## Acceptance

- Full suite green, no skips, no socket opened, and the isolation assertion in
  place.
- A recording from source lands in `Documents\Test Assist\`, history in
  `AppData\Local\…`, and a populated `~/.test-assist` migrates once and then
  stops being touched.
- Report before committing.
