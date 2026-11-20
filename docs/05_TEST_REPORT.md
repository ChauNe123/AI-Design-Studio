# 05 — TEST REPORT (v1.1)

**Bằng chứng dữ liệu thực tế:**
- Regression v1.0: `D:/AI_Design_Studio/tests/output/regression_summary.json` (`9/9 PASS`)
- Acceptance & Stress v1.1: `D:/AI_Design_Studio/tests/output/v1_1_acceptance/v1_1_acceptance_report.json` (`5/5 PASS`)

## 1. Kết quả Bộ Regression (9/9 PASS)

| Case | Kích thước | Layers | PSD Bytes | MAE | Trạng thái |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `01_simple_bg` | `600×600` | 2 | 136,870 | 0.13 | **VERIFIED PASS** |
| `02_multi_text` | `700×500` | 4 | 152,922 | 0.73 | **VERIFIED PASS** |
| `03_multi_product` | `800×500` | 4 | 354,084 | 0.32 | **VERIFIED PASS** |
| `04_white_bg_product` | `600×600` | 2 | 86,530 | 0.31 | **VERIFIED PASS** |
| `05_transparent_png` | `1068×459` | 2 | 347,766 | 0.33 | **VERIFIED PASS** |
| `06_canva_design` | `2048×2048` | 9 | 8,361,202 | 0.63 | **VERIFIED PASS** |
| `07_overlapping` | `1472×1472` | 8 | 6,333,072 | 2.83 | **VERIFIED PASS** |
| `MODE_B::generate_portrait_4x5` | `1080×1350` | 9 | 719,916 | N/A | **VERIFIED PASS** |
| `API::system_redesign_save_export` | `600×600` | 2 | 136,870 | — | **VERIFIED PASS** |

## 2. Kết quả Bộ Acceptance & Edge-Case v1.1 (5/5 PASS)
- `T1_Editor_Groups_MultiExport_PSDBinaryVerify`: **VERIFIED PASS** (`8/8` decoded pixel layers, verified `"NỘI DUNG ĐÃ CHỈNH SỬA"`, moved `x+40`, `hidden=true`).
- `T2_MODE_B_MultiProduct_Reference_3Variants`: **VERIFIED PASS** (3 variants, `diff_v1_v2=16.72`, `diff_v1_v3=133.74`, `diff_v2_v3=130.33`).
- `T3_DesignKnowledge_ReferenceAnalyzer`: **VERIFIED PASS**.
- `T4_ProjectManagement_Autosave_Restore_Integrity`: **VERIFIED PASS** (`versions_count=3`, `missing_detected=1`).
- `T5_Negative_Stress_EdgeCases`: **VERIFIED PASS** (`invalid_image_400`, `highres_capped_ok`, `stress_32layers_6groups_ok`, `font_fallback_ok`, `corrupt_psd_rejected`, `low_disk_guard_ok`, `malformed_json_400`).

## 3. Giới hạn Chưa Xác minh Tự động
- **Adobe Photoshop 2024 COM / GUI:** Quá trình kiểm thử tự động gọi `Photoshop.Application` bị **`TIMEOUT_WAITING_FOR_PHOTOSHOP_COM`** (quá 35s). Do đó chưa xác nhận được bằng chứng mở sửa tương tác trong cửa sổ GUI Photoshop 2024.
- **Browser UI E2E (Playwright click test):** Chưa chạy script click tự động qua trình duyệt đối với `ui/index.html`; mới xác minh các API backend mà UI gọi.
