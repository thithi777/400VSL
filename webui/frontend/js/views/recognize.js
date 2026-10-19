// Nhận diện tự do: làm một ký hiệu bất kỳ -> top-5 trong 400 ký hiệu, xem lại bản ghi, lịch sử phiên.
import { analyze } from '../api.js';
import { h, replace } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { percent } from '../lib/format.js';
import { addHistory, getHistory, loadStatus, onHistory } from '../store.js';
import { createFramePlayer } from '../components/framePlayer.js';
import { createHistoryStrip } from '../components/historyStrip.js';
import { createInputPanel } from '../components/inputPanel.js';
import { createProgressBar } from '../components/progressBar.js';
import { createTop5 } from '../components/topPredictions.js';

function card(title, body, extra = null) {
  return h('section', { class: 'card' },
    h('div', { class: 'card__head' }, h('h2', { class: 'card__title' }, title), extra),
    h('div', { class: 'card__body' }, body));
}

export async function recognizeView() {
  const status = await loadStatus();
  let abort = null;
  let busy = false;
  let replay = null;
  let currentId = null;

  const input = createInputPanel({ capture: status.capture, onSubmit: (payload) => run(payload) });

  const replaySlot = h('div');
  const resultBody = h('div', { class: 'stack', 'aria-live': 'polite' },
    h('p', { class: 'empty' }, 'Chưa có kết quả. Bấm Bắt đầu ghi hoặc tải một video lên.'));
  const historyBody = h('div');

  function renderHistory() {
    replace(historyBody, createHistoryStrip({
      entries: getHistory((e) => e.mode === 'free'),
      currentId,
      onSelect: (e) => showResult(e),
    }));
  }

  function showResult(entry) {
    const { result } = entry;
    currentId = entry.id;
    const top1 = result.top5[0];

    if (replay) replay.destroy();
    replay = createFramePlayer({ frames: result.preview, fps: result.fps });
    replace(replaySlot, card('Xem lại', replay.el));

    const t = result.timing;
    replace(resultBody,
      h('div', { class: 'prediction reveal' },
        h('span', { class: 'eyebrow' }, 'Ký hiệu nhận ra'),
        h('span', { class: 'prediction__gloss' }, top1.gloss),
        h('div', { class: 'prediction__prob' },
          h('div', { class: 'bar' }, h('span', { class: 'bar__fill', style: { '--value': top1.prob.toFixed(4) } })),
          h('span', {}, percent(top1.prob))),
        h('a', { class: 'prediction__link', href: `#/bai/${top1.label}` }, 'Học ký hiệu này với video mẫu', ' ', icon('arrowRight'))),
      createTop5(result.top5),
      result.quality.warnings.map((w) => h('div', { class: 'notice notice--warn' }, icon('alert'), h('span', {}, w))),
      h('p', { class: 'timing' },
        h('span', {}, `${result.frames} frame · ${String(result.fps).replace('.', ',')} fps`),
        h('span', {}, `keypoint ${t.extract_ms} ms`),
        h('span', {}, `model ${t.model_ms} ms`)));
    renderHistory();
  }

  async function run(payload) {
    if (busy) return;
    busy = true;
    input.setBusy(true);
    abort = new AbortController();
    const progress = createProgressBar();
    replace(resultBody, h('p', { class: 'eyebrow' }, 'Đang phân tích'), progress.el);
    try {
      const result = await analyze(payload, { onProgress: progress.update, signal: abort.signal });
      progress.finish();
      showResult(addHistory({ mode: 'free', result }));
    } catch (err) {
      if (err.name === 'AbortError') return;
      replace(resultBody, h('div', { class: 'notice notice--bad' }, icon('alert'), h('span', {}, `Không phân tích được: ${err.message}`)));
    } finally {
      busy = false;
      input.setBusy(false);
    }
  }

  const unsubscribe = onHistory(renderHistory);
  renderHistory();
  const latest = getHistory((e) => e.mode === 'free' && e.result)[0];
  if (latest) showResult(latest);

  const el = h('div', { class: 'page' },
    h('header', { class: 'page-head' },
      h('span', { class: 'eyebrow' }, 'Nhận diện tự do'),
      h('h1', { class: 'page-title' }, 'Làm một ký hiệu bất kỳ'),
      h('p', { class: 'page-lead' }, 'Mô hình chọn 5 ký hiệu gần nhất trong 400 ký hiệu. Mỗi lần ghi hoặc mỗi video chỉ nên có một ký hiệu.')),
    h('div', { class: 'recognize-grid' },
      h('div', { class: 'lesson-result__col' }, card('Nguồn', input.el), replaySlot),
      card('Kết quả', resultBody)),
    h('section', { class: 'stack' },
      h('h2', { class: 'section-title' }, 'Lịch sử phiên', h('span', { class: 'count' }, 'chỉ lưu trong tab này')),
      historyBody));

  return {
    el,
    title: 'Nhận diện tự do',
    onKey(event) {
      return input.handleKey(event);
    },
    destroy() {
      if (abort) abort.abort();
      unsubscribe();
      input.destroy();
      if (replay) replay.destroy();
    },
  };
}
