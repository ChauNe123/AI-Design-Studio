# 22 — GARENA ESPORTS BANNER 5-MODULE DECOMPOSITION & LAYERFX ENGINE (v1.5.0)

**Module chính:** [`core/banner_decomposer.py`](../core/banner_decomposer.py)  
**Tham chiếu nghiệp vụ:** [`garena_banner_decomposition_analysis.md`](file:///d:/Test psd/garena_banner_decomposition_analysis.md) · [`ai_vs_pro_retouch_deep_audit.md`](file:///d:/Test psd/ai_vs_pro_retouch_deep_audit.md)

---

## 1. Kiến trúc 5 Module Đảo Ngược Banner Phẳng Thành Dự Án PSD Designer

Khi người dùng nạp bất kỳ ảnh banner JPG/PNG phẳng nào qua giao diện hoặc API `POST /api/banner_decompose`, hệ thống thực thi tuần tự **5 Module**:

### Module 1 — Dual-Version Typography & Skewed Ribbons
- Áp dụng **Chiến lược Chữ 2 Phiên Bản**:
  1. **`OrigFX_Bitmap` (`visible: true`)**: Cắt tách chính xác cụm chữ nghệ thuật gốc (`CÔNG BỐ GIẢI ĐẤU`, `9h00 ngày 15.09.2024`, `STUDENT CUP 2024`) kèm đường viền stroke trắng & bóng đổ theo nền mây thực tế, giữ 100% chất lượng đồ họa/gradient/halftone gốc.
  2. **`Editable_Vector_Text` (`visible: false`)**: Tạo sẵn lớp **Type Layer (`TySh`)** đã khớp bộ font hiển thị Việt hóa (`Anton`, `Be Vietnam Pro`, `FZ Poppins`) và đính kèm **Live Photoshop LayerFX (`lmfx`)** (Double Drop Shadow, Stroke trắng, Gradient Overlay xanh-ngọc/lam, Inner Shadow) để designer chỉ cần bật mắt layer lên gõ lại tiêu đề cho giải đấu mới.
- Tách riêng phần hình khối **Ribbon Ngày giờ** & **Ribbon Địa điểm (`Vikings XVNT`)**, tự động vá sạch phần chữ đè lên dải ruy băng bằng Telea Inpainting.

### Module 2 — Multi-Object Podiums (Amodal Top-Face Fill) & Prize Sub-Items
- Khắc phục nhược điểm `RMBG-1.4` gộp cả cụm giữa thành 1 cục:
  - Phân tách **3 Bục Vinh Quang Isometric (`Bục 1 Center`, `Bục 2 Left`, `Bục 3 Right`)** dựa trên hình khối màu cam-vàng và dùng **Convex Hull + Amodal Top-Face Inpainting** để vẽ bù hoàn thiện phần mặt trên của từng bục nơi cọc xu và vật phẩm đè lên.
  - Bóc tách độc lập theo 3 cụm giải thưởng (`Giải Nhất`, `Giải Nhì`, `Giải Ba`):
    - **Comic Starbursts (`Comic_Burst_*`)**
    - **Cọc xu FC (`Coc_Xu_FC_*`)** bằng hạt màu ngọc lục bảo kết hợp **`SlimSAM-77 ROI`**
    - **Huy hiệu giải thưởng (`Huy_Hieu_Giai_*`)** (gắn `DropShadow` + `InnerShadow` LayerFX)
    - **Trang phục & Phụ kiện (`Áo thun`, `Nón kết`, `Vòng tay`, `Móc khóa`)**.

### Module 3 — Peripheral Logos, 3D Gaming Gear & Floating Decor
- Bóc tách độc lập các thành phần trang trí ngoại vi:
  - `Logo_EA_SPORTS_FC_ONLINE` & `Logo_SVC_Student_Cup_2024` (bảo toàn chữ trắng bên trong bằng flood-fill viền ngoài)
  - `Laptop_Gaming_3D_Cyan` & `Console_Gamepad_3D_Neon` (dùng `SlimSAM-77 ROI`, gắn `DropShadow` LayerFX)
  - `Location_Pin_Vikings`, `Paper_Floating_Top`, `Stars_4Point_Sparkles` (gắn `InnerShadow` LayerFX), `Confetti_Particles`.

### Module 4 — Sequential LaMa Neural Background Reconstruction
- Gom toàn bộ mask tiền cảnh và chạy **LaMa 2025jan ONNX 3-Pass theo từng vùng `512×512`** (Vùng trời/tiêu đề trên, 3 vùng bục trái/phải/giữa, vùng decor đáy) để tái tạo nền **Sân vận động 3D + Đám mây Anime + Sóng xanh lá (`01_Background_Stadium_Clean.png`)** liền mạch, kèm tùy chọn Adjustment Layer (`Curves_Stadium_Contrast`, `ColorBalance_Stadium_Mint`) và layer tham chiếu `00_Original_Flattened_Ref` (ẩn mặc định).

### Module 5 — Packaging & Live Photoshop LayerFX (`lmfx`)
- [`core/psd_bridge.js`](../core/psd_bridge.js) hỗ trợ đầy đủ `LayerEffectsInfo` của `ag-psd` (`dropShadow` đơn/kép, `innerShadow`, `stroke`, `gradientOverlay`, `solidFill`, `outerGlow`) và đọc kiểm chứng ngược số lớp có hiệu ứng (`fx_layer_count`).
- Xuất đồng thời bảng đối chiếu **`banner_progression_grid.jpg`** (4 bước: Clean BG -> + Podiums/Prizes -> + Decor/Typography -> Final Composite) và **`banner_layers_sheet.jpg`**.

---

## 2. Nâng Cấp Precision Cho Pro Retouching (`core/retouch_analyzer.py`)
Đồng thời khắc phục triệt để 3 điểm yếu trong [ai_vs_pro_retouch_deep_audit.md](file:///d:/Test psd/ai_vs_pro_retouch_deep_audit.md):
1. **Smooth Contour `SlimSAM ROI` + `2x Cubic Anti-Aliasing` cho `Mat sang`**: Loại bỏ răng cưa do ngưỡng HSV thô.
2. **Honeycomb Frequency-Separated Glow (`Mat sang copy`)**: Điều chế mặt nạ theo bản đồ tần số cao của tổ ong gốc & hạ trần Curves tránh clipping 255 để giữ nguyên họa tiết lục giác 3D khi phát sáng.
3. **3D Perspective Top-Lid Contour Fitting**: Dùng `SlimSAM-77` + Convex Hull bám theo viền nắp lon thực tế kết hợp cân bằng tông nhôm titan sạch (`Color Balance 2` nhẹ, `Hue/Saturation 1` `-24`) không tràn màu xanh đục xuống cổ lon.
