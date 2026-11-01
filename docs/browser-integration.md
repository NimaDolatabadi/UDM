# Browser Integration

UDM Capture is a WebExtension that sends browser downloads and playing videos
to UDM. It works in Chromium-based browsers (Chrome, Edge, Brave, Vivaldi,
Opera, Arc, Chromium), Firefox, and Safari, from one shared source tree.

## What It Does

- **Download capture**: clicking a download link hands the file to UDM with
  the page's cookies, referrer, and user agent before the browser shows its
  save dialog. Firefox claims the response itself in a blocking
  `webRequest.onHeadersReceived` listener for page and frame loads that carry
  `Content-Disposition: attachment` or a content type the browser cannot
  display, and cancels the request once UDM accepts it; a tab opened only for
  the download is closed. Chromium decides in `downloads.onDeterminingFilename`,
  which runs before the Save As dialog, and cancels the download once UDM
  accepts it. Downloads Firefox reports only after they start (for example,
  from scripts or POST forms) are paused, offered to UDM, and cancelled on
  acceptance. When UDM is unreachable or refuses a link, the browser handles
  the download normally and the link is not offered again for 30 seconds.
  Safari has no downloads API, so `links.js` claims left clicks on links that
  carry a `download` attribute or end in a file extension from
  `DOWNLOAD_EXTENSIONS`. If UDM refuses or is unreachable, the click is
  replayed and Safari downloads the file.
- **Media detection**: network responses are inspected for HLS (`.m3u8`) and
  DASH (`.mpd`) manifests and for video or audio files. Segments and byte-range
  fragments are ignored. Results are listed per tab with a toolbar badge.
- **On-video button**: a small Download button appears at the top-right of any
  playing or hovered video (at least 200 by 120 pixels). Its panel offers the
  page's video, the element's direct file, and every stream detected on the
  tab. Choosing the page video or a stream lists the qualities yt-dlp finds
  (for example 1080p, 720p, 480p, and Audio only, with approximate sizes)
  before anything is sent. It follows the video into fullscreen when the browser
  allows and can be hidden per video or disabled in the popup.
- **Context menus**: download a link, a video behind a link, a media element,
  or the video on the current page.
- **Popup**: connection status, the capture and on-video toggles, a page
  download button that opens the same quality list, and the detected media
  list.
- **Ask where and when**: each captured link or video opens UDM's New
  Download prompt with the save folder, Start Now, Download Later, and Cancel.
  With Options > Downloads > Ask where to save each new download turned off,
  captured links join the download list paused, like Download Later, unless
  Start captured downloads immediately is on.

## Architecture

```text
browser extension --(native messaging, stdio)--> native host process
native host --(Unix socket or Windows named pipe, JSON lines)--> running UDM app (BridgeServer)
UDM app --> DownloadWorker (direct files) or StreamWorker (yt-dlp + FFmpeg)
```

| Module | Responsibility |
| ------ | -------------- |
| `extension/src/common.js` | API handle, settings, native messaging, cookie capture |
| `extension/src/media.js` | Response classification and per-tab media storage |
| `extension/src/downloads.js` | Download capture before the browser prompts |
| `extension/src/background.js` | Media listener, menus, and message routing |
| `extension/src/overlay*.js` | On-video button and panel in a closed Shadow DOM |
| `extension/src/popup.*` | Toolbar popup |
| `extension/src/links.js` | Safari only: clicked file links |
| `extension/safari/*.swift` | Safari app extension handler and containing app |
| `udm/bridge/protocol.py` | Native framing and the app socket protocol |
| `udm/bridge/native_host.py` | Host process; launches UDM when it is closed |
| `udm/bridge/server.py` | Qt socket server and single-instance detection |
| `udm/bridge/browsers.py` | Supported browsers and their host locations per platform |
| `udm/bridge/browser_detect.py` | Installed-browser detection and platform open commands |
| `udm/bridge/host_registration.py` | Host wrapper and manifests, written or repaired at launch |
| `udm/bridge/windows_hosts.py` | Windows registry entries for host manifests |
| `udm/bridge/connection_status.py` | Last extension contact per engine, for Options > Browser |
| `udm/bridge/extension_build.py` | Per-engine extension assembly and IDs |
| `udm/bridge/extension_package.py` | Standalone `.zip` and `.xpi` release files |
| `udm/bridge/installer.py` | Developer install: builds the extension and registers the host |
| `udm/bridge/safari.py` | Builds, signs, and registers `UDM Capture.app` |
| `udm/capture.py` | Validation of incoming requests |
| `udm/workers/stream.py` | yt-dlp transfers with pause, cancel, and cleanup |

