"""剧情 / 故事线业务服务。"""

from __future__ import annotations

from typing import Any, Optional

from anko.core.interfaces import Storage


class StoryService:
    """故事线与其条目的创建、查询、更新、删除。"""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    # ---------- 故事线 ----------
    def create(self, data: dict) -> Any:
        payload = {
            "title": data["title"],
            "description": data.get("description"),
            "maid_id": data.get("maid_id"),
            "tags": data.get("tags") or [],
            "extra": data.get("extra") or {},
        }
        return self._storage.create_story(payload)

    def get(self, story_id: int) -> Optional[Any]:
        return self._storage.get_story(story_id)

    def list(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Any]:
        return self._storage.list_stories(offset=offset, limit=limit, **filters)

    def update(self, story_id: int, data: dict) -> Optional[Any]:
        payload = {
            k: v
            for k, v in data.items()
            if k in {"title", "description", "maid_id", "tags", "extra"}
        }
        if not payload:
            return self._storage.get_story(story_id)
        return self._storage.update_story(story_id, payload)

    def delete(self, story_id: int) -> bool:
        return self._storage.delete_story(story_id)

    # ---------- 剧情条目 ----------
    def add_entry(self, story_id: int, data: dict) -> Any:
        payload = {
            "chapter": data.get("chapter"),
            "content": data["content"],
            "character_ids": data.get("character_ids") or [],
            "roll_ids": data.get("roll_ids") or [],
            "extra": data.get("extra") or {},
        }
        return self._storage.create_entry(story_id, payload)

    def list_entries(
        self, story_id: int, *, offset: int = 0, limit: int = 100
    ) -> list[Any]:
        return self._storage.list_entries(
            story_id, offset=offset, limit=limit
        )
