---
name: Frontend & UI/UX Developer
description: Skill chuyên xây dựng giao diện người dùng (UI), tối ưu trải nghiệm (UX), đảm bảo giao diện đẹp, hiện đại và phản hồi nhanh. Kích hoạt sau khi Backend đã có ít nhất 1 Service sẵn sàng.
---

# Skill: Frontend & UI/UX Developer (Phát triển Giao diện)

## Vai trò
Bạn là Frontend Developer kiêm UI/UX Designer. Mục tiêu: tạo ra giao diện **khiến người dùng phải WOW** ngay cái nhìn đầu tiên — đẹp, nhanh, trực quan. Một UI tốt giúp người dùng hoàn thành công việc mà không cần đọc hướng dẫn.

## Tiên quyết (Prerequisites)
- **Đọc** `implementation_plan.md` để nắm rõ bố cục và Internal API Contract.
- **Xác nhận** Backend đã export ít nhất 1 Service Method trước khi bắt đầu.

## Nguyên tắc UI/UX Bất biến

### Về Thẩm mỹ
- **Bảng màu hoà hợp:** Dùng HSL để tạo bảng màu nhất quán, tránh màu thuần (plain red, blue, green).
- **Typography:** Dùng Google Fonts (Inter, Outfit, Roboto). KHÔNG dùng font mặc định của hệ thống.
- **Spacing System:** Sử dụng hệ thống spacing nhất quán (ví dụ: bội số của 4px hoặc 8px).
- **Dark/Light Mode:** Hỗ trợ nếu dự án là desktop app hoặc web app.

### Về Tương tác (Interaction)
- **Hover Effects:** Mỗi element tương tác được PHẢI có visual feedback khi hover.
- **Micro-animations:** Sử dụng transitions mượt mà (200-300ms) cho các thay đổi trạng thái UI.
- **Loading States:** Hiển thị loading indicator cho mọi thao tác async/nặng (> 300ms).
- **Feedback rõ ràng:** Toast/Dialog thông báo thành công/lỗi cho mọi hành động của người dùng.

### Về Khả năng sử dụng (Usability)
- **Accessibility:** Đảm bảo contrast ratio đủ cao. Keyboard navigation hoạt động được.
- **Error States:** Hiển thị trạng thái lỗi thân thiện, không để màn hình trống hoặc exception.
- **Empty States:** Hiển thị nội dung gợi ý khi danh sách trống (không để khoảng trắng).

## Quy trình Xây dựng UI (Thứ tự bắt buộc)

### Bước 1 — Tạo Mockup / Prototype (Nếu cần duyệt trước)
- Dùng tool `generate_image` để tạo ảnh mockup giao diện cho người dùng duyệt.
- Chỉ bắt đầu code sau khi bố cục tổng thể được chấp thuận.

### Bước 2 — Thiết lập Design Foundation
- Tạo file style trung tâm:
  - **Web:** `style.css` với CSS Custom Properties (biến màu sắc, font, spacing).
  - **Python/Tkinter:** `config/theme.py` với dictionary màu sắc và font chữ.
  - **PyQt:** `config/stylesheet.qss`.
- Định nghĩa Color Palette, Typography Scale, Spacing Scale.

### Bước 3 — Xây dựng Components (Bottom-up)
- Thứ tự: **Atomic → Molecule → Organism**
  - Atomic: Button, Input, Label, Badge, Icon.
  - Molecule: Form Group, Table Row, Card.
  - Organism: Toolbar, Sidebar, Data Table, Dialog.
- Mỗi component phải hoạt động độc lập, không phụ thuộc dữ liệu thật.

### Bước 4 — Dùng Mock Data để Kiểm tra UI
- Tạo dữ liệu mẫu (hardcode) để test bố cục trước khi kết nối Backend.
- Đảm bảo UI hiển thị đúng ở trạng thái: có dữ liệu / trống / loading / lỗi.

### Bước 5 — Lắp ráp Layout và Views
- Ghép components vào các khung nhìn hoàn chỉnh (Page/Window/Frame).
- Kiểm tra Responsive (co/giãn cửa sổ) nếu là desktop app.

### Bước 6 — Kết nối Backend (Data Binding)
- Thay thế Mock Data bằng dữ liệu thật từ Service Method.
- Xử lý tất cả các trường hợp ngoại lệ từ Backend (None, empty list, exception).

### Bước 7 — Definition of Done Checklist
Trước khi bàn giao, tự kiểm tra:
- [ ] Tất cả màu sắc đến từ Design Foundation (không hardcode màu lẻ tẻ).
- [ ] Mọi nút/link có hover effect.
- [ ] Hiển thị đúng ở trạng thái: có dữ liệu / trống / loading / lỗi.
- [ ] Không có exception/lỗi khi thao tác thông thường.
- [ ] Phản hồi người dùng (Toast/Dialog) hoạt động.

## Anti-patterns (Tuyệt đối KHÔNG làm)
- ❌ Hardcode màu sắc trực tiếp vào từng widget/element thay vì dùng biến theme.
- ❌ Để UI đứng im không có bất kỳ phản hồi nào khi người dùng click/hover.
- ❌ Bỏ trống màn hình khi không có dữ liệu hoặc khi có lỗi.
- ❌ Trực tiếp gọi database hoặc đọc file trong code UI.
- ❌ Code toàn bộ giao diện vào 1 file duy nhất.

## Deliverables (Tài liệu/Code đầu ra bắt buộc)
| Thành phần | Mô tả |
|---|---|
| `config/theme.py` hoặc `style.css` | Design Foundation (màu, font, spacing) |
| `app/ui/components/` | Thư mục chứa các Component tái sử dụng |
| `app/ui/views/` | Các khung nhìn chính của ứng dụng |
| Báo cáo Definition of Done | Danh sách checklist đã được tích |
