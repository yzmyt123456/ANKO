"""探查玩家手册 PDF 的内容结构(目录/法术章节)。

用法: python scripts/probe_ph.py
"""

from __future__ import annotations

from pypdf import PdfReader

PH = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"


def main() -> None:
    reader = PdfReader(PH)
    total = len(reader.pages)
    print(f"玩家手册共 {total} 页")

    # 目录页(前 6 页)
    print("\n===== 目录(前 2 页) =====")
    for i in range(2):
        text = (reader.pages[i].extract_text() or "").strip()
        print(text[:600])

    # 找法术章节:逐页搜索"法术"关键词
    print("\n===== 搜索法术章节 =====")
    spell_pages = []
    for i in range(10, total):
        text = reader.pages[i].extract_text() or ""
        if "法术列表" in text and len(spell_pages) < 3:
            spell_pages.append((i + 1, text[:200]))
        if "第 11 章" in text and len(spell_pages) < 5:
            spell_pages.append((i + 1, text[:200]))
    for pg, sample in spell_pages:
        print(f"第{pg}页: {sample!r}")

    # 样本:抽 30 页看文本质量
    print("\n===== 文本质量抽检 =====")
    import random

    random.seed(42)
    for i in random.sample(range(0, total), 3):
        text = (reader.pages[i].extract_text() or "").strip()
        print(f"第{i+1}页({len(text)}字): {text[:150]!r}")


if __name__ == "__main__":
    main()
