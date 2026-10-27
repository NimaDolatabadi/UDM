/* Download capture: hand browser downloads to UDM before the browser prompts. */
"use strict";

// Content types a browser renders in the tab. Anything else is a download.
const DISPLAYABLE_TYPE = new RegExp(
  "^(text/|image/|audio/|video/|multipart/|application/(xhtml\\+xml|xml|json|pdf"
  + "|javascript|ecmascript|x-javascript|rss\\+xml|atom\\+xml|wasm|signed-exchange)"
  + "|.*\\+(xml|json)$)",
  "i",
);
// URLs UDM refused recently; the browser keeps them so they are not offered twice.
const PASSED_TO_BROWSER = new Set();
const PASS_THROUGH_MS = 30000;

/* Return true when a frame response would make the browser start a download. */
function isDownloadResponse(headers) {
  const disposition = headerValue(headers, "content-disposition").trim();
  if (/^attachment/i.test(disposition)) return true;
  const type = headerValue(headers, "content-type").split(";")[0].trim();
  return type !== "" && !DISPLAYABLE_TYPE.test(type);
}

/* Read the file name from Content-Disposition, preferring the RFC 5987 form. */
function dispositionFilename(headers) {
  const value = headerValue(headers, "content-disposition");
  const encoded = value.match(/filename\*\s*=\s*[^']*'[^']*'([^;]+)/i);
  if (encoded) {
    try {
      return baseName(decodeURIComponent(encoded[1].trim()));
    } catch (error) {
      // Fall through to the plain parameter.
    }
  }
  const plain = value.match(/filename\s*=\s*("([^"]*)"|[^;]+)/i);
  return baseName((plain?.[2] ?? plain?.[1] ?? "").trim());
}

function passToBrowser(url) {
  PASSED_TO_BROWSER.add(url);
  setTimeout(() => PASSED_TO_BROWSER.delete(url), PASS_THROUGH_MS);
}

/* Offer one download to UDM; true means UDM took it and the browser must not. */
async function offerToUdm(url, extra) {
  if (!isHttpUrl(url) || PASSED_TO_BROWSER.has(url)) return false;
  if (!(await getSettings()).captureDownloads) return false;
  const reply = await sendToUdm(await buildRequest("download", url, extra));
  if (!reply.ok) passToBrowser(url);
  return reply.ok;
}

/* Firefox: claim the response itself, so no download or prompt ever starts. */
async function captureResponse(details) {
  if (details.method !== "GET" || details.statusCode < 200 || details.statusCode >= 300) {
    return {};
  }
  if (!isDownloadResponse(details.responseHeaders)) return {};
  const taken = await offerToUdm(details.url, {
    referrer: details.originUrl ?? details.documentUrl ?? "",
    filename: dispositionFilename(details.responseHeaders),
  });
  if (!taken) return {};
  if (details.type === "main_frame") closeIfEmpty(details.tabId);
  return { cancel: true };
}

/* Close a tab that was opened only to receive the download. */
async function closeIfEmpty(tabId) {
  if (tabId < 0) return;
  const tab = await api.tabs.get(tabId).catch(() => null);
  if (tab && (!tab.url || tab.url === "about:blank")) api.tabs.remove(tabId).catch(() => {});
}

/* Chromium: decide before the Save As dialog; `suggest` releases the download. */
function captureBeforeFilename(item, suggest) {
  const url = item.finalUrl || item.url;
  offerToUdm(url, { referrer: item.referrer ?? "", filename: baseName(item.filename) })
    .then(async (taken) => {
      if (!taken) return suggest();
      await api.downloads.cancel(item.id).catch(() => {});
      await api.downloads.erase({ id: item.id }).catch(() => {});
    }, () => suggest());
  return true;
}

/* Fallback for downloads seen only once they exist (for example, from scripts). */
async function captureCreated(item) {
  const url = item.finalUrl || item.url;
  if (!isHttpUrl(url) || PASSED_TO_BROWSER.has(url)) return;
  // Pause first so the browser does not keep transferring while UDM answers.
  const paused = await api.downloads.pause(item.id).then(() => true, () => false);
  const taken = await offerToUdm(url, {
    referrer: item.referrer ?? "",
    filename: baseName(item.filename),
  });
  if (!taken) {
    if (paused) await api.downloads.resume(item.id).catch(() => {});
    return;
  }
  await api.downloads.cancel(item.id).catch(() => {});
  await api.downloads.erase({ id: item.id }).catch(() => {});
}

/*
 * Register the earliest capture point each browser offers. Chromium has
 * onDeterminingFilename but no blocking webRequest under Manifest V3;
 * Firefox has blocking webRequest but no onDeterminingFilename. Safari has
 * neither, so links.js sends clicked file links ("captureLink") instead.
 */
function installDownloadCapture() {
  if (!api.downloads) return;
  if (api.downloads.onDeterminingFilename) {
    api.downloads.onDeterminingFilename.addListener(captureBeforeFilename);
    return;
  }
  api.webRequest.onHeadersReceived.addListener(
    captureResponse,
    { urls: ["http://*/*", "https://*/*"], types: ["main_frame", "sub_frame"] },
    ["blocking", "responseHeaders"],
  );
  api.downloads.onCreated.addListener(captureCreated);
}
