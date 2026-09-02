"""探查法术条目第二行的所有格式变体。

用法: python scripts/probe_spell_formats.py
"""

from __future__ import annotations

import re
from collections import Counter

from pypdf import PdfReader

PH = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"


def main() -> None:
    reader = PdfReader(PH)
    pages = []
    for i in range(210, 313):
        pages.append(reader.pages[i].extract_text() or "")
    text = "\n".join(pages)

    # 找所有"施法时间"行,取前一行的环阶行
    pattern = re.compile(
        r"(?m)^[ \t]*([^\n]{2,60}?)[ \t]*\n"
        r"[ \t]*([^\n]{1,40})[ \t]*\n"
        r"施法时间[:：]"
    )
    counter = Counter()
    samples = {}
    for m in pattern.finditer(text):
        line2 = m.group(2).strip()
        counter[line2] += 1
        if line2 not in samples:
            samples[line2] = m.group(1).strip()[:20]
    print(f"环阶行格式种类: {len(counter)}")
    for line2, cnt in counter.most_common(15):
        print(f"  {line2!r} x{cnt}  (例:{samples[line2]})")


if __name__ == "__main__":
    main()
