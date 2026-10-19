// Khởi động: báo lỗi máy chủ trên thanh trên cùng (chỉ khi có lỗi), đăng nhập, định tuyến, phím tắt toàn cục.
import { getMe, logout } from './api.js';
import { isTyping } from './lib/dom.js';
import { icon } from './lib/icons.js';
import { createRouter } from './router.js';
import { getUser, loadProgress, loadStatus, setUser } from './store.js';
import { authView } from './views/auth.js';

const statusEl = document.getElementById('status');
const statusText = statusEl.querySelector('.status__text');
const navEl = document.querySelector('.app-nav');
const userEl = document.getElementById('user');
const userName = userEl.querySelector('.user__name');

function showError(text, title = '') {
  statusText.textContent = text;
  statusEl.title = title || text;
  statusEl.hidden = false;
}

async function refreshStatus() {
  try {
    const s = await loadStatus({ refresh: true });
    if (s.ready) statusEl.hidden = true;
    else showError('Model chưa sẵn sàng', s.error || '');
  } catch {
    showError('Mất kết nối máy chủ');
    setTimeout(refreshStatus, 5000);
  }
}

function renderUser() {
  const user = getUser();
  navEl.hidden = !user;
  userEl.hidden = !user;
  userName.textContent = user ? user.username : '';
}

async function signIn(user) {
  setUser(user);
  await loadProgress();
  renderUser();
  router.refresh();
}

const router = createRouter(document.getElementById('app'), {
  gate: () => (getUser() ? null : authView({ onSuccess: signIn })),
});

// Phiên hết hạn giữa chừng: quay về trang đăng nhập, đăng nhập lại sẽ mở đúng trang đang xem
window.addEventListener('auth:required', () => {
  if (!getUser()) return;
  setUser(null);
  renderUser();
  router.refresh();
});

const logoutBtn = document.getElementById('logout');
logoutBtn.prepend(icon('logout'));
logoutBtn.addEventListener('click', async () => {
  try {
    await logout();
  } finally {
    // Tải lại trang để xoá lịch sử phiên và dữ liệu của tài khoản này khỏi bộ nhớ tab
    window.location.reload();
  }
});

document.addEventListener('keydown', (event) => {
  if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event)) return;
  // Space trên một nút đang được chọn: để nút tự xử lý
  if (event.code === 'Space' && event.target instanceof HTMLButtonElement) return;
  const view = router.current;
  if (view?.onKey && view.onKey(event)) event.preventDefault();
});

async function boot() {
  try {
    const { user } = await getMe();
    if (user) {
      setUser(user);
      await loadProgress();
    }
  } catch {
    showError('Mất kết nối máy chủ');
    setTimeout(boot, 5000);
    return;
  }
  renderUser();
  router.start();
}

refreshStatus();
boot();
