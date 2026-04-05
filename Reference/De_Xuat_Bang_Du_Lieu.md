# Đề Xuất Cấu Trúc Dữ Liệu: Bảng Tổng Hợp & Bảng Chi Tiết Hóa Đơn

Dựa trên dữ liệu thực tế đã lấy trong 30 ngày (từ 06/03/2026 đến 05/04/2026) thông qua các Request Endpoint API, tôi đã thiết kế và chuẩn hóa một hệ thống các trường dữ liệu cần thiết cho phần mềm.

Theo yêu cầu của bạn, thiết kế này sẽ chia làm 2 phần:
1. **Bảng Tổng Hợp**: Dùng cho màn hình danh sách (hiển thị nhanh, tải nhẹ).
2. **Bảng Chi Tiết (Có tên hàng hóa)**: Cấu trúc chứa chi tiết mặt hàng theo từng Line item.
3. **Cấu trúc JSON chuẩn**: Cấu trúc mẫu khi fetch API và lưu vào hệ thống/local.

---

## 1. Cấu Trúc JSON Chuẩn (Đề xuất)
Đây là cấu trúc JSON được chuẩn hóa lại, loại bỏ các trường `null` và metadata không cần thiết của GDT để việc xử lý trên giao diện trở nên tối ưu hơn.

```json
{
  "id_hoa_don": "b39bcd36-1428-4fc5-ac01-889cc1527429",
  "phan_loai": "MUA_VAO",
  "trang_thai_xly": 8,
  "thong_tin_chung": {
    "mau_so": 1,
    "ky_hieu": "C26MGA",
    "so_hoa_don": 2736943,
    "ngay_lap": "2026-04-03T17:00:00Z",
    "loai_hoa_don": "Hóa đơn điện tử giá trị gia tăng"
  },
  "ben_ban": {
    "mst": "0310510716",
    "ten": "CÔNG TY TNHH MỘT THÀNH VIÊN HÓA DƯỢC SÀI GÒN",
    "dia_chi": "173 Nguyễn Đình Chính, Phường 11, Quận Phú Nhuận..."
  },
  "ben_mua": {
    "mst": "0312650437",
    "ten": "CÔNG TY TNHH GRAB",
    "dia_chi": "Tòa nhà Mapletree Business Centre, 1060 Nguyễn Văn Linh..."
  },
  "gia_tri_tien_te": {
    "tong_tien_chua_thue": 32408.0,
    "tong_tien_thue": 2592.0,
    "tong_tien_thanh_toan": 35000.0,
    "bang_chu": "ba mươi lăm nghìn đồng"
  },
  "chi_tiet_hang_hoa": [
    {
      "stt": 1,
      "tinh_chat": 5,
      "ten_hang_hoa": "Cước phí vận chuyển mã A-963SUETWWAE7AV",
      "dvt": "Chuyến",
      "so_luong": 1.0,
      "don_gia": 30556.0,
      "thanh_tien": 30556.0,
      "thue_suat": "8%",
      "tien_thue": 2444.0
    },
    {
      "stt": 2,
      "tinh_chat": 5,
      "ten_hang_hoa": "Phí dịch vụ mã A-963SUETWWAE7AV",
      "dvt": "Chuyến",
      "so_luong": 1.0,
      "don_gia": 1852.0,
      "thanh_tien": 1852.0,
      "thue_suat": "8%",
      "tien_thue": 148.0
    }
  ]
}
```

---

## 2. Đặc Tả: Các Trường Bảng Tổng Hợp (Invoice Summary Table)
*Sử dụng dữ liệu từ endpoint `/query/invoices/purchase`, `/query/invoices/sold`*

Đây là bảng chính hiển thị cho người dùng danh sách tất cả các hóa đơn. Để bảo đảm hiệu suất, bảng này tuyệt đối **không được chứa chi tiết hàng hóa**.

