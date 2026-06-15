import { browser } from "../shared/browser.js";

const delayInput = document.getElementById("delay");
const sensInput = document.getElementById("sensitivity");
const soundInput = document.getElementById("sound");
const tabList = document.getElementById("tab-list");

let state = { monitors: [], settings: {} };
let soundDataUrl = "";

async function send(type, payload = {}) {
  return browser.runtime.sendMessage({ type, ...payload });
}

function readSettingsFromForm() {
  return {
    delaySeconds: Math.max(1, Number(delayInput.value) || 5),
    sensitivity: Math.max(1, Number(sensInput.value) || 8),
    pollMs: 500,
    soundDataUrl,
  };
}

async function saveSettings() {
  const settings = readSettingsFromForm();
  await send("SAVE_SETTINGS", { settings });
  state.settings = settings;
}

delayInput.addEventListener("change", saveSettings);
sensInput.addEventListener("change", saveSettings);

soundInput.addEventListener("change", async () => {
  const file = soundInput.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    soundDataUrl = reader.result;
    await saveSettings();
  };
  reader.readAsDataURL(file);
});

document.getElementById("test-sound").addEventListener("click", async () => {
  await saveSettings();
  const audio = new Audio(soundDataUrl || "");
  if (soundDataUrl) audio.play().catch(() => beep());
  else beep();
});

function beep() {
  const ctx = new AudioContext();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.frequency.value = 880;
  gain.gain.value = 0.12;
  osc.start();
  setTimeout(() => {
    osc.stop();
    ctx.close();
  }, 350);
}

function render() {
  tabList.innerHTML = "";
  if (!state.monitors.length) {
    tabList.innerHTML = '<li class="empty">Нет вкладок. Нажмите «+ Текущая».</li>';
    return;
  }

  for (const m of state.monitors) {
    const li = document.createElement("li");
    li.className = "tab-item";
    const status = m.enabled
      ? '<span class="badge-on">● мониторинг</span>'
      : '<span class="badge-off">остановлено</span>';

    const zones =
      m.zones.length === 0
        ? "<li>нет зон</li>"
        : m.zones
            .map(
              (z) =>
                `<li>${z.label} (${Math.round(z.w * 100)}×${Math.round(z.h * 100)}%)</li>`
            )
            .join("");

    li.innerHTML = `
      <div class="tab-head">
        <div class="tab-title">${escapeHtml(m.title)} ${status}</div>
      </div>
      <div class="tab-url">${escapeHtml(m.url)}</div>
      <div class="tab-actions">
        <button class="small secondary" data-action="zone" data-tab="${m.tabId}">+ Зона</button>
        <button class="small secondary" data-action="toggle" data-tab="${m.tabId}">
          ${m.enabled ? "Пауза" : "Вкл"}
        </button>
        <button class="small danger" data-action="remove" data-tab="${m.tabId}">Удалить</button>
      </div>
      <ul class="zones">${zones}</ul>
      ${
        m.zones.length
          ? `<div class="zone-actions">${m.zones
              .map(
                (z) =>
                  `<button class="small secondary" data-action="delzone" data-tab="${m.tabId}" data-zone="${z.id}">× ${escapeHtml(z.label)}</button>`
              )
              .join("")}</div>`
          : ""
      }
    `;
    tabList.appendChild(li);
  }

  tabList.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", onTabAction);
  });
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function onTabAction(e) {
  const btn = e.currentTarget;
  const tabId = Number(btn.dataset.tab);
  const action = btn.dataset.action;

  if (action === "zone") {
    await send("SELECT_ZONE", { tabId });
    window.close();
    return;
  }
  if (action === "toggle") {
    const m = state.monitors.find((x) => x.tabId === tabId);
    await send("SET_TAB_ENABLED", { tabId, enabled: !m?.enabled });
  }
  if (action === "remove") {
    await send("REMOVE_TAB", { tabId });
  }
  if (action === "delzone") {
    await send("REMOVE_ZONE", { tabId, zoneId: btn.dataset.zone });
  }
  await refresh();
}

async function refresh() {
  const res = await send("GET_STATE");
  state.monitors = res.monitors || [];
  state.settings = res.settings || {};
  delayInput.value = state.settings.delaySeconds ?? 5;
  sensInput.value = state.settings.sensitivity ?? 8;
  soundDataUrl = state.settings.soundDataUrl || "";
  render();
}

document.getElementById("add-tab").addEventListener("click", async () => {
  await send("ADD_CURRENT_TAB");
  await refresh();
});

document.getElementById("start-all").addEventListener("click", async () => {
  await saveSettings();
  await send("START_ALL");
  await refresh();
});

document.getElementById("stop-all").addEventListener("click", async () => {
  await send("STOP_ALL");
  await refresh();
});

refresh();
