# 10 — FEATURE ACCEPTANCE TESTS (v1.1)

**Script chạy:** `python D:/AI_Design_Studio/tests/run_v1_1_acceptance_tests.py`  
**Kết quả đo thực tế:** `D:/AI_Design_Studio/tests/output/v1_1_acceptance/v1_1_acceptance_report.json` (**5/5 PASS**)

| ID | Tên Kiểm thử | Tiêu chí Nghiệm thu (Thresholds) | Kết quả Đo Thực tế | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **T1** | Layer Editor + Group CRUD + Multi-Export + Binary PSD Verify | `decoded_pixel_layers == layer_count`, `composite_decoded == true`, text sửa mới xuất hiện trong `TySh`, tọa độ `x+40` khớp, `hidden == true` khớp. | `8/8` decoded pixel layers, `edited_text_verified: true`, `moved_coords_verified: true`, `hidden_state_verified: true`. | **VERIFIED PASS** |
| **T2** | MODE B Multi-Product + Logo + Reference + Vietnamese + 3 Variants | Sinh đủ 3 phương án; cả 3 pass QA 1/2/3; giữ nguyên đủ 2 sản phẩm; khác biệt pixel trung bình giữa các cặp `> 15.0`. | 3 variants pass QA; `diff_v1_v2 = 16.72`, `diff_v1_v3 = 133.74`, `diff_v2_v3 = 130.33`. | **VERIFIED PASS** |
| **T3** | Design Knowledge Reference Analyzer | Trích xuất đủ palette, whitespace, focal_zone, suggested_layout và lưu/đọc lại được từ JSON. | `Canva_SafeDrive` (`tech_dark_glow`, `#007F6E`), `OneWay_Taxi` (`clean_card_modern`, `#FBAE23`). | **VERIFIED PASS** |
| **T4** | Project Management (Autosave, Version Restore, Integrity) | Phát hiện `has_recovery & unclean_shutdown`, restore `v001` khôi phục đúng số layer gốc, `check_project_integrity` bắt đúng 1 file bị thiếu. | `versions_count = 3`, `missing_detected = 1`, restore khớp 100%. | **VERIFIED PASS** |
| **T5** | Negative, Stress & Edge Cases | Invalid image trả `400`; `3600×2400` thu về `<= 2048`; 32 layers/6 groups decode đủ `32/32`; font lỗi fallback không rỗng; PSD hỏng bị từ chối (`exit != 0`); low disk bị cảnh báo; malformed JSON trả `400`. | Tất cả 7 điều kiện biên đều **true**. | **VERIFIED PASS** |
