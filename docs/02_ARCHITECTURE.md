# 02 — ARCHITECTURE (v1.1)

## 1. Cấu trúc Thư mục Dự án (`D:/AI_Design_Studio/`)

```text
D:/AI_Design_Studio/
├── launch_studio.bat / run_studio.py
├── settings.json
├── package.json / node_modules/ (ag-psd, pngjs)
├── core/
│   ├── design_document.py     # Schema trung tâm DesignDocument (1.0.0)
│   ├── image_analyzer.py      # MODE A (Unicode-safe, 2x cap max_dim, LAB + floodFill)
│   ├── generate_engine.py     # MODE B (Multi-product, Reference-guided, 3 Variants)
│   ├── reference_analyzer.py  # CV Reference Analyzer (K-means palette, 3x3 saliency, lighting)
│   ├── knowledge_base.py      # Lưu & truy xuất principles, brands, qa_lessons, references_analyzed
│   ├── project_manager.py     # Autosave, Version History, Restore, Group CRUD, Integrity Check
│   ├── qa_engine.py           # QA 1 (Layers) + QA 2 (Composite) + QA 3 (Binary PSD Verify)
│   ├── psd_bridge.js          # ag-psd Export + Full Pixel/Composite/TySh Decode Verify
│   └── server.py              # ThreadingHTTPServer (127.0.0.1:8788)
├── ui/                        # 9 khu vực tương tác + Undo/Redo + Group Manager + Live Text Preview
├── knowledge/knowledge_base.json
├── assets/ (products/, logos/, fonts/FZ Poppins-*.ttf, references/)
├── projects/
├── tests/ (run_regression_tests.py, run_v1_1_acceptance_tests.py, fixtures/, output/)
└── docs/ (01..13)
```

## 2. Luồng Dữ liệu An toàn (v1.1)
- Mọi chỉnh sửa trong Layer Editor tự ghi snapshot vào Undo stack (client) và kích hoạt Autosave (`autosave_draft.json` + `.session_active`) sau 1.5s.
- Khi lưu chính thức (`/api/project/<id>/save`), server tạo phiên bản lịch sử (`versions/vNNN.json`), xóa cờ `.session_active`, re-render ảnh PNG của text nếu nội dung thay đổi, chạy `export_and_qa_all()` và cập nhật `qa_report.json`.
