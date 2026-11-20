# SEMANTIC DESIGN ANALYZER (`core/semantic_analyzer.py`)

## 1. Mục tiêu

`run_semantic_redesign()` chuyển đổi poster/banner phẳng từ ảnh pixels thành cấu trúc ngữ nghĩa phân tầng (`semantic_objects`) gắn kết 1:1 với các layer trong `DesignDocument v1.2`, đồng thời ước lượng vùng bị che khuất để phục vụ chỉnh sửa độc lập.

---

## 2. Pipeline Phân tích 7 Bước

1. **Chuẩn hóa đầu vào & Khử nhiễu nhẹ:** Đọc ảnh an toàn Unicode bằng `np.fromfile` + `cv2.imdecode`, áp dụng `cv2.bilateralFilter` và resize tùy chọn (mặc định tối đa `2048px`), lưu `source_reference.png`.
2. **Nhận diện Typography (`extract_typography_objects`):** Chạy Tesseract `vie+eng`, lọc nhiễu nền/logo, phân tích màu chữ, nét đậm, căn lề, và khớp font nội bộ (`344` font khả dụng từ thư mục `assets/fonts` và `C:/Windows/Fonts`).
3. **Salient Foreground Extraction (`run_rmbg_salient`):** Dùng `briaai/RMBG-1.4` tách chủ thể tiền cảnh nổi bật (`Foreground_Hero`), kèm phân tích chất lượng biên (`analyze_mask_quality`) để cảnh báo nếu có viền xanh hoặc vùng quá lớn chạm nhau.
4. **Phân tách Midground:** Loại bỏ vùng Foreground (`salient_mask`) và Text boxes (`text_mask_all`) khỏi bản đồ khác biệt so với nền (`_estimate_local_background`), phân loại thành phần trung cảnh (`architecture`, `logo`, `foreground_object`).
5. **Tái tạo Nền Sạch (`reconstruct_region`):** Vá phần nền bị che bởi toàn bộ foreground + midground + text (`total_fg_mask`) tạo thành `01_Background_Reconstructed.png` với nhãn `pixel_origin = "algorithmic_inpaint"`.
6. **Tạo Cặp Layer Chữ An Toàn:** Tạo `Text_OrigRaster` (tham chiếu raster gốc) và `Text_Editable` (`type="text"`), gắn `needs_user_confirmation` khi độ tin cậy OCR thấp hoặc nhận diện trên vùng logo cách điệu để tránh tự động phá vỡ thiết kế.
7. **Xây dựng Semantic Graph (`make_semantic_object`):** Lưu `object_id`, `object_category`, `bounding_box`, `z_index`, `confidence_score`, `segmentation_mask`, `overlap_relationships`, `editability_status`, và `linked_layer_id`.

---

## 3. Báo cáo Độ tin cậy & Cảnh báo Trung thực

Hệ thống không che giấu hạn chế tách vùng tự động:
- Nếu `Foreground_Hero` chiếm `> 20%` diện tích canvas, `semantic_analyzer.py` chủ động thêm cảnh báo: *"Hero region spans >20% of canvas and may contain touching foreground sub-objects (use Interactive SlimSAM Point/Box Refine to split sub-objects)."*
- Nếu biên mặt nạ có viền màu xanh/trắng (`halo`), `analyze_mask_quality` gắn cờ cảnh báo để người dùng bật edge decontamination hoặc feather.
