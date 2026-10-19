// Thanh tiến độ phân tích (%), tính từ các bước máy chủ gửi về (NDJSON), kèm dòng chữ cho bước hiện tại.
// Phần lớn thời gian là trích keypoint nên bước này chiếm khoảng rộng nhất.
import { h } from '../lib/dom.js';

// Mạng chậm thì gửi ảnh lên là bước lâu nhất, nên bước này cũng chiếm một khoảng rộng
const STAGE_RANGE = {
  upload: [0, 30],
  queue: [30, 30],
  decode: [30, 34],
  extract: [34, 88],
  model: [88, 92],
  compare: [92, 96],
  preview: [96, 99],
};

const STAGE_TEXT = {
  decode: 'Đang đọc dữ liệu',
  extract: 'Đang trích khung xương',
  model: 'Mô hình đang nhận diện',
  compare: 'Đang so với video mẫu',
  preview: 'Đang nhận bản xem lại',
};

const mb = (bytes) => (bytes / 1024 / 1024).toFixed(1).replace('.', ',');

function uploadText({ current, total }) {
  if (!total) return 'Đang gửi lên máy chủ';
  if (current >= total) return 'Đã gửi xong, đang chờ máy chủ nhận đủ dữ liệu';
  return `Đang gửi lên máy chủ: ${mb(current)} / ${mb(total)} MB`;
}

function queueText({ current, eta }) {
  const wait = eta > 0 ? `, còn khoảng ${eta} giây` : '';
  return current <= 1
    ? `Đang chờ tới lượt: bạn đứng đầu hàng${wait}`
    : `Đang chờ tới lượt: còn ${current - 1} người phía trước${wait}`;
}

function stageText(event) {
  if (event.stage === 'upload') return uploadText(event);
  if (event.stage === 'queue') return queueText(event);
  return STAGE_TEXT[event.stage];
}

export function createProgressBar() {
  const fill = h('span', { class: 'bar__fill' });
  const value = h('span', { class: 'progress__value' }, '0 %');
  const note = h('span', { class: 'progress__note' }, uploadText({}));
  const el = h('div', {
    class: 'progress',
    role: 'progressbar',
    'aria-label': 'Tiến độ phân tích',
    'aria-valuemin': 0,
    'aria-valuemax': 100,
    'aria-valuenow': 0,
  }, h('div', { class: 'bar bar--live' }, fill), value, note);

  let pct = 0;

  function set(p) {
    pct = Math.max(pct, Math.min(100, p)); // không bao giờ lùi
    fill.style.setProperty('--value', (pct / 100).toFixed(3));
    value.textContent = `${Math.round(pct)} %`;
    el.setAttribute('aria-valuenow', String(Math.round(pct)));
  }

  function update(event) {
    const range = STAGE_RANGE[event.stage];
    if (!range) return;
    note.textContent = stageText(event);
    const frac = event.stage !== 'queue' && event.total > 0 ? event.current / event.total : 0;
    set(range[0] + (range[1] - range[0]) * frac);
  }

  return {
    el,
    update,
    finish: () => {
      note.textContent = 'Xong';
      set(100);
    },
  };
}
