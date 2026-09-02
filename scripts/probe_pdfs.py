"""探测 DND 5E 规则包 PDF 的可提取性。

用法: python scripts/probe_pdfs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader

RULES_DIR = Path("D:/bdxiazi/DND 5E 规则包")
TARGETS = [
    "DnD_5E_新手套组_基础入门规则CN.pdf",
    "DnD_5E_新手套组_新手预设角色CN.pdf",
    "人物卡汉化版.pdf",
    "DND_5E_玩家手册CN.pdf",
]


def probe(path: Path, pages: int = 3) -> None:
    try:
        reader = PdfReader(str(path))
        total = len(reader.pages)
        sample = ""
        for i in range(min(pages, total)):
            sample += (reader.pages[i].extract_text() or "") + "\n"
        has_text = len(sample.strip()) > 30
        print(f"[{path.name}]")
        print(f"  页数: {total} | 文本层: {'✓ 可提取' if has_text else '✗ 扫描版/无文本'}")
        if has_text:
            print(f"  样例: {sample.strip()[:120]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"[{path.name}] 读取失败: {exc}")


def main() -> None:
    for name in TARGETS:
        p = RULES_DIR / name
        if p.exists():
            probe(p)
        else:
            print(f"[{name}] 不存在")
        print()


if __name__ == "__main__":
    main()
