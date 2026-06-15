/** Три уровня чувствительности (общие для расширения). */

export const SENSITIVITY_LEVELS = {
  high: {
    id: "high",
    label: "Сильная",
    hint: "на любое изменение",
    threshold: 3,
    minChangedRatio: 0,
  },
  medium: {
    id: "medium",
    label: "Средняя",
    hint: "на заметную часть",
    threshold: 10,
    minChangedRatio: 0.06,
  },
  low: {
    id: "low",
    label: "Слабая",
    hint: "только смена картинки",
    threshold: 24,
    minChangedRatio: 0.15,
  },
};

/** @param {unknown} value */
export function normalizeSensitivity(value) {
  if (value === "high" || value === "medium" || value === "low") return value;
  if (typeof value === "number" && !Number.isNaN(value)) {
    if (value <= 5) return "high";
    if (value <= 14) return "medium";
    return "low";
  }
  return "medium";
}

/** @param {unknown} level */
export function getSensitivityConfig(level) {
  return SENSITIVITY_LEVELS[normalizeSensitivity(level)];
}
