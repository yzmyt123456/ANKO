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
PH_CLASS_NAMES = ["野蛮人", "吟游诗人", "牧师", "德鲁伊", "战士", "武僧",
                  "圣武士", "游侠", "游荡者", "术士", "邪术师", "法师"]

# 背景条目切块(职业改为 ph_class_hierarchy 职业知识树)
PH_ENTRY_CATS: list[tuple[int, int, str, list[str]]] = [
    (126, 142, "背景", ["侍僧", "骗子", "罪犯", "艺人", "平民英雄", "公会工匠", "隐士", "贵族", "化外之民", "智者", "水手", "士兵", "流浪儿"]),
]


def ph_class_hierarchy(
    pdf_path: Path, start: int, end: int, names: list[str]
) -> list[dict]:
    """职业章 → 职业知识树。

    class 父:§故事(引导 lore + 创建提示);children 含:
    - class_levels:1-20 级职业表(等级→特性 JSON)
    - class_feature:核心职业特性(12pt 标题)/信息小节(10pt)
    - subclass:子职业(12pt 标题),其 children 为各级能力(10pt)
    """
    import json

    anchors = {n: re.compile(rf"^{re.escape(n)}( [A-Za-z][A-Za-z'’\- ]*)?$") for n in names}
    classes: list[dict] = []
    cur: dict | None = None
    for pno, y, size, txt, _bold, _x in _iter_pdf_lines(pdf_path, start, end):
        if size <= 7.5:
            continue
        matched = next((n for n, rx in anchors.items() if rx.match(txt)), None)
        if matched and size >= 13.5:
            if cur:
                classes.append(cur)
            cur = {"name": matched, "title": txt, "pno": pno, "lines": []}
            continue
        if cur is not None:
            cur["lines"].append((pno, round(y), size, txt, _x))

    out: list[dict] = []
    for c in classes:
        out.append(_build_class(c))
    if cur:
        out.append(_build_class(cur))
    return out


_GRADE_RE = re.compile(r"^(\d+)(?:st|nd|rd|th)$")
_LV_TEXT_RE = re.compile(r"第\s*(\d{1,2})\s*级")
_D100_LINE_RE = re.compile(r"^\d{2}~\d{2}")
_PLUS_RE = re.compile(r"^\+\d+$")


def _fix_subclass_tables(sub: dict) -> None:
    """把子职卡中误并入末尾能力的 d100 随机表,归并回表标题对应的能力卡。"""
    kids = sub.get("children") or []
    if not kids:
        return
    for ch in kids:
        ls = (ch.get("content") or "").split("\n")
        cut = None
        target = None
        for i, l in enumerate(ls):
            s = l.strip()
            if not s or _D100_LINE_RE.match(s):
                continue
            # 行 == 某能力标题(表标题),且其后紧接 d100/效应/表行 → 表区
            t = next((k for k in kids if k.get("title", "").strip() == s), None)
            if t is None or t is ch:
                continue
            nxt = "\n".join(ls[i : i + 6]).lower()
            if "d100" in nxt or _D100_LINE_RE.match(ls[i + 1].strip() if i + 1 < len(ls) else ""):
                cut, target = i, t
                break
        if cut is None or target is None:
            continue
        tail = "\n".join(x for x in ls[cut:] if x.strip())
        if len(tail) < 300:
            continue
        ch["content"] = "\n".join(x for x in ls[:cut] if x.strip())
        target["content"] = ((target.get("content") or "").strip() + "\n\n" + tail).strip()


def _class_feature_level(feats_map: dict[str, int], title: str, body: str) -> int | None:
    """特性等级:表匹配优先,否则正文'第 N 级'。"""
    m = _LV_TEXT_RE.search(body)
    if m:
        return int(m.group(1))
    zh = title.split(" ")[0].strip()
    if zh in feats_map:
        return feats_map[zh]
    return None


