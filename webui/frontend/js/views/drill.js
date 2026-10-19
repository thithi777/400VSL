// Luyện tập: bốc ngẫu nhiên một ký hiệu chưa đạt trong phạm vi (một chủ đề hoặc cả 400 ký hiệu),
// người học tự biểu diễn, không có video mẫu. Chấm xong chọn: luyện lại ký hiệu đó, hoặc bốc ký hiệu khác.
// Ký hiệu đã làm đúng (máy chủ lưu theo tài khoản) không bị bốc lại.
import { analyze } from '../api.js';
import { h, replace } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { seconds } from '../lib/format.js';
import { addHistory, clearDrill, getDrill, loadCatalog, loadDrill, loadStatus, setDrill } from '../store.js';
import { createFramePlayer } from '../components/framePlayer.js';
import { createInputPanel } from '../components/inputPanel.js';
import { createFeedback, createParts, createVerdict } from '../components/practiceResult.js';
import { createProgressBar } from '../components/progressBar.js';
import { createTop5 } from '../components/topPredictions.js';
import { ALL_SCOPE } from './drillMenu.js';

function card(title, body, extra = null) {
  return h('section', { class: 'card' },
    h('div', { class: 'card__head' }, h('h2', { class: 'card__title' }, title), extra),
    h('div', { class: 'card__body' }, body));
}

