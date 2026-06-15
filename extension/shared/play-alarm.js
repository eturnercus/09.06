/**
 * Воспроизведение сигнала во вкладке (обходит блокировку autoplay в служебных страницах Firefox).
 */
import { browser } from "./browser.js";

export function beepInPage() {
  const ctx = new AudioContext();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.frequency.value = 880;
  gain.gain.value = 0.2;
  osc.start();
  setTimeout(() => {
    osc.stop();
    ctx.close();
  }, 450);
}

export async function playAlarmInTab(tabId, soundDataUrl = "") {
  if (!tabId) return false;
  try {
    await browser.scripting.executeScript({
      target: { tabId },
      func: (url) => {
        const beep = () => {
          const ctx = new AudioContext();
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.frequency.value = 880;
          gain.gain.value = 0.2;
          osc.start();
          setTimeout(() => {
            osc.stop();
            ctx.close();
          }, 450);
        };
        if (url) {
          const audio = new Audio(url);
          audio.play().catch(beep);
        } else {
          beep();
        }
      },
      args: [soundDataUrl || ""],
    });
    return true;
  } catch {
    return false;
  }
}

export async function notifyAlarm(label) {
  try {
    const icon = browser.runtime.getURL("icons/icon48.png");
    await browser.notifications.create(`watchalert-${Date.now()}`, {
      type: "basic",
      iconUrl: icon,
      title: "WatchAlert",
      message: label || "Обнаружено изменение в зоне",
    });
  } catch {
    /* notifications unavailable */
  }
}
