"""剧情 / 故事线模型。

Story       —— 一条安科故事线(串子)
StoryEntry  —— 故事线中的一个剧情条目(一段正文)

entry 通过 character_ids / roll_ids 与人物卡、掷骰记录建立关联,
不强制外键关系,方便未来做版本管理与重排。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from anko.models.base import Base, TimestampMixin


class Story(Base, TimestampMixin):
    """一条安科故事线。"""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    # 默认使用的骰娘(DiceMaid.id,可空:不强制绑定)
    maid_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("dice_maids.id", ondelete="SET NULL"), default=None
    )
    tags: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Story id={self.id} title={self.title!r}>"


class StoryEntry(Base, TimestampMixin):
    """故事线中的一个剧情条目。"""

    __tablename__ = "story_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 章节/幕,如 "第一章",可由作者自由命名
    chapter: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 关联的人物卡 id 列表 / 掷骰记录 id 列表
    character_ids: Mapped[list] = mapped_column(JSON, default=list)
    roll_ids: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StoryEntry id={self.id} story_id={self.story_id}>"
