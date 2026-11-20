# HYBRID AI ENGINE & PRIVACY GOVERNANCE (`core/ai_providers.py`)

## 1. Chính sách Mặc định `LOCAL_ONLY`

- Khi khởi tạo và trong mọi tác vụ mặc định, hệ thống khóa ở chế độ **`LOCAL_ONLY`**.
- Toàn bộ Semantic Redesign, RMBG-1.4, SlimSAM-77, Tesseract Vietnamese OCR, Inpaint nền và PSD Export đều chạy **100% trên CPU máy cục bộ**, không thực hiện bất kỳ kết nối mạng gửi ảnh nào.

---

## 2. Chế độ `HYBRID` & Cổng Xác nhận Người dùng

Để gửi vùng ảnh lên Cloud AI (`openai_image`, `google_gemini`, `replicate`), hệ thống bắt buộc vượt qua **5 lớp kiểm tra tuần tự** trong `AIProviderManager.execute_cloud_inpaint()`:

1. `cfg["mode"] == "HYBRID"` (từ chối ngay nếu đang `LOCAL_ONLY`).
2. `provider["enabled"] == True` (provider cụ thể phải được bật).
3. `user_confirmed == True` (trước khi gọi, UI phải gọi `/api/providers/preview_permission` và mở **Privacy Permission Modal** hiển thị tên provider, model, vùng ảnh, ước tính USD để người dùng bấm xác nhận).
4. **Budget Cap Check:** `total_est_cost_usd + est_cost <= monthly_budget_usd` (từ chối nếu vượt ngân sách tháng).
5. **Credential Verification:** Đọc key từ Windows Credential Manager (`read_api_key`). Nếu thiếu key hoặc API lỗi/timeout, trả về `fallback_to_local = True` và tự động rơi về `algorithmic_inpaint` cục bộ để không làm mất công việc.

---

## 3. Theo dõi Chi phí & Nhật ký Sử dụng

- Tệp `D:/AI_Design_Studio/api_usage_log.json` lưu số lần gọi, tổng chi phí ước tính (`total_est_cost_usd`), và lịch sử 100 tác vụ gần nhất (`SUCCESS`, `BLOCKED_LOCAL_ONLY`, `BLOCKED_NO_PERMISSION`, `BLOCKED_BUDGET`, `ERROR_FALLBACK`).
- **Tách biệt Adapter:** Hiện tại endpoint Gemini `generateContent` đã nối sẵn HTTPS client thực thụ; OpenAI image edit và Replicate prediction kiểm tra kết nối credentialed GET thật (`/v1/models`, `/v1/account`) trong `test_connection()`, và trong tác vụ inpaint sẽ trả fallback an toàn nếu chưa cấu hình key hoặc transport multipart.
