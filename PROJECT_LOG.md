# Project Log

This file records project changes in reverse chronological order. Every entry
corresponds to the canonical version in `VERSION` at the time of the change.

## 2026-07-24 - 0.4.0 - Minor

- Added a top-level `max_concurrent` setting, defaulting to four, and exposed it
  as Max Concurrent Downloads in Options → Network.
- Decoupled default-queue concurrency from the locked default schedule while
  preserving each explicit schedule's independent `max_dl` limit.
- Restored the Downloading status when an explicitly scheduled active transfer
  resumes after its schedule window reopens.
- Added idempotent launch-time startup reconciliation for macOS plists and
  Windows registry values, including missing, stale-command, matching, and
  disabled states.
- Added configuration migration, options, queue-policy, launch integration, and
  platform startup regression coverage.

## 2026-07-24 - 0.3.0 - Minor

- Enforced schedule date, recurrence, time-window, and maximum-concurrency
  policies at runtime for default and explicitly assigned queues.
- Added custom DNS-backed HTTP sessions while preserving HTTP host routing and
  HTTPS hostname verification.
- Validated segmented HTTP 206 and Content-Range responses, individual segment
  sizes, streaming sizes, and final assembled size before reporting completion.
- Kept paused status stable, retained cancelling and just-completed QThreads
  until termination, and prevented Resume from restarting terminal rows or
  changing torrent placeholders.
- Populated actual size, time-left, and transfer-rate columns and generated
  collision-free destination filenames.
- Limited startup registration changes to accepted option changes instead of
  rewriting platform state during every launch.
- Added regression coverage for worker integrity, queue admission, schedule
  windows, DNS configuration, lifecycle ownership, table data, and filename
  collisions.

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
