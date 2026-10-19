// Bộ icon SVG vẽ tay, nét 1.8, đầu tròn. Dùng: icon('camera')
import { h } from './dom.js';

const PATHS = {
  camera: '<path d="M4 8.5A2.5 2.5 0 0 1 6.5 6h7A2.5 2.5 0 0 1 16 8.5v7a2.5 2.5 0 0 1-2.5 2.5h-7A2.5 2.5 0 0 1 4 15.5z"/><path d="m16 10.5 3.6-2.2a.9.9 0 0 1 1.4.8v5.8a.9.9 0 0 1-1.4.8L16 13.5"/>',
  upload: '<path d="M12 15V4.5"/><path d="m7.5 9 4.5-4.5L16.5 9"/><path d="M4.5 14.5v3A2.5 2.5 0 0 0 7 20h10a2.5 2.5 0 0 0 2.5-2.5v-3"/>',
  play: '<path d="M8 5.8v12.4a.8.8 0 0 0 1.2.7l9.6-6.2a.8.8 0 0 0 0-1.4L9.2 5.1A.8.8 0 0 0 8 5.8z" fill="currentColor" stroke="none"/>',
  pause: '<rect x="7" y="5.5" width="3.4" height="13" rx="1" fill="currentColor" stroke="none"/><rect x="13.6" y="5.5" width="3.4" height="13" rx="1" fill="currentColor" stroke="none"/>',
  check: '<path d="m5.5 12.5 4 4 9-9"/>',
  alert: '<path d="M12 8v5"/><circle cx="12" cy="16.6" r=".6" fill="currentColor"/><path d="M10.3 4.2 3.1 17a2 2 0 0 0 1.7 3h14.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/>',
  tip: '<path d="M12 3.5a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V17h5v-.6c0-.8.4-1.5 1-2A6 6 0 0 0 12 3.5z"/><path d="M10 20.5h4"/>',
  arrowLeft: '<path d="M19 12H5"/><path d="m11 6-6 6 6 6"/>',
  arrowRight: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.4-4.4"/>',
  refresh: '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4h-4"/>',
  logout: '<path d="M10 4.5H7A2.5 2.5 0 0 0 4.5 7v10A2.5 2.5 0 0 0 7 19.5h3"/><path d="M20 12H9.5"/><path d="m16 8 4 4-4 4"/>',
  skeleton: '<circle cx="12" cy="5" r="2"/><path d="M12 7.5v7M6 10l6-1.5 6 1.5M9 20l3-5.5 3 5.5"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  video: '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="m10 9.2 4.8 2.8-4.8 2.8z" fill="currentColor"/>',
  book: '<path d="M4.5 5.5A1.5 1.5 0 0 1 6 4h5v15H6a1.5 1.5 0 0 0-1.5 1.5z"/><path d="M19.5 5.5A1.5 1.5 0 0 0 18 4h-5v15h5a1.5 1.5 0 0 1 1.5 1.5z"/>',
};

export function iconSvg(name) {
  const body = PATHS[name] || '';
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

export function icon(name, extraClass = '') {
  return h('span', { class: `icon ${extraClass}`.trim(), html: iconSvg(name) });
}
