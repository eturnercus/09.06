import { cropImageData, ChangeTracker } from "../shared/diff.js";

const alarm = document.getElementById("alarm");

/** tabId -> session */
const sessions = new Map();

let settings = { delaySeconds: 5, sensitivity: 8, pollMs: 500, soundDataUrl: "" };
let monitors = [];

function stopSession(tabId) {
  const s = sessions.get(tabId);
  if (!s) return;
  clearInterval(s.interval);
  s.track?.stop();
  s.stream?.getTracks().forEach((t) => t.stop());
  s.video?.remove();
  sessions.delete(tabId);
}

function stopAll() {
  for (const tabId of [...sessions.keys()]) stopSession(tabId);
}

async function getTabStream(tabId) {
  const streamId = await chrome.tabCapture.getMediaStreamId({ targetTabId: tabId });
  return navigator.mediaDevices.getUserMedia({
    audio: false,
    video: {
      mandatory: {
        chromeMediaSource: "tab",
        chromeMediaSourceId: streamId,
      },
    },
  });
}

async function ensureSession(monitor) {
  if (sessions.has(monitor.tabId)) {
    const s = sessions.get(monitor.tabId);
    s.monitor = monitor;
    s.trackers = buildTrackers(monitor);
    return;
  }

  const stream = await getTabStream(monitor.tabId);
  const track = stream.getVideoTracks()[0];

  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.srcObject = stream;
  document.body.appendChild(video);
  await video.play();

  const canvas = new OffscreenCanvas(16, 16);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  const session = {
    stream,
    track,
    video,
    canvas,
    ctx,
    monitor,
    trackers: buildTrackers(monitor),
    interval: null,
  };

  session.interval = setInterval(() => tickSession(monitor.tabId), settings.pollMs);
  sessions.set(monitor.tabId, session);
}

function buildTrackers(monitor) {
  const map = new Map();
  for (const z of monitor.zones) {
    map.set(z.id, new ChangeTracker(settings.delaySeconds, settings.sensitivity));
  }
  return map;
}

function tickSession(tabId) {
  const session = sessions.get(tabId);
  if (!session || !session.monitor?.zones?.length) return;

  const video = session.video;
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if (!vw || !vh) return;

  session.canvas.width = vw;
  session.canvas.height = vh;
  session.ctx.drawImage(video, 0, 0, vw, vh);
  const frame = session.ctx.getImageData(0, 0, vw, vh);
  const now = Date.now();

  for (const zone of session.monitor.zones) {
    const tracker = session.trackers.get(zone.id);
    if (!tracker) continue;
    const crop = cropImageData(frame.data, vw, vh, zone);
    if (tracker.process(crop.data, crop.w, crop.h, now)) {
      playAlarm();
      chrome.runtime.sendMessage({
        type: "ALARM",
        tabId,
        zoneId: zone.id,
        label: zone.label,
      });
    }
  }
}

function playAlarm() {
  if (settings.soundDataUrl) {
    alarm.src = settings.soundDataUrl;
    alarm.play().catch(() => beep());
  } else {
    beep();
  }
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

async function syncState() {
  const want = monitors.filter((m) => m.enabled && m.zones.length > 0);
  const wantIds = new Set(want.map((m) => m.tabId));

  for (const tabId of [...sessions.keys()]) {
    if (!wantIds.has(tabId)) stopSession(tabId);
  }

  for (const m of want) {
    try {
      await ensureSession(m);
    } catch (e) {
      console.warn("capture failed tab", m.tabId, e);
      stopSession(m.tabId);
    }
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "OFFSCREEN_SYNC") {
    settings = msg.settings;
    monitors = msg.monitors || [];
    if (settings.soundDataUrl) alarm.src = settings.soundDataUrl;
    syncState();
  }
  if (msg.type === "OFFSCREEN_STOP_ALL") {
    stopAll();
  }
});
