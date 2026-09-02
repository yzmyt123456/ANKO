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
import pymupdf
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from anko.models import Base
from anko.models.rules import RuleKnowledge, RuleMap, RuleMonster, RuleSpell

PH_NAME = "DND_5E_玩家手册CN.pdf"
MM_NAME = "DND_5E_怪物图鉴CN.pdf"

# 法术章节起始页(第 11 章法术描述从 211 页起)
SPELL_START_PAGE = 211  # 0-based 索引
SPELL_END_PAGE = 312  # 玩家手册总页数

# 玩家手册章节页范围(0-based 索引)与分类名。条目章节只保留引言页,
# 其余按条目切块(见 PH_ENTRY_CATS)。
PH_PAGE_CATS: list[tuple[int, int, str]] = [
    (0, 10, "导言"),
    (10, 16, "创建角色"),
    # (16, 17) 种族章引言碎片不与种族卡混排,不导入
    (44, 45, "职业"),  # 第 3 章引言页,条目从 p45 起
    (120, 126, "背景"),  # 第 4 章导言(个性/阵营/语言/激励),条目从 p126 起
    (142, 162, "装备"),
    (162, 170, "自定义选项"),
    (172, 180, "属性值应用"),
    (180, 188, "冒险"),
    (188, 198, "战斗"),
    (200, 206, "施法"),
    (206, 289, "法术"),  # 已结构化到 rule_spells,知识片段跳过
    (289, 292, "状态"),
    (292, 299, "诸神"),
    (299, 303, "位面"),
    (303, 311, "生物资料"),
    (311, 313, "附录"),
]

# 条目切块锚点:职业/背景 的条目名与对应分类。
# (种族改为 ph_race_hierarchy 分层卡片,不走此处)
PH_ENTRY_CATS: list[tuple[int, int, str, list[str]]] = [
    (45, 120, "职业", ["野蛮人", "吟游诗人", "牧师", "德鲁伊", "战士", "武僧", "圣武士", "游侠", "游荡者", "术士", "邪术师", "法师"]),
    (126, 142, "背景", ["侍僧", "骗子", "罪犯", "艺人", "平民英雄", "公会工匠", "隐士", "贵族", "化外之民", "智者", "水手", "士兵", "流浪儿"]),
]

_ENTRY_ANCHOR_CACHE: dict[tuple, re.Pattern] = {}


def entry_anchor_re(names: list[str]) -> re.Pattern:
    """匹配'条目名 英文名'行(条目切块锚点)。"""
    key = tuple(names)
    if key not in _ENTRY_ANCHOR_CACHE:
        alt = "|".join(map(re.escape, names))
        _ENTRY_ANCHOR_CACHE[key] = re.compile(
            rf"^({alt})\s+([A-Z][A-Za-z'’\-\/\s]+)$"
        )
    return _ENTRY_ANCHOR_CACHE[key]

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
        description = normalize_spell_desc(description)
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


# 中文字符与中文标点(用于空格清理)
_CN = r"[\u4e00-\u9fff，。、；：！？（）【】《》“”‘’·—…]"


def clean_cn_spaces(text: str) -> str:
    """移除中文之间的无意义空格(PDF 换行/字距产生的'若命 中')。"""
    text = re.sub(rf"({_CN}) (?={_CN})", r"\1", text)
    # 中文字符与中文标点之间的空格
    text = re.sub(rf"({_CN}) (?=[，。、；：！？])", r"\1", text)
    text = re.sub(rf"([，。、；：！？]) (?={_CN})", r"\1", text)
    return text


def normalize_spell_desc(desc: str) -> str:
    """规范法术描述:清理空格、规范段落。"""
    desc = clean_cn_spaces(desc)
    # 升环施法效应 独立成段
    desc = re.sub(r"升环施法效应。", "\n升环施法效应。", desc)
    # 多余空白折叠为单个换行
    desc = re.sub(r"[ \t]+\n", "\n", desc)
    desc = re.sub(r"\n{2,}", "\n", desc)
    return desc.strip()


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


def _fix_cn_en_space(text: str) -> str:
    """中英文边界补充空格(pymupdf 跨字体 span 拼接会丢失)。"""
    text = re.sub(r"([\u4e00-\u9fff])([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])([\u4e00-\u9fff])", r"\1 \2", text)
    return text


