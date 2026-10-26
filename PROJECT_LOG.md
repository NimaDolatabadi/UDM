# Project Log

This file records project changes in reverse chronological order. Every entry
corresponds to the canonical version in `VERSION` at the time of the change.

## 2026-10-26 - 0.8.3 - Patch

- Fixed showing the window from the tray. The toggle only checked
  `isVisible()`, which is also true for a window behind other applications or
  minimized to the Dock. A window behind other apps was hidden instead of
  raised, so it flashed and disappeared. A minimized window was hidden, and
  showing it again on macOS restored it as an empty black frame. The new
  `udm/ui/window_presence.py` treats the window as in front only when it is
  visible, not minimized, and active. It also clears the minimized flag before
  showing the window. The tray menu item now reads "Show UDM" or "Hide UDM",
  based on the window state when the menu opens.
- Synced `udm.__version__` with `VERSION`. The 0.8.2 change bumped only
  `VERSION`, so 0.8.2 builds reported 0.8.1 to the browser extension.

## 2026-10-26 - 0.8.2 - Patch

- Fixed a crash on macOS 27 when the menu bar (tray) icon was clicked
  (issue #6). Qt's Cocoa plugin reads `clickCount` from the current event
  when a natively attached status item menu starts tracking; on macOS 27 that
  event is not a mouse event, so AppKit raised an assertion and UDM aborted.
  The new `udm/ui/tray_menu.py` leaves the menu detached on macOS and pops it
  up at the cursor on a tray click. Linux and Windows still attach the menu
  natively.

## 2026-10-25 - 0.8.1 - Patch

- Fixed torrents losing their paused state when UDM quit soon after a pause.
  `TorrentEngine.save_state` stopped waiting after the first resume-data
  alert, so an older, unpaused save could be the last one written. The engine
  now counts outstanding saves per torrent and waits for all of them; saves
  for removed torrents are dropped, so quitting no longer stalls for the
  5-second timeout. Found by the new macOS CI run.
- `packaging/macos/build_dmg.sh` retries `hdiutil create`, which fails
  intermittently with "Resource busy" on CI runners. This failure stopped the
  0.8.0 release build, so 0.8.0 was never published.

## 2026-10-25 - 0.8.0 - Minor

- Added release packages for every platform, published as GitHub releases by
  `.github/workflows/release.yml` when a `v<version>` tag is pushed: macOS
  DMGs for Apple silicon and Intel, a Windows installer (Inno Setup) and
  portable zip, Linux `.deb`, `.rpm`, and Arch Linux packages built with fpm,
  a Linux tarball, and `SHA256SUMS.txt`. Release notes come from this log.
- Added `.github/workflows/ci.yml`, which runs the unit tests on Ubuntu and
  macOS for pushes to `main` and pull requests.
- Moved the PyInstaller spec to `packaging/udm.spec` and made it
  cross-platform; the icon is passed as `UDM_ICON`. Added
  `packaging/windows/` and `packaging/linux/` build scripts. macOS DMGs are
  now named `UDM-<version>-macos-<arch>.dmg`.
- The bridge client reports a connection error instead of crashing where
  Python has no Unix sockets (Windows), and the fallback socket name no longer
  needs `os.getuid`. Browser-extension installation remains macOS-only.
- Documented the release process and per-platform packages in
  `docs/packaging.md` and the README.

## 2026-10-25 - 0.7.1 - Patch

- Fixed browser download capture (issue #5): clicking a download link in
  Firefox showed the browser's save dialog instead of sending the file to UDM,
  because capture relied on `downloads.onCreated`, which fires after the
  prompt. Firefox now intercepts download responses with a blocking
  `webRequest.onHeadersReceived` listener (new `webRequestBlocking`
  permission) and cancels them once UDM accepts; Chromium captures in
  `downloads.onDeterminingFilename`, before the Save As dialog.
  `downloads.onCreated` remains the Firefox fallback, and refused links fall
  back to the browser without being offered twice.
- Moved download capture into `extension/src/downloads.js`. Engine manifest
  overlays now extend the shared `permissions` list instead of replacing it.
- Reinstall the extension from Options > Browser and reload it to apply.

## 2026-10-25 - 0.7.0 - Minor

- Added native BitTorrent downloads through libtorrent, replacing the Torrents
  tab placeholder that reported missing libtorrent support. Magnet links and
  `.torrent` files can be added from the tab, by drag and drop, from the
  clipboard monitor, and (in the app bundle) by opening magnet links or
  torrent files from other apps.
- Added the Qt-free `udm.torrent` package: `TorrentEngine` (session, add,
  pause, resume, remove, snapshots, resume files in the data directory) and
  `TorrentSnapshot` status labels. Finished torrents are paused instead of
  seeding.
- Added `udm.ui.window_torrents.TorrentController` for the Torrents table,
  completion notices, and saving state on exit, and `udm.ui.open_events` for
  macOS open events. Toolbar pause, resume, stop all, delete, and delete
  completed now act on torrents.
- Torrent content is saved to the `.torrent` category folder
  (`~/Downloads/Torrents/` by default); deleting a torrent keeps its files.
- Added `libtorrent` to the requirements and the app bundle, registered the
  `magnet` URL scheme and `.torrent` document type, and raised the bundle's
  minimum macOS version to 15 to match the libtorrent wheel.
- Documented torrents in `docs/torrents.md` and updated the architecture,
  packaging, and README documentation; added engine tests that run offline and
  offscreen controller tests.

## 2026-10-25 - 0.6.0 - Minor

- Added the UDM Capture browser extension (`extension/`) for Chromium browsers
  and Firefox from one Manifest V3 source: browser-download capture with
  cookies, referrer, and user agent; HLS, DASH, and media-file detection per
  tab; context menus; a popup; and an IDM-style on-video Download button with a
  media panel rendered in a closed Shadow DOM.
- Added the `udm.bridge` package: native-messaging framing, a Qt-free native
  host that relays requests over a local socket and launches UDM when closed,
  a Qt socket server that also enforces a single running instance, browser
  definitions, per-engine extension assembly with a fixed Chromium extension
  ID, and a per-browser installer.
- Added Options > Browser with a browser selector, Install Extension action,
  and stream quality setting (`stream_quality`, default Best).
- Added `StreamWorker`, which downloads pages and stream manifests through
  yt-dlp with captured headers, merges with the imageio-ffmpeg binary, supports
  pause and cancel, and removes partial and fragment files on cancel.
  `DownloadWorker` now accepts captured request headers.
- Added `udm.paths`: settings and logs moved to the per-user data directory
  (`~/Library/Application Support/UDM`), fixing writes to `/` from login items
  and app bundles; a legacy working-directory config is copied once. Login
  items register the bundle executable without a script argument when frozen.
- Changed the default download location from `~/Downloads/UDM/<category>` to
  `~/Downloads/<category>`, reusing existing category folders, and added a
  Download folder setting (`download_dir`, empty for Downloads) with a Browse
  button in Options > General.
- Fixed files from links without a file extension (for example
  `download?id=1` or redirects) being saved to `Others`: `DownloadWorker` now
  adopts the server-reported filename and re-routes to its category, such as
  `Programs/Mac` for a `.dmg`, updating the queue row. Added `udm.filenames`
  and a shared `udm.workers.formatting` module.
- Added quality selection: the on-video panel and popup list the qualities
  yt-dlp finds (heights, Audio only, approximate sizes), answered by the native
  host through the new Qt-free `udm.workers.format_probe`; requests carry the
  chosen `quality`, which overrides the default.
- Captured downloads now join the list paused instead of starting, with an
  opt-in Start captured downloads immediately setting (`capture_autostart`).
- Fixed YouTube downloads failing with "Requested format is not available" by
  bundling the Deno runtime and `yt-dlp-ejs` for yt-dlp's JavaScript
  challenges; stream downloads prefer H.264 and AAC so files play in QuickTime.
- HTTPS now uses the macOS trust store through `truststore` (`udm.tls`), and
  browser cookies reach yt-dlp as scoped cookie records (`cookieJar`, loaded by
  `udm.workers.ytdlp_cookies`) instead of a header, removing its warnings.
- Made `udm.workers` exports lazy so the native host imports no Qt.
- Added macOS packaging (`packaging/macos/`) that builds `UDM.app` and
  `dist/UDM-<version>.dmg`, bundling the extension, yt-dlp, and FFmpeg.
- Split queue actions out of `window_downloads.py` and shared test fixtures out
  of `tests/test_ui.py` to keep files under 300 lines; synchronized
  `udm.__version__` with `VERSION` and added a regression test for drift.
- Documented the integration and packaging in `docs/browser-integration.md` and
  `docs/packaging.md`, and refreshed the architecture, design-system, and
  README documentation, including correcting stale module references. The
  README now covers per-browser extension loading, extension usage (quality
  selection, paused captures, category routing), the real clone URL, and the
  added dependencies.
- Added tests for capture validation, paths, bridge framing and transport, the
  native host, the socket server, installer output, extension assembly, the
  stream worker, the Browser page, and capture handling (see the test suite for current coverage).

## 2026-10-25 - 0.5.1 - Patch

- Stopped tracking the per-user `udm_config.json`; the application creates it
  with defaults on first run, and it is now listed in `.gitignore`.
- Added shared `.vscode/settings.json` selecting the conda environment manager.
- Updated the README project structure to describe the untracked settings file.

## 2026-07-24 - 0.5.0 - Minor

- Implemented the design system in code as a new `udm/ui/theme/` package: design
  tokens and two concrete themes (Refined Dark and Light), a single token-driven
  stylesheet builder covering all components including explicitly styled slim
  scrollbars and unified button styling, and a hand-authored line-icon set
  rendered and re-tinted per theme.
- Replaced the mismatched native Qt toolbar icons with the themed line icons and
  added matching tab icons; removed the former single `udm/ui/styles.py`.
- Added a user-selectable Theme setting in Options > General with a System option
  (the default) that follows the operating system's light or dark preference and
  restyles live when the OS toggles, alongside explicit Refined Dark and Light
  choices. The selection persists via a new `theme` config key that auto-migrates
  existing configuration files, and switching restyles the window and open dialogs
  and re-tints icons without a restart.
- Redesigned checkboxes app-wide to show a themed checkmark (rendered to a cached
  image), and replaced the painted yellow and green queue-tree icons with themed
  line glyphs, removing the former `udm/ui/icons.py`.
- Rebuilt the Scheduler dialog as a table with Schedule, Enabled, and Actions
  columns: a row per schedule with a summary, a centered enable checkbox under the
  Enabled header, and edit and delete actions, with detailed field editing in a
  separate `ScheduleEditorDialog`, so it no longer scrolls horizontally or feels
  cramped. Modernized the Options dialog with a left sidebar navigation, stacked
  pages, section headings, and generous spacing.
- Gave the main tabs consistent page margins and made the Bulk Recursive form
  fields grow to full width instead of appearing cramped.
- Split the stylesheet into control and chrome fragments to keep each module
  small, and added an optional `UDM_DEV` style hot reload that live-reapplies
  styling when theme files change, documented in `README.md`.
- Documented the implementation and iconography in `docs/design-system.md` and
  added theme registry, stylesheet, glyph, checkmark-asset, hot-reload, options
  round-trip and navigation, and live-switch regression coverage.

## 2026-07-24 - 0.4.2 - Patch

- Added `docs/design-system.md` defining the application design system: a shared
  token structure (color surfaces, borders, text, accent, status, spacing,
  radius, control heights, typography) with dark, light, and native macOS themes,
  per-component specifications including explicit scrollbar styling, and binding
  contribution rules for future interface work.
- Wired `AGENTS.md` to the design system with a User Interface and Design System
  section and a completion-checklist item requiring interface changes to conform
  to the design system and reference tokens rather than raw values.

## 2026-07-24 - 0.4.1 - Patch

- Guarded the status-cell lookup in scheduled-transfer reconciliation so a
  missing column item cannot raise, matching the defensive access used
  elsewhere in the queue controller.

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
