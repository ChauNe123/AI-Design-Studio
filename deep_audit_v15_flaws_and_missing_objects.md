# 🚨 Báo Cáo Đối Soát Chuyên Sâu: Thực Trạng Bản Cập Nhật v1.5.1 & Các Lỗi Nặng Về Xóa Nền / Bóc Tách Vật Thể

> **Tài liệu đối chiếu**: [TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md](file:///D:/AI_Design_Studio/TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md)  
> **Các file PSD kiểm tra thực tế**:
> 1. `D:\AI_Design_Studio\exports\Garena_Banner_CongBo_Editable_FullLayers.psd` *(tạo từ `Banner Công bố.psd`)*
> 2. `D:\AI_Design_Studio\exports\Melbourne_Xpress_Cabs_Editable_FullLayers.psd` *(poster quảng cáo taxi)*
> 
> **Kết luận thẳng thắn**: **Nhận định của anh hoàn toàn chính xác 100%!**  
> Dù file tổng hợp update và `07_CHANGELOG.md` ghi nhận kết quả rất đẹp trên lý thuyết (*"11/11 PASS", "misaligned_mask_count = 0", "mae_vs_source = 2.21"*), nhưng khi **mở trực tiếp từng layer thực tế trong PSD lên soi**, hệ thống AI đang bộc lộ những lỗi cực kỳ nặng: **Xóa nền không sạch (bị bệt màu, nham nhở, dính vệt ghost text) và Bóc tách vật thể bị dính chùm, đục thủng lỗ, nát vụn hoặc thiếu sót nghiêm trọng.**

---

## 📸 1. Bằng Chứng Trực Quan: Bảng Sheet Từng Layer Được Bóc Ra

### 1.1. File `Garena_Banner_CongBo_Editable_FullLayers.psd` (Banner Esports)
Hãy nhìn vào bảng tách layer thực tế mà con AI đã xuất ra:

![Banner Layers Sheet](file:///C:/Users/BUM/.gemini/antigravity/brain/71fecb8e-54ce-49a7-b614-c6346126674d/banner_layers_sheet.jpg)

* **Hàng 1 - Nền Sân Vận Động (`01_Background_Stadium_Clean`)**:
  * Bị **bệt màu và sọc ngang loang lổ**. Vùng mái khán đài xuất hiện nguyên một quầng xanh lá/vàng nhân tạo và vết mờ khổng lồ nơi chữ *"CÔNG BỐ GIẢI ĐẤU"* bị xóa cẩu thả.
* **Hàng 2 - Cụm Giải Nhất**:
  * **Cọc Xu FC (`Coc_Xu_FC_Giai_Nhat`)**: Dính nguyên chữ logo màu xanh lá **"ONLINE"** nằm chình ình trên nóc đồng xu, hoàn toàn không được bóc tách!
  * **Áo Thun (`Ao_Thun_FC_Online`)**: Bị **dính chùm** với Móc khóa kim loại và Dây đeo thẻ! Đồng thời viền áo bị rách và dính các mảng ruy băng vàng lem nhem.
* **Hàng 3 - Cụm Giải Nhì**:
  * **Nón Kết (`Non_Ket_FC_Online`)**: Bị **ĐỤC THỦNG MỘT LỖ TRẮNG KHỔNG LỒ** ở bên phải (chỗ giáp ranh với áo thun)! Móc khóa lại bị gộp chung vào nón, viền xung quanh bị răng cưa vàng nham nhở.
* **Hàng 4 - Cụm Giải Ba**:
  * **Cọc Xu FC (`Coc_Xu_FC_Giai_Ba`)**: Lại tiếp tục dính chữ **"FC ONLINE"** màu xanh trên đỉnh cọc xu.
  * **Vòng Tay (`Vong_Tay_FC_Online`)**: Bị **xé rách nát vụn thành nhiều mảnh rời rạc**, thủng lỗ chỗ, không còn hình hài chiếc vòng tay nguyên vẹn!

---

### 1.2. File `Melbourne_Xpress_Cabs_Editable_FullLayers.psd` (Poster Taxi)
Bảng layer của poster taxi sau khi cập nhật v1.5.1:

![Melbourne Layers Sheet](file:///C:/Users/BUM/.gemini/antigravity/brain/71fecb8e-54ce-49a7-b614-c6346126674d/Melbourne_Xpress_Cabs_Layers_Sheet.jpg)

* **Bầu trời hoàng hôn (`01_Background_Sky_Twilight`)**: Xuất hiện một **vệt mờ trắng đục hình chữ nhật** khổng lồ ở phía sau lưng iPhone, làm hỏng toàn bộ dải chuyển màu mượt của bầu trời.
* **Đu quay (`02_Ferris_Wheel_Landmark_Right`)**: Vòng quay là hình tròn, nhưng layer bóc ra lại là một **khối chữ nhật bị chém dọc thẳng đuột bên trái** (như nhát dao cắt bánh), mất hẳn nửa bên trái của vòng quay!
* **Mặt đường nhựa (`03_Asphalt_Road_Curved_Track`)**: Vạch sơn vàng uốn lượn đi được nửa đường thì **bị đứt cụt ngủn**, nửa bên phải là một mảng xám đen bệt đặc không có texture nhựa đường.
* **Icon điện thoại (`18_Icon_Phone_Circle_Bottom`)**: Bản gốc là một huy hiệu tròn màu trắng viền sắc nét chứa icon điện thoại. AI bóc ra **vứt mất tiêu vòng tròn trắng**, chỉ còn lại một cái ống nghe màu xanh mờ căm và méo mó!
* **Icon địa cầu (`19_Icon_Globe_Cursor_Bottom`)**: Bị vỡ hạt pixel, trông như đồ họa game 8-bit thời xưa thay vì vector thương mại.

---

## 🔍 2. Phân Tích Chi Tiết 2 Nhóm Lỗi Lớn Nhất

### 🛑 NHÓM LỖI 1: "XÓA KHÔNG SẠCH" (Background Inpainting Thất Bại)

| Vị trí lỗi | Hiện tượng thực tế trên Layer | Nguyên nhân kỹ thuật trong Source Code |
| :--- | :--- | :--- |
| **Nền sân vận động (Banner Garena)** | Xuất hiện các dải sọc mờ ngang, quầng xanh lá/vàng lơ lửng, vết mờ xám lớn giữa khán đài. | Trong `core/banner_decomposer.py` (dòng 829–848), code dùng vòng lặp `np.interp()` để **nội suy màu ngang 1D** từng dòng pixel (`ry`). Khi hai bên mép có màu cỏ xanh hoặc vệt neon, nó kéo một vệt màu xanh mờ quét ngang toàn bộ sân vận động! |
| **Nền trời hoàng hôn (Melbourne)** | Quầng mờ đục sau thân máy iPhone làm loang lổ hạt noise của nền trời. | Thuật toán `Harmonic Diffusion` chỉ làm nhòe cục bộ (blur) vùng mask cũ thay vì tái tạo hạt gradient hoàng hôn. |
| **Mặt đường gầm xe (Melbourne)** | Vạch kẻ đường màu vàng bị đứt cụt, gầm xe là mảng đen đặc không hạt. | Không có mô hình vẽ bù phối cảnh đường cong (Perspective Inpainting), code chỉ fill mảng màu phẳng bằng hàm `cv2.inpaint` rẻ tiền. |

---

### 🛑 NHÓM LỖI 2: "BÓC TÁCH VẬT THỂ THIẾU QUÁ NHIỀU & DÍNH CHÙM / BỊ ĐỤC THỦNG"

So sánh giữa **Bản thiết kế gốc của Designer (`Banner Công bố.psd`)** và **Bản AI bóc tách (`Garena_Banner_CongBo_Editable_FullLayers.psd`)**:

| Vật thể / Thành phần | Trong bản gốc của Designer Garena | Bản AI bóc tách ra | Hậu quả khi Designer tái sử dụng |
| :--- | :--- | :--- | :--- |
| **Áo thun & Móc khóa (Giải nhất)** | 2 Smart Object độc lập (`aomattruoc` và `mockhoa`). | **Gộp chung vào 1 layer** `Ao_Thun_FC_Online`. | Muốn đổi móc khóa hay dời áo thun đi chỗ khác là **chịu chết**, không thể tách rời. |
| **Nón kết (Giải nhì)** | Smart Object nguyên vẹn (`Nón`). | **Bị khoét thủng một mảng to tướng** ở vành nón bên phải (vết khoét do áo thun đè lên). | Kéo nón sang chỗ khác sẽ thấy nón bị rách toạc một miếng! |
| **Vòng tay (Giải ba)** | Smart Object nguyên vẹn (`Vòng tay`). | **Nát vụn thành các mảnh rời rạc**, thủng lỗ chỗ. | Hoàn toàn không thể sử dụng được, trông như rác đồ họa. |
| **Cọc xu FC Online** | Pixel layer riêng sạch sẽ (`FC`). | Bị **dính chữ "ONLINE"** màu xanh lá của logo trên đỉnh xu. | Nhìn rất bẩn, không phải vật phẩm cọc xu sạch. |
| **3 Bục Vinh Quang (Podiums)** | Bục 3D Isometric có khối đổ bóng, mặt trên có chiều sâu. | Biến thành **3 khối hộp chữ nhật màu cam phẳng lì**, mất toàn bộ góc nghiêng 3D. | Mất hoàn toàn chất 3D gaming của banner gốc. |
| **Hệ thống Confetti & Ngôi sao** | **10 Layer Shape** riêng lẻ (`Shape 10`, `Shape 11`, `Shape 18`...), 4 Layer sao. | Bị gộp hết vào 1 layer `Confetti_Particles` và `Stars_4Point_Sparkles`, một nửa số hạt bị xóa mất. | Không thể chỉnh sửa quỹ đạo bay hay màu sắc của từng hạt confetti. |
| **Thiết bị Gaming (Laptop, Console)** | 2 Smart Object chất lượng cao riêng biệt. | Bị cắt méo viền, dính viền đen xung quanh. | Đặt lên nền sáng sẽ lộ ngay viền đen xấu xí. |

---

## 🛠️ 3. Căn Nguyên Kỹ Thuật: Tại Sao Con AI Lại Làm Ra Kết Quả Tệ Như Vậy?

Khi xem kỹ các file code mới cập nhật (`core/banner_decomposer.py`, `core/poster_decomposer.py`, `core/reconstruction_engine.py`), có 3 nguyên nhân cốt lõi:

1. **Lạm dụng "Heuristic Màu Sắc Cứng" (Hardcoded HSV Thresholding) thay vì AI Phân Đoạn Thực Thụ**:
   - Để tìm bục số 1, 2, 3, code viết: `hsv[:, :, 0] >= 10 & hsv[:, :, 0] <= 26...`
   - Để tìm nón kết, cọc xu, code dùng các tọa độ vùng cố định: `int(w * 0.27), int(h * 0.29)...`
   - **Hệ quả**: Màu sắc trong ảnh thiết kế luôn có gradient, bóng đổ và ánh sáng phản chiếu. Việc dùng ngưỡng màu cứng khiến AI cắt lẹm vào vật thể, bỏ sót chi tiết hoặc gộp nhầm các vật thể khác màu vào nhau.

2. **Hoàn Toàn Thiếu Cơ Chế "Amodal Inpainting" Cho Từng Vật Thể (Chỉ Biết Cắt Phần Nhìn Thấy)**:
   - Khi Áo thun đè lên Nón kết, AI chỉ cắt lấy **vùng nhìn thấy (visible mask)** của Nón kết.
   - Một AI xịn phải hiểu: *"Phía sau chiếc áo thun vẫn là phần vành nón kết, ta phải vẽ bù (inpaint) phần vành nón bị che khuất để khi xuất ra, layer Nón kết là một chiếc nón nguyên vẹn 100%"*.
   - Hiện tại AI của Studio không làm điều này cho vật phẩm, dẫn đến Nón kết bị lẹm một lỗ khuyết, Vòng tay bị đứt đoạn!

3. **Cơ Chế Xóa Nền Bằng Nội Suy 1D (`np.interp`) Làm Hỏng Sân Vận Động**:
   - Thay vì để mô hình chuyên dụng xóa vật thể và bù vân khán đài/mặt sân tự nhiên, code lại chạy một hàm quét ngang kéo màu từ mép trái sang mép phải, biến sân vận động thành một bức tranh nhòe sọc ngang như tivi mất sóng.

---

## 📋 4. Bản Kế Hoạch Nâng Cấp Triệt Để (Action Plan) Để Đạt Chuẩn 10/10

Để AI Design Studio thực sự bóc tách được một file PSD chuẩn như Designer chuyên nghiệp làm ra, hệ thống cần được tái cấu trúc 4 điểm sau:

1. **Thay thế toàn bộ cơ chế xóa nền nội suy 1D bằng Full-Frame Inpainting**:
   - Xóa bỏ đoạn code `np.interp` và Gaussian Blur trong `_reconstruct_clean_stadium_background`.
   - Sử dụng mask giãn nở thông minh (Dilation 15px) và đưa thẳng vào mô hình Inpainting (LaMa / Stable Diffusion Inpainting) với đầy đủ context 2 chiều (2D context) để tái tạo trọn vẹn khán đài và mặt sân cỏ.
2. **Triển khai Amodal Object Completion (Vẽ bù vật thể bị che khuất)**:
   - Đối với các vật phẩm đè nhau (Nón kết, Áo thun, Vòng tay, Bục vinh quang): Sau khi xác định bounding box, chạy thuật toán Inpaint để khôi phục các góc bị che khuất, đảm bảo mỗi layer khi tách ra là **một vật thể hoàn chỉnh không bị thủng lỗ**.
3. **Tách riêng biệt từng Sub-Item bằng Segment Anything 2 (SAM 2) đa điểm**:
   - Tách rời hoàn toàn: `Áo thun riêng` | `Móc khóa riêng` | `Dây đeo riêng`.
   - Làm sạch chữ "ONLINE" trên cọc xu bằng cách coi chữ đó là một text layer đè lên trên bề mặt đồng xu.
4. **Không "làm đẹp số liệu trên giấy" (Reject Shallow QA Metrics)**:
   - Chỉ số `mae_vs_source = 2.21` thực chất là vô nghĩa nếu chỉ ghép lại các layer cắt vụn để đối chiếu tổng thể. QA cần bổ sung bài test **"Từng layer đơn lẻ có bị thủng lỗ không?"** và **"Nền sau khi xóa có bị vệt sọc/mờ loang không?"**.
