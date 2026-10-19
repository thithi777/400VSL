// Định dạng số và chữ theo kiểu Việt Nam.

/** 0.9234 -> "92,3 %" */
export function percent(p, digits = 1) {
  const v = Math.max(0, Math.min(1, Number(p) || 0)) * 100;
  if (v > 0 && v < 0.1) return '<0,1 %';
  return `${v.toFixed(digits).replace('.', ',')} %`;
}

/** 2.56 -> "2,56 s" */
export function seconds(s, digits = 2) {
  return `${Number(s).toFixed(digits).replace('.', ',')} s`;
}

/** Bỏ dấu để tìm kiếm: "Đồng hồ" -> "dong ho" */
export function fold(text) {
  return String(text)
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim();
}

export function clock(date) {
  return new Date(date).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function pad(n, width = 2) {
  return String(n).padStart(width, '0');
}

export function tone(score) {
  if (score === null || score === undefined) return '';
  if (score >= 75) return 'good';
  if (score >= 50) return 'warn';
  return 'bad';
}

export const VERDICT = {
  pass: { label: 'Đúng', tone: 'good' },
  close: { label: 'Gần đúng', tone: 'warn' },
  fail: { label: 'Chưa đúng', tone: 'bad' },
};
