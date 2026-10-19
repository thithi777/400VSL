// Khung nhập gồm hai tab: Webcam (ghi có đếm ngược) và Tải video.
// Đổi tab sẽ tắt camera; gọi onSubmit(input) khi có một đoạn sẵn sàng phân tích.
import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { createCapture } from './capture.js';
import { createUploader } from './uploader.js';

export function createInputPanel({ capture: captureCfg, onSubmit, initial = 'webcam' }) {
  const body = h('div', { class: 'input-panel__body' });
  let current = null;
  let mode = null;
  let busy = false;

  const tabs = {
    webcam: h('button', { class: 'tabs__btn', type: 'button', role: 'tab' }, icon('camera'), 'Webcam'),
    upload: h('button', { class: 'tabs__btn', type: 'button', role: 'tab' }, icon('upload'), 'Tải video'),
  };

  function select(next) {
    if (next === mode) return;
    if (current) current.destroy();
    mode = next;
    Object.entries(tabs).forEach(([key, btn]) => btn.setAttribute('aria-selected', String(key === next)));
    current = next === 'webcam'
      ? createCapture({
        countdown: captureCfg.countdown,
        frames: captureCfg.frames,
        fps: captureCfg.fps,
        maxSide: captureCfg.max_side,
        quality: captureCfg.jpeg_quality,
        onCaptured: onSubmit,
      })
      : createUploader({ onFile: onSubmit });
    current.setBusy(busy);
    body.replaceChildren(current.el);
  }

  tabs.webcam.addEventListener('click', () => select('webcam'));
  tabs.upload.addEventListener('click', () => select('upload'));

  const el = h('div', { class: 'stack input-panel' },
    h('div', { class: 'tabs', role: 'tablist', 'aria-label': 'Nguồn video' }, tabs.webcam, tabs.upload),
    body);

  select(initial);

  return {
    el,
    get mode() { return mode; },
    setBusy(value) {
      busy = value;
      current?.setBusy(value);
    },
    /** Phím tắt: Space ghi, Esc huỷ (chỉ ở tab webcam). Trả true nếu đã xử lý. */
    handleKey(event) {
      if (mode !== 'webcam' || !current) return false;
      if (event.code === 'Space') {
        current.record();
        return true;
      }
      if (event.key === 'Escape') {
        current.cancel();
        return true;
      }
      return false;
    },
    destroy() {
      current?.destroy();
      current = null;
    },
  };
}
