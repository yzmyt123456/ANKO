"""人物卡模板注册表。

模板定义人物卡的结构化字段分组与"鉴定"配置。
例如 DND 5e 模板:六属性 / 战斗 / 熟练 / 法术 / 鉴定项。
新增模板只需在 TEMPLATES 中添加定义,无需改动核心代码。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TemplateField:
    """模板中的一个字段定义。"""

    key: str
    label: str
    type: str = "text"  # text | textarea | number | dnd_score
    placeholder: str = ""


@dataclass
class TemplateGroup:
    """字段分组(表单与详情展示按分组渲染)。"""

    key: str
    label: str
    fields: list[TemplateField]


@dataclass
class CheckDef:
    """一个可鉴定的项目(用于 DND 鉴定掷骰)。"""

    key: str
    label: str  # 如 力量鉴定 / 察觉 / 豁免
    kind: str  # stat | skill | save
    stat: str  # 对应的六属性 key,用于计算属性修正
    prof: str = ""  # 熟练名(技能名或属性中文名),为空则不做熟练判断


@dataclass
class CardTemplate:
    """一张人物卡模板。"""

    id: str
    name: str
    description: str
    groups: list[TemplateGroup]
    checks: list[CheckDef] = field(default_factory=list)

    def to_dict(self, include_checks: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "groups": [
                {
                    "key": g.key,
                    "label": g.label,
                    "fields": [
                        {
                            "key": f.key,
                            "label": f.label,
                            "type": f.type,
                            "placeholder": f.placeholder,
                        }
                        for f in g.fields
                    ],
                }
                for g in self.groups
            ],
        }
        if include_checks:
            data["checks"] = [
                {
                    "key": c.key,
                    "label": c.label,
                    "kind": c.kind,
                    "stat": c.stat,
                    "prof": c.prof,
                }
                for c in self.checks
            ]
        return data


# ------------------------------------------------------------
# DND 5e 常量
# ------------------------------------------------------------
DND_STAT_KEYS = [
    "strength", "dexterity", "constitution",
    "intelligence", "wisdom", "charisma",
]
DND_STAT_LABELS = {
    "strength": "力量",
    "dexterity": "敏捷",
    "constitution": "体质",
    "intelligence": "智力",
    "wisdom": "感知",
    "charisma": "魅力",
}


def dnd_modifier(score: Optional[int]) -> int:
    """DND 5e 属性修正:(属性值 - 10) // 2。"""
    try:
        return (int(score) - 10) // 2
    except (TypeError, ValueError):
        return 0


def _dnd_stat_fields() -> list[TemplateField]:
    return [
        TemplateField(k, DND_STAT_LABELS[k], "dnd_score")
        for k in DND_STAT_KEYS
    ]


def _dnd_stat_checks() -> list[CheckDef]:
    return [
        CheckDef(k, f"{DND_STAT_LABELS[k]}鉴定", "stat", k)
        for k in DND_STAT_KEYS
    ]


def _dnd_save_checks() -> list[CheckDef]:
    """六属性豁免(体质/魅力常为熟练豁免)。"""
    return [
        CheckDef(f"save_{k}", f"{DND_STAT_LABELS[k]}豁免", "save", k, DND_STAT_LABELS[k])
        for k in DND_STAT_KEYS
    ]


def _dnd_skill_checks() -> list[CheckDef]:
    """常用 DND 技能鉴定(技能名 ↔ 属性 + 熟练判断)。"""
    skills = [
        # 力量
        ("athletics", "运动", "strength"),
        # 敏捷
        ("acrobatics", "体操", "dexterity"),
        ("sleight_of_hand", "巧手", "dexterity"),
        ("stealth", "潜行", "dexterity"),
        # 智力(知识类)
        ("arcana", "奥秘", "intelligence"),
        ("history", "历史", "intelligence"),
        ("investigation", "调查", "intelligence"),
        ("nature", "自然", "intelligence"),
        ("religion", "宗教", "intelligence"),
        # 感知
        ("animal_handling", "驯兽", "wisdom"),
        ("insight", "洞悉", "wisdom"),
        ("medicine", "医疗", "wisdom"),
        ("perception", "察觉", "wisdom"),
        ("survival", "生存", "wisdom"),
        # 魅力
        ("deception", "欺瞒", "charisma"),
        ("intimidation", "威吓", "charisma"),
        ("performance", "表演", "charisma"),
        ("persuasion", "游说", "charisma"),
    ]
    return [
        CheckDef(key, label, "skill", stat, label)
        for key, label, stat in skills
    ]


DEFAULT_TEMPLATE = CardTemplate(
    id="default",
    name="通用",
    description="自由属性与标签,适合大多数非 DND 角色。",
    groups=[
        TemplateGroup(
            "general",
            "基本信息",
            [
                TemplateField("attributes", "属性(自由键值)", "dynamic",
                              placeholder="如 智慧: 16"),
            ],
        )
    ],
)

DND5E_TEMPLATE = CardTemplate(
    id="dnd5e",
    name="DND 5e",
    description="龙与地下城 5e 角色卡:六属性、AC、法术、熟练等精细字段,支持鉴定掷骰。",
    groups=[
        TemplateGroup("basic", "基础信息", [
            TemplateField("alignment", "阵营"),
            TemplateField("race", "种族背景"),
            TemplateField("klass", "职业"),
            TemplateField("level", "等级"),
        ]),
        TemplateGroup("stats", "六维属性", _dnd_stat_fields()),
        TemplateGroup("combat", "战斗与防御", [
            TemplateField("hp", "生命值(HP)", "text"),
            TemplateField("ac", "防御等级(AC)", "text"),
            TemplateField("spell_dc", "法术豁免 DC", "text"),
            TemplateField("proficiency_bonus", "熟练加值", "number"),
            TemplateField("primary_stat", "主要属性"),
            TemplateField("armor_training", "护甲受训"),
        ]),
        TemplateGroup("proficiency", "熟练与语言", [
            TemplateField("save_proficiencies", "熟练属性豁免", "textarea"),
            TemplateField("skill_proficiencies", "技能熟练", "textarea"),
            TemplateField("weapon_proficiencies", "武器熟练"),
            TemplateField("tool_proficiencies", "工具熟练"),
            TemplateField("languages", "语言"),
        ]),
        TemplateGroup("spells", "法术", [
            TemplateField("spellcasting_ability", "施法属性"),
            TemplateField("spell_slots", "法术位"),
            TemplateField("known_spells", "掌握法术", "textarea"),
            TemplateField("known_cantrips", "掌握戏法", "textarea"),
        ]),
        TemplateGroup("features", "特质与专长", [
            TemplateField("class_features", "职业特性", "textarea"),
            TemplateField("feats", "专长"),
            TemplateField("faith", "信仰"),
        ]),
        TemplateGroup("equipment", "装备", [
            TemplateField("equipment", "起始装备", "textarea"),
        ]),
    ],
    checks=_dnd_stat_checks() + _dnd_save_checks() + _dnd_skill_checks(),
)

# 内置模板注册表
TEMPLATES: list[CardTemplate] = [DEFAULT_TEMPLATE, DND5E_TEMPLATE]


def get_template(template_id: str) -> Optional[CardTemplate]:
    """按 id 查找模板。"""
    for t in TEMPLATES:
        if t.id == template_id:
            return t
    return None


def list_templates() -> list[dict]:
    """返回模板简要列表。"""
    return [t.to_dict(include_checks=False) for t in TEMPLATES]
