"""AI 业务服务:从大段文本解析出结构化数据。

目前提供:
- parse_character(text):角色描述 → 人物卡草稿(name/title/bio/attributes/tags)

设计为可扩展:后续可增加 parse_story_outline、rewrite_text 等方法,
统一在此处维护提示词与解析逻辑。
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from anko.ai.client import AIError, AIClient
from anko.ai import dm as dm_assets
from anko.ai import corpus as corpus_assets
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


def _strip_trailing_commas(text: str) -> str:
    """移除 JSON 对象/数组中多余的尾随逗号(跳过字符串内容)。

    例如:{ "a": 1, } → { "a": 1 }(AI 常犯的错误)
    """
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            # 向后跳过空白,若紧跟 } 或 ] 则为尾随逗号,跳过它
            j = i + 1
            while j < n and text[j] in " \t\n\r":
                j += 1
            if j < n and text[j] in "}]":
                i = j
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_json_lenient(raw: str) -> Any:
    """宽容 JSON 解析:容忍尾随逗号等常见 AI 输出问题。"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    cleaned = _strip_trailing_commas(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIError(f"AI 返回的 JSON 无法解析:{exc}") from exc


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
    data = _parse_json_lenient(raw)
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


# ------------------------------------------------------------
# 骰点创建法生成角色(借鉴经典安科人物创建流程)
# ------------------------------------------------------------
_GENERATE_PROMPT_DND = """你是一位资深的安科导游与 DND 5e 规则助手。请用经典的"骰点创建法"为用户生成一位登场角色,并且**像经典安科串一样,完整展示骰点过程**。

骰点创建法流程(请严格遵循):
1. 先理解"故事设定",把角色自然地融入其中。
2. 依次"掷骰决定"(在脑海中模拟骰子,给出合理结果):
   - 种族(人类/精灵/矮人/半精灵/提夫林等)
   - 阵营(DND 九宫格:守序/中立/混乱 × 善良/中立/邪恶)
   - 出身背景(贵族/士兵/流浪者/学者/工匠/艺人等)
   - 职业(战士/法师/游荡者/术士/牧师/游侠/圣武士/德鲁伊等)
3. 属性骰点:采用安科骰点法 —— 六项属性(力量/敏捷/体质/智力/感知/魅力)各"掷两次 1d16+2 取较高值"(普通人约 10),再按种族/背景做少量调整,最终 8~20。
4. 结合"角色提示"与故事设定,撰写角色的性格与背景(150 字内),个性鲜明、有安科风味。
5. 生成 3~6 个标签。

输出要求(重要):
- 先输出一段【创建过程】安科文本,严格模仿资深安科导游的节奏与排版,每个决策按以下步骤展开:
  1. 引导语:以角色口吻引出问题,如"首先,我们的故事开始于？""这位冒险者的种族是？"
  2. 掷骰提示与限定:如"[1d8]",可附一句括号说明,如"(考虑到画风,这里限定人类与类人种族)"
  3. 完整选项列表:每行一个,如"1人类""2精灵(使用精灵的模板)"
  4. 骰点结果单独一行,如"[1D8=2]";选中的选项在列表中用 **加粗** 标出(如"**2 → 人类**")
  5. 选中项详解:给出该选项名称与一段设定描述,如"人类 Human\n在整个多元宇宙中,人类……"(3~5 句,有世界观味)
  6. 视情况给一句角色台词(带引号),展现人物性格,如"“诶？黑刀之夜？不太明白您的意思呢。”"
- 属性骰点采用安科式,如:[力量] 两次1d16+2:7+2=9、10+2=12 → 取高 12
- 在决策之间穿插段落式背景叙述(2~4 句),营造"命运在骰子间展开"的氛围
- 过程文本控制在 900 字以内,保留安科的"命运感"。
- 过程文本结束后,单独一行输出【最终人物卡】,然后只输出 JSON 对象(不要任何其他文字):
{
  "name": "角色名",
  "title": "称号或职业",
  "bio": "背景故事概括",
  "stats": {
    "alignment": "阵营", "race": "种族", "klass": "职业", "level": "1级",
    "hp": "生命值(如 12)", "strength": 12, "dexterity": 14, "constitution": 13,
    "intelligence": 10, "wisdom": 9, "charisma": 16,
    "ac": "防御等级(如 15)", "spell_dc": "法术DC", "proficiency_bonus": 2,
    "primary_stat": "主要属性", "save_proficiencies": "熟练豁免",
    "skill_proficiencies": "熟练技能", "weapon_proficiencies": "武器熟练",
    "equipment": "起始装备", "languages": "语言", "tool_proficiencies": "工具熟练",
    "class_features": "职业特性", "feats": "专长", "faith": "信仰"
  },
  "tags": ["标签1", "标签2"]
}

故事设定:
""" + "{story}" + """

角色提示:
""" + "{hint}"


