# Application Architecture

## Current Structure

Before version `0.2.0`, the application was implemented in a single 1,413-line
`MACDM.py` file. That file owned all of the following responsibilities:

- process startup and Qt application creation;
- configuration defaults, JSON persistence, and download path selection;
- operating-system startup registration;
- translations and application styling;
- queue icon rendering;
- segmented and single-stream download execution;
- site grabbing and recursive crawling;
- scheduler editing, including start and end dates and times;
- application options and category editing;
- all main-window widgets, tabs, actions, tray behavior, and event handlers.

This made changes risky because unrelated behavior shared one module and the UI
could not be tested or reused in isolation.

## Target Package Structure

The `udm` package separates domain data, services, workers, and user interface
components:

```text
MACDM.py                  entry point; dispatches --native-messaging-host
extension/                browser extension source (see browser-integration.md)
packaging/                shared PyInstaller spec; macos/, windows/, linux/ build scripts
.github/workflows/        CI tests and release packaging
udm/
  __init__.py             package version
  app.py                  Qt application, single instance, bridge start
  capture.py              validated browser capture requests
  config.py               settings persistence and category routing
  constants.py            defaults and fixed choices
  filenames.py            server filenames and unique destination paths
  network.py              HTTP sessions with custom DNS
  paths.py                data, log, socket, resource paths; launch commands
  scheduling.py           schedule windows and limits
  startup.py              login-item registration
  bridge/
    protocol.py           native-messaging framing and socket JSON lines
    native_host.py        browser-launched relay to the app
    server.py             Qt local-socket server
    browsers.py           supported browsers and host directories
    extension_build.py    per-engine extension assembly
    installer.py          per-browser installation
    safari.py             Safari extension app assembly and signing
  i18n/                   translation catalogs
  torrent/
    engine.py             libtorrent session and resume files
    status.py             torrent snapshots and labels
  workers/
    download.py           segmented and streaming HTTP downloads
    formatting.py         transfer rate and duration text
    spiders.py            page and recursive discovery
    stream.py             yt-dlp stream and page downloads
    ytdlp_options.py      yt-dlp option construction
  ui/
    main_window.py        concrete window composed from mixins
    window_shell.py       chrome, tray, lifecycle
    tray_menu.py          tray menu wiring (no native menu on macOS)
    window_presence.py    in-front check and restore for tray show/hide
    window_actions.py     toolbar, translation, dialogs
    window_theme.py       theme application
    window_add_downloads.py  new-download prompt flow and queue rows
    download_prompt.py    New Download dialog (folder, Start Now, Later)
    window_downloads.py   worker lifecycle, progress, row updates
    progress_delegate.py  progress bar painted in the Size column
    window_clipboard.py   clipboard link monitor
    window_queue_actions.py  pause, resume, stop, delete
    window_bridge.py      extension request handling
    window_torrents.py    Torrents tab and torrent engine lifecycle
    open_events.py        macOS magnet and .torrent open events
    window_grabber.py     single-page discovery
    window_bulk.py        recursive discovery
    queue_runtime.py      schedule and concurrency admission
    options_dialog.py     settings dialog
    options_browser_page.py  Browser settings page
    settings_layout.py    shared settings layout helpers
    scheduler_dialog.py   schedule list
    schedule_editor.py    single schedule editor
    tabs.py               main tab widgets
    download_roles.py     table data roles
    dev_reload.py         development style reload
    theme/                design tokens, stylesheet, glyphs
tests/
```

`MACDM.py` remains a small compatibility entry point so existing launch commands
continue to work.

## Responsibilities

### Configuration and Constants

`udm.constants` contains immutable defaults and fixed choices; translations
live in `udm.i18n`. `udm.config.ConfigManager` owns configuration merging,
persistence, and category-path selection. `udm.paths` resolves the per-user data
directory (`~/Library/Application Support/UDM` on macOS), log and socket paths,
bundled resources, and the command that launches the app from source or from a
PyInstaller bundle. None of these modules depend on Qt.

### Platform Service

`udm.startup` owns operating-system startup registration. Platform-specific code
does not leak into the main window. At construction, the main window requests an
idempotent reconciliation: matching plist or registry entries are untouched,
missing or stale enabled entries are written, and existing disabled entries are
removed. Option changes use the same reconciliation service.

### Network and Scheduling Services

`udm.network` builds per-worker HTTP sessions and applies configured DNS servers
while preserving the original HTTP host and HTTPS certificate hostname.
`udm.scheduling` evaluates date, recurrence, normal or overnight time windows,
and validated concurrency limits without depending on Qt.

### Background Workers

