# 08 — KNOWN ISSUES & LIMITATIONS (v1.1)

1. **Tự động hóa Adobe Photoshop 2024 COM bị Timeout (`TIMEOUT_WAITING_FOR_PHOTOSHOP_COM`):**
   - Thử nghiệm gọi `New-Object -ComObject Photoshop.Application` trên máy bị treo quá 35 giây khi chạy nền. Cần người dùng bấm mở thủ công 1 file `.psd` mẫu trong Photoshop 2024 để xác nhận thực tế trên giao diện Adobe.
2. **Inpainting nền trên CPU offline (MODE A):**
   - Chưa kết nối API Generative Inpainting trả phí nên vùng nền bị che khuất phức tạp được vẽ bù bằng thuật toán OpenCV Telea đa tỷ lệ; chỉ phù hợp nền trơn/gradient/họa tiết đơn giản.
3. **Font khi mở `.psd` trên máy chưa cài `FZ Poppins`:**
   - Hình ảnh chữ vẫn hiển thị đúng nhờ lớp pixel `imageData` đã render sẵn; chỉ khi bấm sửa trực tiếp bằng công cụ Text (`T`) trên máy khác chưa cài font, Photoshop mới hỏi thay thế font.
4. **Kiểm thử giao diện Browser:**
   - Chưa chạy script Playwright click từng nút trên UI v1.1; các tính năng đã được xác minh qua kiểm thử HTTP API trực tiếp và kiểm tra mã nguồn `ui/app.js`.
