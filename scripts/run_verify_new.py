import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
import sqlite3

from scripts.import_dnd_rules import import_rules
from scripts import render_class_tables
import scripts.add_adventuring_gear  # noqa: F401

import_rules(Path("D:/bdxiazi/DND 5E 规则包"))
render_class_tables.main()

conn = sqlite3.connect("data/anko.db")
lines = []
for zh in ("吟游诗人", "术士", "邪术师", "圣武士", "法师", "游侠"):
    pid = conn.execute(
        "select id from rule_knowledge where kind='class' and title like ?", (zh + "%",)
    ).fetchone()[0]
    r = json.loads(conn.execute(
        "select content from rule_knowledge where parent_id=? and kind='class_levels'",
        (pid,),
    ).fetchone()[0])
    r4 = next(x for x in r if x["lv"] == 4)
    r20 = next(x for x in r if x["lv"] == 20)
    has_img = conn.execute(
        "select image from rule_knowledge where parent_id=? and kind='class_levels'", (pid,)
    ).fetchone()[0]
    lines.append(f"{zh} lv4: {json.dumps(r4, ensure_ascii=False)[:160]}")
    lines.append(f"{zh} lv20: {json.dumps(r20, ensure_ascii=False)[:160]}")
    lines.append(f"{zh} image: {has_img}")
for zh in ("奥法骑士", "诡术师"):
    sid = conn.execute(
        "select id from rule_knowledge where kind='subclass' and title like ?", (zh + "%",)
    ).fetchone()[0]
    kids = conn.execute(
        "select title,image,content from rule_knowledge where parent_id=? and kind='class_levels'",
        (sid,),
    ).fetchall()
    for title, img, content in kids:
        rows = json.loads(content)
        lines.append(f"[子职 {zh}] {title} rows={len(rows)} img={img}")
        lines.append("  3级: " + json.dumps(rows[0], ensure_ascii=False)[:140])
        lines.append("  20级: " + json.dumps(rows[-1], ensure_ascii=False)[:140])
conn.close()
Path("data/verify_new.txt").write_text("\n".join(lines), encoding="utf-8")
print("done", len(lines))
