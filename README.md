# AI Design Studio V2

Ứng dụng desktop Windows hướng tới xử lý ảnh thiết kế cục bộ và xuất PSD nhiều layer để người dùng tiếp tục chỉnh sửa, kiểm tra trong Adobe Photoshop.

## Trạng thái

Đây là snapshot V2 đang phát triển, chưa phải bản phát hành hoàn tất. Kết quả PSD cần được mở và QC trực quan trong Photoshop; việc kiểm tra cấu trúc file tự động không đồng nghĩa với QC thiết kế đạt.

- Dự án demo hiện tại: `projects/hera_car_rental_v2_baseline/`
- Ghi chú trạng thái và công việc tiếp theo: `PROJECT.md` và `TASK_LOG.md`
- Hướng dẫn cài đặt/chạy: `INSTALL.md`

## Phạm vi đồng bộ lên GitHub

Repo không chứa `node_modules/`, `tests/output/`, cache Python hoặc model OWL-ViT không được dùng theo cấu hình `.gitignore`. Các model ONNX khác đang được dự án sử dụng vẫn nằm trong repo. Hãy dùng `.gitignore` làm nguồn tham chiếu cho các file không đồng bộ.

## Bảo mật

Không commit API key, mật khẩu hoặc thông tin cá nhân. Cấu hình môi trường và đường dẫn cài Photoshop có thể cần điều chỉnh theo máy Windows đang chạy dự án.
