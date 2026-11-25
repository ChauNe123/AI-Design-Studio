# TASK_LOG.md — NHẬT KÝ CÔNG VIỆC DỰ ÁN (AI DESIGN STUDIO)

> Nhật ký ngắn gọn ghi nhận các mốc thực thi thực tế đã diễn ra để các phiên AI tiếp theo nắm bắt lịch sử mà không cần đọc hội thoại cũ.

---

## [2026-11-25] Task #4 — Sửa Lỗi Mục Tiêu Cho Demo `projects/hera_car_rental_v2_baseline` & Xuất Lại PSD
- **Tóm tắt:** Sửa đúng 5 điểm QC của demo `hera_car_rental_v2_baseline` mà không thêm model mới hay sửa tràn pipeline chung: (1) xóa bỏ layer xe rách trùng lặp `02_Car_02`, hợp nhất thành 1 layer xe duy nhất khử viền lem (`03_Hero_Car_Sedan`) đi kèm 1 layer bóng gầm xe độc lập (`02_Car_Contact_Shadow`, `multiply`); (2) tái tạo lại nền `01_Background_Clean.png` xóa sạch bóng đen dưới xe, làm sạch vệt xám trên bầu trời và ghép hạt nhựa đường ngẫu nhiên không lặp (organic asphalt quilt) giữ độ nét mặt đường; (3) sửa nội dung layer chữ editable thành `"GOING SOMEWHERE?"`, `"RELY ON OUR CAR RENTAL SERVICE"` (cắt bỏ mẩu ngón tay dính bên trái) và `"for a smooth ride"` (giữ nguyên chữ viết tay raster gốc hiển thị mặc định); (4) ghi nhận rõ Logo góc trên trái và thanh CTA đáy (`BOOK NOW | 1800 777 999`) vẫn nằm trong `01_Background_Clean`.
- **File ảnh hưởng:** Các file dữ liệu/layer/PSD trong `projects/hera_car_rental_v2_baseline/` (`design_document.json`, `layers/*`, `masks/*`, `background_cleaned.jpg`, `qa_layers_sheet.png`, `qa_composite.png`, `qa_report.json`, `hera_car_rental_v2_baseline_studio.psd`); cập nhật `PROJECT.md`, `TASK_LOG.md`. (Không sửa file code trong `core/` hay `ui/`).
- **Kết quả kiểm chứng:** Chạy `export_and_qa_all` + `node core/psd_bridge.js verify` (`exit 0`): file `hera_car_rental_v2_baseline_studio.psd` (`3,308,430 bytes`) có `9 layers` thuộc `4 groups`, `3 text layers` khớp chính xác chuỗi chữ mới, `1 masked vehicle layer`, `0` lỗi cấu trúc nhị phân.
- **Trạng thái:** Đã cập nhật `.PSD` & ảnh QA — Bàn giao chờ người dùng kiểm tra trực tiếp trong Adobe Photoshop (chưa tự ghi PASS).

---

## [2026-11-25] Task #3 — Chạy Bóc Tách Layer Thực Tế Ảnh `Hera Automotive Centre` Trên Pipeline Tổng Quát Hiện Hành
- **Tóm tắt:** Chạy luồng tổng quát local (`run_semantic_redesign` + `export_and_qa_all`, không sửa code) cho ảnh thiết kế phẳng mới do người dùng tải lên (`736x736` JPG) và xuất `.PSD` tại `projects/hera_car_rental_v2_baseline/hera_car_rental_v2_baseline_studio.psd` (`9 layers`, `5 groups`, `3,748,078 bytes`).
- **File ảnh hưởng:** Tạo mới thư mục `projects/hera_car_rental_v2_baseline/` (input, layers, masks, `design_document.json`, `qa_layers_sheet.png`, `qa_composite.png`, `hera_car_rental_v2_baseline_studio.psd`); cập nhật `PROJECT.md`, `TASK_LOG.md`.
- **Kết quả kiểm chứng:** Máy đọc ngược nhị phân `ag-psd` hợp lệ (`9/9 layers`), tuy nhiên kiểm tra trực quan `qa_layers_sheet.png` và `01_Background_Clean.png` ghi nhận rõ giới hạn hiện tại của `semantic_analyzer.py`: xe bị tách làm 2 mảnh chồng nhau (`02_Car_02` thiếu nóc/bánh + `03_Foreground_Hero_02` đủ xe), chưa tách riêng Logo góc trái trên / Bàn tay / Khung ảnh Polaroid / Nút `BOOK NOW` + số điện thoại đáy (vẫn dính trên nền), bóng đen dưới gầm xe còn trên nền LaMa, và OCR dòng chữ thảo `"for a smooth ride"` đọc thiếu thành `"for rife"` / dòng `"RELY ON OUR..."` dính góc ngón tay.
- **Trạng thái:** Đã xuất `.PSD` baseline — Chờ người dùng mở kiểm tra trên Photoshop và chỉ định phạm vi nâng cấp pipeline tách layer.

