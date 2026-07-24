# Project Log

This file records project changes in reverse chronological order. Every entry
corresponds to the canonical version in `VERSION` at the time of the change.

## 2026-07-24 - 0.2.2 - Patch

- Added contract docstrings to all public application classes, functions, and
  methods.
- Added rationale comments for configuration isolation, segmented byte ranges,
  worker assembly, recursive crawling, Qt lifecycle behavior, schedule
  preservation, queue row lookup and deletion, paused download startup, clipboard
  signal handling, and platform startup updates.
- Kept comments focused on intent and constraints rather than narrating syntax.

## 2026-07-24 - 0.2.1 - Patch

- Added mandatory code-comment and docstring rules to `AGENTS.md`.
- Documented standards for module and public API docstrings, rationale-focused
  inline comments, maintenance markers, prohibited practices, and code review.

## 2026-07-24 - 0.2.0 - Minor

- Replaced the 1,413-line monolithic application with a reusable `udm` package
  composed of configuration, platform, worker, localization, dialog, tab, and
  main-window modules.
- Preserved `MACDM.py` as a small compatibility entry point.
- Documented the application's responsibilities, schedule record, target package
  structure, dependency direction, and verification strategy.
- Preserved scheduler start and end dates, start and end times, recurrence,
  concurrency limit, color, active state, and default-record protection.
- Fixed Options saving so settings changes no longer discard schedule records.
- Improved queued download behavior so a download initially added as paused can
  be started with Resume.
- Added deterministic spider extraction, safer worker cancellation, partial-file
  cleanup, and error propagation for segmented downloads.
- Added automated coverage for configuration, dialogs, main-window composition,
  translations, downloads, spiders, and application event-loop shutdown.
- Fixed an offscreen startup crash by using Qt's portable Fusion style during
  headless runs while retaining the native style for regular macOS launches.

## 2026-07-24 - 0.1.0 - Minor

- Established strict repository rules for modularity, file size, documentation,
  version updates, and change logging.
- Adopted Semantic Versioning and documented the major, minor, and patch policy.
- Added the canonical `VERSION` file and initialized the project at `0.1.0`.
- Created the `docs/` directory for related project documentation.
- Added the Python runtime dependencies required by the application.
- Added repository ignore rules for local environments, Python caches, logs, and
  operating-system metadata.
