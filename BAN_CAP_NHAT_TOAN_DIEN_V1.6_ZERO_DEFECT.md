# 🛡️ BẢN ĐẶC TẢ NÂNG CẤP TOÀN DIỆN v1.6.0: ZERO-DEFECT ARCHITECTURE OVERHAUL
## HỆ THỐNG PHÂN RÃ THIẾT KẾ & ĐÓNG GÓI PSD CHUẨN THƯƠNG MẠI (COMMERCIAL GRADE)

> **Mục đích**: Tài liệu này là **Chỉ thị Kỹ thuật Tối cao** đóng gói toàn bộ quy chuẩn kiến trúc, thuật toán và tiêu chí nghiệm thu cho AI Design Studio.  
> **Nguyên tắc cốt lõi**: **TUYỆT ĐỐI KHÔNG LÀM ĐẸP SỐ LIỆU TRÊN GIẤY**. Cấm mọi hình thức tự động đánh dấu `PASS` ảo khi chất lượng thị giác chưa đạt chuẩn. Người dùng (User) là người thẩm định trực quan cuối cùng trước khi xuất xưởng.

---

## 🚫 PHẦN 1: BẢNG "LỖI ĐỎ" NGHIÊM CẤM (ZERO-TOLERANCE DEFECTS)

Bất kỳ file PSD hoặc Layer nào vi phạm một trong các điều sau đây đều bị coi là **FAIL 100%**:

| STT | Lỗi Cũ Cấm Tái Phạm | Biểu Hiện Vi Phạm | Quy Định Xử Lý Bắt Buộc |
| :---: | :--- | :--- | :--- |
| ❌ **1** | **Xóa nền bằng nội suy 1D (`np.interp`)** | Sân vận động / Bầu trời bị vệt sọc ngang mờ, kéo màu từ trái qua phải làm bệt nền như tivi mất sóng. | **CẤM HOÀN TOÀN** mọi vòng lặp `np.interp` theo hàng pixel trên ảnh nền. Chỉ được dùng mô hình Inpainting 2D thực thụ (LaMa / SD Inpainting) lấy context 2 chiều. |
| ❌ **2** | **Vật thể bị đục thủng lỗ (Punctured Layers)** | Nón kết bị lẹm một lỗ lớn bên phải do áo thun đè lên; Vòng tay bị nát vụn thành nhiều mảnh rời rạc; Đu quay bị chém thẳng đứng. | **CẤM XUẤT LAYER BỊ KHUYẾT**. Bắt buộc phải kích hoạt cơ chế **Amodal Completion** vẽ bù vùng bị che khuất để mỗi layer là một vật phẩm hoàn chỉnh 100%. |
| ❌ **3** | **Dính chùm vật thể (Clustered Objects)** | Áo thun dính liền Móc khóa và Dây đeo thẻ; Nón kết dính chung với móc khóa kim loại; Chữ "ONLINE" dính trên đỉnh cọc xu. | **BẮT BUỘC TÁCH RỜI ĐỘC LẬP**: Áo thun riêng, Móc khóa riêng, Cọc xu riêng (được làm sạch chữ rác đè lên). |
| ❌ **4** | **Làm phẳng đồ họa 3D (Flattened 3D)** | Biến 3 Bục vinh quang 3D Isometric thành 3 hình chữ nhật màu cam phẳng lì; làm mất bóng tiếp xúc mặt sàn. | Phải bảo tồn góc nghiêng trục đo (Isometric Perspective), mặt trên (Top-face) và ánh sáng khối 3D. |
| ❌ **5** | **Gộp / Xóa chi tiết trang trí nhỏ** | 10 mảnh Confetti nhiều màu và 4 Ngôi sao bị gộp hết vào 1 layer duy nhất, một nửa bị xóa mất tích. | Giữ nguyên từng Layer hạt confetti, ngôi sao hoặc tia sáng như một hệ thống element tách rời. |
| ❌ **6** | **Tự ý đóng gói file khi chưa có User duyệt** | Tự động sinh file `.psd` rồi tự kết luận "11/11 PASS" mà không hiển thị ảnh cho User kiểm tra. | **DỪNG LẠI (STANDBY)** sau bước kết xuất Contact Sheet, chờ lệnh User phê duyệt bằng mắt mới được ghi file PSD hoàn chỉnh. |

---

## 🏗️ PHẦN 2: THIẾT KẾ KIẾN TRÚC 5 MODULE MỚI (V1.6.0 ENGINE)

```
                            [ẢNH PHẲNG GỐC INPUT]
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ MODULE 1: INPAINT│        │ MODULE 2: AMODAL │        │ MODULE 3: ATOMIC │
│ CLEAN BACKGROUND │        │ OBJECT COMPLETION│        │ DISENTANGLEMENT  │
│  (Xóa nền sạch)  │        │ (Vẽ bù vật khuất)│        │ (Tách rời chi tiết)
└────────┬─────────┘        └────────┬─────────┘        └────────┬─────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │ MODULE 4: 3D ISOMETRIC   │
                        │ & GEOMETRY PRESERVATION  │
                        └────────────┬─────────────┘
                                     ▼
                        ┌──────────────────────────┐
                        │ MODULE 5: HUMAN-IN-THE-  │
                        │ LOOP QA & PSD PACKAGER   │
                        └──────────────────────────┘
```

