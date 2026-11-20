# 07 — CHANGELOG

## v1.1.0 — 2026-11-18
- **Backup v1.0:** Sao lưu toàn bộ mã nguồn v1.0 vào `D:/AI_Design_Studio/backups/v1.0_snapshot/`.
- **Root-Cause Fixes:**
  - Sửa lỗi `cv2.imread()` thất bại với đường dẫn chứa ký tự Unicode/Emoji trên Windows bằng `np.fromfile + cv2.imdecode` trong `image_analyzer.py` và `reference_analyzer.py`.
  - Sửa logic giới hạn kích thước trong `image_analyzer.py`: ảnh lớn hơn `max_dim` (`3600×2400`) nay tự thu gọn về `<= 2048px`.
  - Sửa ký tự bullet `✓` bị thiếu glyph trong `FZ Poppins` thành `•` và tách bố cục 2 sản phẩm không chạm nhau trong `generate_engine.py`.
- **New Features & Modules:**
  - Thêm `core/project_manager.py`: Autosave (`autosave_draft.json`), Version History (`versions/vNNN.json`), Restore, Group CRUD, Missing Asset & Disk Space Integrity Check.
  - Thêm `core/reference_analyzer.py`: phân tích ảnh tham khảo bằng CV (K-means palette, 3×3 saliency, whitespace, mood, lighting/shadow) và lưu vào `knowledge_base.json`.
  - Nâng cấp `core/generate_engine.py`: hỗ trợ nhiều sản phẩm, ảnh tham khảo, feature bullets và `generate_layout_variants()` (3 phương án thiết kế khác biệt).
  - Nâng cấp `core/psd_bridge.js` & `core/qa_engine.py`: giải mã toàn bộ pixel từng layer và composite trong bước `verify` thay cho kiểm tra metadata nông.
  - Nâng cấp `ui/`: Undo/Redo, Group Manager, Live Text Preview, Version History & Restore, Reference Analyzer UI, Multi-Variant MODE B UI.

## v1.0.0 — 2026-11-18
- Khởi tạo dự án độc lập `D:/AI_Design_Studio/` từ prototype `TESTER/redesign_studio/`.
