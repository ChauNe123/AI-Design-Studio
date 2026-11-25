# PROJECT_DOC_INDEX.md — DANH MỤC KIỂM KÊ TOÀN BỘ TÀI LIỆU DỰ ÁN

> **Thời điểm kiểm kê:** `2026-11-25 11:20:00 +07:00`
> **Tổng số file Markdown (`.md`) gốc đã kiểm kê:** **`71` file** trên 3 thư mục gốc liên quan:
> - `D:\AI_Design_Studio`: **55 file** (`6` file ở gốc + `27` file trong `docs/` + `9` file trong `backups/v1.0_snapshot/docs/` + `13` file trong `backups/v1.1_snapshot/docs/`)
> - `D:\AI\TESTER`: **12 file** (`8` file ở gốc + `1` file trong `redesign_studio/` + `3` file không liên quan thuộc dự án GoWash)
> - `D:\Test psd`: **4 file** (bản sao đối chiếu của tài liệu phân tích PSD/Retouch)
>
> **Trạng thái tại Workspace mới `D:\AI_Design_Studio_V2`:** Toàn bộ `33` tài liệu cốt lõi của `AI_Design_Studio` + `5` tài liệu chuyên ngành duy nhất từ `D:\AI\TESTER` (được gom sạch vào `docs/external_refs/`) đã có mặt đầy đủ tại `D:\AI_Design_Studio_V2` (loại bỏ `22` bản snapshot v1.0/v1.1 trùng lặp và `3` file rác dự án GoWash).

---

## 1. TÀI LIỆU TRỌNG YẾU CẦN ƯU TIÊN THAM KHẢO (CRITICAL DOCS)

Khi làm việc trên `D:\AI_Design_Studio_V2`, sau khi đọc `AGENTS.md` và `PROJECT.md`, đây là **8 tài liệu gốc quan trọng nhất** chứa đặc tả nghiệp vụ và kiến trúc sâu khi cần tra cứu theo từng module:

1. **`BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md`** — Đặc tả chuẩn V1.6.0 mới nhất (5 Module chống lỗi xóa nền, Amodal Completion, tách rời vật phẩm, giữ khối 3D và cổng chờ duyệt mắt).
2. **`deep_audit_v15_flaws_and_missing_objects.md`** — Bằng chứng kiểm toán trực quan chỉ rõ các lỗi thực tế của bản v1.5.1 cần tránh lặp lại.
3. **`docs/external_refs/garena_banner_decomposition_analysis.md`** — Giải phẫu file PSD gốc `Banner Công bố.psd` của Designer Garena (cơ sở nghiệp vụ của `core/banner_decomposer.py`).
4. **`docs/external_refs/melbourne_psd_deep_audit.md`** — Giải phẫu & tiêu chuẩn bóc tách 6 nhóm cho poster thương mại `Melbourne Xpress Cabs` (cơ sở của `core/poster_decomposer.py`).
5. **`docs/external_refs/retouch_layer_logic_analysis.md`** & **`AI_RETOUCH_UPGRADE_MASTER_PROMPT.md`** — Giải phẫu 18 layer Retouch lon nước chuyên nghiệp & đặc tả nâng cấp `core/retouch_analyzer.py`.
6. **`docs/03_DESIGN_KNOWLEDGE.md`** & **`docs/external_refs/DVF_2022_GIAO_TRINH_VIET_HOA_CHI_TIET.md`** — Hệ thống tri thức học thuật DVF 2022 cho `core/generate_engine.py` và `core/qa_engine.py`.
7. **`docs/10_V12_ARCHITECTURE.md`** — Kiến trúc tổng thể Python + Node ONNX Bridge và cấu trúc `DesignDocument v1.2.0`.
8. **`docs/20_MODELS_AND_UPGRADES.md`** — Danh mục các mô hình ONNX cục bộ và bộ font `FZ Poppins`.

---

## 2. CÁC TÀI LIỆU CÓ DẤU HIỆU MÂU THUẪN VỚI SOURCE CODE THỰC TẾ (VERIFIED CONFLICTS)

*(Đã xác minh bằng cách đọc trực tiếp source code, không kết luận cảm tính dựa trên ngày sửa file)*

1. **Mâu thuẫn phiên bản & trạng thái `.PSD` giữa `README.md` / `TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md` / `docs/07_CHANGELOG.md` so với Code V1.6.0 & `deep_audit_v15_flaws_and_missing_objects.md`:**
   - Ba file tổng hợp trên dừng ở mốc `v1.5.1` (tựa đề `TONG_HOP_UPDATE...` thậm chí còn ghi chữ `(v1.0.0)` ở dòng 1 dù nội dung có mục 9 là `v1.5.1`) và ghi nhận các bản xuất `.PSD` `39 layers` là `"QA Pass"`.
   - Thực tế: `deep_audit_v15_flaws_and_missing_objects.md` đã chứng minh bản `v1.5.1` bị sọc nền do `np.interp()` và thủng lỗ vật thể; đồng thời source code `core/reconstruction_engine.py`, `core/banner_decomposer.py` (`61 layers`), `core/poster_decomposer.py` (`39 layers`) **đã được nâng cấp lên V1.6.0** và đang dừng chờ duyệt ảnh `exports/*visual_audit_sheet.jpg`.