_NUM_NULL = {"—", "–", "-", "－"}
_STYLE_OPTION_PREFIX = ("箭术", "防御", "对决", "巨武器战斗", "守护", "双武器战斗")


def _merge_class_style_options(node: dict) -> None:
    """把职业下的战斗风格选项卡并入"战斗风格"类卡正文(供前端拆成选项卡),并移除冗余卡。"""
    cards = [
        c for c in node.get("children", [])
        if c.get("kind") == "class_feature" and "战斗风格" in (c.get("title") or "")
    ]
    opts = [
        c for c in node.get("children", [])
        if c.get("kind") == "class_feature" and c.get("title")
        and any(c["title"].startswith(p + " ") for p in _STYLE_OPTION_PREFIX)
    ]
    if not cards or not opts:
        return
    lines = ["可选战斗风格:"]
    for o in opts:
        body = clean_cn_spaces((o.get("content") or "").strip())
        lines.append(f"{o['title']}。{body}".rstrip())
    block = "\n\n" + "\n\n".join(lines)
    for card in cards:
        if "可选战斗风格" not in (card.get("content") or ""):
            card["content"] = (card.get("content") or "") + block
    node["children"] = [c for c in node["children"] if c not in opts]





def _spell_anchor_cols(items: list) -> list | None:
    """小字表格页 → 施法资源列锚点 [(x, label)],非施法表返回 None。

    label: 已知戏法/已知法术/术法点/法术位/法术位环阶/已知祈唤 或 N环。
    """
    grade_ys = [y for y, _t, _x in items if _GRADE_RE.match(_t.strip())]
    if not grade_ys:
        return None
    g0 = min(grade_ys)
    band = [(y, t, x) for y, t, x in items if g0 - 45 <= y < g0 - 1]
    if not band:
        return None
    found: dict[str, float] = {}
    for _y, t, x in band:
        t = t.strip()
        if not t or "职业表" in t[:6]:
            continue
        if t.endswith("戏法"):
            found.setdefault("已知戏法", x)
        elif (
            t.endswith("法术")
            and "法术位" not in t
            and "每环" not in t
            and "豁免" not in t
            and "攻击" not in t
        ):
            found.setdefault("已知法术", x)
        elif t.startswith("术法"):
            found.setdefault("术法点", x)
        elif t == "法术位":
            found.setdefault("法术位", x)
        elif t.startswith("法术位环阶") or t == "环阶":
            found.setdefault("法术位环阶", x)
        elif t == "已知祈唤" or t == "祈唤":
            found.setdefault("已知祈唤", x)
    for _y, t, x in band:
        t = t.strip()
        rm = re.match(r"^([1-9])\s*环$", t)
        if rm:
            found.setdefault(f"{rm.group(1)}环", x)
    # 邪术师:表内只有"法术位环阶"(最大环阶),其列值亦写作"N 环",不应误建环位列
    if "法术位环阶" in found:
        for _k in [k for k in found if re.fullmatch(r"[1-9]环", k)]:
            found.pop(_k)
    if not found:
        return None
    return sorted(found.items(), key=lambda kv: kv[1])  # [(label, x)]


def _assign_cast_res(items: list, y: float, x_grade: float, cols: list | None) -> dict | None:
    """把某等级行中的数字/空值格分配给最近的施法资源列。"""
    if not cols:
        return None
    out: dict[str, object] = {}
    for y2, t2, x2 in items:
        t = t2.strip()
        if not t or abs(y2 - y) > 10 or x2 <= x_grade:
            continue
        if _GRADE_RE.match(t) or _PLUS_RE.match(t):
            continue
        rn = re.match(r"^([1-9])\s*环$", t)
        if rn:
            label, ax = min(cols, key=lambda c: abs(c[1] - x2))
            if abs(ax - x2) <= 45:
                out[label] = int(rn.group(1))
            continue
        if re.search(r"[\u4e00-\u9fff]", t):
            continue
        if t.isdigit() or t in _NUM_NULL:
            label, ax = min(cols, key=lambda c: abs(c[1] - x2))
            if abs(ax - x2) <= 45:  # 列宽有限,防止左侧特性列空值格混入
                out[label] = int(t) if t.isdigit() else None
    return out or None


