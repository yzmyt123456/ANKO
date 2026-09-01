"""骰娘与掷骰记录模型。

DiceMaid —— 一个骰娘(可以理解为"有人设的骰子执行器"):
           名字 / 人设 / 开场白 / 默认骰子 / 判定规则配置都存放在 settings 中,
           所以"自定义骰娘"本质上就是配置一条记录,引擎按配置执行。

DiceRoll —— 一次掷骰的完整记录(含每粒骰子的明细与判定结果),
            便于回看历史、追剧情。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from anko.models.base import Base, TimestampMixin


class DiceMaid(Base, TimestampMixin):
    """一个可自定义的骰娘。"""

    __tablename__ = "dice_maids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # 人设 / 性格 / 说话风格描述(未来可接入 LLM 扮演)
    personality: Mapped[Optional[str]] = mapped_column(Text, default=None)
    # 开场白
    greeting: Mapped[Optional[str]] = mapped_column(Text, default=None)
    # 默认骰子表达式,如 "1d100"
    default_expression: Mapped[str] = mapped_column(String(50), default="1d100")
    # 判定规则配置,如 {"threshold": 50, "crit_success": 95, "crit_fail": 5}
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    # 系统内置骰娘不可删除
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DiceMaid id={self.id} name={self.name!r}>"


class DiceRoll(Base, TimestampMixin):
    """一次掷骰的完整记录。"""

    __tablename__ = "dice_rolls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    maid_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("dice_maids.id", ondelete="SET NULL"), default=None
    )
    expression: Mapped[str] = mapped_column(String(200), nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    # 每粒骰子的明细,如 [{"dice": "1d100", "results": [67], "subtotal": 67}]
    details: Mapped[list] = mapped_column(JSON, default=list)
    # 判定结果,如 {"code": "success", "level": "成功", "description": "..."}
    judgement: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    # 关联上下文:如 {"story_id": 1, "entry_id": 3, "character_id": 2}
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[Optional[str]] = mapped_column(Text, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DiceRoll id={self.id} expr={self.expression!r} total={self.total}>"
