# 03 — DESIGN KNOWLEDGE BASE

Hệ thống lưu tri thức thiết kế có thể mở rộng tại `D:\AI_Design_Studio\knowledge\knowledge_base.json` thông qua `core/knowledge_base.py`.

## Nội dung Đang Lưu Trữ & Sử Dụng Thực Tế

1. **Nguyên tắc Thiết kế (`principles`):**
   - Bố cục: Phân cấp thị giác 3 tầng, khoảng trắng tối thiểu 20%, quy tắc 1/3.
   - Typography: Tương phản kích thước 2.0–2.5×, quy tắc đọc hiểu 2 giây.
   - Ánh sáng & Bóng đổ: Tách riêng lớp Contact Shadow (`multiply`) và Radial Backlight Glow (`screen`).
2. **Phong cách theo Ngành hàng (`industry_styles`):**
   - `tech_automotive` (Emerald Tech Dark, Canva Vibrant Green).
   - `commercial_product` (Amber Promo, Clean Studio Light).
   - `social_promo` (Midnight Gold Luxury).
3. **Thương hiệu mẫu (`brands`):** `SafeDrive` (màu chuẩn, font `FZ Poppins` hỗ trợ đầy đủ tiếng Việt tại `assets/fonts/`).
4. **Bài học QA thực tế (`qa_lessons`):**
   - Tách nền trắng chỉ flood-fill từ 4 cạnh ngoài để không làm thủng màn hình/đèn/áo trắng.
   - Luôn xuất pixel `imageData` kèm `TySh` cho Text Layer để tránh mất chữ khi mở trên trình xem không tự render font.
   - Khử quầng màu nền & vẽ lại icon nhỏ bằng vector 4× supersampling.
5. **Khả năng mở rộng:** Người dùng có thể thêm bài học thiết kế/QA mới ngay trong tab **Design Knowledge** trên giao diện.