def _parse_cast_rows(items: list) -> list[dict]:
    """独立施法资源表(无职业特性列的小表,如奥法骑士/诡术师) → [{lv,res}]。"""
    cols = _spell_anchor_cols(items)
    if not cols:
        return []
    rows: list[dict] = []
    for y, txt, x in items:
        m = _GRADE_RE.match(txt.strip())
        if not m:
            continue
        lv = int(m.group(1))
        if lv < 2:
            continue
        res = _assign_cast_res(items, y, x, cols)
        if res:
            rows.append({"lv": lv, "res": res})
    rows.sort(key=lambda r: r["lv"])
    seen: set = set()
    rows = [r for r in rows if not (r["lv"] in seen or seen.add(r["lv"]))]  # type: ignore[func-returns-value]
    return rows


_DESTROY_UNDEAD_TEXT = (
    "第 5 级起，当不死生物进行对抗你驱散特性的豁免失败时，"
    "如果其挑战等级等于或低于一个既定的下限，则该不死生物将被立即摧毁。"
    "相应的数值列在表格“摧毁不死生物”中。\n\n"
    "【表】摧毁不死生物\n"
    "牧师等级 | 摧毁不死生物的挑战等级\n"
    "5 | 1/2 或更低\n"
    "8 | 1 或更低\n"
    "11 | 2 或更低\n"
    "14 | 3 或更低\n"
    "17 | 4 或更低"
)


_CLASS_HP = {
    "野蛮人": ("1d12", "12", "7"), "吟游诗人": ("1d8", "8", "5"),
    "牧师": ("1d8", "8", "5"), "德鲁伊": ("1d8", "8", "5"),
    "战士": ("1d10", "10", "6"), "武僧": ("1d8", "8", "5"),
    "圣武士": ("1d10", "10", "6"), "游侠": ("1d10", "10", "6"),
    "游荡者": ("1d8", "8", "5"), "术士": ("1d6", "6", "4"),
    "邪术师": ("1d8", "8", "5"), "法师": ("1d6", "6", "4"),
}


