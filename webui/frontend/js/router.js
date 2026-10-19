// Định tuyến bằng hash (#/...) để chạy được với StaticFiles, không cần cấu hình máy chủ.
import { h, replace } from './lib/dom.js';
import { icon } from './lib/icons.js';
import { drillMenuView } from './views/drillMenu.js';
import { drillView } from './views/drill.js';
import { libraryView } from './views/library.js';
import { lessonView } from './views/lesson.js';
import { recognizeView } from './views/recognize.js';
import { topicView } from './views/topic.js';

const ROUTES = [
  { pattern: /^$/, nav: 'lessons', view: libraryView, params: () => ({}) },
  { pattern: /^chu-de\/([\w-]+)$/, nav: 'lessons', view: topicView, params: (m) => ({ id: m[1] }) },
  { pattern: /^bai\/(\d+)$/, nav: 'lessons', view: lessonView, params: (m) => ({ label: Number(m[1]) }) },
  { pattern: /^luyen-tap$/, nav: 'drill', view: drillMenuView, params: () => ({}) },
  { pattern: /^luyen-tap\/([\w-]+)$/, nav: 'drill', view: drillView, params: (m) => ({ scope: m[1] }) },
  { pattern: /^nhan-dien$/, nav: 'recognize', view: recognizeView, params: () => ({}) },
];

/**
 * gate(): trả về một view thay cho mọi trang (ví dụ trang đăng nhập), hoặc null để định tuyến bình thường.
 * Đường dẫn trong hash được giữ nguyên nên qua cổng xong (refresh) sẽ mở đúng trang định vào.
 */
export function createRouter(mount, { gate = () => null } = {}) {
  let current = null;
  let token = 0;

  function setNav(key) {
    document.querySelectorAll('[data-nav]').forEach((a) => a.classList.toggle('is-active', a.dataset.nav === key));
  }

  async function resolve() {
    const path = decodeURIComponent(window.location.hash.replace(/^#\/?/, '')).replace(/\/$/, '');
    const gated = gate();
    const route = gated ? null : ROUTES.find((r) => r.pattern.test(path));
    const myToken = ++token;

    if (current?.destroy) current.destroy();
    current = null;

    if (!gated && !route) {
      setNav(null);
      replace(mount, notFound('Không có trang này.'));
      return;
    }
    setNav(gated ? null : route.nav);

    try {
      const view = await (gated || route.view(route.params(path.match(route.pattern))));
      if (myToken !== token) {
        view.destroy?.();
        return;
      }
      current = view;
      replace(mount, h('div', { class: 'reveal' }, view.el));
      document.title = view.title ? `${view.title} · VSL400` : 'VSL400 · Học ký hiệu';
      window.scrollTo({ top: 0 });
      if (view.focus) view.focus();
      else mount.focus({ preventScroll: true });
    } catch (err) {
      if (myToken !== token) return;
      replace(mount, notFound(err.message));
    }
  }

  window.addEventListener('hashchange', resolve);
  return {
    start: resolve,
    refresh: resolve,
    get current() { return current; },
  };
}

function notFound(message) {
  return h('div', { class: 'page' },
    h('div', { class: 'notice notice--bad' }, icon('alert'), h('span', {}, message)),
    h('a', { class: 'btn btn--secondary', href: '#/' }, icon('arrowLeft'), 'Về trang bài học'));
}
