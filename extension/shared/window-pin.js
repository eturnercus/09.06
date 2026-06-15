import { browser } from "./browser.js";

const SKIP_PREFIXES = [
  "chrome:",
  "chrome-extension:",
  "moz-extension:",
  "about:",
  "edge:",
  "brave:",
];

/** Нормализованный URL для сопоставления вкладок после перезапуска. */
export function normalizeUrl(url) {
  if (!url || typeof url !== "string") return "";
  if (SKIP_PREFIXES.some((p) => url.startsWith(p))) return "";
  try {
    const u = new URL(url);
    u.hash = "";
    let path = u.pathname;
    if (path.length > 1 && path.endsWith("/")) path = path.slice(0, -1);
    return `${u.origin}${path}${u.search}`;
  } catch {
    return url.split("#")[0];
  }
}

export function urlsMatch(a, b) {
  const na = normalizeUrl(a);
  const nb = normalizeUrl(b);
  if (!na || !nb) return false;
  return na === nb;
}

function tabUrlsInWindow(window) {
  return [...new Set((window.tabs || []).map((t) => normalizeUrl(t.url)).filter(Boolean))];
}

function scoreWindow(window, pinned) {
  const tabs = tabUrlsInWindow(window);
  const sigs = pinned.windowTabUrls?.length
    ? pinned.windowTabUrls
    : pinned.monitoredUrls || [];
  if (!sigs.length) return 0;
  let hit = 0;
  for (const s of sigs) {
    if (tabs.some((u) => urlsMatch(u, s))) hit++;
  }
  return hit / sigs.length;
}

function windowHasMonitoredTabs(window, monitoredUrls) {
  if (!monitoredUrls?.length) return true;
  const tabs = tabUrlsInWindow(window);
  return monitoredUrls.every((mu) => tabs.some((tu) => urlsMatch(tu, mu)));
}

/**
 * Ищет окно по сохранённому отпечатку (ID окон после перезапуска меняются).
 */
export async function findPinnedWindow(pinned) {
  if (!pinned) return null;
  const monitored = (pinned.monitoredUrls || []).map(normalizeUrl).filter(Boolean);
  const hasSigs =
    monitored.length > 0 || (pinned.windowTabUrls || []).some(Boolean);
  if (!hasSigs) return null;

  if (pinned.lastWindowId) {
    try {
      const w = await browser.windows.get(pinned.lastWindowId, { populate: true });
      if (windowHasMonitoredTabs(w, monitored) && scoreWindow(w, pinned) >= 0.25) {
        return w;
      }
    } catch {
      /* окно закрыто или ID устарел */
    }
  }

  const windows = await browser.windows.getAll({ populate: true });
  let best = null;
  let bestScore = 0;

  for (const w of windows) {
    if (!windowHasMonitoredTabs(w, monitored)) continue;
    const s = scoreWindow(w, pinned);
    if (s > bestScore) {
      bestScore = s;
      best = w;
    }
  }

  const minScore = monitored.length > 0 ? 0.34 : 0.25;
  return bestScore >= minScore ? best : null;
}

/** Обновляет tabId/windowId у мониторов по URL вкладок в найденном окне. */
export function remapMonitorsToWindow(monitors, window) {
  const tabs = window.tabs || [];
  return monitors.map((m) => {
    const tab = tabs.find((t) => urlsMatch(t.url, m.url));
    if (!tab) return { ...m, enabled: false };
    return {
      ...m,
      tabId: tab.id,
      windowId: window.id,
      title: tab.title || m.title,
      url: tab.url || m.url,
    };
  });
}

export function monitoredUrlsFromMonitors(monitors, windowId = null) {
  return [
    ...new Set(
      monitors
        .filter((m) => !windowId || m.windowId === windowId)
        .map((m) => normalizeUrl(m.url))
        .filter(Boolean)
    ),
  ];
}

export function buildPinnedWindow(window, monitors, label = "") {
  const tabUrls = tabUrlsInWindow(window);
  const monitoredUrls = monitoredUrlsFromMonitors(monitors, window.id);
  const active = window.tabs?.find((t) => t.active);
  return {
    label:
      label ||
      (active?.title ? active.title.slice(0, 48) : `Окно ${window.id}`),
    lastWindowId: window.id,
    windowTabUrls: tabUrls,
    monitoredUrls: monitoredUrls.length ? monitoredUrls : tabUrls.slice(0, 8),
  };
}

export function refreshPinnedFromMonitors(pinned, monitors, windowId) {
  if (!pinned) return pinned;
  const monitoredUrls = monitoredUrlsFromMonitors(monitors, windowId);
  return {
    ...pinned,
    monitoredUrls: monitoredUrls.length ? monitoredUrls : pinned.monitoredUrls,
    lastWindowId: windowId ?? pinned.lastWindowId,
  };
}

export async function resolvePinnedSession(settings, monitors) {
  if (!settings.pinnedWindow) {
    return { settings, monitors, window: null };
  }

  const win = await findPinnedWindow(settings.pinnedWindow);
  if (!win) {
    const err = new Error(
      "Закреплённое окно не найдено. Откройте нужное окно с теми же вкладками или нажмите «Открепить»."
    );
    err.code = "PINNED_WINDOW_NOT_FOUND";
    throw err;
  }

  const remapped = remapMonitorsToWindow(monitors, win);
  const nextPinned = refreshPinnedFromMonitors(
    { ...settings.pinnedWindow, lastWindowId: win.id, windowTabUrls: tabUrlsInWindow(win) },
    remapped,
    win.id
  );
  const nextSettings = { ...settings, pinnedWindow: nextPinned };
  return { settings: nextSettings, monitors: remapped, window: win };
}

export function monitorsInPinnedWindow(monitors, windowId) {
  if (windowId == null) return monitors;
  return monitors.filter((m) => m.windowId === windowId);
}
