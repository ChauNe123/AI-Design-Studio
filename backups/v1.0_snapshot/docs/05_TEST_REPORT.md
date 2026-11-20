# 05 — TEST REPORT

**Bộ kiểm thử:** `D:\AI_Design_Studio\tests\run_regression_tests.py`  
**Kết quả ghi nhận thực tế từ:** `D:\AI_Design_Studio\tests\output\regression_summary.json`

## 1. Bảng Kết quả Kiểm thử Hồi quy (9/9 PASS)

| Test Case | Loại | Kích thước | Số Layer | PSD Size (bytes) | Layer đọc lại từ PSD | MAE vs gốc | Trạng thái |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `01_simple_bg` | Ảnh nền đơn giản | `600×600` | 2 | 136,870 | 2 | 0.13 | **PASS** |
| `02_multi_text` | Thiết kế nhiều chữ | `700×500` | 4 | 152,922 | 4 | 0.73 | **PASS** |
| `03_multi_product` | Nhiều sản phẩm | `800×500` | 4 | 354,084 | 4 | 0.32 | **PASS** |
| `04_white_bg_product` | Sản phẩm nền trắng (có chi tiết trắng bên trong) | `600×600` | 2 | 86,530 | 2 | 0.31 | **PASS** |
| `05_transparent_png` | PNG nền trong suốt | `1068×459` | 2 | 347,766 | 2 | 0.33 | **PASS** |
| `06_canva_design` | Thiết kế Canva thực tế (2× Full HD) | `2048×2048` | 9 | 8,361,202 | 9 | 0.63 | **PASS** |
| `07_overlapping` | Thành phần chồng lấp (`ONEWAY`) | `1472×1472` | 8 | 6,333,072 | 8 | 2.83 | **PASS** |
| `MODE_B::generate_portrait_4x5` | Thiết kế mới (4:5 + Logo + Product + Text Việt) | `1080×1350` | 9 (3 Text) | 798,866 | 9 | N/A | **PASS** |
| `API::system_redesign_save_export` | HTTP API + Sửa Layer + Export PSD | `600×600` | 2 | 136,870 | 2 | — | **PASS** |

## 2. Kiểm tra Trực quan Bằng Mắt (`read_file`)
- `06_canva_design/qa_composite.png`: Ảnh ghép khớp thiết kế gốc, không thủng kính lái, không lẹm tay áo tài xế.
- `07_overlapping/qa_composite.png`: Tách lớp chính và ghép lại khớp bố cục gốc.
- `08_mode_b_generate/qa_composite.png`: Tiếng Việt hiển thị đầy đủ dấu (`FZ Poppins`), sản phẩm nền trắng giữ nguyên màn hình trắng bên trong, có shadow và glow tách lớp.

## 3. Phạm vi Chưa Tự động Kiểm thử
- **Photoshop GUI Interactive Check:** QA 3 đã xác minh cấu trúc `.psd` bằng `ag-psd` `readPsd` round-trip và xác nhận có `D:\photoshop\Adobe Photoshop 2024\Photoshop.exe` trên máy, nhưng chưa tự động mở cửa sổ giao diện Photoshop 2024 để bấm sửa từng layer bằng tay. Người dùng nên mở 1 file `.psd` kết quả bằng nút **"Mở trong Photoshop 2024"** để xác nhận cuối cùng.
