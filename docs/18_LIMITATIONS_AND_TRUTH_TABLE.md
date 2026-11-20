# SYSTEM LIMITATIONS & HONEST STATUS MATRIX (V1.2)

Tài liệu này phân tách trung thực giữa những gì đã chạy thực tế (**VERIFIED**), những gì mới dừng ở mức đã cài đặt mã nguồn (**IMPLEMENTED / FUNCTIONAL**), và các giới hạn hiện tại cần cải thiện ở các phiên bản sau.

---

## 1. Ma trận Trạng thái Trung thực (Truth Table)

| Hạng mục / Tính năng | Trạng thái | Bằng chứng Thực tế | Giới hạn / Ghi chú Trung thực |
| :--- | :--- | :--- | :--- |
| **Semantic Design Analyzer (`RMBG-1.4` + Midground + Background Inpaint)** | **VERIFIED** | Chạy trên Grab poster (20.96s, 11 layers, 9 semantic objects), kiểm tra ảnh `grab_01_initial_composite.png` | Một số đối tượng chồng sát hoặc cùng tông xanh lá (xe hơi, gia đình, đường nhựa, tài xế) bị gộp vào một hero mask cho đến khi tách thêm bằng SlimSAM |
| **Interactive SlimSAM Segmentation (`+/- Points`, `Box`, `Carve`)** | **VERIFIED** | Tách `Motorbike` (IoU `0.811`), `Green_Car`, `Family_Group`; kiểm tra PNG alpha | Đòi hỏi người dùng đặt điểm `+`/`-` hợp lý; riêng vùng nền đường sau khi carve vật thể ra khỏi Hero sẽ để lỗ trong suốt nếu không chạy thêm *Reconstruct* trên layer đó |
| **Vietnamese OCR & Editable Typography** | **VERIFIED** | Đọc được `"NỖ LỰC TREN MỌI"`, sửa thành `"AN TOÀN TRÊN MỌI"` có viền/shadow + xuất PSD `TySh` | Chữ nghiêng/chạm viền hoặc logo cách điệu (`"Grab"` bị đọc nhầm thành `"Groo"`) cần lọc & giữ Raster gốc (`Text_OrigRaster`); `match_local_font` là xấp xỉ (`is_exact_font_match=False`) |
| **Non-Destructive Adjustments, Effects & Layer Actions** | **VERIFIED** | Hue, Bright, Contrast, Drop Shadow, Crop, Rotation, Scale, Duplicate, Lock/Unlock, Restore | Giao diện HTML5 Canvas preview sử dụng `ctx.filter` xấp xỉ trước khi bấm *Lưu & Render Server*; kết quả chính xác cuối do Pillow/OpenCV trên backend render |
| **Hybrid AI & Privacy Gates + Windows Credential Manager** | **VERIFIED** | Test chặn upload `LOCAL_ONLY`, chặn thiếu `user_confirmed`, `CredWriteW`/`CredReadW`/`CredDeleteW` | `google_gemini` có adapter HTTPS thật nhưng chưa test với API key trả phí (không tự gọi API trả phí); `openai_image` & `replicate` có endpoint `test_connection` thật, còn inpaint multipart upload trả fallback local an toàn |
| **UI Web App V1.2 (`ui/index.html`, `ui/app.js`, `ui/styles.css`)** | **FUNCTIONAL / PARTIALLY VERIFIED** | Khớp 100% API route & field JSON của `core/server.py`, đã kiểm thử REST API + JS không lỗi cú pháp | Thao tác click chuột trực tiếp trên trình duyệt cho từng tab/modal mới chưa chạy Playwright browser automation riêng; mới verify qua REST API & DOM bindings |
| **PSD Export (`ag-psd` 32-bit/RGBA, Groups, Text)** | **VERIFIED** | `14/14` pixel layers + `2` text layers + composite decoded hợp lệ | Không hỗ trợ native Photoshop Smart Objects hay Vector Curved Text on Path |
| **Adobe Photoshop 2024 GUI Interactive Test** | **NOT AUTOMATED (MANUAL)** | File `Photoshop.exe` tồn tại, nhưng CLI `-r jsx` & COM timeout | Cần người dùng mở file `.psd` trực tiếp trên Photoshop 2024 Desktop để xác nhận chỉnh sửa live trên UI Photoshop |

---

## 2. Điểm Cần Nâng cấp Cho V1.3 (Roadmap Đề xuất)

1. Bổ sung **LaMa ONNX / EdgeConnect Inpainting** vào `ai_vision_bridge.mjs` để vá nền phức tạp (đường nhựa, tòa nhà, họa tiết) mịn hơn OpenCV Telea hiện tại, đặc biệt là tự động inpaint vùng bị carve sau khi tách vật thể con.
2. Tách nhóm đối tượng chữ nghiêng lớn theo từng **cụm từ liên thông** trước khi chạy OCR để tránh trường hợp một bounding box OCR lấn sang đầu chữ khác (`"NỖ LỰC TRÊN MỌI"` chạm vùng `"ĐƯỜNG"`).
3. Mở rộng **OpenAI `images/edits` multipart/form-data** và **Replicate polling** cho người dùng có API key muốn dùng Hybrid Cloud Inpaint thực sự.
4. Viết bộ **Playwright Browser UI E2E** kiểm thử tự động thao tác kéo/chọn điểm/sửa slider trực tiếp trên giao diện trình duyệt.
