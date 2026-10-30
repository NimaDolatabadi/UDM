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
native host --(Unix socket, JSON lines)--> running UDM app (BridgeServer)
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
| `udm/bridge/browsers.py` | Supported browsers and host-manifest locations |
| `udm/bridge/extension_build.py` | Per-engine extension assembly and IDs |
| `udm/bridge/installer.py` | Writes the extension, host wrapper, and manifests |
| `udm/bridge/safari.py` | Builds, signs, and registers `UDM Capture.app` |
| `udm/capture.py` | Validation of incoming requests |
| `udm/workers/stream.py` | yt-dlp transfers with pause, cancel, and cleanup |

The host is the UDM executable started with `--native-messaging-host`. That
flag is handled in `MACDM.py` before Qt is imported, so the host starts quickly
and writes only protocol frames to stdout. When UDM is not running, the host
starts it (`open UDM.app` for the bundle) and waits up to 20 seconds.

The socket is `bridge.sock` in the data directory. If that path exceeds the
macOS Unix-socket limit, both processes derive the same short name in the
system temporary directory instead.

### Messages

Every request is one JSON object. The app answers `{"ok": true}` or
`{"ok": false, "error": "..."}`.

| `type` | Fields | Effect |
| ------ | ------ | ------ |
| `ping` | none | Reports `running` and `version` |
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

## Installing

In UDM, open Options > Browser, choose a browser, and click Install
Extension. A confirmation dialog (`udm/ui/extension_install_dialog.py`) lists
what will be written and opened, with the target folder; nothing changes
until the user clicks Install. UDM then:

1. builds the unpacked extension into
   `~/Library/Application Support/UDM/extension/<chromium|firefox>/`;
2. writes the host wrapper `~/Library/Application Support/UDM/native-host/udm-native-host`;
3. writes `com.udm.capture.json` into the browser's `NativeMessagingHosts`
   directory, authorizing only the UDM extension ID;
4. reveals the extension folder in Finder and opens the browser's extensions
   page, then lists the remaining steps.

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
- Installing is a developer workflow: Chromium browsers need Developer mode,
  Firefox removes the temporary add-on when it quits, and Safari needs Allow
  unsigned extensions after every restart. Updates need a manual reinstall.
- Native-host registration and browser detection are macOS only, so the
  Browser page cannot connect the extension on Windows or Linux (#14).

## Future Work

The plan to ship the extension like a product is tracked in GitHub issue #16:
standalone release files (#10), automatic host registration on launch (#11),
a "Get the extension" flow on the Browser page (#12), a protocol version
check (#13), Windows and Linux support (#14), and pull-request builds of the
macOS app (#15).

- TODO: Publish to the Chrome Web Store, Edge Add-ons, and addons.mozilla.org,
  adding each store-assigned extension ID to the host manifest.
- TODO: Sign the Safari app with a Developer ID and distribute it, so Safari
  keeps the extension enabled without Allow unsigned extensions.
