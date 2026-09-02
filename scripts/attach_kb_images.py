"""把 data/kb_images 下的插图挂到对应种族/职业知识卡。

文件名规范:以 中文名 或 英文名 开头即可关联,
例如: 矮人_1.png / Dwarf.png / 野蛮人_Barbarian.png
用法: python scripts/attach_kb_images.py
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from anko.models import Base
from anko.models.rules import RuleKnowledge

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "kb_images"
DST = ROOT / "anko" / "static" / "img" / "kb"

ALIASES = {
    "矮人": ["矮人", "dwarf"],
    "精灵": ["精灵", "elf"],
    "半身人": ["半身人", "halfling"],
    "人类": ["人类", "human"],
    "龙裔": ["龙裔", "dragonborn"],
    "侏儒": ["侏儒", "gnome"],
    "半精灵": ["半精灵", "half-elf"],
    "半兽人": ["半兽人", "half-orc"],
    "提夫林": ["提夫林", "tiefling"],
    "野蛮人": ["野蛮人", "barbarian"],
    "吟游诗人": ["吟游诗人", "bard"],
    "牧师": ["牧师", "cleric"],
    "德鲁伊": ["德鲁伊", "druid"],
    "战士": ["战士", "fighter"],
    "武僧": ["武僧", "monk"],
    "圣武士": ["圣武士", "paladin"],
    "游侠": ["游侠", "ranger"],
    "游荡者": ["游荡者", "rogue"],
    "术士": ["术士", "sorcerer"],
    "邪术师": ["邪术师", "warlock"],
    "法师": ["法师", "wizard"],
}


def main() -> None:
    if not SRC.is_dir():
        print(f"请先把图片放入 {SRC}(支持 png/jpg/webp)")
        return
    DST.mkdir(parents=True, exist_ok=True)
    engine = create_engine("sqlite:///./data/anko.db", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    files = sorted(list(SRC.glob("*.png")) + list(SRC.glob("*.jpg"))
                   + list(SRC.glob("*.jpeg")) + list(SRC.glob("*.webp")))
    if not files:
        print(f"{SRC} 里没有图片")
        return

    done = []
    with Session() as s:
        for f in files:
            low = f.stem.lower()
            hit = None
            for name, aliases in ALIASES.items():
                if any(a in low for a in aliases):
                    hit = name
                    break
            if hit is None:
                print(f"跳过(无法匹配条目): {f.name}")
                continue
            # 目标可能同时命中 race/class(如 无);排除冲突:矮人等在种族
            kind = "race" if hit in ALIASES and hit in (
                "矮人", "精灵", "半身人", "人类", "龙裔", "侏儒", "半精灵", "半兽人", "提夫林"
            ) else "class"
            if kind == "class" and hit not in (
                "野蛮人", "吟游诗人", "牧师", "德鲁伊", "战士", "武僧", "圣武士",
                "游侠", "游荡者", "术士", "邪术师", "法师"
            ):
                print(f"跳过(无该职业): {f.name}")
                continue
            ext = f.suffix.lower().lstrip(".")
            out = DST / f"kb_{hit}_{f.stem}.{ext}"
            shutil.copy2(f, out)
            url = f"/static/img/kb/{out.name}"
            rows = s.query(RuleKnowledge).filter(
                RuleKnowledge.kind == kind, RuleKnowledge.title.like(f"{hit} %")
            ).all()
            if not rows:
                print(f"跳过(库中无 {hit} {kind} 条目): {f.name}")
                continue
            rows[0].image = url
            done.append((hit, kind, url))
        s.commit()
    for name, kind, url in done:
        print(f"挂载: {name}({kind}) -> {url}")
    print(f"共 {len(done)} 张。刷新网页后在种族/职业详情查看。")


if __name__ == "__main__":
    main()
