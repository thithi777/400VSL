// Trang chọn phạm vi luyện tập: tất cả 400 ký hiệu hoặc một chủ đề.
import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { getDrill, loadCatalog, loadDrill } from '../store.js';

export const ALL_SCOPE = 'tat-ca';

const passedCount = (labels) => labels.filter((l) => getDrill(l)?.passed).length;

function progressFoot(passed, total) {
  return h('span', { class: 'topic-card__foot' },
    h('span', {}, passed ? `${passed}/${total} đạt` : `${total} ký hiệu`),
    h('span', { class: 'bar bar--thin bar--good' },
      h('span', { class: 'bar__fill', style: { '--value': (passed / total).toFixed(3) } })));
}

function topicCard(topic, i) {
  const passed = passedCount(topic.labels);
  const left = topic.labels.length - passed;
  return h('a', { class: 'topic-card reveal', href: `#/luyen-tap/${topic.id}`, style: { '--i': i } },
    h('span', { class: 'topic-card__name' }, topic.name),
    h('span', { class: 'topic-card__sample' }, left ? `Còn ${left} ký hiệu chưa đạt` : 'Đã đạt hết'),
    progressFoot(passed, topic.labels.length));
}

export async function drillMenuView() {
  const [catalog] = await Promise.all([loadCatalog(), loadDrill()]);
  const all = catalog.lessons.map((l) => l.label);
  const passed = passedCount(all);
  let i = 0;

  const el = h('div', { class: 'page' },
    h('div', { class: 'library-head' },
      h('header', { class: 'page-head' },
        h('span', { class: 'eyebrow' }, 'Luyện tập'),
        h('h1', { class: 'page-title' }, 'Tự làm, không xem mẫu'),
        h('p', { class: 'page-lead' },
          'Mỗi lượt hệ thống bốc ngẫu nhiên một ký hiệu, bạn nhớ lại và biểu diễn trước webcam. '
          + 'Ký hiệu đã làm đúng sẽ không bị bốc lại.')),
      h('div', { class: 'stats' },
        h('div', { class: 'stat' }, h('span', { class: 'stat__value' }, String(passed)), h('span', { class: 'stat__label' }, 'Đã đạt')),
        h('div', { class: 'stat' }, h('span', { class: 'stat__value' }, String(all.length - passed)), h('span', { class: 'stat__label' }, 'Còn lại')))),
    h('a', { class: 'drill-all reveal', href: `#/luyen-tap/${ALL_SCOPE}` },
      h('span', { class: 'drill-all__text' },
        h('span', { class: 'topic-card__name' }, `Tất cả ${all.length} ký hiệu`),
        h('span', { class: 'muted' }, 'Bốc ngẫu nhiên trong toàn bộ thư viện')),
      progressFoot(passed, all.length),
      h('span', { class: 'btn btn--primary btn--sm' }, 'Bắt đầu', icon('arrowRight'))),
    catalog.groups.map((group) => h('section', { class: 'group' },
      h('h2', { class: 'section-title' }, group.name,
        h('span', { class: 'count' }, String(group.topics.length))),
      h('div', { class: 'topic-grid' }, group.topics.map((t) => topicCard(t, i++))))));

  return { el, title: 'Luyện tập' };
}
