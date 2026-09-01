"""骰娘配置对象与工具。

一个"自定义骰娘" = 数据库中的一条 DiceMaid 记录。
MaidConfig 是运行时的不可变配置视图,由 DiceEngine 消费。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from anko.models import DiceMaid


@dataclass
class MaidConfig:
    """骰娘的运行时配置视图。"""

    id: Optional[int]
    name: str
    personality: Optional[str] = None
    greeting: Optional[str] = None
    default_expression: str = "1d100"
    settings: dict = field(default_factory=dict)
    is_system: bool = False
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_model(cls, model: DiceMaid) -> "MaidConfig":
        return cls(
            id=model.id,
            name=model.name,
            personality=model.personality,
            greeting=model.greeting,
            default_expression=model.default_expression,
            settings=dict(model.settings or {}),
            is_system=model.is_system,
            extra=dict(model.extra or {}),
        )


def default_maid_data(name: str) -> dict:
    """系统内置骰娘的初始数据。"""
    return {
        "name": name,
        "personality": (
            "沉稳而公正的命运之骰,从不偏袒任何人,"
            "只是安静地掷出每一次结果。"
        ),
        "greeting": "命运之骰在此聆听。请问要掷出什么?",
        "default_expression": "1d100",
        "settings": {
            "threshold": 50,
            "crit_success": 95,
            "crit_fail": 5,
        },
        "is_system": True,
        "extra": {},
    }
