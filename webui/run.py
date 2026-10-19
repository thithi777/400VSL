"""Khởi động web UI.

Trong thư mục SDA-GCN, đã kích hoạt .venv:
    python -X utf8 webui\\run.py            # mở http://127.0.0.1:8000
    python -X utf8 webui\\run.py --open     # tự mở trình duyệt
"""
import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")   # ẩn log của MediaPipe/TFLite
os.environ.setdefault("GLOG_minloglevel", "2")

WEBUI_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(WEBUI_DIR))

import uvicorn  # noqa: E402

from backend.config import HOST, PORT  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Web UI học ngôn ngữ ký hiệu VSL400")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--open", action="store_true", help="tự mở trình duyệt")
    args = parser.parse_args()

    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}"
    if args.open:
        threading.Timer(4.0, lambda: webbrowser.open(url)).start()
    print(f"VSL400 web UI: {url}  (Ctrl+C để dừng)")
    uvicorn.run("backend.app:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
