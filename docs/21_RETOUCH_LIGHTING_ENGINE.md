# 21 — PRO PRODUCT RETOUCHING & INTRINSIC LIGHTING ENGINE (v1.4.0)

**Module chính:** [`core/retouch_analyzer.py`](../core/retouch_analyzer.py)  
**Tham chiếu nghiệp vụ:** [`retouch_layer_logic_analysis.md`](file:///d:/AI/TESTER/retouch_layer_logic_analysis.md)  
**Trạng thái hiện tại:** Đã tích hợp hoàn chỉnh vào `DesignDocument`, `psd_bridge.js`, `qa_engine.py`, `server.py` (`POST /api/retouch`), `knowledge_base.json` và giao diện Desktop Studio.

---

## 1. Kiến trúc 4 Khối (4-Block Pro Retouch Pipeline)

Hệ thống tái lập chuẩn quy trình Retouch sản phẩm thương mại 2 tầng / 16–18 lớp (gồm các lớp nền + nhóm chỉnh sáng & màu `COLOR` ở chế độ `Pass Through` không phá hủy):

### Khối 1 — Semantic Part Segmentation (`RetouchAnalyzer.extract_hero_product` & `segment_product_subparts`)
1. **`Layer 2` — Full Product Cutout & Silhouette Mask (`mask_04_Curves1_ProductSilhouette.png`):**
   - Kết hợp `RMBG-1.4` salient foreground extraction, chọn cụm chủ thể trung tâm, rồi dùng **`SlimSAM-77`** tỉa bỏ các vùng nhiễu nền phẳng dính cạnh (như họa tiết trên ga giường/sàn) và khử lỗ hổng bằng `fill_holes()`.
   - Nếu người dùng truyền `cutout_path`, tự động căn khớp đa tỉ lệ bằng `cv2.matchTemplate(TM_CCORR_NORMED)`.
2. **Top Metallic Lid / Chrome Rim (`mask_08_Curves4_TopLid.png` & `mask_12_ColorBalance2_TopLid.png`):**
   - Quét profile độ bão hòa LAB dọc theo 0%–42% phần đỉnh sản phẩm để tìm ranh giới nắp kim loại/nhựa mờ và sinh mặt nạ elip mượt.
3. **Emissive / Translucent Visor / Eyes Lens Mask (`mask_13_MatSang_VisorLenses.png` & `mask_14_MatSangCopy_GlowCore.png`):**
   - Kết hợp tiêu chí HSV/CIELAB (`blue_lens`: `S >= 115, b <= 118, L <= 76`; `pink_lens`: `S >= 55, a >= 130, L <= 74`) đồng thời triệt tiêu đường viền bạc chrome (`L > 95` hoặc biên gradient cao) để tách đúng vùng mắt kính/đèn phát sáng mà không lem ra khung kim loại hoặc logo trung tâm.
4. **Inverse Radial Spotlight Vignette (`mask_16_Curves3_RadialVignette.png`):**
   - Sinh mặt nạ Gaussian elip nghịch đảo quanh tâm sản phẩm (`0` tại vùng sản phẩm để bảo vệ, `235–255` ra rìa nền) tạo hiệu ứng đèn sân khấu Spotlight.

### Khối 2 — Intrinsic Image Decomposition & Self-Masking Luminosity (`decompose_intrinsic_and_luminosity`)
- Tách bản đồ nội tại lưu tại `intrinsic/`:
  - `intrinsic_albedo.png` (màu vật liệu thuần không phụ thuộc ánh sáng)
  - `intrinsic_shading.png` (trường chiếu sáng 3D ước lượng bằng Bilateral Filter)
  - `intrinsic_specular.png` (điểm phản chiếu kim loại/chrome bậc cao)
- Sinh cặp mặt nạ Luminosity tự động `mask_05_Curves2_Luminosity.png` và `mask_06_Curves2Copy_Specular.png` giới hạn gọn trong đường viền sản phẩm.

### Khối 3 — Parametric Lighting Stack (13 Live Photoshop Adjustment Layers)
Nhóm **`COLOR`** (`blendMode: 'pass through'`) chứa 13 Adjustment Layer sống xếp từ dưới lên trên:
1. `Curves 3` (Radial Vignette Mask, `defaultColor=255`) — dìm tối phông nền tạo hiệu ứng spotlight.
2. `Curves 1` (Product Silhouette Mask) — nâng sáng tổng thể chủ thể.
3. `Curves 2` (`clipping=True`, Luminosity Mask) — tách khối kim loại & chrome.
4. `Curves 2 copy` (`clipping=True`, Specular Mask) — tăng độ gắt highlight.
5. `Hue/Saturation 2` (`clipping=True`) — đẩy độ bão hòa màu thân sản phẩm.
6. `Curves 4` (Top Lid Mask) — tạo độ khối sắc nét cho nắp kim loại.
7. `Hue/Saturation 1` (`clipping=True`) — giảm độ đục/ám màu trên nắp.
8. `Vibrance 1` — tăng độ tươi tự nhiên toàn cục.
9. `Color Balance 1` — cân bằng sắc độ studio tổng thể.
10. `Color Balance 2` (Top Lid Mask) — khử ám vàng, thêm sắc lạnh thép Cyan/Blue cho nắp.
11. `Mat sang` (`curves`, Visor Lens Mask) — đẩy độ phát sáng neon cho mắt kính/đèn mà vẫn giữ họa tiết tổ ong.
12. `Mat sang copy` (`clipping=True`, Glow Core Mask) — nhân cường độ phát sáng lõi neon.
13. `Selective Color 1` (`clipping=True`, `mode='relative'`) — tinh chỉnh hệ mực Red/Cyan/Blue/Magenta/Neutral/Black.

### Khối 4 — Live PSD Binary Writer & Evaluator (`psd_bridge.js` & `qa_engine.py`)
- [`core/psd_bridge.js`](../core/psd_bridge.js) ghi chuẩn các block nhị phân `ag-psd` (`curv`, `blnc`, `hue2`, `vibA`, `selc`), kênh mặt nạ 8-bit (`-2`), cờ `clipping`, nhóm `Pass Through` và ảnh tổng hợp `After` (`psd.imageData`).
- [`core/retouch_analyzer.py :: evaluate_adjustment_stack()`](../core/retouch_analyzer.py) dùng chung cho cả việc xuất `composite_after.png`, `before_after_comparison.jpg`, `masks_contact_sheet.jpg` lẫn `run_qa_2_composite()` trong [`core/qa_engine.py`](../core/qa_engine.py).
