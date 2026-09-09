# Verification report — pre-1.4.0 check

**Date:** 2026-09-09
**Scope:** independent verification of `docs/SESSION_HANDOVER_2026-09-09.md`, the argv/single-instance fix, a claim audit of docs at HEAD, and what remains before tagging 1.4.0.
**Method:** fresh clone from GitHub run independently, real pytest execution (not the commit message's word for it), md5 of the actual build artifact, grep/count against actual source — not a re-read of the docs.

---

## 1. The handover document is stale — on arrival

The handover claims `HEAD: 734dfe7, pushed. origin/main level with local` and describes the argv/single-instance work as **"in progress."** Neither is true of the repository that contains the handover file itself.

**What actually happened, by commit timestamp:**

| Time | Commit | What |
|---|---|---|
| 02:57 | `734dfe7` | (the commit the handover claims is HEAD) |
| 03:19 | `6468591` | **Hand a second launch off to the running instance** — this is the "in progress" item, already done |
| 03:31 | `aa93bb3` | "Documentation only" — writes `SESSION_HANDOVER_2026-09-09.md` itself, plus commits the two files the handover calls "uncommitted" |
| 03:49 | `3fbe4c2` | **TA-211: real global hotkeys (Alt+P/Alt+Shift+P/Alt+V)** — not on GitHub, not mentioned anywhere in the handover |

So the commit that *writes* the handover (`aa93bb3`, 03:31) lands twelve minutes after the single-instance fix it still describes as unfinished, and eighteen minutes before another whole feature that it never mentions at all. The handover's own two "uncommitted files" (`MULTI_DISPLAY_MANUAL_PASS.md`'s INS-02 result, `docs/PHASE_4_DECISION_RECORD.md`) were committed by the very commit that saved the handover — so that claim was also already false when written.

**Independently confirmed by cloning fresh from GitHub** (`git clone https://github.com/emil3663/test-assist`, not the working copy):
- `origin/main` is at `aa93bb3`, two commits ahead of the `734dfe7` the handover names.
- The local working tree is a further commit ahead, at `3fbe4c2` — **one commit exists only locally, never pushed.**
- Running the suite from the fresh clone (`QT_QPA_PLATFORM=offscreen pytest -q`): **283 passed, 0 skipped.** This matches `6468591`'s own commit message exactly, and is 5 more than the handover's stated "278 passed" — because the handover's number describes the state *before* `6468591`, despite being written after it.

**Net effect:** don't trust this handover's "in progress" / "outstanding" framing without re-checking git log first — as of right now the argv/single-instance fix is done and pushed, and there's a whole additional feature (global hotkeys) sitting locally, unpushed, undocumented in the handover, with its own new outstanding manual case.

---

## 2. The argv hand-off / single-instance work — verified, not just read

Checked against the three scenarios you asked about, by reading `python/main.py`, `python/single_instance.py`, `python/editor.py` at `6468591`, and then **actually running** the tests that exercise them (not trusting the commit message):