2. **Mâu thuẫn giữa Quy tắc Module 5 trong `BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md` và `core/server.py`:**
   - Đặc tả V1.6.0 cấm tự động đóng gói `.PSD` trước khi người dùng duyệt ảnh `visual_audit_sheet.jpg`. Hàm Python CLI đã tuân thủ, nhưng các HTTP route trong `core/server.py` (`/api/redesign`, `/api/retouch`, `/api/banner_decompose` ở dòng `401, 438, 481`) vẫn gọi thẳng `export_and_qa_all()` xuất `.PSD` ngay lập tức, và `/api/system` vẫn trả `"version": "1.5.0"`.
3. **Mâu thuẫn trạng thái mô hình LaMa ONNX trong `docs/18_LIMITATIONS_AND_TRUTH_TABLE.md` và `docs/14_NON_DESTRUCTIVE_EDITING.md`:**
   - Tài liệu `18_LIMITATIONS_AND_TRUTH_TABLE.md` (viết ở v1.2) ghi rằng hệ thống chưa tích hợp LaMa ONNX cục bộ mà chỉ dùng OpenCV Telea/NS và đề xuất LaMa cho V1.3.
   - Thực tế code: `models/lama/inpainting_lama_2025jan.onnx` đã có mặt và đang chạy suy luận 2D trực tiếp qua `cv2.dnn.readNetFromONNX` trong `core/reconstruction_engine.py`.
4. **Trùng số thứ tự đầu mục `10..13` trong thư mục `docs/`:**
   - Do giữ song song tài liệu từ đợt `v1.1` và `v1.2`, trong `docs/` tồn tại 4 cặp file trùng tiền tố số (`10_FEATURE_ACCEPTANCE_TESTS.md` vs `10_V12_ARCHITECTURE.md`; `11_PSD_COMPATIBILITY_REPORT.md` vs `11_SEMANTIC_ENGINE.md`; `12_PROJECT_MANAGEMENT.md` vs `12_SEGMENTATION_PIPELINE.md`; `13_DESIGN_GENERATION_BENCHMARK.md` vs `13_EDITABLE_TYPOGRAPHY.md`). Nội dung không trùng nhau nhưng tiền tố số bị lặp.
5. **Xung đột nghiêm trọng file `AGENTS.md` tại thư mục cũ `D:\AI\TESTER`:**
   - `D:\AI\TESTER\AGENTS.md` (`34,511B`), `D:\AI\TESTER\TESTER\AGENTS.md` và `D:\AI\TESTER\TESTER\handover.md` thực chất là tài liệu bàn giao hệ thống kiểm toán biển số rửa xe **GoWash (`gowash.kbtech.vn`)** trên macOS Chrome, hoàn toàn không phải quy tắc của dự án AI Design Studio. Việc chuyển sang workspace mới `D:\AI_Design_Studio_V2` đã triệt tiêu hoàn toàn xung đột này.

---

## 3. DANH SÁCH PHÂN LOẠI ĐẦY ĐỦ 71 FILE MARKDOWN THEO NHÓM (A → K)

> **Quy ước ký hiệu cột đường dẫn:**
> - `[Studio]` = `D:\AI_Design_Studio\` (đồng thời có mặt tương ứng tại `D:\AI_Design_Studio_V2\`, trừ thư mục `backups/`)
> - `[TESTER]` = `D:\AI\TESTER\` (các bản duy nhất đã được chép sang `D:\AI_Design_Studio_V2\docs\external_refs\`)
> - `[TestPSD]` = `D:\Test psd\`

### Nhóm A. Project Rules (Quy tắc Vận hành) — `1 file gốc` *(và 2 file dự án khác ở Nhóm K)*
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 65 | `[TESTER] redesign_studio\SKILL_PSD_REDESIGN_HANDOVER.md`<br>*(V2: `docs/external_refs/SKILL_PSD_REDESIGN_HANDOVER.md`)* | `# 🎨 PSD Layer Redesign & Decomposition — Master Skill & Handover` — Quy trình chuẩn 6 bước bóc tách ảnh, vẽ bù, QA 2 tầng của thế hệ tiền nhiệm `redesign_studio`. | Tiền thân của `core/image_analyzer.py` & `core/qa_engine.py` | Nội dung tương tự skill global `psd-layer-redesign` | **Có (Một phần):** Các tên script cũ (`decompose_deep.py`, `process_canva.py`) đã được thay bằng kiến trúc `core/` hiện tại, nhưng triết lý QA 2 tầng vẫn còn giá trị. | Không có file `.md` nào khác trỏ tới | Trung bình |

