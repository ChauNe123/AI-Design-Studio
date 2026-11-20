# 03 — DESIGN KNOWLEDGE BASE (DVF 2022 INTEGRATED)

**Cập nhật lần cuối:** 2026-11-19  
**Nguồn tri thức cốt lõi:** Giáo trình Cơ sở Thiết kế & Thị giác (*Design & Visual Fundamentals - DVF 2022*, Arena Multimedia, Giảng viên Ryan Lê Minh An)  
**Tệp dữ liệu máy đọc:** `D:/AI_Design_Studio/knowledge/knowledge_base.json`  
**Module nạp & truy vấn:** `D:/AI_Design_Studio/core/knowledge_base.py`  

---

## 1. Tổng Quan Hệ Thống Tri Thức Thiết Kế V1.3

AI Design Studio không hoạt động như một công cụ crop/tách ảnh vô thức, mà được điều khiển bởi **Hệ thống Tri thức Thiết kế Chuẩn hóa (Design Knowledge Base)** tích hợp toàn diện từ giáo trình DVF 2022. Hệ thống này cung cấp các ràng buộc toán học và thẩm mỹ cho cả 2 chế độ:
- **MODE A (Semantic Redesign):** Tự động phát hiện vai trò của layer (Background, Subject, Text Headline/Subhead/CTA, Decoration, Shadow), kiểm tra tương phản và phân cấp thị giác trước khi xuất PSD.
- **MODE B (Generate Composition):** Tự động áp dụng quy tắc 1/3, khoảng trắng âm bản (Negative space >= 20%), bóng tiếp xúc (Contact Shadow multiply), ánh sáng ngược (Backlight glow screen), cặp đôi phông chữ tiếng Việt (FZ Poppins) và hòa sắc theo ngành hàng.

---

## 2. Các Trụ Cột Tri Thức Tích Hợp Từ DVF 2022

### 2.1. 7 Yếu Tố Thị Giác Cơ Bản (The 7 Basic Visual Elements)

1. **Đường nét (Line):**
   - *Tâm lý học đường nét:* Nét ngang (an toàn, thư thái, cân bằng); nét dọc (uy nghiêm, vững chãi, chiều cao); nét chéo (động lực, tốc độ, kịch tính); nét cong (tự nhiên, mềm mại, thanh tao); nét zigzag (phấn khích, cảnh báo nguy hiểm).
   - *4 Công năng ứng dụng:* Contour (đường viền xác định biên giới), Dividing (phân tách không gian/cột), Decoration (trang trí, gạch chân), Gesture (bắt dáng chuyển động).
2. **Hình khối (Shape):**
   - *Hình vuông / Chữ nhật:* Biểu thị sự kiên định, vững chãi, đáng tin cậy (phù hợp công nghệ, ô tô, tài chính).
   - *Hình tròn:* Biểu thị sự hoàn hảo, vận động không ngừng, thân thiện (phù hợp icon, badge, nút bấm).
   - *Hình tam giác:* Biểu thị tính định hướng, sắc bén, cảnh báo nguy hiểm hoặc cân bằng động khi đứng trên cạnh đáy.
   - *Hình hữu cơ (Organic):* Tự nhiên, mềm mại, dòng chảy (phù hợp mỹ phẩm, thực phẩm sạch).
   - *Hình trừu tượng (Abstract):* Biểu tượng và icon hóa thông điệp.
3. **Không gian & Phối cảnh (Space & Perspective):**
   - *Không gian Dương (Positive) & Không gian Âm (Negative Space):* Đảm bảo khoảng thở tối thiểu 20-30% diện tích canvas để tránh tình trạng nhồi nhét chi tiết làm ngộp thị giác.
   - *Luật xa gần 3D & Isometric 2.5D:* Áp dụng phối cảnh trục đo và góc đổ bóng chuẩn cho sản phẩm thương mại.
4. **Nghệ thuật Chữ (Typography):**
   - Phân biệt rõ Typography (xếp chữ), Calligraphy (thư pháp) và Hand Lettering (vẽ chữ).
   - *Phân cấp kích thước 3 tầng:* Headline (lớn gấp 2.0x-2.5x Subheadline), Subheadline (giải thích tính năng), CTA/Hotline (gọn gàng, tương phản cao).
   - *An toàn tiếng Việt 100%:* Bắt buộc dùng `FZ Poppins`, `Be Vietnam Pro`, `Segoe UI` để không bị lỗi ô vuông ký tự có dấu.
