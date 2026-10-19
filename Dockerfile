# syntax=docker/dockerfile:1
# Web học ngôn ngữ ký hiệu VSL400 (SDA-GCN). Model chỉ chạy trên GPU NVIDIA (CUDA).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PIP_RESUME_RETRIES=50

# Thư viện hệ thống mà OpenCV / MediaPipe cần
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# PyTorch nặng nhất (~2,5 GB) nên cài thành một lớp riêng, sửa code không phải tải lại.
# pip >= 25.1 tải tiếp file bị đứt giữa chừng (PIP_RESUME_RETRIES) thay vì báo sai hash.
# Cache pip được giữ giữa các lần build (không nằm trong image): build lại không tải lại gói đã xong.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "pip>=25.1" \
    && pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .

# VSL_WORKERS / VSL_QUEUE_MAX: số bài chấm song song và số lượt được chờ (xem README).
# FORWARDED_ALLOW_IPS: tin X-Forwarded-For/-Proto từ cloudflared trên máy chủ (IP thật của người dùng,
# cookie Secure). An toàn vì docker-compose chỉ mở cổng trên 127.0.0.1 của máy chủ.
ENV VSL_WORKERS=3 \
    VSL_QUEUE_MAX=20 \
    FORWARDED_ALLOW_IPS=*

# CSDL tài khoản và tiến độ (gắn volume để không mất khi tạo lại container)
VOLUME ["/app/webui/instance"]
EXPOSE 8000

CMD ["python", "-X", "utf8", "webui/run.py", "--host", "0.0.0.0", "--port", "8000"]
