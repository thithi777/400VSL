# Web UI VSL400: học và nhận diện ký hiệu

Ứng dụng web chạy trên máy (localhost), dùng HD-GCN `weight_model/runs-top_epoch39_acc_94.10.pt`.

- **Bài học**: 400 ký hiệu chia 29 chủ đề. Mỗi bài có video mẫu của người biểu diễn 008. Người học làm theo
  trước webcam (đếm ngược 3 s, ghi 64 frame = 2,56 s ở 25 fps) hoặc tải video lên. Kết quả gồm: mô hình có
  nhận ra đúng ký hiệu không, điểm, nhận xét và điểm từng bộ phận, bản ghi của người học (chỉ video,
  không vẽ khung xương). Video mẫu cũng không có khung xương.
- **Luyện tập** (`#/luyen-tap`): chọn một chủ đề hoặc cả 400 ký hiệu. Mỗi lượt bốc ngẫu nhiên một ký hiệu,
  người học tự biểu diễn **không có video mẫu**; chấm xong chọn *Luyện lại* (phím R) hoặc *Ký hiệu khác* (phím N).
  Ký hiệu đã làm đúng (model xếp hạng 1) không bị bốc lại; đạt hết thì có nút *Luyện lại từ đầu*.
  Tiến độ luyện tập tách riêng với tiến độ bài học.
- **Nhận diện tự do**: top-5 trong 400 ký hiệu, xem lại bản ghi, lịch sử phiên.

## Chạy

```powershell
cd "C:\D\Sign Recognize\SDA-GCN"
.venv\Scripts\activate
pip install -r webui\requirements.txt          # lần đầu
python -X utf8 webui\run.py --open             # http://127.0.0.1:8000
```

Cần GPU CUDA (EdgeConv của HD-GCN). Webcam chỉ hoạt động trên `localhost`/`127.0.0.1` (hoặc https).
Font tải từ Google Fonts; khi không có mạng, trang tự dùng Segoe UI (vẫn đủ dấu tiếng Việt).

## Tài khoản và dữ liệu người học

- Phải **đăng ký / đăng nhập** mới dùng được (kể cả xem video mẫu). Tên đăng nhập 3-32 ký tự
  (chữ không dấu, số, `.`, `_`, không phân biệt hoa thường), mật khẩu 8-128 ký tự, băm bằng Argon2id.
- Phiên đăng nhập giữ 30 ngày bằng cookie `HttpOnly`, `SameSite=Lax` (tự thêm `Secure` khi chạy qua https).
- Đăng nhập sai 10 lần trong 15 phút thì tài khoản bị khoá tạm 15 phút; mỗi mạng (IP) tạo tối đa 60 tài khoản/giờ.
- Máy chủ tự lưu sau mỗi lần chấm: lịch sử (`attempts`: bài, kết luận, điểm, thời gian, `mode` = practice /
  drill / free), tiến độ từng bài học (`progress`) và tiến độ luyện tập (`drill_progress`; `POST /api/drill/reset`
  bỏ đánh dấu đã đạt). **Không lưu video hay ảnh webcam.** Bảng mới được tự tạo khi khởi động, không đụng dữ liệu cũ.
- CSDL mặc định là SQLite `webui/instance/vsl400.db` (không đưa lên git). Sao lưu = chép file này khi server
  đã dừng. Muốn dùng PostgreSQL: đặt `VSL_DATABASE_URL` và cài driver (ví dụ `psycopg`).

## Hàng đợi chấm bài

Mỗi lần chấm mất khoảng 3 s, phần lớn là MediaPipe trên CPU; mô hình trên GPU chỉ khoảng 0,1 s.

- Tối đa `VSL_WORKERS` lượt chạy song song (mặc định 3), tối đa `VSL_QUEUE_MAX` lượt chờ (mặc định 20).
- Hàng đầy thì trả 503 kèm `Retry-After` **trước khi nhận dữ liệu**, nên RAM và số luồng luôn có giới hạn.
  Ảnh webcam chỉ được giải mã khi tới lượt (người đang chờ chiếm khoảng 1,3 MB thay vì khoảng 60 MB).

## Dữ liệu qua mạng mỗi lượt chấm

