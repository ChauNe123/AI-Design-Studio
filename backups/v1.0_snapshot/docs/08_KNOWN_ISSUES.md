# 08 — KNOWN ISSUES & LIMITATIONS

1. **Giới hạn tái tạo chi tiết bị che khuất trên CPU offline:**
   - Khi chạy hoàn toàn offline trên CPU (không gọi Generative Inpainting API ngoài), MODE A dùng OpenCV Telea inpainting để vẽ bù phần nền bị che; thuật toán này làm mượt tốt nền trơn/gradient nhưng **không thể tự vẽ lại chi tiết phức tạp** (như bánh xe bị che, gương mặt hoặc chữ phức tạp) ở vùng chưa từng tồn tại trong ảnh.
2. **Text tách từ ảnh phẳng trong MODE A:**
   - Các vùng chữ tách từ ảnh phẳng được xuất dưới dạng layer ảnh sắc nét (giữ đúng font & hiệu ứng gốc). Để biến thành Text Layer gõ lại chữ trên file cũ, người dùng thêm Text Layer mới trong Layer Editor hoặc bật Type Layer mẫu; chưa tích hợp OCR tự động đọc ngược font lạ trên CPU.
3. **Font khi mở `.psd` trên máy khác:**
   - Nếu mở file `.psd` tạo từ MODE B trên máy chưa cài `FZ Poppins`, Photoshop có thể hỏi thay thế font khi bấm sửa chữ (tuy nhiên hình hiển thị vẫn đúng 100% nhờ lớp `imageData` đã render sẵn). Khuyến nghị cài bộ font trong `D:\AI_Design_Studio\assets\fonts\` vào Windows (`Install for all users`).
4. **Xác minh GUI Photoshop 2024:**
   - Đã xác minh cấu trúc PSD bằng `ag-psd` `readPsd`; bước mở tương tác trên giao diện `Adobe Photoshop 2024` chưa tự động thực hiện trong test headless.
