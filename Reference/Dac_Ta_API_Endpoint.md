# Đặc Tả Dữ Liệu Các API Tra Cứu Hóa Đơn Điện Tử

Dựa trên kết quả phản hồi thực tế từ các endpoint API của Tổng cục Thuế (GDT), dưới đây là đặc tả các trường dữ liệu quan trọng khi thực hiện Request Tổng hợp (danh sách hóa đơn) và Request Chi tiết (review 1 hóa đơn).

---

## 1. Request Tổng Hợp (Truy vấn danh sách hóa đơn)

Các endpoint dạng `/query/invoices/purchase`, `/query/invoices/sold` hoặc `/sco-query/...` với các tham số tìm kiếm trả về danh sách các hóa đơn thỏa mãn điều kiện.

### Khung phản hồi (Response Structure)
Khi gửi request tổng hợp, dữ liệu trả về là một Object JSON bao gồm:
- `datas` (Array): Mảng chứa các đối tượng tóm tắt của từng hóa đơn.
- `total` (Integer): Tổng số hóa đơn khớp với điều kiện tìm kiếm.
- `state` (String / Null): Mã trạng thái (dùng như cursor để phân trang, load trang tiếp theo).
- `time` (Integer): Thời gian truy vấn (ms).

### Cấu trúc một đối tượng hóa đơn trong `datas` (Invoice Summary)
Mỗi phần tử trong mảng `datas` cung cấp các trường thông tin chung quan trọng sau (không bao gồm chi tiết hàng hóa):

| Trường | Kiểu dữ liệu | Ý nghĩa |
|---|---|---|
| **Thông tin người bán** | | |
| `nbmst` | String | Mã số thuế người bán |
| `nbten` | String | Tên người bán |
| `nbdchi` | String | Địa chỉ người bán |
| **Thông tin người mua** | | |
| `nmmst` | String | Mã số thuế người mua |
| `nmten` | String | Tên người mua |
| `nmdchi` | String | Địa chỉ người mua |
| **Định danh hóa đơn** | | |
| `khmshdon` | Integer | Ký hiệu mẫu số hóa đơn (VD: 1, 2) |
| `khhdon` | String | Ký hiệu hóa đơn (VD: `C26TSG`) |
| `shdon` | Numeric/Str| Số hóa đơn (VD: 509) |
| `hdon`, `thdon`, `tlhdon`| String | Phân loại hóa đơn (VD: "01", "Hóa đơn GTGT")|
| **Thời gian & Trạng thái** | | |
| `tdlap` | String | Ngày lập hóa đơn (ISO 8601 Format) |
| `ncma`, `ntao`, `ntnhan` | String | Các thời điểm cấp mã, tạo, nhận |
| `ttxly` | Integer | Trạng thái xử lý (VD: 5 - Đã cấp mã, 6 - Không nhận mã, 8 - Nhận HĐ MTT) |
| **Giá trị tiền tệ** | | |
| `tgtcthue` | Number | Tổng tiền chưa thuế |
| `tgtthue` | Number | Tổng tiền thuế |
| `tgtttbso` | Number | Tổng tiền thanh toán bằng số |
| `tgtttbchu` | String | Tổng tiền thanh toán bằng chữ |
| `thttltsuat` | Array | Mảng phân tích tiền theo từng loại thuế suất |
| **Chữ ký số & Cấp mã** | | |
| `nbcks` | String/JSON | Thông tin chữ ký số của người bán |
| `cqtcks` | String/JSON | Thông tin chữ ký số của cơ quan thuế |
| `mhdon` | String | Mã hóa đơn do cơ quan thuế cấp |
| **Thông tin khác** | | |
| `hdhhdvu` | **Null** | Dữ liệu tổng hợp **không** trả về danh sách chi tiết hàng hóa dịch vụ, trường này là `null`. |

---

## 2. Request Chi Tiết (Review hóa đơn)

Các endpoint dạng `/query/invoices/detail` hoặc `/sco-query/invoices/detail` nhận tham số truyền vào là `nbmst`, `khhdon`, `shdon`, `khmshdon` sẽ trả về dữ liệu nội dung chi tiết của 1 hóa đơn.