The host is the UDM executable started with `--native-messaging-host`. That
flag is handled in `MACDM.py` before Qt is imported, so the host starts quickly
and writes only protocol frames to stdout. When UDM is not running, the host
starts it (`open UDM.app` for the bundle) and waits up to 20 seconds.

The socket is `bridge.sock` in the data directory. If that path exceeds the
macOS Unix-socket limit, both processes derive the same short name in the
system temporary directory instead. On Windows, where Qt's local server uses
named pipes and Python has no Unix sockets, the app listens on
`\\.\pipe\udm-<hash of the data directory>` and the native host opens that
pipe as a file (`protocol.exchange_over_pipe`). When UDM is closed, the host
starts it detached; on Windows it also leaves the browser's job object when
allowed, so UDM keeps running after the browser ends the host.

### Messages

Every request is one JSON object. The app answers `{"ok": true}` or
`{"ok": false, "error": "..."}`.

| `type` | Fields | Effect |
| ------ | ------ | ------ |
| `ping` | none | Reports `running`, `version`, `protocol`, and `minProtocol` |
| `show` | none | Raises the main window |
| `download` | `url`, `referrer`, `cookies`, `userAgent`, `filename` | Queues a direct HTTP download |
| `stream` | `url`, `referrer`, `cookies`, `cookieJar`, `userAgent`, `title`, `quality` | Queues a yt-dlp download of a page or manifest |
| `formats` | `url`, `referrer`, `cookies`, `cookieJar`, `userAgent` | Lists qualities; answered by the native host itself |

Capture replies include `pending: true` when the New Download prompt opened,
and otherwise `paused`. The app replies before the user answers the prompt,
because the native host waits only 2 seconds. `quality` is `best`, `audio`, or a height
such as `720p`; empty uses the Options default. `cookieJar` carries each
cookie's domain, path, and flags so yt-dlp scopes them correctly.

The native host answers `formats` itself with `udm.workers.format_probe`
(about 3 seconds for YouTube), so listing qualities neither blocks nor starts
the desktop app. Safari's handler cannot run Python, so it forwards `formats`
to the app, which probes on a worker thread (`BridgeServer` `background`
handlers) and replies when done. Sizes are reported by the site or estimated from bitrate and
duration.

`CaptureRequest.from_message` accepts only HTTP and HTTPS URLs, string fields
up to 64 KB, and header fields without line breaks.

### Protocol Version

The message formats have their own version, separate from the app and
extension versions: `PROTOCOL_VERSION` and `MIN_PROTOCOL_VERSION` in
`udm/bridge/protocol.py`, mirrored in `extension/src/common.js`. The current
protocol is **1**. Messages and replies without these fields come from
releases before versioning (UDM 0.11.0 and earlier), which speak version 1.

The extension adds these fields to every message:

| Field | Meaning |
| ----- | ------- |
| `protocol` | The extension's protocol version |
| `minProtocol` | The oldest UDM protocol it accepts |
| `extensionVersion` | The extension's manifest version |
| `engine` | `chromium`, `firefox`, or `safari`, from the extension URL scheme |

Every `ping` reply carries UDM's `protocol` and `minProtocol`, including the
reply the native host (or the Safari handler, from its Info.plist) sends when
UDM is closed. The popup compares them on open and shows "Update needed" with
"Update UDM" or "Update the extension". UDM refuses capture and `formats`
requests from an extension older than `MIN_PROTOCOL_VERSION` with
`{"ok": false, "incompatible": true, "error": "..."}`, which names the side to
update. Bump `PROTOCOL_VERSION` when a message changes shape, and raise the
minimum only when older peers can no longer be served.

### Connection Status

Native messaging lets only the extension start a conversation, so UDM cannot
ask a browser whether the extension is installed. Instead, the native host
records every message that carries an `engine` in
`<data dir>/extension-status.json` (the app records Safari's, which arrive
without a host). The extension pings at browser start and whenever the popup
opens. Options > Browser shows the latest contact for the selected browser's
engine, such as "UDM Capture 0.12.0 last connected 5 minutes ago". One build
serves every Chromium browser, so their contacts are reported together.

