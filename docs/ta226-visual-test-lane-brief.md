# Brief: add a real-rendering visual test lane (TA-226), build, verify, report

## Why

Flagged in rc5's own report: TA-221's acceptance criterion asked for a
rendered screenshot proving Copy/Export are no longer clipped, and this
environment couldn't produce one — `QT_QPA_PLATFORM=offscreen` (set in
`conftest.py` and pinned again in `.github/workflows/python-tests.yml`)
doesn't rasterize real glyphs, so a screenshot taken under it is tofu boxes,
not text. rc5 shipped with a measurement-based proxy instead of the real
check the ticket asked for. Full details, including why this is fixable
without new infrastructure (CI already runs on `windows-latest`, a real
Windows machine — `offscreen` is a self-imposed constraint, not something
the platform requires), are in `TESTASSIST_BACKLOG.md`'s TA-226.

This is infrastructure, not a bug fix, and it's self-contained — it doesn't
touch app code, only the test suite and CI config — so it doesn't need
bundling with anything else.

## Task

Read TA-226 in `TESTASSIST_BACKLOG.md` in full before starting — the ticket
carries the actual Scope/Deliverables/Acceptance criteria. Summary:

1. Add a separate test lane (a `@pytest.mark.visual` marker or its own test
   module — whichever fits this codebase's existing conventions better) that
   runs against the real `windows` Qt platform plugin, not `offscreen`.
2. Pick and justify one assertion mechanism — pixel-diff against a
   checked-in golden image, or a bounding-box/ink-extent check against the
   widget's client rect. The ticket has the tradeoff; make the call and say
   which was chosen and why in the report, don't default silently.
3. Retrofit TA-221's own acceptance criterion (Copy/Export render unclipped)
   as the first real test in this lane. Verify it fails against the old
   `setFixedHeight(26)` code and passes against current code — same
   verify-it-would-have-caught-the-bug discipline as every other test added
   this project.
4. Wire it into `.github/workflows/python-tests.yml` as its own job or step,
   kept independent of the main `offscreen` suite's pass/fail — a slow or
   flaky visual check should never block the suite everything else depends
   on.
5. Add a short note to whichever doc already carries this project's testing
   conventions, saying which class of future ticket belongs in this lane.

## Verification

- Confirm the retrofitted TA-221 test genuinely exercises real font
  rendering — not just that it runs under a different marker. Show real
  measured values (e.g. actual ink-extent pixels, or an attached/described
  screenshot), not a claim that it "should" be rendering for real now.
- Run both lanes: the main suite must be unaffected (same pass count as
  rc5's `320 passed, 0 skipped`, plus whatever count the new lane adds
  separately). Confirm CI shows them as CI reports them (two jobs/steps, or
  however they end up wired) rather than asserting it from the workflow
  file alone.
- If the visual lane is slower per-test than the main suite (real font
  rasterization usually is), note roughly how much, so it's a known cost
  going forward rather than a surprise on a later CI run.

## Report back

One dated entry in `docs/BUILD_LOG.md` covering: which assertion mechanism
was chosen and why, confirmation the retrofitted TA-221 test fails
pre-fix/passes post-fix for real, the CI wiring (job/step name), commit
hash, and CI run link. No install step needed — this doesn't touch
`python/dist/`, only tests and CI config, so no new `rc` build follows from
this brief by itself.

**Commit `TESTASSIST_BACKLOG.md`'s TA-226 status update in the same commit
as the test/CI changes**, not as a separate uncommitted write.
