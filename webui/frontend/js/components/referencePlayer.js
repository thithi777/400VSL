// Video mẫu (H.264), phát lặp, có tua theo frame và chỉnh tốc độ. Không vẽ khung xương.
import { h } from '../lib/dom.js';
import { createControls } from './playerControls.js';

export function createReferencePlayer({ src, frames, fps = 25 }) {
  const video = h('video', { src, playsinline: true, loop: true, preload: 'auto', 'aria-label': 'Video mẫu' });
  video.muted = true;
  video.autoplay = true;
  const stage = h('div', { class: 'player__stage' }, video);

  let rvfcHandle = null;
  let rafHandle = null;

  const controls = createControls({
    total: frames,
    fps,
    onPlayToggle: () => (video.paused ? video.play().catch(() => {}) : video.pause()),
    onSeek: (i) => {
      video.pause();
      video.currentTime = (i + 0.25) / fps;
      controls.setFrame(i);
    },
    onSpeed: (s) => { video.playbackRate = s; },
  });

  const setFromTime = (t) => controls.setFrame(Math.max(0, Math.min(frames - 1, Math.floor(t * fps + 1e-3))));

  if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) {
    const onFrame = (_now, meta) => {
      setFromTime(meta.mediaTime);
      rvfcHandle = video.requestVideoFrameCallback(onFrame);
    };
    rvfcHandle = video.requestVideoFrameCallback(onFrame);
  } else {
    const loop = () => {
      setFromTime(video.currentTime);
      rafHandle = requestAnimationFrame(loop);
    };
    rafHandle = requestAnimationFrame(loop);
  }

  video.addEventListener('play', () => controls.setPlaying(true));
  video.addEventListener('pause', () => controls.setPlaying(false));
  video.addEventListener('seeked', () => setFromTime(video.currentTime));

  const el = h('div', { class: 'player' }, stage, controls.el);

  return {
    el,
    video,
    togglePlay: () => (video.paused ? video.play().catch(() => {}) : video.pause()),
    destroy() {
      if (rvfcHandle !== null && video.cancelVideoFrameCallback) video.cancelVideoFrameCallback(rvfcHandle);
      if (rafHandle !== null) cancelAnimationFrame(rafHandle);
      video.pause();
      video.removeAttribute('src');
      video.load();
    },
  };
}
