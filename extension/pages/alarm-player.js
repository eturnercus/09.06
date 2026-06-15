import { browser } from "../shared/browser.js";

const alarm = document.getElementById("alarm");

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

browser.runtime.onMessage.addListener((msg) => {
  if (msg.type !== "PLAY_ALARM") return;
  if (msg.soundDataUrl) {
    alarm.src = msg.soundDataUrl;
    alarm.play().catch(() => beep());
  } else {
    beep();
  }
});
