import { browser } from "../shared/browser.js";
import { cropImageData, ChangeTracker } from "../shared/diff.js";
import { getMonitors, getSettings } from "../shared/storage.js";

/** tabId -> session */
const sessions = new Map();

let settings = { delaySeconds: 5, sensitivity: 8, pollMs: 500, soundDataUrl: "" };
let alarmPlayerTabId = null;

function buildTrackers(monitor) {
  const map = new Map();
  for (const z of monitor.zones) {
    map.set(z.id, new ChangeTracker(settings.delaySeconds, settings.sensitivity));
  }
  return map;
}

function stopSession(tabId) {
  const s = sessions.get(tabId);
  if (!s) return;
  clearInterval(s.interval);
  sessions.delete(tabId);
}

async function closeAlarmPlayer() {
  if (!alarmPlayerTabId) return;
  try {
    await browser.tabs.remove(alarmPlayerTabId);
  } catch {
    /* already closed */
  }
  alarmPlayerTabId = null;
}

async function ensureAlarmPlayer() {
  if (alarmPlayerTabId) {
    try {
      await browser.tabs.get(alarmPlayerTabId);
      return;
    } catch {
      alarmPlayerTabId = null;
    }
  }
  const tab = await browser.tabs.create({
    url: browser.runtime.getURL("pages/alarm-player.html"),
    active: false,
    pinned: true,
  });
  alarmPlayerTabId = tab.id;
}

async function playAlarm() {
  await ensureAlarmPlayer();
  await browser.runtime
    .sendMessage({
      type: "PLAY_ALARM",
      soundDataUrl: settings.soundDataUrl || "",
    })
    .catch(() => {});
}

async function captureFrame(tabId) {
  const dataUrl = await browser.tabs.captureTab(tabId, { format: "png" });
  const res = await fetch(dataUrl);
  const blob = await res.blob();
  const bitmap = await createImageBitmap(blob);
  const w = bitmap.width;
  const h = bitmap.height;
  const canvas = new OffscreenCanvas(w, h);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(bitmap, 0, 0);
  bitmap.close();
  return { data: ctx.getImageData(0, 0, w, h).data, w, h };
}

async function tickSession(tabId) {
  const session = sessions.get(tabId);
  if (!session?.monitor?.zones?.length) return;

  let frame;
  try {
    frame = await captureFrame(tabId);
  } catch (e) {
    console.warn("captureTab failed", tabId, e);
    return;
  }

  const now = Date.now();
  for (const zone of session.monitor.zones) {
    const tracker = session.trackers.get(zone.id);
    if (!tracker) continue;
    const crop = cropImageData(frame.data, frame.w, frame.h, zone);
    if (tracker.process(crop.data, crop.w, crop.h, now)) {
      await playAlarm();
      browser.runtime
        .sendMessage({
          type: "ALARM",
          tabId,
          zoneId: zone.id,
          label: zone.label,
        })
        .catch(() => {});
    }
  }
}

function ensureSession(monitor) {
  if (sessions.has(monitor.tabId)) {
    const s = sessions.get(monitor.tabId);
    s.monitor = monitor;
    s.trackers = buildTrackers(monitor);
    return;
  }

  const session = {
    monitor,
    trackers: buildTrackers(monitor),
    interval: setInterval(() => tickSession(monitor.tabId), settings.pollMs),
  };
  sessions.set(monitor.tabId, session);
}

export async function syncFirefoxMonitor() {
  settings = await getSettings();
  const monitors = await getMonitors();
  const want = monitors.filter((m) => m.enabled && m.zones.length > 0);
  const wantIds = new Set(want.map((m) => m.tabId));

  for (const tabId of [...sessions.keys()]) {
    if (!wantIds.has(tabId)) stopSession(tabId);
  }

  if (want.length === 0) {
    await closeAlarmPlayer();
    return;
  }

  await ensureAlarmPlayer();

  for (const m of want) {
    try {
      await browser.tabs.get(m.tabId);
      await browser.tabs.update(m.tabId, { autoDiscardable: false });
      ensureSession(m);
    } catch {
      stopSession(m.tabId);
    }
  }
}

export function stopFirefoxMonitor() {
  for (const tabId of [...sessions.keys()]) stopSession(tabId);
  closeAlarmPlayer();
}
