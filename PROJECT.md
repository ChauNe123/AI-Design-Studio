# PROJECT.md — BẢN ĐỒ TRẠNG THÁI TRUNG TÂM (AI DESIGN STUDIO)

> **Cập nhật lần cuối:** `2026-11-25` (Đã đối chiếu trực tiếp với source code thực tế)
> **Thư mục làm việc chính thức (Mới & Độc lập):** `D:\AI_Design_Studio_V2`
> *(Bản gốc đối chiếu giữ nguyên không chỉnh sửa tại `D:\AI_Design_Studio`)*

---

## 1. TỔNG QUAN & MỤC TIÊU DỰ ÁN

**AI Design Studio** là hệ thống Desktop Web-UI chạy cục bộ trên Windows (`100% Offline-capable`), hỗ trợ Designer chuyên nghiệp ở 4 chế độ cốt lõi:
1. **MODE A — Redesign / Decompose (`core/image_analyzer.py`, `core/segmentation_engine.py`, `core/typography_engine.py`):** Phân rã ảnh thiết kế phẳng (PNG/JPG/WebP) thành các layer vật thể độc lập, nền sạch và chữ có thể chỉnh sửa.
2. **MODE B — Academic Layout Generator (`core/generate_engine.py`, `core/knowledge_base.py`):** Sinh bố cục thiết kế đa phương án dựa trên giáo trình chuẩn quốc tế **DVF 2022** (10 phong trào nghệ thuật lịch sử, 6 quy tắc hòa sắc 60-30-10, kiểm soát khoảng trắng âm bản & phân cấp thị giác).
3. **MODE C — Pro Product Retouching (`core/retouch_analyzer.py`):** Phân tích ảnh sản phẩm và tạo cấu trúc **18 Layer không phá hủy** (Frequency Separation, Intrinsic Specular/Shadow Masks, Live Photoshop Adjustment Layers `curv`, `hue2`, `vibA`, `brit`, `colorBalance`, `selectiveColor`).
4. **MODE D — Commercial Banner & Poster Decomposer V1.6.0 (`core/banner_decomposer.py`, `core/poster_decomposer.py`, `core/reconstruction_engine.py`):** Bóc tách sâu ấn phẩm sự kiện/thương mại phức tạp (như Garena Esports Banner, Melbourne Xpress Cabs Poster) với tái tạo nền 2D LaMa ONNX, vẽ bù phần khuất (Amodal Completion), tách rời vật phẩm nguyên tử, giữ khối 3D và gắn hiệu ứng Live Layer Styles (`lmfx`).

---

## 2. TECH STACK & MÔ HÌNH CỤC BỘ

- **Backend & Xử lý ảnh:** Python `3.10–3.15` (`numpy>=2.0.0`, `opencv-python>=4.10.0`, `Pillow>=11.0.0`), HTTP Server nội bộ `http.server` tại `http://127.0.0.1:8788` (`run_studio.py` -> `core/server.py`).
- **Node.js PSD & ONNX Vision Bridge:** Node.js CommonJS/ESM (`ag-psd@^34.2.1`, `@huggingface/transformers@^4.3.2`, `pngjs@^7.0.0`, `tesseract.js@^7.0.0`).
- **Trọng số AI Offline có sẵn trong `models/` (~358 MB):**
  - `models/lama/inpainting_lama_2025jan.onnx`: Mô hình LaMa 2D Inpainting tái tạo nền thực thụ (dùng qua `cv2.dnn` trong `core/reconstruction_engine.py`).
  - `models/hf_cache/briaai/RMBG-1.4`: Tách nền chủ thể alpha matting.
  - `models/hf_cache/Xenova/slimsam-77-uniform`: Phân vùng vật thể theo điểm/hộp (Promptable SAM).
  - `models/hf_cache/Xenova/detr-resnet-50`: Phát hiện vật thể tổng quát (`owlvit-base-patch32` có trên ổ đĩa nhưng chưa nối vào luồng chính).
  - `tessdata` (`vie.traineddata`, `eng.traineddata`) & bộ font Việt hóa `assets/fonts/FZ Poppins-*.ttf`.

