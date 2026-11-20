# EDITABLE TYPOGRAPHY ENGINE (`core/typography_engine.py`)

## 1. Quy trình Khôi phục Chữ Có Thể Sửa (`Editable Text Layer`)

1. **OCR Tiếng Việt (`run_vietnamese_ocr`):**
   - Dùng `tesseract.js@7` gói ngôn ngữ `vie+eng` (model cache tại `D:/AI_Design_Studio/models/tessdata`).
   - Sử dụng tùy chọn `{ blocks: true, text: true }` để trích xuất tọa độ từng dòng (`bbox`), đường cơ sở (`baseline`), và độ tin cậy (`confidence`).
2. **Lọc Nhiễu Nền & Logo Cách Điệu:**
   - Loại bỏ các chuỗi ký tự rác phát sinh trên vùng ảnh kết cấu (`alpha_cnt < 2`, tỷ lệ ký tự chữ/số `< 62%`, hoặc `conf < 0.45`).
   - Đánh dấu `needs_user_confirmation = True` nếu độ tin cậy `< 72%` hoặc vùng chữ nằm tại khu vực logo đầu trang để bảo toàn giao diện raster gốc (`Text_OrigRaster`) cho đến khi người dùng xác nhận sửa.
3. **Phân tích Thị giác Dòng chữ (`analyze_text_line_appearance`):**
   - Ước lượng màu chữ chủ đạo (`fill_color`), đậm/mảnh (`estimated_weight`), căn lề (`left`/`center`/`right`), kích thước font, và phát hiện sơ bộ sự hiện diện của viền/bóng (`has_stroke_or_3d`).
4. **Khớp Font Nội bộ Trung thực (`match_local_font`):**
   - Quét font thực tế tại `D:/AI_Design_Studio/assets/fonts` và `C:/Windows/Fonts`.
   - Không tự động suy đoán sai sự thật: gán `is_exact_font_match = False` và ghi rõ `match_note` kèm danh sách ứng viên font có dấu tiếng Việt.

---

## 2. Khả năng Render & Xuất PSD

Hàm `render_styled_text()` hỗ trợ đầy đủ:
- Chữ đa dòng, tiếng Việt có dấu Unicode đầy đủ (`Pillow ImageFont.truetype`).
- **Typography Layout:** Cỡ chữ, tracking (giãn cách ký tự), leading (giãn dòng), căn lề (`left`, `center`, `right`), xoay góc (`rotation`).
- **Hiệu ứng:** Stroke viền, Drop Shadow (màu, độ lệch dx/dy, blur), Outer Glow, Gradient 2 màu theo trục dọc, và 3D Extrusion (`extrude_3d_depth`).
- **Xuất PSD (`core/psd_bridge.js`):** Ghi block `TySh` text thực cho `ag-psd` kèm pixel buffer đồng bộ 100%.

---

## 3. Hạn chế Cần Lưu Ý

- Font chữ thiết kế mỹ thuật (custom display fonts hoặc chữ uốn cong trên logo) không thể xác định chính xác tuyệt đối chỉ từ raster; người dùng có thể bật checkbox **Xem Raster gốc** trong tab **Typography** hoặc đổi font trong danh sách font hệ thống (`/api/fonts`).
- Hiệu ứng chữ cong theo đường dẫn (Text on Path) chưa tự động vector hóa được sang Photoshop Path ở bản v1.2.
