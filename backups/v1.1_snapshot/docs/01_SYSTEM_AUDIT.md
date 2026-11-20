# 01 — SYSTEM AUDIT REPORT (v1.0 AUDIT → v1.1 VERIFIED)

**Ngày kiểm toán sâu:** 2026-11-18  
**Phạm vi kiểm tra:** Toàn bộ mã nguồn trong `D:/AI_Design_Studio/` (`core/`, `ui/`, `knowledge/`, `tests/`).

---

## 1. Thang Phân loại Trạng thái Nghiêm ngặt
- **IMPLEMENTED:** Đã có mã nguồn.
- **FUNCTIONAL:** Đã chạy thực thi không lỗi.
- **VERIFIED:** Đã có bằng chứng kiểm thử định lượng & kiểm tra trực quan (composite/binary readback).
- **PRODUCTION READY:** Đã vượt qua kiểm thử biên/stress và kiểm tra tương thích môi trường mục tiêu.

---

## 2. Kết quả Kiểm toán Lại Bản v1.0 (Những Chỗ Thiếu / Chưa Đạt Đã Phát Hiện)

| Module v1.0 | Tuyên bố v1.0 | Kiểm toán thực tế trên code v1.0 | Hành động sửa ở v1.1 |
| :--- | :--- | :--- | :--- |
| `image_analyzer.py` & `reference_analyzer.py` | Đọc mọi ảnh trên Windows | `cv2.imread()` lỗi với tên file Unicode/Emoji (`✅ SAFE DRIVE.png`), và ảnh `3600×2400` không được tự thu về `<= max_dim`. | Thay bằng `np.fromfile + cv2.imdecode` và bổ sung logic cap `max_dim`. |
| `generate_engine.py` | Sinh thiết kế mới + tiếng Việt | Chỉ tạo 1 layout/lần, chưa phân tích ảnh tham khảo, chưa tách 2 sản phẩm cân đối, và ký tự `✓` bị thiếu glyph trong `FZ Poppins`. | Thêm `propose_and_generate_variants` (3 phương án), đọc reference, tách 2 sản phẩm không chạm nhau, đổi bullet sang `•`. |
| `psd_bridge.js` (`verify`) | Xác minh file PSD | v1.0 dùng `{ skipLayerImageData: true }` nên chỉ đọc metadata, chưa giải mã pixel thật. | Thêm JS canvas shim + `readPsd(buf, { useImageData: true })` kiểm tra đủ buffer RGBA của từng layer và composite. |
| `project_manager.py` & UI Editor | Quản lý Layer, Group, Undo/Redo, Khôi phục | v1.0 chưa có Group CRUD, Undo/Redo, Autosave, Version Restore, Missing Asset Checker, Live Text Preview. | Xây mới `core/project_manager.py` và kết nối đầy đủ vào `server.py` + `ui/app.js`. |
| **Photoshop 2024 COM** | Đã cài `Photoshop.exe` trên máy | Test tự động hóa `Photoshop.Application` bị **`TIMEOUT_WAITING_FOR_PHOTOSHOP_COM`** (treo quá 35s khi gọi headless). | Ghi nhận trung thực là **CHƯA VERIFIED qua COM/GUI**; chỉ đánh dấu `VERIFIED` ở tầng nhị phân `ag-psd`. |

---

## 3. Ma trận Trạng thái Sau Nâng cấp v1.1

| Thành phần | Trạng thái Hiện tại | Bằng chứng Thực tế |
| :--- | :--- | :--- |
| `core/design_document.py` | **VERIFIED** | Schema thống nhất, `validate_document` chạy trong mọi test. |
| `core/image_analyzer.py` (MODE A) | **VERIFIED** | `9/9 PASS` trên 7 loại ảnh + `highres_capped_ok: true` (`3600×2400 -> 2048×1365`) + Unicode path OK. |
| `core/generate_engine.py` (MODE B) | **VERIFIED** | `T2` tạo 3 phương án khác biệt (`diff >= 16.72`), đa sản phẩm, logo, tiếng Việt, reference-guided. |
| `core/reference_analyzer.py` & `knowledge_base.py` | **VERIFIED** | `T3` phân tích thành công `Canva_SafeDrive` và `OneWay_Taxi` thành cấu trúc JSON có thể lưu & đọc lại. |
| `core/project_manager.py` | **VERIFIED** | `T4` xác minh Autosave recovery, Version restore `v001`, và phát hiện 100% file thiếu (`missing_assets`). |
| `core/psd_bridge.js` & `core/qa_engine.py` | **VERIFIED (Binary) / PARTIAL (Photoshop GUI)** | `T1` (`8/8` pixel layers + text chỉnh sửa + tọa độ + hidden) & `T5` (`32 layers / 6 groups`, từ chối PSD hỏng). Photoshop COM bị timeout nên **chưa** gán nhãn Production Ready cho bước GUI Photoshop. |
| `core/server.py` & `ui/` | **VERIFIED (API) / FUNCTIONAL (UI)** | Các endpoint API đã test end-to-end trong `T1`, `T5` và `API::system_redesign_save_export`. Giao diện HTML/JS đã rà soát kết nối endpoint nhưng chưa chạy browser UI click test tự động (Playwright) trên v1.1. |
