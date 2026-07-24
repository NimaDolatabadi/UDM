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
MACDM.py
udm/
  __init__.py
  app.py
  config.py
  constants.py
  startup.py
  workers/
    __init__.py
    download.py
    spiders.py
  ui/
    __init__.py
    icons.py
    options_dialog.py
    scheduler_dialog.py
    styles.py
    tabs.py
    main_window.py
    window_bulk.py
    window_downloads.py
    window_grabber.py
    window_shell.py
tests/
```

`MACDM.py` remains a small compatibility entry point so existing launch commands
continue to work.

## Responsibilities

### Configuration and Constants

`udm.constants` contains immutable defaults, schedule choices, colors, and
translations. `udm.config.ConfigManager` owns configuration merging, persistence,
and category-path selection. It has no Qt dependency.

### Platform Service

`udm.startup` owns operating-system startup registration. Platform-specific code
does not leak into the main window.

### Background Workers

`udm.workers.download` owns HTTP download execution, pause, resume, cancellation,
and segmented file assembly. `udm.workers.spiders` owns single-page media
discovery and same-domain recursive discovery.

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

### Main Window

The concrete main window composes focused mixins:

- shell: application chrome, toolbar, tabs, translations, tray, and lifecycle;
- downloads: queue rows, workers, selection, pause, resume, and deletion;
- grabber: single-page discovery, filtering, selection, and transfer;
- bulk: recursive discovery, progress, cancellation, and transfer.

The split follows behavior boundaries while keeping the shared main-window state
explicit. UI construction helpers live in `udm.ui.tabs`.

## Dependency Direction

```text
entry point -> application -> main window -> dialogs/tabs/workers/services
                                      |
                                      -> configuration -> constants
```

Constants and configuration do not import UI modules. Workers do not import the
main window. Dialogs return data and do not persist it themselves. This keeps
lower-level modules reusable and prevents circular imports.

## Verification Strategy

- Compile every maintained Python module.
- Unit test configuration merging and category routing with temporary paths.
- Unit test spider extraction and worker state without external network access.
- Construct dialogs and the main window with Qt's offscreen platform.
- Verify all four tabs, scheduler date/time fields, toolbar actions, and clean
  application shutdown.
- Launch the compatibility entry point in an offscreen smoke test and confirm it
  remains alive until intentionally closed.
