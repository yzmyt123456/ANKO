"""人物卡业务服务。"""

from __future__ import annotations

from typing import Any, Optional

from anko.core.interfaces import Storage
from anko.dice.engine import DiceEngine, RollOutcome
from anko.dice.rules import Judgement
from anko.templates.registry import (
    DND_STAT_KEYS,
    CheckDef,
    dnd_modifier,
    get_template,
)


class CharacterService:
    """人物卡的创建、查询、更新、删除与 DND 鉴定。"""

    def __init__(
        self, storage: Storage, dice_engine: Optional[DiceEngine] = None
    ) -> None:
        self._storage = storage
        self._dice_engine = dice_engine or DiceEngine()

    def create(self, data: dict) -> Any:
        payload = {
            "name": data["name"],
            "title": data.get("title"),
            "avatar": data.get("avatar"),
            "bio": data.get("bio"),
            "template": data.get("template") or "default",
            "stats": data.get("stats") or {},
            "attributes": data.get("attributes") or {},
            "tags": data.get("tags") or [],
            "extra": data.get("extra") or {},
        }
        return self._storage.create_character(payload)

    def get(self, character_id: int) -> Optional[Any]:
        return self._storage.get_character(character_id)

    def list(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Any]:
        return self._storage.list_characters(
            offset=offset, limit=limit, **filters
        )

    def update(self, character_id: int, data: dict) -> Optional[Any]:
        payload = {
            k: v
            for k, v in data.items()
            if k
            in {
                "name",
                "title",
                "avatar",
                "bio",
                "template",
                "stats",
                "attributes",
                "tags",
                "extra",
            }
        }
        if not payload:
            return self._storage.get_character(character_id)
        return self._storage.update_character(character_id, payload)

    def delete(self, character_id: int) -> bool:
        return self._storage.delete_character(character_id)

    # ---------------- DND 鉴定 ----------------
    def perform_check(
        self,
        character_id: int,
        kind: str,
        key: str,
        dc: Optional[int] = None,
    ) -> dict:
        """执行一次 DND 鉴定:1d20 + 属性修正(+ 熟练加值)。

        kind: stat(属性鉴定)/ skill(技能鉴定)/ save(豁免鉴定)
        """
        character = self._storage.get_character(character_id)
        if character is None:
            raise KeyError(f"人物卡不存在:{character_id}")
        if character.template != "dnd5e":
            raise ValueError("仅 DND 5e 模板的人物卡支持鉴定掷骰")

        template = get_template("dnd5e")
        check: Optional[CheckDef] = None
        for c in template.checks:
            if c.kind == kind and c.key == key:
                check = c
                break
        if check is None:
            raise ValueError(f"未知鉴定项:{kind}/{key}")

        stats = character.stats or {}
        modifier = dnd_modifier(stats.get(check.stat))
        bonus = modifier

        # 熟练加值:技能熟练 或 豁免熟练 中命中则追加
        prof_text_field = (
            "skill_proficiencies" if kind == "skill" else "save_proficiencies"
        )
        prof_text = str(stats.get(prof_text_field) or "")
        if check.prof and check.prof in prof_text:
            try:
                bonus += int(stats.get("proficiency_bonus") or 0)
            except (TypeError, ValueError):
                pass

        expr = f"1d20{bonus:+d}"
        outcome: RollOutcome = self._dice_engine.roll(expr, maid=None)
        natural = outcome.result.parts[0].results[0]
        total = outcome.result.total

        judgement = self._judge_check(natural, total, dc)
        desc = (
            f"{character.name} 的「{check.label}」:{expr} = {total}"
        )
        if judgement:
            desc += f"\n{judgement.description}"
        elif dc is not None:
            desc += f"\n(未判定,DC {dc})"
        else:
            desc += "\n(未设置 DC,仅查看出目)"

        return {
            "character_id": character.id,
            "label": check.label,
            "kind": kind,
            "expression": expr,
            "natural": natural,
            "modifier": bonus,
            "total": total,
            "judgement": judgement.to_dict() if judgement else None,
            "description": desc,
        }

    @staticmethod
    def _judge_check(
        natural: int, total: int, dc: Optional[int]
    ) -> Optional[Judgement]:
        """DND 鉴定判定:裸 20 大成功、裸 1 大失败;否则与 DC 比较。"""
        if natural == 20:
            return Judgement(
                "crit_success", "大成功", f"骰出 20!大成功!"
            )
        if natural == 1:
            return Judgement(
                "crit_fail", "大失败", f"骰出 1!大失败!"
            )
        if dc is not None:
            if total >= dc:
                return Judgement(
                    "success", "成功", f"{total} ≥ DC {dc}:鉴定成功。"
                )
            return Judgement(
                "fail", "失败", f"{total} < DC {dc}:鉴定失败。"
            )
        return None
