"""
CaptchaSolver — Giải captcha SVG từ cổng thuế.

Cổng thuế gdt.gov.vn trả về captcha dạng SVG (đường path).
Module này nhận diện ký tự bằng cách phân tích path commands (M, Q, Z)
và so khớp với bảng keywords đã biết.

Ported from Reference/captcha_solver.py
"""
import re
from config.logger import get_logger

logger = get_logger(__name__)


class CaptchaSolver:
    """Giải captcha SVG bằng pattern matching trên SVG path commands."""

    def __init__(self):
        self.keywords = self._list_path_all_keywords()
        self.char_map = {}
        for i, kw in enumerate(self.keywords):
            if kw:
                # Map index to character: 0-25 -> A-Z, 26-35 -> 0-9
                if i <= 25:
                    self.char_map[kw] = chr(i + 65)
                else:
                    self.char_map[kw] = str(i - 26)

    def _list_path_all_keywords(self):
        """Bảng keywords cho từng ký tự (A-Z, 0-9).
        
        Mỗi chuỗi là pattern các lệnh SVG (M, Q, Z) đặc trưng của ký tự đó.
        Ký tự rỗng = chưa có mẫu.
        """
        a = "MQQQQQZMQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQZMQQZ"
        b = "MQQQQQQQQQZMQQQQQQZMQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQZMQQQQQQQQZMQQQQQQQQZ"
        c = "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQZ"
        d = "MQQQQQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQZ"
        e = "MQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        f = "MQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZ"
        g = "MQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        h = "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQZ"
        i = ""
        j = "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQZ"
        k = "MQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZ"
        l = ""
        m = "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        n = "MQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQZ"
        o = ""
        p = "MQQQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ"
        q = "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQZ"
        r = "MQQQQQQZMQQQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ"
        s = "MQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        t = "MQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQZ"
        u = ""
        v = "MQQQQQQQQQQZMQQQQQQQQQQQQQQQQZ"
        w = "MQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        x = "MQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZ"
        y = "MQQQQQQQQQZMQQQQQQQQQQQQQZ"
        z = "MQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZ"
        k0 = ""
        k1 = ""
        k2 = "MQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        k3 = "MQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        k4 = "MQQQQZMQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZMQQQQQZ"
        k5 = "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ"
        k6 = "MQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQZ"
        k7 = "MQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQZ"
        k8 = "MQQQQQQQQZMQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQZMQQQQQQQZ"
        k9 = "MQQQQQQQQZMQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQZ"
        return [
            a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z,
            k0, k1, k2, k3, k4, k5, k6, k7, k8, k9,
        ]

    def solve(self, svg_content: str) -> str:
        """Giải captcha từ SVG content string.
        
        Args:
            svg_content: Nội dung SVG (string hoặc bytes sẽ được decode).
            
        Returns:
            Chuỗi captcha đã giải (ví dụ: 'A3KX'), hoặc rỗng nếu không nhận diện được.
        """
        if isinstance(svg_content, bytes):
            svg_content = svg_content.decode("utf-8", errors="replace")
        
        return self.detect_svg_captcha(svg_content)

    def detect_svg_captcha(self, svg_captcha: str) -> str:
        """Nhận diện captcha từ SVG path data.
        
        Phân tích các thẻ <path d="..."> trong SVG,
        trích xuất chuỗi commands (M, Q, Z) và so khớp với bảng keywords.
        Sắp xếp ký tự theo tọa độ X để đúng thứ tự.
        """
        # Tách các path data từ SVG
        p = svg_captcha.split(' d="')
        results = []
        
        for i in range(1, len(p)):
            path_data = p[i].split('"')[0]
            
            # Simplify path to just commands M, Q, Z
            cmds = "".join(re.findall(r'([MQZ])', path_data))
            
            if cmds in self.char_map:
                # Extract the first number after M to get X coordinate for sorting
                m_match = re.search(r'M\s*(\d+(?:\.\d+)?)', path_data)
                x_coord = float(m_match.group(1)) if m_match else 0
                results.append((x_coord, self.char_map[cmds]))
        
        if not results:
            logger.debug(f"CaptchaSolver: No characters recognized from SVG")
            return ""
        
        # Sort by X coordinate (left to right)
        results.sort(key=lambda x: x[0])
        solved = "".join([r[1] for r in results])
        logger.info(f"CaptchaSolver: Solved captcha = '{solved}' ({len(results)} chars)")
        return solved


# Singleton instance — sử dụng lại trong toàn bộ app
_solver_instance = None


def get_captcha_solver() -> CaptchaSolver:
    """Lấy singleton CaptchaSolver instance."""
    global _solver_instance
    if _solver_instance is None:
        _solver_instance = CaptchaSolver()
    return _solver_instance
