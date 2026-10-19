// Dải lịch sử các lần nhận diện trong phiên (chỉ trong bộ nhớ tab).
import { h } from '../lib/dom.js';
import { clock, percent, VERDICT } from '../lib/format.js';

export function createHistoryStrip({ entries, currentId = null, onSelect }) {
  if (!entries.length) {
    return h('p', { class: 'empty' }, 'Chưa có lần nào trong phiên này. Kết quả sẽ hiện ở đây, mới nhất bên trái.');
  }
  return h('div', { class: 'history', role: 'list' },
    entries.map((e) => {
      const meta = e.verdict
        ? [h('span', {}, VERDICT[e.verdict].label), h('span', {}, `${e.score}/100`)]
        : [h('span', {}, clock(e.time)), h('span', {}, percent(e.top1.prob))];
      return h('button', {
        class: `history__item${e.id === currentId ? ' is-current' : ''}`,
        type: 'button',
        role: 'listitem',
        disabled: !e.result,
        title: e.result ? 'Xem lại kết quả này' : 'Kết quả cũ đã được giải phóng khỏi bộ nhớ',
        onClick: () => e.result && onSelect(e),
      },
      e.thumb
        ? h('img', { class: 'history__thumb', src: e.thumb, alt: '' })
        : h('div', { class: 'history__thumb' }),
      h('span', { class: 'history__gloss' }, e.verdict ? e.gloss : e.top1.gloss),
      h('span', { class: 'history__meta' }, meta));
    }));
}
