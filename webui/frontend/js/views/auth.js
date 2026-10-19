// Đăng nhập / đăng ký. Chưa đăng nhập thì mọi đường dẫn đều hiện trang này (xem main.js);
// đăng nhập xong sẽ mở đúng trang người dùng định vào.
import { login, register } from '../api.js';
import { h, replace } from '../lib/dom.js';
import { icon } from '../lib/icons.js';

const PASSWORD_MIN = 8;

const MODES = {
  login: {
    tab: 'Đăng nhập',
    title: 'Đăng nhập',
    lead: 'Đăng nhập để học 400 ký hiệu và lưu tiến độ của bạn.',
    submit: 'Đăng nhập',
    busy: 'Đang đăng nhập',
  },
  register: {
    tab: 'Đăng ký',
    title: 'Tạo tài khoản',
    lead: 'Tài khoản lưu tiến độ học, mở trên máy nào cũng thấy.',
    submit: 'Tạo tài khoản',
    busy: 'Đang tạo tài khoản',
  },
};

function field(label, input, hint = null) {
  return h('div', { class: 'field' },
    h('label', { class: 'field__label', for: input.id }, label),
    input,
    hint);
}

export function authView({ onSuccess }) {
  let mode = null;
  let busy = false;

  const username = h('input', {
    class: 'field__input', id: 'auth-username', name: 'username', autocomplete: 'username',
    autocapitalize: 'none', spellcheck: 'false', maxlength: 32,
  });
  const password = h('input', { class: 'field__input', id: 'auth-password', name: 'password', type: 'password', maxlength: 128 });
  const confirm = h('input', {
    class: 'field__input', id: 'auth-confirm', name: 'confirm', type: 'password', autocomplete: 'new-password', maxlength: 128,
  });

  const usernameHint = h('span', { class: 'field__hint' }, '3 đến 32 ký tự: chữ không dấu, số, dấu chấm hoặc gạch dưới.');
  const passwordHint = h('span', { class: 'field__hint' }, `Ít nhất ${PASSWORD_MIN} ký tự.`);
  const confirmField = field('Nhập lại mật khẩu', confirm);

  const title = h('h1', { class: 'page-title' });
  const lead = h('p', { class: 'page-lead' });
  const message = h('div', { 'aria-live': 'polite' });
  const submit = h('button', { class: 'btn btn--primary', type: 'submit' });

  const tabs = Object.fromEntries(Object.entries(MODES).map(([key, m]) => [key,
    h('button', { class: 'tabs__btn', type: 'button', role: 'tab', onClick: () => setMode(key) }, m.tab)]));

  function showError(text) {
    replace(message, h('div', { class: 'notice notice--bad' }, icon('alert'), h('span', {}, text)));
  }

  function setMode(next) {
    if (next === mode || busy) return;
    mode = next;
    const m = MODES[mode];
    Object.entries(tabs).forEach(([key, btn]) => btn.setAttribute('aria-selected', String(key === mode)));
    title.textContent = m.title;
    lead.textContent = m.lead;
    submit.textContent = m.submit;
    const isRegister = mode === 'register';
    password.autocomplete = isRegister ? 'new-password' : 'current-password';
    usernameHint.hidden = !isRegister;
    passwordHint.hidden = !isRegister;
    confirmField.hidden = !isRegister;
    confirm.value = '';
    replace(message);
    document.title = `${m.title} · VSL400`;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (busy) return;
    const name = username.value.trim();
    const pass = password.value;

    if (!name || !pass) return showError('Hãy nhập tên đăng nhập và mật khẩu.');
    if (mode === 'register') {
      if (pass.length < PASSWORD_MIN) return showError(`Mật khẩu cần ít nhất ${PASSWORD_MIN} ký tự.`);
      if (pass !== confirm.value) return showError('Hai lần nhập mật khẩu chưa khớp.');
    }

    busy = true;
    submit.disabled = true;
    submit.textContent = MODES[mode].busy;
    replace(message);
    try {
      const { user } = await (mode === 'login' ? login(name, pass) : register(name, pass));
      await onSuccess(user);
    } catch (err) {
      showError(err.message);
      password.select();
    } finally {
      busy = false;
      submit.disabled = false;
      submit.textContent = MODES[mode].submit;
    }
    return undefined;
  }

  const form = h('form', { class: 'auth__form', novalidate: true, onSubmit: handleSubmit },
    field('Tên đăng nhập', username, usernameHint),
    field('Mật khẩu', password, passwordHint),
    confirmField,
    message,
    submit);

  setMode('login');

  const el = h('div', { class: 'auth' },
    h('header', { class: 'page-head' },
      h('span', { class: 'eyebrow' }, 'Ngôn ngữ ký hiệu Việt Nam'),
      title,
      lead),
    h('section', { class: 'card' },
      h('div', { class: 'card__body auth__body' },
        h('div', { class: 'tabs', role: 'tablist', 'aria-label': 'Đăng nhập hoặc đăng ký' }, tabs.login, tabs.register),
        form)));

  return {
    el,
    title: MODES[mode].title,
    focus: () => username.focus(),
    onKey: () => false,
  };
}
