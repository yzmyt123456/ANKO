"""为 12 个职业从玩家手册裁剪"职业等级表"原图,并挂到各职业等级表卡。"""

import re
import sys

sys.path.insert(0, ".")
from pathlib import Path

import pymupdf
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from anko.models import Base
from anko.models.rules import RuleKnowledge

PDF = Path("D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf")
DST = Path(__file__).resolve().parent.parent / "anko" / "static" / "img" / "kb"
GRADE = re.compile(r"^\d+(st|nd|rd|th)$")

ZH_EN = {
    "野蛮人": "barbarian", "吟游诗人": "bard", "牧师": "cleric", "德鲁伊": "druid",
    "战士": "fighter", "武僧": "monk", "圣武士": "paladin", "游侠": "ranger",
    "游荡者": "rogue", "术士": "sorcerer", "邪术师": "warlock", "法师": "wizard",
}


def _green_bbox(page):
    """淡绿条纹矩形联合框(表格精确边界)。返回 Rect 或 None。"""
    rects = []
    for d in page.get_drawings():
        fill = d.get("fill")
        if fill is None:
            continue
        r, g, b = fill
        if g > 0.6 and r < g and b < g and abs(r - b) < 0.2:
            rects.append(d["rect"])
    if len(rects) < 10:
        return None
    x0 = min(r.x0 for r in rects)
    x1 = max(r.x1 for r in rects)
    y0 = min(r.y0 for r in rects)
    y1 = max(r.y1 for r in rects)
    return pymupdf.Rect(x0, y0, x1, y1)


def find_and_crop(doc, pno0, en):
    for pno in range(pno0, min(pno0 + 7, len(doc))):
        page = doc[pno]
        words = page.get_text("words")
        rows = {}
        for w in words:
            rows.setdefault(round(w[1]), []).append(w)
        grade_rows = [
            (y, ws) for y, ws in rows.items()
            if any(GRADE.match(w[4]) for w in ws)
        ]
        if len(grade_rows) < 12:
            continue
        ys = sorted({y for y, _ in grade_rows})
        y_min_lv, y_max_lv = ys[0], ys[-1]
        gbox = _green_bbox(page)

        # 左右边界以淡绿条纹为准(宽度结束=表结束),否则退回等级行文字范围
        if gbox is not None:
            x0 = gbox.x0 - 2
            x1 = min(gbox.x1 + 2, page.rect.width)
        else:
            x0 = min(min(w[0] for w in ws) for _, ws in grade_rows) - 4
            x1 = max(max(w[2] for w in ws) for _, ws in grade_rows) + 6

        # 上界:表标题"XX职业表"整行完整(不腰斩、不带上文),标题缺失则用列头/绿区
        title_y = None
        for y, ws in sorted(rows.items()):
            if y >= y_min_lv:
                break
            joined = "".join(w[4] for w in ws)
            if "职业表" in joined:
                title_y = y
                break
        if title_y is not None:
            y_top = title_y - 4
        elif gbox is not None and gbox.y0 < y_min_lv - 2:
            y_top = gbox.y0 - 4
        else:
            y_top = y_min_lv - 34

        # 下界:等级末行兜底;若绿区底更低则取其(包含表尾线)
        y_bot = y_max_lv + 12
        if gbox is not None and gbox.y1 > y_bot - 4:
            y_bot = gbox.y1 + 2

        clip = pymupdf.Rect(x0, y_top, min(x1, page.rect.width), y_bot)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2.2, 2.2), clip=clip, alpha=False)
        out = DST / f"class_{en}_table.png"
        pix.save(str(out))
        return pno, f"/static/img/kb/{out.name}"
    return None, None


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    engine = create_engine("sqlite:///./data/anko.db", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    doc = pymupdf.open(str(PDF))
    done = []
    with Session() as s:
        classes = s.query(RuleKnowledge).filter(
            RuleKnowledge.kind == "class", RuleKnowledge.category == "职业"
        ).all()
        for cls in sorted(classes, key=lambda x: x.page):
            zh = (cls.title or "").split(" ")[0]
            en = ZH_EN.get(zh)
            if not en:
                print(f"跳过(无英文名): {zh}")
                continue
            pno, url = find_and_crop(doc, cls.page - 1, en)
            if not pno:
                print(f"跳过(未找到等级表): {zh}")
                continue
            level_child = s.query(RuleKnowledge).filter(
                RuleKnowledge.parent_id == cls.id, RuleKnowledge.kind == "class_levels"
            ).first()
            if level_child:
                level_child.image = url
                done.append((zh, pno, url))
        # 子职独立施法表(奥法骑士/诡术师 3-20 级) → 挂其"施法资源表"卡
        for zh, en in (("奥法骑士", "fighter_ek"), ("诡术师", "rogue_at")):
            subs = s.query(RuleKnowledge).filter(
                RuleKnowledge.kind == "subclass", RuleKnowledge.title.like(zh + "%")
            ).all()
            for sub in subs:
                pno, url = find_and_crop(doc, sub.page - 1, en)
                if not pno:
                    continue
                cast_child = s.query(RuleKnowledge).filter(
                    RuleKnowledge.parent_id == sub.id,
                    RuleKnowledge.kind == "class_levels",
                    RuleKnowledge.title.like("施法资源表%"),
                ).first()
                if cast_child:
                    cast_child.image = url
                    done.append((f"{sub.title.split(' ')[0]}(子职施法表)", pno, url))
        s.commit()
    doc.close()
    for zh, pno, url in done:
        print(f"挂载: {zh} (表页 {pno}) -> {url}")
    print(f"共 {len(done)} 张。")


if __name__ == "__main__":
    main()