def _iter_pdf_lines(pdf_path: Path, start: int, end: int):
    """遍历玩家手册页范围的文本行 (pno, y, size, text, has_bold),按 PDF 内容流顺序。"""
    doc = pymupdf.open(str(pdf_path))
    try:
        for pno in range(start, min(end, doc.page_count)):
            d = doc[pno].get_text("dict")
            for b in d["blocks"]:
                if b["type"] != 0:
                    continue
                for l in b["lines"]:
                    spans = l["spans"]
                    if not spans:
                        continue
                    parts = []
                    has_bold = False
                    for s in spans:
                        t = s["text"]
                        if t:
                            parts.append(t)
                        if t.strip() and (
                            (s["flags"] & 16)
                            or "Bold" in s["font"]
                            or "bold" in s["font"]
                        ):
                            has_bold = True
                    txt = _fix_cn_en_space("".join(parts)).strip()
                    if not txt:
                        continue
                    yield pno, l["bbox"][1], max(s["size"] for s in spans), txt, has_bold
    finally:
        doc.close()


def ph_section_pieces(
    pdf_path: Path, start: int, end: int, cat: str
) -> list[tuple]:
    """玩家手册按小节标题(size>=9.5)切块,保留原文行;返回 (title, page, cat, content)。"""
    pieces: list[tuple] = []
    cur_title: str | None = None
    cur_pno: int | None = None
    cur_lines: list[tuple[float, str]] = []
    last_title_y: float | None = None

    def flush() -> None:
        nonlocal cur_title, cur_pno, cur_lines, last_title_y
        if cur_lines:
            title = cur_title or f"{cat} · 第{cur_pno + 1}页"
            content_lines = [clean_cn_spaces(t.strip()) for _, t in cur_lines]
            content = "\n".join(x for x in content_lines if x)
            if content:
                pieces.append((clean_cn_spaces(title), (cur_pno or 0) + 1, cat, content))
        cur_title, cur_pno, cur_lines, last_title_y = None, None, [], None  # noqa: F824

    for pno, y, size, txt, _bold in _iter_pdf_lines(pdf_path, start, end):
        if size <= 7.5:  # 页码
            continue
        if size >= 9.5 and len(txt) <= 60:
            # 相邻的标题行(如中文/英文两行)合并为同一标题
            if cur_title is not None and last_title_y is not None and abs(y - last_title_y) <= 35:
                cur_title = f"{cur_title} {txt}"
            else:
                flush()
                cur_title = txt
                cur_pno = pno
            last_title_y = y
        else:
            if cur_title is None and cur_pno is None:
                cur_pno = pno
            cur_lines.append((y, txt))
            last_title_y = None
    flush()
    return pieces


def ph_entry_pieces(
    pages: list[str], start: int, end: int, cat: str, names: list[str]
) -> list[tuple]:
    """玩家手册按条目切块(如'矮人 Dwarf'),整条目合并为一条。"""
    anchor = entry_anchor_re(names)
    boundaries: list[tuple[int, int, str]] = []
    for pi in range(start, min(end, len(pages))):
        for li, line in enumerate(pages[pi].splitlines()):
            line = line.strip()
            if anchor.match(line):
                boundaries.append((pi, li, line))

    pieces: list[tuple] = []
    for i, (pi, li, line) in enumerate(boundaries):
        name = line.split()[0]
        if i + 1 < len(boundaries):
            epi, eli, _ = boundaries[i + 1]
            if epi == pi:
                lines = pages[pi].splitlines()[li:eli]
            else:
                lines = pages[pi].splitlines()[li:]
                for mp in range(pi + 1, epi):
                    lines.extend(pages[mp].splitlines())
                lines.extend(pages[epi].splitlines()[:eli])
        else:
            lines = pages[pi].splitlines()[li:]
            for mp in range(pi + 1, min(end, len(pages))):
                lines.extend(pages[mp].splitlines())
        content_lines = [clean_cn_spaces(ln.strip()) for ln in lines]
        content = "\n".join(ln for ln in content_lines if ln)
        pieces.append((name, pi + 1, cat, content))
    return pieces


PH_RACE_NAMES = ["矮人", "精灵", "半身人", "人类", "龙裔", "侏儒", "半精灵", "半兽人", "提夫林"]


_CN_TRAIT_NAMES = ("年龄", "阵营", "体型", "速度", "语言", "亚种", "技能", "专长",
                   "属性值加成", "幸运", "勇气", "出神", "矮人体魄", "矮人战斗训练",
                   "矮人护甲训练", "工具熟练项", "石中精妙", "黑暗视觉", "敏锐感官",
                   "精类血统", "多才多艺", "炎狱抗性", "地狱遗赠", "侏儒狡黠", "矮人刚毅")


