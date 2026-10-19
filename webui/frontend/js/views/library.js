// Trang thư viện: 5 nhóm, 29 chủ đề, tìm kiếm không dấu trên 400 ký hiệu.
import { h, replace } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { fold } from '../lib/format.js';
import { getAllProgress, loadCatalog } from '../store.js';
import { createLessonTile } from '../components/lessonTile.js';

function topicCard(topic, catalog, progress, i) {
  const glosses = topic.labels.map((l) => catalog.byLabel.get(l).gloss);
  const passed = topic.labels.filter((l) => progress[l]?.passed).length;
  return h('a', { class: 'topic-card reveal', href: `#/chu-de/${topic.id}`, style: { '--i': i } },
    h('span', { class: 'topic-card__name' }, topic.name),
    h('span', { class: 'topic-card__sample' }, glosses.join(', ')),
    h('span', { class: 'topic-card__foot' },
      h('span', {}, passed ? `${passed}/${topic.labels.length} đạt` : `${topic.labels.length} ký hiệu`),
      h('span', { class: 'bar bar--thin bar--good' },
        h('span', { class: 'bar__fill', style: { '--value': (passed / topic.labels.length).toFixed(3) } }))));
}

export async function libraryView() {
  const catalog = await loadCatalog();
  const progress = getAllProgress();
  const practiced = Object.keys(progress).length;
  const passed = Object.values(progress).filter((p) => p.passed).length;
  const topicCount = catalog.groups.reduce((n, g) => n + g.topics.length, 0);

  const searchInput = h('input', {
    type: 'search',
    placeholder: 'Tìm ký hiệu, gõ có dấu hoặc không dấu',
    'aria-label': 'Tìm ký hiệu',
    autocomplete: 'off',
  });

  const content = h('div', { class: 'page' });

  function renderGroups() {
    let i = 0;
    replace(content, catalog.groups.map((group) => h('section', { class: 'group' },
      h('h2', { class: 'section-title' }, group.name,
        h('span', { class: 'count' }, String(group.topics.reduce((n, t) => n + t.labels.length, 0)))),
      h('div', { class: 'topic-grid' }, group.topics.map((t) => topicCard(t, catalog, progress, i++))))));
  }

  function renderSearch(query) {
    const q = fold(query);
    const hits = catalog.lessons.filter((l) => fold(l.gloss).includes(q));
    hits.sort((a, b) => (fold(a.gloss).startsWith(q) ? 0 : 1) - (fold(b.gloss).startsWith(q) ? 0 : 1));
    replace(content, h('section', { class: 'group' },
      h('h2', { class: 'section-title' }, `Kết quả cho “${query.trim()}”`, h('span', { class: 'count' }, String(hits.length))),
      hits.length
        ? h('div', { class: 'lesson-grid' }, hits.map((l, i) => createLessonTile(l, {
          topicName: catalog.topics.get(l.topic).name,
          progress: progress[l.label],
          i,
        })))
        : h('p', { class: 'empty' }, 'Không có ký hiệu nào khớp. Thử gõ ngắn hơn, ví dụ “me” cho “Mẹ”.')));
  }

  let timer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => (searchInput.value.trim() ? renderSearch(searchInput.value) : renderGroups()), 80);
  });

  renderGroups();

  const el = h('div', { class: 'page' },
    h('div', { class: 'library-head' },
      h('header', { class: 'page-head' },
        h('span', { class: 'eyebrow' }, 'Ngôn ngữ ký hiệu Việt Nam'),
        h('h1', { class: 'page-title' }, 'Học 400 ký hiệu'),
        h('p', { class: 'page-lead' },
          `Mỗi bài có video mẫu của người biểu diễn ${catalog.signer ?? ''}. Bạn làm theo trước webcam, `
          + 'mô hình SDA-GCN chấm bài và chỉ ra chỗ cần sửa.')),
      h('div', { class: 'stats' },
        h('div', { class: 'stat' }, h('span', { class: 'stat__value' }, String(catalog.lessons.length)), h('span', { class: 'stat__label' }, 'Ký hiệu')),
        h('div', { class: 'stat' }, h('span', { class: 'stat__value' }, String(topicCount)), h('span', { class: 'stat__label' }, 'Chủ đề')),
        h('div', { class: 'stat' }, h('span', { class: 'stat__value' }, String(practiced)), h('span', { class: 'stat__label' }, 'Đã luyện')),
        h('div', { class: 'stat' }, h('span', { class: 'stat__value' }, String(passed)), h('span', { class: 'stat__label' }, 'Đã đạt')))),
    h('div', { class: 'library-tools' },
      h('div', { class: 'search' }, icon('search'), searchInput, h('kbd', {}, '/')),
      h('a', { class: 'btn btn--secondary', href: '#/nhan-dien' }, icon('camera'), 'Nhận diện tự do')),
    content);

  return {
    el,
    title: 'Bài học',
    onKey(event) {
      if (event.key === '/') {
        searchInput.focus();
        return true;
      }
      return false;
    },
    destroy() {
      clearTimeout(timer);
    },
  };
}
