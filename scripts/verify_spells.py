"""查看成分格式样例。"""

import sqlite3

conn = sqlite3.connect("data/anko.db")
rows = conn.execute(
    "select name, components, description from rule_spells "
    "where components is not null limit 10"
).fetchall()
for r in rows:
    print(r[0], "|", r[1], "| 换行:", r[2].count("\n"))
conn.close()
