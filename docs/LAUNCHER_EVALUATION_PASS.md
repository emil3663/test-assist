# Launcher evaluation pass — PR #19 (`ca71881`)

**Purpose:** produce a defensible accept/reject on the launcher rebuild, from
use rather than from argument. Roughly 30 minutes.
**Status:** ⬜ not run

---

## Why this exists

Every input to this decision so far has been a diff, a rendered screenshot, or
a written case. Nobody has *used* the rebuilt launcher. The two things in
dispute — whether the panel explains itself, and whether 2.68× the height
costs anything real — are both properties of using it next to an application
under test, and neither survives being reasoned about.

**The criteria below are written before the session deliberately.** You have
now read a well-argued case for the rebuild; judging it afterwards against
remembered impressions is how a decision gets ratified rather than made.
Answer these, in writing, as you go.

---

## Setup

Run from the review worktree — it is detached, so nothing you do there can
land on the branch:

```powershell
cd "C:\Users\MSI workstation\source\repos\test-assist\artifacts\review\ui-polish\python"
& "C:\Users\MSI workstation\source\repos\test-assist\.venv\Scripts\python.exe" main.py
```

**Run one build at a time.** The installed v1.4.0 and this one both claim the
real Win32 hotkeys via `RegisterHotKey`, and both enforce single-instance —
running them together produces exactly the failure TA-230 records. Close one
fully (check the tray) before starting the other.

Have a real application open to capture from — whatever you would actually be
testing. Not a blank desktop.

---

## The tasks

Each is work that is queued anyway, so the session produces artefacts you
need as well as a verdict.

| # | Task | What it exercises |
|---|---|---|
| 1 | Capture and annotate evidence for **TA-222** (settings bar right-aligned instead of centred) | Region capture → annotate → export, the core loop |
| 2 | Capture evidence for **TA-215**'s two open gaps: video-mode not visually distinct before recording; a finished recording not appearing in History without reopening the editor | Mode-less design under a real question about modes |
| 3 | Record a ten-second clip, then stop it | The rebuild's central UX claim |
| 4 | Repeat task 1 **docked**, then **undocked** | Whether the strip is genuinely the compact mode |
| 5 | Capture something while the **About** dialog is open | TA-217's still-open gap, against the new panel |

---

## What to answer — write the answer, not a tick

### Descriptiveness — the case *for* the rebuild

1. At any point, did you have to stop and work out which control did what?
   Which one, and for how long?
2. Task 3: when you wanted to stop the recording, did you hesitate? Where did
   your eye go first?
3. Did you read the footer ("Hides to the tray · right-click → Quit")? Did it
   tell you something you did not know?

### Footprint — the case *against*

4. Where did you put the panel on screen? Did you move it during the session,
   and why?
5. Did it cover anything you needed to see? Concretely — what?
6. Task 4: docked, did the strip do the job the panel does? Or did you undock
   it to get something done? The strip also grew — 156px → 271px tall, six
   controls where there were three.

### The mode removal

7. Did you miss the Photo/Video toggle, or not notice it was gone?
8. Three separate buttons instead of one mode-dependent button — better, worse,
   or indifferent in use?

### The palette — `ff0f276`, a separate decision

9. The current launcher is dark with an amber accent; the rebuild is light with
   indigo, following the OS theme. **Does the rebuilt panel read as part of the
   application you were capturing from?** The commit that made this change
   flags the question itself: the amber may have been deliberate, to keep an
   always-on-top overlay visually distinct from whatever is under test.
10. This is droppable on its own — `ff0f276` is the earliest launcher commit on
    the branch. Judge it separately from the rebuild.

### Anything unprompted

11. What annoyed you that is not on this list? That is usually the real
    finding.

---

## The decision to record

One of:

- **Accept whole** — #19 merges as-is.
- **Accept, drop `ff0f276`** — keep the rebuild, keep the amber palette.
- **Reject the rebuild** — a five-commit unpick (`ca71881`, `5c5e0a1`,
  `aca5463`, parts of `cc5d893`, the launcher/strip diagrams in `1eb6421`),
  and `5c5e0a1`'s dangling `_btn_record` reference must be unpicked with it or
  the app raises `AttributeError` on startup. See
  `docs/VERIFICATION_2026-09-11.md` §6.
- **Accept with changes** — name them. "RECENT should be collapsible" is a
  legitimate outcome: it accounts for 79px of the 185px growth, so making it
  optional takes the panel from 2.68× to 1.96× the current height.

Record the verdict and the reasoning in this file, then it feeds the 1.5.0
decision record.

---

## Results

**Date:**
**Build:** `ui-polish` @ `90fcf92`, from source
**Application under test:**

| # | Answer |
|---|---|
| 1 | |
| 2 | |
| 3 | |
| 4 | |
| 5 | |
| 6 | |
| 7 | |
| 8 | |
| 9 | |
| 10 | |
| 11 | |

**Decision:**

**Reasoning:**
