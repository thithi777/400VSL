"""HD-GCN (model/model28/SDAGCN.py) + weight_model/runs-top_epoch39_acc_94.10.pt.

Kiến trúc mạng được import từ chính thư mục dự án (không chép) để luôn khớp với
trọng số đã train. Model chỉ chạy trên CUDA (EdgeConv dùng x.get_device()).
"""
import importlib
import sys
from collections import OrderedDict

import numpy as np
import torch

from ..config import CUDA_DEVICE, MODEL_ARGS, MODEL_CLASS, PROJECT_DIR, WEIGHTS_PATH


def _import_class(name):
    """'a.b.C' -> class C. Nạp cả module con (SDAGCN tự import graph bằng __import__ + getattr)."""
    if str(PROJECT_DIR) not in sys.path:
        sys.path.append(str(PROJECT_DIR))
    module_name, class_name = name.rsplit(".", 1)
    return getattr(importlib.import_module(module_name), class_name)


class SignRecognizer:
    def __init__(self, weights_path=WEIGHTS_PATH, device=CUDA_DEVICE):
        if not torch.cuda.is_available():
            raise RuntimeError("SDA-GCN cần GPU CUDA (EdgeConv dùng x.get_device()), không tìm thấy CUDA.")

        self.device = torch.device(device)
        self.weights_path = weights_path

        _import_class(MODEL_ARGS["graph"])  # nạp sẵn module graph cho import_class bên trong SDAGCN
        Model = _import_class(MODEL_CLASS)
        model = Model(**MODEL_ARGS)

        # Giống main1.py: bỏ tiền tố 'module.' (nếu checkpoint lưu từ DataParallel)
        weights = torch.load(str(weights_path), map_location="cpu")
        weights = OrderedDict((k.split("module.")[-1], v) for k, v in weights.items())
        model.load_state_dict(weights)

        self.model = model.to(self.device).eval()
        self.num_class = MODEL_ARGS["num_class"]
        self.gpu_name = torch.cuda.get_device_name(self.device)

    def warm_up(self):
        """Chạy thử một lần để CUDA khởi tạo kernel trước yêu cầu đầu tiên."""
        self.logits(np.zeros((1, 3, 64, MODEL_ARGS["num_point"], 1), dtype=np.float32))

    @torch.no_grad()
    def logits(self, batch):
        """batch: (N, 3, 64, 28, 1) float32 -> (N, 400) logit (numpy)."""
        x = torch.from_numpy(np.ascontiguousarray(batch, dtype=np.float32)).to(self.device)
        return self.model(x).float().cpu().numpy()

    def probabilities(self, batch):
        """(N, 3, 64, 28, 1) -> (N, 400) xác suất softmax."""
        z = self.logits(batch)
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)
