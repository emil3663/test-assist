# Brief: push TA-211, build rc3, install it, report exact locations

## Why

Two commits landed after `docs/SESSION_HANDOVER_2026-09-09.md` was written and
are not reflected in it or in any build:

| Commit | What | Pushed? | In a build? |
|---|---|---|---|
| `6468591` | Single-instance handoff (argv/second-launch fix) | ✅ on `origin/main` | ❌ |
| `3fbe4c2` | TA-211 — real global hotkeys (Alt+P / Alt+Shift+P / Alt+V) | ❌ local only | ❌ |

The exe currently on disk — `python\dist\TestAssist\TestAssist.exe`, md5
`9c2ecf4dd35356af2c8062bff9a9d762` — has an mtime of **00:58**, before both
commits (03:19 and 03:49). Nothing built contains either fix. Eight items in
`MULTI_DISPLAY_MANUAL_PASS.md` don't need the second monitor (DSP-18, PKG-03,
PKG-05, UPD-12, REC-console, DSP-15, DSP-16, LCH-13), but running them against
this exe would silently test 90-minutes-stale code — exactly the class of
mistake `docs/SESSION_HANDOVER_2026-09-09.md`'s own "Build identity" section
warns about (the wasted INS-02 cycle against a three-week-old zip).

## Task

**1. Push.**

```powershell
git push origin main
```

Confirm the `Python Tests` workflow (`.github/workflows/python-tests.yml`,
`windows-latest`) goes green on `3fbe4c2` before moving on. If it doesn't,
stop and report why rather than building on top of a red push.

**2. Build.**

```powershell
git status               # must be clean, HEAD at 3fbe4c2, before building
cd python
..\.venv\Scripts\Activate.ps1
.\build.ps1 -Zip -Shortcut
```

`build.ps1` already runs the built exe once to verify it starts before it zips
— don't skip past that check if it fails.

**3. Verify the build actually changed** (don't take a successful `build.ps1`
run as proof by itself — this is the exact failure mode the build-identity
section exists to catch):

```powershell
Get-FileHash python\dist\TestAssist\TestAssist.exe -Algorithm MD5
```

The result must **differ** from `9c2ecf4dd35356af2c8062bff9a9d762` (the stale
rc2 hash) and the exe's size must differ from both known builds (old 2 Sep:
1,804,298 bytes; current rc2: 2,266,596+ bytes — record the new one).

**4. Name and keep the zip as an rc**, per the project's own convention (don't
let a zip claim a version it isn't — `__version__` is still `1.3.0` until the
manual pass is green):

```powershell
Rename-Item python\dist\TestAssist-1.3.0-win64.zip TestAssist-1.4.0-rc3-win64.zip
```

(adjust the source name to whatever `build.ps1` actually produced — check
`python\dist\` rather than assuming).

**5. Install it**, following `MULTI_DISPLAY_MANUAL_PASS.md`'s own setup steps
S-1 through S-4:

```powershell
# S-1: close Test Assist completely first — check the tray, not just the window.
# S-2: keep rc1 for comparison
Rename-Item "C:\TestAssist" "C:\TestAssist-1.4.0-rc1"
# S-4: install rc3
New-Item -ItemType Directory C:\TestAssist
Copy-Item python\dist\TestAssist\* C:\TestAssist\ -Recurse
```

**6. Report back in the repo, not chat.** Append a short, dated note to
`docs/SESSION_HANDOVER_2026-09-09.md`'s "Build identity" table (or a new
`docs/BUILD_LOG.md` entry if you'd rather not hand-edit the handover) stating:

- Exact md5 and byte size of the new `TestAssist.exe`
- Exact path of the installed copy (`C:\TestAssist\TestAssist.exe`)
- Exact path of the zip (`python\dist\TestAssist-1.4.0-rc3-win64.zip`)
- Confirmation that `git log -1` on the pushed commit matches `3fbe4c2`

## What this unblocks

Once installed at `C:\TestAssist\`, these `MULTI_DISPLAY_MANUAL_PASS.md`
cases don't need the second monitor and can be run as-is (the machine is
already single-screen right now, which is exactly Block E's precondition —
no unplugging needed):

| ID | Case |
|---|---|
| DSP-18 | Help page header/footer shows the right version |
| PKG-03 | Pin to taskbar — icon matches the tray icon |
| PKG-05 | Right-click exe → Properties → Details — product name/version populated |
| UPD-12 | Check for Updates reaches GitHub and reports correctly |
| REC-console | Record and save — no console window flashes |
| DSP-15 | Launcher was on the (now absent) second screen — still reachable, not off-screen |
| DSP-16 | Capture, full capture, record, dock, undock all behave with one screen |
| LCH-13 | Focus a browser (or anything else), press Alt+P / Alt+Shift+P / Alt+V — each fires with Test Assist unfocused |

Everything else in that file (Blocks A–D, and PKG-04) genuinely needs the
second monitor or a clean machine and stays blocked until then.

## Verification

Don't mark any of the eight cases above ✅ on the strength of "it built" —
run each one against the installed `C:\TestAssist\TestAssist.exe` and record
the real result in `MULTI_DISPLAY_MANUAL_PASS.md`, the same way INS-02 was
recorded (date, build md5, outcome). LCH-13 in particular is new — it has no
prior passing run to compare against.
