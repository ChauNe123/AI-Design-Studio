# TỔNG HỢP TOÀN BỘ NỘI DUNG ĐÃ UPDATE — AI DESIGN STUDIO (v1.0.0)

**Ngày tổng hợp:** 2026-11-18  
**Thư mục dự án độc lập mới:** `D:/AI_Design_Studio/`  
**Bản sao lưu code cũ:** `D:/AI_Design_Studio/backups/legacy_redesign_studio/` *(thư mục gốc `D:/AI/TESTER/redesign_studio/` được giữ nguyên không bị xóa hay ghi đè)*

---

## 1. Những Gì Đã Nâng Cấp (So với Bản Thử Nghiệm Cũ)

| Hạng mục | Trước đây (`TESTER/redesign_studio`) | Sau khi Update (`D:/AI_Design_Studio`) |
| :--- | :--- | :--- |
| **Vị trí dự án** | Nằm chung trong thư mục `TESTER`. | Tách ra thư mục độc lập hoàn toàn trên ổ D (`D:/AI_Design_Studio/`). |
| **Kiến trúc dữ liệu** | Mỗi script dùng 1 file `manifest*.json` khác nhau, thiếu thông số layer chuẩn. | Thống nhất 1 schema trung tâm **`DesignDocument`** (`core/design_document.py`) cho Preview, Editor, QA và PSD Export. |
| **MODE A (Redesign)** | Các script tách ảnh bị fix cứng tọa độ riêng cho từng tấm ảnh (`OneWay`, `SafeDrive`, `Canva`). | Viết lại thành **`core/image_analyzer.py`** tổng quát: chạy được với **mọi ảnh PNG/JPG/WEBP/Canva**, tự ước lượng nền LAB, tách lớp, inpaint nền và đánh dấu `ai_reconstructed`. |
| **MODE B (Generate)** | Chưa có. | Xây mới **`core/generate_engine.py`**: nhận nhiều tài nguyên (sản phẩm gốc giữ nguyên pixel + logo + chữ + kích thước + ngành hàng) → tự tạo nền, ánh sáng `screen`, bóng tiếp xúc `multiply` và text Việt hóa. |
| **Font tiếng Việt** | Font `Poppins` cũ thiếu dấu tiếng Việt (bị ô vuông lỗi ở chữ `Ơ`, `Ả`, `Ớ`). | Đã thay bằng bộ font Việt hóa **`FZ Poppins`** (`assets/fonts/FZ Poppins-*.ttf`) hiển thị đầy đủ 100% dấu tiếng Việt. |
| **Design Knowledge** | Chưa có hệ thống lưu trữ. | Xây mới **`core/knowledge_base.py`** + `knowledge/knowledge_base.json` lưu quy tắc bố cục, màu sắc ngành hàng, brand guideline và bài học QA. |
| **Xuất PSD** | 3 file `build_*.js` trùng lặp; nút tải `.psd` trên web cũ tải file tĩnh không cập nhật chỉnh sửa. | Hợp nhất thành **`core/psd_bridge.js`**: xuất Group, Blend mode, cả pixel `imageData` lẫn `TySh` Text Layer, kèm `export_cache/` để xuất đúng 100% các chỉnh sửa trên UI. |
| **Kiểm duyệt QA** | Kiểm duyệt rời rạc, chưa tự động kiểm tra đủ 3 cấp. | Xây mới **`core/qa_engine.py`**: tự động chạy **QA 1** (soi từng layer + `qa_layers_sheet.png`), **QA 2** (ghép `qa_composite.png` + đo vùng thủng + MAE), **QA 3** (đọc lại cấu trúc `.psd` bằng `ag-psd`). |
| **Giao diện Desktop** | 1 trang `index.html` đơn giản, thiếu nhiều khu vực chức năng. | Hoàn thiện giao diện 9 khu vực (`ui/`) + Launcher **`launch_studio.bat`** / **`run_studio.py`** chạy như app Windows độc lập. |

---

## 2. Danh Sách Các Tệp Đã Tạo Mới & Cấu Trúc Dự Án

