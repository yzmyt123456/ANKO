"""验证造水/枯水术、唤起死灵、带斜杠法术。"""

import sqlite3

conn = sqlite3.connect("data/anko.db")
rows = conn.execute(
    "select id, name, level, school from rule_spells "
    "where name like '%造水%' or name like '%唤起死灵%' "
    "or name like '%变巨%' or name like '%目盲%' or name like '%嫌恶%'"
).fetchall()
for r in rows:
    print(r)

row = conn.execute(
    "select description from rule_spells where name = '造水/枯水术'"
).fetchone()
if row:
    print("造水描述含'唤起死灵':", "唤起死灵" in row[0])
    print("造水描述结尾:", row[0][-40:])
conn.close()
