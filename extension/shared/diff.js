/**
 * Сравнение изображений (как в десктопном WatchAlert).
 */

export function imageDataBrightness(data) {
  let sum = 0;
  for (let i = 0; i < data.length; i += 4) {
    sum += (data[i] + data[i + 1] + data[i + 2]) / 3;
  }
  return sum / (data.length / 4);
}

export function cropImageData(full, fullW, fullH, zone) {
  const x = Math.floor(zone.x * fullW);
  const y = Math.floor(zone.y * fullH);
  const w = Math.max(1, Math.floor(zone.w * fullW));
  const h = Math.max(1, Math.floor(zone.h * fullH));
  const out = new Uint8ClampedArray(w * h * 4);
  for (let row = 0; row < h; row++) {
    for (let col = 0; col < w; col++) {
      const src = ((y + row) * fullW + (x + col)) * 4;
      const dst = (row * w + col) * 4;
      out[dst] = full[src];
      out[dst + 1] = full[src + 1];
      out[dst + 2] = full[src + 2];
      out[dst + 3] = 255;
    }
  }
  return { data: out, w, h };
}

export function downsample(data, w, h, size = 64) {
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext("2d");
  const tmp = new OffscreenCanvas(w, h);
  const tctx = tmp.getContext("2d");
  const img = tctx.createImageData(w, h);
  img.data.set(data);
  tctx.putImageData(img, 0, 0);
  ctx.drawImage(tmp, 0, 0, size, size);
  return ctx.getImageData(0, 0, size, size).data;
}

export function imagesDiffer(a, b, aw, ah, bw, bh, threshold = 8) {
  const da = downsample(a, aw, ah);
  const db = downsample(b, bw, bh);
  let diff = 0;
  for (let i = 0; i < da.length; i += 4) {
    diff +=
      (Math.abs(da[i] - db[i]) +
        Math.abs(da[i + 1] - db[i + 1]) +
        Math.abs(da[i + 2] - db[i + 2])) /
      3;
  }
  return diff / (da.length / 4) >= threshold;
}

export class ChangeTracker {
  constructor(delaySeconds, sensitivity = 8) {
    this.delaySeconds = delaySeconds;
    this.sensitivity = sensitivity;
    this.reference = null;
    this.refW = 0;
    this.refH = 0;
    this.changeSince = null;
  }

  process(data, w, h, nowMs) {
    if (!this.reference) {
      this.reference = new Uint8ClampedArray(data);
      this.refW = w;
      this.refH = h;
      this.changeSince = null;
      return false;
    }
    const changed = imagesDiffer(
      this.reference,
      data,
      this.refW,
      this.refH,
      w,
      h,
      this.sensitivity
    );
    if (changed) {
      if (this.changeSince === null) this.changeSince = nowMs;
      else if (nowMs - this.changeSince >= this.delaySeconds * 1000) {
        this.reference = new Uint8ClampedArray(data);
        this.refW = w;
        this.refH = h;
        this.changeSince = null;
        return true;
      }
    } else {
      this.changeSince = null;
    }
    return false;
  }
}
