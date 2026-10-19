// Tạo phần tử DOM gọn: h('div', { class: 'card', onClick: fn }, 'chữ', con)

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') {
      el.className = value;
    } else if (key === 'style' && typeof value === 'object') {
      for (const [prop, v] of Object.entries(value)) {
        if (prop.startsWith('--')) el.style.setProperty(prop, v);
        else el.style[prop] = v;
      }
    } else if (key === 'html') {
      el.innerHTML = value; // chỉ dùng cho chuỗi tin cậy (icon SVG viết sẵn)
    } else if (key.startsWith('on') && typeof value === 'function') {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === 'dataset') {
      Object.assign(el.dataset, value);
    } else if (value === true) {
      el.setAttribute(key, '');
    } else {
      el.setAttribute(key, String(value));
    }
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const child of [children].flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : String(child));
  }
  return el;
}

export function clear(el) {
  el.replaceChildren();
  return el;
}

export function replace(el, ...children) {
  el.replaceChildren();
  return append(el, children);
}

/** Hình chữ nhật đặt ảnh srcW x srcH vừa trong dstW x dstH (object-fit: contain). */
export function containRect(srcW, srcH, dstW, dstH) {
  const s = Math.min(dstW / srcW, dstH / srcH);
  const w = srcW * s;
  const hh = srcH * s;
  return { x: (dstW - w) / 2, y: (dstH - hh) / 2, w, h: hh };
}

/** Canvas khớp kích thước hiển thị x devicePixelRatio. Trả về true nếu kích thước đổi. */
export function fitCanvas(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const rect = canvas.getBoundingClientRect();
  const w = Math.max(1, Math.round(rect.width * dpr));
  const hgt = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== w || canvas.height !== hgt) {
    canvas.width = w;
    canvas.height = hgt;
    return true;
  }
  return false;
}

/** Bàn phím toàn cục không nên kích hoạt khi đang gõ chữ. */
export function isTyping(event) {
  const t = event.target;
  return t instanceof HTMLElement && (t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName));
}
