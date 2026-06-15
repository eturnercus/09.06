import { browser } from "../shared/browser.js";
import { cropImageData, ChangeTracker } from "../shared/diff.js";

const alarm = document.getElementById("alarm");

/** tabId -> session */
const sessions = new Map();

let settings = { delaySeconds: 5, sensitivity: 8, pollMs: 500, soundDataUrl: "" };

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

function stopAll() {
  for (const tabId of [...sessions.keys()]) stopSession(tabId);
}

function beep() {
  const ctx = new AudioContext();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.frequency.value = 880;
  gain.gain.value = 0.15;
  osc.start();
  setTimeout(() => {
    osc.stop();
    ctx.close();
  }, 400);
}

function playAlarm() {
  if (settings.soundDataUrl) {
    alarm.src = settings.soundDataUrl;
    alarm.play().catch(() => beep());
  } else {
    beep();
  }
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
      playAlarm();
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

browser.runtime.onMessage.addListener((msg) => {
  if (msg.type === "FF_MONITOR_SYNC") {
    settings = msg.settings || settings;
    if (settings.soundDataUrl) alarm.src = settings.soundDataUrl;
    syncState(msg.monitors || []);
  }
  if (msg.type === "FF_MONITOR_STOP_ALL") {
    stopAll();
  }
});
