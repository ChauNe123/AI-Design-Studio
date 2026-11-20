# ADVANCED OBJECT SEGMENTATION PIPELINE (`core/segmentation_engine.py`)

## 1. Kiến trúc Đa phương thức Segmentation

| Engine / Thành phần | Vị trí | Chức năng | Đầu ra |
| :--- | :--- | :--- | :--- |
| **`briaai/RMBG-1.4` (q8 ONNX)** | `core/ai_vision_bridge.mjs` (`rmbg`) | Tách chủ thể chính không cần prompt điểm | Alpha mask 8-bit full resolution |
| **`Xenova/slimsam-77-uniform` (q8 ONNX)** | `core/ai_vision_bridge.mjs` (`slimsam`) | Tách từng đối tượng hoặc bộ phận theo điểm `+`/`-` & `mask_level` | Mask + `iou_score` |
| **OpenCV GrabCut Fallback** | `core/segmentation_engine.py` | Dự phòng khi tách theo bounding box thuần không dùng SAM | Mask nhị phân |
| **Mask Refinement & Quality Check** | `refine_mask()`, `analyze_mask_quality()` | Đóng lỗ, xóa nhiễu nhỏ, expand/contract, feather, phát hiện green/white halo | Mask lưu riêng trong `masks/*.png` |

---

## 2. Cơ chế Tách Vật thể Tương tác & Không chồng lấn (`POST /api/project/<id>/segment`)

1. Người dùng chọn công cụ **➕ Điểm +**, **➖ Điểm -**, hoặc **🔲 Kéo Box** trên `#editorCanvas`.
2. Backend chuẩn hóa Box `[x, y, w, h]` thành `[x1, y1, x2, y2]` trước khi truyền vào `segment_interactive()`.
3. SlimSAM hỗ trợ chọn **Mask Level**:
   - `Level 2`: Ưu tiên toàn bộ đối tượng (VD: cả chiếc xe máy + người ngồi).
   - `Level 1`: Cụm trung bình.
   - `Level 0`: Chi tiết nhỏ (VD: nón bảo hiểm, bánh xe, giày).
4. Mask được lưu thành file độc lập trong `projects/<id>/masks/seg_<hex>.png`.
5. **Tách khỏi Layer cha (`carve_from_layer_id`):** Khi tách một đối tượng nằm chồng trên layer tiền cảnh (ví dụ tách Xe máy ra khỏi Nhân vật Grab), backend tự động khoét alpha vùng đã tách trên layer cha và ghi nhật ký `user_edited` để tránh hiện tượng nhân đôi bóng mờ khi di chuyển vật thể mới.

---

## 3. Hạn chế Thực tế

- Trên CPU không có GPU NVIDIA CUDA, mỗi lần chạy SlimSAM encoder cho ảnh `1024×1024` mất khoảng `3–5 giây`; khuyến nghị chọn nhiều điểm `+`/`-` cùng lúc trước khi nhấn *Tách đối tượng mới*.
- Với vật thể màu tương đồng sát nền (ví dụ xe xanh trên nền đường tối có bóng đổ), cần bổ sung điểm `-` ở vùng trời/nền xung quanh để đường viền sắc nét.