---

### Module 1: Clean Background Reconstruction (Xóa Nền Đẳng Cấp Cao)
1. **Mask Dilate 2 Giai Đoạn**:
   - Giai đoạn 1: Tạo Foreground Mask thô của toàn bộ vật thể + chữ + bóng đổ.
   - Giai đoạn 2: Giãn nở biên (Dilation) với kernel `15×15` hoặc `23×23` để triệt tiêu 100% ánh sáng viền (fringing) và bóng đổ mềm (soft drop shadows).
2. **Context-Aware 2D Inpainting (Cấm tiệt `np.interp`)**:
   - Sử dụng native `LaMa ONNX` với cửa sổ trượt (Sliding Windows `512×512`, overlap 25%) kèm Gaussian Blending ở các mép ghép tile.
   - Với nền có texture hạt (như bầu trời hoàng hôn hay mặt đường nhựa): Sau khi inpaint, chạy bộ lọc tổng hợp nhiễu vi mô (`Micro-Noise Synthesis`) đồng nhất hạt noise với vùng xung quanh, loại bỏ vệt mờ nhẵn thô thiển.

---

### Module 2: Amodal Object Completion (Vẽ Bù Vật Thể Bị Che Khuất)
Mọi vật phẩm thương mại (quần áo, nón, cúp, cọc xu, điện thoại, xe cộ) khi xuất hiện trong thiết kế đều có phần bị che khuất bởi vật thể khác phía trước.
1. **Xác định Convex Hull & Dự đoán Dáng Hoàn Chỉnh**:
   - Lấy contour của phần nhìn thấy (visible part).
   - Dự đoán đường biên khép kín dựa trên tính đối xứng hình học của vật thể (ví dụ: vành nón kết là hình oval cong đều; vòng tay là hình elip khép kín; thân điện thoại là chữ nhật bo góc).
2. **Inpaint Nội Bộ Vật Thể (Internal Fill)**:
   - Chỉ vẽ bù trong phạm vi đường biên dự đoán của vật thể đó.
   - Lấy mẫu texture/màu sắc chính của vật thể để điền vào vết khuyết, đảm bảo **layer xuất ra là một vật phẩm độc lập, hoàn chỉnh, không có vết cắn hay lỗ thủng**.

---

### Module 3: Atomic Disentanglement (Tách Rời Từng Phụ Kiện & Làm Sạch Chữ Rác)
1. **Tách Rời Phụ Kiện Khỏi Sản Phẩm**:
   - `Áo thun` phải tách rời khỏi `Móc khóa` và `Dây đeo`.
   - `Nón kết` phải tách rời khỏi `Móc khóa`.
   - Bằng cách sử dụng **SAM 2 Point-Prompting**: Đặt điểm dương (positive point) vào mặt vải áo, điểm âm (negative point) vào kim loại móc khóa để mô hình bóc tách 2 đường biên riêng biệt.
2. **Khử Chữ Rác Trên Bề Mặt Vật Thể**:
   - Chữ logo "ONLINE" đè trên đỉnh cọc xu: Xác định mask của chữ, dùng inpaint texture kim loại đồng xu để xóa chữ trên layer cọc xu.
   - Text "ONLINE" được đưa sang một layer độc lập (nếu cần tái sử dụng) hoặc loại bỏ hoàn toàn khỏi cọc xu.

---

### Module 4: 3D Isometric & Geometry Preservation (Bảo Tồn Khối 3D)
1. Không được xén bục theo bounding box 2D phẳng.
2. Bảo tồn 3 mặt của bục: Mặt trên (Top-Face), Mặt trước (Front-Face) và Mặt bên (Side-Face) cùng hiệu ứng bevel/bo góc.
3. Khi vẽ bù mặt trên của bục (nơi bị cọc xu đè lên): Chỉ vẽ bù đúng màu gradient vàng/cam ánh kim của mặt trên, không làm mất đường viền phối cảnh trục đo.

---

### Module 5: Human-in-the-Loop QA Protocol (Quy Trình User Thẩm Định)
Đây là chốt chặn quan trọng nhất để chống lại tình trạng AI tự ý làm bậy:

1. **Bước 1 — Render Tự Động Contact Sheet**:
   - Xuất file ảnh `visual_audit_sheet.jpg`: Chứa toàn bộ các layer đơn lẻ đặt trên nền lưới ca-rô trong suốt (**Checkerboard 1:1**).
   - Xuất file ảnh `background_cleaned.jpg`: Nền sau khi xóa toàn bộ vật thể.
   - Xuất file ảnh `before_after_slider.jpg`: So sánh đối chiếu 1:1 với ảnh gốc.
