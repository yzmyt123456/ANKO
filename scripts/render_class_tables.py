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


def find_and_crop(doc, pno0, zh):
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
        y0, y1 = ys[0] - 6, ys[-1] + 8
        x0 = min(min(w[0] for w in ws) for _, ws in grade_rows) - 4
        x1 = max(max(w[2] for w in ws) for _, ws in grade_rows) + 6
        clip = pymupdf.Rect(x0, y0, min(x1, page.rect.width), y1)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2.2, 2.2), clip=clip, alpha=False)
        out = DST / f"class_{zh}_table.png"
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
            pno, url = find_and_crop(doc, cls.page - 1, zh)
            if not pno:
                print(f"跳过(未找到等级表): {zh}")
                continue
            level_child = s.query(RuleKnowledge).filter(
                RuleKnowledge.parent_id == cls.id, RuleKnowledge.kind == "class_levels"
            ).first()
            if level_child:
                level_child.image = url
                done.append((zh, pno, url))
        s.commit()
    doc.close()
    for zh, pno, url in done:
        print(f"挂载: {zh} (表页 {pno}) -> {url}")
    print(f"共 {len(done)} / {len(classes)} 个职业。")


if __name__ == "__main__":
    main()
