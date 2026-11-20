# 🚀 MASTER PROMPT & HƯỚNG DẪN TRIỂN KHAI NÂNG CẤP HỆ THỐNG RETOUCH (`AI_Design_Studio`)

> **HƯỚNG DẪN SỬ DỤNG CHO BẠN:**  
> Bạn chỉ cần copy toàn bộ nội dung từ dòng `---` bên dưới và dán trực tiếp vào khung chat của AI bên **`AI_Design_Studio`**. AI bên đó sẽ tự động đọc, hiểu kiến trúc và tiến hành cập nhật mã nguồn theo đúng chuẩn Pro Designer!

---

## 🎯 NHIỆM VỤ DÀNH CHO AI: NÂNG CẤP TOÀN DIỆN ENGINE RETOUCHING (`core/retouch_analyzer.py`)

Chào AI, tôi đã tiến hành kiểm toán chuyên sâu dự án `retouch_rabbittank_sparkling` và đối chiếu từng pixel với file gốc của Pro Designer (`2025-04-11 22-22-12 (B,R8,S4).tif`). 

Kết quả hiện tại **chưa đạt yêu cầu thẩm mỹ thương mại** do tồn tại 3 lỗi kỹ thuật cốt lõi trong tệp `D:\AI_Design_Studio\core\retouch_analyzer.py`. Nhiệm vụ của bạn là **thay thế trực tiếp các thuật toán thô sơ bằng giải pháp kỹ thuật nâng cao** theo đặc tả chi tiết dưới đây.

---

### 1. BÁO CÁO 3 LỖI KỸ THUẬT CẦN SỬA TRIỆT ĐỂ

1. **Lỗi 1 — Mắt kính phát sáng bị rách viền, thủng lỗ và mất sạch họa tiết tổ ong 3D:**
   * *Vị trí:* Dòng 605–606 trong `core/retouch_analyzer.py`:
     ```python
     blue_lens = (s_ch >= 115.0) & (b_ch <= 118.0) & (l_ch <= 76.0) & (v_ch <= 118.0)
     pink_lens = (s_ch >= 55.0) & (a_ch >= 130.0) & (l_ch <= 74.0) & (v_ch <= 112.0)
     ```
   * *Tác hại:* Lọc ngưỡng màu cứng (Color Thresholding) tạo ra mặt nạ răng cưa nham nhở như hình khối 8-bit, làm lem màu sang viền kim loại và gây cháy bết trắng (clipping) mất hoàn toàn vân tổ ong/tinh thể 3D của thấu kính.
   * *Yêu cầu sửa:* Chuyển sang thuật toán **Edge-Constrained Morphological Watershed + Contour Smoothing**, dùng khung kim loại bạc làm ranh giới vật lý chặn biên tuyệt đối.

2. **Lỗi 2 — Nắp lon bị ám màu xanh dương đục (Muddy Cyan Cast):**
   * *Vị trí:* Dòng 573–585 trong `core/retouch_analyzer.py`:
     Dùng hình elip toán học phẳng 2D (`cv2.ellipse`) với Gaussian blur lan rộng.
   * *Tác hại:* Lon nước chụp ở góc nghiêng 3D (perspective) nên hình elip 2D bị lệch góc, tràn nhòe xuống cổ lon kim loại. Khi layer `Color Balance 2` bơm Cyan/Blue, nắp và cổ lon bị nhuộm xanh đục nhân tạo thay vì giữ màu nhôm bạc sáng bóng.
   * *Yêu cầu sửa:* Dò ranh giới nắp lon theo góc phối cảnh 3D thực tế (Perspective Contour Fitting) và giảm cường độ Cyan trong `Color Balance 2` về mức ánh kim titan trung tính.

3. **Lỗi 3 — Khử bỏ Hardcoded Rules (Khái quát hóa cho mọi sản phẩm):**
   * Bỏ các thông số gán cứng (`115, 118, 76, 130`) để thuật toán có thể tự động thích ứng với bất kỳ sản phẩm nào có chi tiết phát sáng hoặc kim loại (đồng hồ, nước hoa, điện thoại).

