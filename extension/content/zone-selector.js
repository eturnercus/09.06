(function () {
  if (window.__watchalertSelectorActive) return;
  window.__watchalertSelectorActive = true;

  const overlay = document.createElement("div");
  overlay.id = "watchalert-zone-overlay";
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    zIndex: "2147483646",
    cursor: "crosshair",
    background: "rgba(0,0,0,0.15)",
  });

  const hint = document.createElement("div");
  hint.textContent = "Выделите область на странице. Esc — отмена.";
  Object.assign(hint.style, {
    position: "fixed",
    top: "12px",
    left: "50%",
    transform: "translateX(-50%)",
    zIndex: "2147483647",
    background: "rgba(0,0,0,0.75)",
    color: "#fff",
    padding: "10px 16px",
    borderRadius: "8px",
    fontFamily: "system-ui, sans-serif",
    fontSize: "14px",
    pointerEvents: "none",
  });

  const box = document.createElement("div");
  Object.assign(box.style, {
    position: "fixed",
    border: "3px solid #00ff88",
    background: "rgba(0,255,136,0.12)",
    display: "none",
    zIndex: "2147483647",
    pointerEvents: "none",
  });

  let startX = 0;
  let startY = 0;
  let dragging = false;

  function cleanup() {
    overlay.remove();
    hint.remove();
    box.remove();
    window.__watchalertSelectorActive = false;
    document.removeEventListener("keydown", onKey);
  }

  function onKey(e) {
    if (e.key === "Escape") cleanup();
  }

  function relRect(x1, y1, x2, y2) {
    const left = Math.min(x1, x2);
    const top = Math.min(y1, y2);
    const width = Math.abs(x2 - x1);
    const height = Math.abs(y2 - y1);
    return {
      x: left / window.innerWidth,
      y: top / window.innerHeight,
      w: width / window.innerWidth,
      h: height / window.innerHeight,
    };
  }

  overlay.addEventListener("mousedown", (e) => {
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    Object.assign(box.style, {
      left: `${startX}px`,
      top: `${startY}px`,
      width: "0",
      height: "0",
      display: "block",
    });
  });

  overlay.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const left = Math.min(startX, e.clientX);
    const top = Math.min(startY, e.clientY);
    const w = Math.abs(e.clientX - startX);
    const h = Math.abs(e.clientY - startY);
    Object.assign(box.style, {
      left: `${left}px`,
      top: `${top}px`,
      width: `${w}px`,
      height: `${h}px`,
    });
  });

  overlay.addEventListener("mouseup", (e) => {
    if (!dragging) return;
    dragging = false;
    const w = Math.abs(e.clientX - startX);
    const h = Math.abs(e.clientY - startY);
    if (w < 12 || h < 12) return;
    const zone = relRect(startX, startY, e.clientX, e.clientY);
    cleanup();
    chrome.runtime.sendMessage({ type: "ZONE_SELECTED", zone });
  });

  document.addEventListener("keydown", onKey);
  document.body.append(overlay, hint, box);

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "START_ZONE_SELECT") {
      /* already open */
    }
  });
})();