| Tên Cột (Giao diện) | Mapping API Field | Định Dạng Dữ Liệu | Diễn Giải |
|---|---|---|---|
| Mã Nội Bộ (ID) | `id` | Chuỗi ký tự | ID gốc sinh bởi hệ thống thuế (Primary Key). |
| Ký Hiệu Hóa Đơn | `khhdon` | Chuỗi ký tự | Ví dụ: `C26TSG` |
| Số Hóa Đơn | `shdon` | Số tự nhiên | Ví dụ: `509`, `2736943` |
| Ngày Lập | `tdlap` | Ngày Thực Thể (DateTime)| Ngày phát hành hóa đơn |
| MST Bên Bán | `nbmst` | Chuỗi số | Mã số thuế của người bán |
| Tên Bên Bán | `nbten` | Chuỗi ký tự | Tên công ty / đơn vị xuất hóa đơn |
| Địa Chỉ Bên Bán | `nbdchi`| Chuỗi ký tự | Địa chỉ của người bán |
| MST Bên Mua | `nmmst` | Chuỗi số | Mã số thuế của người mua |
| Tên Bên Mua | `nmten` | Chuỗi ký tự | Tên công ty / cá nhân mua hàng |
| Địa Chỉ Bên Mua | `nmdchi`| Chuỗi ký tự | Địa chỉ của người mua |
| Tổng Tiền Trước Thuế | `tgtcthue` | Số thập phân | Lấy tiền trước VAT |
| Tổng Phí VAT | `tgtthue` | Số thập phân | Lấy tổng tiền chi phí VAT |
| Tổng Thanh Toán | `tgtttbso` | Số thập phân | Tổng tiền phải trả / được nhận. |
| Trạng Thái Hóa Đơn | `tthai` | Số nguyên (`Int`) | Tính chất thực tế của HĐ (Ví dụ 1: Hóa đơn Mới/Gốc, 2: Hóa đơn thay thế, 3: Điều chỉnh...). |
| Kết Quả Xử Lý (Của CQT) | `ttxly` | Số nguyên (`Int`) | Kết quả từ cơ quan thuế: 5 = Đã cấp mã, 6 = Không nhận mã, 8 = Máy tính tiền. |
| Nguồn Tải API | Bổ sung từ Client/URL | Chuỗi ký tự | Gắn giá trị dựa trên URL API khi fetch: <br>- "Hóa đơn điện tử - Đã cấp mã / Không nhận mã"<br>- "Hóa đơn máy tính tiền (SCO)..." |

---

## 3. Đặc Tả: Các Trường Bảng Chi Tiết (Invoice Details View/Table)
*Sử dụng bổ sung thêm mảng `hdhhdvu` từ endpoint `/query/invoices/detail`*

Bảng chi tiết bao gồm mọi thông tin như Bảng Tổng Hợp để tạo phiếu in, tuy nhiên để rõ ràng theo yêu cầu, giao diện chi tiết sẽ gồm 2 phần: Thông tin chung hóa đơn và Bảng Chi tiết mặt hàng.

### 3.1 Phần tóm tắt thông tin hóa đơn phía trên (Header)
Khác với bảng tổng hợp, khi in hoặc view 1 hóa đơn, ta sẽ trích lọc riêng:
- **Ký hiệu hóa đơn:** `khhdon`
- **Số hóa đơn:** `shdon`
- **Ngày lập:** `tdlap`
- **Tên Đối Tác (Bán/Mua tùy loại):** `nmten` / `nbten`
- **MST Đối Tác:** `nmmst` / `nbmst`
- **Tổng Tiền Trước Thuế:** `tgtcthue`

### 3.2 Bảng Chi Tiết Mặt Hàng (Danh sách list)
Chứa DataGrid hoặc Bảng con liệt kê các **Tên hàng hóa**:

| Tên Cột (Chi Tiết Hàng) | Mapping API Field của item trong `hdhhdvu` | Diễn Giải Quan Trọng |
|---|---|---|
| Số Thứ Tự | `stt` | Vị trí dòng hàng trên hóa đơn (1, 2, 3...) |
| **Tên Hàng Hóa/Dịch Vụ** | `ten` | Lấy tên mặt hàng/chi phí trực tiếp (Đây là mục bạn quan tâm đặc biệt). VD: "Cước phí vận chuyển..." |
| Danh Mục / Tính chất | `tchat` | Mã tính chất: Hàng hóa (1), Khuyến mãi (2), Chiết khấu (3), Ghi chú (4). |
| Đơn Vị Tính | `dvtinh` | VD: "Chuyến", "Cái", "Bộ" |
| Số Lượng | `sluong` | Dùng để tính toán (VD: `1.0`) |
| Đơn Giá | `dgia` | Số tiền quy đổi trên mỗi khối lượng/đơn vị |
| Hệ số Thuế Suất (%) | `ltsuat` hoặc `tsuat` | Chuỗi ký hiệu `8%`, `10%` hoặc số thực (`0.08`) |
| Tiền Thuế Dòng Hàng | `tthue` | Tính theo công thức hoặc lấy thẳng từ thuế của riêng item đó. |
| Thành Tiền | `thtien` | Bằng Đơn Giá x Số lượng |

