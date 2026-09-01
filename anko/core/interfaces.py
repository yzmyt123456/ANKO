"""存储层抽象接口。

业务服务只依赖这里的抽象,不依赖具体数据库实现。
当前提供 SQLite(SQLAlchemy)实现;未来可增加 JSON 文件、PostgreSQL 等实现,
只要实现本接口即可无缝接入,业务代码无需改动。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class Storage(ABC):
    """统一的数据存取接口。

    所有方法的返回值都是 ORM 实体对象(dict 的子类/普通对象),
    具体形态由实现决定;业务层只调用接口并读取属性。
    """

    # ---------- 人物卡 ----------
    @abstractmethod
    def create_character(self, data: dict) -> Any: ...

    @abstractmethod
    def get_character(self, character_id: int) -> Optional[Any]: ...

    @abstractmethod
    def list_characters(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Any]: ...

    @abstractmethod
    def update_character(self, character_id: int, data: dict) -> Optional[Any]: ...

    @abstractmethod
    def delete_character(self, character_id: int) -> bool: ...

    # ---------- 剧情 / 故事线 ----------
    @abstractmethod
    def create_story(self, data: dict) -> Any: ...

    @abstractmethod
    def get_story(self, story_id: int) -> Optional[Any]: ...

    @abstractmethod
    def list_stories(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Any]: ...

    @abstractmethod
    def update_story(self, story_id: int, data: dict) -> Optional[Any]: ...

    @abstractmethod
    def delete_story(self, story_id: int) -> bool: ...

    # ---------- 剧情条目 ----------
    @abstractmethod
    def create_entry(self, story_id: int, data: dict) -> Any: ...

    @abstractmethod
    def list_entries(
        self, story_id: int, *, offset: int = 0, limit: int = 100
    ) -> list[Any]: ...

    # ---------- 骰娘 ----------
    @abstractmethod
    def create_maid(self, data: dict) -> Any: ...

    @abstractmethod
    def get_maid(self, maid_id: int) -> Optional[Any]: ...

    @abstractmethod
    def get_maid_by_name(self, name: str) -> Optional[Any]: ...

    @abstractmethod
    def list_maids(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Any]: ...

    @abstractmethod
    def update_maid(self, maid_id: int, data: dict) -> Optional[Any]: ...

    @abstractmethod
    def delete_maid(self, maid_id: int) -> bool: ...

    # ---------- 掷骰记录 ----------
    @abstractmethod
    def create_roll(self, data: dict) -> Any: ...

    @abstractmethod
    def get_roll(self, roll_id: int) -> Optional[Any]: ...

    @abstractmethod
    def list_rolls(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Any]: ...
