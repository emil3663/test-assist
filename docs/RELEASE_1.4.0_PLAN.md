# Release plan — v1.4.0

**Date:** 2026-09-11
**Goal:** ship tonight, without a second monitor, without claiming anything the
hardware has not shown.

---

## 1. Scope

### In

| | Why |
|---|---|
| `main` as it stands | TA-201–TA-222, the multi-display work, the editor rebuild |
| **PR #12** `gitignore-fix` | one line; `.claude/` was never being ignored in a public repo |
| **PR #8** `hidpi-capture` **+ the full-screen fix below** | both capture paths keep the pixels they grabbed |

### Out, deliberately

| | Why deferred |
|---|---|
| **PR #19** `ui-polish` | The launcher rebuild has been rendered but never *used*. A 2.68× taller always-on-top panel behaves differently in anger than in a screenshot. Goes to 1.5.0 with its own manual pass. Also carries the `__version__` bump — see §2. |
| **PR #9** `macos-support` | Shipping "macOS support" without a Mac to test the packaged build promises what cannot yet be stood behind. |
| **PR #10** `issue-workflow` | Process documentation; no reason to couple it to a release. |

### Blocking, and it is not a two-monitor problem

The full-screen capture defect (new issue; `docs/VERIFICATION_2026-09-11.md` §4)
must land in this release. It reproduces on **one laptop at 125%** — the
ordinary Windows configuration — and it ships in rc5 today. Releasing 1.4.0
with capture correctness as its headline while the most-used capture path
writes black-padded, logical-resolution evidence is not defensible.

The fix is one line and verifies on a single screen in about two minutes.

---

## 2. Sequence

### 2.1 Complete PR #8 before merging it

`_grab_full_capture()` in `python/launcher.py`:

```python
def _grab_full_capture(self) -> None:
    pixmap = self._current_screen().grabWindow(0)
    pixmap.setDevicePixelRatio(1.0)          # matches capture.py's normalisation
    self._on_capture_ready(pixmap)
```

Commit it onto `hidpi-capture` so the PR is complete rather than patched after
merge. Add a test alongside `test_HIDPI_02`'s pattern: assert the emitted
pixmap reports `devicePixelRatio() == 1.0` and matches the screen's device
size.

### 2.2 Verify on the 125% laptop — single screen, no second monitor

1. Full-screen capture → the PNG fills 1920×1080 with **no black padding**.
2. Region capture of small text → compare against the full-screen reference;
   text should be equally sharp, not softer.
3. Full-screen capture on the **100%** external → byte-identical to today
   (regression guard: the ordinary case must not move).

If (1) still shows black padding, stop — the diagnosis was wrong and the
release waits.

### 2.3 Merge

```powershell
cd "C:\Users\MSI workstation\source\repos\test-assist"
git checkout main
git pull

gh pr merge 12 --merge --delete-branch=false
gh pr merge 8  --merge --delete-branch=false

git pull
```

### 2.4 Version, changelog, suite

`main` is still at `__version__ = "1.3.0"` — the 1.4.0 bump lives on
`ui-polish`, which is being deferred, so it has to be made here.

```powershell
# python/main.py: __version__ = "1.4.0"
cd python
python generate_version_info.py      # propagates to version_info.txt and help.html
pytest -q                            # expect green; note the count in the release entry
cd ..
```

In `CHANGELOG.md`, convert `## [Unreleased]` to `## [1.4.0] — 2026-09-11` and
add the two capture entries from §3 below. A fresh empty `## [Unreleased]`
goes above it.

```powershell
git add python/main.py python/version_info.txt python/help.html CHANGELOG.md
git commit -m "build: release 1.4.0"
git push
```

### 2.5 Tag

```powershell
git tag v1.4.0
git push origin v1.4.0
```

Then confirm on the release page: **Assets 3** — the zip attached, not just the
two auto-generated source archives — and the workflow's version-equals-tag
assertion green.

---

## 3. Changelog entries to add

