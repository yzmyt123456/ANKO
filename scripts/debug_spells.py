"""调试:检查 parse_spells 能否匹配"修复术"等戏法格式。"""

import re
import sys

sys.path.insert(0, ".")
from pathlib import Path

from pypdf import PdfReader

from scripts.import_dnd_rules import _SPELL_RE, _NAME_RE, extract_pages

PH = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"
pages = extract_pages(Path(PH), 210, 313)
text = "\n".join(pages)

# 找"修复术"附近的原始文本
idx = text.find("修复术")
print("修复术附近原始文本:")
print(repr(text[idx - 10:idx + 200]))
print()

# 测试正则是否能匹配修复术
for m in _SPELL_RE.finditer(text):
    name_line = m.group(1).strip()
    if "修复术" in name_line:
        print("匹配到修复术!环阶行:", m.group(2).strip())
        break
else:
    print("正则未匹配到修复术!")

# 统计匹配到的法术数量
matches = list(_SPELL_RE.finditer(text))
print("正则匹配法术数:", len(matches))

# 检查舞光术(Dancing Lights)
for m in _SPELL_RE.finditer(text):
    if "舞光术" in m.group(1):
        print("舞光术匹配,环阶行:", m.group(2).strip())
        break
else:
    print("舞光术未匹配!")