---

## 3. KIẾN TRÚC MODULE THỰC TẾ (`20` module trong `core/` + `3` file `ui/`)

| Nhóm | File Code Thực Tế | Vai trò xác minh trong code |
| :--- | :--- | :--- |
| **Core Schema & Bridge** | `core/design_document.py`, `core/psd_bridge.js` | Schema trung tâm `SCHEMA_VERSION = "1.2.0"`; xuất nhị phân `.PSD` qua `ag-psd` hỗ trợ Group, Layer Mask, Clipping Mask, Editable Text (`TySh`), Live Adjustment Layers & `lmfx`. |
| **Decomposers (V1.6.0)** | `core/banner_decomposer.py`, `core/poster_decomposer.py`, `core/reconstruction_engine.py` | Đã nâng cấp lên kiến trúc **V1.6.0**: xóa sạch `np.interp()`, giãn nở mask `17–20px`, hòa trộn LaMa ONNX + 2D Navier-Stokes + khớp hạt nhiễu `_match_background_grain()`, Amodal Completion cho vật thể bị che và dừng ở cổng xuất ảnh kiểm duyệt. |
| **Retouch & Effects** | `core/retouch_analyzer.py`, `core/effects_engine.py` | Phân tách 18 layer retouch chuyên nghiệp + tham số không phá hủy. |
| **Vision, Text & Semantic** | `core/image_analyzer.py`, `core/segmentation_engine.py`, `core/ai_vision_bridge.mjs`, `core/typography_engine.py`, `core/semantic_analyzer.py` | Pipeline tách lớp MODE A, bridge gọi ONNX qua Node.js, OCR chữ song song `OrigFX` + `Editable TySh`, phân tích ngữ nghĩa bố cục. |
| **Mode B & DVF Knowledge** | `core/generate_engine.py`, `core/knowledge_base.py`, `core/reference_analyzer.py`, `knowledge/knowledge_base.json` | Engine sinh thiết kế chuẩn học thuật DVF 2022, 10 style presets lịch sử, 6 hòa sắc tự động. |
| **QA, Server & Security** | `core/qa_engine.py`, `core/server.py`, `core/project_manager.py`, `core/ai_providers.py`, `core/credential_store.py`, `ui/index.html`, `ui/app.js`, `ui/styles.css` | Kiểm định QA 3 tầng, quản lý phiên bản dự án (`autosave` + snapshot), cổng bảo mật `LOCAL_ONLY` mặc định và giao diện Studio. |

---

## 4. TRẠNG THÁI HIỆN TẠI (ĐÃ XÁC MINH TRÊN CODE & FILE XUẤT)

