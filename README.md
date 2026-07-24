# UDM (Umbrella Download Manager)

A lightweight, high-performance, multi-threaded open-source download manager built using **Python** and **PyQt6**. Designed with an "umbrella" philosophy, UDM acts as a protective, covert shield for your data—handling bulk recursive web crawling, multi-segmented file transfers, categorization, and system tray integration seamlessly in the background.

---

## Features

* **Multi-Threaded & Chunked Downloads**: Splits files across multiple concurrent threads (`bytes=start-end`) to maximize bandwidth utilization and speed.
* **Pure Python Architecture**: Relies on robust libraries like `requests` and `BeautifulSoup4` for stable, self-contained operations without requiring external heavy daemon runtimes.
* **Bulk Recursive Spider**: Scans website directories recursively to discover and harvest target file types (e.g., `.zip`, `.pdf`, `.exe`, `.mp4`) automatically.
* **Site Grabber**: Scans web pages for media assets, links, and documents with instant keyword filtering.
* **Smart File Categorization**: Automatically detects file extensions and routes downloaded items into structured subdirectories (`Compressed`, `Documents`, `Videos`, `Programs`, etc.).
* **System Tray & Background Operation**: Supports minimizing to the system tray, running invisibly in the background, and closing directly to the tray without lingering dock footprints when configured.
* **Clipboard Monitor**: Automatically watches system clipboard events for downloadable links.
* **Download Scheduler**: Configure time-window rules and recurring download limits to manage network usage efficiently.
* **Multi-Language Support**: Fully localized interface supporting English, Persian, Russian, French, and Italian.

---

## Project Structure

```text
UDM/
├── UDM.py              # Main application entry point and UI controller
├── udm_config.json     # Local user settings and category maps (auto-generated)
├── download_manager.log# Runtime logging and error tracking
└── logo.png            # Application branding icon and system tray graphic

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
pip install PyQt6 requests beautifulsoup4

```

### 3. Run the Application

Ensure you have a `logo.png` file placed in the project root directory for window icons and system tray integration, then launch the app:

```bash
python UDM.py

```

---

## Project Status & Roadmap

### ✅ Current Capabilities

* **Multi-threaded Core Engine**: Dynamic fallback between single-thread and multi-segment parallel stream downloads.
* **Recursive Bulk Scraping**: Deep domain link traversal with live progress bars and individual abort controls.
* **Site Media Grabber**: Filterable web asset extraction table.
* **Smart Categorization Engine**: Automated file routing based on configurable extensions.
* **System Tray Integration**: Background running state, quick show/hide toggle, and tray notifications upon task completion.
* **Custom Configuration & Options**: Persistent settings for proxy support, DNS rules, segment counts, system startup behavior, and multi-language UI localization.
* **Robust UI Styling**: Modern dark-themed stylesheet optimized for cross-platform desktop usage.

### ☐ Future Development

* **Native Torrent & Magnet Support**: Integration with `libtorrent` for native peer-to-peer downloading directly inside the manager queue.
* **Browser Extension Bridge**: Local HTTP server implementation to seamlessly intercept browser clicks without manual URL copying.
* **Speed Limiting Controls**: Global and per-task bandwidth throttling algorithms.
* **Advanced Queue Prioritizing**: Drag-and-drop custom queue reordering and automatic sequential queue processing.
* **Encrypted Proxy Authentication**: Expanded support for secure SOCKS5 proxies and advanced credential managers.

