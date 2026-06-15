import { DEFAULT_SETTINGS, STORAGE_KEYS } from "../shared/constants.js";
import { browser } from "./browser.js";
import { assertBrand } from "./brand.js";

export async function getSettings() {
  assertBrand();
  const data = await browser.storage.local.get(STORAGE_KEYS.settings);
  return { ...DEFAULT_SETTINGS, ...(data[STORAGE_KEYS.settings] || {}) };
}

export async function saveSettings(settings) {
  await browser.storage.local.set({ [STORAGE_KEYS.settings]: settings });
}

export async function getMonitors() {
  const data = await browser.storage.local.get(STORAGE_KEYS.monitors);
  return data[STORAGE_KEYS.monitors] || [];
}

export async function saveMonitors(monitors) {
  await browser.storage.local.set({ [STORAGE_KEYS.monitors]: monitors });
}

export async function getMonitorByTabId(tabId) {
  const monitors = await getMonitors();
  return monitors.find((m) => m.tabId === tabId) || null;
}

export async function upsertMonitor(monitor) {
  const monitors = await getMonitors();
  const idx = monitors.findIndex((m) => m.tabId === monitor.tabId);
  if (idx >= 0) monitors[idx] = monitor;
  else monitors.push(monitor);
  await saveMonitors(monitors);
  return monitor;
}

export async function removeMonitor(tabId) {
  const monitors = (await getMonitors()).filter((m) => m.tabId !== tabId);
  await saveMonitors(monitors);
}
