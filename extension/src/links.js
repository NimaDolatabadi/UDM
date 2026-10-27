/* Safari download capture: hand clicked file links to UDM. */
"use strict";

/*
 * Safari has no downloads API, so the background script never sees a
 * download start. This content script, loaded only by the Safari manifest,
 * claims clicks on links that point at files instead. When UDM refuses or is
 * unreachable, the click is replayed so Safari downloads the file itself.
 */
(() => {
  const ext = globalThis.browser ?? globalThis.chrome;
  // Matches DOWNLOAD_EXTENSIONS in udm/constants.py.
  const FILE_PATH = /\.(zip|rar|mp4|mp3|pdf|exe|dmg|pkg|iso|mkv|7z|gz|tar)$/i;
  const replaying = new WeakSet();

  function fileLink(event) {
    if (event.defaultPrevented || event.button !== 0) return null;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return null;
    const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
    if (!link || replaying.has(link) || !/^https?:$/.test(link.protocol)) return null;
    return link.hasAttribute("download") || FILE_PATH.test(link.pathname) ? link : null;
  }

  document.addEventListener("click", (event) => {
    const link = fileLink(event);
    if (!link) return;
    event.preventDefault();
    const message = {
      type: "captureLink",
      url: link.href,
      referrer: location.href,
      filename: link.getAttribute("download") ?? "",
    };
    ext.runtime.sendMessage(message).then((taken) => taken || replay(link), () => replay(link));
  }, true);

  function replay(link) {
    replaying.add(link);
    link.click();
    replaying.delete(link);
  }
})();
