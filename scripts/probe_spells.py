"""探查玩家手册法术条目格式。

用法: python scripts/probe_spells.py
"""

from __future__ import annotations

from pypdf import PdfReader

PH = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"


def main() -> None:
    reader = PdfReader(PH)
    # 法术列表通常在 208-210 页附近;扫 205~235 找法术条目样本
    for i in range(205, 240):
        text = reader.pages[i].extract_text() or ""
        if "燃烧之手" in text or "火球术" in text or "魔法飞弹" in text:
            print(f"===== 第 {i+1} 页 =====")
            print(text[:1200])
            print()
            if "火球术" in text:
                break


if __name__ == "__main__":
    main()
