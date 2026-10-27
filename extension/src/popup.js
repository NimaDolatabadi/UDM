/* Toolbar popup: connection status, capture settings, and detected media. */
"use strict";

const $ = (id) => document.getElementById(id);
const ALL_SITES = { origins: ["<all_urls>"] };

async function activeTab() {
  const [tab] = await api.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function refreshStatus() {
  const status = $("status");
  const reply = await sendToUdm({ type: "ping" });
  if (reply.hostMissing) {
    status.textContent = "Not installed";
    status.className = "status danger";
    status.title = reply.detail ?? "";
  } else if (reply.running === false) {
    status.textContent = "UDM closed";
    status.className = "status warning";
    status.title = "UDM starts automatically when a download is sent.";
  } else {
    status.textContent = "Connected";
    status.className = "status success";
  }
}

async function refreshPermission() {
  const granted = await api.permissions.contains(ALL_SITES);
  $("permission").hidden = granted;
}

function mediaLabel(item) {
  let name = item.url;
  try {
    name = decodeURIComponent(new URL(item.url).pathname.split("/").pop()) || item.url;
  } catch (error) {
    // Keep the raw URL when it cannot be parsed.
  }
  const kind = item.stream ? `${item.kind.toUpperCase()} stream` : item.kind;
  return { name, meta: [kind, formatBytes(item.size)].filter(Boolean).join(" - ") };
}

async function renderMedia(tab) {
  const list = $("media");
  list.replaceChildren();
  let media = [];
  try {
    media = await api.runtime.sendMessage({ type: "getMedia", tabId: tab.id });
  } catch (error) {
    media = [];
  }
  $("empty").hidden = media.length > 0;
  for (const item of [...media].reverse()) {
    const { name, meta } = mediaLabel(item);
    const row = document.createElement("li");
    row.innerHTML = '<div class="text"><span class="name"></span>'
      + '<span class="meta"></span></div><button type="button">Download</button>';
    row.querySelector(".name").textContent = name;
    row.querySelector(".name").title = item.url;
    row.querySelector(".meta").textContent = meta;
    row.querySelector("button").addEventListener("click", () => (
      item.stream
        ? chooseQuality(item.url, { referrer: tab.url, title: tab.title })
        : send("download", item.url, { referrer: tab.url })
    ));
    list.appendChild(row);
  }
}

function showMessage(text, state = "") {
  $("message").className = `message ${state}`;
  $("message").textContent = text;
}

async function send(type, url, extra) {
  showMessage("Sending to UDM...");
  const reply = await sendToUdm(await buildRequest(type, url, extra));
  const added = reply.pending
    ? "Sent to UDM - choose where to save"
    : reply.paused === false ? "Downloading in UDM" : "Added to the UDM download list";
  showMessage(reply.ok ? added : reply.error, reply.ok ? "success" : "danger");
  if (reply.ok) {
    $("qualityBox").hidden = true;
    refreshStatus();
  }
}

/* List the qualities yt-dlp finds for a page or stream, then send the pick. */
async function chooseQuality(url, extra) {
  const box = $("qualityBox");
  const list = $("qualityList");
  list.replaceChildren();
  box.hidden = false;
  $("qualityTitle").textContent = "Checking available qualities...";
  const reply = await sendToUdm(await buildRequest("formats", url, extra));
  if (!reply.ok) {
    $("qualityTitle").textContent = "Qualities unavailable";
    showMessage(reply.error, "danger");
  } else {
    $("qualityTitle").textContent = reply.title || "Choose a quality";
  }
  const choices = reply.ok ? reply.qualities : [
    { quality: "best", label: "Best quality", detail: "Try anyway" },
  ];
  for (const choice of choices) {
    const row = document.createElement("li");
    row.innerHTML = '<div class="text"><span class="name"></span>'
      + '<span class="meta"></span></div><button type="button">Add</button>';
    row.querySelector(".name").textContent = choice.label;
    row.querySelector(".meta").textContent = choice.detail;
    row.querySelector("button").addEventListener("click", () => send("stream", url, {
      ...extra, title: reply.title || extra.title, quality: choice.quality,
    }));
    list.appendChild(row);
  }
}

async function init() {
  const tab = await activeTab();
  const settings = await getSettings();
  $("capture").checked = settings.captureDownloads;
  $("overlay").checked = settings.showOverlay;
  $("capture").addEventListener("change", (event) => {
    saveSettings({ captureDownloads: event.target.checked });
  });
  $("overlay").addEventListener("change", (event) => {
    saveSettings({ showOverlay: event.target.checked });
  });
  $("grant").addEventListener("click", async () => {
    // Firefox may withhold host access until the user grants it here.
    await api.permissions.request(ALL_SITES);
    refreshPermission();
  });
  $("sendPage").disabled = !isHttpUrl(tab?.url);
  $("sendPage").addEventListener("click", () => {
    chooseQuality(tab.url, { title: tab.title });
  });
  $("qualityClose").addEventListener("click", () => {
    $("qualityBox").hidden = true;
  });
  $("clear").addEventListener("click", async () => {
    await api.runtime.sendMessage({ type: "clearMedia", tabId: tab.id });
    renderMedia(tab);
  });
  refreshPermission();
  refreshStatus();
  if (tab) renderMedia(tab);
}

init();
