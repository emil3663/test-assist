# Test Assist

Two builds from one specification: a vanilla-JS browser app at the repo root,
and a PySide6 desktop app under `python/`. They are separate codebases with
separate suites — check which one a change belongs to before starting.

## Commits

Conventional Commits: `<type>(<scope>): <subject>`, then a body giving the
why, the alternatives rejected, and what the change deliberately does not do.
Full convention in `docs/CONVENTIONAL_COMMITS.md`.

Scopes for this repo: `capture` `canvas` `editor` `launcher` `hotkeys`
`geometry` `theme` `build` `tests` `docs` `browser`.

Applies from the next commit. History is not rewritten to conform, and no
commit linter is installed — that is deliberate, and the reasoning is in
`docs/CONVENTIONAL_COMMITS.md`.

## Working agreements

`docs/WORKING_AGREEMENTS.md` — brief shape, how issues relate to the desktop
build's `TA-NNN` tickets, and the `Closes #N` trailer.
