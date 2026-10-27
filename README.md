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
- **Browser Extension (UDM Capture)**: Chrome, Edge, Brave, Vivaldi, Opera,
  Arc, Chromium, Firefox, and Safari. Captures browser downloads with their cookies,
  detects HLS, DASH, and media files on any page, and adds an IDM-style
  Download button at the top-right of playing videos. Install it from
  Options > Browser.
- **Streaming Video Downloads**: Pages and stream manifests (including
  YouTube, through a bundled Deno runtime) are resolved by yt-dlp and merged
  with a bundled FFmpeg. Pick the quality from a list in the browser, then
  choose the save folder and Start Now or Download Later in UDM. DRM protected
  services are not supported.
- **New Download Prompt and Progress Bars**: Each link or video you send to
  UDM opens a prompt with the file name, save folder, Start Now, Download
  Later, and Cancel. Every row in the download list shows a progress bar.
- **Native Torrents**: Magnet links and `.torrent` files download through
  libtorrent in the Torrents tab, with pause, resume, and progress that
  survives restarts. The app opens magnet links clicked in a browser.
- **Installers for macOS, Windows, and Linux**: GitHub releases ship a macOS
  DMG, a Windows installer and portable zip, and Linux `.deb`, `.rpm`, and
  Arch Linux packages.
- **Multi-Language Support**: Includes English, Persian, Russian, French, and
  Italian.

---

## Project Structure

```text
UDM/
|-- MACDM.py             # Entry point (GUI or --native-messaging-host)
|-- udm/                 # Modular application package
|   |-- app.py           # QApplication lifecycle and single instance
|   |-- config.py        # Settings and category routing
|   |-- paths.py         # Data, log, socket, and resource locations
|   |-- startup.py       # OS startup integration
|   |-- bridge/          # Browser extension bridge and installer
|   |-- torrent/         # libtorrent session and torrent status
|   |-- workers/         # Download, stream (yt-dlp), and spider threads
|   `-- ui/              # Dialogs, tabs, window controllers, and theme package
|-- extension/           # UDM Capture browser extension source
|-- packaging/           # PyInstaller spec and per-platform package scripts
|-- .github/workflows/   # CI tests and the release build
|-- tests/               # Automated unit and offscreen UI tests
|-- docs/                # Architecture, design system, browser, packaging
|-- udm_config.json      # Local settings, created on first run (untracked)
`-- logo.png             # Window and tray icon
```

---

## Installation & Setup

### Option A: Download a Release

Download the package for your system from the
[Releases page](https://github.com/NimaDolatabadi/UDM/releases):

* **macOS 15 or later**: `UDM-<version>-macos-arm64.dmg` (Apple silicon) or
  `-macos-x86_64.dmg` (Intel). Open it and drag UDM into Applications. The
  build is not notarized, so Control-click UDM and choose Open on first launch.
* **Windows 10 or later**: `UDM-<version>-windows-x64-setup.exe`, or the
  portable `.zip`.
* **Debian and Ubuntu**: `sudo apt install ./udm_<version>_amd64.deb`
* **Fedora and RHEL**: `sudo dnf install ./udm-<version>-1.x86_64.rpm`
* **Arch Linux**: `sudo pacman -U ./udm-<version>-1-x86_64.pkg.tar.xz`

The browser extension installer is currently macOS-only. See
`docs/packaging.md` to build the packages yourself.

### Option B: From Source

### Prerequisites

* Python 3.10 or higher installed on your system.

### 1. Clone the Repository

```bash
git clone https://github.com/NimaDolatabadi/UDM.git
cd UDM

```

### 2. Install Dependencies

Install PyQt6, Requests, BeautifulSoup, yt-dlp (with `yt-dlp-ejs`),
imageio-ffmpeg (FFmpeg), deno (the JavaScript runtime YouTube needs),
truststore (macOS certificate verification), and libtorrent (torrents) via pip:

```bash
pip install -r requirements.txt

```

### 3. Run the Application

Launch the app. Settings and logs are stored in
`~/Library/Application Support/UDM/` on macOS:

```bash
python MACDM.py

```

### 4. Install the Browser Extension

Open Options > Browser, choose your browser, and click Install Extension, then
follow the steps shown:

- **Chrome, Edge, Brave, Vivaldi, Opera, Arc, Chromium**: on the extensions
  page enable Developer mode, click Load unpacked, and choose the folder UDM
  revealed in Finder.
- **Firefox**: open `about:debugging#/runtime/this-firefox`, click Load
  Temporary Add-on, and choose `manifest.json` in that folder. Firefox removes
  temporary add-ons when it quits.
- **Safari**: UDM writes `UDM Capture.app` and opens Safari's settings. Turn
  on Settings > Advanced > Show features for web developers, then Developer >
  Allow unsigned extensions (Safari turns this off when it quits), and enable
  UDM Capture in the Extensions tab. On Safari, clicked file links are sent to
  UDM instead of all browser downloads.

After updating UDM, install again and click Reload on the extension card.
Details and the message protocol are in `docs/browser-integration.md`.

### 5. Using the Extension

- Browser downloads are handed to UDM automatically and sorted into the
  category folders in `~/Downloads` (for example, `.dmg` files go to
  `Programs/Mac`).
- Hover or play a video to show the Download button at its top-right. Choose
  **This video** or a detected stream, then pick a quality (Best, 1080p, 720p,
  and so on, or Audio only) from the list with approximate sizes.
- Each captured item opens UDM's **New Download** prompt: pick the folder and
  press **Start Now** or **Download Later**, or **Cancel**. Turn the prompt
  off with Options > Browser > Ask where to save each new download; captured
  items then join the list paused unless Start captured downloads immediately
  is on.
- The toolbar popup shows the connection status, toggles, and every media
  stream detected on the current tab.

### 6. Downloading Torrents

Paste a magnet link in the Torrents tab and press Add Magnet, click Load
.torrent, or drop either on the window. Files are saved to
`~/Downloads/Torrents/`, and the toolbar Pause, Resume, and Delete actions work
on the selected torrents. With the DMG install, magnet links clicked in a
browser open in UDM. See `docs/torrents.md`.

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
UDM_DEV=1 conda run -n mine python MACDM.py
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
- Browser extension for Chromium browsers, Firefox, and Safari with download capture,
  stream detection, an on-video Download button, and quality selection.
- yt-dlp stream downloads (including YouTube) merged to MP4 with FFmpeg.
- Single-instance app that the browser can launch on demand.
- Release packages for macOS, Windows, and Linux built by GitHub Actions.
- Native magnet and `.torrent` downloads with resume across restarts.

### Future Development

- Torrent seeding, port, and per-file options.
- Store-published extensions, including a signed Safari version.
- Global and per-download speed limits.
- Queue ordering and sequential processing.
- Expanded secure proxy support.

## Tests

Run the complete test suite with Qt's offscreen platform:

```bash
QT_QPA_PLATFORM=offscreen conda run -n mine python -m unittest discover -v
```

Tests use a temporary data directory and never touch real settings.
