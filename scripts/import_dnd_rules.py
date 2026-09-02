"""从 DND 5E 规则包 PDF 导入数据到本地数据库。

导入内容:
- 玩家手册全文 → rule_knowledge(按页切块)
- 玩家手册法术章节 → rule_spells
- 怪物图鉴 → rule_monsters

用法:
  python scripts/import_dnd_rules.py [--pdf-dir 路径]
注意:导入数据保存在本地 data/anko.db,不会上传 GitHub。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from anko.models import Base

PH_NAME = "DND_5E_玩家手册CN.pdf"
MM_NAME = "DND_5E_怪物图鉴CN.pdf"

# 法术章节起始页(第 11 章法术描述从 211 页起)
SPELL_START_PAGE = 211  # 0-based 索引
SPELL_END_PAGE = 312  # 玩家手册总页数

_SPELL_RE = re.compile(
    r"(?m)^[ \t]*([^\n]{2,60}?)[ \t]*\n"
    r"[ \t]*(\d+) 环([^\n]*)\n"
    r"施法时间[:：]([^\n]*)\n"
    r"施法距离[:：]([^\n]*)\n"
    r"法术成分[:：]([^\n]*)\n"
    r"持续时间[:：]([^\n]*)"
)
_NAME_RE = re.compile(r"^([\u4e00-\u9fff·\-'’\s]{1,20}?)\s+([A-Za-z][A-Za-z'’\-\s]{1,60})$")


def extract_pages(path: Path, start: int, end: int) -> list[str]:
    reader = PdfReader(str(path))
    pages = []
    for i in range(start, min(end, len(reader.pages))):
        pages.append(reader.pages[i].extract_text() or "")
    return pages


def parse_spells(pages: list[str]) -> list[dict]:
    """从法术章节页解析法术条目。"""
    text = "\n".join(pages)
    spells: list[dict] = []
    matches = list(_SPELL_RE.finditer(text))
    for idx, m in enumerate(matches):
        name_line = m.group(1).strip()
        nm = _NAME_RE.match(name_line)
        name = nm.group(1).strip() if nm else name_line.strip()
        name_en = nm.group(2).strip() if nm else None
        level = int(m.group(2))
        school_part = m.group(3).strip()
        ritual = "仪式" in school_part
        school = school_part.replace("（仪式）", "").replace("(仪式)", "").strip()
        desc_start = m.end()
        desc_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        description = re.sub(r"\s+", " ", text[desc_start:desc_end]).strip()
        spells.append(
            {
                "name": name,
                "name_en": name_en,
                "level": level,
                "school": school or None,
                "ritual": ritual,
                "casting_time": m.group(4).strip() or None,
                "range": m.group(5).strip() or None,
                "components": m.group(6).strip() or None,
                "duration": m.group(7).strip() or None,
                "description": description,
            }
        )
    return spells


def _dedup(text: str) -> str:
    """压缩相邻重复字符(PDF 字体描边导致的伪影,如'阿阿兰兰')。"""
    return re.sub(r"(.)\1", r"\1", text)


def parse_monsters(pages: list[str]) -> list[dict]:
    """从怪物图鉴页解析怪物统计块。"""
    text = "\n".join(pages)
    pattern = re.compile(
        r"(?m)^[ \t]*([^\n]{2,50}?)[ \t]*\n"
        r"[ \t]*([^\n]{1,50})[,，][ \t]*([^\n]{1,30})[ \t]*\n"
        r"AC[:：][ \t]*([^\n]*)\n"
        r"HP[:：][ \t]*([^\n]*)\n"
        r"速度[:：][ \t]*([^\n]*)"
    )
    monsters: list[dict] = []
    for m in pattern.finditer(text):
        name_line = _dedup(m.group(1).strip())
        nm = _NAME_RE.match(name_line)
        name = nm.group(1).strip() if nm else name_line.strip()
        name_en = nm.group(2).strip() if nm else None
        abilities = {}
        after = text[m.end(): m.end() + 300]
        am = re.search(
            r"力量\s*(\d+).*?敏捷\s*(\d+).*?体质\s*(\d+).*?"
            r"智力\s*(\d+).*?感知\s*(\d+).*?魅力\s*(\d+)",
            after,
            re.S,
        )
        if am:
            abilities = {
                "力量": int(am.group(1)),
                "敏捷": int(am.group(2)),
                "体质": int(am.group(3)),
                "智力": int(am.group(4)),
                "感知": int(am.group(5)),
                "魅力": int(am.group(6)),
            }
        monsters.append(
            {
                "name": name,
                "name_en": name_en,
                "meta": f"{m.group(2).strip()},{m.group(3).strip()}",
                "ac": m.group(4).strip() or None,
                "hp": m.group(5).strip() or None,
                "speed": m.group(6).strip() or None,
                "abilities": abilities,
                "description": "",
            }
        )
    return monsters


def import_rules(pdf_dir: Path, db_url: str = "sqlite:///./data/anko.db") -> None:
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()

    # 清空旧数据
    for model in (RuleSpell, RuleMonster, RuleKnowledge):
        session.query(model).delete()
    session.commit()

    ph = pdf_dir / PH_NAME
    mm = pdf_dir / MM_NAME

    # ---- 玩家手册:知识切块 ----
    if ph.exists():
        print(f"提取玩家手册({ph.name})…")
        pages = extract_pages(ph, 0, 400)
        for i, page_text in enumerate(pages):
            page_text = re.sub(r"\s+", " ", page_text).strip()
            if len(page_text) > 40:
                session.add(
                    RuleKnowledge(
                        book="玩家手册", page=i + 1,
                        title=page_text[:40], content=page_text,
                    )
                )
        # ---- 法术 ----
        print("解析法术条目…")
        spell_pages = extract_pages(ph, SPELL_START_PAGE, SPELL_END_PAGE)
        spells = parse_spells(spell_pages)
        for s in spells:
            session.add(RuleSpell(**s))
        session.commit()
        print(f"  法术 {len(spells)} 个,知识片段 {len(pages)} 段")

    # ---- 怪物图鉴 ----
    if mm.exists():
        print(f"提取怪物图鉴({mm.name})…")
        m_pages = extract_pages(mm, 0, 400)
        monsters = parse_monsters(m_pages)
        for m in monsters:
            session.add(RuleMonster(**m))
        session.commit()
        print(f"  怪物 {len(monsters)} 个")

    session.close()
    print("导入完成 ✅")


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 DND 5E 规则数据")
    parser.add_argument("--pdf-dir", default="D:/bdxiazi/DND 5E 规则包")
    parser.add_argument("--db", default="sqlite:///./data/anko.db")
    args = parser.parse_args()
    import_rules(Path(args.pdf_dir), args.db)


if __name__ == "__main__":
    # 循环导入避免模型未定义
    from anko.models.rules import RuleKnowledge, RuleMonster, RuleSpell  # noqa: F401

    main()
