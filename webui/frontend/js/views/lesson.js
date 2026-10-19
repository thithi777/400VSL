// Trang bài học: video mẫu | lượt của bạn (webcam hoặc tải video) -> kết luận, nhận xét, điểm từng bộ phận.
import { analyze, getLesson } from '../api.js';
import { h, replace } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { clock, seconds, VERDICT } from '../lib/format.js';
import { addHistory, getHistory, getProgress, loadStatus, onHistory, setProgress } from '../store.js';
import { createFramePlayer } from '../components/framePlayer.js';
import { createInputPanel } from '../components/inputPanel.js';
import { progressBadge } from '../components/lessonTile.js';
import { createFeedback, createParts, createVerdict } from '../components/practiceResult.js';
import { createReferencePlayer } from '../components/referencePlayer.js';
import { createProgressBar } from '../components/progressBar.js';
import { createTop5 } from '../components/topPredictions.js';

function card(title, body, extra = null) {
  return h('section', { class: 'card' },
    h('div', { class: 'card__head' }, h('h2', { class: 'card__title' }, title), extra),
    h('div', { class: 'card__body' }, body));
}

export async function lessonView({ label }) {
  const [status, lesson] = await Promise.all([loadStatus(), getLesson(label)]);
  const capture = status.capture;
  const disposables = new Set();
  let resultDisposables = [];
  let abort = null;
  let busy = false;

  // ---------------- Đầu trang ----------------
  const progressSlot = h('span');
  const refreshProgress = () => replace(progressSlot, progressBadge(getProgress(label)));
  refreshProgress();

  const navBtn = (target, dir) => (target
    ? h('a', { class: 'btn btn--secondary btn--sm', href: `#/bai/${target.label}`, title: `${target.gloss} (phím ${dir === 'prev' ? '←' : '→'})` },
      dir === 'prev' ? icon('arrowLeft') : null,
      h('span', { class: 'label' }, target.gloss),
      dir === 'next' ? icon('arrowRight') : null)
    : null);

  const head = h('header', { class: 'lesson-head' },
    h('div', {},
      h('nav', { class: 'breadcrumb', 'aria-label': 'Đường dẫn' },
        h('a', { href: '#/' }, 'Bài học'),
        h('span', { class: 'breadcrumb__sep' }, '/'),
        h('a', { href: `#/chu-de/${lesson.topic.id}` }, lesson.topic.name)),
      h('h1', { class: 'lesson-title' }, lesson.gloss),
      h('div', { class: 'lesson-meta' },
        h('span', { class: 'mono' }, `Bài ${lesson.position}/${lesson.count}`),
        h('span', {}, lesson.topic.group),
        progressSlot)),
    h('nav', { class: 'lesson-nav', 'aria-label': 'Bài trước và bài sau' },
      navBtn(lesson.prev, 'prev'),
      navBtn(lesson.next, 'next')));

  // ---------------- Video mẫu ----------------
  let refPlayer = null;
  let refBody;
  if (lesson.reference) {
    refPlayer = createReferencePlayer({
      src: lesson.reference.video_url,
      frames: lesson.reference.frames,
      fps: lesson.reference.fps,
    });
    disposables.add(refPlayer);
    refBody = h('div', {},
      refPlayer.el,
      h('p', { class: 'lesson-note' },
        `Người biểu diễn ${lesson.reference.signer} · ${seconds(lesson.reference.frames / lesson.reference.fps)}. `
        + 'Video không lật gương: tay phải của người mẫu nằm ở bên trái màn hình.'));
  } else {
    refBody = h('p', { class: 'empty' }, 'Bài này chưa có video mẫu. Chạy scripts/build_references.py để tạo.');
  }

  // ---------------- Lượt của bạn ----------------
  const input = createInputPanel({ capture, onSubmit: (payload) => run(payload) });
  disposables.add(input);

  const steps = h('ol', { class: 'steps' },
    h('li', {}, h('b', {}, '1'), 'Đứng chính diện, thấy từ đầu tới hông'),
    h('li', {}, h('b', {}, '2'), `${capture.countdown} giây chuẩn bị`),
    h('li', {}, h('b', {}, '3'), `Làm ký hiệu trong ${seconds(capture.frames / capture.fps)}`));

  const stage = h('div', { class: 'lesson-stage' },
    card('Video mẫu', refBody),
    card('Lượt của bạn', h('div', { class: 'stack' }, input.el, steps)));

  // ---------------- Kết quả + các lần thử ----------------
  const resultArea = h('div', { class: 'result-block', 'aria-live': 'polite' });
  const attemptsBody = h('div');

  function renderAttempts() {
    const entries = getHistory((e) => e.mode === 'practice' && e.label === label);
    if (!entries.length) {
      replace(attemptsBody, h('p', { class: 'muted' }, 'Chưa có lần thử nào trong phiên này.'));
      return;
    }
    replace(attemptsBody, h('ol', { class: 'attempts' },
      entries.map((e, i) => h('li', { class: 'attempts__item' },
        h('span', { class: 'attempts__time' }, `Lần ${entries.length - i}`),
        h('span', { class: `badge badge--${VERDICT[e.verdict].tone}` }, VERDICT[e.verdict].label),
        e.result
          ? h('button', { type: 'button', onClick: () => showResult(e) }, `Điểm ${e.score}/100`)
          : h('span', { class: 'muted' }, `Điểm ${e.score}/100`),
        h('span', { class: 'attempts__time' }, clock(e.time))))));
  }

  function disposeResult() {
    resultDisposables.forEach((d) => d.destroy());
    resultDisposables = [];
  }

  function showResult(entry) {
    disposeResult();
    const { result } = entry;
    const p = result.practice;

    const replay = createFramePlayer({ frames: result.preview, fps: result.fps });
    resultDisposables.push(replay);

    const warnings = result.quality.warnings.map((w) => h('div', { class: 'notice notice--warn' }, icon('alert'), h('span', {}, w)));
    const t = result.timing;

    replace(resultArea,
      createVerdict(p),
      warnings,
      h('div', { class: 'lesson-result' },
        h('div', { class: 'lesson-result__col' },
          card('Nhận xét', createFeedback(p.feedback)),
          card('Điểm từng bộ phận', createParts(p.parts),
            h('span', { class: 'muted', style: { fontSize: '13px' } }, 'so với video mẫu'))),
        h('div', { class: 'lesson-result__col' },
          card('Bản ghi của bạn', replay.el),
          card('Mô hình đoán', createTop5(result.top5, { target: label })))),
      h('p', { class: 'timing' },
        h('span', {}, `${result.frames} frame`),
        h('span', {}, `keypoint ${t.extract_ms} ms`),
        h('span', {}, `model ${t.model_ms} ms`),
        t.compare_ms !== undefined ? h('span', {}, `DTW ${t.compare_ms} ms`) : null));
    renderAttempts();
  }

  async function run(payload) {
    if (busy) return;
    busy = true;
    input.setBusy(true);
    disposeResult();
    abort = new AbortController();

    const progress = createProgressBar();
    replace(resultArea, card('Đang phân tích', progress.el));
    if (resultArea.getBoundingClientRect().top > window.innerHeight - 120) {
      resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    try {
      const result = await analyze(payload, { target: label, onProgress: progress.update, signal: abort.signal });
      progress.finish();
      const entry = addHistory({ mode: 'practice', label, result });
      setProgress(label, result.practice.progress);
      refreshProgress();
      showResult(entry);
    } catch (err) {
      if (err.name === 'AbortError') return;
      replace(resultArea, h('div', { class: 'notice notice--bad' }, icon('alert'),
        h('span', {}, `Không phân tích được: ${err.message}`)));
    } finally {
      busy = false;
      input.setBusy(false);
    }
  }

  const unsubscribe = onHistory(renderAttempts);
  renderAttempts();

  // Mở lại lần thử gần nhất của bài này (nếu quay lại trang trong cùng phiên)
  const latest = getHistory((e) => e.mode === 'practice' && e.label === label && e.result)[0];
  if (latest) showResult(latest);
  else {
    resultArea.append(h('p', { class: 'empty' },
      'Kết quả sẽ hiện ở đây: mô hình có nhận ra ký hiệu không, bộ phận nào chưa giống mẫu, và bản ghi để bạn xem lại.'));
  }

  const el = h('div', { class: 'page' },
    head,
    stage,
    resultArea,
    card('Các lần thử trong phiên', attemptsBody));

  return {
    el,
    title: lesson.gloss,
    onKey(event) {
      if (input.handleKey(event)) return true;
      if (busy) return false;
      if (event.key === 'ArrowLeft' && lesson.prev) {
        window.location.hash = `#/bai/${lesson.prev.label}`;
        return true;
      }
      if (event.key === 'ArrowRight' && lesson.next) {
        window.location.hash = `#/bai/${lesson.next.label}`;
        return true;
      }
      if (event.key === 'p' && refPlayer) {
        refPlayer.togglePlay();
        return true;
      }
      return false;
    },
    destroy() {
      if (abort) abort.abort();
      unsubscribe();
      disposeResult();
      disposables.forEach((d) => d.destroy());
    },
  };
}
