# 07 — CHANGELOG

## v1.5.1 — 2026-11-20 (PSD Mask Alignment, Amodal Road Texture, Ferris Wheel Rim & Text BBox Deep-Audit Fixes)
- **Bug 1 — Sửa Lỗi Lệch Tọa Độ Layer Mask Về `(0, 0)` (`core/psd_bridge.js`, `core/design_document.py`, `core/poster_decomposer.py`, `core/banner_decomposer.py`):**
  - Sửa `buildPsdFromDocument()` trong `core/psd_bridge.js`: dùng `lyr.mask_y ?? psdLayer.top ?? lyr.y ?? 0` và `lyr.mask_x ?? psdLayer.left ?? lyr.x ?? 0` cho các layer có mask đã crop theo bounding box (giữ `(0, 0)` riêng cho `adjustment` layer và full-canvas mask).
  - Bổ sung tham số `mask_x`, `mask_y` vào `make_layer()` và kiểm định bắt buộc `misaligned_mask_count === 0` (`maskLeft === left`, `maskTop === top` khớp kích thước) ngay trong `verifyPsdFile()`.
- **Bug 2 — Nâng Cấp Tái Tạo Đường Nhựa Cong Amodal (`core/poster_decomposer.py`):**
  - Ràng buộc mép trên đường nhựa theo đường chân trời phối cảnh mượt `road_top_curve` (`514px -> 610px` qua `x=55..655`), loại bỏ hoàn toàn khối xám nhô phẳng dưới gầm xe.
  - Tổng hợp hạt nhựa đường đa tầng bất tuần hoàn (`coarse_grain + streak_grain + fine_grain`), vẽ nối vạch đôi vàng uốn cong vào phối cảnh xa, và làm mượt vùng chuyển tiếp `25×25` không bị dính viền vàng gầm xe hay chữ footer.
- **Bug 3 — Khử Vết Cắt Khung iPhone Trên Vòng Quay & Làm Mượt Bầu Trời (`core/poster_decomposer.py`):**
  - Cắt tách `02_Ferris_Wheel_Landmark_Right` hoàn toàn ngoài rìa khung/bóng iPhone (`x >= 658`) và vẽ bù 22px vành cong bên trái (`x: 636..657`) theo tiếp tuyến vòng tròn, xóa 100% đường vạch dọc sẫm.
  - Tái tạo `01_Background_Sky_Twilight_Clean` bằng khuếch tán điều hòa đa tỷ lệ (Harmonic Diffusion) giữ nguyên dải chuyển hoàng hôn tự nhiên, không còn vết hộp chữ nhật hay vệt tối.
- **Bug 4 — Cắt Gọn & Chống Tràn Bounding Box Text Editable (`core/poster_decomposer.py`, `core/banner_decomposer.py`):**
  - Cắt sát vùng pixel thực của ảnh preview `render_styled_text()` và kẹp chặt tọa độ trong khung canvas (`x + width <= canvas_w`, `y + height <= canvas_h`), khắc phục tràn lề dưới `> 736px` của 4 footer text layers.
- **Kiểm định Xác minh Toàn Diện:**
  - `Melbourne_Xpress_Cabs_Editable_FullLayers.psd` (`736×736`, `6,310,448 bytes`, `39` layers, `26` masks, `9` `TySh` text): `misaligned_mask_count = 0`, `overflow = 0`, `mae_vs_source = 2.49`.
  - `Garena_Banner_CongBo_Editable_FullLayers.psd` (`1160×1080`, `10,372,803 bytes`, `39` layers, `28` masks, `7` `TySh` text): `misaligned_mask_count = 0`, `overflow = 0`, `mae_vs_source = 2.67`.
  - `RabbitTank_Sparkling_18Layer_LiveRetouch.psd` (`1200×798`, `8,056,377 bytes`, `16` layers, `9` masks, `6` clipping): `misaligned_mask_count = 0`, `overflow = 0`.
  - Bộ kiểm thử hồi quy `python tests/run_regression_tests.py`: **11/11 PASS**.

## v1.5.0 — 2026-11-20 (Banner 5-Module, Commercial Poster 6-Group Amodal & Pro Retouch Honeycomb Upgrade)
- **Engine Bóc Tách Banner Esports & Sự Kiện (`core/banner_decomposer.py`, `docs/22_GARENA_BANNER_DECOMPOSER.md`):**
  - Hiện thực hóa kiến trúc 5 Module cho banner sự kiện: **Module 1** tách ruy băng hình học + cặp Dual Typography (`_OrigFX` hiển thị mặc định + `_Editable_Backup` vector `TySh` ẩn kèm `LayerFX`); **Module 2** tách 3 bục vinh quang 3D Isometric (Amodal Top-Face Inpainting) + huy hiệu (`DropShadow`/`InnerShadow`), cọc xu kim loại, tia nổ starburst và trang phục + móc khóa; **Module 3** tách logo, thiết bị gaming 3D, ngôi sao & confetti; **Module 4** tái tạo nền sân vận động sạch bằng `LaMa 2025jan ONNX` (`512×512` tiled); **Module 5** đóng gói `.PSD` 6 group.
  - Xác minh trên `exports/Garena_Banner_CongBo_Editable_FullLayers.psd`: `1160×1080`, `39` layers trong `6` groups, `7` Text layers `TySh`, `10` LayerFX `lmfx`, `28` Layer Masks, `2` Adjustment Layers, `mae_vs_source = 2.67`, `overall_passed = true`.