def _strip_story_table_junk(zh: str, content: str) -> str | None:
    """职业简介误并等级表文字时,按该职业页面段落锚点重建简介(仅德鲁伊/野蛮人/术士)。"""
    lines = (content or "").split("\n")
    junk = next(
        (i for i, l in enumerate(lines) if l.strip() == "职业" or l.strip().startswith("职业等级")),
        None,
    )
    if junk is None:
        return None

    def find(prefix: str, start: int = 0) -> int | None:
        for i in range(start, len(lines)):
            if lines[i].startswith(prefix):
                return i
        return None

    if zh == "德鲁伊":
        bal = find("维持平衡", junk + 1)
        hd = find("自然之力")
        p2 = find("德鲁伊的法术")
        cb = find("德鲁伊也会", bal + 1) if bal is not None else None
        cc = find("德鲁伊经常", bal + 1) if bal is not None else None
        if None in (bal, hd, p2, cb, cc) or not (hd < p2 < junk < bal < cb < cc):
            return None
        return "\n\n".join([
            "\n".join(lines[:hd]),
            "\n".join(lines[hd:p2]),
            "\n".join(lines[p2:junk]),
            "\n".join(lines[bal:cb]),
            "\n".join(lines[cb:cc]),
            "\n".join(lines[cc:]),
        ]).strip()
    if zh == "野蛮人":
        p2 = find("野蛮人活跃")
        h2 = find("危险的生活")
        tail = find("野蛮人面对危险时", junk + 1)
        if None in (p2, h2, tail) or not (p2 < h2 < junk < tail):
            return None
        return "\n\n".join([
            "\n".join(lines[:p2]),
            "\n".join(lines[p2:h2]),
            "\n".join(lines[h2:junk]),
            "\n".join(lines[tail:]),
        ]).strip()
    if zh == "术士":
        p2 = find("术法力量")
        p3 = find("术士不需要")
        h2 = find("未知力量")
        tail = find("驱使术士冒险", junk + 1)
        if None in (p2, p3, h2, tail) or not (p2 < p3 < h2 < junk < tail):
            return None
        return "\n\n".join([
            "\n".join(lines[:p2]),
            "\n".join(lines[p2:p3]),
            "\n".join(lines[p3:h2]),
            "\n".join(lines[h2:junk]),
            "\n".join(lines[tail:]),
        ]).strip()
    if zh == "圣武士":
        p2s = find("圣武士经年累月")
        h2 = find("超凡脱俗")
        tail = find("冒险中的圣武士", junk + 1)
        if None in (p2s, h2, tail) or not (p2s < h2 < junk < tail):
            return None
        return "\n\n".join([
            "\n".join(lines[:p2s]),
            "\n".join(lines[p2s:h2]),
            "\n".join(lines[h2:junk]),
            "\n".join(lines[tail:]),
        ]).strip()
    if zh == "武僧":
        p2 = find("有的武僧彻底")
        tail = find("武僧大多不拒绝", junk + 1)
        if None in (p2, tail) or not (p2 < junk < tail):
            return None
        return "\n\n".join([
            "\n".join(lines[:p2]),
            "\n".join(lines[p2:junk]),
            "\n".join(lines[tail:]),
        ]).strip()
    if zh == "法师":
        p2 = find("法师们为魔法而生")
        tail = find("法师的生活", junk + 1)
        if None in (p2, tail) or not (p2 < junk < tail):
            return None
        return "\n\n".join([
            "§故事",
            "奥术学者 Scholars of the Arcane\n" + "\n".join(lines[2:p2]).strip(),
            "知识的诱惑 The Lure of Knowledge\n" + "\n".join(lines[p2:junk]).strip(),
            "\n".join(lines[tail:]).strip(),
        ]).strip()
    if zh == "游侠":
        return "\n".join(lines[:junk]).strip()
    if zh == "邪术师":
        tail = find("立下契约后", junk + 1)
        if tail is None:
            return None
        return "\n\n".join([
            "\n".join(lines[:junk]),
            "\n".join(lines[tail:]),
        ]).strip()
    if zh == "战士":
        tail = find("某些战士认为", junk + 1)
        if tail is None:
            return None
        return "\n\n".join([
            "\n".join(lines[:junk]),
            "\n".join(lines[tail:]),
        ]).strip()
    return None


