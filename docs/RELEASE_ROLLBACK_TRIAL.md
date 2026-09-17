# Release rollback trial — TA-250

**Version:** 1.0
**Date:** 2026-09-16
**Trial of:** `sre-release` and `sre-toil` (`testforge/skills/proposed/`), against a real,
felt pain point: "frustrating trying to get a proper update or rollback working."

Same pattern as `DESKTOP_STABILITY_MATRIX.md` and `testforge/skills/INTROSPECT_CRAWL_SPIKE.md`
— real findings from reading the actual code and running the actual numbers, not a summary of
intentions.

---

## Confirmed before analysis, not assumed

- `release.yml` (desktop) already does what `verified-release-pipeline` asks: tag-triggered,
  `workflow_dispatch` for rehearsal, a real `--version` probe checked against the actual tag on
  a real tag push, and a `--selftest` probe confirming ffmpeg and TLS work inside the frozen
  bundle. Not touched here.
- `python/main.py`'s `__version__` is `"1.5.0"` on `main`, but **`gh release list` shows the
  latest published release is still `v1.4.0`** — no `v1.5.0` tag has been pushed. The
  `pre-1.5.0-merge` tag exists (from the earlier merge's rollback procedure) but the release
  itself was never cut. Worth knowing before reading anything below as "v1.5.0 already
  shipped" — it hasn't, yet.
- `python/update_check.py`'s manual-only design (no poll, no telemetry, no auto-download) is a
  stated constraint, not an oversight — confirmed by its own docstring. `sre-release`'s
  thundering-herd/jitter material assumes automatic client polling; there is none here to
  stampede. Not proposed, not applicable.
- The `github-pages` GitHub Environment has exactly one protection rule, checked directly via
  `gh api repos/emil3663/test-assist/environments/github-pages` and
  `.../deployment-branch-policies`: a `branch_policy` restricting deploys to `main`. **No
  `required_reviewers` rule exists.** There is no manual approval gate today, confirmed, not
  inferred from the workflow YAML alone (a required-reviewer rule can exist in the Environment
  without appearing in `pages.yml`, which is exactly why this was checked via the API instead
  of assumed absent).

---

## Toil ledger: handling a shipped-bad release today

Per `sre-toil`'s own procedure — classify each recurring task against the six properties
(manual, repetitive, automatable, tactical, no enduring value, O(n)); 4+ hits is toil, not a
vibe.

### Desktop build

**Walkthrough — what happens today if the current `releases/latest` turns out broken:**

1. `UpdateChecker` has no concept of "bad." It calls `GET releases/latest` and reports
   whatever comes back as the thing to install. There is no denylist, no known-good marker,
   nothing to check against.
2. To stop recommending the bad release, the maintainer's only lever is publishing an entirely
   new, fixed release — bump `__version__`, regenerate `version_info.txt`, confirm
   `help.html`, tag, push, wait for `release.yml`. There is no way to simply retract or
   supersede the bad one without going through a full release cycle, even if the "fix" isn't
   ready yet and the maintainer just wants to say "don't use this one, use the previous one for
   now."
3. Any user who already updated to the broken release has zero in-app signal. Nothing tells
   them a rollback is possible, or which version was last known-good. Their only path is
   knowing to visit the GitHub Releases page themselves and picking an older `.zip` by hand.

**Classification — maintainer-side recovery tasks** (the tasks a human on this project
actually repeats; `sre-toil`'s definition is about the operator's burden, so end-user
self-service friction from item 3 is named above as a real cost but not force-fit into this
six-property test, which is about who runs the service):

| Task | Manual | Repetitive | Automatable | Tactical | No enduring value | O(n) |
|---|---|---|---|---|---|---|
| **A.** Cut a whole new release cycle just to un-recommend a bad one | Yes — a human tags and pushes | Yes, each bad release | Yes — a denylist/marker check is small and mechanical | Yes — reactive to a defect report | Yes — the gap (no rollback mechanism) still exists afterward, only the instance is patched | Weak — doesn't scale with users/traffic in the classic sense |
| **B.** Manually tell already-affected users to roll back, and how | Yes | Yes | Yes — exactly what an in-app signal replaces | Yes | Yes | **Yes** — scales with how many corporate machines run the tool; more affected installs, more individual outreach |

**Verdict: toil.** Task A hits 4 of 6 (manual, repetitive, automatable, tactical, no enduring
value — 5 of 6, with O(n) the one genuinely weak property, named honestly rather than forced).
Task B hits all 6, including the property `sre-toil` calls the one that matters most. This
clears the "4+ is toil" bar on real classification, not assumption.

### Browser build

**Walkthrough — what happens today if a push to `main` breaks the live site:**

1. `pages.yml` deploys on every push to `main` (or `workflow_dispatch`), immediately, to every
   visitor — confirmed no staging environment and no reviewer gate (see above).
2. Recovery requires: identify the last-good commit, `git revert` it (or the merge commit, with
   `-m 1`), push, and wait for `deploy-pages` to run again. No faster lever exists — no
   "point traffic at the previous artifact" toggle was found in `pages.yml` or the actions it
   calls.
3. `concurrency: { group: pages, cancel-in-progress: false }` means if the bad deploy is still
   running when the revert lands, the revert's run **queues behind it** rather than
   pre-empting it — a real, specific detail from reading the workflow, not a hypothetical.

**Classification — "revert and redeploy on a bad push":**

| Property | Assessment |
|---|---|
| Manual | Yes — a human decides and runs the revert |
| Repetitive | Yes, if it recurs |
| Automatable | Yes, and cheaply — the mechanical part (revert, push) is scriptable; the deploy itself is already automatic |
| Tactical | Yes — reactive |
| No enduring value | Yes — same structural gap (no staging) remains afterward |
| O(n) | **No, honestly.** This is a single-maintainer static site. The *recovery task's own cost* doesn't scale with visitor count or traffic — it's a fixed-cost action per incident. (Exposure while broken scales with traffic; that's a different claim from the recovery task itself scaling, and conflating the two would overclaim.) |