```text
D:/AI_Design_Studio/
├── launch_studio.bat                  # File chạy nhanh 1-click trên Windows
├── run_studio.py                      # Khởi động server và mở cửa sổ app độc lập (Edge/Chrome --app)
├── settings.json                      # Cấu hình Photoshop path, upscale 2x, kích thước tối đa
├── package.json / node_modules/       # Đóng gói sẵn ag-psd và pngjs
├── TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md# File tổng hợp này
├── core/
│   ├── design_document.py             # Schema DesignDocument chuẩn + validate_document()
│   ├── image_analyzer.py              # MODE A: Phân tích, tách lớp, floodFill bảo vệ nền, upscale 2x
│   ├── generate_engine.py             # MODE B: Thiết kế mới + font FZ Poppins + Shadow/Glow tách lớp
│   ├── knowledge_base.py              # Truy xuất và lưu Design Knowledge
│   ├── qa_engine.py                   # QA 1 (Layers) + QA 2 (Composite) + QA 3 (PSD Round-trip)
│   ├── psd_bridge.js                  # Xuất PSD chuẩn & verify đọc lại PSD qua ag-psd
│   └── server.py                      # Local HTTP API Server (127.0.0.1:8788)
├── ui/
│   ├── index.html                     # 9 màn hình: Dashboard, Redesign, Generate, Editor, Assets, Knowledge, History, Export/QA, Settings
│   ├── styles.css                     # Giao diện Dark Studio hiện đại
│   └── app.js                         # Kết nối trực tiếp toàn bộ nút bấm với backend thật
├── assets/
│   ├── fonts/                         # Bộ font FZ Poppins đầy đủ tiếng Việt
│   └── logos/                         # Asset mẫu SafeDrive
├── projects/                          # Chứa sẵn 2 dự án mẫu đã pass QA (06_canva_design, 08_mode_b_generate)
├── tests/
│   ├── run_regression_tests.py        # Bộ test tự động 7 loại ảnh + MODE B + Live HTTP API
│   └── output/regression_summary.json # Kết quả đo thực tế (9/9 PASS)
├── backups/legacy_redesign_studio/    # Bản sao lưu toàn bộ script cũ trước nâng cấp
└── docs/
    ├── 01_SYSTEM_AUDIT.md
    ├── 02_ARCHITECTURE.md
    ├── 03_DESIGN_KNOWLEDGE.md
    ├── 04_DEVELOPMENT_ROADMAP.md
    ├── 05_TEST_REPORT.md
    ├── 06_USER_REQUIREMENTS.md
    ├── 07_CHANGELOG.md
    ├── 08_KNOWN_ISSUES.md
    └── 09_RECOVERY_GUIDE.md
```

---

## 3. Lỗi Đã Tự Phát Hiện & Sửa Trong Quá Trình Kiểm Thử

1. **Sửa lỗi thiếu dấu tiếng Việt (`MODE B`):**
   - *Phát hiện:* Khi mở ảnh ghép `08_mode_b_generate/qa_composite.png` kiểm tra bằng mắt, chữ `HƠN`, `Cảnh`, `sớm`, `khoảng`, `chuẩn`, `Tải` bị ô vuông lỗi glyph do file `Poppins` cũ không có tiếng Việt.
   - *Đã sửa:* Thay toàn bộ font mặc định sang **`FZ Poppins`** (chép từ `D:/CanvaSafeDrive/FzPoppins/`) và kiểm tra lại ảnh ghép hiển thị đầy đủ dấu 100%.
2. **Sửa lỗi `floodFill` lọt vào vùng kính lái sáng (`MODE A`):**
   - *Phát hiện:* Trên ảnh Canva (`06_canva_design`), vùng trời sáng qua kính lái chạm cạnh phải làm `floodFill` ăn lẹm tạo mảng lốm đốm và chia vụn thành 37 layer.
   - *Đã sửa:* Ràng buộc chỉ seed `floodFill` tại các điểm viền thuộc nhóm màu nền chủ đạo (`dist_dom < 38`), giảm từ 37 xuống **9 layer sạch** và `MAE` giảm từ `0.92` xuống `0.63`.

---

## 4. Kết Quả Kiểm Thử Thực Tế (`9/9 PASS`)

Chạy từ `python D:/AI_Design_Studio/tests/run_regression_tests.py`:

