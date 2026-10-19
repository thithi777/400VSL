// Ô một bài học trong lưới (trang chủ đề, kết quả tìm kiếm).
import { h } from '../lib/dom.js';
import { pad } from '../lib/format.js';

export function progressBadge(progress) {
  if (!progress) return null;
  if (progress.passed) return h('span', { class: 'badge badge--good' }, 'Đã đạt');
  return h('span', { class: 'badge badge--warn' }, `${progress.best}/100`);
}

export function createLessonTile(lesson, { index = null, topicName = null, progress = null, i = 0 } = {}) {
  return h('a', { class: 'lesson-tile reveal', href: `#/bai/${lesson.label}`, style: { '--i': Math.min(i, 24) } },
    h('span', { class: 'lesson-tile__top' },
      h('span', { class: 'lesson-tile__num' }, index !== null ? pad(index) : `#${lesson.label}`),
      progressBadge(progress)),
    h('span', { class: 'lesson-tile__gloss' }, lesson.gloss),
    topicName ? h('span', { class: 'lesson-tile__topic' }, topicName) : null);
}
