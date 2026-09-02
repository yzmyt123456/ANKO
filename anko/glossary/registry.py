"""内置 DND 词条注册表。

每个词条:名称 / 分类 / 灰机 Wiki 释义页链接。
前端据此把人物卡、剧情中的 DND 专有名词渲染为可点击跳转链接。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 灰机 Wiki DND 站首页
DND_WIKI_BASE = "https://dnd.huijiwiki.com/wiki"

# 分类说明(供前端展示)
CATEGORY_LABELS = {
    "attribute": "属性",
    "skill": "技能",
    "spell": "法术",
    "class": "职业",
    "rule": "规则",
    "equipment": "装备",
}

# (名称, 分类, wiki 页面名)
_RAW_ENTRIES: list[tuple[str, str, str]] = [
    # ---- 属性(统一指向"玩家手册2014/属性值应用"的完整释义) ----
    ("力量", "attribute", "玩家手册2014/属性值应用"),
    ("敏捷", "attribute", "玩家手册2014/属性值应用"),
    ("体质", "attribute", "玩家手册2014/属性值应用"),
    ("智力", "attribute", "玩家手册2014/属性值应用"),
    ("感知", "attribute", "玩家手册2014/属性值应用"),
    ("魅力", "attribute", "玩家手册2014/属性值应用"),
    # ---- 技能 ----
    ("运动", "skill", "运动"),
    ("体操", "skill", "体操"),
    ("巧手", "skill", "巧手"),
    ("潜行", "skill", "潜行"),
    ("奥秘", "skill", "奥秘"),
    ("历史", "skill", "历史"),
    ("调查", "skill", "调查"),
    ("自然", "skill", "自然"),
    ("宗教", "skill", "宗教"),
    ("驯兽", "skill", "驯兽"),
    ("洞悉", "skill", "洞悉"),
    ("医疗", "skill", "医疗"),
    ("察觉", "skill", "察觉"),
    ("生存", "skill", "生存"),
    ("欺瞒", "skill", "欺瞒"),
    ("威吓", "skill", "威吓"),
    ("表演", "skill", "表演"),
    ("游说", "skill", "游说"),
    # ---- 法术(玩家手册 2024) ----
    ("易容术", "spell", "易容术"),
    ("七彩喷射", "spell", "七彩喷射"),
    ("雷鸣波", "spell", "雷鸣波"),
    ("术法爆发", "spell", "术法爆发"),
    ("传讯术", "spell", "传讯术"),
    ("心灵之楔", "spell", "心灵之楔"),
    ("修复术", "spell", "修复术"),
    ("次级幻象", "spell", "次级幻象"),
    ("光亮术", "spell", "光亮术"),
    ("火球术", "spell", "火球术"),
    ("魔法飞弹", "spell", "魔法飞弹"),
    ("护盾术", "spell", "护盾术"),
    ("燃烧之手", "spell", "燃烧之手"),
    ("治愈真言", "spell", "治愈真言"),
    ("睡眠术", "spell", "睡眠术"),
    ("油腻术", "spell", "油腻术"),
    ("闪电束", "spell", "闪电束"),
    ("法术反制", "spell", "法术反制"),
    ("解除魔法", "spell", "解除魔法"),
    ("侦测魔法", "spell", "侦测魔法"),
    ("通晓语言", "spell", "通晓语言"),
    ("隐身术", "spell", "隐身术"),
    ("飞行术", "spell", "飞行术"),
    # ---- 职业 ----
    ("术士", "class", "术士#原初魔法"),
    ("狂野魔法", "class", "职业/2014/术士#狂野魔法"),
    ("法师", "class", "法师"),
    ("牧师", "class", "牧师"),
    ("战士", "class", "战士"),
    ("盗贼", "class", "盗贼"),
    # ---- 规则 ----
    ("防御等级", "rule", "防御等级"),
    ("生命值", "rule", "生命值"),
    ("熟练加值", "rule", "熟练加值"),
    ("豁免", "rule", "豁免"),
    ("施法者等级", "rule", "施法者等级"),
    # ---- 装备 ----
    ("简易武器", "equipment", "简易武器"),
    ("矛", "equipment", "矛"),
    ("匕首", "equipment", "匕首"),
    ("奥术法器", "equipment", "奥术法器"),
    ("皮甲", "equipment", "皮甲"),
    ("长剑", "equipment", "长剑"),
    ("短弓", "equipment", "短弓"),
    ("重弩", "equipment", "重弩"),
]


@dataclass(frozen=True)
class GlossaryEntry:
    """一个 DND 词条。"""

    name: str
    category: str
    url: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "category_label": CATEGORY_LABELS.get(self.category, self.category),
            "url": self.url,
        }


def _build() -> list[GlossaryEntry]:
    entries: list[GlossaryEntry] = []
    for name, category, page in _RAW_ENTRIES:
        entries.append(
            GlossaryEntry(
                name=name,
                category=category,
                url=f"{DND_WIKI_BASE}/{page}",
            )
        )
    # 名称长优先,保证最长匹配
    entries.sort(key=lambda e: len(e.name), reverse=True)
    return entries


ENTRIES: list[GlossaryEntry] = _build()
# 名称 → 词条(用于快速查找)
_BY_NAME: dict[str, GlossaryEntry] = {e.name: e for e in ENTRIES}


def list_entries(category: str | None = None) -> list[dict]:
    """返回词条列表(可按分类过滤)。"""
    entries = ENTRIES if category is None else [
        e for e in ENTRIES if e.category == category
    ]
    return [e.to_dict() for e in entries]


def find_entries(text: str) -> list[dict]:
    """从文本中找出命中的词条(去重,按出现位置)。"""
    text = text or ""
    hits: list[GlossaryEntry] = []
    seen: set[str] = set()
    for entry in ENTRIES:
        if entry.name in text and entry.name not in seen:
            seen.add(entry.name)
            hits.append(entry)
    return [e.to_dict() for e in hits]


def linkify(text: str) -> list[dict]:
    """把文本中的 DND 名词标注为可链接片段。

    返回片段列表:[{"text": "...", "entry": {...} | None}, ...]
    前端可据此渲染为链接。
    """
    text = text or ""
    if not text:
        return []
    # 用正则切分:先找所有命中的词条位置
    pattern = "|".join(re.escape(e.name) for e in ENTRIES)
    if not pattern:
        return [{"text": text, "entry": None}]

    segments: list[dict] = []
    last = 0
    for m in re.finditer(pattern, text):
        if m.start() > last:
            segments.append({"text": text[last : m.start()], "entry": None})
        name = m.group(0)
        entry = _BY_NAME.get(name)
        segments.append(
            {"text": name, "entry": entry.to_dict() if entry else None}
        )
        last = m.end()
    if last < len(text):
        segments.append({"text": text[last:], "entry": None})
    return segments
