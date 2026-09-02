"""AI 业务服务:从大段文本解析出结构化数据。

目前提供:
- parse_character(text):角色描述 → 人物卡草稿(name/title/bio/attributes/tags)

设计为可扩展:后续可增加 parse_story_outline、rewrite_text 等方法,
统一在此处维护提示词与解析逻辑。
"""

from __future__ import annotations

import json
import re
from typing import Any

from anko.ai.client import AIError, AIClient
from anko.config import AISettings

# 允许的最大输入长度(字符)
MAX_INPUT_CHARS = 8000

_CHARACTER_PROMPT = """你是一个专业的角色卡整理助手。用户会粘贴一段关于某个角色的描述文本,请从中提取信息,只输出一个 JSON 对象,不要输出任何其他文字或解释。

JSON 结构:
{
  "name": "角色名(必填,从文本中识别)",
  "title": "称号或职业(没有则为空字符串)",
  "bio": "简洁的背景故事概括(150 字以内,只提炼文本中已有的信息,不要编造)",
  "attributes": {"属性名": 数值或简短描述, ...},
  "tags": ["简短标签", ...]
}

规则:
1. name 必须从文本中识别,若确实无法识别则填空字符串。
2. attributes 只提取文本中明确提到的属性/能力/性格特征,数值或描述均可。
3. tags 提取 3~8 个主题标签,如 主角/魔法/冒险/暗黑。
4. 只输出 JSON,不要 Markdown 代码块包裹,不要任何额外文字。

角色描述:
""" + "{text}"


def build_character_prompt(text: str) -> str:
    """构造角色解析提示词。"""
    # 注意:提示词中含 JSON 花括号,不能使用 str.format,需用 replace
    return _CHARACTER_PROMPT.replace("{text}", text[:MAX_INPUT_CHARS])


def extract_json(text: str) -> dict:
    """从 LLM 回复中稳健地提取 JSON 对象。"""
    content = text.strip()
    # 去掉 ```json ... ``` 代码块包裹
    fence = re.search(r"```(?:json)?\s*(.*?)```", content, re.S)
    if fence:
        content = fence.group(1).strip()
    # 提取第一个 { 到最后一个 } 之间的部分
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIError("AI 回复中未找到 JSON 数据")
    raw = content[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"AI 返回的 JSON 无法解析:{exc}") from exc
    if not isinstance(data, dict):
        raise AIError("AI 返回的数据不是 JSON 对象")
    return data


def normalize_character_draft(data: dict) -> dict:
    """把 AI 返回的原始 JSON 规范化为人物卡草稿。"""
    attributes: dict[str, Any] = {}
    raw_attrs = data.get("attributes") or {}
    if isinstance(raw_attrs, dict):
        for key, value in raw_attrs.items():
            key = str(key).strip()
            if key:
                attributes[key] = value

    tags = [
        str(t).strip()
        for t in (data.get("tags") or [])
        if isinstance(t, (str, int, float)) and str(t).strip()
    ]

    draft = {
        "name": str(data.get("name") or "").strip(),
        "title": str(data.get("title") or "").strip() or None,
        "bio": str(data.get("bio") or "").strip() or None,
        "template": str(data.get("template") or "default").strip(),
        "stats": {},
        "attributes": attributes,
        "tags": tags[:10],
    }
    return draft


# ------------------------------------------------------------
# DND 5e 解析
# ------------------------------------------------------------
_DND_PROMPT = """你是一个专业的 DND 5e 角色卡整理助手。用户会粘贴一段 DND 角色卡文本,请从中提取信息,只输出一个 JSON 对象,不要输出任何其他文字。

JSON 结构:
{
  "name": "角色名",
  "title": "称号(没有则为空字符串)",
  "bio": "背景故事概括(100 字以内)",
  "stats": {
    "alignment": "阵营",
    "race": "种族背景",
    "klass": "职业",
    "level": "等级",
    "hp": "生命值(HP)",
    "strength": 12,
    "dexterity": 18,
    "constitution": 13,
    "intelligence": 15,
    "wisdom": 9,
    "charisma": 20,
    "ac": "防御等级",
    "spell_dc": "法术豁免DC",
    "proficiency_bonus": 2,
    "primary_stat": "主要属性",
    "save_proficiencies": "熟练属性豁免",
    "skill_proficiencies": "技能熟练",
    "weapon_proficiencies": "武器熟练",
    "armor_training": "护甲受训",
    "equipment": "起始装备",
    "tool_proficiencies": "工具熟练",
    "languages": "语言",
    "spellcasting_ability": "施法属性",
    "spell_slots": "法术位",
    "known_spells": "掌握法术",
    "known_cantrips": "掌握戏法",
    "class_features": "职业特性",
    "feats": "专长",
    "faith": "信仰"
  },
  "tags": ["简短标签", ...]
}

规则:
1. 六属性(strength~charisma)只取数字本身,不要带修正值。
2. proficiency_bonus 取数字。
3. 无法提取的字段填空字符串。
4. 文本按原样整理,保留顿号、逗号分隔。
5. 只输出 JSON,不要 Markdown 代码块包裹,不要任何额外文字。

角色卡文本:
""" + "{text}"


def build_dnd_prompt(text: str) -> str:
    return _DND_PROMPT.replace("{text}", text[:MAX_INPUT_CHARS])


def normalize_dnd_draft(data: dict) -> dict:
    """规范化 DND 解析结果。"""
    from anko.templates.registry import DND5E_TEMPLATE

    raw_stats = data.get("stats") or {}
    if not isinstance(raw_stats, dict):
        raw_stats = {}

    stats: dict[str, Any] = {}
    for group in DND5E_TEMPLATE.groups:
        for field in group.fields:
            key = field.key
            if key == "attributes":
                continue
            value = raw_stats.get(key)
            if field.type == "dnd_score" or key == "proficiency_bonus":
                try:
                    stats[key] = int(str(value).strip())
                except (TypeError, ValueError):
                    stats[key] = 0
            elif value is None:
                stats[key] = ""
            else:
                stats[key] = str(value).strip()

    draft = normalize_character_draft(data)
    draft["template"] = "dnd5e"
    draft["stats"] = stats
    return draft


class AIService:
    """AI 能力门面:路由到具体功能。"""

    def __init__(self, settings: AISettings) -> None:
        self._settings = settings
        self._client = AIClient(settings)

    @property
    def enabled(self) -> bool:
        """是否已配置可用(开启且填了 api_key)。"""
        return self._settings.enabled and bool(self._settings.api_key)

    @property
    def provider_desc(self) -> str:
        return f"{self._settings.base_url} / {self._settings.model}"

    async def parse_character(
        self, text: str, template: str = "default"
    ) -> dict:
        """把一段角色描述解析为人物卡草稿。"""
        text = (text or "").strip()
        if not text:
            raise ValueError("角色描述不能为空")
        if len(text) > MAX_INPUT_CHARS:
            raise ValueError(f"描述过长(>{MAX_INPUT_CHARS} 字),请精简后重试")

        if template == "dnd5e":
            prompt = build_dnd_prompt(text)
        else:
            prompt = build_character_prompt(text)

        content = await self._client.chat(
            [{"role": "user", "content": prompt}]
        )
        data = extract_json(content)

        if template == "dnd5e":
            draft = normalize_dnd_draft(data)
        else:
            draft = normalize_character_draft(data)

        if not draft["name"]:
            raise ValueError("AI 未能从这段文本中识别出角色名,可尝试补充人物名字后重试")
        return draft
