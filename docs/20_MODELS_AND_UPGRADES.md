# AI DESIGN STUDIO — MODEL REGISTRY & UPGRADE LOG

Tài liệu này được cập nhật liên tục mỗi khi tích hợp hoặc nâng cấp mô hình AI cục bộ, bộ font hoặc thuật toán xử lý ảnh trong `D:/AI_Design_Studio/`.

---

## 1. Danh sách Mô hình AI Đang Hoạt động Cục bộ (`100% Offline CPU`)

| STT | Mô hình / Bộ công cụ | Phiên bản / Format | Vị trí lưu trữ | Chức năng trong Pipeline | Tốc độ Thực tế (CPU 16 cores) |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **`Xenova/detr-resnet-50`** | `q8` ONNX (`@huggingface/transformers`) | `models/hf_cache/` | Tự động phát hiện vật thể (`person`, `motorcycle`, `car`, `truck`, `bicycle`, ...) ngay khi import ảnh | ~`8.6s` (gồm tải lần đầu), ~`2–3s` khi cached |
| **2** | **`briaai/RMBG-1.4`** | `q8` ONNX (`@huggingface/transformers`) | `models/hf_cache/` | Tách chủ thể tiền cảnh nổi bật (`Salient Foreground`) độ phân giải gốc | ~`2.5–3.5s` |
| **3** | **`Xenova/slimsam-77-uniform`** | `q8` ONNX + **ROI Zoom-In** | `models/hf_cache/` | Tách vật thể chi tiết theo Box + điểm `+`/`-` (`Mask Level 0/1/2`); tự zoom vùng nhỏ `≥ 512px` giữ sắc nét | ~`2–4s` / object |
| **4** | **`opencv/inpainting_lama`** | `inpainting_lama_2025jan.onnx` (`92.5 MB`, `onnxruntime-node`) | `models/lama/` | Tái tạo nền sạch tự nhiên phía sau vật thể (`01_Background_Clean`) và vá vùng xóa vật thể, thay thế vết nhòe OpenCV Telea | ~`4.7s` / `512×512` tile |
| **5** | **`tesseract.js`** | `v7.0.0` (`vie+eng`) | `models/tessdata/` | OCR tiếng Việt có dấu + word-level bounding box & baseline | ~`1.5–2.5s` / poster |

---

## 2. Bộ Font Tiếng Việt Thương mại Đã Cài đặt (`D:/AI_Design_Studio/assets/fonts/`)

Hệ thống ưu tiên chọn font phù hợp với vai trò hiển thị (`match_local_font()`):
- **Headline Nén / Cao Đậm (`is_condensed_headline && is_uppercase`):** `Anton-Regular.ttf`, `FZ Poppins-ExtraBold.ttf`
- **Headline Đậm Cực đại (`extrabold / black`):** `FZ Poppins-Black.ttf`, `BeVietnamPro-ExtraBold.ttf`, `BeVietnamPro-Bold.ttf`
- **Thân chữ / Mô tả (`regular / medium`):** `BeVietnamPro-Regular.ttf`, `BeVietnamPro-Medium.ttf`, `FZ Poppins-Regular.ttf`
- *(Cùng 300+ font hệ thống Windows làm lựa chọn bổ sung trong dropdown `/api/fonts`).*

---

## 3. Lịch sử Nâng cấp Gần nhất (Semantic Object Auto-Split & Remix)

- **Auto Object-by-Object Extraction (`core/semantic_analyzer.py`):** Tự động tách từng xe, từng nhân vật, thẻ cầm tay và tiền cảnh thành các layer không chồng lấn; giữ nguyên 1:1 pixel gốc; trừ `erode(claimed_fg, 3x3)` để triệt tiêu đường viền tối giữa các mảnh ghép.
- **Bảo vệ vùng Logo & Pháp lý Đáy Poster:** Bảo toàn dải `y > 88%` khỏi bị dilation ăn hụt chữ khi tái tạo nền.
- **Fix `fill_holes()` Corner Inversion Bug (`core/segmentation_engine.py`):** Pad 1px biên `0` trước `cv2.floodFill(..., (0,0), 128)` để không bị đảo ngược mask khi đối tượng chạm mép `(0,0)`.
- **Remix / Lấy Ý tưởng từ Dự án Cũ (`GET /api/projects/remix_catalog`, `POST /api/project/<id>/import_remix`):** Cho phép chọn layer/vật thể hoặc bảng màu + font chữ từ bất kỳ dự án cũ nào để ghép trực tiếp vào dự án đang chỉnh sửa.
