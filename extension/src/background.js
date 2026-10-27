/* Background wiring: download capture, media detection, menus, and messages. */
"use strict";

// Chromium loads this file alone as a service worker; Firefox lists the
// helper scripts in the manifest, where importScripts does not exist.
if (typeof importScripts === "function" && typeof sendToUdm === "undefined") {
  importScripts("common.js", "media.js", "downloads.js");
}

const ICON = "icons/icon-128.png";

installDownloadCapture();

api.webRequest.onHeadersReceived.addListener(
  (details) => {
    if (details.tabId < 0 || !isHttpUrl(details.url)) return;
    const media = classifyResponse(details.url, details.responseHeaders);
    if (media) recordMedia(details.tabId, { url: details.url, ...media });
  },
  { urls: ["<all_urls>"], types: ["media", "xmlhttprequest", "other"] },
  ["responseHeaders"],
);

api.tabs.onRemoved.addListener((tabId) => clearTabMedia(tabId));
api.tabs.onUpdated.addListener((tabId, change) => {
  if (change.status === "loading" && change.url) clearTabMedia(tabId);
});

async function createMenus() {
  await api.contextMenus.removeAll();
  const menus = [
    { id: "udm-link", title: "Download link with UDM", contexts: ["link"] },
    { id: "udm-link-video", title: "Download video from link with UDM", contexts: ["link"] },
    { id: "udm-media", title: "Download media with UDM", contexts: ["video", "audio"] },
    { id: "udm-page", title: "Download video on this page with UDM", contexts: ["page"] },
  ];
  for (const menu of menus) api.contextMenus.create(menu);
}

api.runtime.onInstalled.addListener(createMenus);
api.runtime.onStartup.addListener(createMenus);

api.contextMenus.onClicked.addListener(async (info, tab) => {
  const page = { referrer: info.pageUrl ?? tab?.url ?? "", title: tab?.title ?? "" };
  let request = null;
  if (info.menuItemId === "udm-link") {
    request = await buildRequest("download", info.linkUrl, { referrer: page.referrer });
  } else if (info.menuItemId === "udm-link-video") {
    request = await buildRequest("stream", info.linkUrl, { referrer: page.referrer });
  } else if (info.menuItemId === "udm-media") {
    request = await mediaRequest(info.srcUrl, page);
  } else if (info.menuItemId === "udm-page") {
    request = await buildRequest("stream", page.referrer, { title: page.title });
  }
  if (request) notify(await sendToUdm(request), request);
});

/* Direct media files download as files; blob and manifest sources go to yt-dlp. */
async function mediaRequest(source, page) {
  if (isHttpUrl(source) && !/\.(m3u8|mpd)(\?|$)/i.test(source)) {
    return buildRequest("download", source, { referrer: page.referrer });
  }
  if (isHttpUrl(source)) {
    return buildRequest("stream", source, { referrer: page.referrer, title: page.title });
  }
  return buildRequest("stream", page.referrer, { title: page.title });
}

function notify(reply, request) {
  api.notifications.create({
    type: "basic",
    iconUrl: ICON,
    title: !reply.ok
      ? "UDM could not take this link"
      : reply.pending ? "Sent to UDM - choose where to save" : "Added to the UDM download list",
    message: reply.ok ? (request.title || request.url) : reply.error,
  });
}

api.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // The popup names its tab; content scripts are identified by their sender.
  const tabId = message?.tabId ?? sender.tab?.id;
  if (message?.type === "getMedia") {
    loadTabMedia(tabId).then((list) => sendResponse([...list]));
    return true;
  }
  if (message?.type === "capture") {
    captureFromPage(message.request).then(sendResponse);
    return true;
  }
  if (message?.type === "formats") {
    formatsForPage(message.request).then(sendResponse);
    return true;
  }
  if (message?.type === "clearMedia") {
    clearTabMedia(tabId).then(() => sendResponse(true));
    return true;
  }
  return false;
});

/* Send a request chosen in the on-video panel, accepting only HTTP links. */
async function captureFromPage(request) {
  if (!request || !["download", "stream"].includes(request.type) || !isHttpUrl(request.url)) {
    return { ok: false, error: "This video source cannot be downloaded." };
  }
  return sendToUdm(await buildRequest(request.type, request.url, {
    referrer: request.referrer ?? "",
    title: request.title ?? "",
    quality: request.quality ?? "",
  }));
}

/* Ask UDM which qualities a page or stream offers (resolved by yt-dlp). */
async function formatsForPage(request) {
  if (!request || !isHttpUrl(request.url)) {
    return { ok: false, error: "This video source cannot be downloaded." };
  }
  return sendToUdm(await buildRequest("formats", request.url, {
    referrer: request.referrer ?? "",
    title: request.title ?? "",
  }));
}
