import {
  getMonitors,
  getSettings,
  removeMonitor,
  saveSettings,
  upsertMonitor,
} from "../shared/storage.js";
import { uid } from "../shared/constants.js";

const OFFSCREEN_URL = "offscreen/offscreen.html";
let offscreenReady = false;

async function ensureOffscreen() {
  const existing = await chrome.runtime.getContexts({
    contextTypes: ["OFFSCREEN_DOCUMENT"],
    documentUrls: [chrome.runtime.getURL(OFFSCREEN_URL)],
  });
  if (existing.length > 0) {
    offscreenReady = true;
    return;
  }
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_URL,
    reasons: ["USER_MEDIA", "AUDIO_PLAYBACK"],
    justification: "Захват кадров вкладки и воспроизведение сигнала",
  });
  offscreenReady = true;
}

async function closeOffscreenIfIdle() {
  const monitors = await getMonitors();
  const active = monitors.some((m) => m.enabled && m.zones.length > 0);
  if (active) return;
  const existing = await chrome.runtime.getContexts({
    contextTypes: ["OFFSCREEN_DOCUMENT"],
    documentUrls: [chrome.runtime.getURL(OFFSCREEN_URL)],
  });
  if (existing.length > 0) {
    await chrome.offscreen.closeDocument();
    offscreenReady = false;
  }
}

async function syncOffscreen() {
  const monitors = await getMonitors();
  const settings = await getSettings();
  const active = monitors.filter((m) => m.enabled && m.zones.length > 0);
  if (active.length === 0) {
    if (offscreenReady) {
      await chrome.runtime.sendMessage({ type: "OFFSCREEN_STOP_ALL" }).catch(() => {});
    }
    await closeOffscreenIfIdle();
    return;
  }
  await ensureOffscreen();
  for (const m of monitors) {
    if (m.enabled && m.zones.length > 0) {
      try {
        await chrome.tabs.get(m.tabId);
        await chrome.tabs.update(m.tabId, { autoDiscardable: false });
      } catch {
        await removeMonitor(m.tabId);
      }
    }
  }
  await chrome.runtime.sendMessage({
    type: "OFFSCREEN_SYNC",
    monitors: await getMonitors(),
    settings,
  });
}

async function injectZoneSelector(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content/zone-selector.js"],
  });
  await chrome.tabs.sendMessage(tabId, { type: "START_ZONE_SELECT" });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    switch (msg.type) {
      case "GET_STATE": {
        const [monitors, settings] = await Promise.all([
          getMonitors(),
          getSettings(),
        ]);
        sendResponse({ monitors, settings });
        break;
      }
      case "SAVE_SETTINGS": {
        await saveSettings(msg.settings);
        await syncOffscreen();
        sendResponse({ ok: true });
        break;
      }
      case "ADD_CURRENT_TAB": {
        const [tab] = await chrome.tabs.query({
          active: true,
          currentWindow: true,
        });
        if (!tab?.id) throw new Error("Нет активной вкладки");
        let monitor = (await getMonitors()).find((m) => m.tabId === tab.id);
        if (!monitor) {
          monitor = {
            tabId: tab.id,
            windowId: tab.windowId,
            title: tab.title || "Вкладка",
            url: tab.url || "",
            enabled: false,
            zones: [],
          };
          await upsertMonitor(monitor);
        }
        sendResponse({ monitor });
        break;
      }
      case "SELECT_ZONE": {
        const tabId = msg.tabId;
        await injectZoneSelector(tabId);
        sendResponse({ ok: true });
        break;
      }
      case "ZONE_SELECTED": {
        const tabId = sender.tab?.id;
        if (!tabId) break;
        const monitors = await getMonitors();
        let monitor = monitors.find((m) => m.tabId === tabId);
        if (!monitor) {
          const tab = await chrome.tabs.get(tabId);
          monitor = {
            tabId,
            windowId: tab.windowId,
            title: tab.title || "Вкладка",
            url: tab.url || "",
            enabled: false,
            zones: [],
          };
        }
        monitor.zones.push({
          id: uid(),
          x: msg.zone.x,
          y: msg.zone.y,
          w: msg.zone.w,
          h: msg.zone.h,
          label: `Зона ${monitor.zones.length + 1}`,
        });
        await upsertMonitor(monitor);
        sendResponse({ monitor });
        break;
      }
      case "REMOVE_ZONE": {
        const monitors = await getMonitors();
        const monitor = monitors.find((m) => m.tabId === msg.tabId);
        if (monitor) {
          monitor.zones = monitor.zones.filter((z) => z.id !== msg.zoneId);
          await upsertMonitor(monitor);
        }
        await syncOffscreen();
        sendResponse({ ok: true });
        break;
      }
      case "REMOVE_TAB": {
        await removeMonitor(msg.tabId);
        await syncOffscreen();
        sendResponse({ ok: true });
        break;
      }
      case "SET_TAB_ENABLED": {
        const monitors = await getMonitors();
        const monitor = monitors.find((m) => m.tabId === msg.tabId);
        if (monitor) {
          monitor.enabled = msg.enabled;
          await upsertMonitor(monitor);
        }
        await syncOffscreen();
        sendResponse({ ok: true });
        break;
      }
      case "START_ALL": {
        const monitors = await getMonitors();
        for (const m of monitors) {
          if (m.zones.length > 0) {
            m.enabled = true;
            await upsertMonitor(m);
          }
        }
        await syncOffscreen();
        sendResponse({ ok: true });
        break;
      }
      case "STOP_ALL": {
        const monitors = await getMonitors();
        for (const m of monitors) {
          m.enabled = false;
          await upsertMonitor(m);
        }
        await syncOffscreen();
        sendResponse({ ok: true });
        break;
      }
      case "ALARM": {
        chrome.action.setBadgeText({ text: "!" });
        chrome.action.setBadgeBackgroundColor({ color: "#e53935" });
        setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
        sendResponse({ ok: true });
        break;
      }
      default:
        sendResponse({ error: "unknown" });
    }
  })().catch((e) => sendResponse({ error: String(e) }));
  return true;
});

chrome.tabs.onRemoved.addListener(async (tabId) => {
  await removeMonitor(tabId);
  await syncOffscreen();
});

chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (info.title || info.url) {
    const monitors = await getMonitors();
    const monitor = monitors.find((m) => m.tabId === tabId);
    if (monitor) {
      if (info.title) monitor.title = tab.title;
      if (info.url) monitor.url = tab.url;
      await upsertMonitor(monitor);
    }
  }
});

chrome.runtime.onStartup.addListener(() => syncOffscreen());
chrome.runtime.onInstalled.addListener(() => syncOffscreen());
