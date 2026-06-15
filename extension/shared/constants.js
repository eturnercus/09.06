/** Общие константы и утилиты. */

export const DEFAULT_SETTINGS = {
  delaySeconds: 5,
  sensitivity: 8,
  pollMs: 500,
  soundDataUrl: "",
};

export const STORAGE_KEYS = {
  settings: "settings",
  monitors: "monitors",
};

export function uid() {
  return `z_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}