`udm.workers.download` owns HTTP download execution, pause, resume, cancellation,
and segmented file assembly. A segmented response must be HTTP 206 with the
requested `Content-Range`, every part must have its expected size, and the
assembled file must match the advertised total. `udm.workers.spiders` owns
single-page media discovery and same-domain recursive discovery.
`udm.workers.stream` runs yt-dlp for captured pages and HLS or DASH manifests,
merging with FFmpeg, and reports progress through the same signals.

Before writing, `DownloadWorker` adopts the server-reported filename
(`Content-Disposition`, then the post-redirect URL, then an extension inferred
from `Content-Type`) and, when it differs from the provisional name derived
from the link, re-routes the transfer to that name's category folder and emits
`relocated`. The new destination is claimed by creating it atomically, so
concurrent downloads of the same file receive distinct names.

Workers communicate through Qt signals. They do not directly modify widgets.

### Dialogs

`udm.ui.scheduler_dialog` exclusively owns schedule editing. A schedule record
contains:

- `name`: display name;
- `active`: whether the schedule is enabled;
- `max_dl`: maximum concurrent downloads;
- `start_date` and `end_date`: inclusive calendar range in `yyyy-MM-dd`;
- `start_time` and `end_time`: daily time range in `HH:mm`;
- `recurrence`: every day, even days, or odd days;
- `color`: queue marker color;
- `is_default`: whether the record is protected from deletion.

`udm.ui.options_dialog` owns general, network, and category settings.
The Network tab exposes the top-level `max_concurrent` limit for the always
eligible default queue. Explicit schedules retain their independent `max_dl`
limits.

### Main Window

The concrete main window composes focused mixins:

- shell: application chrome, toolbar, tabs, translations, tray, and lifecycle;
  on macOS the tray menu is not attached to the native status item, because
  Qt's Cocoa plugin crashes on macOS 27 when that menu opens (issue #6); it is
  popped up at the cursor from the tray `activated` signal instead. Tray
  show/hide hides the window only when it is visible, not minimized, and
  active; otherwise it restores the window, clearing the minimized state first;
- add downloads: single links, clipboard links, dropped links, and browser
  captures go through `offer_download`, which opens the New Download prompt
  (folder, file name, Start Now, Download Later, Cancel) unless Options turns
  it off. Grabber and Bulk transfers add rows directly. A chosen folder keeps
  server-reported names in that folder, and an edited name is kept exactly;
- downloads: workers, progress, and row updates. The Size column stores the
  percentage in `PROGRESS_ROLE`, and `ProgressDelegate` paints it as a bar;
- clipboard: offers copied magnet and file links;
- queue runtime: schedule-window enforcement and concurrency-limited admission;
- grabber: single-page discovery, filtering, selection, and transfer;
- bulk: recursive discovery, progress, cancellation, and transfer;
- queue actions: pause, resume, stop, and delete for selected rows;
- bridge: browser-extension requests and window focus requests;
- torrents: magnet and `.torrent` adds, progress refresh, and persistence.

### Browser Bridge

`udm.bridge` connects the browser extension to the app. The browser starts the
native host, which relays each request over a local socket to the
`BridgeServer` owned by the running window, launching UDM when needed. The same
socket enforces a single running instance. See `docs/browser-integration.md`.

### Torrents

`udm.torrent.TorrentEngine` wraps one libtorrent session without Qt. The
`TorrentController` window mixin polls its snapshots once a second into the
Torrents tab and saves state on exit. See `docs/torrents.md`.

The split follows behavior boundaries while keeping the shared main-window state
explicit. UI construction helpers live in `udm.ui.tabs`.

## Dependency Direction

```text
entry point -> application -> main window -> dialogs/tabs/workers/services
     |                                |
     |                                -> configuration -> paths, constants
     -> native host -> bridge protocol, paths   (no Qt)
```

Constants and configuration do not import UI modules. Workers do not import the
main window. Dialogs return data and do not persist it themselves. This keeps
lower-level modules reusable and prevents circular imports.

## Verification Strategy

- Compile every maintained Python module.
- Unit test configuration merging and category routing with temporary paths.
- Unit test spider extraction, DNS session construction, schedule policy, range
  validation, integrity checks, and worker state without external network access.
- Construct dialogs and the main window with Qt's offscreen platform.
- Verify all four tabs, scheduler date/time fields, toolbar actions, and clean
  application shutdown.
- Launch the compatibility entry point in an offscreen smoke test and confirm it
  remains alive until intentionally closed.
- Test bridge framing, the native host, the socket server, installer output,
  extension assembly, capture validation, and the stream worker with a fake
  yt-dlp downloader.
- Before a release, build the packages (see `docs/packaging.md`) and exercise the bundled native host and
  single-instance handoff (see `docs/packaging.md`).
