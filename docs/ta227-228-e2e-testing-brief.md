# Brief: TA-227 (in-process retrofit) and TA-228 (black-box pywinauto lane)

## Why

From the layered-testing discussion after TA-226: two more gaps, one small
and confirmed by direct code read, one a genuine new capability. Both are
now locked tickets in `TESTASSIST_BACKLOG.md`. Handed over together since
they were scoped together, but they're independent — no dependency between
them, do them in either order or in parallel.

**Read each ticket in `TESTASSIST_BACKLOG.md` in full before starting it.**

## Tickets in scope

| ID | Priority | Class | File(s) | One-liner |
|---|---|---|---|---|
| TA-227 | P2 | test retrofit | `python/tests/test_regressions.py` | TA-217's two dispatch tests stub `_start_capture` itself, so neither can detect a real capture-overlay regression |
| TA-228 | P2 | new test infra | new `tests_e2e/` + `pywinauto` | Nothing drives the actual packaged `.exe` from outside — the one thing that could turn TA-220's and TA-217's instrumented-not-fixed gaps into real fixes without another manual pass |

## TA-227: what to check before writing new assertions

Confirmed directly in `python/tests/test_regressions.py`: both
`test_TA217_global_hotkey_closes_an_open_about_dialog_before_capturing`
(~line 570) and
`test_TA217_quick_capture_button_closes_an_open_about_dialog_before_capturing`
(~line 639) do this:

```python
calls: list[str] = []
launcher._start_capture = lambda: calls.append("start_capture")
...
assert calls == ["start_capture"]
```

That's a function-was-called assertion standing in for "a capture actually
happened." Retrofit both to let the real `_start_capture()` run and assert
the real end state instead — `launcher._overlay` visible and interactive.
The ticket has the full scope, including the smaller button-vs-`.click()`
gap and the repo-wide grep for the same shape elsewhere — do that grep, it's
cheap and this is exactly the kind of thing that hides in more than one
place once you know what to look for.

## TA-228: the one open call to make before writing code

The ticket recommends starting this lane as a local/manual smoke pass
rather than wiring it into CI immediately — building the exe just to run
three checks is more CI time than three checks are worth today, and this is
new, unproven infrastructure. That's a recommendation, not something to
treat as already decided. If a different call is made, write down why in
the ticket before building around it, the same way TA-226's assertion
mechanism and TA-224's deferral were both decided explicitly rather than
defaulted into.

Keep the three checks exactly as scoped — this is meant to be a small,
sturdy first slice that proves the approach works, not a first attempt at
full coverage. TA-220's real-OS-minimize-state check is the one worth
getting right most carefully, since it's the first time anything in this
project will observe a real Windows window state instead of Qt's internal
flags for it.

## Sequencing

1. **TA-227 first** — smaller, self-contained, touches only test files, no
   new dependency.
2. **TA-228** — needs the CI-vs-manual decision made and recorded before
   the three checks are built, so the "how do I run this" documentation
   doesn't have to be rewritten after the fact.

## Explicitly out of scope for this brief

Any attempt to use TA-228's new lane to actually resolve TA-220's or
TA-217's still-open investigate-first gaps in this same pass — get the lane
working and passing against current (already-fixed) behavior first. Closing
those two gaps for real is its own follow-up once the lane exists and has
been run against real hardware.

## Build + verify

TA-227 is test-only — same shape as TA-226's report: no build/install step,
report in `docs/BUILD_LOG.md`, confirm the retrofitted tests fail when the
regression they're meant to catch is reintroduced (temporarily revert the
relevant `_dismiss_active_modal_dialog()`/`_start_capture()` call, confirm
red, restore, confirm green) before calling it done.

TA-228 needs a build to test against, but building specifically *for* this
brief isn't required — run the three checks against the current
`python/dist/TestAssist/TestAssist.exe` (rc5) if it's still current, or note
plainly if a rebuild was needed and why.

**Report back in `docs/BUILD_LOG.md`, not chat** — one dated entry (or two,
if that reads more naturally) covering: TA-227's grep findings and whether
anything beyond the two named tests needed retrofitting; TA-228's
CI-vs-manual decision and reasoning, the three checks' real pass/fail
results including the deliberate-break verification, and how to run the new
lane. Commit `TESTASSIST_BACKLOG.md`'s status updates for both tickets in
the same commit as the corresponding code/test changes.
