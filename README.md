# UDM (Umbrella Download Manager)

A lightweight, multi-threaded open-source download manager built using Python
and PyQt6. UDM supports bulk recursive web crawling, segmented file transfers,
categorization, scheduling, and system tray integration.

---

## Features

- **Multi-Threaded and Chunked Downloads**: Splits files across multiple
  concurrent HTTP range requests.
- **Pure Python Architecture**: Uses `requests` and `BeautifulSoup4` without an
  external download daemon.
- **Bulk Recursive Spider**: Traverses same-domain pages to discover selected
  file types.
- **Site Grabber**: Finds media, documents, and downloadable links with filtering.
- **Smart File Categorization**: Routes downloads by configurable extension maps.
- **System Tray and Background Operation**: Supports hiding and closing to tray.
- **Clipboard Monitor**: Detects supported downloadable links.
- **Download Scheduler**: Enforces date ranges, time windows, recurrence, and
  per-queue concurrency limits.
- **Controlled Concurrency**: Exposes a global maximum of four simultaneous
  main-queue downloads in Options → Network; explicit schedules retain their
  own limits. The default Scheduler row directs configuration to the effective
  global setting instead of presenting an inert limit editor.
- **Custom DNS**: Resolves HTTP and HTTPS destinations through configured DNS
  servers while retaining hostname and certificate validation.
- **Multi-Language Support**: Includes English, Persian, Russian, French, and
  Italian.

---

## Project Structure

```text
UDM/
|-- MACDM.py             # Compatibility entry point
|-- udm/                 # Modular application package
|   |-- app.py           # QApplication lifecycle
|   |-- config.py        # Settings and category routing
|   |-- startup.py       # OS startup integration
|   |-- workers/         # Download and spider threads
|   `-- ui/              # Dialogs, tabs, window controllers, and theme package
|-- tests/               # Automated unit and offscreen UI tests
|-- docs/architecture.md # Architecture and schedule record
|-- udm_config.json      # Local settings, created on first run (untracked)
`-- logo.png             # Window and tray icon
```

---

## Installation & Setup

### Prerequisites

* Python 3.10 or higher installed on your system.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/UDM.git
cd UDM

```

### 2. Install Dependencies

Install the required PyQt6, Requests, and BeautifulSoup packages via pip:

```bash
pip install -r requirements.txt

```

### 3. Run the Application

Ensure you have a `logo.png` file placed in the project root directory for window icons and system tray integration, then launch the app:

```bash
python MACDM.py

```

---

## Theming

UDM ships a token-based design system with two themes, Refined Dark and Light,
plus a **System** option (the default) that follows the operating system's light
or dark appearance and switches live when the OS toggles. Choose a theme in
Options > General. The design system is documented in `docs/design-system.md`.

### Development style hot reload

When iterating on the interface, set the `UDM_DEV` environment variable to reload
styling live: editing any file under `udm/ui/theme/` re-applies the stylesheet and
icon colors to the running app without a restart. Structural layout changes still
require a restart.

```bash
UDM_DEV=1 .venv/bin/python MACDM.py
```

---

## Project Status & Roadmap

### Current Capabilities

- Multi-threaded downloads with a single-stream fallback.
- Recursive domain crawling with progress and cancellation.
- Filterable site media extraction.
- Configurable file routing.
- System tray controls and completion notifications.
- Runtime-enforced scheduling and configurable custom DNS resolution.
- Idempotent launch-time startup registration that repairs missing or stale
  platform entries without rewriting matching entries.
- Persistent proxy, segment, startup, category, schedule, and language settings.
- Token-based design system with Refined Dark, Light, and OS-following System
  themes, live theme switching, and matching line icons.

### Future Development

- Native torrent and magnet support.
- Browser extension integration.
- Global and per-download speed limits.
- Queue ordering and sequential processing.
- Expanded secure proxy support.

## Tests

Run the complete test suite with Qt's offscreen platform:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -v
```
