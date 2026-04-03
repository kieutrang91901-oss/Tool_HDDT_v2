"""
XML Parser — Parse hóa đơn điện tử XML (Multi-vendor, Two-Tier).

Kiến trúc Two-Tier:
  - Tầng 1: Trích xuất fields chuẩn TCVN (cố định, mọi vendor)
  - Tầng 2: Tự động trích xuất TẤT CẢ TTKhac/TTin[] ở mọi cấp → extras_*

Auto-Discovery: Trả về danh sách field_keys mới phát hiện để DB đăng ký.

Hỗ trợ: EasyInvoice, MISA_GTGT, MISA_MTT — mở rộng tự động khi gặp vendor mới.

KHÔNG import bất kỳ thư viện UI nào.
"""
from lxml import etree
from typing import List, Dict, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from app.models.entities import InvoiceData, HangHoa, LTSuat, TCHAT_LABEL
from config.logger import get_logger
from config.settings import PARSER_MAX_WORKERS

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def _t(el, xpath: str) -> str:
    """Trích xuất text từ XPath, trả về chuỗi rỗng nếu không tìm thấy."""
    try:
        nodes = el.xpath(xpath)
        if not nodes:
            return ""
        n = nodes[0]
        return (n.text or "").strip() if hasattr(n, "text") else str(n).strip()
    except Exception:
        return ""


def _ttkhac(el, scope_xpath: str = ".") -> Dict[str, str]:
    """Trích xuất TẤT CẢ TTin trong scope thành dict {TTruong: DLieu}.
    
    Đây là nền tảng của Tầng 2 (Dynamic).
    Gọi ở mọi cấp: TTChung, NBan, NMua, HHDVu, TToan, HDon.
    """
    result = {}
    try:
        for item in el.xpath(f"{scope_xpath}//*[local-name()='TTin']"):
            k = item.xpath("*[local-name()='TTruong']")
            v = item.xpath("*[local-name()='DLieu']")
            if k and v:
                key = (k[0].text or "").strip()
                value = (v[0].text or "").strip()
                if key:  # Bỏ qua key rỗng
                    result[key] = value
    except Exception:
        pass
    return result


# ══════════════════════════════════════════════════════════
# VENDOR DETECTION
# ══════════════════════════════════════════════════════════

# MST → Vendor mapping (mở rộng khi biết thêm)
MSTTCGP_MAP = {
    "0105987432": "EASYINV",
    # Thêm MST của VNPT, Viettel, Bkav... ở đây
}


def detect_vendor(root) -> str:
    """Nhận diện nhà cung cấp PM hóa đơn điện tử từ XML.
    
    Thứ tự ưu tiên: MCCQT → TTKhac cấu trúc → KHMSHDon → MSTTCGP → UNKNOWN.
    """
    # B1: Kiểm tra MCCQT (nhanh nhất)
    mccqt = _t(root, "//*[local-name()='MCCQT']/text()")
    if "ZVEBS" in mccqt:
        return "MISA_GTGT"
    if "ZMFWJ" in mccqt:
        return "MISA_MTT"
    # ── Thêm pattern vendor mới ở đây ──
    
    # B2: Kiểm tra TTChung/TTKhac
    ttchung_extras = _ttkhac(root, "//*[local-name()='TTChung']/*[local-name()='TTKhac']")
    if "PortalLink" in ttchung_extras:
        return "EASYINV"
    if "Mã số bí mật" in ttchung_extras:
        return "MISA_MTT"
    
    # B3: Kiểm tra HDon/TTKhac (ngoài cùng)
    hdon_extras = _ttkhac(root, "/*[local-name()='HDon']/*[local-name()='TTKhac']")
    if "SearchKey" in hdon_extras:
        return "MISA_GTGT"
    
    # B4: Mẫu số (KHMSHDon) — MTT thường = 2
    mau_so = _t(root, "//*[local-name()='KHMSHDon']/text()")
    if mau_so == "2":
        return "MISA_MTT"
    
    # B5: MSTTCGP (MST đơn vị cung cấp PM)
    mst_tcgp = _t(root, "//*[local-name()='MSTTCGP']/text()")
    if mst_tcgp in MSTTCGP_MAP:
        return MSTTCGP_MAP[mst_tcgp]
    
    return "UNKNOWN"


# ══════════════════════════════════════════════════════════
# PARSER CHÍNH
# ══════════════════════════════════════════════════════════