export async function drillView({ scope }) {
  const [status, catalog] = await Promise.all([loadStatus(), loadCatalog(), loadDrill()]);
  const topic = scope === ALL_SCOPE ? null : catalog.topics.get(scope);
  if (scope !== ALL_SCOPE && !topic) throw new Error(`Không có chủ đề “${scope}”.`);

  const labels = topic ? topic.labels : catalog.lessons.map((l) => l.label);
  const scopeName = topic ? topic.name : `Tất cả ${labels.length} ký hiệu`;
  const capture = status.capture;

  let current = null;
  let input = null;
  let resultDisposables = [];
  let abort = null;
  let busy = false;
  let hasResult = false;

  const remaining = () => labels.filter((l) => !getDrill(l)?.passed);

  /** Ký hiệu chưa đạt ngẫu nhiên; tránh ký hiệu vừa làm nếu còn lựa chọn khác. null khi đã đạt hết. */
  function pick(avoid = null) {
    const pool = remaining();
    const choices = pool.length > 1 ? pool.filter((l) => l !== avoid) : pool;
    return choices.length ? choices[Math.floor(Math.random() * choices.length)] : null;
  }

  // ---------------- Đầu trang: phạm vi + số đã đạt ----------------
  const counter = h('div', { class: 'drill-counter' });
  function renderCounter() {
    const passed = labels.length - remaining().length;
    replace(counter,
      h('span', { class: 'mono' }, `${passed}/${labels.length} đạt`),
      h('span', { class: 'bar bar--thin bar--good' },
        h('span', { class: 'bar__fill', style: { '--value': (passed / labels.length).toFixed(3) } })));
  }

  const head = h('header', { class: 'drill-head' },
    h('nav', { class: 'breadcrumb', 'aria-label': 'Đường dẫn' },
      h('a', { href: '#/luyen-tap' }, 'Luyện tập'),
      h('span', { class: 'breadcrumb__sep' }, '/'),
      h('span', {}, scopeName)),
    counter);

  // ---------------- Ký hiệu cần làm | lượt của bạn ----------------
  const promptBody = h('div', { class: 'drill-prompt' });
  const stageSlot = h('div');

  function renderPrompt() {
    const lesson = catalog.byLabel.get(current);
    const tries = getDrill(current)?.attempts || 0;
    replace(promptBody,
      h('div', { class: 'drill-prompt__word reveal' },
        h('h1', { class: 'lesson-title drill-prompt__gloss' }, lesson.gloss),
        h('div', { class: 'lesson-meta' },
          topic ? null : h('span', {}, catalog.topics.get(lesson.topic).name),
          tries ? h('span', { class: 'mono' }, `Đã thử ${tries} lần`) : null)),
      h('p', { class: 'lesson-note' }, 'Không có video mẫu. Hãy nhớ lại cách làm rồi biểu diễn.'),
      h('ol', { class: 'steps' },
        h('li', {}, h('b', {}, '1'), 'Đứng chính diện, thấy từ đầu tới hông'),
        h('li', {}, h('b', {}, '2'), `${capture.countdown} giây chuẩn bị`),
        h('li', {}, h('b', {}, '3'), `Làm ký hiệu trong ${seconds(capture.frames / capture.fps)}`)));
  }

  function mountStage() {
    if (input) return;
    input = createInputPanel({ capture, onSubmit: (payload) => run(payload) });
    replace(stageSlot, h('div', { class: 'lesson-stage' },
      h('section', { class: 'card drill-prompt-card' },
        h('div', { class: 'card__head' }, h('h2', { class: 'card__title' }, 'Hãy biểu diễn ký hiệu')),
        h('div', { class: 'card__body' }, promptBody)),
      card('Lượt của bạn', input.el)));
  }

  // ---------------- Kết quả ----------------
  const resultArea = h('div', { class: 'result-block', 'aria-live': 'polite' });

  function disposeResult() {
    resultDisposables.forEach((d) => d.destroy());
    resultDisposables = [];
    hasResult = false;
  }

  function showWord(label) {
    disposeResult();
    current = label;
    if (current === null) {
      showDone();
      return;
    }
    mountStage();
    renderPrompt();
    replace(resultArea, h('p', { class: 'empty' },
      'Kết quả sẽ hiện ở đây. Chấm xong bạn chọn luyện lại ký hiệu này hoặc chuyển sang ký hiệu khác.'));
  }

  const retry = () => {
    showWord(current);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const next = () => {
    showWord(pick(current));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  async function restart(event) {
    const btn = event.currentTarget;
    btn.disabled = true;
    try {
      await clearDrill(labels);
      renderCounter();
      showWord(pick());
    } catch (err) {
      btn.disabled = false;
      replace(resultArea, h('div', { class: 'notice notice--bad' }, icon('alert'),
        h('span', {}, `Không đặt lại được: ${err.message}`)));
    }
  }

  function showDone() {
    input?.destroy(); // tắt camera
    input = null;
    replace(stageSlot, h('section', { class: 'card drill-done reveal' },
      h('span', { class: 'badge badge--good' }, 'Hoàn thành'),
      h('p', { class: 'verdict__headline' },
        topic
          ? `Bạn đã làm đúng cả ${labels.length} ký hiệu của chủ đề “${topic.name}”.`
          : `Bạn đã làm đúng cả ${labels.length} ký hiệu.`),
      h('div', { class: 'row' },
        h('button', { class: 'btn btn--primary', type: 'button', onClick: restart }, icon('refresh'), 'Luyện lại từ đầu'),
        h('a', { class: 'btn btn--secondary', href: '#/luyen-tap' }, 'Chọn phạm vi khác'))));
    replace(resultArea);
  }

  function showResult(entry) {
    disposeResult();
    hasResult = true;
    const { result } = entry;
    const p = result.practice;
    const passed = p.verdict === 'pass';

    const replay = createFramePlayer({ frames: result.preview, fps: result.fps });
    resultDisposables.push(replay);

    const warnings = result.quality.warnings.map((w) => h('div', { class: 'notice notice--warn' }, icon('alert'), h('span', {}, w)));
    // Làm đúng thì gợi ý sang ký hiệu khác, chưa đúng thì gợi ý làm lại
    const actions = h('div', { class: 'drill-actions' },
      h('button', {
        class: `btn ${passed ? 'btn--secondary' : 'btn--primary'}`, type: 'button', onClick: retry,
      }, icon('refresh'), 'Luyện lại', h('kbd', {}, 'R')),
      h('button', {
        class: `btn ${passed ? 'btn--primary' : 'btn--secondary'}`, type: 'button', onClick: next,
      }, remaining().length ? 'Ký hiệu khác' : 'Hoàn thành', h('kbd', {}, 'N'), icon('arrowRight')));

    replace(resultArea,
      createVerdict(p),
      actions,
      warnings,
      h('div', { class: 'lesson-result' },
        h('div', { class: 'lesson-result__col' },
          card('Nhận xét', createFeedback(p.feedback)),
          card('Điểm từng bộ phận', createParts(p.parts),
            h('span', { class: 'muted', style: { fontSize: '13px' } }, 'so với video mẫu'))),
        h('div', { class: 'lesson-result__col' },
          card('Bản ghi của bạn', replay.el),
          card('Mô hình đoán', createTop5(result.top5, { target: p.target.label })))));
  }

  async function run(payload) {
    if (busy || current === null) return;
    busy = true;
    input.setBusy(true);
    disposeResult();
    abort = new AbortController();
    const label = current;

    const progress = createProgressBar();
    replace(resultArea, card('Đang chấm', progress.el));
    if (resultArea.getBoundingClientRect().top > window.innerHeight - 120) {
      resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    try {
      const result = await analyze(payload, { target: label, drill: true, onProgress: progress.update, signal: abort.signal });
      progress.finish();
      const entry = addHistory({ mode: 'drill', label, result });
      setDrill(label, result.practice.progress);
      renderCounter();
      showResult(entry);
    } catch (err) {
      if (err.name === 'AbortError') return;
      replace(resultArea, h('div', { class: 'notice notice--bad' }, icon('alert'),
        h('span', {}, `Không phân tích được: ${err.message}`)));
    } finally {
      busy = false;
      input?.setBusy(false);
    }
  }

  renderCounter();
  showWord(pick());

  const el = h('div', { class: 'page' }, head, stageSlot, resultArea);

  return {
    el,
    title: `Luyện tập · ${scopeName}`,
    onKey(event) {
      if (input?.handleKey(event)) return true;
      if (busy || !hasResult) return false;
      const key = event.key.toLowerCase();
      if (key === 'r') {
        retry();
        return true;
      }
      if (key === 'n') {
        next();
        return true;
      }
      return false;
    },
    destroy() {
      if (abort) abort.abort();
      disposeResult();
      input?.destroy();
    },
  };
}
