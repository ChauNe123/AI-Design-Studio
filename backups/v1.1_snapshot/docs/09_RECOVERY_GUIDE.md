# 09 — RECOVERY GUIDE

## 1. Khởi chạy lại ứng dụng Windows Studio
- Nhấp đúp **`D:\AI_Design_Studio\launch_studio.bat`** hoặc chạy:
  ```powershell
  python D:\AI_Design_Studio\run_studio.py
  ```
- Truy cập trực tiếp qua trình duyệt nếu cửa sổ app bị đóng: `http://127.0.0.1:8788`

## 2. Chạy lại toàn bộ kiểm thử hồi quy
```powershell
python D:\AI_Design_Studio\tests\run_regression_tests.py
```

## 3. Khôi phục mã nguồn bản cũ (nếu cần)
- Toàn bộ script gốc trước khi nâng cấp được giữ nguyên vẹn tại:
  `D:\AI_Design_Studio\backups\legacy_redesign_studio\`
- Thư mục gốc `D:\AI\TESTER\redesign_studio\` cũng không bị xóa hay ghi đè.

## 4. Khắc phục sự cố thường gặp
- **Cổng `8788` bị chiếm:** Kiểm tra tiến trình Python cũ đang chạy (`Get-Process python`) hoặc đổi `PORT` trong `run_studio.py`.
- **Lỗi `node` / `ag-psd` không tìm thấy:** Kiểm tra `node -v` và đảm bảo thư mục `D:\AI_Design_Studio\node_modules\ag-psd` tồn tại (nếu mất, chạy `npm install` trong `D:\AI_Design_Studio`).
- **Lỗi thiếu dấu tiếng Việt khi render chữ:** Đảm bảo thư mục `D:\AI_Design_Studio\assets\fonts\` có các file `FZ Poppins-*.ttf`.