| Test Case | Kích thước | Số Layer | Dung lượng PSD | MAE vs gốc | Kết quả |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `MODE_A::01_simple_bg` | `600×600` | 2 | 136,870 bytes | 0.13 | **PASS** |
| `MODE_A::02_multi_text` | `700×500` | 4 | 152,922 bytes | 0.73 | **PASS** |
| `MODE_A::03_multi_product` | `800×500` | 4 | 354,084 bytes | 0.32 | **PASS** |
| `MODE_A::04_white_bg_product` | `600×600` | 2 | 86,530 bytes | 0.31 | **PASS** |
| `MODE_A::05_transparent_png` | `1068×459` | 2 | 347,766 bytes | 0.33 | **PASS** |
| `MODE_A::06_canva_design` | `2048×2048` | 9 | 8,361,202 bytes | 0.63 | **PASS** |
| `MODE_A::07_overlapping` | `1472×1472` | 8 | 6,333,072 bytes | 2.83 | **PASS** |
| `MODE_B::generate_portrait_4x5` | `1080×1350` | 9 (3 Text) | 798,866 bytes | N/A | **PASS** |
| `API::system_redesign_save_export` | `600×600` | 2 | 136,870 bytes | — | **PASS** |

*Ghi chú minh bạch:* QA 3 đã xác minh đọc lại toàn bộ file `.psd` bằng `ag-psd` (`readPsd`). Bước mở kiểm tra tương tác trên giao diện `Adobe Photoshop 2024` chưa tự động bấm GUI headless và được để sẵn nút **"Mở trong Photoshop 2024"** ngay trong ứng dụng để bạn mở xác nhận trực tiếp.

---

## 5. Cách Sử Dụng Nhanh Hàng Ngày

1. **Mở ứng dụng:** Nhấp đúp file **`D:/AI_Design_Studio/launch_studio.bat`**.
2. **Làm việc:**
   - Muốn tách ảnh phẳng sẵn có → vào tab **MODE A: Redesign**.
   - Muốn tạo thiết kế mới từ ảnh sản phẩm + logo + chữ → vào tab **MODE B: Generate**.
   - Muốn kéo thả, đổi màu, sửa chữ → chỉnh ngay tại **Layer Editor**, rồi bấm **Lưu thay đổi & Xuất PSD**.
3. **Mở Photoshop:** Qua tab **Export PSD & QA** → bấm **Tải file .PSD** hoặc **Mở trong Photoshop 2024**.


---

## 6. Nhật Ký Nâng Cấp v1.3.0 (2026-11-19 — Tích Hợp Giáo Trình DVF 2022)

- **Engine MODE B (`core/generate_engine.py`):**
  - Thêm 5 phong cách mỹ thuật: `bauhaus`, `pop_art` (Ben-Day halftone), `art_deco` (ziggurat vàng ánh kim), `memphis` (anti-design pastel/neon), `swiss_modern` (grid chuẩn).
  - Thêm hàm `generate_color_harmony()` hỗ trợ 6 quy tắc hòa sắc DVF tỷ lệ 60-30-10 (`monochrome`, `complementary`, `split_complementary`, `analogous`, `triadic`, `tetradic`).
  - Áp dụng Layout Safeguards: tỷ lệ Headline/Subheadline `>= 2.0x`, khoảng trắng âm bản `>= 20–25%`, đặt điểm nhấn theo `Rule of Thirds`.
- **Engine QA 2 (`core/qa_engine.py`):**
  - Thêm 3 kiểm tra thẩm mỹ tự động: `check_hierarchy_ratio`, `check_negative_space_ratio`, `check_text_contrast`.
- **Giao diện Studio (`ui/index.html`, `ui/app.js`, `core/server.py`):**
  - Tab **Design Knowledge** hiển thị trực quan các thẻ Yếu tố Thị giác, Phong trào Nghệ thuật và bảng Tâm lý học Màu sắc (Tích cực vs Tiêu cực).

---

## 7. Nhật Ký Nâng Cấp v1.4.0 (2026-11-19 — Pro Product Retouching & Live Adjustment Layers Engine)