---

## [2026-11-25] Task #2 — Cập nhật `D-05`, Khóa Tải Model Từ Xa (`LOCAL_ONLY`) & Xuất PSD Mẫu Cho Photoshop QC
- **Tóm tắt:** Cập nhật quyết định `D-05` theo Phương án A người dùng chỉ thị (cho phép xuất thẳng `.PSD` để QC trong Photoshop, ảnh audit JPG chỉ để xem nhanh, cấm AI tự kết luận chất lượng/PASS); khóa `env.allowRemoteModels = false` và chặn fallback CDN `jsdelivr` của `tesseract.js` trong `core/ai_vision_bridge.mjs` khi ở `LOCAL_ONLY`; xuất file `.PSD` từ project mẫu có sẵn `projects/melbourne_xpress_cabs`.
- **File ảnh hưởng:** `DECISIONS.md`, `AGENTS.md`, `core/ai_vision_bridge.mjs`, `PROJECT.md`, `TASK_LOG.md` (+ sinh artifact `projects/melbourne_xpress_cabs/melbourne_xpress_cabs_studio.psd`, `qa_composite.png`, `qa_layers_sheet.png`, `qa_report.json` và cập nhật `qa_status` trong `design_document.json`).
- **Kết quả kiểm chứng:** Test gọi OCR ngôn ngữ thiếu (`fra`) và model HuggingFace không có local đều bị chặn ngay lập tức không tải mạng; gọi OCR `vie+eng` và `detr-resnet-50` local chạy thành công; `export_and_qa_all` sinh `melbourne_xpress_cabs_studio.psd` (`6,070,373 bytes`, `39 layers`, `6 groups`, `0` lỗi đọc ngược nhị phân `ag-psd`).
- **Trạng thái:** Đã xuất file `.PSD` mẫu — Chờ người dùng mở kiểm tra trực tiếp trên Adobe Photoshop và chờ QC độc lập.

---

## [2026-11-25] Task #1 — Sửa Launcher `launch_studio.bat` cho Workspace V2
- **Tóm tắt:** Loại bỏ đường dẫn cứng `cd /d "D:\AI_Design_Studio"`, thay bằng `pushd "%~dp0"` và gọi `python "%~dp0run_studio.py"` kèm `popd` + bảo toàn mã thoát (`%ERRORLEVEL%`) để launcher luôn chạy đúng bản `D:\AI_Design_Studio_V2` từ mọi working directory.
- **File ảnh hưởng:** `launch_studio.bat`, `PROJECT.md`, `TASK_LOG.md`.
- **Kết quả kiểm chứng:** Đã kiểm tra nội dung file `.bat`, test phân giải `%~dp0` từ working directory ngoài (`D:\AI\TESTER`) và import dry-run `run_studio` không mở server/trình duyệt (trả đúng `STUDIO_ROOT = D:\AI_Design_Studio_V2`).
- **Trạng thái:** Đã triển khai & bàn giao chờ QC độc lập.

---

