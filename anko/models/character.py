"""人物卡模型。

设计要点:
- attributes:可自定义属性组字典,如 {"力量": 18, "敏捷": 12}。
- extra:预留自由扩展字段,后续功能(装备/技能/羁绊等)可直接写入,
  无需改动数据库表结构,保证向前兼容。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from anko.models.base import Base, TimestampMixin


class CharacterCard(Base, TimestampMixin):
    """一张人物卡。"""

    __tablename__ = "character_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    bio: Mapped[Optional[str]] = mapped_column(Text, default=None)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CharacterCard id={self.id} name={self.name!r}>"
