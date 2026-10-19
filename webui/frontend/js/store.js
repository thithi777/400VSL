// Trạng thái phía trình duyệt:
// - người đang đăng nhập
// - danh mục bài học và trạng thái máy chủ (tải một lần)
// - lịch sử phiên (chỉ trong bộ nhớ tab, mất khi tải lại trang; không lưu video)
// - tiến độ học từng bài (máy chủ lưu theo tài khoản; ở đây là bản sao tải lúc đăng nhập)
// - tiến độ luyện tập không xem mẫu (tải lại mỗi lần mở trang luyện tập)
import { fetchDrill, fetchProgress, getCatalog, getStatus, resetDrill } from './api.js';

let user = null;

export function getUser() {
  return user;
}

export function setUser(value) {
  user = value;
}

let catalogPromise = null;
let statusPromise = null;

export function loadCatalog() {
  if (!catalogPromise) {
    catalogPromise = getCatalog().then((data) => {
      const byLabel = new Map(data.lessons.map((l) => [l.label, l]));
      const topics = new Map();
      for (const group of data.groups) {
        for (const topic of group.topics) topics.set(topic.id, { ...topic, group });
      }
      return { ...data, byLabel, topics };
    });
    catalogPromise.catch(() => { catalogPromise = null; });
  }
  return catalogPromise;
}

export function loadStatus({ refresh = false } = {}) {
  if (!statusPromise || refresh) {
    statusPromise = getStatus();
    statusPromise.catch(() => { statusPromise = null; });
  }
  return statusPromise;
}

// ------------------------------------------------------------------
// Lịch sử phiên
// ------------------------------------------------------------------
const HISTORY_LIMIT = 24;
const KEEP_MEDIA = 12; // chỉ giữ ảnh xem lại cho 12 lần gần nhất để tab không nặng
const history = [];
const listeners = new Set();
let nextId = 1;

export function addHistory({ mode, label = null, result }) {
  const practice = result.practice;
  const top1 = result.top5[0];
  const entry = {
    id: nextId++,
    time: Date.now(),
    mode,
    label,
    gloss: practice ? practice.target.gloss : top1.gloss,
    top1,
    verdict: practice ? practice.verdict : null,
    score: practice ? practice.score : null,
    thumb: result.preview.length ? result.preview[Math.floor(result.preview.length / 2)] : null,
    result,
  };
  history.unshift(entry);
  history.splice(HISTORY_LIMIT).forEach((e) => releaseMedia(e, { thumb: true }));
  history.slice(KEEP_MEDIA).forEach((e) => releaseMedia(e, { thumb: false }));
  listeners.forEach((fn) => fn(history));
  return entry;
}

// Ảnh webcam là URL blob: (api.js tạo) nên phải thu hồi thì trình duyệt mới giải phóng bộ nhớ
const revoke = (url) => { if (url.startsWith('blob:')) URL.revokeObjectURL(url); };

function releaseMedia(entry, { thumb }) {
  if (entry.result) {
    entry.result.preview.forEach((url) => { if (url !== entry.thumb) revoke(url); });
    entry.result = null;
  }
  if (thumb && entry.thumb) {
    revoke(entry.thumb);
    entry.thumb = null;
  }
}

export function getHistory(filter = () => true) {
  return history.filter(filter);
}

export function onHistory(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// ------------------------------------------------------------------
// Tiến độ học: { label: { attempts, best, passed, last } }
// Máy chủ tự ghi sau mỗi lần chấm và trả tiến độ mới trong kết quả (practice.progress).
// ------------------------------------------------------------------
let progress = {};

export async function loadProgress() {
  progress = await fetchProgress();
  return progress;
}

export function getProgress(label) {
  return progress[label] || null;
}

export function getAllProgress() {
  return progress;
}

export function setProgress(label, entry) {
  if (entry) progress[label] = entry;
}

// ------------------------------------------------------------------
// Tiến độ luyện tập: cùng dạng tiến độ học. passed = ký hiệu không còn bị bốc ngẫu nhiên.
// ------------------------------------------------------------------
let drill = {};

export async function loadDrill() {
  drill = await fetchDrill();
  return drill;
}

export function getDrill(label) {
  return drill[label] || null;
}

export function setDrill(label, entry) {
  if (entry) drill[label] = entry;
}

export async function clearDrill(labels) {
  drill = await resetDrill(labels);
  return drill;
}