| Scenario | Where | Verified |
|---|---|---|
| **File path argument** | `main.py::_extract_open_path()` reads `sys.argv`, skips `--version`/`--selftest`; first instance calls `editor.load_image_path()` at startup | `test_INS_08` — loads a real PNG from disk, asserts the canvas has the image and the window isn't hidden |
| **Bad path** | `editor.py::load_image_path()` checks `Path(path).is_file()`, then `QPixmap(...).isNull()`, before touching canvas state; shows a `QMessageBox.warning` and returns `False` on either failure | `test_INS_09` (missing file) and `test_INS_09b` (a real file that isn't an image) — both assert a warning was shown and canvas state didn't change |
| **Second launch while running** | `single_instance.py::SingleInstanceManager.acquire()` — tries `_handoff_to_existing()` first (writes `OPEN:<path>` or `SHOW` over a real `QLocalSocket`, waits up to 800ms for an `OK` ack); only falls back to the old `QUIT`-and-replace if the handoff isn't acknowledged | `test_INS_10` — **two real `SingleInstanceManager`s talking over a real local socket**, asserts `quit_requested` is never fired and the second launch hands off cleanly. `test_INS_11` — a stub server that accepts but never replies, proving a genuinely hung instance still falls back to the recoverable QUIT path rather than being mistaken for a successful handoff |

I ran this myself: cloned fresh, `pip install -r python/requirements.txt`, `QT_QPA_PLATFORM=offscreen pytest -q` → **283 passed, 0 skipped**, INS-08 through INS-11 included and green. This is a genuine fix for the exact failure mode you described (second launch silently killing the first with no unsaved-work prompt) — not just a documented intention.

**One catch:** the currently built artifact predates this fix. `python/dist/TestAssist/TestAssist.exe` (the "latest build" the handover points at) has an mtime of **00:58**, which is before `6468591` (03:19) *and* `3fbe4c2` (03:49). **Nothing has been packaged with the single-instance handoff or the hotkey fix in it yet** — a rebuild is required before either can be verified on real hardware, not just in the offscreen test suite.

---

## 3. Build identity — the one number I could check without a real Windows run

md5 of `python/dist/TestAssist/TestAssist.exe` as it sits on disk: **`9c2ecf4dd35356af2c8062bff9a9d762`**, i.e. `9c2ecf4d` — this matches the handover's claim exactly. That part is true. (I couldn't reach `C:\TestAssist\...` — the installed copy — since folder access was scoped to the repo only; if you want that hashed too, I can request that folder specifically.)

What I *can't* verify without the real desktop — window geometry, tray behavior, the actual second-launch handoff on Windows, frame extraction from a recording — needs the computer-control tools on your machine and your permission to drive them. I didn't start that without checking with you first, especially since the one build on disk right now doesn't contain the code being asked about.

---

## 4. Claim audit — README and doc counts vs. code at HEAD

| Claim | Where | Reality |
|---|---|---|
| **"229 pytest tests"**, and "`DESKTOP_STABILITY_MATRIX.md` triages all 151 cases — 145 automated, 6 blocked" | `README.md`, "Testing" section | Actual: **283 passed on origin/main, 287 locally** (unpushed). `DESKTOP_TEST_PLAN.md` v1.21 currently has **188 cases**, 182 automated, 6 blocked. README hasn't been touched in ~6 days (mtime predates this session's work by a wide margin) — **stale, understates by a lot**. |
| **"55 Playwright tests"**, "regression suite... 47 tests" | `README.md`, "Testing" section | Counted directly in `tests/smoke.spec.ts` and `tests/regression.spec.ts`: **8 smoke + 41 regression = 49 total**, not 55/47. **False**, and doesn't match `npm run test:regression`'s own comment either — worth checking whether the count was always wrong or drifted. |
| **"the desktop build is covered by 29 pytest regression tests"** | `STABILITY_MATRIX.md` (browser doc), line 6 | Off by roughly 10x (283–287 actual). This file (v1.1, last updated 2026-08-20) looks like it hasn't been touched since well before the desktop suite grew — low priority since it's the browser-build doc, but still a false claim sitting in a committed file. |
| **"A green run is `287 passed, 0 skipped`, everywhere"** ... "works everywhere: CI, the packaged build, and any clean checkout" | `DESKTOP_STABILITY_MATRIX.md` (as of `3fbe4c2`, TA-211) | Ran it myself on Linux (`QT_QPA_PLATFORM=offscreen pytest -q` from a clean checkout): **5 fail** with `AttributeError: module 'ctypes' has no attribute 'windll'` — the five new TA-211 hotkey tests call `ctypes.windll.user32` directly, which doesn't exist off Windows, and none of them are `skipif`-guarded. CI genuinely does run on `windows-latest` (`.github/workflows/python-tests.yml`), so this is true in the two places that matter for shipping — but "everywhere" and "any clean checkout" are no longer accurate claims once a Windows-only API entered the suite with no skip guard. Recommend either rewording ("passes in CI and on Windows") or adding `@pytest.mark.skipif(sys.platform != "win32", ...)` so a non-Windows contributor gets an honest skip instead of a crash. |
| **help.html's Alt+P / Alt+Shift+P / Alt+V shortcut table and card text** | `python/help.html` | This was a live false claim in the actual released code: on `origin/main` (before `3fbe4c2`), these three shortcuts are documented but bound to nothing (this is exactly what TA-211's own backlog entry says: *"this violates the project's standing rule that every claim... is true of the code as committed — here the false claim is on the app's own face"*). It's fixed in the local, unpushed commit, but help.html's text wasn't updated to say they're now **system-wide** hotkeys (not window-scoped) — TA-213 is already backlogged for this. |
| Single-instance description: *"a second launch focuses the running window"* | `README.md`, "Only in the desktop build" | Not false, but **understated** post-`6468591`: a second launch can also hand off a file to open (`OPEN:<path>`), not just focus the window. Worth a one-line update alongside the other README fixes. |
| Published page (`emil3663.github.io/test-assist`) — first-ten-seconds check | live URL | **Unverifiable this pass** — WebFetch hit a session limit while checking it. Nothing in this audit suggests it changed; still worth a quick manual look before tagging, since it's the thing a reviewer sees first. |

