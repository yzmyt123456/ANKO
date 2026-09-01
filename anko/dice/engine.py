"""骰子引擎:把表达式、骰娘配置、判定规则串起来。

流程:
  1. 解析并执行骰子表达式
  2. 应用骰娘设定的"命运修正"(modifiers)
  3. 用匹配的判定规则给出结果等级(若有)
  4. 生成人类可读描述

引擎是可扩展的:
  - register_rule():注册自定义判定规则
  - register_modifier():注册自定义骰子修正方式(供插件调用)
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable, Optional

from anko.dice.expression import DiceExprError, RollResult, roll_expression
from anko.dice.maids import MaidConfig
from anko.dice.rules import BUILTIN_RULES, Judgement, JudgementRule

# 修正器签名:接收 (出目, RollResult, 骰娘 settings) -> 修正后出目
Modifier = Callable[[int, RollResult, dict], int]


@dataclass
class RollOutcome:
    """一次掷骰的最终结果(纯计算,不落库)。"""

    result: RollResult
    judgement: Optional[Judgement] = None
    description: str = ""

    def to_dict(self) -> dict:
        data = {
            "expression": self.result.expression,
            "total": self.result.total,
            "parts": [
                {
                    "kind": p.kind,
                    "label": p.label,
                    "value": p.value,
                    "results": p.results,
                }
                for p in self.result.parts
            ],
            "description": self.description,
        }
        if self.judgement:
            data["judgement"] = self.judgement.to_dict()
        return data


class DiceEngine:
    """骰子执行引擎(无状态,可安全复用)。"""

    def __init__(self) -> None:
        self._rules: dict[str, JudgementRule] = {}
        self._modifiers: dict[str, Modifier] = {}
        for rule in BUILTIN_RULES:
            self.register_rule(rule)

    # ---------------- 扩展注册 ----------------
    def register_rule(self, rule: JudgementRule) -> None:
        """注册判定规则(同名覆盖),供平台与插件调用。"""
        self._rules[rule.name] = rule

    def register_modifier(self, name: str, modifier: Modifier) -> None:
        """注册一个具名修正器,供骰娘 settings 引用。

        骰娘 settings 示例:
          modifiers: [{"type": "add", "value": 5}]
          modifiers: [{"type": "plugin_<name>", "value": ...}]
        """
        self._modifiers[name] = modifier

    # ---------------- 核心掷骰 ----------------
    def roll(
        self,
        expression: str,
        maid: Optional[MaidConfig] = None,
        rng: Optional[Random] = None,
    ) -> RollOutcome:
        """执行一次掷骰并给出判定结果。"""
        settings = maid.settings if maid else {}

        # 1. 掷骰
        result = roll_expression(expression, rng)

        # 2. 命运修正
        modified_total = self._apply_modifiers(result, settings)

        # 3. 判定
        judgement = self._judge(expression, modified_total, settings)

        # 4. 描述
        parts: list[str] = [result.describe()]
        if modified_total != result.total:
            parts.append(f"(命运修正后 {modified_total})")
        if judgement:
            parts.append(judgement.description)
        description = "\n".join(parts)

        outcome = RollOutcome(
            result=RollResult(
                expression=expression, total=modified_total, parts=result.parts
            ),
            judgement=judgement,
            description=description,
        )
        return outcome

    # ---------------- 内部工具 ----------------
    def _apply_modifiers(self, result: RollResult, settings: dict) -> int:
        total = result.total
        for item in settings.get("modifiers") or []:
            if not isinstance(item, dict):
                continue
            type_ = item.get("type")
            if type_ == "add":
                total += int(item.get("value", 0))
            elif type_ == "multiply":
                total *= int(item.get("value", 1))
            elif type_ in self._modifiers:
                total = self._modifiers[type_](total, result, settings)
        return total

    def _judge(
        self, expression: str, total: int, settings: dict
    ) -> Optional[Judgement]:
        for rule in self._rules.values():
            if rule.applies(expression):
                return rule.judge(total, expression, settings)
        return None

    def parse(self, expression: str) -> object:
        """暴露表达式解析(供校验/测试使用)。"""
        return roll_expression(expression).parts  # 仅用于校验语法


__all__ = [
    "DiceEngine",
    "RollOutcome",
    "Modifier",
    "DiceExprError",
]
