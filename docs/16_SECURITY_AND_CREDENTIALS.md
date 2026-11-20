# SECURITY & CREDENTIAL STORAGE (`core/credential_store.py`)

## 1. Lưu trữ API Key trên Windows Credential Manager

- V1.2 tuyệt đối **không lưu API Key** trong mã nguồn, `settings.json`, `ai_providers.json`, `design_document.json`, file log hay ảnh/PSD xuất ra.
- Tệp `core/credential_store.py` gọi trực tiếp Win32 API của `advapi32.dll` thông qua Python `ctypes`:
  - `CredWriteW` (`CRED_TYPE_GENERIC`, `CRED_PERSIST_LOCAL_MACHINE`, TargetName: `AIDesignStudio/<provider_id>`)
  - `CredReadW` + `CredFree`
  - `CredDeleteW`
- Dữ liệu khóa được mã hóa UTF-16LE và bảo vệ bởi Windows DPAPI / Credential Manager của người dùng Windows hiện tại.

---

## 2. Che giấu Khóa (Masking & Redaction)

- `get_public_status()` trả về `has_credential` (boolean) và `credential_hint` qua `mask_key_hint()` (ví dụ chỉ hiển thị 4 ký tự đầu/cuối hoặc `"Not configured"`), **không bao giờ** trả raw secret qua `/api/providers`.
- Đã kiểm thử thực tế tạo, đọc, xóa secret tạm trong `tests/run_v1_2_tests.py` và kiểm chứng JSON công khai không chứa chuỗi `sk-`.

---

## 3. An toàn Dữ liệu Người dùng & Kiểm tra Input

- Không tự động upload ảnh gốc hay crop layer khi chưa có thao tác mở modal xác nhận trong `HYBRID` mode.
- Mọi endpoint nhận ảnh (`Base64`) bắt lỗi ảnh hỏng/giả mạo trả mã `400` và dọn sạch thư mục tạm nếu thất bại (`shutil.rmtree(pdir, ignore_errors=True)`).
