# V1.2 TESTING & QA REPORT (`tests/run_v1_2_tests.py` + `v1.1` Regression)

## 1. Kết quả Chạy Kiểm thử Sau Lần Chỉnh sửa Cuối

| Bộ Test | Lệnh Chạy | Kết quả | Chi tiết Quan sát Thực tế |
| :--- | :--- | :--- | :--- |
| **v1.1 Regression** | `python tests/run_regression_tests.py` | **PASS (9/9)** | Toàn bộ 9 test case MODE A (01–07), MODE B (`portrait_4x5`), API save/export đều pass không hồi quy |
| **v1.1 Acceptance** | `python tests/run_v1_1_acceptance_tests.py` | **PASS (5/5)** | `T1`–`T5` (Groups, Multi-Export, 3 Variants, Reference Analyzer, Autosave/Restore/Integrity, 32-layer stress, malformed input) đều pass |
| **v1.2 Unit & Stress** | `python tests/run_v1_2_tests.py` | **PASS (4/4)** | Credential Manager write/read/delete OK; Hybrid AI privacy gates chặn upload khi `LOCAL_ONLY` hoặc `user_confirmed=False`; Migration v1.1→v1.2.0 OK; Stress **30 layers @ 2048×2048** chạy mất **5.5s**, PSD **1.33 MB**, QA1/QA2/QA3 PASS |
| **v1.2 Grab Poster E2E** | `python tests/run_v1_2_tests.py` | **PASS** | Live server API `/api/redesign`, `/segment`, `/reconstruct`, `/save`, `/layer_action`, `/api/project/<id>`, và `psd_bridge.js verify` |

---

## 2. Chi tiết Kiểm thử Poster Thực tế (`Grab Poster 1024×1024`)

**Đầu vào:** `media_1794977150476_12e90368.jpg`

1. **Semantic Redesign (`POST /api/redesign`):**
   - Thời gian chạy CPU: **20.96s**
   - Kết quả ban đầu: **11 layers**, **9 semantic_objects**, `qa_passed = true`
   - Hệ thống tự phát hiện và cảnh báo: `"Green edge fringe (39.66%)"` và `"Hero region spans >20% of canvas and may contain touching foreground sub-objects"`.
2. **Interactive SlimSAM Segmentation (`POST /api/project/<id>/segment`):**
   - Tách `Motorbike_And_Rider_SlimSAM` (`slimsam-77-uniform`, `iou_score = 0.811`, `carve_from_layer_id` khỏi Hero)
   - Tách `Green_Car_SlimSAM` (`slimsam-77-uniform`, dùng 3 điểm `+` và 1 điểm `-` vùng trời → tách gọn thân xe xanh)
   - Tách `Family_Group_SlimSAM` (`slimsam-77-uniform`, 3 điểm `+`)
3. **Thao tác Sửa Chữa & Quản lý Layer Thực tế (`POST /save`, `/reconstruct`, `/layer_action`):**
   - Đổi chữ OCR `"NỖ LỰC TREN MỌI"` → **`"AN TOÀN TRÊN MỌI"`** (`font_size=68`, viền `#064E3B`, shadow).
   - Chỉnh màu không phá hủy trên `Foreground_Hero`: `hue=-18`, `bright=112`, `contrast=108`, bật `drop_shadow`.
   - Di chuyển `Motorbike_And_Rider_SlimSAM` thêm `(+45, -18)` tới tọa độ `[336, 712]`.
   - Ẩn tòa nhà Bitexco (`05_Architecture_04`, `visible=False`).
   - Kiểm thử `duplicate`, `lock`, `unlock` thành công; tái tạo `01_Background_Reconstructed` (`pixel_origin = "algorithmic_inpaint"`).
   - Lưu **10 versions**, đóng & gọi `GET /api/project/<pid>` mở lại → kiểm chứng mọi thay đổi bền vững, `integrity_ok = true`.
4. **Xuất & Kiểm định PSD (`core/psd_bridge.js verify`):**
   - Tệp PSD cuối: **4,588,002 bytes** (~4.38 MB), **6 groups**, **14 layers**, **2 text layers (`TySh`)**, `decoded_pixel_layers = 14/14`, `composite_decoded = true`.

---

## 3. Kiểm tra Adobe Photoshop 2024

- Đã xác minh sự tồn tại của `D:/photoshop/Adobe Photoshop 2024/Photoshop.exe`.
- Khi chạy tự động headless (`COM` >35s và `-r ps_check.jsx` 20s) trong môi trường agent không tương tác desktop, Photoshop không trả log JSX tự động (tệp `ps_check_out.txt` rỗng).
- Vì vậy: **PSD Binary Structure (`8BPS`, pixel buffers, groups, text records)** đạt **VERIFIED** qua `ag-psd`, còn việc mở giao diện **Photoshop 2024 GUI** giữ ở trạng thái **cần mở kiểm tra thủ công trên desktop** (nút *Mở trong Photoshop 2024* trong UI).
