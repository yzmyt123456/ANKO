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
    """一张人物卡。

    设计要点:
    - template:人物卡模板(默认 default,可扩展 dnd5e 等)。
    - stats:模板相关的结构化字段(如 DND 的六属性/AC/法术等)。
    - attributes:通用自由属性字典,非模板字段,如 {"力量": 18}。
    - extra:预留自由扩展字段,后续功能可直接写入,无需改表结构。
    """

    __tablename__ = "character_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    bio: Mapped[Optional[str]] = mapped_column(Text, default=None)
    # 人物卡模板:default / dnd5e / 插件可扩展
    template: Mapped[str] = mapped_column(String(50), default="default", index=True)
    # 模板结构化字段(如 DND 六属性/AC/法术/熟练)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CharacterCard id={self.id} name={self.name!r}>"
