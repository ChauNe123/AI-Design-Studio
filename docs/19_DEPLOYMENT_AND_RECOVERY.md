# DEPLOYMENT, OPERATIONS & RECOVERY GUIDE (V1.2)

## 1. Khởi chạy Hệ thống

1. Mở terminal tại `D:/AI_Design_Studio/`:
   ```powershell
   python app.py
   ```
   *(Hoặc chạy thẳng `D:/AI_Design_Studio/start_studio.bat` — mở trình duyệt tới `http://127.0.0.1:8788`).*
2. Kiểm tra nhanh tình trạng API & Version:
   ```powershell
   curl http://127.0.0.1:8788/api/system
   ```

---

## 2. Cấu trúc Dữ liệu & Model Cục bộ

- **Mã nguồn lõi:** `D:/AI_Design_Studio/core/`
- **Giao diện Web App:** `D:/AI_Design_Studio/ui/`
- **Model AI Offline đã cache:**
  - `D:/AI_Design_Studio/models/hf_cache/` (`briaai/RMBG-1.4`, `Xenova/slimsam-77-uniform`)
  - `D:/AI_Design_Studio/models/tessdata/` (`vie.traineddata`, `eng.traineddata`)
- **Dự án & Backup:** `D:/AI_Design_Studio/projects/<project_id>/` (`design_document.json`, `versions/`, `masks/`, `layers/`, `export_cache/`, `*.psd`)
- **Bản sao lưu v1.1 an toàn:** `D:/AI_Design_Studio/backups/v1.1_snapshot/`

---

## 3. Quy trình Khôi phục & Kiểm thử Sau Cập nhật

1. **Khôi phục phiên bản dự án:** Trong tab **Export PSD & QA**, chọn một phiên bản trong *Version History* và bấm **Khôi phục** (`/api/project/<id>/restore`), hoặc đồng ý khôi phục bản *Autosave* khi mở lại dự án.
2. **Khôi phục toàn bộ layer về ảnh gốc:** Chọn layer trong Layer Editor → bấm **↺ Khôi phục gốc** (`/api/project/<id>/layer_action` `restore_original`).
3. **Chạy toàn bộ Test hồi quy & Chấp nhận v1.1 + v1.2:**
   ```powershell
   cd D:\AI_Design_Studio
   python tests/run_regression_tests.py
   python tests/run_v1_1_acceptance_tests.py
   python tests/run_v1_2_tests.py
   ```
4. **Mở PSD bằng Adobe Photoshop 2024:** Bấm nút **🎨 Mở trong Photoshop 2024** ở màn hình Export hoặc mở trực tiếp file `.psd` trong `D:/AI_Design_Studio/projects/<project_id>/`.
