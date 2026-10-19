// Webcam: xem trước (lật gương cho dễ làm theo), đếm ngược, ghi đúng N frame ở fps cố định.
// Frame gửi đi KHÔNG lật và được cắt vuông ở giữa, giống video train 1080 x 1080 quay chính diện,
// rồi thu nhỏ còn maxSide (máy chủ quyết định qua /api/status) để gửi nhanh trên mạng chậm.
import { h } from '../lib/dom.js';
import { seconds } from '../lib/format.js';

// Vị trí trung bình trong video train (frame đầu): mũi y 0,37 · vai y 0,49 (rộng 0,20) · hông y 0,80
const GUIDE_SVG = `
<svg class="capture__guide" viewBox="0 0 100 100" aria-hidden="true">
  <g fill="none" stroke="currentColor" stroke-width="0.45" stroke-dasharray="1.6 1.3" stroke-linecap="round">
    <ellipse cx="49" cy="35" rx="6.3" ry="8.3"/>
    <path d="M45.6 43.2 V46 Q38.6 46.4 37 50 L35.4 80 M52.4 43.2 V46 Q59.4 46.4 61 50 L62.6 80"/>
    <path d="M24 49 H31 M67 49 H74 M24 80 H31 M67 80 H74" stroke-dasharray="none"/>
  </g>
  <g fill="currentColor" font-size="3.1" font-family="Be Vietnam Pro, Segoe UI, sans-serif">
    <text x="75.5" y="50.1">vai</text>
    <text x="75.5" y="81.1">hông</text>
  </g>
</svg>`;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function createCapture({ countdown = 3, frames = 64, fps = 25, maxSide = 540, quality = 0.85, onCaptured }) {
  const video = h('video', { playsinline: true, muted: true, 'aria-label': 'Xem trước webcam' });
  video.muted = true;
  const guide = h('div', { html: GUIDE_SVG });
  const count = h('div', { class: 'capture__count', 'aria-live': 'assertive' });
  const statusPill = h('span', { class: 'capture__pill' }, 'Đang mở camera');
  const infoPill = h('span', { class: 'capture__pill' });
  const progressBar = h('span');
  const progress = h('div', { class: 'capture__progress', hidden: true }, progressBar);
  const message = h('div', { class: 'capture__message', hidden: true });

  const stage = h('div', { class: 'capture__stage' },
    video,
    guide.firstElementChild,
    h('div', { class: 'capture__hud' }, statusPill, infoPill),
    count,
    progress,
    message);

  const recordBtn = h('button', { class: 'btn btn--primary btn--rec', type: 'button', disabled: true },
    h('span', { class: 'rec-dot' }), 'Bắt đầu ghi', h('kbd', {}, 'Space'));
  const cancelBtn = h('button', { class: 'btn btn--ghost', type: 'button', hidden: true }, 'Huỷ', h('kbd', {}, 'Esc'));
  const hint = h('p', { class: 'capture__hint' },
    `${countdown} giây chuẩn bị, sau đó ghi ${seconds(frames / fps)} (${frames} frame).`);

  const el = h('div', { class: 'capture', dataset: { state: 'starting' } },
    stage,
    h('div', { class: 'capture__controls' }, recordBtn, cancelBtn, hint));

  let stream = null;
  let state = 'starting';
  let busy = false;
  let cancelled = false;
  let destroyed = false;

  function setState(next) {
    state = next;
    el.dataset.state = next;
    recordBtn.disabled = next !== 'ready' || busy;
    cancelBtn.hidden = !(next === 'countdown' || next === 'recording');
    progress.hidden = next !== 'recording';
    if (next !== 'countdown') count.replaceChildren();
    if (next === 'ready') statusPill.replaceChildren(busy ? 'Đang phân tích lượt trước' : 'Sẵn sàng');
  }

  function showError(text) {
    message.hidden = false;
    message.replaceChildren(h('p', {}, text));
    statusPill.replaceChildren('Không có camera');
    setState('error');
  }

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia) {
      showError('Trình duyệt không cho dùng webcam. Hãy mở trang bằng http://127.0.0.1 hoặc localhost trên Chrome/Edge.');
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 }, facingMode: 'user' },
        audio: false,
      });
      if (destroyed) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      video.srcObject = stream;
      await video.play();
      const side = Math.min(video.videoWidth, video.videoHeight);
      const out = Math.min(side, maxSide);
      infoPill.replaceChildren(`${out} × ${out} · ${fps} fps`);
      setState('ready');
    } catch (err) {
      if (destroyed) return;
      const name = err?.name || '';
      if (name === 'NotAllowedError') showError('Chưa được cấp quyền camera. Bấm biểu tượng camera trên thanh địa chỉ để cho phép, rồi tải lại trang.');
      else if (name === 'NotFoundError' || name === 'OverconstrainedError') showError('Không tìm thấy webcam nào.');
      else if (name === 'NotReadableError') showError('Webcam đang được ứng dụng khác dùng. Hãy tắt ứng dụng đó rồi tải lại trang.');
      else showError(`Không mở được webcam: ${err?.message || name}`);
    }
  }

  function cropRect() {
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    const side = Math.min(vw, vh);
    return { sx: (vw - side) / 2, sy: (vh - side) / 2, side, out: Math.min(side, maxSide) };
  }

  function grab(crop) {
    if (window.createImageBitmap) {
      return createImageBitmap(video, crop.sx, crop.sy, crop.side, crop.side, {
        resizeWidth: crop.out,
        resizeHeight: crop.out,
        resizeQuality: 'high',
      });
    }
    const c = document.createElement('canvas');
    c.width = crop.out;
    c.height = crop.out;
    c.getContext('2d').drawImage(video, crop.sx, crop.sy, crop.side, crop.side, 0, 0, crop.out, crop.out);
    return Promise.resolve(c);
  }

  async function encode(sources, size) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    const blobs = [];
    for (const src of sources) {
      ctx.drawImage(src, 0, 0, size, size);
      if (src.close) src.close();
      // eslint-disable-next-line no-await-in-loop
      blobs.push(await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality)));
    }
    return blobs;
  }

  async function record() {
    if (state !== 'ready' || busy) return;
    cancelled = false;

    // 1. Đếm ngược để người biểu diễn chuẩn bị
    setState('countdown');
    statusPill.replaceChildren('Chuẩn bị');
    for (let n = countdown; n >= 1; n -= 1) {
      count.replaceChildren(h('span', {}, String(n)));
      // eslint-disable-next-line no-await-in-loop
      await sleep(1000);
      if (cancelled || destroyed) { setState('ready'); return; }
    }

    // 2. Ghi đúng `frames` frame, mỗi frame cách nhau 1000/fps ms
    setState('recording');
    const crop = cropRect();
    const interval = 1000 / fps;
    const grabs = [];
    const t0 = performance.now();
    for (let k = 0; k < frames; k += 1) {
      const wait = t0 + k * interval - performance.now();
      // eslint-disable-next-line no-await-in-loop
      if (wait > 0) await sleep(wait);
      if (cancelled || destroyed) break;
      grabs.push(grab(crop));
      progressBar.style.setProperty('--value', String((k + 1) / frames));
      statusPill.replaceChildren(h('span', { class: 'rec-dot' }), `Đang ghi ${seconds((k + 1) / fps)} / ${seconds(frames / fps)}`);
    }
    const sources = await Promise.all(grabs);
    if (cancelled || destroyed) {
      sources.forEach((s) => s.close && s.close());
      setState('ready');
      return;
    }

    // 3. Nén JPEG rồi giao cho nơi gọi
    setState('encoding');
    statusPill.replaceChildren('Đang nén ảnh');
    const blobs = await encode(sources, crop.out);
    if (destroyed) return;
    setState('ready');
    onCaptured({ kind: 'frames', blobs, fps, size: crop.out });
  }

  function cancel() {
    if (state === 'countdown' || state === 'recording') cancelled = true;
  }

  recordBtn.addEventListener('click', record);
  cancelBtn.addEventListener('click', cancel);

  start();

  return {
    el,
    record,
    cancel,
    get state() { return state; },
    setBusy(value) {
      busy = value;
      if (state === 'ready') setState('ready');
    },
    destroy() {
      destroyed = true;
      cancelled = true;
      if (stream) stream.getTracks().forEach((t) => t.stop());
      video.srcObject = null;
    },
  };
}
