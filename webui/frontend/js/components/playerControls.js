// Thanh điều khiển dùng chung: phát/dừng, tua theo frame, tốc độ.
import { h } from '../lib/dom.js';
import { icon, iconSvg } from '../lib/icons.js';
import { seconds } from '../lib/format.js';

export function createControls({
  total,
  fps,
  onPlayToggle,
  onSeek,
  speeds = [0.5, 1],
  speed = 1,
  onSpeed = null,
}) {
  const playBtn = h('button', {
    class: 'btn btn--ghost btn--icon',
    type: 'button',
    'aria-label': 'Phát',
    onClick: () => onPlayToggle(),
  }, icon('play'));

  const scrubber = h('input', {
    class: 'scrubber',
    type: 'range',
    min: 0,
    max: Math.max(total - 1, 0),
    step: 1,
    value: 0,
    'aria-label': 'Vị trí frame',
  });
  scrubber.addEventListener('input', () => onSeek(Number(scrubber.value)));

  const time = h('span', { class: 'player__time' });

  const speedBtns = onSpeed
    ? speeds.map((s) => {
      const btn = h('button', {
        class: 'toggle',
        type: 'button',
        'aria-pressed': String(s === speed),
        title: `Tốc độ ${s}×`,
      }, `${String(s).replace('.', ',')}×`);
      btn.addEventListener('click', () => {
        speedBtns.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
        onSpeed(s);
      });
      return btn;
    })
    : [];

  const el = h('div', { class: 'player__bar' },
    playBtn,
    scrubber,
    time,
    h('div', { class: 'player__toggles' }, speedBtns));

  const totalSec = total / fps;

  function setFrame(i) {
    scrubber.value = String(i);
    const pct = total > 1 ? (i / (total - 1)) * 100 : 0;
    scrubber.style.setProperty('--progress', `${pct}%`);
    time.textContent = `${seconds(i / fps)} / ${seconds(totalSec)}`;
  }

  function setPlaying(playing) {
    playBtn.innerHTML = '';
    playBtn.append(h('span', { class: 'icon', html: iconSvg(playing ? 'pause' : 'play') }));
    playBtn.setAttribute('aria-label', playing ? 'Tạm dừng' : 'Phát');
  }

  setFrame(0);
  setPlaying(false);
  return { el, setFrame, setPlaying };
}
