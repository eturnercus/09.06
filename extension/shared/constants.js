/** Общие константы и утилиты. */

export const DEFAULT_SETTINGS = {
  delaySeconds: 5,
  sensitivity: 8,
  pollMs: 500,
  soundDataUrl: "",
  soundFileName: "",
  /** @type {null | { label: string, lastWindowId: number, windowTabUrls: string[], monitoredUrls: string[] }} */
  pinnedWindow: null,
};

/** ~8 МБ сырого файла; base64 чуть больше. */
export const MAX_SOUND_BYTES = 8 * 1024 * 1024;

export const STORAGE_KEYS = {
  settings: "settings",
  monitors: "monitors",
};

/** Команда для ff-monitor (Firefox), через storage.session. */
export const FF_MONITOR_CMD_KEY = "__ffMonitorCmd";

export function uid() {
  return `z_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}
