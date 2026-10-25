/* Detects streaming manifests and media files in network responses per tab. */
"use strict";

const MEDIA_LIMIT = 50;
const MIN_FILE_BYTES = 512 * 1024;
// Accent token from docs/design-system.md, used for the toolbar badge.
const BADGE_COLOR = "#2f81f7";
const mediaByTab = new Map();

const MANIFEST_TYPES = {
  "application/vnd.apple.mpegurl": "hls",
  "application/x-mpegurl": "hls",
  "audio/mpegurl": "hls",
  "audio/x-mpegurl": "hls",
  "application/dash+xml": "dash",
};
// Segments and byte-range fragments are pieces of a stream, not downloads.
const SEGMENT_PATH = /\.(ts|m4s|m4f|m4v\.part|aac|vtt|webvtt|key)$/i;
const FRAGMENT_QUERY = /[?&](range|bytestart|byteend|sq|rn)=/i;

function headerValue(headers, name) {
  const header = (headers ?? []).find((item) => item.name.toLowerCase() === name);
  return header?.value ?? "";
}

/* Return the full resource size from Content-Range or Content-Length. */
function responseSize(headers) {
  const range = headerValue(headers, "content-range").match(/\/(\d+)$/);
  if (range) return Number(range[1]);
  return Number(headerValue(headers, "content-length")) || 0;
}

/* Classify a response as a stream manifest, a media file, or neither. */
function classifyResponse(url, headers) {
  let path;
  try {
    path = new URL(url).pathname.toLowerCase();
  } catch (error) {
    return null;
  }
  const type = headerValue(headers, "content-type").split(";")[0].trim().toLowerCase();
  const manifest = MANIFEST_TYPES[type]
    ?? (path.endsWith(".m3u8") ? "hls" : path.endsWith(".mpd") ? "dash" : null);
  if (manifest) return { kind: manifest, stream: true, size: 0 };
  if (SEGMENT_PATH.test(path) || FRAGMENT_QUERY.test(url) || type === "video/mp2t") {
    return null;
  }
  if (!type.startsWith("video/") && !type.startsWith("audio/")) return null;
  const size = responseSize(headers);
  if (size && size < MIN_FILE_BYTES) return null;
  return { kind: type.split("/")[1] || "media", stream: false, size };
}

async function loadTabMedia(tabId) {
  if (mediaByTab.has(tabId)) return mediaByTab.get(tabId);
  let list = [];
  // The Chromium service worker can restart; session storage keeps results.
  if (api.storage.session) {
    const stored = await api.storage.session.get(`tab:${tabId}`);
    list = stored[`tab:${tabId}`] ?? [];
  }
  mediaByTab.set(tabId, list);
  return list;
}

async function recordMedia(tabId, item) {
  const list = await loadTabMedia(tabId);
  if (list.some((existing) => existing.url === item.url)) return;
  list.push({ ...item, time: Date.now() });
  if (list.length > MEDIA_LIMIT) list.splice(0, list.length - MEDIA_LIMIT);
  await persistTab(tabId, list);
}

async function clearTabMedia(tabId) {
  mediaByTab.delete(tabId);
  if (api.storage.session) await api.storage.session.remove(`tab:${tabId}`);
  await updateBadge(tabId, 0);
}

async function persistTab(tabId, list) {
  if (api.storage.session) {
    await api.storage.session.set({ [`tab:${tabId}`]: list });
  }
  await updateBadge(tabId, list.length);
}

async function updateBadge(tabId, count) {
  try {
    await api.action.setBadgeBackgroundColor({ tabId, color: BADGE_COLOR });
    await api.action.setBadgeText({ tabId, text: count ? String(count) : "" });
  } catch (error) {
    // The tab may have closed between the request and the badge update.
  }
}
