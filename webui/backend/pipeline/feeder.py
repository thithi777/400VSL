"""Bước 3: feeder lúc test, chép từ feeders28/feeder_ntu.py và feeders/tools.py.

test_feeder_args: normalization=True, p_interval=[1], window_size=64, random_rot=False, bone=False.
"""
import numpy as np
import torch
import torch.nn.functional as F

NECK = 24
SHO_L, SHO_R = 22, 23


def valid_crop_resize(data_numpy, valid_frame_num, p_interval, window):
    """feeders/tools.py: cắt phần hợp lệ rồi nội suy song tuyến về `window` frame. Input (C, T, V, M)."""
    C, T, V, M = data_numpy.shape
    begin = 0
    end = valid_frame_num
    valid_size = end - begin

    if len(p_interval) == 1:
        p = p_interval[0]
        bias = int((1 - p) * valid_size / 2)
        data = data_numpy[:, begin + bias:end - bias, :, :]
        cropped_length = data.shape[1]
    else:
        p = np.random.rand(1) * (p_interval[1] - p_interval[0]) + p_interval[0]
        cropped_length = np.minimum(np.maximum(int(np.floor(valid_size * p)), 64), valid_size)
        bias = np.random.randint(0, valid_size - cropped_length + 1)
        data = data_numpy[:, begin + bias:begin + bias + cropped_length, :, :]

    data = torch.tensor(data, dtype=torch.float)
    data = data.permute(0, 2, 3, 1).contiguous().view(C * V * M, cropped_length)
    data = data[None, None, :, :]
    data = F.interpolate(data, size=(C * V * M, window), mode="bilinear", align_corners=False).squeeze()
    data = data.contiguous().view(C, V, M, window).permute(0, 3, 1, 2).contiguous().numpy()

    return data


def to_model_input(fused, window=64):
    """(3, 64, 28) từ fuse() -> (1, 3, 64, 28, 1) float32, đúng như Feeder.__getitem__ ở pha test."""
    data_numpy = np.array(fused, dtype=np.float32)[:, :, :, np.newaxis]  # (C, T, V, M)

    # Điểm 24: mũi -> cổ = trung điểm 2 vai
    data_numpy[:, :, NECK] = (data_numpy[:, :, SHO_L] + data_numpy[:, :, SHO_R]) / 2

    # normalization: True -> lấy cổ làm tâm
    data_numpy = data_numpy - data_numpy[:, :, NECK:NECK + 1, :]

    valid_frame_num = np.sum(data_numpy.sum(0).sum(-1).sum(-1) != 0)
    if valid_frame_num == 0:
        valid_frame_num = data_numpy.shape[1]

    data_numpy = valid_crop_resize(data_numpy, valid_frame_num, [1], window)
    return data_numpy[np.newaxis].astype(np.float32)
