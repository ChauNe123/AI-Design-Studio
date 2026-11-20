# 12 — PROJECT MANAGEMENT SPECIFICATION (v1.1)

**Module triển khai:** `D:/AI_Design_Studio/core/project_manager.py`  
**Endpoint kết nối:** `/api/project/<id>`, `/api/project/<id>/autosave`, `/api/project/<id>/save`, `/api/project/<id>/restore`, `/api/project/<id>/group`

## Các Tính năng Đã Triển khai & Kiểm chứng (`T1`, `T4`)
1. **Autosave & Crash Recovery:**
   - Tự động lưu bản nháp `autosave_draft.json` kèm tệp khóa `.session_active` sau mỗi thao tác chỉnh sửa trên UI (1.5s debounce).
   - Khi mở lại dự án có `.session_active` hoặc `autosave_draft.json` mới hơn `design_document.json`, giao diện hỏi người dùng khôi phục bản nháp chưa lưu chính thức.
2. **Version History & Restore:**
   - Tự động tạo snapshot `versions/v001.json`, `v002.json`... (giữ tối đa 25 phiên bản) tại `versions/index.json` mỗi khi tạo dự án, chỉnh Group hoặc Lưu phiên bản.
   - Cho phép khôi phục về bất kỳ phiên bản cũ nào (và tự sao lưu trạng thái hiện tại trước khi restore).
3. **Group Management:**
   - Hỗ trợ `create`, `rename`, `delete` (tự chuyển layer về `Main` không làm mất layer) và `assign_layer`.
4. **Integrity & Disk Space Guard:**
   - `check_project_integrity()` xác minh `design_document.json`, kiểm tra tồn tại & `Image.verify()` cho toàn bộ `source_file` và `mask_file`, đồng thời kiểm tra dung lượng trống ổ đĩa `D:/`.