2. **Bước 2 — Chế Độ Chờ Lệnh (STANDBY LOCK)**:
   - Hệ thống **DỪNG LẠI**, thông báo cho User đường dẫn các file ảnh visual trên.
   - **CẤM TỰ Ý ĐÓNG GÓI PSD** cho đến khi User kiểm tra trực quan bằng mắt và phản hồi:
     - *"Đạt rồi, xuất file đi"* ➔ Lúc đó mới được gọi `psd_bridge.js` đóng gói PSD.
     - *"Nón kết còn lẹm / Nền còn vệt"* ➔ AI phải sửa tiếp vùng đó, không được cãi hoặc tự ý bypass.

---

## 📝 PHẦN 3: ĐOẠN LỆNH GIAO VIỆC MẪU CHO CON AI CỦA ANH

Anh hãy copy toàn bộ đoạn văn bản trong khung dưới đây và gửi trực tiếp vào phiên chat của con AI Studio:

```markdown
CHỈ THỊ CẢI TỔ HỆ THỐNG V1.6.0: NÂNG CẤP CHẤT LƯỢNG THỰC TẾ — CẤM LÀM ĐẸP SỐ LIỆU TRÊN GIẤY

Tao đã kiểm tra trực quan từng layer thực tế trong các file PSD mày xuất (Garena Banner và Melbourne Cabs). Sản phẩm đầu ra hoàn toàn CHƯA ĐẠT YÊU CẦU:
1. XÓA NỀN CỰC BẨN: Sân vận động bị bệt sọc ngang loang lổ do mày dùng vòng lặp np.interp() kéo màu rẻ tiền; khán đài dính vết mờ khổng lồ và quầng xanh loang lổ; bầu trời hoàng hôn bị vệt mờ đục.
2. BÓC TÁCH THỦNG LỖ & DÍNH CHÙM: Nón kết bị đục thủng một lỗ lớn bên vành; Vòng tay bị nát vụn thành nhiều mảnh; Áo thun dính chùm với Móc khóa; Cọc xu dính nguyên chữ ONLINE xanh lè; 3 bục vinh quang 3D bị biến thành 3 hộp cam phẳng lì; Confetti bị gộp mất hết.

YÊU CẦU MÀY NÂNG CẤP SOURCE CODE THEO ĐÚNG BẢN ĐẶC TẢ V1.6.0:
- MODULE 1: Xóa bỏ 100% vòng lặp np.interp() và blur rẻ tiền trong file reconstruction. Dùng mô hình inpaint 2D thực thụ với mask giãn nở 15-20px để tái tạo khán đài, mặt sân cỏ và bầu trời sạch tinh, đồng nhất hạt noise.
- MODULE 2 (AMODAL COMPLETION): Bắt buộc vẽ bù các phần bị che khuất. Nón kết, Áo thun, Vòng tay khi bóc ra phải là vật phẩm nguyên vẹn 100%, TUYỆT ĐỐI KHÔNG ĐƯỢC THỦNG LỖ hay ĐỨT ĐOẠN.
- MODULE 3: Tách rời hoàn toàn Áo thun riêng, Móc khóa riêng, Dây thẻ riêng. Làm sạch chữ ONLINE khỏi cọc xu. Giữ nguyên từng layer Confetti, Sao và Tia sáng độc lập.
- MODULE 4: Giữ nguyên khối 3D Isometric của 3 bục vinh quang.
- MODULE 5 (QUY TRÌNH DUYỆT BẰNG MẮT): Sau khi code xong, MÀY KHÔNG ĐƯỢC TỰ Ý ĐÓNG GÓI PSD VÀ KHÔNG ĐƯỢC TỰ TUYÊN BỐ "PASS". Mày phải xuất ảnh visual_audit_sheet.jpg (từng layer trên nền ca-rô) và background_cleaned.jpg, sau đó DỪNG LẠI và CHỜ TAO VÔ XEM TRỰC QUAN BẰNG MẮT. Khi nào tao gật đầu thì mới được xuất PSD!

Triển khai cập nhật ngay và báo cáo chi tiết những dòng code mày đã thay đổi!
```

---

## 🤝 PHẦN 4: QUY TRÌNH PHỐI HỢP 3 BƯỚC GIỮA ANH VÀ TÔI

Khi anh đưa chỉ thị trên cho con AI Studio:

1. **Bước 1 — AI Studio cập nhật code & xuất ảnh visual**: Con AI sẽ sửa code và xuất ra các ảnh kiểm duyệt `visual_audit_sheet.jpg` và `background_cleaned.jpg`.
2. **Bước 2 — Anh kiểm tra trực quan & báo cáo**: Anh chỉ cần mở 2 ảnh đó lên soi bằng mắt, chụp màn hình hoặc nhắn cho tôi biết chỗ nào anh thấy đã sạch, chỗ nào vẫn còn cấn hoặc lỗi.
3. **Bước 3 — Tôi kiểm định độc lập & cung cấp giải pháp**: Tôi sẽ đọc trực tiếp nhị phân file, phân tích ma trận pixel và code để chỉ ra chính xác con AI đã sửa thật hay còn sót điểm nào, giúp anh nắm thế chủ động 100% mà không bị đánh lừa bởi bất kỳ chỉ số ảo nào!
