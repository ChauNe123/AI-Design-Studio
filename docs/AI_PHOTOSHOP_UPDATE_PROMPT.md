# 🚀 PROMPT NÂNG CẤP DỰ ÁN AI DESIGN STUDIO (CHO AI PHOTOSHOP)

> **Hướng dẫn sử dụng:** Sao chép toàn bộ nội dung trong khung prompt dưới đây và dán thẳng vào phiên chat của **AI PHOTOSHOP** (hoặc mở phiên làm việc mới trên thư mục `D:\AI_Design_Studio`).

---

```markdown
Chào AI PHOTOSHOP! Tôi cần bạn tiếp tục phát triển và nâng cấp hệ thống **AI Design Studio (hiện tại là V1.2)** tại thư mục `D:\AI_Design_Studio`.

Toàn bộ giáo trình học thuật chuẩn quốc tế **"Cơ sở Thiết kế & Thị giác" (Design & Visual Fundamentals - DVF 2022, Arena Multimedia)** vừa được nghiên cứu và đồng bộ hoàn tất vào hệ thống tại:
- `D:\AI_Design_Studio\knowledge\knowledge_base.json` (Dữ liệu máy đọc chuẩn)
- `D:\AI_Design_Studio\docs\03_DESIGN_KNOWLEDGE.md` (Tài liệu kiến trúc tri thức chi tiết)
- `D:\AI_Design_Studio\core\knowledge_base.py` (Module truy vấn tri thức)

---

### 🎯 MỤC TIÊU CÔNG VIỆC CẦN TRIỂN KHAI TIẾP THEO (V1.3 UPGRADE)

Bạn hãy đọc kỹ cấu trúc dự án hiện tại, đọc `knowledge_base.json` mới và thực hiện tự động các đầu việc sau:

#### 1. Nâng cấp Engine Sinh Bố Cục MODE B (`core/generate_engine.py`):
- **Bổ sung Style Presets từ 10 Phong trào Nghệ thuật Lịch sử:**
  + `bauhaus`: Tối giản hình học, font sans-serif tinh gọn, màu cơ bản, bố cục lưới bất đối xứng khúc chiết, tôn chỉ "Form follows function".
  + `pop_art`: Màu neon rực rỡ, độ tương phản cực đại, hiệu ứng chấm hạt Ben-Day/halftone nhẹ trên nền.
  + `art_deco`: Khối hình học ziggurat đối xứng sắc sảo, đường viền ánh kim vàng/bạc trên nền tối sang trọng.
  + `memphis`: Anti-design, hình khối bất quy tắc, hoa văn chấm bi/zic-zac lộn xộn, màu pastel kết hợp neon vui nhộn.
  + `swiss_modern`: Tinh khiết, grid hệ thống chuẩn, tỷ lệ khoảng trắng lớn (>30%), typography đậm nét.
- **Tự động áp dụng 6 Quy tắc Hòa sắc DVF:**
  + Cung cấp hàm sinh bảng màu tự động: Đơn sắc (Monochrome), Bổ túc trực tiếp (Complementary), Bổ túc xen kẽ (Split Complementary), Tương đồng (Analogous) theo tỷ lệ chuẩn 60-30-10.
- **Ràng buộc An toàn Bố cục (Layout Safeguards):**
  + Đảm bảo Headline luôn lớn hơn Subheadline tối thiểu 2.0x-2.5x (`visual_hierarchy`).
  + Luôn giữ khoảng trắng âm bản (Negative space) tối thiểu 20-25% diện tích canvas để thiết kế không bị ngộp.
  + Đặt điểm nhấn thị giác (sản phẩm/chủ thể) tại giao điểm 1/3 hoặc chiếm 45-55% diện tích bên phải/dưới (`rule_of_thirds`).

#### 2. Nâng cấp Engine Kiểm Định QA (`core/qa_engine.py`):
- Bổ sung bộ kiểm tra thẩm mỹ tự động (**Visual Aesthetic Checks**) trong QA 2:
  + `check_hierarchy_ratio`: Cảnh báo nếu kích thước Headline / Subheadline < 2.0x.
  + `check_negative_space_ratio`: Tính diện tích tổng các layer vật thể/chữ, cảnh báo nếu chiếm > 80% canvas.
  + `check_text_contrast`: Đo độ tương phản màu chữ và màu nền phía sau layer chữ, đảm bảo dễ đọc trong 2 giây.

#### 3. Cập nhật Giao diện Studio (`ui/index.html` và `ui/app.js`):
- **Tab Design Knowledge:** Nâng cấp hàm `loadKnowledge()` để hiển thị trực quan các thẻ:
  + *7 Yếu tố thị giác (Visual Elements)* kèm quy tắc tâm lý học.
  + *10 Phong trào Nghệ thuật (Art Movements)* kèm định nghĩa phong cách.
  + *Bảng tra cứu Tâm lý học 10 Màu sắc* (Tích cực vs Tiêu cực).
- **Tab MODE B (Generate):** Bổ sung dropdown chọn **"Phong cách Mỹ thuật (Art Movement Style)"** và **"Mô hình Hòa sắc (Color Harmony)"** để người dùng bấm chọn nhanh khi thiết kế poster mới.

#### 4. Kiểm thử Hồi quy & Đóng gói:
- Chạy lại bộ kiểm thử `python D:\AI_Design_Studio\tests\run_regression_tests.py` đảm bảo 9/9 test cases hiện tại tiếp tục PASS.
- Viết thêm 1 test case mới `MODE_B::test_art_movement_presets` kiểm tra sinh thiết kế theo style Bauhaus và Pop Art.
- Cập nhật nhật ký vào `D:\AI_Design_Studio\docs\07_CHANGELOG.md` và `TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md`.

Hãy bắt đầu phân tích mã nguồn và triển khai từng bước một cách cẩn thận, không làm hỏng các tính năng V1.2 đang chạy ổn định.
```