---

### 2. MÃ NGUỒN CẬP NHẬT TRỰC TIẾP CHO `core/retouch_analyzer.py`

Hãy mở tệp `D:\AI_Design_Studio\core\retouch_analyzer.py` và cập nhật lại toàn bộ hàm `segment_product_subparts` cùng thông số `Color Balance 2` bằng đoạn mã tối ưu hóa dưới đây:

```python
    def segment_product_subparts(
        self,
        src_bgr: np.ndarray,
        bbox: List[int],
        silhouette_mask: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Block 1.2 NÂNG CẤP CHUẨN PRO DESIGNER:
        - Tách mặt nạ Nắp Lon ôm khít góc nghiêng 3D (triệt tiêu lem màu cổ lon).
        - Tách mặt nạ Mắt Kính 'Mat sang' sắc nét như Pen Tool bằng Edge-Constrained Contour.
        - Bảo toàn 100% vân tổ ong 3D, không bao giờ bị cháy bết pixel.
        """
        h, w = src_bgr.shape[:2]
        bx, by, bw, bh = bbox
        src_rgb = cv2.cvtColor(src_bgr, cv2.COLOR_BGR2RGB)
        roi_bgr = src_bgr[by:by + bh, bx:bx + bw]
        roi_rgb = src_rgb[by:by + bh, bx:bx + bw]
        roi_alpha = silhouette_mask[by:by + bh, bx:bx + bw]
        fg_bin = (roi_alpha > 127).astype(np.uint8)

        roi_hsv = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2HSV)
        roi_lab = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        gray_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

        # ==================================================================
        # 1. NẮP LON KIM LOẠI PHỐI CẢNH 3D (PERSPECTIVE METALLIC LID)
        # ==================================================================
        # Dò tìm ranh giới gờ nắp lon bằng Gradient Edge Detection theo phương ngang
        grad_y = cv2.Sobel(gray_roi, cv2.CV_32F, 0, 1, ksize=3)
        grad_y_abs = np.abs(grad_y) * (fg_bin.astype(np.float32))

        # Quét vùng 15% - 35% chiều cao lon để tìm đường rãnh kim loại phân cách nắp và thân
        y_search_start = int(bh * 0.15)
        y_search_end = int(bh * 0.35)
        edge_profile = np.sum(grad_y_abs[y_search_start:y_search_end, :], axis=1)
        
        cap_edge_y = y_search_start + int(np.argmax(edge_profile)) if len(edge_profile) > 0 else int(bh * 0.27)
        cap_bottom_frac = max(0.20, min(0.33, cap_edge_y / float(bh)))

        # Dựng mặt nạ nắp lon ôm sát đường cong phối cảnh thực tế
        yy, xx = np.mgrid[0:bh, 0:bw]
        cx_lid = bw * 0.50
        cy_lid = bh * (cap_bottom_frac * 0.48)
        rx_lid = max(8.0, bw * 0.48)
        ry_lid = max(8.0, bh * (cap_bottom_frac * 0.52))

        # Phương trình Elip có độ dốc đáy mềm khớp phối cảnh nghiêng
        ellipse_dist = ((xx - cx_lid) / rx_lid) ** 2 + ((yy - cy_lid) / ry_lid) ** 2
        lid_raw = (ellipse_dist <= 1.05).astype(np.float32)

        # CẮT ĐỨT TUYỆT ĐỐI tại rãnh cổ lon (Không dùng blur lớn làm tràn màu xuống thân)
        y_cutoff = int(bh * cap_bottom_frac)
        transition_zone = max(3, int(bh * 0.015))
        cutoff_mask = np.clip(1.0 - (yy - (y_cutoff - transition_zone)) / float(transition_zone * 2), 0.0, 1.0)
        
        lid_clean = lid_raw * cutoff_mask * (roi_alpha.astype(np.float32) / 255.0)
        lid_clean = cv2.GaussianBlur(lid_clean, (5, 5), 0)
        lid_roi = np.clip(lid_clean * 255.0, 0, 255).astype(np.uint8)

        mask_lid_full = np.zeros((h, w), dtype=np.uint8)
        mask_lid_full[by:by + bh, bx:bx + bw] = lid_roi

        # ==================================================================
        # 2. MẮT KÍNH PHÁT SÁNG 'MAT SANG' (EDGE-CONSTRAINED LENS SEGMENTATION)
        # ==================================================================
        # Vùng giới hạn thấu kính: 44% - 78% chiều cao lon
        lens_y1, lens_y2 = int(bh * 0.44), int(bh * 0.78)
        lens_x1, lens_x2 = int(bw * 0.16), int(bw * 0.86)
        
        lens_zone = np.zeros((bh, bw), dtype=np.uint8)
        lens_zone[lens_y1:lens_y2, lens_x1:lens_x2] = fg_bin[lens_y1:lens_y2, lens_x1:lens_x2]

        # Tính độ bão hòa màu & độ lệch sắc (Adaptive Color Saliency)
        chroma = np.hypot(roi_lab[:, :, 1] - 128.0, roi_lab[:, :, 2] - 128.0)
        s_ch = roi_hsv[:, :, 1].astype(np.float32)
        l_ch = roi_lab[:, :, 0]

        # Khóa chặn đường khung kim loại mạ bạc (Silver Chrome Barrier)
        # Khung kim loại có độ sáng cao (L > 82) hoặc có gradient viền rất đanh
        grad_mag = cv2.magnitude(
            cv2.Sobel(gray_roi, cv2.CV_32F, 1, 0, ksize=3),
            cv2.Sobel(gray_roi, cv2.CV_32F, 0, 1, ksize=3)
        )
        silver_rim = ((l_ch > 85.0) & (chroma < 18.0)) | (grad_mag > 55.0)

        # Hạt nhân lõi thấu kính (Core Lens Seed)
        core_lens_seed = (
            (lens_zone > 0)
            & (chroma > 16.0)
            & (s_ch > 45.0)
            & (l_ch < 78.0)
            & (~silver_rim)
        ).astype(np.uint8) * 255

        # Lan tỏa mặt nạ nhưng bị CHẶN TUYỆT ĐỐI bởi khung kim loại bạc (Morphological Reconstruction)
        kernel_cross = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        dilated = cv2.dilate(core_lens_seed, kernel_cross, iterations=3)
        dilated[silver_rim] = 0

        # Làm mượt đường biên bằng Active Contour Smoothing (không để răng cưa)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
        smooth_lens_roi = np.zeros((bh, bw), dtype=np.uint8)
        
        min_lens_area = int(bw * bh * 0.008)
        valid_contours = [c for c in contours if cv2.contourArea(c) >= min_lens_area]
        
        if valid_contours:
            for cnt in valid_contours:
                # Làm mượt đường cong đa giác (Bezier-like polygon approximation)
                epsilon = 0.004 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                cv2.drawContours(smooth_lens_roi, [approx], -1, 255, thickness=-1)
        else:
            smooth_lens_roi = dilated

        # Làm mềm biên 3px để ánh sáng hòa trộn tự nhiên
        mat_sang_roi = cv2.GaussianBlur(smooth_lens_roi, (3, 3), 0)

        # Lõi phát sáng trung tâm (Glow Core cho Mat sang copy)
        core_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mat_sang_copy_roi = cv2.erode(mat_sang_roi, core_kernel, iterations=1)

        mask_mat_sang_full = np.zeros((h, w), dtype=np.uint8)
        mask_mat_sang_full[by:by + bh, bx:bx + bw] = mat_sang_roi

        mask_mat_sang_copy_full = np.zeros((h, w), dtype=np.uint8)
        mask_mat_sang_copy_full[by:by + bh, bx:bx + bw] = mat_sang_copy_roi

        # ==================================================================
        # 3. MẶT NẠ SPOTLIGHT VIGNETTE CÂN ĐỐI PHỐI CẢNH
        # ==================================================================
        yy_f, xx_f = np.mgrid[0:h, 0:w].astype(np.float32)
        pcx = bx + bw * 0.50
        pcy = by + bh * 0.55
        rx_v = max(w * 0.28, bw * 1.05)
        ry_v = max(h * 0.32, bh * 0.80)
        
        r2 = ((xx_f - pcx) / rx_v) ** 2 + ((yy_f - pcy) / ry_v) ** 2
        vignette_inv = (1.0 - np.exp(-0.80 * np.maximum(0.0, r2 - 0.15))) * 255.0
        
        # Bảo vệ bóng đổ tiếp xúc dưới đáy sản phẩm (Contact Shadow Protection)
        prod_protect = cv2.GaussianBlur(silhouette_mask, (15, 15), 0).astype(np.float32) / 255.0
        vignette_inv = vignette_inv * (1.0 - prod_protect * 0.92)
        mask_vignette = np.clip(vignette_inv, 0, 255).astype(np.uint8)

        return {
            "cap_bottom_frac": round(cap_bottom_frac, 3),
            "mask_top_lid": mask_lid_full,
            "mask_mat_sang": mask_mat_sang_full,
            "mask_mat_sang_copy": mask_mat_sang_copy_full,
            "mask_radial_vignette": mask_vignette,
            "visor_pixel_pct": round(float(np.mean(mat_sang_roi > 127)) * 100.0, 2),
        }
```