## Getting the Extension

Options > Browser (`udm/ui/options_browser_page.py`) is organized around
getting the extension rather than building it:

- **Status** shows the last contact for the selected browser, with Check
  Again.
- **Get UDM Capture...** opens the browser's store listing (`Browser.store_url`)
  or, until listings exist, the latest GitHub release, which carries the
  standalone extension files. For Safari the button is Install for Safari...,
  because Safari's extension is built on the Mac (see below).
- **Developers > Install from Source...** keeps the build-and-load flow for
  work on the extension itself.

### Release Files

`python -m udm.bridge.extension_package dist` writes the standalone files
with `extension_build.build_extension`, so they match what Install from Source
writes for the same version:

| File | Browsers |
| ---- | -------- |
| `udm-capture-chromium-<version>.zip` | Chrome, Edge, Brave, Vivaldi, Opera, Arc, Chromium |
| `udm-capture-firefox-<version>.xpi` | Firefox (unsigned) |

The archives are reproducible (sorted entries, fixed timestamps). Release
builds attach both (`.github/workflows/release.yml`), and pull requests that
change the extension upload them as workflow artifacts
(`.github/workflows/extension.yml`). The Chromium archive keeps the manifest
`key`, so an unpacked copy has the fixed development ID; the Chrome Web Store
rejects `key` and assigns its own ID, which must then be added to
`host_registration.CHROMIUM_STORE_IDS`. Until the stores and signing in
issue #16 are set up, both files still load only as developer extensions.

### Automatic Host Registration

The host manifest is the part of installation only the app can do, so UDM
writes it at every launch (`host_registration.sync_all`, called from
`udm/app.py`), whichever way the extension was installed. For each browser
detected on this computer it writes the host wrapper and
`com.udm.capture.json`, authorizing only the UDM extension IDs (the
development IDs plus any store IDs). Files and registry values that already
match are left untouched; stale ones, for example after UDM moved or updated,
are rewritten. For browsers that are not detected, existing UDM manifests are
repaired and nothing new is created. Failures are logged per browser.

| Platform | Wrapper | Manifest location | Detection |
| -------- | ------- | ----------------- | --------- |
| macOS | `<data>/native-host/udm-native-host` | `~/Library/Application Support/<browser>/NativeMessagingHosts/` | `/Applications`, `~/Applications` |
| Linux | `<data>/native-host/udm-native-host` | `~/.config/<browser>/NativeMessagingHosts/`, `~/.mozilla/native-messaging-hosts/` | Executable on `PATH` |
| Windows | `<data>\native-host\udm-native-host.bat` | `<data>\native-host\<engine>\com.udm.capture.json`, referenced from `HKCU\Software\<browser>\NativeMessagingHosts\com.udm.capture` | Program Files, Local AppData |

Per-browser folders and registry keys are listed in `udm/bridge/browsers.py`.
Opera and Arc document no location of their own, so Google Chrome's is
written as well; on Windows, Brave and Vivaldi get both their own key and
Chrome's.

### Installing From Source (Developers)

Options > Browser > Install from Source... opens a confirmation dialog
(`udm/ui/extension_install_dialog.py`) that lists what will be written and
opened, with the target folder; nothing changes until the user clicks
Install. UDM then:

1. builds the unpacked extension into `<data>/extension/<chromium|firefox>/`;
2. registers the host as above;
3. reveals the extension folder in the file manager and opens the browser's
   extensions page, then lists the remaining steps.

Browsers do not allow applications to add extensions silently, so the final
step is manual:

- **Chromium browsers**: open the extensions page, enable Developer mode,
  click Load unpacked, and choose the extension folder. The manifest carries a
  fixed public key, so the unpacked extension ID is always
  `himmjkpdagijcljpofjkgoagloapginc`.
- **Firefox**: open `about:debugging#/runtime/this-firefox`, click Load
  Temporary Add-on, and choose `manifest.json`. Firefox removes temporary
  add-ons when it quits. A permanent install requires signing through
  addons.mozilla.org, or Firefox Developer Edition or Nightly with
  `xpinstall.signatures.required` set to `false`. If Firefox withholds site
  access, use the Allow access button in the popup.

