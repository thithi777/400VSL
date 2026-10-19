"""Đường dẫn và hằng số dùng chung cho toàn bộ web UI.

Mọi đường dẫn tính từ vị trí file này nên chạy được từ bất kỳ thư mục làm việc nào.
Các giá trị đọc từ biến môi trường VSL_* có thể đổi khi triển khai mà không sửa code.
"""
import os
from pathlib import Path

WEBUI_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = WEBUI_DIR.parent  # SDA-GCN

# ------------------------------------------------------------------
# Model (giống weight_model/config.yaml)
# ------------------------------------------------------------------
WEIGHTS_PATH = PROJECT_DIR / "weight_model" / "runs-top_epoch39_acc_94.10.pt"
MODEL_CLASS = "model.model28.SDAGCN.Model"
MODEL_ARGS = {
    "num_class": 400,
    "num_point": 28,
    "num_person": 1,
    "graph": "graph28.ntu_rgb_d_hierarchy.Graph",
    "graph_args": {"labeling_mode": "spatial", "CoM": 24},
    "in_channels": 3,
    "drop_out": 0.5,
    "adaptive": True,
}
CUDA_DEVICE = "cuda:0"

# ------------------------------------------------------------------
# Dữ liệu gốc của dự án (chỉ đọc)
# ------------------------------------------------------------------
MP_MODEL_DIR = PROJECT_DIR / "mp_models"
DATA_DIR = PROJECT_DIR / "data" / "VSL400"
GLOSS_CSV = DATA_DIR / "check_csv.csv"
METADATA_JSON = DATA_DIR / "front_view.json"
VIDEO_DIR = DATA_DIR / "front_view"
KEYPOINT_DIR = DATA_DIR / "keypoints"
TEST_SCORE_PKL = PROJECT_DIR / "weight_model" / "epoch39_test_score.pkl"
SPLIT_CSV_DIR = PROJECT_DIR / "data" / "csv"

# ------------------------------------------------------------------
# Dữ liệu riêng của web UI
# ------------------------------------------------------------------
TOPICS_JSON = WEBUI_DIR / "data" / "topics.json"
REFERENCES_JSON = WEBUI_DIR / "data" / "references.json"
CALIBRATION_JSON = WEBUI_DIR / "data" / "calibration.json"
REFERENCE_DIR = WEBUI_DIR / "media" / "reference"
REFERENCE_VIDEO_DIR = REFERENCE_DIR / "videos"
REFERENCE_KEYPOINT_DIR = REFERENCE_DIR / "keypoints"
FRONTEND_DIR = WEBUI_DIR / "frontend"

# Người biểu diễn làm video mẫu: phát hiện tay tốt nhất (98,2 % frame), test 98,7 %
REFERENCE_SIGNER = "008"

# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------
WINDOW = 64            # số frame đầu vào model
DEFAULT_FPS = 25.0     # fps của VSL400 và của webcam khi ghi

# ------------------------------------------------------------------
# Ghi webcam (trình duyệt đọc qua /api/status)
# ------------------------------------------------------------------
CAPTURE_COUNTDOWN_S = 3    # đếm ngược cho người biểu diễn chuẩn bị
CAPTURE_FRAMES = 64        # 64 frame ở 25 fps = 2,56 s; chỉ đoạn này được gửi đi
# Cắt vuông ở giữa rồi thu về cạnh tối đa này (video train 1080 x 1080). Đo trên 80 video mẫu:
# 720 px JPEG 92: 2,76 MB/lượt, top-1 98,8 % | 540 px JPEG 85: 1,31 MB, 98,8 %, trùng 100 % dự đoán
# | 480 px JPEG 80: 0,96 MB, 97,5 %. Chọn 540: nhẹ gấp đôi mà không mất độ chính xác (mạng chậm vẫn gửi nhanh).
CAPTURE_MAX_SIDE = 540
CAPTURE_JPEG_QUALITY = 0.85

# ------------------------------------------------------------------
# Giới hạn đầu vào và ảnh xem lại
# ------------------------------------------------------------------
MAX_UPLOAD_MB = 200
MAX_FRAMES = 500       # 20 s ở 25 fps; model coi cả đoạn là MỘT ký hiệu
PREVIEW_SIZE = 384     # cạnh dài của ảnh xem lại gửi về trình duyệt
PREVIEW_QUALITY = 80

# ------------------------------------------------------------------
# Tài khoản và dữ liệu người học
# ------------------------------------------------------------------
INSTANCE_DIR = WEBUI_DIR / "instance"   # CSDL SQLite mặc định; không đưa lên git
DATABASE_URL = os.environ.get("VSL_DATABASE_URL", f"sqlite:///{(INSTANCE_DIR / 'vsl400.db').as_posix()}")
SESSION_COOKIE = "vsl400_session"
SESSION_DAYS = 30
USERNAME_MIN, USERNAME_MAX = 3, 32
PASSWORD_MIN, PASSWORD_MAX = 8, 128

# ------------------------------------------------------------------
# Hàng đợi chấm bài (đo trên i5-11400H: ~3 s/bài, 88 % là MediaPipe trên CPU)
# ------------------------------------------------------------------
QUEUE_WORKERS = int(os.environ.get("VSL_WORKERS", "3"))         # số bài chấm song song
QUEUE_MAX_WAITING = int(os.environ.get("VSL_QUEUE_MAX", "20"))  # đầy thì từ chối ngay, trước khi nhận dữ liệu
UPLOAD_TIMEOUT_S = 120                                          # tải lên lâu hơn thì huỷ, nhả chỗ trong hàng

HOST = "127.0.0.1"
PORT = 8000
