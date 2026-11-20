# AI Design Studio v1.5.0 🎨✨

**Ứng dụng Desktop độc lập trên Windows** chuyên **bóc tách ảnh thiết kế phẳng (JPG/PNG)** thành **dự án Photoshop `.PSD` nhiều layer không phá hủy (Non-Destructive)**, phục hồi vùng bị che khuất (**Amodal Inpainting**), **Retouch ánh sáng sản phẩm sống (Live Adjustment Layers)**, **hệ thống chữ song song (Dual Typography + Live LayerFX)** và **sinh bố cục poster mới theo chuẩn học thuật DVF 2022**.

> Toàn bộ AI Segmentation, Detection, Inpainting và OCR chạy **100% cục bộ (Offline Local ONNX + Node.js + Python)** — không gửi ảnh người dùng ra ngoài, không tốn phí API.

---

## 🚀 Khả Năng Cốt Lõi Hiện Tại (v1.5.0)

| Engine / Chế độ | Module Chính | Khả Năng Nổi Bật |
| :--- | :--- | :--- |
| **1. Banner Esports 5-Module** | [`core/banner_decomposer.py`](core/banner_decomposer.py) | Tách 3 bục 3D (Amodal Top-Face Fill), cụm giải thưởng đúng `z-index` (Huy hiệu, Cọc xu, Burst, Trang phục), Gaming Gear, nền sân vận động `LaMa 2025jan`, chữ song song (`OrigFX` + `TySh`) & Live `lmfx` (`DropShadow`, `InnerShadow`, `Stroke`, `GradientOverlay`, `OuterGlow`). |
| **2. Poster Thương Mại 6-Group Amodal** | [`core/poster_decomposer.py`](core/poster_decomposer.py) | Tái tạo nền trời sạch, kéo dài rìa vật thể kiến trúc, vẽ bù đường nhựa liên tục dưới xe, xóa tuyến GPS & vẽ bù khung/bản đồ điện thoại bị che, tách xe nét mịn bằng `SlimSAM-77` + `2x Cubic` anti-aliasing, dọn chữ trên thanh vát footer & xuất 9 cặp Dual Typography. |
| **3. Pro Product Retouching 18-Layer** | [`core/retouch_analyzer.py`](core/retouch_analyzer.py) | Tách chủ thể bằng `RMBG-1.4` + `SlimSAM-77`, tự động sinh mặt nạ Nắp Kim Loại 3D, Mắt/Đèn phát sáng giữ nguyên vân tổ ong (**Frequency-Separated Honeycomb Glow**), Vignette hướng tâm & xuất 13 Live Photoshop Adjustment Layers (`curv`, `blnc`, `hue2`, `vibA`, `selc`) + 6 Clipping Masks. |
| **4. MODE A — Semantic Poster Redesign** | [`core/semantic_analyzer.py`](core/semantic_analyzer.py) | Tự động nhận diện ngữ nghĩa đối tượng (`DETR-ResNet-50` + `RMBG-1.4` + `SlimSAM-77`), khử ám màu viền, vẽ bù nền `LaMa`, khớp font tiếng Việt (`Tesseract` + local fonts). |
| **5. MODE B — DVF Academic Generator** | [`core/generate_engine.py`](core/generate_engine.py) | Sinh poster mới từ ảnh sản phẩm + logo + chữ theo 5 trường phái nghệ thuật (`bauhaus`, `pop_art`, `art_deco`, `memphis`, `swiss_modern`) và 6 quy tắc hòa sắc DVF 60-30-10 (`knowledge/knowledge_base.json`). |
| **6. Kiểm Định QA 3 Tầng & PSD Bridge** | [`core/qa_engine.py`](core/qa_engine.py), [`core/psd_bridge.js`](core/psd_bridge.js) | **QA 1** (Kiểm tra alpha & preview từng layer), **QA 2** (Ghép stack + đo `MAE` + kiểm tra thẩm mỹ DVF), **QA 3** (Đọc ngược nhị phân `.PSD` qua `ag-psd` xác nhận pixel, mask, clipping, `TySh`, `lmfx` và Adjustment Layers). |

---

## 📦 Các File `.PSD` Mẫu Đã Kiểm Định Trong `exports/`

