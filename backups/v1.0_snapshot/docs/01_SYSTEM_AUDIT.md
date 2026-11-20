# 01 — SYSTEM AUDIT REPORT (AI DESIGN STUDIO)

**Ngày kiểm toán:** 2026-11-18  
**Thư mục gốc mới (độc lập):** `D:\AI_Design_Studio\`  
**Nguồn kế thừa đã sao lưu:** `D:\AI\TESTER\redesign_studio\` → `D:\AI_Design_Studio\backups\legacy_redesign_studio\`

---

## 1. Kiểm tra Môi trường & Phần cứng Thực tế

| Hạng mục | Kết quả đo thực tế | Ghi chú vận hành |
| :--- | :--- | :--- |
| **Hệ điều hành** | `Windows-11-10.0.26200-SP0` | 64-bit |
| **CPU** | 16 cores | Phù hợp xử lý CPU OpenCV/Pillow theo batch |
| **RAM** | 15.9 GB tổng (~4.7 GB khả dụng lúc kiểm tra) | Giới hạn cạnh ảnh tối đa `2048px` để tránh tràn RAM |
| **Ổ đĩa `D:\`** | 931.5 GB tổng (419.8 GB trống) | Đủ không gian lưu project & PSD |
| **GPU** | AMD Radeon RX 5600 XT (~4 GB VRAM, không có NVIDIA CUDA) | Không dùng mô hình PyTorch/CUDA nặng; chạy CPU + API tùy chọn |
| **Python** | `3.15.2` (`Pillow 13.0.0`, `cv2 5.0.0`, `numpy 2.5.4`, `tkinter`) | Thiếu `scipy`, `psd_tools`, `rembg`, `onnxruntime`, `fastapi` |
| **Node.js** | `v24.18.0` + `npm 11.16.0` (`ag-psd`, `pngjs`) | Dùng làm lõi xuất & kiểm tra đọc lại `.psd` |
| **Adobe Photoshop** | `D:\photoshop\Adobe Photoshop 2024\Photoshop.exe` | Có sẵn trên máy |
| **PhoToSop (KBDobe)** | `D:\KBDobe_Hub_Windows_x64\KBDobe_Hub\Apps\PhoToSop\PhoToSop.exe` | App đóng gói sẵn |

---

## 2. Bảng Đánh giá Hệ thống Trước & Sau Nâng cấp

| Thành phần | Trạng thái Ban đầu (Legacy `TESTER\redesign_studio`) | Vấn đề Gốc Rễ | Trạng thái Hiện tại (`D:\AI_Design_Studio`) |
| :--- | :--- | :--- | :--- |
| **Giao diện (UI)** | Lỗi / Thiếu | Chỉ có `index.html` đơn giản, thiếu MODE B, Asset Library, Knowledge, History, Settings; nút `Tải .PSD` chỉ tải file tĩnh cũ (không phản ánh chỉnh sửa). | **Đạt** — Đủ 9 khu vực trong `ui/`, mọi nút đều kết nối backend thật. |
| **Backend** | Lỗi / Thiếu | `server.py` gọi hàm `decompose_poster` fix cứng tọa độ OneWay; không có API Generate, Asset, Knowledge, Save edits. | **Đạt** — `core/server.py` (`ThreadingHTTPServer` port `8788`) xử lý đầy đủ endpoint. |
| **AI / CV Engine** | Lỗi cục bộ | Script tách ảnh bị fix cứng tọa độ theo từng ảnh (`decompose_deep.py`, `process_safedrive.py`, `process_canva.py`). Thiếu MODE B. | **Đạt** — `image_analyzer.py` (MODE A tổng quát) + `generate_engine.py` (MODE B dùng font Việt hóa `FZ Poppins`). |
| **Layer Engine** | Thiếu | Mỗi script dùng 1 cấu trúc `manifest*.json` khác nhau, thiếu `z_index`, `blend_mode`, `ai_reconstructed`. | **Đạt** — `core/design_document.py` thống nhất 1 schema duy nhất. |
| **PSD Export** | Trùng lặp / Lỗi | 3 file `build_*.js` trùng code; Text Layer thiếu `imageData` khiến 1 số trình xem không hiện chữ. | **Đạt** — `core/psd_bridge.js` hợp nhất xuất group, blend mode, cả `imageData` lẫn `TySh` text. |
| **QA Engine** | Thiếu | Kiểm duyệt rời rạc, chưa tự động chạy QA 1/2/3 và chưa ghi nhận `qa_report.json`. | **Đạt** — `core/qa_engine.py` chạy đủ QA 1, QA 2, QA 3 (round-trip `readPsd`). |
