"""
InvoiceParserService — Parse batch XML + Auto-Discovery.

Orchestrator cho xml_parser.py và db_handler.py:
1. Nhận input (files, folders, zips)
2. Gọi parser (Two-Tier)
3. Đăng ký discovered fields vào field_registry
4. Trả về InvoiceData[]
"""
from typing import List, Optional, Callable, Dict
from app.models.xml_parser import parse_invoice_xml, parse_batch
from app.models.file_handler import FileHandler
from app.models.db_handler import DBHandler
from app.models.entities import InvoiceData
from config.logger import get_logger

logger = get_logger(__name__)


class InvoiceParserService:
    """Parse file XML/ZIP hóa đơn (multi-vendor) + auto-register fields."""
    
    def __init__(self, db: DBHandler):
        self._db = db
    
    # ═══════════════════════════════════════════════════════
    # PARSE SINGLE
    # ═══════════════════════════════════════════════════════
    
    def parse_file(self, file_path: str) -> InvoiceData:
        """Parse 1 file XML + đăng ký fields mới.
        
        Returns:
            InvoiceData (full parsed data, Tầng 1 + Tầng 2)
        """
        inv, discovered = parse_invoice_xml(file_path)
        
        # Auto-register discovered fields
        if discovered:
            self._db.register_fields_batch(discovered)
            logger.debug(
                f"Registered {len(discovered)} fields from {file_path}"
            )
        
        return inv
    
    # ═══════════════════════════════════════════════════════
    # PARSE BATCH
    # ═══════════════════════════════════════════════════════
    
    def parse_batch(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[InvoiceData]:
        """Parse nhiều file XML song song + đăng ký fields mới.
        
        Args:
            file_paths: Danh sách đường dẫn XML
            progress_callback: Callable(current, total)
        
        Returns:
            List[InvoiceData] — giữ nguyên thứ tự input
        """
        if not file_paths:
            return []
        
        invoices, discovered = parse_batch(
            file_paths, 
            progress_callback=progress_callback
        )
        
        # Auto-register tất cả discovered fields
        if discovered:
            registered = self._db.register_fields_batch(discovered)
            logger.info(
                f"Auto-discovery: {registered} unique fields registered "
                f"from {len(file_paths)} files"
            )
        
        return invoices
    
    # ═══════════════════════════════════════════════════════
    # PARSE ZIP / FOLDER
    # ═══════════════════════════════════════════════════════
    
    def parse_zip(
        self,
        zip_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[InvoiceData]:
        """Giải nén ZIP rồi parse tất cả XML bên trong."""
        xml_files = FileHandler.extract_zip(zip_path)
        return self.parse_batch(xml_files, progress_callback)
    
    def parse_folder(
        self,
        folder_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[InvoiceData]:
        """Quét folder tìm XML rồi parse tất cả."""
        xml_files = FileHandler.find_xml_files(folder_path)
        return self.parse_batch(xml_files, progress_callback)
    
    def parse_input(
        self,
        paths: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[InvoiceData]:
        """Xử lý hỗn hợp: files + folders + ZIPs → parse tất cả.
        
        Đây là method chính cho chức năng Import Offline.
        """
        xml_files = FileHandler.process_input(paths)
        return self.parse_batch(xml_files, progress_callback)
    
    # ═══════════════════════════════════════════════════════
    # QUERY DYNAMIC FIELDS
    # ═══════════════════════════════════════════════════════
    
    def get_discovered_fields(self, scope: str = "") -> List[Dict]:
        """Lấy danh sách fields đã phát hiện (cho Column Chooser).
        
        Args:
            scope: Lọc theo scope ('header', 'item', ...).
                   Rỗng = tất cả.
        
        Returns:
            List[FieldRegistryEntry] as dicts
        """
        entries = self._db.get_discovered_fields(scope)
        return [
            {
                "scope": e.scope,
                "field_key": e.field_key,
                "display_name": e.display_name or e.field_key,
                "format_type": e.format_type,
                "vendor_hint": e.vendor_hint,
                "seen_count": e.seen_count,
            }
            for e in entries
        ]
    
    # ═══════════════════════════════════════════════════════
    # VENDOR DETECTION
    # ═══════════════════════════════════════════════════════
    
    @staticmethod
    def detect_vendor(file_path: str) -> str:
        """Nhận diện vendor của 1 file XML."""
        from app.models.xml_parser import detect_vendor as _detect
        from lxml import etree
        try:
            root = etree.parse(file_path).getroot()
            return _detect(root)
        except Exception:
            return "UNKNOWN"
