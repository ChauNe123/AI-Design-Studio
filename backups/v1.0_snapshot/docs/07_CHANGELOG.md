# 07 — CHANGELOG

## v1.0.0 — 2026-11-18
- **New Workspace:** Tạo dự án độc lập tại `D:\AI_Design_Studio\`, sao lưu toàn bộ script cũ từ `D:\AI\TESTER\redesign_studio\` vào `backups\legacy_redesign_studio\`.
- **Unified Schema:** Thêm `core/design_document.py` làm nguồn dữ liệu duy nhất.
- **MODE A Rewrite (Generic):** Thay thế các script fix cứng tọa độ bằng `core/image_analyzer.py` (tự động ước lượng nền LAB + flood-fill bảo vệ vùng ảnh chụp + phân loại component + nâng nét 2×).
- **MODE B New:** Thêm `core/generate_engine.py` kết hợp `core/knowledge_base.py` và bộ font tiếng Việt `FZ Poppins`.
- **PSD Export Unified:** Hợp nhất 3 file `build_*.js` cũ thành `core/psd_bridge.js` kèm chế độ `verify`.
- **QA Engine:** Thêm `core/qa_engine.py` thực hiện QA 1, QA 2, QA 3 và lưu `qa_report.json`.
- **UI & Server:** Hoàn thiện `core/server.py` + `ui/` (9 màn hình, kết nối thật 100%) và bộ launcher `run_studio.py` / `launch_studio.bat`.
- **Bugfixes after Visual Regression Check:**
  - Sửa lỗi font `Poppins` bản gốc thiếu dấu tiếng Việt (`Ơ`, `Ả`, `Ớ`) bằng cách chuyển sang `FZ Poppins` tại `assets/fonts/`.
  - Sửa lỗi `floodFill` lọt vào vùng kính lái sáng ở `06_canva_design` bằng cách ràng buộc khoảng cách màu với nền chủ đạo (`dist_dom < 38`).