```markdown
### Fixed

- **A HiDPI capture discarded three quarters of the pixels it grabbed.** A
  region selection on a display above 100% scaling — every Retina Mac, and
  every Windows machine at 125% or 150% — was composited into a pixmap sized
  in logical pixels, resampling the device pixels `grabWindow()` returned down
  to roughly the selection's on-screen size. A 400×300 selection on a 2.0
  screen grabbed 800×600 real pixels and exported 400×300. For a tool whose
  output is evidence that is a correctness problem rather than a cosmetic one:
  1px borders and antialiased small text are exactly what a tester circles,
  and exactly what does not survive the downsample. Captures are now sized in
  device pixels at the highest ratio among the contributing screens, so a
  selection spanning a sharp screen and a coarse one keeps the sharp half at
  full detail. Ordinary 1.0-ratio hardware is unaffected, with a regression
  test pinning that.
- **A full-screen capture wrote a device-sized file containing logical-sized
  content.** On a 125% display the result was a 1920×1080 PNG holding only
  1536×864 of picture in the top-left with black filling the rest, because the
  full-screen path emitted a pixmap still tagged with the screen's device
  pixel ratio, and the canvas measures its own geometry in device pixels. The
  full-screen path now applies the same ratio normalisation the region path
  does. Single-monitor reproducible; present since before 1.3.0.

### Changed

- `.gitignore`'s fifth line merged two patterns onto one line, so neither
  `.venv/` nor `.claude/` was actually ignored.
```

---

## 4. Release notes (GitHub release description)

> Capture correctness, and the multi-display work from issue #1.
>
> **Captures now keep every pixel they grabbed.** On any display above 100%
> scaling — 125% and 150% are the ordinary Windows laptop — both region and
> full-screen captures were losing detail before the editor ever saw them.
> Region captures were resampled down to their on-screen size; full-screen
> captures were written into a correctly-sized file with the picture painted
> at the smaller logical size and black filling the remainder. Both paths are
> fixed. If you work on a scaled display, this is the release to take.
>
> **Multi-display capture (issue #1).** Region capture, full-screen capture,
> recording and the launcher's own positioning all follow whichever screen you
> are actually on, and a selection spanning two screens is composited rather
> than clamped.
>
> **Verified how:** the full suite runs on every push, and the capture fixes
> carry tests that exercise HiDPI ratios explicitly on ordinary CI hardware.
> The multi-display geometry is covered by tests against synthetic layouts and
> by a partial pass on real dual-monitor hardware — **not a complete one.**
> Two multi-display defects found during that pass remain open: a selection
> rectangle that resizes when dragged across a mixed-DPI screen boundary
> (#TA-223) and a capture that came back empty in one specific
> secondary-above arrangement (#TA-225). Neither is fixed here.
>
> Full detail in `CHANGELOG.md`.

---

## 5. Comment for issue #1

> Released in [v1.4.0](https://github.com/emil3663/test-assist/releases/tag/v1.4.0).
>
> What changed for the case you reported: region capture, full-screen capture,
> recording and the launcher's own positioning now all resolve against the
> screen actually in use rather than the primary one, and a selection spanning
> two screens is composited into one image instead of being clamped to one of
> them. The capture overlay also no longer uses `showFullScreen()`, which was
> the root cause — it made the overlay fullscreen on *a* screen rather than
> spanning the virtual desktop, so the secondary display could not even be
> pressed on.
>
> A defect you did not hit was fixed alongside it: recordings had the same
> single-screen assumption.
>
> **What I can and cannot claim.** The geometry is covered by tests against
> synthetic multi-screen layouts, and I ran a partial pass on real
> dual-monitor hardware. It is not a complete hardware pass, and two defects
> found during it are still open — a selection rectangle that resizes when
> dragged across a boundary between screens at different scaling, and a
> capture that came back empty in one particular secondary-above arrangement.
> I would rather say that plainly than describe this as fully verified.
>
> So: please do try it on your setup and tell me what you see. If your
> arrangement still misbehaves, the About dialog now has a **Copy details for
> a bug report** button — version, OS and the full display layout — which
> saves you describing your monitor configuration by hand.
>
> Leaving this open until you have had a chance to confirm.

---

## 6. What this release does not claim

- That multi-display capture is verified on hardware. It is verified by test,
  and partially on hardware. TA-204's 18-case pass is **not** done.
- That TA-223 or TA-225 are fixed. Both remain open and are named in the
  release notes and the issue comment.
- That the launcher rebuild is in it. It is not; it is deferred to 1.5.0.
- That macOS is supported. Deferred with #9.
