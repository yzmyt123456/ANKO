"""精确调试:完整正则分段拼接。"""

import re
import sys

sys.path.insert(0, ".")
from pathlib import Path

from scripts.import_dnd_rules import _SPELL_RE, extract_pages

PH = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"
pages = extract_pages(Path(PH), 210, 313)
text = "\n".join(pages)
pos = text.find("唤起死灵 Create Undead \n6 环 死灵")

p1 = r"(?m)^[ \t]*([^\n]{2,60}?)[ \t]*\n"
p2 = r"[ \t]*((?:\d+) 环[^\n]*|[\u4e00-\u9fff·]+ 戏法[^\n]*)[ \t]*\n"
p3 = r"施法时间[:：]([^\n]*)\n"
p4 = r"施法距离[:：]([^\n]*)\n"
p5 = r"法术成分[:：]([^\n]*)\n"
p6 = r"持续时间[:：]([^\n]*)"

for name, pat in [
    ("p1", p1),
    ("p1p2", p1 + p2),
    ("p1p2p3", p1 + p2 + p3),
    ("p1p2p3p4", p1 + p2 + p3 + p4),
    ("full", p1 + p2 + p3 + p4 + p5 + p6),
]:
    m = re.match(pat, text[pos:])
    print(f"{name}: {'OK' if m else 'FAIL'}")

starts = [m.start() for m in _SPELL_RE.finditer(text)]
print("匹配数量:", len(starts))
print("34222 附近匹配起点:", [s for s in starts if abs(s - pos) < 500])