- **Engine 4 Khối (`core/retouch_analyzer.py` + `docs/21_RETOUCH_LIGHTING_ENGINE.md`):**
  - **Khối 1 — Semantic Part Segmentation:** Bóc tách chủ thể sản phẩm trung tâm (`Layer 2`) bằng `RMBG-1.4` kết hợp tỉa vùng nền dính cạnh bằng **`SlimSAM-77`**; tự động sinh mặt nạ cho **Top Metallic Lid**, vùng **Emissive Visor / Eyes (`Mat sang`)** và **Inverse Radial Spotlight Vignette**.
  - **Khối 2 — Intrinsic Image Decomposition:** Bóc tách `Albedo`, `Shading`, `Specular` và cặp **Self-Masking Luminosity Masks** (`Curves 2`, `Curves 2 copy`).
  - **Khối 3 — Live 13-Adjustment Stack:** Sinh đầy đủ `Curves 3`, `Curves 1`, `Curves 2`, `Curves 2 copy`, `Hue/Saturation 2`, `Curves 4`, `Hue/Saturation 1`, `Vibrance 1`, `Color Balance 1`, `Color Balance 2`, `Mat sang`, `Mat sang copy`, `Selective Color 1` trong nhóm `COLOR` (`Pass Through`).
- **PSD Bridge & QA (`core/psd_bridge.js`, `core/design_document.py`, `core/qa_engine.py`):**
  - Xuất & đọc kiểm tra ngược các Adjustment Layer sống (`curv`, `blnc`, `hue2`, `vibA`, `selc`), 8-bit Layer Mask (`-2`) và `clipping`; dùng chung `evaluate_adjustment_stack()` để dựng ảnh ghép QA chính xác.
- **API & UI (`core/server.py`, `ui/index.html`, `ui/app.js`):**
  - Thêm endpoint `POST /api/retouch`, nút **✨ Retouch Sản Phẩm & Bóc Tách Ánh Sáng** ở MODE A, xem trực tiếp cặp ảnh `Before / After` + `8-Mask Contact Sheet`.
- **Kiểm thử Hồi quy (`tests/run_regression_tests.py`):**
  - Tổng hợp toàn bộ hệ thống (7 bộ ảnh MODE A + MODE B + Art Movements + `RETOUCH::test_18_layer_product_retouch_psd` + Live HTTP API gồm `/api/retouch`) → **11/11 PASS** (`OVERALL REGRESSION: ALL PASSED`).
  - File PSD mẫu xuất từ ảnh raw thật (`RabbitTank_Sparkling_18Layer_LiveRetouch.psd`): `1200×798`, `7,925,689 bytes`, `16 layers` (`3` pixel layers + `13` live adjustment layers), `9` masks, `6` clipping flags.
  - Tab **MODE B: Generate** bổ sung dropdown chọn **Phong cách Mỹ thuật** và **Mô hình Hòa sắc**.
- **Kiểm thử (`tests/run_regression_tests.py`):**
  - Chạy lại toàn bộ 9 test cũ + thêm `MODE_B::test_art_movement_presets` (`bauhaus` + `pop_art`): **ALL PASSED (10/10)**, tổng PSD `1,274,234 bytes` cho 2 bản Art Movement.

---

## 8. Nhật Ký Nâng Cấp v1.5.0 (2026-11-20 — Banner 5-Module, Commercial Poster 6-Group Amodal & Pro Retouch Honeycomb Upgrade)

- **1. Bóc Tách Banner Esports & Sự Kiện (`core/banner_decomposer.py` + `docs/22_GARENA_BANNER_DECOMPOSER.md`):**
  - Tự động tách riêng ruy băng hình học (`Ribbon_Shape_Date_Bar`, `Ribbon_Venue_Bar_Vikings`), 3 bục vinh quang 3D Isometric (với Amodal Top-Face Fill), cụm giải thưởng theo đúng `z-index` (Huy hiệu + Ruy băng → Cọc xu → Tia nổ vàng → Trang phục + Móc khóa), thiết bị gaming 3D (`Laptop_Gaming_3D_Cyan`, `Console_Gamepad_3D_Neon`), nền sân vận động tái tạo bằng `LaMa 2025jan ONNX` (`512×512` tiled) và cặp **Dual-Version Typography** (`_OrigFX` hiển thị mặc định + `_Editable_Backup` vector `TySh` ẩn kèm live `lmfx` Layer Styles).
  - File `.PSD` mẫu đã kiểm định: `exports/Garena_Banner_CongBo_Editable_FullLayers.psd` (`1160×1080`, `39` layers, `6` groups, `7` `TySh`, `10` `lmfx`, `28` masks, `mae_vs_source = 2.67`, `overall_passed = true`).
