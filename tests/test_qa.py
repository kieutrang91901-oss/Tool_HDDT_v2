"""QA Test — Kiểm tra toàn diện backend + import chain."""
import sys, os
sys.path.insert(0, r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

errors = []
warnings = []

def test(name, func):
    try:
        func()
        print(f"  [OK] {name}")
    except Exception as e:
        errors.append((name, str(e)))
        print(f"  [FAIL] {name}: {e}")

def warn(msg):
    warnings.append(msg)
    print(f"  [WARN] {msg}")

# ═══════════════════════════════════════════════════════
print("=== 1. CONFIG IMPORTS ===")
# ═══════════════════════════════════════════════════════
test("config.settings", lambda: __import__('config.settings'))
test("config.logger", lambda: __import__('config.logger'))
test("config.api_config", lambda: __import__('config.api_config'))
test("config.column_config", lambda: __import__('config.column_config'))
test("config.theme", lambda: __import__('config.theme'))

# ═══════════════════════════════════════════════════════
print("\n=== 2. MODEL IMPORTS ===")
# ═══════════════════════════════════════════════════════
test("entities", lambda: __import__('app.models.entities', fromlist=['InvoiceData']))
test("db_handler", lambda: __import__('app.models.db_handler', fromlist=['DBHandler']))
test("credential_store", lambda: __import__('app.models.credential_store', fromlist=['CredentialStore']))
test("api_client", lambda: __import__('app.models.api_client', fromlist=['APIClient']))
test("xml_parser", lambda: __import__('app.models.xml_parser', fromlist=['parse_invoice_xml']))
test("file_handler", lambda: __import__('app.models.file_handler', fromlist=['FileHandler']))

# ═══════════════════════════════════════════════════════
print("\n=== 3. SERVICE IMPORTS ===")
# ═══════════════════════════════════════════════════════
test("auth_service", lambda: __import__('app.services.auth_service', fromlist=['AuthService']))
test("account_service", lambda: __import__('app.services.account_service', fromlist=['AccountService']))
test("invoice_query_service", lambda: __import__('app.services.invoice_query_service', fromlist=['InvoiceQueryService']))
test("invoice_parser_service", lambda: __import__('app.services.invoice_parser_service', fromlist=['InvoiceParserService']))
test("excel_export_service", lambda: __import__('app.services.excel_export_service', fromlist=['ExcelExportService']))
test("remote_config_service", lambda: __import__('app.services.remote_config_service', fromlist=['RemoteConfigService']))

# ═══════════════════════════════════════════════════════
print("\n=== 4. DB HANDLER CRUD ===")
# ═══════════════════════════════════════════════════════
from app.models.db_handler import DBHandler
db = DBHandler()

def test_accounts():
    db.add_account("TEST001", "Test Corp", "test001")
    acc = db.get_account("TEST001")
    assert acc is not None, "Account not found"
    assert acc.ten_cty == "Test Corp"
    db.update_account("TEST001", ten_cty="Updated Corp")
    acc2 = db.get_account("TEST001")
    assert acc2.ten_cty == "Updated Corp"
    db.delete_account("TEST001")
    assert db.get_account("TEST001") is None
test("Account CRUD", test_accounts)

def test_settings():
    db.set_setting("test_key", "test_value")
    assert db.get_setting("test_key") == "test_value"
    assert db.get_setting("non_exist", "default") == "default"
test("Settings", test_settings)

def test_column_config():
    from app.models.entities import ColumnConfig
    col = ColumnConfig(column_key="test_col", display_name="Test", table_name="test", format_type="currency", width=100)
    db.upsert_column(col)
    cols = db.get_columns("test")
    assert len(cols) >= 1
    db.update_column_visibility("test", "test_col", False)
    vis_cols = db.get_columns("test", visible_only=True)
    assert not any(c.column_key == "test_col" for c in vis_cols)
test("Column Config", test_column_config)

def test_field_registry():
    db.register_field("header", "TestField", "EASYINV")
    db.register_field("header", "TestField", "MISA")  # increment count
    fields = db.get_discovered_fields("header")
    tf = [f for f in fields if f.field_key == "TestField"]
    assert len(tf) == 1
    assert tf[0].seen_count >= 2
    assert "EASYINV" in tf[0].vendor_hint
test("Field Registry", test_field_registry)

def test_invoice_upsert():
    data = {"account_mst": "TEST", "loai": "purchase", "ky_hieu": "C26T", 
            "so_hd": "999", "ngay_lap": "2024-12-30", "mst_ban": "0123",
            "ten_ban": "Test Ban", "tong_thanh_toan": 1000000}
    assert db.upsert_invoice(data)
    inv = db.get_invoices(account_mst="TEST")
    assert len(inv) >= 1
    assert db.count_invoices(account_mst="TEST") >= 1
test("Invoice Upsert", test_invoice_upsert)

def test_remote_config():
    db.save_remote_config("test_rc", "1.0.1", {"base_url": "https://test.com"})
    rc = db.get_remote_config("test_rc")
    assert rc is not None
    assert rc["version"] == "1.0.1"
test("Remote Config", test_remote_config)

# ═══════════════════════════════════════════════════════
print("\n=== 5. XML PARSER ===")
# ═══════════════════════════════════════════════════════
from app.services.invoice_parser_service import InvoiceParserService
parser = InvoiceParserService(db)

def test_parse_sample():
    xml = r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2\tests\fixtures\sample_easyinvoice.xml'
    inv = parser.parse_file(xml)
    assert inv.nha_cung_cap == "EASYINV", f"Vendor={inv.nha_cung_cap}"
    assert inv.so_hd == "238"
    assert inv.ten_ban == "CÔNG TY CỔ PHẦN ABC"
    assert len(inv.hang_hoa) == 2
    assert inv.fkey == "ABC123DEF456"
    assert inv.portal_link == "https://einvoice.vn/tra-cuu"
    assert len(inv.extras_header) >= 2
    assert len(inv.extras_buyer) >= 2
    assert inv.status_label == "Hợp lệ"
test("Parse EasyInvoice", test_parse_sample)

def test_parse_batch():
    xml = r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2\tests\fixtures\sample_easyinvoice.xml'
    invs = parser.parse_batch([xml, xml])
    assert len(invs) == 2
test("Parse Batch", test_parse_batch)

def test_parse_error():
    inv = parser.parse_file("nonexistent.xml")
    assert inv.parse_error != ""
    assert inv.status_label == "Lỗi đọc file"
test("Parse Error Handling", test_parse_error)

# ═══════════════════════════════════════════════════════
print("\n=== 6. EXCEL EXPORT ===")
# ═══════════════════════════════════════════════════════
from app.services.excel_export_service import ExcelExportService
from app.models.entities import ColumnConfig as CC

def test_export():
    xml = r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2\tests\fixtures\sample_easyinvoice.xml'
    inv = parser.parse_file(xml)
    
    s_cols = [CC(column_key="stt", display_name="STT", format_type="text", width=50),
              CC(column_key="ky_hieu", display_name="Ky hieu", format_type="text", width=100),
              CC(column_key="tong_thanh_toan", display_name="Tong TT", format_type="currency", width=130)]
    d_cols = [CC(column_key="ten_hang", display_name="Ten hang", format_type="text", width=200),
              CC(column_key="don_gia", display_name="Don gia", format_type="currency", width=120)]
    
    dest = r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2\data\qa_test.xlsx'
    r1 = ExcelExportService.export_summary([inv], dest, s_cols)
    assert r1["success"], f"Summary export failed: {r1['error_msg']}"
    
    dest2 = r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2\data\qa_detail.xlsx'
    r2 = ExcelExportService.export_detail([inv], dest2, s_cols, d_cols)
    assert r2["success"], f"Detail export failed: {r2['error_msg']}"
    assert r2["row_count"] == 2
test("Excel Export", test_export)

# ═══════════════════════════════════════════════════════
print("\n=== 7. THEME & FORMAT ===")
# ═══════════════════════════════════════════════════════
from config.theme import format_number, get_colors, set_mode

def test_theme():
    c = get_colors("dark")
    assert "bg_primary" in c
    c2 = get_colors("light")
    assert c2["bg_primary"] != c["bg_primary"]
test("Theme colors", test_theme)

def test_format():
    assert format_number(1234567, "currency") == "1.234.567"
    assert format_number(50000.5, "number") == "50.000,50"
    assert format_number("", "currency") == ""
    assert format_number(None, "text") == ""
    assert format_number(0, "currency") == "0"
test("Number format", test_format)

# ═══════════════════════════════════════════════════════
print("\n=== 8. COLUMN CONFIG HELPERS ===")
# ═══════════════════════════════════════════════════════
from config.column_config import make_dynamic_column_key, parse_dynamic_column_key

def test_column_helpers():
    key = make_dynamic_column_key("header", "PortalLink")
    assert key == "hdr_PortalLink"
    scope, fkey = parse_dynamic_column_key(key)
    assert scope == "header" and fkey == "PortalLink"
test("Column key helpers", test_column_helpers)

# ═══════════════════════════════════════════════════════
print("\n=== 9. SERVICE INSTANTIATION ===")
# ═══════════════════════════════════════════════════════
from app.models.api_client import APIClient
from app.models.credential_store import CredentialStore
from app.services.auth_service import AuthService
from app.services.account_service import AccountService
from app.services.invoice_query_service import InvoiceQueryService
from app.services.remote_config_service import RemoteConfigService

def test_services():
    api = APIClient()
    cred = CredentialStore()
    AuthService(api, cred)
    AccountService(db, cred)
    InvoiceQueryService(api, db)
    RemoteConfigService(db)
test("Service instantiation", test_services)

# ═══════════════════════════════════════════════════════
print("\n=== 10. UI IMPORTS (no display) ===")
# ═══════════════════════════════════════════════════════
test("components.__init__", lambda: __import__('app.ui.components', fromlist=['DataTable']))

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════
print(f"\n{'='*60}")
if errors:
    print(f"FAILED: {len(errors)} tests")
    for name, err in errors:
        print(f"  - {name}: {err}")
else:
    print("ALL TESTS PASSED!")
if warnings:
    print(f"\nWarnings: {len(warnings)}")
    for w in warnings:
        print(f"  - {w}")
print(f"{'='*60}")
