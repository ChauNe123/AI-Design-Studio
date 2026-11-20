# NON-DESTRUCTIVE EDITING WORKFLOW (`core/effects_engine.py` & `ui/app.js`)

## 1. Nguyên tắc Không Phá Hủy Dữ Liệu Gốc

Mỗi layer ảnh trong `DesignDocument v1.2` luôn tách biệt giữa:
- **`original_source_file`**: File PNG trích xuất ban đầu — tuyệt đối không bị ghi đè bởi thao tác đổi màu, blur, crop, glow hay drop shadow.
- **`adjustments` & `effects` & `crop` & `rotation`**: Lưu dưới dạng tham số JSON có cấu trúc trong `design_document.json`.
- **`export_cache/<layer_id>.png` & `metadata.export_offset`**: Do `qa_engine.prepare_export_cache()` render lại từ `source_file` mỗi lần lưu Version và xuất PSD, giữ nguyên tọa độ gốc nhờ bù trừ `[pad_x, pad_y]`.

---

## 2. Danh sách Tham số & Thao tác Hỗ trợ

| Nhóm | Tham số / Thao tác | Ghi chú |
| :--- | :--- | :--- |
| **Biến đổi & Quản lý** | `x`, `y`, `z_index`, `scale`, `rotation`, `crop [x,y,w,h]`, `visible`, `locked`, `opacity`, `blend_mode` | Layer bị khóa (`locked=true`) được backend và UI bảo vệ |
| **Action API (`/layer_action`)** | `duplicate`, `rename`, `lock`, `unlock`, `replace_asset`, `restore_original` | `restore_original` khôi phục `original_source_file` & reset hiệu ứng |
| **Màu sắc & Ánh sáng** | `hue`, `sat`, `bright`, `contrast`, `exposure` (EV), `temperature` (Warm/Cool), `shadow`, `highlight` | Tính toán trên không gian RGB/HSV float32 bằng NumPy + OpenCV |
| **Hiệu ứng** | `feather`, `blur`, `glow` (`color`, `radius`, `opacity`), `drop_shadow` (`dx`, `dy`, `blur`, `color`, `opacity`), `color_overlay`, `gradient_overlay` | Padding được ghi vào `export_offset` để giữ khớp vị trí trong Composite & PSD |
| **Lịch sử & An toàn** | Undo/Redo (`Ctrl+Z`/`Ctrl+Y`), Autosave (`1.5s`), Versioning + Restore | Giữ nguyên giữa các phiên đóng/mở lại dự án |

---

## 3. Phân biệt Nguồn gốc Pixel Tái tạo (`core/reconstruction_engine.py`)

Mỗi lần tái tạo vùng che khuất hoặc xóa vật thể (`POST /api/project/<id>/reconstruct`), hệ thống ghi rõ `reconstruction_history`:
- **`original`**: Pixel trích xuất trực tiếp từ ảnh gốc.
- **`algorithmic_inpaint`**: Pixel nội suy bằng thuật toán OpenCV Telea / Navier-Stokes offline.
- **`ai_generated`**: Pixel được sinh bởi Cloud Hybrid AI (chỉ khi người dùng bật `HYBRID` và xác nhận từng lần).
- **`user_edited`**: Pixel do người dùng khoét alpha hoặc thay ảnh thủ công (`carve_from_layer_id`, `replace_asset`).
