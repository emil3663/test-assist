# Brief: add the missing skipif guard to the TA-211 hotkey tests

## Why

Flagged twice now and dropped both times without being reported as skipped:
first by Claude Code itself after the rc3 build ("the 5 new TA-211 tests call
`ctypes.windll` directly with no `skipif` guard... let me know if you want
that addressed"), then queued explicitly into `docs/ta214-220-fix-brief.md`
for the rc4 batch. Checked directly in `python/tests/test_regressions.py`
after rc4 landed: still no `skipif`, no `sys.platform` check, anywhere in
`tests/` — the guard was never added. Unlike the batch's two repro-first
items (TA-217's Properties-dialog case, TA-215's PKG-05 case), which were
explicitly reported as "not attempted," this one wasn't mentioned as skipped
at all in `docs/BUILD_LOG.md`'s rc4 entry — it just didn't happen.

This is small and self-contained — it only touches test guards, not app
code — so it doesn't need bundling with anything else.

## What needs the guard

Five tests exercise the real Win32 `RegisterHotKey`/`UnregisterHotKey` API
via `FloatingLauncher(..., register_global_hotkeys=True)` or a direct
`ctypes.windll.user32` call, and crash with
`AttributeError: module 'ctypes' has no attribute 'windll'` on any
non-Windows run:

- `test_TA211_global_hotkeys_register_and_are_advertised` (line ~497)
- `test_TA211_global_hotkey_dispatch_routes_to_the_right_action` (line ~512)
- `test_TA211_an_unrelated_native_message_is_ignored` (line ~543)
- `test_TA211_a_failed_registration_is_surfaced_and_not_advertised` (line ~618)
- `test_TA211_hotkeys_are_released_on_close` (line ~653)

`test_TA211_hotkeys_are_not_touched_without_opting_in` and
`test_TA217_global_hotkey_closes_an_open_about_dialog_before_capturing` use
`register_global_hotkeys=False` (default) and don't touch the real API —
leave them unguarded, they already run fine off Windows.

## Task

Add a `skipif` guard to exactly those five tests (a shared marker or a
`pytestmark`/decorator on that section is fine — whatever fits the file's
existing style) so a non-Windows run skips them cleanly instead of crashing:

```python
@pytest.mark.skipif(sys.platform != "win32", reason="RegisterHotKey is a Win32 API")
```

Don't change what any of the five assert on Windows — this is a guard, not a
rewrite. `import sys` at the top of the file if it isn't already there.

## Verification

- Run the suite normally on Windows first — all five must still run for real
  and pass, exactly as before. The guard should have zero effect here.
- If there's any way to check the skip actually fires off-Windows (a
  non-Windows shell, a container, CI matrix, or just reasoning from the
  `sys.platform` check itself if a real off-Windows run isn't available),
  do that and say plainly which you did — don't just assert it would work.
- Report the before/after skip count from a real Windows run: same pass
  count as before (guards inert here), 0 new skips introduced on this
  platform.

## Report back

One line appended to `docs/BUILD_LOG.md` (new dated entry, or a note on the
rc4 entry if that reads more naturally) confirming: the guard is in place on
all five tests, the full Windows suite still passes at the same count as
rc4's `307 passed, 0 skipped`, and the commit hash. No build/install step is
needed for this one — it's test-only, nothing in `python/dist/` changes.
