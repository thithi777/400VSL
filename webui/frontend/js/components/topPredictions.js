// Top-5 dự đoán của model với thanh độ tin cậy.
import { h } from '../lib/dom.js';
import { percent } from '../lib/format.js';

export function createTop5(top5, { target = null, link = true } = {}) {
  return h('ol', { class: 'top5' },
    top5.map((item, i) => h('li', {
      class: `top5__item reveal${item.label === target ? ' is-target' : ''}`,
      style: { '--i': i },
    },
    h('span', { class: 'top5__rank' }, String(i + 1)),
    h('span', { class: 'top5__gloss' },
      link ? h('a', { href: `#/bai/${item.label}`, title: 'Mở bài học ký hiệu này' }, item.gloss) : item.gloss),
    h('div', { class: 'bar' }, h('span', { class: 'bar__fill', style: { '--value': item.prob.toFixed(4) } })),
    h('span', { class: 'top5__prob' }, percent(item.prob)))));
}
