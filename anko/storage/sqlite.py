"""Storage 接口的 SQLAlchemy(SQLite)实现。

每个方法独立提交事务,简单可靠;后续如需要复杂事务可扩展为
由服务层统一管理 session。
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from anko.core.interfaces import Storage
from anko.models import CharacterCard, DiceMaid, DiceRoll, Story, StoryEntry


def _apply_filters(query: Any, model: type, filters: dict) -> Any:
    """按 filters 逐字段等值过滤,忽略值为 None 的项。"""
    for key, value in filters.items():
        if value is not None and hasattr(model, key):
            query = query.where(getattr(model, key) == value)
    return query


class SqliteStorage(Storage):
    """基于 SQLAlchemy 会话的存储实现。"""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _session(self) -> Session:
        return self._session_factory()

    # ---------- 人物卡 ----------
    def create_character(self, data: dict) -> CharacterCard:
        with self._session() as session:
            obj = CharacterCard(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def get_character(self, character_id: int) -> Optional[CharacterCard]:
        with self._session() as session:
            return session.get(CharacterCard, character_id)

    def list_characters(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[CharacterCard]:
        with self._session() as session:
            query = _apply_filters(select(CharacterCard), CharacterCard, filters)
            return list(
                session.execute(
                    query.order_by(CharacterCard.id).offset(offset).limit(limit)
                )
                .scalars()
                .all()
            )

    def update_character(self, character_id: int, data: dict) -> Optional[CharacterCard]:
        with self._session() as session:
            obj = session.get(CharacterCard, character_id)
            if obj is None:
                return None
            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            session.commit()
            session.refresh(obj)
            return obj

    def delete_character(self, character_id: int) -> bool:
        with self._session() as session:
            obj = session.get(CharacterCard, character_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            return True

    # ---------- 剧情 ----------
    def create_story(self, data: dict) -> Story:
        with self._session() as session:
            obj = Story(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def get_story(self, story_id: int) -> Optional[Story]:
        with self._session() as session:
            return session.get(Story, story_id)

    def list_stories(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Story]:
        with self._session() as session:
            query = _apply_filters(select(Story), Story, filters)
            return list(
                session.execute(query.order_by(Story.id).offset(offset).limit(limit))
                .scalars()
                .all()
            )

    def update_story(self, story_id: int, data: dict) -> Optional[Story]:
        with self._session() as session:
            obj = session.get(Story, story_id)
            if obj is None:
                return None
            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            session.commit()
            session.refresh(obj)
            return obj

    def delete_story(self, story_id: int) -> bool:
        with self._session() as session:
            obj = session.get(Story, story_id)
            if obj is None:
                return False

    # ---------- 剧情条目 ----------
    def create_entry(self, story_id: int, data: dict) -> StoryEntry:
        with self._session() as session:
            obj = StoryEntry(story_id=story_id, **data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def list_entries(
        self, story_id: int, *, offset: int = 0, limit: int = 100
    ) -> list[StoryEntry]:
        with self._session() as session:
            query = select(StoryEntry).where(StoryEntry.story_id == story_id)
            return list(
                session.execute(query.order_by(StoryEntry.id).offset(offset).limit(limit))
                .scalars()
                .all()
            )

    # ---------- 骰娘 ----------
    def create_maid(self, data: dict) -> DiceMaid:
        with self._session() as session:
            obj = DiceMaid(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def get_maid(self, maid_id: int) -> Optional[DiceMaid]:
        with self._session() as session:
            return session.get(DiceMaid, maid_id)

    def get_maid_by_name(self, name: str) -> Optional[DiceMaid]:
        with self._session() as session:
            return session.execute(
                select(DiceMaid).where(DiceMaid.name == name)
            ).scalar_one_or_none()

    def list_maids(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[DiceMaid]:
        with self._session() as session:
            query = _apply_filters(select(DiceMaid), DiceMaid, filters)
            return list(
                session.execute(query.order_by(DiceMaid.id).offset(offset).limit(limit))
                .scalars()
                .all()
            )

    def update_maid(self, maid_id: int, data: dict) -> Optional[DiceMaid]:
        with self._session() as session:
            obj = session.get(DiceMaid, maid_id)
            if obj is None:
                return None
            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            session.commit()
            session.refresh(obj)
            return obj

    def delete_maid(self, maid_id: int) -> bool:
        with self._session() as session:
            obj = session.get(DiceMaid, maid_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            return True

    # ---------- 掷骰记录 ----------
    def create_roll(self, data: dict) -> DiceRoll:
        with self._session() as session:
            obj = DiceRoll(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def get_roll(self, roll_id: int) -> Optional[DiceRoll]:
        with self._session() as session:
            return session.get(DiceRoll, roll_id)

    def list_rolls(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[DiceRoll]:
        with self._session() as session:
            query = _apply_filters(select(DiceRoll), DiceRoll, filters)
            return list(
                session.execute(query.order_by(DiceRoll.id).offset(offset).limit(limit))
                .scalars()
                .all()
            )

            session.delete(obj)
            session.commit()
            return True
