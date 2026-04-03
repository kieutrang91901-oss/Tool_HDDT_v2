"""
Database Handler — SQLite CRUD cho Tool HDDT v2.

Quản lý:
- accounts: Tài khoản đăng nhập (nhiều MST)
- invoices: Cache hóa đơn đã tải/parse
- column_config: Cấu hình cột do user tự chọn
- field_registry: Auto-discovery — fields mới phát hiện từ TTKhac
- settings: Key-value settings
- remote_config: Version tracking cho auto-update
- license: Schema sẵn cho v2.1

KHÔNG import bất kỳ thư viện UI nào.
"""
import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime

from config.settings import DB_PATH, DATA_DIR
from config.logger import get_logger
from app.models.entities import (
    Account, ColumnConfig, FieldRegistryEntry,
)

logger = get_logger(__name__)


class DBHandler:
    """Quản lý SQLite database cho ứng dụng."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        """Context manager cho SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Tốt hơn cho concurrent read
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Tạo toàn bộ bảng nếu chưa có."""
        with self._get_conn() as conn:
            conn.executescript("""
                -- ═══ TÀI KHOẢN ═══
                CREATE TABLE IF NOT EXISTS accounts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    mst         TEXT NOT NULL UNIQUE,
                    ten_cty     TEXT DEFAULT '',
                    username    TEXT DEFAULT '',
                    is_active   INTEGER DEFAULT 1,
                    created_at  TEXT DEFAULT (datetime('now')),
                    updated_at  TEXT DEFAULT (datetime('now'))
                );
                
                -- ═══ CACHE HÓA ĐƠN ═══
                CREATE TABLE IF NOT EXISTS invoices (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_mst     TEXT NOT NULL,
                    loai            TEXT NOT NULL,
                    ky_hieu         TEXT DEFAULT '',
                    so_hd           TEXT DEFAULT '',
                    ngay_lap        TEXT DEFAULT '',
                    mst_ban         TEXT DEFAULT '',
                    ten_ban         TEXT DEFAULT '',
                    mst_mua         TEXT DEFAULT '',
                    ten_mua         TEXT DEFAULT '',
                    tong_tien       REAL DEFAULT 0,
                    tong_thue       REAL DEFAULT 0,
                    tong_thanh_toan REAL DEFAULT 0,
                    trang_thai      TEXT DEFAULT '',
                    vendor          TEXT DEFAULT 'UNKNOWN',
                    mccqt           TEXT DEFAULT '',
                    fkey            TEXT DEFAULT '',
                    portal_link     TEXT DEFAULT '',
                    xml_path        TEXT DEFAULT '',
                    raw_json        TEXT DEFAULT '',
                    created_at      TEXT DEFAULT (datetime('now')),
                    UNIQUE(account_mst, ky_hieu, so_hd)
                );
                CREATE INDEX IF NOT EXISTS idx_inv_account ON invoices(account_mst);
                CREATE INDEX IF NOT EXISTS idx_inv_ngay ON invoices(ngay_lap);
                CREATE INDEX IF NOT EXISTS idx_inv_loai ON invoices(loai);
                
                -- ═══ CẤU HÌNH CỘT ═══
                CREATE TABLE IF NOT EXISTS column_config (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name  TEXT NOT NULL,
                    column_key  TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    is_visible  INTEGER DEFAULT 1,
                    sort_order  INTEGER DEFAULT 0,
                    width       INTEGER DEFAULT 120,
                    format_type TEXT DEFAULT 'text',
                    is_dynamic  INTEGER DEFAULT 0,
                    scope       TEXT DEFAULT '',
                    UNIQUE(table_name, column_key)
                );
                
                -- ═══ FIELD REGISTRY (Auto-Discovery) ═══
                CREATE TABLE IF NOT EXISTS field_registry (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope       TEXT NOT NULL,
                    field_key   TEXT NOT NULL,
                    display_name TEXT DEFAULT '',
                    format_type TEXT DEFAULT 'text',
                    first_seen  TEXT DEFAULT (datetime('now')),
                    vendor_hint TEXT DEFAULT '',
                    seen_count  INTEGER DEFAULT 1,
                    UNIQUE(scope, field_key)
                );
                
                -- ═══ SETTINGS ═══
                CREATE TABLE IF NOT EXISTS settings (
                    key     TEXT PRIMARY KEY,
                    value   TEXT DEFAULT ''
                );
                
                -- ═══ REMOTE CONFIG ═══
                CREATE TABLE IF NOT EXISTS remote_config (
                    key             TEXT PRIMARY KEY,
                    version         TEXT DEFAULT '1.0.0',
                    data_json       TEXT DEFAULT '{}',
                    last_checked    TEXT DEFAULT (datetime('now')),
                    last_updated    TEXT DEFAULT (datetime('now'))
                );
                
                -- ═══ LICENSE (chuẩn bị cho v2.1) ═══
                CREATE TABLE IF NOT EXISTS license (
                    key             TEXT PRIMARY KEY DEFAULT 'main',
                    license_key     TEXT DEFAULT '',
                    license_type    TEXT DEFAULT 'trial',
                    activated_at    TEXT DEFAULT '',
                    expires_at      TEXT DEFAULT '',
                    machine_id      TEXT DEFAULT ''
                );
            """)
            logger.info(f"Database initialized: {self.db_path}")
    
    # ═══════════════════════════════════════════════════════
    # ACCOUNTS CRUD
    # ═══════════════════════════════════════════════════════
    
    def get_all_accounts(self) -> List[Account]:
        """Lấy tất cả tài khoản."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM accounts ORDER BY is_active DESC, ten_cty ASC"
            ).fetchall()
            return [Account(**dict(r)) for r in rows]
    
    def get_account(self, mst: str) -> Optional[Account]:
        """Lấy tài khoản theo MST."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM accounts WHERE mst = ?", (mst,)
            ).fetchone()
            return Account(**dict(row)) if row else None
    
    def add_account(self, mst: str, ten_cty: str = "", username: str = "") -> bool:
        """Thêm tài khoản mới."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO accounts (mst, ten_cty, username) VALUES (?, ?, ?)",
                    (mst, ten_cty, username or mst)
                )
            logger.info(f"Added account: {mst}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Account already exists: {mst}")
            return False
        except Exception as e:
            logger.error(f"Failed to add account {mst}: {e}")
            return False
    
    def update_account(self, mst: str, **kwargs) -> bool:
        """Cập nhật tài khoản."""
        allowed = {"ten_cty", "username", "is_active"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        try:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [mst]
            with self._get_conn() as conn:
                conn.execute(
                    f"UPDATE accounts SET {set_clause}, updated_at = datetime('now') WHERE mst = ?",
                    values
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update account {mst}: {e}")
            return False
    
    def delete_account(self, mst: str) -> bool:
        """Xóa tài khoản."""
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM accounts WHERE mst = ?", (mst,))
            logger.info(f"Deleted account: {mst}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete account {mst}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════
    # INVOICES CRUD
    # ═══════════════════════════════════════════════════════
    
    def upsert_invoice(self, data: Dict[str, Any]) -> bool:
        """Thêm hoặc cập nhật hóa đơn (theo account_mst + ky_hieu + so_hd)."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO invoices 
                        (account_mst, loai, ky_hieu, so_hd, ngay_lap,
                         mst_ban, ten_ban, mst_mua, ten_mua,
                         tong_tien, tong_thue, tong_thanh_toan,
                         trang_thai, vendor, mccqt, fkey, portal_link,
                         xml_path, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_mst, ky_hieu, so_hd)
                    DO UPDATE SET
                        ngay_lap=excluded.ngay_lap,
                        mst_ban=excluded.mst_ban, ten_ban=excluded.ten_ban,
                        mst_mua=excluded.mst_mua, ten_mua=excluded.ten_mua,
                        tong_tien=excluded.tong_tien, tong_thue=excluded.tong_thue,
                        tong_thanh_toan=excluded.tong_thanh_toan,
                        trang_thai=excluded.trang_thai, vendor=excluded.vendor,
                        mccqt=excluded.mccqt, fkey=excluded.fkey,
                        portal_link=excluded.portal_link,
                        xml_path=excluded.xml_path, raw_json=excluded.raw_json
                """, (
                    data.get("account_mst", ""), data.get("loai", ""),
                    data.get("ky_hieu", ""), data.get("so_hd", ""),
                    data.get("ngay_lap", ""),
                    data.get("mst_ban", ""), data.get("ten_ban", ""),
                    data.get("mst_mua", ""), data.get("ten_mua", ""),
                    data.get("tong_tien", 0), data.get("tong_thue", 0),
                    data.get("tong_thanh_toan", 0),
                    data.get("trang_thai", ""), data.get("vendor", "UNKNOWN"),
                    data.get("mccqt", ""), data.get("fkey", ""),
                    data.get("portal_link", ""),
                    data.get("xml_path", ""), data.get("raw_json", ""),
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to upsert invoice: {e}")
            return False
    
    def get_invoices(
        self,
        account_mst: str = "",
        loai: str = "",
        tu_ngay: str = "",
        den_ngay: str = "",
        search: str = "",
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict]:
        """Truy vấn danh sách hóa đơn đã cache."""
        conditions = []
        params = []
        
        if account_mst:
            conditions.append("account_mst = ?")
            params.append(account_mst)
        if loai:
            conditions.append("loai = ?")
            params.append(loai)
        if tu_ngay:
            conditions.append("ngay_lap >= ?")
            params.append(tu_ngay)
        if den_ngay:
            conditions.append("ngay_lap <= ?")
            params.append(den_ngay)
        if search:
            conditions.append(
                "(ten_ban LIKE ? OR mst_ban LIKE ? OR so_hd LIKE ? OR ky_hieu LIKE ?)"
            )
            s = f"%{search}%"
            params.extend([s, s, s, s])
        
        where = " AND ".join(conditions) if conditions else "1=1"
        
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM invoices WHERE {where} ORDER BY ngay_lap DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            return [dict(r) for r in rows]
    
    def count_invoices(self, account_mst: str = "", loai: str = "") -> int:
        """Đếm tổng số hóa đơn."""
        conditions = []
        params = []
        if account_mst:
            conditions.append("account_mst = ?")
            params.append(account_mst)
        if loai:
            conditions.append("loai = ?")
            params.append(loai)
        where = " AND ".join(conditions) if conditions else "1=1"
        
        with self._get_conn() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM invoices WHERE {where}", params
            ).fetchone()
            return row["cnt"] if row else 0
    
    # ═══════════════════════════════════════════════════════
    # COLUMN CONFIG
    # ═══════════════════════════════════════════════════════
    
    def get_columns(self, table_name: str, visible_only: bool = False) -> List[ColumnConfig]:
        """Lấy cấu hình cột cho bảng."""
        condition = "AND is_visible = 1" if visible_only else ""
        with self._get_conn() as conn:
            rows = conn.execute(
                f"""SELECT * FROM column_config 
                    WHERE table_name = ? {condition}
                    ORDER BY sort_order ASC""",
                (table_name,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d.pop("id", None)  # ColumnConfig không có field 'id'
                result.append(ColumnConfig(**d))
            return result
    
    def upsert_column(self, col: ColumnConfig) -> bool:
        """Thêm/cập nhật cấu hình 1 cột."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO column_config 
                        (table_name, column_key, display_name, is_visible, sort_order, 
                         width, format_type, is_dynamic, scope)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(table_name, column_key)
                    DO UPDATE SET
                        display_name=excluded.display_name,
                        is_visible=excluded.is_visible,
                        sort_order=excluded.sort_order,
                        width=excluded.width,
                        format_type=excluded.format_type,
                        is_dynamic=excluded.is_dynamic,
                        scope=excluded.scope
                """, (
                    col.table_name, col.column_key, col.display_name,
                    int(col.is_visible), col.sort_order, col.width,
                    col.format_type, int(col.is_dynamic), col.scope,
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to upsert column {col.column_key}: {e}")
            return False
    
    def update_column_visibility(self, table_name: str, column_key: str, visible: bool) -> bool:
        """Bật/tắt hiển thị 1 cột."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE column_config SET is_visible = ? WHERE table_name = ? AND column_key = ?",
                    (int(visible), table_name, column_key)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update column visibility: {e}")
            return False
    
    def update_column_order(self, table_name: str, ordered_keys: List[str]) -> bool:
        """Cập nhật thứ tự cột."""
        try:
            with self._get_conn() as conn:
                for i, key in enumerate(ordered_keys):
                    conn.execute(
                        "UPDATE column_config SET sort_order = ? WHERE table_name = ? AND column_key = ?",
                        (i, table_name, key)
                    )
            return True
        except Exception as e:
            logger.error(f"Failed to update column order: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════
    # FIELD REGISTRY (Auto-Discovery)
    # ═══════════════════════════════════════════════════════
    
    def register_field(self, scope: str, field_key: str, vendor_hint: str = "") -> bool:
        """Đăng ký field mới phát hiện (hoặc tăng seen_count nếu đã có).
        
        Gọi bởi XML Parser mỗi khi gặp TTKhac key.
        """
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO field_registry (scope, field_key, display_name, vendor_hint)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(scope, field_key)
                    DO UPDATE SET 
                        seen_count = seen_count + 1,
                        vendor_hint = CASE 
                            WHEN vendor_hint = '' THEN excluded.vendor_hint
                            WHEN vendor_hint NOT LIKE '%' || excluded.vendor_hint || '%' 
                                THEN vendor_hint || ',' || excluded.vendor_hint
                            ELSE vendor_hint
                        END
                """, (scope, field_key, field_key, vendor_hint))
            return True
        except Exception as e:
            logger.error(f"Failed to register field {scope}.{field_key}: {e}")
            return False
    
    def register_fields_batch(self, fields: List[Dict[str, str]]) -> int:
        """Đăng ký nhiều fields cùng lúc (hiệu quả hơn khi parse batch).
        
        Args:
            fields: List of {"scope": "...", "field_key": "...", "vendor_hint": "..."}
        
        Returns:
            Số fields đã đăng ký thành công.
        """
        count = 0
        try:
            with self._get_conn() as conn:
                for f in fields:
                    conn.execute("""
                        INSERT INTO field_registry (scope, field_key, display_name, vendor_hint)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(scope, field_key)
                        DO UPDATE SET 
                            seen_count = seen_count + 1,
                            vendor_hint = CASE 
                                WHEN vendor_hint = '' THEN excluded.vendor_hint
                                WHEN vendor_hint NOT LIKE '%' || excluded.vendor_hint || '%' 
                                    THEN vendor_hint || ',' || excluded.vendor_hint
                                ELSE vendor_hint
                            END
                    """, (
                        f["scope"], f["field_key"], 
                        f.get("display_name", f["field_key"]),
                        f.get("vendor_hint", ""),
                    ))
                    count += 1
        except Exception as e:
            logger.error(f"Failed to register batch fields: {e}")
        return count
    
    def get_discovered_fields(self, scope: str = "") -> List[FieldRegistryEntry]:
        """Lấy danh sách fields đã phát hiện."""
        condition = "WHERE scope = ?" if scope else ""
        params = [scope] if scope else []
        
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM field_registry {condition} ORDER BY scope, seen_count DESC",
                params
            ).fetchall()
            return [FieldRegistryEntry(**dict(r)) for r in rows]
    
    # ═══════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════
    
    def get_setting(self, key: str, default: str = "") -> str:
        """Lấy giá trị setting."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default
    
    def set_setting(self, key: str, value: str) -> bool:
        """Lưu setting."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════
    # REMOTE CONFIG
    # ═══════════════════════════════════════════════════════
    
    def get_remote_config(self, key: str = "api_config") -> Optional[Dict]:
        """Lấy remote config đã cache."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM remote_config WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return {
                    "version": row["version"],
                    "data": json.loads(row["data_json"]),
                    "last_checked": row["last_checked"],
                    "last_updated": row["last_updated"],
                }
            return None
    
    def save_remote_config(self, key: str, version: str, data: dict) -> bool:
        """Lưu remote config mới."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO remote_config (key, version, data_json, last_checked, last_updated)
                    VALUES (?, ?, ?, datetime('now'), datetime('now'))
                    ON CONFLICT(key) DO UPDATE SET
                        version=excluded.version,
                        data_json=excluded.data_json,
                        last_checked=datetime('now'),
                        last_updated=datetime('now')
                """, (key, version, json.dumps(data, ensure_ascii=False)))
            return True
        except Exception as e:
            logger.error(f"Failed to save remote config: {e}")
            return False
    
    def update_remote_check_time(self, key: str = "api_config") -> bool:
        """Cập nhật thời gian kiểm tra remote config (không có update)."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE remote_config SET last_checked = datetime('now') WHERE key = ?",
                    (key,)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update check time: {e}")
            return False