### Nhóm B. Project Overview (Tổng quan Dự án) — `1 file`
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 03 | `[Studio] README.md` | `# AI Design Studio v1.5.1 🎨✨` — Tổng quan 4 chế độ của hệ thống, cấu trúc thư mục, danh sách file `.psd` mẫu và hướng dẫn cài đặt trên máy cá nhân. | Toàn dự án (`run_studio.py`, `core/*`) | Không | **Có (Nhẹ):** Dừng ở `v1.5.1`, chưa ghi nhận đợt nâng cấp code V1.6.0 và cổng chờ duyệt mắt. | Không | **Có** |

### Nhóm C. Current Progress (Tiến độ & Đối chiếu Trạng thái) — `2 file`
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 04 | `[Studio] TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md` | `# TỔNG HỢP TOÀN BỘ NỘI DUNG ĐÃ UPDATE — AI DESIGN STUDIO (v1.0.0)` — Báo cáo tích lũy tiến độ xuyên suốt từ v1.0 → v1.3 → v1.4 → v1.5.0 → v1.5.1. | Toàn bộ `core/`, `ui/`, `tests/` | Không | **Có (Một phần):** Tiêu đề dòng 1 còn sót chữ `(v1.0.0)`, nội dung dừng ở `v1.5.1` trước khi kiểm toán lỗi V1.6.0. | `deep_audit_v15_flaws...md`, `docs/AI_PHOTOSHOP_UPDATE_PROMPT.md` | Trung bình |
| 50 | `[Studio] docs\18_LIMITATIONS_AND_TRUTH_TABLE.md` | `# SYSTEM LIMITATIONS & HONEST STATUS MATRIX (V1.2)` — Bảng đối chiếu trung thực những gì làm được và giới hạn kỹ thuật ở thời điểm v1.2. | `core/server.py`, `core/reconstruction_engine.py`, `ui/app.js` | Không | **Có (Đã xác minh code):** Ghi chưa có LaMa ONNX, thực tế V1.6.0 đã chạy `inpainting_lama_2025jan.onnx`. | Không | Trung bình |