- [`exports/Melbourne_Xpress_Cabs_Editable_FullLayers.psd`](exports/Melbourne_Xpress_Cabs_Editable_FullLayers.psd) — `736×736`, **39 layers** / **6 groups**, **9 `TySh` text layers**, **11 `lmfx` FX layers**, **26 masks**, `mae_vs_source = 2.21`, QA Pass (`Melbourne_Xpress_Cabs_Progression_Grid.jpg`, `Melbourne_Xpress_Cabs_Layers_Sheet.jpg`).
- [`exports/Garena_Banner_CongBo_Editable_FullLayers.psd`](exports/Garena_Banner_CongBo_Editable_FullLayers.psd) — `1160×1080`, **39 layers** / **6 groups**, **7 `TySh` text layers**, **10 `lmfx` FX layers**, **28 masks**, `mae_vs_source = 2.67`, QA Pass (`banner_progression_grid.jpg`, `banner_layers_sheet.jpg`).
- [`exports/RabbitTank_Sparkling_18Layer_LiveRetouch.psd`](exports/RabbitTank_Sparkling_18Layer_LiveRetouch.psd) — `1200×798`, **16 layers** (`3` pixel layers + `13` live Adjustment Layers), **9 masks**, **6 clipping flags**, QA Pass (`RabbitTank_Sparkling_Before_After.jpg`, `RabbitTank_Sparkling_Masks_Sheet.jpg`).
- [`exports/Grab_Economy_FullHD_2048x2048_Editable.psd`](exports/Grab_Economy_FullHD_2048x2048_Editable.psd) — `2048×2048` Full HD multi-layer project.

---

## 🛠️ Hướng Dẫn Cài Đặt & Triển Khai Tiếp Khi Về Nhà

### Yêu cầu hệ thống
- **Windows 10 / 11**
- **Python 3.10+** (khuyên dùng Python 3.10–3.15)
- **Node.js 18+** (hỗ trợ `onnxruntime-node`, `@huggingface/transformers`, `ag-psd`, `tesseract.js`)

### Các bước cài đặt (chỉ mất 2 phút)

1. **Clone mã nguồn đầy đủ (bao gồm các model ONNX đang dùng & thư mục `exports/`):**
   ```bash
   git clone https://github.com/ChauNe123/AI-Design-Studio.git
   cd AI-Design-Studio
   ```

2. **Chạy script cài đặt tự động (hoặc cài tay):**
   - Nhấp đúp **`setup_home_pc.bat`**
   - Hoặc chạy trong Terminal:
     ```bash
     pip install -r requirements.txt
     npm install
     ```

3. **Khởi chạy AI Design Studio UI (`http://127.0.0.1:8788`):**
   ```bash
   python run_studio.py
   ```
   *(Lưu ý: nếu clone ở thư mục khác `D:\AI_Design_Studio`, hãy chạy trực tiếp `python run_studio.py` hoặc sửa đường dẫn trong `launch_studio.bat` và `settings.json` trỏ tới đường dẫn `Photoshop.exe` trên máy nhà nếu cần.)*

4. **Chạy nhanh pipeline qua CLI nếu muốn xuất `.PSD` trực tiếp từ 1 tấm ảnh:**
   ```python
   from core.poster_decomposer import run_commercial_poster_decomposition_pipeline
   from core.banner_decomposer import run_banner_decomposition_pipeline
   from core.retouch_analyzer import run_product_retouch_pipeline
   from core.qa_engine import export_and_qa_all
   ```

---

## 📁 Cấu Trúc Thư Mục Chính

```text
AI-Design-Studio/
├── core/                 # Toàn bộ engine phân tích, tách lớp, retouch, generate, QA & PSD bridge
├── ui/                   # Giao diện Studio web app cục bộ (HTML/CSS/JS)
├── models/               # Các model AI cục bộ (LaMa 2025jan, RMBG-1.4, SlimSAM-77, DETR, Tessdata)
│                         # (Lưu ý: Xenova/owlvit-base-patch32 148MB không dùng được loại qua .gitignore)
├── knowledge/            # Cơ sở tri thức DVF 2022 & kiến thức thiết kế dạng JSON
├── docs/                 # Tài liệu kiến trúc chi tiết từ v1.0 đến v1.5
├── exports/              # Các file .PSD hoàn chỉnh & contact sheets đã kiểm định
├── projects/             # Dự án làm việc mẫu (bao gồm melbourne_xpress_cabs)
├── tests/                # Bộ kiểm thử hồi quy (run_regression_tests.py)
├── assets/ & backups/    # Tài nguyên mẫu, font & snapshot sao lưu
├── run_studio.py         # Điểm khởi chạy ứng dụng Desktop port 8788
├── setup_home_pc.bat     # Cài đặt nhanh môi trường cho máy mới
├── package.json          # Dependencies Node.js (ag-psd, onnxruntime-node, transformers, tesseract)
└── requirements.txt      # Dependencies Python (numpy, opencv-python, Pillow)
```