### Cấu trúc đối tượng (Invoice Detail)
Dữ liệu trả về là một Object chứa tất cả các trường giống hệt như một thẻ trong `datas` của Request tổng hợp, nhưng **được bổ sung thêm** các mảng thông tin phụ và đặc biệt là chi tiết từng dòng hàng (line items).

Bao gồm tất cả các trường đã liệt kê ở phần 1, cộng với:

#### 1. Chi tiết mảng Hàng hóa - Dịch vụ: `hdhhdvu`
Đây là chi tiết cực kỳ quan trọng chỉ có trong request review hóa đơn. 
Mảng `hdhhdvu` chứa các phần tử (mỗi phần tử là một mặt hàng/dịch vụ):

| Trường | Kiểu dữ liệu | Ý nghĩa |
|---|---|---|
| `stt` / `sxep` | Integer | Số thứ tự dòng hàng |
| `tchat` | Integer | Tính chất hàng hóa (1: HH_DV, 2: KM, 3: C/K, 4: Ghi chú, v.v...) |
| `ten` | String | Tên hàng hóa, dịch vụ |
| `dvtinh` | String | Đơn vị tính (Chuyến, Hộp, Chai, Cái...) |
| `sluong` | Number | Số lượng |
| `dgia` | Number | Đơn giá |
| `thtien` | Number | Thành tiền (Số lượng x Đơn giá, chưa VAT) |
| `tsuat` / `ltsuat`| Numeric/Str | Mức thuế suất áp dụng (0.08, "8%") |
| `tthue` | Number | Tiền thuế tương ứng cho dòng hàng này |
| `stckhau` | Number | Tiền chiết khấu (nếu có) |
| `tlckhau` | Number | Tỷ lệ chiết khấu (%) |
| `ttkhac` | Array | Các trường mở rộng riêng cho dòng hàng này (mã booking, loại xe, số máy...) do ERP của công ty gửi lên |

#### 2. Các thông tin mở rộng khác (Extra metadata)
Khác với JSON tóm tắt, JSON chi tiết thường bao gồm các mảng cấu hình cấu trúc linh hoạt khác do bên xuất hóa đơn truyền lên:

| Trường | Kiểu dữ liệu | Ý nghĩa |
|---|---|---|
| `qrcode` | String | Chuỗi ký tự để generate ra mã QR của hóa đơn điện tử |
| `cttkhac` | Array | Chứa các metadata (Ví dụ: `SearchKey`, `VATAmount8`, `GrossValue`...) |
| `nbttkhac` | Array | Chứa các thông tin bổ sung người bán (VD: Email CC, ComAddress) |
| `nmttkhac` | Array | Chứa các thông tin bổ sung người mua (VD: CusCode, PaymentMethod) |
| `ttkhac` | Array | Tiền tệ (`Currency`), Tỷ giá (`ExchangeRate`) |

---

## 3. Tổng kết Phân biệt (Tóm tắt)

| Tiêu chuẩn so sánh | Query Tổng Hợp (Purchase / Sold) | Query Chi Tiết (Detail) |
|---|---|---|
| **Mục đích** | Dùng để lấy danh sách tra cứu, làm bảng kê | Dùng để xem đầy đủ nội dung hoặc in 1 hóa đơn |
| **Dung lượng phản hồi** | Nhẹ (Do không chứa các dòng Item và Metadata phụ) | Nặng hơn nhiều do chứa rất nhiều key-value tuỳ chỉnh |
| **Chi tiết Hàng Hóa (`hdhhdvu`)** | Thuộc tính này thường xuyên là `null` hoặc không có | Trả về một mảng đầy đủ `[{}, {}, ...]` các mặt hàng |
| **Metadata mở rộng (các mảng `ttkhac`)** | Rất ít hoặc rỗng `[]` | Mở rộng chi tiết (VD: Grab có hàng chục trường metadata như `BookingCode`, `Vehicle`) |
| **Mã QR (`qrcode`)** | `null` | Chứa string QR code đầy đủ định dạng |
