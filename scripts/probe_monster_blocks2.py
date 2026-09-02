"""更精确探查怪物统计块。

用法: python scripts/probe_monster_blocks2.py
"""

from __future__ import annotations

import re

from pypdf import PdfReader

MM = "D:/bdxiazi/DND 5E 规则包/DND_5E_怪物图鉴CN.pdf"


def main() -> None:
    reader = PdfReader(MM)
    total = len(reader.pages)
    shown = 0
    # 统计块特征:护甲等级: 后跟数字
    pat = re.compile(r"护甲等级[:：]\s*\d")
    for i in range(10, total):
        text = reader.pages[i].extract_text() or ""
        if pat.search(text):
            m = pat.search(text)
            idx = m.start()
            snippet = text[max(0, idx - 400): idx + 500].replace("\t", " ")
            print(f"===== 第 {i+1} 页 =====")
            print(snippet)
            print()
            shown += 1
            if shown >= 3:
                break


if __name__ == "__main__":
    main()