**Verdict: toil, at 5 of 6** — clears the bar, but the classification is honest about which
property doesn't hold, rather than padding to 6 for a cleaner story.

---

## Proposal 1 — Desktop: a rollback marker through the existing seam

**What `sre-release` applies here, and what doesn't:**

- **Applies:** "Have a rollback path and test it. Untested rollback is not a rollback." The
  core gap this proposal closes.
- **Applies:** "The pipeline is an artifact... review the pipeline as deliberately as you
  review the code" — this proposal was designed by reading `update_check.py`'s actual seam,
  not by adding a parallel mechanism next to it.
- **Does not apply:** canarying, staged rollout, feature flags, thundering-herd/jitter — all of
  it assumes a continuously-operated service with automatic client check-ins. This is a
  manually-triggered, zero-telemetry desktop checker with no traffic to stagger and no fleet to
  canary against. Proposing any of that here would be cargo-culting the skill's material
  against a project shape it wasn't written for.

**The design.** `UpdateChecker.interpret()` is already the pure seam between network I/O and
the app's own logic, already tested with literal payloads (`test_update_check.py`). The
`releases/latest` response GitHub already returns includes the release's own notes (`body`),
which `parse_latest_release()` doesn't currently read. A maintainer retracts a shipped release
by editing *that release's own* GitHub Release notes — a metadata edit on an existing
release — to add one line:

```
KNOWN_GOOD: v1.3.0
```

A new pure function, `parse_known_good_override(payload)`, looks for that line and returns the
version it names (or `None`). `UpdateResult` gains one field,
`known_good_override: str = ""`, populated by `interpret()`. No new network call — this rides
the exact same request `UpdateChecker.check()` already makes, still only on the user pressing
the button, still zero telemetry.

**Why this is the minimal option, not just an option.** The alternative considered and
rejected: a second fetch against a maintained denylist file (e.g. a raw GitHub URL to a JSON
file in this repo). That would work, but adds a second network round-trip per check and a new
file to keep in sync. Editing the existing release's own notes reuses infrastructure GitHub
already hosts for free, needs zero new files, and keeps `update_check.py`'s network footprint
at exactly one request — the same commitment its own docstring already makes.

**Implemented, not just proposed** — genuinely minimal, went through `interpret()`'s existing
seam, real tests added the same way the existing ones are structured:

- `python/update_check.py`: `parse_known_good_override()` (new pure function, ~20 lines),
  `UpdateResult.known_good_override` (new field, default `""`), `interpret()` populates it.
- `python/tests/test_update_check.py`: 9 new tests — the marker line found, absent, no body at
  all, malformed JSON, non-string body, non-object payload, found among unrelated lines, and
  two `interpret()`-level tests (override surfaced, defaults empty).
- Full suite run: **405 passed, 2 skipped, 3 deselected, 1 xfailed** — the same shape
  `DESKTOP_STABILITY_MATRIX.md` documents as this suite's normal green state; no regression.

