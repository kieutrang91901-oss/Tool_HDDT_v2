"""Test Two-Tier Parser + Auto-Discovery"""
import sys, os
sys.path.insert(0, r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.models.db_handler import DBHandler
from app.services.invoice_parser_service import InvoiceParserService

db = DBHandler()
parser = InvoiceParserService(db)

# Parse sample EasyInvoice
inv = parser.parse_file(r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2\tests\fixtures\sample_easyinvoice.xml')

print('=== TIER 1 (Fixed) ===')
print(f'Vendor:     {inv.nha_cung_cap}')
print(f'Ky hieu:    {inv.ky_hieu}')
print(f'So HD:      {inv.so_hd}')
print(f'Ngay lap:   {inv.ngay_lap}')
print(f'NB Ten:     {inv.ten_ban}')
print(f'NB MST:     {inv.mst_ban}')
print(f'NM Ten:     {inv.ten_mua}')
print(f'NM MST:     {inv.mst_mua}')
print(f'Tong CThue: {inv.tong_chua_thue}')
print(f'Tong Thue:  {inv.tong_thue}')
print(f'Tong TT:    {inv.tong_thanh_toan_so}')
print(f'Da ky NB:   {inv.da_ky_nguoi_ban}')
print(f'Da ky CQT:  {inv.da_ky_cqt}')
print(f'Status:     {inv.status_label}')
print(f'Hang hoa:   {len(inv.hang_hoa)} dong')

print()
print('=== TIER 2 (Dynamic Extras) ===')
print(f'extras_header:  {inv.extras_header}')
print(f'extras_seller:  {inv.extras_seller}')
print(f'extras_buyer:   {inv.extras_buyer}')
print(f'extras_payment: {inv.extras_payment}')
print(f'Fkey (prop):    {inv.fkey}')
print(f'Portal (prop):  {inv.portal_link}')

print()
print('=== HANG HOA EXTRAS ===')
for h in inv.hang_hoa:
    print(f'  [{h.stt}] {h.ten_hang} | SL={h.so_luong} | DG={h.don_gia} | TT={h.thanh_tien} | extras={h.extras}')

print()
print('=== FIELD REGISTRY (auto-discovered) ===')
fields = parser.get_discovered_fields()
for f in fields:
    scope = f["scope"]
    fkey = f["field_key"]
    vendor = f["vendor_hint"]
    print(f'  {scope:8s} | {fkey:35s} | vendor={vendor}')

print()
print(f'[OK] Two-Tier parse + Auto-Discovery works! ({len(fields)} fields discovered)')

# Test Excel Export
from app.services.excel_export_service import ExcelExportService
from app.models.entities import ColumnConfig

summary_cols = [
    ColumnConfig(column_key="stt", display_name="STT", format_type="text", width=50),
    ColumnConfig(column_key="ky_hieu", display_name="Ky hieu", format_type="text", width=100),
    ColumnConfig(column_key="so_hd", display_name="So HD", format_type="text", width=80),
    ColumnConfig(column_key="ten_ban", display_name="Ten NB", format_type="text", width=250),
    ColumnConfig(column_key="tong_chua_thue", display_name="Tong chua thue", format_type="currency", width=130),
    ColumnConfig(column_key="tong_thue", display_name="Tong thue", format_type="currency", width=120),
    ColumnConfig(column_key="tong_thanh_toan", display_name="Tong TT", format_type="currency", width=130),
]

detail_cols = [
    ColumnConfig(column_key="stt", display_name="STT", format_type="text", width=50),
    ColumnConfig(column_key="ten_hang", display_name="Ten hang", format_type="text", width=300),
    ColumnConfig(column_key="so_luong", display_name="SL", format_type="number", width=80),
    ColumnConfig(column_key="don_gia", display_name="Don gia", format_type="currency", width=120),
    ColumnConfig(column_key="thanh_tien", display_name="Thanh tien", format_type="currency", width=130),
]

dest = r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2\data\test_export.xlsx'
result = ExcelExportService.export_detail([inv], dest, summary_cols, detail_cols)
print(f'[OK] Excel export: {result}')
