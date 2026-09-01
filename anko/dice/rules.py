"""掷骰判定规则。

规则决定一次掷骰的结果等级(大成功 / 成功 / 失败 / 大失败)。
规则是可注册的:插件可以定义新的判定规则,例如
"COC 风格 (1d100 低于属性为成功)"、二值规则等。

默认提供经典安科 d100 规则。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Judgement:
    """一次判定的结果。"""

    code: str  # 机器码:crit_fail / fail / success / crit_success
    level: str  # 人类可读等级:大失败 / 失败 / 成功 / 大成功
    description: str  # 面向读者的描述文本

    def to_dict(self) -> dict:
        return asdict(self)


class JudgementRule(ABC):
    """判定规则基类。"""

    name: str = "base"

    @abstractmethod
    def applies(self, expression: str) -> bool:
        """该规则是否适用于这个掷骰表达式。"""
        ...

    @abstractmethod
    def judge(
        self, total: int, expression: str, config: dict
    ) -> Judgement:
        """根据出目与骰娘配置给出判定。"""
        ...


class D100Rule(JudgementRule):
    """经典安科 d100 判定。

    config(骰娘 settings 中的子集)说明:
      threshold:    成功阈值,默认 50;出目 > threshold 为成功。
      crit_success: 大成功临界,默认 95;出目 >= 95 为大成功。
      crit_fail:    大失败临界,默认 5;出目 <= 5 为大失败。
    """

    name = "d100"
    # 匹配:1d100、d100、d100+2、1d100-10 等
    _pattern = re.compile(
        r"^\s*(\d+)?d100\s*([+-]\s*\d+\s*)?$", re.IGNORECASE
    )

    def applies(self, expression: str) -> bool:
        return bool(self._pattern.match(expression))

    def judge(self, total: int, expression: str, config: dict) -> Judgement:
        threshold = int(config.get("threshold", 50))
        crit_success = int(config.get("crit_success", 95))
        crit_fail = int(config.get("crit_fail", 5))

        if total >= crit_success:
            return Judgement(
                "crit_success",
                "大成功",
                f"出目 {total} ≥ {crit_success}:命运的眷顾,大成功!",
            )
        if total <= crit_fail:
            return Judgement(
                "crit_fail",
                "大失败",
                f"出目 {total} ≤ {crit_fail}:天崩地裂,大失败!",
            )
        if total > threshold:
            return Judgement(
                "success",
                "成功",
                f"出目 {total} > {threshold}:判定成功。",
            )
        return Judgement(
            "fail",
            "失败",
            f"出目 {total} ≤ {threshold}:判定失败。",
        )


# 内置规则注册表(引擎默认加载)
BUILTIN_RULES: list[JudgementRule] = [D100Rule()]
