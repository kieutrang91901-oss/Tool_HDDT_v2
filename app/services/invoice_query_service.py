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
    
    # ═══════════════════════════════════════════════════════
    # TRA CỨU
    # ═══════════════════════════════════════════════════════
    
    def query_invoices(
        self,
        loai: str,
        tu_ngay: str,
        den_ngay: str,
        trang_thai: str = "",
        page: int = 1,
        page_size: int = 50,
        is_sco: bool = False,
    ) -> QueryResult:
        """Tra cứu danh sách hóa đơn từ API.
        
        Args:
            loai: 'purchase' (mua vào) | 'sold' (bán ra)
            tu_ngay: Từ ngày (DD/MM/YYYYTHH:MM:SS)
            den_ngay: Đến ngày
            trang_thai: Filter trạng thái xử lý (5, 6, 8)
            page: Trang hiện tại
            page_size: Số dòng mỗi trang
            is_sco: True nếu tra cứu HĐ máy tính tiền
        
        Returns:
            QueryResult
        """
        result = QueryResult(page=page, page_size=page_size)
        
        try:
            data = self._api.query_invoices(
                loai=loai,
                tu_ngay=tu_ngay,
                den_ngay=den_ngay,
                trang_thai=trang_thai,
                page=page,
                page_size=page_size,
                is_sco=is_sco,
            )
            
            if "error" in data:
                result.error_msg = data["error"]
                return result
            
            # Parse response
            datas = data.get("datas", [])
            result.total = data.get("total", len(datas))
            result.success = True
            
            for item in datas:
                summary = self._parse_api_item(item, loai)
                result.invoices.append(summary)
            
            logger.info(
                f"Query {loai}: {len(result.invoices)} invoices "
                f"(page {page}, total {result.total})"
            )
            
        except Exception as e:
            result.error_msg = str(e)
            logger.error(f"Query error: {e}")
        
        return result
    
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
    ) -> DownloadResult:
        """Tải 1 file XML hóa đơn.
        
        Returns:
            DownloadResult
        """
        try:
            dest_folder = FileHandler.ensure_download_folder(
                self._download_base, account_mst or nbmst
            )
            
            content = self._api.download_xml(nbmst, khhdon, shdon)
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
        """Tải nhiều hóa đơn XML (danh sách đang hiển thị sau lọc).
        
        Args:
            invoices: Danh sách HĐ cần tải (từ bảng đã lọc)
            account_mst: MST tài khoản đang đăng nhập
            progress_callback: Callable(current, total)
        
        Returns:
            BatchDownloadResult
        """
        total = len(invoices)
        batch_result = BatchDownloadResult(total=total)
        
        for i, inv in enumerate(invoices):
            result = self.download_xml(
                nbmst=inv.mst_nban,
                khhdon=inv.khhdon,
                shdon=inv.shdon,
                account_mst=account_mst,
            )
            
            batch_result.results.append(result)
            if result.success:
                batch_result.success_count += 1
            else:
                batch_result.failed_count += 1
            
            if progress_callback:
                try:
                    progress_callback(i + 1, total)
                except Exception:
                    pass
        
        logger.info(
            f"Batch download: {batch_result.success_count}/{total} success, "
            f"{batch_result.failed_count} failed"
        )
        return batch_result
    
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
