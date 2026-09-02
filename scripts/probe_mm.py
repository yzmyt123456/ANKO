"""探查怪物图鉴结构:目录与统计块术语。

用法: python scripts/probe_mm.py
"""

from __future__ import annotations

import re

from pypdf import PdfReader

MM = "D:/bdxiazi/DND 5E 规则包/DND_5E_怪物图鉴CN.pdf"


def main() -> None:
    reader = PdfReader(MM)
    total = len(reader.pages)
    print(f"怪物图鉴 {total} 页")
    print("\n===== 目录(前 4 页) =====")
    for i in range(4):
        text = (reader.pages[i].extract_text() or "").strip()
        print(text[:400])
        print("---")

    print("\n===== 搜索统计块术语 =====")
    for term in ["AC", "Armor Class", "护甲等级", "HP", "挑战等级", "挑战值"]:
        found = 0
        for i in range(5, total):
            text = reader.pages[i].extract_text() or ""
            if term in text:
                idx = text.find(term)
                print(f"  {term} → 第{i+1}页: {text[max(0,idx-60):idx+80]!r}")
                found += 1
                if found >= 2:
                    break
        if not found:
            print(f"  {term} → 未找到")


if __name__ == "__main__":
    main()
