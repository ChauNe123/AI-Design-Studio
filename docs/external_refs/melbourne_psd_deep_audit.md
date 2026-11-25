# 🔍 Báo Cáo Giải Phẫu & Đánh Giá Toàn Diện File PSD: `Melbourne_Xpress_Cabs_Editable_FullLayers.psd`

> **File kiểm tra**: `D:\AI_Design_Studio\exports\Melbourne_Xpress_Cabs_Editable_FullLayers.psd`  
> **Dự án liên kết**: `D:\AI_Design_Studio\projects\melbourne_xpress_cabs`  
> **Kích thước**: 736 × 736 px | RGB 8-bit | Dung lượng: **4.89 MB** | Tổng cộng **39 Layers** trong **6 Groups**  
> **Điểm đánh giá tổng quan**: **6.5 / 10** *(Kiến trúc phân rã xuất sắc, nhưng bị trừ nặng bởi bug lệch Mask trong code xuất PSD và inpainting mặt đường thô)*

---

## 📸 1. Tổng Thể Kết Quả Bóc Tách Trực Quan

Hệ thống AI Design Studio đã bóc tách từ 1 bức ảnh poster quảng cáo taxi Melbourne phẳng (`source_reference.png`) thành 39 layers độc lập.

![So sánh Bản gốc vs Recomposed vs Nhiệt lỗi](file:///C:/Users/BUM/.gemini/antigravity/brain/71fecb8e-54ce-49a7-b614-c6346126674d/melbourne_compare_combo.jpg)
*(Từ trái qua: **Bản gốc 100%** | **Bản ghép lại từ 39 Layer** | **Bản đồ nhiệt sai số 5x Heatmap**)*

![Toàn bộ 39 Layer trên nền Checkerboard](file:///C:/Users/BUM/.gemini/antigravity/brain/71fecb8e-54ce-49a7-b614-c6346126674d/all_39_layers_grid.jpg)
*(Bảng kiểm duyệt trực quan từng layer bóc tách: từ nền trời, đu quay, mặt đường, điện thoại, xe taxi đến từng cụm text)*

---

## 🏗️ 2. Cấu Trúc Phân Tầng (Layer Hierarchy) — ĐIỂM SÁNG XUẤT SẮC

File PSD được phân bổ cấu trúc vô cùng bài bản theo tiêu chuẩn studio chuyên nghiệp, chia thành **6 Nhóm lớn (Groups)** từ dưới lên trên:

```
📁 Melbourne_Xpress_Cabs_Editable_FullLayers.psd (736x736)
├── 📁 1_BG_&_Atmosphere (Nhóm 1: Nền & Khí hậu)
│   ├── [Layer] 00_Original_Flattened_Ref (Ảnh gốc để đối chiếu - Đang tắt mắt)
│   ├── [Layer] 01_Background_Sky_Twilight_Clean (Bầu trời hoàng hôn đã xóa chi tiết đè)
│   ├── [Layer] 02_Ferris_Wheel_Landmark_Right (Vòng quay mặt trời Ferris Wheel bên phải)
│   ├── [Layer] 03_Asphalt_Road_Curved_Track (Đoạn đường nhựa uốn cong uốn lượn)
│   ├── [Adj]   04_Curves_Sky_Contrast (Curves chỉnh tương phản bầu trời)
│   └── [Adj]   05_ColorBalance_Twilight_Grade (Color Balance phủ tone hoàng hôn)
│
├── 📁 2_Hero_Subjects_&_Mockup (Nhóm 2: Chủ thể chính & Mockup)
│   ├── [Layer] 06_iPhone_Mockup_Body_&_Map_Amodal (Điện thoại iPhone vẽ bù phần bị xe đè)
│   ├── [Layer] 07_iPhone_Map_Screen_Only (Màn hình Google Maps bóc riêng)
│   ├── [Layer] 08_Taxi_Contact_Shadow_Road (Bóng đổ tiếp xúc mặt đường của xe taxi)
│   ├── [Layer] 09_Yellow_Taxi_Cab_Hero (Xe taxi vàng chủ đạo - Hero Object)
│   ├── [Layer] 10_Taxi_Checkered_Decal_Strip (Dải decal caro đen trắng trên thân xe)
│   └── [Layer] 11_Taxi_Front_License_Plate_Orange (Biển số xe màu cam phía trước)
│
├── 📁 3_GPS_Route_&_Pins (Nhóm 3: Đường đi GPS & Ghim bản đồ)
│   ├── [Layer] 12_GPS_Route_Path_Blue (Đường nét đứt màu xanh điều hướng GPS)
│   ├── [Layer] 13_Pin_Origin_Red_Left (Ghim đỏ điểm đón phía trước xe)
│   └── [Layer] 14_Pin_Destination_Red_Glow (Ghim đỏ có hiệu ứng phát sáng điểm đến)
│
├── 📁 4_Footer_Banners_&_Badges (Nhóm 4: Băng rôn, Mảng chân trang & Icon)
│   ├── [Layer] 15_Ribbon_Strip_WeAreAvailable_Clean (Dải ruy băng cong màu vàng bóc sạch)
│   ├── [Layer] 16_Footer_Wedge_Blue_Left_Clean (Mảng vát chân trang màu xanh navy)
│   ├── [Layer] 17_Footer_Wedge_Orange_Right_Clean (Mảng vát chân trang màu cam)
│   ├── [Layer] 18_Icon_Phone_Circle_BottomLeft (Icon điện thoại tròn trắng bên trái)
│   └── [Layer] 19_Icon_Globe_Cursor_BottomRight (Icon quả địa cầu tròn trắng bên phải)
│
├── 📁 5_Brand_Logo_TopLeft (Nhóm 5: Logo thương hiệu)
│   ├── [Layer] 20_Logo_Cab_Graphic_Black (Biểu tượng xe taxi trên logo)
│   ├── [Layer] 21_Logo_Checkered_Arc_Yellow (Dải cung vòm caro vàng trên logo)
│   ├── [Layer] 22_Text_Brand_Name_OrigFX (Chữ thương hiệu "Melbourne Xpress Cabs" gốc)
│   └── [Type]  23_Text_Brand_Name_Editable (Chữ thương hiệu dạng gõ sửa text vector)
│
└── 📁 6_Typography_OrigFX_&_Editable (Nhóm 6: Hệ chữ song song Dual-Layer)
    ├── [Layer] 25_Text_Headline_TaxiService_OrigFX  /  [Type] 26_Text_Headline_TaxiService_Editable
    ├── [Layer] 27_Text_Subhead_MeCabs_OrigFX        /  [Type] 28_Text_Subhead_MeCabs_Editable
    ├── [Layer] 29_Text_Badge_WeAreAvailable_OrigFX  /  [Type] 30_Text_Badge_WeAreAvailable_Editable
    ├── [Layer] 31_Text_CallUs_Label_OrigFX          /  [Type] 32_Text_CallUs_Label_Editable
    ├── [Layer] 33_Text_Phone_Number_OrigFX          /  [Type] 34_Text_Phone_Number_Editable
    ├── [Layer] 35_Text_VisitWebsite_Label_OrigFX    /  [Type] 36_Text_VisitWebsite_Label_Editable
    └── [Layer] 37_Text_Website_URL_OrigFX           /  [Type] 38_Text_Website_URL_Editable
```

---

## 🌟 3. Các Điểm Cộng Đột Phá (Strengths)

### 3.1. Chiến lược Chữ Kép "Dual-Layer Typography" (Cực kỳ Thực dụng)
Trong thiết kế đồ họa AI, một trong những rào cản lớn nhất là font chữ vector tự nhận diện không bao giờ giống 100% font chữ gốc có hiệu ứng phức tạp (bevel, shadow, gradient màu, biến dạng phối cảnh). Con AI này đã xử lý cực thông minh bằng cách:
* Giữ **9 Layer `OrigFX` (Bitmap Pixels)**: Cắt nguyên vẹn từng chữ với 100% hiệu ứng gốc, nền trong suốt. Dành cho ai muốn render in ấn y hệt bản gốc.
* Kèm **9 Layer `Editable` (Type Layer vector)**: Tạo sẵn layer chữ chuẩn của Photoshop với thuộc tính Font, Size, Color, Tracking để người dùng click đúp chuột gõ sửa được ngay (thay đổi số điện thoại, đổi URL, đổi tên thương hiệu).

### 3.2. Bóc tách Amodal Object (Vẽ bù vật thể bị che khuất)
* Khi **ẩn chiếc xe taxi vàng** (`09_Yellow_Taxi_Cab_Hero`), thân chiếc iPhone (`06_iPhone_Mockup_Body_&_Map_Amodal`) không bị thủng một lỗ hình chiếc xe mà đã được AI tự động **vẽ bù thân máy và góc màn hình**!
* Khi **ẩn chiếc iPhone**, phần nền trời và vòng xoay đu quay phía sau đã có sẵn để không làm rách thiết kế.

| Thử nghiệm 1: Ẩn Xe Taxi (Xem thân iPhone vẽ bù) | Thử nghiệm 2: Ẩn iPhone (Xem nền sau lưng) | Thử nghiệm 3: Bật chế độ Text Gõ Sửa |
| :---: | :---: | :---: |
| ![Test 1](file:///C:/Users/BUM/.gemini/antigravity/brain/71fecb8e-54ce-49a7-b614-c6346126674d/test1_behind_taxi.jpg) | ![Test 2](file:///C:/Users/BUM/.gemini/antigravity/brain/71fecb8e-54ce-49a7-b614-c6346126674d/test2_behind_phone.jpg) | ![Test 3](file:///C:/Users/BUM/.gemini/antigravity/brain/71fecb8e-54ce-49a7-b614-c6346126674d/test3_editable_text_mode.jpg) |

---

## 🚨 4. CÁC LỖI KỸ THUẬT NGHIÊM TRỌNG (Critical Bugs Cần Sửa Ngay)

Khi đào sâu vào mã nguồn `D:\AI_Design_Studio\core\psd_bridge.js` và cấu trúc nhị phân của file PSD, tôi đã phát hiện **3 lỗi kỹ thuật rất nặng** khiến sản phẩm chưa thể đạt chuẩn thương mại:

### 🔴 Lỗi 1: Tọa độ Layer Mask bị trôi về `(0, 0)` trong `psd_bridge.js` (LỖI CHÍ MẠNG)
* **Vị trí bug**: File [psd_bridge.js](file:///D:/AI_Design_Studio/core/psd_bridge.js#L285-L291):
  ```javascript
  const maskTop = isAdj ? 0 : Math.round(lyr.mask_y ?? 0);
  const maskLeft = isAdj ? 0 : Math.round(lyr.mask_x ?? 0);
  psdLayer.mask = {
    top: maskTop,
    left: maskLeft,
    bottom: maskTop + maskImg.height,
    right: maskLeft + maskImg.width,
    defaultColor: 0
  };
  ```
* **Bản chất lỗi**: Trong file cấu hình `design_document.json`, trường `mask_x` và `mask_y` của tất cả các layer đều bị bỏ trống (`null`/`None`). Khi `psd_bridge.js` gặp `lyr.mask_y ?? 0`, nó lập tức gán tọa độ Mask ở vị trí **`Top: 0, Left: 0`**!
* **Hậu quả thực tế**:
  * Ví dụ xe taxi nằm ở tọa độ `(X: 58, Y: 362)`, kích thước mask là `598 × 291`.
  * Thay vì đặt mask ôm đúng vị trí xe tại `(58, 362)`, code lại đặt chiếc mask đó ở `(0, 0)` (tận góc trên cùng của bầu trời)!
  * Khi mở bằng Adobe Photoshop thực tế và bật layer mask, mask hoàn toàn **lệch khỏi pixel của xe**, làm xe taxi hoặc các chi tiết bị cắt lẹm hoặc tàng hình mất tích!
* **Cách khắc phục triệt để trong code**:
  Thay thế 2 dòng đó bằng:
  ```javascript
  const maskTop = isAdj ? 0 : Math.round(lyr.mask_y ?? lyr.y ?? 0);
  const maskLeft = isAdj ? 0 : Math.round(lyr.mask_x ?? lyr.x ?? 0);
  ```

---

### 🔴 Lỗi 2: Amodal Inpainting mặt đường bị "đóng cục" và viền răng cưa
* Hãy quan sát kỹ Layer `03_Asphalt_Road_Curved_Track`:
  * Ở vùng đường lộ ra bên ngoài thì có texture nhựa đường và vạch phân cách.
  * Nhưng vùng đường **nằm dưới gầm xe taxi được AI vẽ bù** lại là một **mảng màu xám bệt (flat gray block)** không hạt texture, viền cắt đứt khúc sắc nhọn bất thường.
  * Nếu người dùng kéo chiếc xe taxi sang góc khác hoặc đổi xe lớn hơn, mảng xám đục này lộ ra nhìn rất giả và thô, không thể dùng ngay mà bắt buộc phải dùng Stamp Tool hoặc Clone Tool vẽ lại.

---

### 🔴 Lỗi 3: Vết cắt hỏng trên Tháp Đu Quay & Vết nhòe trên Bầu Trời
* **Trên layer `02_Ferris_Wheel_Landmark_Right`**: Có một **vệt cắt dọc màu xám đậm** xẻ đôi các nan hoa của vòng quay đu quay. Đây là hậu quả của việc thuật toán phân đoạn (segmentation) cắt lẹm viền điện thoại iPhone ăn lấn vào đu quay.
* **Trên layer `01_Background_Sky_Twilight_Clean`**: Vùng trời bên trái iPhone có một vết vệt mờ hình chữ nhật (smudge rectangle) do AI dùng thuật toán xóa chữ bằng inpaint cục bộ bị bệt màu so với hạt nhiễu (noise) của bầu trời hoàng hôn.

---

### 🔴 Lỗi 4: Tràn viền kích thước Text Layer (Bounding Box Overflow)
* Trong file `design_document.json`, 4 layer chữ chân trang (`32_Text_CallUs_Label_Editable`, `34_Text_Phone_Number_Editable`, `36_Text_VisitWebsite_Label_Editable`, `38_Text_Website_URL_Editable`) có tọa độ đáy:
  * `y2 = 771` và `y2 = 773`.
  * Trong khi canvas chỉ cao **736 px**.
* Kết quả là khung chữ (Text Box) bị trôi vượt quá mép dưới của canvas 35px, gây khó khăn khi click chọn trong Photoshop nếu không zoom out.

---

## 📊 5. Bảng Điểm Đánh Giá So Với Tiêu Chuẩn Designer Chuyên Nghiệp

| Tiêu chí | Điểm số | Nhận xét chi tiết từ chuyên gia |
| :--- | :---: | :--- |
| **Cấu trúc File & Tên Layer** | **9.5 / 10** | Quá chuẩn mực. Đặt tên tiếng Anh chuẩn studio, phân 6 group rõ ràng, thứ tự z-index chính xác. |
| **Bóc tách Từng Vật Thể (Segmentation)** | **8.5 / 10** | Bóc rất sạch biên xe taxi, logo, biển số xe, icon hotline và dải ruy băng. |
| **Khả năng Gõ Sửa Text (Dual-Layer)** | **8.0 / 10** | Rất sáng tạo và thực dụng. Giúp cân bằng giữa giữ nguyên mỹ thuật gốc và cho phép sửa nội dung. |
| **Vẽ bù vùng khuất (Amodal Inpainting)** | **5.0 / 10** | Điểm yếu lớn nhất. Vẽ bù iPhone khá ổn nhưng mặt đường nhựa bị bệt xám, đu quay bị chém vệt. |
| **Độ tin cậy Kỹ thuật File PSD (Packaging)** | **4.0 / 10** | Dính bug chí mạng lệch Mask `(0, 0)` trong `psd_bridge.js` và tràn tọa độ text footer ra ngoài 736px. |
| **TỔNG KẾT TOÀN DIỆN** | **6.5 / 10** | **Ý tưởng & Kiến trúc đạt 9/10, nhưng khâu hoàn thiện kỹ thuật và inpainting chỉ đạt 5/10.** |

---

## 🎯 6. Đề Xuất Nâng Cấp Ngay Để Đạt Điểm 10/10

1. **Sửa 1 dòng code trong `D:\AI_Design_Studio\core\psd_bridge.js`**:
   Đổi `lyr.mask_y ?? 0` thành `lyr.mask_y ?? lyr.y ?? 0` để dời toàn bộ mask về đúng tọa độ thật của layer.
2. **Nâng cấp Module Inpaint đường nhựa**:
   Thay vì dùng inpainting thông thường cho mặt đường, hãy nạp prompt hoặc dùng ControlNet Depth/Lineart để vẽ tiếp vạch kẻ đường màu vàng uốn cong và rải thêm texture hạt nhựa đường đồng nhất.
3. **Thêm cơ chế Clamp Bounding Box Text**:
   Trước khi ghi file JSON, ép `y2 = Math.min(y2, canvas_height)` để tránh text layer lọt ra ngoài mép file.