def _fix_known_class_texts(node: dict) -> None:
    """文本层勘误(玩家手册 PDF 矢量字抽取常见丢字):不依赖视觉识图二次兜底。"""
    import json

    zh = (node.get("title") or "").split(" ")[0]
    story = _strip_story_table_junk(zh, node.get("content") or "")
    if story is not None:
        node["content"] = story
    for k in node.get("children", []):
        if k.get("kind") == "class_levels":
            rows = json.loads(k["content"])
            for r in rows:
                f = r.get("feats", "")
                if "/休）" in f and "短休" not in f:
                    r["feats"] = f.replace("/休）", "/短休）")
            k["content"] = json.dumps(rows, ensure_ascii=False)
        if k.get("kind") == "class_feature" and k.get("title", "").startswith(
            "摧毁不死生物"
        ):
            k["content"] = _DESTROY_UNDEAD_TEXT
            k["lv"] = 5
        # 德鲁伊:同一张卡误合"荒野形态+德鲁伊结社"(均 Lv2) → 拆成两张
        if (
            k.get("kind") == "class_feature"
            and k.get("title", "").startswith("荒野形态 Wild Shape 德鲁伊结社 Druid Circle")
        ):
            body = k.get("content") or ""
            marker = "第 2 级时，你将选择参与一个德鲁伊结社"
            at = body.find(marker)
            wild_body = body[:at].strip() if at > 0 else body
            circle_body = body[at:].strip() if at > 0 else (
                "第 2 级时，你将选择参与一个德鲁伊结社。你可以从大地结社 Circle of the Land 或月亮结社 Circle of the Moon 中选择其一。\n\n"
                "第 2、6、10、14 级时，你将获得所选结社相应的特性；大地结社与月亮结社的具体能力见下方「子职业」卡片。"
            )
            k["title"] = "荒野形态 Wild Shape"
            k["content"] = wild_body
            node["children"].append({
                "title": "德鲁伊结社 Druid Circle",
                "page": k.get("page"),
                "kind": "class_feature",
                "content": circle_body,
                "children": [],
            })
        # 战士等职业表与右侧"生命值"同高重叠时,正文易被误当作表格丢弃 → 自动回填
        if (
            k.get("kind") == "class_base"
            and k.get("title", "").startswith("生命值 Hit Points")
            and not (k.get("content") or "").strip()
            and zh in _CLASS_HP
        ):
            die, first, fixed = _CLASS_HP[zh]
            k["content"] = (
                f"生命骰：每{zh}等级{die}\n"
                f"首级生命值：{first}＋你的体质调整值\n"
                f"升级生命值：首级生命值之外，对应每个{zh}等级{fixed}（{die}）＋你的体质调整值"
            )