### Nhóm D. Architecture & Technical Documentation (Kiến trúc & Kỹ thuật) — `16 file`
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 30 | `[Studio] docs\02_ARCHITECTURE.md` | `# 02 — ARCHITECTURE (v1.1)` — Sơ đồ cấu trúc thư mục và luồng dữ liệu an toàn giai đoạn v1.1. | `core/design_document.py`, `core/project_manager.py` | Trùng 100% với `[17] backups/v1.1_snapshot/...` | **Có:** Đã được mở rộng bởi `10_V12_ARCHITECTURE.md` và các engine v1.4–v1.6. | `TONG_HOP_UPDATE...md` | Thấp |
| 37 | `[Studio] docs\09_RECOVERY_GUIDE.md` | `# 09 — RECOVERY GUIDE` — Hướng dẫn chạy lại Studio và khôi phục bản sao lưu v1.0/v1.1. | `run_studio.py`, `tests/run_regression_tests.py` | Trùng 100% với `[15]`, `[24]` | **Có:** Được thay thế chi tiết hơn bởi `19_DEPLOYMENT_AND_RECOVERY.md`. | `TONG_HOP_UPDATE...md` | Thấp |
| 39 | `[Studio] docs\10_V12_ARCHITECTURE.md` | `# AI DESIGN STUDIO V1.2 — ARCHITECTURE` — Kiến trúc Hybrid Python + Node ONNX Bridge và đặc tả Schema `DesignDocument 1.2.0`. | `core/design_document.py`, `core/ai_vision_bridge.mjs`, `core/psd_bridge.js` | Trùng số `10_` với file `[38]` | **Không** (Schema `1.2.0` vẫn là chuẩn cốt lõi hiện hành; chỉ thêm các decomposer mới). | Không | **Có** |
| 41 | `[Studio] docs\11_SEMANTIC_ENGINE.md` | `# SEMANTIC DESIGN ANALYZER` — Pipeline 7 bước phân tích ngữ nghĩa bố cục và độ tin cậy. | `core/semantic_analyzer.py` | Trùng số `11_` với file `[40]` | **Không** | Không | Trung bình |
| 42 | `[Studio] docs\12_PROJECT_MANAGEMENT.md` | `# 12 — PROJECT MANAGEMENT SPECIFICATION (v1.1)` — Cơ chế lưu nháp `autosave_draft.json` và lịch sử phiên bản `versions/vNNN.json`. | `core/project_manager.py` | Trùng 100% với `[27]`; trùng số `12_` với `[43]` | **Không** (Code `project_manager.py` vẫn giữ đúng cơ chế này). | Không | Trung bình |
| 43 | `[Studio] docs\12_SEGMENTATION_PIPELINE.md` | `# ADVANCED OBJECT SEGMENTATION PIPELINE` — Kiến trúc đa phương thức `RMBG-1.4` + `SlimSAM` + `DETR` và tách vật thể không chồng lấn. | `core/segmentation_engine.py`, `core/ai_vision_bridge.mjs` | Trùng số `12_` với file `[42]` | **Không** | Không | **Có** |
| 45 | `[Studio] docs\13_EDITABLE_TYPOGRAPHY.md` | `# EDITABLE TYPOGRAPHY ENGINE` — Quy trình OCR khôi phục chữ có thể sửa (`TySh`) và đo màu/cỡ chữ. | `core/typography_engine.py`, `core/psd_bridge.js` | Trùng số `13_` với file `[44]` | **Không** | Không | **Có** |
| 46 | `[Studio] docs\14_NON_DESTRUCTIVE_EDITING.md` | `# NON-DESTRUCTIVE EDITING WORKFLOW` — Tham số chỉnh sửa không phá hủy và gắn nhãn nguồn gốc pixel tái tạo. | `core/effects_engine.py`, `core/reconstruction_engine.py`, `ui/app.js` | Không | **Có (Nhẹ):** Phần mô tả `reconstruction_engine.py` viết trước khi nâng cấp LaMa 2D V1.6.0. | Không | Trung bình |
| 47 | `[Studio] docs\15_HYBRID_AI_AND_PRIVACY.md` | `# HYBRID AI ENGINE & PRIVACY GOVERNANCE` — Chính sách `LOCAL_ONLY`, cổng xác nhận `HYBRID` và nhật ký `api_usage_log.json`. | `core/ai_providers.py` | Không | **Không** | Không | Trung bình |
| 48 | `[Studio] docs\16_SECURITY_AND_CREDENTIALS.md` | `# SECURITY & CREDENTIAL STORAGE` — Lưu khóa trên Windows Credential Manager, che giấu khóa (masking) và kiểm tra input. | `core/credential_store.py` | Không | **Không** | Không | Trung bình |
| 51 | `[Studio] docs\19_DEPLOYMENT_AND_RECOVERY.md` | `# DEPLOYMENT, OPERATIONS & RECOVERY GUIDE (V1.2)` — Hướng dẫn khởi chạy hệ thống, cấu trúc model cục bộ và quy trình kiểm thử. | `run_studio.py`, `models/`, `tests/` | Không | **Có (Nhẹ):** Có nhắc tên `app.py` trong ví dụ trong khi file thực tế là `run_studio.py`. | Không | Trung bình |
| 52 | `[Studio] docs\20_MODELS_AND_UPGRADES.md` | `# AI DESIGN STUDIO — MODEL REGISTRY & UPGRADE LOG` — Sổ đăng ký mô hình ONNX offline đang hoạt động và bộ font `FZ Poppins`. | `models/`, `assets/fonts/`, `core/segmentation_engine.py` | Không | **Có (Nhẹ):** Chưa liệt kê thêm file `models/lama/inpainting_lama_2025jan.onnx` mới nạp sau này. | `docs/10_V12_ARCHITECTURE.md` | **Có** |
| 53 | `[Studio] docs\21_RETOUCH_LIGHTING_ENGINE.md` | `# 21 — PRO PRODUCT RETOUCHING & INTRINSIC LIGHTING ENGINE (v1.4.0)` — Kiến trúc 4 khối phân tách ánh sáng nội tại và xuất 18 layer PSD Retouch. | `core/retouch_analyzer.py`, `core/psd_bridge.js`, `core/qa_engine.py` | Không | **Không** | `TONG_HOP_UPDATE...md` | **Có** |
| 54 | `[Studio] docs\22_GARENA_BANNER_DECOMPOSER.md` | `# 22 — GARENA ESPORTS BANNER 5-MODULE DECOMPOSITION & LAYERFX ENGINE (v1.5.0)` — Kiến trúc 5 module phân rã banner sự kiện và nâng cấp mặt nạ tổ ong Retouch. | `core/banner_decomposer.py`, `core/psd_bridge.js`, `core/retouch_analyzer.py` | Không | **Có (Một phần):** Kiến trúc 5 module vẫn giữ nhưng thuật toán xóa nền và tách vật phẩm trong code đã nâng cấp lên V1.6.0 (`61 layers`). | `docs/07_CHANGELOG.md`, `TONG_HOP_UPDATE...md` | **Có** |

