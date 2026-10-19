// Phát lại đoạn đã phân tích (chỉ ảnh, không vẽ keypoint).
// frames: URL ảnh từng frame (webcam: blob: của chính ảnh vừa ghi; video tải lên: data: máy chủ trả về,
// vì video tải lên có thể ở codec trình duyệt không phát được).
import { containRect, fitCanvas, h } from '../lib/dom.js';
import { createControls } from './playerControls.js';

export function createFramePlayer({ frames, fps = 25, autoplay = true, label = 'Bản ghi của bạn' }) {
  const total = frames.length;
  const images = frames.map((src) => {
    const img = new Image();
    img.decoding = 'async';
    img.src = src;
    return img;
  });

  const canvas = h('canvas', { role: 'img', 'aria-label': label });
  const stage = h('div', { class: 'player__stage' }, canvas);
  const ctx = canvas.getContext('2d');

  let frame = 0;
  let playing = false;
  let speed = 1;
  let clock = 0;
  let last = 0;
  let raf = null;
  let destroyed = false;

  const controls = createControls({
    total,
    fps,
    onPlayToggle: () => (playing ? pause() : play()),
    onSeek: (i) => { pause(); setFrame(i); },
    onSpeed: (s) => { speed = s; },
  });

  function draw() {
    if (destroyed || !total) return;
    fitCanvas(canvas);
    ctx.fillStyle = '#1A1A19';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const img = images[frame];
    const iw = img.naturalWidth || 1;
    const ih = img.naturalHeight || 1;
    const r = containRect(iw, ih, canvas.width, canvas.height);
    if (img.complete && img.naturalWidth) ctx.drawImage(img, r.x, r.y, r.w, r.h);
  }

  function setFrame(i) {
    frame = ((i % total) + total) % total;
    clock = frame / fps;
    controls.setFrame(frame);
    draw();
  }

  function tick(now) {
    if (!playing) return;
    const dt = last ? (now - last) / 1000 : 0;
    last = now;
    clock += dt * speed;
    const next = Math.floor(clock * fps) % total;
    if (next !== frame) {
      frame = next;
      controls.setFrame(frame);
      draw();
    }
    if (clock * fps >= total) clock -= total / fps;
    raf = requestAnimationFrame(tick);
  }

  function play() {
    if (playing || !total) return;
    playing = true;
    last = 0;
    controls.setPlaying(true);
    raf = requestAnimationFrame(tick);
  }

  function pause() {
    playing = false;
    controls.setPlaying(false);
    if (raf !== null) cancelAnimationFrame(raf);
    raf = null;
  }

  images[0]?.addEventListener('load', draw, { once: true });
  const ro = new ResizeObserver(draw);
  ro.observe(stage);

  setFrame(0);
  if (autoplay) {
    Promise.all(images.map((img) => (img.decode ? img.decode().catch(() => {}) : null)))
      .then(() => { if (!destroyed) play(); });
  }

  const el = h('div', { class: 'player' }, stage, controls.el);
  return {
    el,
    play,
    pause,
    togglePlay: () => (playing ? pause() : play()),
    destroy() {
      destroyed = true;
      pause();
      ro.disconnect();
    },
  };
}
