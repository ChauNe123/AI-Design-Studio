# AI DESIGN STUDIO V1.2 — ARCHITECTURE

**Schema Version:** `1.2.0` (`D:/AI_Design_Studio/core/design_document.py`)  
**Runtime Stack:** Python `3.15.2` + Node.js `v24.18.0` (`@huggingface/transformers@4.3.2`, `onnxruntime-node@1.30.0`, `tesseract.js@7.0.0`, `ag-psd`, `pngjs`)  
**Default Privacy Mode:** `LOCAL_ONLY` (100% offline processing on CPU)

---

## 1. Kiến trúc Tổng thể V1.2

V1.2 nâng cấp trực tiếp trên nền tảng `DesignDocument` và hệ thống 3 tầng QA của v1.1 mà không viết lại hay phá vỡ pipeline v1.1 (`MODE A v1.1`, `MODE B`, `Project History`, `Knowledge Base`).

```text
[Web UI: ui/index.html + ui/app.js + ui/styles.css]
        │  REST/JSON + Base64
        ▼
[HTTP Backend: core/server.py]
  ├── Semantic Redesign:  core/semantic_analyzer.py
  ├── Segmentation:       core/segmentation_engine.py  ──► core/ai_vision_bridge.mjs (RMBG-1.4 / SlimSAM-77)
  ├── Editable Type:      core/typography_engine.py    ──► core/ai_vision_bridge.mjs (Tesseract.js vie+eng)
  ├── Reconstruction:     core/reconstruction_engine.py──► core/ai_providers.py ──► core/credential_store.py
  ├── Non-Destructive:    core/effects_engine.py       (scale, rotate, crop, tone, blur, glow, shadow, overlay)
  ├── QA & Export Cache:  core/qa_engine.py            ──► core/psd_bridge.js (ag-psd + export_offset)
  └── Design Document:    core/design_document.py      (Schema 1.2.0 + v1.1 -> v1.2 migration)
```

---

## 2. Thiết kế Hybrid Python + Node ONNX Bridge

Do môi trường chạy Python `3.15.2` chưa có prebuilt wheel cho `onnxruntime`, nhưng Node.js `v24.18.0` chạy ổn định `onnxruntime-node@1.30.0`, v1.2 sử dụng cầu nối nhẹ `core/ai_vision_bridge.mjs` qua `subprocess.run`:

1. `node core/ai_vision_bridge.mjs detect <inImg> [thresh]`: chạy `Xenova/detr-resnet-50` (`q8` ONNX) tự động nhận diện vật thể.
2. `node core/ai_vision_bridge.mjs rmbg <inImg> <outMask>`: chạy `briaai/RMBG-1.4` (`q8` quantized ONNX) tách foreground mask.
3. `node core/ai_vision_bridge.mjs slimsam <inImg> <ptsJson> <outMask>`: chạy `Xenova/slimsam-77-uniform` (`q8` ONNX) với điểm `+`/`-`, `mask_level` (`0`, `1`, `2`) và ROI Zoom-In.
4. `node core/ai_vision_bridge.mjs lama_inpaint <inImg> <inMask> <outImg>`: chạy `inpainting_lama_2025jan.onnx` tái tạo nền sạch tự nhiên.
5. `node core/ai_vision_bridge.mjs ocr <inImg> <outJson>`: chạy `tesseract.js@7.0.0` ngôn ngữ `vie+eng`, trả về từng dòng kèm `bbox`, `baseline`, `confidence`, word boxes.

Toàn bộ model AI được cache cục bộ tại `D:/AI_Design_Studio/models/` (`hf_cache/`, `lama/` và `tessdata/`), không cần kết nối Internet sau lần tải đầu tiên. Chi tiết cấu hình và benchmark từng mô hình xem tại [20_MODELS_AND_UPGRADES.md](20_MODELS_AND_UPGRADES.md).

---

## 3. DesignDocument Schema `1.2.0`

Tệp `core/design_document.py` mở rộng backward-compatible qua hàm `migrate_document_v1_to_v1_2()`:

- **Cấp Document:** bổ sung `semantic_objects[]`, `api_tasks[]`, `warnings[]`.
- **Cấp Layer:** bổ sung `original_source_file`, `locked`, `rotation`, `crop`, `adjustments` (`hue`, `sat`, `bright`, `contrast`, `exposure`, `temperature`, `shadow`, `highlight`), `effects` (`feather`, `blur`, `glow`, `drop_shadow`, `color_overlay`, `gradient_overlay`), `text_reconstruction`, `reconstruction_history`, `confidence_score`, `warnings`.
- `export_override_file` và `export_offset` trong `layer.metadata` do `qa_engine.prepare_export_cache()` quản lý để layer nguồn gốc (`original_source_file`) luôn bất biến.