def _is_trait_start(s: str, has_bold: bool) -> bool:
    """特质起点:带加粗英文名且以句号结束('中文名 英文。描述'),或白名单纯中文短名。"""
    if has_bold and re.match(
        r"^[\u4e00-\u9fff·（）()]{2,12}\s+[A-Za-z][A-Za-z'’\-\s/]*?。", s
    ):
        return True
    for n in _CN_TRAIT_NAMES:
        if s.startswith(n + "。"):
            # 孤行只有名称+句号(如'语言。')是上一特质描述的断行残词
            if not s[len(n) + 1 :].strip():
                return False
            return True
    return False


def _split_trait_lines(lines) -> list[dict]:
    """把'XX Traits/特质'小节内容按每条特质切分。lines 可含 (txt, has_bold)。"""
    traits: list[dict] = []
    for item in lines:
        s = item[0].strip() if isinstance(item, (tuple, list)) else item.strip()
        bold = bool(item[1]) if isinstance(item, (tuple, list)) else False
        if not s:
            continue
        if _is_trait_start(s, bold):
            traits.append({"name": s.split("。")[0].strip(), "lines": [s]})
        elif traits:
            traits[-1]["lines"].append(s)
        elif len(s) > 6:
            # 标题后导语(前几个非特质句子)并入首条,避免丢失
            traits.append({"name": None, "lines": [s]})
    return [t for t in traits if t.get("name") or t["lines"]]


def ph_race_hierarchy(
    pdf_path: Path, start: int, end: int, names: list[str]
) -> tuple[list[dict], list[dict]]:
    """种族章 → 分层卡片。

    父卡(kind='race'):content 含 §故事(引文)/§简介 段;
    子卡(kind='race_part'):种族内小节(大族谱/人类特质/各人种/…)。
    返回 (parents, children),children 带 parent_title 便于回填 parent_id。
    """
    anchors = {n: re.compile(rf"^{re.escape(n)}( [A-Za-z][A-Za-z'’\-/ ]*)?$") for n in names}
    parents: list[dict] = []
    cur: dict | None = None
    for pno, y, size, txt, has_bold in _iter_pdf_lines(pdf_path, start, end):
        if size <= 7.5:
            continue
        matched = next((n for n, rx in anchors.items() if rx.match(txt)), None)
        if matched:
            if cur and (cur["lead"] or cur["sections"]):
                parents.append(cur)
            cur = {
                "name": matched,
                "title": txt,
                "pno": pno,
                "lead": [],
                "sections": [],
                "sec": None,
            }
            continue
        if cur is None:
            continue
        if size >= 9.5 and len(txt) <= 60 and not txt.startswith("§"):
            # 相邻的标题行(中文/英文两行)合并为同一标题
            if cur["sec"] is not None and abs(y - cur["sec"]["ty"]) <= 22:
                cur["sec"]["title"] = f'{cur["sec"]["title"]} {txt}'
                cur["sec"]["ty"] = y
            else:
                cur["sections"].append({"title": txt, "pno": pno, "lines": [], "ty": y})
                cur["sec"] = cur["sections"][-1]
        elif cur["sec"] is not None:
            cur["sec"]["lines"].append((txt, has_bold))
        else:
            cur["lead"].append(txt)
    if cur and (cur["lead"] or cur["sections"]):
        parents.append(cur)

    def make_trait(tr: dict, page: int) -> dict:
        """特质条目(title=名称,content=去除名称前缀后的描述)。"""
        lines_clean = [clean_cn_spaces(x.strip()) for x in tr["lines"]]
        first = lines_clean[0] if lines_clean else ""
        name = tr.get("name") or ""
        if name and first.startswith(name + "。"):
            rest = first[len(name) + 1 :].strip()
            lines_clean = ([rest] if rest else []) + lines_clean[1:]
        body = "\n".join(x for x in lines_clean if x)
        return {"title": name, "page": page, "kind": "trait", "content": body, "children": []}

    out_parents: list[dict] = []
    for p in parents:
        lead = clean_cn_spaces("\n".join(x.strip() for x in p["lead"] if x.strip()))
        story = None
        intro = lead
        lines = lead.split("\n")
        for i, ln in enumerate(lines):
            ls = ln.strip()
            if ls.startswith(("——", "—", "–")) and len(ls) < 90:
                story = clean_cn_spaces("\n".join(lines[: i + 1]))
                rest = "\n".join(lines[i + 1 :])
                intro = clean_cn_spaces(rest.strip())
                break
        parts = []
        if story:
            parts.append(f"§故事\n{story}")
        if intro:
            parts.append(f"§简介\n{intro}")
        parent = {
            "title": p["title"],
            "page": p["pno"] + 1,
            "kind": "race",
            "content": "\n\n".join(parts),
            "parent_title": p["name"],
            "children": [],
        }
        for sec in p["sections"]:
            title = clean_cn_spaces(sec["title"])
            spage = sec["pno"] + 1
            if re.search(r"特质|Traits", title):
                # 特质小节 → 按每条特质拆成独立知识卡(kind=trait)
                for tr in _split_trait_lines(sec["lines"]):
                    if tr.get("name") is None:
                        continue
                    body = make_trait(tr, spage)["content"]
                    if body:
                        parent["children"].append(make_trait(tr, spage))
                continue
            # 亚种/文化小节:内含"属性值加成"特质 → 亚种,拆分;否则整块
            split_parts = _split_trait_lines(sec["lines"])
            named = [t for t in split_parts if t.get("name")]
            is_subrace = any(t["name"].startswith("属性值") for t in named)
            if named and is_subrace:
                sub_desc = ""
                if split_parts and split_parts[0].get("name") is None:
                    sub_desc = clean_cn_spaces(
                        "\n".join(x.strip() for x in split_parts[0]["lines"] if x.strip())
                    )
                sub = {
                    "title": title, "page": spage, "kind": "race_part",
                    "content": sub_desc, "children": [],
                }
                for tr in named:
                    mt = make_trait(tr, spage)
                    if mt["content"]:
                        sub["children"].append(mt)
                parent["children"].append(sub)
            else:
                body = clean_cn_spaces(
                    "\n".join(x[0].strip() for x in sec["lines"] if x[0].strip())
                )
                body = "\n".join(x for x in body.split("\n") if x)
                if body:
                    parent["children"].append(
                        {"title": title, "page": spage, "kind": "race_part",
                         "content": body, "children": []}
                    )
        out_parents.append(parent)
    return out_parents