- **2. Bóc Tách Poster Thương Mại 6-Group Amodal (`core/poster_decomposer.py`):**
  - Dựng lại trọn vẹn poster dịch vụ thành `.PSD` chỉnh sửa không phá hủy với **Amodal Completion**: nền trời hoàng hôn sạch (`01_Background_Sky_Twilight_Clean`), kéo dài rìa vòng quay (`02_Ferris_Wheel_Landmark_Right`), vẽ bù mặt đường nhựa liên tục bên dưới xe (`03_Asphalt_Road_Curved_Track`), xóa route GPS khỏi bản đồ và hoàn thiện khung/màn hình iPhone bị xe che (`06_iPhone_Mockup_Body_&_Map_Amodal`), tách xe Taxi nét mịn bằng `SlimSAM-77` + `2x Cubic` anti-aliasing (`09_Yellow_Taxi_Cab_Hero`), làm sạch 2 thanh footer chéo + 2 icon + logo + **9 cặp Dual Typography** (`18` text layers).
  - File `.PSD` mẫu đã kiểm định: `exports/Melbourne_Xpress_Cabs_Editable_FullLayers.psd` (`736×736`, `39` layers, `6` groups, `9` `TySh`, `11` `lmfx`, `26` masks, `mae_vs_source = 2.21`, `overall_passed = true`).
- **3. Nâng Cấp Pro Retouching (`core/retouch_analyzer.py`):**
  - Bổ sung `SlimSAM-77` ROI + convex hull cho nắp kim loại 3D, `2x Cubic` contour anti-aliasing, điều biến **Frequency-Separated Honeycomb Texture Glow** trên `Mat sang copy` và cân bằng Titanium chống cháy sáng `255`.
  - File `.PSD` mẫu đã kiểm định: `exports/RabbitTank_Sparkling_18Layer_LiveRetouch.psd` (`1200×798`, `16` layers gồm `3` pixel + `13` live Adjustment Layers, `9` masks, `6` clipping flags, `overall_passed = true`).
- **4. PSD Bridge LayerFX, Tri thức & Giao Diện (`core/psd_bridge.js`, `core/design_document.py`, `core/qa_engine.py`, `core/server.py`, `knowledge/knowledge_base.json`, `ui/`):**
  - Xuất & kiểm định ngược live Photoshop LayerFX (`lmfx`: `dropShadow`, `innerShadow`, `stroke`, `solidFill`, `gradientOverlay`, `outerGlow`), bổ sung endpoint `POST /api/banner_decompose` và nút **🏆 Bóc Tách Banner Esports / Sự Kiện** trong Studio UI `v1.5`.

---

## 9. Nhật Ký Vá Lỗi Deep-Audit v1.5.1 (2026-11-20)

- **Sửa lỗi lệch Layer Mask về `(0, 0)` (`core/psd_bridge.js`, `core/design_document.py`):** Dùng `lyr.mask_y ?? psdLayer.top ?? lyr.y ?? 0` và `lyr.mask_x ?? psdLayer.left ?? lyr.x ?? 0` cho mask đã crop theo layer, nâng cấp `verifyPsdFile()` kiểm tra `misaligned_mask_count === 0` (`26/26` mask ở `Melbourne` và `28/28` mask ở `Garena` đều khớp 1:1 với tọa độ layer).
- **Sửa bầu trời, rìa vòng quay & mặt đường nhựa Amodal (`core/poster_decomposer.py`):**
  - Khuếch tán điều hòa đa tỷ lệ tạo dải hoàng hôn mượt đều trên `01_Background_Sky_Twilight_Clean`.
  - Lọc sạch vệt đen khung iPhone khỏi `02_Ferris_Wheel_Landmark_Right` (`x >= 658`, vẽ bù 22px vành cong).
  - Ràng buộc đường cong chân trời `road_top_curve`, vân nhựa đường bất tuần hoàn, vẽ nối vạch vàng đôi vào phối cảnh và feather `25×25` sạch viền gầm xe trên `03_Asphalt_Road_Curved_Track`.
- **Cắt gọn Text Bounding Box (`core/poster_decomposer.py`, `core/banner_decomposer.py`):** Loại bỏ lề trong suốt 24px dư thừa để toàn bộ 9 Editable Text Layer nằm gọn trong `736×736` (`overflow = 0`).
- **Kết quả kiểm thử sau sửa lỗi:** Cả 4 PSD mẫu trong `exports/` đạt `ok = true`, `misaligned = 0`, `overflow = 0`; bộ hồi quy `tests/run_regression_tests.py` đạt **11/11 PASS**.
