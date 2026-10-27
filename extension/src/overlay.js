/* On-video download button: a floating control at the top-right of videos. */
"use strict";

(() => {
  const ext = globalThis.browser ?? globalThis.chrome;
  const MIN_WIDTH = 200;
  const MIN_HEIGHT = 120;
  const HIDE_DELAY_MS = 3000;
  const ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    + '<path d="M12 4 V14"/><path d="M8 11 L12 15 L16 11"/><path d="M5 18 H19"/></svg>';

  let enabled = true;
  let current = null;
  let hideTimer = null;
  const dismissed = new WeakSet();

  const host = document.createElement("udm-capture-overlay");
  const root = host.attachShadow({ mode: "closed" });
  root.innerHTML = `<style>${UDM_OVERLAY_CSS}</style>
    <div class="wrap">
      <div class="row">
        <button class="trigger" type="button">${ICON}<span>Download</span></button>
        <button class="close" type="button" title="Hide for this video">&times;</button>
      </div>
      <div class="panel" hidden></div>
    </div>`;
  const trigger = root.querySelector(".trigger");
  const closeButton = root.querySelector(".close");
  const panel = root.querySelector(".panel");

  function eligible(video) {
    const rect = video.getBoundingClientRect();
    return enabled && !dismissed.has(video)
      && rect.width >= MIN_WIDTH && rect.height >= MIN_HEIGHT;
  }

  function show(video) {
    if (!eligible(video)) return;
    if (current !== video) panel.hidden = true;
    current = video;
    const container = document.fullscreenElement ?? document.documentElement;
    if (host.parentNode !== container) container.appendChild(host);
    host.style.display = "block";
    position();
    scheduleHide();
  }

  function hide() {
    if (!panel.hidden) return;
    host.style.display = "none";
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, HIDE_DELAY_MS);
  }

  function position() {
    if (!current || host.style.display === "none") return;
    const rect = current.getBoundingClientRect();
    if (!current.isConnected || rect.width === 0) {
      host.style.display = "none";
      return;
    }
    host.style.top = `${Math.max(rect.top + 8, 8)}px`;
    host.style.right = `${Math.max(window.innerWidth - rect.right + 8, 8)}px`;
  }

  function videoAt(target) {
    if (target instanceof HTMLVideoElement) return target;
    // Players often cover the video with controls; find the video beneath.
    for (const video of document.querySelectorAll("video")) {
      if (video.parentElement?.contains(target)) return video;
    }
    return null;
  }

  async function openPanel() {
    panel.hidden = false;
    clearTimeout(hideTimer);
    panel.innerHTML = '<div class="message">Looking for downloadable media...</div>';
    let media = [];
    try {
      media = await ext.runtime.sendMessage({ type: "getMedia" });
    } catch (error) {
      media = [];
    }
    panel.replaceChildren();
    addItem("This video", "Choose a quality", {
      type: "stream", url: location.href, title: document.title,
    });
    const direct = current?.currentSrc;
    if (direct && /^https?:/i.test(direct)) {
      addItem(fileName(direct), "Direct video file", { type: "download", url: direct });
    }
    for (const item of media ?? []) {
      const label = item.stream ? `${item.kind.toUpperCase()} stream` : item.kind;
      addItem(fileName(item.url), [label, formatSize(item.size)].filter(Boolean).join(" - "), {
        type: item.stream ? "stream" : "download", url: item.url, title: document.title,
      });
    }
  }

  function addItem(name, meta, request) {
    const button = document.createElement("button");
    button.className = "item";
    button.type = "button";
    button.innerHTML = '<span class="name"></span><span class="meta"></span>';
    button.querySelector(".name").textContent = name;
    button.querySelector(".meta").textContent = meta;
    // Streams resolve through yt-dlp, so offer their qualities first.
    button.addEventListener("click", () => (
      request.type === "stream" && !request.quality ? chooseQuality(request) : send(request)
    ));
    panel.appendChild(button);
  }

  async function chooseQuality(request) {
    panel.replaceChildren();
    setMessage("Checking available qualities...", "");
    let reply;
    try {
      reply = await ext.runtime.sendMessage({
        type: "formats",
        request: { ...request, referrer: location.href },
      });
    } catch (error) {
      reply = { ok: false, error: "The extension was reloaded; refresh this page." };
    }
    panel.replaceChildren();
    const back = document.createElement("button");
    back.className = "item back";
    back.type = "button";
    back.textContent = "< Back";
    back.addEventListener("click", openPanel);
    panel.appendChild(back);
    if (!reply?.ok) {
      setMessage(reply?.error ?? "UDM did not answer", "error");
      addItem("Download at best quality anyway", "UDM will try the best format", {
        ...request, quality: "best",
      });
      return;
    }
    for (const choice of reply.qualities ?? []) {
      addItem(choice.label, choice.detail, {
        ...request, title: reply.title || request.title, quality: choice.quality,
      });
    }
  }

  async function send(request) {
    setMessage("Sending to UDM...", "");
    let reply;
    try {
      reply = await ext.runtime.sendMessage({
        type: "capture",
        request: { ...request, referrer: location.href },
      });
    } catch (error) {
      reply = { ok: false, error: "The extension was reloaded; refresh this page." };
    }
    const added = reply?.pending
      ? "Sent to UDM - choose where to save"
      : reply?.paused === false
        ? "Downloading in UDM"
        : "Added to the UDM download list";
    setMessage(reply?.ok ? added : (reply?.error ?? "UDM did not answer"),
      reply?.ok ? "ok" : "error");
    if (reply?.ok) setTimeout(() => { panel.hidden = true; hide(); }, 1200);
  }

  function setMessage(text, state) {
    let line = panel.querySelector(".message");
    if (!line) {
      line = document.createElement("div");
      const back = panel.querySelector(".back");
      if (back) back.after(line);
      else panel.prepend(line);
    }
    line.className = `message ${state}`;
    line.textContent = text;
  }

  function fileName(url) {
    try {
      return decodeURIComponent(new URL(url).pathname.split("/").pop()) || url;
    } catch (error) {
      return url;
    }
  }

  function formatSize(bytes) {
    if (!bytes) return "";
    const mb = bytes / (1024 * 1024);
    return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`;
  }

  trigger.addEventListener("click", (event) => {
    event.stopPropagation();
    if (panel.hidden) openPanel();
    else panel.hidden = true;
  });
  closeButton.addEventListener("click", (event) => {
    event.stopPropagation();
    if (current) dismissed.add(current);
    panel.hidden = true;
    host.style.display = "none";
  });
  host.addEventListener("mouseenter", () => clearTimeout(hideTimer));
  host.addEventListener("mouseleave", () => { if (panel.hidden) scheduleHide(); });

  // Media events do not bubble, so listen in the capture phase.
  document.addEventListener("play", (event) => {
    if (event.target instanceof HTMLVideoElement) show(event.target);
  }, true);
  let lastTarget = null;
  document.addEventListener("mousemove", (event) => {
    // Only re-resolve when the pointer moves onto a different element.
    if (event.target === lastTarget) {
      if (current && host.style.display !== "none") scheduleHide();
      return;
    }
    lastTarget = event.target;
    const video = videoAt(event.target);
    if (video) show(video);
  }, { passive: true });
  document.addEventListener("fullscreenchange", () => current && show(current));
  window.addEventListener("scroll", position, { passive: true, capture: true });
  window.addEventListener("resize", position, { passive: true });

  ext.storage.local.get({ showOverlay: true }).then((stored) => {
    enabled = stored.showOverlay;
  });
  ext.storage.onChanged.addListener((changes) => {
    if (changes.showOverlay) {
      enabled = changes.showOverlay.newValue;
      if (!enabled) host.style.display = "none";
    }
  });
  host.style.display = "none";
})();
