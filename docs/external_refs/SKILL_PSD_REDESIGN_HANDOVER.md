---
name: psd-layer-redesign
description: Quy trình chuẩn & bộ công cụ tự động hóa bóc tách ảnh thiết kế phẳng (PNG/JPG/WebP/Canva) thành từng Layer độc lập, vẽ bù vùng bị che, làm nét Full HD (2x), kiểm duyệt QA 2 tầng (Checkerboard + Composite 1:1) và đóng gói thành file .PSD nhiều Layer kèm Editable Text Layers.
---

# 🎨 PSD Layer Redesign & Decomposition — Master Skill & Handover

Tài liệu này tổng hợp **toàn bộ kiến trúc, quy trình vận hành, thư viện kỹ thuật, các bài học xử lý lỗi thực tế và hệ thống kiểm duyệt QA** cho hệ thống **"Thay đổi toàn diện"** (tách ảnh phẳng thành `.psd` nhiều Layer chuẩn Full HD). Bất kỳ AI Agent nào đọc file này đều có thể tiếp quản và chạy tiếp ngay lập tức.

*(Bản đồng bộ với Skill hệ thống tại `C:\Users\BUM\.gemini\config\skills\psd-layer-redesign\SKILL.md`).*

---

## 1. Mục tiêu & Triết lý Vận hành

1. **Mục tiêu:** Biến 1 bức ảnh thiết kế phẳng (`.png`, `.jpg`, `.webp`, ảnh xuất từ Canva...) thành **1 file `.psd` nhiều Layer hoàn chỉnh** để người dùng mở trực tiếp bằng **`PhoToSop.exe`** (`D:\KBDobe_Hub_Windows_x64\KBDobe_Hub\Apps\PhoToSop\PhoToSop.exe`) hoặc **`Adobe Photoshop 2024`** (`D:\photoshop\Adobe Photoshop 2024`) và chỉnh sửa từng thành phần thoải mái.
2. **Nguyên tắc Cốt lõi:**
   - **Không giao file chưa kiểm duyệt:** Bắt buộc chạy qua **Kiểm duyệt 2 Tầng** (soi từng Layer trên nền ca-rô + ghép ngược toàn bộ Layer đối chiếu 1:1 với ảnh gốc) trước khi gửi kết quả cho người dùng.
   - **Làm nét Full HD (`2×`):** Luôn khử nhiễu nén JPEG/watermark nhẹ, nâng độ phân giải lên `2×` (Full HD) và tăng độ nét có kiểm soát.
   - **Trung thực về giới hạn kỹ thuật:** Với máy không có GPU NVIDIA rời (`nvidia-smi` không có), việc vẽ bù vật thể phức tạp bị che khuất dùng **AI Generative Inpainting** (`image-generator` hoặc API ngoài); nếu hết quota API thì dùng phương án dự phòng OpenCV + Vector hóa thủ công.

---

## 2. Môi trường & Công cụ Đã Cài Sẵn trên Máy

