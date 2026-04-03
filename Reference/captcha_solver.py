import re

class CaptchaSolver:
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
        # Ported from modDetectCaptcha.bas
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
        return [a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z, 
                k0, k1, k2, k3, k4, k5, k6, k7, k8, k9]

    def detect_svg_captcha(self, svg_captcha):
        # re.Pattern = "([MQZ])([^MQZ]*)"
        p = svg_captcha.split(' d="')
        results = []
        for i in range(1, len(p)):
            path_data = p[i].split('"')[0]
            # Simplify path to just commands MQZ
            cmds = "".join(re.findall(r'([MQZ])', path_data))
            
            if cmds in self.char_map:
                # Extract the first number after M to get X coordinate for sorting
                m_match = re.search(r'M\s*(\d+(?:\.\d+)?)', path_data)
                x_coord = float(m_match.group(1)) if m_match else 0
                results.append((x_coord, self.char_map[cmds]))
        
        if not results:
            return ""
        
        # Sort by X coordinate
        results.sort(key=lambda x: x[0])
        return "".join([r[1] for r in results])

if __name__ == "__main__":
    # Test with a snippet if available
    pass
