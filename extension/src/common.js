/* Shared helpers: browser API handle, settings, and the UDM native bridge. */
"use strict";

// Firefox exposes promise-based `browser`; Chromium exposes promise-capable
// `chrome` under Manifest V3. Both share the API surface used here.
const api = globalThis.browser ?? globalThis.chrome;
const NATIVE_HOST = "com.udm.capture";
const DEFAULT_SETTINGS = { captureDownloads: true, showOverlay: true };

async function getSettings() {
  const stored = await api.storage.local.get(DEFAULT_SETTINGS);
  return { ...DEFAULT_SETTINGS, ...stored };
}

async function saveSettings(changes) {
  await api.storage.local.set(changes);
}

/* Send one message to UDM through the native host and never throw. */
async function sendToUdm(message) {
  try {
    const reply = await api.runtime.sendNativeMessage(NATIVE_HOST, message);
    return reply ?? { ok: false, error: "No reply from UDM" };
  } catch (error) {
    return {
      ok: false,
      hostMissing: true,
      error: "UDM is not connected. Install the extension from UDM Options.",
      detail: String(error?.message ?? error),
    };
  }
}

/* Return the browser's cookies for a URL, or an empty list. */
async function cookiesFor(url) {
  try {
    return await api.cookies.getAll({ url });
  } catch (error) {
    return [];
  }
}

/*
 * Build a capture message carrying the session UDM needs to fetch the URL.
 * `cookies` is a header for direct downloads; `cookieJar` keeps each cookie's
 * domain and path for yt-dlp. `quality` is "best", "audio", or e.g. "720p".
 */
async function buildRequest(type, url, extra = {}) {
  const cookies = await cookiesFor(url);
  return {
    type,
    url,
    referrer: extra.referrer ?? "",
    title: extra.title ?? "",
    filename: extra.filename ?? "",
    quality: extra.quality ?? "",
    cookies: cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join("; "),
    cookieJar: cookies.map((cookie) => ({
      name: cookie.name,
      value: cookie.value,
      domain: cookie.domain,
      path: cookie.path,
      secure: cookie.secure,
      hostOnly: cookie.hostOnly,
      expirationDate: cookie.expirationDate ?? null,
    })),
    userAgent: navigator.userAgent,
  };
}

function isHttpUrl(url) {
  return typeof url === "string" && /^https?:\/\//i.test(url);
}

function baseName(path) {
  return (path ?? "").split(/[\\/]/).pop() ?? "";
}

function formatBytes(bytes) {
  if (!bytes) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)} ${units[unit]}`;
}
