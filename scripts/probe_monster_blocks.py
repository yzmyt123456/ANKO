"""探查怪物统计块页面格式。

用法: python scripts/probe_monster_blocks.py
"""

from __future__ import annotations

from pypdf import PdfReader

MM = "D:/bdxiazi/DND 5E 规则包/DND_5E_怪物图鉴CN.pdf"


def main() -> None:
    reader = PdfReader(MM)
    total = len(reader.pages)
    shown = 0
    for i in range(10, total):
        text = reader.pages[i].extract_text() or ""
        # 统计块特征:同一页有"护甲等级"和"生命值"和"速度:"
        if "护甲等级" in text and "生命值" in text and "速度" in text:
            idx = text.find("护甲等级")
            # 往前找名称/meta 行
            snippet = text[max(0, idx - 300): idx + 400]
            print(f"===== 第 {i+1} 页 =====")
            print(snippet.replace("\t", " "))
            print()
            shown += 1
            if shown >= 2:
                break


if __name__ == "__main__":
    main()
