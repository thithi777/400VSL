// Gọi backend FastAPI. /api/analyze trả NDJSON: nhiều dòng tiến độ rồi một dòng kết quả.
// Phiên đăng nhập nằm trong cookie HttpOnly nên JS không cần (và không đọc được) token.
// Gặp 401 ở API cần đăng nhập: phát sự kiện 'auth:required' để main.js hiện trang đăng nhập.

const NETWORK_ERROR = 'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.';

function errorDetail(text, status, statusText) {
  try {
    const data = JSON.parse(text);
    if (typeof data.detail === 'string') return data.detail;
    return JSON.stringify(data.detail ?? data);
  } catch {
    return `${status} ${statusText}`;
  }
}

async function readError(res) {
  return errorDetail(await res.text().catch(() => ''), res.status, res.statusText);
}

function requireAuth(status, url) {
  if (status === 401 && !url.startsWith('/api/auth/')) window.dispatchEvent(new CustomEvent('auth:required'));
}

async function send(url, { method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let res;
  try {
    res = await fetch(url, { method, signal, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new Error(NETWORK_ERROR);
  }
  if (!res.ok) {
    requireAuth(res.status, url);
    throw new Error(await readError(res));
  }
  return res;
}

export async function getJSON(url, { signal } = {}) {
  return (await send(url, { signal })).json();
}

const postJSON = async (url, body) => (await send(url, { method: 'POST', body })).json();

export const getStatus = () => getJSON('/api/status');
export const getCatalog = () => getJSON('/api/catalog');
export const getLesson = (label, opts) => getJSON(`/api/lessons/${label}`, opts);
export const fetchProgress = () => getJSON('/api/progress');
export const fetchDrill = () => getJSON('/api/drill');
export const resetDrill = (labels) => postJSON('/api/drill/reset', { labels });

export const getMe = () => getJSON('/api/auth/me');
export const login = (username, password) => postJSON('/api/auth/login', { username, password });
export const register = (username, password) => postJSON('/api/auth/register', { username, password });
export const logout = () => postJSON('/api/auth/logout', {});

/** result.preview -> danh sách URL ảnh để phát lại. Webcam: dùng chính ảnh vừa ghi (máy chủ không gửi lại). */
function attachPreview(result, input) {
  result.preview = input.kind === 'frames'
    ? input.blobs.map((blob) => URL.createObjectURL(blob))
    : result.preview.map((b64) => `data:image/jpeg;base64,${b64}`);
  return result;
}

/**
 * Gửi một đoạn ký hiệu đi phân tích.
 * input: { kind: 'frames', blobs: Blob[], fps } | { kind: 'video', file: File }
 * target: label bài đang luyện (tuỳ chọn) -> kết quả có thêm phần so sánh với video mẫu
 * drill: true khi luyện tập không xem mẫu -> máy chủ ghi vào tiến độ luyện tập thay cho bài học
 * Dùng XMLHttpRequest (fetch không báo được tiến độ tải lên): onProgress nhận
 * { stage: 'upload', current: byte đã gửi, total } rồi các dòng NDJSON của máy chủ.
 */
export function analyze(input, { target = null, drill = false, onProgress = () => {}, signal } = {}) {
  const form = new FormData();
  if (input.kind === 'frames') {
    input.blobs.forEach((blob, i) => form.append('frames', blob, `frame_${String(i).padStart(3, '0')}.jpg`));
    form.append('fps', String(input.fps));
  } else {
    form.append('video', input.file, input.file.name || 'video.mp4');
  }
  if (target !== null && target !== undefined) form.append('target', String(target));
  if (drill) form.append('mode', 'drill');

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let seen = 0;
    let buffer = '';
    let result = null;
    let settled = false;

    const finish = (err, value) => {
      if (settled) return;
      settled = true;
      if (err) {
        reject(err);
        xhr.abort();
      } else {
        resolve(value);
      }
    };

    const handle = (line) => {
      if (!line.trim()) return;
      const event = JSON.parse(line);
      if (event.type === 'progress') onProgress(event);
      else if (event.type === 'result') result = event.data;
      else if (event.type === 'error') throw new Error(event.message);
    };

    // Đọc các dòng NDJSON mới tới (responseText lớn dần trong lúc máy chủ còn gửi)
    const consume = (final) => {
      const text = xhr.responseText;
      buffer += text.slice(seen);
      seen = text.length;
      let nl;
      while ((nl = buffer.indexOf('\n')) >= 0) {
        handle(buffer.slice(0, nl));
        buffer = buffer.slice(nl + 1);
      }
      if (final) handle(buffer);
    };

    xhr.open('POST', '/api/analyze');
    xhr.setRequestHeader('Accept', 'application/x-ndjson');
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress({ type: 'progress', stage: 'upload', current: e.loaded, total: e.total });
    };
    xhr.onprogress = () => {
      if (xhr.status !== 200) return;
      try {
        consume(false);
      } catch (err) {
        finish(err);
      }
    };
    xhr.onload = () => {
      if (xhr.status !== 200) {
        requireAuth(xhr.status, '/api/analyze');
        finish(new Error(errorDetail(xhr.responseText, xhr.status, xhr.statusText)));
        return;
      }
      try {
        consume(true);
        if (!result) throw new Error('Máy chủ ngắt kết nối trước khi trả kết quả.');
        finish(null, attachPreview(result, input));
      } catch (err) {
        finish(err);
      }
    };
    xhr.onerror = () => finish(new Error(NETWORK_ERROR));
    xhr.onabort = () => finish(new DOMException('Đã huỷ', 'AbortError'));

    if (signal?.aborted) {
      finish(new DOMException('Đã huỷ', 'AbortError'));
      return;
    }
    signal?.addEventListener('abort', () => xhr.abort(), { once: true });
    onProgress({ type: 'progress', stage: 'upload', current: 0, total: 0 });
    xhr.send(form);
  });
}