### Nhóm E. Business Logic & Domain Knowledge (Nghiệp vụ Thiết kế & Phân tích Mẫu Chuẩn) — `6 file` *(4 tài liệu gốc + 2 bản sao)*
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 31 | `[Studio] docs\03_DESIGN_KNOWLEDGE.md` | `# 03 — DESIGN KNOWLEDGE BASE (DVF 2022 INTEGRATED)` — Tài liệu kiến trúc tri thức thiết kế V1.3 tích hợp giáo trình DVF 2022 và QA 3 cấp độ. | `core/knowledge_base.py`, `knowledge/knowledge_base.json`, `core/generate_engine.py`, `core/qa_engine.py` | Không (bản v1.3 khác hẳn bản v1.0/v1.1 cũ) | **Không** | `TONG_HOP_UPDATE...md`, `docs/AI_PHOTOSHOP_UPDATE_PROMPT.md` | **Có** |
| 59 | `[TESTER] DVF_2022_GIAO_TRINH_VIET_HOA_CHI_TIET.md`<br>*(V2: `docs/external_refs/DVF_2022_GIAO_TRINH_VIET_HOA_CHI_TIET.md`)* | `# 🎨 GIÁO TRÌNH CƠ SỞ THIẾT KẾ & THỊ GIÁC TOÀN TẬP (DVF 2022)` — Giáo trình Việt hóa chi tiết 7 yếu tố thị giác, 12 nguyên lý thiết kế, 10 phong trào lịch sử. | Nguồn học thuật gốc của `knowledge/knowledge_base.json` | Không | **Không** (Tài liệu nền tảng học thuật bất biến). | Gián tiếp qua `docs/03_DESIGN_KNOWLEDGE.md` | **Có** |
| 62 | `[TESTER] garena_banner_decomposition_analysis.md`<br>*(V2: `docs/external_refs/garena_banner_decomposition_analysis.md`)* | `# 🏆 Phân Tích Chuyên Sâu Tệp Banner Công bố.psd (Garena)` — Giải phẫu chi tiết từng group, blend mode, layer mask và hiệu ứng của file PSD Garena gốc. | `core/banner_decomposer.py`, `core/psd_bridge.js` | Trùng 100% byte-for-byte với `[70]` | **Không** (Tài liệu chuẩn đối chiếu thiết kế gốc). | `docs/22_GARENA_BANNER_DECOMPOSER.md` | **Có** |
| 70 | `[TestPSD] garena_banner_decomposition_analysis.md` | Bản sao y hệt 100% (`12,399B`) của file `[62]` nằm tại `D:\Test psd`. | `core/banner_decomposer.py` | **Trùng 100% với `[62]`** | **Không** | `docs/22_GARENA_BANNER_DECOMPOSER.md` | Bản sao |
| 64 | `[TESTER] retouch_layer_logic_analysis.md`<br>*(V2: `docs/external_refs/retouch_layer_logic_analysis.md`)* | `# 🔬 Phân Tích Chuyên Sâu Tệp Retouch Lon Nước (.tif)` — Giải phẫu 18 layer & mask thực tế của Pro Retoucher (Before vs After). | `core/retouch_analyzer.py`, `core/psd_bridge.js` | Trùng 100% byte-for-byte với `[71]` | **Không** (Tài liệu chuẩn nghiệp vụ Retouch). | `docs/07_CHANGELOG.md`, `docs/21_RETOUCH_LIGHTING_ENGINE.md` | **Có** |
| 71 | `[TestPSD] retouch_layer_logic_analysis.md` | Bản sao y hệt 100% (`10,697B`) của file `[64]` nằm tại `D:\Test psd`. | `core/retouch_analyzer.py` | **Trùng 100% với `[64]`** | **Không** | Như `[64]` | Bản sao |

### Nhóm F. Requirements & Upgrade Specifications (Yêu cầu & Đặc tả Nâng cấp) — `8 file` *(5 tài liệu gốc + 3 bản sao)*
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 02 | `[Studio] BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md` | `# 🛡️ BẢN ĐẶC TẢ NÂNG CẤP TOÀN DIỆN v1.6.0: ZERO-DEFECT ARCHITECTURE OVERHAUL` — Bảng "Lỗi Đỏ" nghiêm cấm, kiến trúc 5 module V1.6.0 và quy trình phối hợp duyệt bằng mắt trước khi xuất PSD. | `core/reconstruction_engine.py`, `core/banner_decomposer.py`, `core/poster_decomposer.py`, `core/psd_bridge.js`, `core/server.py` | Trùng 100% với `[58]` | **Không (Mới nhất & Đang hiệu lực).** | Không | **Cực kỳ quan trọng** |
| 58 | `[TESTER] BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md` | Bản sao y hệt 100% (`13,191B`) của file `[02]` tại `D:\AI\TESTER`. | Như `[02]` | **Trùng 100% với `[02]`** | Không | Không | Bản sao |
| 01 | `[Studio] AI_RETOUCH_UPGRADE_MASTER_PROMPT.md` | `# 🚀 MASTER PROMPT & HƯỚNG DẪN TRIỂN KHAI NÂNG CẤP HỆ THỐNG RETOUCH` — Đặc tả kỹ thuật nâng cấp `retouch_analyzer.py` lên chuẩn Pro Retouch (mặt nạ lục giác tổ ong, specular, live adjustments). | `core/retouch_analyzer.py` | Trùng 100% với `[57]` và `[68]` | **Không** (Đã triển khai vào code v1.5.0, vẫn dùng để đối chiếu chuẩn Retouch). | Không | **Có** |
| 57 | `[TESTER] AI_RETOUCH_UPGRADE_MASTER_PROMPT.md` | Bản sao y hệt 100% (`13,050B`) của file `[01]` tại `D:\AI\TESTER`. | `core/retouch_analyzer.py` | **Trùng 100% với `[01]`, `[68]`** | Không | Không | Bản sao |
| 68 | `[TestPSD] AI_RETOUCH_UPGRADE_MASTER_PROMPT.md` | Bản sao y hệt 100% (`13,050B`) của file `[01]` tại `D:\Test psd`. | `core/retouch_analyzer.py` | **Trùng 100% với `[01]`, `[57]`** | Không | Không | Bản sao |
| 55 | `[Studio] docs\AI_PHOTOSHOP_UPDATE_PROMPT.md` | `# 🚀 PROMPT NÂNG CẤP DỰ ÁN AI DESIGN STUDIO (CHO AI PHOTOSHOP)` — Bản yêu cầu triển khai nâng cấp V1.3 tích hợp DVF 2022. | `core/generate_engine.py`, `core/qa_engine.py`, `ui/app.js` | Không | **Có (Đã hoàn thành từ v1.3):** Chỉ giữ làm tư liệu đối chiếu yêu cầu cũ. | Không | Thấp |
| 34 | `[Studio] docs\06_USER_REQUIREMENTS.md` | `# 06 — USER REQUIREMENTS` — Tóm tắt ngắn 8 dòng yêu cầu ban đầu thời v1.0. | Toàn dự án | Trùng 100% với `[12]`, `[21]` | **Có:** Quá sơ lược so với yêu cầu V1.3–V1.6 hiện tại. | `TONG_HOP_UPDATE...md` | Thấp |
| 32 | `[Studio] docs\04_DEVELOPMENT_ROADMAP.md` | `# 04 — DEVELOPMENT ROADMAP` — Lộ trình đề xuất từ thời v1.0. | Toàn dự án | Trùng 100% với `[10]`, `[19]` | **Có:** Hầu hết lộ trình v1.0 đã được triển khai vượt xa ở v1.2–v1.6. | `TONG_HOP_UPDATE...md` | Thấp |

