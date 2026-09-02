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
    r"[ \t]*((?:\d+) 环[^\n]*|[\u4e00-\u9fff·]+ 戏法[^\n]*)[ \t]*\n"
    r"施法时间[:：]([^\n]*)\n"
    r"施法距离[:：]([^\n]*)\n"
    r"法术成分[:：]([\s\S]*?)\n"
    r"持续时间[:：]([^\n]*)"
)
_NAME_RE = re.compile(
    r"^([\u4e00-\u9fff·/\-&，、／'’\s]{1,24}?)\s+"
    r"([A-Za-z][A-Za-z'’\-\/\s]{1,60})$"
)


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
        # 环阶行解析:支持 "2 环 塑能" 与 "变化 戏法" 两种格式
        level_line = m.group(2).strip()
        if "戏法" in level_line:
            level = 0
            school_part = level_line.split("戏法")[0].strip()
            school = school_part
        else:
            lm = re.match(r"(\d+) 环(.*)", level_line)
            level = int(lm.group(1))
            school_part = (lm.group(2) or "").strip()
            school = school_part
        ritual = "仪式" in school_part
        school = (
            school.replace("（仪式）", "").replace("(仪式)", "").strip()
            or None
        )
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
                "casting_time": m.group(3).strip() or None,
                "range": m.group(4).strip() or None,
                "components": m.group(5).strip() or None,
                "duration": m.group(6).strip() or None,
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
    """全量导入:核心规则 + 冒险模组 → 知识库;地图 → 地图素材库。"""
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()

    # 清空旧数据
    for model in (RuleSpell, RuleMonster, RuleKnowledge, RuleMap):
        session.query(model).delete()
    session.commit()

    maps_dir = Path("data/maps")
    maps_dir.mkdir(parents=True, exist_ok=True)

    spells_count = monsters_count = knowledge_count = maps_count = 0

    # ---- 遍历顶层 PDF ----
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        stem = pdf.stem
        try:
            reader = PdfReader(str(pdf))
        except Exception as exc:  # noqa: BLE001
            print(f"  跳过 {pdf.name}: {exc}")
            continue
        total = len(reader.pages)
        print(f"[{stem}] {total} 页")

        # 知识切块(每本书最多 400 页)
        pages = []
        for i in range(min(total, 400)):
            pages.append(reader.pages[i].extract_text() or "")
        for i, page_text in enumerate(pages):
            cleaned = re.sub(r"\s+", " ", page_text).strip()
            if len(cleaned) > 40:
                session.add(
                    RuleKnowledge(
                        book=stem, page=i + 1,
                        title=cleaned[:40], content=cleaned,
                    )
                )
                knowledge_count += 1

        # 玩家手册 → 法术
        if "玩家手册" in stem:
            spell_pages = extract_pages(pdf, SPELL_START_PAGE, SPELL_END_PAGE)
            spells = parse_spells(spell_pages)
            for s in spells:
                session.add(RuleSpell(**s))
            spells_count = len(spells)

        # 怪物图鉴 → 怪物
        if "怪物图鉴" in stem:
            m_pages = []
            for i in range(min(total, 400)):
                m_pages.append(reader.pages[i].extract_text() or "")
            monsters = parse_monsters(m_pages)
            for m in monsters:
                session.add(RuleMonster(**m))
            monsters_count = len(monsters)

        session.commit()

    # ---- 冒险模组文件夹 → 知识库 ----
    module_dir = pdf_dir / "冒险模组"
    if module_dir.is_dir():
        for pdf in sorted(module_dir.glob("*.pdf")):
            stem = pdf.stem
            try:
                reader = PdfReader(str(pdf))
            except Exception as exc:  # noqa: BLE001
                print(f"  跳过 {pdf.name}: {exc}")
                continue
            total = len(reader.pages)
            print(f"[冒险模组/{stem}] {total} 页")
            for i in range(min(total, 400)):
                page_text = reader.pages[i].extract_text() or ""
                cleaned = re.sub(r"\s+", " ", page_text).strip()
                if len(cleaned) > 40:
                    session.add(
                        RuleKnowledge(
                            book=stem, page=i + 1,
                            title=cleaned[:40], content=cleaned,
                        )
                    )
                    knowledge_count += 1
            session.commit()

    # ---- 地图包 → 地图素材库 ----
    import pymupdf

    map_dir = pdf_dir / "地图包"
    if map_dir.is_dir():
        for pdf in sorted(map_dir.glob("*.pdf")):
            stem = pdf.stem
            try:
                doc = pymupdf.open(str(pdf))
            except Exception as exc:  # noqa: BLE001
                print(f"  跳过地图 {pdf.name}: {exc}")
                continue
            for pno in range(len(doc)):
                page = doc[pno]
                pix = page.get_pixmap(dpi=150)
                out = maps_dir / f"{stem}_p{pno + 1}.png"
                pix.save(str(out))
                session.add(
                    RuleMap(
                        name=f"{stem} (第{pno + 1}页)",
                        source=f"地图包/{pdf.name}",
                        file=f"/maps/{out.name}",
                        width=pix.width,
                        height=pix.height,
                    )
                )
                maps_count += 1
            doc.close()
            session.commit()

    session.close()
    print(
        f"导入完成 ✅ 法术 {spells_count} · 怪物 {monsters_count} · "
        f"知识片段 {knowledge_count} · 地图 {maps_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 DND 5E 规则数据")
    parser.add_argument("--pdf-dir", default="D:/bdxiazi/DND 5E 规则包")
    parser.add_argument("--db", default="sqlite:///./data/anko.db")
    args = parser.parse_args()
    import_rules(Path(args.pdf_dir), args.db)


if __name__ == "__main__":
    # 循环导入避免模型未定义
    from anko.models.rules import (  # noqa: F401
        RuleKnowledge,
        RuleMap,
        RuleMonster,
        RuleSpell,
    )

    main()
