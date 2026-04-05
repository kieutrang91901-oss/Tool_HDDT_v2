"""
InvoiceQueryService — Tra cứu & tải hóa đơn từ API cổng thuế.

Kết hợp APIClient + DBHandler để query, cache, download.
Download tích hợp trực tiếp trong luồng Invoice List.
"""
import os
import json
from typing import List, Optional, Callable, Dict, Any
from app.models.api_client import APIClient
from app.models.db_handler import DBHandler
from app.models.file_handler import FileHandler
from app.models.entities import (
    InvoiceSummary, QueryResult, DownloadResult, BatchDownloadResult,
)
from config.logger import get_logger
from config.settings import DATA_DIR

logger = get_logger(__name__)


class InvoiceQueryService:
    """Tra cứu danh sách HĐ mua vào / bán ra từ cổng thuế."""
    
    def __init__(self, api_client: APIClient, db: DBHandler):
        self._api = api_client
        self._db = db
        self._download_base = os.path.join(DATA_DIR, "downloads")
    
    def query_invoices(
        self,
        loai: str,
        tu_ngay: str,
        den_ngay: str,
        trang_thai: str = "",
        page_size: int = 50,
        is_sco: bool = False,
        state: str = "",
    ) -> QueryResult:
        """Tra cứu danh sách hóa đơn từ API (1 trang).
        
        Args:
            loai: 'purchase' (mua vào) | 'sold' (bán ra)
            tu_ngay: DD/MM/YYYYTHH:MM:SS
            den_ngay: DD/MM/YYYYTHH:MM:SS
            trang_thai: Filter ttxly (5, 6, 8)
            page_size: Số dòng mỗi trang (max 50)
            is_sco: True nếu query SCO endpoint
            state: Cursor từ response trước (cho page 2+)
        
        Returns:
            QueryResult (bao gồm .state cho trang tiếp)
        """
        result = QueryResult(page_size=page_size)
        
        try:
            data = self._api.query_invoices(
                loai=loai,
                tu_ngay=tu_ngay,
                den_ngay=den_ngay,
                trang_thai=trang_thai,
                page_size=page_size,
                is_sco=is_sco,
                state=state,
            )
            
            if "error" in data:
                result.error_msg = data["error"]
                return result
            
            datas = data.get("datas", [])
            result.total = data.get("total", len(datas))
            result.state = data.get("state", "")  # Cursor cho trang tiếp
            result.success = True
            
            for item in datas:
                summary = self._parse_api_item(item, loai)
                result.invoices.append(summary)
            
            logger.info(
                f"Query {loai}: {len(result.invoices)} invoices "
                f"(total {result.total}, has_next={bool(result.state)})"
            )
            
        except Exception as e:
            result.error_msg = str(e)
            logger.error(f"Query error: {e}")
        
        return result
    
    def query_all_invoices(
        self,
        loai: str,
        tu_ngay: str,
        den_ngay: str,
        is_sco: bool = False,
        progress_cb=None,
    ) -> List[InvoiceSummary]:
        """Tải TẤT CẢ hóa đơn bằng state cursor pagination.
        
        API trả max 50/request + cursor 'state' để lấy trang tiếp.
        Method này tự động follow cursor cho đến khi hết data.
        
        Args:
            loai: 'purchase' | 'sold'
            tu_ngay: DD/MM/YYYYTHH:MM:SS
            den_ngay: DD/MM/YYYYTHH:MM:SS
            is_sco: True nếu query SCO endpoint
            progress_cb: callback(fetched_count) khi có thêm kết quả
            
        Returns:
            List[InvoiceSummary] — đã dedup
        """
        import time
        
        all_results = []
        seen_keys = set()
        state = ""
        page_num = 0
        prefix = "SCO-" if is_sco else ""
        
        while True:
            page_num += 1
            
            if page_num > 1:
                time.sleep(0.3)  # Delay tránh rate limit
            
            qr = self.query_invoices(
                loai=loai, tu_ngay=tu_ngay, den_ngay=den_ngay,
                is_sco=is_sco, page_size=50, state=state,
            )
            
            if not qr.success or not qr.invoices:
                break
            
            # Dedup
            new_count = 0
            for inv in qr.invoices:
                key = (inv.khhdon, inv.shdon)
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_results.append(inv)
                    new_count += 1
            
            logger.info(
                f"query_all {prefix}{loai} page {page_num}: "
                f"{len(qr.invoices)} records, {new_count} new "
                f"(total: {len(all_results)}/{qr.total})"
            )
            
            if progress_cb:
                progress_cb(len(all_results))
            
            # Dừng nếu: không còn cursor → hết data
            if not qr.state:
                break
            
            state = qr.state
            
            # Safety: max 100 pages
            if page_num >= 100:
                logger.warning(f"query_all {prefix}{loai}: max pages reached")
                break
        
        logger.info(f"query_all {prefix}{loai}: {len(all_results)} unique invoices")
        return all_results
    
    def _parse_api_item(self, item: Dict, loai: str) -> InvoiceSummary:
        """Parse 1 item từ API response thành InvoiceSummary."""
        # Mapping trạng thái
        ttxly = str(item.get("ttxly", ""))
        ttxly_labels = {
            "5": "Đã cấp mã",
            "6": "CQT không cấp mã",
            "8": "CQT nhận HĐ MTT",
        }
        
        return InvoiceSummary(
            khhdon=item.get("khhdon", ""),
            shdon=str(item.get("shdon", "")),
            ngay_lap=item.get("tdlap", ""),
            mst_nban=item.get("nbmst", ""),
            ten_nban=item.get("nbten", ""),
            mst_nmua=item.get("nmmst", ""),
            ten_nmua=item.get("nmten", ""),
            tong_tien_cthue=str(item.get("tgtcthue", "")),
            tong_tien_thue=str(item.get("tgtthue", "")),
            tong_thanh_toan=str(item.get("tgtttbso", "")),
            trang_thai=ttxly,
            trang_thai_label=ttxly_labels.get(ttxly, ttxly),
            loai_hd=loai,
            raw_data=item,
        )
    
    # ═══════════════════════════════════════════════════════
    # CACHE VÀO DB
    # ═══════════════════════════════════════════════════════
    
    def cache_query_results(
        self,
        account_mst: str,
        invoices: List[InvoiceSummary],
    ) -> int:
        """Lưu kết quả tra cứu vào DB cache.
        
        Returns:
            Số invoice đã lưu thành công.
        """
        count = 0
        for inv in invoices:
            success = self._db.upsert_invoice({
                "account_mst": account_mst,
                "loai": inv.loai_hd,
                "ky_hieu": inv.khhdon,
                "so_hd": inv.shdon,
                "ngay_lap": inv.ngay_lap,
                "mst_ban": inv.mst_nban,
                "ten_ban": inv.ten_nban,
                "mst_mua": inv.mst_nmua,
                "ten_mua": inv.ten_nmua,
                "tong_tien": self._safe_float(inv.tong_tien_cthue),
                "tong_thue": self._safe_float(inv.tong_tien_thue),
                "tong_thanh_toan": self._safe_float(inv.tong_thanh_toan),
                "trang_thai": inv.trang_thai,
                "raw_json": json.dumps(inv.raw_data, ensure_ascii=False),
            })
            if success:
                count += 1
        
        logger.info(f"Cached {count}/{len(invoices)} invoices for {account_mst}")
        return count
    
    # ═══════════════════════════════════════════════════════
    # TẢI XML
    # ═══════════════════════════════════════════════════════
    def download_xml(
        self,
        nbmst: str,
        khhdon: str,
        shdon: str,
        account_mst: str = "",
        khmshdon: str = "1",
    ) -> DownloadResult:
        """Tải 1 file XML hóa đơn.
        
        Tự động phát hiện HĐ máy tính tiền (SCO/MTT) dựa trên khmshdon.
        Nếu endpoint bình thường fail → thử endpoint SCO và ngược lại.
        
        Returns:
            DownloadResult
        """
        try:
            dest_folder = FileHandler.ensure_download_folder(
                self._download_base, account_mst or nbmst
            )
            
            # Auto-detect SCO: khmshdon="6" hoặc ký hiệu bắt đầu bằng "K"
            is_sco = (str(khmshdon) == "6") or (khhdon and khhdon[0].upper() == "K")
            
            # Thử endpoint chính trước
            content = self._api.download_xml(
                nbmst, khhdon, shdon, khmshdon=khmshdon, is_sco=is_sco
            )
            
            # Nếu fail → thử endpoint ngược lại (fallback)
            if content is None:
                logger.info(
                    f"Fallback: trying {'normal' if is_sco else 'sco'} "
                    f"endpoint for {khhdon}-{shdon}"
                )
                content = self._api.download_xml(
                    nbmst, khhdon, shdon, khmshdon=khmshdon, is_sco=not is_sco
                )
            
            if content is None:
                return DownloadResult(error_msg="Không tải được file XML")
            
            # Lưu file ZIP
            file_name = f"{khhdon}_{shdon}.zip"
            file_path = os.path.join(dest_folder, file_name)
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Giải nén
            xml_files = FileHandler.extract_zip(file_path)
            xml_path = xml_files[0] if xml_files else file_path
            
            # Cập nhật DB
            if account_mst:
                self._db.upsert_invoice({
                    "account_mst": account_mst,
                    "loai": "",
                    "ky_hieu": khhdon,
                    "so_hd": shdon,
                    "mst_ban": nbmst,
                    "xml_path": xml_path,
                })
            
            return DownloadResult(success=True, file_path=xml_path)
            
        except Exception as e:
            logger.error(f"Download error {khhdon}-{shdon}: {e}")
            return DownloadResult(error_msg=str(e))
    
    def download_batch(
        self,
        invoices: List[InvoiceSummary],
        account_mst: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BatchDownloadResult:
        """Tải nhiều hóa đơn XML song song (concurrent).
        
        Args:
            invoices: Danh sách HĐ cần tải
            account_mst: MST tài khoản đang đăng nhập
            progress_callback: Callable(current, total)
        
        Returns:
            BatchDownloadResult
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        total = len(invoices)
        batch_result = BatchDownloadResult(total=total)
        MAX_WORKERS = 3
        
        def _dl_one(inv):
            return self.download_xml(
                nbmst=inv.mst_nban,
                khhdon=inv.khhdon,
                shdon=inv.shdon,
                account_mst=account_mst,
            )
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            for i, inv in enumerate(invoices):
                future = executor.submit(_dl_one, inv)
                futures[future] = inv
                if i < total - 1:
                    time.sleep(0.15)
            
            done = 0
            for future in as_completed(futures):
                result = future.result()
                done += 1
                
                batch_result.results.append(result)
                if result.success:
                    batch_result.success_count += 1
                else:
                    batch_result.failed_count += 1
                
                if progress_callback:
                    try:
                        progress_callback(done, total)
                    except Exception:
                        pass
        
        logger.info(
            f"Batch download: {batch_result.success_count}/{total} success, "
            f"{batch_result.failed_count} failed"
        )
        return batch_result
    
    # ═══════════════════════════════════════════════════════
    # EXPORT BẢNG KÊ EXCEL TỪ CỔNG THUẾ
    # ═══════════════════════════════════════════════════════
    
    def export_excel_from_portal(
        self,
        tu_ngay: str,
        den_ngay: str,
        save_path: str,
    ) -> bool:
        """Tải bảng kê Excel trực tiếp từ cổng thuế và lưu file.
        
        Tải cả HĐ bình thường + HĐ MTT (nếu có).
        
        Args:
            tu_ngay: DD/MM/YYYYTHH:MM:SS
            den_ngay: DD/MM/YYYYTHH:MM:SS  
            save_path: Đường dẫn file .xlsx output
            
        Returns:
            True nếu thành công
        """
        try:
            # Tải bảng kê HĐ bình thường
            content = self._api.export_excel(tu_ngay, den_ngay, is_sco=False)
            if content:
                with open(save_path, "wb") as f:
                    f.write(content)
                logger.info(f"Exported portal Excel: {save_path}")
                return True
            
            logger.warning("Export Excel: No data from portal")
            return False
            
        except Exception as e:
            logger.error(f"Export Excel error: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════
    
    @staticmethod
    def _safe_float(value) -> float:
        """Chuyển đổi an toàn sang float."""
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0
