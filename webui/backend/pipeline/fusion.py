"""Bước 2: fusion, chép từ fusion/ (interpolate.py, normalize_pose.py, kalman_filter.py,
generate_fused_features.py). Không import fusion/generate_fused_features.py vì file đó
gọi os.chdir khi import.

Thứ tự: interpolate_missing -> normalize_pose -> apply_kalman_filter -> fit_length.
Không có augment (chỉ dùng lúc train).
"""
import numpy as np

SHO_L, SHO_R, HIP_C = 22, 23, 25


def interpolate_missing(kpts):
    """Điểm thiếu (x = y = 0) -> nội suy tuyến tính theo thời gian; thiếu ở biên giữ giá trị gần nhất."""
    kpts = kpts.astype(np.float32).copy()
    T, V, C = kpts.shape
    t = np.arange(T)

    valid = (kpts[:, :, 0] != 0) | (kpts[:, :, 1] != 0)  # (T, V)

    for v in range(V):
        ok = valid[:, v]
        if ok.all() or not ok.any():
            continue
        for c in range(C):
            kpts[~ok, v, c] = np.interp(t[~ok], t[ok], kpts[ok, v, c])

    return kpts


def normalize_pose(pose):
    """Dời tâm về (2 vai + 2 x tâm hông) / 4 từng frame, chia cho chiều rộng vai trung bình."""
    data = pose.astype(np.float32).copy()

    empty = np.all(data[:, :, :2] == 0, axis=(0, 2))  # (V,) khớp toàn 0 cả video

    x = data[:, :, 0]
    y = data[:, :, 1]

    center_x = (x[:, SHO_L] + x[:, SHO_R] + 2 * x[:, HIP_C]) / 4
    center_y = (y[:, SHO_L] + y[:, SHO_R] + 2 * y[:, HIP_C]) / 4

    dx = x[:, SHO_L] - x[:, SHO_R]
    dy = y[:, SHO_L] - y[:, SHO_R]
    scale = np.sqrt(dx ** 2 + dy ** 2).mean()
    if scale < 1e-6:
        scale = 1

    data[:, :, 0] -= center_x[:, None]
    data[:, :, 1] -= center_y[:, None]
    data /= scale

    data[:, empty] = 0

    return data.astype(np.float32)


def apply_kalman_filter(kpts, process_noise=1e-3, measurement_noise=1e-3):
    """Kalman 1D random-walk cho từng khớp x kênh, lọc xuôi + làm mượt ngược (RTS)."""
    x = kpts.astype(np.float64)
    T = x.shape[0]
    Q, R = process_noise, measurement_noise

    x_filt = np.empty_like(x)
    P_filt = np.empty(T)
    P_pred = np.empty(T)

    state = x[0]
    P = R
    x_filt[0], P_filt[0], P_pred[0] = state, P, P

    for t in range(1, T):
        P_prior = P + Q
        K = P_prior / (P_prior + R)
        state = state + K * (x[t] - state)
        P = (1 - K) * P_prior
        x_filt[t], P_filt[t], P_pred[t] = state, P, P_prior

    smoothed = x_filt.copy()
    for t in range(T - 2, -1, -1):
        G = P_filt[t] / P_pred[t + 1]
        smoothed[t] = x_filt[t] + G * (smoothed[t + 1] - x_filt[t])

    return smoothed.astype(np.float32)


def fit_length(kpts, max_frames=64):
    """Dài hơn max_frames: lấy mẫu đều (nội suy tuyến tính). Ngắn hơn: pad 0 ở cuối."""
    T, V, C = kpts.shape

    if T > max_frames:
        src = np.arange(T)
        dst = np.linspace(0, T - 1, max_frames)
        flat = kpts.reshape(T, -1)
        kpts = np.stack([np.interp(dst, src, flat[:, i]) for i in range(flat.shape[1])], axis=1)
        kpts = kpts.reshape(max_frames, V, C)
    elif T < max_frames:
        pad = np.zeros((max_frames - T, V, C), dtype=kpts.dtype)
        kpts = np.concatenate([kpts, pad], axis=0)

    return kpts.astype(np.float32)


def smooth_sequence(raw):
    """(T, 28, 3) thô -> (T, 28, 3) đã nội suy, chuẩn hóa, làm mượt; chưa đổi độ dài.
    Dùng chung cho model (qua fuse) và cho phần so sánh với video mẫu."""
    kpt = interpolate_missing(raw)
    kpt = normalize_pose(kpt)
    return apply_kalman_filter(kpt)


def fuse(raw, max_frames=64):
    """(T, 28, 3) thô -> (3, 64, 28), giống process_one_sample(augment=False)."""
    kpt = fit_length(smooth_sequence(raw), max_frames)
    return np.transpose(kpt, (2, 0, 1))