## [2026-11-25] Thiết lập Hệ thống Quản lý Trung tâm & Khởi tạo Workspace Độc lập `D:\AI_Design_Studio_V2`
- **Tóm tắt công việc:**
  - Kiểm kê toàn bộ **71 file Markdown (`.md`)** trên cả 3 thư mục liên quan (`D:\AI_Design_Studio`: 55 file, `D:\AI\TESTER`: 12 file, `D:\Test psd`: 4 file) và đối chiếu trực tiếp với toàn bộ 20 module Python/JS trong `core/` để phân loại và phát hiện mâu thuẫn tài liệu.
  - Phát hiện xung đột quan trọng: `D:\AI\TESTER\AGENTS.md` (34,511 bytes) thuộc dự án kiểm toán biển số xe **GoWash**, hoàn toàn không liên quan đến `AI Design Studio` — đã bảo toàn nguyên vẹn 100% không ghi đè.
  - Sao chép độc lập toàn bộ mã nguồn, UI, tài sản font, trọng số mô hình AI Offline (`models/`), thư viện Node (`node_modules/`) và gom thêm 5 tài liệu phân tích chuyên ngành rời rạc bên ngoài vào `D:\AI_Design_Studio_V2\docs\external_refs\`.
  - Khởi tạo bộ 5 file Quản lý Trung tâm chuẩn hóa (`AGENTS.md`, `PROJECT.md`, `DECISIONS.md`, `TASK_LOG.md`, `PROJECT_DOC_INDEX.md`) tại `D:\AI_Design_Studio_V2` (đồng thời bổ sung các file chưa tồn tại tương ứng cho thư mục cũ mà không ghi đè bất kỳ file nào đã có).
- **File ảnh hưởng (chỉ tạo mới, không sửa/xóa file cũ):**
  - Tạo mới thư mục độc lập `D:\AI_Design_Studio_V2\` cùng 5 file trung tâm tại gốc dự án mới.
  - Tạo mới 5 file trung tâm tại `D:\AI_Design_Studio\` (nơi chưa có file nào trong 5 file này).
  - Tạo mới 4 file (`PROJECT.md`, `DECISIONS.md`, `TASK_LOG.md`, `PROJECT_DOC_INDEX.md`) tại `D:\AI\TESTER\` (giữ nguyên `D:\AI\TESTER\AGENTS.md`).
- **Kết quả kiểm tra:** Đã xác minh 0 file cũ bị xóa/ghi đè; kiểm tra import Python `core.server` trên `D:\AI_Design_Studio_V2` thành công.
- **Trạng thái:** **HOÀN THÀNH (DONE)** — Sẵn sàng chuyển sang phiên chat mới tại `D:\AI_Design_Studio_V2`.

---

## [2026-11-20] Cải tổ Chất lượng Thực tế V1.6.0 (Zero-Defect Architecture Overhaul — Module 1 đến Module 5)
- **Tóm tắt công việc:**
  - Xóa bỏ 100% vòng lặp `np.interp()` kéo màu sọc ngang trong tái tạo nền; nâng cấp `core/reconstruction_engine.py` với giãn nở mask elip `17–20px`, 2D Navier-Stokes PDE kết hợp `LaMa 2025jan ONNX` (trộn biên cosine) và đồng bộ hạt nhiễu `_match_background_grain()`.
  - Bổ sung Amodal Completion vẽ bù vùng khuất cho Nón kết, Áo thun, Vòng tay, Cọc xu FC, Dây thẻ, Sóng xanh, Bục vinh quang 3D Isometric trong `core/banner_decomposer.py` và làm sạch viền chữ alpha + khung vòng quay mặt trời trong `core/poster_decomposer.py`.
  - Tách rời nguyên tử từng Móc khóa, Ngôi sao 4 cánh và mảnh Confetti độc lập.
  - Xuất bộ ảnh kiểm duyệt trực quan trên nền ca-rô (`exports/visual_audit_sheet.jpg`, `exports/background_cleaned.jpg`, `exports/melbourne_visual_audit_sheet.jpg`, `exports/melbourne_background_cleaned.jpg`) và dừng tại Cổng Duyệt Bằng Mắt Module 5.
- **File ảnh hưởng:** `core/reconstruction_engine.py`, `core/banner_decomposer.py`, `core/poster_decomposer.py`, `exports/*_audit_sheet.jpg`, `exports/*background_cleaned.jpg`.
- **Kết quả kiểm tra:** Pipeline chạy thành công (`exit 0`): Garena Banner tách `61 layers` (`83.8s`), Melbourne Cabs tách `39 layers` (`21.2s`). Chưa đóng gói `.PSD` V1.6.0 theo đúng lệnh chờ người dùng duyệt mắt.
- **Trạng thái:** **CHỜ NGƯỜI DÙNG DUYỆT MẮT (AWAITING VISUAL APPROVAL)** trước khi đóng gói `.PSD`.

---

## [2026-11-20] Nâng cấp v1.5.0 & Bản vá v1.5.1 (Banner 5-Module & Commercial Poster 6-Group)
- **Tóm tắt công việc:** Xây dựng mới `core/banner_decomposer.py` (dựa trên phân tích `Banner Công bố.psd` của Garena) và `core/poster_decomposer.py` (dựa trên kiểm toán `Melbourne Xpress Cabs`), hỗ trợ cấu trúc Group chuẩn thương mại, `lmfx` Layer Styles, và căn chỉnh tọa độ Layer Mask trong `core/psd_bridge.js`.
- **File ảnh hưởng:** `core/banner_decomposer.py`, `core/poster_decomposer.py`, `core/psd_bridge.js`, `core/retouch_analyzer.py`, `core/server.py`, `docs/22_GARENA_BANNER_DECOMPOSER.md`, `docs/07_CHANGELOG.md`.
- **Kết quả kiểm tra:** Bộ test kỹ thuật v1.5.1 đạt `11/11`, tuy nhiên kiểm toán trực quan sau đó (`deep_audit_v15_flaws_and_missing_objects.md`) phát hiện lỗi sọc nền `np.interp` và thủng vật thể che khuất → dẫn tới đợt cải tổ V1.6.0 ở trên.
- **Trạng thái:** **ĐÃ THAY THẾ BỞI CODE V1.6.0 (SUPERSEDED)**.

---

## [2026-11-19] Nâng cấp v1.3.0 (Giáo trình DVF 2022) & v1.4.0 (Pro Product Retouching 18-Layer)
- **Tóm tắt công việc:**
  - **v1.3.0:** Tích hợp tri thức học thuật *Design & Visual Fundamentals (DVF 2022)* vào `knowledge/knowledge_base.json`, `core/generate_engine.py` (10 phong trào nghệ thuật, 6 hòa sắc 60-30-10, quy tắc 1/3) và `core/qa_engine.py` (kiểm định phân cấp chữ, khoảng trắng âm bản, tương phản WCAG).
  - **v1.4.0:** Xây dựng `core/retouch_analyzer.py` và nâng cấp `core/psd_bridge.js` để xuất file `.PSD` 18 Layer Retouch chuyên nghiệp (Frequency Separation + Live Adjustment Layers + Specular/Honeycomb Masks).
- **File ảnh hưởng:** `knowledge/knowledge_base.json`, `core/knowledge_base.py`, `core/generate_engine.py`, `core/qa_engine.py`, `core/retouch_analyzer.py`, `core/psd_bridge.js`, `ui/index.html`, `ui/app.js`, `docs/03_DESIGN_KNOWLEDGE.md`, `docs/21_RETOUCH_LIGHTING_ENGINE.md`.
- **Kết quả kiểm tra:** Bộ kiểm thử hồi quy `tests/run_regression_tests.py` đạt `11/11 PASS`.
- **Trạng thái:** **HOÀN THÀNH (DONE)**.

---

## [2026-11-18] Xây dựng Nền tảng AI Design Studio v1.0 → v1.2
- **Tóm tắt công việc:** Thiết kế schema trung tâm `DesignDocument v1.2.0`, tích hợp các mô hình ONNX cục bộ (`RMBG-1.4`, `SlimSAM`, `DETR`), OCR `Tesseract.js`, quản lý phiên bản dự án (`project_manager.py`), bảo mật khóa (`credential_store.py`) và Web UI độc lập trên cổng `8788`.
- **File ảnh hưởng:** `run_studio.py`, `core/*`, `ui/*`, `docs/01..20_*.md`, `tests/*`.
- **Kết quả kiểm tra:** Regression v1.1 (`9/9 PASS`), Acceptance v1.1 (`5/5 PASS`), V1.2 Suite (`6/6 PASS`).
- **Trạng thái:** **HOÀN THÀNH (DONE)**.
