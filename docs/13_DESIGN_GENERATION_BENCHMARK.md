# 13 — DESIGN GENERATION BENCHMARK (MODE B v1.1)

**Module:** `D:/AI_Design_Studio/core/generate_engine.py` + `D:/AI_Design_Studio/core/reference_analyzer.py`  
**Dữ liệu benchmark:** `D:/AI_Design_Studio/tests/output/v1_1_acceptance/mode_b_variants/`

## 1. Benchmark Đa Phương án (`T2_MODE_B_MultiProduct_Reference_3Variants`)
Đầu vào thực tế: 2 ảnh sản phẩm (`04_white_bg_product.png` + `03_multi_product.png`), 1 logo (`✅ SAFE DRIVE.png`), 1 ảnh tham khảo (`06_canva_design.jpg`), headline/subheadline/3 bullets/CTA tiếng Việt, kích thước `1080×1350` (4:5).

| Variant | Layout Strategy | Số Layer | Khác biệt Pixel so với Variant khác | QA 1 / QA 2 / QA 3 |
| :--- | :--- | :---: | :--- | :---: |
| `safedrive_multi_v1` | `tech_dark_glow` | 12 | `diff(v1,v2)=16.72`, `diff(v1,v3)=133.74` | **PASS** |
| `safedrive_multi_v2` | `hero_split` | 12 | `diff(v2,v3)=130.33` | **PASS** |
| `safedrive_multi_v3` | `clean_card_modern` | 11 | Nền sáng + card bo góc + viền accent | **PASS** |

## 2. Xác minh Nguyên tắc Thiết kế
- **Bảo toàn 100% ảnh sản phẩm thương mại:** Không vẽ lại sản phẩm; tách riêng lớp bóng tiếp xúc (`multiply`) và ánh sáng nền (`screen`) thành layer độc lập.
- **Không sao chép máy móc ảnh tham khảo:** `analyze_reference_image()` chỉ trích xuất bảng màu (`#007F6E`, `#00FF6A`), tỷ lệ khoảng trắng, vùng trọng tâm và gợi ý bố cục để áp dụng lên nội dung mới.
- **Tiếng Việt đầy đủ dấu:** Dùng bộ font `FZ Poppins` (`assets/fonts/`), đã kiểm tra trực quan qua `qa_composite.png` không còn lỗi mất glyph.
