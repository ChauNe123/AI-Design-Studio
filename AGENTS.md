# AGENTS.md — NGUYÊN TẮC VẬN HÀNH & GIAO THỨC TIẾT KIỆM TOKEN (AI DESIGN STUDIO)

> **Workspace Chuẩn Độc Lập:** `D:\AI_Design_Studio_V2`
> **Mục tiêu:** Đảm bảo mọi phiên AI mới tiếp quản dự án nhanh nhất, tốn ít token nhất, phản ánh đúng 100% thực trạng source code và không phụ thuộc vào lịch sử hội thoại cũ.

---

## 1. QUY TRÌNH ĐỌC TỐI GIẢN KHI BẮT ĐẦU MỌI PHIÊN CHAT (TOKEN-SAVING PROTOCOL)

Mỗi khi mở phiên làm việc mới, AI **bắt buộc** thực hiện đúng 5 bước theo thứ tự sau và **dừng đọc ngay** khi đã đủ thông tin cho task hiện tại:

1. **Bước 1:** Đọc `AGENTS.md` (file này) để nắm kỷ luật vận hành và cổng an toàn.
2. **Bước 2:** Đọc `PROJECT.md` để nắm trạng thái thực tế của source code, module chính, việc đang làm dở và lỗi đã biết.
3. **Bước 3:** Đọc `DECISIONS.md` **chỉ khi** task liên quan đến kiến trúc, định dạng `.PSD`, mô hình AI/ONNX, quy chuẩn thiết kế hoặc cổng kiểm duyệt.
4. **Bước 4:** Tra cứu `PROJECT_DOC_INDEX.md` khi cần tìm tài liệu kỹ thuật chuyên sâu cho một module cụ thể.
5. **Bước 5:** Chỉ mở **đúng 1–2 file tài liệu kỹ thuật hoặc file code** trực tiếp liên quan đến task đang giao.

### 🚫 Nghiêm cấm lãng phí ngữ cảnh:
- **KHÔNG** quét hoặc đọc toàn bộ thư mục `docs/` hay `docs/external_refs/` cùng lúc.
- **KHÔNG** đọc các file lịch sử (`07_CHANGELOG.md`, `TONG_HOP_UPDATE_AI_DESIGN_STUDIO.md`, `TASK_LOG.md`) trừ khi cần tra cứu lịch sử thay đổi hoặc cập nhật nhật ký cuối phiên.
- **KHÔNG** đọc lại các snapshot cũ hoặc các thư mục ngoài workspace (`D:\AI\TESTER`, `D:\Test psd`, `D:\AI_Design_Studio`).

---

## 2. THỨ BẬC SỰ THẬT & XỬ LÝ MÂU THUẪN (SOURCE OF TRUTH)

1. **Source code thực tế (`core/`, `ui/`, `knowledge/knowledge_base.json`) là nguồn sự thật cao nhất** về hành vi hiện hành của hệ thống.
2. Nếu tài liệu Markdown mô tả khác với source code:
   - **Tin vào source code đã xác minh**, không tin mù quáng vào tuyên bố cũ trong tài liệu.
   - **Báo cáo rõ mâu thuẫn** cho người dùng trước khi sửa tài liệu hoặc sửa code.
3. **Tuyệt đối không suy đoán:** Không bịa đặt số liệu QA, không tự gán trạng thái `"PASS"` hay `"10/10"` khi chưa chạy kiểm chứng thực tế và chưa qua mắt người dùng.

---

## 3. NGUYÊN TẮC LÀM VIỆC BẮT BUỘC

1. **Không tự ý sửa ngoài phạm vi:** Chỉ chỉnh sửa đúng module/file thuộc yêu cầu hiện tại của người dùng.
2. **Không tự ý thay đổi quyết định đã chốt:** Mọi quyết định trong `DECISIONS.md` (`D-01` → `D-06`) là bất biến trừ khi người dùng ra lệnh thay đổi trực tiếp.
3. **Tuân thủ Quy tắc Xuất `.PSD` & Người Dùng QC Trực Tiếp Trong Photoshop (`D-05` — Cập nhật `2026-11-25`):**
   - Sau khi xử lý tách layer và tái tạo nền, hệ thống **được phép xuất ngay file `.PSD`** để người dùng mở và QC trực tiếp trong Adobe Photoshop. Có thể xuất kèm `visual_audit_sheet.jpg` / `background_cleaned.jpg` để xem nhanh, nhưng ảnh đó **không phải bước chặn xuất `.PSD`**.
   - **CẤM** AI tự kết luận chất lượng hình ảnh hoặc tự ghi `"đã QC"` / `"PASS"` thay người dùng.
4. **Kiểm tra trước và sau khi thực hiện:**
   - Trước khi sửa code: đọc đúng hàm/module liên quan để hiểu đầu vào, đầu ra và phụ thuộc.
   - Sau khi sửa code: chạy kiểm tra cú pháp/import/test mục tiêu và đối chiếu kết quả trực quan (nếu là xử lý ảnh).
5. **An toàn tài liệu & dữ liệu:**
   - Không xóa, đổi tên, di chuyển hoặc ghi đè tài liệu gốc khi chưa được phép.
   - Không lưu khóa bí mật (API Key/Password) dạng rõ vào file cấu hình hoặc tài liệu dự án.

---

## 4. QUY TẮC CẬP NHẬT BỘ NHỚ TRUNG TÂM SAU MỖI TASK

Khi hoàn thành một đầu việc có thay đổi trạng thái dự án:
- Cập nhật ngắn gọn mục **Trạng thái hiện tại / Đang thực hiện / Việc tiếp theo** trong `PROJECT.md`.
- Ghi thêm 1 dòng nhật ký vào `TASK_LOG.md` (Ngày, Tóm tắt, File ảnh hưởng, Kết quả kiểm chứng, Trạng thái).
- Chỉ ghi vào `DECISIONS.md` khi người dùng **chính thức chốt** một quyết định kiến trúc/quy trình mới (không ghi đề xuất chưa duyệt).
- Chỉ cập nhật `PROJECT_DOC_INDEX.md` khi có thêm tài liệu `.md` mới hoặc phát hiện mâu thuẫn tài liệu mới.