5. **Màu sắc & Hòa sắc (Color Theory):**
   - Bánh xe màu Isaac Newton 1666 và hệ thống 3 bậc màu (Primary, Secondary, Tertiary).
   - Làm chủ 6 mô hình hòa sắc: Đơn sắc (Monochrome), Bổ túc trực tiếp (Complementary), Bổ túc xen kẽ (Split Complementary), Tương đồng (Analogous), Tam giác (Triadic), Tứ giác (Tetradic).
   - Quy tắc phân bổ màu 60-30-10: 60% màu nền chủ đạo, 30% màu phụ trợ, 10% màu nhấn tương phản (CTA/Badge).
6. **Chất cảm bề mặt (Texture):**
   - Sử dụng ảo ảnh xúc giác 2D (grain, noise mờ, vân kim loại, gradient đa điểm) để tăng chiều sâu cho nền poster.
7. **Ngôn ngữ Hình ảnh (Image):**
   - Thiết lập bối cảnh, độ kịch tính và tâm trạng cảm xúc phù hợp với thông điệp chiến dịch.

---

### 2.2. 12 Nguyên Lý Thiết Kế Bố Cục (The 12 Design Principles)

| Nguyên lý | Quy tắc ứng dụng trong AI Design Studio |
| :--- | :--- |
| **1. Tương phản (Contrast)** | Tách bạch chủ thể khỏi nền bằng độ sáng (Luminance) >= 40% hoặc màu bổ túc. |
| **2. Cân bằng (Balance)** | Cân bằng đối xứng cho thương hiệu sang trọng; Bất đối xứng cho công nghệ & khuyến mãi. |
| **3. Nhấn mạnh (Emphasis)** | Tạo DUY NHẤT một Tiêu điểm thị giác (Focal Point) chiếm 35-45% trọng tâm thị giác. |
| **4. Tỷ lệ (Proportion)** | Sản phẩm chính chiếm 40-55% diện tích khung hình; Headline nổi bật gấp 2-2.5x. |
| **5. Phân cấp (Hierarchy)** | Trật tự quét mắt: Headline → Hình ảnh sản phẩm → Lợi ích/Subhead → Nút CTA. |
| **6. Lặp lại (Repetition)** | Đồng bộ font chữ, màu sắc nhấn và kiểu bo góc nút bấm trên toàn bộ các artboard. |
| **7. Nhịp điệu (Rhythm)** | Khoảng cách ngắt nhịp đều đặn giữa các dòng text và các icon tính năng. |
| **8. Hoa văn (Pattern)** | Mẫu lưới đồ họa nền hỗ trợ nhận diện thương hiệu mà không làm rối mắt. |
| **9. Khoảng trắng (White Space)** | Dành tối thiểu 20-30% diện tích làm khoảng thở an toàn cho canvas. |
| **10. Chuyển động (Movement)** | Dẫn dắt ánh mắt theo đường Z-pattern (từ góc trên trái qua góc dưới phải đến CTA). |
| **11. Đa dạng (Variety)** | Kết hợp nét chữ đậm/mảnh hoặc thêm điểm sáng glow nhẹ để tránh nhàm chán. |
| **12. Đồng nhất (Unity)** | Mọi layer trong `DesignDocument` phải quy tụ về một phong cách mỹ thuật duy nhất. |

---

### 2.3. Bảng Tâm Lý Học 10 Màu Sắc Ứng Dụng Thực Chiến

