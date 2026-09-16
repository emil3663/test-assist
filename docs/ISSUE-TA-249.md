TA-249 — Let the user pick the launcher's accent color (picker, amber as the default)

## Context

Tonight's 1.5.0 merge kept the launcher pinned to a fixed dark/amber
palette (`theme.LAUNCHER`, `69e692c`) independent of the OS light/dark
toggle — deliberate, since the launcher's whole point is staying visually
distinct from whatever app is under test. Decision made in this session:
rather than leave that palette fixed, give the user a real color picker,
with amber as the shipped default/base color.

## Change

**Scope: the launcher only** (`theme.LAUNCHER`), not the editor's
OS-linked palette (`theme.ACCENT`/etc.) — that separation already exists
and this doesn't touch it.

- Add a "Launcher accent color…" action opening a `QColorDialog`,
  reachable from the tray menu (`_setup_tray()`, `python/main.py`) between
  "Open Editor" and the separator — the tray is available without the
  editor being open, which the color choice shouldn't require. Consider
  mirroring the entry in the editor's `Window` menu (`build_menu_bar()`,
  already added by `ui-polish`) for discoverability, but the tray entry is
  the one that must exist.
- Persist the chosen color. **No settings-persistence mechanism exists
  anywhere in this app today** (checked: no `QSettings`, no config file;
  `paths.py` only resolves `recordings_dir()`/`history_dir()`/`legacy_dir()`)
  — this is new, minimal infrastructure: a small `settings.json` next to
  `history/` under the same `AppLocalDataLocation` `paths.py` already
  resolves. Store one key, the chosen ACCENT hex; absence or an invalid
  value falls back to the amber default (`#c8763a`).
- Derive `ACCENT_HOVER`/`ACCENT_PRESSED`/`PANEL_BORDER` from the chosen
  color algorithmically (HSL lighten/darken, hue and saturation held
  fixed) rather than hand-tuning per color, the way the two existing
  hand-picked palettes are — those aren't reachable for an arbitrary
  user-chosen color. Roughly matching the existing ramps: hover ≈ +8%
  lightness, pressed ≈ -15% lightness (measured off the shipped amber
  values, not an exact spec — tune by eye against the existing panel).
- **Contrast check, not a hard block.** The launcher's labels are white
  text on the ACCENT-colored buttons — both hand-tuned palettes have an
  explicit comment recording that this was checked (the light palette's
  amber was deliberately darkened from the original `#c8763a` because the
  lighter shade fell under 4.5:1 for white text). A free-form picker can't
  carry that guarantee by construction. Compute the WCAG contrast ratio of
  white against the picked color live in the dialog and show a plain
  warning below a 4.5:1 threshold ("Low contrast — button labels may be
  hard to read") — informational, not blocking; the user's choice always
  wins.
- **No live re-theming.** Checked directly: `launcher.py` bakes
  `theme.LAUNCHER.*` values into ~32 `setStyleSheet()` calls at widget
  construction, the same pattern `theme.use_scheme()` already uses for the
  editor (and that function's own docstring documents why it can't be
  live: "a widget already built has its stylesheet baked in"). A picked
  color applies the same way OS-theme-following already does — on next
  launch, not mid-session. Do not attempt to rebuild ~20 widgets'
  stylesheets live; that's a materially bigger, more error-prone feature
  than this ticket asks for.

## Acceptance

- [ ] Tray menu has a working "Launcher accent color…" picker.
- [ ] A freshly-installed app with no settings file shows the current
      amber (`#c8763a`) — the base/default, unchanged from tonight's
      `69e692c`.
- [ ] Picking a color, then restarting Test Assist, shows the launcher
      (floating and docked) in the new color — hover/pressed states and
      the panel border all derived consistently, not just the flat
      button fills.
- [ ] Picking a low-contrast color shows the warning; picking it anyway
      is still honored on restart.
- [ ] The editor's own theme (light/dark, OS-linked) is unaffected by
      this setting.
- [ ] A corrupt or missing settings file falls back to the amber default
      without crashing.

## Not in this issue

- Editor accent color / a second, separate palette choice for
  `theme.ACCENT` — out of scope; only the launcher was asked for.
- Live re-theming while the app is running — restart-to-apply, matching
  how OS-theme-following already works.
- Preset swatches — explicitly decided against; this is a full picker.

## Provenance

User, 2026-09-16: "make it a picker with amber as base." Follows directly
from the earlier question "is there a way to allow a user to select their
own colour palette?", asked right after this session's amber-vs-indigo
fix (`69e692c`) was explained.
