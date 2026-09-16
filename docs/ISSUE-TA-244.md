TA-244 — The recording play-badge exists but is too small/subtle to notice in the History strip

## Context

Correcting an earlier read of this same T2 evaluation session: I had told
the tester Finding 1 (History thumbnails not visibly distinguishing a
recording from a snapshot) was already fixed and needed no new ticket,
based on `_RecordingThumb`'s play-badge existing in code (commit `a7a465f`).
The tester then pointed at the actual editor screenshot
(`test-assist-...playback button on video...png`, 2026-09-16) and confirmed
the badge genuinely is there — but sitting tiny and low-contrast in the
thumbnail's bottom-right corner, easy to miss entirely at a glance, and
with nothing else about the "Recent 5" strip signalling that any of it
contains video. That's a real, distinct finding from what the mechanism's
existence alone answers.

Confirmed in code (`python/editor.py`, `_RecordingThumb` class): the badge
is a `QLabel("▶")` styled
`"QLabel { color: #ffffff; background: rgba(0,0,0,0.55); border-radius: 9px;
font-size: 11px; padding: 1px 6px 1px 8px; }"`, positioned in
`resizeEvent`-driven `move()` at the thumbnail's bottom-right corner minus a
6px margin. On a 168px-wide thumbnail tile, an 11px-font badge in a
semi-transparent dark pill in the corner is easy to scan straight past,
especially scrolling quickly through a "Recent 5" list rather than
examining one tile closely — which is exactly the discoverability problem
the badge's own docstring says it exists to prevent ("a recording is never
mistakable for a screenshot at a glance"). In practice, for this tester, it
was.

## Change

**Decided, 2026-09-16: a combination, not a single treatment** — enlarging
the existing corner badge alone still requires looking directly at that
corner, which is exactly what "easy to scan straight past" means; only a
whole-tile signal is noticeable at normal scanning speed regardless of
where the eye lands on the tile.

- **Whole-tile border, at rest, not just on hover.** `_RecordingThumb`
  already carries a static `theme.LINE_STRONG` border at rest and only
  switches to `theme.ACCENT` on hover (`python/editor.py` ~1439) — change
  the rest-state border itself to `theme.ACCENT`, so a recording tile
  reads as visually distinct from a snapshot tile in the strip before any
  interaction, not only when the pointer happens to land on it. Reuses the
  token already in this exact file (`_SnapshotThumb` uses the same
  `theme.ACCENT` for its own hover state) — no new color introduced.
- **Larger, higher-contrast badge.** Bump the glyph's `font-size` and the
  badge's overall size from its current 11px/tight-padding pill, and swap
  the semi-transparent `rgba(0,0,0,0.55)` background for a solid
  `theme.ACCENT` background — the transparent dark pill is exactly what
  blends into a dark-mode thumbnail; a solid brand color doesn't.
- **No caption-text chip.** Rejected: the "Recording N · date" caption is
  already compact, and a whole-tile border already solves "noticeable at a
  glance" without adding text that competes with that caption for space in
  a 168px-wide tile.

Both changes reuse `theme.ACCENT`, so a recording tile's accent border and
its badge read as one consistent signal, not two independently-colored
elements. `_SnapshotThumb` is untouched by either change — its border
stays `theme.LINE` at rest, its hover stays `theme.ACCENT`, exactly as
today.

## Acceptance

- [ ] A design decision is recorded on the badge's visual treatment.
- [ ] After the change, a recording is identifiable from the "Recent 5"
      strip at normal scanning speed, not only on close inspection of a
      single tile — verified against a real rendered screenshot, not
      argued from the CSS alone.
- [ ] Snapshot thumbnails are unaffected (no badge, no new visual noise
      added to `_SnapshotThumb`).

## Not in this issue

- Whether the play badge is present at all — it is, confirmed working,
  not the gap here.
- `TA-242` (launcher visible in its own recording) and `TA-243` (double-
  click to stop, plus a newly-found phantom-snapshot correlation) — same
  testing session, unrelated mechanisms.

## Provenance

- Tester's live evaluation, Launcher Evaluation Pass task T2, 2026-09-16,
  reacting to a screenshot of the Editor's History panel: "there does seem
  to be a playback button but it is tiny and hidden in the bottom right
  corner of the image in the editor... there is nothing indicating that
  the recent strip has videos though."
- Badge styling and positioning confirmed by reading `_RecordingThumb` in
  `python/editor.py` directly, not inferred from the screenshot alone.
