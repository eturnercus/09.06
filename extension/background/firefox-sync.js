import { browser } from "../shared/browser.js";
import { getMonitors, getSettings } from "../shared/storage.js";

const MONITOR_PAGE = "pages/ff-monitor.html";

async function waitTabComplete(tabId) {
  const tab = await browser.tabs.get(tabId);
  if (tab.status === "complete") return;
  await new Promise((resolve) => {
    const onUpdated = (id, info) => {
      if (id === tabId && info.status === "complete") {
        browser.tabs.onUpdated.removeListener(onUpdated);
        resolve();
      }
    };
    browser.tabs.onUpdated.addListener(onUpdated);
  });
}

async function sendToMonitorPage(payload) {
  for (let i = 0; i < 15; i++) {
    try {
      await browser.runtime.sendMessage(payload);
      return;
    } catch {
      await new Promise((r) => setTimeout(r, 100));
    }
  }
}

export async function syncFirefoxCapture() {
  const monitors = await getMonitors();
  const settings = await getSettings();
  const active = monitors.filter((m) => m.enabled && m.zones.length > 0);
  const pageUrl = browser.runtime.getURL(MONITOR_PAGE);

  if (active.length === 0) {
    await sendToMonitorPage({ type: "FF_MONITOR_STOP_ALL" });
    const tabs = await browser.tabs.query({ url: pageUrl });
    for (const t of tabs) {
      await browser.tabs.remove(t.id).catch(() => {});
    }
    return;
  }

  let tabs = await browser.tabs.query({ url: pageUrl });
  if (tabs.length === 0) {
    const tab = await browser.tabs.create({
      url: pageUrl,
      active: false,
      pinned: true,
    });
    await waitTabComplete(tab.id);
  }

  for (const m of monitors) {
    if (m.enabled && m.zones.length > 0) {
      try {
        await browser.tabs.get(m.tabId);
        await browser.tabs.update(m.tabId, { autoDiscardable: false });
      } catch {
        /* tab gone — cleaned up elsewhere */
      }
    }
  }

  await sendToMonitorPage({
    type: "FF_MONITOR_SYNC",
    monitors: await getMonitors(),
    settings,
  });
}
