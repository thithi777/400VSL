# 400VSL – Web học ngôn ngữ ký hiệu tiếng Việt

Ứng dụng web dạy và nhận diện **400 ký hiệu tiếng Việt** (bộ dữ liệu VSL400). Người học xem video mẫu, biểu diễn
trước webcam (hoặc tải video lên) và được chấm điểm, kèm nhận xét chỗ cần sửa.

- **Bài học:** 400 ký hiệu chia theo 29 chủ đề, mỗi bài có video mẫu.
- **Luyện tập:** bốc ngẫu nhiên ký hiệu và biểu diễn khi không xem video mẫu.
- **Nhận diện tự do:** trả về 5 ký hiệu khớp nhất.
- Có tài khoản (đăng ký / đăng nhập). Máy chủ lưu tiến độ học, **không lưu video hay ảnh webcam**.

Mô hình: SDA-GCN (dựa trên HD-GCN) trên 28 điểm khung xương nửa thân trên do MediaPipe trích ra.
Độ chính xác top-1 trên tập test (những người biểu diễn không có trong tập train) là 97,86 %.

## Yêu cầu

- **GPU NVIDIA có CUDA (bắt buộc).** Mô hình không chạy được trên CPU. Đã chạy được trên GTX 1650 4 GB và RTX 3080.
- Driver NVIDIA mới (hỗ trợ CUDA 12.4 trở lên). Kiểm tra bằng lệnh `nvidia-smi`.
- Dung lượng trống: khoảng 3 GB khi cài bằng Python, khoảng 8 GB khi dùng Docker.

Có hai cách chạy, chọn một trong hai.

## Cách 1: Docker (khuyên dùng)

Cần Docker Desktop (Windows: bật WSL 2) hoặc Docker Engine kèm NVIDIA Container Toolkit (Linux).

```bash
git clone https://github.com/thithi777/400VSL.git
cd 400VSL
docker compose up -d --build      # lần đầu tải khoảng 3 GB, mất 10–30 phút
```

Mở http://127.0.0.1:8000 và đăng ký tài khoản. Lúc mới bật, máy chủ mất khoảng 10–20 giây để nạp mô hình.

| Việc cần làm | Lệnh |
|---|---|
| Xem log | `docker compose logs -f` |
| Dừng | `docker compose down` |
| Chạy lại sau khi cập nhật code | `git pull` rồi `docker compose up -d --build` |
| Kiểm tra container thấy GPU | `docker compose exec web nvidia-smi` |

Tài khoản và tiến độ nằm trong volume `vsl400-data`, không mất khi dừng hay build lại.
Chỉ lệnh `docker compose down -v` mới xoá volume này.

## Cách 2: Python

Cần Python **3.11**.

**Windows (PowerShell):**

```powershell
git clone https://github.com/thithi777/400VSL.git
cd 400VSL
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
python -X utf8 webui\run.py --open
```

**Linux:**

```bash
git clone https://github.com/thithi777/400VSL.git
cd 400VSL
python3.11 -m venv .venv
source .venv/bin/activate
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
python -X utf8 webui/run.py
```

Mở http://127.0.0.1:8000. Lần sau chỉ cần kích hoạt `.venv` rồi chạy dòng `python ... run.py` cuối cùng.
Đổi cổng: thêm `--port 8001`.

## Cho người khác truy cập qua Internet

Webcam trên trình duyệt chỉ chạy ở `localhost` hoặc qua **https**. Cách đơn giản nhất là Cloudflare Tunnel
(miễn phí, không cần mở cổng router). Cài [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/),
giữ server đang chạy rồi gõ:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Lệnh in ra một địa chỉ `https://....trycloudflare.com` để gửi cho người khác. Địa chỉ này đổi mỗi lần chạy lại;
muốn có địa chỉ cố định thì tạo tunnel có tên gắn với tên miền riêng trong Cloudflare Zero Trust.

Máy chủ đã nhận đúng IP thật của người dùng (để chặn dò mật khẩu) và https (cookie `Secure`) khi đứng sau
cloudflared, ở cả hai cách chạy.

## Cấu hình

Đặt bằng biến môi trường: với Docker sửa phần `environment` trong `docker-compose.yml`, với Python đặt trước
khi chạy (PowerShell: `$env:VSL_WORKERS = "4"`).

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `VSL_WORKERS` | `3` | Số bài chấm cùng lúc. Nên đặt bằng khoảng 2/3 số nhân CPU |
| `VSL_QUEUE_MAX` | `20` | Số lượt được xếp hàng chờ. Hàng đầy thì báo người dùng thử lại sau |
| `VSL_DATABASE_URL` | SQLite `webui/instance/vsl400.db` | CSDL khác, ví dụ PostgreSQL (cần cài thêm driver) |

Mỗi lượt chấm mất khoảng 3 giây, phần lớn là MediaPipe chạy trên CPU. Một máy laptop tầm trung phục vụ được
khoảng 20–30 người luyện tập cùng lúc.

## Cấu trúc

```
├── webui/
│   ├── run.py                 khởi động server
│   ├── backend/               FastAPI: tài khoản, hàng đợi, trích khung xương, mô hình, chấm điểm
│   ├── frontend/              giao diện HTML/CSS/JS (không cần build)
│   ├── data/                  chủ đề, danh sách video mẫu, thang điểm
│   ├── media/reference/       400 video mẫu và khung xương tương ứng
│   └── instance/              CSDL tài khoản (tự tạo khi chạy, không đưa lên git)
├── model/model28/SDAGCN.py    kiến trúc mô hình
├── graph28/                   đồ thị 28 điểm khung xương
├── weight_model/              trọng số đã train
├── mp_models/                 mô hình MediaPipe (Pose + Hand)
├── data/VSL400/check_csv.csv  tên 400 ký hiệu
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

Chi tiết kỹ thuật (cách chấm điểm, hàng đợi, dữ liệu gửi qua mạng) có trong `webui/README.md`.

## Sao lưu tài khoản

- **Python:** dừng server rồi chép file `webui/instance/vsl400.db`.
- **Docker:** dừng container (`docker compose stop`), chạy `docker cp vsl400-web:/app/webui/instance/vsl400.db ./vsl400.db`,
  rồi bật lại bằng `docker compose start`. Muốn đưa một file CSDL có sẵn vào container thì làm ngược lại
  (`docker cp ./vsl400.db vsl400-web:/app/webui/instance/vsl400.db` khi container đang dừng).

## Lưu ý

- Video mẫu lấy từ bộ dữ liệu VSL400, có hình người biểu diễn. Chỉ dùng cho học tập và nghiên cứu.
- Nếu gặp lỗi "cần GPU CUDA": kiểm tra `nvidia-smi`. Với Docker thì kiểm tra thêm Docker Desktop đang dùng WSL 2
  và driver NVIDIA trên Windows đã được cập nhật.