### Nhóm G. Decisions (Quyết định Kiến trúc) — `0 file trước kiểm kê`
*(Trước đợt thiết lập này dự án chưa có file `DECISIONS.md` riêng; các quyết định nằm rải rác trong `BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md`, `docs/15_HYBRID_AI_AND_PRIVACY.md` và `docs/10_V12_ARCHITECTURE.md`. Nay đã được tập hợp chuẩn xác tại `DECISIONS.md`).*

### Nhóm H. Task History & Changelog (Lịch sử Thay đổi) — `1 file chính` *(+ 2 snapshot ở Nhóm J)*
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 35 | `[Studio] docs\07_CHANGELOG.md` | `# 07 — CHANGELOG` — Nhật ký phiên bản từ `v1.0.0` (18/11) đến `v1.5.1` (20/11). | Toàn dự án | Bản gốc mới hơn `[13]`, `[22]` | **Có (Thiếu mốc mới nhất):** Chưa ghi nhận đợt nâng cấp code V1.6.0 và đợt tạo Workspace V2 ngày 25/11 (nay đã ghi tại `TASK_LOG.md`). | `TONG_HOP_UPDATE...md`, `deep_audit_v15...md`, `docs/AI_PHOTOSHOP_UPDATE_PROMPT.md` | Trung bình |

