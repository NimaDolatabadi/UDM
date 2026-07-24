# Project Instructions

These rules are strict and apply to every contributor and automated agent working
in this repository.

## Communication and Content

- Do not use emojis in source code, documentation, commit messages, logs, user
  interfaces, or other project content.
- Keep writing clear, direct, and maintainable.

## Architecture

- Every source file must be designed as a reusable module with one clear
  responsibility.
- Prefer small, composable modules with explicit public interfaces.
- Keep each file below 300 lines. Aim for fewer than 200 lines when practical.
- Treat any file approaching 300 lines as a refactoring signal.
- A file with 500 or more lines is considered to have multiple responsibilities
  and must be split before more behavior is added.
- Generated files and third-party vendored files are exempt only when they are not
  maintained by this project.

## Documentation

- Store all project documentation in `docs/`.
- Create `docs/` before adding documentation when it does not exist.
- Root-level documentation is limited to conventional entry-point or governance
  files, including `README.md`, `AGENTS.md`, and `PROJECT_LOG.md`.
- Update related documentation whenever behavior, architecture, setup, or
  maintenance processes change.

## Code Comments and Docstrings

- Follow the commenting standard in `docs/commenting.md`.
- Give every maintained source module a concise module-level docstring.
- Document public classes, functions, and methods when their contract, inputs,
  return value, side effects, or failure behavior is not immediately obvious.
- Use inline comments to explain intent, constraints, invariants, or non-obvious
  decisions. Do not narrate syntax or restate what the code already expresses.
- Keep comments accurate whenever related behavior changes. Remove stale comments
  in the same change that makes them obsolete.
- Use `TODO:`, `FIXME:`, and `NOTE:` only with the meanings defined in
  `docs/commenting.md`.
- Do not commit commented-out code.

## Versioning

- The canonical project version is stored in the root `VERSION` file.
- Follow the versioning policy in `docs/versioning.md`.
- Every project change must update `VERSION`.
- Use exactly one version bump per coherent change set or pull request.
- Apply the bump that matches the highest-impact change in the change set.
- Never reuse a released version.

## Project Log

- Every project change must add an entry to the root `PROJECT_LOG.md`.
- Each entry must state the date, version, change category, and a concise summary.
- Add new entries at the top of the log, directly below its introduction.
- Keep log entries useful to someone investigating the project's history later.
- Do not remove or rewrite previous entries except to correct factual errors.

## Completion Checklist

Before considering any change complete:

1. Confirm source files remain reusable, single-responsibility modules.
2. Confirm maintained files are below 300 lines.
3. Confirm comments and docstrings follow `docs/commenting.md`.
4. Place or update related documentation in `docs/`.
5. Choose the appropriate version bump and update `VERSION`.
6. Add the matching entry to `PROJECT_LOG.md`.
7. Run the relevant checks or tests and report their results.