I didn't check every line of every doc (`CHANGELOG.md`, `DESKTOP_TEST_PLAN.md`, `DESKTOP_STABILITY_MATRIX.md` beyond what's above) — those three are large and, from the diffs I read while verifying the argv work, are being actively and carefully kept in sync commit-by-commit. The stale spots above are consistently in the docs that *aren't* touched every commit — `README.md` and the browser `STABILITY_MATRIX.md` — which is the pattern you'd expect: the file someone edits every commit stays honest, the one nobody has reason to open silently rots.

---

## 5. What's genuinely left before 1.4.0

The manual pass grew from 26 to **27 outstanding checks** — `3fbe4c2` (unpushed) added `LCH-13`.

**Needs the second monitor (18 checks)** — real dual-display hardware, can't be done from here or on a laptop alone:
- Block A (current layout, negative coords + mixed DPI): DSP-03, 05, 05b, 07, 08, 09, 10, 11, 12, 13, 14, 17 (12)
- Block B (matched DPI): DSP-03b, 06, 08b (3)
- Block C (secondary on the right): DSP-01, 02 (2)
- Block D (secondary above — flagged in the handover as "the configuration that nearly shipped broken"): DSP-04 (1)

**Doesn't need the second monitor — can run on the laptop alone, right now (8 checks):**
DSP-18 (help page header/footer), PKG-03 (taskbar pin icon), PKG-05 (exe file properties), UPD-12 (update check reaches GitHub), REC-console (no console flash on save), DSP-15 and DSP-16 (Block E, single-monitor regression — these actually need the external monitor *disconnected*, not connected), and now **LCH-13** (Alt+P etc. firing with Test Assist unfocused — just needs any other window focused).

**Deferred, not about monitor count:** PKG-04 (first launch on a machine with no Python) needs a genuinely clean Windows machine — the doc already says defer this with the reason rather than guessing.

**Before any of that manual pass means anything for the hotkey/handoff work specifically:** the exe on disk right now was built *before* both `6468591` and `3fbe4c2`. It needs a rebuild first, or the single-screen checks above will be testing 90-minute-old code.

**Non-manual work outstanding:**
- Push `3fbe4c2` to `origin/main` — it's sitting local-only.
- README's test counts (229/55/47) need correcting — real fix is fifteen minutes of counting and replacing four numbers, not a rewrite.
- `STABILITY_MATRIX.md`'s "29 pytest" reference, same kind of fix.
- Either reword `DESKTOP_STABILITY_MATRIX.md`'s "passes everywhere" claim or add `skipif` guards to the five TA-211 tests.
- TA-213 (help.html rework) is backlogged and not started — the shortcut table is functionally true now but doesn't say "system-wide."
- The published page's first-ten-seconds framing — unverified this pass, worth a quick manual look.

---

## What I didn't do

I didn't touch the actual Windows desktop — no window-geometry measurement, no live second-launch test, no frame extraction from a recording, no binary hash of the *installed* copy at `C:\TestAssist\...`. All of that needs the computer-control tools and a rebuilt exe, and I didn't want to start driving your screen without checking first, especially since the artifact currently on disk doesn't contain the code being asked about.
