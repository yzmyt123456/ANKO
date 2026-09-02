"""验证法术解析修复:检查马友夫强酸箭等是否独立、描述正确。"""

import sqlite3

conn = sqlite3.connect("data/anko.db")

rows = conn.execute(
    "select name, level, school, casting_time, substr(description, 1, 60) "
    "from rule_spells where name = '马友夫强酸箭'"
).fetchall()
print("马友夫强酸箭:", rows)

rows2 = conn.execute(
    "select name, level, school from rule_spells "
    "where name in ('修复术', '传讯术', '舞光术', '德鲁伊伎俩')"
).fetchall()
print("独立法术:", rows2)

n = conn.execute("select count(*) from rule_spells").fetchone()[0]
print("法术总数:", n)
conn.close()