### Phân tích bổ sung cho Bảng Chi Tiết (Extra Metadata):
1. Tính chất hàng hóa quan trọng vì 1 Hóa Đơn có thể có **Dòng Chiết Khấu** mang tiền âm. 
2. Một số công ty có các thông số đặc biệt khác (VD: Grab có kèm `BookingCode`, `Vehicle` lưu trong mảng `ttkhac` của từng dòng `hdhhdvu`). Tuy nhiên, về mặt quản lý tiêu chuẩn, chỉ cần trích xuất `ten` (Tên hàng hóa), `sluong`, `dgia`, và `thtien` là đủ để hiển thị.

---

## 4. Chức Năng Custom Cột (Ẩn/Hiện Trường Thông Tin)
Chức năng này giúp người dùng không bị "ngợp" thông tin. Nó sẽ được chia tách làm hai phần quản lý độc lập.

### 4.1. Custom Cột Bảng Tổng Hợp (Summary Column Chooser)
Bảng tổng hợp chủ yếu dùng để lướt, thống kê và lọc nhanh. Dựa vào các trường API đã mapping ở Mục 2, ta chia làm 2 list Cột (Mặc định và Tùy chỉnh).

- **Cột mặc định (Bắt buộc hiện):**
  - Ký Hiệu Hóa Đơn (`khhdon`), Số Hóa Đơn (`shdon`), Ngày Lập (`tdlap`)
  - Tên Đối Tác (Bán / Mua linh hoạt theo loại file)
  - Tổng Thanh Toán (`tgtttbso`)
  - Trạng Thái Hóa Đơn (`tthai`) & Kết Quả Xử Lý CQT (`ttxly`)

- **Cột tùy chọn (Cho phép checkbox ẩn/hiện):**
  - Mã Nội Bộ Hóa Đơn (`id`) - Mặc định Ẩn
  - Nguồn Tải API (URL) - Mặc định Hiện
  - MST Đối Tác, Địa Chỉ Đối Tác
  - Tên / MST / Địa chỉ đầu ngược lại (Trường hợp muốn nhìn đầy đủ bên bán lẫn mua).
  - Tổng Tiền Trước Thuế (`tgtcthue`), Tổng Tiền Thuế (`tgtthue`)

### 4.2. Custom Cột Bảng Chi Tiết (Detail Column Chooser)
Custom được áp dụng cho **Bảng (Grid) Hàng Hóa Dịch Vụ** chứa trong màn hình Chi Tiết (tương ứng Mục 3.2). 

- **Cột mặc định (Bắt buộc hiện):**
  - Số Thứ Tự (`stt`)
  - Tên Hàng Hóa / Dịch Vụ (`ten`)
  - Thành Tiền (`thtien`)

- **Cột tùy chọn (Cho phép checkbox ẩn/hiện):**
  - Danh Mục/Tính chất (`tchat`)
  - Đơn Vị Tính (`dvtinh`)
  - Số Lượng (`sluong`)
  - Đơn Giá (`dgia`)
  - Hệ số Thuế Suất (`tsuat`)
  - Tiền Thuế (`tthue`)
  - Tiền Chiết Khấu/Khuyến mãi (Bóc từ array metadata nếu cần thiết hoặc từ trường `stckhau` - Mặc định Ẩn).

*Cấu trúc này giúp lập trình viên cài đặt 2 component UI ColumnChooser khác nhau: 1 cho màn hình Main Menu, 1 cho Popup / Dialog Chi Tiết.*
