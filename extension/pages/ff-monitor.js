import { browser } from "../shared/browser.js";
import { assertBrand, uiMark } from "../shared/brand.js";
import { cropImageData, ChangeTracker, syncZoneTrackers } from "../shared/diff.js";
import { normalizeSensitivity } from "../shared/sensitivity.js";
import { FF_MONITOR_CMD_KEY } from "../shared/constants.js";
import { notifyAlarm, playAlarmInTab } from "../shared/play-alarm.js";

const alarm = document.getElementById("alarm");
const brandEl = document.getElementById("brand-mark");
if (brandEl) brandEl.textContent = uiMark();

/** tabId -> session */
const sessions = new Map();

let settings = {
  delaySeconds: 5,
  sensitivity: "medium",
  pollMs: 500,
  soundDataUrl: "",
};

function stopSession(tabId) {
  const s = sessions.get(tabId);
  if (!s) return;
  clearInterval(s.interval);
  sessions.delete(tabId);
}

function stopAll() {
  for (const tabId of [...sessions.keys()]) stopSession(tabId);
}

async function playAlarm(tabId, label) {
  const played = await playAlarmInTab(tabId, settings.soundDataUrl || "");
  if (!played) {
    if (settings.soundDataUrl) {
      try {
        alarm.src = settings.soundDataUrl;
        await alarm.play();
      } catch {
        /* fallback below */
      }
    }
  }
  await notifyAlarm(label);
}

async function captureFrame(tabId) {
  let dataUrl = null;
  try {
    if (browser.tabs.captureTab) {
      dataUrl = await browser.tabs.captureTab(tabId, { format: "png" });
    }
  } catch (e) {
    console.warn("captureTab direct failed", tabId, e);
  }

  if (!dataUrl) {
    const res = await browser.runtime.sendMessage({ type: "FF_CAPTURE_TAB", tabId });
    if (res?.error) throw new Error(res.error);
    if (!res?.dataUrl) throw new Error("captureTab: empty response");
    dataUrl = res.dataUrl;
  }

  const fetchRes = await fetch(dataUrl);
  const blob = await fetchRes.blob();
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
  assertBrand();
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
      await playAlarm(tabId, zone.label);
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
  const level = normalizeSensitivity(settings.sensitivity);
  const delay = settings.delaySeconds;

  if (sessions.has(monitor.tabId)) {
    const s = sessions.get(monitor.tabId);
    s.monitor = monitor;
    syncZoneTrackers(s.trackers, monitor, delay, level);
    return;
  }

  const trackers = new Map();
  for (const z of monitor.zones) {
    trackers.set(z.id, new ChangeTracker(delay, level));
  }

  const session = {
    monitor,
    trackers,
    interval: setInterval(() => tickSession(monitor.tabId), settings.pollMs),
  };
  sessions.set(monitor.tabId, session);
}

function syncState(monitors) {
  const want = monitors.filter((m) => m.enabled && m.zones.length > 0);
  const wantIds = new Set(want.map((m) => m.tabId));

  for (const tabId of [...sessions.keys()]) {
    if (!wantIds.has(tabId)) stopSession(tabId);
  }

  for (const m of want) {
    ensureSession(m);
  }
}

function handleCommand(msg) {
  if (!msg?.type) return;
  if (msg.type === "FF_MONITOR_SYNC") {
    settings = {
      ...settings,
      ...(msg.settings || {}),
      sensitivity: normalizeSensitivity(msg.settings?.sensitivity ?? settings.sensitivity),
    };
    if (settings.soundDataUrl) alarm.src = settings.soundDataUrl;
    syncState(msg.monitors || []);
  }
  if (msg.type === "FF_MONITOR_STOP_ALL") {
    stopAll();
  }
}

browser.storage.session.get(FF_MONITOR_CMD_KEY).then((data) => {
  if (data[FF_MONITOR_CMD_KEY]) handleCommand(data[FF_MONITOR_CMD_KEY]);
});

browser.storage.session.onChanged.addListener((changes, area) => {
  if (area !== "session" || !changes[FF_MONITOR_CMD_KEY]) return;
  handleCommand(changes[FF_MONITOR_CMD_KEY].newValue);
});

browser.runtime.onMessage.addListener((msg) => {
  if (msg.type === "FF_MONITOR_SYNC" || msg.type === "FF_MONITOR_STOP_ALL") {
    handleCommand(msg);
  }
});

browser.runtime.sendMessage({ type: "FF_MONITOR_READY" }).catch(() => {});
