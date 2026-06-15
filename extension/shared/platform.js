import { browser } from "./browser.js";

/** Firefox has tabs.captureTab; Chromium uses tabCapture + offscreen. */
export const isFirefox = !browser.tabCapture;
