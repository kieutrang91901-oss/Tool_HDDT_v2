# Tool Quản Lý Hóa Đơn Điện Tử v2 (HDDT v2)

> Ứng dụng Desktop quản lý hóa đơn điện tử — hỗ trợ nhiều MST, import offline, tải từ cổng thuế, export Excel.

## Tính năng chính

- **Đăng nhập cổng thuế** — Hỗ trợ nhiều MST, captcha, session tự động
- **Tra cứu & tải HĐ** — Tìm kiếm HĐ mua vào/bán ra, tải XML từ API
- **Import offline** — Đọc file XML/ZIP từ máy tính
- **Bảng dữ liệu Excel-like** — Hiển thị 10K+ dòng, user tự chọn cột
- **Export Excel** — Xuất tổng hợp + chi tiết, format #,##0 tự động
- **Two-Tier Data Model** — Tự phát hiện fields vendor-specific (EasyInvoice, MISA, VNPT...)
- **Bảo mật** — Password lưu trong Windows Credential Locker
- **Auto-update** — Cập nhật API endpoints tự động từ remote server
- **Dark/Light theme** — Giao diện hiện đại, chuyên nghiệp

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| UI Framework | CustomTkinter |
| Data Table | tksheet |
| Database | SQLite3 (WAL mode) |
| HTTP Client | httpx |
| XML Parser | lxml |
| Excel Export | openpyxl |
| Security | keyring (Windows Credential Locker) |
| Packaging | PyInstaller (onefile) |

## Kiến trúc

```
Tool_HDDT_v2/
├── main.py                    # Entry point
├── config/
│   ├── settings.py            # Hằng số, đường dẫn
│   ├── logger.py              # Logging (rotating file)
│   ├── api_config.py          # API endpoints (remote-updatable)
│   ├── column_config.py       # Cột mặc định Summary/Detail
│   └── theme.py               # Dark/Light palettes, fonts
├── app/
│   ├── models/                # Data Layer
│   │   ├── entities.py        # Dataclasses (Two-Tier)
│   │   ├── db_handler.py      # SQLite CRUD
│   │   ├── credential_store.py # Keyring wrapper
│   │   ├── api_client.py      # HTTP client
│   │   ├── xml_parser.py      # Multi-vendor parser
│   │   └── file_handler.py    # ZIP/folder scanner
│   ├── services/              # Business Logic
│   │   ├── auth_service.py
│   │   ├── account_service.py
│   │   ├── invoice_query_service.py
│   │   ├── invoice_parser_service.py
│   │   ├── excel_export_service.py
│   │   └── remote_config_service.py
│   └── ui/                    # Presentation Layer
│       ├── main_window.py     # Sidebar + Content + StatusBar
│       ├── components/        # Reusable widgets
│       │   ├── data_table.py, toolbar.py, toast.py
│       │   ├── column_chooser.py, dialog.py
│       │   ├── search_bar.py, status_bar.py
│       │   └── loading_indicator.py
│       └── views/             # Screens
│           ├── login_view.py
│           ├── invoice_list_view.py
│           ├── invoice_detail_view.py
│           └── settings_view.py
├── data/                      # SQLite DB + downloads (auto-created)
├── logs/                      # Log files (auto-created)
└── tests/                     # Test suite
```

## Cài đặt & Chạy

### Development
```bash
# Cài dependencies
pip install -r requirements.txt

# Chạy ứng dụng
python main.py
```

### Build EXE
```bash
pip install pyinstaller
pyinstaller hddt_v2.spec
# Output: dist/HDDT_v2.exe
```

## Two-Tier Data Model

### Tầng 1 (Fixed) — Fields chuẩn TCVN
Mọi hóa đơn đều có: Ký hiệu, Số HĐ, Ngày lập, Người bán/mua, Hàng hóa...

### Tầng 2 (Dynamic) — Auto-Discovery
Parser tự phát hiện TẤT CẢ `TTKhac/TTin[]` ở mọi cấp XML:
- `extras_header`: PortalLink, Fkey, Mã số bí mật...
- `extras_seller`: Tỉnh/Thành phố người bán...
- `extras_buyer`: CusCode, PaymentMethod...
- `extras_payment`: Tổng tiền thuế TTĐB...
- `extras_invoice`: SearchKey, MappingKey...

Fields mới tự đăng ký vào `field_registry` → User tự chọn hiển thị qua Column Chooser.

## Changelog

### v2.0.0 (2026-03-29)
- Initial release — rebuild bài bản từ v1
- Two-Tier Data Model + Auto-Discovery
- CustomTkinter UI + tksheet
- Multi-MST support
- Keyring credential storage
- Remote Config auto-update
