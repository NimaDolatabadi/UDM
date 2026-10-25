# Torrents

UDM downloads BitTorrent content natively through libtorrent (the
`libtorrent` Python bindings, rasterbar libtorrent 2.x). No external client is
needed.

## Adding Torrents

- **Torrents tab**: paste a magnet link and press Add Magnet (or Return), or
  click Load .torrent and choose one or more files.
- **Drag and drop**: drop a magnet link or `.torrent` files on the window.
- **Clipboard monitor**: when enabled in Options, a copied magnet link is
  offered like a copied file link.
- **Other apps (DMG install)**: `UDM.app` registers the `magnet` URL scheme and
  the `.torrent` document type, so clicking a magnet link in a browser or
  opening a torrent from Finder adds it to the running UDM. macOS asks which
  app to use the first time; choose UDM.

Content is saved to the category folder for `.torrent` files, `Torrents` by
default (`~/Downloads/Torrents/`). Adding a torrent already in the list only
shows a notice.

## Controlling Torrents

The shared toolbar actions apply to selected rows when the Torrents tab is
active: Pause, Resume, Delete (removes the transfer and keeps downloaded files),
and Delete Completed. Stop All also pauses every torrent. The table shows name,
downloaded and total size, status with percentage, time left, download speed,
and peers, seeds, and upload speed.

Finished torrents are marked Completed, announced in the tray, and paused, so
UDM does not keep seeding in the background.

## Persistence

Each torrent's resume data is written to
`~/Library/Application Support/UDM/torrents/<info-hash>.resume` when it is
added, paused, and when UDM quits. On the next launch UDM restores them with
their progress and paused state. The torrent session, and therefore its peer
ports, starts only when saved torrents exist or a torrent is added.

## Modules

| Module | Responsibility |
| ------ | -------------- |
| `udm/torrent/engine.py` | Qt-free libtorrent session: add, pause, resume, remove, snapshots, resume files |
| `udm/torrent/status.py` | `TorrentSnapshot` and status labels, independent of libtorrent |
| `udm/ui/window_torrents.py` | Torrents tab controller, refresh timer, completion notices |
| `udm/ui/open_events.py` | macOS open events for magnet links and `.torrent` files |

The engine listens on port 6881 and enables DHT, local peer discovery, UPnP,
and NAT-PMP. Unreachable trackers and failed port mappings are logged at debug
level because peers usually arrive through DHT anyway.

## Limits

- Use torrents only for content you are allowed to download and share.
- The libtorrent wheel targets macOS 15 or later, which sets the app's minimum
  macOS version.

## Future Work

- TODO: Options for seeding after completion, port, and speed limits.
- TODO: Per-file selection inside multi-file torrents.
