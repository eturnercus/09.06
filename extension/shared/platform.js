import { browser } from "./browser.js";

/** Надёжное определение Firefox (captureTab есть и в некоторых сборках Chromium). */
export const isFirefox =
  typeof browser.runtime.getBrowserInfo === "function";
