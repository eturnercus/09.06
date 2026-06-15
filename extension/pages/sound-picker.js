import { browser } from "../shared/browser.js";
import { uiMark } from "../shared/brand.js";
import { MAX_SOUND_BYTES } from "../shared/constants.js";

const fileInput = document.getElementById("file");
const statusEl = document.getElementById("status");
const clearBtn = document.getElementById("clear");
const brandEl = document.getElementById("brand-mark");
if (brandEl) brandEl.textContent = uiMark();

function setStatus(text, kind = "") {
  statusEl.textContent = text;
  statusEl.className = "status" + (kind ? ` ${kind}` : "");
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error("Не удалось прочитать файл"));
    reader.readAsDataURL(file);
  });
}

async function loadCurrent() {
  const res = await browser.runtime.sendMessage({ type: "GET_STATE" });
  const name = res.settings?.soundFileName;
  if (res.settings?.soundDataUrl && name) {
    setStatus(`Текущий звук: ${name}`, "ok");
  } else if (res.settings?.soundDataUrl) {
    setStatus("Текущий звук: пользовательский файл", "ok");
  } else {
    setStatus("Сейчас используется встроенный сигнал.");
  }
}

async function saveSound(dataUrl, fileName) {
  const res = await browser.runtime.sendMessage({ type: "GET_STATE" });
  const settings = {
    ...(res.settings || {}),
    soundDataUrl: dataUrl,
    soundFileName: fileName,
  };
  const saved = await browser.runtime.sendMessage({ type: "SAVE_SETTINGS", settings });
  if (saved?.error) throw new Error(saved.error);
}

fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  fileInput.value = "";
  if (!file) return;

  if (file.size > MAX_SOUND_BYTES) {
    setStatus(`Файл слишком большой (${Math.round(file.size / 1024 / 1024)} МБ). Максимум 8 МБ.`, "error");
    return;
  }

  setStatus("Загрузка…");
  try {
    const dataUrl = await readFileAsDataUrl(file);
    await saveSound(dataUrl, file.name);
    setStatus(`Сохранено: ${file.name}. Можно закрыть вкладку.`, "ok");
  } catch (e) {
    const msg = String(e?.message || e);
    if (msg.includes("QUOTA") || msg.includes("quota")) {
      setStatus("Не хватило места в хранилище расширения. Выберите файл меньше.", "error");
    } else {
      setStatus(`Ошибка: ${msg}`, "error");
    }
  }
});

clearBtn.addEventListener("click", async () => {
  setStatus("Сброс…");
  try {
    await saveSound("", "");
    setStatus("Сброшено — будет встроенный сигнал.", "ok");
  } catch (e) {
    setStatus(`Ошибка: ${e}`, "error");
  }
});

loadCurrent().catch((e) => setStatus(`Ошибка: ${e}`, "error"));