def parse_invoice_xml(file_path: str) -> Tuple[InvoiceData, List[Dict[str, str]]]:
    """Parse 1 file XML hóa đơn → InvoiceData + danh sách discovered fields.
    
    Returns:
        Tuple:
        - InvoiceData: Dữ liệu hóa đơn đầy đủ (Tầng 1 + Tầng 2)
        - List[Dict]: Fields mới phát hiện, format: 
          [{"scope": "header", "field_key": "PortalLink", "vendor_hint": "EASYINV"}, ...]
    """
    inv = InvoiceData(file_path=file_path)
    discovered_fields: List[Dict[str, str]] = []
    
    try:
        root = etree.parse(file_path).getroot()
        vendor = detect_vendor(root)
        inv.nha_cung_cap = vendor
        
        # ══════════════════════════════════════════════════
        # TẦNG 1: Fields chuẩn TCVN
        # ══════════════════════════════════════════════════
        
        # ── Header ──────────────────────────────────────
        inv.mau_so          = _t(root, "//*[local-name()='KHMSHDon']/text()")
        inv.ky_hieu         = _t(root, "//*[local-name()='KHHDon']/text()")
        inv.so_hd           = _t(root, "//*[local-name()='SHDon']/text()")
        inv.ngay_lap        = _t(root, "//*[local-name()='NLap']/text()")
        inv.ten_loai_hd     = _t(root, "//*[local-name()='THDon']/text()")
        inv.httt            = _t(root, "//*[local-name()='HTTToan']/text()")
        inv.don_vi_tien_te  = _t(root, "//*[local-name()='DVTTe']/text()")
        inv.ty_gia          = _t(root, "//*[local-name()='TGia']/text()")
        inv.mccqt           = _t(root, "//*[local-name()='MCCQT']/text()")
        inv.qr_content      = _t(root, "//*[local-name()='DLQRCode']/text()")
        inv.mst_tcgp        = _t(root, "//*[local-name()='MSTTCGP']/text()")
        
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
            
            # Tầng 2: Extras người bán
            inv.extras_seller = _ttkhac(b)
            for key in inv.extras_seller:
                discovered_fields.append({
                    "scope": "seller", "field_key": key, "vendor_hint": vendor
                })
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
            inv.so_tk_mua        = _t(m, "*[local-name()='STKNHang']/text()")
            
            # Tầng 2: Extras người mua
            inv.extras_buyer = _ttkhac(m)
            for key in inv.extras_buyer:
                discovered_fields.append({
                    "scope": "buyer", "field_key": key, "vendor_hint": vendor
                })
            
            # Fallback: lấy thông tin từ extras
            if not inv.ma_khach_hang:
                inv.ma_khach_hang = inv.extras_buyer.get("CusCode", "")
            if not inv.httt:
                inv.httt = inv.extras_buyer.get("PaymentMethod", "")
            break
        
        # ══════════════════════════════════════════════════
        # TẦNG 2: Extras ở các cấp khác
        # ══════════════════════════════════════════════════
        
        # TTChung/TTKhac
        inv.extras_header = _ttkhac(
            root, "//*[local-name()='TTChung']/*[local-name()='TTKhac']"
        )
        for key in inv.extras_header:
            discovered_fields.append({
                "scope": "header", "field_key": key, "vendor_hint": vendor
            })
        
        # HDon/TTKhac (ngoài cùng — MISA_GTGT)
        inv.extras_invoice = _ttkhac(
            root, "/*[local-name()='HDon']/*[local-name()='TTKhac']"
        )
        for key in inv.extras_invoice:
            discovered_fields.append({
                "scope": "invoice", "field_key": key, "vendor_hint": vendor
            })
        
        # Fallback httt từ extras_invoice
        if not inv.httt:
            inv.httt = inv.extras_invoice.get("PaymentMethod", "")
        
        # ══════════════════════════════════════════════════
        # HÀNG HÓA (HHDVu)
        # ══════════════════════════════════════════════════
        
        for item in root.xpath("//*[local-name()='HHDVu']"):
            # Tầng 2: Extras từng dòng hàng
            item_extras = _ttkhac(item)
            for key in item_extras:
                discovered_fields.append({
                    "scope": "item", "field_key": key, "vendor_hint": vendor
                })
            
            tc = _t(item, "*[local-name()='TChat']/text()")
            h = HangHoa(
                # Tầng 1
                stt         = _t(item, "*[local-name()='STT']/text()"),
                tinh_chat_ma = tc,
                tinh_chat   = TCHAT_LABEL.get(tc, tc),
                ma_hang     = _t(item, "*[local-name()='MHHDVu']/text()"),
                ten_hang    = _t(item, "*[local-name()='THHDVu']/text()"),
                don_vi_tinh = _t(item, "*[local-name()='DVTinh']/text()"),
                so_luong    = _t(item, "*[local-name()='SLuong']/text()"),
                don_gia     = _t(item, "*[local-name()='DGia']/text()"),
                ty_le_ck    = _t(item, "*[local-name()='TLCKhau']/text()"),
                so_tien_ck  = _t(item, "*[local-name()='STCKhau']/text()"),
                thue_suat   = _t(item, "*[local-name()='TSuat']/text()"),
                thanh_tien  = _t(item, "*[local-name()='ThTien']/text()"),
                # Tầng 2
                extras      = item_extras,
            )
            inv.hang_hoa.append(h)
        
        # ══════════════════════════════════════════════════
        # BẢNG THUẾ SUẤT (LTSuat)
        # ══════════════════════════════════════════════════
        
        for lt in root.xpath("//*[local-name()='LTSuat']"):
            inv.lt_suat.append(LTSuat(
                thue_suat  = _t(lt, "*[local-name()='TSuat']/text()"),
                thanh_tien = _t(lt, "*[local-name()='ThTien']/text()"),
                tong_thue  = _t(lt, "*[local-name()='TThue']/text()"),
            ))
        
        # ══════════════════════════════════════════════════
        # TỔNG KẾT (TToan)
        # ══════════════════════════════════════════════════
        
        for t in root.xpath("//*[local-name()='TToan']"):
            inv.tong_chua_thue      = _t(t, "*[local-name()='TgTCThue']/text()")
            inv.tong_thue           = _t(t, "*[local-name()='TgTThue']/text()")
            inv.tong_ck_tm          = _t(t, "*[local-name()='TTCKTMai']/text()")
            inv.tong_thanh_toan_so  = _t(t, "*[local-name()='TgTTTBSo']/text()")
            inv.tong_thanh_toan_chu = _t(t, "*[local-name()='TgTTTBChu']/text()")
            
            # Tầng 2: Extras thanh toán
            inv.extras_payment = _ttkhac(t)
            for key in inv.extras_payment:
                discovered_fields.append({
                    "scope": "payment", "field_key": key, "vendor_hint": vendor
                })
            break
        
        # Fallback tổng thanh toán chữ
        if not inv.tong_thanh_toan_chu:
            inv.tong_thanh_toan_chu = inv.extras_invoice.get("AmountInWords", "")
        
        # ══════════════════════════════════════════════════
        # CHỮ KÝ SỐ
        # ══════════════════════════════════════════════════
        
        # Chữ ký người bán
        ck_time = root.xpath(
            "//*[local-name()='DSCKS']/*[local-name()='NBan']"
            "//*[local-name()='SigningTime']/text()"
        )
        ck_cn = root.xpath(
            "//*[local-name()='DSCKS']/*[local-name()='NBan']"
            "//*[local-name()='X509SubjectName']/text()"
        )
        inv.da_ky_nguoi_ban = bool(ck_time)
        if ck_time:
            inv.ky_ngay_nguoi_ban = ck_time[0]
        if ck_cn:
            for part in ck_cn[0].split(","):
                if part.strip().startswith("CN="):
                    inv.ky_boi_nguoi_ban = part.strip()[3:]
                    break
        
        # Chữ ký CQT
        cqt_time = root.xpath(
            "//*[local-name()='DSCKS']/*[local-name()='CQT']"
            "//*[local-name()='SigningTime']/text()"
        )
        inv.da_ky_cqt = bool(cqt_time)
        if cqt_time:
            inv.ky_ngay_cqt = cqt_time[0]
        
        # ══════════════════════════════════════════════════
        # HTML PATH (tự tìm)
        # ══════════════════════════════════════════════════
        html_candidate = os.path.join(os.path.dirname(file_path), "invoice.html")
        if os.path.exists(html_candidate):
            inv.html_path = html_candidate
    
    except Exception as e:
        inv.parse_error = str(e)
        logger.error(f"Parse error for {file_path}: {e}")
    
    return inv, discovered_fields