Máy chủ đặt ở nhà thường có chiều tải lên chậm (đo được 0,7 Mbit/s), nên mỗi lượt gửi càng ít càng tốt:

- Webcam gửi 64 ảnh 540 x 540 JPEG chất lượng 0,85: khoảng 1,3 MB. Trên 80 video mẫu, mức này nhận đúng
  như 720 px (98,8 %, trùng 100 % dự đoán); 480 px bắt đầu sai thêm. Đổi bằng `CAPTURE_MAX_SIDE`,
  `CAPTURE_JPEG_QUALITY` trong `backend/config.py`.
- Với webcam, máy chủ không gửi lại ảnh xem lại (trình duyệt dùng chính ảnh vừa ghi), kết quả chỉ vài chục KB.
  Video tải lên vẫn nhận ảnh xem lại (khoảng 1 MB) vì trình duyệt có thể không phát được codec của video.
- Thanh tiến độ hiện số MB đã gửi, rồi vị trí trong hàng chờ, rồi từng bước chấm.
- Mỗi tài khoản chỉ có một lượt trong hàng (gửi thêm trả 409). Người chờ thấy vị trí và số giây ước tính.
  Đóng tab thì lượt bị huỷ, nhả chỗ cho người sau.
- `GET /api/status` cho biết số lượt đang chạy / đang chờ và thời gian trung bình một lượt.

Đo trên i5-11400H (6 nhân): 1 luồng 0,34 lượt/s, 4 luồng 0,78 lượt/s. Mỗi người luyện tập gửi khoảng
một lượt mỗi 20-30 s, nên một máy chủ kiểu này phục vụ tốt khoảng vài chục người luyện **cùng lúc**.

## Cho người khác truy cập (chưa cần tên miền)

```powershell
$env:VSL_WORKERS = "4"            # tuỳ số nhân CPU của máy chủ
python -X utf8 webui\run.py       # chỉ nghe trên 127.0.0.1
cloudflared tunnel --url http://127.0.0.1:8000
```

`cloudflared` in ra địa chỉ `https://....trycloudflare.com` (đổi mỗi lần chạy lại). Đây là Quick Tunnel dùng
để thử nghiệm: Cloudflare giới hạn 200 yêu cầu đồng thời và không cam kết ổn định. Khi có tên miền, chuyển
sang Cloudflare Tunnel có tên; code không cần sửa. uvicorn đã tin header `X-Forwarded-*` từ 127.0.0.1 nên
IP người dùng (để chặn dò mật khẩu) và https (cookie `Secure`) được nhận đúng.

## Cấu trúc

```
webui/
├── run.py                     khởi động uvicorn
├── backend/
│   ├── config.py              đường dẫn, hằng số, biến môi trường VSL_* (CSDL, hàng đợi)
│   ├── app.py                 FastAPI: nạp model khi khởi động, phục vụ frontend + video mẫu (cần đăng nhập)
│   ├── db.py                  SQLAlchemy: users, sessions, progress, attempts
│   ├── api/                   route: status, auth/*, catalog, lessons/{label}, progress,
│   │                          analyze (NDJSON tiến độ + kết quả)
│   ├── pipeline/              tiền xử lý GIỐNG HỆT lúc train (HANDOFF.md mục 3)
│   │   ├── landmarks.py       MediaPipe Tasks Pose FULL + Hand, 28 điểm (chép extractkpt/mp_landmarkers.py)
│   │   ├── extract.py         frame RGB -> (T, 28, 3)
│   │   ├── fusion.py          interpolate -> normalize -> Kalman RTS -> fit_length (chép fusion/)
│   │   └── feeder.py          điểm 24 = cổ, trừ cổ, valid_crop_resize (chép feeders28/, feeders/tools.py)
│   ├── inference/             nạp HD-GCN (import model/model28/SDAGCN.py của dự án) + softmax
│   ├── coaching/              so với video mẫu
│   │   ├── features.py        4 bộ phận: hình dạng / vị trí mỗi tay, toạ độ gốc cổ, đơn vị vai
│   │   ├── dtw.py             DTW hai đầu nới lỏng
│   │   ├── compare.py         trọng số theo tay được dùng, điểm 0-100, phát hiện dùng ngược tay
│   │   └── feedback.py        nhận xét tiếng Việt
│   └── services/              đọc media, danh mục bài học, Analyzer (ghép các bước, báo tiến độ),
│                              auth (tài khoản, phiên), queue (hàng đợi chấm), records (lưu kết quả)
├── frontend/                  HTML/CSS/JS thuần (ES modules, không cần build)
│   ├── css/                   tokens, base, components, views
│   └── js/                    lib/ (DOM, icon), components/, views/, router, api, store
├── data/
│   ├── topics.json            5 nhóm, 29 chủ đề, đủ 400 label
│   ├── references.json        label -> video mẫu (sinh bởi scripts/build_references.py)
│   └── calibration.json       ngưỡng điểm DTW (sinh bởi scripts/calibrate_coaching.py)
├── media/reference/           400 video mẫu H.264 720x720 + keypoint thô tương ứng (bản sao)
├── instance/                  vsl400.db (SQLite, tạo khi chạy lần đầu, không đưa lên git)
└── scripts/
    ├── verify_pipeline.py     kiểm chứng keypoint, fusion, dự đoán khớp với lúc test
    ├── build_references.py    chọn video mẫu, chuyển H.264, chép keypoint
    └── calibrate_coaching.py  hiệu chuẩn thang điểm so sánh
```