- **Đỏ (`#ED2939`):** Quyền lực, năng lượng, tốc độ, kích thích vị trí → Nút Sale sốc, F&B, CTA.
- **Cam (`#FF7A00`):** Ấm áp, vui tươi, sôi nổi, thân thiện → Giới trẻ, nước giải khát, app sáng tạo.
- **Vàng (`#FFD600`):** Lạc quan, tự tin, trí tuệ, cảnh báo chú ý → Bán lẻ, giáo dục, biển báo.
- **Xanh Lá (`#10B981`):** Sinh thái, bình yên, an toàn, phát triển bền vững → SafeDrive, dược phẩm sạch, tài chính xanh.
- **Xanh Dương (`#0066FF`):** Tin cậy, công nghệ, bảo mật, chuyên nghiệp → Phần mềm, ngân hàng, bảo hiểm, y tế.
- **Tím (`#9104D3`):** Quý tộc hoàng gia, tâm linh, chữa lành, bí ẩn → Mỹ phẩm xa xỉ, spa cao cấp.
- **Hồng (`#FB0FBF`):** Ngọt ngào, hạnh phúc, lãng mạn → Phái nữ, mẹ & bé, bánh ngọt, thời trang.
- **Trắng (`#FFFFFF`):** Tinh khiết, tối giản sang trọng, sạch sẽ → Phong cách Minimalism, phòng khám, công nghệ cao.
- **Nâu (`#8B6400`):** Trầm ấm, mộc mạc của đất, tự nhiên → Cà phê, đồ da thủ công, nội thất gỗ mộc.
- **Đen (`#0C090A`):** Quyền lực tối thượng, xa xỉ, bí ẩn đỉnh cao → Thời trang hàng hiệu, ô tô hạng sang, typography.

---

### 2.4. Phong Cách Lấy Cảm Hứng Từ 10 Phong Trào Nghệ Thuật Lịch Sử

AI Design Studio hỗ trợ tạo kiểu (Presets) theo triết lý của 10 phong trào nghệ thuật lớn:
1. **Bauhaus (1919-1933):** "Form follows function" — Khối hình học thuần khiết, màu cơ bản, font sans-serif tinh gọn.
2. **Pop Art (1958-1972):** Màu neon bùng nổ, hoa văn chấm hạt Ben-Day, độ tương phản cực đại, phong cách truyện tranh.
3. **Art Deco (1920-1939):** Đối xứng hình học ziggurat, ánh kim vàng/bạc trên nền đen sang trọng.
4. **De Stijl (1917-1931):** Đường thẳng vuông góc, mảng màu Đỏ - Vàng - Xanh lam kết hợp Trắng - Xám - Đen.
5. **Constructivism (1917-1935):** Góc nghiêng chéo động lực học, phong cách công nghiệp Nga Đỏ - Đen - Trắng.
6. **Memphis (1981-1988):** Phản thiết kế (Anti-design), nổi loạn, hình khối bất quy tắc, màu pastel & neon vui tươi.
7. **Art Nouveau (1880-1910):** Đường cong ngọn roi hữu cơ, hoa văn thiên nhiên uốn lượn, thanh lịch.
8. **Futurism (1909-1930):** Tốc độ, máy móc, xung lực cơ khí bằng các vệt sáng chéo năng động.
9. **Dadaism (1916-1923):** Cắt dán ảnh ngẫu hứng (Photomontage / Collage), phá vỡ logic cũ.
10. **Arts & Crafts (1850-1914):** Tôn vinh vẻ đẹp thủ công mỹ nghệ và hoa văn thiên nhiên lặp lại.

---

## 3. Quy Trình QA 3 Cấp Độ Đã Nâng Cấp Bộ Quy Chuẩn Thị Giác

Ngoài việc kiểm tra kỹ thuật (không thủng ảnh, không mất text layer `TySh`), hệ thống QA tự động bổ sung các bài học kiểm định thị giác:
1. **QA Level 1 — Kiểm tra Phân cấp Thị giác (Hierarchy & Contrast):** Đảm bảo cỡ chữ Headline lớn hơn Subheadline tối thiểu 2.0x, độ tương phản văn bản với nền đạt chuẩn đọc rõ trong 2 giây.
2. **QA Level 2 — Kiểm tra Khoảng thở Âm bản (Negative Space Clutter):** Đảm bảo tổng diện tích chiếm dụng của chữ + vật thể không vượt quá 75-80% canvas.
3. **QA Level 3 — Kiểm tra Hòa sắc & Ánh sáng (Harmonies & Shadow Layers):** Xác nhận layer bóng tiếp xúc (`multiply`) và layer ánh sáng nền (`screen`) luôn tách riêng biệt, cho phép người dùng bật tắt hoặc chỉnh sửa tự do trên Photoshop 2024.