# ══════════════════════════════════════════════════════════
# BATCH PARSER
# ══════════════════════════════════════════════════════════

def parse_batch(
    file_paths: List[str],
    progress_callback=None,
    max_workers: int = PARSER_MAX_WORKERS,
) -> Tuple[List[InvoiceData], List[Dict[str, str]]]:
    """Parse nhiều file XML song song.
    
    Args:
        file_paths: Danh sách đường dẫn XML.
        progress_callback: Callable(current, total) — gọi sau mỗi file.
        max_workers: Số thread tối đa.
    
    Returns:
        Tuple:
        - List[InvoiceData]: Giữ nguyên thứ tự input.
        - List[Dict]: Tất cả discovered fields (đã deduplicate).
    """
    total = len(file_paths)
    if total == 0:
        return [], []
    
    logger.info(f"Starting batch parse: {total} files, {max_workers} workers")
    
    order = {fp: i for i, fp in enumerate(file_paths)}
    results: List[InvoiceData] = []
    all_discovered: List[Dict[str, str]] = []
    seen_fields: Set[Tuple[str, str]] = set()  # (scope, field_key) đã gặp
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(parse_invoice_xml, fp): fp 
            for fp in file_paths
        }
        
        for future in as_completed(futures):
            inv, discovered = future.result()
            results.append(inv)
            
            # Deduplicate discovered fields
            for f in discovered:
                key = (f["scope"], f["field_key"])
                if key not in seen_fields:
                    seen_fields.add(key)
                    all_discovered.append(f)
            
            completed += 1
            if progress_callback:
                try:
                    progress_callback(completed, total)
                except Exception:
                    pass
    
    # Sắp xếp lại theo thứ tự input
    results.sort(key=lambda inv: order.get(inv.file_path, 9999))
    
    logger.info(
        f"Batch parse complete: {total} files, "
        f"{len(all_discovered)} unique fields discovered"
    )
    
    return results, all_discovered