_GENERATE_PROMPT_DEFAULT = """你是一位资深的安科导游与 AI 创作助手。请用"骰点创建法"为用户生成一位登场角色,并且**像经典安科串一样,完整展示骰点过程**。

流程:
1. 先理解"故事设定",把角色自然地融入其中。
2. 依次"掷骰决定"身份/性格/经历(展示选项与骰子结果)。
3. 结合"角色提示"撰写人物背景(150字内),给出 3~6 个标签和若干自由属性(如智慧/武力/魅力等)。

输出要求(重要):
- 先输出一段【创建过程】安科文本,完整展示骰点过程:
  · 每个决策(身份/性格/经历)【列出全部选项】并掷骰,选中项用 **加粗** 标注并附骰点结果,
    例如:**3 → 沉稳** [1d10=3]
  · 每项骰点都用表达式展示,每个决定附一句简短说明,600 字以内。
- 过程文本结束后,单独一行输出【最终人物卡】,然后只输出 JSON 对象:
{
  "name": "角色名",
  "title": "称号",
  "bio": "背景故事概括",
  "attributes": {"属性名": 数值或描述, ...},
  "tags": ["标签1", "标签2"]
}

故事设定:
""" + "{story}" + """

角色提示:
""" + "{hint}"


# 过程文本与最终 JSON 之间的分隔标记
PROCESS_MARKER = "【最终人物卡】"


def build_generate_prompt(
    story_context: str,
    hint: str,
    template: str,
    partial: str = "",
) -> str:
    story = (story_context or "").strip()[:3000] or "无特别设定,由你自由发挥一个奇幻世界。"
    hint = (hint or "").strip()[:500] or "无特别要求,自由发挥。"
    prompt = (
        _GENERATE_PROMPT_DND if template == "dnd5e" else _GENERATE_PROMPT_DEFAULT
    )
    prompt = prompt.replace("{story}", story).replace("{hint}", hint)
    if partial.strip():
        prompt += (
            "\n\n========================\n"
            "以下是一段已经生成的内容(可能不完整,可能在被用户中断处截断)。\n"
            "请从中断处继续,不要重复开头,最终输出完整的过程文本与"
            f"{PROCESS_MARKER} 分隔的完整 JSON。已生成内容:\n"
            f"{partial.strip()[:4000]}"
        )
    return prompt


_STORY_SEGMENT_PROMPT = """你是一位资深的安科导游。玩家用骰子推进剧情,你要接着“当前正文”写出**下一段**(一段即可)。

当前正文:
{context}

登场角色卡片:
{cast}

最近掷骰结果(供参考,不要在正文里重复骰点):
{roll_note}

本段指示:
{instruction}

要求:
1. 只输出一段 150~400 字的安科正文,风格贴合上文,自然收尾,不要标题、不要序号、不要额外说明。
2. 不要在本段内自行掷骰;如果你认为该在此处做一次判定,在段落末尾另起一行只输出一行:“判定:表达式”,例如“判定:1d100”。
3. 必须紧密承接上文与登场角色的设定。
"""