**Explicitly not implemented in this ticket:** `launcher.py`'s `_on_update_result()` doesn't
yet read or display `known_good_override` — the UI decision (what exact copy, whether to show
it even when `is_newer` is false, whether to open the known-good release's page instead of
`releases/latest`'s) is a real design question of its own, out of scope for "propose the
minimal seam addition." The data is now available to build that against.

---

## Proposal 2 — Browser: a timed runbook, not new infrastructure

**What `sre-release` applies here, and what doesn't:**

- **Applies:** "Is the rollback path defined here, and is it exercised? An untested rollback is
  not a rollback, and a rollback that only exists in someone's memory is not defined." This
  proposal exists because that question's honest answer today is no.
- **Applies:** "match sophistication to risk" — the deploy step itself, measured below, is not
  the bottleneck, which is direct evidence against adding process weight to it.
- **Does not apply, explicitly:** canary, staged/gradual rollout, feature flags. `sre-release`
  frames these for "a service you operate" continuously, at a scale where a bad change reaches
  users gradually. A static Pages site with one deployer and no realistic way to serve two
  versions simultaneously doesn't have the shape these tools assume — proposing them would be
  sizing the fix for a team this project doesn't have.
- **Considered and rejected:** a required-reviewer gate on the `github-pages` Environment
  (confirmed absent above, so genuinely available to add). Rejected specifically because this
  is a single-maintainer repo: the only reviewer would be the same person who pushed, so the
  gate either blocks on self-approval (friction, no real second-pair-of-eyes benefit) or
  requires nominating a reviewer who doesn't otherwise exist for this project. This is exactly
  the "don't propose a team-shaped control for a solo maintainer" instinct the trial's scope
  asked for.

**Real, measured deploy timing** (not estimated — `gh run list --workflow=pages.yml`, 5 most
recent completed runs, `createdAt` to `updatedAt`):

| Run | Duration |
|---|---|
| 2026-09-16T09:09:04Z → 09:09:24Z | 20s |
| 2026-09-16T08:16:58Z → 08:17:18Z | 20s |
| 2026-09-16T06:38:16Z → 06:38:42Z | 26s |
| 2026-09-16T05:48:30Z → 05:49:21Z | 51s |
| 2026-09-16T03:41:30Z → 03:41:45Z | 15s |

Range 15-51s, average ~26s. **The deploy pipeline is not the bottleneck in a recovery.** Total
time-to-recover is dominated by human decision time and how the revert lands (direct push vs.
waiting for a PR review), not by `deploy-pages` itself. This is the concrete case against
adding staging infrastructure: there's no slow step here to insert a pause into.

**The proposal — a documented runbook, not a workflow change:**

1. Identify the last-known-good commit (previous successful `pages.yml` run, or `git log`).
2. `git revert <bad-commit>` (or `-m 1` for a merge commit) — preserves history, matches
   `WORKING_AGREEMENTS.md`'s review norms; not a force-push or hard reset.
3. **Normal path:** open a PR per `CONTRIBUTING.md`/`WORKING_AGREEMENTS.md` — for most bad
   pushes there's time for the ~seconds-to-minutes a self-review takes, and `main` staying
   PR-gated is a deliberate existing rule, not incidental.
4. **Break-glass path, named explicitly rather than left to guesswork under pressure:** for a
   live-site emergency where waiting for a PR isn't acceptable, a direct push to `main` is the
   exception — and per `sre-toil`'s own rule ("break-glass should be loud and should file a
   bug"), it should be announced (not silently done) and followed by a real issue recording
   what happened and why the normal path was skipped, not just fixed and forgotten.
5. `pages.yml` runs automatically on the push — 15-51s per the measurements above.
6. Note the `cancel-in-progress: false` concurrency behavior: if the bad deploy is still
   in-flight when the revert lands, the revert's run queues rather than pre-empting it — worth
   knowing so a maintainer under pressure doesn't assume the revert deploy started before it
   actually did.

**Not implemented as a workflow change** — this genuinely is the cheap fix, and it's a
documentation change (this doc plus, if the PR reviewer wants it, a short addition to
`CONTRIBUTING.md`), not a code or CI change. No `pages.yml` edit is proposed.

---

## Provenance

- `sre-release`/`sre-toil` read in full from `testforge/skills/proposed/` before starting, per
  TFP-052's own instruction — the toil classification applies the six-property test per task
  rather than asserting "this is toil," and both proposals cite which parts of `sre-release`
  applied and which explicitly didn't, including one part (the reviewer gate) that was
  confirmed available but rejected on its own scale-mismatch merits, not skipped by default.
- `release.yml`, `pages.yml`, `update_check.py`, `test_update_check.py`, `launcher.py` (the
  `_on_update_result` UI seam), and `WORKING_AGREEMENTS.md`/`CONTRIBUTING.md` read directly,
  not assumed from the TFP-052 handover's own context summary.
- `github-pages` Environment protection rules and deploy timing checked live via `gh api` and
  `gh run list` against the real repository, not inferred from the workflow YAML alone.
- This is filed as `TA-250` (next available; highest prior reference found across
  `TESTASSIST_BACKLOG.md` and open issues was `TA-249`/`TA-232` respectively) — it needed real
  design work before becoming an issue, per `WORKING_AGREEMENTS.md`'s own rule for when a
  `TA-NNN` is warranted. The design record lives in this doc rather than also being duplicated
  into `TESTASSIST_BACKLOG.md`, matching how `CALIBRATION.md` and
  `skills/INTROSPECT_CRAWL_SPIKE.md` served the same role in `testforge` without a second copy
  elsewhere.
