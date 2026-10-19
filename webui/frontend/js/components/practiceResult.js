// Kết quả một lượt luyện: kết luận, điểm từng bộ phận, nhận xét.
import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { percent, tone, VERDICT } from '../lib/format.js';

const PHASE_NAMES = ['Đầu', 'Giữa', 'Cuối'];

export function createVerdict(practice) {
  const v = VERDICT[practice.verdict];
  return h('section', { class: 'card verdict reveal', 'aria-label': 'Kết luận' },
    h('div', { class: 'verdict__main' },
      h('span', { class: `badge badge--${v.tone}` }, v.label),
      h('p', { class: 'verdict__headline' }, practice.headline)),
    h('div', { class: 'stats' },
      h('div', {
        class: 'stat stat--main',
        title: 'Điểm bài = 70 % độ tin cậy của mô hình + 30 % độ giống video mẫu',
      },
      h('span', { class: 'stat__value' }, String(practice.score), h('small', {}, ' /100')),
      h('span', { class: 'stat__label' }, 'Điểm')),
      h('div', { class: 'stat', title: 'Xác suất mô hình SDA-GCN gán cho ký hiệu của bài này' },
        h('span', { class: 'stat__value' }, percent(practice.prob, 0).replace(' %', ''), h('small', {}, ' %')),
        h('span', { class: 'stat__label' }, `Mô hình · hạng ${practice.rank}`)),
      h('div', { class: 'stat', title: 'So khung xương với video mẫu bằng DTW, 0 đến 100' },
        h('span', { class: 'stat__value' }, String(practice.similarity), h('small', {}, ' /100')),
        h('span', { class: 'stat__label' }, 'Giống mẫu'))));
}

export function createParts(parts) {
  return h('ul', { class: 'parts' },
    parts.map((p, i) => h('li', {
      class: `parts__item reveal${p.active ? '' : ' is-inactive'}`,
      style: { '--i': i },
      title: p.active ? '' : 'Video mẫu gần như không dùng tay này nên điểm ít ảnh hưởng',
    },
    h('span', { class: 'parts__name' },
      h('span', { class: `parts__swatch parts__swatch--${p.side}` }),
      p.name,
      p.active ? null : h('span', { class: 'badge' }, 'ít dùng')),
    h('div', { class: `bar bar--${tone(p.score)}` }, h('span', { class: 'bar__fill', style: { '--value': (p.score / 100).toFixed(3) } })),
    h('span', { class: 'parts__score' }, String(p.score)),
    h('div', { class: 'parts__phases' },
      p.phases.map((s, k) => h('span', { class: `parts__phase ${s === null ? '' : `tone-${tone(s)}`}` },
        PHASE_NAMES[k], h('b', {}, s === null ? '–' : String(s))))))));
}

const LEVEL_ICON = { warn: 'alert', tip: 'tip', good: 'check' };

export function createFeedback(items) {
  if (!items.length) return h('p', { class: 'muted' }, 'Không có nhận xét.');
  return h('ul', { class: 'feedback' },
    items.map((item, i) => h('li', { class: `feedback__item feedback__item--${item.level} reveal`, style: { '--i': i } },
      h('span', { class: 'feedback__mark' }, icon(LEVEL_ICON[item.level] || 'tip')),
      h('span', {}, item.text))));
}
