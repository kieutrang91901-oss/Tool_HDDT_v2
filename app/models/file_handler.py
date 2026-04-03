"""
File Handler — Đọc/giải nén ZIP, quản lý file XML hóa đơn.

Chức năng:
- Giải nén file ZIP (hỗ trợ nested XML)
- Quét folder tìm tất cả file XML/ZIP
- Quản lý thư mục lưu trữ file đã tải

KHÔNG import bất kỳ thư viện UI nào.
"""
import os
import zipfile
import tempfile
import shutil
from typing import List, Optional, Tuple
from config.logger import get_logger

logger = get_logger(__name__)


class FileHandler:
    """Quản lý file XML/ZIP hóa đơn."""
    
    # Extensions hỗ trợ
    XML_EXTENSIONS = {".xml"}
    ZIP_EXTENSIONS = {".zip"}
    ALL_EXTENSIONS = XML_EXTENSIONS | ZIP_EXTENSIONS
    
    @staticmethod
    def find_xml_files(folder_path: str) -> List[str]:
        """Tìm tất cả file XML trong folder (đệ quy).
        
        Returns:
            Danh sách đường dẫn tuyệt đối của các file XML.
        """
        xml_files = []
        try:
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    if os.path.splitext(f)[1].lower() in FileHandler.XML_EXTENSIONS:
                        xml_files.append(os.path.join(root, f))
        except Exception as e:
            logger.error(f"Error scanning folder {folder_path}: {e}")
        
        logger.info(f"Found {len(xml_files)} XML files in {folder_path}")
        return sorted(xml_files)
    
    @staticmethod
    def extract_zip(zip_path: str, dest_folder: Optional[str] = None) -> List[str]:
        """Giải nén ZIP và trả về danh sách file XML bên trong.
        
        Args:
            zip_path: Đường dẫn file ZIP.
            dest_folder: Thư mục đích. Nếu None, tạo thư mục cùng tên ZIP.
        
        Returns:
            Danh sách đường dẫn các file XML đã giải nén.
        """
        if not os.path.exists(zip_path):
            logger.error(f"ZIP file not found: {zip_path}")
            return []
        
        if dest_folder is None:
            # Tạo folder cùng tên ZIP (bỏ extension)
            base_name = os.path.splitext(os.path.basename(zip_path))[0]
            dest_folder = os.path.join(os.path.dirname(zip_path), base_name)
        
        xml_files = []
        try:
            os.makedirs(dest_folder, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(dest_folder)
            
            # Tìm XML trong folder vừa giải nén
            xml_files = FileHandler.find_xml_files(dest_folder)
            logger.info(f"Extracted {len(xml_files)} XML files from {zip_path}")
            
        except zipfile.BadZipFile:
            logger.error(f"Bad ZIP file: {zip_path}")
        except Exception as e:
            logger.error(f"Error extracting {zip_path}: {e}")
        
        return xml_files
    
    @staticmethod
    def find_all_invoice_files(paths: List[str]) -> Tuple[List[str], List[str]]:
        """Từ list paths (file + folder), tìm tất cả file XML/ZIP.
        
        Args:
            paths: Danh sách đường dẫn (có thể là file hoặc folder).
        
        Returns:
            Tuple (xml_files, zip_files)
        """
        xml_files = []
        zip_files = []
        
        for path in paths:
            if os.path.isdir(path):
                # Là folder → quét
                xml_files.extend(FileHandler.find_xml_files(path))
                # Tìm cả ZIP trong folder
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if os.path.splitext(f)[1].lower() in FileHandler.ZIP_EXTENSIONS:
                            zip_files.append(os.path.join(root, f))
            
            elif os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in FileHandler.XML_EXTENSIONS:
                    xml_files.append(path)
                elif ext in FileHandler.ZIP_EXTENSIONS:
                    zip_files.append(path)
            else:
                logger.warning(f"Path not found: {path}")
        
        return sorted(set(xml_files)), sorted(set(zip_files))
    
    @staticmethod
    def process_input(paths: List[str]) -> List[str]:
        """Xử lý đầu vào: giải nén ZIP + tìm XML → trả về danh sách XML.
        
        Đây là method chính cho chức năng Import offline.
        """
        xml_files, zip_files = FileHandler.find_all_invoice_files(paths)
        
        # Giải nén tất cả ZIP
        for zp in zip_files:
            extracted = FileHandler.extract_zip(zp)
            xml_files.extend(extracted)
        
        # Deduplicate
        xml_files = sorted(set(xml_files))
        logger.info(f"Total XML files to process: {len(xml_files)}")
        return xml_files
    
    @staticmethod
    def ensure_download_folder(base_folder: str, mst: str) -> str:
        """Tạo thư mục tải về cho 1 MST: base_folder/MST/
        
        Returns:
            Đường dẫn thư mục đã tạo.
        """
        folder = os.path.join(base_folder, mst)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """Lấy kích thước file (MB)."""
        try:
            return os.path.getsize(file_path) / (1024 * 1024)
        except Exception:
            return 0.0
