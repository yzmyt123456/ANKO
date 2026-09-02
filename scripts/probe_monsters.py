"""探查怪物图鉴条目格式。

用法: python scripts/probe_monsters.py
"""

from __future__ import annotations

from pypdf import PdfReader

MM = "D:/bdxiazi/DND 5E 规则包/DND_5E_怪物图鉴CN.pdf"


def main() -> None:
    reader = PdfReader(MM)
    total = len(reader.pages)
    # 找怪物条目:搜"护甲等级"+"生命值"+"速度"
    for i in range(10, total):
        text = reader.pages[i].extract_text() or ""
        if "护甲等级" in text and "生命值" in text:
            print(f"===== 怪物图鉴第 {i+1} 页 =====")
            print(text[:1300])
            break


if __name__ == "__main__":
    main()