### Nhóm I. Testing, Deep Audits & Troubleshooting (Kiểm thử, Kiểm toán Lỗi & Khắc phục) — `13 file` *(10 file gốc + 3 bản sao)*
| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung chính | Module liên quan | Trùng lặp? | Khả năng lỗi thời? | Được tham chiếu bởi | Quan trọng? |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| 06 | `[Studio] deep_audit_v15_flaws_and_missing_objects.md` | `# 🚨 Báo Cáo Đối Soát Chuyên Sâu: Thực Trạng Bản Cập Nhật v1.5.1 & Các Lỗi Nặng` — Chỉ rõ lỗi bệt sọc `np.interp`, thủng vành nón kết, nát vòng tay, dính chùm giải thưởng ở v1.5.1. | `core/reconstruction_engine.py`, `core/banner_decomposer.py`, `core/poster_decomposer.py` | Trùng 100% với `[61]` | **Không** (Tài liệu kiểm toán trực quan cực kỳ quan trọng dẫn tới V1.6.0). | Không | **Có** |
| 61 | `[TESTER] deep_audit_v15_flaws_and_missing_objects.md` | Bản sao y hệt 100% (`11,724B`) của file `[06]` tại `D:\AI\TESTER`. | Như `[06]` | **Trùng 100% với `[06]`** | Không | Không | Bản sao |
| 63 | `[TESTER] melbourne_psd_deep_audit.md`<br>*(V2: `docs/external_refs/melbourne_psd_deep_audit.md`)* | `# 🔍 Báo Cáo Giải Phẫu & Đánh Giá Toàn Diện File PSD: Melbourne_Xpress_Cabs_Editable_FullLayers.psd` — Đánh giá cấu trúc 6 group và chỉ ra các lỗi biên mask, mặt đường dưới gầm xe, khung vòng quay Ferris wheel. | `core/poster_decomposer.py`, `core/psd_bridge.js` | Không | **Không** (Chuẩn đối chiếu kiểm định cho bài toán Commercial Poster). | Không | **Có** |
| 05 | `[Studio] ai_vs_pro_retouch_deep_audit.md` | `# 🔍 Báo Cáo Kiểm Toán & Đối Chiếu: AI_Design_Studio vs Pro Designer Trong Giới Retouch` — Phân tích 4 điểm yếu của bản Retouch v1.4 so với Pro Designer và lộ trình sửa ở v1.5. | `core/retouch_analyzer.py`, `core/psd_bridge.js` | Trùng 100% với `[60]` và `[69]` | **Không** (Tư liệu kiểm định chất lượng Retouch). | `docs/22_GARENA_BANNER_DECOMPOSER.md` | **Có** |
| 60 | `[TESTER] ai_vs_pro_retouch_deep_audit.md` | Bản sao y hệt 100% (`9,339B`) của file `[05]` tại `D:\AI\TESTER`. | `core/retouch_analyzer.py` | **Trùng 100% với `[05]`, `[69]`** | Không | Không | Bản sao |
| 69 | `[TestPSD] ai_vs_pro_retouch_deep_audit.md` | Bản sao y hệt 100% (`9,339B`) của file `[05]` tại `D:\Test psd`. | `core/retouch_analyzer.py` | **Trùng 100% với `[05]`, `[60]`** | Không | Không | Bản sao |
| 49 | `[Studio] docs\17_TESTING_AND_QA_REPORT.md` | `# V1.2 TESTING & QA REPORT` — Kết quả chạy `run_v1_2_tests.py`, kiểm thử Grab Poster và ghi chú trung thực về việc kiểm tra Photoshop 2024. | `tests/run_v1_2_tests.py`, `tests/run_regression_tests.py` | Không | **Có (Một phần):** Phản ánh kết quả kiểm thử thời điểm v1.2. | Không | Trung bình |
| 29 | `[Studio] docs\01_SYSTEM_AUDIT.md` | `# 01 — SYSTEM AUDIT REPORT (v1.0 AUDIT → v1.1 VERIFIED)` — Kiểm toán hệ thống giai đoạn v1.0 lên v1.1. | `core/*` (v1.1) | Trùng 100% với `[16]` | **Có:** Lịch sử kiểm toán giai đoạn đầu v1.1. | `TONG_HOP_UPDATE...md` | Thấp |
| 33 | `[Studio] docs\05_TEST_REPORT.md` | `# 05 — TEST REPORT (v1.1)` — Báo cáo `9/9` regression và `5/5` acceptance thời điểm v1.1. | `tests/run_regression_tests.py` | Trùng 100% với `[20]` | **Có:** Đã có các báo cáo mới hơn (`17_TESTING...` và audit v1.5/v1.6). | `TONG_HOP_UPDATE...md` | Thấp |
| 36 | `[Studio] docs\08_KNOWN_ISSUES.md` | `# 08 — KNOWN ISSUES & LIMITATIONS (v1.1)` — 10 dòng ghi nhận giới hạn thời v1.1. | `ui/app.js` | Trùng 100% với `[23]` | **Có:** Quá cũ (từ v1.1). | `TONG_HOP_UPDATE...md` | Thấp |
| 38 | `[Studio] docs\10_FEATURE_ACCEPTANCE_TESTS.md` | `# 10 — FEATURE ACCEPTANCE TESTS (v1.1)` — Kết quả kiểm thử nghiệm thu tính năng v1.1. | `tests/run_v1_1_acceptance_tests.py` | Trùng 100% với `[25]`; trùng số `10_` với `[39]` | **Có (Lịch sử v1.1)** | Không | Thấp |
| 40 | `[Studio] docs\11_PSD_COMPATIBILITY_REPORT.md` | `# 11 — PSD COMPATIBILITY REPORT (v1.1)` — Phương pháp kiểm định tương thích file PSD ở v1.1. | `core/psd_bridge.js` | Trùng 100% với `[26]`; trùng số `11_` với `[41]` | **Có:** `psd_bridge.js` nay đã hỗ trợ thêm Live Adjustment Layers và `lmfx` ở v1.4–v1.5. | Không | Thấp |
| 44 | `[Studio] docs\13_DESIGN_GENERATION_BENCHMARK.md` | `# 13 — DESIGN GENERATION BENCHMARK (MODE B v1.1)` — Benchmark sinh 3 phương án thiết kế ở v1.1. | `core/generate_engine.py`, `core/reference_analyzer.py` | Trùng 100% với `[28]`; trùng số `13_` với `[45]` | **Có:** `generate_engine.py` đã nâng cấp mạnh lên chuẩn DVF 2022 ở v1.3. | Không | Thấp |

