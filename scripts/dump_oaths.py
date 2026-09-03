import sqlite3

c = sqlite3.connect("data/anko.db")
pid = c.execute("select id from rule_knowledge where kind='class' and title like '圣武士%'").fetchone()[0]
for sid, t in c.execute("select id,title from rule_knowledge where parent_id=? and kind='subclass' order by page,id", (pid,)):
    print(sid, t)