def build_story_segment_prompt(
    context: str,
    cast: str,
    instruction: str = "",
    roll_note: str = "",
) -> str:
    return (
        _STORY_SEGMENT_PROMPT
        .replace("{context}", (context or "").strip()[:6000] or "(正文为空,写一段开场)")
        .replace("{cast}", (cast or "").strip()[:1500] or "(暂无角色卡)")
        .replace("{roll_note}", (roll_note or "").strip()[:600] or "(尚未掷骰)")
        .replace("{instruction}", (instruction or "").strip()[:500] or "自然推进剧情一个段落")
    )


def split_process_and_json(text: str) -> tuple[str, str]:
    """把 AI 输出拆分为(过程文本, JSON 原文)。"""
    if PROCESS_MARKER in text:
        process, json_part = text.split(PROCESS_MARKER, 1)
        return process.strip(), json_part
    # 兜底:尝试从全文提取 JSON
    return "", text


class AIService:
    """AI 能力门面:路由到具体功能。

    配置支持运行时更新(通过 config_getter 从数据库读取最新配置),
    网页上修改 AI 设置后无需重启立即生效。
    """

    def __init__(
        self,
        settings: AISettings,
        config_getter: Optional[Callable[[], AISettings]] = None,
    ) -> None:
        self._default_settings = settings
        self._config_getter = config_getter

    def _current(self) -> AISettings:
        """获取当前生效的 AI 配置。"""
        if self._config_getter is not None:
            s = self._config_getter()
            if s is not None:
                return s
        return self._default_settings

    @property
    def enabled(self) -> bool:
        """是否已配置可用(开启且填了 api_key)。"""
        s = self._current()
        return s.enabled and bool(s.api_key)

    @property
    def provider_desc(self) -> str:
        s = self._current()
        return f"{s.base_url} / {s.model}"

    async def test_connection(self) -> dict:
        """测试 AI 连接:发送一条最小消息。"""
        client = AIClient(self._current())
        try:
            reply = await client.chat(
                [{"role": "user", "content": "请回复 OK"}]
            )
            return {"ok": True, "reply": (reply or "")[:50]}
        except AIError as exc:
            return {"ok": False, "error": str(exc)}

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

        client = AIClient(self._current())
        content = await client.chat(
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

    async def generate_character(
        self,
        story_context: str = "",
        hint: str = "",
        template: str = "dnd5e",
    ) -> dict:
        """用"骰点创建法"生成一位角色(借鉴经典安科人物创建流程)。

        story_context:故事世界观/已写剧情摘要(供 AI 参考融合)
        hint:         用户对角色的一句话想法(可选)
        """
        client = AIClient(self._current())
        content = await client.chat(
            [{"role": "user", "content": build_generate_prompt(
                story_context, hint, template)}]
        )
        data = extract_json(content)

        if template == "dnd5e":
            draft = normalize_dnd_draft(data)
        else:
            draft = normalize_character_draft(data)

        if not draft["name"]:
            raise ValueError("AI 未能生成角色名,请重试")
        return draft

    async def generate_character_stream(
        self,
        story_context: str = "",
        hint: str = "",
        template: str = "dnd5e",
        partial: str = "",
        extra_rules: str = "",
    ):
        """流式生成角色:逐块产出增量文本(供 SSE 推送)。

        支持 partial:从已生成(可能被中断)的文本处继续补全。
        extra_rules:本地规则库检索到的规则参考片段。
        """
        client = AIClient(self._current())
        prompt = build_generate_prompt(story_context, hint, template, partial)
        if extra_rules.strip():
            prompt += (
                "\n\n【本地规则参考(创建角色时请参考并尽量符合)】\n"
                f"{extra_rules.strip()[:2500]}"
            )
        async for delta in client.chat_stream(
            [{"role": "user", "content": prompt}]
        ):
            yield delta

    async def generate_story_segment_stream(
        self,
        context: str,
        cast: str,
        instruction: str = "",
        roll_note: str = "",
        extra_rules: str = "",
        persona_id: str = dm_assets.PERSONA_ID,
    ):
        """续写一段安科正文(流式):供“逐段生成、玩家可中途修改”流程使用。"""
        client = AIClient(self._current())
        prompt = build_story_segment_prompt(context, cast, instruction, roll_note)
        prompt += "\n\n【导游人格参考】\n" + dm_assets.persona_rules(persona_id)
        if extra_rules.strip():
            prompt += (
                "\n\n【本地规则参考(保证世界观/规则一致)】\n"
                f"{extra_rules.strip()[:2500]}"
            )
        async for delta in client.chat_stream(
            [{"role": "user", "content": prompt}]
        ):
            yield delta

    async def dm_propose(
        self,
        context: str,
        cast: str,
        instruction: str = "",
        roll_note: str = "",
        extra_rules: str = "",
        persona_id: str = dm_assets.PERSONA_ID,
    ) -> dict:
        """导游提案:判断下一步该叙述、掷骰,还是把选择权交还玩家。

        返回 JSON 提案(kind=roll/narrate/ask),由前端展示给玩家确认后再执行真实掷骰或写正文。
        """
        refs = []
        try:
            query = f"{instruction or ''} {cast or ''} {context or ''}"
            refs = corpus_assets.search_corpus(query, top=3)
        except Exception:  # noqa: BLE001 语料缺失不阻断
            refs = []
        corpus_refs = corpus_assets.format_corpus_refs(refs)
        client = AIClient(self._current())
        prompt = dm_assets.build_dm_propose_prompt(
            context,
            cast,
            instruction,
            roll_note,
            extra_rules,
            corpus_refs,
            persona_id,
        )
        content = await client.chat([{"role": "user", "content": prompt}])
        data = extract_json(content)
        kind = str(data.get("kind") or "").strip()
        if kind not in {"roll", "narrate", "ask"}:
            raise ValueError(f"导游提案格式不正确(kind={kind or '空'}),请重试")
        options = data.get("options") or []
        if not isinstance(options, list):
            options = []
        thresholds = data.get("thresholds") or []
        if not isinstance(thresholds, list):
            thresholds = []
        return {
            "kind": kind,
            "summary": str(data.get("summary") or "").strip()[:200],
            "question": str(data.get("question") or "").strip()[:200],
            "expr": str(data.get("expr") or "").strip()[:40],
            "options": [str(x).strip() for x in options if str(x).strip()][:20],
            "thresholds": [str(x).strip() for x in thresholds if str(x).strip()][:12],
            "hint": str(data.get("hint") or "").strip()[:300],
            "persona": persona_id,
            "references": [
                {
                    "date": r.get("date", ""),
                    "page": r.get("page"),
                    "floor": r.get("floor"),
                    "category": r.get("category", ""),
                    "snippet": (r.get("snippet") or "")[:160],
                }
                for r in refs
            ],
        }

    async def dm_ankai_draft(
        self,
        topic: str,
        context: str = "",
        cast: str = "",
        count: int = 6,
        persona_id: str = dm_assets.PERSONA_ID,
    ) -> dict:
        """安价工作流:让导游以热心读者口吻起草候选选项(最终列表由导游/玩家编辑确认)。"""
        count = max(2, min(count, 12))
        client = AIClient(self._current())
        prompt = dm_assets.build_ankai_draft_prompt(
            topic, context, cast, count, persona_id
        )
        content = await client.chat([{"role": "user", "content": prompt}])
        data = extract_json(content)
        items = data.get("items") or []
        if not isinstance(items, list):
            items = []
        clean: list[str] = []
        for it in items:
            s = str(it).strip()
            if s:
                clean.append(s)
        return {"topic": topic.strip()[:60], "items": clean[:count]}