def import_rules(pdf_dir: Path, db_url: str = "sqlite:///./data/anko.db") -> None:
    """全量导入:核心规则 + 冒险模组 → 知识库;地图 → 地图素材库。"""
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    # SQLite 旧表补充新列(幂等)
    try:
        with engine.connect() as conn:
            cols = [
                r[1]
                for r in conn.exec_driver_sql("PRAGMA table_info(rule_knowledge)")
            ]
            for col, ddl in (
                ("category", "ALTER TABLE rule_knowledge ADD COLUMN category VARCHAR(50)"),
                ("kind", "ALTER TABLE rule_knowledge ADD COLUMN kind VARCHAR(20)"),
                ("parent_id", "ALTER TABLE rule_knowledge ADD COLUMN parent_id INTEGER"),
            ):
                if col not in cols:
                    conn.exec_driver_sql(ddl)
            conn.commit()
    except Exception:  # noqa: BLE001
        pass
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

        # 玩家手册 → 按章节/条目切块入库;其他书按页切块
        pages = []
        for i in range(min(total, 400)):
            pages.append(reader.pages[i].extract_text() or "")

        if "玩家手册" in stem:
            for start, end, cat in PH_PAGE_CATS:
                if cat == "法术":
                    continue
                for title, pno, pcat, content in ph_section_pieces(pdf, start, end, cat):
                    session.add(
                        RuleKnowledge(
                            book=stem, page=pno,
                            title=title, category=pcat, content=content,
                        )
                    )
                    knowledge_count += 1
            # 种族章 → 分层知识卡树(race 父卡 / race_part 亚种与小节 / trait 特质)
            def _add_race_tree(node: dict, pid=None) -> None:  # noqa: ANN001
                nonlocal knowledge_count
                rec = RuleKnowledge(
                    book=stem, page=node["page"], title=node["title"],
                    category="种族", kind=node["kind"], parent_id=pid,
                    content=node["content"],
                )
                session.add(rec)
                session.flush()
                knowledge_count += 1
                for ch in node.get("children") or []:
                    _add_race_tree(ch, rec.id)

            for rp in ph_race_hierarchy(pdf, 17, 44, PH_RACE_NAMES):
                _add_race_tree(rp)
            for start, end, cat, names in PH_ENTRY_CATS:
                for title, pno, pcat, content in ph_entry_pieces(
                    pages, start, end, cat, names
                ):
                    session.add(
                        RuleKnowledge(
                            book=stem, page=pno,
                            title=title, category=pcat, content=content,
                        )
                    )
                    knowledge_count += 1
        else:
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
    main()
