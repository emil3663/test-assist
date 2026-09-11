# Conventional Commits

A commit message convention: a small, fixed grammar at the front of the
subject line that makes a commit readable by a person *and* parseable by a
tool.

This is not a style preference. It buys three specific things this repo
currently does by hand or not at all — see "Why bother" below.

---

## The format

```
<type>(<scope>): <subject>

<body>

<footers>
```

Only the first line is mandatory, and only `<type>` and `<subject>` within it.

```
fix(capture): keep every pixel grabbed from a HiDPI screen
```

### Rules for the subject

- **Imperative mood** — "add", not "adds" or "added". The test: the subject
  should complete the sentence *"Applying this commit will…"*.
- **Lower case** after the colon, no trailing full stop.
- **Under ~72 characters**, because `git log --oneline` truncates.
- **One concern.** If the subject needs an "and", it is usually two commits.

### The body

Optional, but this repo's existing commit messages already do the valuable
thing: they explain *why*, and what was rejected. Keep that. The convention
changes the first line only — it does not ask anyone to write less.

Wrap at 72 columns. Separate from the subject by a blank line.

---

## Types

The full set in use here:

| Type | Use it for | In the changelog? |
|---|---|---|
| `feat` | a new capability a user can notice | yes — Added |
| `fix` | corrected behaviour | yes — Fixed |
| `perf` | faster or lighter, same behaviour | yes — Changed |
| `docs` | documentation only | no |
| `test` | tests only — adding, fixing, restructuring | no |
| `refactor` | restructuring with no behaviour change | no |
| `build` | packaging, PyInstaller spec, dependencies, CI | no |
| `chore` | everything else — housekeeping, release records | no |
| `revert` | undoing an earlier commit | yes |

Two that are worth being strict about:

- **`refactor` means no behaviour change.** If behaviour changed at all, it
  is a `fix` or a `feat` that happened to involve restructuring. This
  matters because `refactor` is the one type a reviewer may read less
  carefully.
- **`test` means tests only.** A commit that fixes code *and* adds the test
  for it is a `fix` — the test is part of the fix, not a separate event.

---

## Scopes

Optional, but nearly always worth it here because the codebase has clean
module boundaries. Use the ones that already exist:

| Scope | Covers |
|---|---|
| `capture` | `capture.py` — the overlay, grabbing, the recorder |
| `canvas` | `canvas.py` — annotations, rendering, export |
| `editor` | `editor.py` — the editor window, history, exports |
| `launcher` | `launcher.py` — the floating/docked launcher, tray |
| `hotkeys` | `global_hotkeys.py` |
| `geometry` | `screen_geometry.py` — multi-display maths |
| `theme` | `theme.py` — colours, fonts, stylesheet |
| `build` | `TestAssist.spec`, `build.ps1`, workflows, packaging |
| `tests` | the suites themselves |
| `docs` | README, briefs, this file |
| `browser` | the vanilla-JS build — `index.html`, `app.js`, `style.css` |

Leave the scope off when a change genuinely spans several — don't invent
`(multiple)`.

---

## Breaking changes

Two ways, and you can use both:

```
feat(canvas)!: store annotation coordinates in device pixels
```

```
feat(canvas): store annotation coordinates in device pixels

BREAKING CHANGE: exported JSON from earlier versions no longer loads,
because coordinates were logical pixels and are now device pixels.
```

The `!` is the signal; the `BREAKING CHANGE:` footer is where the migration
story goes. For a tool whose JSON export is explicitly a public interface
("for replay or downstream integration"), this is the flag that matters
most — it is the one thing that can silently break someone else's work.

---

## Footers, and how this meets `CONTRIBUTING.md`

The issue trailers from `CONTRIBUTING.md` are footers, and go last:

```
fix(capture): keep every pixel grabbed from a HiDPI screen

A selection is dragged in logical pixels, but a screen with a
devicePixelRatio above 1 holds more real pixels than that, and the
result pixmap was sized in logical pixels. Measured on a 2.0-ratio
display: 480,000 pixels grabbed, 120,000 kept.

Closes #2
```

