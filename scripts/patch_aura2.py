import sqlite3

content = (
    "第 18 级起，你的防护灵光（6 级）与勇气灵光（10 级）作用范围从 10 尺扩展至 30 尺。\n\n"
    "若所立誓言在 7 级提供了专属灵光，该专属灵光同样扩展至 30 尺：奉献之誓为奉献灵光 Aura of Devotion，古贤之誓为守护灵光 Aura of Warding。\n\n"
    "黑骑（复仇之誓）同样受益：它没有专属灵光，但防护灵光与勇气灵光照常获得 18 级增效。\n\n"
    "各誓约的具体灵光见对应「子职业」卡。"
)
c = sqlite3.connect("data/anko.db")
rid = c.execute("select id from rule_knowledge where parent_id=? and title like '灵光增效%'",
                (c.execute("select id from rule_knowledge where kind='class' and title like '圣武士%'").fetchone()[0],)).fetchone()[0]
c.execute("update rule_knowledge set content=? where id=?", (content, rid))
c.commit()
print(rid)
print(content)
