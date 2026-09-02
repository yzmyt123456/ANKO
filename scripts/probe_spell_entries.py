"""探查玩家手册法术描述条目的文本格式。

用法: python scripts/probe_spell_entries.py
"""

from __future__ import annotations

from pypdf import PdfReader

PH = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"


def main() -> None:
    reader = PdfReader(PH)
    # 法术描述通常在 211 页之后;搜"施法时间:1 动作"格式
    found_pages = []
    for i in range(210, 260):
        text = reader.pages[i].extract_text() or ""
        if "施法时间" in text and "法术成分" in text and len(found_pages) < 3:
            found_pages.append(i)
    for i in found_pages[:2]:
        text = (reader.pages[i].extract_text() or "").strip()
        print(f"===== 第 {i+1} 页 =====")
        print(text[:1500])
        print()


if __name__ == "__main__":
    main()