- **Thư mục làm việc chính:** `D:\AI\TESTER\redesign_studio\`
- **Python (`3.15.2`):** Đã cài `Pillow` (`PIL`), `OpenCV` (`cv2`), `numpy`.
- **Node.js (`v24.18.0`):** Đã cài `ag-psd`, `pngjs` trong `D:\AI\TESTER\redesign_studio\node_modules\`.
- **Phần cứng:** CPU Windows (không có GPU NVIDIA rời).

### Cấu trúc File & Script Hiện Có trong `D:\AI\TESTER\redesign_studio\`

| File / Thư mục | Vai trò & Trường hợp đã triển khai |
| :--- | :--- |
| `decompose.py` / `decompose_deep.py` | Tách ảnh poster bằng OpenCV (ước lượng nền cục bộ LAB + Flood-fill + GrabCut). |
| `extract_ai_layers.py` + `build_psd.js` | **Case 1 (`ONEWAY TAXI` `736×736`):** Kết hợp ảnh AI vẽ bù Con đường 3D & Đuôi xe Taxi + tách Tay cầm iPhone → xuất `OneWay_AI_QA_Passed.psd`. |
| `process_safedrive.py` + `build_safedrive_psd.js` | **Case 2 (`SafeDrive` `765×1024` → Full HD `1530×2048`):** Tách nền sóng xanh, ảnh tròn tài xế, điện thoại AR, logo, 4 thẻ tính năng bo góc → xuất `safedrive_fullhd/SafeDrive_FullHD_Editable.psd`. |
| `process_canva.py` + `enhance_canva_phone.py` + `build_canva_psd.js` | **Case 3 (`Canva SafeDrive` `1024×1024` → Full HD `2048×2048`):** Tách nền xanh giữ sóng nhẹ, khối cong đen liền khối, ảnh tài xế, **4 icon vẽ lại bằng vector 4× siêu nét**, **điện thoại taplo tách riêng & thay màn hình AR sắc nét** → xuất `canva_fullhd/Canva_SafeDrive_FullHD_Editable.psd`. |
| `index.html` + `server.py` | Web App Mini-Photoshop Local (`http://127.0.0.1:8765`) dùng khi người dùng muốn kéo thả, đổi màu Hue/Sat/Bright trực tiếp trên trình duyệt (mặc định tắt, chỉ bật khi được yêu cầu). |

---

## 3. Quy trình Chuẩn 6 Bước khi Nhận 1 Ảnh Mới

### Bước 1: Khảo sát & Lập bản đồ Layer
- Đọc kích thước ảnh gốc (`PIL.Image.size`), phóng to các vùng chi tiết nhỏ (icon, màn hình điện thoại, chữ nhỏ) để nhìn rõ bằng mắt.
- Liệt kê các nhóm Layer cần tách:
  1. `1_Background` (Nền trơn / Gradient / Họa tiết sóng + Khối hình nền).
  2. `2_Objects_&_Photos` (Vật thể chính, Ảnh chụp, Điện thoại, Thẻ tính năng, Logo).
  3. `3_Icons_Vector` (Các icon nhỏ cần độ nét cao).
  4. `4_Texts_Visible_Sharp` (Các lớp chữ sắc nét tách từ ảnh gốc — **để hiển thị mặc định**).
  5. `5_Editable_Texts_Template_Hidden` (Các **Type Layer thật `ag-psd`** để gõ sửa chữ trực tiếp trong Photoshop — **để ẩn mặc định** hoặc kèm `imageData`).

### Bước 2: Tách Vật thể & Vẽ bù Vùng bị Che (*Inpainting*)
- **Nếu có vật thể chồng chéo phức tạp** (VD: xe đè lên đường, tay cầm điện thoại đè lên đuôi xe, thẻ chữ đè lên nền sóng):
  - Dùng `image-generator` (hoặc API Generative Inpainting) tạo ảnh tách riêng từng vật thể trên nền trắng thuần `#FFFFFF` và ảnh nền sạch đã vẽ bù.
  - Khi tách từ nền `#FFFFFF`: **Bắt buộc dùng `floodFill` từ 4 cạnh viền ngoài** để xóa nền trắng bên ngoài, **tuyệt đối không** xóa màu trắng toàn cục (sẽ làm thủng đèn xe, màn hình trắng, mắt, răng...).
- **Nếu tách trực tiếp bằng OpenCV (hoặc khi `image-generator` hết quota 429):**
  - Ước lượng mặt phẳng nền cục bộ (`inpaint` bản thu nhỏ + `GaussianBlur` + so sánh khoảng cách màu trong không gian **LAB**).
  - **Không rải điểm seed flood-fill bừa bãi vào vùng vật thể** (tránh làm thủng capô xe vàng hoặc làm lẹm tay áo tài xế màu xám/xanh). Phải khóa vùng bảo vệ cho người/xe trước khi lọc màu nền.