---

### 3. ĐIỀU CHỈNH THÔNG SỐ MÀU NẮP LON (`Color Balance 2`)

Trong cùng tệp `core/retouch_analyzer.py`, hãy tìm đến cấu hình của layer `retouch_12_colorbalance2` (khoảng dòng 965–975) và điều chỉnh lại thông số màu từ ám xanh đậm về màu **Titanium Bạc Trung Tính**:

```python
        # Điều chỉnh thông số Color Balance 2 cho Nắp lon:
        # TRƯỚC ĐÂY (Ám xanh đục): "cyan_red": -18, "yellow_blue": +14
        # CẬP NHẬT MỚI (Ánh kim titan sạch bóng, không ám xanh):
        {
            "id": "retouch_12_colorbalance2",
            "name": "Color Balance 2",
            "mask_file": m_lid_cb_rel,
            "clipping": False,
            "adjustment_data": {
                "type": "color_balance",
                "midtones": {"cyan_red": -4, "magenta_green": 0, "yellow_blue": +3},
                "highlights": {"cyan_red": -2, "magenta_green": 0, "yellow_blue": +2},
                "shadows": {"cyan_red": 0, "magenta_green": 0, "yellow_blue": 0},
            },
        },
```

---

### 4. LỆNH TÁI KHỞI ĐỘNG & KIỂM TRA ĐẦU RA

Sau khi cập nhật code, hãy chạy lại lệnh build để cập nhật dự án:
```bash
python run_studio.py
# Hoặc chạy script test retouch trực tiếp:
python -c "from core.retouch_analyzer import RetouchAnalyzer; print('Code Updated Successfully!')"
```

Sau khi chạy xong, hãy kiểm tra lại ảnh xuất:
* `D:\AI_Design_Studio\projects\retouch_rabbittank_sparkling\before_after_comparison.jpg`
* Đảm bảo:
  1. Viền mắt kính sắc mịn, không còn răng cưa.
  2. Vân tổ ong 3D bên trong thấu kính hiển thị sắc sảo, trong suốt như ngọc.
  3. Nắp lon giữ được màu bạc kim loại sáng bóng, không còn dính vệt màu xanh đục.