After updating UDM, install again and click Reload on the extension card.

### Safari

Safari has no native-messaging hosts. It loads web extensions from an app
extension inside an app, and delivers `runtime.sendNativeMessage` to that app
extension. Installing for Safari therefore writes
`~/Library/Application Support/UDM/safari/UDM Capture.app`:

- `Contents/PlugIns/UDM Capture Extension.appex` holds the web extension
  (built with `manifest.safari.json`) in `Resources/` and the Swift handler
  `extension/safari/SafariWebExtensionHandler.swift`. The handler does the
  native host's job: it forwards each message to the bridge socket and opens
  UDM through Launch Services when it is closed. Its Info.plist records the
  socket path (`UDMBridgeSocket`) and the UDM bundle (`UDMAppPath`, empty for
  source runs, which must already be running).
- The containing app (`ContainerApp.swift`) only opens the extension in
  Safari's settings and quits.
- Both are ad hoc signed with the App Sandbox. The sandbox blocks Unix
  sockets outside the container, and no standard entitlement allows one, so
  the app extension carries a `temporary-exception.sbpl` rule naming only the
  bridge socket. The app extension is then registered with `pluginkit -a`.

Release builds ship the compiled Swift binaries (`build_dmg.sh` compiles them
into `safari-bin`). Source runs compile them with `xcrun swiftc`, which needs
the Xcode Command Line Tools.

The extension is unsigned by Apple, so Safari loads it only with Settings >
Developer > Allow unsigned extensions, which Safari turns off when it quits.
Safari also lacks `downloads`, `notifications`, and, for non-persistent
background scripts, possibly `webRequest`; the scripts check for each.
Without `webRequest`, the on-video button still offers the page video.

## Stream Downloads

`StreamWorker` runs yt-dlp with the captured headers and cookies, the
Options > Network proxy, and up to 16 concurrent fragments (the Connections
per file setting). The quality chosen in the browser wins; otherwise Options >
Downloads > Video quality sets the default (Best, 1080p, 720p, 480p, or Audio Only). Within a resolution
H.264 video and AAC audio are preferred so files play in QuickTime and Finder.
YouTube requires solving JavaScript challenges, which yt-dlp does with the
Deno runtime (the `deno` wheel, bundled in the app) and the `yt-dlp-ejs`
scripts. HTTPS is verified through the macOS trust store (`truststore`), which
matches browser behavior for servers that send incomplete certificate chains. Video
and audio are merged to MP4 with the FFmpeg binary shipped by
`imageio-ffmpeg`, falling back to a system `ffmpeg`. Files are written to the
Videos category as `<title> [<id>].<ext>`. Pausing holds the transfer at the
next progress callback; cancelling removes `.part`, `.ytdl`, and fragment files.

## Limits

- DRM-protected services (Widevine, FairPlay, PlayReady) such as Netflix,
  Disney+, Prime Video, and Spotify cannot be downloaded, and UDM does not try
  to circumvent protection.
- Sites may forbid downloading in their terms of service; users are
  responsible for what they download.
- Some signed stream URLs expire quickly; send them to UDM promptly.
- Overlay buttons cannot appear inside a video element that is itself in
  fullscreen, because the browser renders no other content there.
- Until the extension is in the browser stores and signed (issue #16), every
  install path still ends in a developer install: Chromium browsers need
  Developer mode, Firefox removes the temporary add-on when it quits, and
  Safari needs Allow unsigned extensions after every restart.
- Windows and Linux host registration is covered by unit tests but has not
  yet been verified against real browsers on those systems. Linux detection
  checks `PATH` only, so Flatpak and Snap browsers, which also keep their
  settings in sandboxed folders, are not registered.

## Future Work

Issue #16 tracks the steps that need the project owner's accounts:

- TODO: Publish to the Chrome Web Store, Edge Add-ons, and addons.mozilla.org,
  then set each `Browser.store_url` and add the store-assigned Chromium IDs to
  `host_registration.CHROMIUM_STORE_IDS`. Issue #16.
- TODO: Sign the Safari app with a Developer ID and distribute it, so Safari
  keeps the extension enabled without Allow unsigned extensions. Issue #16.