### Bước 3: Xử lý Icon, Logo & Chữ Đơn Sắc (*Zero Halo / Zero Pixelation*)
- **Khử viền màu nền (*Color Decontamination*):** Với logo hoặc chữ đen trên nền màu (xanh/vàng), sau khi có alpha mask, ép toàn bộ pixel RGB bên trong mask về màu thuần (`#000000`) để loại bỏ 100% quầng xanh/vàng bám ở rìa.
- **Vẽ lại Icon nhỏ bằng Vector (`4× Supersampling`):** Tuyệt đối không phóng to bitmap icon `30×30px` lên Full HD (sẽ bị răng cưa nặng). Phải vẽ lại bằng hình học (hình tròn, bo góc, đường cong Bezier) ở kích thước `4×` rồi thu nhỏ bằng `LANCZOS`.

### Bước 4: Làm nét Full HD (`2×`)
- Ảnh chụp thực tế (nội thất xe, chân dung, sản phẩm): chạy `cv2.bilateralFilter(5, 25, 25)` khử nhiễu nén JPEG → phóng `2×` bằng `INTER_LANCZOS4` → tăng micro-contrast nhẹ bằng `CLAHE (clipLimit=1.5)` pha `45%` → `UnsharpMask(radius=1.3..1.6, percent=130..145)`.
- Nếu trong ảnh có **màn hình điện thoại nhỏ bị mờ** và đã có ảnh gốc màn hình sắc nét: tách thành layer riêng (`03b_Dashboard_Phone_Sharp`) và dùng `cv2.getPerspectiveTransform` ghép phối cảnh 4 góc khớp khít vào khung viền điện thoại.

### Bước 5: Đóng gói `.psd` bằng `ag-psd` (Node.js)
- Dùng `writePsdBuffer` trong `ag-psd` (`channels: 4, bitsPerChannel: 8, colorMode: 3`).
- **Quy tắc hiển thị Text Layer:**
  - Một số trình đọc PSD không tự render `TySh` (Text Layer) nếu thiếu `imageData`, dẫn đến mở file lên thấy bị mất chữ.
  - Vì vậy: **Luôn giữ nhóm chữ gốc sắc nét ở trạng thái hiển thị (`hidden: false`)** để khi mở `.psd` hình hiển thị **giống 100% bản gốc**, và đặt nhóm **Type Layer thật (`text: {...}`)** trong group `5_Editable_Texts_Template_Hidden` (`hidden: true`) để người dùng bật lên gõ sửa khi cần thay nội dung.

### Bước 6: Kiểm duyệt QA 2 Tầng (BẮT BUỘC trước khi gửi User)
1. **Tầng 1 — Soi từng Layer trên nền ca-rô (`graphic-qa-reviewer`):**
   - Xuất bảng lưới `qa_sheet.png` đặt các layer trên nền ca-rô xám/trắng.
   - Gọi subagent `graphic-qa-reviewer` kiểm tra: không có lỗ hổng chưa fill, không dính mảnh vật thể khác, không quầng halo, không răng cưa, không cắt mất chữ/viền.
   - Layer nào `FAIL` (< 9/10) phải sửa ngay và chấm lại cho tới khi **100% `PASS`**.
2. **Tầng 2 — Ghép ngược Composite 1:1 (`psd_preview_check.png`):**
   - Chạy script ghép toàn bộ các layer có `hidden: false` theo đúng tọa độ `(x, y)` ra 1 ảnh tổng thể.
   - Mở ảnh đó bằng `read_file` đối chiếu trực tiếp với ảnh gốc của người dùng để chắc chắn **không mất chữ, không cắt thiếu đuôi chữ, không sai vị trí, không bị lẹm chi tiết**.

---

## 4. Câu Lệnh Giao Việc cho AI Mới

Khi mở phiên chat mới hoặc chuyển sang AI khác, người dùng chỉ cần nói:
> `"Đọc skill psd-layer-redesign (tại C:\Users\BUM\.gemini\config\skills\psd-layer-redesign\SKILL.md), nhận ảnh mới này và chạy đầy đủ quy trình 6 bước bóc tách Full HD, kiểm duyệt QA 2 tầng rồi xuất file .psd cho tôi."`
