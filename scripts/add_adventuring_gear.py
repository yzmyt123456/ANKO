"""补充条目:冒险用品表(物品与价格)。重导后可一键恢复。

用法: python scripts/add_adventuring_gear.py
"""
import sys

sys.path.insert(0, ".")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from anko.models import Base
from anko.models.rules import RuleKnowledge

ITEMS = [
    "沙漏 Hourglass · 25 gp", "墨水 Ink(1 盎司瓶)· 10 gp", "墨水笔 Ink pen · 2 cp",
    "牛眼提灯 Lantern, bullseye · 10 gp", "附盖提灯 Lantern, hooded · 5 gp",
    "锁 Lock · 10 gp", "石匠工具 Mason's tools · 10 gp", "野炊用具 Mess kit · 2 sp",
    "钢面镜 Mirror, steel · 5 gp", "灯油 Oil(瓶 flask)· 1 sp",
    "纸 Paper(每张)· 2 sp", "羊皮纸 Parchment(每张)· 1 sp",
    "香水 Perfume(小瓶 vial)· 5 gp", "矿工镐 Pick, miner's · 2 gp",
    "岩钉 Piton · 5 cp", "铁锅 Pot, iron · 2 gp",
    "治疗药水 Potion of healing · 50 gp", "扑克牌 Playing cards · 5 sp",
    "小包 Pouch · 5 sp", "口粮 Rations(1 日份)· 5 sp",
    "长袍 Robes · 1 gp", "麻绳 Rope, hempen(50 尺)· 1 gp",
    "丝质绳索 Rope, silk(50 尺)· 10 gp", "麻袋 Sack · 1 cp",
    "封蜡 Sealing wax · 5 sp", "铲子 Shovel · 2 gp",
    "哨子 Signal whistle · 5 cp", "图章戒指 Signet ring · 5 gp",
    "法术书 Spellbook · 50 gp", "长铁钉 Spikes, iron(10 根)· 1 gp",
    "双人帐篷 Tent, two-person · 2 gp", "盗贼工具 Thieves' tools · 25 gp",
    "火绒匣 Tinderbox · 5 sp", "火把 Torch · 1 cp",
    "水袋 Waterskin · 2 sp", "磨刀石 Whetstone · 1 cp",
]
content = "\n".join("- " + i for i in ITEMS)
content += "\n\n(依据玩家手册『冒险用品表 Adventuring Gear』整理;物品重量/属性详见原书表。)"

engine = create_engine("sqlite:///./data/anko.db", future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, expire_on_commit=False)
with Session() as s:
    old = s.query(RuleKnowledge).filter(
        RuleKnowledge.title.like("冒险用品表(物品与价格)%")
    ).first()
    if old is None:
        s.add(
            RuleKnowledge(
                book="DND_5E_玩家手册CN", page=150,
                title="冒险用品表(物品与价格) Adventuring Gear",
                category="装备", content=content,
            )
        )
        s.commit()
        print("已新增冒险用品条目")
    else:
        print("冒险用品条目已存在,跳过")