`Closes #N`, `Refs #N`, `BREAKING CHANGE:` and `Co-Authored-By:` are all
footers. Keep them in one block at the end, separated from the body by a
blank line, so `git interpret-trailers` can read them.

---

## Worked examples, from this repository

Real commits from `git log`, rewritten. The point is not that the originals
were bad — several are better prose than what replaces them. It is that the
rewrite is *sortable*, and that two of them turn out to be more than one
commit.

**Already close:**

```
-  TA-215: the docked launcher now shows recording state
+  feat(launcher): show recording state on the docked launcher
```
```
-  Bind Alt+P, Alt+Shift+P and Alt+V as real global hotkeys (TA-211)
+  feat(hotkeys): bind Alt+P, Alt+Shift+P and Alt+V as real global hotkeys
```
The `TA-NNN` moves out of the subject — it belongs in the issue link, and
the subject has only ~72 characters to spend.

**Mechanical:**

```
-  Guard the five real-Win32-API TA-211 hotkey tests with skipif
+  test(hotkeys): guard the five real-Win32-API tests with skipif
```
```
-  Add a pywinauto black-box smoke lane driving the real packaged exe
+  test(build): add a pywinauto smoke lane driving the packaged exe
```
```
-  Record the rc5 build: exact md5, paths, CI confirmation
+  chore(build): record the rc5 build — md5, paths, CI confirmation
```

**Where the convention does real work** — these were each several commits:

```
-  Fix help btn visibility, anchor docked strip, reorganise help.html SVGs
+  fix(launcher): make the help button visible against the docked strip
+  fix(launcher): anchor the docked strip flush to the screen edge
+  docs(launcher): reorganise the help.html diagrams
```
```
-  Add zoom, persistent history, single-instance, and expanded tool tests
+  feat(editor): add zoom and fit-to-window
+  feat(editor): persist capture history across restarts
+  feat(launcher): enforce a single running instance
+  test(editor): expand tool coverage
```

Neither original is a bad message. But "add zoom, persistent history,
single-instance, and expanded tool tests" cannot be reverted in parts,
cannot be bisected to find which of the four broke something, and appears
once in a changelog that needs it four times.

---

## Why bother

Three concrete things, in the order they will actually arrive.

**1. `CHANGELOG.md` stops being written twice.** It is currently maintained
by hand, so every user-visible change is described once in the commit and
again in the changelog — where it can drift, or be missed. With types on
commits, the changelog is generated from `feat` and `fix` since the last
tag.

**2. Version numbers follow a rule instead of a judgement.** `v1.0.0`,
`v1.1.0` and `v1.3.0` are tagged with nothing mechanical connecting a set of
commits to the number that follows. Conventional Commits maps directly onto
semver: a `fix` is a patch, a `feat` is a minor, a `!`/`BREAKING CHANGE` is
a major. The decision stops being made from memory at tag time.

**3. `git log` becomes answerable.** "What did a user get between v1.1.0 and
v1.3.0" is currently a read-everything exercise:

```bash
git log v1.1.0..v1.3.0 --oneline --grep '^feat\|^fix'
```

**What adopting this does not do.** Nothing is automated by the convention
alone — it only makes automation possible later. No tooling is being added
here, on purpose: a commit linter that rejects messages before anyone has
internalised why is a good way to make people resent a convention. Get the
habit first; add `commitlint` or `release-please` when the payoff is wanted.

---

## Starting from here

- The convention applies **from the next commit**. History is not being
  rewritten, so `git log` will stay mixed for a while. That is fine.
- When unsure of the type, ask: *would a user of Test Assist notice this?*
  If yes it is `feat` or `fix`; if no it is almost always one of the rest.
- When unsure whether it is one commit or two, it is two.

Reference: <https://www.conventionalcommits.org/en/v1.0.0/>