## Kiểm chứng pipeline

```powershell
python -X utf8 webui\scripts\verify_pipeline.py --num 8
```

So với `data/VSL400/keypoints`, `data/vsl400fusion/test` và `weight_model/epoch39_test_score.pkl`.
Kết quả hiện tại: 20/20 video test khớp tuyệt đối ở cả keypoint, fusion và nhãn dự đoán.

## Cách chấm bài luyện

1. **Đúng/sai** do chính HD-GCN quyết định: ký hiệu của bài đứng hạng 1 là *Đúng*, trong top-5 là *Gần đúng*.
2. **Điểm bài** = 70 % xác suất HD-GCN gán cho ký hiệu của bài + 30 % độ giống mẫu.
   Trên 300 video test (trừ người mẫu 008): 292 video được nhận đúng có điểm p10 / trung vị = 89 / 100,
   không video nào dưới 60; 8 video bị nhận sai có điểm 9 đến 60.
3. **Độ giống mẫu và chỗ cần sửa** do DTW: căn thời gian chuỗi khung xương của người học với video mẫu,
   rồi đo lệch từng bộ phận (hình dạng bàn tay, vị trí cổ tay và khuỷu) theo 3 đoạn đầu / giữa / cuối,
   từng ngón và hướng lệch. Tay mà video mẫu không dùng chỉ có trọng số nhỏ.
4. **Thang DTW** hiệu chuẩn từ dữ liệu (`calibrate_coaching.py`): lệch bằng trung vị giữa hai ký hiệu
   *khác nhau* -> 0 điểm. Mức được 100 điểm phụ thuộc kết luận của model:
   - model nhận đúng: phân vị 75 giữa hai người làm *cùng* ký hiệu (khác biệt lúc này chủ yếu là phong
     cách; nhận xét chỉ là gợi ý "để giống mẫu hơn");
   - model nhận sai: trung vị (chặt hơn, để chỉ ra chỗ sai).
   DTW một mình chỉ phân biệt đúng/sai ở mức AUC ~0,85, vì vậy không dùng làm điểm chính.
5. Nếu khớp tốt hơn hẳn khi đổi tay (người thuận tay trái), hệ thống báo và chấm trên chuỗi đã đổi tay.

Vì sao không dùng Grad-CAM: Grad-CAM cho biết mô hình *nhìn vào* khớp nào khi đoán, không cho biết người học
làm *sai ở đâu* so với mẫu, và không cho hướng sửa (cao hơn, sang trái, ngón nào). DTW trên khung xương trả
lời trực tiếp các câu đó, còn quyết định đúng/sai vẫn để cho HD-GCN.

## Dựng lại dữ liệu mẫu (khi cần)

```powershell
python -X utf8 webui\scripts\build_references.py        # khoảng 2 phút
python -X utf8 webui\scripts\calibrate_coaching.py      # khoảng 2 phút
```
