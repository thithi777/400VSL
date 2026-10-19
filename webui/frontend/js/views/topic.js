// Trang một chủ đề: các bài theo thứ tự học.
import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { getAllProgress, loadCatalog } from '../store.js';
import { createLessonTile } from '../components/lessonTile.js';

export async function topicView({ id }) {
  const catalog = await loadCatalog();
  const topic = catalog.topics.get(id);
  if (!topic) throw new Error(`Không có chủ đề “${id}”.`);

  const progress = getAllProgress();
  const lessons = topic.labels.map((l) => catalog.byLabel.get(l));
  const passed = lessons.filter((l) => progress[l.label]?.passed).length;
  const nextLesson = lessons.find((l) => !progress[l.label]?.passed) || lessons[0];

  const el = h('div', { class: 'page' },
    h('header', { class: 'page-head' },
      h('nav', { class: 'breadcrumb', 'aria-label': 'Đường dẫn' },
        h('a', { href: '#/' }, 'Bài học'),
        h('span', { class: 'breadcrumb__sep' }, '/'),
        h('span', {}, topic.group.name)),
      h('h1', { class: 'page-title' }, topic.name),
      h('div', { class: 'row' },
        h('p', { class: 'page-lead' }, `${lessons.length} ký hiệu · ${passed} đã đạt`),
        h('div', { class: 'row' },
          h('a', { class: 'btn btn--secondary btn--sm', href: `#/luyen-tap/${topic.id}` }, 'Luyện tập chủ đề'),
          h('a', { class: 'btn btn--primary btn--sm', href: `#/bai/${nextLesson.label}` },
            passed ? 'Học tiếp' : 'Bắt đầu', icon('arrowRight'))))),
    h('div', { class: 'lesson-grid' },
      lessons.map((l, i) => createLessonTile(l, { index: i + 1, progress: progress[l.label], i }))));

  return { el, title: topic.name };
}