- **Các phần đã hoàn thành & kiểm chứng:**
  - Kiến trúc nền tảng V1.0 → V1.5.1 (Schema `1.2.0`, Mode A/B/C, DVF 2022, Live Adjustment Layers, `ag-psd` binary writer).
  - **Nâng cấp code V1.6.0 (Module 1 → Module 5)** trên 3 file `core/reconstruction_engine.py`, `core/banner_decomposer.py`, `core/poster_decomposer.py`:
    - Garena Banner V1.6.0 đã chạy xuất JSON (`61 layers`, `7 text`, `26 FX`) kèm ảnh kiểm duyệt `exports/visual_audit_sheet.jpg` và `exports/background_cleaned.jpg`.
    - Melbourne Cabs V1.6.0 đã chạy xuất JSON (`39 layers`) kèm ảnh kiểm duyệt `exports/melbourne_visual_audit_sheet.jpg` và `exports/melbourne_background_cleaned.jpg`.
  - Thiết lập Workspace mới độc lập `D:\AI_Design_Studio_V2` kèm hệ thống 5 file Quản lý Trung tâm.
  - **Sửa launcher `launch_studio.bat` (Task #1):** Đã đổi từ đường dẫn cứng `D:\AI_Design_Studio` sang `pushd "%~dp0"` + `python "%~dp0run_studio.py"`, đảm bảo luôn khởi chạy đúng thư mục `D:\AI_Design_Studio_V2` kể cả khi gọi từ working directory khác.
  - **Cập nhật `D-05`, Khóa chặt Offline `LOCAL_ONLY` & Xuất PSD mẫu để QC trong Photoshop (Task #2):**
    - Đã cập nhật `D-05` trong `DECISIONS.md` và `AGENTS.md`: cho phép xuất thẳng `.PSD` để người dùng mở QC trực tiếp bằng Adobe Photoshop (ảnh audit JPG chỉ để xem nhanh, không chặn xuất PSD; giữ nghiêm lệnh cấm AI tự kết luận chất lượng/PASS).
    - Đã khóa `env.allowRemoteModels = false` và chặn tải CDN `tesseract.js` trong `core/ai_vision_bridge.mjs` khi `ai_providers.json` đang ở chế độ `LOCAL_ONLY`.
    - Đã chạy pipeline xuất PSD hiện hành trên project mẫu `projects/melbourne_xpress_cabs`, sinh file `projects/melbourne_xpress_cabs/melbourne_xpress_cabs_studio.psd` (`6,070,373 bytes`, `39 layers`, `6 groups`, `9 text`, `11 FX`, `2 adjustment`).
  - **Chạy thực nghiệm & Sửa lỗi mục tiêu demo `projects/hera_car_rental_v2_baseline` (Task #3 → Task #4):**
    - Đã khử trùng 2 layer xe thành 1 layer xe nguyên vẹn khử viền lem (`03_Hero_Car_Sedan`) + 1 layer bóng đổ gầm xe tách riêng (`02_Car_Contact_Shadow`, `multiply`).
    - Đã tái tạo lại nền `01_Background_Clean.png` xóa sạch vệt bóng đen dưới xe, không còn vệt xám trên trời và bù kết cấu hạt nhựa đường không lặp (organic asphalt quilt).
    - Đã sửa chuẩn nội dung & vùng cắt 3 cặp chữ (`GOING SOMEWHERE?`, `RELY ON OUR CAR RENTAL SERVICE` không còn dính ngón tay, `for a smooth ride` giữ nguyên chữ ký raster gốc + editable text đầy đủ) và xuất lại `hera_car_rental_v2_baseline_studio.psd` (`3,308,430 bytes`, `9 layers`, `4 groups`).
    - Ghi nhận trung thực phạm vi: Logo góc trái trên (`HERA AUTOMOTIVE CENTRE`), bàn tay, 3 khung Polaroid, lá bay và thanh CTA đáy (`>> BOOK NOW | 1800 777 999`) hiện **đang nằm trong nền `01_Background_Clean`**, chưa tách rời thành layer editable trong demo này.

- **Now / Blockers:**
  - **Chờ người dùng mở kiểm tra trực tiếp trong Adobe Photoshop 2024** đối với file vừa sửa: `D:\AI_Design_Studio_V2\projects\hera_car_rental_v2_baseline\hera_car_rental_v2_baseline_studio.psd` (và `projects/melbourne_xpress_cabs/melbourne_xpress_cabs_studio.psd`).
  - Sau khi người dùng QC thực tế trên Photoshop, mới lập kế hoạch nâng cấp pipeline tổng quát (nếu cần tách thêm khối Logo/Badge/Polaroid/CTA cho ảnh bất kỳ).

---

## 5. CÁC VIỆC TIẾP THEO CẦN LÀM (NEXT)

1. **Tiếp nhận phản hồi QC từ người dùng trên Photoshop** đối với file `melbourne_xpress_cabs_studio.psd` (đặc biệt về khả năng sửa chữ `TySh`, độ khớp mask/layer, hiệu ứng `lmfx` và nền tái tạo).
2. **Lập kế hoạch & thử nghiệm nâng cấp pipeline tách layer tổng quát** cho ảnh thiết kế phẳng JPG/PNG bất kỳ (chỉ lên task chi tiết sau khi người dùng hoàn tất QC mẫu ở bước 1; mọi giải pháp như OCR+LaMa hay Open-Vocabulary Detection phải qua thử nghiệm thực tế trước khi kết luận hiệu quả).
3. **Đồng bộ `core/server.py`, rà soát nguồn gốc artifact Garena & chuẩn hóa `PROJECT_DOC_INDEX.md` + chạy lại `tests/run_regression_tests.py`.**

---

## 6. LỖI ĐÃ BIẾT, MÂU THUẪN TÀI LIỆU & HẠNG MỤC CHƯA XÁC MINH

### Lỗi / Điểm tồn đọng nhỏ trong Code:
- `core/server.py`: `/api/system` trả về `"version": "1.5.0"` (comment đầu file ghi `v1.2`), và chưa mở route HTTP riêng cho `core/poster_decomposer.py`.
- `core/banner_decomposer.py` và `core/poster_decomposer.py` hiện chứa nhiều vùng tọa độ/màu sắc chuyên biệt theo mẫu (Garena / Melbourne), chưa phải bộ tách tổng quát cho mọi bố cục thiết kế bất kỳ.
- Garena V1.6.0 `visual_audit_sheet.jpg`: Layer `#40 Sao_4_Canh_04 (69x61)` thực chất là chóp tia sét vàng góc phải trên.

### Mâu thuẫn giữa Tài liệu cũ và Thực tế Code (Xem chi tiết tại `PROJECT_DOC_INDEX.md`):
- `README.md`, `TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md` và `docs/07_CHANGELOG.md` mới cập nhật đến `v1.5.1` và ghi các file `.psd` v1.5.1 là `"QA Pass"`, trong khi `deep_audit_v15_flaws_and_missing_objects.md` đã bác bỏ chất lượng trực quan của v1.5.1 và code thực tế đã lên **V1.6.0**.
- `docs/18_LIMITATIONS_AND_TRUTH_TABLE.md` (viết từ v1.2) ghi chưa có LaMa ONNX cục bộ, nhưng thực tế `models/lama/inpainting_lama_2025jan.onnx` đã được tích hợp và chạy trực tiếp trong `core/reconstruction_engine.py`.

### Hạng mục CHƯA ĐƯỢC XÁC MINH TỰ ĐỘNG (Không được tự nhận là đã kiểm chứng):
- Chưa mở kiểm tra trực tiếp bằng giao diện phần mềm **Adobe Photoshop 2024/2025 GUI** đối với bản V1.6.0 (mới kiểm định cấu trúc binary qua `ag-psd` read-back và ảnh render).
- Chưa chạy lại `tests/run_regression_tests.py` kể từ sau bản sửa code V1.6.0.
- Chưa có bộ kiểm thử tự động E2E trình duyệt (Playwright) cho mọi thao tác kéo thả trên `ui/app.js`.

---

## 7. LIÊN KẾT TÀI LIỆU QUAN TRỌNG NHẤT

- Quy tắc vận hành AI & tiết kiệm token: [AGENTS.md](file:///D:/AI_Design_Studio_V2/AGENTS.md)
- Các quyết định kiến trúc bất biến: [DECISIONS.md](file:///D:/AI_Design_Studio_V2/DECISIONS.md)
- Danh mục toàn bộ tài liệu & cảnh báo lỗi thời: [PROJECT_DOC_INDEX.md](file:///D:/AI_Design_Studio_V2/PROJECT_DOC_INDEX.md)
- Đặc tả kỹ thuật V1.6.0 mới nhất: [BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md](file:///D:/AI_Design_Studio_V2/BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md)
- Nhật ký thực thi công việc: [TASK_LOG.md](file:///D:/AI_Design_Studio_V2/TASK_LOG.md)
