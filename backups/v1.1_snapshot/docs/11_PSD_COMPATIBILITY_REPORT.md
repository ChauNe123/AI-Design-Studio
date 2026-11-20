# 11 — PSD COMPATIBILITY REPORT (v1.1)

## 1. Phương pháp Kiểm thử PSD Đã Thực Hiện

| Cấp độ Kiểm tra | Công cụ / Cơ chế | Kết quả | Mức độ Xác minh |
| :--- | :--- | :---: | :--- |
| **Binary Header & Structure** | `core/psd_bridge.js verify` kiểm tra chữ ký `8BPS`, `width`, `height`, `colorMode=3` (RGB), `bitsPerChannel=8`. | **PASS** | **VERIFIED** |
| **Full Pixel Buffer & Alpha Decode** | `ag-psd` `readPsd(buf, { useImageData: true })` với JS canvas shim giải mã toàn bộ mảng byte RGBA (`width * height * 4`) của từng layer và composite. | **PASS** (9/9 regression + `T1` 8/8 + `T5` 32/32) | **VERIFIED** |
| **Group Hierarchy & Blend Modes** | Kiểm tra `group_count`, tên Group, thuộc tính `hidden`, `opacity`, `blendMode` đọc ngược từ PSD. | **PASS** (bao gồm 6 groups / 32 layers) | **VERIFIED** |
| **Editable Text Layer (`TySh`)** | Kiểm tra `l.text.text` đọc lại từ binary PSD sau khi chỉnh sửa nội dung tiếng Việt (`"NỘI DUNG ĐÃ CHỈNH SỬA"`). | **PASS** | **VERIFIED** |
| **Corrupt PSD Rejection** | Đưa file PSD hỏng (`8BPS_CORRUPTED_BYTES_0000`) vào `verify`. | **PASS** (từ chối với exit code khác 0) | **VERIFIED** |
| **Adobe Photoshop 2024 COM / GUI** | Gọi `New-Object -ComObject Photoshop.Application` mở `ps_com_test.psd`. | **TIMEOUT (`> 35s`)** | **NOT VERIFIED** |

## 2. Kết luận Trung thực
- Về mặt **cấu trúc nhị phân `.psd`, giải mã từng layer RGBA, nhóm Group và dữ liệu chữ `TySh`**, hệ thống đã đạt mức **VERIFIED**.
- Về mặt **tương thích giao diện thực tế trên `Adobe Photoshop 2024`**, do tiến trình COM của Photoshop 2024 trên máy bị timeout khi gọi tự động hóa headless, mục này **chưa được xác nhận tự động** và cần người dùng mở kiểm tra trực tiếp bằng nút **"Mở trong Photoshop 2024"**.
