# DECISIONS.md — SỔ ĐĂNG KÝ QUYẾT ĐỊNH ĐÃ CHỐT (CONFIRMED DECISIONS)

> **Quy tắc nghiêm ngặt:** File này **chỉ lưu các quyết định đã được người dùng xác nhận hoặc chỉ thị trực tiếp**. Tuyệt đối không ghi các đề xuất tự suy diễn của AI chưa được phê duyệt.

---

## D-01: Ưu tiên Xử lý Cục bộ Offline & Cổng Quyền Riêng Tư (`LOCAL_ONLY`)
- **Trạng thái:** Đã chốt & Đang áp dụng (`core/ai_providers.py`, `models/`).
- **Nội dung:** Toàn bộ pipeline tách nền (`RMBG-1.4`), phân vùng (`SlimSAM`), phát hiện vật thể (`DETR`), tái tạo nền (`LaMa 2025jan ONNX`), OCR (`Tesseract vie+eng`) và đóng gói `.PSD` (`ag-psd`) phải hoạt động độc lập 100% Offline trên máy cá nhân. Chế độ mặc định là `LOCAL_ONLY`; không gửi ảnh của người dùng ra API đám mây nếu chưa bật `HYBRID` và xác nhận rõ ràng. Không lưu API Key dạng rõ trong JSON dự án (dùng Windows Credential Manager qua `core/credential_store.py`).

## D-02: Kiến trúc Không Phá Hủy (`DesignDocument v1.2.0`) & Chuẩn Xuất `.PSD` Chuyên Nghiệp
- **Trạng thái:** Đã chốt & Đang áp dụng (`core/design_document.py`, `core/psd_bridge.js`).
- **Nội dung:**
  - Mọi pipeline phân rã, tạo mới hoặc retouch đều hội tụ về cấu trúc `DesignDocument` (`SCHEMA_VERSION = "1.2.0"`).
  - Với chữ (Typography) trong ấn phẩm phức tạp: duy trì song song layer pixel gốc giữ nguyên hiệu ứng (`*_OrigFX`, hiển thị mặc định) và layer chữ có thể gõ sửa (`Editable TySh`, ẩn sẵn hoặc bật tùy chọn) để vừa bảo toàn 100% giao diện gốc vừa cho phép Designer sửa nội dung.
  - Với Retouch & Hiệu ứng: xuất **Live Photoshop Adjustment Layers** (`Curves`, `Hue/Saturation`, `Vibrance`, `Color Balance`, `Selective Color`, `Brightness/Contrast`) kèm Layer Mask riêng và **Live Layer Styles (`lmfx`)** thay vì nướng cứng (bake) toàn bộ hiệu ứng vào ảnh phẳng.

## D-03: Tích hợp Học thuật Chuẩn Quốc tế DVF 2022 & Bộ Font Tiếng Việt Thương Mại
- **Trạng thái:** Đã chốt & Đang áp dụng (`knowledge/knowledge_base.json`, `core/generate_engine.py`, `core/qa_engine.py`).
- **Nội dung:**
  - Mode B và bộ kiểm định thẩm mỹ QA 2 áp dụng các quy tắc định lượng từ giáo trình *Design & Visual Fundamentals (DVF 2022 - Arena Multimedia)*: 10 phong trào nghệ thuật lịch sử, 6 quy tắc hòa sắc theo tỷ lệ `60-30-10`, tỷ lệ phân cấp chữ `Headline / Subheadline >= 2.0x`, và khoảng trắng âm bản tối thiểu `20–25%` diện tích canvas.
  - Sử dụng bộ font Việt hóa chuẩn `FZ Poppins` (`assets/fonts/`) để không lỗi dấu tiếng Việt.

## D-04: Tiêu chuẩn Chất lượng V1.6.0 — "Zero-Defect" Trong Tái Tạo Nền & Bóc Tách Vật Thể
- **Trạng thái:** Đã chốt theo chỉ thị trực tiếp của người dùng (`BAN_CAP_NHAT_TOAN_DIEN_V1.6_ZERO_DEFECT.md`).
- **Nội dung:**
  1. **Cấm tuyệt đối `np.interp()` kéo sọc màu rẻ tiền** hoặc làm mờ nhòe bẩn khi xóa nền: bắt buộc giãn nở mask `15–20px` quanh biên vật thể/hào quang chữ, dùng mô hình Inpaint 2D thực thụ (`LaMa ONNX` kết hợp 2D PDE / cấu trúc hình học 2 chiều) và đồng nhất hạt nhiễu (`grain matching`) với nền gốc.
  2. **Bắt buộc Vẽ bù Phần bị Che khuất (Amodal Completion):** Các vật phẩm bị chữ, ruy-băng hoặc vật khác đè lên (như Nón kết, Áo thun, Vòng tay, Cọc xu, Thân xe, Con đường) sau khi tách ra phải được khôi phục nguyên vẹn hình dáng 100%, **tuyệt đối không thủng lỗ hay đứt đoạn**.
  3. **Bóc tách Nguyên tử (Atomic Disentanglement) & Giữ khối 3D:** Tách rời từng vật phẩm độc lập (Áo thun riêng, từng Móc khóa riêng, Dây thẻ riêng, từng ngôi sao/confetti riêng) và bảo toàn cấu trúc khối 3D Isometric (như 3 bục vinh quang), không biến khối 3D thành hình hộp phẳng.

## D-05: Xuất Trực Tiếp `.PSD` Để Người Dùng QC Trong Photoshop & Cấm AI Tự Kết Luận Chất Lượng
- **Trạng thái:** Đã cập nhật theo chỉ thị trực tiếp của người dùng (`2026-11-25` — Phương án A, thay thế cơ chế chặn xuất PSD cũ).
- **Nội dung:** Sau khi chạy phân rã và tái tạo nền, hệ thống **được phép xuất ngay file `.PSD`** để người dùng mở và QC trực tiếp trong Adobe Photoshop (có thể xuất kèm ảnh `visual_audit_sheet.jpg` / `background_cleaned.jpg` để xem nhanh, nhưng ảnh audit không phải bước chặn xuất `.PSD`). Tuy nhiên, AI **tuyệt đối không được tự kết luận chất lượng hình ảnh** hoặc tự ghi `"đã QC"` / `"PASS"` thay người dùng.

## D-06: Thiết lập Bộ Nhớ Quản Lý Trung Tâm & Tách Sang Workspace Sạch `D:\AI_Design_Studio_V2`
- **Trạng thái:** Đã chốt (`2026-11-25`).
- **Nội dung:**
  - Giữ nguyên hiện trạng 100% các thư mục cũ (`D:\AI\TESTER`, `D:\AI_Design_Studio`, `D:\Test psd`), không xóa, đổi tên hay ghi đè bất kỳ tài liệu `.md` nào đã có (đặc biệt không chạm vào `D:\AI\TESTER\AGENTS.md` của dự án GoWash).
  - Khởi tạo dự án độc lập hoàn toàn tại `D:\AI_Design_Studio_V2` tích hợp sẵn bộ 5 file Quản lý Trung tâm (`AGENTS.md`, `PROJECT.md`, `DECISIONS.md`, `TASK_LOG.md`, `PROJECT_DOC_INDEX.md`) để mọi phiên chat mới làm việc trực tiếp trên `D:\AI_Design_Studio_V2`, chấm dứt phụ thuộc vào thư mục cũ.
