"""人物卡业务服务。"""

from __future__ import annotations

from typing import Any, Optional

from anko.core.interfaces import Storage


class CharacterService:
    """人物卡的创建、查询、更新、删除。"""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def create(self, data: dict) -> Any:
        payload = {
            "name": data["name"],
            "title": data.get("title"),
            "avatar": data.get("avatar"),
            "bio": data.get("bio"),
            "attributes": data.get("attributes") or {},
            "tags": data.get("tags") or [],
            "extra": data.get("extra") or {},
        }
        return self._storage.create_character(payload)

    def get(self, character_id: int) -> Optional[Any]:
        return self._storage.get_character(character_id)

    def list(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[Any]:
        return self._storage.list_characters(
            offset=offset, limit=limit, **filters
        )

    def update(self, character_id: int, data: dict) -> Optional[Any]:
        payload = {
            k: v
            for k, v in data.items()
            if k
            in {
                "name",
                "title",
                "avatar",
                "bio",
                "attributes",
                "tags",
                "extra",
            }
        }
        if not payload:
            return self._storage.get_character(character_id)
        return self._storage.update_character(character_id, payload)

    def delete(self, character_id: int) -> bool:
        return self._storage.delete_character(character_id)
