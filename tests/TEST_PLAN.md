# TEST PLAN — Tool HDDT v2

Bản kế hoạch kiểm thử toàn diện cho ứng dụng Quản lý Hóa đơn Điện tử v2.

---

## 1. Thông tin chung
- **Phiên bản:** v2.0.0
- **QA:** Antigravity (Assistant)
- **Ngày:** 2026-03-29

---

## 2. Kịch bản kiểm thử (Test Cases)

### TC-01: Đăng nhập & Quản lý tài khoản
- **Mô tả:** Kiểm tra luồng đăng nhập cổng thuế và lưu trữ MST.
- **Bước thực hiện:**
  1. Mở app, tại Login View, nhấn "+ Thêm tài khoản".
  2. Nhập `0123456789, CONG TY TEST, MatKhau123`.
  3. Kiểm tra MST hiện trong dropdown.
  4. Nhấn "Đăng nhập" (với captcha giả định hoặc thật).
- **Kết quả mong đợi:** 
  - Tài khoản được lưu vào DB.
  - Password lưu an toàn vào Windows Keyring.
  - Status bar cập nhật "MST: 0123456789 (Connected)".
- **Trạng thái:** [ ] To-Do

### TC-02: Import Hóa đơn Offline (Happy Path)
- **Mô tả:** Kiểm tra việc đọc file XML EasyInvoice.
- **Bước thực hiện:**
  1. Vào view "Danh sách HĐ".
  2. Bấm "Import" -> Chọn file `tests/fixtures/sample_easyinvoice.xml`.
- **Kết quả mong đợi:** 
  - Bảng hiện 1 dòng hóa đơn với đầy đủ thông tin Tầng 1.
  - Toast thông báo "Đã import 1 HĐ".
- **Trạng thái:** [ ] To-Do

### TC-03: Two-Tier Data & Auto-Discovery
- **Mô tả:** Kiểm tra khả năng tự phát hiện trường động.
- **Bước thực hiện:**
  1. Sau khi import TC-02, vào "Cài đặt".
  2. Kiểm tra phần "Fields đã phát hiện".
- **Kết quả mong đợi:** Hiện danh sách fields: `PortalLink`, `Fkey`, `VATAmount`... với prefix `hdr_`, `itm_` etc.
- **Trạng thái:** [ ] To-Do

### TC-04: Column Chooser & Danh sách động
- **Mô tả:** Kiểm tra việc bật/tắt cột động.
- **Bước thực hiện:**
  1. Tại "Danh sách HĐ", bấm "Cột" (nút ☰).
  2. Tìm field động mới phát hiện (VD: `PortalLink`), tích chọn "Visible".
  3. Bấm "Áp dụng".
- **Kết quả mong đợi:** Bảng `tksheet` hiện thêm cột mới với dữ liệu tương ứng.
- **Trạng thái:** [ ] To-Do

### TC-05: Export Excel (Professional Formatting)
- **Mô tả:** Kiểm tra xuất file XLSX với định dạng số.
- **Bước thực hiện:**
  1. Tại "Danh sách HĐ", bấm "Export CT" (Chi tiết).
  2. Mở file Excel vừa xuất.
- **Kết quả mong đợi:** 
  - Các cột số tiền có định dạng `#,##0` (có dấu chấm phân cách nghìn).
  - Có đủ sheet Tổng hợp và Chi tiết.
- **Trạng thái:** [ ] To-Do

### TC-06: Edge Case - File lỗi
- **Mô tả:** Kiểm tra xử lý khi file XML không đúng cấu trúc.
- **Bước thực hiện:**
  1. Import một file XML rác hoặc không phải hóa đơn.
- **Kết quả mong đợi:** 
  - Không crash ứng dụng.
  - Toast thông báo "0 HĐ (1 lỗi)".
  - Trạng thái dòng hiển thị "Lỗi cấu trúc".
- **Trạng thái:** [ ] To-Do

---

## 3. Checklist UI/UX
- [ ] Responsive: Thay đổi kích thước cửa sổ không vỡ layout.
- [ ] Theme switch: Chuyển Dark/Light mượt mà, text dễ đọc.
- [ ] Loading: Hiện progress bar khi đang parse XML/Download.
- [ ] Scrollbar: Hoạt động tốt trong bảng 1000+ dòng.
