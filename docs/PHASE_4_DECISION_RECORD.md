# Phase 4 Decision Record (Locked)

Date: 2026-09-09 (decision 7 amended same day)
Scope: Test Assist as a general-purpose Windows image viewer, with immediate annotation of the image being viewed
Status: Approved and awaiting implementation
Depends on: the argv hand-off change (a second launch hands the file path to the running instance instead of quitting it). That work is briefed separately and lands in 1.4.0. Phase 4 does not start until it is in.

## Decisions

1. Test Assist registers as a candidate image handler and never sets itself as the default.
- Registration writes ProgIDs, `Applications\TestAssist.exe\SupportedTypes` and `RegisteredApplications` under `HKCU`. No `HKLM`, no elevation.
- Windows 10 and 11 forbid an application assigning itself as the default handler. The user makes Test Assist the default in Settings → Default apps, or via "Always use this app" in the Open with dialog.
- Registration happens only from an explicit user action in the app. It never runs silently at first launch.
- Unregistering is available from the same place and removes every key it wrote.

2. The registered formats are exactly those the bundled Qt plugins decode.
- `.png` `.jpg` `.jpeg` `.bmp` `.gif` `.webp` `.tif` `.tiff` `.ico` `.tga`.
- Verified against the plugins present in the build: `qgif`, `qicns`, `qico`, `qjpeg`, `qsvg`, `qtga`, `qtiff`, `qwbmp`, `qwebp`, plus PNG and BMP built into Qt.
- A format the app cannot decode is never registered. Registering a type that then fails to open is worse than not appearing in the list.

3. The canonical install location is `%LOCALAPPDATA%\Programs\Test Assist`.
- Per-user, matching the per-user `HKCU` registration. No elevation.
- Distribution stays a zip. Builds are extracted to that path, replacing the previous contents in place; dated build folders elsewhere are working copies and are never registered.
- Registry entries carry an absolute path to the executable. The app refuses to register while running from any other location, and says which location it expects.
- On launch, the app compares its own path against the registered path and offers to re-register when they disagree, rather than leaving every association silently broken.

4. Opening a file never writes to the capture history.
- The history gallery holds capture evidence. A file opened for viewing is not evidence and does not appear there.
- History pruning never sees, moves or deletes a file opened for viewing.
- This holds regardless of whether the user annotates the opened file.

5. Saving an opened file never overwrites the original.
- Save writes a new file beside the original under a suffixed name, for example `photo.png` → `photo-annotated.png`. A name already taken is suffixed further rather than replaced.
- Save As remains available for writing anywhere the user names, including over the original. Overwriting an original is reachable only through an action the user chose by name.
- The destination path is shown to the user before the write, not only after it.
- No control labelled "Save" writes to a location the user did not name.

6. The editor tracks modified state.
- `annotation_changed` gains a listener that marks the document dirty; every mutation of the annotation set marks it, and a successful save clears it.
- The window title marks an unsaved document.
- This closes a gap open since the undo work, where the editor never knew whether it had unsaved changes.

7. Viewer navigation is folder-based, read once, driven by on-screen buttons, and cannot silently discard work.
- Previous and Next are explicit toolbar buttons. The arrow keys do not navigate.
- The arrow keys already nudge the selected annotation (`canvas.py` `keyPressEvent` → `nudge_selected`). Binding them to folder navigation as well would make Left mean "move this arrow one pixel" or "abandon this image" depending on selection state, which is the worst kind of ambiguity in an evidence tool.
- The file list is read when the image opens. Files added to the folder afterwards do not appear until the folder is opened again.
- Navigation stops at the first and last image; it does not wrap. Both buttons disable at their respective boundaries rather than doing nothing when pressed.
- Navigating away from a dirty document prompts, offering save, discard, or cancel. The same prompt applies to closing the editor and to opening another file.

8. Viewing brings the editor forward and leaves the floating launcher hidden.
- Opening a file activates the editor window. The launcher does not appear.
- The launcher stays reachable from the tray and from the editor's own launcher button.
- The editor window title shows the file name of the image being viewed.

9. The following are out of scope for this phase.
- HEIC and HEIF, RAW camera formats, PDF viewing, SVG editing.
- Explorer thumbnail and preview handlers.
- Slideshow, EXIF display, rotation, cropping to file, printing.
- Multiple images open at once, tabs, or a folder tree.
- An installer, an uninstall entry, and any `Program Files` deployment.

## Acceptance Criteria

1. Registration
- An explicit action in the app registers Test Assist as a candidate handler, and it then appears in the Windows "Open with" list and in Settings → Default apps for each registered format.
- The app never becomes the default without the user choosing it in Windows.
- Unregistering removes every key written, verified by inspecting `HKCU` before and after.
- Running from anywhere other than `%LOCALAPPDATA%\Programs\Test Assist` refuses registration and names the expected location.
- A build extracted over the canonical location keeps its associations working with no user action.
- Moving or renaming the install folder after registration produces an offer to re-register on next launch, not a silent failure.

2. Opening files
- Double-clicking a registered image type with Test Assist as default opens that image in the editor, activated, with the file name in the title bar.
- The floating launcher does not appear when a file is opened.
- A file that does not exist, or that fails to decode, leaves the app running normally and says so. It never starts with an empty editor presenting itself as a successful open.
- Opening a file while Test Assist is already running loads it into the running instance. The running instance is not terminated.

3. History isolation
- Opening and annotating a file from disk adds nothing to the history gallery.
- A full pass of the history pruning leaves files opened for viewing untouched.

4. Saving
- Save on an opened file writes a new suffixed file beside the original and leaves the original byte-identical, verified by hashing it before and after.
- Saving twice does not overwrite the first result; the second write takes a further suffix.
- The destination path is visible to the user before the write completes.
- Save As is the only path that can write over an original, and it requires the user to name that destination.

5. Modified state
- Any annotation mutation marks the document dirty; a successful save clears it.
- The title bar distinguishes a dirty document from a clean one.
- Navigate, close, and open-another each prompt on a dirty document, and cancel genuinely aborts the action.
- Discard on a dirty document loses the annotations and nothing else; the file on disk is untouched.

6. Navigation
- Previous and Next move through the folder's decodable images in name order.
- Pressing an arrow key still nudges a selected annotation and never changes the image.
- Non-image files and images that fail to decode are skipped, not shown as errors.
- Previous is disabled on the first image and Next on the last; neither wraps.
- A folder containing exactly one image leaves both buttons disabled.

## Regression Policy

- Add a `VIEW-` case group to `DESKTOP_TEST_PLAN.md` covering: registration and unregistration, install-location refusal and re-registration, open-by-double-click, open-while-running, bad-path handling, history isolation, save-never-overwrites, dirty-state prompting, and folder navigation including its boundaries.
- Add the format list from decision 2 to `DESKTOP_TEST_PLAN.md` as an explicit per-format open check. A format that is registered but not covered by a test case is a format that will silently regress.
- Decision 5 needs a test that hashes the original before and after a save. An assertion that a new file appeared does not prove the old one survived.
- Decision 6 is the mechanism protecting the user's work in decision 7, so it is tested directly and not only through navigation.
- Record in `DESKTOP_STABILITY_MATRIX.md` which of these can be automated and which need a real Windows shell. Registration, default-handler assignment and double-click-from-Explorer are shell-dependent and are Blocked for the offscreen suite; path validation, format decoding, history isolation, save behaviour, dirty-state tracking and navigation ordering are not, and are covered by tests.
