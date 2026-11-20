# 02 — ARCHITECTURE (`D:\AI_Design_Studio\`)

## 1. Cấu trúc Thư mục Độc lập

```text
D:\AI_Design_Studio\
├── launch_studio.bat          # Khởi chạy ứng dụng Windows 1-click
├── run_studio.py              # Launcher mở server + cửa sổ Edge/Chrome App (--app)
├── package.json / node_modules/ (ag-psd, pngjs)
├── settings.json              # Cấu hình Photoshop path, upscale 2x, max_dim
├── core/
│   ├── design_document.py     # Schema dữ liệu trung tâm (DesignDocument)
│   ├── image_analyzer.py      # MODE A: Phân tích, tách lớp, inpaint nền, upscale 2x
│   ├── generate_engine.py     # MODE B: Thiết kế mới từ Asset + Brand + Knowledge
│   ├── knowledge_base.py      # Quản lý Design Knowledge JSON
│   ├── qa_engine.py           # QA 1 (Layers) + QA 2 (Composite) + QA 3 (PSD Round-trip)
│   ├── psd_bridge.js          # Unified ag-psd Exporter & Verifier
│   └── server.py              # HTTP API Server (127.0.0.1:8788)
├── ui/
│   ├── index.html, styles.css, app.js
├── knowledge/knowledge_base.json
├── assets/ (products/, logos/, fonts/, references/)
├── projects/                  # Thư mục lưu từng dự án độc lập
├── tests/ (fixtures/, output/, run_regression_tests.py)
├── backups/legacy_redesign_studio/
└── docs/ (01..09)
```

## 2. Luồng Dữ liệu Trung tâm (`DesignDocument`)

Mọi tính năng (**MODE A Redesign**, **MODE B Generate**, **Layer Editor**, **QA Engine**, **PSD Export**) dùng chung đúng 1 file `projects/<project_id>/design_document.json`:

- Mỗi layer chứa: `id`, `name`, `type`, `source_file`, `x`, `y`, `width`, `height`, `z_index`, `opacity`, `visible`, `blend_mode`, `mask_file`, `ai_reconstructed`, `text_data`, `group`, `metadata`.
- Khi người dùng chỉnh sửa trong **Layer Editor** (di chuyển, đổi opacity, scale, hue/sat/bright, sửa chữ, đổi thứ tự z-index) và bấm **Lưu thay đổi & Xuất PSD**:
  1. `server.py` cập nhật `design_document.json` và render lại ảnh PNG của text layer nếu chữ thay đổi.
  2. `qa_engine.py` pre-render mọi layer có bộ lọc/scale vào `export_cache/`.
  3. `psd_bridge.js` đóng gói thành `<project_id>_studio.psd` khớp 1:1 với bản Preview.
  4. `qa_engine.py` chạy lại đủ QA 1, QA 2, QA 3 và lưu `qa_report.json`.
