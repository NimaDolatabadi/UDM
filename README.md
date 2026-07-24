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
- **Download Scheduler**: Stores date ranges, time windows, recurrence, and
  concurrency limits.
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
|   `-- ui/              # Dialogs, tabs, window controllers, and styles
|-- tests/               # Automated unit and offscreen UI tests
|-- docs/architecture.md # Architecture and schedule record
|-- udm_config.json      # Local user settings
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

## Project Status & Roadmap

### Current Capabilities

- Multi-threaded downloads with a single-stream fallback.
- Recursive domain crawling with progress and cancellation.
- Filterable site media extraction.
- Configurable file routing.
- System tray controls and completion notifications.
- Persistent proxy, DNS, segment, startup, category, schedule, and language
  settings.
- Cross-platform dark interface styling.

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