def _build_class(c: dict) -> dict:
    """解析单个职业的行流 → 树节点。"""
    import json

    lines = c["lines"]
    # ---- 等级表:等级格 ↔ 同行最近特性格 配对 ----
    by_page: dict[int, list] = {}
    for pno, y, sz, txt, x in lines:
        if sz >= 11:  # 标题级文本不参与表格
            continue
        by_page.setdefault(pno, []).append([y, txt, x])
    table_cells: set = set()
    # 表头"职业特性"列 x(用于行内定位特性格)
    header_x: float | None = None
    for _pno, _items in by_page.items():
        for _y, txt, x in _items:
            if txt.strip() == "职业特性":
                header_x = x
                break
        if header_x is not None:
            break
    level_rows: list[dict] = []
    feat_pages: set[int] = set()
    for pno, items in by_page.items():
        page_cols = _spell_anchor_cols(items)
        page_has_feat = 0
        for y, txt, x in items:
            m = _GRADE_RE.match(txt.strip())
            if not m:
                continue
            lv = int(m.group(1))
            # 特性格:取同行与"职业特性"列最接近的中文格(无表头时取最左中文)
            best = None
            for y2, t2, x2 in items:
                if not re.search(r"[\u4e00-\u9fff]", t2) or _GRADE_RE.match(t2.strip()):
                    continue
                if t2.strip() in (
                    "熟练项 Proficiencies", "生命值 Hit Point", "生命值 Hit Points", "装备 Equipment",
                    "＋你的体质调整值", "+你的体质调整值",
                ):
                    # 栏外基础卡标题(如页边"熟练项/生命值")不是等级表特性格
                    continue
                if x2 <= x or x2 - x > 300 or len(t2) > 36:
                    continue
                if abs(y2 - y) > 8:
                    continue
                dx = abs(x2 - header_x) if header_x is not None else x2
                # 先比"与职业特性列对齐"(列距离),再比行内纵向距离,防止栏边词同高误夺
                if best is None or (dx, abs(y2 - y)) < best[:2]:
                    best = (dx, abs(y2 - y), x2, t2)
            if best is not None:
                page_has_feat += 1
            # 熟练加值:同行 x 最小的 +N 格(等级格右侧第一数值列)
            prof = None
            for y2, t2, x2 in items:
                if not _PLUS_RE.match(t2.strip()):
                    continue
                if x2 <= x or x2 - x > 300 or abs(y2 - y) > 8:
                    continue
                if prof is None or x2 < prof[0]:
                    prof = (x2, t2.strip())
            row = {"lv": lv, "prof": prof[1] if prof else "", "feats": best[3] if best else ""}
            res = _assign_cast_res(items, y, x, page_cols)
            if res:
                row["res"] = res
            level_rows.append(row)
            # 标记该表行全部格(等级列到特性列之间小字)供 sections 跳过
            for y2, t2, x2 in items:
                if abs(y2 - y) <= 2 and x - 6 <= x2 <= x + 300:
                    table_cells.add((pno, round(y2), x2))
        if page_has_feat >= 10:
            feat_pages.add(pno)
    level_rows.sort(key=lambda r: r["lv"])
    # 等级去重(某些职业页含多张同等级小表,保留首次/主表)
    _seen: set = set()
    level_rows = [
        r for r in level_rows if not (r["lv"] in _seen or _seen.add(r["lv"]))  # type: ignore[func-returns-value]
    ]
    # 特性→等级映射(表权威)
    feats_map: dict[str, int] = {}
    for r in level_rows:
        for f in re.split(r"[，,、/]", r["feats"]):
            f = f.strip()
            if f and f not in feats_map:
                feats_map[f] = r["lv"]

    # ---- 标题小节流 ----
    sections: list[dict] = []
    cur_sec: dict | None = None
    for pno, y, size, txt, x in lines:
        # 标题级文本永不跳过;仅小字表格格按 (页,基线,x) 精确跳过
        if (pno, y, x) in table_cells and size < 9.5:
            continue
        if size <= 7.5 or "职业表" in txt[:6]:
            continue
        if size >= 9.5 and len(txt) <= 60:
            if cur_sec is not None and abs(y - (cur_sec.get("ty") or 0)) <= 22:
                cur_sec["title"] = f"{cur_sec['title']} {txt}"
                cur_sec["ty"] = y
                continue
            sections.append({"title": txt, "size": size, "pno": pno, "ty": y, "lines": []})
            cur_sec = sections[-1]
        elif cur_sec is not None:
            cur_sec["lines"].append(txt)
    # 无标题正文归入 story 前导(职业名后 lore 段)

    def feat_kind(title: str) -> str:
        return "class_base" if title.split(" ")[0] in ("生命值", "熟练项", "装备") else "class_feature"

    def make_feat(s: dict) -> dict:
        body = clean_cn_spaces(
            "\n".join(x.strip() for x in s["lines"] if x.strip())
        )
        body = "\n".join(x for x in body.split("\n") if x)
        lv = _class_feature_level(feats_map, s["title"], body)
        extra = {}
        if lv is not None:
            extra["lv"] = lv
        return {
            "title": clean_cn_spaces(s["title"]),
            "page": s["pno"] + 1,
            "kind": feat_kind(s["title"]),
            "content": body,
            "children": [],
            **extra,
        }

    node = {
        "title": c["title"],
        "page": c["pno"] + 1,
        "kind": "class",
        "content": "",
        "parent_title": c["name"],
        "children": [],
    }
    # 等级表卡
    rows_json = json.dumps(level_rows, ensure_ascii=False)
    node["children"].append(
        {"title": "职业等级表", "page": node["page"], "kind": "class_levels",
         "content": rows_json, "children": []}
    )

    # 分区域:pre(story/创建)、core(Class Features 后到子职分区)、sub
    phase = "pre"
    story_parts: list[str] = []
    sub: dict | None = None
    for s in sections:
        title = s["title"]
        if s["size"] >= 13.5 and "职业特性" in title:
            phase = "core"
            continue
        if s["size"] >= 13.5:
            phase = "sub"
            sub = None
            continue
        if phase == "pre":
            if "创建" in title or title.startswith("快速建卡"):
                node["children"].append(make_feat(s))
            else:
                part = clean_cn_spaces(
                    "\n".join([title] + [x.strip() for x in s["lines"] if x.strip()])
                )
                if part:
                    story_parts.append(part)
            continue
        if phase == "core":
            node["children"].append(make_feat(s))
            continue
        # sub 区域
        if s["size"] >= 11.5:
            sub = make_feat(s)
            sub["kind"] = "subclass"
            node["children"].append(sub)
        elif sub is not None:
            sub["children"].append(make_feat(s))
        else:
            node["children"].append(make_feat(s))

    # 子职卡:将误并入末尾能力的 d100 随机表归并到该子职首个能力
    for _sub in node["children"]:
        if _sub.get("kind") == "subclass":
            _fix_subclass_tables(_sub)

    # 子职独立施法资源表(奥法骑士/诡术师 3-20 级小表)→ 子职卡下新增 class_levels
    cast_pages: dict[int, list] = {}
    for _pno, _items in by_page.items():
        if _pno in feat_pages:
            continue
        _rows = _parse_cast_rows(_items)
        if len(_rows) >= 12:
            cast_pages[_pno] = _rows
    for _sub in node["children"]:
        if _sub.get("kind") != "subclass":
            continue
        if any(ch.get("kind") == "class_levels" for ch in (_sub.get("children") or [])):
            continue
        # 仅挂接通过子职获得施法能力的子职(如奥法骑士/诡术师的"施法 Spellcasting")
        if not any(
            ch.get("kind") != "class_levels" and ch.get("title", "").startswith("施法")
            for ch in (_sub.get("children") or [])
        ):
            continue
        sp = _sub["page"] - 1
        for _pno in range(sp - 3, sp + 4):
            _rows = cast_pages.get(_pno)
            if _rows:
                _sub.setdefault("children", []).append(
                    {
                        "title": "施法资源表(环位)",
                        "page": _sub["page"],
                        "kind": "class_levels",
                        "content": json.dumps(_rows, ensure_ascii=False),
                        "children": [],
                    }
                )
                break

    if story_parts:
        node["content"] = f"§故事\n{chr(10).join(story_parts)}"
    # 战斗风格选项卡(战士/圣武士/游侠)并入对应"战斗风格"卡
    _merge_class_style_options(node)
    # 文本层已知勘误:等级表引导神力"X/休)"补"短";摧毁不死生物卡正文/表格规范化
    _fix_known_class_texts(node)
    return node

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
    """遍历页范围文本行 (pno, y, size, text, has_bold, x)。"""
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
                    yield (
                        pno,
                        round(l["bbox"][1]),
                        max(s["size"] for s in spans),
                        txt,
                        has_bold,
                        round(l["bbox"][0]),
                    )
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

    for pno, y, size, txt, _bold, _x in _iter_pdf_lines(pdf_path, start, end):
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
    for pno, y, size, txt, has_bold, _x in _iter_pdf_lines(pdf_path, start, end):
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
                ("image", "ALTER TABLE rule_knowledge ADD COLUMN image VARCHAR(300)"),
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
            # 种族/职业 → 分层知识卡树;背景 → 条目
            def _add_tree(node: dict, cat: str, pid=None) -> None:  # noqa: ANN001
                nonlocal knowledge_count
                rec = RuleKnowledge(
                    book=stem, page=node["page"], title=node["title"],
                    category=cat, kind=node["kind"], parent_id=pid,
                    content=node["content"],
                )
                session.add(rec)
                session.flush()
                knowledge_count += 1
                for ch in node.get("children") or []:
                    _add_tree(ch, cat, rec.id)

            for rp in ph_race_hierarchy(pdf, 17, 44, PH_RACE_NAMES):
                _add_tree(rp, "种族")
            for cls in ph_class_hierarchy(pdf, 45, 120, PH_CLASS_NAMES):
                _add_tree(cls, "职业")
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