- **Engine Bóc Tách Poster Thương Mại 6-Group Amodal (`core/poster_decomposer.py`):**
  - Bóc tách poster dịch vụ phẳng thành dự án `.PSD` chỉnh sửa không phá hủy kèm **Amodal Completion**: tái tạo bầu trời hoàng hôn mịn (`01_Background_Sky_Twilight_Clean`), mở rộng vòng quay bên phải (`02_Ferris_Wheel_Landmark_Right`), vẽ bù đường nhựa liên tục dưới gầm xe (`03_Asphalt_Road_Curved_Track`), xóa tuyến đường GPS khỏi màn hình bản đồ và vẽ bù phần khung/bản đồ iPhone bị che khuất (`06_iPhone_Mockup_Body_&_Map_Amodal`), tách xe Taxi bằng `SlimSAM-77` + `2x Cubic` anti-aliasing (`09_Yellow_Taxi_Cab_Hero`), dọn sạch chữ/icon trên 2 thanh vát chéo footer và sinh 9 cặp Dual Typography (`OrigFX` + `TySh`).
  - Xác minh trên `exports/Melbourne_Xpress_Cabs_Editable_FullLayers.psd`: `736×736`, `39` layers trong `6` groups, `9` Text layers `TySh`, `11` LayerFX `lmfx`, `26` Layer Masks, `2` Adjustment Layers, `mae_vs_source = 2.21`, `overall_passed = true`.
- **Nâng Cấp Pro Product Retouching Precision (`core/retouch_analyzer.py`):**
  - Bổ sung `SlimSAM-77` ROI + convex hull cho nắp kim loại 3D, `2x Cubic` contour anti-aliasing, điều biến tần số cao **Honeycomb Texture Glow** trên `Mat sang copy` và cân bằng kim loại Titanium không cháy trắng `255`.
  - Xác minh trên `exports/RabbitTank_Sparkling_18Layer_LiveRetouch.psd`: `1200×798`, `16` layers (`3` pixel layers + `13` live Adjustment Layers), `9` Layer Masks, `6` Clipping Masks, `overall_passed = true`.
- **Nâng Cấp Schema, PSD Bridge, QA, API & UI (`core/design_document.py`, `core/psd_bridge.js`, `core/qa_engine.py`, `core/server.py`, `ui/index.html`, `ui/app.js`):**
  - Hỗ trợ serialize & kiểm định ngược `psd_effects` (`lmfx`: `dropShadow`, `innerShadow`, `stroke`, `solidFill`, `gradientOverlay`, `outerGlow`), bổ sung `POST /api/banner_decompose` và nút **Bóc Tách Banner Esports / Sự Kiện** trên UI `v1.5`.