### Nhóm J. Drafts & Historical Documents (Bản sao Lưu trữ Lịch sử `v1.0` & `v1.1`) — `22 file`
*(Toàn bộ 22 file dưới đây nằm trong `D:\AI_Design_Studio\backups\` là bản chụp lịch sử tĩnh của `docs/` thời v1.0 và v1.1. Được giữ nguyên 100% tại `D:\AI_Design_Studio\backups\` và không chép sang `D:\AI_Design_Studio_V2` để tránh nhiễu tìm kiếm).*

| STT Kiểm kê | Đường dẫn tương đối trong `D:\AI_Design_Studio` | Tiêu đề | Ghi chú Trùng lặp & Trạng thái |
| :---: | :--- | :--- | :--- |
| `07` → `15` (`9` file) | `backups\v1.0_snapshot\docs\01_SYSTEM_AUDIT.md`, `02_ARCHITECTURE.md`, `03_DESIGN_KNOWLEDGE.md`, `04_DEVELOPMENT_ROADMAP.md`, `05_TEST_REPORT.md`, `06_USER_REQUIREMENTS.md`, `07_CHANGELOG.md`, `08_KNOWN_ISSUES.md`, `09_RECOVERY_GUIDE.md` | Bộ tài liệu `01..09` của Snapshot `v1.0` (`2026-11-18`) | Bản lưu lịch sử `v1.0`; các file `04, 06, 09` trùng hệt với `docs/` hiện tại, các file còn lại đã được nâng cấp ở các bản sau. **Không cần đọc trong phiên mới.** |
| `16` → `28` (`13` file) | `backups\v1.1_snapshot\docs\01_SYSTEM_AUDIT.md` .. `13_DESIGN_GENERATION_BENCHMARK.md` | Bộ tài liệu `01..13` của Snapshot `v1.1` (`2026-11-18`) | Bản lưu lịch sử `v1.1`; `11/13` file trùng byte-for-byte với các file cùng tên đang nằm trong `docs/` (trừ `03_DESIGN_KNOWLEDGE.md` và `07_CHANGELOG.md` đã nâng cấp). **Không cần đọc trong phiên mới.** |

### Nhóm K. Unknown / Unrelated External Project Docs (Tài liệu Không thuộc Dự án AI Design Studio) — `3 file`
*(Phát hiện trong quá trình quét workspace cũ `D:\AI\TESTER` — gây nhiễu `<user_rules>` nếu mở chat từ `D:\AI\TESTER`)*

| # | Tên file & Đường dẫn tương đối | Tiêu đề & Nội dung thực tế | Đánh giá & Cách xử lý an toàn |
| :---: | :--- | :--- | :--- |
| 56 | `[TESTER] AGENTS.md` (`34,511B`, `590L`) | `# 📦 GoWash AI License Plate Audit & Daily Report — Full Handover Package (handover.md)` | **KHÔNG LIÊN QUAN ĐẾN AI DESIGN STUDIO:** Đây là bộ quy tắc kiểm toán biển số xe máy cho chuỗi rửa xe GoWash (`gowash.kbtech.vn`). **Đã giữ nguyên 100% không ghi đè tại `D:\AI\TESTER`**, và **loại bỏ hoàn toàn khỏi `D:\AI_Design_Studio_V2`**. |
| 66 | `[TESTER] TESTER\AGENTS.md` (`34,511B`, `590L`) | Bản sao y hệt 100% của `[56]` trong thư mục con `TESTER\`. | Giữ nguyên tại chỗ cũ, không đưa sang `D:\AI_Design_Studio_V2`. |
| 67 | `[TESTER] TESTER\handover.md` (`34,511B`, `590L`) | Bản gốc `handover.md` y hệt 100% của `[56]` trong thư mục con `TESTER\`. | Giữ nguyên tại chỗ cũ, không đưa sang `D:\AI_Design_Studio_V2`. |

---

## 4. SƠ ĐỒ LIÊN KẾT GIỮA CÁC TÀI LIỆU CHÍNH (DOCUMENT CROSS-LINKS)

- `AGENTS.md` ➔ điều hướng sang `PROJECT.md` ➔ điều hướng sang `DECISIONS.md`, `TASK_LOG.md` và `PROJECT_DOC_INDEX.md`.
- `BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md` ⬅ khắc phục trực tiếp các lỗi nêu trong `deep_audit_v15_flaws_and_missing_objects.md` & `docs/external_refs/melbourne_psd_deep_audit.md`.
- `docs/22_GARENA_BANNER_DECOMPOSER.md` ➔ tham chiếu `docs/external_refs/garena_banner_decomposition_analysis.md` và `ai_vs_pro_retouch_deep_audit.md`.
- `docs/21_RETOUCH_LIGHTING_ENGINE.md` & `AI_RETOUCH_UPGRADE_MASTER_PROMPT.md` ➔ tham chiếu `docs/external_refs/retouch_layer_logic_analysis.md`.
- `docs/03_DESIGN_KNOWLEDGE.md` ➔ hiện thực hóa giáo trình gốc `docs/external_refs/DVF_2022_GIAO_TRINH_VIET_HOA_CHI_TIET.md` vào `knowledge/knowledge_base.json`.
