"""探查法术章节与怪物图鉴的文本格式。

用法: python scripts/probe_formats.py
"""

from __future__ import annotations

from pypdf import PdfReader

PH = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"
MM = "D:/bdxiazi/DND 5E 规则包/DND_5E_怪物图鉴CN.pdf"


def main() -> None:
    # 1. 玩家手册:定位法术章节起始页
    reader = PdfReader(PH)
    total = len(reader.pages)
    print(f"玩家手册 {total} 页,定位法术章节:")
    found = None
    for i in range(200, total):
        text = reader.pages[i].extract_text() or ""
        if "第 11 章" in text and "法术" in text and found is None:
            found = i
            print(f"  第 11 章出现于第 {i+1} 页")
            break
    if found:
        # 打印法术章节开头 3 页
        for i in range(found, min(found + 3, total)):
            text = (reader.pages[i].extract_text() or "").strip()
            print(f"\n===== 第 {i+1} 页 =====")
            print(text[:800])

    # 2. 怪物图鉴:格式探查
    print("\n\n########## 怪物图鉴 ##########")
    mm = PdfReader(MM)
    mt = len(mm.pages)
    print(f"怪物图鉴 {mt} 页")
    # 找一个怪物页面样本(搜"成年红龙"或看目录后页)
    for i in range(5, min(40, mt)):
        text = mm.pages[i].extract_text() or ""
        if "龙" in text and ("AC" in text or "护甲" in text):
            print(f"\n===== 怪物图鉴第 {i+1} 页 =====")
            print(text[:900])
            break


if __name__ == "__main__":
    main()
