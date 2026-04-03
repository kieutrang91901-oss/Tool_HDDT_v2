# BẢNG TỔNG HỢP ĐẶC TẢ CHUNG — HÓA ĐƠN ĐIỆN TỬ VIỆT NAM
> Phiên bản: v1.1 | Cập nhật lần cuối: 2026-03-23
> Mẫu đã phân tích: **3 mẫu** (EasyInvoice/C26TVK · MISA-GRAB/C26MGA · MISA-MTT/C26MTT)
> Cấu trúc thiết kế để **mở rộng liên tục** khi có thêm mẫu mới

---

## MỤC LỤC

1. [Registry Nhà Cung Cấp](#1-registry-nhà-cung-cấp)
2. [Cấu Trúc XML Chuẩn Chung (TCVN)](#2-cấu-trúc-xml-chuẩn-chung)
3. [Bảng Mapping Tag XML → Field](#3-bảng-mapping-tag-xml--field)
4. [Bảng TTin Đặc Thù Theo Vendor](#4-bảng-ttin-đặc-thù-theo-vendor)
5. [Bảng Khác Biệt Cấu Trúc Theo Vendor](#5-bảng-khác-biệt-cấu-trúc-theo-vendor)
6. [Bảng TChat — Tính Chất Hàng Hóa](#6-bảng-tchat--tính-chất-hàng-hóa)
7. [Bảng Trạng Thái Hóa Đơn](#7-bảng-trạng-thái-hóa-đơn)
8. [Logic Nhận Diện Vendor (Auto-detect)](#8-logic-nhận-diện-vendor)
9. [Parser Python Tổng Hợp](#9-parser-python-tổng-hợp)
10. [Mẫu Hóa Đơn Đã Gặp (Registry)](#10-mẫu-hóa-đơn-đã-gặp)
11. [Changelog](#11-changelog)

---

## 1. REGISTRY NHÀ CUNG CẤP

| ID | Tên Nhà Cung Cấp | Nhận Diện MCCQT | Nhận Diện XML | Portal Mẫu | Ghi Chú |
|----|-----------------|-----------------|----------------|------------|---------|
| `EASYINV` | **EasyInvoice** | Hash thuần (không có mã cấu trúc) | Có `PortalLink` trong `TTChung/TTKhac` | `http://{MST}hd.easyinvoice.vn` | Có QR, có chữ ký đầy đủ |
| `MISA_GTGT` | **MISA — HĐ GTGT** | Chứa `ZVEBS`, Mẫu số `1` — `M1-YY-ZVEBS-XXX` | Fkey + SearchKey ở `HDon/TTKhac` | Chưa xác định | HĐ GTGT dịch vụ (VD: GRAB). Có thể thiếu QR/chữ ký |
| `MISA_MTT` | **MISA — Máy Tính Tiền** | Chứa `ZMFWJ`, Mẫu số `2` — `M2-YY-ZMFWJ-XXX` | TTChung/TTKhac có `Mã số bí mật` + `Trạng thái thanh toán` | Chưa xác định | HĐ bán hàng MTT, không có thuế GTGT riêng, không có chữ ký số, QR nội dung đặc thù |
| `VNPT` | **VNPT Invoice** | *(chưa có mẫu)* | *(chưa có mẫu)* | `https://einvoice.vn` | *Cần bổ sung* |
| `VIETTEL` | **Viettel Invoice** | *(chưa có mẫu)* | *(chưa có mẫu)* | `https://vinvoice.vn` | *Cần bổ sung* |
| `BKAV` | **Bkav eHoadon** | *(chưa có mẫu)* | *(chưa có mẫu)* | `https://ehoadon.vn` | *Cần bổ sung* |
| `UNKNOWN` | **Chưa xác định** | — | — | — | Fallback mặc định |

> 📌 **Cách thêm vendor mới**: Thêm 1 dòng vào bảng này + cập nhật Phần 4, 5, 8, 10.

---

## 2. CẤU TRÚC XML CHUẨN CHUNG

Cây XML chuẩn TCVN — các tag **in đậm** là bắt buộc, *in nghiêng* là tùy chọn:

```
HDon
├── DLHDon  [Id="..."]                    ← Dữ liệu chính (ký số bao bọc vùng này)
│   ├── TTChung                            ← Thông tin chung
│   │   ├── PBan                           ← Phiên bản (2.1.0)
│   │   ├── THDon                          ← Tên loại hóa đơn
│   │   ├── KHMSHDon                       ← Mẫu số (thường = 1)
│   │   ├── KHHDon                         ← Ký hiệu (C26TVK, C26MGA...)
│   │   ├── SHDon                          ← Số hóa đơn
│   │   ├── NLap                           ← Ngày lập (YYYY-MM-DD)
│   │   ├── HTTToan                        ← Hình thức thanh toán
│   │   ├── *DVTTe                         ← Đơn vị tiền tệ
│   │   ├── *TGia                          ← Tỷ giá
│   │   ├── *MSTTCGP                       ← MST tổ chức cung cấp phần mềm
│   │   └── *TTKhac/TTin[]                 ← [VENDOR-SPECIFIC] EasyInvoice: PortalLink, Fkey
│   │
│   └── NDHDon                             ← Nội dung hóa đơn
│       ├── NBan                           ← Người bán
│       │   ├── Ten, MST, DChi
│       │   ├── *DCTDTu, *SDThoai, *Fax, *Website
│       │   ├── *STKNHang, *TNHang         ← Tài khoản ngân hàng
│       │   ├── *MCHang, *TCHang           ← Mã/Tên cửa hàng
│       │   └── *TTKhac/TTin[]             ← [VENDOR-SPECIFIC] ComAddress...
│       │
│       ├── NMua                           ← Người mua
│       │   ├── Ten, MST, DChi
│       │   ├── *HVTNMHang                 ← Họ tên người mua hàng / BKS xe
│       │   ├── *MKHang                    ← Mã khách hàng
│       │   ├── *CCCDan, *SHChieu
│       │   ├── *MDVQHNSach
│       │   ├── *STKNHang, *TNHang
│       │   └── *TTKhac/TTin[]             ← [VENDOR-SPECIFIC] CusCode, PaymentMethod...
│       │
│       ├── DSHHDVu                        ← Danh sách hàng hóa/dịch vụ
│       │   └── HHDVu[]                    ← Từng dòng hàng
│       │       ├── TChat                  ← Tính chất (1-5, xem Phần 6)
│       │       ├── STT                    ← Số thứ tự
│       │       ├── *MHHDVu               ← Mã hàng hóa
│       │       ├── THHDVu                 ← Tên hàng hóa/dịch vụ
│       │       ├── DVTinh                 ← Đơn vị tính
│       │       ├── SLuong                 ← Số lượng
│       │       ├── DGia                   ← Đơn giá
│       │       ├── TLCKhau                ← Tỷ lệ chiết khấu
│       │       ├── STCKhau                ← Số tiền chiết khấu
│       │       ├── ThTien                 ← Thành tiền chưa thuế
│       │       ├── TSuat                  ← Thuế suất (8%, 10%, 0%, KCT...)
│       │       ├── *TTHHDTrung/TTin[]     ← [VENDOR-SPECIFIC] MISA: BKSPTVChuyen
│       │       └── *TTKhac/TTin[]         ← [VENDOR-SPECIFIC] BookingCode, VATAmount...
│       │
│       └── TToan                          ← Thông tin thanh toán
│           ├── *TGTKCThue                 ← Tiền giảm trừ khác không chịu thuế
│           ├── *TGTKhac                   ← Tiền giảm trừ khác
│           ├── TgTCThue                   ← Tổng tiền chưa thuế
│           ├── TgTThue                    ← Tổng tiền thuế GTGT
│           ├── *TTCKTMai                  ← Tổng chiết khấu thương mại
│           ├── *DSLPhi/LPhi[]             ← Danh sách phí
│           ├── THTTLTSuat/LTSuat[]        ← Bảng thuế theo từng mức
│           │   ├── TSuat                  ← Thuế suất
│           │   ├── ThTien                 ← Thành tiền theo mức
│           │   └── TThue                  ← Tiền thuế theo mức
│           ├── TgTTTBSo                   ← Tổng thanh toán (số)
│           └── TgTTTBChu                  ← Tổng thanh toán (chữ)
│
├── *TTKhac/TTin[]                         ← [VENDOR-SPECIFIC] MISA: Fkey, SearchKey ở đây
├── DLQRCode                               ← Nội dung QR code (có thể trống)
├── MCCQT                                  ← Mã cơ quan thuế cấp
└── DSCKS                                  ← Chữ ký số
    ├── NBan/Signature                     ← Chữ ký người bán
    ├── NMua/Signature                     ← Chữ ký người mua (thường rỗng)
    ├── CQT/Signature                      ← Chữ ký CQT xác nhận
    └── CCKSKhac                           ← Chữ ký khác
```

---

## 3. BẢNG MAPPING TAG XML → FIELD

### 3.1 Trường Chuẩn (Mọi Vendor)

| Nhóm | Tag XML | Field Hiển Thị | Bắt Buộc | Ghi Chú |
|------|---------|----------------|----------|---------|
| **Header** | `TTChung/KHMSHDon` | Mẫu số | ✅ | Thường = `1` |
| | `TTChung/KHHDon` | Ký hiệu | ✅ | Ví dụ: C26TVK, C26MGA |
| | `TTChung/SHDon` | Số hóa đơn | ✅ | |
| | `TTChung/NLap` | Ngày lập | ✅ | Format YYYY-MM-DD |
| | `TTChung/THDon` | Tên loại HĐ | ✅ | "Hóa đơn GTGT..." |
| | `TTChung/HTTToan` | Hình thức thanh toán | ⚪ | Có thể ở NMua/TTKhac |
| | `MCCQT` | Mã CQT cấp | ✅ | |
| | `DLQRCode` | Nội dung QR | ⚪ | Có thể trống |
| **Người bán** | `NBan/Ten` | Tên người bán | ✅ | |
| | `NBan/MST` | MST người bán | ✅ | |
| | `NBan/DChi` | Địa chỉ người bán | ✅ | |
| | `NBan/DCTDTu` | Email người bán | ⚪ | |
| | `NBan/SDThoai` | Điện thoại | ⚪ | |
| | `NBan/STKNHang` | Số tài khoản | ⚪ | |
| | `NBan/TNHang` | Tên ngân hàng | ⚪ | |
| | `NBan/MCHang` | Mã cửa hàng | ⚪ | |
| | `NBan/TCHang` | Tên cửa hàng | ⚪ | |
| **Người mua** | `NMua/Ten` | Tên người mua | ✅ | |
| | `NMua/MST` | MST người mua | ✅ | |
| | `NMua/DChi` | Địa chỉ người mua | ✅ | |
| | `NMua/HVTNMHang` | Họ tên / BKS xe | ⚪ | GRAB dùng để ghi BKS |
| | `NMua/MKHang` | Mã khách hàng | ⚪ | |
| | `NMua/CCCDan` | CCCD người mua | ⚪ | |
| | `NMua/SHChieu` | Số hộ chiếu | ⚪ | |
| | `NMua/MDVQHNSach` | Mã ĐVCQHVNSNN | ⚪ | |
| **Hàng hóa** | `HHDVu/STT` | STT | ✅ | |
| | `HHDVu/TChat` | Tính chất | ✅ | Xem Phần 6 |
| | `HHDVu/MHHDVu` | Mã hàng hóa | ⚪ | GRAB = Booking code |
| | `HHDVu/THHDVu` | Tên hàng hóa/DV | ✅ | |
| | `HHDVu/DVTinh` | Đơn vị tính | ✅ | |
| | `HHDVu/SLuong` | Số lượng | ✅ | |
| | `HHDVu/DGia` | Đơn giá | ✅ | |
| | `HHDVu/TLCKhau` | Tỷ lệ chiết khấu % | ✅ | |
| | `HHDVu/STCKhau` | Số tiền chiết khấu | ✅ | |
| | `HHDVu/ThTien` | Thành tiền chưa thuế | ✅ | |
| | `HHDVu/TSuat` | Thuế suất | ✅ | 8%, 10%, 0%, KCT... |
| **Tổng kết** | `TToan/TgTCThue` | Tổng tiền chưa thuế | ✅ | |
| | `TToan/TgTThue` | Tổng tiền thuế GTGT | ✅ | |
| | `TToan/TTCKTMai` | Tổng chiết khấu TM | ⚪ | |
| | `TToan/TgTTTBSo` | Tổng thanh toán (số) | ✅ | |
| | `TToan/TgTTTBChu` | Tổng thanh toán (chữ) | ✅ | |
| | `TToan/LTSuat/TSuat` | Thuế suất (bảng TH) | ⚪ | |
| | `TToan/LTSuat/ThTien` | Thành tiền (bảng TH) | ⚪ | |
| | `TToan/LTSuat/TThue` | Tiền thuế (bảng TH) | ⚪ | |
| **Chữ ký** | `DSCKS/NBan/Signature` | Chữ ký người bán | ⚪ | Có thể rỗng |
| | `DSCKS/CQT/Signature` | Chữ ký CQT | ⚪ | Có thể rỗng |

---

## 4. BẢNG TTIN ĐẶC THÙ THEO VENDOR

### 4.1 EasyInvoice — `TTKhac` trong `TTChung`

| TTruong (Key) | Mô Tả | Ví Dụ | Dùng Để |
|---------------|-------|-------|---------|
| `PortalLink` | URL portal tra cứu | `http://0312571520hd.easyinvoice.vn` | Nút "Tra cứu online" |
| `Fkey` | Mã tra cứu HĐ | `5UOMTDSHQ` | Tra cứu trực tiếp |

### 4.2 EasyInvoice — `TTKhac` trong từng `HHDVu`

| TTruong (Key) | Mô Tả | Ví Dụ |
|---------------|-------|-------|
| `VATAmount` | Tiền thuế VAT dòng này | `8889` |
| `Amount` | Thành tiền có thuế | `120000` |
| `ProdSubTotal` | Thành tiền chưa thuế | `111111` |

### 4.3 MISA/GRAB — `TTKhac` ở `HDon` (ngoài cùng)

| TTruong (Key) | Mô Tả | Ví Dụ | Dùng Để |
|---------------|-------|-------|---------|
| `Fkey` | Mã tra cứu HĐ | `26GAebrm69xaijv` | Tra cứu |
| `SearchKey` | Mã tìm kiếm | `9ce9be85ff424...` | Tìm kiếm hệ thống |
| `MappingKey` | Số HĐ nội bộ | `2293651` | Reference nội bộ |
| `VATAmount8` | Tổng VAT mức 8% | `4000` | Báo cáo thuế |
| `VATAmount0/5/10` | Tổng VAT các mức khác | `0` | Báo cáo thuế |
| `GrossValue8` | Doanh thu chịu thuế 8% | `50000` | Báo cáo |
| `GrossValue` | Tổng doanh thu chưa thuế | `50000` | Báo cáo |
| `AmountVAT` | Tổng thanh toán | `54000` | Kiểm tra |
| `AmountInWords` | Số tiền bằng chữ (VI) | `năm mươi bốn nghìn đồng` | Fallback |
| `AmountInWordsOther` | Số tiền bằng chữ (EN) | `Fifty four thousand VND.` | Export |
| `CusEmailCC` | Email CC người mua | `accountingsupport.vn@...` | Gửi email |

### 4.4 MISA/GRAB — `TTKhac` trong `NMua`

| TTruong (Key) | Mô Tả | Ví Dụ |
|---------------|-------|-------|
| `CusName` | Tên KH (bản sao) | `CÔNG TY TNHH...` |
| `CusCode` | Mã KH nội bộ | `1000142556` |
| `PaymentMethod` | Hình thức thanh toán | `Chuyển khoản` |
| `CusEmailCC` | Email CC | `accountingsupport.vn@grabtaxi.com` |

### 4.5 MISA/GRAB — `TTKhac` trong từng `HHDVu`

| TTruong (Key) | Mô Tả | Ví Dụ | Ghi Chú |
|---------------|-------|-------|---------|
| `BookingCode` | Mã chuyến đi | `A-944EJ7CGW7RSAV` | GRAB |
| `BookingDate` | Ngày đặt xe | `2026-03-19` | GRAB |
| `Vertical` | Loại dịch vụ | `GrabCar` | GRAB |
| `Departurepoint` | Điểm đón | `338 Nguyễn Trọng Tuyển...` | GRAB |
| `Destination` | Điểm đến | `142A Tô Hiến Thành...` | GRAB |
| `Vehicle` | Biển số xe | `50H-261.37` | GRAB |
| `ProdQuantity` | Số lượng | `1` | Bản sao |
| `ProdPrice` | Đơn giá | `44444` | Bản sao |
| `VATAmount` | Tiền thuế VAT dòng này | `3556` | |
| `Total` | Thành tiền chưa thuế | `44444` | |
| `Amount` | Thành tiền có thuế | `48000` | |
| `ProductNo` | Số thứ tự sản phẩm | `0` | |

### 4.6 MISA/GRAB — `TTHHDTrung` trong `HHDVu`

| TTruong (Key) | LHHDTrung | Mô Tả | Ví Dụ |
|---------------|-----------|-------|-------|
| `BKSPTVChuyen` | `2` | BKS phương tiện vận chuyển | `50H-261.37` |

### 4.7 MISA/MTT — `TTKhac` trong `TTChung`

> Hóa đơn bán hàng từ **máy tính tiền** — TTKhac nằm trong `TTChung` (giống EasyInvoice nhưng nội dung khác hoàn toàn)

| TTruong (Key) | Mô Tả | Ví Dụ | Dùng Để |
|---------------|-------|-------|---------|
| `Trạng thái thanh toán` | Trạng thái TT tại thời điểm xuất | `Đã thanh toán` | Hiển thị ghi chú TT |
| `Mã số bí mật` | Mã xác thực HĐ MTT | `8FPJR3LESXDY01K` | Tra cứu / xác thực |

### 4.8 MISA/MTT — `TTKhac` trong `NBan`

| TTruong (Key) | Mô Tả | Ví Dụ |
|---------------|-------|-------|
| `Tỉnh/Thành phố người bán` | Tỉnh/TP của người bán | `TPHCM` |
| `Mã quốc gia người bán` | Mã quốc gia | `84` |

### 4.9 MISA/MTT — `TTKhac` trong `TToan`

| TTruong (Key) | Mô Tả | Ví Dụ |
|---------------|-------|-------|
| `Tổng tiền thuế tiêu thụ đặc biệt` | Thuế TTĐB | `0` |
| `Tổng tiền phí` | Phí dịch vụ | `0` |

### 4.10 MISA/MTT — `TTKhac` trong `NDHDon` (cấp NDHDon)

| TTruong (Key) | Mô Tả | Ví Dụ |
|---------------|-------|-------|
| `Tổng tiền thanh toán bằng số` | Bản sao tổng TT | `1500000` |
| `Tổng tiền thanh toán bằng chữ` | Bản sao bằng chữ | `Một triệu năm trăm nghìn đồng` |

> 📌 **Vendor mới**: Thêm mục 4.X tương ứng khi phân tích mẫu mới.

---

## 5. BẢNG KHÁC BIỆT CẤU TRÚC THEO VENDOR

| Tiêu Chí | EasyInvoice | MISA_GTGT | MISA_MTT | VNPT | Viettel | *Vendor mới* |
|----------|-------------|-----------|----------|------|---------|--------------|
| **Loại HĐ** | GTGT | GTGT | Bán hàng MTT | ? | ? | ? |
| **Mẫu số (KHMSHDon)** | `1` | `1` | `2` | ? | ? | ? |
| **Tên loại HĐ (THDon)** | Hóa đơn GTGT | Hóa đơn GTGT | Hóa đơn bán hàng được khởi tạo từ máy tính tiền | ? | ? | ? |
| **Fkey vị trí** | `TTChung/TTKhac` | `HDon/TTKhac` | `TTChung/TTKhac[Mã số bí mật]` | ? | ? | ? |
| **Portal link** | `TTChung/TTKhac[PortalLink]` | ❌ Không có | ❌ Không có | ? | ? | ? |
| **SearchKey** | ❌ Không có | `HDon/TTKhac[SearchKey]` | ❌ Không có | ? | ? | ? |
| **Mã bí mật MTT** | ❌ Không có | ❌ Không có | `TTChung/TTKhac[Mã số bí mật]` | ? | ? | ? |
| **QR Code** | ✅ Nội dung ngắn | ❌ Trống | ✅ Nội dung đặc thù MTT | ? | ? | ? |
| **QR format** | `HHMMSSHDKYH.SOHD...` | *(trống)* | `MST\|MauSo/001\|1\|KHHDon+SHDon\|MSTMua\|dd/MM/yyyy\|TongTT` | ? | ? | ? |
| **Chữ ký NBan** | ✅ Đầy đủ | ⚠️ Có thể rỗng | ❌ Không có | ? | ? | ? |
| **Chữ ký CQT** | ✅ Đầy đủ | ⚠️ Có thể rỗng | ❌ Không có | ? | ? | ? |
| **MCCQT format** | Hash thuần | `M1-YY-ZVEBS-XXX` | `M2-YY-ZMFWJ-XXX` | ? | ? | ? |
| **Mã MCCQT** | *(hash)* | `ZVEBS` | `ZMFWJ` | ? | ? | ? |
| **MSTTCGP** | ✅ Có | ❌ Không có | ❌ Không có | ? | ? | ? |
| **TTHHDTrung** | ❌ Không dùng | ✅ BKS xe GRAB | ❌ Không có | ? | ? | ? |
| **Bảng LTSuat** | ✅ Có | ✅ Có | ❌ Không có (không có GTGT) | ? | ? | ? |
| **Cột Thuế suất trong bảng HH** | ✅ Có | ✅ Có | ❌ Không có | ? | ? | ? |
| **Nhiều dòng/booking** | 1 dòng | N dòng/booking | N dòng (tùy sản phẩm) | ? | ? | ? |
| **Email CC** | ❌ Không có | ✅ Có | ❌ Không có | ? | ? | ? |
| **SDThoai NBan** | ❌ Không có | ❌ Không có | ✅ Có (`0919890559`) | ? | ? | ? |
| **Tỉnh/TP NBan** | ❌ Không có | ❌ Không có | ✅ `TTKhac[Tỉnh/Thành phố người bán]` | ? | ? | ? |
| **TChat phổ biến** | `1`, `2` | `5` | `1` | ? | ? | ? |
| **TTKhac đặc thù** | PortalLink, Fkey | BookingCode, Vehicle... | Mã số bí mật, Trạng thái TT | ? | ? | ? |

---

## 6. BẢNG TCHAT — TÍNH CHẤT HÀNG HÓA

| Giá Trị | Nhãn Hiển Thị | Mô Tả | Vendor Gặp |
|---------|--------------|-------|-----------|
| `1` | Hàng hóa, dịch vụ | Hàng hóa/DV thông thường | EasyInvoice |
| `2` | Hàng hóa đặc trưng | Có thông tin đặc trưng đính kèm | EasyInvoice |
| `3` | Khuyến mại | Hàng khuyến mại, giảm giá | *Chưa gặp* |
| `4` | Chiết khấu | Dòng chiết khấu thương mại | *Chưa gặp* |
| `5` | Hàng hóa đặc trưng | MISA dùng cho dịch vụ Grab | MISA/GRAB |

---

## 7. BẢNG TRẠNG THÁI HÓA ĐƠN

| Trạng Thái | Điều Kiện Xác Định | Icon UI | Màu |
|------------|-------------------|---------|-----|
| ✅ **Hợp lệ đầy đủ** | Có MCCQT + QR + Chữ ký NBan + Chữ ký CQT | ✅ | Xanh lá |
| 🟡 **Hợp lệ một phần** | Có MCCQT, thiếu QR hoặc chữ ký CQT | 🟡 | Vàng |
| ⚠️ **Chưa ký số** | `DSCKS/NBan` rỗng | ⚠️ | Cam |
| ❌ **Thiếu MCCQT** | `MCCQT` trống hoặc không hợp lệ | ❌ | Đỏ |
| 🔴 **Lỗi parse** | Exception khi đọc XML | 🔴 | Đỏ đậm |

```python
def get_invoice_status(inv: InvoiceData) -> tuple[str, str]:
    """Trả về (icon, label) trạng thái hóa đơn."""
    if inv.parse_error:
        return "🔴", "Lỗi đọc file"
    if not inv.mccqt:
        return "❌", "Thiếu MCCQT"
    if not inv.da_ky_nguoi_ban:
        return "⚠️", "Chưa ký số"
    if not inv.da_ky_cqt or not inv.qr_content:
        return "🟡", "Hợp lệ một phần"
    return "✅", "Hợp lệ"
```

---

## 8. LOGIC NHẬN DIỆN VENDOR

```python
def detect_vendor(root) -> str:
    """
    Nhận diện nhà cung cấp phần mềm HĐ điện tử từ XML.
    Thứ tự ưu tiên: MCCQT → cấu trúc TTKhac → fallback MSTTCGP.
    """
    # B1: Kiểm tra MCCQT (nhanh nhất)
    mccqt = _t(root, "//*[local-name()='MCCQT']/text()")
    if "ZVEBS" in mccqt:   return "MISA_GTGT"
    if "ZMFWJ" in mccqt:   return "MISA_MTT"
    # ── Thêm vendor mới ở đây ──
    # if "VNPT" in mccqt: return "VNPT"

    # B2: Kiểm tra cấu trúc TTKhac
    ttchung_keys = {
        item.xpath("*[local-name()='TTruong']")[0].text
        for item in root.xpath("//*[local-name()='TTChung']//*[local-name()='TTin']")
        if item.xpath("*[local-name()='TTruong']")
    }
    if "PortalLink" in ttchung_keys:        return "EASYINV"
    if "Mã số bí mật" in ttchung_keys:     return "MISA_MTT"
    # ── Thêm vendor mới ở đây ──

    # B3: Kiểm tra HDon/TTKhac (MISA_GTGT fallback)
    hdon_keys = {
        item.xpath("*[local-name()='TTruong']")[0].text
        for item in root.xpath(
            "/*[local-name()='HDon']/*[local-name()='TTKhac']//*[local-name()='TTin']"
        )
        if item.xpath("*[local-name()='TTruong']")
    }
    if "SearchKey" in hdon_keys:            return "MISA_GTGT"

    # B4: Kiểm tra KHMSHDon (Mẫu số) — MTT thường là mẫu số 2
    mau_so = _t(root, "//*[local-name()='KHMSHDon']/text()")
    if mau_so == "2":                       return "MISA_MTT"

    # B5: MSTTCGP (MST đơn vị cung cấp)
    mst_tcgp = _t(root, "//*[local-name()='MSTTCGP']/text()")
    MSTTCGP_MAP = {
        "0105987432": "EASYINV",
        # Thêm MST của VNPT, Viettel... ở đây
    }
    if mst_tcgp in MSTTCGP_MAP:
        return MSTTCGP_MAP[mst_tcgp]

    return "UNKNOWN"


def get_fkey(root, vendor: str) -> str:
    """Lấy Fkey / mã tra cứu đúng vị trí theo vendor."""
    if vendor == "EASYINV":
        # EasyInvoice: Fkey trong TTChung/TTKhac
        for item in root.xpath("//*[local-name()='TTChung']//*[local-name()='TTin']"):
            k = item.xpath("*[local-name()='TTruong']")
            v = item.xpath("*[local-name()='DLieu']")
            if k and k[0].text == "Fkey" and v:
                return (v[0].text or "").strip()
    elif vendor == "MISA_GTGT":
        # MISA GTGT: Fkey trong HDon/TTKhac (cấp ngoài cùng)
        for item in root.xpath(
            "/*[local-name()='HDon']/*[local-name()='TTKhac']//*[local-name()='TTin']"
        ):
            k = item.xpath("*[local-name()='TTruong']")
            v = item.xpath("*[local-name()='DLieu']")
            if k and k[0].text == "Fkey" and v:
                return (v[0].text or "").strip()
    elif vendor == "MISA_MTT":
        # MISA MTT: dùng "Mã số bí mật" làm mã tra cứu
        for item in root.xpath("//*[local-name()='TTChung']//*[local-name()='TTin']"):
            k = item.xpath("*[local-name()='TTruong']")
            v = item.xpath("*[local-name()='DLieu']")
            if k and k[0].text == "Mã số bí mật" and v:
                return (v[0].text or "").strip()
    # ── Thêm vendor mới ở đây ──
    return ""


def get_portal_url(inv: "InvoiceData") -> str:
    """Tạo URL tra cứu theo vendor."""
    if inv.nha_cung_cap == "EASYINV":
        return inv.portal_link
    if inv.nha_cung_cap == "MISA_GTGT":
        return ""  # Chưa xác định portal public
    if inv.nha_cung_cap == "MISA_MTT":
        return ""  # Chưa xác định portal public
    # ── Thêm vendor mới ở đây ──
    return ""
```

---

## 9. PARSER PYTHON TỔNG HỢP

```python
# invoice_parser_master.py
# Hỗ trợ: EasyInvoice, MISA — dễ mở rộng thêm vendor
from lxml import etree
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# ══════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════

@dataclass
class HangHoa:
    # Chuẩn TCVN
    stt: str = ""
    tinh_chat: str = ""         # Nhãn đã dịch (không phải mã số)
    tinh_chat_ma: str = ""      # Mã gốc (1,2,3,4,5)
    loai_hang_dac_trung: str = ""  # Từ TTHHDTrung (MISA)
    ma_hang: str = ""
    ten_hang: str = ""
    don_vi_tinh: str = ""
    so_luong: str = ""
    don_gia: str = ""
    ty_le_ck: str = ""
    so_tien_ck: str = ""
    thue_suat: str = ""
    thanh_tien: str = ""
    # Vendor-specific extras
    vat_amount: str = ""        # EasyInvoice + MISA
    amount_co_thue: str = ""    # EasyInvoice + MISA
    booking_code: str = ""      # MISA/GRAB
    booking_date: str = ""      # MISA/GRAB
    vertical: str = ""          # MISA/GRAB (GrabCar, GrabBike...)
    diem_don: str = ""          # MISA/GRAB
    diem_den: str = ""          # MISA/GRAB
    bien_so_xe: str = ""        # MISA/GRAB
    extras: Dict[str, str] = field(default_factory=dict)

@dataclass
class LTSuat:
    thue_suat: str = ""
    thanh_tien: str = ""
    tong_thue: str = ""

@dataclass
class InvoiceData:
    # ── Metadata vendor ──────────────────────────────────
    nha_cung_cap: str = "UNKNOWN"   # EASYINV | MISA_GTGT | MISA_MTT | VNPT | ...

    # ── Header chuẩn ─────────────────────────────────────
    mau_so: str = ""
    ky_hieu: str = ""
    so_hd: str = ""
    ngay_lap: str = ""
    ten_loai_hd: str = ""
    httt: str = ""
    don_vi_tien_te: str = ""
    ty_gia: str = ""
    mccqt: str = ""
    qr_content: str = ""
    mst_tcgp: str = ""

    # ── Lookup (vị trí khác nhau tùy vendor) ─────────────
    fkey: str = ""              # EasyInvoice: Fkey | MISA_GTGT: Fkey | MISA_MTT: Mã số bí mật
    portal_link: str = ""       # EasyInvoice only
    search_key: str = ""        # MISA_GTGT only
    mapping_key: str = ""       # MISA_GTGT only
    # MISA_MTT specifics
    trang_thai_tt: str = ""     # "Đã thanh toán" — từ TTChung/TTKhac

    # ── Người bán ────────────────────────────────────────
    ten_ban: str = ""
    mst_ban: str = ""
    dia_chi_ban: str = ""
    email_ban: str = ""
    dien_thoai_ban: str = ""
    so_tk_ban: str = ""
    ten_ngan_hang_ban: str = ""
    ma_cua_hang: str = ""
    ten_cua_hang: str = ""
    tinh_tp_ban: str = ""       # MISA_MTT: TTKhac[Tỉnh/Thành phố người bán]
    ma_quoc_gia_ban: str = ""   # MISA_MTT: TTKhac[Mã quốc gia người bán]

    # ── Người mua ────────────────────────────────────────
    ten_mua: str = ""
    ho_ten_nguoi_mua: str = ""
    mst_mua: str = ""
    ma_khach_hang: str = ""
    dia_chi_mua: str = ""
    cccd_nguoi_mua: str = ""
    so_ho_chieu: str = ""
    email_cc: str = ""
    so_tk_mua: str = ""

    # ── Hàng hóa & Thuế suất ─────────────────────────────
    hang_hoa: List[HangHoa] = field(default_factory=list)
    lt_suat: List[LTSuat] = field(default_factory=list)

    # ── Tổng kết ─────────────────────────────────────────
    tong_chua_thue: str = ""
    tong_thue: str = ""
    tong_phi: str = ""
    tong_ck_tm: str = ""
    tong_thanh_toan_so: str = ""
    tong_thanh_toan_chu: str = ""
    # MISA_GTGT extras
    vat_amount_8: str = ""
    gross_value_8: str = ""

    # ── Chữ ký ───────────────────────────────────────────
    da_ky_nguoi_ban: bool = False
    ky_boi_nguoi_ban: str = ""
    ky_ngay_nguoi_ban: str = ""
    da_ky_cqt: bool = False
    ky_ngay_cqt: str = ""

    # ── Runtime ──────────────────────────────────────────
    file_path: str = ""
    html_path: str = ""
    parse_error: str = ""

    @property
    def status_icon(self) -> str:
        if self.parse_error:            return "🔴"
        if not self.mccqt:             return "❌"
        if self.nha_cung_cap == "MISA_MTT":
            return "🟢" if self.qr_content else "🟡"  # MTT không có chữ ký, dùng QR
        if not self.da_ky_nguoi_ban:   return "⚠️"
        if not self.da_ky_cqt or not self.qr_content: return "🟡"
        return "✅"

    @property
    def display_title(self) -> str:
        return f"{self.ky_hieu}-{self.so_hd} | {self.ten_ban} | {self.ngay_lap}"

    @property
    def fkey_label(self) -> str:
        """Nhãn hiển thị cho mã tra cứu tuỳ vendor."""
        if self.nha_cung_cap == "MISA_MTT":
            return "Mã số bí mật"
        return "Fkey"


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

TCHAT_LABEL = {
    "1": "Hàng hóa, dịch vụ",
    "2": "Hàng hóa đặc trưng",
    "3": "Khuyến mại",
    "4": "Chiết khấu",
    "5": "Hàng hóa đặc trưng",
}

def _t(el, xpath: str) -> str:
    try:
        nodes = el.xpath(xpath)
        if not nodes: return ""
        n = nodes[0]
        return (n.text or "").strip() if hasattr(n, "text") else str(n).strip()
    except Exception:
        return ""

def _ttkhac(el, scope_xpath: str = ".") -> Dict[str, str]:
    """Trích toàn bộ TTin trong scope thành dict {TTruong: DLieu}."""
    result = {}
    try:
        for item in el.xpath(f"{scope_xpath}//*[local-name()='TTin']"):
            k = item.xpath("*[local-name()='TTruong']")
            v = item.xpath("*[local-name()='DLieu']")
            if k and v:
                result[(k[0].text or "").strip()] = (v[0].text or "").strip()
    except Exception:
        pass
    return result

def _detect_vendor(root) -> str:
    mccqt = _t(root, "//*[local-name()='MCCQT']/text()")
    if "ZVEBS" in mccqt: return "MISA_GTGT"
    if "ZMFWJ" in mccqt: return "MISA_MTT"
    # ── Thêm VNPT, Viettel... ở đây ──

    ttchung_extras = _ttkhac(root, "//*[local-name()='TTChung']/*[local-name()='TTKhac']")
    if "PortalLink" in ttchung_extras:    return "EASYINV"
    if "Mã số bí mật" in ttchung_extras: return "MISA_MTT"

    hdon_extras = _ttkhac(root, "/*[local-name()='HDon']/*[local-name()='TTKhac']")
    if "SearchKey" in hdon_extras: return "MISA_GTGT"

    mau_so = _t(root, "//*[local-name()='KHMSHDon']/text()")
    if mau_so == "2": return "MISA_MTT"

    mst_tcgp = _t(root, "//*[local-name()='MSTTCGP']/text()")
    MSTTCGP_MAP = {"0105987432": "EASYINV"}
    if mst_tcgp in MSTTCGP_MAP: return MSTTCGP_MAP[mst_tcgp]

    return "UNKNOWN"


# ══════════════════════════════════════════════════════════
# PARSER CHÍNH
# ══════════════════════════════════════════════════════════

def parse_invoice_xml(file_path: str) -> InvoiceData:
    inv = InvoiceData(file_path=file_path)
    try:
        root = etree.parse(file_path).getroot()
        inv.nha_cung_cap = _detect_vendor(root)

        # ── Header ──────────────────────────────────────
        inv.mau_so       = _t(root, "//*[local-name()='KHMSHDon']/text()")
        inv.ky_hieu      = _t(root, "//*[local-name()='KHHDon']/text()")
        inv.so_hd        = _t(root, "//*[local-name()='SHDon']/text()")
        inv.ngay_lap     = _t(root, "//*[local-name()='NLap']/text()")
        inv.ten_loai_hd  = _t(root, "//*[local-name()='THDon']/text()")
        inv.httt         = _t(root, "//*[local-name()='HTTToan']/text()")
        inv.don_vi_tien_te = _t(root, "//*[local-name()='DVTTe']/text()")
        inv.ty_gia       = _t(root, "//*[local-name()='TGia']/text()")
        inv.mccqt        = _t(root, "//*[local-name()='MCCQT']/text()")
        inv.qr_content   = _t(root, "//*[local-name()='DLQRCode']/text()")
        inv.mst_tcgp     = _t(root, "//*[local-name()='MSTTCGP']/text()")

        # ── Lookup — EasyInvoice: TTChung/TTKhac ────────
        ttchung_ex = _ttkhac(root, "//*[local-name()='TTChung']/*[local-name()='TTKhac']")
        inv.portal_link  = ttchung_ex.get("PortalLink", "")
        inv.fkey         = ttchung_ex.get("Fkey", "")
        # MISA_MTT: mã tra cứu là "Mã số bí mật"
        if not inv.fkey:
            inv.fkey     = ttchung_ex.get("Mã số bí mật", "")
        inv.trang_thai_tt = ttchung_ex.get("Trạng thái thanh toán", "")

        # ── Lookup — MISA_GTGT: HDon/TTKhac ─────────────
        hdon_ex = _ttkhac(root, "/*[local-name()='HDon']/*[local-name()='TTKhac']")
        inv.fkey        = inv.fkey or hdon_ex.get("Fkey", "")
        inv.search_key  = hdon_ex.get("SearchKey", "")
        inv.mapping_key = hdon_ex.get("MappingKey", "")
        inv.vat_amount_8  = hdon_ex.get("VATAmount8", "")
        inv.gross_value_8 = hdon_ex.get("GrossValue8", "")
        if not inv.httt:
            inv.httt = hdon_ex.get("PaymentMethod", "")

        # ── Người bán ────────────────────────────────────
        for b in root.xpath("//*[local-name()='NBan']"):
            inv.ten_ban           = _t(b, "*[local-name()='Ten']/text()")
            inv.mst_ban           = _t(b, "*[local-name()='MST']/text()")
            inv.dia_chi_ban       = _t(b, "*[local-name()='DChi']/text()")
            inv.email_ban         = _t(b, "*[local-name()='DCTDTu']/text()")
            inv.dien_thoai_ban    = _t(b, "*[local-name()='SDThoai']/text()")
            inv.so_tk_ban         = _t(b, "*[local-name()='STKNHang']/text()")
            inv.ten_ngan_hang_ban = _t(b, "*[local-name()='TNHang']/text()")
            inv.ma_cua_hang       = _t(b, "*[local-name()='MCHang']/text()")
            inv.ten_cua_hang      = _t(b, "*[local-name()='TCHang']/text()")
            nban_ex = _ttkhac(b)
            inv.tinh_tp_ban       = nban_ex.get("Tỉnh/Thành phố người bán", "")
            inv.ma_quoc_gia_ban   = nban_ex.get("Mã quốc gia người bán", "")
            break

        # ── Người mua ────────────────────────────────────
        for m in root.xpath("//*[local-name()='NMua']"):
            inv.ten_mua          = _t(m, "*[local-name()='Ten']/text()")
            inv.mst_mua          = _t(m, "*[local-name()='MST']/text()")
            inv.dia_chi_mua      = _t(m, "*[local-name()='DChi']/text()")
            inv.ho_ten_nguoi_mua = _t(m, "*[local-name()='HVTNMHang']/text()")
            inv.ma_khach_hang    = _t(m, "*[local-name()='MKHang']/text()")
            inv.cccd_nguoi_mua   = _t(m, "*[local-name()='CCCDan']/text()")
            inv.so_ho_chieu      = _t(m, "*[local-name()='SHChieu']/text()")
            nmua_ex = _ttkhac(m)
            inv.ma_khach_hang    = inv.ma_khach_hang or nmua_ex.get("CusCode", "")
            inv.email_cc         = nmua_ex.get("CusEmailCC", "")
            if not inv.httt:
                inv.httt         = nmua_ex.get("PaymentMethod", "")
            break

        # ── Hàng hóa ─────────────────────────────────────
        for item in root.xpath("//*[local-name()='HHDVu']"):
            ex = _ttkhac(item)
            # TTHHDTrung — loại hàng đặc trưng (MISA/GRAB)
            loai_hang_parts = []
            for tt in item.xpath(".//*[local-name()='TTHHDTrung']//*[local-name()='TTin']"):
                k = tt.xpath("*[local-name()='TTruong']")
                v = tt.xpath("*[local-name()='DLieu']")
                if k and v:
                    label = {"BKSPTVChuyen": "Dịch vụ vận chuyển\nBKS phương tiện vận chuyển"}.get(
                        k[0].text, k[0].text)
                    loai_hang_parts.append(f"{label}: {v[0].text or ''}")
            tc = _t(item, "*[local-name()='TChat']/text()")
            h = HangHoa(
                stt                 = _t(item, "*[local-name()='STT']/text()"),
                tinh_chat_ma        = tc,
                tinh_chat           = TCHAT_LABEL.get(tc, tc),
                loai_hang_dac_trung = "\n".join(loai_hang_parts),
                ma_hang             = _t(item, "*[local-name()='MHHDVu']/text()"),
                ten_hang            = _t(item, "*[local-name()='THHDVu']/text()"),
                don_vi_tinh         = _t(item, "*[local-name()='DVTinh']/text()"),
                so_luong            = _t(item, "*[local-name()='SLuong']/text()"),
                don_gia             = _t(item, "*[local-name()='DGia']/text()"),
                ty_le_ck            = _t(item, "*[local-name()='TLCKhau']/text()"),
                so_tien_ck          = _t(item, "*[local-name()='STCKhau']/text()"),
                thue_suat           = _t(item, "*[local-name()='TSuat']/text()"),
                thanh_tien          = _t(item, "*[local-name()='ThTien']/text()"),
                vat_amount          = ex.get("VATAmount", ""),
                amount_co_thue      = ex.get("Amount", ""),
                booking_code        = ex.get("BookingCode", ""),
                booking_date        = ex.get("BookingDate", ""),
                vertical            = ex.get("Vertical", ""),
                diem_don            = ex.get("Departurepoint", ""),
                diem_den            = ex.get("Destination", ""),
                bien_so_xe          = ex.get("Vehicle", "") or _t(item, "*[local-name()='HVTNMHang']/text()"),
                extras              = ex,
            )
            inv.hang_hoa.append(h)

        # ── Bảng thuế suất ────────────────────────────────
        for lt in root.xpath("//*[local-name()='LTSuat']"):
            inv.lt_suat.append(LTSuat(
                thue_suat  = _t(lt, "*[local-name()='TSuat']/text()"),
                thanh_tien = _t(lt, "*[local-name()='ThTien']/text()"),
                tong_thue  = _t(lt, "*[local-name()='TThue']/text()"),
            ))

        # ── Tổng kết ─────────────────────────────────────
        for t in root.xpath("//*[local-name()='TToan']"):
            inv.tong_chua_thue      = _t(t, "*[local-name()='TgTCThue']/text()")
            inv.tong_thue           = _t(t, "*[local-name()='TgTThue']/text()")
            inv.tong_ck_tm          = _t(t, "*[local-name()='TTCKTMai']/text()")
            inv.tong_thanh_toan_so  = _t(t, "*[local-name()='TgTTTBSo']/text()")
            inv.tong_thanh_toan_chu = _t(t, "*[local-name()='TgTTTBChu']/text()")
            break
        if not inv.tong_thanh_toan_chu:
            inv.tong_thanh_toan_chu = hdon_ex.get("AmountInWords", "")

        # ── Chữ ký người bán ─────────────────────────────
        ck_time = root.xpath("//*[local-name()='DSCKS']/*[local-name()='NBan']//*[local-name()='SigningTime']/text()")
        ck_cn   = root.xpath("//*[local-name()='DSCKS']/*[local-name()='NBan']//*[local-name()='X509SubjectName']/text()")
        inv.da_ky_nguoi_ban = bool(ck_time)
        if ck_time: inv.ky_ngay_nguoi_ban = ck_time[0]
        if ck_cn:
            for part in ck_cn[0].split(","):
                if part.strip().startswith("CN="):
                    inv.ky_boi_nguoi_ban = part.strip()[3:]; break

        # ── Chữ ký CQT ───────────────────────────────────
        cqt_time = root.xpath("//*[local-name()='DSCKS']/*[local-name()='CQT']//*[local-name()='SigningTime']/text()")
        inv.da_ky_cqt = bool(cqt_time)
        if cqt_time: inv.ky_ngay_cqt = cqt_time[0]

        # ── html_path (tự tìm) ───────────────────────────
        html_candidate = os.path.join(os.path.dirname(file_path), "invoice.html")
        if os.path.exists(html_candidate):
            inv.html_path = html_candidate

    except Exception as e:
        inv.parse_error = str(e)
    return inv


def parse_batch(file_paths: List[str]) -> List[InvoiceData]:
    """Parse nhiều file song song, giữ nguyên thứ tự."""
    order = {fp: i for i, fp in enumerate(file_paths)}
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for f in as_completed({ex.submit(parse_invoice_xml, fp): fp for fp in file_paths}):
            results.append(f.result())
    results.sort(key=lambda inv: order.get(inv.file_path, 9999))
    return results
```

---

## 10. MẪU HÓA ĐƠN ĐÃ GẶP (Registry)

| # | File ZIP | Ký Hiệu | Số HĐ | Vendor | Người Bán | Ngày | Tổng TT | QR | Chữ Ký | Đặc Điểm |
|---|----------|---------|-------|--------|-----------|------|---------|----|---------|----|
| 1 | `8312.zip` | C26**TVK** | 8312 | `EASYINV` | CÔNG TY TNHH Ô TÔ VĂN KHOA | 2026-03-20 | 120.000 | ✅ | ✅ NBan + CQT | 1 dòng, rửa xe, đầy đủ chữ ký |
| 2 | `2293651.zip` | C26**MGA** | 2293651 | `MISA_GTGT` | CÔNG TY TNHH GRAB | 2026-03-20 | 54.000 | ❌ | ⚠️ Rỗng | 2 dòng GRAB, BKS xe, BookingCode, chưa ký |
| 3 | `112.zip` | C26**MTT** | 112 | `MISA_MTT` | HỘ KINH DOANH MINH ANH FLOWER | 2026-03-18 | 1.500.000 | ✅ MTT | ❌ Không có | Bán hàng MTT, mẫu số 2, không GTGT, 2 dòng hoa tươi, có Mã số bí mật |

> 📌 **Cách thêm mẫu mới**: Thêm 1 dòng vào bảng này + cập nhật Phần 4 nếu có TTin mới + cập nhật Phần 5 nếu có khác biệt cấu trúc.

---

## 11. CHANGELOG

| Phiên Bản | Ngày | Nội Dung |
|-----------|------|---------|
| v1.0 | 2026-03-22 | Khởi tạo từ 2 mẫu: EasyInvoice (8312) + MISA_GTGT/GRAB (2293651) |
| v1.1 | 2026-03-23 | Bổ sung mẫu 3: MISA_MTT (112). Tách MISA → MISA_GTGT + MISA_MTT. Thêm Phần 4.7–4.10. Cập nhật Phần 5 (19 tiêu chí), Phần 8 logic detect. Thêm fields: `trang_thai_tt`, `tinh_tp_ban`, `ma_quoc_gia_ban`, `fkey_label`. |

---

## HƯỚNG DẪN CẬP NHẬT KHI CÓ MẪU MỚI

Khi nhận được ZIP hóa đơn mới, thực hiện theo thứ tự:

```
Bước 1 — Đọc XML
  → Xác định vendor (Phần 8)
  → Nếu vendor mới: thêm vào Bảng 1 + Phần 8

Bước 2 — So sánh cấu trúc
  → Có TTin nào chưa có trong Phần 4? → Thêm vào 4.X
  → Có cấu trúc XML khác (vị trí Fkey, TTHHDTrung...)? → Cập nhật Phần 5

Bước 3 — Bổ sung Tag mới
  → Có tag XML chuẩn chưa có trong Phần 3? → Thêm dòng

Bước 4 — Cập nhật Registry
  → Thêm dòng vào Bảng Phần 10

Bước 5 — Cập nhật Parser
  → Thêm logic vendor mới vào _detect_vendor()
  → Thêm field mới vào InvoiceData / HangHoa nếu cần

Bước 6 — Cập nhật Changelog (Phần 11)
```
