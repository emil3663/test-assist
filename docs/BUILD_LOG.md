# Build log

Dated entries recording exactly what was built, its real hash, and where it
was installed — so "which binary is this" never again has to be inferred
from a version string that hasn't changed since 1.3.0 (see
`docs/SESSION_HANDOVER_2026-09-09.md`'s "Build identity" section for why
that string alone cannot tell you).

---

## rc3 — 2026-09-09

Built per `docs/rc3-build-and-install-brief.md`, executed in full.

**Source:** `origin/main` at `3fbe4c287cc7838b0cf4a69c7f4cd2cfaed84fb6` (`3fbe4c2`)
— pushed this session (`aa93bb3..3fbe4c2`). `git log -1` on the pushed ref
matches `3fbe4c2` exactly. CI (`Python Tests`, `.github/workflows/python-tests.yml`,
`windows-latest`) confirmed **green** on this exact commit before building —
[run 34305421541](https://github.com/emil3663/test-assist/actions/runs/34305421541),
conclusion `success`, `headSha` `3fbe4c287cc7838b0cf4a69c7f4cd2cfaed84fb6`.

Contains both commits that predate every prior build: `6468591`
(single-instance handoff) and `3fbe4c2` (TA-211 global hotkeys).

**Build command:** `.\build.ps1 -Zip -Shortcut` from `python\`, venv active.
The build's own self-check passed (`Built and verified: Test Assist 1.3.0`,
ffmpeg resolved, SSL backend `schannel`).

**Hash verification — this build genuinely differs from the stale rc2:**

| | rc2 (stale, built before `6468591`/`3fbe4c2`) | rc3 (this entry) |
|---|---|---|
| md5 | `9c2ecf4dd35356af2c8062bff9a9d762` | `481ffa8d588ed8b15ee7455e119ac136` |
| size (bytes) | 2,266,091 | 2,277,554 |
| exe mtime | 2026-09-09 00:58 | 2026-09-09 05:04:46 |

Not taken on faith: `python\build\TestAssist\xref-TestAssist.html` (PyInstaller's
own module cross-reference for *this* build) was grepped directly and lists
`global_hotkeys` / `global_hotkeys.py` — proof the TA-211 module was actually
analyzed into this exe, not just that the hash happened to differ.

**Artifacts:**
- Built folder: `python\dist\TestAssist\` (exe md5 `481ffa8d588ed8b15ee7455e119ac136`, 2,277,554 bytes)
- Zip: `python\dist\TestAssist-1.4.0-rc3-win64.zip` (renamed from the `TestAssist-1.3.0-win64.zip` `build.ps1` produced — `__version__` is still `1.3.0`, deliberately, until the manual pass is green)
- Desktop shortcut: `C:\Users\MSI workstation\Desktop\Test Assist.lnk` (from `-Shortcut`)

**Installed at:** `C:\TestAssist\TestAssist-1.4.0-rc3(09092026)\TestAssist.exe`
— a new dated subfolder, matching the naming convention already used by the
other builds already sitting in `C:\TestAssist\` (`TestAssist-1.4.0-rc(08092026)`,
`TestAssist-1.3.0(09092026)`, etc.). Nothing existing was renamed or moved;
`C:\TestAssist` is a container of dated builds plus manual-pass reference
files, not itself a flat install, so the brief's literal
`Rename-Item "C:\TestAssist" ...` step did not apply as written — confirmed
with the user before installing. Installed copy's md5 checked directly
against the build output: **identical** (`481ffa8d588ed8b15ee7455e119ac136`).

No `TestAssist` process was running at install time (checked via `tasklist`
before copying), so there was nothing to close per S-1.

**Unblocks** (per the brief): DSP-18, PKG-03, PKG-05, UPD-12, REC-console,
DSP-15, DSP-16, LCH-13 — none of these run results are recorded here; running
them is a manual step for whoever performs the pass, against
`C:\TestAssist\TestAssist-1.4.0-rc3(09092026)\TestAssist.exe` specifically
(not rc1, not rc2), same as `MULTI_DISPLAY_MANUAL_PASS.md` already records
INS-02's outcome.
