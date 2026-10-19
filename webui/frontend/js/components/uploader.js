// Ô kéo thả / chọn file video. Mỗi video chỉ nên chứa một ký hiệu.
import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';

const MAX_MB = 200;

export function createUploader({ onFile }) {
  const input = h('input', { type: 'file', accept: 'video/*,.mp4,.mov,.avi,.webm,.mkv', 'aria-label': 'Chọn file video' });
  const meta = h('p', { class: 'dropzone__meta' },
    'Kéo thả hoặc bấm để chọn. Mỗi video một ký hiệu, quay chính diện, thấy từ đầu tới hông.');
  const zone = h('label', { class: 'dropzone' },
    input,
    h('div', { class: 'dropzone__inner' },
      h('span', { class: 'dropzone__icon' }, icon('upload')),
      h('p', { class: 'dropzone__title' }, 'Tải video lên'),
      meta));

  let disabled = false;

  function take(file) {
    if (!file || disabled) return;
    if (!file.type.startsWith('video/') && !/\.(mp4|mov|avi|webm|mkv)$/i.test(file.name)) {
      meta.textContent = `“${file.name}” không phải file video.`;
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      meta.textContent = `File lớn hơn ${MAX_MB} MB.`;
      return;
    }
    meta.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1).replace('.', ',')} MB`;
    onFile({ kind: 'video', file });
  }

  input.addEventListener('change', () => {
    take(input.files[0]);
    input.value = '';
  });
  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('is-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('is-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('is-over');
    take(e.dataTransfer.files[0]);
  });

  return {
    el: zone,
    setBusy(value) {
      disabled = value;
      input.disabled = value;
      zone.style.opacity = value ? '0.55' : '';
    },
    destroy() {},
  };
}