## v1.4.0 — 2026-11-19 (Pro Product Retouching, Intrinsic Lighting & Live Adjustment Layers Engine)
- **Engine Mới (`core/retouch_analyzer.py`):**
  - Hiện thực hóa kiến trúc 4 khối Pro Product Retouching từ [`retouch_layer_logic_analysis.md`](file:///d:/AI/TESTER/retouch_layer_logic_analysis.md):
    - **Khối 1 — Semantic Part Segmentation:** Tự động bóc tách `Layer 2` sản phẩm bằng `RMBG-1.4` kết hợp **`SlimSAM-77` pruning** (loại bỏ họa tiết nền dính cạnh), phát hiện **Top Metallic Lid**, vùng **Emissive Visor / Eyes (`Mat sang`)** và sinh **Inverse Radial Vignette Mask**.
    - **Khối 2 — Intrinsic Image Decomposition:** Bóc tách `Albedo`, `Shading`, `Specular` và sinh **Self-Masking Luminosity Masks** (`Curves 2`, `Curves 2 copy`).
    - **Khối 3 — Live 13-Adjustment Stack + Shared Evaluator:** Tự động cân chỉnh Curves, Color Balance, Hue/Saturation, Vibrance, Selective Color; xuất `composite_after.png`, `before_after_comparison.jpg` và `masks_contact_sheet.jpg`.
- **Nâng cấp Schema & PSD Bridge (`core/design_document.py`, `core/psd_bridge.js`):**
  - Hỗ trợ `type: "adjustment"`, `clipping`, `mask_default_color`, `adjustment_data` (`curv`, `blnc`, `hue2`, `vibA`, `selc`), nhóm `Pass Through` (`COLOR`), kênh mặt nạ 8-bit `-2`, và nhúng composite preview vào `psd.imageData`.
  - Nâng cấp `verifyPsdFile()` xác minh cả lớp pixel, lớp adjustment, mặt nạ và clipping mask khi `readPsd` đọc ngược.
- **Nâng cấp QA, API & UI (`core/qa_engine.py`, `core/server.py`, `ui/index.html`, `ui/app.js`, `knowledge/knowledge_base.json`):**
  - Bổ sung endpoint `POST /api/retouch`, nút **✨ Retouch Sản Phẩm & Bóc Tách Ánh Sáng** trong MODE A, hiển thị badge `[CLIP]` / `[MASK]` / loại Adjustment trong Layer Editor.
  - QA 2 dùng chung `evaluate_adjustment_stack()` để render chính xác stack Adjustment Layers khi bật/tắt layer hoặc lưu dự án.

## v1.3.0 — 2026-11-19 (DVF 2022 Academic Design Engine Upgrade)
- **MODE B — Art Movement Style Presets (`core/generate_engine.py`):**
  - Bổ sung 5 preset phong trào nghệ thuật lịch sử: `bauhaus`, `pop_art` (kèm họa tiết Ben-Day halftone), `art_deco` (khung ziggurat ánh kim), `memphis` (anti-design pastel/neon + chấm bi/zigzag), và `swiss_modern` (grid hệ thống & khoảng trắng lớn).
  - Bổ sung `generate_color_harmony()` sinh bảng màu tự động theo tỷ lệ chuẩn 60-30-10 cho 6 quy tắc hòa sắc DVF (`monochrome`, `complementary`, `split_complementary`, `analogous`, `triadic`, `tetradic`).
  - Ràng buộc Layout Safeguards: `Headline / Subheadline >= 2.0x`, giữ khoảng trắng tối thiểu `20–25%`, đặt điểm nhấn sản phẩm theo quy tắc `Rule of Thirds`.
- **QA 2 — Visual Aesthetic Checks (`core/qa_engine.py`):**
  - Bổ sung `check_hierarchy_ratio()`, `check_negative_space_ratio()`, và `check_text_contrast()` (WCAG contrast ratio `>= 3.0:1`) trong `run_qa_2_composite()`.
- **UI & API (`core/server.py`, `ui/index.html`, `ui/app.js`):**
  - Nâng cấp tab **Design Knowledge** hiển thị trực quan thẻ Yếu tố Thị giác (`visual_elements`), Phong trào Nghệ thuật (`art_movements`), và bảng tra cứu Tâm lý học Màu sắc (`color_psychology`: Tích cực vs Tiêu cực).
  - Thêm dropdown chọn **Phong cách Mỹ thuật** và **Mô hình Hòa sắc** trong tab **MODE B: Generate**.
- **Kiểm thử Hồi quy (`tests/run_regression_tests.py`):**
  - Bổ sung test case `MODE_B::test_art_movement_presets` kiểm tra `bauhaus` & `pop_art` → **10/10 PASS**.

## v1.1.0 — 2026-11-18
- **Backup v1.0:** Sao lưu toàn bộ mã nguồn v1.0 vào `D:/AI_Design_Studio/backups/v1.0_snapshot/`.
- **Root-Cause Fixes:**
  - Sửa lỗi `cv2.imread()` thất bại với đường dẫn chứa ký tự Unicode/Emoji trên Windows bằng `np.fromfile + cv2.imdecode` trong `image_analyzer.py` và `reference_analyzer.py`.
  - Sửa logic giới hạn kích thước trong `image_analyzer.py`: ảnh lớn hơn `max_dim` (`3600×2400`) nay tự thu gọn về `<= 2048px`.
  - Sửa ký tự bullet `✓` bị thiếu glyph trong `FZ Poppins` thành `•` và tách bố cục 2 sản phẩm không chạm nhau trong `generate_engine.py`.
- **New Features & Modules:**
  - Thêm `core/project_manager.py`: Autosave (`autosave_draft.json`), Version History (`versions/vNNN.json`), Restore, Group CRUD, Missing Asset & Disk Space Integrity Check.
  - Thêm `core/reference_analyzer.py`: phân tích ảnh tham khảo bằng CV (K-means palette, 3×3 saliency, whitespace, mood, lighting/shadow) và lưu vào `knowledge_base.json`.
  - Nâng cấp `core/generate_engine.py`: hỗ trợ nhiều sản phẩm, ảnh tham khảo, feature bullets và `generate_layout_variants()` (3 phương án thiết kế khác biệt).
  - Nâng cấp `core/psd_bridge.js` & `core/qa_engine.py`: giải mã toàn bộ pixel từng layer và composite trong bước `verify` thay cho kiểm tra metadata nông.
  - Nâng cấp `ui/`: Undo/Redo, Group Manager, Live Text Preview, Version History & Restore, Reference Analyzer UI, Multi-Variant MODE B UI.

## v1.0.0 — 2026-11-18
- Khởi tạo dự án độc lập `D:/AI_Design_Studio/` từ prototype `TESTER/redesign_studio/`.
