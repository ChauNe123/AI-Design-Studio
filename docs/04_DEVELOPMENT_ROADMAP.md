# 04 — DEVELOPMENT ROADMAP

## Đã Hoàn Thành (Phiên bản 1.0 — Standalone)
- [x] Tách dự án ra thư mục độc lập `D:\AI_Design_Studio\` và sao lưu bản cũ.
- [x] Xây dựng schema trung tâm `DesignDocument` (`core/design_document.py`).
- [x] Xây dựng MODE A tổng quát (`core/image_analyzer.py`) không phụ thuộc tọa độ fix cứng.
- [x] Xây dựng MODE B (`core/generate_engine.py`) giữ nguyên pixel sản phẩm thương mại gốc.
- [x] Hợp nhất PSD Export + Round-trip Verify (`core/psd_bridge.js`).
- [x] Xây dựng QA 1 / QA 2 / QA 3 (`core/qa_engine.py`).
- [x] Hoàn thiện UI Desktop 9 khu vực (`ui/` + `run_studio.py` + `launch_studio.bat`).
- [x] Kiểm thử hồi quy 7 bộ dữ liệu + MODE B + Live HTTP API (`9/9 PASS`).

## Lộ Trình Mở Rộng Tiếp Theo (Không cài tự động nếu chưa được yêu cầu)
- [ ] Tích hợp OCR chuyên sâu (PaddleOCR / Tesseract) để tự động chuyển vùng text tách từ MODE A thành `text_data` gõ sửa được luôn.
- [ ] Bổ sung tùy chọn kết nối API Generative Inpainting bên ngoài (khi người dùng cung cấp API key) để tái tạo cấu trúc phức tạp sau vật thể chồng lấp trong MODE A.
- [ ] Đóng gói thành file `.exe` độc lập (PyInstaller) nếu cần chạy trên máy Windows chưa cài Python.
